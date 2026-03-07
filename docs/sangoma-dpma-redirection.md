# Sangoma DPMA Redirection Setup

How to point a Sangoma P-series phone at our platform using Sangoma's Zero Touch Configuration portal.

## Portal Access

- URL: Sangoma portal (portal.sangoma.com or similar)
- Navigate: **Phones** > select the phone by MAC address > **Edit Sangoma Phone**

## Zero Touch Configuration Fields

| Field | Description | Required Value |
|-------|-------------|----------------|
| **Enable Redirection** | Checkbox — must be checked | Checked |
| **Redirection Type** | `IP/FQDN` or other options | `IP/FQDN` |
| **Sangoma Configuration Server Address** | FQDN or IP of your server | `ucc.aspendora.com` |
| **Server DPMA Port** | Port the phone connects to for SIP | `5061` |
| **Server Transport** | `UDP`, `TCP`, or `TLS` | `TLS` |
| **Full Address** | Auto-generated from above fields | `ucc.aspendora.com:5061;transport=tls` |

## How It Works

1. Phone boots and contacts Sangoma's cloud redirection service.
2. Sangoma's service looks up the phone's MAC address.
3. If redirection is enabled, it tells the phone to connect to the configured server address instead.
4. Phone SIP-registers with our sip-proxy (port 5061, TLS).
5. sip-proxy forwards registration to FreeSWITCH backend (port 5060, internal).
6. Phone fetches provisioning config via HTTPS: `GET /provisioning/{mac}.xml`
   - nginx terminates TLS on port 443
   - Proxies to Python API (`api:8000/provisioning/`)
   - API looks up device by MAC, renders Sangoma XML config from Jinja2 templates

## Current Test Phone

| Property | Value |
|----------|-------|
| Model | Sangoma P325 |
| MAC | 000FD3D202F7 |
| Company | Aspendora Technologies, LLC |
| Redirect Target | `ucc.aspendora.com:5061;transport=tls` |

**Note:** Portal screenshot (2026-03-07) showed port 5060/UDP — needs to be updated to 5061/TLS.

## Architecture

```
Sangoma Cloud Redirect
        |
        v (tells phone to connect to ucc.aspendora.com:5061;transport=tls)
   Sangoma P325
        |
        |--- SIP TLS (5061) ---> sip-proxy (Rust) ---> FreeSWITCH (5060 internal)
        |
        |--- HTTPS (443) -----> nginx ---> Python API (8000 internal)
                                           GET /provisioning/{mac}.xml
                                           (Jinja2 templates: sangoma/base.cfg.xml.j2)
```

### Service Roles

| Service | Port | Protocol | Role |
|---------|------|----------|------|
| **sip-proxy** (Rust) | 5061/tcp | SIP over TLS | Phone registration + call signaling. TLS termination, load-balanced to FreeSWITCH. |
| **nginx** (web) | 443/tcp | HTTPS | Reverse proxy. Terminates TLS for provisioning, phone apps, web UI, API. |
| **API** (Python) | 8000 (internal) | HTTP | Provisioning endpoint at `/provisioning/{mac}.xml`. DB-backed, Jinja2 templates, per-tenant config. |
| **dpma-service** (Rust) | 8082 (internal) | HTTP | Future: real-time BLF push, presence updates, firmware management. Currently skeleton. |
| **FreeSWITCH** | 5060 (internal) | SIP | Media engine. Receives forwarded registrations from sip-proxy. |

### What the Phone Gets

The Sangoma XML config template (`api/src/new_phone/provisioning/templates/sangoma/base.cfg.xml.j2`) includes:
- SIP account: server, port 5061, TLS transport, SRTP mode 2 (mandatory)
- Network: DHCP, LLDP
- Time: NTP server, timezone
- Line keys and BLF keys (from `keys.cfg.xml.j2`)

## Sangoma Portal Update Required

The portal currently shows:
- Port: 5060, Transport: UDP

Needs to be changed to:
- Port: **5061**, Transport: **TLS**

## Setup Checklist

1. [ ] Generate or install TLS certs for sip-proxy (`make tls-sip-proxy` for dev, Let's Encrypt for prod)
2. [ ] Build sip-proxy Docker image (`make rust-docker-one SVC=sip-proxy`)
3. [ ] Ensure port 5061/tcp is open in firewall
4. [ ] Register the Sangoma phone in the platform (device + extension assignment)
5. [ ] Update Sangoma portal: port 5061, transport TLS
6. [ ] Reboot the phone — it should redirect, SIP-register, and fetch config

## Source

Screenshot from Sangoma portal, captured 2026-03-07.
