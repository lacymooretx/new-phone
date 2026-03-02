use std::collections::HashMap;
use std::sync::Arc;

use anyhow::Result;
use serde::{Deserialize, Serialize};
use tokio::sync::RwLock;
use tracing::{info, warn};

use crate::providers::{MessageStatus, SendResult, SmsProvider};

/// Route configuration for a DID.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DidRoute {
    pub did: String,
    pub primary_provider: String,
    pub failover_provider: Option<String>,
}

/// SMS routing engine with provider failover.
pub struct SmsRouter {
    providers: HashMap<String, Arc<dyn SmsProvider>>,
    did_routes: Arc<RwLock<HashMap<String, DidRoute>>>,
    default_provider: String,
}

impl SmsRouter {
    pub fn new(default_provider: String) -> Self {
        SmsRouter {
            providers: HashMap::new(),
            did_routes: Arc::new(RwLock::new(HashMap::new())),
            default_provider,
        }
    }

    /// Register a provider.
    pub fn add_provider(&mut self, name: &str, provider: Arc<dyn SmsProvider>) {
        self.providers.insert(name.to_string(), provider);
        info!(provider = name, "SMS provider registered");
    }

    /// Set a DID route.
    pub async fn set_did_route(&self, route: DidRoute) {
        self.did_routes
            .write()
            .await
            .insert(route.did.clone(), route);
    }

    /// Send an SMS with automatic failover.
    pub async fn send(
        &self,
        from: &str,
        to: &str,
        body: &str,
        media_urls: &[String],
    ) -> Result<SendResult> {
        let routes = self.did_routes.read().await;
        let route = routes.get(from);

        let primary_name = route
            .map(|r| r.primary_provider.as_str())
            .unwrap_or(&self.default_provider);

        let failover_name = route.and_then(|r| r.failover_provider.as_deref());

        // Try primary provider
        if let Some(primary) = self.providers.get(primary_name) {
            match primary.send_sms(from, to, body, media_urls).await {
                Ok(result) => {
                    info!(
                        provider = primary_name,
                        message_id = %result.message_id,
                        "SMS sent via primary provider"
                    );
                    return Ok(result);
                }
                Err(e) => {
                    warn!(
                        provider = primary_name,
                        error = %e,
                        "primary provider failed, attempting failover"
                    );
                }
            }
        } else {
            warn!(
                provider = primary_name,
                "primary provider not found"
            );
        }

        // Try failover provider
        if let Some(failover_name) = failover_name {
            if let Some(failover) = self.providers.get(failover_name) {
                match failover.send_sms(from, to, body, media_urls).await {
                    Ok(result) => {
                        info!(
                            provider = failover_name,
                            message_id = %result.message_id,
                            "SMS sent via failover provider"
                        );
                        return Ok(result);
                    }
                    Err(e) => {
                        warn!(
                            provider = failover_name,
                            error = %e,
                            "failover provider also failed"
                        );
                        return Err(anyhow::anyhow!(
                            "all SMS providers failed. Primary: {}, Failover: {}",
                            primary_name,
                            failover_name
                        ));
                    }
                }
            }
        }

        Err(anyhow::anyhow!(
            "no available SMS provider for DID {}",
            from
        ))
    }

    /// Get delivery status from the appropriate provider.
    pub async fn get_status(
        &self,
        message_id: &str,
        provider_name: &str,
    ) -> Result<MessageStatus> {
        let provider = self
            .providers
            .get(provider_name)
            .ok_or_else(|| anyhow::anyhow!("provider {} not found", provider_name))?;

        provider.get_status(message_id).await
    }
}
