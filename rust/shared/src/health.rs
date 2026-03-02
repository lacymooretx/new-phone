use axum::http::StatusCode;
use axum::response::{IntoResponse, Response};
use axum::Json;
use serde::Serialize;

#[derive(Serialize)]
pub struct HealthResponse {
    pub status: String,
    pub service: String,
    pub version: String,
}

/// Create a health check handler closure for a given service name.
///
/// Usage with axum:
/// ```ignore
/// let app = Router::new().route("/health", get(health_handler("my-service")));
/// ```
pub fn health_handler(
    service_name: &'static str,
) -> impl Fn() -> std::pin::Pin<Box<dyn std::future::Future<Output = Response> + Send>>
       + Clone
       + Send {
    move || {
        Box::pin(async move {
            let resp = HealthResponse {
                status: "healthy".to_string(),
                service: service_name.to_string(),
                version: env!("CARGO_PKG_VERSION").to_string(),
            };
            (StatusCode::OK, Json(resp)).into_response()
        })
    }
}
