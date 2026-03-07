//! SRTP/SRTCP implementation per RFC 3711.
//!
//! Profile: AES_CM_128_HMAC_SHA1_80
//!   - AES-128 in Counter Mode (AES-CM) for encryption
//!   - HMAC-SHA1 with 80-bit (10-byte) tag for authentication
//!   - Key derivation using AES-CM as a PRF
//!
//! Master key: 16 bytes, Master salt: 14 bytes.

use aes::cipher::{BlockEncrypt, KeyInit};
use aes::Aes128;
use hmac::{Hmac, Mac};
use sha1::Sha1;
use thiserror::Error;

type HmacSha1 = Hmac<Sha1>;

/// SRTP authentication tag length (80 bits = 10 bytes).
const SRTP_AUTH_TAG_LEN: usize = 10;

/// SRTCP authentication tag length (80 bits = 10 bytes).
const SRTCP_AUTH_TAG_LEN: usize = 10;

/// AES block size.
const AES_BLOCK_SIZE: usize = 16;

/// Master key length for AES-128.
const MASTER_KEY_LEN: usize = 16;

/// Master salt length per RFC 3711.
const MASTER_SALT_LEN: usize = 14;

/// Session encryption key length.
const SESSION_KEY_LEN: usize = 16;

/// Session salt length.
const SESSION_SALT_LEN: usize = 14;

/// Session authentication key length (HMAC-SHA1 uses 20-byte key).
const SESSION_AUTH_KEY_LEN: usize = 20;

/// KDF labels per RFC 3711 Section 4.3.1.
const LABEL_SRTP_ENCRYPTION: u8 = 0x00;
const LABEL_SRTP_AUTH: u8 = 0x01;
const LABEL_SRTP_SALT: u8 = 0x02;
const LABEL_SRTCP_ENCRYPTION: u8 = 0x03;
const LABEL_SRTCP_AUTH: u8 = 0x04;
const LABEL_SRTCP_SALT: u8 = 0x05;

#[derive(Error, Debug)]
pub enum SrtpError {
    #[error("invalid key length: expected {expected}, got {got}")]
    InvalidKeyLength { expected: usize, got: usize },
    #[error("encryption failed: {0}")]
    EncryptionFailed(String),
    #[error("decryption failed: {0}")]
    DecryptionFailed(String),
    #[error("authentication failed")]
    AuthenticationFailed,
    #[error("invalid packet")]
    InvalidPacket,
    #[error("replay detected: packet index {0}")]
    ReplayDetected(u64),
}

/// Anti-replay sliding window (64-bit window, tracks last 64 sequence numbers).
#[derive(Debug, Clone)]
struct ReplayWindow {
    /// The highest validated packet index so far.
    top: u64,
    /// Bitmask for the 64 indices below `top`.
    bitmap: u64,
}

impl ReplayWindow {
    fn new() -> Self {
        ReplayWindow {
            top: 0,
            bitmap: 0,
        }
    }

    /// Check if a packet index has already been seen. Returns true if OK (not a replay).
    fn check(&self, index: u64) -> bool {
        if index > self.top {
            return true; // ahead of window, always OK
        }
        let diff = self.top - index;
        if diff >= 64 {
            return false; // too old, outside window
        }
        // Check if bit is already set
        (self.bitmap & (1u64 << diff)) == 0
    }

    /// Mark a packet index as received. Call only after check() returns true.
    fn update(&mut self, index: u64) {
        if index > self.top {
            let shift = index - self.top;
            if shift >= 64 {
                self.bitmap = 0;
            } else {
                self.bitmap <<= shift;
            }
            self.bitmap |= 1; // mark the new top
            self.top = index;
        } else {
            let diff = self.top - index;
            if diff < 64 {
                self.bitmap |= 1u64 << diff;
            }
        }
    }
}

/// SRTP crypto context for AES_CM_128_HMAC_SHA1_80.
///
/// Handles both SRTP (RTP) and SRTCP (RTCP) protection/unprotection.
pub struct SrtpContext {
    // -- SRTP session keys --
    /// Derived session encryption key (16 bytes)
    srtp_session_key: [u8; SESSION_KEY_LEN],
    /// Derived session salt (14 bytes)
    srtp_session_salt: [u8; SESSION_SALT_LEN],
    /// Derived authentication key (20 bytes)
    srtp_auth_key: [u8; SESSION_AUTH_KEY_LEN],

    // -- SRTCP session keys --
    /// Derived SRTCP encryption key (16 bytes)
    srtcp_session_key: [u8; SESSION_KEY_LEN],
    /// Derived SRTCP salt (14 bytes)
    srtcp_session_salt: [u8; SESSION_SALT_LEN],
    /// Derived SRTCP authentication key (20 bytes)
    srtcp_auth_key: [u8; SESSION_AUTH_KEY_LEN],

    /// Rollover counter for SRTP (extended sequence number tracking)
    roc: u32,
    /// Last seen sequence number (for ROC estimation)
    last_seq: Option<u16>,
    /// SRTCP index counter (31-bit, incremented per SRTCP packet)
    srtcp_index: u32,

    /// Anti-replay window for SRTP
    srtp_replay: ReplayWindow,
    /// Anti-replay window for SRTCP
    srtcp_replay: ReplayWindow,
}

