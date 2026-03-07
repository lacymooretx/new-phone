use std::collections::HashMap;

use anyhow::{Context, Result};
use redis::AsyncCommands;
use serde::{Deserialize, Serialize};
use tracing::{debug, info, warn};

/// Phone registration data.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Phone {
    pub mac_address: String,
    pub model: String,
    pub firmware_version: String,
    pub ip_address: Option<String>,
    pub extension: Option<String>,
    pub tenant_id: Option<String>,
    pub registered_at: Option<u64>,
    pub last_seen: Option<u64>,
}

/// Phone check-in request sent to the API.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CheckinRequest {
    pub mac_address: String,
    pub model: String,
    pub firmware_version: String,
    pub ip_address: String,
}

/// Phone check-in response from the API (or local).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CheckinResponse {
    pub phone: Phone,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub firmware_update: Option<FirmwareUpdateInfo>,
}

/// Firmware update info returned in check-in response.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FirmwareUpdateInfo {
    pub model: String,
    pub current_version: String,
    pub available_version: String,
    pub filename: String,
    pub download_url: String,
    pub checksum: String,
}

/// Firmware entry from the manifest file.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FirmwareEntry {
    pub model: String,
    pub version: String,
    pub filename: String,
    pub checksum: String,
}

/// Firmware manifest: model -> latest firmware info.
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct FirmwareManifest {
    pub firmware: Vec<FirmwareEntry>,
}

impl FirmwareManifest {
    /// Load from a JSON file, returning empty manifest if file doesn't exist.
    pub fn load_from_file(path: &str) -> Self {
        match std::fs::read_to_string(path) {
            Ok(contents) => match serde_json::from_str(&contents) {
                Ok(manifest) => {
                    info!(path = path, "loaded firmware manifest");
                    manifest
                }
                Err(e) => {
                    warn!(path = path, error = %e, "failed to parse firmware manifest, using defaults");
                    Self::default_manifest()
                }
            },
            Err(_) => {
                info!(path = path, "firmware manifest not found, using defaults");
                Self::default_manifest()
            }
        }
    }

    /// Default firmware manifest for common phone models.
    fn default_manifest() -> Self {
        FirmwareManifest {
            firmware: vec![
                FirmwareEntry {
                    model: "P310".to_string(),
                    version: "4.1.0".to_string(),
                    filename: "p310-4.1.0.fw".to_string(),
                    checksum: String::new(),
                },
                FirmwareEntry {
                    model: "P315".to_string(),
                    version: "4.1.0".to_string(),
                    filename: "p315-4.1.0.fw".to_string(),
                    checksum: String::new(),
                },
                FirmwareEntry {
                    model: "P320".to_string(),
                    version: "4.1.0".to_string(),
                    filename: "p320-4.1.0.fw".to_string(),
                    checksum: String::new(),
                },
                FirmwareEntry {
                    model: "P325".to_string(),
                    version: "4.1.0".to_string(),
                    filename: "p325-4.1.0.fw".to_string(),
                    checksum: String::new(),
                },
                FirmwareEntry {
                    model: "P330".to_string(),
                    version: "4.1.0".to_string(),
                    filename: "p330-4.1.0.fw".to_string(),
                    checksum: String::new(),
                },
                FirmwareEntry {
                    model: "P370".to_string(),
                    version: "4.1.0".to_string(),
                    filename: "p370-4.1.0.fw".to_string(),
                    checksum: String::new(),
                },
            ],
        }
    }

    /// Build a lookup map: model -> FirmwareEntry.
    pub fn by_model(&self) -> HashMap<String, FirmwareEntry> {
        self.firmware
            .iter()
            .map(|e| (e.model.clone(), e.clone()))
            .collect()
    }
}

/// Phone device store backed by the API and cached in Redis.
pub struct DeviceStore {
    http_client: reqwest::Client,
    redis_client: redis::Client,
    redis_conn: Option<redis::aio::MultiplexedConnection>,
    api_url: String,
    cache_ttl: u64,
}

impl DeviceStore {
    pub async fn new(api_url: &str, redis_url: &str, cache_ttl: u64) -> Result<Self> {
        let http_client = reqwest::Client::builder()
            .timeout(std::time::Duration::from_secs(10))
            .build()
            .context("failed to create HTTP client")?;

        let redis_client = redis::Client::open(redis_url)
            .with_context(|| format!("failed to create Redis client for {}", redis_url))?;

        let redis_conn = redis_client
            .get_multiplexed_async_connection()
            .await
            .with_context(|| "failed to connect to Redis")?;

        info!("device store initialized (API: {}, Redis: {})", api_url, redis_url);

        Ok(DeviceStore {
            http_client,
            redis_client,
            redis_conn: Some(redis_conn),
            api_url: api_url.trim_end_matches('/').to_string(),
            cache_ttl,
        })
    }

