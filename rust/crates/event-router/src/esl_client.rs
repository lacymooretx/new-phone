use anyhow::{Context, Result};
use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader};
use tokio::net::TcpStream;
use tracing::{debug, info, warn};

/// Events to subscribe to from FreeSWITCH.
const SUBSCRIBED_EVENTS: &[&str] = &[
    "CHANNEL_CREATE",
    "CHANNEL_HANGUP",
    "CHANNEL_ANSWER",
    "CHANNEL_STATE",
    "CHANNEL_BRIDGE",
    "CHANNEL_UNBRIDGE",
    "RECORD_START",
    "RECORD_STOP",
    "DTMF",
    "CUSTOM",
];

/// ESL (Event Socket Library) client for FreeSWITCH.
pub struct EslClient {
    host: String,
    port: u16,
    password: String,
}

/// A raw ESL event as key-value pairs.
#[derive(Debug, Clone)]
pub struct EslEvent {
    pub headers: Vec<(String, String)>,
    pub body: Option<String>,
}

impl EslEvent {
    /// Get a header value by name.
    pub fn get(&self, name: &str) -> Option<&str> {
        self.headers
            .iter()
            .find(|(k, _)| k == name)
            .map(|(_, v)| v.as_str())
    }

    /// Get the event name.
    pub fn event_name(&self) -> Option<&str> {
        self.get("Event-Name")
    }
}

impl EslClient {
    pub fn new(host: String, port: u16, password: String) -> Self {
        EslClient {
            host,
            port,
            password,
        }
    }

    /// Connect to FreeSWITCH ESL, authenticate, subscribe to events, and return
    /// a stream of events. Caller should handle reconnection on error.
    pub async fn connect_and_subscribe(
        &self,
    ) -> Result<EslConnection> {
        let addr = format!("{}:{}", self.host, self.port);
        info!(addr = %addr, "connecting to FreeSWITCH ESL");

        let stream = TcpStream::connect(&addr)
            .await
            .with_context(|| format!("failed to connect to ESL at {}", addr))?;

        let (reader, writer) = stream.into_split();
        let mut buf_reader = BufReader::new(reader);

        // Read initial content-type header
        let mut line = String::new();
        buf_reader.read_line(&mut line).await?;
        debug!(line = %line.trim(), "ESL initial response");

        // Read the rest of the initial response (until blank line)
        loop {
            line.clear();
            buf_reader.read_line(&mut line).await?;
            if line.trim().is_empty() {
                break;
            }
        }

        let mut writer = writer;

        // Authenticate
        let auth_cmd = format!("auth {}\n\n", self.password);
        writer.write_all(auth_cmd.as_bytes()).await?;
        writer.flush().await?;

        // Read auth response
        let auth_response = read_esl_response(&mut buf_reader).await?;
        if let Some(reply) = auth_response.get("Reply-Text") {
            if reply.starts_with("+OK") {
                info!("ESL authentication successful");
            } else {
                return Err(anyhow::anyhow!("ESL auth failed: {}", reply));
            }
        } else {
            // Check content-type for auth/request
            debug!("auth response (no Reply-Text): {:?}", auth_response.headers);
        }

        // Subscribe to events
        let event_list = SUBSCRIBED_EVENTS.join(" ");
        let event_cmd = format!("event plain {}\n\n", event_list);
        writer.write_all(event_cmd.as_bytes()).await?;
        writer.flush().await?;

        // Read subscription response
        let sub_response = read_esl_response(&mut buf_reader).await?;
        if let Some(reply) = sub_response.get("Reply-Text") {
            info!(reply = %reply, "ESL event subscription response");
        }

        info!(events = %event_list, "subscribed to FreeSWITCH events");

        Ok(EslConnection {
            reader: buf_reader,
            _writer: writer,
        })
    }
}

pub struct EslConnection {
    reader: BufReader<tokio::net::tcp::OwnedReadHalf>,
    _writer: tokio::net::tcp::OwnedWriteHalf,
}

impl EslConnection {
    /// Read the next event from the ESL connection.
    pub async fn next_event(&mut self) -> Result<EslEvent> {
        read_esl_response(&mut self.reader).await
    }
}

/// Read an ESL response/event: headers separated by \n, terminated by blank line,
/// optionally followed by a body if Content-Length is present.
async fn read_esl_response(
    reader: &mut BufReader<tokio::net::tcp::OwnedReadHalf>,
) -> Result<EslEvent> {
    let mut headers = Vec::new();
    let mut content_length: Option<usize> = None;

    loop {
        let mut line = String::new();
        let n = reader.read_line(&mut line).await?;
        if n == 0 {
            return Err(anyhow::anyhow!("ESL connection closed"));
        }

        let trimmed = line.trim();
        if trimmed.is_empty() {
            break;
        }

        if let Some((key, value)) = trimmed.split_once(':') {
            let key = key.trim().to_string();
            let value = url_decode(value.trim());

            if key == "Content-Length" {
                content_length = value.parse::<usize>().ok();
            }

            headers.push((key, value));
        }
    }

    // Read body if Content-Length is present
    let body = if let Some(len) = content_length {
        if len > 0 {
            let mut body_buf = vec![0u8; len];
            use tokio::io::AsyncReadExt;
            reader.read_exact(&mut body_buf).await?;
            Some(String::from_utf8_lossy(&body_buf).to_string())
        } else {
            None
        }
    } else {
        None
    };

    Ok(EslEvent { headers, body })
}

/// Simple URL decode for ESL header values.
fn url_decode(input: &str) -> String {
    let mut result = String::with_capacity(input.len());
    let mut chars = input.chars();
    while let Some(c) = chars.next() {
        if c == '%' {
            let hex: String = chars.by_ref().take(2).collect();
            if hex.len() == 2 {
                if let Ok(byte) = u8::from_str_radix(&hex, 16) {
                    result.push(byte as char);
                } else {
                    result.push('%');
                    result.push_str(&hex);
                }
            } else {
                result.push('%');
                result.push_str(&hex);
            }
        } else if c == '+' {
            result.push(' ');
        } else {
            result.push(c);
        }
    }
    result
}

/// Connect to ESL with exponential backoff retry.
pub async fn connect_with_retry(
    client: &EslClient,
    base_delay: u64,
    max_delay: u64,
) -> EslConnection {
    let mut delay = base_delay;
    let mut attempt = 0u32;

    loop {
        attempt += 1;
        match client.connect_and_subscribe().await {
            Ok(conn) => {
                info!(attempt = attempt, "ESL connected successfully");
                return conn;
            }
            Err(e) => {
                warn!(
                    attempt = attempt,
                    delay = delay,
                    error = %e,
                    "ESL connection failed, retrying"
                );
                tokio::time::sleep(tokio::time::Duration::from_secs(delay)).await;
                delay = (delay * 2).min(max_delay);
            }
        }
    }
}
