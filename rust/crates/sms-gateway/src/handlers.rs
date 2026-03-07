use std::collections::HashMap;
use std::sync::Arc;

use axum::extract::{Path, State};
use axum::http::StatusCode;
use axum::response::IntoResponse;
use axum::{Form, Json};
use reqwest::Client as HttpClient;
use serde::Deserialize;
use serde_json::json;
use tracing::{error, info, warn};

use crate::providers::InboundMessage;
use crate::rate_limiter::RateLimiter;
use crate::router::SmsRouter;

pub struct AppState {
    pub router: SmsRouter,
    pub rate_limiter: RateLimiter,
    pub api_url: String,
    pub http_client: HttpClient,
}

/// POST /send -- Send an SMS/MMS.
#[derive(Debug, Deserialize)]
pub struct SendRequest {
    pub from: String,
    pub to: String,
    pub body: String,
    #[serde(default)]
    pub media_urls: Vec<String>,
}

pub async fn send_sms(
    State(state): State<Arc<AppState>>,
    Json(request): Json<SendRequest>,
) -> impl IntoResponse {
    // Check rate limit
    match state.rate_limiter.check_and_increment(&request.from).await {
        Ok(result) if !result.allowed => {
            return (
                StatusCode::TOO_MANY_REQUESTS,
                Json(json!({
                    "error": "rate limit exceeded",
                    "retry_after_ms": result.retry_after_ms,
                    "minute_count": result.minute_count,
                    "hour_count": result.hour_count,
                })),
            );
        }
        Err(e) => {
            warn!(error = %e, "rate limiter error, proceeding without limit check");
        }
        _ => {}
    }

    // Route and send
    match state
        .router
        .send(&request.from, &request.to, &request.body, &request.media_urls)
        .await
    {
        Ok(result) => (StatusCode::OK, Json(json!(result))),
        Err(e) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(json!({"error": e.to_string()})),
        ),
    }
}

// ---------------------------------------------------------------------------
// Inbound webhook: ClearlyIP (JSON POST)
// ---------------------------------------------------------------------------

#[derive(Debug, Deserialize)]
pub struct ClearlyIpWebhook {
    #[serde(default)]
    pub from: String,
    #[serde(default)]
    pub to: String,
    #[serde(default)]
    pub body: String,
    #[serde(default)]
    pub message_id: String,
    #[serde(default)]
    pub media_urls: Vec<String>,
}

pub async fn webhook_clearlyip(
    State(state): State<Arc<AppState>>,
    Json(payload): Json<ClearlyIpWebhook>,
) -> impl IntoResponse {
    let now = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs();

    let message = InboundMessage {
        message_id: if payload.message_id.is_empty() {
            uuid::Uuid::new_v4().to_string()
        } else {
            payload.message_id
        },
        from: payload.from,
        to: payload.to,
        body: payload.body,
        media_urls: payload.media_urls,
        provider: "clearlyip".to_string(),
        received_at: now,
    };

    info!(
        from = %message.from,
        to = %message.to,
        message_id = %message.message_id,
        media_count = message.media_urls.len(),
        "inbound SMS received via ClearlyIP"
    );

    process_inbound_message(&state, &message).await;

    (
        StatusCode::OK,
        Json(json!({"status": "received", "message_id": message.message_id})),
    )
}

// ---------------------------------------------------------------------------
// Inbound webhook: Twilio (application/x-www-form-urlencoded POST)
// ---------------------------------------------------------------------------

/// Twilio sends webhooks as form-encoded data. Media attachments arrive as
/// MediaUrl0, MediaUrl1, ..., MediaUrlN alongside a NumMedia count field.
/// We use a HashMap to capture all fields including the dynamic MediaUrl keys.
#[derive(Debug, Deserialize)]
pub struct TwilioWebhookCore {
    #[serde(rename = "From", default)]
    pub from: String,
    #[serde(rename = "To", default)]
    pub to: String,
    #[serde(rename = "Body", default)]
    pub body: String,
    #[serde(rename = "MessageSid", default)]
    pub message_sid: String,
    #[serde(rename = "NumMedia", default)]
    pub num_media: String,
}

pub async fn webhook_twilio(
    State(state): State<Arc<AppState>>,
    Form(params): Form<HashMap<String, String>>,
) -> impl IntoResponse {
    let now = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs();

    let from = params.get("From").cloned().unwrap_or_default();
    let to = params.get("To").cloned().unwrap_or_default();
    let body = params.get("Body").cloned().unwrap_or_default();
    let message_sid = params.get("MessageSid").cloned().unwrap_or_default();
    let num_media_str = params.get("NumMedia").cloned().unwrap_or_default();

    // Extract MMS media URLs: Twilio sends MediaUrl0, MediaUrl1, ... MediaUrlN
    let num_media: u32 = num_media_str.parse().unwrap_or(0);
    let mut media_urls = Vec::with_capacity(num_media as usize);
    for i in 0..num_media {
        let key = format!("MediaUrl{}", i);
        if let Some(url) = params.get(&key) {
            media_urls.push(url.clone());
        }
    }

    let message = InboundMessage {
        message_id: if message_sid.is_empty() {
            uuid::Uuid::new_v4().to_string()
        } else {
            message_sid
        },
        from,
        to,
        body,
        media_urls,
        provider: "twilio".to_string(),
        received_at: now,
    };

    info!(
        from = %message.from,
        to = %message.to,
        message_id = %message.message_id,
        media_count = message.media_urls.len(),
        "inbound SMS received via Twilio"
    );

    process_inbound_message(&state, &message).await;

    // Return empty TwiML response to acknowledge receipt
    (
        StatusCode::OK,
        [("content-type", "application/xml")],
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?><Response></Response>".to_string(),
    )
}

