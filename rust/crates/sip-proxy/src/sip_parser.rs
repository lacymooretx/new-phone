use thiserror::Error;

#[derive(Error, Debug)]
pub enum SipParseError {
    #[error("invalid SIP message: {0}")]
    InvalidMessage(String),
    #[error("missing required header: {0}")]
    MissingHeader(String),
    #[error("malformed header: {0}")]
    MalformedHeader(String),
}

#[derive(Debug, Clone, PartialEq)]
pub enum SipMethod {
    Invite,
    Register,
    Bye,
    Refer,
    Options,
    Subscribe,
    Notify,
    Ack,
    Cancel,
    Info,
    Update,
    Message,
    Prack,
    Unknown(String),
}

impl SipMethod {
    pub fn from_str(s: &str) -> Self {
        match s.to_uppercase().as_str() {
            "INVITE" => SipMethod::Invite,
            "REGISTER" => SipMethod::Register,
            "BYE" => SipMethod::Bye,
            "REFER" => SipMethod::Refer,
            "OPTIONS" => SipMethod::Options,
            "SUBSCRIBE" => SipMethod::Subscribe,
            "NOTIFY" => SipMethod::Notify,
            "ACK" => SipMethod::Ack,
            "CANCEL" => SipMethod::Cancel,
            "INFO" => SipMethod::Info,
            "UPDATE" => SipMethod::Update,
            "MESSAGE" => SipMethod::Message,
            "PRACK" => SipMethod::Prack,
            _ => SipMethod::Unknown(s.to_string()),
        }
    }

    pub fn as_str(&self) -> &str {
        match self {
            SipMethod::Invite => "INVITE",
            SipMethod::Register => "REGISTER",
            SipMethod::Bye => "BYE",
            SipMethod::Refer => "REFER",
            SipMethod::Options => "OPTIONS",
            SipMethod::Subscribe => "SUBSCRIBE",
            SipMethod::Notify => "NOTIFY",
            SipMethod::Ack => "ACK",
            SipMethod::Cancel => "CANCEL",
            SipMethod::Info => "INFO",
            SipMethod::Update => "UPDATE",
            SipMethod::Message => "MESSAGE",
            SipMethod::Prack => "PRACK",
            SipMethod::Unknown(s) => s.as_str(),
        }
    }
}

#[derive(Debug, Clone)]
pub struct SipHeader {
    pub name: String,
    pub value: String,
}

#[derive(Debug, Clone)]
pub enum SipMessageType {
    Request {
        method: SipMethod,
        uri: String,
        version: String,
    },
    Response {
        version: String,
        status_code: u16,
        reason: String,
    },
}

#[derive(Debug, Clone)]
pub struct SipMessage {
    pub message_type: SipMessageType,
    pub headers: Vec<SipHeader>,
    pub body: Vec<u8>,
    raw: Vec<u8>,
}

impl SipMessage {
    /// Parse a SIP message from raw bytes.
    pub fn parse(data: &[u8]) -> Result<Self, SipParseError> {
        let text = String::from_utf8_lossy(data);

        // Split headers from body (separated by \r\n\r\n)
        let (header_section, body_bytes) = if let Some(pos) = find_header_body_boundary(data) {
            (&data[..pos], &data[pos + 4..])
        } else {
            (data, &[] as &[u8])
        };

        let header_text = String::from_utf8_lossy(header_section);
        let mut lines: Vec<&str> = header_text.split("\r\n").collect();
        if lines.is_empty() {
            // Try LF-only line endings
            lines = header_text.split('\n').collect();
        }

        if lines.is_empty() {
            return Err(SipParseError::InvalidMessage(
                "empty message".to_string(),
            ));
        }

        // Parse the first line (request-line or status-line)
        let first_line = lines[0].trim();
        if first_line.is_empty() {
            return Err(SipParseError::InvalidMessage(
                "empty first line".to_string(),
            ));
        }

        let message_type = parse_first_line(first_line)?;

        // Parse headers (remaining lines)
        let mut headers = Vec::new();
        let mut i = 1;
        while i < lines.len() {
            let line = lines[i];
            if line.is_empty() {
                break;
            }
            // Handle header line folding (continuation with whitespace)
            if line.starts_with(' ') || line.starts_with('\t') {
                if let Some(last) = headers.last_mut() {
                    let h: &mut SipHeader = last;
                    h.value.push(' ');
                    h.value.push_str(line.trim());
                }
            } else if let Some((name, value)) = line.split_once(':') {
                headers.push(SipHeader {
                    name: name.trim().to_string(),
                    value: value.trim().to_string(),
                });
            }
            i += 1;
        }

        // Determine body based on Content-Length
        let content_length = headers
            .iter()
            .find(|h| h.name.eq_ignore_ascii_case("Content-Length"))
            .and_then(|h| h.value.parse::<usize>().ok())
            .unwrap_or(0);

        let body = if content_length > 0 && !body_bytes.is_empty() {
            body_bytes[..content_length.min(body_bytes.len())].to_vec()
        } else {
            Vec::new()
        };

        let _ = text; // used to borrow data, keep it alive

        Ok(SipMessage {
            message_type,
            headers,
            body,
            raw: data.to_vec(),
        })
    }

