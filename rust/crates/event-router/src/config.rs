use clap::Parser;
use serde::Deserialize;

#[derive(Parser, Debug, Clone, Deserialize)]
#[command(name = "event-router", about = "New Phone FreeSWITCH ESL to Redis Event Router")]
pub struct Config {
    /// FreeSWITCH ESL host
    #[arg(long, env = "NP_ESL_HOST", default_value = "127.0.0.1")]
    pub esl_host: String,

    /// FreeSWITCH ESL port
    #[arg(long, env = "NP_ESL_PORT", default_value = "8021")]
    pub esl_port: u16,

    /// FreeSWITCH ESL password
    #[arg(long, env = "NP_ESL_PASSWORD", default_value = "ClueCon")]
    pub esl_password: String,

    /// Redis URL
    #[arg(long, env = "NP_REDIS_URL", default_value = "redis://127.0.0.1:6379")]
    pub redis_url: String,

    /// HTTP health check listen address
    #[arg(long, env = "NP_EVENT_ROUTER_HEALTH_ADDR", default_value = "0.0.0.0:8083")]
    pub health_addr: String,

    /// Reconnection base delay in seconds
    #[arg(long, env = "NP_ESL_RECONNECT_DELAY", default_value = "1")]
    pub reconnect_delay: u64,

    /// Max reconnection delay in seconds
    #[arg(long, env = "NP_ESL_RECONNECT_MAX_DELAY", default_value = "60")]
    pub reconnect_max_delay: u64,
}