impl SrtpContext {
    /// Create a new SRTP context from master key and master salt.
    ///
    /// - `master_key`: 16 bytes (128-bit AES key)
    /// - `master_salt`: 14 bytes
    pub fn new(master_key: &[u8], master_salt: &[u8]) -> Result<Self, SrtpError> {
        if master_key.len() != MASTER_KEY_LEN {
            return Err(SrtpError::InvalidKeyLength {
                expected: MASTER_KEY_LEN,
                got: master_key.len(),
            });
        }
        if master_salt.len() != MASTER_SALT_LEN {
            return Err(SrtpError::InvalidKeyLength {
                expected: MASTER_SALT_LEN,
                got: master_salt.len(),
            });
        }

        // Derive SRTP session keys (RFC 3711 Section 4.3.1)
        let srtp_session_key =
            kdf_derive(master_key, master_salt, LABEL_SRTP_ENCRYPTION, 0, SESSION_KEY_LEN)?;
        let srtp_session_salt =
            kdf_derive(master_key, master_salt, LABEL_SRTP_SALT, 0, SESSION_SALT_LEN)?;
        let srtp_auth_key =
            kdf_derive(master_key, master_salt, LABEL_SRTP_AUTH, 0, SESSION_AUTH_KEY_LEN)?;

        // Derive SRTCP session keys
        let srtcp_session_key =
            kdf_derive(master_key, master_salt, LABEL_SRTCP_ENCRYPTION, 0, SESSION_KEY_LEN)?;
        let srtcp_session_salt =
            kdf_derive(master_key, master_salt, LABEL_SRTCP_SALT, 0, SESSION_SALT_LEN)?;
        let srtcp_auth_key =
            kdf_derive(master_key, master_salt, LABEL_SRTCP_AUTH, 0, SESSION_AUTH_KEY_LEN)?;

        let mut sk = [0u8; SESSION_KEY_LEN];
        sk.copy_from_slice(&srtp_session_key);
        let mut ss = [0u8; SESSION_SALT_LEN];
        ss.copy_from_slice(&srtp_session_salt);
        let mut sa = [0u8; SESSION_AUTH_KEY_LEN];
        sa.copy_from_slice(&srtp_auth_key);

        let mut ck = [0u8; SESSION_KEY_LEN];
        ck.copy_from_slice(&srtcp_session_key);
        let mut cs = [0u8; SESSION_SALT_LEN];
        cs.copy_from_slice(&srtcp_session_salt);
        let mut ca = [0u8; SESSION_AUTH_KEY_LEN];
        ca.copy_from_slice(&srtcp_auth_key);

        Ok(SrtpContext {
            srtp_session_key: sk,
            srtp_session_salt: ss,
            srtp_auth_key: sa,
            srtcp_session_key: ck,
            srtcp_session_salt: cs,
            srtcp_auth_key: ca,
            roc: 0,
            last_seq: None,
            srtcp_index: 0,
            srtp_replay: ReplayWindow::new(),
            srtcp_replay: ReplayWindow::new(),
        })
    }

    /// Protect (encrypt + authenticate) an RTP packet, producing an SRTP packet.
    ///
    /// Input: plaintext RTP packet (header + payload).
    /// Output: SRTP packet (header + encrypted payload + 10-byte auth tag).
    pub fn protect(&mut self, rtp_packet: &[u8]) -> Result<Vec<u8>, SrtpError> {
        if rtp_packet.len() < 12 {
            return Err(SrtpError::InvalidPacket);
        }

        let header_len = rtp_header_length(rtp_packet)?;
        let header = &rtp_packet[..header_len];
        let payload = &rtp_packet[header_len..];

        let seq = u16::from_be_bytes([rtp_packet[2], rtp_packet[3]]);
        let ssrc = u32::from_be_bytes([rtp_packet[8], rtp_packet[9], rtp_packet[10], rtp_packet[11]]);

        // Update ROC based on sequence number
        self.update_roc_for_send(seq);
        let packet_index = ((self.roc as u64) << 16) | (seq as u64);

        // Encrypt payload with AES-CM
        let encrypted_payload = aes_cm_encrypt(
            &self.srtp_session_key,
            &self.srtp_session_salt,
            ssrc,
            packet_index,
            payload,
        )?;

        // Build SRTP packet: original header + encrypted payload
        let mut srtp_packet = Vec::with_capacity(header.len() + encrypted_payload.len() + SRTP_AUTH_TAG_LEN);
        srtp_packet.extend_from_slice(header);
        srtp_packet.extend_from_slice(&encrypted_payload);

        // Compute HMAC-SHA1 auth tag over (header + encrypted_payload || ROC)
        let tag = compute_srtp_auth_tag(&self.srtp_auth_key, &srtp_packet, self.roc)?;
        srtp_packet.extend_from_slice(&tag);

        Ok(srtp_packet)
    }