    /// Get a header value by name (case-insensitive).
    pub fn header(&self, name: &str) -> Option<&str> {
        self.headers
            .iter()
            .find(|h| h.name.eq_ignore_ascii_case(name))
            .map(|h| h.value.as_str())
    }

    /// Get the Via header value.
    pub fn via(&self) -> Option<&str> {
        self.header("Via").or_else(|| self.header("v"))
    }

    /// Get the From header value.
    pub fn sip_from(&self) -> Option<&str> {
        self.header("From").or_else(|| self.header("f"))
    }

    /// Get the To header value.
    pub fn to_header(&self) -> Option<&str> {
        self.header("To").or_else(|| self.header("t"))
    }

    /// Get the Call-ID header value.
    pub fn call_id(&self) -> Option<&str> {
        self.header("Call-ID").or_else(|| self.header("i"))
    }

    /// Get the CSeq header value.
    pub fn cseq(&self) -> Option<&str> {
        self.header("CSeq")
    }

    /// Get the Contact header value.
    pub fn contact(&self) -> Option<&str> {
        self.header("Contact").or_else(|| self.header("m"))
    }

    /// Check if this is a request.
    pub fn is_request(&self) -> bool {
        matches!(self.message_type, SipMessageType::Request { .. })
    }

    /// Check if this is a response.
    pub fn is_response(&self) -> bool {
        matches!(self.message_type, SipMessageType::Response { .. })
    }

    /// Get the method if this is a request.
    pub fn method(&self) -> Option<&SipMethod> {
        match &self.message_type {
            SipMessageType::Request { method, .. } => Some(method),
            _ => None,
        }
    }

    /// Get the status code if this is a response.
    pub fn status_code(&self) -> Option<u16> {
        match &self.message_type {
            SipMessageType::Response { status_code, .. } => Some(*status_code),
            _ => None,
        }
    }

    /// Add a Via header to the message and serialize.
    pub fn add_via_and_serialize(&self, via_value: &str) -> Vec<u8> {
        let text = String::from_utf8_lossy(&self.raw);

        // Find end of first line
        if let Some(pos) = text.find("\r\n") {
            let mut result = String::new();
            result.push_str(&text[..pos + 2]);
            result.push_str(&format!("Via: {}\r\n", via_value));
            result.push_str(&text[pos + 2..]);
            result.into_bytes()
        } else {
            // Fallback: just prepend Via after first line with LF
            let mut result = self.raw.clone();
            if let Some(pos) = text.find('\n') {
                let via_line = format!("Via: {}\r\n", via_value);
                let insert_pos = pos + 1;
                let via_bytes = via_line.into_bytes();
                result.splice(insert_pos..insert_pos, via_bytes);
            }
            result
        }
    }

    /// Serialize the raw message bytes.
    pub fn as_bytes(&self) -> &[u8] {
        &self.raw
    }
}

