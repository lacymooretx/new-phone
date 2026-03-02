use serde::Serialize;

/// Per-session statistics for RTP relay.
#[derive(Debug, Clone, Serialize)]
pub struct SessionStats {
    pub session_id: String,
    pub packets_caller_to_callee: u64,
    pub packets_callee_to_caller: u64,
    pub bytes_caller_to_callee: u64,
    pub bytes_callee_to_caller: u64,
    pub packet_loss_caller: f64,
    pub packet_loss_callee: f64,
    pub jitter_caller_ms: f64,
    pub jitter_callee_ms: f64,
    pub codec: String,
}

impl SessionStats {
    pub fn new(session_id: &str) -> Self {
        SessionStats {
            session_id: session_id.to_string(),
            packets_caller_to_callee: 0,
            packets_callee_to_caller: 0,
            bytes_caller_to_callee: 0,
            bytes_callee_to_caller: 0,
            packet_loss_caller: 0.0,
            packet_loss_callee: 0.0,
            jitter_caller_ms: 0.0,
            jitter_callee_ms: 0.0,
            codec: "unknown".to_string(),
        }
    }

    /// Update jitter estimate using RFC 3550 algorithm.
    /// D(i,j) = arrival time difference - send time difference
    pub fn update_jitter(current_jitter: f64, transit_diff: f64) -> f64 {
        // J(i) = J(i-1) + (|D(i-1,i)| - J(i-1))/16
        current_jitter + (transit_diff.abs() - current_jitter) / 16.0
    }

    /// Calculate packet loss percentage given expected and received counts.
    pub fn calculate_packet_loss(expected: u64, received: u64) -> f64 {
        if expected == 0 {
            return 0.0;
        }
        let lost = expected.saturating_sub(received);
        (lost as f64 / expected as f64) * 100.0
    }

    /// Get total packets relayed in both directions.
    pub fn total_packets(&self) -> u64 {
        self.packets_caller_to_callee + self.packets_callee_to_caller
    }

    /// Get total bytes relayed in both directions.
    pub fn total_bytes(&self) -> u64 {
        self.bytes_caller_to_callee + self.bytes_callee_to_caller
    }
}

/// RTP packet header fields useful for statistics.
#[derive(Debug, Clone)]
pub struct RtpHeader {
    pub version: u8,
    pub padding: bool,
    pub extension: bool,
    pub csrc_count: u8,
    pub marker: bool,
    pub payload_type: u8,
    pub sequence_number: u16,
    pub timestamp: u32,
    pub ssrc: u32,
}

impl RtpHeader {
    /// Parse RTP header from bytes.
    pub fn parse(data: &[u8]) -> Option<Self> {
        if data.len() < 12 {
            return None;
        }

        Some(RtpHeader {
            version: (data[0] >> 6) & 0x03,
            padding: (data[0] & 0x20) != 0,
            extension: (data[0] & 0x10) != 0,
            csrc_count: data[0] & 0x0F,
            marker: (data[1] & 0x80) != 0,
            payload_type: data[1] & 0x7F,
            sequence_number: u16::from_be_bytes([data[2], data[3]]),
            timestamp: u32::from_be_bytes([data[4], data[5], data[6], data[7]]),
            ssrc: u32::from_be_bytes([data[8], data[9], data[10], data[11]]),
        })
    }

    /// Get the codec name from the payload type.
    pub fn codec_name(&self) -> &'static str {
        match self.payload_type {
            0 => "PCMU",
            3 => "GSM",
            4 => "G723",
            8 => "PCMA",
            9 => "G722",
            18 => "G729",
            96..=127 => "dynamic",
            _ => "unknown",
        }
    }
}
