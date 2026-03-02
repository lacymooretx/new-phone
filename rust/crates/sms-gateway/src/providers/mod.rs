pub mod clearlyip;
pub mod twilio;

use std::future::Future;
use std::pin::Pin;

use anyhow::Result;
use serde::{Deserialize, Serialize};

/// Result of sending an SMS.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SendResult {
    pub message_id: String,
    pub provider: String,
    pub status: MessageStatus,
}

/// SMS message status.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum MessageStatus {
    Queued,
    Sent,
    Delivered,
    Failed,
    Undelivered,
}

/// Inbound SMS message.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InboundMessage {
    pub message_id: String,
    pub from: String,
    pub to: String,
    pub body: String,
    pub media_urls: Vec<String>,
    pub provider: String,
    pub received_at: u64,
}

/// SMS provider trait that all providers must implement.
pub trait SmsProvider: Send + Sync {
    /// Send an SMS/MMS message.
    fn send_sms(
        &self,
        from: &str,
        to: &str,
        body: &str,
        media_urls: &[String],
    ) -> Pin<Box<dyn Future<Output = Result<SendResult>> + Send + '_>>;

    /// Get the delivery status of a message.
    fn get_status(
        &self,
        message_id: &str,
    ) -> Pin<Box<dyn Future<Output = Result<MessageStatus>> + Send + '_>>;

    /// Get the provider name.
    fn provider_name(&self) -> &str;
}