    /// Unprotect (verify + decrypt) an SRTP packet, producing a plaintext RTP packet.
    ///
    /// Input: SRTP packet (header + encrypted payload + 10-byte auth tag).
    /// Output: plaintext RTP packet (header + payload).
    pub fn unprotect(&mut self, srtp_packet: &[u8]) -> Result<Vec<u8>, SrtpError> {
        // Minimum: 12 header + 0 payload + 10 auth tag
        if srtp_packet.len() < 12 + SRTP_AUTH_TAG_LEN {
            return Err(SrtpError::InvalidPacket);
        }

        let auth_tag_offset = srtp_packet.len() - SRTP_AUTH_TAG_LEN;
        let packet_data = &srtp_packet[..auth_tag_offset];
        let received_tag = &srtp_packet[auth_tag_offset..];

        let seq = u16::from_be_bytes([packet_data[2], packet_data[3]]);

        // Estimate ROC for this packet
        let estimated_roc = self.estimate_roc(seq);
        let packet_index = ((estimated_roc as u64) << 16) | (seq as u64);

        // Verify authentication tag
        let computed_tag = compute_srtp_auth_tag(&self.srtp_auth_key, packet_data, estimated_roc)?;
        if !constant_time_eq(received_tag, &computed_tag) {
            return Err(SrtpError::AuthenticationFailed);
        }

        // Anti-replay check
        if !self.srtp_replay.check(packet_index) {
            return Err(SrtpError::ReplayDetected(packet_index));
        }

        // Decrypt payload
        let header_len = rtp_header_length(packet_data)?;
        let header = &packet_data[..header_len];
        let encrypted_payload = &packet_data[header_len..];

        let ssrc = u32::from_be_bytes([
            packet_data[8],
            packet_data[9],
            packet_data[10],
            packet_data[11],
        ]);

        let decrypted_payload = aes_cm_encrypt(
            &self.srtp_session_key,
            &self.srtp_session_salt,
            ssrc,
            packet_index,
            encrypted_payload,
        )?;

        // Update ROC and replay window only after successful auth + decrypt
        self.update_roc_for_recv(seq, estimated_roc);
        self.srtp_replay.update(packet_index);

        let mut rtp_packet = Vec::with_capacity(header.len() + decrypted_payload.len());
        rtp_packet.extend_from_slice(header);
        rtp_packet.extend_from_slice(&decrypted_payload);

        Ok(rtp_packet)
    }

    /// Protect an RTCP packet, producing an SRTCP packet.
    ///
    /// Input: plaintext RTCP compound packet.
    /// Output: SRTCP packet (header + encrypted payload + E-flag||SRTCP-index(4 bytes) + 10-byte auth tag).
    pub fn protect_rtcp(&mut self, rtcp_packet: &[u8]) -> Result<Vec<u8>, SrtpError> {
        // RTCP header is 8 bytes minimum (version, padding, RC, PT, length, SSRC)
        if rtcp_packet.len() < 8 {
            return Err(SrtpError::InvalidPacket);
        }

        // RTCP header is always first 8 bytes (fixed for encryption boundary)
        let header_len = 8;
        let header = &rtcp_packet[..header_len];
        let payload = &rtcp_packet[header_len..];

        let ssrc = u32::from_be_bytes([rtcp_packet[4], rtcp_packet[5], rtcp_packet[6], rtcp_packet[7]]);

        // SRTCP index with E-flag set (bit 31 = 1 means encrypted)
        let srtcp_index_with_e = self.srtcp_index | 0x8000_0000;

        // Encrypt payload with AES-CM using SRTCP keys
        // For SRTCP, the "packet index" is the SRTCP index (31 bits)
        let encrypted_payload = aes_cm_encrypt(
            &self.srtcp_session_key,
            &self.srtcp_session_salt,
            ssrc,
            self.srtcp_index as u64,
            payload,
        )?;

        // Build SRTCP packet: header + encrypted_payload + E||SRTCP_index
        let mut srtcp_packet = Vec::with_capacity(
            header.len() + encrypted_payload.len() + 4 + SRTCP_AUTH_TAG_LEN,
        );
        srtcp_packet.extend_from_slice(header);
        srtcp_packet.extend_from_slice(&encrypted_payload);
        srtcp_packet.extend_from_slice(&srtcp_index_with_e.to_be_bytes());

        // Compute auth tag over the entire SRTCP packet (including E||index)
        let tag = compute_srtcp_auth_tag(&self.srtcp_auth_key, &srtcp_packet)?;
        srtcp_packet.extend_from_slice(&tag);

        // Increment SRTCP index (wraps at 2^31 - 1)
        self.srtcp_index = (self.srtcp_index + 1) & 0x7FFF_FFFF;

        Ok(srtcp_packet)
    }

