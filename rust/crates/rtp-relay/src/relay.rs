use std::collections::HashMap;
use std::net::SocketAddr;
use std::sync::Arc;

use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use tokio::net::UdpSocket;
use tokio::sync::{watch, Mutex, RwLock};
use tracing::{debug, error, info, warn};
use uuid::Uuid;

use crate::srtp::{self, SrtpContext};
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
    /// Hex-encoded 16-byte master key for the caller leg.
    pub caller_master_key: Option<String>,
    /// Hex-encoded 14-byte master salt for the caller leg.
    pub caller_master_salt: Option<String>,
    /// Hex-encoded 16-byte master key for the callee leg.
    /// If absent, falls back to caller key (symmetric mode).
    pub callee_master_key: Option<String>,
    /// Hex-encoded 14-byte master salt for the callee leg.
    /// If absent, falls back to caller salt (symmetric mode).
    pub callee_master_salt: Option<String>,
    // Legacy fields (still accepted for backward compatibility)
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
        if port % 2 != 0 {
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

        // Build optional SRTP contexts.
        // The relay sits between two endpoints. Each endpoint has its own SRTP keys.
        //   - caller_ctx: used to decrypt from caller / encrypt to caller
        //   - callee_ctx: used to decrypt from callee / encrypt to callee
        //
        // For backward compatibility, if only master_key/master_salt are provided,
        // both legs use the same keys (symmetric mode).
        let srtp_contexts = if request.use_srtp {
            // Resolve caller keys (prefer per-leg, fallback to legacy)
            let caller_key_hex = request
                .caller_master_key
                .as_ref()
                .or(request.master_key.as_ref());
            let caller_salt_hex = request
                .caller_master_salt
                .as_ref()
                .or(request.master_salt.as_ref());

            // Resolve callee keys (prefer per-leg, fallback to caller keys)
            let callee_key_hex = request
                .callee_master_key
                .as_ref()
                .or(caller_key_hex);
            let callee_salt_hex = request
                .callee_master_salt
                .as_ref()
                .or(caller_salt_hex);

            match (caller_key_hex, caller_salt_hex, callee_key_hex, callee_salt_hex) {
                (Some(ck), Some(cs), Some(lk), Some(ls)) => {
                    let caller_key = hex_decode(ck).context("invalid caller master key hex")?;
                    let caller_salt = hex_decode(cs).context("invalid caller master salt hex")?;
                    let callee_key = hex_decode(lk).context("invalid callee master key hex")?;
                    let callee_salt = hex_decode(ls).context("invalid callee master salt hex")?;

                    // Each leg needs two contexts: one for decrypt (incoming) and one for
                    // encrypt (outgoing). Since SrtpContext is stateful (ROC tracking),
                    // we need separate instances for each direction.
                    let caller_inbound = SrtpContext::new(&caller_key, &caller_salt)
                        .context("failed to create caller inbound SRTP")?;
                    let caller_outbound = SrtpContext::new(&caller_key, &caller_salt)
                        .context("failed to create caller outbound SRTP")?;
                    let callee_inbound = SrtpContext::new(&callee_key, &callee_salt)
                        .context("failed to create callee inbound SRTP")?;
                    let callee_outbound = SrtpContext::new(&callee_key, &callee_salt)
                        .context("failed to create callee outbound SRTP")?;

                    Some(SrtpRelayCrypto {
                        caller_inbound: Arc::new(Mutex::new(caller_inbound)),
                        caller_outbound: Arc::new(Mutex::new(caller_outbound)),
                        callee_inbound: Arc::new(Mutex::new(callee_inbound)),
                        callee_outbound: Arc::new(Mutex::new(callee_outbound)),
                    })
                }
                _ => {
                    warn!(
                        session_id = %session_id,
                        "SRTP requested but keys not provided, falling back to plain RTP"
                    );
                    None
                }
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
        let sid = session_id.clone();
        tokio::spawn(async move {
            if let Err(e) = run_relay(
                session_clone,
                &bind_ip,
                srtp_contexts,
                relay_stats,
                shutdown_rx,
            )
            .await
            {
                warn!(session_id = %sid, error = %e, "relay task error");
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
            use_srtp = request.use_srtp,
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

/// Holds the four SRTP contexts needed for a bidirectional relay.
///
/// The relay sits between caller and callee. Each leg can have different SRTP keys
/// (e.g., when the relay terminates SRTP from each endpoint independently).
///
/// Data flow:
///   Caller --[SRTP with caller keys]--> Relay --[SRTP with callee keys]--> Callee
///   Callee --[SRTP with callee keys]--> Relay --[SRTP with caller keys]--> Caller
struct SrtpRelayCrypto {
    /// Decrypt SRTP packets arriving from the caller.
    caller_inbound: Arc<Mutex<SrtpContext>>,
    /// Encrypt RTP packets being sent to the caller.
    caller_outbound: Arc<Mutex<SrtpContext>>,
    /// Decrypt SRTP packets arriving from the callee.
    callee_inbound: Arc<Mutex<SrtpContext>>,
    /// Encrypt RTP packets being sent to the callee.
    callee_outbound: Arc<Mutex<SrtpContext>>,
}

/// The main relay loop: receives UDP packets on both legs and forwards them.
///
/// When SRTP is enabled, the relay:
///   1. Decrypts incoming SRTP with the sender's inbound context
///   2. Re-encrypts with the receiver's outbound context
///
/// This allows each leg to use different SRTP keys, which is the standard
/// behavior for a media relay / SBC.
async fn run_relay(
    session: RelaySession,
    bind_ip: &str,
    crypto: Option<SrtpRelayCrypto>,
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

    // Extract crypto contexts for each direction
    let (caller_in, callee_out, callee_in, caller_out) = match crypto {
        Some(c) => (
            Some(c.caller_inbound),
            Some(c.callee_outbound),
            Some(c.callee_inbound),
            Some(c.caller_outbound),
        ),
        None => (None, None, None, None),
    };

    // ---- Caller -> Callee relay ----
    let cs_caller = caller_socket.clone();
    let cs_callee = callee_socket.clone();
    let cs_callee_remote = callee_remote.clone();
    let cs_caller_remote = caller_remote.clone();
    let stats_c2c = stats.clone();
    let mut shutdown_c2c = shutdown.clone();
    let sid_c2c = session.session_id.clone();

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

                            let forwarded = match (&caller_in, &callee_out) {
                                (Some(decrypt_ctx), Some(encrypt_ctx)) => {
                                    // Determine if this is RTP or RTCP
                                    if srtp::is_rtp_packet(data) {
                                        // Decrypt SRTP from caller
                                        let rtp = match decrypt_ctx.lock().await.unprotect(data) {
                                            Ok(rtp) => rtp,
                                            Err(e) => {
                                                debug!(
                                                    session_id = %sid_c2c,
                                                    error = %e,
                                                    "failed to decrypt SRTP from caller"
                                                );
                                                continue;
                                            }
                                        };
                                        // Re-encrypt for callee
                                        match encrypt_ctx.lock().await.protect(&rtp) {
                                            Ok(srtp) => srtp,
                                            Err(e) => {
                                                debug!(
                                                    session_id = %sid_c2c,
                                                    error = %e,
                                                    "failed to encrypt SRTP for callee"
                                                );
                                                continue;
                                            }
                                        }
                                    } else {
                                        // SRTCP
                                        let rtcp = match decrypt_ctx.lock().await.unprotect_rtcp(data) {
                                            Ok(rtcp) => rtcp,
                                            Err(e) => {
                                                debug!(
                                                    session_id = %sid_c2c,
                                                    error = %e,
                                                    "failed to decrypt SRTCP from caller"
                                                );
                                                continue;
                                            }
                                        };
                                        match encrypt_ctx.lock().await.protect_rtcp(&rtcp) {
                                            Ok(srtcp) => srtcp,
                                            Err(e) => {
                                                debug!(
                                                    session_id = %sid_c2c,
                                                    error = %e,
                                                    "failed to encrypt SRTCP for callee"
                                                );
                                                continue;
                                            }
                                        }
                                    }
                                }
                                _ => {
                                    // Plain RTP pass-through
                                    data.to_vec()
                                }
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

    // ---- Callee -> Caller relay ----
    let cs_caller2 = caller_socket;
    let cs_caller_remote2 = caller_remote.clone();
    let cs_callee_remote2 = callee_remote.clone();
    let stats_c2caller = stats.clone();
    let sid_c2caller = session.session_id.clone();

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

                            let forwarded = match (&callee_in, &caller_out) {
                                (Some(decrypt_ctx), Some(encrypt_ctx)) => {
                                    if srtp::is_rtp_packet(data) {
                                        // Decrypt SRTP from callee
                                        let rtp = match decrypt_ctx.lock().await.unprotect(data) {
                                            Ok(rtp) => rtp,
                                            Err(e) => {
                                                debug!(
                                                    session_id = %sid_c2caller,
                                                    error = %e,
                                                    "failed to decrypt SRTP from callee"
                                                );
                                                continue;
                                            }
                                        };
                                        // Re-encrypt for caller
                                        match encrypt_ctx.lock().await.protect(&rtp) {
                                            Ok(srtp) => srtp,
                                            Err(e) => {
                                                debug!(
                                                    session_id = %sid_c2caller,
                                                    error = %e,
                                                    "failed to encrypt SRTP for caller"
                                                );
                                                continue;
                                            }
                                        }
                                    } else {
                                        // SRTCP
                                        let rtcp = match decrypt_ctx.lock().await.unprotect_rtcp(data) {
                                            Ok(rtcp) => rtcp,
                                            Err(e) => {
                                                debug!(
                                                    session_id = %sid_c2caller,
                                                    error = %e,
                                                    "failed to decrypt SRTCP from callee"
                                                );
                                                continue;
                                            }
                                        };
                                        match encrypt_ctx.lock().await.protect_rtcp(&rtcp) {
                                            Ok(srtcp) => srtcp,
                                            Err(e) => {
                                                debug!(
                                                    session_id = %sid_c2caller,
                                                    error = %e,
                                                    "failed to encrypt SRTCP for caller"
                                                );
                                                continue;
                                            }
                                        }
                                    }
                                }
                                _ => {
                                    // Plain RTP pass-through
                                    data.to_vec()
                                }
                            };

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
    if hex.len() % 2 != 0 {
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
