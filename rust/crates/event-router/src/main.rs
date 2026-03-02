#![allow(dead_code)]

mod config;
mod esl_client;
mod parser;
mod publisher;

use std::sync::Arc;
use std::sync::atomic::{AtomicBool, Ordering};

use anyhow::Result;
use axum::routing::get;
use axum::Json;
use axum::Router;
use clap::Parser;
use tokio::signal;
use tracing::{error, info, warn};

use crate::config::Config;
use crate::esl_client::{connect_with_retry, EslClient};
use crate::publisher::EventPublisher;

#[tokio::main]
async fn main() -> Result<()> {
    let config = Config::parse();
    np_shared::init_logging("event-router");

    info!(
        esl_host = %config.esl_host,
        esl_port = config.esl_port,
        redis_url = %config.redis_url,
        health_addr = %config.health_addr,
        "starting event-router"
    );

    let connected = Arc::new(AtomicBool::new(false));

    // Start health endpoint
    let health_connected = connected.clone();
    let health_addr = config.health_addr.clone();
    tokio::spawn(async move {
        let app = Router::new().route(
            "/health",
            get(move || {
                let c = health_connected.clone();
                async move {
                    let is_connected = c.load(Ordering::Relaxed);
                    Json(serde_json::json!({
                        "status": if is_connected { "healthy" } else { "degraded" },
                        "service": "event-router",
                        "esl_connected": is_connected,
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

    // Main event routing loop with reconnection
    let esl_client = EslClient::new(
        config.esl_host.clone(),
        config.esl_port,
        config.esl_password.clone(),
    );

    let mut publisher = EventPublisher::new(&config.redis_url).await?;

    // Outer loop: reconnect on disconnect
    loop {
        let mut conn = connect_with_retry(
            &esl_client,
            config.reconnect_delay,
            config.reconnect_max_delay,
        )
        .await;

        connected.store(true, Ordering::Relaxed);

        // Inner loop: read and process events
        loop {
            match conn.next_event().await {
                Ok(event) => {
                    if let Some(parsed) = parser::parse_event(&event) {
                        publisher::publish_loop(&mut publisher, &parsed).await;
                    }
                }
                Err(e) => {
                    error!(error = %e, "ESL connection error");
                    connected.store(false, Ordering::Relaxed);
                    break; // Break to outer loop for reconnection
                }
            }
        }

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
