use std::future::Future;
use std::pin::Pin;

use anyhow::{Context, Result};
use reqwest::Client;
use serde::Deserialize;
use tracing::{debug, error};

use super::{MessageStatus, SendResult, SmsProvider};

/// Twilio SMS API client.
pub struct TwilioProvider {
    client: Client,
    account_sid: String,
    auth_token: String,
}

#[derive(Deserialize)]
struct TwilioSendResponse {
    #[serde(default)]
    sid: String,
    #[serde(default)]
    status: String,
}

#[derive(Deserialize)]
struct TwilioStatusResponse {
    #[serde(default)]
    status: String,
}

impl TwilioProvider {
    pub fn new(account_sid: String, auth_token: String) -> Self {
        TwilioProvider {
            client: Client::new(),
            account_sid,
            auth_token,
        }
    }

    async fn do_send_sms(
        &self,
        from: &str,
        to: &str,
        body: &str,
        media_urls: &[String],
    ) -> Result<SendResult> {
        let url = format!(
            "https://api.twilio.com/2010-04-01/Accounts/{}/Messages.json",
            self.account_sid
        );

        let mut params = vec![
            ("From", from.to_string()),
            ("To", to.to_string()),
            ("Body", body.to_string()),
        ];

        // Add media URLs for MMS
        for media_url in media_urls {
            params.push(("MediaUrl", media_url.clone()));
        }

        let response = self
            .client
            .post(&url)
            .basic_auth(&self.account_sid, Some(&self.auth_token))
            .form(&params)
            .send()
            .await
            .context("Twilio API request failed")?;

        let status_code = response.status();
        if !status_code.is_success() {
            let error_body = response.text().await.unwrap_or_default();
            error!(
                status = %status_code,
                body = %error_body,
                "Twilio API error"
            );
            return Err(anyhow::anyhow!(
                "Twilio API returned {}: {}",
                status_code,
                error_body
            ));
        }

        let resp: TwilioSendResponse = response
            .json()
            .await
            .context("failed to parse Twilio response")?;

        debug!(
            message_id = %resp.sid,
            status = %resp.status,
            "Twilio message sent"
        );

        let message_status = match resp.status.as_str() {
            "queued" => MessageStatus::Queued,
            "sent" => MessageStatus::Sent,
            "delivered" => MessageStatus::Delivered,
            "failed" => MessageStatus::Failed,
            "undelivered" => MessageStatus::Undelivered,
            _ => MessageStatus::Queued,
        };

        Ok(SendResult {
            message_id: resp.sid,
            provider: "twilio".to_string(),
            status: message_status,
        })
    }

    async fn do_get_status(&self, message_id: &str) -> Result<MessageStatus> {
        let url = format!(
            "https://api.twilio.com/2010-04-01/Accounts/{}/Messages/{}.json",
            self.account_sid, message_id
        );

        let response = self
            .client
            .get(&url)
            .basic_auth(&self.account_sid, Some(&self.auth_token))
            .send()
            .await
            .context("Twilio status request failed")?;

        if !response.status().is_success() {
            return Err(anyhow::anyhow!(
                "Twilio status API returned {}",
                response.status()
            ));
        }

        let resp: TwilioStatusResponse = response
            .json()
            .await
            .context("failed to parse Twilio status response")?;

        let status = match resp.status.as_str() {
            "queued" => MessageStatus::Queued,
            "sending" | "sent" => MessageStatus::Sent,
            "delivered" => MessageStatus::Delivered,
            "failed" => MessageStatus::Failed,
            "undelivered" => MessageStatus::Undelivered,
            _ => MessageStatus::Queued,
        };

        Ok(status)
    }
}

impl SmsProvider for TwilioProvider {
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
        "twilio"
    }
}
