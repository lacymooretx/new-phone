use std::collections::HashMap;
use std::sync::Arc;

use serde::Serialize;
use tokio::sync::RwLock;
use tracing::{debug, info};

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

/// BLF state manager that tracks parking slot states and notifies subscribers.
pub struct BlfManager {
    /// Current BLF states keyed by extension.
    states: Arc<RwLock<HashMap<String, BlfState>>>,
    /// Subscribers keyed by extension they're watching.
    subscribers: Arc<RwLock<HashMap<String, Vec<BlfSubscriber>>>>,
}

impl BlfManager {
    pub fn new() -> Self {
        BlfManager {
            states: Arc::new(RwLock::new(HashMap::new())),
            subscribers: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    /// Update the BLF state for a parking slot extension.
    pub async fn update_state(&self, extension: &str, state: BlfStatus, caller_id: Option<String>) {
        let blf_state = BlfState {
            extension: extension.to_string(),
            state: state.clone(),
            caller_id,
        };

        let mut states = self.states.write().await;
        states.insert(extension.to_string(), blf_state.clone());

        debug!(
            extension = extension,
            state = ?state,
            "BLF state updated"
        );

        // Notify subscribers
        let subscribers = self.subscribers.read().await;
        if let Some(subs) = subscribers.get(extension) {
            for sub in subs {
                let notify_xml = build_dialog_info_xml(extension, &blf_state);
                debug!(
                    subscriber = %sub.subscriber_id,
                    extension = extension,
                    "sending BLF NOTIFY to subscriber (would send SIP NOTIFY)"
                );
                // In a full implementation, this would send a SIP NOTIFY to the subscriber
                let _ = notify_xml;
            }
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
fn build_dialog_info_xml(extension: &str, state: &BlfState) -> String {
    let dialog_state = state.state.as_sip_state();
    let entity = format!("sip:{}@pbx.local", extension);

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

    #[tokio::test]
    async fn test_blf_state_update() {
        let manager = BlfManager::new();

        manager
            .update_state("7001", BlfStatus::InUse, Some("1001".to_string()))
            .await;

        let state = manager.get_state("7001").await.unwrap();
        assert_eq!(state.state, BlfStatus::InUse);
        assert_eq!(state.caller_id, Some("1001".to_string()));
    }

    #[test]
    fn test_dialog_info_xml() {
        let state = BlfState {
            extension: "7001".to_string(),
            state: BlfStatus::InUse,
            caller_id: Some("1001".to_string()),
        };

        let xml = build_dialog_info_xml("7001", &state);
        assert!(xml.contains("confirmed"));
        assert!(xml.contains("1001"));
    }
}
