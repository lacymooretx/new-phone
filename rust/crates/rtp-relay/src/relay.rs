use std::collections::HashMap;
use std::net::SocketAddr;
use std::sync::Arc;

use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use tokio::net::UdpSocket;
use tokio::sync::{watch, RwLock};
use tracing::{debug, error, info, warn};
use uuid::Uuid;

use crate::srtp::SrtpContext;
use crate::stats::SessionStats;

/// A relay session represents a bidirectional media path between two endpoints.
#[derive(Debug, Clone, Serialize)]
pub struct RelaySession {
    pub session_id: String,
    pub caller_addr: Option<SocketAddr>,
    pub callee_addr: Option<SocketAddr>,
    pub caller_port: u16,
    pub callee_port: u16,
    pub created_at: u64,
}

#[derive(Debug, Deserialize)]
pub struct CreateSessionRequest {
    pub caller_addr: Option<String>,
    pub callee_addr: Option<String>,
    pub use_srtp: bool,
    pub master_key: Option<String>,
    pub master_salt: Option<String>,
}

#[derive(Debug, Serialize)]
pub struct CreateSessionResponse {
    pub session_id: String,
    pub caller_port: u16,
    pub callee_port: u16,
}

/// Port allocator for RTP sessions.
pub struct PortAllocator {
    min_port: u16,
    max_port: u16,
    allocated: Arc<RwLock<Vec<u16>>>,
}

impl PortAllocator {
    pub fn new(min_port: u16, max_port: u16) -> Self {
        PortAllocator {
            min_port,
            max_port,
            allocated: Arc::new(RwLock::new(Vec::new())),
        }
    }

    /// Allocate a pair of consecutive ports (RTP + RTCP).
    pub async fn allocate_pair(&self) -> Option<(u16, u16)> {
        let mut allocated = self.allocated.write().await;

        // Find an even port that's available (RTP uses even, RTCP uses odd)
        let mut port = self.min_port;
        if !port.is_multiple_of(2) {
            port += 1;
        }

        while port < self.max_port {
            if !allocated.contains(&port) && !allocated.contains(&(port + 1)) {
                allocated.push(port);
                allocated.push(port + 1);
                return Some((port, port + 1));
            }
            port += 2;
        }

        None
    }

    /// Release a pair of ports.
    pub async fn release_pair(&self, rtp_port: u16) {
        let mut allocated = self.allocated.write().await;
        allocated.retain(|&p| p != rtp_port && p != rtp_port + 1);
    }
}

struct ActiveRelay {
    session: RelaySession,
    _shutdown_tx: watch::Sender<bool>,
    stats: Arc<RwLock<SessionStats>>,
}

/// The relay manager handles creation and lifecycle of relay sessions.
pub struct RelayManager {
    port_allocator: PortAllocator,
    external_ip: String,
    sessions: Arc<RwLock<HashMap<String, ActiveRelay>>>,
}

