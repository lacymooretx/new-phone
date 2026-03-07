use std::sync::Arc;
use std::sync::atomic::{AtomicU64, Ordering};

use anyhow::{Context, Result};
use redis::AsyncCommands;
use serde::{Deserialize, Serialize};
use tokio::sync::RwLock;
use tracing::{debug, error, info, warn};

use crate::pidf_lo::ExtensionLocation;

// ---------------------------------------------------------------------------
// PSAP route types
// ---------------------------------------------------------------------------

/// PSAP (Public Safety Answering Point) route entry.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PsapRoute {
    pub psap_id: String,
    pub name: String,
    /// Trunk or gateway to route 911 calls through
    pub trunk: String,
    /// Geographic coverage: state codes (e.g., ["CA", "NV"])
    pub states: Vec<String>,
    /// Priority (lower = higher priority)
    pub priority: u32,
}

/// Result of emergency call routing.
#[derive(Debug, Clone, Serialize)]
pub struct RoutingResult {
    pub psap_id: String,
    pub psap_name: String,
    pub trunk: String,
    pub extension: String,
    pub tenant_id: String,
    /// If the carrier API provided routing, this is true
    pub carrier_routed: bool,
}

// ---------------------------------------------------------------------------
// Emergency Router — PSAP route lookup with API + file fallback + hot-reload
// ---------------------------------------------------------------------------

pub struct EmergencyRouter {
    routes: Arc<RwLock<Vec<PsapRoute>>>,
    default_trunk: String,
    route_count: AtomicU64,
    routes_loaded: std::sync::atomic::AtomicBool,
}

impl EmergencyRouter {
    pub fn new(default_trunk: String) -> Self {
        EmergencyRouter {
            routes: Arc::new(RwLock::new(Vec::new())),
            default_trunk,
            route_count: AtomicU64::new(0),
            routes_loaded: std::sync::atomic::AtomicBool::new(false),
        }
    }

    /// Load PSAP routes from the control-plane API, falling back to a local JSON file.
    pub async fn load_routes_from_api_or_file(
        &self,
        http_client: &reqwest::Client,
        api_url: &str,
        internal_api_key: &str,
        file_path: &str,
    ) -> Result<()> {
        // Try API first
        match self
            .fetch_routes_from_api(http_client, api_url, internal_api_key)
            .await
        {
            Ok(routes) => {
                let count = routes.len();
                *self.routes.write().await = routes;
                self.route_count.store(count as u64, Ordering::Relaxed);
                self.routes_loaded
                    .store(true, std::sync::atomic::Ordering::Relaxed);
                info!(count = count, source = "api", "loaded PSAP routes from API");
                return Ok(());
            }
            Err(e) => {
                warn!(
                    error = %e,
                    "failed to load PSAP routes from API, falling back to file"
                );
            }
        }

        // Fallback to local file
        self.load_routes_from_file(file_path).await
    }

    /// Load PSAP routes from a JSON file.
    pub async fn load_routes_from_file(&self, path: &str) -> Result<()> {
        match tokio::fs::read_to_string(path).await {
            Ok(contents) => {
                let routes: Vec<PsapRoute> =
                    serde_json::from_str(&contents).context("failed to parse PSAP routes JSON")?;

                let count = routes.len();
                *self.routes.write().await = routes;
                self.route_count.store(count as u64, Ordering::Relaxed);
                self.routes_loaded
                    .store(true, std::sync::atomic::Ordering::Relaxed);
                info!(count = count, path = path, "loaded PSAP routes from file");
                Ok(())
            }
            Err(e) => {
                warn!(
                    error = %e,
                    path = path,
                    "PSAP routes file not found, using default routing only"
                );
                // Mark as loaded even if empty — default trunk is always available
                self.routes_loaded
                    .store(true, std::sync::atomic::Ordering::Relaxed);
                Ok(())
            }
        }
    }

    /// Fetch PSAP routes from the control-plane API.
    async fn fetch_routes_from_api(
        &self,
        client: &reqwest::Client,
        api_url: &str,
        internal_api_key: &str,
    ) -> Result<Vec<PsapRoute>> {
        let url = format!("{}/api/v1/e911/psap-routes", api_url);
        let mut req = client.get(&url);
        if !internal_api_key.is_empty() {
            req = req.header("X-Internal-Key", internal_api_key);
        }

        let resp = req.send().await.context("PSAP routes API request failed")?;

        if !resp.status().is_success() {
            let status = resp.status();
            let body = resp.text().await.unwrap_or_default();
            return Err(anyhow::anyhow!(
                "PSAP routes API returned {}: {}",
                status,
                body
            ));
        }

        let routes: Vec<PsapRoute> = resp
            .json()
            .await
            .context("failed to parse PSAP routes API response")?;

        Ok(routes)
    }

