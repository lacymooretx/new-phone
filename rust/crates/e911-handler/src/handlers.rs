use std::sync::Arc;

use axum::extract::{Path, State};
use axum::http::{HeaderMap, StatusCode};
use axum::response::IntoResponse;
use axum::Json;
use serde::Deserialize;
use serde_json::json;
use tracing::{error, warn};

use crate::pidf_lo::{self, ExtensionLocation};
use crate::routing::{
    self, CarrierApiClient, EmergencyRouter, LocationStore, RoutingResult,
};

// ---------------------------------------------------------------------------
// Shared application state
// ---------------------------------------------------------------------------

pub struct AppState {
    pub router: EmergencyRouter,
    pub locations: LocationStore,
    pub carrier: Option<CarrierApiClient>,
    pub http_client: reqwest::Client,
    pub api_url: String,
    pub internal_api_key: String,
    pub esl_host: String,
    pub esl_port: u16,
    pub esl_password: String,
    pub sip_domain: String,
    pub listen_addr: String,
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/// Extract tenant_id from the X-Tenant-ID header, or fall back to request body field.
fn extract_tenant_id(headers: &HeaderMap) -> Option<String> {
    headers
        .get("X-Tenant-ID")
        .and_then(|v| v.to_str().ok())
        .map(|s| s.to_string())
}

/// Require tenant_id from headers; return 400 if missing.
fn require_tenant_id(headers: &HeaderMap) -> Result<String, (StatusCode, Json<serde_json::Value>)> {
    extract_tenant_id(headers).ok_or_else(|| {
        (
            StatusCode::BAD_REQUEST,
            Json(json!({"error": "X-Tenant-ID header is required"})),
        )
    })
}

// ---------------------------------------------------------------------------
// POST /locations — Create/update extension location
// ---------------------------------------------------------------------------

#[derive(Debug, Deserialize)]
pub struct CreateLocationRequest {
    pub extension: String,
    /// Optional in body — if provided it overrides the header for backward compat
    pub tenant_id: Option<String>,
    pub civic_address: pidf_lo::CivicAddress,
    pub geo_coordinates: Option<pidf_lo::GeoCoordinates>,
}

pub async fn create_location(
    State(state): State<Arc<AppState>>,
    headers: HeaderMap,
    Json(request): Json<CreateLocationRequest>,
) -> impl IntoResponse {
    // Resolve tenant: header takes precedence, body field is fallback
    let tenant_id = match extract_tenant_id(&headers).or(request.tenant_id.clone()) {
        Some(tid) => tid,
        None => {
            return (
                StatusCode::BAD_REQUEST,
                Json(json!({"error": "tenant_id required (X-Tenant-ID header or body field)"})),
            );
        }
    };

    let now = now_epoch();

    let location = ExtensionLocation {
        extension: request.extension.clone(),
        tenant_id: tenant_id.clone(),
        civic_address: request.civic_address,
        geo_coordinates: request.geo_coordinates,
        updated_at: now,
    };

    // Push to control-plane API + cache in Redis
    if let Err(e) = state.locations.set_location(location.clone()).await {
        error!(error = %e, "failed to persist location");
        return (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(json!({"error": format!("failed to persist location: {}", e)})),
        );
    }

    // Provision with carrier API (async, non-blocking)
    if let Some(ref carrier) = state.carrier {
        let carrier_loc = location.clone();
        let carrier_client_url = carrier.api_url().to_string();
        // We cannot move carrier out of Arc, so we do the call inline in a spawn
        // but we need an owned reference. Since CarrierApiClient is inside Arc<AppState>,
        // we clone the state Arc.
        let state_clone = state.clone();
        tokio::spawn(async move {
            if let Some(ref c) = state_clone.carrier {
                if let Err(e) = c.provision_location(&carrier_loc).await {
                    warn!(
                        error = %e,
                        carrier_url = %carrier_client_url,
                        extension = %carrier_loc.extension,
                        "failed to provision location with carrier (non-fatal)"
                    );
                }
            }
        });
    }

    (StatusCode::CREATED, Json(json!(location)))
}

// ---------------------------------------------------------------------------
// GET /locations/{extension} — Get extension location
// ---------------------------------------------------------------------------

pub async fn get_location(
    State(state): State<Arc<AppState>>,
    headers: HeaderMap,
    Path(extension): Path<String>,
) -> impl IntoResponse {
    let tenant_id = match require_tenant_id(&headers) {
        Ok(t) => t,
        Err(e) => return e,
    };

    match state.locations.get_location(&extension, &tenant_id).await {
        Some(location) => (StatusCode::OK, Json(json!(location))),
        None => (
            StatusCode::NOT_FOUND,
            Json(json!({"error": format!("no location found for extension {}", extension)})),
        ),
    }
}

// ---------------------------------------------------------------------------
// GET /locations — List all locations for tenant
// ---------------------------------------------------------------------------

pub async fn list_locations(
    State(state): State<Arc<AppState>>,
    headers: HeaderMap,
) -> impl IntoResponse {
    let tenant_id = match require_tenant_id(&headers) {
        Ok(t) => t,
        Err(e) => return e.into_response(),
    };

    match state.locations.list_locations(&tenant_id).await {
        Ok(locations) => (StatusCode::OK, Json(json!(locations))).into_response(),
        Err(e) => {
            error!(error = %e, "failed to list locations");
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(json!({"error": format!("failed to list locations: {}", e)})),
            )
                .into_response()
        }
    }
}

