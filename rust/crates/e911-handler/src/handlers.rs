use std::sync::Arc;

use axum::extract::{Path, State};
use axum::http::StatusCode;
use axum::response::IntoResponse;
use axum::Json;
use serde::Deserialize;
use serde_json::json;

use crate::pidf_lo::{self, ExtensionLocation};
use crate::routing::{EmergencyRouter, LocationStore};

pub struct AppState {
    pub router: EmergencyRouter,
    pub locations: LocationStore,
}

/// POST /locations — Create/update extension location.
#[derive(Debug, Deserialize)]
pub struct CreateLocationRequest {
    pub extension: String,
    pub tenant_id: String,
    pub civic_address: pidf_lo::CivicAddress,
    pub geo_coordinates: Option<pidf_lo::GeoCoordinates>,
}

pub async fn create_location(
    State(state): State<Arc<AppState>>,
    Json(request): Json<CreateLocationRequest>,
) -> impl IntoResponse {
    let now = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs();

    let location = ExtensionLocation {
        extension: request.extension.clone(),
        tenant_id: request.tenant_id.clone(),
        civic_address: request.civic_address,
        geo_coordinates: request.geo_coordinates,
        updated_at: now,
    };

    state.locations.set_location(location.clone()).await;

    (StatusCode::CREATED, Json(json!(location)))
}

/// GET /locations/{extension} — Get extension location.
pub async fn get_location(
    State(state): State<Arc<AppState>>,
    Path(extension): Path<String>,
) -> impl IntoResponse {
    // Try with "default" tenant first — in production, tenant_id would come from auth
    match state.locations.get_location(&extension, "default").await {
        Some(location) => (StatusCode::OK, Json(json!(location))),
        None => (
            StatusCode::NOT_FOUND,
            Json(json!({"error": format!("no location found for extension {}", extension)})),
        ),
    }
}

/// GET /locations — List all locations.
pub async fn list_locations(State(state): State<Arc<AppState>>) -> impl IntoResponse {
    let locations = state.locations.list_locations().await;
    Json(json!(locations))
}

/// DELETE /locations/{extension} — Remove extension location.
pub async fn delete_location(
    State(state): State<Arc<AppState>>,
    Path(extension): Path<String>,
) -> impl IntoResponse {
    let removed = state.locations.remove_location(&extension, "default").await;
    if removed {
        (StatusCode::OK, Json(json!({"status": "deleted"})))
    } else {
        (
            StatusCode::NOT_FOUND,
            Json(json!({"error": "location not found"})),
        )
    }
}

/// POST /emergency-call — Handle emergency call routing.
#[derive(Debug, Deserialize)]
pub struct EmergencyCallRequest {
    pub extension: String,
    pub tenant_id: String,
    pub call_uuid: String,
}

pub async fn handle_emergency_call(
    State(state): State<Arc<AppState>>,
    Json(request): Json<EmergencyCallRequest>,
) -> impl IntoResponse {
    // Look up the caller's location
    let location = state
        .locations
        .get_location(&request.extension, &request.tenant_id)
        .await;

    let state_code = location
        .as_ref()
        .and_then(|l| l.civic_address.state.as_deref());

    // Route the call
    let result = state
        .router
        .route_call(&request.extension, &request.tenant_id, state_code)
        .await;

    tracing::warn!(
        extension = %request.extension,
        tenant_id = %request.tenant_id,
        call_uuid = %request.call_uuid,
        psap_id = %result.psap_id,
        trunk = %result.trunk,
        "EMERGENCY CALL ROUTED"
    );

    (StatusCode::OK, Json(json!(result)))
}

/// GET /pidf-lo/{extension} — Get PIDF-LO XML document.
pub async fn get_pidf_lo(
    State(state): State<Arc<AppState>>,
    Path(extension): Path<String>,
) -> impl IntoResponse {
    match state.locations.get_location(&extension, "default").await {
        Some(location) => {
            let xml = pidf_lo::build_pidf_lo(&location);
            (
                StatusCode::OK,
                [("content-type", "application/pidf+xml")],
                xml,
            )
        }
        None => (
            StatusCode::NOT_FOUND,
            [("content-type", "application/pidf+xml")],
            format!("<!-- No location found for extension {} -->", extension),
        ),
    }
}

/// GET /health — Health check.
pub async fn health_check() -> impl IntoResponse {
    Json(json!({
        "status": "healthy",
        "service": "e911-handler"
    }))
}