    /// Route an emergency call based on the caller's state/location.
    /// First tries carrier API routing if available, then falls back to local PSAP table.
    pub async fn route_call(
        &self,
        extension: &str,
        tenant_id: &str,
        state_code: Option<&str>,
        carrier: Option<&CarrierApiClient>,
        location: Option<&ExtensionLocation>,
    ) -> RoutingResult {
        // Try carrier API routing first
        if let Some(carrier_client) = carrier {
            if let Some(loc) = location {
                match carrier_client.query_routing(loc).await {
                    Ok(Some(result)) => {
                        info!(
                            psap_id = %result.psap_id,
                            trunk = %result.trunk,
                            extension = extension,
                            "carrier API routed emergency call"
                        );
                        return RoutingResult {
                            psap_id: result.psap_id,
                            psap_name: result.psap_name,
                            trunk: result.trunk,
                            extension: extension.to_string(),
                            tenant_id: tenant_id.to_string(),
                            carrier_routed: true,
                        };
                    }
                    Ok(None) => {
                        warn!(
                            extension = extension,
                            "carrier API returned no routing, falling back to local PSAP table"
                        );
                    }
                    Err(e) => {
                        error!(
                            error = %e,
                            extension = extension,
                            "carrier API routing failed, falling back to local PSAP table"
                        );
                    }
                }
            }
        }

        // Local PSAP table routing
        let routes = self.routes.read().await;

        let matched = if let Some(state) = state_code {
            routes
                .iter()
                .filter(|r| r.states.iter().any(|s| s.eq_ignore_ascii_case(state)))
                .min_by_key(|r| r.priority)
        } else {
            None
        };

        if let Some(route) = matched {
            info!(
                psap_id = %route.psap_id,
                trunk = %route.trunk,
                extension = extension,
                "routed emergency call to PSAP via local table"
            );

            RoutingResult {
                psap_id: route.psap_id.clone(),
                psap_name: route.name.clone(),
                trunk: route.trunk.clone(),
                extension: extension.to_string(),
                tenant_id: tenant_id.to_string(),
                carrier_routed: false,
            }
        } else {
            warn!(
                extension = extension,
                state = ?state_code,
                "no specific PSAP route found, using default trunk"
            );

            RoutingResult {
                psap_id: "default".to_string(),
                psap_name: "Default PSAP".to_string(),
                trunk: self.default_trunk.clone(),
                extension: extension.to_string(),
                tenant_id: tenant_id.to_string(),
                carrier_routed: false,
            }
        }
    }

    /// Add or update a PSAP route.
    pub async fn add_route(&self, route: PsapRoute) {
        let mut routes = self.routes.write().await;
        routes.retain(|r| r.psap_id != route.psap_id);
        routes.push(route);
        routes.sort_by_key(|r| r.priority);
        self.route_count
            .store(routes.len() as u64, Ordering::Relaxed);
    }

    /// Get all PSAP routes.
    pub async fn get_routes(&self) -> Vec<PsapRoute> {
        self.routes.read().await.clone()
    }

    /// Returns the number of loaded PSAP routes.
    pub fn route_count(&self) -> u64 {
        self.route_count.load(Ordering::Relaxed)
    }

    /// Returns whether routes have been loaded at least once.
    pub fn routes_loaded(&self) -> bool {
        self.routes_loaded
            .load(std::sync::atomic::Ordering::Relaxed)
    }
}

// ---------------------------------------------------------------------------
// Location Store — API-backed with Redis cache
// ---------------------------------------------------------------------------

pub struct LocationStore {
    http_client: reqwest::Client,
    api_url: String,
    internal_api_key: String,
    redis_client: redis::Client,
    cache_ttl_secs: u64,
    /// Cache hit/miss counters for health reporting
    cache_hits: AtomicU64,
    cache_misses: AtomicU64,
}

