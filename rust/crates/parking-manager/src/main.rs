#![allow(dead_code)]

mod blf;
mod config;
mod handlers;
mod parking;

use std::sync::Arc;

use anyhow::Result;
use axum::routing::{delete, get, post};
use axum::Router;
use clap::Parser;
use tokio::signal;
use tracing::info;

use crate::blf::BlfManager;
use crate::config::Config;
use crate::handlers::AppState;
use crate::parking::ParkingManager;

#[tokio::main]
async fn main() -> Result<()> {
    let config = Config::parse();
    np_shared::init_logging("parking-manager");

    info!(
        listen_addr = %config.listen_addr,
        timeout = config.default_timeout,
        slots = config.default_slots,
        "starting parking-manager"
    );

    let parking = ParkingManager::new(
        &config.redis_url,
        &config.esl_host,
        config.esl_port,
        &config.esl_password,
        config.default_timeout,
        config.default_slots,
    )?;

    let blf = BlfManager::new();

    let state = Arc::new(AppState { parking, blf });

    // Spawn timeout checker background task
    let timeout_state = state.clone();
    tokio::spawn(async move {
        let mut interval = tokio::time::interval(tokio::time::Duration::from_secs(5));
        loop {
            interval.tick().await;
            timeout_state.parking.check_timeouts().await;
        }
    });

    let app = Router::new()
        .route("/lots/{lot_id}/park", post(handlers::park_call))
        .route(
            "/lots/{lot_id}/slots/{slot}/retrieve",
            post(handlers::retrieve_call),
        )
        .route("/lots/{lot_id}/slots", get(handlers::list_slots))
        .route("/lots", get(handlers::list_lots))
        .route(
            "/lots/{lot_id}/slots/{slot}",
            delete(handlers::force_release),
        )
        .route("/health", get(handlers::health_check))
        .with_state(state);

    let listener = tokio::net::TcpListener::bind(&config.listen_addr).await?;
    info!(addr = %config.listen_addr, "parking-manager listening");

    axum::serve(listener, app)
        .with_graceful_shutdown(shutdown_signal())
        .await?;

    info!("parking-manager stopped");
    Ok(())
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
