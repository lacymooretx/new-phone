# Phone Provisioning (Phase 30)

## Overview

The Aspendora Connect platform supports HTTP auto-provisioning for Yealink desk phones. When a phone boots, it pulls its configuration from the platform automatically, including SIP credentials, display settings, and BLF/line key assignments.

## How It Works

1. **DHCP Option 66** — Configure your DHCP server to send Option 66 (TFTP Server) or Option 160 (Provisioning URL) pointing to `http://<your-server>:8000/provisioning/`
2. **Phone Boot** — Yealink phones request `GET /provisioning/{mac}.cfg` where `{mac}` is the phone's MAC address in lowercase hex (e.g., `001565abcdef.cfg`)
3. **Config Delivery** — The platform looks up the MAC, loads the assigned extension's SIP credentials, renders a Jinja2 template, and returns the config as `text/plain`
4. **Registration** — The phone parses the config and registers to FreeSWITCH with the correct SIP credentials

## Registering a Phone

### Via Admin UI

1. Navigate to **Telephony → Devices**
2. Click **Register Device**
3. Enter the phone's MAC address (formats accepted: `AA:BB:CC:DD:EE:FF`, `aa-bb-cc-dd-ee-ff`, `aabbccddeeff`)
4. Select the phone model from the dropdown
5. Optionally assign an extension
6. Set a name and location for easy identification
7. Click **Create Device**

### Assigning BLF/Line Keys

1. From the Devices list, click the **⋮** menu on a device
2. Select **Line Keys**
3. Configure each key slot:
   - **Line** — Primary SIP line registration
   - **BLF** — Busy Lamp Field (monitor another extension's status)
   - **Speed Dial** — One-touch dial a number
   - **DTMF** — Send DTMF tones
   - **Park** — Call parking slot
   - **Intercom** — Direct intercom to another extension
4. Click **Save Keys**

### Getting the Provisioning URL

- Click the **⋮** menu → **Copy Provisioning URL**
- The URL format is: `http://<server>/provisioning/<mac>.cfg`

## DHCP Configuration

### ISC DHCP Server

```
option tftp-server-name "http://pbx.example.com:8000/provisioning/";
```

### Mikrotik

```
/ip dhcp-server option
add code=66 name=tftp-server value="'http://pbx.example.com:8000/provisioning/'"
```

### Windows DHCP

1. Open DHCP Manager
2. Right-click the scope → Set Predefined Options
3. Set Option 66 to `http://pbx.example.com:8000/provisioning/`

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NP_PROVISIONING_SIP_SERVER` | `pbx.example.com` | SIP server address phones will register to |
| `NP_PROVISIONING_NTP_SERVER` | `pool.ntp.org` | NTP server for phone time sync |
| `NP_PROVISIONING_TIMEZONE` | `America/New_York` | Default timezone for phones |

## Supported Phone Models

### Yealink T-Series (Seeded)

| Model | Line Keys | Expansion | Color | WiFi | BT | PoE | Gigabit |
|-------|-----------|-----------|-------|------|----|-----|---------|
| T58W  | 27        | 3×40      | Yes   | Yes  | Yes| Yes | Yes     |
| T54W  | 27        | 3×40      | Yes   | Yes  | Yes| Yes | Yes     |
| T53W  | 21        | 3×40      | Yes   | Yes  | No | Yes | Yes     |
| T46U  | 27        | 3×40      | Yes   | No   | No | Yes | Yes     |
| T43U  | 21        | 3×40      | No    | No   | No | Yes | Yes     |
| T33G  | 12        | —         | Yes   | No   | No | Yes | Yes     |
| T31G  | 2         | —         | No    | No   | No | Yes | Yes     |
| T31P  | 2         | —         | No    | No   | No | Yes | No      |

## Template Customization

Templates are Jinja2 files located at:
```
api/src/new_phone/provisioning/templates/yealink/
├── base.cfg.j2    # Account, network, NTP, security settings
└── keys.cfg.j2    # Line keys and expansion module keys
```

### Available Template Variables

| Variable | Type | Description |
|----------|------|-------------|
| `device` | Device | The device model instance |
| `extension` | Extension | The assigned extension (null if none) |
| `tenant` | Tenant | The tenant owning this device |
| `phone_model` | PhoneModel | The phone model reference |
| `sip_password` | str | Decrypted SIP password |
| `sip_domain` | str | Tenant's SIP domain |
| `sip_server` | str | FreeSWITCH server address |
| `ntp_server` | str | NTP server address |
| `timezone` | str | Phone timezone |
| `line_keys` | list | Line key configurations |
| `expansion_keys` | list | Expansion module key configurations |
| `key_type_map` | dict | Yealink key type code mapping |

## Security Notes

- The provisioning endpoint is **unauthenticated** (phones cannot send JWTs)
- Only registered MACs receive configurations — unknown MACs get 404
- SIP passwords are decrypted at render time and sent in plaintext in the config
- **For production hardening (future):** add rate limiting, HMAC URL tokens, IP allowlisting, HTTPS

## API Endpoints

### Phone Models (global, MSP-managed)

```
GET    /api/v1/phone-models          — List all phone models
POST   /api/v1/phone-models          — Create phone model
GET    /api/v1/phone-models/{id}     — Get phone model
PATCH  /api/v1/phone-models/{id}     — Update phone model
DELETE /api/v1/phone-models/{id}     — Deactivate phone model
```

### Devices (tenant-scoped)

```
GET    /api/v1/tenants/{tid}/devices           — List devices
POST   /api/v1/tenants/{tid}/devices           — Register device
GET    /api/v1/tenants/{tid}/devices/{id}      — Get device
PATCH  /api/v1/tenants/{tid}/devices/{id}      — Update device
DELETE /api/v1/tenants/{tid}/devices/{id}      — Deactivate device
GET    /api/v1/tenants/{tid}/devices/{id}/keys — Get device keys
PUT    /api/v1/tenants/{tid}/devices/{id}/keys — Bulk update keys
```

### Provisioning (unauthenticated)

```
GET    /provisioning/{mac}.cfg    — Get phone config by MAC
```
