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
| **Sangoma Configuration Server Address** | FQDN or IP of your server | `sip.aspendora.com` |
| **Server DPMA Port** | Port the phone connects to for SIP | `5061` |
| **Server Transport** | `UDP`, `TCP`, or `TLS` | `TLS` |
| **Full Address** | Auto-generated from above fields | `sip.aspendora.com:5061;transport=tls` |

**Important:** Use `sip.aspendora.com` (DNS-only, not Cloudflare-proxied) — NOT `ucc.aspendora.com` (Cloudflare-proxied). Cloudflare only proxies HTTP/HTTPS; SIP traffic on port 5061 will be silently dropped by Cloudflare.

## How It Works

1. Phone boots and contacts Sangoma's cloud redirection service.
2. Sangoma's service looks up the phone's MAC address.
3. If redirection is enabled, it tells the phone to connect to the configured server address instead.
4. Phone SIP-registers with FreeSWITCH (port 5061, TLS) directly.
5. Phone fetches provisioning config via HTTPS: `GET /provisioning/{mac}.xml`
   - nginx terminates TLS on port 443
   - Proxies to Python API (`api:8000/provisioning/`)
   - API looks up device by MAC, renders Sangoma XML config from Jinja2 templates

## Current Test Phone

| Property | Value |
|----------|-------|
| Model | Sangoma P325 |
| MAC | 000FD3D202F7 |
| Company | Aspendora Technologies, LLC |
| Redirect Target | `sip.aspendora.com:5061;transport=tls` |

## Architecture

```
Sangoma Cloud Redirect
        |
        v (tells phone to connect to sip.aspendora.com:5061;transport=tls)
   Sangoma P325
        |
        |--- SIP TLS (5061) ---> FreeSWITCH (host network, Let's Encrypt cert)
        |
        |--- HTTPS (443) -----> Cloudflare ---> nginx ---> Python API (8000)
                                                           GET /provisioning/{mac}.xml
                                                           (Jinja2 templates: sangoma/base.cfg.xml.j2)
```

### DNS Setup

| Domain | Points To | Cloudflare Proxy | Purpose |
|--------|-----------|-----------------|---------|
| `ucc.aspendora.com` | Cloudflare IPs | Yes (proxied) | Web UI, API, provisioning HTTPS |
| `sip.aspendora.com` | `149.28.251.164` | No (DNS-only) | SIP TLS (port 5061) |

### Service Roles

| Service | Port | Protocol | Role |
|---------|------|----------|------|
| **FreeSWITCH** | 5061/tcp | SIP over TLS | Phone registration + call signaling. Host network, Let's Encrypt cert. |
| **nginx** (web) | 443/tcp | HTTPS | Reverse proxy. Terminates TLS for provisioning, phone apps, web UI, API. |
| **API** (Python) | 8000 (internal) | HTTP | Provisioning endpoint at `/provisioning/{mac}.xml`. DB-backed, Jinja2 templates, per-tenant config. |
| **dpma-service** (Rust) | 8082 (internal) | HTTP | Future: real-time BLF push, presence updates, firmware management. Currently skeleton. |
| **sip-proxy** (Rust) | 5061 (internal) | SIP over TLS | Future: multi-backend load balancing. Currently not exposed externally. |

### What the Phone Gets

The Sangoma XML config template (`api/src/new_phone/provisioning/templates/sangoma/base.cfg.xml.j2`) includes:
- SIP account: server `sip.aspendora.com`, port 5061, TLS transport, SRTP mode 2 (mandatory)
- Network: DHCP, LLDP
- Time: NTP server, timezone
- Line keys and BLF keys (from `keys.cfg.xml.j2`)

### TLS Certificate

- Let's Encrypt cert: CN=ucc.aspendora.com, SANs: ucc.aspendora.com + sip.aspendora.com
- Location on server: `/etc/letsencrypt/live/ucc.aspendora.com/`
- FreeSWITCH cert dir: `/opt/new-phone/freeswitch/tls/` (agent.pem = cert+key combined)
- Auto-renewal via certbot + Cloudflare DNS plugin
- Deploy hook: `/etc/letsencrypt/renewal-hooks/deploy/newphone-freeswitch.sh`

## Setup Checklist

1. [x] Let's Encrypt cert with `sip.aspendora.com` SAN (obtained via DNS-Cloudflare challenge)
2. [x] Cert deployed to FreeSWITCH (`agent.pem` + `cafile.pem`)
3. [x] Port 5061/tcp open in firewall (UFW)
4. [x] DNS: `sip.aspendora.com` → `149.28.251.164` (Cloudflare DNS-only)
5. [ ] Register the Sangoma phone in the platform (device + extension assignment)
6. [ ] Update Sangoma portal: server `sip.aspendora.com`, port `5061`, transport `TLS`
7. [ ] Reboot the phone — it should redirect, SIP-register, and fetch config
