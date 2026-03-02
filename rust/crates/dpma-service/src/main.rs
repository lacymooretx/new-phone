#![allow(dead_code)]

mod config;
mod handlers;
mod provisioning;
mod templates;

use std::sync::Arc;

use anyhow::Result;
use axum::routing::{get, post};
use axum::Router;
use clap::Parser;
use tokio::signal;
use tracing::info;

use crate::config::Config;
use crate::handlers::AppState;
use crate::provisioning::ProvisioningStore;
use crate::templates::PhoneTemplateEngine;

#[tokio::main]
async fn main() -> Result<()> {
    let config = Config::parse();
    np_shared::init_logging("dpma-service");

    info!(
        listen_addr = %config.listen_addr,
        template_dir = %config.template_dir,
        "starting dpma-service"
    );

    let store = ProvisioningStore::new();
    let template_engine = PhoneTemplateEngine::new(&config.template_dir)?;

    let state = Arc::new(AppState {
        store,
        template_engine,
    });

    let app = Router::new()
        .route("/config/{mac}", get(handlers::get_config))
        .route("/firmware/{model}", get(handlers::get_firmware))
        .route("/phones/register", post(handlers::register_phone))
        .route("/phones", get(handlers::list_phones))
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
