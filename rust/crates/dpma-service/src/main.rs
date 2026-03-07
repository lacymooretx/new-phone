#![allow(dead_code)]

mod config;
mod handlers;
mod provisioning;

use std::path::PathBuf;
use std::sync::Arc;

use anyhow::Result;
use axum::routing::{get, post};
use axum::Router;
use clap::Parser;
use redis::AsyncCommands;
use tokio::signal;
use tokio::sync::RwLock;
use tracing::{error, info, warn};

use crate::config::Config;
use crate::handlers::AppState;
use crate::provisioning::{DeviceStore, FirmwareManifest};

#[tokio::main]
async fn main() -> Result<()> {
    let config = Config::parse();
    np_shared::init_logging("dpma-service");

    info!(
        listen_addr = %config.listen_addr,
        firmware_dir = %config.firmware_dir,
        api_url = %config.api_url,
        redis_url = %config.redis_url,
        offline_threshold = config.offline_threshold_secs,
        "starting dpma-service"
    );

    // Load firmware manifest
    let manifest = FirmwareManifest::load_from_file(&config.firmware_manifest);
    let firmware_map = manifest.by_model();
    info!(models = firmware_map.len(), "firmware manifest loaded");

    // Initialize device store (API + Redis backed)
    let store =
        DeviceStore::new(&config.api_url, &config.redis_url, config.cache_ttl_secs).await?;

    let state = Arc::new(AppState {
        store: RwLock::new(store),
        firmware_map,
        firmware_dir: PathBuf::from(&config.firmware_dir),
        offline_threshold_secs: config.offline_threshold_secs,
    });

    // Start background phone monitoring task
    let monitor_state = state.clone();
    let monitor_redis_url = config.redis_url.clone();
    let monitor_interval = config.monitor_interval_secs;
    let offline_threshold = config.offline_threshold_secs;
    tokio::spawn(async move {
        phone_monitor_loop(
            monitor_state,
            &monitor_redis_url,
            monitor_interval,
            offline_threshold,
        )
        .await;
    });

    let app = Router::new()
        .route("/phones/checkin", post(handlers::phone_checkin))
        .route("/phones/by-mac/{mac}", get(handlers::get_phone_by_mac))
        .route("/firmware/info/{model}", get(handlers::get_firmware_info))
        .route(
            "/firmware/download/{filename}",
            get(handlers::download_firmware),
        )
        .route("/health", get(handlers::health_check))
        .with_state(state);

    let listener = tokio::net::TcpListener::bind(&config.listen_addr).await?;
    info!(addr = %config.listen_addr, "dpma-service listening");

    axum::serve(listener, app)
        .with_graceful_shutdown(shutdown_signal())
        .await?;

    info!("dpma-service stopped");
    Ok(())
}

/// Background task that monitors phone last-seen timestamps and publishes
/// offline alerts to Redis pub/sub.
async fn phone_monitor_loop(
    state: Arc<AppState>,
    redis_url: &str,
    interval_secs: u64,
    offline_threshold_secs: u64,
) {
    // Create a separate Redis connection for publishing alerts
    let redis_client = match redis::Client::open(redis_url) {
        Ok(c) => c,
        Err(e) => {
            error!(error = %e, "phone monitor: failed to create Redis client");
            return;
        }
    };

    let mut redis_conn = match redis_client.get_multiplexed_async_connection().await {
        Ok(c) => c,
        Err(e) => {
            error!(error = %e, "phone monitor: failed to connect to Redis");
            return;
        }
    };

    info!(
        interval = interval_secs,
        threshold = offline_threshold_secs,
        "phone monitor started"
    );

    let mut interval = tokio::time::interval(tokio::time::Duration::from_secs(interval_secs));

    loop {
        interval.tick().await;

        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs();

        // Get all last-seen data
        let mut store = state.store.write().await;
        let all_last_seen = match store.get_all_last_seen().await {
            Ok(data) => data,
            Err(e) => {
                warn!(error = %e, "phone monitor: failed to get last-seen data");
                continue;
            }
        };
        drop(store); // Release lock early

        for (mac, last_seen) in &all_last_seen {
            let elapsed = now.saturating_sub(*last_seen);
            if elapsed > offline_threshold_secs {
                let alert = serde_json::json!({
                    "type": "phone_offline",
                    "mac_address": mac,
                    "last_seen_epoch": last_seen,
                    "elapsed_secs": elapsed,
                    "threshold_secs": offline_threshold_secs,
                    "timestamp_epoch": now,
                });

                let alert_str = serde_json::to_string(&alert).unwrap_or_default();
                let result: std::result::Result<i64, _> = redis_conn
                    .publish("np:phone:alerts", &alert_str)
                    .await;

                match result {
                    Ok(_) => {
                        warn!(
                            mac = %mac,
                            elapsed = elapsed,
                            "phone offline alert published"
                        );
                    }
                    Err(e) => {
                        error!(
                            mac = %mac,
                            error = %e,
                            "failed to publish phone offline alert"
                        );
                        // Try to reconnect
                        if let Ok(new_conn) =
                            redis_client.get_multiplexed_async_connection().await
                        {
                            redis_conn = new_conn;
                        }
                    }
                }
            }
        }
    }
}

async fn shutdown_signal() {
    let ctrl_c = async {
        signal::ctrl_c()
            .await
            .expect("failed to install Ctrl+C handler");
    };

    #[cfg(unix)]
    let terminate = async {
        signal::unix::signal(signal::unix::SignalKind::terminate())
            .expect("failed to install SIGTERM handler")
            .recv()
            .await;
    };

    #[cfg(not(unix))]
    let terminate = std::future::pending::<()>();

    tokio::select! {
        _ = ctrl_c => {},
        _ = terminate => {},
    }
}
