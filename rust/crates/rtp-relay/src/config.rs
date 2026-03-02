use clap::Parser;
use serde::Deserialize;

#[derive(Parser, Debug, Clone, Deserialize)]
#[command(name = "rtp-relay", about = "New Phone SRTP Media Relay/Mixer")]
pub struct Config {
    /// HTTP API listen address for session management
    #[arg(long, env = "NP_RTP_API_ADDR", default_value = "0.0.0.0:8081")]
    pub api_addr: String,

    /// Start of RTP port range
    #[arg(long, env = "NP_RTP_PORT_MIN", default_value = "10000")]
    pub port_min: u16,

    /// End of RTP port range
    #[arg(long, env = "NP_RTP_PORT_MAX", default_value = "20000")]
    pub port_max: u16,

    /// External/public IP address for SDP
    #[arg(long, env = "NP_RTP_EXTERNAL_IP", default_value = "0.0.0.0")]
    pub external_ip: String,
}