    /// Ensure Redis connection is alive.
    async fn ensure_redis(&mut self) -> Result<&mut redis::aio::MultiplexedConnection> {
        if self.redis_conn.is_none() {
            let conn = self
                .redis_client
                .get_multiplexed_async_connection()
                .await
                .context("failed to reconnect to Redis")?;
            self.redis_conn = Some(conn);
            info!("reconnected to Redis");
        }
        Ok(self.redis_conn.as_mut().unwrap())
    }

    /// Check in a phone with the API and update Redis tracking.
    pub async fn checkin(&mut self, req: &CheckinRequest) -> Result<Phone> {
        let mac = normalize_mac(&req.mac_address);
        let cache_ttl = self.cache_ttl;

        // POST to API
        let url = format!("{}/api/v1/devices/checkin", self.api_url);
        let api_result = self
            .http_client
            .post(&url)
            .json(req)
            .send()
            .await;

        let phone = match api_result {
            Ok(response) if response.status().is_success() => {
                match response.json::<Phone>().await {
                    Ok(phone) => {
                        debug!(mac = %mac, "phone check-in via API succeeded");
                        phone
                    }
                    Err(e) => {
                        warn!(mac = %mac, error = %e, "failed to parse API check-in response, using local data");
                        self.build_local_phone(req)
                    }
                }
            }
            Ok(response) => {
                warn!(mac = %mac, status = %response.status(), "API check-in returned error, using local data");
                self.build_local_phone(req)
            }
            Err(e) => {
                warn!(mac = %mac, error = %e, "API check-in failed, using local data");
                self.build_local_phone(req)
            }
        };

        // Update last-seen in Redis
        if let Ok(conn) = self.ensure_redis().await {
            let now = now_epoch_secs();
            let key = format!("np:phone:lastseen:{}", mac);
            let _: std::result::Result<(), _> = conn.set_ex(&key, now, cache_ttl * 5).await;

            // Cache the phone data in Redis
            let cache_key = format!("np:phone:cache:{}", mac);
            if let Ok(json) = serde_json::to_string(&phone) {
                let _: std::result::Result<(), _> = conn.set_ex(&cache_key, json, cache_ttl).await;
            }
        }

        Ok(phone)
    }

    /// Look up a phone by MAC, first checking Redis cache, then API.
    pub async fn get_by_mac(&mut self, mac: &str) -> Result<Option<Phone>> {
        let mac = normalize_mac(mac);
        let cache_ttl = self.cache_ttl;

        // Check Redis cache first
        if let Ok(conn) = self.ensure_redis().await {
            let cache_key = format!("np:phone:cache:{}", mac);
            let cached: std::result::Result<Option<String>, _> = conn.get(&cache_key).await;
            if let Ok(Some(json)) = cached {
                if let Ok(phone) = serde_json::from_str::<Phone>(&json) {
                    debug!(mac = %mac, "phone found in Redis cache");
                    return Ok(Some(phone));
                }
            }
        }

        // Fall back to API
        let url = format!("{}/api/v1/devices/by-mac/{}", self.api_url, mac);
        match self.http_client.get(&url).send().await {
            Ok(response) if response.status().is_success() => {
                match response.json::<Phone>().await {
                    Ok(phone) => {
                        // Cache in Redis
                        if let Ok(conn) = self.ensure_redis().await {
                            let cache_key = format!("np:phone:cache:{}", mac);
                            if let Ok(json) = serde_json::to_string(&phone) {
                                let _: std::result::Result<(), _> =
                                    conn.set_ex(&cache_key, json, cache_ttl).await;
                            }
                        }
                        Ok(Some(phone))
                    }
                    Err(e) => {
                        warn!(mac = %mac, error = %e, "failed to parse API device response");
                        Ok(None)
                    }
                }
            }
            Ok(response) if response.status() == reqwest::StatusCode::NOT_FOUND => Ok(None),
            Ok(response) => {
                warn!(mac = %mac, status = %response.status(), "API device lookup failed");
                Ok(None)
            }
            Err(e) => {
                warn!(mac = %mac, error = %e, "API device lookup request failed");
                Ok(None)
            }
        }
    }

