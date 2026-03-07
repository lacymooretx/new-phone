use std::collections::HashMap;
use std::sync::Arc;

use anyhow::{Context, Result};
use redis::AsyncCommands;
use serde::{Deserialize, Serialize};
use tokio::sync::RwLock;
use tracing::{debug, error, info, warn};

use crate::blf::{BlfManager, BlfStatus};

// ---------------------------------------------------------------------------
// Data types
// ---------------------------------------------------------------------------

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

impl ParkingLot {
    /// Compute the BLF extension string for a given slot in this lot.
    pub fn extension_for_slot(&self, slot_number: u32) -> String {
        format!("{}{:02}", self.extension_base, slot_number)
    }
}

/// Request to park a call.
#[derive(Debug, Deserialize)]
pub struct ParkRequest {
    pub call_uuid: String,
    pub caller_id: Option<String>,
    pub callee_id: Option<String>,
    pub parked_by: String,
    pub timeout: Option<u64>,
    pub tenant_id: Option<String>,
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

// ---------------------------------------------------------------------------
// ESL connection pool
// ---------------------------------------------------------------------------

/// A simple pool of raw ESL TCP connections.
///
/// Connections are authenticated on creation and returned to the pool after
/// use.  If a command fails the connection is dropped rather than returned.
struct EslConnection {
    stream: tokio::net::TcpStream,
}

impl EslConnection {
    async fn connect(addr: &str, password: &str) -> Result<Self> {
        use tokio::io::{AsyncReadExt, AsyncWriteExt};

        let mut stream = tokio::net::TcpStream::connect(addr)
            .await
            .context("ESL: failed to connect")?;

        // Read greeting
        let mut buf = [0u8; 4096];
        let _ = stream.read(&mut buf).await?;

        // Authenticate
        let auth = format!("auth {}\n\n", password);
        stream.write_all(auth.as_bytes()).await?;
        let n = stream.read(&mut buf).await?;
        let resp = String::from_utf8_lossy(&buf[..n]);
        if resp.contains("-ERR") {
            anyhow::bail!("ESL auth failed: {}", resp.trim());
        }

        Ok(EslConnection { stream })
    }

    /// Send a single ESL command and read the response.
    async fn execute(&mut self, command: &str) -> Result<String> {
        use tokio::io::{AsyncReadExt, AsyncWriteExt};

        let cmd = format!("{}\n\n", command);
        self.stream.write_all(cmd.as_bytes()).await?;
        let mut buf = [0u8; 8192];
        let n = self.stream.read(&mut buf).await?;
        Ok(String::from_utf8_lossy(&buf[..n]).to_string())
    }
}

pub struct EslPool {
    addr: String,
    password: String,
    max_size: usize,
    connections: tokio::sync::Mutex<Vec<EslConnection>>,
}

impl EslPool {
    pub fn new(addr: String, password: String, max_size: usize) -> Self {
        EslPool {
            addr,
            password,
            max_size,
            connections: tokio::sync::Mutex::new(Vec::with_capacity(max_size)),
        }
    }

    /// Acquire a connection from the pool or create a new one.
    async fn acquire(&self) -> Result<EslConnection> {
        {
            let mut pool = self.connections.lock().await;
            if let Some(conn) = pool.pop() {
                return Ok(conn);
            }
        }
        EslConnection::connect(&self.addr, &self.password).await
    }

    /// Return a connection to the pool (if pool isn't full, else drop it).
    async fn release(&self, conn: EslConnection) {
        let mut pool = self.connections.lock().await;
        if pool.len() < self.max_size {
            pool.push(conn);
        }
        // else: connection is dropped
    }

    /// Execute a command, acquiring a connection from the pool.
    /// On failure the connection is discarded.
    pub async fn execute(&self, command: &str) -> Result<String> {
        let mut conn = self.acquire().await?;
        match conn.execute(command).await {
            Ok(resp) => {
                self.release(conn).await;
                Ok(resp)
            }
            Err(e) => {
                // Don't return broken connections to the pool.
                Err(e)
            }
        }
    }