    /// Unprotect an SRTCP packet, producing a plaintext RTCP packet.
    ///
    /// Input: SRTCP packet (header + encrypted payload + E||SRTCP-index(4 bytes) + 10-byte auth tag).
    /// Output: plaintext RTCP compound packet.
    pub fn unprotect_rtcp(&mut self, srtcp_packet: &[u8]) -> Result<Vec<u8>, SrtpError> {
        // Minimum: 8 header + 0 payload + 4 E||index + 10 auth tag = 22
        if srtcp_packet.len() < 8 + 4 + SRTCP_AUTH_TAG_LEN {
            return Err(SrtpError::InvalidPacket);
        }

        let auth_tag_offset = srtcp_packet.len() - SRTCP_AUTH_TAG_LEN;
        let packet_data = &srtcp_packet[..auth_tag_offset];
        let received_tag = &srtcp_packet[auth_tag_offset..];

        // Verify auth tag (covers everything before the tag, including E||index)
        let computed_tag = compute_srtcp_auth_tag(&self.srtcp_auth_key, packet_data)?;
        if !constant_time_eq(received_tag, &computed_tag) {
            return Err(SrtpError::AuthenticationFailed);
        }

        // Extract E-flag and SRTCP index (last 4 bytes of packet_data)
        let e_index_offset = packet_data.len() - 4;
        let e_index = u32::from_be_bytes([
            packet_data[e_index_offset],
            packet_data[e_index_offset + 1],
            packet_data[e_index_offset + 2],
            packet_data[e_index_offset + 3],
        ]);
        let is_encrypted = (e_index & 0x8000_0000) != 0;
        let srtcp_index = e_index & 0x7FFF_FFFF;

        // Anti-replay check
        if !self.srtcp_replay.check(srtcp_index as u64) {
            return Err(SrtpError::ReplayDetected(srtcp_index as u64));
        }

        let rtcp_data = &packet_data[..e_index_offset];

        let ssrc = u32::from_be_bytes([rtcp_data[4], rtcp_data[5], rtcp_data[6], rtcp_data[7]]);
        let header_len = 8;
        let header = &rtcp_data[..header_len];
        let encrypted_payload = &rtcp_data[header_len..];

        let decrypted_payload = if is_encrypted {
            aes_cm_encrypt(
                &self.srtcp_session_key,
                &self.srtcp_session_salt,
                ssrc,
                srtcp_index as u64,
                encrypted_payload,
            )?
        } else {
            encrypted_payload.to_vec()
        };

        self.srtcp_replay.update(srtcp_index as u64);

        let mut rtcp_packet = Vec::with_capacity(header.len() + decrypted_payload.len());
        rtcp_packet.extend_from_slice(header);
        rtcp_packet.extend_from_slice(&decrypted_payload);

        Ok(rtcp_packet)
    }

    /// Estimate the ROC for a received packet based on its sequence number.
    /// Per RFC 3711 Section 3.3.1.
    fn estimate_roc(&self, seq: u16) -> u32 {
        match self.last_seq {
            None => self.roc,
            Some(last) => {
                let s_l = last;
                if seq < s_l {
                    // Sequence wrapped or is significantly lower
                    if (s_l as i32 - seq as i32) > 0x8000 {
                        // Sequence wrapped forward
                        self.roc.wrapping_add(1)
                    } else {
                        self.roc
                    }
                } else if (seq as i32 - s_l as i32) > 0x8000 {
                    // Sequence wrapped backward (late packet from previous ROC)
                    self.roc.wrapping_sub(1)
                } else {
                    self.roc
                }
            }
        }
    }

    /// Update ROC state after successfully receiving a packet.
    fn update_roc_for_recv(&mut self, seq: u16, estimated_roc: u32) {
        if estimated_roc > self.roc || (estimated_roc == self.roc && Some(seq) > self.last_seq) {
            self.roc = estimated_roc;
            self.last_seq = Some(seq);
        }
    }

    /// Update ROC state for a packet being sent.
    fn update_roc_for_send(&mut self, seq: u16) {
        if let Some(last) = self.last_seq {
            if seq < last && (last as i32 - seq as i32) > 0x8000 {
                self.roc = self.roc.wrapping_add(1);
            }
        }
        self.last_seq = Some(seq);
    }

    /// Get the current ROC value (for testing / diagnostics).
    pub fn roc(&self) -> u32 {
        self.roc
    }
}

// ---------------------------------------------------------------------------
// AES-CM (Counter Mode) per RFC 3711 Section 4.1.1
// ---------------------------------------------------------------------------

/// AES-CM encrypt/decrypt. Since CTR mode is its own inverse, this function
/// serves for both encryption and decryption.
///
/// IV construction per RFC 3711:
///   IV[0..1]  = 0
///   IV[2..5]  = (ssrc XOR session_salt[2..5])  -- note: salt is 14 bytes placed at [2..15]
///   IV[6..13] = (packet_index XOR session_salt[6..13])
///   IV[14..15] = block_counter (set per block during keystream generation)
///
/// Actually per RFC 3711 Section 4.1.1, the IV is:
///   IV = (session_salt XOR (label=0 || r || index || 0...)) but for SRTP packet encryption
///   the IV is constructed differently from the KDF IV.
///
/// For SRTP packet encryption (Section 4.1.1):
///   IV = session_salt[0..13] padded to 16 bytes, then XOR with:
///     bytes 4-7: SSRC
///     bytes 8-13: packet_index (48 bits)
fn aes_cm_encrypt(
    session_key: &[u8],
    session_salt: &[u8],
    ssrc: u32,
    packet_index: u64,
    data: &[u8],
) -> Result<Vec<u8>, SrtpError> {
    if data.is_empty() {
        return Ok(Vec::new());
    }

    // Build IV (16 bytes)
    let mut iv = [0u8; AES_BLOCK_SIZE];
    // Place session salt at bytes 2-15 (14 bytes of salt)
    for i in 0..session_salt.len().min(SESSION_SALT_LEN) {
        iv[2 + i] = session_salt[i];
    }
    // XOR SSRC into bytes 4-7
    let ssrc_bytes = ssrc.to_be_bytes();
    for i in 0..4 {
        iv[4 + i] ^= ssrc_bytes[i];
    }
    // XOR packet index (48 bits) into bytes 8-13
    let pi_bytes = packet_index.to_be_bytes(); // 8 bytes, we want the low 6
    for i in 0..6 {
        iv[8 + i] ^= pi_bytes[2 + i];
    }

    // Generate keystream and XOR
    let keystream = aes_cm_keystream(session_key, &iv, data.len())?;

    let mut output = vec![0u8; data.len()];
    for i in 0..data.len() {
        output[i] = data[i] ^ keystream[i];
    }

    Ok(output)
}