impl LocationStore {
    pub fn new(
        api_url: String,
        internal_api_key: String,
        redis_url: &str,
        cache_ttl_secs: u64,
    ) -> Result<Self> {
        let redis_client =
            redis::Client::open(redis_url).context("failed to create Redis client for e911")?;
        let http_client = reqwest::Client::new();

        Ok(LocationStore {
            http_client,
            api_url,
            internal_api_key,
            redis_client,
            cache_ttl_secs,
            cache_hits: AtomicU64::new(0),
            cache_misses: AtomicU64::new(0),
        })
    }

    fn cache_key(tenant_id: &str, extension: &str) -> String {
        format!("np:e911:loc:{}:{}", tenant_id, extension)
    }

    /// Get location — Redis cache first, then API, then None.
    pub async fn get_location(
        &self,
        extension: &str,
        tenant_id: &str,
    ) -> Option<ExtensionLocation> {
        let key = Self::cache_key(tenant_id, extension);

        // Try Redis cache
        if let Ok(cached) = self.get_from_cache(&key).await {
            if let Some(location) = cached {
                self.cache_hits.fetch_add(1, Ordering::Relaxed);
                debug!(extension = extension, tenant_id = tenant_id, "location cache hit");
                return Some(location);
            }
        }

        self.cache_misses.fetch_add(1, Ordering::Relaxed);

        // Cache miss — fetch from API
        match self.fetch_location_from_api(extension, tenant_id).await {
            Ok(Some(location)) => {
                // Populate cache
                if let Err(e) = self.set_in_cache(&key, &location).await {
                    warn!(error = %e, "failed to cache location in Redis");
                }
                Some(location)
            }
            Ok(None) => None,
            Err(e) => {
                error!(
                    error = %e,
                    extension = extension,
                    tenant_id = tenant_id,
                    "failed to fetch location from API"
                );
                None
            }
        }
    }

    /// Create or update a location — push to API, then cache in Redis.
    pub async fn set_location(&self, location: ExtensionLocation) -> Result<()> {
        // Push to control-plane API
        self.push_location_to_api(&location).await?;

        // Update Redis cache
        let key = Self::cache_key(&location.tenant_id, &location.extension);
        if let Err(e) = self.set_in_cache(&key, &location).await {
            warn!(error = %e, "failed to cache updated location in Redis");
        }

        Ok(())
    }

    /// Remove a location — delete via API, then evict from cache.
    pub async fn remove_location(&self, extension: &str, tenant_id: &str) -> Result<bool> {
        let deleted = self
            .delete_location_from_api(extension, tenant_id)
            .await?;

        // Evict cache
        let key = Self::cache_key(tenant_id, extension);
        if let Err(e) = self.evict_cache(&key).await {
            warn!(error = %e, "failed to evict location from Redis cache");
        }

        Ok(deleted)
    }

    /// List all locations for a tenant — always from API (not cached).
    pub async fn list_locations(&self, tenant_id: &str) -> Result<Vec<ExtensionLocation>> {
        self.fetch_locations_list_from_api(tenant_id).await
    }

    // -- Cache helpers -------------------------------------------------------

    async fn get_from_cache(&self, key: &str) -> Result<Option<ExtensionLocation>> {
        let mut conn = self
            .redis_client
            .get_multiplexed_async_connection()
            .await
            .context("Redis connect failed")?;

        let val: Option<String> = conn.get(key).await.context("Redis GET failed")?;
        match val {
            Some(json_str) => {
                let loc: ExtensionLocation =
                    serde_json::from_str(&json_str).context("failed to deserialize cached location")?;
                Ok(Some(loc))
            }
            None => Ok(None),
        }
    }

    async fn set_in_cache(&self, key: &str, location: &ExtensionLocation) -> Result<()> {
        let mut conn = self
            .redis_client
            .get_multiplexed_async_connection()
            .await
            .context("Redis connect failed")?;

        let json_str =
            serde_json::to_string(location).context("failed to serialize location for cache")?;

        conn.set_ex::<_, _, ()>(key, &json_str, self.cache_ttl_secs)
            .await
            .context("Redis SETEX failed")?;

        debug!(key = key, ttl = self.cache_ttl_secs, "location cached in Redis");
        Ok(())
    }

    async fn evict_cache(&self, key: &str) -> Result<()> {
        let mut conn = self
            .redis_client
            .get_multiplexed_async_connection()
            .await
            .context("Redis connect failed")?;

        conn.del::<_, ()>(key)
            .await
            .context("Redis DEL failed")?;
        Ok(())
    }

    // -- API helpers ---------------------------------------------------------

