use anyhow::{Context, Result};
use redis::AsyncCommands;
use tracing::{debug, error, info};

use crate::parser::ParsedEvent;

/// Redis publisher for parsed FreeSWITCH events.
pub struct EventPublisher {
    client: redis::Client,
    connection: Option<redis::aio::MultiplexedConnection>,
}

impl EventPublisher {
    /// Create a new publisher connected to Redis.
    pub async fn new(redis_url: &str) -> Result<Self> {
        let client = redis::Client::open(redis_url)
            .with_context(|| format!("failed to create Redis client for {}", redis_url))?;

        let connection = client
            .get_multiplexed_async_connection()
            .await
            .with_context(|| "failed to connect to Redis")?;

        info!(url = redis_url, "connected to Redis for event publishing");

        Ok(EventPublisher {
            client,
            connection: Some(connection),
        })
    }

    /// Publish a parsed event to the appropriate Redis pub/sub channel.
    ///
    /// Channel naming: `np:events:{tenant_id}:{event_type}`
    /// Also publishes to `np:events:all:{event_type}` for global subscribers.
    pub async fn publish(&mut self, event: &ParsedEvent) -> Result<()> {
        let conn = self.ensure_connection().await?;

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

    /// Ensure we have a valid Redis connection, reconnecting if needed.
    async fn ensure_connection(&mut self) -> Result<&mut redis::aio::MultiplexedConnection> {
        if self.connection.is_none() {
            let conn = self
                .client
                .get_multiplexed_async_connection()
                .await
                .context("failed to reconnect to Redis")?;
            self.connection = Some(conn);
            info!("reconnected to Redis");
        }

        Ok(self.connection.as_mut().unwrap())
    }

    /// Try to reconnect to Redis.
    pub async fn reconnect(&mut self) -> Result<()> {
        self.connection = None;
        self.ensure_connection().await?;
        Ok(())
    }
}

/// Publish events in a loop, handling errors with reconnection.
pub async fn publish_loop(
    publisher: &mut EventPublisher,
    event: &ParsedEvent,
) {
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
