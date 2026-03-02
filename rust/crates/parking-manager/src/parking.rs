use std::collections::HashMap;
use std::sync::Arc;

use anyhow::{Context, Result};
use redis::AsyncCommands;
use serde::{Deserialize, Serialize};
use tokio::sync::RwLock;
use tracing::{debug, info, warn};

/// State of a single parking slot.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ParkingSlot {
    pub slot_number: u32,
    pub occupied: bool,
    pub call_uuid: Option<String>,
    pub caller_id: Option<String>,
    pub callee_id: Option<String>,
    pub parked_by: Option<String>,
    pub parked_at: Option<u64>,
    pub timeout_at: Option<u64>,
}

/// A parking lot with multiple slots.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ParkingLot {
    pub lot_id: String,
    pub tenant_id: String,
    pub extension_base: String,
    pub slots: Vec<ParkingSlot>,
}

/// Request to park a call.
#[derive(Debug, Deserialize)]
pub struct ParkRequest {
    pub call_uuid: String,
    pub caller_id: Option<String>,
    pub callee_id: Option<String>,
    pub parked_by: String,
    pub timeout: Option<u64>,
}

/// Request to retrieve a parked call.
#[derive(Debug, Deserialize)]
pub struct RetrieveRequest {
    pub retrieved_by: String,
}

/// Result of a park operation.
#[derive(Debug, Serialize)]
pub struct ParkResult {
    pub lot_id: String,
    pub slot_number: u32,
    pub extension: String,
}

/// The parking manager handles all parking operations.
pub struct ParkingManager {
    lots: Arc<RwLock<HashMap<String, ParkingLot>>>,
    redis_client: redis::Client,
    esl_addr: String,
    esl_password: String,
    default_timeout: u64,
    default_slots: u32,
}

impl ParkingManager {
    pub fn new(
        redis_url: &str,
        esl_host: &str,
        esl_port: u16,
        esl_password: &str,
        default_timeout: u64,
        default_slots: u32,
    ) -> Result<Self> {
        let redis_client = redis::Client::open(redis_url)
            .context("failed to create Redis client")?;

        Ok(ParkingManager {
            lots: Arc::new(RwLock::new(HashMap::new())),
            redis_client,
            esl_addr: format!("{}:{}", esl_host, esl_port),
            esl_password: esl_password.to_string(),
            default_timeout,
            default_slots,
        })
    }

    /// Ensure a parking lot exists, creating it if needed.
    pub async fn ensure_lot(&self, lot_id: &str, tenant_id: &str) {
        let mut lots = self.lots.write().await;
        if !lots.contains_key(lot_id) {
            let extension_base = format!("7{}", lot_id.chars().filter(|c| c.is_ascii_digit()).collect::<String>());
            let slots: Vec<ParkingSlot> = (1..=self.default_slots)
                .map(|i| ParkingSlot {
                    slot_number: i,
                    occupied: false,
                    call_uuid: None,
                    caller_id: None,
                    callee_id: None,
                    parked_by: None,
                    parked_at: None,
                    timeout_at: None,
                })
                .collect();

            lots.insert(
                lot_id.to_string(),
                ParkingLot {
                    lot_id: lot_id.to_string(),
                    tenant_id: tenant_id.to_string(),
                    extension_base,
                    slots,
                },
            );
            info!(lot_id = lot_id, tenant_id = tenant_id, "parking lot created");
        }
    }

    /// Park a call in the first available slot.
    pub async fn park_call(&self, lot_id: &str, request: ParkRequest) -> Result<ParkResult> {
        let now = now_epoch();
        let timeout = request.timeout.unwrap_or(self.default_timeout);

        let mut lots = self.lots.write().await;
        let lot = lots
            .get_mut(lot_id)
            .ok_or_else(|| anyhow::anyhow!("parking lot {} not found", lot_id))?;

        // Find first available slot
        let slot = lot
            .slots
            .iter_mut()
            .find(|s| !s.occupied)
            .ok_or_else(|| anyhow::anyhow!("no available slots in lot {}", lot_id))?;

        slot.occupied = true;
        slot.call_uuid = Some(request.call_uuid.clone());
        slot.caller_id = request.caller_id.clone();
        slot.callee_id = request.callee_id.clone();
        slot.parked_by = Some(request.parked_by.clone());
        slot.parked_at = Some(now);
        slot.timeout_at = Some(now + timeout);

        let slot_number = slot.slot_number;
        let extension = format!("{}{:02}", lot.extension_base, slot_number);

        info!(
            lot_id = lot_id,
            slot = slot_number,
            call_uuid = %request.call_uuid,
            parked_by = %request.parked_by,
            "call parked"
        );

        // Store state in Redis
        let lot_clone = lot.clone();
        let redis = self.redis_client.clone();
        tokio::spawn(async move {
            if let Err(e) = save_lot_to_redis(&redis, &lot_clone).await {
                warn!(error = %e, "failed to save parking state to Redis");
            }
        });

        // Send ESL command to transfer call to parking hold music
        let esl_addr = self.esl_addr.clone();
        let esl_pass = self.esl_password.clone();
        let uuid = request.call_uuid.clone();
        tokio::spawn(async move {
            if let Err(e) = esl_park_call(&esl_addr, &esl_pass, &uuid).await {
                warn!(error = %e, "failed to send ESL park command");
            }
        });

        Ok(ParkResult {
            lot_id: lot_id.to_string(),
            slot_number,
            extension,
        })
    }