// ---------------------------------------------------------------------------
// DELETE /locations/{extension} — Remove extension location
// ---------------------------------------------------------------------------

pub async fn delete_location(
    State(state): State<Arc<AppState>>,
    headers: HeaderMap,
    Path(extension): Path<String>,
) -> impl IntoResponse {
    let tenant_id = match require_tenant_id(&headers) {
        Ok(t) => t,
        Err(e) => return e,
    };

    match state.locations.remove_location(&extension, &tenant_id).await {
        Ok(true) => (StatusCode::OK, Json(json!({"status": "deleted"}))),
        Ok(false) => (
            StatusCode::NOT_FOUND,
            Json(json!({"error": "location not found"})),
        ),
        Err(e) => {
            error!(error = %e, "failed to delete location");
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(json!({"error": format!("failed to delete location: {}", e)})),
            )
        }
    }
}

// ---------------------------------------------------------------------------
// POST /emergency-call — Handle emergency call routing
// ---------------------------------------------------------------------------

#[derive(Debug, Deserialize)]
pub struct EmergencyCallRequest {
    pub extension: String,
    pub tenant_id: Option<String>,
    pub call_uuid: String,
}

pub async fn handle_emergency_call(
    State(state): State<Arc<AppState>>,
    headers: HeaderMap,
    Json(request): Json<EmergencyCallRequest>,
) -> impl IntoResponse {
    let tenant_id = match extract_tenant_id(&headers).or(request.tenant_id.clone()) {
        Some(tid) => tid,
        None => {
            return (
                StatusCode::BAD_REQUEST,
                Json(json!({"error": "tenant_id required (X-Tenant-ID header or body field)"})),
            );
        }
    };

    // Look up the caller's location
    let location = state
        .locations
        .get_location(&request.extension, &tenant_id)
        .await;

    let state_code = location
        .as_ref()
        .and_then(|l| l.civic_address.state.as_deref());

    // Route the call — tries carrier API first, then local PSAP table
    let result: RoutingResult = state
        .router
        .route_call(
            &request.extension,
            &tenant_id,
            state_code,
            state.carrier.as_ref(),
            location.as_ref(),
        )
        .await;

    tracing::warn!(
        extension = %request.extension,
        tenant_id = %tenant_id,
        call_uuid = %request.call_uuid,
        psap_id = %result.psap_id,
        trunk = %result.trunk,
        carrier_routed = result.carrier_routed,
        "EMERGENCY CALL ROUTED"
    );

    // Originate the call via FreeSWITCH ESL (non-blocking)
    {
        let esl_host = state.esl_host.clone();
        let esl_port = state.esl_port;
        let esl_password = state.esl_password.clone();
        let call_uuid = request.call_uuid.clone();
        let trunk = result.trunk.clone();
        let extension = request.extension.clone();
        let sip_domain = state.sip_domain.clone();
        let listen_addr = state.listen_addr.clone();

        // The PIDF-LO URL points back to this service so the SIP stack can
        // dereference it when building the outbound INVITE.
        let pidf_lo_url = format!(
            "http://{}/pidf-lo/{}",
            listen_addr, extension
        );

        tokio::spawn(async move {
            if let Err(e) = routing::esl_originate_emergency_call(
                &esl_host,
                esl_port,
                &esl_password,
                &call_uuid,
                &trunk,
                &extension,
                &sip_domain,
                &pidf_lo_url,
            )
            .await
            {
                error!(
                    error = %e,
                    call_uuid = %call_uuid,
                    "CRITICAL: failed to originate emergency call via ESL"
                );
            }
        });
    }

    // Log emergency call to audit trail (non-blocking)
    {
        let http_client = state.http_client.clone();
        let api_url = state.api_url.clone();
        let internal_api_key = state.internal_api_key.clone();
        let call_uuid = request.call_uuid.clone();
        let extension = request.extension.clone();
        let tenant_id_clone = tenant_id.clone();
        let result_clone = result.clone();
        let location_clone = location.clone();

        tokio::spawn(async move {
            if let Err(e) = routing::log_emergency_call_to_api(
                &http_client,
                &api_url,
                &internal_api_key,
                &call_uuid,
                &extension,
                &tenant_id_clone,
                &result_clone,
                location_clone.as_ref(),
            )
            .await
            {
                warn!(
                    error = %e,
                    call_uuid = %call_uuid,
                    "failed to log emergency call to audit trail (non-fatal)"
                );
            }
        });
    }

    (StatusCode::OK, Json(json!(result)))
}

