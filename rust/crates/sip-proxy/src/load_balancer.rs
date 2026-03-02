use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;
use tracing::{debug, info, warn};

use crate::sip_parser::{SipMessage, SipMethod};

#[derive(Debug, Clone, PartialEq)]
pub enum BackendState {
    Healthy,
    Unhealthy,
    Draining,
}

#[derive(Debug, Clone)]
pub struct Backend {
    pub address: String,
    pub state: BackendState,
    pub active_connections: u64,
    pub total_requests: u64,
}

#[derive(Debug, Clone, PartialEq)]
pub enum LbStrategy {
    RoundRobin,
    LeastConnections,
}

impl LbStrategy {
    pub fn from_str(s: &str) -> Self {
        match s.to_lowercase().as_str() {
            "least_connections" | "least-connections" => LbStrategy::LeastConnections,
            _ => LbStrategy::RoundRobin,
        }
    }
}

/// Dialog tracking for SIP sessions (ensures mid-dialog requests go to the same backend).
#[derive(Debug, Clone)]
struct DialogBinding {
    call_id: String,
    backend_addr: String,
}

pub struct LoadBalancer {
    backends: Arc<RwLock<Vec<Backend>>>,
    strategy: LbStrategy,
    round_robin_index: Arc<RwLock<usize>>,
    dialog_bindings: Arc<RwLock<HashMap<String, DialogBinding>>>,
}

impl LoadBalancer {
    pub fn new(addresses: Vec<String>, strategy: LbStrategy) -> Self {
        let backends: Vec<Backend> = addresses
            .into_iter()
            .map(|addr| Backend {
                address: addr,
                state: BackendState::Healthy,
                active_connections: 0,
                total_requests: 0,
            })
            .collect();

        info!(
            count = backends.len(),
            strategy = ?strategy,
            "load balancer initialized"
        );

        LoadBalancer {
            backends: Arc::new(RwLock::new(backends)),
            strategy,
            round_robin_index: Arc::new(RwLock::new(0)),
            dialog_bindings: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    /// Select a backend for the given SIP message.
    /// Mid-dialog requests are routed to the same backend as the initial request.
    pub async fn select_backend(&self, msg: &SipMessage) -> Option<String> {
        // Check for existing dialog binding
        if let Some(call_id) = msg.call_id() {
            let bindings = self.dialog_bindings.read().await;
            if let Some(binding) = bindings.get(call_id) {
                // Check if bound backend is still healthy
                let backends = self.backends.read().await;
                if backends
                    .iter()
                    .any(|b| b.address == binding.backend_addr && b.state == BackendState::Healthy)
                {
                    debug!(
                        call_id = call_id,
                        backend = %binding.backend_addr,
                        "reusing dialog binding"
                    );
                    return Some(binding.backend_addr.clone());
                }
            }
        }

        // Select a new backend based on strategy
        let selected = match self.strategy {
            LbStrategy::RoundRobin => self.select_round_robin().await,
            LbStrategy::LeastConnections => self.select_least_connections().await,
        };

        // Create dialog binding for new INVITE requests
        if let (Some(ref addr), Some(call_id)) = (&selected, msg.call_id()) {
            if msg.method() == Some(&SipMethod::Invite) {
                let mut bindings = self.dialog_bindings.write().await;
                bindings.insert(
                    call_id.to_string(),
                    DialogBinding {
                        call_id: call_id.to_string(),
                        backend_addr: addr.clone(),
                    },
                );
                debug!(call_id = call_id, backend = %addr, "created dialog binding");
            }
        }

        selected
    }

    async fn select_round_robin(&self) -> Option<String> {
        let backends = self.backends.read().await;
        let healthy: Vec<&Backend> = backends
            .iter()
            .filter(|b| b.state == BackendState::Healthy)
            .collect();

        if healthy.is_empty() {
            warn!("no healthy backends available");
            return None;
        }

        let mut idx = self.round_robin_index.write().await;
        let selected = &healthy[*idx % healthy.len()];
        *idx = idx.wrapping_add(1);

        Some(selected.address.clone())
    }

    async fn select_least_connections(&self) -> Option<String> {
        let backends = self.backends.read().await;
        backends
            .iter()
            .filter(|b| b.state == BackendState::Healthy)
            .min_by_key(|b| b.active_connections)
            .map(|b| b.address.clone())
    }

    /// Mark a backend as healthy or unhealthy.
    pub async fn set_backend_state(&self, address: &str, state: BackendState) {
        let mut backends = self.backends.write().await;
        if let Some(backend) = backends.iter_mut().find(|b| b.address == address) {
            let old_state = backend.state.clone();
            backend.state = state.clone();
            if old_state != state {
                info!(
                    backend = address,
                    old_state = ?old_state,
                    new_state = ?state,
                    "backend state changed"
                );
            }
        }
    }

    /// Increment active connections for a backend.
    pub async fn increment_connections(&self, address: &str) {
        let mut backends = self.backends.write().await;
        if let Some(backend) = backends.iter_mut().find(|b| b.address == address) {
            backend.active_connections += 1;
            backend.total_requests += 1;
        }
    }

    /// Decrement active connections for a backend.
    pub async fn decrement_connections(&self, address: &str) {
        let mut backends = self.backends.write().await;
        if let Some(backend) = backends.iter_mut().find(|b| b.address == address) {
            backend.active_connections = backend.active_connections.saturating_sub(1);
        }
    }

    /// Remove dialog binding when a call ends.
    pub async fn remove_dialog(&self, call_id: &str) {
        let mut bindings = self.dialog_bindings.write().await;
        if bindings.remove(call_id).is_some() {
            debug!(call_id = call_id, "removed dialog binding");
        }
    }

    /// Get all backends and their states.
    pub async fn get_backends(&self) -> Vec<Backend> {
        self.backends.read().await.clone()
    }

    /// Send SIP OPTIONS to a backend to check health.
    pub async fn check_backend_health(address: &str) -> bool {
        use tokio::net::TcpStream;
        use tokio::time::{timeout, Duration};

        let options_msg = format!(
            "OPTIONS sip:ping@{} SIP/2.0\r\n\
             Via: SIP/2.0/TCP {};branch=z9hG4bKhealthcheck\r\n\
             From: <sip:healthcheck@proxy>;tag=hc\r\n\
             To: <sip:ping@{}>\r\n\
             Call-ID: healthcheck@proxy\r\n\
             CSeq: 1 OPTIONS\r\n\
             Content-Length: 0\r\n\
             \r\n",
            address, address, address
        );

        let result = timeout(Duration::from_secs(5), async {
            match TcpStream::connect(address).await {
                Ok(stream) => {
                    use tokio::io::AsyncWriteExt;
                    let (_, mut writer) = stream.into_split();
                    writer.write_all(options_msg.as_bytes()).await.is_ok()
                }
                Err(_) => false,
            }
        })
        .await;

        result.unwrap_or(false)
    }

    /// Run periodic health checks on all backends.
    pub async fn run_health_checks(&self, interval_secs: u64) {
        let mut interval = tokio::time::interval(tokio::time::Duration::from_secs(interval_secs));

        loop {
            interval.tick().await;

            let backends = self.get_backends().await;
            for backend in &backends {
                let healthy = Self::check_backend_health(&backend.address).await;
                let new_state = if healthy {
                    BackendState::Healthy
                } else {
                    BackendState::Unhealthy
                };
                self.set_backend_state(&backend.address, new_state).await;
            }
        }
    }
}