    async fn fetch_location_from_api(
        &self,
        extension: &str,
        tenant_id: &str,
    ) -> Result<Option<ExtensionLocation>> {
        let url = format!(
            "{}/api/v1/e911/locations/{}",
            self.api_url, extension
        );

        let mut req = self.http_client.get(&url);
        req = req.header("X-Tenant-ID", tenant_id);
        if !self.internal_api_key.is_empty() {
            req = req.header("X-Internal-Key", &self.internal_api_key);
        }

        let resp = req.send().await.context("location API request failed")?;

        if resp.status() == reqwest::StatusCode::NOT_FOUND {
            return Ok(None);
        }
        if !resp.status().is_success() {
            let status = resp.status();
            let body = resp.text().await.unwrap_or_default();
            return Err(anyhow::anyhow!(
                "location API returned {}: {}",
                status,
                body
            ));
        }

        let location: ExtensionLocation = resp
            .json()
            .await
            .context("failed to parse location API response")?;
        Ok(Some(location))
    }

    async fn push_location_to_api(&self, location: &ExtensionLocation) -> Result<()> {
        let url = format!(
            "{}/api/v1/e911/locations/{}",
            self.api_url, location.extension
        );

        let mut req = self.http_client.put(&url);
        req = req.header("X-Tenant-ID", &location.tenant_id);
        if !self.internal_api_key.is_empty() {
            req = req.header("X-Internal-Key", &self.internal_api_key);
        }

        let resp = req
            .json(location)
            .send()
            .await
            .context("location API PUT request failed")?;

        if !resp.status().is_success() {
            let status = resp.status();
            let body = resp.text().await.unwrap_or_default();
            return Err(anyhow::anyhow!(
                "location API PUT returned {}: {}",
                status,
                body
            ));
        }

        debug!(
            extension = %location.extension,
            tenant_id = %location.tenant_id,
            "location pushed to API"
        );
        Ok(())
    }

    async fn delete_location_from_api(
        &self,
        extension: &str,
        tenant_id: &str,
    ) -> Result<bool> {
        let url = format!("{}/api/v1/e911/locations/{}", self.api_url, extension);

        let mut req = self.http_client.delete(&url);
        req = req.header("X-Tenant-ID", tenant_id);
        if !self.internal_api_key.is_empty() {
            req = req.header("X-Internal-Key", &self.internal_api_key);
        }

        let resp = req.send().await.context("location API DELETE request failed")?;

        if resp.status() == reqwest::StatusCode::NOT_FOUND {
            return Ok(false);
        }
        if !resp.status().is_success() {
            let status = resp.status();
            let body = resp.text().await.unwrap_or_default();
            return Err(anyhow::anyhow!(
                "location API DELETE returned {}: {}",
                status,
                body
            ));
        }

        Ok(true)
    }

    async fn fetch_locations_list_from_api(
        &self,
        tenant_id: &str,
    ) -> Result<Vec<ExtensionLocation>> {
        let url = format!("{}/api/v1/e911/locations", self.api_url);

        let mut req = self.http_client.get(&url);
        req = req.header("X-Tenant-ID", tenant_id);
        if !self.internal_api_key.is_empty() {
            req = req.header("X-Internal-Key", &self.internal_api_key);
        }

        let resp = req.send().await.context("location list API request failed")?;

        if !resp.status().is_success() {
            let status = resp.status();
            let body = resp.text().await.unwrap_or_default();
            return Err(anyhow::anyhow!(
                "location list API returned {}: {}",
                status,
                body
            ));
        }

        let locations: Vec<ExtensionLocation> = resp
            .json()
            .await
            .context("failed to parse location list API response")?;
        Ok(locations)
    }

    /// Check if Redis is reachable.
    pub async fn redis_healthy(&self) -> bool {
        match self.redis_client.get_multiplexed_async_connection().await {
            Ok(mut conn) => {
                let result: Result<String, _> = redis::cmd("PING").query_async(&mut conn).await;
                result.is_ok()
            }
            Err(_) => false,
        }
    }

    /// Return cache statistics for health reporting.
    pub fn cache_stats(&self) -> (u64, u64) {
        (
            self.cache_hits.load(Ordering::Relaxed),
            self.cache_misses.load(Ordering::Relaxed),
        )
    }
}

// ---------------------------------------------------------------------------
// Carrier API Client — provision locations and query routing from E911 carrier
// ---------------------------------------------------------------------------

/// Carrier routing result returned by the E911 carrier API.
#[derive(Debug, Clone, Deserialize)]
pub struct CarrierRoutingResult {
    pub psap_id: String,
    pub psap_name: String,
    pub trunk: String,
}

