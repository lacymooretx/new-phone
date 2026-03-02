# Rust Services

## Architecture Overview

The platform includes 7 Rust microservices plus a shared library, organized as a Cargo workspace under `rust/`.

```
rust/
  Cargo.toml              Workspace root
  Cargo.lock
  .rustfmt.toml           edition=2021, max_width=100
  shared/                 np-shared library
  crates/
    sip-proxy/            SIP TLS proxy + load balancer
    rtp-relay/            SRTP media relay
    dpma-service/         Sangoma phone provisioning (DPMA replacement)
    event-router/         FreeSWITCH ESL event router
    parking-manager/      Call park/retrieve manager
    e911-handler/         E911 location and PSAP routing
    sms-gateway/          SMS send/receive gateway
```

All services use the `NP_` env var prefix, tokio async runtime, and axum for HTTP APIs.

## Shared Library (np-shared)

Path: `rust/shared/`

Provides common utilities used by all services:

- **config.rs** -- Env var parsing helpers
- **logging.rs** -- Tracing initialization (JSON in production, pretty in development)
- **health.rs** -- Standardized `/health` endpoint handler

## Service Reference

### 1. SIP Proxy (`sip-proxy`)

SIP TLS proxy and load balancer that sits between SIP clients and FreeSWITCH instances.

| Property | Value |
|----------|-------|
| **SIP listen** | `NP_SIP_LISTEN_ADDR` (default: `0.0.0.0:5061`) |
| **Health HTTP** | `NP_SIP_HEALTH_ADDR` (default: `0.0.0.0:8080`) |
| **Health endpoint** | `GET /health` |

**Env vars:**

| Variable | Description | Default |
|----------|-------------|---------|
| `NP_SIP_LISTEN_ADDR` | SIP TLS listen address | `0.0.0.0:5061` |
| `NP_SIP_HEALTH_ADDR` | HTTP health check address | `0.0.0.0:8080` |
| `NP_SIP_TLS_CERT` | Path to TLS certificate | (required for TLS) |
| `NP_SIP_TLS_KEY` | Path to TLS private key | (required for TLS) |
| `NP_SIP_BACKENDS` | Comma-separated FreeSWITCH backend addresses | `127.0.0.1:5060` |
| `NP_SIP_HEALTH_INTERVAL` | Backend health check interval (seconds) | `10` |
| `NP_SIP_LB_STRATEGY` | Load balancing strategy (`round_robin` or `least_connections`) | `round_robin` |

**Features:**
- SIP message parsing and Via header injection
- TLS termination via tokio-rustls (falls back to TCP without cert/key)
- Dialog-binding (sticky sessions per Call-ID)
- Backend health checks via SIP OPTIONS
- 503 response when no healthy backends

### 2. RTP Relay (`rtp-relay`)

SRTP media relay for NAT traversal, encryption, and conference mixing.

| Property | Value |
|----------|-------|
| **API listen** | `NP_RTP_API_ADDR` (default: `0.0.0.0:8081`) |
| **Health endpoint** | `GET /health` |
| **UDP port range** | `NP_RTP_PORT_MIN` to `NP_RTP_PORT_MAX` |

**Env vars:**

| Variable | Description | Default |
|----------|-------------|---------|
| `NP_RTP_API_ADDR` | HTTP API listen address | `0.0.0.0:8081` |
| `NP_RTP_PORT_MIN` | Minimum UDP port for media | `10000` |
| `NP_RTP_PORT_MAX` | Maximum UDP port for media | `20000` |
| `NP_RTP_EXTERNAL_IP` | Advertised external IP for SDP | `0.0.0.0` |

**Features:**
- SRTP encrypt/decrypt using ring crypto
- Per-session UDP relay with NAT traversal
- Conference mixer (multi-party audio mixing)
- Per-session statistics (packet count, jitter, loss)

### 3. DPMA Service (`dpma-service`)

Sangoma P-series phone provisioning, replacing Digium's proprietary DPMA protocol.

| Property | Value |
|----------|-------|
| **Listen** | `NP_DPMA_LISTEN_ADDR` (default: `0.0.0.0:8082`) |
| **Health endpoint** | `GET /health` |

**Env vars:**

| Variable | Description | Default |
|----------|-------------|---------|
| `NP_DPMA_LISTEN_ADDR` | HTTP listen address | `0.0.0.0:8082` |
| `NP_DPMA_TEMPLATE_DIR` | Path to Tera XML templates | `./templates` |
| `NP_DPMA_FIRMWARE_DIR` | Path to firmware files | `./firmware` |
| `NP_DPMA_FS_ADDR` | FreeSWITCH address for SIP config | `127.0.0.1` |
| `NP_DPMA_SIP_DOMAIN` | Default SIP domain | `pbx.local` |

**Features:**
- MAC-based phone configuration lookup
- Tera XML template rendering for phone config files
- Firmware management and delivery

### 4. Event Router (`event-router`)

Subscribes to FreeSWITCH ESL events and publishes them to Redis pub/sub.

