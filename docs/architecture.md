# Architecture

This document describes the system architecture of Aspendora Connect, a multi-tenant PBX platform built for Managed Service Providers.

## System Overview

Aspendora Connect is an API-first platform where all functionality is exposed through a RESTful API. Client applications (web, desktop, mobile, browser extension) are thin consumers of this API. The media engine (FreeSWITCH) handles all real-time voice traffic and is controlled by the API via the Event Socket Layer (ESL) protocol.

Tenant isolation is enforced at the database level using PostgreSQL Row-Level Security (RLS), meaning a compromised or buggy API endpoint cannot leak data across tenant boundaries.

## Component Diagram

```
+------------------------------------------------------------------+
|                         CLIENT TIER                               |
|                                                                   |
|  +----------+  +-----------+  +-----------+  +----------+        |
|  | Web UI   |  | Desktop   |  | Extension |  | Mobile   |        |
|  | React 19 |  | Electron  |  | Chrome    |  | Flutter  |        |
|  | :3000    |  | (wraps    |  | Preact    |  | CallKit/ |        |
|  | Vite     |  |  web UI)  |  | MV3       |  | ConnSvc  |        |
|  +----+-----+  +-----+-----+  +-----+-----+  +----+-----+       |
|       |               |              |              |             |
+-------+---------------+--------------+--------------+-------------+
        |               |              |              |
     HTTPS           HTTPS          HTTPS          HTTPS
      WSS             WSS                           WSS
        |               |              |              |
+-------v---------------v--------------v--------------v-------------+
|                          API TIER                                  |
|                                                                    |
|  +--------------------------------------------------------------+ |
|  |                    FastAPI  (:8000)                           | |
|  |                                                              | |
|  |  /api/v1/*           52 routers, 59 services                 | |
|  |  /api/docs           Swagger UI                              | |
|  |  /provision/{mac}    Phone auto-provisioning                 | |
|  |  /phone-apps/*       Desk phone XML apps                     | |
|  |  /freeswitch/*       XML CURL config server                  | |
|  |  /sms/webhook/*      SMS provider webhook ingress            | |
|  |  /ws/events          WebSocket real-time events              | |
|  |                                                              | |
|  |  Middleware: request logging, RFC 7807 errors, CORS          | |
|  |  Auth: JWT (access/refresh), TOTP MFA, SSO (OIDC)           | |
|  |  RBAC: 5 roles, 60+ permissions                             | |
|  +------+-----------+-----------+-----------+-------------------+ |
|         |           |           |           |                     |
+---------|-----------|-----------|-----------|---------------------+
          |           |           |           |
+---------v---+ +-----v-----+ +--v--------+ +v--------------+
| PostgreSQL  | |   Redis   | |   MinIO   | |  FreeSWITCH   |
| 17          | |   7       | |   (S3)    | |               |
|             | |           | |           | |  SIP TLS:5061 |
| RLS per     | | Session   | | Record-   | |  WSS:7443     |
| tenant      | | cache     | | ings,     | |  ESL:8021     |
| 55 migra-   | | Pub/sub   | | voicemail | |               |
| tions       | | Rate      | | fax, MoH  | |  XML CURL     |
| UUID PKs    | | limiting  | |           | |  config from  |
|             | |           | |           | |  API          |
+-------------+ +-----------+ +-----------+ +-------+-------+
                                                     |
                                              +------v------+
                                              |  AI Engine  |
                                              |  :8090 WS   |
                                              |  :8091 API  |
                                              |             |
                                              | STT -> LLM  |
                                              |  -> TTS     |
                                              | Tool calls  |
                                              +-------------+
```

## Data Flow

### Authentication

1. Client sends `POST /api/v1/auth/login` with email and password.
2. API verifies credentials using bcrypt, checks account lockout status.
3. If MFA is enabled, API returns a partial token requiring TOTP verification via `POST /api/v1/auth/mfa/verify`.
4. On success, API issues a JWT access token (15 min TTL) and a refresh token (7 day TTL).
5. Client includes the access token as `Authorization: Bearer <token>` on all subsequent requests.
6. When the access token expires, client calls `POST /api/v1/auth/refresh` with the refresh token.
7. For SSO: client redirects to `/api/v1/auth/sso/{provider}/authorize`, which redirects to the IdP. The callback at `/api/v1/auth/sso/callback` exchanges the authorization code for tokens and issues JWT tokens.