    /// Check if ESL is reachable by connecting and authenticating.
    pub async fn health_check(&self) -> bool {
        match EslConnection::connect(&self.addr, &self.password).await {
            Ok(conn) => {
                self.release(conn).await;
                true
            }
            Err(_) => false,
        }
    }
}

// ---------------------------------------------------------------------------
// Parking Manager
// ---------------------------------------------------------------------------

/// The parking manager handles all parking operations.
pub struct ParkingManager {
    lots: Arc<RwLock<HashMap<String, ParkingLot>>>,
    redis_conn: redis::aio::ConnectionManager,
    redis_client: redis::Client,
    esl_pool: Arc<EslPool>,
    default_timeout: u64,
    default_slots: u32,
    blf: Arc<BlfManager>,
}

impl ParkingManager {
    pub async fn new(
        redis_url: &str,
        esl_host: &str,
        esl_port: u16,
        esl_password: &str,
        default_timeout: u64,
        default_slots: u32,
        esl_pool_size: usize,
        blf: Arc<BlfManager>,
    ) -> Result<Self> {
        let redis_client = redis::Client::open(redis_url)
            .context("failed to create Redis client")?;

        let redis_conn = redis_client
            .get_connection_manager()
            .await
            .context("failed to create Redis connection manager")?;

        let esl_addr = format!("{}:{}", esl_host, esl_port);
        let esl_pool = Arc::new(EslPool::new(
            esl_addr,
            esl_password.to_string(),
            esl_pool_size,
        ));

        Ok(ParkingManager {
            lots: Arc::new(RwLock::new(HashMap::new())),
            redis_conn,
            redis_client,
            esl_pool,
            default_timeout,
            default_slots,
            blf,
        })
    }

    /// Access the Redis client (for health checks, pub/sub, etc.).
    pub fn redis_client(&self) -> &redis::Client {
        &self.redis_client
    }

    /// Access the ESL pool (for health checks).
    pub fn esl_pool(&self) -> &Arc<EslPool> {
        &self.esl_pool
    }

    // -----------------------------------------------------------------------
    // Redis state recovery
    // -----------------------------------------------------------------------

    /// Load all parking lot state from Redis.  Called on startup to survive
    /// restarts.
    pub async fn recover_from_redis(&self) -> Result<()> {
        let mut conn = self.redis_conn.clone();

        // Scan for all np:parking:* keys
        let keys: Vec<String> = redis::cmd("KEYS")
            .arg("np:parking:*")
            .query_async(&mut conn)
            .await
            .context("failed to scan parking keys from Redis")?;

        if keys.is_empty() {
            info!("no parking state found in Redis — starting fresh");
            return Ok(());
        }

        let mut lots = self.lots.write().await;
        let mut recovered = 0u32;

        for key in &keys {
            let value: Option<String> = conn.get(key).await.ok();
            if let Some(json) = value {
                match serde_json::from_str::<ParkingLot>(&json) {
                    Ok(lot) => {
                        let occupied = lot.slots.iter().filter(|s| s.occupied).count();
                        info!(
                            lot_id = %lot.lot_id,
                            tenant_id = %lot.tenant_id,
                            slots = lot.slots.len(),
                            occupied = occupied,
                            "recovered parking lot from Redis"
                        );
                        lots.insert(lot.lot_id.clone(), lot);
                        recovered += 1;
                    }
                    Err(e) => {
                        warn!(key = %key, error = %e, "failed to deserialize parking lot from Redis, skipping");
                    }
                }
            }
        }

        info!(recovered = recovered, "parking state recovery complete");
        Ok(())
    }

