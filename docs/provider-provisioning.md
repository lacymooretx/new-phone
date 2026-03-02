# Provider Provisioning

## Overview

The platform uses a provider abstraction layer for DID (phone number) and SIP trunk management. Two providers are supported: ClearlyIP and Twilio. All provider operations go through the `TelephonyProvider` abstract base class at `api/src/new_phone/providers/base.py`.

## Architecture

```
Admin UI / API
      |
  Provider Factory  (api/src/new_phone/providers/factory.py)
      |
  ┌───┴───┐
  │       │
ClearlyIP  Twilio
Provider   Provider
```

The factory uses `get_provider(provider_type)` to return the correct implementation. Per-tenant provider selection (`get_tenant_provider()`) checks if the tenant has an existing SIP trunk with a `provider_type` set; if not, it defaults to ClearlyIP.

## DID Provisioning

### Workflow: Search, Purchase, Configure

1. **Search** -- Find available numbers by area code or state.
2. **Purchase** -- Buy a specific number from the provider.
3. **Configure Routing** -- Set voice/SMS routing for the DID at the provider level.

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/tenants/{tid}/dids/search?area_code=512&quantity=10` | Search provider inventory |
| POST | `/api/v1/tenants/{tid}/dids/purchase` | Purchase a DID from provider, create local record |
| PATCH | `/api/v1/tenants/{tid}/dids/{did_id}` | Update local DID record |
| POST | `/api/v1/tenants/{tid}/dids/{did_id}/configure-routing` | Push routing config to provider |
| DELETE | `/api/v1/tenants/{tid}/dids/{did_id}` | Release DID at provider and deactivate locally |

### Search Request

```
GET /api/v1/tenants/{tid}/dids/search?area_code=512&state=TX&quantity=5
Authorization: Bearer {token}
```

Returns a list of available numbers with monthly cost, setup cost, and capabilities (voice, SMS, MMS, fax).

### Purchase Request

```json
POST /api/v1/tenants/{tid}/dids/purchase
{
  "provider": "clearlyip",
  "number": "+15125551234"
}
```

This calls `provider.purchase_did()`, then creates a local DID record in the database with the `provider_sid` for future reference.

## SIP Trunk Provisioning

### Workflow: Create, Configure, Test

1. **Provision** -- Create a trunk at the provider (returns host, port, credentials).
2. **Verify** -- Test SIP connectivity via OPTIONS ping.
3. **Deprovision** -- Delete the trunk at the provider and deactivate locally.

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/tenants/{tid}/trunks/provision` | Create trunk at provider + local record |
| POST | `/api/v1/tenants/{tid}/trunks/{id}/test` | SIP OPTIONS connectivity test |
| POST | `/api/v1/tenants/{tid}/trunks/{id}/deprovision` | Delete at provider + deactivate locally |
| GET | `/api/v1/tenants/{tid}/trunks` | List all trunks |
| POST | `/api/v1/tenants/{tid}/trunks` | Create trunk manually (no provider) |

### Provision Request

```json
POST /api/v1/tenants/{tid}/trunks/provision
{
  "provider": "clearlyip",
  "name": "Primary Trunk",
  "region": "us-east",
  "channels": 30,
  "config": {}
}
```

The service calls `provider.create_trunk()`, encrypts the returned password with Fernet, and stores the trunk record. FreeSWITCH config sync runs automatically (cache flush + sofia rescan).

### Test Result

```json
POST /api/v1/tenants/{tid}/trunks/{id}/test

Response:
{
  "status": "healthy",
  "latency_ms": 42.5,
  "error": null
}
```

If the trunk is not provider-managed (created manually), the test returns `status: "skipped"`.

## Tenant Onboarding (Automated)

The onboarding endpoint orchestrates the full provisioning flow for a new tenant:

```
POST /api/v1/onboarding
```

Steps performed:
1. Create tenant (name, slug, SIP domain)
2. Provision SIP trunk via provider
3. Purchase DIDs (if requested)
4. Create admin user

Check onboarding status:

```
GET /api/v1/onboarding/{tenant_id}/status
```

Returns per-step status: `create_tenant`, `provision_trunk`, `purchase_dids`.

## Provider Differences

| Feature | ClearlyIP | Twilio |
|---------|-----------|--------|
| DID search | Area code + state | Area code + state |
| DID purchase | Instant activation | Instant activation |
| SIP trunks | Registration-based auth | Credential-based auth |
| SMS | Trunk token auth | Account SID + auth token |
| Webhook verification | None (IP whitelist recommended) | HMAC signature (`X-Twilio-Signature`) |
| Default provider | Yes (platform default) | No |

## Configuration (Environment Variables)

All env vars use the `NP_` prefix.

| Variable | Description | Required |
|----------|-------------|----------|
| `NP_CLEARLYIP_API_URL` | ClearlyIP API base URL | Yes (if using ClearlyIP) |
| `NP_CLEARLYIP_API_KEY` | ClearlyIP API key | Yes (if using ClearlyIP) |
| `NP_TWILIO_ACCOUNT_SID` | Twilio account SID | Yes (if using Twilio) |
| `NP_TWILIO_AUTH_TOKEN` | Twilio auth token | Yes (if using Twilio) |
| `NP_TRUNK_ENCRYPTION_KEY` | Fernet key for encrypting trunk passwords | Yes |

Generate a Fernet key:

```python
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
```

## FreeSWITCH Config Sync

After any trunk provisioning/deprovisioning, the API triggers:

1. `flush_xml_cache` -- Clears the mod_xml_curl cache
2. `sofia_profile_rescan` -- Reloads SIP profiles to pick up new gateways

After trunk updates, it additionally calls `kill_gateway(old_name)` to remove the stale gateway before rescan.

These are best-effort: if FreeSWITCH is unreachable, the API operation still succeeds. Changes take effect on FS restart or next cache expiry.

## Key Source Files

| File | Purpose |
|------|---------|
| `api/src/new_phone/providers/base.py` | Abstract base class + dataclasses |
| `api/src/new_phone/providers/clearlyip.py` | ClearlyIP implementation |
| `api/src/new_phone/providers/twilio.py` | Twilio implementation |
| `api/src/new_phone/providers/factory.py` | Provider factory + tenant provider resolution |
| `api/src/new_phone/routers/sip_trunks.py` | SIP trunk API endpoints |
| `api/src/new_phone/routers/dids.py` | DID API endpoints |
| `api/src/new_phone/routers/onboarding.py` | Tenant onboarding orchestration |
| `api/src/new_phone/services/sip_trunk_service.py` | Trunk CRUD + provider operations |
| `api/src/new_phone/services/did_service.py` | DID CRUD + provider operations |
| `api/src/new_phone/freeswitch/config_sync.py` | FreeSWITCH cache/profile sync |
