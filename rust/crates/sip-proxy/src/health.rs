use std::sync::Arc;

use axum::extract::State;
use axum::http::StatusCode;
use axum::response::IntoResponse;
use axum::Json;
use serde::Serialize;

use crate::load_balancer::{BackendState, LoadBalancer};

#[derive(Serialize)]
pub struct ProxyHealthResponse {
    pub status: String,
    pub service: String,
    pub backends: Vec<BackendHealth>,
}

#[derive(Serialize)]
pub struct BackendHealth {
    pub address: String,
    pub state: String,
    pub active_connections: u64,
}

pub async fn health_check(State(lb): State<Arc<LoadBalancer>>) -> impl IntoResponse {
    let backends = lb.get_backends().await;
    let healthy_count = backends
        .iter()
        .filter(|b| b.state == BackendState::Healthy)
        .count();

    let backend_health: Vec<BackendHealth> = backends
        .iter()
        .map(|b| BackendHealth {
            address: b.address.clone(),
            state: format!("{:?}", b.state),
            active_connections: b.active_connections,
        })
        .collect();

    let status = if healthy_count > 0 {
        "healthy"
    } else {
        "unhealthy"
    };

    let code = if healthy_count > 0 {
        StatusCode::OK
    } else {
        StatusCode::SERVICE_UNAVAILABLE
    };

    (
        code,
        Json(ProxyHealthResponse {
            status: status.to_string(),
            service: "sip-proxy".to_string(),
            backends: backend_health,
        }),
    )
}
