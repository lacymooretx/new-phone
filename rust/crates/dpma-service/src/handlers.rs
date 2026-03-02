use std::sync::Arc;

use axum::extract::{Path, State};
use axum::http::StatusCode;
use axum::response::IntoResponse;
use axum::Json;
use serde_json::json;

use crate::provisioning::{ProvisioningStore, RegisterRequest};
use crate::templates::PhoneTemplateEngine;

pub struct AppState {
    pub store: ProvisioningStore,
    pub template_engine: PhoneTemplateEngine,
}

/// GET /config/{mac} - Return phone configuration XML.
pub async fn get_config(
    State(state): State<Arc<AppState>>,
    Path(mac): Path<String>,
) -> impl IntoResponse {
    match state.store.get_config(&mac).await {
        Some(config) => match state.template_engine.render_config(&config) {
            Ok(xml) => (
                StatusCode::OK,
                [("content-type", "application/xml")],
                xml,
            ),
            Err(e) => (
                StatusCode::INTERNAL_SERVER_ERROR,
                [("content-type", "application/xml")],
                format!("<!-- Error rendering config: {} -->", e),
            ),
        },
        None => (
            StatusCode::NOT_FOUND,
            [("content-type", "application/xml")],
            format!("<!-- No configuration found for MAC {} -->", mac),
        ),
    }
}

/// GET /firmware/{model} - Return firmware info for a model.
pub async fn get_firmware(
    State(state): State<Arc<AppState>>,
    Path(model): Path<String>,
) -> impl IntoResponse {
    match state.store.get_firmware(&model).await {
        Some(firmware) => (StatusCode::OK, Json(json!(firmware))),
        None => (
            StatusCode::NOT_FOUND,
            Json(json!({"error": format!("no firmware found for model {}", model)})),
        ),
    }
}

/// POST /phones/register - Phone registration callback.
pub async fn register_phone(
    State(state): State<Arc<AppState>>,
    Json(request): Json<RegisterRequest>,
) -> impl IntoResponse {
    let phone = state.store.register_phone(request).await;
    (StatusCode::OK, Json(json!(phone)))
}

/// GET /phones - List all registered phones.
pub async fn list_phones(State(state): State<Arc<AppState>>) -> impl IntoResponse {
    let phones = state.store.list_phones().await;
    Json(json!(phones))
}

/// GET /health - Health check.
pub async fn health_check() -> impl IntoResponse {
    Json(json!({
        "status": "healthy",
        "service": "dpma-service"
    }))
}