    /// Update last-seen timestamp for a MAC in Redis.
    pub async fn update_last_seen(&mut self, mac: &str) -> Result<()> {
        let mac = normalize_mac(mac);
        let cache_ttl = self.cache_ttl;
        if let Ok(conn) = self.ensure_redis().await {
            let now = now_epoch_secs();
            let key = format!("np:phone:lastseen:{}", mac);
            let _: () = conn
                .set_ex(&key, now, cache_ttl * 5)
                .await
                .context("failed to update last-seen in Redis")?;
        }
        Ok(())
    }

    /// Get all tracked phone MACs and their last-seen timestamps from Redis.
    /// Uses SCAN to find all np:phone:lastseen:* keys.
    pub async fn get_all_last_seen(&mut self) -> Result<Vec<(String, u64)>> {
        let conn = self.ensure_redis().await?;
        let pattern = "np:phone:lastseen:*";

        // Use KEYS for simplicity (SCAN would be better at scale)
        let keys: Vec<String> = redis::cmd("KEYS")
            .arg(pattern)
            .query_async(conn)
            .await
            .unwrap_or_default();

        let mut results = Vec::new();
        for key in keys {
            let mac = key
                .strip_prefix("np:phone:lastseen:")
                .unwrap_or(&key)
                .to_string();
            let ts: Option<u64> = conn.get(&key).await.unwrap_or(None);
            if let Some(ts) = ts {
                results.push((mac, ts));
            }
        }

        Ok(results)
    }

    /// Check Redis connectivity.
    pub async fn check_redis(&mut self) -> bool {
        match self.ensure_redis().await {
            Ok(conn) => {
                let result: std::result::Result<String, _> =
                    redis::cmd("PING").query_async(conn).await;
                result.is_ok()
            }
            Err(_) => false,
        }
    }

    /// Check API connectivity.
    pub async fn check_api(&self) -> bool {
        let url = format!("{}/health", self.api_url);
        match self.http_client.get(&url).send().await {
            Ok(r) => r.status().is_success(),
            Err(_) => false,
        }
    }

    /// Build a local phone record when API is unavailable.
    fn build_local_phone(&self, req: &CheckinRequest) -> Phone {
        let now = now_epoch_secs();
        Phone {
            mac_address: normalize_mac(&req.mac_address),
            model: req.model.clone(),
            firmware_version: req.firmware_version.clone(),
            ip_address: Some(req.ip_address.clone()),
            extension: None,
            tenant_id: None,
            registered_at: Some(now),
            last_seen: Some(now),
        }
    }
}

/// Normalize MAC address to lowercase colon-separated format.
pub fn normalize_mac(mac: &str) -> String {
    let clean: String = mac
        .chars()
        .filter(|c| c.is_ascii_hexdigit())
        .collect::<String>()
        .to_lowercase();

    if clean.len() == 12 {
        format!(
            "{}:{}:{}:{}:{}:{}",
            &clean[0..2],
            &clean[2..4],
            &clean[4..6],
            &clean[6..8],
            &clean[8..10],
            &clean[10..12]
        )
    } else {
        clean
    }
}

fn now_epoch_secs() -> u64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_normalize_mac() {
        assert_eq!(normalize_mac("AA:BB:CC:DD:EE:FF"), "aa:bb:cc:dd:ee:ff");
        assert_eq!(normalize_mac("AABBCCDDEEFF"), "aa:bb:cc:dd:ee:ff");
        assert_eq!(normalize_mac("aa-bb-cc-dd-ee-ff"), "aa:bb:cc:dd:ee:ff");
    }

    #[test]
    fn test_firmware_manifest_default() {
        let manifest = FirmwareManifest::load_from_file("/nonexistent/manifest.json");
        let by_model = manifest.by_model();
        assert!(by_model.contains_key("P310"));
        assert!(by_model.contains_key("P370"));
        assert_eq!(by_model["P310"].version, "4.1.0");
    }

    #[test]
    fn test_firmware_manifest_parse() {
        let json = r#"{
            "firmware": [
                {"model": "P310", "version": "5.0.0", "filename": "p310-5.0.0.fw", "checksum": "abc123"},
                {"model": "P315", "version": "5.0.0", "filename": "p315-5.0.0.fw", "checksum": "def456"}
            ]
        }"#;
        let manifest: FirmwareManifest = serde_json::from_str(json).unwrap();
        let by_model = manifest.by_model();
        assert_eq!(by_model["P310"].version, "5.0.0");
        assert_eq!(by_model["P310"].checksum, "abc123");
    }
}
