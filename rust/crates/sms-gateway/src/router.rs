use std::collections::HashMap;
use std::sync::Arc;
use std::time::Instant;

use anyhow::{Context, Result};
use redis::AsyncCommands;
use serde::{Deserialize, Serialize};
use tokio::sync::RwLock;
use tracing::{debug, info, warn};

use crate::providers::{MessageStatus, SendResult, SmsProvider};

/// Route configuration for a DID.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DidRoute {
    pub did: String,
    pub primary_provider: String,
    pub failover_provider: Option<String>,
}

/// Tracks failure state for a provider (for backoff/cooldown).
#[derive(Debug, Clone)]
struct ProviderHealth {
    consecutive_failures: u32,
    last_failure: Option<Instant>,
    in_cooldown: bool,
}

impl Default for ProviderHealth {
    fn default() -> Self {
        ProviderHealth {
            consecutive_failures: 0,
            last_failure: None,
            in_cooldown: false,
        }
    }
}

/// Stored mapping from our message_id to the provider that handled it.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MessageTracking {
    pub provider: String,
    pub provider_message_id: String,
}

/// SMS routing engine with provider failover and backoff.
pub struct SmsRouter {
    providers: HashMap<String, Arc<dyn SmsProvider>>,
    did_routes: Arc<RwLock<HashMap<String, DidRoute>>>,
    default_provider: String,
    redis_client: redis::Client,
    provider_health: Arc<RwLock<HashMap<String, ProviderHealth>>>,
    cooldown_secs: u64,
    failure_threshold: u32,
}

/// Redis key prefix for message tracking.
const MSG_TRACKING_PREFIX: &str = "np:sms:msg:";
/// TTL for message tracking entries (7 days).
const MSG_TRACKING_TTL_SECS: u64 = 7 * 24 * 3600;

