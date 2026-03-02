use clap::Parser;
use serde::Deserialize;

#[derive(Parser, Debug, Clone, Deserialize)]
#[command(name = "sip-proxy", about = "New Phone SIP TLS Proxy + Load Balancer")]
pub struct Config {
    /// SIP TLS listen address
    #[arg(long, env = "NP_SIP_LISTEN_ADDR", default_value = "0.0.0.0:5061")]
    pub listen_addr: String,

    /// HTTP health check listen address
    #[arg(long, env = "NP_SIP_HEALTH_ADDR", default_value = "0.0.0.0:8080")]
    pub health_addr: String,

    /// Path to TLS certificate file (PEM)
    #[arg(long, env = "NP_SIP_TLS_CERT")]
    pub tls_cert: Option<String>,

    /// Path to TLS private key file (PEM)
    #[arg(long, env = "NP_SIP_TLS_KEY")]
    pub tls_key: Option<String>,

    /// Comma-separated list of FreeSWITCH backend addresses (host:port)
    #[arg(long, env = "NP_SIP_BACKENDS", default_value = "127.0.0.1:5060")]
    pub backends: String,

    /// Health check interval in seconds
    #[arg(long, env = "NP_SIP_HEALTH_INTERVAL", default_value = "10")]
    pub health_check_interval: u64,

    /// Load balancing strategy: round_robin or least_connections
    #[arg(long, env = "NP_SIP_LB_STRATEGY", default_value = "round_robin")]
    pub lb_strategy: String,
}

impl Config {
    pub fn backend_list(&self) -> Vec<String> {
        self.backends
            .split(',')
            .map(|s| s.trim().to_string())
            .filter(|s| !s.is_empty())
            .collect()
    }
}
