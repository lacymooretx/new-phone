use clap::Parser;
use serde::Deserialize;

#[derive(Parser, Debug, Clone, Deserialize)]
#[command(name = "dpma-service", about = "New Phone DPMA Provisioning Service for Sangoma Phones")]
pub struct Config {
    /// HTTP listen address
    #[arg(long, env = "NP_DPMA_LISTEN_ADDR", default_value = "0.0.0.0:8082")]
    pub listen_addr: String,

    /// Template directory path
    #[arg(long, env = "NP_DPMA_TEMPLATE_DIR", default_value = "./templates")]
    pub template_dir: String,

    /// Firmware directory path
    #[arg(long, env = "NP_DPMA_FIRMWARE_DIR", default_value = "./firmware")]
    pub firmware_dir: String,

    /// FreeSWITCH server address for SIP registration
    #[arg(long, env = "NP_DPMA_FS_ADDR", default_value = "127.0.0.1")]
    pub freeswitch_addr: String,

    /// SIP domain for phone registration
    #[arg(long, env = "NP_DPMA_SIP_DOMAIN", default_value = "pbx.local")]
    pub sip_domain: String,
}
