#![allow(dead_code)]

mod config;
mod esl_client;
mod parser;
mod publisher;

use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::Arc;

use anyhow::Result;
use axum::routing::get;
use axum::Json;
use axum::Router;
use clap::Parser;
use tokio::signal;
use tokio::sync::RwLock;
use tracing::{error, info, warn};

use crate::config::Config;
use crate::esl_client::{connect_with_retry, EslClient};
use crate::publisher::EventPublisher;

/// Shared metrics for health reporting.
struct Metrics {
    /// Whether ESL is currently connected.
    esl_connected: AtomicBool,
    /// Total number of events processed (parsed successfully).
    events_processed: AtomicU64,
    /// Timestamp (unix millis) of last event received.
    last_event_time: AtomicU64,
    /// Number of reconnect attempts since startup.
    reconnect_count: AtomicU64,
    /// Last event name received (for debugging).
    last_event_name: RwLock<String>,
}

impl Metrics {
    fn new() -> Self {
        Metrics {
            esl_connected: AtomicBool::new(false),
            events_processed: AtomicU64::new(0),
            last_event_time: AtomicU64::new(0),
            reconnect_count: AtomicU64::new(0),
            last_event_name: RwLock::new(String::new()),
        }
    }
}

#[tokio::main]
async fn main() -> Result<()> {
    let config = Config::parse();
    np_shared::init_logging("event-router");

    info!(
        esl_host = %config.esl_host,
        esl_port = config.esl_port,
        redis_url = %config.redis_url,
        api_url = %config.api_url,
        health_addr = %config.health_addr,
        "starting event-router"
    );

    let metrics = Arc::new(Metrics::new());

    // Start health endpoint
    let health_metrics = metrics.clone();
    let health_addr = config.health_addr.clone();
    tokio::spawn(async move {
        let app = Router::new().route(
            "/health",
            get(move || {
                let m = health_metrics.clone();
                async move {
                    let is_connected = m.esl_connected.load(Ordering::Relaxed);
                    let events_processed = m.events_processed.load(Ordering::Relaxed);
                    let last_event_time = m.last_event_time.load(Ordering::Relaxed);
                    let reconnect_count = m.reconnect_count.load(Ordering::Relaxed);
                    let last_event_name = m.last_event_name.read().await.clone();

                    let status = if is_connected { "healthy" } else { "degraded" };

                    Json(serde_json::json!({
                        "status": status,
                        "service": "event-router",
                        "esl_connected": is_connected,
                        "events_processed": events_processed,
                        "last_event_time_ms": last_event_time,
                        "last_event_name": last_event_name,
                        "reconnect_count": reconnect_count,
                    }))
                }
            }),
        );

        let listener = tokio::net::TcpListener::bind(&health_addr)
            .await
            .expect("failed to bind health endpoint");
        info!(addr = %health_addr, "health endpoint listening");
        axum::serve(listener, app).await.expect("health server error");
    });

    // Parse event filter
    let event_filter = config.allowed_events();

    // Main event routing loop with reconnection
    let esl_client = EslClient::new(
        config.esl_host.clone(),
        config.esl_port,
        config.esl_password.clone(),
    );

    let mut publisher =
        EventPublisher::new(&config.redis_url, &config.api_url, event_filter).await?;

    // Outer loop: reconnect on disconnect
    loop {
        let mut conn = connect_with_retry(
            &esl_client,
            config.reconnect_delay,
            config.reconnect_max_delay,
        )
        .await;

        metrics.esl_connected.store(true, Ordering::Relaxed);

        // Inner loop: read and process events
        loop {
            match conn.next_event().await {
                Ok(event) => {
                    if let Some(parsed) = parser::parse_event(&event) {
                        // Update metrics
                        metrics.events_processed.fetch_add(1, Ordering::Relaxed);
                        let now = std::time::SystemTime::now()
                            .duration_since(std::time::UNIX_EPOCH)
                            .unwrap_or_default()
                            .as_millis() as u64;
                        metrics.last_event_time.store(now, Ordering::Relaxed);
                        {
                            let mut name = metrics.last_event_name.write().await;
                            *name = parsed.event_name.clone();
                        }

                        publisher::publish_loop(&mut publisher, &parsed).await;
                    }
                }
                Err(e) => {
                    error!(error = %e, "ESL connection error");
                    metrics.esl_connected.store(false, Ordering::Relaxed);
                    break; // Break to outer loop for reconnection
                }
            }
        }

        metrics.reconnect_count.fetch_add(1, Ordering::Relaxed);
        warn!("ESL disconnected, will reconnect");
    }
}

async fn _shutdown_signal() {
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
