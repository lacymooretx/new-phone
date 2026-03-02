use clap::Parser;
use serde::Deserialize;

#[derive(Parser, Debug, Clone, Deserialize)]
#[command(name = "e911-handler", about = "New Phone E911 Emergency Call Handler")]
pub struct Config {
    /// HTTP listen address
    #[arg(long, env = "NP_E911_LISTEN_ADDR", default_value = "0.0.0.0:8085")]
    pub listen_addr: String,

    /// PSAP routing table file (JSON)
    #[arg(long, env = "NP_E911_PSAP_TABLE", default_value = "./psap_routes.json")]
    pub psap_table: String,

    /// Default PSAP trunk for fallback routing
    #[arg(long, env = "NP_E911_DEFAULT_PSAP_TRUNK", default_value = "default_psap")]
    pub default_psap_trunk: String,

    /// E911 carrier API base URL
    #[arg(long, env = "NP_E911_CARRIER_API_URL")]
    pub carrier_api_url: Option<String>,

    /// E911 carrier API key
    #[arg(long, env = "NP_E911_CARRIER_API_KEY")]
    pub carrier_api_key: Option<String>,
}