/// Response from carrier location provisioning.
#[derive(Debug, Clone, Deserialize)]
struct CarrierProvisionResponse {
    #[serde(default)]
    status: String,
    #[serde(default)]
    location_id: Option<String>,
}

/// Response from carrier routing query.
#[derive(Debug, Clone, Deserialize)]
struct CarrierRoutingResponse {
    #[serde(default)]
    psap_id: Option<String>,
    #[serde(default)]
    psap_name: Option<String>,
    #[serde(default)]
    trunk: Option<String>,
}

pub struct CarrierApiClient {
    http_client: reqwest::Client,
    api_url: String,
    api_key: String,
}

impl CarrierApiClient {
    pub fn new(api_url: String, api_key: String) -> Self {
        CarrierApiClient {
            http_client: reqwest::Client::new(),
            api_url,
            api_key,
        }
    }

    /// Return the carrier API base URL (for logging/diagnostics).
    pub fn api_url(&self) -> &str {
        &self.api_url
    }

    /// Provision (create/update) a location with the carrier's E911 service.
    /// Called whenever a location is created or updated locally.
    pub async fn provision_location(&self, location: &ExtensionLocation) -> Result<()> {
        let url = format!("{}/v1/e911/locations", self.api_url);

        let payload = serde_json::json!({
            "caller_id": location.extension,
            "address": {
                "country": location.civic_address.country,
                "state": location.civic_address.state,
                "county": location.civic_address.county,
                "city": location.civic_address.city,
                "street": location.civic_address.street,
                "house_number": location.civic_address.house_number,
                "house_number_suffix": location.civic_address.house_number_suffix,
                "floor": location.civic_address.floor,
                "room": location.civic_address.room,
                "postal_code": location.civic_address.postal_code,
                "location_name": location.civic_address.location_name,
            },
            "geo": location.geo_coordinates.as_ref().map(|g| serde_json::json!({
                "latitude": g.latitude,
                "longitude": g.longitude,
                "altitude": g.altitude,
            })),
        });

        let resp = self
            .http_client
            .post(&url)
            .header("Authorization", format!("Bearer {}", self.api_key))
            .header("Content-Type", "application/json")
            .json(&payload)
            .send()
            .await
            .context("carrier E911 location provision request failed")?;

        let status_code = resp.status();
        if !status_code.is_success() {
            let body = resp.text().await.unwrap_or_default();
            error!(
                status = %status_code,
                body = %body,
                extension = %location.extension,
                "carrier E911 location provision failed"
            );
            return Err(anyhow::anyhow!(
                "carrier E911 API returned {}: {}",
                status_code,
                body
            ));
        }

        let resp_body: CarrierProvisionResponse = resp
            .json()
            .await
            .context("failed to parse carrier provision response")?;

        info!(
            extension = %location.extension,
            status = %resp_body.status,
            location_id = ?resp_body.location_id,
            "location provisioned with carrier"
        );

        Ok(())
    }

    /// Query the carrier for emergency call routing based on a location.
    pub async fn query_routing(
        &self,
        location: &ExtensionLocation,
    ) -> Result<Option<CarrierRoutingResult>> {
        let url = format!("{}/v1/e911/routing", self.api_url);

        let payload = serde_json::json!({
            "caller_id": location.extension,
            "address": {
                "country": location.civic_address.country,
                "state": location.civic_address.state,
                "city": location.civic_address.city,
                "postal_code": location.civic_address.postal_code,
            },
            "geo": location.geo_coordinates.as_ref().map(|g| serde_json::json!({
                "latitude": g.latitude,
                "longitude": g.longitude,
            })),
        });

        let resp = self
            .http_client
            .post(&url)
            .header("Authorization", format!("Bearer {}", self.api_key))
            .header("Content-Type", "application/json")
            .json(&payload)
            .send()
            .await
            .context("carrier E911 routing query failed")?;

        let status_code = resp.status();
        if !status_code.is_success() {
            let body = resp.text().await.unwrap_or_default();
            return Err(anyhow::anyhow!(
                "carrier routing API returned {}: {}",
                status_code,
                body
            ));
        }

        let resp_body: CarrierRoutingResponse = resp
            .json()
            .await
            .context("failed to parse carrier routing response")?;

        match (resp_body.psap_id, resp_body.psap_name, resp_body.trunk) {
            (Some(psap_id), Some(psap_name), Some(trunk)) => Ok(Some(CarrierRoutingResult {
                psap_id,
                psap_name,
                trunk,
            })),
            _ => Ok(None),
        }
    }

