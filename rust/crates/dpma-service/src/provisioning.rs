use std::collections::HashMap;
use std::sync::Arc;

use serde::{Deserialize, Serialize};
use tokio::sync::RwLock;
use tracing::info;

/// Phone registration data discovered by MAC address.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Phone {
    pub mac_address: String,
    pub model: String,
    pub firmware_version: String,
    pub ip_address: Option<String>,
    pub extension: Option<String>,
    pub tenant_id: Option<String>,
    pub registered_at: Option<u64>,
    pub last_seen: Option<u64>,
}

/// Phone configuration assignment.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PhoneConfig {
    pub mac_address: String,
    pub extension: String,
    pub password: String,
    pub display_name: String,
    pub tenant_id: String,
    pub sip_server: String,
    pub sip_port: u16,
    pub transport: String,
    pub codecs: Vec<String>,
    pub line_keys: Vec<LineKey>,
    pub softkeys: Vec<SoftKey>,
    pub blf_keys: Vec<BlfKey>,
    pub tls_enabled: bool,
    pub srtp_enabled: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LineKey {
    pub index: u32,
    pub key_type: String,
    pub label: String,
    pub value: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SoftKey {
    pub index: u32,
    pub label: String,
    pub action: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BlfKey {
    pub index: u32,
    pub extension: String,
    pub label: String,
}

/// Firmware info for a phone model.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FirmwareInfo {
    pub model: String,
    pub version: String,
    pub filename: String,
    pub checksum: String,
    pub download_url: String,
}

/// Phone registration callback data.
#[derive(Debug, Clone, Deserialize)]
pub struct RegisterRequest {
    pub mac_address: String,
    pub model: String,
    pub firmware_version: String,
    pub ip_address: String,
}

/// Provisioning store that manages phone registrations and configurations.
pub struct ProvisioningStore {
    phones: Arc<RwLock<HashMap<String, Phone>>>,
    configs: Arc<RwLock<HashMap<String, PhoneConfig>>>,
    firmware: Arc<RwLock<HashMap<String, FirmwareInfo>>>,
}

impl ProvisioningStore {
    pub fn new() -> Self {
        let mut firmware = HashMap::new();

        // Default firmware entries for common Sangoma P-series models
        for (model, version) in &[
            ("P310", "4.1.0"),
            ("P315", "4.1.0"),
            ("P320", "4.1.0"),
            ("P325", "4.1.0"),
            ("P330", "4.1.0"),
            ("P370", "4.1.0"),
        ] {
            firmware.insert(
                model.to_string(),
                FirmwareInfo {
                    model: model.to_string(),
                    version: version.to_string(),
                    filename: format!("{}-{}.fw", model.to_lowercase(), version),
                    checksum: String::new(),
                    download_url: format!("/firmware/{}/{}-{}.fw", model, model.to_lowercase(), version),
                },
            );
        }

        ProvisioningStore {
            phones: Arc::new(RwLock::new(HashMap::new())),
            configs: Arc::new(RwLock::new(HashMap::new())),
            firmware: Arc::new(RwLock::new(firmware)),
        }
    }

    /// Register or update a phone by MAC address.
    pub async fn register_phone(&self, req: RegisterRequest) -> Phone {
        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs();

        let mac = normalize_mac(&req.mac_address);
        let mut phones = self.phones.write().await;

        let phone = phones.entry(mac.clone()).or_insert_with(|| Phone {
            mac_address: mac.clone(),
            model: req.model.clone(),
            firmware_version: req.firmware_version.clone(),
            ip_address: None,
            extension: None,
            tenant_id: None,
            registered_at: Some(now),
            last_seen: None,
        });

        phone.ip_address = Some(req.ip_address.clone());
        phone.firmware_version = req.firmware_version.clone();
        phone.model = req.model.clone();
        phone.last_seen = Some(now);

        // Check if there's an extension assignment
        let configs = self.configs.read().await;
        if let Some(config) = configs.get(&mac) {
            phone.extension = Some(config.extension.clone());
            phone.tenant_id = Some(config.tenant_id.clone());
        }

        info!(
            mac = %mac,
            model = %req.model,
            ip = %req.ip_address,
            "phone registered"
        );

        phone.clone()
    }

    /// Get a phone by MAC address.
    pub async fn get_phone(&self, mac: &str) -> Option<Phone> {
        let mac = normalize_mac(mac);
        self.phones.read().await.get(&mac).cloned()
    }

    /// List all registered phones.
    pub async fn list_phones(&self) -> Vec<Phone> {
        self.phones.read().await.values().cloned().collect()
    }

    /// Set or update phone configuration.
    pub async fn set_config(&self, config: PhoneConfig) {
        let mac = normalize_mac(&config.mac_address);
        let mut configs = self.configs.write().await;
        configs.insert(mac, config);
    }

    /// Get phone configuration by MAC address.
    pub async fn get_config(&self, mac: &str) -> Option<PhoneConfig> {
        let mac = normalize_mac(mac);
        self.configs.read().await.get(&mac).cloned()
    }

    /// Get firmware info for a model.
    pub async fn get_firmware(&self, model: &str) -> Option<FirmwareInfo> {
        self.firmware.read().await.get(model).cloned()
    }
}

/// Normalize MAC address to lowercase colon-separated format.
fn normalize_mac(mac: &str) -> String {
    let clean: String = mac
        .chars()
        .filter(|c| c.is_ascii_hexdigit())
        .collect::<String>()
        .to_lowercase();

    if clean.len() == 12 {
        format!(
            "{}:{}:{}:{}:{}:{}",
            &clean[0..2],
            &clean[2..4],
            &clean[4..6],
            &clean[6..8],
            &clean[8..10],
            &clean[10..12]
        )
    } else {
        clean
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_normalize_mac() {
        assert_eq!(normalize_mac("AA:BB:CC:DD:EE:FF"), "aa:bb:cc:dd:ee:ff");
        assert_eq!(normalize_mac("AABBCCDDEEFF"), "aa:bb:cc:dd:ee:ff");
        assert_eq!(normalize_mac("aa-bb-cc-dd-ee-ff"), "aa:bb:cc:dd:ee:ff");
    }
}