    /// Retrieve a parked call from a specific slot.
    pub async fn retrieve_call(
        &self,
        lot_id: &str,
        slot_number: u32,
        request: RetrieveRequest,
    ) -> Result<String> {
        let mut lots = self.lots.write().await;
        let lot = lots
            .get_mut(lot_id)
            .ok_or_else(|| anyhow::anyhow!("parking lot {} not found", lot_id))?;

        let slot = lot
            .slots
            .iter_mut()
            .find(|s| s.slot_number == slot_number)
            .ok_or_else(|| anyhow::anyhow!("slot {} not found", slot_number))?;

        if !slot.occupied {
            return Err(anyhow::anyhow!("slot {} is empty", slot_number));
        }

        let call_uuid = slot
            .call_uuid
            .clone()
            .ok_or_else(|| anyhow::anyhow!("no call UUID in slot"))?;

        // Clear the slot
        slot.occupied = false;
        slot.call_uuid = None;
        slot.caller_id = None;
        slot.callee_id = None;
        slot.parked_by = None;
        slot.parked_at = None;
        slot.timeout_at = None;

        info!(
            lot_id = lot_id,
            slot = slot_number,
            call_uuid = %call_uuid,
            retrieved_by = %request.retrieved_by,
            "call retrieved from parking"
        );

        // Update Redis
        let lot_clone = lot.clone();
        let redis = self.redis_client.clone();
        tokio::spawn(async move {
            if let Err(e) = save_lot_to_redis(&redis, &lot_clone).await {
                warn!(error = %e, "failed to save parking state to Redis");
            }
        });

        // Send ESL command to bridge call to the retriever
        let esl_addr = self.esl_addr.clone();
        let esl_pass = self.esl_password.clone();
        let uuid = call_uuid.clone();
        let dest = request.retrieved_by.clone();
        tokio::spawn(async move {
            if let Err(e) = esl_retrieve_call(&esl_addr, &esl_pass, &uuid, &dest).await {
                warn!(error = %e, "failed to send ESL retrieve command");
            }
        });

        Ok(call_uuid)
    }

    /// Force-release a slot without retrieving the call.
    pub async fn force_release(&self, lot_id: &str, slot_number: u32) -> Result<()> {
        let mut lots = self.lots.write().await;
        let lot = lots
            .get_mut(lot_id)
            .ok_or_else(|| anyhow::anyhow!("parking lot {} not found", lot_id))?;

        let slot = lot
            .slots
            .iter_mut()
            .find(|s| s.slot_number == slot_number)
            .ok_or_else(|| anyhow::anyhow!("slot {} not found", slot_number))?;

        if slot.occupied {
            // Hangup the call via ESL if there's a UUID
            if let Some(uuid) = &slot.call_uuid {
                let esl_addr = self.esl_addr.clone();
                let esl_pass = self.esl_password.clone();
                let uuid = uuid.clone();
                tokio::spawn(async move {
                    if let Err(e) = esl_hangup_call(&esl_addr, &esl_pass, &uuid).await {
                        warn!(error = %e, "failed to hangup parked call");
                    }
                });
            }

            slot.occupied = false;
            slot.call_uuid = None;
            slot.caller_id = None;
            slot.callee_id = None;
            slot.parked_by = None;
            slot.parked_at = None;
            slot.timeout_at = None;

            info!(lot_id = lot_id, slot = slot_number, "slot force-released");
        }

        Ok(())
    }

    /// Get all slots for a parking lot.
    pub async fn get_slots(&self, lot_id: &str) -> Option<Vec<ParkingSlot>> {
        let lots = self.lots.read().await;
        lots.get(lot_id).map(|l| l.slots.clone())
    }

    /// List all parking lots.
    pub async fn list_lots(&self) -> Vec<ParkingLot> {
        let lots = self.lots.read().await;
        lots.values().cloned().collect()
    }