    /// Rebuild BLF state from current in-memory lots after recovery.
    pub async fn rebuild_blf_state(&self) {
        let lots = self.lots.read().await;
        for lot in lots.values() {
            for slot in &lot.slots {
                let extension = lot.extension_for_slot(slot.slot_number);
                if slot.occupied {
                    self.blf
                        .update_state(
                            &extension,
                            BlfStatus::InUse,
                            slot.caller_id.clone(),
                        )
                        .await;
                } else {
                    self.blf
                        .update_state(&extension, BlfStatus::Idle, None)
                        .await;
                }
            }
        }
    }

    // -----------------------------------------------------------------------
    // Lot management
    // -----------------------------------------------------------------------

    /// Ensure a parking lot exists, creating it if needed.
    pub async fn ensure_lot(&self, lot_id: &str, tenant_id: &str) {
        let mut lots = self.lots.write().await;
        if !lots.contains_key(lot_id) {
            let extension_base = format!(
                "7{}",
                lot_id.chars().filter(|c| c.is_ascii_digit()).collect::<String>()
            );
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

            let lot = ParkingLot {
                lot_id: lot_id.to_string(),
                tenant_id: tenant_id.to_string(),
                extension_base,
                slots,
            };

            // Persist to Redis
            let lot_clone = lot.clone();
            let mut conn = self.redis_conn.clone();
            tokio::spawn(async move {
                if let Err(e) = save_lot_to_redis(&mut conn, &lot_clone).await {
                    warn!(error = %e, "failed to save new parking lot to Redis");
                }
            });

            lots.insert(lot_id.to_string(), lot);
            info!(lot_id = lot_id, tenant_id = tenant_id, "parking lot created");
        }
    }

    // -----------------------------------------------------------------------
    // Park / Retrieve / Release
    // -----------------------------------------------------------------------

    /// Park a call in the first available slot.
    pub async fn park_call(&self, lot_id: &str, request: ParkRequest) -> Result<ParkResult> {
        let now = now_epoch();
        let timeout = request.timeout.unwrap_or(self.default_timeout);

        let (slot_number, extension, lot_clone, call_uuid) = {
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
            let extension = lot.extension_for_slot(slot_number);

            info!(
                lot_id = lot_id,
                slot = slot_number,
                call_uuid = %request.call_uuid,
                parked_by = %request.parked_by,
                extension = %extension,
                "call parked"
            );

            (slot_number, extension, lot.clone(), request.call_uuid.clone())
        };
        // Lock released here

        // Extract caller_id before moving lot_clone
        let caller_id = lot_clone
            .slots
            .iter()
            .find(|s| s.slot_number == slot_number)
            .and_then(|s| s.caller_id.clone());

        // Persist state to Redis (fire-and-forget)
        let mut conn = self.redis_conn.clone();
        tokio::spawn(async move {
            if let Err(e) = save_lot_to_redis(&mut conn, &lot_clone).await {
                warn!(error = %e, "failed to save parking state to Redis");
            }
        });

        // Send ESL park command via pool
        let pool = self.esl_pool.clone();
        let uuid = call_uuid;
        tokio::spawn(async move {
            let cmd = format!(
                "api uuid_transfer {} -both park+${{parking_lot_range}} inline",
                uuid
            );
            if let Err(e) = pool.execute(&cmd).await {
                warn!(error = %e, call_uuid = %uuid, "failed to send ESL park command");
            }
        });

        // Update BLF state
        self.blf
            .update_state(&extension, BlfStatus::InUse, caller_id)
            .await;

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
    ) -> Result<(String, String)> {
        let (call_uuid, extension, lot_clone) = {
            let mut lots = self.lots.write().await;
            let lot = lots
                .get_mut(lot_id)
                .ok_or_else(|| anyhow::anyhow!("parking lot {} not found", lot_id))?;

            let extension = lot.extension_for_slot(slot_number);

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

            (call_uuid, extension, lot.clone())
        };
        // Lock released here

        // Update Redis
        let mut conn = self.redis_conn.clone();
        let lot_for_redis = lot_clone;
        tokio::spawn(async move {
            if let Err(e) = save_lot_to_redis(&mut conn, &lot_for_redis).await {
                warn!(error = %e, "failed to save parking state to Redis");
            }
        });

        // Send ESL retrieve command via pool
        let pool = self.esl_pool.clone();
        let uuid = call_uuid.clone();
        let dest = request.retrieved_by.clone();
        tokio::spawn(async move {
            let cmd = format!("api uuid_transfer {} -both {} XML default", uuid, dest);
            if let Err(e) = pool.execute(&cmd).await {
                warn!(error = %e, call_uuid = %uuid, "failed to send ESL retrieve command");
            }
        });

        // Update BLF to idle
        self.blf
            .update_state(&extension, BlfStatus::Idle, None)
            .await;

        Ok((call_uuid, extension))
    }

