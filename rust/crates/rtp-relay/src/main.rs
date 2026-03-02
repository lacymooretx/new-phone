#![allow(dead_code)]

mod config;
mod mixer;
mod relay;
mod srtp;
mod stats;

use std::sync::Arc;

use anyhow::Result;
use axum::extract::{Path, State};
use axum::http::StatusCode;
use axum::response::IntoResponse;
use axum::routing::{delete, get, post};
use axum::{Json, Router};
use clap::Parser;
use tokio::signal;
use tracing::info;

use crate::config::Config;
use crate::relay::{CreateSessionRequest, RelayManager};

struct AppState {
    relay_manager: RelayManager,
}

#[tokio::main]
async fn main() -> Result<()> {
    let config = Config::parse();
    np_shared::init_logging("rtp-relay");

    info!(
        api_addr = %config.api_addr,
        port_range = %format!("{}-{}", config.port_min, config.port_max),
        "starting rtp-relay"
    );

    let relay_manager = RelayManager::new(
        config.port_min,
        config.port_max,
        config.external_ip.clone(),
    );

    let state = Arc::new(AppState { relay_manager });

    let app = Router::new()
        .route("/sessions", post(create_session))
        .route("/sessions", get(list_sessions))
        .route("/sessions/{session_id}", delete(destroy_session))
        .route("/sessions/{session_id}/stats", get(session_stats))
        .route("/health", get(health_check))
        .with_state(state);

    let listener = tokio::net::TcpListener::bind(&config.api_addr).await?;
    info!(addr = %config.api_addr, "rtp-relay API listening");

    axum::serve(listener, app)
        .with_graceful_shutdown(shutdown_signal())
        .await?;

    info!("rtp-relay stopped");
    Ok(())
}

async fn create_session(
    State(state): State<Arc<AppState>>,
    Json(request): Json<CreateSessionRequest>,
) -> impl IntoResponse {
    match state.relay_manager.create_session(request).await {
        Ok(response) => (StatusCode::CREATED, Json(serde_json::to_value(response).unwrap())),
        Err(e) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(serde_json::json!({"error": e.to_string()})),
        ),
    }
}

async fn list_sessions(State(state): State<Arc<AppState>>) -> impl IntoResponse {
    let sessions = state.relay_manager.list_sessions().await;
    Json(serde_json::to_value(sessions).unwrap())
}

async fn destroy_session(
    State(state): State<Arc<AppState>>,
    Path(session_id): Path<String>,
) -> impl IntoResponse {
    match state.relay_manager.destroy_session(&session_id).await {
        Ok(()) => (
            StatusCode::OK,
            Json(serde_json::json!({"status": "destroyed"})),
        ),
        Err(e) => (
            StatusCode::NOT_FOUND,
            Json(serde_json::json!({"error": e.to_string()})),
        ),
    }
}

async fn session_stats(
    State(state): State<Arc<AppState>>,
    Path(session_id): Path<String>,
) -> impl IntoResponse {
    match state.relay_manager.get_session_stats(&session_id).await {
        Some(stats) => (StatusCode::OK, Json(serde_json::to_value(stats).unwrap())),
        None => (
            StatusCode::NOT_FOUND,
            Json(serde_json::json!({"error": "session not found"})),
        ),
    }
}

async fn health_check() -> impl IntoResponse {
    Json(serde_json::json!({
        "status": "healthy",
        "service": "rtp-relay"
    }))
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
