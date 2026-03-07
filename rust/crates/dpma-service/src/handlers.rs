use std::collections::HashMap;
use std::path::PathBuf;
use std::sync::Arc;

use axum::body::Body;
use axum::extract::{Path, State};
use axum::http::{header, HeaderMap, StatusCode};
use axum::response::IntoResponse;
use axum::Json;
use serde_json::json;
use tokio::sync::RwLock;
use tracing::{debug, warn};

use crate::provisioning::{
    CheckinRequest, CheckinResponse, DeviceStore, FirmwareEntry, FirmwareUpdateInfo,
};

pub struct AppState {
    pub store: RwLock<DeviceStore>,
    pub firmware_map: HashMap<String, FirmwareEntry>,
    pub firmware_dir: PathBuf,
    pub offline_threshold_secs: u64,
}

/// POST /phones/checkin - Phone check-in (register/heartbeat).
///
/// The phone sends its MAC, model, firmware version, and IP.
/// We forward to the API, cache in Redis, check firmware, and respond.
pub async fn phone_checkin(
    State(state): State<Arc<AppState>>,
    Json(request): Json<CheckinRequest>,
) -> impl IntoResponse {
    let mut store = state.store.write().await;

    match store.checkin(&request).await {
        Ok(phone) => {
            // Check if firmware update is available
            let firmware_update = state
                .firmware_map
                .get(&phone.model)
                .and_then(|latest| {
                    if latest.version != phone.firmware_version {
                        Some(FirmwareUpdateInfo {
                            model: phone.model.clone(),
                            current_version: phone.firmware_version.clone(),
                            available_version: latest.version.clone(),
                            filename: latest.filename.clone(),
                            download_url: format!(
                                "/firmware/download/{}",
                                latest.filename
                            ),
                            checksum: latest.checksum.clone(),
                        })
                    } else {
                        None
                    }
                });

            let response = CheckinResponse {
                phone,
                firmware_update,
            };
            (StatusCode::OK, Json(json!(response)))
        }
        Err(e) => {
            warn!(error = %e, "phone check-in failed");
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(json!({"error": format!("check-in failed: {}", e)})),
            )
        }
    }
}

/// GET /phones/by-mac/{mac} - Look up a phone by MAC address.
pub async fn get_phone_by_mac(
    State(state): State<Arc<AppState>>,
    Path(mac): Path<String>,
) -> impl IntoResponse {
    let mut store = state.store.write().await;

    match store.get_by_mac(&mac).await {
        Ok(Some(phone)) => (StatusCode::OK, Json(json!(phone))),
        Ok(None) => (
            StatusCode::NOT_FOUND,
            Json(json!({"error": format!("no phone found for MAC {}", mac)})),
        ),
        Err(e) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(json!({"error": format!("lookup failed: {}", e)})),
        ),
    }
}

/// GET /firmware/info/{model} - Get firmware info for a model.
pub async fn get_firmware_info(
    State(state): State<Arc<AppState>>,
    Path(model): Path<String>,
) -> impl IntoResponse {
    match state.firmware_map.get(&model) {
        Some(entry) => (StatusCode::OK, Json(json!(entry))),
        None => (
            StatusCode::NOT_FOUND,
            Json(json!({"error": format!("no firmware found for model {}", model)})),
        ),
    }
}

