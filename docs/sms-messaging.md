# SMS Messaging — Setup Guide

## Overview

Phase 31 adds SMS messaging capabilities to the platform. Each tenant can configure their own SMS provider (ClearlyIP or Twilio), send/receive SMS through the admin UI, and have conversations automatically tracked with full opt-out compliance.

## Architecture

```
Customer Phone ←→ SMS Provider (ClearlyIP/Twilio) ←→ Webhook Endpoints ←→ API ←→ Database
                                                                                    ↕
                                                                               Admin UI
```

- **Provider abstraction** — `api/src/new_phone/sms/` contains a pluggable provider layer
- **Conversations** — Messages are grouped into conversations by (DID + remote number)
- **Opt-out enforcement** — STOP/START/HELP keywords are handled at the platform level

## Configuration

### 1. Enable SMS on a DID

In the DIDs page or via API, set `sms_enabled: true` on any DID that should handle SMS:

```
PATCH /api/v1/tenants/{tid}/dids/{did_id}
{ "sms_enabled": true }
```

### 2. Configure an SMS Provider

Navigate to **SMS > SMS Providers** in the admin UI, or use the API:

#### ClearlyIP

```json
POST /api/v1/tenants/{tid}/sms/providers
{
  "provider_type": "clearlyip",
  "label": "ClearlyIP Production",
  "credentials": {
    "trunk_token": "YOUR_CLEARLYIP_TRUNK_TOKEN"
  },
  "is_default": true
}
```

#### Twilio

```json
POST /api/v1/tenants/{tid}/sms/providers
{
  "provider_type": "twilio",
  "label": "Twilio Production",
  "credentials": {
    "account_sid": "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "auth_token": "YOUR_TWILIO_AUTH_TOKEN"
  },
  "is_default": true
}
```

Credentials are encrypted at rest using Fernet symmetric encryption (same key as SIP trunk passwords: `NP_TRUNK_ENCRYPTION_KEY`).

### 3. Set Up Webhooks on the Provider Side

Configure your SMS provider to send inbound messages and status callbacks to these URLs:

#### ClearlyIP
- **Inbound SMS:** `https://your-domain.com/sms/inbound/clearlyip`
- **Delivery Status:** `https://your-domain.com/sms/status/clearlyip`

#### Twilio
- **Inbound SMS (Messaging Webhook):** `https://your-domain.com/sms/inbound/twilio`
- **Status Callback URL:** `https://your-domain.com/sms/status/twilio`

These endpoints are unauthenticated (providers can't send JWTs). Twilio supports signature verification via `X-Twilio-Signature`.

## Sending Messages

### Via API

```
POST /api/v1/tenants/{tid}/sms/conversations/{cid}/messages
{ "body": "Hello, how can we help?" }
```

### Via Admin UI

1. Navigate to **SMS > Conversations**
2. Select a conversation from the left panel
3. Type a message in the compose bar and press Enter or click Send

## Receiving Messages

Inbound messages arrive via webhook and are automatically:
1. Matched to the correct tenant via the DID number
2. Added to an existing conversation (or a new one is created)
3. Checked for opt-out keywords (STOP/START/HELP)

## Opt-Out Handling

The platform enforces SMS opt-out at the application level:

| Keyword | Action |
|---------|--------|
| STOP, STOPALL, UNSUBSCRIBE, CANCEL, END, QUIT | Opts out the sender, sends confirmation |
| START, UNSTOP, SUBSCRIBE | Re-subscribes the sender, sends confirmation |
| HELP, INFO | Sends usage instructions |

Once opted out:
- Outbound sends to that number are **blocked** with an error
- Inbound messages from opted-out numbers are **silently dropped** (except the STOP message itself)

## Conversation States

| State | Meaning |
|-------|---------|
| `open` | Active, needs attention |
| `waiting` | Agent replied, waiting for customer response |
| `resolved` | Issue resolved |
| `archived` | Closed/archived |

State transitions:
- New inbound → `open`
- Agent sends reply → `waiting`
- Customer replies to `waiting` → `open`
- Agent marks resolved → `resolved`
- Inbound to `resolved`/`archived` → re-opens to `open`

## RBAC Permissions

| Permission | Roles |
|-----------|-------|
| `manage_sms` | MSP Super Admin, MSP Tech, Tenant Admin |
| `view_sms` | All roles (MSP Super Admin, MSP Tech, Tenant Admin, Tenant Manager, Tenant User) |

## API Endpoints

### Conversations
| Method | Path | Permission |
|--------|------|------------|
| GET | `/api/v1/tenants/{tid}/sms/conversations` | view_sms |
| GET | `/api/v1/tenants/{tid}/sms/conversations/{cid}` | view_sms |
| PATCH | `/api/v1/tenants/{tid}/sms/conversations/{cid}` | manage_sms |
| GET | `/api/v1/tenants/{tid}/sms/conversations/{cid}/messages` | view_sms |
| POST | `/api/v1/tenants/{tid}/sms/conversations/{cid}/messages` | manage_sms |
| GET | `/api/v1/tenants/{tid}/sms/conversations/{cid}/notes` | view_sms |
| POST | `/api/v1/tenants/{tid}/sms/conversations/{cid}/notes` | manage_sms |

### Provider Configs
| Method | Path | Permission |
|--------|------|------------|
| GET | `/api/v1/tenants/{tid}/sms/providers` | manage_sms |
| POST | `/api/v1/tenants/{tid}/sms/providers` | manage_sms |
| GET | `/api/v1/tenants/{tid}/sms/providers/{id}` | manage_sms |
| PATCH | `/api/v1/tenants/{tid}/sms/providers/{id}` | manage_sms |
| DELETE | `/api/v1/tenants/{tid}/sms/providers/{id}` | manage_sms |

### Webhooks (unauthenticated)
| Method | Path | Source |
|--------|------|--------|
| POST | `/sms/inbound/clearlyip` | ClearlyIP |
| POST | `/sms/inbound/twilio` | Twilio |
| POST | `/sms/status/clearlyip` | ClearlyIP |
| POST | `/sms/status/twilio` | Twilio |

## Database Tables

- `sms_provider_configs` — Per-tenant provider credentials (encrypted)
- `conversations` — SMS conversation threads (unique per tenant+DID+remote)
- `messages` — Individual SMS messages
- `conversation_notes` — Internal agent notes
- `sms_opt_outs` — Opt-out tracking per DID+phone
- `dids.sms_enabled` — Boolean flag on existing DIDs table

All tables use Row-Level Security for tenant isolation.