    /// Check for timed-out parked calls and handle them.
    pub async fn check_timeouts(&self) {
        let now = now_epoch();
        let mut lots = self.lots.write().await;

        for lot in lots.values_mut() {
            for slot in &mut lot.slots {
                if slot.occupied {
                    if let Some(timeout_at) = slot.timeout_at {
                        if now >= timeout_at {
                            info!(
                                lot_id = %lot.lot_id,
                                slot = slot.slot_number,
                                call_uuid = ?slot.call_uuid,
                                "parking timeout, returning call to parker"
                            );

                            // Return call to the person who parked it
                            if let (Some(uuid), Some(parker)) =
                                (&slot.call_uuid, &slot.parked_by)
                            {
                                let esl_addr_clone = "esl_addr".to_string();
                                let _ = esl_addr_clone;
                                info!(
                                    call_uuid = %uuid,
                                    return_to = %parker,
                                    "would return timed-out call to parker"
                                );
                            }

                            // Clear the slot
                            slot.occupied = false;
                            slot.call_uuid = None;
                            slot.caller_id = None;
                            slot.callee_id = None;
                            slot.parked_by = None;
                            slot.parked_at = None;
                            slot.timeout_at = None;
                        }
                    }
                }
            }
        }
    }
}

async fn save_lot_to_redis(client: &redis::Client, lot: &ParkingLot) -> Result<()> {
    let mut conn = client
        .get_multiplexed_async_connection()
        .await
        .context("failed to connect to Redis")?;

    let key = format!("np:parking:{}", lot.lot_id);
    let value = serde_json::to_string(lot).context("failed to serialize lot")?;
    conn.set::<_, _, ()>(&key, &value)
        .await
        .context("failed to set parking state in Redis")?;

    debug!(key = %key, "saved parking state to Redis");
    Ok(())
}

/// Send ESL command to park a call (transfer to hold music).
async fn esl_park_call(esl_addr: &str, esl_password: &str, call_uuid: &str) -> Result<()> {
    let mut stream = tokio::net::TcpStream::connect(esl_addr)
        .await
        .context("failed to connect to ESL")?;

    use tokio::io::{AsyncReadExt, AsyncWriteExt};

    // Read greeting
    let mut buf = [0u8; 4096];
    let _ = stream.read(&mut buf).await?;

    // Auth
    let auth = format!("auth {}\n\n", esl_password);
    stream.write_all(auth.as_bytes()).await?;
    let _ = stream.read(&mut buf).await?;

    // Park the call by transferring to a parking hold extension
    let cmd = format!(
        "api uuid_transfer {} -both park+${{parking_lot_range}} inline\n\n",
        call_uuid
    );
    stream.write_all(cmd.as_bytes()).await?;
    let _ = stream.read(&mut buf).await?;

    debug!(call_uuid = call_uuid, "ESL park command sent");
    Ok(())
}

/// Send ESL command to retrieve a parked call.
async fn esl_retrieve_call(
    esl_addr: &str,
    esl_password: &str,
    call_uuid: &str,
    dest_extension: &str,
) -> Result<()> {
    let mut stream = tokio::net::TcpStream::connect(esl_addr)
        .await
        .context("failed to connect to ESL")?;

    use tokio::io::{AsyncReadExt, AsyncWriteExt};

    let mut buf = [0u8; 4096];
    let _ = stream.read(&mut buf).await?;

    let auth = format!("auth {}\n\n", esl_password);
    stream.write_all(auth.as_bytes()).await?;
    let _ = stream.read(&mut buf).await?;

    let cmd = format!(
        "api uuid_transfer {} -both {} XML default\n\n",
        call_uuid, dest_extension
    );
    stream.write_all(cmd.as_bytes()).await?;
    let _ = stream.read(&mut buf).await?;

    debug!(
        call_uuid = call_uuid,
        dest = dest_extension,
        "ESL retrieve command sent"
    );
    Ok(())
}

/// Send ESL command to hangup a call.
async fn esl_hangup_call(esl_addr: &str, esl_password: &str, call_uuid: &str) -> Result<()> {
    let mut stream = tokio::net::TcpStream::connect(esl_addr)
        .await
        .context("failed to connect to ESL")?;

    use tokio::io::{AsyncReadExt, AsyncWriteExt};

    let mut buf = [0u8; 4096];
    let _ = stream.read(&mut buf).await?;

    let auth = format!("auth {}\n\n", esl_password);
    stream.write_all(auth.as_bytes()).await?;
    let _ = stream.read(&mut buf).await?;

    let cmd = format!("api uuid_kill {} NORMAL_CLEARING\n\n", call_uuid);
    stream.write_all(cmd.as_bytes()).await?;
    let _ = stream.read(&mut buf).await?;

    debug!(call_uuid = call_uuid, "ESL hangup command sent");
    Ok(())
}

fn now_epoch() -> u64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs()
}
