use std::collections::HashMap;
use std::sync::Arc;

use redis::AsyncCommands;
use serde::Serialize;
use tokio::sync::RwLock;
use tracing::{debug, info, warn};

/// BLF (Busy Lamp Field) state for a parking slot.
#[derive(Debug, Clone, Serialize)]
pub struct BlfState {
    pub extension: String,
    pub state: BlfStatus,
    pub caller_id: Option<String>,
}

/// BLF status values (maps to SIP dialog states).
#[derive(Debug, Clone, Serialize, PartialEq)]
pub enum BlfStatus {
    /// Slot is empty/idle
    Idle,
    /// Slot has a parked call (ringing equivalent)
    InUse,
    /// Slot is being retrieved
    Ringing,
}

impl BlfStatus {
    /// Convert to SIP dialog-info state string.
    pub fn as_sip_state(&self) -> &'static str {
        match self {
            BlfStatus::Idle => "terminated",
            BlfStatus::InUse => "confirmed",
            BlfStatus::Ringing => "early",
        }
    }
}

/// Subscriber interested in BLF state changes.
#[derive(Debug, Clone)]
pub struct BlfSubscriber {
    pub subscriber_id: String,
    pub extension: String,
    pub contact: String,
}

/// BLF state manager that tracks parking slot states and publishes changes
/// to Redis pub/sub so the event-router (or other services) can send SIP
/// NOTIFYs via FreeSWITCH.
pub struct BlfManager {
    /// Current BLF states keyed by extension.
    states: Arc<RwLock<HashMap<String, BlfState>>>,
    /// Subscribers keyed by extension they're watching.
    subscribers: Arc<RwLock<HashMap<String, Vec<BlfSubscriber>>>>,
    /// Redis connection manager for publishing BLF events.
    redis_conn: redis::aio::ConnectionManager,
    /// SIP domain used in dialog-info entity URIs.
    sip_domain: String,
}

impl BlfManager {
    pub async fn new(redis_conn: redis::aio::ConnectionManager, sip_domain: String) -> Self {
        BlfManager {
            states: Arc::new(RwLock::new(HashMap::new())),
            subscribers: Arc::new(RwLock::new(HashMap::new())),
            redis_conn,
            sip_domain,
        }
    }

    /// Update the BLF state for a parking slot extension and publish to
    /// Redis pub/sub channel `np:blf:{extension}`.
    pub async fn update_state(
        &self,
        extension: &str,
        state: BlfStatus,
        caller_id: Option<String>,
    ) {
        let blf_state = BlfState {
            extension: extension.to_string(),
            state: state.clone(),
            caller_id,
        };

        {
            let mut states = self.states.write().await;
            states.insert(extension.to_string(), blf_state.clone());
        }

        debug!(
            extension = extension,
            state = ?state,
            "BLF state updated"
        );

        // Build dialog-info XML for the new state
        let notify_xml = build_dialog_info_xml(extension, &blf_state, &self.sip_domain);

        // Publish to Redis pub/sub so event-router / other services can
        // send SIP NOTIFYs via FreeSWITCH
        let channel = format!("np:blf:{}", extension);
        let mut conn = self.redis_conn.clone();
        match conn.publish::<_, _, ()>(&channel, &notify_xml).await {
            Ok(()) => {
                debug!(
                    channel = %channel,
                    extension = extension,
                    "published BLF state change to Redis pub/sub"
                );
            }
            Err(e) => {
                warn!(
                    channel = %channel,
                    extension = extension,
                    error = %e,
                    "failed to publish BLF state change to Redis pub/sub"
                );
            }
        }

        // Also publish a JSON summary to a consolidated channel for any
        // service that wants all BLF events in one stream.
        let summary = serde_json::json!({
            "extension": extension,
            "state": blf_state.state.as_sip_state(),
            "caller_id": blf_state.caller_id,
        });
        if let Ok(json) = serde_json::to_string(&summary) {
            let _ = conn
                .publish::<_, _, ()>("np:blf:all", &json)
                .await;
        }
    }

    /// Get the current BLF state for an extension.
    pub async fn get_state(&self, extension: &str) -> Option<BlfState> {
        let states = self.states.read().await;
        states.get(extension).cloned()
    }

    /// Get all BLF states.
    pub async fn get_all_states(&self) -> Vec<BlfState> {
        let states = self.states.read().await;
        states.values().cloned().collect()
    }

    /// Add a subscriber for BLF state changes on an extension.
    pub async fn add_subscriber(&self, extension: &str, subscriber: BlfSubscriber) {
        let mut subscribers = self.subscribers.write().await;
        subscribers
            .entry(extension.to_string())
            .or_default()
            .push(subscriber.clone());

        info!(
            extension = extension,
            subscriber = %subscriber.subscriber_id,
            "BLF subscriber added"
        );
    }

    /// Remove a subscriber.
    pub async fn remove_subscriber(&self, extension: &str, subscriber_id: &str) {
        let mut subscribers = self.subscribers.write().await;
        if let Some(subs) = subscribers.get_mut(extension) {
            subs.retain(|s| s.subscriber_id != subscriber_id);
            info!(
                extension = extension,
                subscriber = subscriber_id,
                "BLF subscriber removed"
            );
        }
    }
}

/// Build a SIP dialog-info XML body for NOTIFY messages.
pub fn build_dialog_info_xml(extension: &str, state: &BlfState, sip_domain: &str) -> String {
    let dialog_state = state.state.as_sip_state();
    let entity = format!("sip:{}@{}", extension, sip_domain);

    let remote_info = if let Some(caller_id) = &state.caller_id {
        format!(
            r#"
        <remote>
          <identity>{}</identity>
        </remote>"#,
            caller_id
        )
    } else {
        String::new()
    };

    format!(
        r#"<?xml version="1.0" encoding="UTF-8"?>
<dialog-info xmlns="urn:ietf:params:xml:ns:dialog-info"
             version="1"
             state="full"
             entity="{entity}">
  <dialog id="{extension}-park">
    <state>{dialog_state}</state>{remote_info}
  </dialog>
</dialog-info>"#,
        entity = entity,
        extension = extension,
        dialog_state = dialog_state,
        remote_info = remote_info,
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_blf_status_sip_state() {
        assert_eq!(BlfStatus::Idle.as_sip_state(), "terminated");
        assert_eq!(BlfStatus::InUse.as_sip_state(), "confirmed");
        assert_eq!(BlfStatus::Ringing.as_sip_state(), "early");
    }

    #[test]
    fn test_dialog_info_xml() {
        let state = BlfState {
            extension: "7001".to_string(),
            state: BlfStatus::InUse,
            caller_id: Some("1001".to_string()),
        };

        let xml = build_dialog_info_xml("7001", &state, "pbx.local");
        assert!(xml.contains("confirmed"));
        assert!(xml.contains("1001"));
        assert!(xml.contains("sip:7001@pbx.local"));
    }

    #[test]
    fn test_dialog_info_xml_idle_no_caller() {
        let state = BlfState {
            extension: "7002".to_string(),
            state: BlfStatus::Idle,
            caller_id: None,
        };

        let xml = build_dialog_info_xml("7002", &state, "example.com");
        assert!(xml.contains("terminated"));
        assert!(xml.contains("sip:7002@example.com"));
        assert!(!xml.contains("<remote>"));
    }
}
