use std::collections::HashMap;
use std::sync::Arc;

use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use tokio::sync::RwLock;
use tracing::{info, warn};

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
}

/// Emergency routing engine.
pub struct EmergencyRouter {
    routes: Arc<RwLock<Vec<PsapRoute>>>,
    default_trunk: String,
}

impl EmergencyRouter {
    pub fn new(default_trunk: String) -> Self {
        EmergencyRouter {
            routes: Arc::new(RwLock::new(Vec::new())),
            default_trunk,
        }
    }

    /// Load PSAP routes from a JSON file.
    pub async fn load_routes(&self, path: &str) -> Result<()> {
        match tokio::fs::read_to_string(path).await {
            Ok(contents) => {
                let routes: Vec<PsapRoute> =
                    serde_json::from_str(&contents).context("failed to parse PSAP routes JSON")?;

                let count = routes.len();
                *self.routes.write().await = routes;
                info!(count = count, path = path, "loaded PSAP routes");
                Ok(())
            }
            Err(e) => {
                warn!(
                    error = %e,
                    path = path,
                    "PSAP routes file not found, using default routing"
                );
                Ok(())
            }
        }
    }

    /// Route an emergency call based on the caller's state/location.
    pub async fn route_call(
        &self,
        extension: &str,
        tenant_id: &str,
        state_code: Option<&str>,
    ) -> RoutingResult {
        let routes = self.routes.read().await;

        // Find matching PSAP route by state
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
                "routed emergency call to PSAP"
            );

            RoutingResult {
                psap_id: route.psap_id.clone(),
                psap_name: route.name.clone(),
                trunk: route.trunk.clone(),
                extension: extension.to_string(),
                tenant_id: tenant_id.to_string(),
            }
        } else {
            // Default routing
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
            }
        }
    }

    /// Add or update a PSAP route.
    pub async fn add_route(&self, route: PsapRoute) {
        let mut routes = self.routes.write().await;
        // Replace existing route with same ID
        routes.retain(|r| r.psap_id != route.psap_id);
        routes.push(route);
        routes.sort_by_key(|r| r.priority);
    }

    /// Get all PSAP routes.
    pub async fn get_routes(&self) -> Vec<PsapRoute> {
        self.routes.read().await.clone()
    }
}

/// Location store for per-extension E911 locations.
pub struct LocationStore {
    locations: Arc<RwLock<HashMap<String, super::pidf_lo::ExtensionLocation>>>,
}

impl LocationStore {
    pub fn new() -> Self {
        LocationStore {
            locations: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    /// Create or update a location for an extension.
    pub async fn set_location(&self, location: super::pidf_lo::ExtensionLocation) {
        let key = format!("{}:{}", location.tenant_id, location.extension);
        self.locations.write().await.insert(key, location);
    }

    /// Get location for an extension.
    pub async fn get_location(
        &self,
        extension: &str,
        tenant_id: &str,
    ) -> Option<super::pidf_lo::ExtensionLocation> {
        let key = format!("{}:{}", tenant_id, extension);
        self.locations.read().await.get(&key).cloned()
    }

    /// List all locations.
    pub async fn list_locations(&self) -> Vec<super::pidf_lo::ExtensionLocation> {
        self.locations.read().await.values().cloned().collect()
    }

    /// Remove a location.
    pub async fn remove_location(&self, extension: &str, tenant_id: &str) -> bool {
        let key = format!("{}:{}", tenant_id, extension);
        self.locations.write().await.remove(&key).is_some()
    }
}