/// Generate AES-CM keystream: encrypt counter blocks with AES-ECB.
///
/// The counter block is: IV with bytes 14-15 replaced by the block counter.
/// We increment the block counter for each 16-byte block of keystream needed.
fn aes_cm_keystream(
    key: &[u8],
    iv: &[u8; AES_BLOCK_SIZE],
    length: usize,
) -> Result<Vec<u8>, SrtpError> {
    let cipher = Aes128::new_from_slice(key)
        .map_err(|e| SrtpError::EncryptionFailed(format!("AES key init: {}", e)))?;

    let num_blocks = (length + AES_BLOCK_SIZE - 1) / AES_BLOCK_SIZE;
    let mut keystream = Vec::with_capacity(num_blocks * AES_BLOCK_SIZE);

    for block_count in 0..num_blocks {
        // Build counter block: IV with last 2 bytes as block counter
        let mut counter_block = aes::Block::default();
        counter_block.copy_from_slice(iv);
        // XOR block counter into the last 2 bytes (big-endian)
        let bc = (block_count as u16).to_be_bytes();
        counter_block[14] ^= bc[0];
        counter_block[15] ^= bc[1];

        // Encrypt the counter block to produce keystream
        cipher.encrypt_block(&mut counter_block);

        keystream.extend_from_slice(counter_block.as_slice());
    }

    keystream.truncate(length);
    Ok(keystream)
}

// ---------------------------------------------------------------------------
// SRTP Key Derivation Function (KDF) per RFC 3711 Section 4.3.1
// ---------------------------------------------------------------------------

/// Derive a session key using AES-CM as a PRF.
///
/// r = key_derivation_rate (we use 0, meaning keys are derived once).
/// x = label || r  (with r = 0 for index_div_kdr = 0)
/// Then: x XOR salt, padded to 16 bytes, used as IV for AES-CM with master_key.
fn kdf_derive(
    master_key: &[u8],
    master_salt: &[u8],
    label: u8,
    index_div_kdr: u64,
    length: usize,
) -> Result<Vec<u8>, SrtpError> {
    // Build the key_id: label(1 byte) || index_div_kdr(6 bytes) = 7 bytes
    // x = key_id placed at position [7..13] of a 14-byte value, XOR'd with salt
    //
    // Per RFC 3711 Section 4.3.1:
    //   key_id = label || r  where r is the key derivation rate index
    //   x = key_id XOR master_salt
    //
    // The label is placed at byte 7 in a 14-byte array:
    //   [0..6] = 0
    //   [7] = label
    //   [8..13] = index_div_kdr (48-bit, big-endian)

    let mut x = [0u8; 14];
    x[7] = label;
    // Place index_div_kdr (48-bit) at bytes 8-13
    let idx_bytes = index_div_kdr.to_be_bytes(); // 8 bytes
    x[8..14].copy_from_slice(&idx_bytes[2..8]);

    // XOR with master salt
    for i in 0..master_salt.len().min(14) {
        x[i] ^= master_salt[i];
    }

    // Use x (padded to 16 bytes with 2 zero bytes) as IV for AES-CM
    let mut iv = [0u8; AES_BLOCK_SIZE];
    iv[2..16].copy_from_slice(&x);

    // Generate `length` bytes of keystream using AES-CM with the master key
    aes_cm_keystream(master_key, &iv, length)
}

// ---------------------------------------------------------------------------
// Authentication
// ---------------------------------------------------------------------------

/// Compute SRTP authentication tag: HMAC-SHA1 over (authenticated_portion || ROC),
/// truncated to 80 bits (10 bytes).
fn compute_srtp_auth_tag(
    auth_key: &[u8],
    authenticated_data: &[u8],
    roc: u32,
) -> Result<[u8; SRTP_AUTH_TAG_LEN], SrtpError> {
    let mut mac = <HmacSha1 as Mac>::new_from_slice(auth_key)
        .map_err(|e| SrtpError::EncryptionFailed(format!("HMAC init: {}", e)))?;
    mac.update(authenticated_data);
    mac.update(&roc.to_be_bytes());
    let result = mac.finalize().into_bytes();

    let mut tag = [0u8; SRTP_AUTH_TAG_LEN];
    tag.copy_from_slice(&result[..SRTP_AUTH_TAG_LEN]);
    Ok(tag)
}

/// Compute SRTCP authentication tag: HMAC-SHA1 over the entire packet data
/// (which already includes the E||SRTCP_index), truncated to 80 bits.
fn compute_srtcp_auth_tag(
    auth_key: &[u8],
    authenticated_data: &[u8],
) -> Result<[u8; SRTCP_AUTH_TAG_LEN], SrtpError> {
    let mut mac = <HmacSha1 as Mac>::new_from_slice(auth_key)
        .map_err(|e| SrtpError::EncryptionFailed(format!("HMAC init: {}", e)))?;
    mac.update(authenticated_data);
    let result = mac.finalize().into_bytes();

    let mut tag = [0u8; SRTCP_AUTH_TAG_LEN];
    tag.copy_from_slice(&result[..SRTCP_AUTH_TAG_LEN]);
    Ok(tag)
}

// ---------------------------------------------------------------------------
// RTP header parsing
// ---------------------------------------------------------------------------

