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
use crate::routing::{CarrierApiClient, EmergencyRouter, LocationStore};

#[tokio::main]
async fn main() -> Result<()> {
    let config = Config::parse();
    np_shared::init_logging("e911-handler");

    info!(
        listen_addr = %config.listen_addr,
        psap_table = %config.psap_table,
        api_url = %config.api_url,
        redis_url = %config.redis_url,
        "starting e911-handler"
    );

    // HTTP client for API calls
    let http_client = reqwest::Client::new();

    // Emergency router — load PSAP routes from API first, file fallback
    let router = EmergencyRouter::new(config.default_psap_trunk.clone());
    router
        .load_routes_from_api_or_file(
            &http_client,
            &config.api_url,
            &config.internal_api_key,
            &config.psap_table,
        )
        .await?;

    // Location store — API-backed with Redis cache
    let locations = LocationStore::new(
        config.api_url.clone(),
        config.internal_api_key.clone(),
        &config.redis_url,
        config.cache_ttl_secs,
    )?;

    // Carrier API client (optional — only if configured)
    let carrier = match (&config.carrier_api_url, &config.carrier_api_key) {
        (Some(url), Some(key)) if !url.is_empty() && !key.is_empty() => {
            info!(carrier_url = %url, "carrier E911 API configured");
            Some(CarrierApiClient::new(url.clone(), key.clone()))
        }
        _ => {
            info!("no carrier E911 API configured, using local PSAP routing only");
            None
        }
    };

    let state = Arc::new(AppState {
        router,
        locations,
        carrier,
        http_client: http_client.clone(),
        api_url: config.api_url.clone(),
        internal_api_key: config.internal_api_key.clone(),
        esl_host: config.esl_host.clone(),
        esl_port: config.esl_port,
        esl_password: config.esl_password.clone(),
        sip_domain: config.sip_domain.clone(),
        listen_addr: config.listen_addr.clone(),
    });

    // Spawn PSAP route reload background task
    if config.route_reload_secs > 0 {
        let reload_state = state.clone();
        let reload_client = http_client.clone();
        let reload_api_url = config.api_url.clone();
        let reload_api_key = config.internal_api_key.clone();
        let reload_file = config.psap_table.clone();
        let reload_interval = config.route_reload_secs;

        tokio::spawn(async move {
            let mut interval =
                tokio::time::interval(tokio::time::Duration::from_secs(reload_interval));
            // Skip the first immediate tick (routes were just loaded)
            interval.tick().await;

            loop {
                interval.tick().await;
                info!("reloading PSAP routes");
                if let Err(e) = reload_state
                    .router
                    .load_routes_from_api_or_file(
                        &reload_client,
                        &reload_api_url,
                        &reload_api_key,
                        &reload_file,
                    )
                    .await
                {
                    tracing::error!(error = %e, "failed to reload PSAP routes");
                }
            }
        });
    }

    let app = Router::new()
        .route("/locations", post(handlers::create_location))
        .route("/locations", get(handlers::list_locations))
        .route("/locations/{extension}", get(handlers::get_location))
        .route(
            "/locations/{extension}",
            delete(handlers::delete_location),
        )
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