### Call Routing (Inbound)

1. SIP trunk delivers an INVITE to FreeSWITCH over TLS (:5061).
2. FreeSWITCH issues an XML CURL request to the API (`/freeswitch/directory` or `/freeswitch/dialplan`) to fetch the routing configuration.
3. API looks up the DID, resolves the inbound route, and returns FreeSWITCH XML defining the dialplan actions (ring group, queue, IVR, extension, voicemail, etc.).
4. FreeSWITCH executes the dialplan: bridges the call, plays prompts, or queues the caller.
5. Call events (CHANNEL_CREATE, CHANNEL_ANSWER, CHANNEL_HANGUP) are received by the ESL event listener running in the API process.
6. The ESL listener writes CDR records, triggers recording storage to MinIO, sends voicemail-to-email notifications, and publishes real-time events to Redis pub/sub.
7. The WebSocket connection manager picks up Redis pub/sub events and pushes them to connected clients.

### Tenant Isolation

Every API request that accesses tenant data follows this path:

1. JWT is decoded to identify the user and their `tenant_id`.
2. For MSP-level roles (`msp_super_admin`, `msp_tech`), the tenant is determined from the URL path parameter (`/tenants/{tenant_id}/...`).
3. For tenant-scoped roles, access is restricted to the user's own tenant.
4. The database session calls `SET LOCAL app.current_tenant = '{tenant_id}'` before executing any queries.
5. PostgreSQL RLS policies on every tenant-scoped table filter rows to only those matching `app.current_tenant`.
6. The `SET LOCAL` is scoped to the current transaction -- when the session returns to the pool, the setting is automatically cleared. No pool leak.

## Multi-Tenancy

### Row-Level Security (RLS)

Every table containing tenant data has a `tenant_id` column and an RLS policy:

```sql
ALTER TABLE extensions ENABLE ROW LEVEL SECURITY;
ALTER TABLE extensions FORCE ROW LEVEL SECURITY;

CREATE POLICY extensions_tenant_isolation ON extensions
    USING (tenant_id::text = current_setting('app.current_tenant', true));
```

Key properties:
- RLS is enforced for `new_phone_app` (the runtime API user) but bypassed for `new_phone_admin` (the migration user).
- The tenant context is set per-transaction using `SET LOCAL`, which is automatically cleared when the transaction ends.
- All tenant-scoped tables inherit from `TenantScopedMixin` in SQLAlchemy, which adds the `tenant_id` column.
- Every migration that adds a new tenant table also adds a corresponding RLS migration (e.g., `0010_queues.py` + `0011_queues_rls.py`).

### Two-User Database Pattern

| User | Role | Purpose |
|---|---|---|
| `new_phone_admin` | Superuser (no RLS) | Runs Alembic migrations, DB initialization, bypasses RLS |
| `new_phone_app` | Limited (RLS enforced) | Used by the API at runtime, every query filtered by tenant |

The `new_phone_app` user is created by `db/init/00-create-roles.sql` during initial PostgreSQL startup. Default privileges ensure it automatically gets `SELECT, INSERT, UPDATE, DELETE` on all tables created by the admin user.

## Authentication Model

### JWT Tokens

- **Access token**: Short-lived (15 min default, configurable via `NP_JWT_ACCESS_TOKEN_EXPIRE_MINUTES`). Contains `sub` (user UUID), `tenant_id`, `role`, `type: "access"`.
- **Refresh token**: Longer-lived (7 days default, configurable via `NP_JWT_REFRESH_TOKEN_EXPIRE_DAYS`). Used to obtain new access tokens without re-authentication.
- Algorithm: HS256 (configurable via `NP_JWT_ALGORITHM`).
- Secret: `NP_JWT_SECRET_KEY` (must be a strong random string in production).

### TOTP MFA