/// Determine the RTP header length including CSRC and extension headers.
fn rtp_header_length(packet: &[u8]) -> Result<usize, SrtpError> {
    if packet.len() < 12 {
        return Err(SrtpError::InvalidPacket);
    }

    let cc = (packet[0] & 0x0F) as usize;
    let has_extension = (packet[0] & 0x10) != 0;
    let mut len = 12 + cc * 4;

    if has_extension {
        if packet.len() < len + 4 {
            return Err(SrtpError::InvalidPacket);
        }
        let ext_len = u16::from_be_bytes([packet[len + 2], packet[len + 3]]) as usize;
        len += 4 + ext_len * 4;
    }

    if len > packet.len() {
        return Err(SrtpError::InvalidPacket);
    }

    Ok(len)
}

/// Returns true if a UDP packet looks like an RTP packet (vs RTCP).
/// Simple heuristic: RTP version=2, payload type 0-34 or 96-127.
pub fn is_rtp_packet(data: &[u8]) -> bool {
    if data.len() < 12 {
        return false;
    }
    let version = (data[0] >> 6) & 0x03;
    if version != 2 {
        return false;
    }
    let pt = data[1] & 0x7F;
    // RTCP payload types are 200-206 (SR, RR, SDES, BYE, APP, RTPFB, PSFB)
    // But since the marker bit is in bit 7, the raw PT byte for RTCP would be 72-78
    // (200-128=72, etc.) or 200-206 without marker consideration.
    // A cleaner check: RTCP PTs when masked with 0x7F give 72-78.
    // RTP PTs are 0-34 (static) or 96-127 (dynamic).
    !(72..=78).contains(&pt)
}

// ---------------------------------------------------------------------------
// Utility
// ---------------------------------------------------------------------------