// ---------------------------------------------------------------------------
// GET /pidf-lo/{extension} — Get PIDF-LO XML document
// ---------------------------------------------------------------------------

pub async fn get_pidf_lo(
    State(state): State<Arc<AppState>>,
    headers: HeaderMap,
    Path(extension): Path<String>,
) -> impl IntoResponse {
    // For PIDF-LO retrieval, tenant_id can come from header or default
    // (FreeSWITCH may fetch this without knowing tenant context)
    let tenant_id = extract_tenant_id(&headers).unwrap_or_else(|| "default".to_string());

    match state.locations.get_location(&extension, &tenant_id).await {
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

// ---------------------------------------------------------------------------
// GET /health — Detailed health check
// ---------------------------------------------------------------------------

pub async fn health_check(State(state): State<Arc<AppState>>) -> impl IntoResponse {
    let redis_ok = state.locations.redis_healthy().await;
    let (cache_hits, cache_misses) = state.locations.cache_stats();
    let psap_route_count = state.router.route_count();
    let psap_routes_loaded = state.router.routes_loaded();

    let carrier_status = if let Some(ref carrier) = state.carrier {
        if carrier.health_check().await {
            "connected"
        } else {
            "unreachable"
        }
    } else {
        "not_configured"
    };

    let overall = if redis_ok && psap_routes_loaded {
        "healthy"
    } else {
        "degraded"
    };

    Json(json!({
        "status": overall,
        "service": "e911-handler",
        "redis": {
            "connected": redis_ok,
        },
        "location_cache": {
            "hits": cache_hits,
            "misses": cache_misses,
        },
        "psap_routes": {
            "loaded": psap_routes_loaded,
            "count": psap_route_count,
        },
        "carrier_api": {
            "status": carrier_status,
        },
    }))
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

fn now_epoch() -> u64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs()
}