| Property | Value |
|----------|-------|
| **Health HTTP** | `NP_EVENT_ROUTER_HEALTH_ADDR` (default: `0.0.0.0:8083`) |
| **Health endpoint** | `GET /health` |

**Env vars:**

| Variable | Description | Default |
|----------|-------------|---------|
| `NP_ESL_HOST` | FreeSWITCH ESL host | `127.0.0.1` |
| `NP_ESL_PORT` | FreeSWITCH ESL port | `8021` |
| `NP_ESL_PASSWORD` | FreeSWITCH ESL password | `ClueCon` |
| `NP_REDIS_URL` | Redis URL for pub/sub | `redis://127.0.0.1:6379` |
| `NP_EVENT_ROUTER_HEALTH_ADDR` | HTTP health check address | `0.0.0.0:8083` |
| `NP_ESL_RECONNECT_DELAY` | Initial reconnect delay (seconds) | `1` |
| `NP_ESL_RECONNECT_MAX_DELAY` | Max reconnect delay (seconds) | `60` |

**Features:**
- Persistent ESL TCP connection with automatic reconnection (exponential backoff)
- FreeSWITCH event parsing
- Redis pub/sub publishing for downstream consumers
- Subscribes to: CHANNEL_CREATE, CHANNEL_ANSWER, CHANNEL_HANGUP_COMPLETE, RECORD_STOP, DTMF, etc.

### 5. Parking Manager (`parking-manager`)

Call parking with BLF (Busy Lamp Field) status, SIP dialog-info notifications, and timeout handling.

| Property | Value |
|----------|-------|
| **Listen** | `NP_PARKING_LISTEN_ADDR` (default: `0.0.0.0:8084`) |
| **Health endpoint** | `GET /health` |

**Env vars:**

| Variable | Description | Default |
|----------|-------------|---------|
| `NP_PARKING_LISTEN_ADDR` | HTTP listen address | `0.0.0.0:8084` |
| `NP_PARKING_ESL_HOST` | FreeSWITCH ESL host | `127.0.0.1` |
| `NP_PARKING_ESL_PORT` | FreeSWITCH ESL port | `8021` |
| `NP_PARKING_ESL_PASSWORD` | FreeSWITCH ESL password | `ClueCon` |
| `NP_PARKING_REDIS_URL` | Redis URL for state storage | `redis://127.0.0.1:6379` |
| `NP_PARKING_TIMEOUT` | Park timeout (seconds) | `120` |
| `NP_PARKING_SLOTS` | Number of parking slots per lot | `10` |

**Features:**
- Park/retrieve calls via ESL commands
- BLF state tracking (parked slot status)
- SIP dialog-info XML generation for BLF phone lights
- Redis-backed state for high availability
- Timeout checker (returns call to parker after timeout)

### 6. E911 Handler (`e911-handler`)

Emergency call routing with PIDF-LO (Presence Information Data Format - Location Object) support.

| Property | Value |
|----------|-------|
| **Listen** | `NP_E911_LISTEN_ADDR` (default: `0.0.0.0:8085`) |
| **Health endpoint** | `GET /health` |

**Env vars:**

| Variable | Description | Default |
|----------|-------------|---------|
| `NP_E911_LISTEN_ADDR` | HTTP listen address | `0.0.0.0:8085` |
| `NP_E911_PSAP_TABLE` | Path to PSAP routing table JSON | `./psap_routes.json` |
| `NP_E911_DEFAULT_PSAP_TRUNK` | Default PSAP trunk name | `default_psap` |
| `NP_E911_CARRIER_API_URL` | E911 carrier API URL | (optional) |
| `NP_E911_CARRIER_API_KEY` | E911 carrier API key | (optional) |

**Features:**
- PIDF-LO XML building (civic address + geographic coordinates)
- Per-extension location database
- PSAP routing table (map locations to PSAP trunks)
- Emergency call handler with location injection

### 7. SMS Gateway (`sms-gateway`)

High-throughput SMS send/receive with provider abstraction and rate limiting.

| Property | Value |
|----------|-------|
| **Listen** | `NP_SMS_LISTEN_ADDR` (default: `0.0.0.0:8086`) |
| **Health endpoint** | `GET /health` |

**Env vars:**

| Variable | Description | Default |
|----------|-------------|---------|
| `NP_SMS_LISTEN_ADDR` | HTTP listen address | `0.0.0.0:8086` |
| `NP_SMS_REDIS_URL` | Redis URL for rate limiting | `redis://127.0.0.1:6379` |
| `NP_SMS_CLEARLYIP_API_URL` | ClearlyIP API base URL | `https://api.clearlyip.com` |
| `NP_SMS_CLEARLYIP_API_KEY` | ClearlyIP API key | (empty) |
| `NP_SMS_TWILIO_ACCOUNT_SID` | Twilio account SID | (empty) |
| `NP_SMS_TWILIO_AUTH_TOKEN` | Twilio auth token | (empty) |
| `NP_SMS_DEFAULT_PROVIDER` | Default SMS provider | `clearlyip` |
| `NP_SMS_RATE_LIMIT_PER_MIN` | Per-number rate limit (msgs/min) | `60` |
| `NP_SMS_RATE_LIMIT_PER_HOUR` | Per-number rate limit (msgs/hour) | `1000` |
| `NP_SMS_WEBHOOK_BASE_URL` | Base URL for inbound webhooks | `http://localhost:8086` |

