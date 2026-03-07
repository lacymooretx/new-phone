use clap::Parser;
use serde::Deserialize;

#[derive(Parser, Debug, Clone, Deserialize)]
#[command(name = "dpma-service", about = "New Phone DPMA Phone Management Service")]
pub struct Config {
    /// HTTP listen address
    #[arg(long, env = "NP_DPMA_LISTEN_ADDR", default_value = "0.0.0.0:8082")]
    pub listen_addr: String,

    /// Firmware directory path (serves firmware files for phone updates)
    #[arg(long, env = "NP_DPMA_FIRMWARE_DIR", default_value = "./firmware")]
    pub firmware_dir: String,

    /// Firmware manifest file (JSON file with model->version->filename mappings)
    #[arg(long, env = "NP_DPMA_FIRMWARE_MANIFEST", default_value = "./firmware/manifest.json")]
    pub firmware_manifest: String,

    /// Redis URL for caching and pub/sub
    #[arg(long, env = "NP_REDIS_URL", default_value = "redis://127.0.0.1:6379")]
    pub redis_url: String,

    /// API base URL
    #[arg(long, env = "NP_API_URL", default_value = "http://api:8000")]
    pub api_url: String,

    /// Phone offline threshold in seconds (alert if no check-in within this window)
    #[arg(long, env = "NP_DPMA_OFFLINE_THRESHOLD", default_value = "300")]
    pub offline_threshold_secs: u64,

    /// Redis cache TTL for device lookups in seconds
    #[arg(long, env = "NP_DPMA_CACHE_TTL", default_value = "60")]
    pub cache_ttl_secs: u64,

    /// Phone monitor check interval in seconds
    #[arg(long, env = "NP_DPMA_MONITOR_INTERVAL", default_value = "60")]
    pub monitor_interval_secs: u64,
}
