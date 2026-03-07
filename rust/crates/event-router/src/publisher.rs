use anyhow::{Context, Result};
use redis::AsyncCommands;
use tracing::{debug, error, info, warn};

use crate::parser::ParsedEvent;

/// Events that should be forwarded to the API for persistence.
const API_FORWARD_EVENTS: &[&str] = &[
    "CHANNEL_HANGUP",
    "RECORD_STOP",
];

/// Redis publisher for parsed FreeSWITCH events.
pub struct EventPublisher {
    redis_client: redis::Client,
    redis_connection: Option<redis::aio::MultiplexedConnection>,
    http_client: reqwest::Client,
    api_url: String,
    /// Allowed event names for publishing. None means all events are published.
    event_filter: Option<Vec<String>>,
}

impl EventPublisher {
    /// Create a new publisher connected to Redis with optional API forwarding.
    pub async fn new(
        redis_url: &str,
        api_url: &str,
        event_filter: Option<Vec<String>>,
    ) -> Result<Self> {
        let redis_client = redis::Client::open(redis_url)
            .with_context(|| format!("failed to create Redis client for {}", redis_url))?;

        let redis_connection = redis_client
            .get_multiplexed_async_connection()
            .await
            .with_context(|| "failed to connect to Redis")?;

        info!(url = redis_url, "connected to Redis for event publishing");

        let http_client = reqwest::Client::builder()
            .timeout(std::time::Duration::from_secs(10))
            .build()
            .context("failed to create HTTP client")?;

        if let Some(ref filter) = event_filter {
            info!(events = ?filter, "event filter active");
        } else {
            info!("no event filter, publishing all events");
        }

        Ok(EventPublisher {
            redis_client,
            redis_connection: Some(redis_connection),
            http_client,
            api_url: api_url.trim_end_matches('/').to_string(),
            event_filter,
        })
    }

    /// Check if an event should be published based on the filter.
    pub fn should_publish(&self, event_name: &str) -> bool {
        match &self.event_filter {
            None => true,
            Some(allowed) => allowed.iter().any(|e| e == event_name),
        }
    }

    /// Check if an event should be forwarded to the API.
    fn should_forward_to_api(event_name: &str) -> bool {
        API_FORWARD_EVENTS.contains(&event_name)
    }

    /// Publish a parsed event to Redis pub/sub and optionally forward to API.
    pub async fn publish(&mut self, event: &ParsedEvent) -> Result<()> {
        // Publish to Redis
        self.publish_to_redis(event).await?;

        // Forward significant events to the API for persistence
        if Self::should_forward_to_api(&event.event_name) {
            self.forward_to_api(event).await;
        }

        Ok(())
    }

    /// Publish to Redis pub/sub channels.
    async fn publish_to_redis(&mut self, event: &ParsedEvent) -> Result<()> {
        let conn = self.ensure_redis_connection().await?;

        let payload = serde_json::to_string(&event.payload)
            .context("failed to serialize event payload")?;

        // Tenant-specific channel
        let tenant_channel = format!(
            "np:events:{}:{}",
            event.tenant_id,
            event.event_name.to_lowercase()
        );

        // Global channel
        let global_channel = format!(
            "np:events:all:{}",
            event.event_name.to_lowercase()
        );

        // Publish to both channels
        let _: i64 = conn
            .publish(&tenant_channel, &payload)
            .await
            .with_context(|| format!("failed to publish to {}", tenant_channel))?;

        let _: i64 = conn
            .publish(&global_channel, &payload)
            .await
            .with_context(|| format!("failed to publish to {}", global_channel))?;

        debug!(
            tenant_channel = %tenant_channel,
            global_channel = %global_channel,
            event_name = %event.event_name,
            "published event to Redis"
        );

        Ok(())
    }

    /// Forward an event to the API for persistence (fire-and-forget with error logging).
    async fn forward_to_api(&self, event: &ParsedEvent) {
        let url = format!("{}/api/v1/events/ingest", self.api_url);

        let body = serde_json::json!({
            "event_name": event.event_name,
            "tenant_id": event.tenant_id,
            "channel_uuid": event.channel_uuid,
            "payload": event.payload,
        });

        match self.http_client.post(&url).json(&body).send().await {
            Ok(response) => {
                if response.status().is_success() {
                    debug!(
                        event_name = %event.event_name,
                        channel_uuid = %event.channel_uuid,
                        "forwarded event to API"
                    );
                } else {
                    warn!(
                        event_name = %event.event_name,
                        status = %response.status(),
                        "API rejected event"
                    );
                }
            }
            Err(e) => {
                warn!(
                    event_name = %event.event_name,
                    error = %e,
                    "failed to forward event to API (non-fatal)"
                );
            }
        }
    }

    /// Ensure we have a valid Redis connection, reconnecting if needed.
    async fn ensure_redis_connection(&mut self) -> Result<&mut redis::aio::MultiplexedConnection> {
        if self.redis_connection.is_none() {
            let conn = self
                .redis_client
                .get_multiplexed_async_connection()
                .await
                .context("failed to reconnect to Redis")?;
            self.redis_connection = Some(conn);
            info!("reconnected to Redis");
        }

        Ok(self.redis_connection.as_mut().unwrap())
    }

    /// Try to reconnect to Redis.
    pub async fn reconnect(&mut self) -> Result<()> {
        self.redis_connection = None;
        self.ensure_redis_connection().await?;
        Ok(())
    }
}

/// Publish events, handling errors with reconnection.
pub async fn publish_loop(
    publisher: &mut EventPublisher,
    event: &ParsedEvent,
) {
    // Check filter before publishing
    if !publisher.should_publish(&event.event_name) {
        debug!(event_name = %event.event_name, "event filtered out, skipping");
        return;
    }

    match publisher.publish(event).await {
        Ok(()) => {}
        Err(e) => {
            error!(error = %e, "failed to publish event, attempting reconnection");
            if let Err(re) = publisher.reconnect().await {
                error!(error = %re, "Redis reconnection failed");
            }
        }
    }
}