/// Constant-time comparison to prevent timing attacks.
fn constant_time_eq(a: &[u8], b: &[u8]) -> bool {
    if a.len() != b.len() {
        return false;
    }
    let mut diff = 0u8;
    for (x, y) in a.iter().zip(b.iter()) {
        diff |= x ^ y;
    }
    diff == 0
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    /// Build a minimal RTP packet for testing.
    fn make_rtp_packet(seq: u16, ssrc: u32, payload: &[u8]) -> Vec<u8> {
        let mut pkt = vec![0u8; 12 + payload.len()];
        pkt[0] = 0x80; // V=2, no padding, no extension, CC=0
        pkt[1] = 0x00; // PT=0 (PCMU), no marker
        pkt[2..4].copy_from_slice(&seq.to_be_bytes());
        // timestamp
        pkt[4..8].copy_from_slice(&(seq as u32 * 160).to_be_bytes());
        pkt[8..12].copy_from_slice(&ssrc.to_be_bytes());
        pkt[12..].copy_from_slice(payload);
        pkt
    }

    /// Build a minimal RTCP SR packet for testing.
    fn make_rtcp_sr(ssrc: u32) -> Vec<u8> {
        // RTCP SR: V=2, P=0, RC=0, PT=200, length=6 (28 bytes)
        let mut pkt = vec![0u8; 28];
        pkt[0] = 0x80; // V=2
        pkt[1] = 200;  // PT = SR
        pkt[2..4].copy_from_slice(&6u16.to_be_bytes()); // length in 32-bit words minus 1
        pkt[4..8].copy_from_slice(&ssrc.to_be_bytes());
        // Rest is NTP timestamp, RTP timestamp, packet/octet counts (zeros for test)
        pkt
    }

    #[test]
    fn test_protect_unprotect_roundtrip() {
        let master_key = [0x01u8; 16];
        let master_salt = [0x02u8; 14];

        let mut ctx_tx = SrtpContext::new(&master_key, &master_salt).unwrap();
        let mut ctx_rx = SrtpContext::new(&master_key, &master_salt).unwrap();

        let payload = vec![0xFFu8; 160];
        let rtp = make_rtp_packet(1, 0x12345678, &payload);

        let srtp = ctx_tx.protect(&rtp).unwrap();

        // SRTP packet should be larger (auth tag appended)
        assert_eq!(srtp.len(), rtp.len() + SRTP_AUTH_TAG_LEN);

        // The header should be unchanged
        assert_eq!(&srtp[..12], &rtp[..12]);

        // The payload should be encrypted (different from original for non-zero payload)
        assert_ne!(&srtp[12..12 + 160], &rtp[12..]);

        let decrypted = ctx_rx.unprotect(&srtp).unwrap();
        assert_eq!(decrypted, rtp);
    }

    #[test]
    fn test_protect_unprotect_multiple_packets() {
        let master_key = [0xABu8; 16];
        let master_salt = [0xCDu8; 14];

        let mut ctx_tx = SrtpContext::new(&master_key, &master_salt).unwrap();
        let mut ctx_rx = SrtpContext::new(&master_key, &master_salt).unwrap();

        for seq in 1u16..=100 {
            let payload: Vec<u8> = (0..160).map(|i| (seq as u8).wrapping_add(i)).collect();
            let rtp = make_rtp_packet(seq, 0xDEADBEEF, &payload);

            let srtp = ctx_tx.protect(&rtp).unwrap();
            let decrypted = ctx_rx.unprotect(&srtp).unwrap();
            assert_eq!(decrypted, rtp, "roundtrip failed for seq={}", seq);
        }
    }

    #[test]
    fn test_tampered_packet_fails_auth() {
        let master_key = [0x01u8; 16];
        let master_salt = [0x02u8; 14];

        let mut ctx_tx = SrtpContext::new(&master_key, &master_salt).unwrap();
        let mut ctx_rx = SrtpContext::new(&master_key, &master_salt).unwrap();

        let rtp = make_rtp_packet(1, 0x12345678, &[0xFFu8; 160]);
        let mut srtp = ctx_tx.protect(&rtp).unwrap();

        // Tamper with the encrypted payload
        srtp[20] ^= 0xFF;

        let result = ctx_rx.unprotect(&srtp);
        assert!(matches!(result, Err(SrtpError::AuthenticationFailed)));
    }

    #[test]
    fn test_invalid_key_length() {
        let result = SrtpContext::new(&[0u8; 15], &[0u8; 14]);
        assert!(result.is_err());

        let result = SrtpContext::new(&[0u8; 16], &[0u8; 13]);
        assert!(result.is_err());
    }

    #[test]
    fn test_invalid_packet_too_short() {
        let master_key = [0x01u8; 16];
        let master_salt = [0x02u8; 14];
        let mut ctx = SrtpContext::new(&master_key, &master_salt).unwrap();

        // Too short for RTP
        let result = ctx.protect(&[0u8; 11]);
        assert!(matches!(result, Err(SrtpError::InvalidPacket)));

        // Too short for SRTP (needs 12 header + 10 auth tag minimum)
        let result = ctx.unprotect(&[0u8; 21]);
        assert!(matches!(result, Err(SrtpError::InvalidPacket)));
    }

    #[test]
    fn test_empty_payload_roundtrip() {
        let master_key = [0x01u8; 16];
        let master_salt = [0x02u8; 14];

        let mut ctx_tx = SrtpContext::new(&master_key, &master_salt).unwrap();
        let mut ctx_rx = SrtpContext::new(&master_key, &master_salt).unwrap();

        // RTP with zero-length payload (just header)
        let rtp = make_rtp_packet(1, 0x12345678, &[]);
        let srtp = ctx_tx.protect(&rtp).unwrap();
        let decrypted = ctx_rx.unprotect(&srtp).unwrap();
        assert_eq!(decrypted, rtp);
    }

    #[test]
    fn test_replay_detection() {
        let master_key = [0x01u8; 16];
        let master_salt = [0x02u8; 14];

        let mut ctx_tx = SrtpContext::new(&master_key, &master_salt).unwrap();
        let mut ctx_rx = SrtpContext::new(&master_key, &master_salt).unwrap();

        let rtp = make_rtp_packet(1, 0x12345678, &[0xAAu8; 160]);
        let srtp = ctx_tx.protect(&rtp).unwrap();

        // First unprotect should succeed
        let _ = ctx_rx.unprotect(&srtp).unwrap();

        // Replay of the same packet should fail
        let result = ctx_rx.unprotect(&srtp);
        assert!(matches!(result, Err(SrtpError::ReplayDetected(_))));
    }

    #[test]
    fn test_rtcp_protect_unprotect_roundtrip() {
        let master_key = [0x01u8; 16];
        let master_salt = [0x02u8; 14];

        let mut ctx_tx = SrtpContext::new(&master_key, &master_salt).unwrap();
        let mut ctx_rx = SrtpContext::new(&master_key, &master_salt).unwrap();

        let rtcp = make_rtcp_sr(0x12345678);

        let srtcp = ctx_tx.protect_rtcp(&rtcp).unwrap();
        // SRTCP = original_len + 4 (E||index) + 10 (auth tag)
        assert_eq!(srtcp.len(), rtcp.len() + 4 + SRTCP_AUTH_TAG_LEN);

        let decrypted = ctx_rx.unprotect_rtcp(&srtcp).unwrap();
        assert_eq!(decrypted, rtcp);
    }

    #[test]
    fn test_rtcp_tampered_fails_auth() {
        let master_key = [0x01u8; 16];
        let master_salt = [0x02u8; 14];

        let mut ctx_tx = SrtpContext::new(&master_key, &master_salt).unwrap();
        let mut ctx_rx = SrtpContext::new(&master_key, &master_salt).unwrap();

        let rtcp = make_rtcp_sr(0x12345678);
        let mut srtcp = ctx_tx.protect_rtcp(&rtcp).unwrap();

        // Tamper with encrypted data
        srtcp[10] ^= 0xFF;

        let result = ctx_rx.unprotect_rtcp(&srtcp);
        assert!(matches!(result, Err(SrtpError::AuthenticationFailed)));
    }

    #[test]
    fn test_different_keys_fail_auth() {
        let mut ctx_tx = SrtpContext::new(&[0x01u8; 16], &[0x02u8; 14]).unwrap();
        let mut ctx_rx = SrtpContext::new(&[0x03u8; 16], &[0x04u8; 14]).unwrap();

        let rtp = make_rtp_packet(1, 0x12345678, &[0xFFu8; 160]);
        let srtp = ctx_tx.protect(&rtp).unwrap();

        let result = ctx_rx.unprotect(&srtp);
        assert!(matches!(result, Err(SrtpError::AuthenticationFailed)));
    }

    #[test]
    fn test_rtp_header_with_csrc() {
        // V=2, P=0, X=0, CC=2
        let mut pkt = vec![0u8; 20 + 160]; // 12 + 2*4 CSRC + payload
        pkt[0] = 0x82; // V=2, CC=2
        pkt[1] = 0x00;
        pkt[2..4].copy_from_slice(&1u16.to_be_bytes());
        pkt[4..8].copy_from_slice(&160u32.to_be_bytes());
        pkt[8..12].copy_from_slice(&0x12345678u32.to_be_bytes());
        // CSRC list (2 entries)
        pkt[12..16].copy_from_slice(&0xAAAAAAAAu32.to_be_bytes());
        pkt[16..20].copy_from_slice(&0xBBBBBBBBu32.to_be_bytes());
        // Payload
        for i in 20..pkt.len() {
            pkt[i] = 0xCC;
        }

        let header_len = rtp_header_length(&pkt).unwrap();
        assert_eq!(header_len, 20);

        let mut ctx_tx = SrtpContext::new(&[0x01u8; 16], &[0x02u8; 14]).unwrap();
        let mut ctx_rx = SrtpContext::new(&[0x01u8; 16], &[0x02u8; 14]).unwrap();

        let srtp = ctx_tx.protect(&pkt).unwrap();
        let decrypted = ctx_rx.unprotect(&srtp).unwrap();
        assert_eq!(decrypted, pkt);
    }

    #[test]
    fn test_rtp_header_with_extension() {
        // V=2, P=0, X=1, CC=0
        let ext_data_words = 2u16; // 2 words = 8 bytes of extension data
        let header_len = 12 + 4 + (ext_data_words as usize * 4); // 12 + 4 (ext header) + 8 = 24
        let payload_len = 160;
        let mut pkt = vec![0u8; header_len + payload_len];
        pkt[0] = 0x90; // V=2, X=1, CC=0
        pkt[1] = 0x00;
        pkt[2..4].copy_from_slice(&1u16.to_be_bytes());
        pkt[4..8].copy_from_slice(&160u32.to_be_bytes());
        pkt[8..12].copy_from_slice(&0x12345678u32.to_be_bytes());
        // Extension header
        pkt[12..14].copy_from_slice(&0xBEDEu16.to_be_bytes()); // profile-specific
        pkt[14..16].copy_from_slice(&ext_data_words.to_be_bytes());
        // Extension data (8 bytes)
        for i in 16..24 {
            pkt[i] = 0xDD;
        }
        // Payload
        for i in 24..pkt.len() {
            pkt[i] = 0xEE;
        }

        let parsed_header_len = rtp_header_length(&pkt).unwrap();
        assert_eq!(parsed_header_len, 24);

        let mut ctx_tx = SrtpContext::new(&[0x01u8; 16], &[0x02u8; 14]).unwrap();
        let mut ctx_rx = SrtpContext::new(&[0x01u8; 16], &[0x02u8; 14]).unwrap();

        let srtp = ctx_tx.protect(&pkt).unwrap();
        let decrypted = ctx_rx.unprotect(&srtp).unwrap();
        assert_eq!(decrypted, pkt);
    }

    #[test]
    fn test_replay_window() {
        let mut w = ReplayWindow::new();

        // First packet
        assert!(w.check(0));
        w.update(0);

        // Same packet again - replay
        assert!(!w.check(0));

        // Next packet
        assert!(w.check(1));
        w.update(1);

        // Packet well ahead
        assert!(w.check(100));
        w.update(100);

        // Packet within window
        assert!(w.check(50));
        w.update(50);

        // Packet 50 again - replay
        assert!(!w.check(50));

        // Packet too old (outside 64-packet window from top=100)
        assert!(!w.check(35));

        // Packet at edge of window
        assert!(w.check(37));
    }

    #[test]
    fn test_is_rtp_packet() {
        // Valid RTP
        let rtp = make_rtp_packet(1, 0x12345678, &[0u8; 160]);
        assert!(is_rtp_packet(&rtp));

        // RTCP-like (PT=200 -> masked = 72)
        let mut rtcp_like = [0u8; 12];
        rtcp_like[0] = 0x80;
        rtcp_like[1] = 200u8.wrapping_sub(128); // 72
        assert!(!is_rtp_packet(&rtcp_like));

        // Too short
        assert!(!is_rtp_packet(&[0u8; 4]));

        // Wrong version
        let mut bad_ver = rtp.clone();
        bad_ver[0] = 0x40; // V=1
        assert!(!is_rtp_packet(&bad_ver));
    }

    #[test]
    fn test_kdf_produces_different_keys_for_different_labels() {
        let master_key = [0x01u8; 16];
        let master_salt = [0x02u8; 14];

        let key1 = kdf_derive(&master_key, &master_salt, LABEL_SRTP_ENCRYPTION, 0, 16).unwrap();
        let key2 = kdf_derive(&master_key, &master_salt, LABEL_SRTP_AUTH, 0, 20).unwrap();
        let key3 = kdf_derive(&master_key, &master_salt, LABEL_SRTP_SALT, 0, 14).unwrap();

        // All derived keys should be different
        assert_ne!(key1, key2[..16]);
        assert_ne!(key1, key3[..14].to_vec().into_iter().chain(std::iter::repeat(0).take(2)).collect::<Vec<u8>>());
        assert_ne!(&key2[..14], &key3[..14]);
    }

    #[test]
    fn test_constant_time_eq() {
        assert!(constant_time_eq(&[1, 2, 3], &[1, 2, 3]));
        assert!(!constant_time_eq(&[1, 2, 3], &[1, 2, 4]));
        assert!(!constant_time_eq(&[1, 2], &[1, 2, 3]));
    }
}