    /// Force-release a slot without retrieving the call.
    pub async fn force_release(&self, lot_id: &str, slot_number: u32) -> Result<String> {
        let (uuid_to_hangup, extension, lot_clone) = {
            let mut lots = self.lots.write().await;
            let lot = lots
                .get_mut(lot_id)
                .ok_or_else(|| anyhow::anyhow!("parking lot {} not found", lot_id))?;

            let extension = lot.extension_for_slot(slot_number);

            let slot = lot
                .slots
                .iter_mut()
                .find(|s| s.slot_number == slot_number)
                .ok_or_else(|| anyhow::anyhow!("slot {} not found", slot_number))?;

            let uuid_to_hangup = if slot.occupied {
                let uuid = slot.call_uuid.clone();

                slot.occupied = false;
                slot.call_uuid = None;
                slot.caller_id = None;
                slot.callee_id = None;
                slot.parked_by = None;
                slot.parked_at = None;
                slot.timeout_at = None;

                info!(lot_id = lot_id, slot = slot_number, "slot force-released");
                uuid
            } else {
                None
            };

            (uuid_to_hangup, extension, lot.clone())
        };
        // Lock released here

        // Hangup the call if there was one
        if let Some(uuid) = uuid_to_hangup {
            let pool = self.esl_pool.clone();
            let uuid_clone = uuid.clone();
            tokio::spawn(async move {
                let cmd = format!("api uuid_kill {} NORMAL_CLEARING", uuid_clone);
                if let Err(e) = pool.execute(&cmd).await {
                    warn!(error = %e, "failed to hangup parked call");
                }
            });
        }

        // Update Redis
        let mut conn = self.redis_conn.clone();
        tokio::spawn(async move {
            if let Err(e) = save_lot_to_redis(&mut conn, &lot_clone).await {
                warn!(error = %e, "failed to save parking state to Redis");
            }
        });

        // Update BLF to idle
        self.blf
            .update_state(&extension, BlfStatus::Idle, None)
            .await;

        Ok(extension)
    }

    // -----------------------------------------------------------------------
    // Query
    // -----------------------------------------------------------------------

    /// Get all slots for a parking lot.
    pub async fn get_slots(&self, lot_id: &str) -> Option<Vec<ParkingSlot>> {
        let lots = self.lots.read().await;
        lots.get(lot_id).map(|l| l.slots.clone())
    }

    /// Get a parking lot by ID.
    pub async fn get_lot(&self, lot_id: &str) -> Option<ParkingLot> {
        let lots = self.lots.read().await;
        lots.get(lot_id).cloned()
    }

    /// List all parking lots.
    pub async fn list_lots(&self) -> Vec<ParkingLot> {
        let lots = self.lots.read().await;
        lots.values().cloned().collect()
    }

    /// Count total active (occupied) slots across all lots.
    pub async fn active_call_count(&self) -> usize {
        let lots = self.lots.read().await;
        lots.values()
            .flat_map(|lot| lot.slots.iter())
            .filter(|slot| slot.occupied)
            .count()
    }