- Users can enable MFA via `POST /api/v1/auth/mfa/setup`, which generates a TOTP secret and returns a QR code URI.
- On login, if MFA is enabled, the initial auth response requires a second step: `POST /api/v1/auth/mfa/verify` with the 6-digit TOTP code.
- TOTP secrets are stored encrypted in the database.
- Issuer name: configurable via `NP_MFA_ISSUER` (default: "NewPhone").

### SSO (Single Sign-On)

- Supports Microsoft Entra ID and Google Workspace via OpenID Connect (OIDC).
- Per-tenant SSO configuration: each tenant can configure their own IdP.
- SSO role mappings allow automatic role assignment based on IdP group claims.
- Flow: client redirects to API -> API redirects to IdP -> IdP callback -> API issues JWT tokens.
- SSO users can optionally have a local password as fallback.

### RBAC (Role-Based Access Control)

Five roles with hierarchical permissions:

| Role | Scope | Description |
|---|---|---|
| `msp_super_admin` | Platform | Full platform access, all tenants, all features |
| `msp_tech` | Platform | MSP technician, all tenants, all features except platform management |
| `tenant_admin` | Tenant | Full admin of their own tenant |
| `tenant_manager` | Tenant | Manages users and day-to-day operations within their tenant |
| `tenant_user` | Tenant | End user with self-service access (own profile, voicemail, call history, click-to-call) |

Permissions are checked via FastAPI dependencies:

```python
@router.get("/tenants/{tenant_id}/extensions")
async def list_extensions(
    user: Annotated[User, Depends(require_permission(Permission.VIEW_EXTENSIONS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    ...
```

## API Design

### URL Structure

All authenticated endpoints are prefixed with `/api/v1/`. Tenant-scoped resources follow the pattern:

```
/api/v1/tenants/{tenant_id}/extensions
/api/v1/tenants/{tenant_id}/extensions/{extension_id}
/api/v1/tenants/{tenant_id}/users
/api/v1/tenants/{tenant_id}/sip-trunks
```

Platform-level endpoints:

```
/api/v1/auth/login
/api/v1/auth/refresh
/api/v1/health
/api/v1/admin/tenants
```

Internal endpoints (no `/api/v1` prefix, Docker-network only):

```
/freeswitch/directory          XML CURL directory requests
/freeswitch/dialplan           XML CURL dialplan requests
/provision/{mac_address}       Phone auto-provisioning
/phone-apps/{mac_address}/*    Desk phone XML apps
/sms/webhook/{provider}        SMS provider webhooks
/building/webhook              Building system webhooks (HMAC-validated)
```

### Error Responses (RFC 7807)

All errors follow the RFC 7807 Problem Details format:

```json
{
  "type": "about:blank",
  "title": "Not Found",
  "status": 404,
  "detail": "Extension 1001 not found",
  "instance": "/api/v1/tenants/abc-123/extensions/1001"
}
```

### OpenAPI Documentation

- Swagger UI: `http://localhost:8000/api/docs`
- ReDoc: `http://localhost:8000/api/redoc`
- OpenAPI JSON: `http://localhost:8000/api/openapi.json`

## FreeSWITCH Integration

### Communication

The API communicates with FreeSWITCH in two directions:

**API -> FreeSWITCH (ESL)**:
- The API connects to FreeSWITCH via the Event Socket Layer (ESL) on port 8021.
- Used for: originating calls, transferring calls, sending commands, reloading configuration.
- A persistent ESL connection is maintained for subscribing to real-time events (CHANNEL_CREATE, CHANNEL_ANSWER, CHANNEL_HANGUP, RECORD_START, RECORD_STOP, etc.).
- Connection is managed by `FreeSwitchService` using raw async sockets (no third-party ESL library).

**FreeSWITCH -> API (XML CURL)**:
- FreeSWITCH requests configuration from the API via HTTP (XML CURL binding).
- The API generates FreeSWITCH XML configuration dynamically based on the database state.
- Used for: user directory (SIP registration credentials), dialplan (call routing rules), configuration (codecs, profiles).
- The `xml_builder.py` module generates compliant FreeSWITCH XML.

### Security