/// GET /firmware/download/{filename} - Serve a firmware file with range request support.
pub async fn download_firmware(
    State(state): State<Arc<AppState>>,
    Path(filename): Path<String>,
    headers: HeaderMap,
) -> impl IntoResponse {
    // Sanitize filename to prevent directory traversal
    let safe_name = filename
        .replace('/', "")
        .replace('\\', "")
        .replace("..", "");

    let file_path = state.firmware_dir.join(&safe_name);

    if !file_path.exists() || !file_path.is_file() {
        return (
            StatusCode::NOT_FOUND,
            [
                (header::CONTENT_TYPE, "application/json".to_string()),
                (header::ACCEPT_RANGES, "bytes".to_string()),
            ],
            Body::from(format!(r#"{{"error":"firmware file not found: {}"}}"#, safe_name)),
        );
    }

    let metadata = match tokio::fs::metadata(&file_path).await {
        Ok(m) => m,
        Err(_) => {
            return (
                StatusCode::INTERNAL_SERVER_ERROR,
                [
                    (header::CONTENT_TYPE, "application/json".to_string()),
                    (header::ACCEPT_RANGES, "bytes".to_string()),
                ],
                Body::from(r#"{"error":"failed to read firmware file metadata"}"#),
            );
        }
    };

    let total_size = metadata.len();

    // Check for Range header
    if let Some(range_header) = headers.get(header::RANGE) {
        if let Ok(range_str) = range_header.to_str() {
            if let Some(range) = parse_range_header(range_str, total_size) {
                let (start, end) = range;
                let length = end - start + 1;

                debug!(
                    file = %safe_name,
                    start = start,
                    end = end,
                    total = total_size,
                    "serving firmware range request"
                );

                match read_file_range(&file_path, start, length).await {
                    Ok(data) => {
                        return (
                            StatusCode::PARTIAL_CONTENT,
                            [
                                (
                                    header::CONTENT_TYPE,
                                    "application/octet-stream".to_string(),
                                ),
                                (header::ACCEPT_RANGES, "bytes".to_string()),
                            ],
                            Body::from(data),
                        );
                    }
                    Err(_) => {
                        return (
                            StatusCode::INTERNAL_SERVER_ERROR,
                            [
                                (header::CONTENT_TYPE, "application/json".to_string()),
                                (header::ACCEPT_RANGES, "bytes".to_string()),
                            ],
                            Body::from(r#"{"error":"failed to read firmware file range"}"#),
                        );
                    }
                }
            }
        }
    }

    // Full file download
    debug!(file = %safe_name, size = total_size, "serving full firmware download");

    match tokio::fs::read(&file_path).await {
        Ok(data) => (
            StatusCode::OK,
            [
                (
                    header::CONTENT_TYPE,
                    "application/octet-stream".to_string(),
                ),
                (header::ACCEPT_RANGES, "bytes".to_string()),
            ],
            Body::from(data),
        ),
        Err(_) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            [
                (header::CONTENT_TYPE, "application/json".to_string()),
                (header::ACCEPT_RANGES, "bytes".to_string()),
            ],
            Body::from(r#"{"error":"failed to read firmware file"}"#),
        ),
    }
}

/// GET /health - Health check with detailed metrics.
pub async fn health_check(State(state): State<Arc<AppState>>) -> impl IntoResponse {
    let mut store = state.store.write().await;

    let redis_ok = store.check_redis().await;
    let api_ok = store.check_api().await;

    // Count tracked phones and find offline ones
    let all_last_seen = store.get_all_last_seen().await.unwrap_or_default();
    let now = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs();

    let total_phones = all_last_seen.len();
    let offline_phones: Vec<&String> = all_last_seen
        .iter()
        .filter(|(_, ts)| now.saturating_sub(*ts) > state.offline_threshold_secs)
        .map(|(mac, _)| mac)
        .collect();

    // Firmware versions in fleet
    let firmware_models: Vec<String> = state.firmware_map.keys().cloned().collect();

    let status = if redis_ok && api_ok {
        "healthy"
    } else if redis_ok {
        "degraded"
    } else {
        "unhealthy"
    };

    Json(json!({
        "status": status,
        "service": "dpma-service",
        "redis_connected": redis_ok,
        "api_connected": api_ok,
        "total_phones_tracked": total_phones,
        "phones_offline": offline_phones.len(),
        "offline_macs": offline_phones,
        "firmware_models_available": firmware_models,
        "offline_threshold_secs": state.offline_threshold_secs,
    }))
}

/// Parse a simple "bytes=start-end" Range header.
fn parse_range_header(range_str: &str, total_size: u64) -> Option<(u64, u64)> {
    let range_str = range_str.strip_prefix("bytes=")?;

    if let Some((start_str, end_str)) = range_str.split_once('-') {
        if start_str.is_empty() {
            // Suffix range: bytes=-500 means last 500 bytes
            let suffix: u64 = end_str.parse().ok()?;
            let start = total_size.saturating_sub(suffix);
            let end = total_size - 1;
            if start < total_size {
                Some((start, end))
            } else {
                None
            }
        } else {
            let start: u64 = start_str.parse().ok()?;
            let end: u64 = if end_str.is_empty() {
                total_size - 1
            } else {
                end_str.parse().ok()?
            };

            if start <= end && start < total_size {
                Some((start, end.min(total_size - 1)))
            } else {
                None
            }
        }
    } else {
        None
    }
}

/// Read a range of bytes from a file.
async fn read_file_range(
    path: &std::path::Path,
    start: u64,
    length: u64,
) -> Result<Vec<u8>, std::io::Error> {
    use tokio::io::{AsyncReadExt, AsyncSeekExt};

    let mut file = tokio::fs::File::open(path).await?;
    file.seek(std::io::SeekFrom::Start(start)).await?;

    let mut buffer = vec![0u8; length as usize];
    let bytes_read = file.read_exact(&mut buffer).await?;
    buffer.truncate(bytes_read);
    Ok(buffer)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_range_header_basic() {
        assert_eq!(parse_range_header("bytes=0-499", 1000), Some((0, 499)));
        assert_eq!(parse_range_header("bytes=500-999", 1000), Some((500, 999)));
    }

    #[test]
    fn test_parse_range_header_open_end() {
        assert_eq!(parse_range_header("bytes=500-", 1000), Some((500, 999)));
    }

    #[test]
    fn test_parse_range_header_suffix() {
        assert_eq!(parse_range_header("bytes=-200", 1000), Some((800, 999)));
    }

    #[test]
    fn test_parse_range_header_invalid() {
        assert_eq!(parse_range_header("bytes=999-100", 1000), None);
        assert_eq!(parse_range_header("bytes=1500-2000", 1000), None);
        assert_eq!(parse_range_header("invalid", 1000), None);
    }

    #[test]
    fn test_parse_range_header_clamp_end() {
        // end beyond file size should be clamped
        assert_eq!(parse_range_header("bytes=900-2000", 1000), Some((900, 999)));
    }
}
