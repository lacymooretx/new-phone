use anyhow::{Context, Result};
use redis::AsyncCommands;
use tracing::{debug, warn};

/// Redis-based sliding window rate limiter for SMS per DID.
pub struct RateLimiter {
    client: redis::Client,
    limit_per_minute: u32,
    limit_per_hour: u32,
}

impl RateLimiter {
    pub fn new(redis_url: &str, limit_per_minute: u32, limit_per_hour: u32) -> Result<Self> {
        let client = redis::Client::open(redis_url)
            .context("failed to create Redis client for rate limiter")?;

        Ok(RateLimiter {
            client,
            limit_per_minute,
            limit_per_hour,
        })
    }

    /// Check if a DID is within rate limits. Returns Ok(true) if allowed.
    /// If allowed, increments the counters.
    pub async fn check_and_increment(&self, did: &str) -> Result<RateLimitResult> {
        let mut conn = self
            .client
            .get_multiplexed_async_connection()
            .await
            .context("failed to connect to Redis")?;

        let now_ms = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default()
            .as_millis() as u64;

        let minute_key = format!("np:sms:rate:{}:min", did);
        let hour_key = format!("np:sms:rate:{}:hour", did);

        // Sliding window using sorted sets
        // Remove entries outside the window, count remaining, add new entry

        let minute_window = now_ms.saturating_sub(60_000);
        let hour_window = now_ms.saturating_sub(3_600_000);

        // Clean up old entries
        let _: () = conn
            .zrembyscore(&minute_key, 0u64, minute_window)
            .await
            .unwrap_or(());
        let _: () = conn
            .zrembyscore(&hour_key, 0u64, hour_window)
            .await
            .unwrap_or(());

        // Count current entries
        let minute_count: u32 = conn
            .zcard(&minute_key)
            .await
            .unwrap_or(0);
        let hour_count: u32 = conn
            .zcard(&hour_key)
            .await
            .unwrap_or(0);

        // Check limits
        if minute_count >= self.limit_per_minute {
            warn!(
                did = did,
                count = minute_count,
                limit = self.limit_per_minute,
                "rate limit exceeded (per-minute)"
            );
            return Ok(RateLimitResult {
                allowed: false,
                minute_count,
                hour_count,
                minute_limit: self.limit_per_minute,
                hour_limit: self.limit_per_hour,
                retry_after_ms: Some(60_000 - (now_ms - minute_window)),
            });
        }

        if hour_count >= self.limit_per_hour {
            warn!(
                did = did,
                count = hour_count,
                limit = self.limit_per_hour,
                "rate limit exceeded (per-hour)"
            );
            return Ok(RateLimitResult {
                allowed: false,
                minute_count,
                hour_count,
                minute_limit: self.limit_per_minute,
                hour_limit: self.limit_per_hour,
                retry_after_ms: Some(3_600_000 - (now_ms - hour_window)),
            });
        }

        // Add entry with current timestamp as score and a unique member
        let member = format!("{}:{}", now_ms, uuid::Uuid::new_v4());
        let _: () = conn
            .zadd(&minute_key, &member, now_ms as f64)
            .await
            .unwrap_or(());
        let _: () = conn
            .zadd(&hour_key, &member, now_ms as f64)
            .await
            .unwrap_or(());

        // Set TTL on the keys to auto-expire
        let _: () = conn.expire(&minute_key, 120).await.unwrap_or(());
        let _: () = conn.expire(&hour_key, 7200).await.unwrap_or(());

        debug!(
            did = did,
            minute_count = minute_count + 1,
            hour_count = hour_count + 1,
            "rate limit check passed"
        );

        Ok(RateLimitResult {
            allowed: true,
            minute_count: minute_count + 1,
            hour_count: hour_count + 1,
            minute_limit: self.limit_per_minute,
            hour_limit: self.limit_per_hour,
            retry_after_ms: None,
        })
    }

    /// Clean up expired rate limit entries for a DID.
    pub async fn cleanup(&self, did: &str) -> Result<()> {
        let mut conn = self
            .client
            .get_multiplexed_async_connection()
            .await
            .context("failed to connect to Redis")?;

        let now_ms = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default()
            .as_millis() as u64;

        let minute_key = format!("np:sms:rate:{}:min", did);
        let hour_key = format!("np:sms:rate:{}:hour", did);

        let minute_window = now_ms.saturating_sub(60_000);
        let hour_window = now_ms.saturating_sub(3_600_000);

        let _: () = conn.zrembyscore(&minute_key, 0u64, minute_window).await?;
        let _: () = conn.zrembyscore(&hour_key, 0u64, hour_window).await?;

        Ok(())
    }
}

