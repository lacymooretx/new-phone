use std::sync::Arc;

use axum::extract::{Path, State};
use axum::http::{HeaderMap, StatusCode};
use axum::response::IntoResponse;
use axum::Json;
use serde_json::json;

use crate::parking::{self, ParkRequest, ParkingManager, RetrieveRequest};

/// Shared application state passed to all handlers.
pub struct AppState {
    pub parking: ParkingManager,
}

/// Default tenant ID when none is provided.
const DEFAULT_TENANT: &str = "default";

/// Extract tenant_id from the `X-Tenant-ID` header, falling back to the
/// request body's `tenant_id` field if present, or the default.
fn extract_tenant_id(headers: &HeaderMap) -> String {
    headers
        .get("x-tenant-id")
        .and_then(|v| v.to_str().ok())
        .filter(|s| !s.is_empty())
        .map(|s| s.to_string())
        .unwrap_or_else(|| DEFAULT_TENANT.to_string())
}

/// POST /lots/{lot_id}/park -- Park a call.
pub async fn park_call(
    State(state): State<Arc<AppState>>,
    Path(lot_id): Path<String>,
    headers: HeaderMap,
    Json(request): Json<ParkRequest>,
) -> impl IntoResponse {
    // Determine tenant: header > body > default
    let tenant_id = {
        let from_header = extract_tenant_id(&headers);
        if from_header != DEFAULT_TENANT {
            from_header
        } else if let Some(ref tid) = request.tenant_id {
            tid.clone()
        } else {
            from_header
        }
    };

    // Ensure lot exists for this tenant
    state.parking.ensure_lot(&lot_id, &tenant_id).await;

    match state.parking.park_call(&lot_id, request).await {
        Ok(result) => (StatusCode::OK, Json(json!(result))),
        Err(e) => (
            StatusCode::BAD_REQUEST,
            Json(json!({"error": e.to_string()})),
        ),
    }
}

/// POST /lots/{lot_id}/slots/{slot}/retrieve -- Retrieve a parked call.
pub async fn retrieve_call(
    State(state): State<Arc<AppState>>,
    Path((lot_id, slot)): Path<(String, u32)>,
    Json(request): Json<RetrieveRequest>,
) -> impl IntoResponse {
    match state.parking.retrieve_call(&lot_id, slot, request).await {
        Ok((call_uuid, extension)) => (
            StatusCode::OK,
            Json(json!({
                "call_uuid": call_uuid,
                "extension": extension,
                "status": "retrieved"
            })),
        ),
        Err(e) => (
            StatusCode::BAD_REQUEST,
            Json(json!({"error": e.to_string()})),
        ),
    }
}

/// GET /lots/{lot_id}/slots -- List slot states.
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

/// GET /lots -- List all parking lots.
pub async fn list_lots(State(state): State<Arc<AppState>>) -> impl IntoResponse {
    let lots = state.parking.list_lots().await;
    Json(json!(lots))
}

/// DELETE /lots/{lot_id}/slots/{slot} -- Force-release a slot.
pub async fn force_release(
    State(state): State<Arc<AppState>>,
    Path((lot_id, slot)): Path<(String, u32)>,
) -> impl IntoResponse {
    match state.parking.force_release(&lot_id, slot).await {
        Ok(_extension) => (StatusCode::OK, Json(json!({"status": "released"}))),
        Err(e) => (
            StatusCode::BAD_REQUEST,
            Json(json!({"error": e.to_string()})),
        ),
    }
}

/// GET /health -- Health check with actual connectivity verification.
pub async fn health_check(State(state): State<Arc<AppState>>) -> impl IntoResponse {
    let redis_ok = parking::redis_health_check(state.parking.redis_client()).await;
    let esl_ok = state.parking.esl_pool().health_check().await;
    let lot_count = state.parking.list_lots().await.len();
    let active_calls = state.parking.active_call_count().await;

    let overall = if redis_ok && esl_ok {
        "healthy"
    } else if redis_ok || esl_ok {
        "degraded"
    } else {
        "unhealthy"
    };

    let status_code = if overall == "healthy" {
        StatusCode::OK
    } else {
        StatusCode::SERVICE_UNAVAILABLE
    };

    (
        status_code,
        Json(json!({
            "status": overall,
            "service": "parking-manager",
            "checks": {
                "redis": if redis_ok { "ok" } else { "fail" },
                "esl": if esl_ok { "ok" } else { "fail" },
            },
            "stats": {
                "lot_count": lot_count,
                "active_calls": active_calls,
            }
        })),
    )
}