impl RelayManager {
    pub fn new(port_min: u16, port_max: u16, external_ip: String) -> Self {
        RelayManager {
            port_allocator: PortAllocator::new(port_min, port_max),
            external_ip,
            sessions: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    /// Create a new relay session with allocated port pairs.
    pub async fn create_session(
        &self,
        request: CreateSessionRequest,
    ) -> Result<CreateSessionResponse> {
        let session_id = Uuid::new_v4().to_string();

        // Allocate two port pairs (one for each leg)
        let (caller_rtp, _caller_rtcp) = self
            .port_allocator
            .allocate_pair()
            .await
            .context("no ports available for caller leg")?;

        let (callee_rtp, _callee_rtcp) = self
            .port_allocator
            .allocate_pair()
            .await
            .context("no ports available for callee leg")?;

        let caller_addr = request
            .caller_addr
            .as_deref()
            .and_then(|s| s.parse::<SocketAddr>().ok());
        let callee_addr = request
            .callee_addr
            .as_deref()
            .and_then(|s| s.parse::<SocketAddr>().ok());

        let session = RelaySession {
            session_id: session_id.clone(),
            caller_addr,
            callee_addr,
            caller_port: caller_rtp,
            callee_port: callee_rtp,
            created_at: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap_or_default()
                .as_secs(),
        };

        let stats = Arc::new(RwLock::new(SessionStats::new(&session_id)));

        // Build optional SRTP contexts
        let srtp_ctx = if request.use_srtp {
            if let (Some(key_hex), Some(salt_hex)) = (&request.master_key, &request.master_salt) {
                let key = hex_decode(key_hex).context("invalid master key hex")?;
                let salt = hex_decode(salt_hex).context("invalid master salt hex")?;
                Some((
                    SrtpContext::new(&key, &salt).context("failed to create caller SRTP")?,
                    SrtpContext::new(&key, &salt).context("failed to create callee SRTP")?,
                ))
            } else {
                None
            }
        } else {
            None
        };

        // Shutdown channel for this session
        let (shutdown_tx, shutdown_rx) = watch::channel(false);
        let relay_stats = stats.clone();

        // Spawn the relay task
        let bind_ip = self.external_ip.clone();
        let session_clone = session.clone();
        tokio::spawn(async move {
            if let Err(e) = run_relay(
                session_clone,
                &bind_ip,
                srtp_ctx,
                relay_stats,
                shutdown_rx,
            )
            .await
            {
                warn!(error = %e, "relay task error");
            }
        });

        let active = ActiveRelay {
            session: session.clone(),
            _shutdown_tx: shutdown_tx,
            stats,
        };

        self.sessions
            .write()
            .await
            .insert(session_id.clone(), active);

        info!(
            session_id = %session_id,
            caller_port = caller_rtp,
            callee_port = callee_rtp,
            "relay session created"
        );

        Ok(CreateSessionResponse {
            session_id,
            caller_port: caller_rtp,
            callee_port: callee_rtp,
        })
    }

    /// Tear down a relay session.
    pub async fn destroy_session(&self, session_id: &str) -> Result<()> {
        let mut sessions = self.sessions.write().await;
        if let Some(active) = sessions.remove(session_id) {
            // Shutdown sender is dropped, which signals the relay task
            self.port_allocator
                .release_pair(active.session.caller_port)
                .await;
            self.port_allocator
                .release_pair(active.session.callee_port)
                .await;
            info!(session_id = session_id, "relay session destroyed");
            Ok(())
        } else {
            Err(anyhow::anyhow!("session not found: {}", session_id))
        }
    }

    /// List all active sessions.
    pub async fn list_sessions(&self) -> Vec<RelaySession> {
        let sessions = self.sessions.read().await;
        sessions.values().map(|a| a.session.clone()).collect()
    }

    /// Get stats for a session.
    pub async fn get_session_stats(&self, session_id: &str) -> Option<SessionStats> {
        let sessions = self.sessions.read().await;
        if let Some(active) = sessions.get(session_id) {
            Some(active.stats.read().await.clone())
        } else {
            None
        }
    }
}

/// The main relay loop: receives UDP packets on both legs and forwards them.
async fn run_relay(
    session: RelaySession,
    bind_ip: &str,
    srtp: Option<(SrtpContext, SrtpContext)>,
    stats: Arc<RwLock<SessionStats>>,
    mut shutdown: watch::Receiver<bool>,
) -> Result<()> {
    let caller_socket = UdpSocket::bind(format!("{}:{}", bind_ip, session.caller_port))
        .await
        .with_context(|| format!("failed to bind caller port {}", session.caller_port))?;

    let callee_socket = UdpSocket::bind(format!("{}:{}", bind_ip, session.callee_port))
        .await
        .with_context(|| format!("failed to bind callee port {}", session.callee_port))?;

    let caller_socket = Arc::new(caller_socket);
    let callee_socket = Arc::new(callee_socket);

    // Track the latest remote address for each side (NAT traversal / symmetric RTP)
    let caller_remote: Arc<RwLock<Option<SocketAddr>>> =
        Arc::new(RwLock::new(session.caller_addr));
    let callee_remote: Arc<RwLock<Option<SocketAddr>>> =
        Arc::new(RwLock::new(session.callee_addr));

    // Caller -> Callee relay
    let cs_caller = caller_socket.clone();
    let cs_callee = callee_socket.clone();
    let cs_callee_remote = callee_remote.clone();
    let cs_caller_remote = caller_remote.clone();
    let stats_c2c = stats.clone();
    let mut shutdown_c2c = shutdown.clone();

    let c2c_handle = tokio::spawn(async move {
        let mut buf = [0u8; 2048];
        loop {
            tokio::select! {
                result = cs_caller.recv_from(&mut buf) => {
                    match result {
                        Ok((n, from_addr)) => {
                            // Update caller's remote address (symmetric RTP)
                            *cs_caller_remote.write().await = Some(from_addr);

                            let data = &buf[..n];
                            let forwarded = if srtp.is_some() {
                                // In a full implementation, decrypt from caller then
                                // re-encrypt for callee. For now, pass through.
                                data.to_vec()
                            } else {
                                data.to_vec()
                            };

                            if let Some(dest) = *cs_callee_remote.read().await {
                                if let Err(e) = cs_callee.send_to(&forwarded, dest).await {
                                    debug!(error = %e, "failed to forward to callee");
                                }
                            }

                            // Update stats
                            let mut s = stats_c2c.write().await;
                            s.packets_caller_to_callee += 1;
                            s.bytes_caller_to_callee += n as u64;
                        }
                        Err(e) => {
                            error!(error = %e, "caller socket recv error");
                            break;
                        }
                    }
                }
                _ = shutdown_c2c.changed() => {
                    break;
                }
            }
        }
    });

    // Callee -> Caller relay
    let cs_caller2 = caller_socket;
    let cs_caller_remote2 = caller_remote.clone();
    let cs_callee_remote2 = callee_remote.clone();
    let stats_c2caller = stats.clone();

    let c2caller_handle = tokio::spawn(async move {
        let mut buf = [0u8; 2048];
        loop {
            tokio::select! {
                result = callee_socket.recv_from(&mut buf) => {
                    match result {
                        Ok((n, from_addr)) => {
                            // Update callee's remote address (symmetric RTP)
                            *cs_callee_remote2.write().await = Some(from_addr);

                            let data = &buf[..n];
                            let forwarded = data.to_vec();

                            if let Some(dest) = *cs_caller_remote2.read().await {
                                if let Err(e) = cs_caller2.send_to(&forwarded, dest).await {
                                    debug!(error = %e, "failed to forward to caller");
                                }
                            }

                            // Update stats
                            let mut s = stats_c2caller.write().await;
                            s.packets_callee_to_caller += 1;
                            s.bytes_callee_to_caller += n as u64;
                        }
                        Err(e) => {
                            error!(error = %e, "callee socket recv error");
                            break;
                        }
                    }
                }
                _ = shutdown.changed() => {
                    break;
                }
            }
        }
    });

    let _ = c2c_handle.await;
    let _ = c2caller_handle.await;

    info!(
        session_id = %session.session_id,
        "relay session ended"
    );
    Ok(())
}

fn hex_decode(hex: &str) -> Result<Vec<u8>> {
    let hex = hex.trim();
    if !hex.len().is_multiple_of(2) {
        return Err(anyhow::anyhow!("odd length hex string"));
    }
    let mut bytes = Vec::with_capacity(hex.len() / 2);
    for i in (0..hex.len()).step_by(2) {
        let byte = u8::from_str_radix(&hex[i..i + 2], 16)
            .with_context(|| format!("invalid hex at position {}", i))?;
        bytes.push(byte);
    }
    Ok(bytes)
}