    // -----------------------------------------------------------------------
    // Timeout checker
    // -----------------------------------------------------------------------

    /// Check for timed-out parked calls and handle them.
    ///
    /// This method first collects timed-out calls under a read lock, then
    /// releases the lock before performing any async ESL operations.
    pub async fn check_timeouts(&self) {
        let now = now_epoch();

        // Phase 1: collect timed-out calls under a write lock and clear them
        let timed_out: Vec<(String, u32, String, String, String)>;
        {
            let mut lots = self.lots.write().await;
            let mut collected = Vec::new();

            for lot in lots.values_mut() {
                let lot_id = lot.lot_id.clone();
                let ext_base = lot.extension_base.clone();

                for slot in &mut lot.slots {
                    if slot.occupied {
                        if let Some(timeout_at) = slot.timeout_at {
                            if now >= timeout_at {
                                if let (Some(uuid), Some(parker)) =
                                    (&slot.call_uuid, &slot.parked_by)
                                {
                                    let extension = format!(
                                        "{}{:02}",
                                        ext_base, slot.slot_number
                                    );
                                    collected.push((
                                        lot_id.clone(),
                                        slot.slot_number,
                                        uuid.clone(),
                                        parker.clone(),
                                        extension,
                                    ));
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

            // Persist updated lot state for any lots that had timeouts
            if !collected.is_empty() {
                let lot_ids: Vec<String> =
                    collected.iter().map(|(lid, ..)| lid.clone()).collect();
                for lid in &lot_ids {
                    if let Some(lot) = lots.get(lid) {
                        let mut conn = self.redis_conn.clone();
                        let lot_clone = lot.clone();
                        tokio::spawn(async move {
                            if let Err(e) = save_lot_to_redis(&mut conn, &lot_clone).await {
                                warn!(error = %e, "failed to save parking state after timeout");
                            }
                        });
                    }
                }
            }

            timed_out = collected;
        }
        // Write lock released here

        // Phase 2: perform ESL operations without holding the lock
        for (lot_id, slot_number, uuid, parker, extension) in timed_out {
            info!(
                lot_id = %lot_id,
                slot = slot_number,
                call_uuid = %uuid,
                return_to = %parker,
                "parking timeout — returning call to parker"
            );

            // Return the call to the person who parked it via ESL
            let pool = self.esl_pool.clone();
            let uuid_clone = uuid.clone();
            let parker_clone = parker.clone();
            tokio::spawn(async move {
                let cmd = format!(
                    "api uuid_transfer {} -both {} XML default",
                    uuid_clone, parker_clone
                );
                if let Err(e) = pool.execute(&cmd).await {
                    error!(
                        error = %e,
                        call_uuid = %uuid_clone,
                        return_to = %parker_clone,
                        "failed to return timed-out call to parker"
                    );
                }
            });

            // Update BLF to idle
            self.blf
                .update_state(&extension, BlfStatus::Idle, None)
                .await;
        }
    }
}

// ---------------------------------------------------------------------------
// Redis helpers
// ---------------------------------------------------------------------------

async fn save_lot_to_redis(conn: &mut redis::aio::ConnectionManager, lot: &ParkingLot) -> Result<()> {
    let key = format!("np:parking:{}", lot.lot_id);
    let value = serde_json::to_string(lot).context("failed to serialize lot")?;
    conn.set::<_, _, ()>(&key, &value)
        .await
        .context("failed to set parking state in Redis")?;
    debug!(key = %key, "saved parking state to Redis");
    Ok(())
}

/// Check if Redis is reachable via a PING.
pub async fn redis_health_check(client: &redis::Client) -> bool {
    match client.get_connection_manager().await {
        Ok(mut conn) => {
            let result: Result<String, _> = redis::cmd("PING")
                .query_async(&mut conn)
                .await;
            result.is_ok()
        }
        Err(_) => false,
    }
}

fn now_epoch() -> u64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs()
}
