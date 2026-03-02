use std::sync::Arc;

use axum::extract::{Path, State};
use axum::http::StatusCode;
use axum::response::IntoResponse;
use axum::Json;
use serde::Deserialize;
use serde_json::json;
use tracing::{info, warn};

use crate::providers::InboundMessage;
use crate::rate_limiter::RateLimiter;
use crate::router::SmsRouter;

pub struct AppState {
    pub router: SmsRouter,
    pub rate_limiter: RateLimiter,
}

/// POST /send — Send an SMS/MMS.
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

/// POST /webhooks/clearlyip — Inbound webhook from ClearlyIP.
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

pub async fn webhook_clearlyip(Json(payload): Json<ClearlyIpWebhook>) -> impl IntoResponse {
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
        from: payload.from.clone(),
        to: payload.to.clone(),
        body: payload.body.clone(),
        media_urls: payload.media_urls,
        provider: "clearlyip".to_string(),
        received_at: now,
    };

    info!(
        from = %message.from,
        to = %message.to,
        message_id = %message.message_id,
        "inbound SMS received via ClearlyIP"
    );

    // In production, this would publish to Redis or an internal queue for processing
    (StatusCode::OK, Json(json!({"status": "received", "message_id": message.message_id})))
}

/// POST /webhooks/twilio — Inbound webhook from Twilio.
#[derive(Debug, Deserialize)]
pub struct TwilioWebhook {
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

pub async fn webhook_twilio(Json(payload): Json<TwilioWebhook>) -> impl IntoResponse {
    let now = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs();

    let message = InboundMessage {
        message_id: if payload.message_sid.is_empty() {
            uuid::Uuid::new_v4().to_string()
        } else {
            payload.message_sid
        },
        from: payload.from.clone(),
        to: payload.to.clone(),
        body: payload.body.clone(),
        media_urls: Vec::new(), // Would extract from MediaUrl0, MediaUrl1, etc.
        provider: "twilio".to_string(),
        received_at: now,
    };

    info!(
        from = %message.from,
        to = %message.to,
        message_id = %message.message_id,
        "inbound SMS received via Twilio"
    );

    // Return TwiML-style empty response
    (
        StatusCode::OK,
        [("content-type", "application/xml")],
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?><Response></Response>".to_string(),
    )
}

/// GET /status/{message_id} — Get message delivery status.
#[derive(Debug, Deserialize)]
pub struct StatusQuery {
    pub provider: Option<String>,
}

pub async fn get_status(
    State(state): State<Arc<AppState>>,
    Path(message_id): Path<String>,
) -> impl IntoResponse {
    // Try each provider to find the message
    // In production, we'd store message -> provider mapping in Redis
    let providers = ["clearlyip", "twilio"];
    for provider in &providers {
        match state.router.get_status(&message_id, provider).await {
            Ok(status) => {
                return (
                    StatusCode::OK,
                    Json(json!({
                        "message_id": message_id,
                        "provider": provider,
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

/// GET /health — Health check.
pub async fn health_check() -> impl IntoResponse {
    Json(json!({
        "status": "healthy",
        "service": "sms-gateway"
    }))
}
