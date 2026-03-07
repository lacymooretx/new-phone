use serde_json::{json, Value};
use tracing::debug;

use crate::esl_client::EslEvent;

/// Parsed event with tenant context and structured JSON payload.
#[derive(Debug, Clone)]
pub struct ParsedEvent {
    pub event_name: String,
    pub tenant_id: String,
    pub channel_uuid: String,
    pub payload: Value,
}

/// Key fields to extract from ESL events.
const KEY_FIELDS: &[&str] = &[
    "Event-Name",
    "Event-Subclass",
    "Channel-UUID",
    "Unique-ID",
    "Caller-Caller-ID-Number",
    "Caller-Caller-ID-Name",
    "Caller-Destination-Number",
    "Caller-Direction",
    "Channel-State",
    "Channel-Call-State",
    "Channel-Name",
    "Channel-HIT-Dialplan",
    "Channel-Read-Codec-Name",
    "Channel-Write-Codec-Name",
    "variable_sip_from_uri",
    "variable_sip_to_uri",
    "variable_sip_contact_uri",
    "variable_sip_call_id",
    "variable_bridge_uuid",
    "variable_record_file_path",
    "variable_record_seconds",
    "variable_hangup_cause",
    "variable_billsec",
    "variable_duration",
    "variable_start_epoch",
    "variable_answer_epoch",
    "variable_end_epoch",
    "variable_np_tenant_id",
    "variable_np_extension_id",
    "DTMF-Digit",
    "DTMF-Duration",
    "Other-Leg-Unique-ID",
    "Other-Leg-Caller-ID-Number",
    "Other-Leg-Destination-Number",
];

/// Fields that should be parsed as numeric values (integers) in JSON output.
const NUMERIC_FIELDS: &[&str] = &[
    "variable_record_seconds",
    "variable_billsec",
    "variable_duration",
    "variable_start_epoch",
    "variable_answer_epoch",
    "variable_end_epoch",
    "DTMF-Duration",
];

/// Check if a field name should be parsed as a number.
fn is_numeric_field(field: &str) -> bool {
    NUMERIC_FIELDS.contains(&field)
}

/// Try to parse a string as an integer, falling back to string if it fails.
fn parse_field_value(field: &str, value: &str) -> Value {
    if is_numeric_field(field) {
        if let Ok(n) = value.parse::<i64>() {
            return Value::Number(n.into());
        }
    }
    Value::String(value.to_string())
}

/// Parse an ESL event into a structured format.
pub fn parse_event(event: &EslEvent) -> Option<ParsedEvent> {
    let event_name = event.event_name()?.to_string();

    // Extract key fields into a JSON object
    let mut payload = serde_json::Map::new();

    for &field in KEY_FIELDS {
        if let Some(value) = event.get(field) {
            if !value.is_empty() {
                // Convert header names to snake_case for JSON
                let json_key = header_to_snake_case(field);
                payload.insert(json_key, parse_field_value(field, value));
            }
        }
    }

    // Add a timestamp
    let timestamp = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default()
        .as_millis();
    payload.insert("timestamp_ms".to_string(), json!(timestamp));

    // Add body if present (e.g., for CUSTOM events with extra data)
    if let Some(body) = &event.body {
        // Try to parse body as additional headers
        for line in body.lines() {
            if let Some((key, value)) = line.split_once(':') {
                let key = key.trim();
                let value = value.trim();
                if !value.is_empty() {
                    let json_key = header_to_snake_case(key);
                    payload.insert(json_key, Value::String(value.to_string()));
                }
            }
        }
    }

    // Extract tenant_id from np_tenant_id variable, or use "default"
    let tenant_id = event
        .get("variable_np_tenant_id")
        .unwrap_or("default")
        .to_string();

    // Extract channel UUID
    let channel_uuid = event
        .get("Channel-UUID")
        .or_else(|| event.get("Unique-ID"))
        .unwrap_or("unknown")
        .to_string();

    debug!(
        event_name = %event_name,
        tenant_id = %tenant_id,
        channel_uuid = %channel_uuid,
        "parsed ESL event"
    );

    Some(ParsedEvent {
        event_name,
        tenant_id,
        channel_uuid,
        payload: Value::Object(payload),
    })
}