    /// Check if the carrier API is reachable.
    pub async fn health_check(&self) -> bool {
        let url = format!("{}/v1/health", self.api_url);
        match self
            .http_client
            .get(&url)
            .header("Authorization", format!("Bearer {}", self.api_key))
            .timeout(std::time::Duration::from_secs(5))
            .send()
            .await
        {
            Ok(resp) => resp.status().is_success(),
            Err(_) => false,
        }
    }
}

// ---------------------------------------------------------------------------
// ESL (Event Socket Layer) helper for FreeSWITCH emergency call origination
// ---------------------------------------------------------------------------

/// Originate an emergency call via FreeSWITCH ESL.
///
/// This sends the call to the PSAP trunk with PIDF-LO SIP headers attached.
pub async fn esl_originate_emergency_call(
    esl_host: &str,
    esl_port: u16,
    esl_password: &str,
    call_uuid: &str,
    trunk: &str,
    extension: &str,
    sip_domain: &str,
    pidf_lo_url: &str,
) -> Result<()> {
    let esl_addr = format!("{}:{}", esl_host, esl_port);

    let mut stream = tokio::net::TcpStream::connect(&esl_addr)
        .await
        .context("failed to connect to FreeSWITCH ESL")?;

    use tokio::io::{AsyncReadExt, AsyncWriteExt};

    let mut buf = [0u8; 4096];

    // Read greeting
    let _ = stream.read(&mut buf).await?;

    // Authenticate
    let auth = format!("auth {}\n\n", esl_password);
    stream.write_all(auth.as_bytes()).await?;
    let _ = stream.read(&mut buf).await?;

    // Set the Geolocation SIP header on the existing call channel so the
    // PSAP receives the PIDF-LO reference per RFC 6442.
    let set_header_cmd = format!(
        "api uuid_setvar {} sip_h_Geolocation <{}>;purpose=emergency;inserted-by=\"{}\" \n\n",
        call_uuid, pidf_lo_url, sip_domain
    );
    stream.write_all(set_header_cmd.as_bytes()).await?;
    let _ = stream.read(&mut buf).await?;

    // Transfer the call to the 911 trunk/gateway.
    // The trunk profile should be configured in FreeSWITCH to route to the
    // carrier's SIP endpoint (e.g., ClearlyIP E911 SBC).
    let transfer_cmd = format!(
        "api uuid_transfer {} 911 XML {} \n\n",
        call_uuid, trunk
    );
    stream.write_all(transfer_cmd.as_bytes()).await?;
    let _ = stream.read(&mut buf).await?;

    info!(
        call_uuid = call_uuid,
        trunk = trunk,
        extension = extension,
        "ESL emergency call routed to PSAP trunk"
    );

    Ok(())
}

/// Log an emergency call event to the control-plane API for audit trail.
pub async fn log_emergency_call_to_api(
    http_client: &reqwest::Client,
    api_url: &str,
    internal_api_key: &str,
    call_uuid: &str,
    extension: &str,
    tenant_id: &str,
    routing_result: &RoutingResult,
    location: Option<&ExtensionLocation>,
) -> Result<()> {
    let url = format!("{}/api/v1/e911/call-log", api_url);

    let payload = serde_json::json!({
        "call_uuid": call_uuid,
        "extension": extension,
        "tenant_id": tenant_id,
        "psap_id": routing_result.psap_id,
        "psap_name": routing_result.psap_name,
        "trunk": routing_result.trunk,
        "carrier_routed": routing_result.carrier_routed,
        "timestamp": now_epoch(),
        "location": location,
    });

    let mut req = http_client.post(&url);
    if !internal_api_key.is_empty() {
        req = req.header("X-Internal-Key", internal_api_key);
    }

    let resp = req
        .json(&payload)
        .send()
        .await
        .context("emergency call log API request failed")?;

    if !resp.status().is_success() {
        let status = resp.status();
        let body = resp.text().await.unwrap_or_default();
        warn!(
            status = %status,
            body = %body,
            call_uuid = call_uuid,
            "failed to log emergency call to API (non-fatal)"
        );
    } else {
        info!(call_uuid = call_uuid, "emergency call logged to API audit trail");
    }

    Ok(())
}

fn now_epoch() -> u64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs()
}
