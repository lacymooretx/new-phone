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

    /// API base URL for event persistence
    #[arg(long, env = "NP_API_URL", default_value = "http://api:8000")]
    pub api_url: String,

    /// HTTP health check listen address
    #[arg(long, env = "NP_EVENT_ROUTER_HEALTH_ADDR", default_value = "0.0.0.0:8083")]
    pub health_addr: String,

    /// Reconnection base delay in seconds
    #[arg(long, env = "NP_ESL_RECONNECT_DELAY", default_value = "1")]
    pub reconnect_delay: u64,

    /// Max reconnection delay in seconds
    #[arg(long, env = "NP_ESL_RECONNECT_MAX_DELAY", default_value = "60")]
    pub reconnect_max_delay: u64,

    /// Comma-separated list of event names to publish (empty = all events)
    /// Example: CHANNEL_CREATE,CHANNEL_HANGUP,CHANNEL_ANSWER
    #[arg(long, env = "NP_EVENT_FILTER", default_value = "")]
    pub event_filter: String,
}

impl Config {
    /// Parse the event_filter string into a set of allowed event names.
    /// Returns None if the filter is empty (meaning all events pass).
    pub fn allowed_events(&self) -> Option<Vec<String>> {
        let trimmed = self.event_filter.trim();
        if trimmed.is_empty() {
            None
        } else {
            Some(
                trimmed
                    .split(',')
                    .map(|s| s.trim().to_uppercase())
                    .filter(|s| !s.is_empty())
                    .collect(),
            )
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_allowed_events_empty() {
        let config = Config {
            esl_host: String::new(),
            esl_port: 0,
            esl_password: String::new(),
            redis_url: String::new(),
            api_url: String::new(),
            health_addr: String::new(),
            reconnect_delay: 1,
            reconnect_max_delay: 60,
            event_filter: "".to_string(),
        };
        assert!(config.allowed_events().is_none());
    }

    #[test]
    fn test_allowed_events_parsed() {
        let config = Config {
            esl_host: String::new(),
            esl_port: 0,
            esl_password: String::new(),
            redis_url: String::new(),
            api_url: String::new(),
            health_addr: String::new(),
            reconnect_delay: 1,
            reconnect_max_delay: 60,
            event_filter: "CHANNEL_HANGUP, RECORD_STOP, channel_answer".to_string(),
        };
        let allowed = config.allowed_events().unwrap();
        assert_eq!(allowed, vec!["CHANNEL_HANGUP", "RECORD_STOP", "CHANNEL_ANSWER"]);
    }
}