fn find_header_body_boundary(data: &[u8]) -> Option<usize> {
    data.windows(4)
        .position(|w| w == b"\r\n\r\n")
}

fn parse_first_line(line: &str) -> Result<SipMessageType, SipParseError> {
    // Check if it's a response (starts with SIP/2.0)
    if line.starts_with("SIP/") {
        let parts: Vec<&str> = line.splitn(3, ' ').collect();
        if parts.len() < 2 {
            return Err(SipParseError::InvalidMessage(format!(
                "malformed status line: {}",
                line
            )));
        }
        let version = parts[0].to_string();
        let status_code = parts[1].parse::<u16>().map_err(|_| {
            SipParseError::InvalidMessage(format!("invalid status code: {}", parts[1]))
        })?;
        let reason = if parts.len() >= 3 {
            parts[2].to_string()
        } else {
            String::new()
        };
        Ok(SipMessageType::Response {
            version,
            status_code,
            reason,
        })
    } else {
        // It's a request: METHOD URI SIP/2.0
        let parts: Vec<&str> = line.splitn(3, ' ').collect();
        if parts.len() < 3 {
            return Err(SipParseError::InvalidMessage(format!(
                "malformed request line: {}",
                line
            )));
        }
        let method = SipMethod::from_str(parts[0]);
        let uri = parts[1].to_string();
        let version = parts[2].to_string();
        Ok(SipMessageType::Request {
            method,
            uri,
            version,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_invite() {
        let msg = b"INVITE sip:bob@example.com SIP/2.0\r\n\
            Via: SIP/2.0/TLS client.example.com:5061;branch=z9hG4bK776\r\n\
            From: <sip:alice@example.com>;tag=1234\r\n\
            To: <sip:bob@example.com>\r\n\
            Call-ID: abcdef@example.com\r\n\
            CSeq: 1 INVITE\r\n\
            Contact: <sip:alice@client.example.com>\r\n\
            Content-Length: 0\r\n\
            \r\n";

        let parsed = SipMessage::parse(msg).unwrap();
        assert!(parsed.is_request());
        assert_eq!(parsed.method(), Some(&SipMethod::Invite));
        assert!(parsed.call_id().unwrap().contains("abcdef"));
        assert!(parsed.sip_from().is_some());
        assert!(parsed.to_header().is_some());
    }

    #[test]
    fn test_parse_response() {
        let msg = b"SIP/2.0 200 OK\r\n\
            Via: SIP/2.0/TLS server.example.com:5061;branch=z9hG4bK776\r\n\
            From: <sip:alice@example.com>;tag=1234\r\n\
            To: <sip:bob@example.com>;tag=5678\r\n\
            Call-ID: abcdef@example.com\r\n\
            CSeq: 1 INVITE\r\n\
            Content-Length: 0\r\n\
            \r\n";

        let parsed = SipMessage::parse(msg).unwrap();
        assert!(parsed.is_response());
        assert_eq!(parsed.status_code(), Some(200));
    }

    #[test]
    fn test_extract_via_from_to_callid_headers() {
        let msg = b"INVITE sip:bob@example.com SIP/2.0\r\n\
            Via: SIP/2.0/TLS proxy.example.com:5061;branch=z9hG4bK-abc\r\n\
            From: \"Alice\" <sip:alice@example.com>;tag=9876\r\n\
            To: \"Bob\" <sip:bob@example.com>\r\n\
            Call-ID: unique-call-id-12345@example.com\r\n\
            CSeq: 1 INVITE\r\n\
            Content-Length: 0\r\n\
            \r\n";

        let parsed = SipMessage::parse(msg).unwrap();

        let via = parsed.via().expect("Via header missing");
        assert!(via.contains("proxy.example.com"));
        assert!(via.contains("branch=z9hG4bK-abc"));

        let from = parsed.sip_from().expect("From header missing");
        assert!(from.contains("alice@example.com"));
        assert!(from.contains("tag=9876"));

        let to = parsed.to_header().expect("To header missing");
        assert!(to.contains("bob@example.com"));

        let call_id = parsed.call_id().expect("Call-ID header missing");
        assert_eq!(call_id, "unique-call-id-12345@example.com");
    }

    #[test]
    fn test_parse_bye_request() {
        let msg = b"BYE sip:bob@192.168.1.100:5060 SIP/2.0\r\n\
            Via: SIP/2.0/TLS client.example.com:5061;branch=z9hG4bKbye1\r\n\
            From: <sip:alice@example.com>;tag=1111\r\n\
            To: <sip:bob@example.com>;tag=2222\r\n\
            Call-ID: bye-call-id@example.com\r\n\
            CSeq: 2 BYE\r\n\
            Content-Length: 0\r\n\
            \r\n";

        let parsed = SipMessage::parse(msg).unwrap();
        assert!(parsed.is_request());
        assert!(!parsed.is_response());
        assert_eq!(parsed.method(), Some(&SipMethod::Bye));
        assert_eq!(parsed.call_id(), Some("bye-call-id@example.com"));
        let cseq = parsed.cseq().expect("CSeq missing");
        assert!(cseq.contains("BYE"));
    }

    #[test]
    fn test_parse_register_request() {
        let msg = b"REGISTER sip:registrar.example.com SIP/2.0\r\n\
            Via: SIP/2.0/TLS phone.example.com:5061;branch=z9hG4bKreg1\r\n\
            From: <sip:alice@example.com>;tag=reg-tag\r\n\
            To: <sip:alice@example.com>\r\n\
            Call-ID: register-id@example.com\r\n\
            CSeq: 1 REGISTER\r\n\
            Contact: <sip:alice@phone.example.com>\r\n\
            Expires: 3600\r\n\
            Content-Length: 0\r\n\
            \r\n";

        let parsed = SipMessage::parse(msg).unwrap();
        assert!(parsed.is_request());
        assert_eq!(parsed.method(), Some(&SipMethod::Register));
        let contact = parsed.contact().expect("Contact header missing");
        assert!(contact.contains("alice@phone.example.com"));
        if let SipMessageType::Request { uri, .. } = &parsed.message_type {
            assert_eq!(uri, "sip:registrar.example.com");
        } else {
            panic!("Expected request");
        }
    }

    #[test]
    fn test_parse_options_request() {
        let msg = b"OPTIONS sip:bob@example.com SIP/2.0\r\n\
            Via: SIP/2.0/TLS client.example.com:5061;branch=z9hG4bKopt1\r\n\
            From: <sip:alice@example.com>;tag=opt-tag\r\n\
            To: <sip:bob@example.com>\r\n\
            Call-ID: options-id@example.com\r\n\
            CSeq: 1 OPTIONS\r\n\
            Content-Length: 0\r\n\
            \r\n";

        let parsed = SipMessage::parse(msg).unwrap();
        assert!(parsed.is_request());
        assert_eq!(parsed.method(), Some(&SipMethod::Options));
    }

    #[test]
    fn test_parse_response_404_not_found() {
        let msg = b"SIP/2.0 404 Not Found\r\n\
            Via: SIP/2.0/TLS server.example.com:5061;branch=z9hG4bK404\r\n\
            From: <sip:alice@example.com>;tag=1234\r\n\
            To: <sip:bob@example.com>;tag=5678\r\n\
            Call-ID: notfound@example.com\r\n\
            CSeq: 1 INVITE\r\n\
            Content-Length: 0\r\n\
            \r\n";

        let parsed = SipMessage::parse(msg).unwrap();
        assert!(parsed.is_response());
        assert_eq!(parsed.status_code(), Some(404));
        if let SipMessageType::Response { reason, .. } = &parsed.message_type {
            assert_eq!(reason, "Not Found");
        }
    }

    #[test]
    fn test_sip_method_from_str_unknown() {
        let method = SipMethod::from_str("PUBLISH");
        assert_eq!(method, SipMethod::Unknown("PUBLISH".to_string()));
    }

    #[test]
    fn test_empty_message_error() {
        let result = SipMessage::parse(b"");
        assert!(result.is_err());
    }
}