impl SmsRouter {
    pub fn new(
        default_provider: String,
        redis_client: redis::Client,
        cooldown_secs: u64,
        failure_threshold: u32,
    ) -> Self {
        SmsRouter {
            providers: HashMap::new(),
            did_routes: Arc::new(RwLock::new(HashMap::new())),
            default_provider,
            redis_client,
            provider_health: Arc::new(RwLock::new(HashMap::new())),
            cooldown_secs,
            failure_threshold,
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

    /// Check if a provider is currently in cooldown.
    async fn is_provider_in_cooldown(&self, provider_name: &str) -> bool {
        let health = self.provider_health.read().await;
        if let Some(ph) = health.get(provider_name) {
            if ph.in_cooldown {
                if let Some(last_failure) = ph.last_failure {
                    let elapsed = last_failure.elapsed().as_secs();
                    if elapsed < self.cooldown_secs {
                        debug!(
                            provider = provider_name,
                            elapsed_secs = elapsed,
                            cooldown_secs = self.cooldown_secs,
                            "provider in cooldown"
                        );
                        return true;
                    }
                    // Cooldown has expired -- will be cleared on next success or send attempt
                }
            }
        }
        false
    }

    /// Record a provider failure.
    async fn record_failure(&self, provider_name: &str) {
        let mut health = self.provider_health.write().await;
        let ph = health
            .entry(provider_name.to_string())
            .or_insert_with(ProviderHealth::default);
        ph.consecutive_failures += 1;
        ph.last_failure = Some(Instant::now());

        if ph.consecutive_failures >= self.failure_threshold {
            ph.in_cooldown = true;
            warn!(
                provider = provider_name,
                consecutive_failures = ph.consecutive_failures,
                cooldown_secs = self.cooldown_secs,
                "provider entering cooldown after repeated failures"
            );
        }
    }

    /// Record a provider success (resets failure tracking).
    async fn record_success(&self, provider_name: &str) {
        let mut health = self.provider_health.write().await;
        if let Some(ph) = health.get_mut(provider_name) {
            if ph.consecutive_failures > 0 || ph.in_cooldown {
                info!(
                    provider = provider_name,
                    prev_failures = ph.consecutive_failures,
                    "provider recovered, resetting failure tracking"
                );
            }
            ph.consecutive_failures = 0;
            ph.last_failure = None;
            ph.in_cooldown = false;
        }
    }

    /// Store message_id -> provider mapping in Redis.
    async fn store_message_tracking(
        &self,
        message_id: &str,
        provider: &str,
        provider_message_id: &str,
    ) {
        let tracking = MessageTracking {
            provider: provider.to_string(),
            provider_message_id: provider_message_id.to_string(),
        };

        let json = match serde_json::to_string(&tracking) {
            Ok(j) => j,
            Err(e) => {
                warn!(error = %e, "failed to serialize message tracking");
                return;
            }
        };

        let key = format!("{}{}", MSG_TRACKING_PREFIX, message_id);
        match self.redis_client.get_multiplexed_async_connection().await {
            Ok(mut conn) => {
                let _: Result<(), _> = conn.set_ex(&key, &json, MSG_TRACKING_TTL_SECS).await;
                debug!(
                    message_id = message_id,
                    provider = provider,
                    provider_message_id = provider_message_id,
                    "stored message tracking in Redis"
                );
            }
            Err(e) => {
                warn!(error = %e, "failed to connect to Redis for message tracking");
            }
        }
    }

    /// Look up which provider handled a message.
    pub async fn lookup_message_tracking(
        &self,
        message_id: &str,
    ) -> Option<MessageTracking> {
        let key = format!("{}{}", MSG_TRACKING_PREFIX, message_id);
        let mut conn = self
            .redis_client
            .get_multiplexed_async_connection()
            .await
            .ok()?;
        let json: Option<String> = conn.get(&key).await.ok()?;
        let json = json?;
        serde_json::from_str(&json).ok()
    }

    /// Send an SMS with automatic failover and backoff.
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

        // Determine which provider to try first based on cooldown state.
        // If the primary is in cooldown, swap to failover immediately (if available).
        let primary_in_cooldown = self.is_provider_in_cooldown(primary_name).await;

        let (first_name, second_name) = if primary_in_cooldown {
            if let Some(fo) = failover_name {
                (fo, Some(primary_name))
            } else {
                // No failover; still try the primary even in cooldown
                (primary_name, None)
            }
        } else {
            (primary_name, failover_name)
        };

        // Try first provider
        if let Some(result) = self
            .try_provider(first_name, from, to, body, media_urls)
            .await
        {
            return result;
        }

        // Try second provider (if available and not also in cooldown)
        if let Some(second) = second_name {
            let second_in_cooldown = self.is_provider_in_cooldown(second).await;
            if !second_in_cooldown {
                if let Some(result) = self
                    .try_provider(second, from, to, body, media_urls)
                    .await
                {
                    return result;
                }
            } else {
                warn!(
                    provider = second,
                    "failover provider also in cooldown"
                );
            }
        }

        Err(anyhow::anyhow!(
            "no available SMS provider for DID {}",
            from
        ))
    }

    /// Attempt to send via a single provider. Returns Some(Result) if the provider
    /// was found and attempted, None if the provider doesn't exist.
    async fn try_provider(
        &self,
        name: &str,
        from: &str,
        to: &str,
        body: &str,
        media_urls: &[String],
    ) -> Option<Result<SendResult>> {
        let provider = self.providers.get(name)?;

        match provider.send_sms(from, to, body, media_urls).await {
            Ok(result) => {
                self.record_success(name).await;

                // Store message tracking in Redis
                self.store_message_tracking(
                    &result.message_id,
                    name,
                    &result.message_id,
                )
                .await;

                info!(
                    provider = name,
                    message_id = %result.message_id,
                    "SMS sent successfully"
                );
                Some(Ok(result))
            }
            Err(e) => {
                self.record_failure(name).await;
                warn!(
                    provider = name,
                    error = %e,
                    "provider send failed"
                );
                // Return None to allow caller to try next provider
                None
            }
        }
    }

    /// Get delivery status using Redis tracking to find the correct provider.
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

    /// Get the list of registered provider names.
    pub fn provider_names(&self) -> Vec<String> {
        self.providers.keys().cloned().collect()
    }

    /// Check if we can reach Redis.
    pub async fn redis_healthy(&self) -> bool {
        match self.redis_client.get_multiplexed_async_connection().await {
            Ok(mut conn) => {
                let result: Result<String, _> = redis::cmd("PING")
                    .query_async(&mut conn)
                    .await;
                result.is_ok()
            }
            Err(_) => false,
        }
    }

    /// Get current provider health status.
    pub async fn provider_health_status(&self) -> HashMap<String, ProviderHealthReport> {
        let health = self.provider_health.read().await;
        let mut report = HashMap::new();
        for name in self.providers.keys() {
            let status = if let Some(ph) = health.get(name) {
                ProviderHealthReport {
                    available: !ph.in_cooldown
                        || ph
                            .last_failure
                            .map(|lf| lf.elapsed().as_secs() >= self.cooldown_secs)
                            .unwrap_or(true),
                    consecutive_failures: ph.consecutive_failures,
                    in_cooldown: ph.in_cooldown
                        && ph
                            .last_failure
                            .map(|lf| lf.elapsed().as_secs() < self.cooldown_secs)
                            .unwrap_or(false),
                    cooldown_remaining_secs: if ph.in_cooldown {
                        ph.last_failure.map(|lf| {
                            self.cooldown_secs.saturating_sub(lf.elapsed().as_secs())
                        })
                    } else {
                        None
                    },
                }
            } else {
                ProviderHealthReport {
                    available: true,
                    consecutive_failures: 0,
                    in_cooldown: false,
                    cooldown_remaining_secs: None,
                }
            };
            report.insert(name.clone(), status);
        }
        report
    }

    /// Publish an inbound message to Redis pub/sub.
    pub async fn publish_inbound(
        &self,
        to_number: &str,
        message_json: &str,
    ) -> Result<()> {
        let channel = format!("np:sms:inbound:{}", to_number);
        let mut conn = self
            .redis_client
            .get_multiplexed_async_connection()
            .await
            .context("failed to connect to Redis for inbound publish")?;
        conn.publish::<_, _, ()>(&channel, message_json)
            .await
            .context("failed to publish inbound message to Redis")?;
        debug!(channel = %channel, "published inbound message to Redis pub/sub");
        Ok(())
    }
}

/// Health report for a single provider.
#[derive(Debug, Clone, Serialize)]
pub struct ProviderHealthReport {
    pub available: bool,
    pub consecutive_failures: u32,
    pub in_cooldown: bool,
    pub cooldown_remaining_secs: Option<u64>,
}
