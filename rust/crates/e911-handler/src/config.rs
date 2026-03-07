use clap::Parser;
use serde::Deserialize;

#[derive(Parser, Debug, Clone, Deserialize)]
#[command(name = "e911-handler", about = "New Phone E911 Emergency Call Handler")]
pub struct Config {
    /// HTTP listen address
    #[arg(long, env = "NP_E911_LISTEN_ADDR", default_value = "0.0.0.0:8085")]
    pub listen_addr: String,

    /// PSAP routing table file (JSON) — used as fallback if API is unreachable
    #[arg(long, env = "NP_E911_PSAP_TABLE", default_value = "./psap_routes.json")]
    pub psap_table: String,

    /// Default PSAP trunk for fallback routing
    #[arg(long, env = "NP_E911_DEFAULT_PSAP_TRUNK", default_value = "default_psap")]
    pub default_psap_trunk: String,

    /// E911 carrier API base URL (e.g., ClearlyIP, Bandwidth, Intrado)
    #[arg(long, env = "NP_E911_CARRIER_API_URL")]
    pub carrier_api_url: Option<String>,

    /// E911 carrier API key
    #[arg(long, env = "NP_E911_CARRIER_API_KEY")]
    pub carrier_api_key: Option<String>,

    /// New Phone control plane API base URL
    #[arg(long, env = "NP_API_URL", default_value = "http://api:8000")]
    pub api_url: String,

    /// Internal API key for service-to-service auth
    #[arg(long, env = "NP_INTERNAL_API_KEY", default_value = "")]
    pub internal_api_key: String,

    /// Redis URL for location caching
    #[arg(long, env = "NP_REDIS_URL", default_value = "redis://127.0.0.1:6379")]
    pub redis_url: String,

    /// Redis cache TTL for locations (seconds)
    #[arg(long, env = "NP_E911_CACHE_TTL", default_value = "300")]
    pub cache_ttl_secs: u64,

    /// FreeSWITCH ESL host
    #[arg(long, env = "NP_E911_ESL_HOST", default_value = "127.0.0.1")]
    pub esl_host: String,

    /// FreeSWITCH ESL port
    #[arg(long, env = "NP_E911_ESL_PORT", default_value = "8021")]
    pub esl_port: u16,

    /// FreeSWITCH ESL password
    #[arg(long, env = "NP_E911_ESL_PASSWORD", default_value = "ClueCon")]
    pub esl_password: String,

    /// SIP domain for FreeSWITCH originate commands
    #[arg(long, env = "NP_SIP_DOMAIN", default_value = "pbx.local")]
    pub sip_domain: String,

    /// PSAP route reload interval in seconds (0 = no auto-reload)
    #[arg(long, env = "NP_E911_ROUTE_RELOAD_SECS", default_value = "300")]
    pub route_reload_secs: u64,
}
