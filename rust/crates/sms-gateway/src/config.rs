use clap::Parser;
use serde::Deserialize;

#[derive(Parser, Debug, Clone, Deserialize)]
#[command(name = "sms-gateway", about = "New Phone High-Throughput SMS Gateway")]
pub struct Config {
    /// HTTP listen address
    #[arg(long, env = "NP_SMS_LISTEN_ADDR", default_value = "0.0.0.0:8086")]
    pub listen_addr: String,

    /// Redis URL for rate limiting and message tracking
    #[arg(long, env = "NP_SMS_REDIS_URL", default_value = "redis://127.0.0.1:6379")]
    pub redis_url: String,

    /// ClearlyIP API base URL
    #[arg(long, env = "NP_SMS_CLEARLYIP_API_URL", default_value = "https://api.clearlyip.com")]
    pub clearlyip_api_url: String,

    /// ClearlyIP API key
    #[arg(long, env = "NP_SMS_CLEARLYIP_API_KEY", default_value = "")]
    pub clearlyip_api_key: String,

    /// Twilio Account SID
    #[arg(long, env = "NP_SMS_TWILIO_ACCOUNT_SID", default_value = "")]
    pub twilio_account_sid: String,

    /// Twilio Auth Token
    #[arg(long, env = "NP_SMS_TWILIO_AUTH_TOKEN", default_value = "")]
    pub twilio_auth_token: String,

    /// Default provider: clearlyip or twilio
    #[arg(long, env = "NP_SMS_DEFAULT_PROVIDER", default_value = "clearlyip")]
    pub default_provider: String,

    /// Rate limit: max messages per DID per minute
    #[arg(long, env = "NP_SMS_RATE_LIMIT_PER_MIN", default_value = "60")]
    pub rate_limit_per_min: u32,

    /// Rate limit: max messages per DID per hour
    #[arg(long, env = "NP_SMS_RATE_LIMIT_PER_HOUR", default_value = "1000")]
    pub rate_limit_per_hour: u32,

    /// Webhook base URL for inbound message callbacks
    #[arg(long, env = "NP_SMS_WEBHOOK_BASE_URL", default_value = "http://localhost:8086")]
    pub webhook_base_url: String,
}