/// Rate limit check result.
#[derive(Debug, serde::Serialize)]
pub struct RateLimitResult {
    pub allowed: bool,
    pub minute_count: u32,
    pub hour_count: u32,
    pub minute_limit: u32,
    pub hour_limit: u32,
    pub retry_after_ms: Option<u64>,
}

impl RateLimitResult {
    /// Returns true if the request was allowed.
    pub fn is_allowed(&self) -> bool {
        self.allowed
    }

    /// Returns the remaining capacity for the per-minute window.
    pub fn minute_remaining(&self) -> u32 {
        self.minute_limit.saturating_sub(self.minute_count)
    }

    /// Returns the remaining capacity for the per-hour window.
    pub fn hour_remaining(&self) -> u32 {
        self.hour_limit.saturating_sub(self.hour_count)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_rate_limiter_constructor_valid() {
        let limiter = RateLimiter::new("redis://localhost:6379/15", 10, 100);
        assert!(limiter.is_ok());
        let limiter = limiter.unwrap();
        assert_eq!(limiter.limit_per_minute, 10);
        assert_eq!(limiter.limit_per_hour, 100);
    }

    #[test]
    fn test_rate_limiter_constructor_invalid_url() {
        // Invalid Redis URL should produce an error
        let limiter = RateLimiter::new("not-a-valid-redis-url", 10, 100);
        assert!(limiter.is_err());
    }

    #[test]
    fn test_rate_limit_result_allowed() {
        let result = RateLimitResult {
            allowed: true,
            minute_count: 3,
            hour_count: 15,
            minute_limit: 10,
            hour_limit: 100,
            retry_after_ms: None,
        };

        assert!(result.is_allowed());
        assert_eq!(result.minute_remaining(), 7);
        assert_eq!(result.hour_remaining(), 85);
        assert!(result.retry_after_ms.is_none());
    }

    #[test]
    fn test_rate_limit_result_blocked_per_minute() {
        let result = RateLimitResult {
            allowed: false,
            minute_count: 10,
            hour_count: 50,
            minute_limit: 10,
            hour_limit: 100,
            retry_after_ms: Some(30_000),
        };

        assert!(!result.is_allowed());
        assert_eq!(result.minute_remaining(), 0);
        assert_eq!(result.hour_remaining(), 50);
        assert_eq!(result.retry_after_ms, Some(30_000));
    }

    #[test]
    fn test_rate_limit_result_blocked_per_hour() {
        let result = RateLimitResult {
            allowed: false,
            minute_count: 5,
            hour_count: 100,
            minute_limit: 10,
            hour_limit: 100,
            retry_after_ms: Some(1_800_000),
        };

        assert!(!result.is_allowed());
        assert_eq!(result.minute_remaining(), 5);
        assert_eq!(result.hour_remaining(), 0);
        assert_eq!(result.retry_after_ms, Some(1_800_000));
    }

    #[test]
    fn test_rate_limit_result_serializes_to_json() {
        let result = RateLimitResult {
            allowed: true,
            minute_count: 1,
            hour_count: 1,
            minute_limit: 10,
            hour_limit: 100,
            retry_after_ms: None,
        };

        let json = serde_json::to_string(&result).unwrap();
        assert!(json.contains("\"allowed\":true"));
        assert!(json.contains("\"minute_count\":1"));
        assert!(json.contains("\"hour_count\":1"));
        assert!(json.contains("\"minute_limit\":10"));
        assert!(json.contains("\"hour_limit\":100"));
        assert!(json.contains("\"retry_after_ms\":null"));
    }

    #[test]
    fn test_rate_limit_result_at_limit_boundary() {
        // Exactly at the limit but not over
        let result = RateLimitResult {
            allowed: true,
            minute_count: 9,
            hour_count: 99,
            minute_limit: 10,
            hour_limit: 100,
            retry_after_ms: None,
        };

        assert!(result.is_allowed());
        assert_eq!(result.minute_remaining(), 1);
        assert_eq!(result.hour_remaining(), 1);
    }
}
