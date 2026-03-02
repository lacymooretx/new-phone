use clap::Parser;
use serde::Deserialize;

#[derive(Parser, Debug, Clone, Deserialize)]
#[command(name = "parking-manager", about = "New Phone Call Parking Manager with BLF")]
pub struct Config {
    /// HTTP listen address
    #[arg(long, env = "NP_PARKING_LISTEN_ADDR", default_value = "0.0.0.0:8084")]
    pub listen_addr: String,

    /// FreeSWITCH ESL host
    #[arg(long, env = "NP_PARKING_ESL_HOST", default_value = "127.0.0.1")]
    pub esl_host: String,

    /// FreeSWITCH ESL port
    #[arg(long, env = "NP_PARKING_ESL_PORT", default_value = "8021")]
    pub esl_port: u16,

    /// FreeSWITCH ESL password
    #[arg(long, env = "NP_PARKING_ESL_PASSWORD", default_value = "ClueCon")]
    pub esl_password: String,

    /// Redis URL for state storage
    #[arg(long, env = "NP_PARKING_REDIS_URL", default_value = "redis://127.0.0.1:6379")]
    pub redis_url: String,

    /// Default parking timeout in seconds
    #[arg(long, env = "NP_PARKING_TIMEOUT", default_value = "120")]
    pub default_timeout: u64,

    /// Default number of parking slots per lot
    #[arg(long, env = "NP_PARKING_SLOTS", default_value = "10")]
    pub default_slots: u32,
}
