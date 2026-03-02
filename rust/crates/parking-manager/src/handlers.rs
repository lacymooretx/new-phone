use std::sync::Arc;

use axum::extract::{Path, State};
use axum::http::StatusCode;
use axum::response::IntoResponse;
use axum::Json;
use serde_json::json;

use crate::blf::BlfManager;
use crate::parking::{ParkRequest, ParkingManager, RetrieveRequest};

pub struct AppState {
    pub parking: ParkingManager,
    pub blf: BlfManager,
}

/// POST /lots/{lot_id}/park — Park a call.
pub async fn park_call(
    State(state): State<Arc<AppState>>,
    Path(lot_id): Path<String>,
    Json(request): Json<ParkRequest>,
) -> impl IntoResponse {
    // Ensure lot exists with a default tenant
    state.parking.ensure_lot(&lot_id, "default").await;

    match state.parking.park_call(&lot_id, request).await {
        Ok(result) => {
            // Update BLF state
            state
                .blf
                .update_state(
                    &result.extension,
                    crate::blf::BlfStatus::InUse,
                    None,
                )
                .await;

            (StatusCode::OK, Json(json!(result)))
        }
        Err(e) => (
            StatusCode::BAD_REQUEST,
            Json(json!({"error": e.to_string()})),
        ),
    }
}

/// POST /lots/{lot_id}/slots/{slot}/retrieve — Retrieve a parked call.
pub async fn retrieve_call(
    State(state): State<Arc<AppState>>,
    Path((lot_id, slot)): Path<(String, u32)>,
    Json(request): Json<RetrieveRequest>,
) -> impl IntoResponse {
    match state.parking.retrieve_call(&lot_id, slot, request).await {
        Ok(call_uuid) => {
            // Update BLF state to idle
            let extension = format!("7{:02}", slot);
            state
                .blf
                .update_state(&extension, crate::blf::BlfStatus::Idle, None)
                .await;

            (
                StatusCode::OK,
                Json(json!({"call_uuid": call_uuid, "status": "retrieved"})),
            )
        }
        Err(e) => (
            StatusCode::BAD_REQUEST,
            Json(json!({"error": e.to_string()})),
        ),
    }
}

/// GET /lots/{lot_id}/slots — List slot states.
pub async fn list_slots(
    State(state): State<Arc<AppState>>,
    Path(lot_id): Path<String>,
) -> impl IntoResponse {
    match state.parking.get_slots(&lot_id).await {
        Some(slots) => (StatusCode::OK, Json(json!(slots))),
        None => (
            StatusCode::NOT_FOUND,
            Json(json!({"error": format!("lot {} not found", lot_id)})),
        ),
    }
}

/// GET /lots — List all parking lots.
pub async fn list_lots(State(state): State<Arc<AppState>>) -> impl IntoResponse {
    let lots = state.parking.list_lots().await;
    Json(json!(lots))
}

/// DELETE /lots/{lot_id}/slots/{slot} — Force-release a slot.
pub async fn force_release(
    State(state): State<Arc<AppState>>,
    Path((lot_id, slot)): Path<(String, u32)>,
) -> impl IntoResponse {
    match state.parking.force_release(&lot_id, slot).await {
        Ok(()) => {
            let extension = format!("7{:02}", slot);
            state
                .blf
                .update_state(&extension, crate::blf::BlfStatus::Idle, None)
                .await;

            (StatusCode::OK, Json(json!({"status": "released"})))
        }
        Err(e) => (
            StatusCode::BAD_REQUEST,
            Json(json!({"error": e.to_string()})),
        ),
    }
}

/// GET /health — Health check.
pub async fn health_check() -> impl IntoResponse {
    Json(json!({
        "status": "healthy",
        "service": "parking-manager"
    }))
}