- **SIP TLS mandatory**: All SIP signaling is encrypted. No UDP or TCP SIP is exposed.
- **SRTP mandatory**: All media (RTP) is encrypted.
- TLS certificates are in `freeswitch/tls/` (gitignored, generated via `make tls-cert` for development).
- SIP trunk credentials are encrypted at rest using Fernet symmetric encryption (`NP_TRUNK_ENCRYPTION_KEY`).

### Configuration Sync

When the API modifies configuration that affects FreeSWITCH (extensions, SIP profiles, dial plans), it notifies FreeSWITCH to reload via ESL commands. The `ConfigSync` class wraps these operations.

## AI Engine

The AI Engine is a separate service that provides conversational AI capabilities for voice calls.

### Architecture

```
                FreeSWITCH
                    |
              WebSocket (:8090)
                    |
            +-------v--------+
            |   AI Engine    |
            |                |
            |  +----------+  |
            |  | Session  |  |    +----------+
            |  | Manager  |  |    | Provider |
            |  +----+-----+  |    | Registry |
            |       |         |    +----+-----+
            |  +----v-----+  |         |
            |  | Pipeline  |  +---------+
            |  |           |  |
            |  | STT ----+ |  |   STT: Deepgram, Google, OpenAI Whisper
            |  | LLM ----+ |  |   LLM: OpenAI, Anthropic, Google Gemini
            |  | TTS ----+ |  |   TTS: ElevenLabs, Google, OpenAI
            |  +-----------+  |
            |                 |
            |  Tools:         |
            |  - Transfer     |
            |  - Lookup CRM   |
            |  - Create ticket|
            |  - Custom       |
            +-----------------+
```

### Pipeline

1. **Audio ingress**: Raw audio from FreeSWITCH arrives over WebSocket.
2. **VAD (Voice Activity Detection)**: WebRTC VAD detects speech segments.
3. **STT (Speech-to-Text)**: Speech is transcribed using a configured provider.
4. **LLM (Language Model)**: Transcribed text is sent to the LLM with conversation context and available tools.
5. **Tool execution**: If the LLM requests a tool call (transfer, CRM lookup, etc.), it is executed and the result fed back.
6. **TTS (Text-to-Speech)**: The LLM response is synthesized to audio.
7. **Audio egress**: Synthesized audio is streamed back to FreeSWITCH over WebSocket.

### Configuration

AI agents are configured per-tenant via the API (`/api/v1/tenants/{tenant_id}/ai-agents`). Each agent has:
- A system prompt defining its persona and behavior
- Provider configuration (which STT/LLM/TTS providers and models to use)
- Tool definitions (what actions the agent can take)
- Conversation context rules

Provider API keys are stored encrypted in the database, same as SIP trunk credentials.

## Real-Time Events

### WebSocket

Clients connect to `/api/v1/ws/events` with a JWT token. The server pushes real-time events:

- Call state changes (ringing, answered, hung up)
- Queue status updates
- Parking lot changes
- SMS message arrivals
- System alerts

### Redis Pub/Sub

Internal services publish events to Redis channels. The WebSocket connection manager subscribes to these channels and fans events out to connected clients, filtered by tenant.

## Infrastructure Services

| Service | Image | Purpose | Ports |
|---|---|---|---|
| postgres | postgres:17-bookworm | Primary database with RLS | 5434:5432 |
| redis | redis:7-bookworm | Cache, pub/sub, rate limiting | 6379 |
| minio | minio/minio:latest | Object storage (recordings, voicemail) | 9000, 9001 |
| mailhog | mailhog/mailhog:latest | Development SMTP/email viewer | 1025, 8025 |
| freeswitch | Custom (./freeswitch) | Media engine | 5061 (SIP TLS), 7443 (WSS), 8021 (ESL) |
| api | Custom (./api) | REST API | 8000 |
| web | Custom (./web) | React frontend (nginx) | 3000 |
| ai-engine | Custom (./ai-engine) | AI voice agent engine | 8090 (WS), 8091 (API) |

All services are on a shared Docker network (`new_phone_net`). Named volumes with `new_phone_` prefix prevent conflicts with other projects.
