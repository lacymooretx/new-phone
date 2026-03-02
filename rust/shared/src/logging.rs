use tracing_subscriber::{fmt, EnvFilter};

/// Initialize the tracing subscriber.
///
/// - In production (`NP_ENV=production`), outputs JSON-formatted logs.
/// - Otherwise, outputs human-readable pretty-printed logs.
///
/// The log level can be controlled via `NP_LOG_LEVEL` (defaults to `info`)
/// or the standard `RUST_LOG` env var.
pub fn init_logging(service_name: &str) {
    let env = std::env::var("NP_ENV").unwrap_or_default();
    let log_level = std::env::var("NP_LOG_LEVEL").unwrap_or_else(|_| "info".to_string());

    let filter = EnvFilter::try_from_default_env()
        .unwrap_or_else(|_| EnvFilter::new(&log_level));

    if env == "production" {
        fmt()
            .json()
            .with_env_filter(filter)
            .with_target(true)
            .with_thread_ids(true)
            .with_file(true)
            .with_line_number(true)
            .init();
    } else {
        fmt()
            .pretty()
            .with_env_filter(filter)
            .with_target(true)
            .with_thread_ids(false)
            .init();
    }

    tracing::info!(service = service_name, "logging initialized");
}