**Features:**
- ClearlyIP and Twilio provider abstraction (trait objects)
- Failover routing (if primary provider fails, try secondary)
- Redis-backed rate limiting (per-number, per-minute and per-hour)
- Inbound webhook endpoints for both providers

## Build Instructions

### Prerequisites

- Rust 1.75+ (install via [rustup](https://rustup.rs/))
- OpenSSL dev headers (for TLS features)

### Build All Services

```bash
cd rust/
cargo build --workspace --release
```

Binaries output to `rust/target/release/`:
- `sip-proxy`
- `rtp-relay`
- `dpma-service`
- `event-router`
- `parking-manager`
- `e911-handler`
- `sms-gateway`

### Run Tests

```bash
cd rust/
cargo test --workspace
```

### Check (No Build Artifacts)

```bash
cd rust/
cargo check --workspace
```

## Docker Build and Deploy

Each service has a Dockerfile at `rust/crates/{service}/Dockerfile`. All use multi-stage alpine builds for minimal image size.

### Build a Single Service

```bash
cd rust/
docker build -f crates/sip-proxy/Dockerfile -t newphone/sip-proxy .
```

### Build All Services

```bash
cd rust/
for svc in sip-proxy rtp-relay dpma-service event-router parking-manager e911-handler sms-gateway; do
  docker build -f crates/$svc/Dockerfile -t newphone/$svc .
done
```

### Run a Service

```bash
docker run -d --name np-sip-proxy \
  -e NP_SIP_BACKENDS=freeswitch:5060 \
  -e NP_SIP_TLS_CERT=/certs/sip.crt \
  -e NP_SIP_TLS_KEY=/certs/sip.key \
  -p 5061:5061 \
  -p 8080:8080 \
  newphone/sip-proxy
```

## Health Check Endpoints

All services expose a `GET /health` endpoint on their HTTP listen address.

| Service | Default Health URL |
|---------|--------------------|
| sip-proxy | `http://localhost:8080/health` |
| rtp-relay | `http://localhost:8081/health` |
| dpma-service | `http://localhost:8082/health` |
| event-router | `http://localhost:8083/health` |
| parking-manager | `http://localhost:8084/health` |
| e911-handler | `http://localhost:8085/health` |
| sms-gateway | `http://localhost:8086/health` |

Response format:

```json
{
  "status": "healthy",
  "service": "sip-proxy",
  "uptime_seconds": 3600
}
```

## Inter-Service Communication

```
                          ┌─────────────┐
SIP Clients ──TLS──>  sip-proxy  ──>  FreeSWITCH
                          │
                     ┌────┴────┐
                     │         │
               rtp-relay   parking-manager
                     │         │
                     └────┬────┘
                          │
FreeSWITCH ──ESL──>  event-router  ──Redis pub/sub──>  API (Python)
                                                          │
                                                    ┌─────┴─────┐
                                                    │           │
                                               sms-gateway  e911-handler
```

- **sip-proxy <-> FreeSWITCH**: SIP over TLS/TCP
- **event-router <-> FreeSWITCH**: ESL TCP (port 8021)
- **parking-manager <-> FreeSWITCH**: ESL TCP (port 8021)
- **event-router -> Redis**: pub/sub (events channel)
- **sms-gateway -> Redis**: rate limit counters
- **parking-manager -> Redis**: parking slot state
- **API (Python) -> Redis**: pub/sub subscriber for WebSocket push

## Monitoring and Logging

### Logging

All services use the `tracing` crate with configurable output:

- **Production** (`RUST_LOG` unset or set to `info`): JSON-formatted structured logs
- **Development** (`RUST_LOG=debug`): Human-readable pretty-printed logs

Set log level via `RUST_LOG` env var:

```bash
RUST_LOG=debug          # All debug logs
RUST_LOG=info           # Info and above (default)
RUST_LOG=sip_proxy=debug,tower=warn  # Per-crate levels
```

### Metrics

Health endpoints provide basic uptime and status. For detailed metrics, use the Python API's Prometheus `/metrics` endpoint which aggregates platform-wide telemetry.

### Graceful Shutdown

All services handle SIGTERM and Ctrl+C for graceful shutdown. In-flight requests complete before the process exits. Docker's default 10-second stop timeout is sufficient for all services.

## Key Design Decisions

- **tokio** for async runtime (all services)
- **axum 0.7** for HTTP APIs
- **clap derive** for configuration (env vars + CLI args)
- **anyhow** for application error handling, **thiserror** for library error types
- **ring** for SRTP crypto (rtp-relay)
- **tokio-rustls** for TLS (sip-proxy, optional)
- **tera** for XML template rendering (dpma-service)
- Trait objects with `Pin<Box<dyn Future>>` for provider abstraction (sms-gateway)
- All services compile with `cargo check --workspace` producing zero errors