// ---------------------------------------------------------------------------
// Shared inbound message processing
// ---------------------------------------------------------------------------

/// Publish the inbound message to Redis pub/sub and POST it to the API for
/// persistence. Both operations are best-effort; webhook acknowledgement is
/// not blocked by downstream failures.
async fn process_inbound_message(state: &AppState, message: &InboundMessage) {
    let message_json = match serde_json::to_string(message) {
        Ok(j) => j,
        Err(e) => {
            error!(error = %e, "failed to serialize inbound message");
            return;
        }
    };

    // 1. Publish to Redis pub/sub: np:sms:inbound:{to_number}
    if let Err(e) = state
        .router
        .publish_inbound(&message.to, &message_json)
        .await
    {
        warn!(
            error = %e,
            to = %message.to,
            message_id = %message.message_id,
            "failed to publish inbound message to Redis"
        );
    }

    // 2. POST to API for persistence: POST {API_URL}/api/v1/sms/inbound
    let api_url = format!("{}/api/v1/sms/inbound", state.api_url);
    match state
        .http_client
        .post(&api_url)
        .header("Content-Type", "application/json")
        .body(message_json)
        .send()
        .await
    {
        Ok(resp) => {
            if resp.status().is_success() {
                info!(
                    message_id = %message.message_id,
                    "inbound message forwarded to API"
                );
            } else {
                warn!(
                    message_id = %message.message_id,
                    status = %resp.status(),
                    "API returned non-success for inbound message"
                );
            }
        }
        Err(e) => {
            warn!(
                error = %e,
                message_id = %message.message_id,
                "failed to POST inbound message to API"
            );
        }
    }
}

// ---------------------------------------------------------------------------
// GET /status/{message_id} -- Get message delivery status
// ---------------------------------------------------------------------------

pub async fn get_status(
    State(state): State<Arc<AppState>>,
    Path(message_id): Path<String>,
) -> impl IntoResponse {
    // Look up the provider from Redis message tracking
    if let Some(tracking) = state.router.lookup_message_tracking(&message_id).await {
        match state
            .router
            .get_status(&tracking.provider_message_id, &tracking.provider)
            .await
        {
            Ok(status) => {
                return (
                    StatusCode::OK,
                    Json(json!({
                        "message_id": message_id,
                        "provider": tracking.provider,
                        "provider_message_id": tracking.provider_message_id,
                        "status": status,
                    })),
                );
            }
            Err(e) => {
                warn!(
                    message_id = %message_id,
                    provider = %tracking.provider,
                    error = %e,
                    "failed to fetch status from tracked provider"
                );
            }
        }
    }

    // Fallback: try each provider sequentially (for messages sent before tracking was added)
    for provider_name in state.router.provider_names() {
        match state.router.get_status(&message_id, &provider_name).await {
            Ok(status) => {
                return (
                    StatusCode::OK,
                    Json(json!({
                        "message_id": message_id,
                        "provider": provider_name,
                        "status": status,
                    })),
                );
            }
            Err(_) => continue,
        }
    }

    (
        StatusCode::NOT_FOUND,
        Json(json!({"error": "message not found"})),
    )
}

// ---------------------------------------------------------------------------
// GET /health -- Comprehensive health check
// ---------------------------------------------------------------------------

pub async fn health_check(State(state): State<Arc<AppState>>) -> impl IntoResponse {
    let redis_ok = state.router.redis_healthy().await;
    let rate_limiter_ok = state.rate_limiter.redis_healthy().await;
    let provider_health = state.router.provider_health_status().await;

    let all_healthy = redis_ok && rate_limiter_ok;

    let status_code = if all_healthy {
        StatusCode::OK
    } else {
        StatusCode::SERVICE_UNAVAILABLE
    };

    (
        status_code,
        Json(json!({
            "status": if all_healthy { "healthy" } else { "degraded" },
            "service": "sms-gateway",
            "components": {
                "redis": {
                    "status": if redis_ok { "healthy" } else { "unhealthy" }
                },
                "rate_limiter": {
                    "status": if rate_limiter_ok { "healthy" } else { "unhealthy" }
                },
                "providers": provider_health,
            }
        })),
    )
}
