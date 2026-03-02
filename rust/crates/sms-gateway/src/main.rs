#![allow(dead_code)]

mod config;
mod handlers;
mod providers;
mod rate_limiter;
mod router;

use std::sync::Arc;

use anyhow::Result;
use axum::routing::{get, post};
use axum::Router;
use clap::Parser;
use tokio::signal;
use tracing::info;

use crate::config::Config;
use crate::handlers::AppState;
use crate::providers::clearlyip::ClearlyIpProvider;
use crate::providers::twilio::TwilioProvider;
use crate::rate_limiter::RateLimiter;
use crate::router::SmsRouter;

#[tokio::main]
async fn main() -> Result<()> {
    let config = Config::parse();
    np_shared::init_logging("sms-gateway");

    info!(
        listen_addr = %config.listen_addr,
        default_provider = %config.default_provider,
        rate_limit_min = config.rate_limit_per_min,
        rate_limit_hour = config.rate_limit_per_hour,
        "starting sms-gateway"
    );

    // Initialize providers
    let mut sms_router = SmsRouter::new(config.default_provider.clone());

    let clearlyip = ClearlyIpProvider::new(
        config.clearlyip_api_url.clone(),
        config.clearlyip_api_key.clone(),
    );
    sms_router.add_provider("clearlyip", Arc::new(clearlyip));

    let twilio = TwilioProvider::new(
        config.twilio_account_sid.clone(),
        config.twilio_auth_token.clone(),
    );
    sms_router.add_provider("twilio", Arc::new(twilio));

    // Initialize rate limiter
    let rate_limiter = RateLimiter::new(
        &config.redis_url,
        config.rate_limit_per_min,
        config.rate_limit_per_hour,
    )?;

    let state = Arc::new(AppState {
        router: sms_router,
        rate_limiter,
    });

    let app = Router::new()
        .route("/send", post(handlers::send_sms))
        .route("/webhooks/clearlyip", post(handlers::webhook_clearlyip))
        .route("/webhooks/twilio", post(handlers::webhook_twilio))
        .route("/status/{message_id}", get(handlers::get_status))
        .route("/health", get(handlers::health_check))
        .with_state(state);

    let listener = tokio::net::TcpListener::bind(&config.listen_addr).await?;
    info!(addr = %config.listen_addr, "sms-gateway listening");

    axum::serve(listener, app)
        .with_graceful_shutdown(shutdown_signal())
        .await?;

    info!("sms-gateway stopped");
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