/// Convert ESL header name format to snake_case.
/// "Caller-Caller-ID-Number" -> "caller_caller_id_number"
/// "variable_sip_from_uri" -> "variable_sip_from_uri"
fn header_to_snake_case(header: &str) -> String {
    header
        .replace('-', "_")
        .to_lowercase()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::esl_client::EslEvent;

    #[test]
    fn test_parse_channel_create() {
        let event = EslEvent {
            headers: vec![
                ("Event-Name".to_string(), "CHANNEL_CREATE".to_string()),
                ("Channel-UUID".to_string(), "abc-123".to_string()),
                (
                    "Caller-Caller-ID-Number".to_string(),
                    "1001".to_string(),
                ),
                (
                    "Caller-Destination-Number".to_string(),
                    "1002".to_string(),
                ),
                (
                    "variable_np_tenant_id".to_string(),
                    "tenant-xyz".to_string(),
                ),
            ],
            body: None,
        };

        let parsed = parse_event(&event).unwrap();
        assert_eq!(parsed.event_name, "CHANNEL_CREATE");
        assert_eq!(parsed.tenant_id, "tenant-xyz");
        assert_eq!(parsed.channel_uuid, "abc-123");
    }

    #[test]
    fn test_header_to_snake_case() {
        assert_eq!(
            header_to_snake_case("Caller-Caller-ID-Number"),
            "caller_caller_id_number"
        );
        assert_eq!(
            header_to_snake_case("variable_sip_from_uri"),
            "variable_sip_from_uri"
        );
    }

    #[test]
    fn test_parse_basic_esl_event_to_json() {
        let event = EslEvent {
            headers: vec![
                ("Event-Name".to_string(), "CHANNEL_ANSWER".to_string()),
                ("Channel-UUID".to_string(), "uuid-999".to_string()),
                (
                    "Caller-Caller-ID-Number".to_string(),
                    "2001".to_string(),
                ),
                (
                    "Caller-Destination-Number".to_string(),
                    "3001".to_string(),
                ),
            ],
            body: None,
        };

        let parsed = parse_event(&event).unwrap();
        assert_eq!(parsed.event_name, "CHANNEL_ANSWER");
        assert_eq!(parsed.channel_uuid, "uuid-999");

        // Verify the payload is a JSON object with expected keys
        let payload = parsed.payload.as_object().unwrap();
        assert_eq!(
            payload.get("caller_caller_id_number").unwrap().as_str().unwrap(),
            "2001"
        );
        assert_eq!(
            payload.get("caller_destination_number").unwrap().as_str().unwrap(),
            "3001"
        );
        // timestamp_ms should be present
        assert!(payload.contains_key("timestamp_ms"));
    }

    #[test]
    fn test_numeric_fields_parsed_as_numbers() {
        let event = EslEvent {
            headers: vec![
                ("Event-Name".to_string(), "CHANNEL_HANGUP".to_string()),
                ("Channel-UUID".to_string(), "uuid-hangup".to_string()),
                ("variable_billsec".to_string(), "142".to_string()),
                ("variable_duration".to_string(), "150".to_string()),
                ("variable_start_epoch".to_string(), "1709827200".to_string()),
                ("variable_answer_epoch".to_string(), "1709827208".to_string()),
                ("variable_end_epoch".to_string(), "1709827350".to_string()),
                ("variable_record_seconds".to_string(), "140".to_string()),
                ("DTMF-Duration".to_string(), "2000".to_string()),
            ],
            body: None,
        };

        let parsed = parse_event(&event).unwrap();
        let payload = parsed.payload.as_object().unwrap();

        // All numeric fields should be numbers, not strings
        assert_eq!(payload.get("variable_billsec").unwrap().as_i64().unwrap(), 142);
        assert_eq!(payload.get("variable_duration").unwrap().as_i64().unwrap(), 150);
        assert_eq!(payload.get("variable_start_epoch").unwrap().as_i64().unwrap(), 1709827200);
        assert_eq!(payload.get("variable_answer_epoch").unwrap().as_i64().unwrap(), 1709827208);
        assert_eq!(payload.get("variable_end_epoch").unwrap().as_i64().unwrap(), 1709827350);
        assert_eq!(payload.get("variable_record_seconds").unwrap().as_i64().unwrap(), 140);
        assert_eq!(payload.get("dtmf_duration").unwrap().as_i64().unwrap(), 2000);
    }

    #[test]
    fn test_non_numeric_field_stays_string() {
        let event = EslEvent {
            headers: vec![
                ("Event-Name".to_string(), "CHANNEL_CREATE".to_string()),
                ("Channel-UUID".to_string(), "uuid-str".to_string()),
                ("Caller-Caller-ID-Number".to_string(), "1001".to_string()),
            ],
            body: None,
        };

        let parsed = parse_event(&event).unwrap();
        let payload = parsed.payload.as_object().unwrap();

        // Caller-Caller-ID-Number is NOT in NUMERIC_FIELDS, so stays string
        assert!(payload.get("caller_caller_id_number").unwrap().is_string());
    }

    #[test]
    fn test_numeric_field_with_invalid_value_stays_string() {
        let event = EslEvent {
            headers: vec![
                ("Event-Name".to_string(), "CHANNEL_HANGUP".to_string()),
                ("Channel-UUID".to_string(), "uuid-bad".to_string()),
                ("variable_billsec".to_string(), "not-a-number".to_string()),
            ],
            body: None,
        };

        let parsed = parse_event(&event).unwrap();
        let payload = parsed.payload.as_object().unwrap();

        // Falls back to string if parsing fails
        assert_eq!(
            payload.get("variable_billsec").unwrap().as_str().unwrap(),
            "not-a-number"
        );
    }

    #[test]
    fn test_handle_url_encoded_header_values() {
        let event = EslEvent {
            headers: vec![
                ("Event-Name".to_string(), "CHANNEL_CREATE".to_string()),
                ("Channel-UUID".to_string(), "uuid-enc".to_string()),
                (
                    "variable_sip_from_uri".to_string(),
                    "sip%3Aalice%40example.com".to_string(),
                ),
            ],
            body: None,
        };

        let parsed = parse_event(&event).unwrap();
        let payload = parsed.payload.as_object().unwrap();
        assert_eq!(
            payload.get("variable_sip_from_uri").unwrap().as_str().unwrap(),
            "sip%3Aalice%40example.com"
        );
    }

    #[test]
    fn test_extract_tenant_id_from_variable() {
        let event = EslEvent {
            headers: vec![
                ("Event-Name".to_string(), "CHANNEL_HANGUP".to_string()),
                ("Channel-UUID".to_string(), "uuid-hangup".to_string()),
                (
                    "variable_np_tenant_id".to_string(),
                    "tenant-abc-123".to_string(),
                ),
                (
                    "variable_hangup_cause".to_string(),
                    "NORMAL_CLEARING".to_string(),
                ),
            ],
            body: None,
        };

        let parsed = parse_event(&event).unwrap();
        assert_eq!(parsed.tenant_id, "tenant-abc-123");
        assert_eq!(parsed.event_name, "CHANNEL_HANGUP");
    }

    #[test]
    fn test_missing_tenant_id_defaults() {
        let event = EslEvent {
            headers: vec![
                ("Event-Name".to_string(), "HEARTBEAT".to_string()),
                ("Channel-UUID".to_string(), "uuid-heartbeat".to_string()),
            ],
            body: None,
        };

        let parsed = parse_event(&event).unwrap();
        assert_eq!(parsed.tenant_id, "default");
    }

    #[test]
    fn test_missing_event_name_returns_none() {
        let event = EslEvent {
            headers: vec![
                ("Channel-UUID".to_string(), "uuid-no-name".to_string()),
            ],
            body: None,
        };

        assert!(parse_event(&event).is_none());
    }

    #[test]
    fn test_body_parsed_as_extra_headers() {
        let event = EslEvent {
            headers: vec![
                ("Event-Name".to_string(), "CUSTOM".to_string()),
                ("Channel-UUID".to_string(), "uuid-custom".to_string()),
            ],
            body: Some("Custom-Header: some-value\nAnother-Key: 42".to_string()),
        };

        let parsed = parse_event(&event).unwrap();
        let payload = parsed.payload.as_object().unwrap();
        assert_eq!(
            payload.get("custom_header").unwrap().as_str().unwrap(),
            "some-value"
        );
        assert_eq!(
            payload.get("another_key").unwrap().as_str().unwrap(),
            "42"
        );
    }
}
