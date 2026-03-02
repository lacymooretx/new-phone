use std::collections::HashMap;
use std::sync::Arc;

use serde::Serialize;
use tokio::sync::RwLock;
use tracing::{debug, info};

/// Represents a participant in a conference bridge.
#[derive(Debug, Clone)]
pub struct Participant {
    pub id: String,
    /// The latest audio frame from this participant (PCM 16-bit LE samples, 8kHz).
    pub latest_frame: Vec<i16>,
}

/// Conference bridge mixer that combines N audio streams.
#[derive(Debug, Clone, Serialize)]
pub struct ConferenceBridge {
    pub bridge_id: String,
    pub participant_count: usize,
}

pub struct ConferenceMixer {
    bridges: Arc<RwLock<HashMap<String, BridgeState>>>,
}

struct BridgeState {
    bridge_id: String,
    participants: HashMap<String, Participant>,
}

impl ConferenceMixer {
    pub fn new() -> Self {
        ConferenceMixer {
            bridges: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    /// Create a new conference bridge.
    pub async fn create_bridge(&self, bridge_id: &str) {
        let mut bridges = self.bridges.write().await;
        bridges.insert(
            bridge_id.to_string(),
            BridgeState {
                bridge_id: bridge_id.to_string(),
                participants: HashMap::new(),
            },
        );
        info!(bridge_id = bridge_id, "conference bridge created");
    }

    /// Add a participant to a bridge.
    pub async fn add_participant(&self, bridge_id: &str, participant_id: &str) -> bool {
        let mut bridges = self.bridges.write().await;
        if let Some(bridge) = bridges.get_mut(bridge_id) {
            bridge.participants.insert(
                participant_id.to_string(),
                Participant {
                    id: participant_id.to_string(),
                    latest_frame: Vec::new(),
                },
            );
            info!(
                bridge_id = bridge_id,
                participant_id = participant_id,
                "participant added to bridge"
            );
            true
        } else {
            false
        }
    }

    /// Remove a participant from a bridge.
    pub async fn remove_participant(&self, bridge_id: &str, participant_id: &str) -> bool {
        let mut bridges = self.bridges.write().await;
        if let Some(bridge) = bridges.get_mut(bridge_id) {
            let removed = bridge.participants.remove(participant_id).is_some();
            if removed {
                info!(
                    bridge_id = bridge_id,
                    participant_id = participant_id,
                    "participant removed from bridge"
                );
            }
            removed
        } else {
            false
        }
    }

    /// Submit an audio frame for a participant.
    pub async fn submit_frame(&self, bridge_id: &str, participant_id: &str, frame: Vec<i16>) {
        let mut bridges = self.bridges.write().await;
        if let Some(bridge) = bridges.get_mut(bridge_id) {
            if let Some(participant) = bridge.participants.get_mut(participant_id) {
                participant.latest_frame = frame;
            }
        }
    }

    /// Mix all audio frames for a bridge, returning a map of participant_id -> mixed frame.
    /// Each participant receives the mix of all OTHER participants (excluding their own audio).
    pub async fn mix_frames(&self, bridge_id: &str) -> HashMap<String, Vec<i16>> {
        let bridges = self.bridges.read().await;
        let bridge = match bridges.get(bridge_id) {
            Some(b) => b,
            None => return HashMap::new(),
        };

        if bridge.participants.is_empty() {
            return HashMap::new();
        }

        // Determine the frame length (use the max across all participants)
        let frame_len = bridge
            .participants
            .values()
            .map(|p| p.latest_frame.len())
            .max()
            .unwrap_or(0);

        if frame_len == 0 {
            return HashMap::new();
        }

        // Compute the sum of all frames
        let mut sum_frame: Vec<i32> = vec![0i32; frame_len];
        for participant in bridge.participants.values() {
            for (i, &sample) in participant.latest_frame.iter().enumerate() {
                if i < frame_len {
                    sum_frame[i] += sample as i32;
                }
            }
        }

        // For each participant, subtract their contribution and normalize
        let participant_count = bridge.participants.len();
        let mut mixed = HashMap::new();

        for participant in bridge.participants.values() {
            let mut output = Vec::with_capacity(frame_len);
            for (i, &sum_val) in sum_frame.iter().enumerate().take(frame_len) {
                let own_sample = if i < participant.latest_frame.len() {
                    participant.latest_frame[i] as i32
                } else {
                    0
                };
                // Mix = sum - own, then normalize to prevent clipping
                let mixed_sample = sum_val - own_sample;
                let normalized = normalize_sample(mixed_sample, participant_count.saturating_sub(1));
                output.push(normalized);
            }
            mixed.insert(participant.id.clone(), output);
        }

        debug!(
            bridge_id = bridge_id,
            participants = participant_count,
            frame_len = frame_len,
            "mixed audio frames"
        );

        mixed
    }

    /// Remove a conference bridge.
    pub async fn destroy_bridge(&self, bridge_id: &str) -> bool {
        let mut bridges = self.bridges.write().await;
        let removed = bridges.remove(bridge_id).is_some();
        if removed {
            info!(bridge_id = bridge_id, "conference bridge destroyed");
        }
        removed
    }

    /// List all active bridges.
    pub async fn list_bridges(&self) -> Vec<ConferenceBridge> {
        let bridges = self.bridges.read().await;
        bridges
            .values()
            .map(|b| ConferenceBridge {
                bridge_id: b.bridge_id.clone(),
                participant_count: b.participants.len(),
            })
            .collect()
    }
}

/// Normalize a mixed sample to i16 range, scaling by the number of contributing sources.
fn normalize_sample(mixed: i32, source_count: usize) -> i16 {
    if source_count == 0 {
        return 0;
    }

    // Simple normalization: divide by source count to prevent clipping
    let normalized = mixed / source_count as i32;

    // Clamp to i16 range
    normalized.clamp(i16::MIN as i32, i16::MAX as i32) as i16
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_conference_mixing() {
        let mixer = ConferenceMixer::new();
        mixer.create_bridge("test-bridge").await;
        mixer.add_participant("test-bridge", "alice").await;
        mixer.add_participant("test-bridge", "bob").await;

        // Alice speaks (1000 amplitude), Bob is silent
        let alice_frame: Vec<i16> = vec![1000; 160];
        let bob_frame: Vec<i16> = vec![0; 160];

        mixer
            .submit_frame("test-bridge", "alice", alice_frame)
            .await;
        mixer.submit_frame("test-bridge", "bob", bob_frame).await;

        let mixed = mixer.mix_frames("test-bridge").await;

        // Alice should hear Bob's silence (0)
        let alice_hears = &mixed["alice"];
        assert_eq!(alice_hears[0], 0);

        // Bob should hear Alice's speech (1000)
        let bob_hears = &mixed["bob"];
        assert_eq!(bob_hears[0], 1000);
    }
}
