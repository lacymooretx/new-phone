use std::sync::Arc;

use anyhow::{Context, Result};
use tokio::io::{AsyncReadExt, AsyncWriteExt};
use tokio::net::{TcpListener, TcpStream};
use tracing::{debug, error, info, warn};

use crate::config::Config;
use crate::load_balancer::LoadBalancer;
use crate::sip_parser::{SipMessage, SipMethod};

/// The SIP proxy server.
pub struct SipProxy {
    config: Config,
    load_balancer: Arc<LoadBalancer>,
}

impl SipProxy {
    pub fn new(config: Config, load_balancer: Arc<LoadBalancer>) -> Self {
        SipProxy {
            config,
            load_balancer,
        }
    }

    /// Start the TLS SIP proxy listener.
    /// If TLS cert/key are configured, uses TLS. Otherwise, falls back to plain TCP
    /// (for development only).
    pub async fn run(&self, shutdown: tokio::sync::watch::Receiver<bool>) -> Result<()> {
        let listener = TcpListener::bind(&self.config.listen_addr)
            .await
            .with_context(|| format!("failed to bind to {}", self.config.listen_addr))?;

        info!(addr = %self.config.listen_addr, "SIP proxy listening");

        // Optionally load TLS config
        let tls_acceptor = if let (Some(cert_path), Some(key_path)) =
            (&self.config.tls_cert, &self.config.tls_key)
        {
            match load_tls_config(cert_path, key_path) {
                Ok(config) => {
                    info!("TLS enabled for SIP proxy");
                    Some(tokio_rustls::TlsAcceptor::from(Arc::new(config)))
                }
                Err(e) => {
                    warn!(error = %e, "failed to load TLS config, running in plain TCP mode");
                    None
                }
            }
        } else {
            info!("no TLS cert/key configured, running in plain TCP mode (dev only)");
            None
        };

        let mut shutdown = shutdown;
        loop {
            tokio::select! {
                accept_result = listener.accept() => {
                    match accept_result {
                        Ok((stream, peer_addr)) => {
                            debug!(peer = %peer_addr, "accepted connection");
                            let lb = self.load_balancer.clone();
                            let tls = tls_acceptor.clone();

                            tokio::spawn(async move {
                                if let Err(e) = handle_connection(stream, lb, tls).await {
                                    debug!(peer = %peer_addr, error = %e, "connection error");
                                }
                            });
                        }
                        Err(e) => {
                            error!(error = %e, "failed to accept connection");
                        }
                    }
                }
                _ = shutdown.changed() => {
                    info!("SIP proxy shutting down");
                    break;
                }
            }
        }

        Ok(())
    }
}

fn load_tls_config(
    cert_path: &str,
    key_path: &str,
) -> Result<rustls::ServerConfig> {
    use rustls_pemfile::{certs, private_key};
    use std::io::BufReader;

    let cert_file = std::fs::File::open(cert_path)
        .with_context(|| format!("failed to open cert file: {}", cert_path))?;
    let key_file = std::fs::File::open(key_path)
        .with_context(|| format!("failed to open key file: {}", key_path))?;

    let cert_chain: Vec<_> = certs(&mut BufReader::new(cert_file))
        .filter_map(|r| r.ok())
        .collect();

    let key = private_key(&mut BufReader::new(key_file))
        .map_err(|e| anyhow::anyhow!("failed to read private key: {}", e))?
        .ok_or_else(|| anyhow::anyhow!("no private key found in file"))?;

    let config = rustls::ServerConfig::builder()
        .with_no_client_auth()
        .with_single_cert(cert_chain, key)
        .context("failed to build TLS server config")?;

    Ok(config)
}

async fn handle_connection(
    stream: TcpStream,
    lb: Arc<LoadBalancer>,
    tls_acceptor: Option<tokio_rustls::TlsAcceptor>,
) -> Result<()> {
    if let Some(acceptor) = tls_acceptor {
        let tls_stream = acceptor
            .accept(stream)
            .await
            .context("TLS handshake failed")?;
        let (reader, writer) = tokio::io::split(tls_stream);
        process_sip_stream(reader, writer, lb).await
    } else {
        let (reader, writer) = stream.into_split();
        process_sip_stream(reader, writer, lb).await
    }
}

