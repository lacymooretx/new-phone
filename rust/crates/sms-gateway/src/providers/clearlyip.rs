use std::future::Future;
use std::pin::Pin;

use anyhow::{Context, Result};
use reqwest::Client;
use serde::{Deserialize, Serialize};
use tracing::{debug, error};

use super::{MessageStatus, SendResult, SmsProvider};

/// ClearlyIP SMS API client.
pub struct ClearlyIpProvider {
    client: Client,
    api_url: String,
    api_key: String,
}

#[derive(Serialize)]
struct ClearlyIpSendRequest {
    from: String,
    to: String,
    body: String,
    #[serde(skip_serializing_if = "Vec::is_empty")]
    media_urls: Vec<String>,
}

#[derive(Deserialize)]
struct ClearlyIpSendResponse {
    #[serde(default)]
    message_id: String,
    #[serde(default)]
    status: String,
}

#[derive(Deserialize)]
struct ClearlyIpStatusResponse {
    #[serde(default)]
    status: String,
}

impl ClearlyIpProvider {
    pub fn new(api_url: String, api_key: String) -> Self {
        ClearlyIpProvider {
            client: Client::new(),
            api_url,
            api_key,
        }
    }

    async fn do_send_sms(
        &self,
        from: &str,
        to: &str,
        body: &str,
        media_urls: &[String],
    ) -> Result<SendResult> {
        let url = format!("{}/v1/messages", self.api_url);

        let request_body = ClearlyIpSendRequest {
            from: from.to_string(),
            to: to.to_string(),
            body: body.to_string(),
            media_urls: media_urls.to_vec(),
        };

        let response = self
            .client
            .post(&url)
            .header("Authorization", format!("Bearer {}", self.api_key))
            .header("Content-Type", "application/json")
            .json(&request_body)
            .send()
            .await
            .context("ClearlyIP API request failed")?;

        let status_code = response.status();
        if !status_code.is_success() {
            let error_body = response.text().await.unwrap_or_default();
            error!(
                status = %status_code,
                body = %error_body,
                "ClearlyIP API error"
            );
            return Err(anyhow::anyhow!(
                "ClearlyIP API returned {}: {}",
                status_code,
                error_body
            ));
        }

        let resp: ClearlyIpSendResponse = response
            .json()
            .await
            .context("failed to parse ClearlyIP response")?;

        debug!(
            message_id = %resp.message_id,
            status = %resp.status,
            "ClearlyIP message sent"
        );

        let message_status = match resp.status.as_str() {
            "queued" => MessageStatus::Queued,
            "sent" => MessageStatus::Sent,
            "delivered" => MessageStatus::Delivered,
            "failed" => MessageStatus::Failed,
            _ => MessageStatus::Queued,
        };

        Ok(SendResult {
            message_id: resp.message_id,
            provider: "clearlyip".to_string(),
            status: message_status,
        })
    }

    async fn do_get_status(&self, message_id: &str) -> Result<MessageStatus> {
        let url = format!("{}/v1/messages/{}", self.api_url, message_id);

        let response = self
            .client
            .get(&url)
            .header("Authorization", format!("Bearer {}", self.api_key))
            .send()
            .await
            .context("ClearlyIP status request failed")?;

        if !response.status().is_success() {
            return Err(anyhow::anyhow!(
                "ClearlyIP status API returned {}",
                response.status()
            ));
        }

        let resp: ClearlyIpStatusResponse = response
            .json()
            .await
            .context("failed to parse ClearlyIP status response")?;

        let status = match resp.status.as_str() {
            "queued" => MessageStatus::Queued,
            "sent" => MessageStatus::Sent,
            "delivered" => MessageStatus::Delivered,
            "failed" => MessageStatus::Failed,
            "undelivered" => MessageStatus::Undelivered,
            _ => MessageStatus::Queued,
        };

        Ok(status)
    }
}

impl SmsProvider for ClearlyIpProvider {
    fn send_sms(
        &self,
        from: &str,
        to: &str,
        body: &str,
        media_urls: &[String],
    ) -> Pin<Box<dyn Future<Output = Result<SendResult>> + Send + '_>> {
        let from = from.to_string();
        let to = to.to_string();
        let body = body.to_string();
        let media_urls = media_urls.to_vec();
        Box::pin(async move { self.do_send_sms(&from, &to, &body, &media_urls).await })
    }

    fn get_status(
        &self,
        message_id: &str,
    ) -> Pin<Box<dyn Future<Output = Result<MessageStatus>> + Send + '_>> {
        let message_id = message_id.to_string();
        Box::pin(async move { self.do_get_status(&message_id).await })
    }

    fn provider_name(&self) -> &str {
        "clearlyip"
    }
}
