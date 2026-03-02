#![allow(dead_code)]

mod config;
mod handlers;
mod pidf_lo;
mod routing;

use std::sync::Arc;

use anyhow::Result;
use axum::routing::{delete, get, post};
use axum::Router;
use clap::Parser;
use tokio::signal;
use tracing::info;

use crate::config::Config;
use crate::handlers::AppState;
use crate::routing::{EmergencyRouter, LocationStore};

#[tokio::main]
async fn main() -> Result<()> {
    let config = Config::parse();
    np_shared::init_logging("e911-handler");

    info!(
        listen_addr = %config.listen_addr,
        psap_table = %config.psap_table,
        "starting e911-handler"
    );

    let router = EmergencyRouter::new(config.default_psap_trunk.clone());
    router.load_routes(&config.psap_table).await?;

    let locations = LocationStore::new();

    let state = Arc::new(AppState { router, locations });

    let app = Router::new()
        .route("/locations", post(handlers::create_location))
        .route("/locations", get(handlers::list_locations))
        .route("/locations/{extension}", get(handlers::get_location))
        .route("/locations/{extension}", delete(handlers::delete_location))
        .route("/emergency-call", post(handlers::handle_emergency_call))
        .route("/pidf-lo/{extension}", get(handlers::get_pidf_lo))
        .route("/health", get(handlers::health_check))
        .with_state(state);

    let listener = tokio::net::TcpListener::bind(&config.listen_addr).await?;
    info!(addr = %config.listen_addr, "e911-handler listening");

    axum::serve(listener, app)
        .with_graceful_shutdown(shutdown_signal())
        .await?;

    info!("e911-handler stopped");
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