async fn process_sip_stream<R, W>(mut reader: R, mut writer: W, lb: Arc<LoadBalancer>) -> Result<()>
where
    R: tokio::io::AsyncRead + Unpin,
    W: tokio::io::AsyncWrite + Unpin,
{
    let mut buf = vec![0u8; 65536];
    let proxy_via = format!(
        "SIP/2.0/TLS {};branch=z9hG4bK{}",
        "proxy.local:5061",
        uuid::Uuid::new_v4().to_string().replace('-', "")
    );

    loop {
        let n = reader.read(&mut buf).await?;
        if n == 0 {
            debug!("client disconnected");
            break;
        }

        let data = &buf[..n];
        match SipMessage::parse(data) {
            Ok(msg) => {
                if msg.is_request() {
                    // Select backend
                    let backend_addr = match lb.select_backend(&msg).await {
                        Some(addr) => addr,
                        None => {
                            warn!("no healthy backend, sending 503");
                            let response = build_503_response(&msg);
                            writer.write_all(response.as_bytes()).await?;
                            continue;
                        }
                    };

                    debug!(
                        method = ?msg.method(),
                        backend = %backend_addr,
                        call_id = ?msg.call_id(),
                        "forwarding request to backend"
                    );

                    // Add Via header and forward
                    let forwarded = msg.add_via_and_serialize(&proxy_via);

                    lb.increment_connections(&backend_addr).await;

                    match forward_to_backend(&backend_addr, &forwarded).await {
                        Ok(response_data) => {
                            writer.write_all(&response_data).await?;

                            // If this is a BYE, clean up the dialog binding
                            if msg.method() == Some(&SipMethod::Bye) {
                                if let Some(call_id) = msg.call_id() {
                                    lb.remove_dialog(call_id).await;
                                }
                            }
                        }
                        Err(e) => {
                            warn!(
                                backend = %backend_addr,
                                error = %e,
                                "backend forwarding failed"
                            );
                            let response = build_502_response(&msg);
                            writer.write_all(response.as_bytes()).await?;
                        }
                    }

                    lb.decrement_connections(&backend_addr).await;
                } else {
                    // It's a response, just forward as-is
                    debug!(
                        status = ?msg.status_code(),
                        "forwarding response"
                    );
                    writer.write_all(data).await?;
                }
            }
            Err(e) => {
                warn!(error = %e, "failed to parse SIP message, forwarding raw");
                writer.write_all(data).await?;
            }
        }
    }

    Ok(())
}

async fn forward_to_backend(backend_addr: &str, data: &[u8]) -> Result<Vec<u8>> {
    use tokio::time::{timeout, Duration};

    let stream = timeout(Duration::from_secs(5), TcpStream::connect(backend_addr))
        .await
        .context("backend connection timeout")?
        .context("failed to connect to backend")?;

    let (mut reader, mut writer) = stream.into_split();
    writer.write_all(data).await?;

    let mut response = vec![0u8; 65536];
    let n = timeout(Duration::from_secs(30), reader.read(&mut response))
        .await
        .context("backend response timeout")?
        .context("failed to read backend response")?;

    Ok(response[..n].to_vec())
}

fn build_503_response(request: &SipMessage) -> String {
    let call_id = request.call_id().unwrap_or("unknown");
    let from = request.sip_from().unwrap_or("<sip:unknown>");
    let to = request.to_header().unwrap_or("<sip:unknown>");
    let cseq = request.cseq().unwrap_or("1 UNKNOWN");
    let via = request.via().unwrap_or("SIP/2.0/TLS unknown");

    format!(
        "SIP/2.0 503 Service Unavailable\r\n\
         Via: {}\r\n\
         From: {}\r\n\
         To: {}\r\n\
         Call-ID: {}\r\n\
         CSeq: {}\r\n\
         Content-Length: 0\r\n\
         \r\n",
        via, from, to, call_id, cseq
    )
}

fn build_502_response(request: &SipMessage) -> String {
    let call_id = request.call_id().unwrap_or("unknown");
    let from = request.sip_from().unwrap_or("<sip:unknown>");
    let to = request.to_header().unwrap_or("<sip:unknown>");
    let cseq = request.cseq().unwrap_or("1 UNKNOWN");
    let via = request.via().unwrap_or("SIP/2.0/TLS unknown");

    format!(
        "SIP/2.0 502 Bad Gateway\r\n\
         Via: {}\r\n\
         From: {}\r\n\
         To: {}\r\n\
         Call-ID: {}\r\n\
         CSeq: {}\r\n\
         Content-Length: 0\r\n\
         \r\n",
        via, from, to, call_id, cseq
    )
}
