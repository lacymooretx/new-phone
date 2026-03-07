#![allow(dead_code)]

mod config;
mod health;
mod load_balancer;
mod proxy;
mod sip_parser;

use std::sync::Arc;

use anyhow::Result;
use axum::routing::get;
use axum::Router;
use clap::Parser;
use tokio::signal;
use tracing::info;

use crate::config::Config;
use crate::load_balancer::{LbStrategy, LoadBalancer};
use crate::proxy::SipProxy;

#[tokio::main]
async fn main() -> Result<()> {
    let config = Config::parse();
    np_shared::init_logging("sip-proxy");

    info!(
        listen_addr = %config.listen_addr,
        health_addr = %config.health_addr,
        backends = %config.backends,
        strategy = %config.lb_strategy,
        "starting sip-proxy"
    );

    let backends = config.backend_list();
    let strategy = LbStrategy::from_str(&config.lb_strategy);
    let lb = Arc::new(LoadBalancer::new(backends, strategy));

    // Shutdown signal
    let (shutdown_tx, shutdown_rx) = tokio::sync::watch::channel(false);

    // Start health check loop
    let lb_health = lb.clone();
    let health_interval = config.health_check_interval;
    tokio::spawn(async move {
        lb_health.run_health_checks(health_interval).await;
    });

    // Start HTTP health endpoint
    let lb_http = lb.clone();
    let health_addr = config.health_addr.clone();
    let health_server = tokio::spawn(async move {
        let app = Router::new()
            .route("/health", get(health::health_check))
            .with_state(lb_http);

        let listener = tokio::net::TcpListener::bind(&health_addr)
            .await
            .expect("failed to bind health endpoint");

        info!(addr = %health_addr, "health endpoint listening");

        axum::serve(listener, app)
            .with_graceful_shutdown(async move {
                let mut rx = shutdown_rx.clone();
                let _ = rx.changed().await;
            })
            .await
            .expect("health server error");
    });

    // Start SIP proxy (reuse shutdown_rx so it stops on the same signal)
    let proxy = SipProxy::new(config, lb);
    let proxy_shutdown_rx = shutdown_tx.subscribe();

    let proxy_handle = tokio::spawn(async move {
        if let Err(e) = proxy.run(proxy_shutdown_rx).await {
            tracing::error!(error = %e, "SIP proxy error");
        }
    });

    // Wait for shutdown signal
    shutdown_signal().await;
    info!("shutdown signal received, stopping services");
    let _ = shutdown_tx.send(true);

    // Wait for tasks to finish
    let _ = tokio::time::timeout(std::time::Duration::from_secs(10), async {
        let _ = health_server.await;
        let _ = proxy_handle.await;
    })
    .await;

    info!("sip-proxy stopped");
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
