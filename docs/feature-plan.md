# Feature Plan — New Phone Platform

> Multi-tenant, API-first PBX platform built on FreeSWITCH
> Last updated: 2026-02-25

---

## 1. Authentication & Identity

### Login Methods
- **Microsoft Entra ID (Azure AD)** — SSO via OIDC/SAML, tenant mapping (Entra tenant → PBX tenant)
- **Google Workspace / Google Identity** — SSO via OIDC
- **Traditional email + password** — with mandatory MFA

### MFA (traditional login only)
- TOTP (authenticator app — Google Authenticator, Authy, Microsoft Authenticator, etc.)
- WebAuthn/FIDO2 (hardware keys — YubiKey, passkeys)
- SMS fallback (optional, admin-configurable per tenant)
- Recovery codes (one-time use, generated at MFA enrollment)

### Identity Architecture
- MSP admin can enforce auth method per tenant (e.g., "Tenant A must use Entra ID")
- Entra ID / Google groups can map to PBX roles (admin, manager, user)
- Session management: JWT access tokens (short-lived) + refresh tokens
- API keys for service accounts / integrations (per tenant, scoped permissions)
- Audit log of all auth events (login, logout, MFA challenge, failed attempts)
- Account lockout after configurable failed attempts
- Password policy enforcement (length, complexity, expiry — configurable per tenant)

### User Roles (RBAC)
| Role | Scope | Capabilities |
|------|-------|-------------|
| MSP Super Admin | All tenants | Full platform access, tenant provisioning, global settings |
| MSP Technician | Assigned tenants | Manage assigned tenant configs, view CDR, troubleshoot |
| Tenant Admin | Single tenant | Full control of own tenant (extensions, routing, recordings, etc.) |
| Tenant Manager | Single tenant | Manage users, view reports, limited config changes |
| Tenant User | Single tenant | Own extension settings, voicemail, presence, call history |

---

## 2. Core Telephony — Per Tenant Features

### Extensions
- SIP over TLS endpoint registration (SRTP mandatory for all media)
- WebRTC endpoint (web client)
- Mobile endpoint (Flutter app)
- Per-extension caller ID (internal + external)
- Per-extension E911 location assignment
- Emergency CID override
- Multiple device registration per extension (desk phone + softphone + mobile)
- Do Not Disturb (DND) toggle
- Call Forward: unconditional, busy, no answer, not registered (per destination)
- Call Waiting toggle
- Voicemail assignment
- Class of Service assignment (controls what features/routes the extension can use)
- Hot Desking — login to any physical phone with your extension
- Extension mobility — roaming between tenant locations

### Ring Groups
- Static member lists
- Dynamic members (via login/logout)
- Ring strategies: simultaneous, sequential, random, round-robin, memory hunt
- Configurable ring time per member and total
- Skip busy agents option
- Caller ID passthrough vs. ring group name
- Failover destination (voicemail, IVR, external number, another group)
- CID name prefix (e.g., "SALES: John Doe")
- BLF monitoring of ring group status
- Confirm calls (press 1 to accept — prevents voicemail pickup on cell phones)

### Omnichannel Queues (ACD) — Voice + SMS
- Multiple queues per tenant
- **Each queue handles both voice calls AND SMS conversations**
- Agent login/logout (via feature code, web, mobile, BLF)
- Agent tiers/priority levels
- Queue strategies: ring-all, longest-idle, round-robin, random, top-down, agent-with-least-calls, agent-with-fewest-calls, sequentially-by-agent-order
- Max wait time, max queue size
- Position announcements ("You are caller number 3") — voice only
- Estimated wait time announcements — voice only
- SMS auto-acknowledgment ("Thanks for contacting us, an agent will be with you shortly")
- Periodic comfort messages (configurable interval) — voice only
- Music on hold per queue — voice only
- Queue callback ("Press 1 to receive a callback") — voice only
- Overflow destination (on max wait / max size) — both voice and SMS
- Wrapup time (post-call cooldown per agent)
- Agent penalties / skills-based routing
- **Skills can include channel preference (voice-only, SMS-only, both)**
- Real-time queue statistics (web dashboard, wallboard) — combined and per-channel
- Historical queue reports (SLA, abandoned rate, avg wait, avg talk, per-agent stats) — combined and per-channel
- Queue supervisor: listen, whisper, barge, take over (voice); read, intervene, reassign (SMS)
- Agent status: available, on break, after-call work, logged out
- **Agent concurrency: configurable max simultaneous SMS conversations per agent (e.g., 5 SMS chats at once but only 1 voice call)**

### IVR / Auto Attendant
- Multi-level IVR trees
- DTMF input handling (single digit and multi-digit)
- Text-to-Speech prompts (configurable TTS engine)
- Recorded audio prompts (upload or record via phone)
- Dial-by-name directory (first name, last name, or both)
- Dial-by-extension
- Time-based routing within IVR (business hours vs. after hours)
- Invalid input handling (retry count, failover)
- Timeout handling
- Direct-to-extension on known caller (optional CID-based routing)
- Speech recognition input (future — plugin architecture)

### Time Conditions & Schedules
- Named time condition groups
- Day of week, time of day, date ranges
- Holiday calendars (per tenant, reusable)
- Manual override toggle (day/night mode with BLF key)
- Nested time conditions
- Time zone per tenant (and per condition if needed)

### Voicemail
- Per-extension voicemail box
- Shared/group voicemail boxes
- Voicemail-to-email (audio attachment + details)
- Voicemail transcription (speech-to-text, delivered in email and app)
- Visual voicemail in web client and mobile app
- Voicemail greetings: busy, unavailable, temporary, name recording
- Voicemail PIN with configurable policy
- Voicemail forwarding to another extension
- Voicemail blast groups (send one message to multiple boxes)
- MWI (Message Waiting Indicator) for desk phones
- Voicemail retention policy (auto-delete after X days, per tenant)
- Unified messaging (voicemail accessible from all clients)

### Conference Bridges
- Ad-hoc conferences (initiated from a call)
- Scheduled conference rooms (PIN-protected)
- Moderator controls: mute all, mute individual, kick, lock room
- Participant count announcements
- Join/leave notifications (tone or name announcement)
- Recording of conferences
- Web-based conference control panel
- Video conferencing (WebRTC — web and mobile clients)
- Screen sharing in web client conferences
- Max participants per room (configurable)
- Music on hold when single participant waiting

### Call Recording
- Per-extension recording policy (always, never, on-demand)
- Per-trunk recording policy
- Per-queue recording policy
- On-demand recording via feature code (start/stop mid-call)
- On-demand recording via web/mobile client button
- Recording storage in object storage (MinIO/S3) per tenant
- Recording playback in web client, mobile client, CDR view
- Recording download/export
- Recording retention policy (per tenant, configurable days)
- Automatic recording deletion after retention period
- Recording search (by date, extension, caller ID, duration)
- PCI compliance: pause/resume recording during sensitive data
- Legal hold (prevent auto-deletion of specific recordings)
- Recording transcription (speech-to-text)

### CDR / Call Detail Records
- Complete call logging (inbound, outbound, internal, missed)
- Searchable/filterable by date, extension, DID, caller ID, duration, disposition
- Call disposition tracking (answered, busy, no answer, failed, voicemail)
- Call flow visualization (who transferred to whom, hold times, etc.)
- CSV/PDF export
- Real-time CDR streaming via WebSocket (for dashboards)
- Per-tenant CDR isolation
- CDR retention policy (configurable per tenant)
- Cost calculation per call (rate decks per trunk)

### Parking (already designed — see separate spec)
- Numbered parking lots with slot ranges
- Auto-assign + announce slot
- BLF monitoring on desk phones
- Visual parking panel in web/mobile clients
- Timeout with comeback-to-origin
- Multi-lot per tenant (by department)
- DTMF controls (re-park, transfer, hangup from pickup)

### E911 (already designed — see separate spec)
- Per-extension location assignment with MSAG validation
- Dynamic location via mobile GPS
- PIDF-LO or Geolocation header injection
- Multi-carrier support (Bandwidth, Telnyx, etc.)
- Notification engine (email, SMS, push, page group, webhook)
- Kari's Law / Ray Baum's Act compliance
- Audit logging of all 911 calls

### Paging & Intercom
- Page groups (one-way broadcast to group of phones)
- Intercom (two-way, auto-answer on target phone)
- Overhead paging (SIP-based PA systems)
- Page + park announcement ("Call for John on 71")
- Multicast paging support (for large deployments — RTP multicast)
- Scheduled paging (bell schedules for schools, etc.)
- Zone paging (different physical areas)

### Fax
- T.38 fax over SIP
- Fax-to-email (incoming fax → PDF attachment to email)
- Email-to-fax (send PDF via email → outbound fax)
- Web client fax send (upload PDF, enter destination)
- Fax DID assignment per tenant/user
- Fax storage per tenant (searchable, downloadable)
- Cover page templates

### Music on Hold
- System-wide default MOH
- Per-tenant MOH classes
- Per-queue MOH
- Per-parking-lot MOH
- Upload custom audio files (MP3, WAV)
- Streaming audio source (URL-based)
- Random or sequential playback

### Feature Codes
- Configurable *-codes per tenant (with sane defaults)
- Standard codes: call forward, DND, voicemail, call pickup, intercom, parking, recording toggle, agent login/logout, day/night toggle
- Feature code enable/disable via Class of Service
- Custom feature codes (tenant admin definable, mapped to actions)

### Call Pickup
- Directed call pickup (pick up specific ringing extension)
- Group call pickup (pick up any ringing extension in your group)
- BLF-based pickup (press BLF key for ringing extension)

### Caller ID Management
- Inbound CNAM lookup (configurable provider)
- Outbound caller ID per extension
- Outbound caller ID per trunk/route
- Emergency CID override
- Caller ID spoofing prevention (restrict to tenant's owned DIDs)
- Internal caller ID (name/number for internal calls)
- Blacklist / blocklist (block by CID pattern, per tenant)
- Allowlist / whitelist

### Outbound Routing
- Route patterns (NANPA, international, emergency, toll-free, local, long distance)
- Route priority/failover (primary trunk → backup trunk)
- Time-based route selection
- CID-based route selection
- Class of Service restrictions (e.g., user can't dial international)
- PIN-required routes (for toll/international)
- Least-cost routing (multiple trunks, choose cheapest)
- Route prepend/prefix (add digits before sending to trunk)

### Inbound Routing
- DID → destination mapping (extension, ring group, queue, IVR, voicemail, external, condition)
- CID-based routing (known callers → VIP treatment)
- Time condition integration
- Fax detection (CNG tone → route to fax)
- Alert info headers (distinctive ring on desk phones)
- DID description/label for management

### SIP Trunks
- Multiple trunks per tenant
- Registration and IP-based authentication
- Codec priority configuration
- Failover/redundancy (primary + backup per trunk)
- Concurrent call limits per trunk
- Trunk monitoring (registration status, call quality)
- **SIP TLS + SRTP preferred** for trunks (but not enforceable — provider may not support it)
- If trunk connects via UDP/TCP (unencrypted): **security warning displayed on dashboards**
  - Trunk status shows amber/warning indicator: "Signaling: Unencrypted" or "Media: Unencrypted"
  - Alert generated on trunk creation if TLS/SRTP negotiation fails
  - MSP admin dashboard shows encryption status across all trunks at a glance
- Auto-negotiate: attempt TLS first, fall back to TCP/UDP if provider doesn't support it
- DTLS-SRTP for WebRTC endpoints (standard WebRTC encryption)

> **Encryption policy summary:**
> - **Extensions/clients (desk phones, web, mobile): SIP TLS + SRTP mandatory — no exceptions**
> - **SIP trunks (carrier-facing): TLS + SRTP preferred, fallback to unencrypted if provider requires it, with visible warnings**

### DISA (Direct Inward System Access)
- Dial in from external phone → authenticate → get internal dial tone
- PIN-protected
- Caller ID restriction (only allow known CIDs)
- Class of Service applied to DISA calls

### Speed Dial / BLF
- BLF keys provisioned per phone via phone provisioning system
- Presence monitoring (idle, ringing, in-call, DND)
- Speed dial + BLF combined keys
- Parking slot BLF keys
- Queue login status BLF keys
- Shared line appearance (SLA) keys

### Follow Me / Find Me
- Per-extension follow-me rules
- Ring internal first, then external numbers
- Configurable ring time per step
- Confirm calls (press 1 to accept)
- Pre-ring delay (give desk phone time to ring first)

### Call Broadcast / Auto Dialer
- Upload contact list
- Record or TTS message
- Schedule broadcast
- DTMF interaction (press 1 to connect to agent)
- Campaign reporting (delivered, answered, completed)
- Per-tenant rate limiting

### Directory
- Company directory per tenant
- Dial-by-name (first, last, or both)
- Searchable from web/mobile client
- LDAP/Entra sync for directory population
- Shared contacts across tenant
- Personal contacts per user

---

## 3. SMS & Messaging Subsystem

### SIP Trunk SMS Providers
- **ClearlyIP Trunking** — SMS API at `https://sms.clearlyip.com/api/v1/message`, auth via SIP Trunk Token
- **Twilio Programmable Messaging** — REST API, auth via Account SID + Auth Token
- Provider-agnostic abstraction layer so tenants can use either (or future providers)
- Per-tenant provider configuration (Tenant A uses ClearlyIP, Tenant B uses Twilio)
- Automatic failover between providers (if primary fails, try secondary)

### SMS/MMS Capabilities
- Send/receive SMS from any SMS-enabled DID in the tenant
- MMS support (images, PDF, media) — provider-dependent
- Long message handling (auto-segmentation for >160 char, reassembly on receive)
- Delivery receipts (sent, delivered, failed) via provider status callbacks
- Opt-out handling (STOP/START keyword compliance — 10DLC/A2P requirement)

### 10DLC Registration & Compliance Toolkit

Since Feb 2025, all A2P SMS from unregistered 10DLC numbers is blocked by US carriers.
Our platform must make this painless for every tenant — not just the registration itself,
but all the supporting materials tenants need to get approved.

#### Brand Registration (via TCR — The Campaign Registry)
- Guided wizard in MSP admin and tenant admin portals
- Collects: legal business name, EIN/Tax ID, business type, website URL, vertical/industry, company address, contact info
- Submits to TCR via provider API (ClearlyIP or Twilio — both proxy to TCR)
- Trust Score tracking (returned by TCR, determines throughput limits)
- Brand status monitoring: pending, verified, failed (with failure reasons)
- Typical approval: 1-3 business days

#### Campaign Registration
- Per-DID or per-number-group campaign registration
- Guided wizard that collects:
  - **Use case type** selection (pre-populated list from TCR):
    - Customer Care
    - Account Notifications
    - Mixed (2-5 use cases)
    - Low Volume Mixed (small/test accounts)
    - Marketing
    - Delivery Notifications
    - Security Alerts / 2FA
    - Public Service Announcement
    - And all other standard + special use cases
  - **Campaign description** — plain-English description of what messages are sent and why
  - **Sample messages** (minimum 2) — pre-filled templates the tenant can customize
  - **Message flow** — how the customer initiates contact or opts in
  - **Opt-in type** — verbal, web form, text keyword, paper form, etc.
  - **Opt-in description** — exactly how consent is collected
  - **Opt-out keywords** — STOP, CANCEL, END, QUIT, UNSUBSCRIBE (pre-filled, standard)
  - **Opt-out message** — auto-generated but customizable (e.g., "You have been unsubscribed from [Brand]. No further messages will be sent.")
  - **Help keywords** — HELP, INFO (pre-filled)
  - **Help message** — auto-generated but customizable (e.g., "For support, contact us at [phone] or [email]. Reply STOP to unsubscribe.")
  - **Message frequency** disclosure
  - **Embedded link** flag (do your messages contain links?)
  - **Embedded phone number** flag
  - **Age-gated content** flag
  - **Direct lending/loan** flag
- Campaign status monitoring: pending, approved, rejected (with rejection reasons and guidance to fix)
- Typical approval: 2-7 business days

#### Platform-Generated Compliance Documents (per tenant)
The platform auto-generates these documents from tenant info, brandable with tenant's logo/name.
Tenant admin can review, customize, and download/host them.

- **SMS Terms of Service page** (hosted or downloadable HTML)
  - Program name and brand
  - Description of message types
  - Message frequency disclosure ("Message frequency varies" or specific)
  - "Message and data rates may apply"
  - Opt-out instructions ("Reply STOP to unsubscribe")
  - Help instructions ("Reply HELP for help or contact [support info]")
  - Privacy policy link
  - Carrier disclaimer
  - CTIA-compliant disclosures

- **Privacy Policy SMS addendum** (or standalone if tenant has no existing policy)
  - What data is collected (phone number, message content, opt-in records)
  - How data is used (to send SMS communications as described)
  - How data is stored and protected
  - Data retention and deletion
  - **Explicit statement that data is NOT sold or shared with third parties for marketing** (carrier requirement — rejection if missing)
  - Contact information for privacy inquiries
  - CCPA/GDPR references as applicable

- **Sample Opt-In Form** (embeddable HTML/JS widget or downloadable template)
  - Phone number input field
  - **Separate, unchecked checkbox** for SMS consent (cannot be pre-checked, cannot be bundled with other consent)
  - Consent language: "By checking this box, you agree to receive text messages from [Brand] at the number provided. Message frequency varies. Message and data rates may apply. Reply STOP to unsubscribe. Reply HELP for help. View our [Terms] and [Privacy Policy]."
  - Links to SMS Terms and Privacy Policy
  - Submit button
  - Double opt-in flow (optional but recommended):
    1. User submits form
    2. System sends confirmation SMS: "You requested to receive messages from [Brand]. Reply YES to confirm. Msg & data rates may apply."
    3. User replies YES → subscribed
    4. User ignores or replies NO → not subscribed
  - Opt-in record stored in database (timestamp, method, IP, consent text shown) — required for compliance audits

- **Opt-In Keyword Auto-Responder** (for text-to-join)
  - Customer texts keyword (e.g., "JOIN") to tenant's DID
  - Auto-reply with consent confirmation + disclosures
  - Record opt-in

- **Sample Messages** (pre-written templates per use case, tenant customizable)
  - Customer Care: "Hi [Name], this is [Brand] support. How can we help you today? Reply STOP to opt out."
  - Account Notification: "[Brand]: Your appointment is confirmed for [date] at [time]. Reply STOP to opt out."
  - Marketing: "[Brand]: This week only — 20% off all services. Visit [link]. Reply STOP to opt out."
  - 2FA: "Your [Brand] verification code is [code]. Do not share this code."

#### Opt-Out Management (automated, tenant cannot disable)
- STOP, CANCEL, END, QUIT, UNSUBSCRIBE keywords → automatic unsubscribe
- Sends carrier-compliant opt-out confirmation
- Prevents further messages to opted-out numbers
- START, UNSTOP, YES keywords → re-subscribe
- Opt-out list per tenant per DID
- Opt-out/opt-in audit log (immutable, timestamped)
- API to check opt-out status before sending programmatic messages
- **Carrier-level opt-out honoring** — even if message is sent via API, platform blocks delivery to opted-out numbers before it hits the provider

#### Compliance Dashboard (tenant admin + MSP admin)
- Brand registration status per tenant
- Campaign registration status per DID/campaign
- Trust Score and throughput tier
- Opt-in / opt-out rates
- Complaint rate monitoring (carriers flag high-complaint campaigns)
- Warnings when approaching throughput limits
- Alerts on campaign rejection with remediation steps
- Links to hosted compliance documents (terms, privacy, opt-in form)

### Conversation Model
- **Threaded conversations** — all messages between a DID and an external number grouped into a conversation
- Conversations persist across sessions (full history searchable)
- Conversation states: open, waiting, resolved, archived
- Conversation assignment: unassigned, assigned to user, assigned to queue
- Internal notes on conversations (visible to agents, not sent to customer)
- Conversation tags/labels (per tenant, customizable)
- Conversation transfer between agents
- Conversation merge (if same customer texts different DIDs)

### SMS Routing — Who Sees What

#### Personal DID Assignment (1:1)
- DID assigned to a single extension/user
- That user's web client, mobile client, and desk phone (if capable) receive the SMS
- Only that user can see and respond to conversations on that DID
- Voicemail-style behavior — it's your number, your messages

#### Shared DID / Queue Assignment (many:many)
- DID assigned to a queue instead of a single user
- **Shared inbox** — all agents in that queue can see inbound SMS conversations on that DID
- Inbound SMS creates a new conversation (or appends to existing) in the queue
- Queue routing applies: round-robin, least-busy, skills-based, etc.
- Conversation gets assigned to an available agent
- Other agents can see the conversation but it's "owned" by the assigned agent
- Reassignment: agent can release back to queue or transfer to specific agent
- Supervisor can reassign conversations
- **Agent concurrency**: agent can handle multiple SMS conversations simultaneously (configurable max, e.g., 5)
- After-conversation wrapup time (configurable)
- Unassigned conversations show in shared queue view for any agent to claim
- SLA tracking on SMS response time (first response time, resolution time)

#### Department/Group DID Assignment
- DID assigned to a ring group or department
- All members see inbound SMS in a shared view
- No formal queue routing — first to respond claims it
- Good for small teams that don't need full ACD

### Auto-Responders & Automation
- Per-DID auto-reply (configurable message, e.g., "Thanks for texting Acme Corp")
- After-hours auto-reply (tied to time conditions)
- Keyword-based routing (text "SUPPORT" → route to support queue, "SALES" → sales queue)
- SMS-triggered IVR (future — text menu system)
- Webhook on inbound SMS (for custom integrations / bots)
- API for sending SMS programmatically (automations, appointment reminders, etc.)

### SMS in Web Client
- Conversations panel (separate from or tabbed alongside voice/chat)
- Conversation list with unread badges, timestamps, assignment status
- Real-time message delivery (WebSocket push)
- Compose with character count and segment indicator
- MMS: attach images/files
- Canned responses / templates (per tenant, pre-written replies)
- Search across all conversations (by phone number, content, date, agent, tag)
- Conversation history with full thread view
- Typing indicator (when agent is composing)
- Queue SMS dashboard: unassigned count, avg response time, conversations per agent

### SMS in Mobile Client
- Same conversation view as web client (synced in real-time)
- Push notifications for new inbound SMS (per-DID and queue notifications)
- Quick reply from notification
- Offline queue: compose while offline, send when reconnected
- Shared inbox view for queue-assigned DIDs
- Personal DID conversations in separate section

### SMS Reporting & Analytics
- Messages sent/received per DID, per agent, per tenant
- Response time metrics (first response, avg response, resolution time)
- Conversation volume by hour/day/week
- Agent SMS workload distribution
- Failed delivery reports
- Cost per message / per tenant (from provider billing)
- SMS included in unified CDR (voice + SMS activity per contact)

### SMS Data Model
```
conversations
├── id, tenant_id
├── did (our DID — the number the customer texted)
├── remote_number (customer's phone number)
├── channel (sms, mms)
├── state (open, waiting, resolved, archived)
├── assigned_to (user_id or null)
├── queue_id (if queue-routed, or null)
├── tags[], labels[]
├── first_response_at, resolved_at
├── created_at, updated_at
│
├── messages[]
│   ├── id, conversation_id
│   ├── direction (inbound, outbound)
│   ├── from, to
│   ├── body
│   ├── media_urls[] (MMS attachments)
│   ├── status (queued, sent, delivered, failed, received)
│   ├── provider (clearlyip, twilio)
│   ├── provider_message_id
│   ├── sent_by (user_id — which agent sent it)
│   ├── created_at
│   └── cost
│
└── notes[] (internal, not sent)
    ├── id, conversation_id
    ├── user_id, body
    └── created_at
```

---

## 4. DPMA Replacement — Sangoma P-Series Phone Integration

### Rust-based provisioning and control service

- **Provisioning**
  - Auto-discovery of Sangoma P-series phones on network
  - Zero-touch provisioning (phone contacts server, gets config)
  - Firmware management and updates
  - Template-based configuration per phone model (P310, P315, P320, P325, P330, P370)
  - Per-extension phone config push
  - Bulk provisioning (import CSV, auto-assign)

- **BLF / Presence**
  - Real-time presence sync (idle, ringing, in-call, DND, away)
  - BLF key configuration pushed to phones
  - Parking slot status on BLF keys
  - Queue status on BLF keys

- **Visual Voicemail**
  - Voicemail list with caller ID, timestamp, duration
  - Playback, delete, forward directly on phone screen
  - Voicemail transcription display on phone (if model supports)

- **Contacts / Directory**
  - Tenant directory pushed to phone
  - Personal contacts sync
  - Search from phone UI
  - Entra / Google contacts sync to phone

- **Call History**
  - Missed, received, placed calls on phone display
  - Synced from CDR (consistent across phone, web, mobile)

- **Phone Apps**
  - Custom XML/HTML apps on phone display
  - Status dashboards (queue stats, parking, etc.)
  - Weather, time zone clocks, custom tenant apps

---

## 5. Web Client (React/TypeScript + WebRTC)

### Softphone
- WebRTC-based calling (audio and video)
- FreeSWITCH Verto protocol or standard WebRTC/SIP.js
- Dial pad with DTMF
- Call controls: hold, transfer (blind + attended), mute, record toggle, park
- Call history (missed, placed, received)
- Visual voicemail (list, playback, delete, forward, transcription)
- Presence indicators for all tenant contacts
- Click-to-call from contact list or directory
- Multi-line support (handle multiple active/held calls)
- Incoming call popup with caller ID and CNAM

### Video & Conferencing
- 1:1 video calls
- Multi-party video conferences
- Screen sharing
- In-meeting chat
- Meeting scheduling (calendar integration)
- Join via link (external participants without account)

### Chat / Messaging
- Internal 1:1 chat between tenant users
- Group chat channels
- File sharing (images, documents)
- Chat history (searchable, persistent)
- Typing indicators, read receipts
- Notification badges
- **SMS/MMS integration (see Section 3 for full spec)**
  - Personal DID conversations (your number, your inbox)
  - Shared queue SMS inbox (see all queue conversations, claim/respond)
  - Canned responses / templates
  - Conversation state management (open/waiting/resolved)
  - Internal notes on SMS conversations
  - Unified view: internal chat + SMS in one panel with tabs

### Admin Panel (Tenant Admin)
- Dashboard: active calls, system health, quick stats
- Extension management (CRUD, bulk operations)
- Ring group, queue, IVR builders (visual/drag-and-drop for IVR)
- Time condition calendar view
- DID management
- Trunk status monitoring
- CDR viewer with filters, export, cost reports
- Recording browser with playback
- User management (invite users, assign roles, manage MFA)
- Phone provisioning (assign phones, push configs)
- E911 location manager
- Feature code configuration
- Class of Service editor
- Music on hold uploader
- Fax manager

### MSP Admin Panel (Super Admin)
- Tenant list with health/status overview
- Tenant provisioning wizard (create tenant, set quotas, assign DIDs, configure trunks)
- Cross-tenant search (CDR, recordings, extensions)
- Global system monitoring (FreeSWITCH status, call volume, resource usage)
- SIP trunk status across all tenants
- Billing/usage dashboard
- Alert/notification management (system alerts, tenant alerts)
- Audit log viewer (all admin actions across all tenants)
- Platform settings (global defaults, feature flags, maintenance mode)
- White-label / branding per tenant (logo, colors, domain)

---

## 6. Mobile Client (Flutter/Dart — iOS + Android)

### Calling
- SIP/WebRTC calling over WiFi and cellular data
- iOS CallKit integration (native incoming call screen)
- Android ConnectionService integration (native call handling)
- Push notifications for incoming calls (even when app is backgrounded/killed)
- Call controls: hold, transfer, mute, speaker, record toggle, park
- Bluetooth headset support
- Dial pad with DTMF (in-call and pre-dial)
- Contact-based calling (tap to call)

### Voicemail
- Visual voicemail list
- Playback with scrubbing
- Voicemail transcription display
- Delete, forward, callback
- Push notification on new voicemail

### Chat & Messaging
- Same chat features as web client (synced in real-time)
- Push notifications for new messages (internal chat + SMS)
- Photo/file sharing from device camera/gallery
- **SMS/MMS integration (see Section 3 for full spec)**
  - Personal DID conversations
  - Shared queue SMS inbox with claim/respond
  - Quick reply from push notification
  - Canned responses
  - Offline queue: compose while offline, send when reconnected

### Presence & Status
- Set own status (available, busy, DND, away, custom)
- View status of all tenant contacts
- Presence synced across all devices (phone, web, mobile)

### Contacts & Directory
- Tenant directory (searchable)
- Personal contacts
- Device contacts integration (match incoming calls to phone contacts)
- Favorites / frequently called

### Call History
- Unified call history (synced with CDR)
- Missed call badge / push notification

### E911
- GPS-based dynamic location reporting
- Location auto-update when on mobile network
- User override for manual location entry

### Settings
- Call forwarding rules (from mobile)
- DND toggle
- Voicemail greeting management
- Ringtone selection
- Audio device selection (speaker, earpiece, bluetooth)
- Network preference (WiFi preferred, cellular fallback)

---

## 7. Phone Provisioning System

### General (all phone brands)
- Template-based configuration
- Per-model templates (different capabilities per phone model)
- Auto-provisioning via DHCP option 66/67 or DNS SRV
- HTTP/HTTPS provisioning server
- Bulk provisioning (CSV import)
- MAC address registration and assignment
- Firmware management (per model, staged rollouts)
- Factory reset and re-provision commands

### Supported Phone Brands (initial)
- Sangoma P-series (via DPMA replacement — primary focus)
- Yealink (T-series, CP-series)
- Polycom/Poly (VVX series)
- Grandstream (GRP/GXP series)
- Fanvil
- Cisco SPA (legacy)

### Per-Phone Configuration
- Line keys / BLF keys
- Expansion module (sidecar) key layouts
- Speed dial assignments
- Ringtone per line
- Display name
- Time zone, language, date format
- Network settings (VLAN, CDP/LLDP)
- Firmware version pinning or auto-update

---

## 8. Integrations

### Microsoft Teams (Direct Routing / Operator Connect)
- SIP trunk between our platform and Teams
- Teams users can call/receive via our trunks and DIDs
- Presence sync between PBX extensions and Teams
- Shared calling plan (PBX extensions and Teams users in same dial plan)

### CRM Integration
- Click-to-call from CRM
- Incoming call screen pop (caller lookup → CRM record)
- Automatic call logging to CRM (after call, CDR writes to CRM activity)
- Supported CRMs: Salesforce, HubSpot, Zoho, ConnectWise Manage, custom via webhook
- Webhook-based integration framework for unsupported CRMs
- **Bidirectional sync**: caller ID → CRM contact lookup, CRM contact → extension mapping
- **Contact cache**: local cache of CRM contacts for instant screen pop (sync on schedule + CRM webhooks)
- **CRM field mapping**: configurable mapping between PBX call data and CRM fields (per tenant)

### ConnectWise PSA Integration (Deep)
MSP-focused ConnectWise Manage integration for automatic ticket management.

#### Automatic Ticket Creation
- **Inbound call from client** → lookup caller ID against ConnectWise company/contact records
  - Match by phone number (office, mobile, direct) on ConnectWise contact
  - Match by DID/extension mapping (tenant's DID → ConnectWise company)
  - If matched: auto-create service ticket under that company/contact
  - If unmatched: create ticket under "Unknown Caller" board or skip (configurable)
- **Ticket fields auto-populated**:
  - Company: matched ConnectWise company
  - Contact: matched ConnectWise contact
  - Summary: "Inbound call from [caller name/number] to [extension/queue name]"
  - Description: call details (time, duration, extension/queue, agent who answered)
  - Board: configurable per tenant (e.g., "Help Desk", "Support")
  - Status: configurable (e.g., "New", "In Progress")
  - Priority: configurable default, with optional AI-based priority from call content
  - Type/subtype: configurable per queue or DID
  - Source: "Phone"
- **Outbound call ticket creation**: optionally create ticket when agent places outbound call to client number
- **Voicemail ticket creation**: voicemail from client → auto-create ticket with transcription in description
- **Missed call ticket creation**: missed call from client number → create ticket flagged as "Missed Call — callback needed"

#### Ticket Update on Existing Calls
- If a ConnectWise ticket is already open for the same company/contact:
  - Option A: add time entry/note to existing ticket instead of creating new one
  - Option B: always create new ticket (configurable per tenant)
- After call: append call notes, duration, recording link, transcription, AI summary to ticket
- **Time entry**: automatically log call duration as a billable/non-billable time entry on the ticket

#### Extension ↔ ConnectWise Mapping
- **Per-tenant mapping table**:
  - Extension/DID → ConnectWise company ID (so calls TO this extension/DID are attributed to the right client)
  - Used for: inbound DID routing ("calls to 555-1234 belong to Acme Corp in CW")
  - Used for: outbound caller ID matching ("agent dialed Acme's number → create ticket under Acme")
- **Bulk import**: import ConnectWise company list → auto-suggest DID/extension mappings
- **Auto-discovery**: match existing tenant DIDs against ConnectWise company phone fields

#### ConnectWise Screen Pop
- Inbound call → instant screen pop showing:
  - ConnectWise company name, contact name
  - Open tickets for that company (count + most recent)
  - Configuration items (managed devices) for that company
  - Last ticket summary
- Click-through to ConnectWise ticket from call history / CDR
- Click-to-call from ConnectWise (via browser extension or ConnectWise plugin)

#### ConnectWise API Integration
- **REST API**: ConnectWise Manage REST API v2021.1+
- **Authentication**: API member credentials (public/private key pair) per tenant
  - Stored in platform secrets, never exposed in UI
- **API operations used**:
  - `GET /company/companies` — company lookup by phone
  - `GET /company/contacts` — contact lookup by phone
  - `POST /service/tickets` — create ticket
  - `PATCH /service/tickets/{id}` — update ticket
  - `POST /service/tickets/{id}/notes` — add note
  - `POST /time/entries` — add time entry
  - `GET /service/tickets` — query open tickets for company
  - `GET /company/configurations` — get config items for screen pop
- **Rate limiting**: respect ConnectWise API rate limits, queue requests if throttled
- **Webhook support**: ConnectWise callback URLs for ticket status changes (if configured)
- **Error handling**: log API failures, retry with backoff, alert if CW integration is down

#### Configuration (Per Tenant)
- Enable/disable ConnectWise integration
- ConnectWise instance URL (e.g., `https://na.myconnectwise.net`)
- API credentials (company ID, public key, private key)
- Default board, status, priority, type for auto-created tickets
- Ticket creation rules:
  - Create on: inbound calls, outbound calls, voicemail, missed calls (toggle each)
  - Minimum call duration to create ticket (e.g., skip calls under 10 seconds)
  - Skip ticket creation for internal calls
- Time entry settings: billable vs. non-billable, work type, work role
- Test connection button (validate API credentials and permissions)

### Calendar Integration
- Google Calendar and Microsoft 365 Calendar
- Presence sync (in meeting → auto-DND or auto-forward)
- Conference scheduling with dial-in details auto-added to invite

### Webhook / Event System
- Configurable webhooks per tenant
- Events: call started, call answered, call ended, voicemail received, fax received, queue events, recording available, 911 dialed
- Retry logic with exponential backoff
- Webhook delivery logs (success/failure)
- Webhook signature verification (HMAC)

### REST API — First-Class, Fully Documented
**Every feature in this platform is API-first.** The web and mobile clients consume the same
public API that third-party integrations use. Nothing is UI-only.

- **OpenAPI 3.1 / Swagger UI** — auto-generated from code, always up to date
  - Interactive Swagger UI at `/api/docs` (try-it-out enabled)
  - ReDoc at `/api/redoc` (clean reading format)
  - Downloadable OpenAPI spec (JSON + YAML) for code generation
- **Every resource is a REST endpoint**, including:
  - Tenants, users, extensions, DIDs, trunks
  - Ring groups, queues, IVRs, time conditions
  - Call recordings, CDR, voicemail
  - SMS conversations, messages, opt-in/opt-out status
  - 10DLC brand registration, campaign registration, compliance documents
  - Phone provisioning, firmware, templates
  - E911 locations
  - Parking lots, feature codes, MOH
  - Reports, analytics, billing/usage
  - Audit logs, alerts, webhooks
- Tenant-scoped API keys (API key inherits tenant + role permissions)
- MSP-scoped API keys (cross-tenant access for automation)
- Rate limiting per API key (configurable per tier)
- Pagination, filtering, sorting on all list endpoints
- Consistent error responses (RFC 7807 Problem Details)
- Versioned API (URL prefix `/api/v1/`, `/api/v2/` when breaking changes needed)
- WebSocket API for real-time events (calls, presence, queue stats, SMS, parking)
- SDK generation: OpenAPI spec enables auto-generated client libraries (Python, JS/TS, Go, etc.)
- **API changelog** — documented breaking/non-breaking changes per version

### LDAP / Active Directory Sync
- Import users from LDAP/AD/Entra
- Sync on schedule or on-demand
- Map AD groups to PBX roles
- Map AD attributes to extension properties

---

## 9. Dashboards, Reports & Analytics

### Dashboard: MSP Overview (Super Admin)
The single pane of glass across all tenants.
- **Tenant health grid**: all tenants at a glance, color-coded (green/yellow/red)
  - Per-tenant: active calls, registered phones, trunk status, encryption status, alerts
- **Platform vitals**: total active calls, total registered endpoints, FreeSWITCH CPU/memory/uptime
- **Trunk status map**: all SIP trunks across all tenants
  - Registered/unregistered, active call count, encryption status (green = TLS+SRTP, amber = unencrypted)
  - **Unencrypted trunk warning**: prominently displayed if any trunk is not using TLS/SRTP
- **Alert feed**: real-time scrolling alert log (trunk down, quality degraded, 911 called, etc.)
- **Call volume sparklines**: per-tenant call volume trend (last 24h)
- **Top tenants**: by call volume, by concurrent calls, by storage usage
- **System alerts**: disk space, CPU, memory, certificate expiry, FreeSWITCH health

### Dashboard: Infrastructure & Capacity (MSP Admin)
Dedicated to ensuring the Docker host and platform can handle voice load.

#### Docker Host Resources
- **CPU**: real-time utilization (%), per-core breakdown, load average (1/5/15 min)
  - Alert thresholds: warning at 70%, critical at 85%
  - Historical trend graph (24h, 7d, 30d)
- **Memory**: total, used, free, cached, swap usage
  - Per-container memory breakdown (which container is consuming most)
  - Alert on memory pressure (system swap usage, OOM risk)
- **Disk I/O**: read/write IOPS, throughput (MB/s), disk latency
  - Recording storage disk utilization (critical for voice workloads)
  - Alert on high I/O wait (affects call quality)
- **Network I/O**: bandwidth utilization in/out, packets/sec, errors/drops
  - SIP signaling traffic vs. RTP media traffic breakdown
  - Alert on dropped packets or interface errors
- **Disk Space**: per-volume utilization, growth rate, projected days until full
  - Separate tracking: recordings volume, database volume, logs volume, OS volume
  - Alert on >80% utilization with growth projection

#### Container Health
- **Per-container status panel**:
  - FreeSWITCH, FastAPI, PostgreSQL, Redis, MinIO, SIP Proxy, Event Router, each Rust service
  - Status: running/stopped/restarting, uptime, restart count
  - CPU and memory per container (cgroup metrics)
  - Container logs tail (last N lines, searchable)
- **Container restart alerts**: any container restarting unexpectedly
- **Health check status**: per-container health check pass/fail history

#### Voice Capacity Metrics
- **Concurrent calls vs. capacity**: current concurrent calls / estimated max capacity
  - Capacity estimation based on CPU headroom and codec (G.711 vs G.729 vs Opus)
  - Trend line showing peak concurrency over time
  - Projected max capacity based on current resource usage per call
- **FreeSWITCH internals**:
  - Active channels, active calls, sessions per second
  - ESL connection pool status
  - Codec transcoding load (transcoding is CPU-intensive)
  - Conference bridge count and participant count
- **Call quality correlation**: overlay call quality (MOS) with resource utilization
  - Identify: "quality drops when CPU exceeds X%" patterns
- **Capacity planning projection**: based on historical growth, when will current host hit capacity limits?

#### Collection Method
- **Node exporter** (Prometheus) for Docker host OS metrics
- **cAdvisor** for per-container resource metrics
- **Custom FreeSWITCH exporter** for media engine metrics (via ESL `status` and `show` commands)
- **Docker API** for container health, restart counts, log access
- Data retained: 15-second resolution for 24h, 1-minute for 7d, 5-minute for 90d, 1-hour for 1 year
- All metrics exposed via platform API for external monitoring integration (Datadog, Grafana Cloud, etc.)

### Dashboard: Tenant Overview (Tenant Admin)
- **Active calls panel**: current calls with caller/callee, duration, recording status
- **Extension status grid**: all extensions, color-coded (available/ringing/in-call/DND/offline)
- **Queue summary**: active queues with calls waiting, agents available, current SLA %
- **SMS summary**: open conversations, unassigned conversations, avg response time today
- **Trunk status**: per-trunk registration, active calls, encryption indicator
- **Phone fleet status**: online/offline count, firmware version distribution
- **Quick stats cards**: calls today, avg call duration, voicemails pending, missed calls
- **Recent alerts**: relevant alerts for this tenant

### Dashboard: Queue / Call Center (Real-Time)
Designed for supervisors and wall-mounted TVs.
- **Per-queue panels** (one or combined view):
  - Calls in queue, longest wait, agents available/busy/on-break
  - SLA % (real-time, rolling window configurable)
  - Calls answered / abandoned / overflow today
  - Avg wait time, avg handle time (today, rolling)
- **Agent roster**: each agent's status (available, in-call, wrapup, break, logged out)
  - Current call duration, calls handled today, avg handle time
  - SMS conversations active (if omnichannel queue)
- **Threshold color coding**: configurable thresholds per metric
  - e.g., wait time >30s = yellow, >60s = red
  - e.g., SLA <90% = yellow, <80% = red
- **Full-screen wallboard mode** (hides navigation, auto-refreshes)
- **Customizable widget layout** (drag-and-drop arrangement)
- **Multi-queue combined view** (all queues side by side)

### Dashboard: SMS / Messaging
- Open conversations count (unassigned, assigned, waiting)
- Avg first response time (today, this week)
- Conversations resolved today
- Agent workload: conversations per agent, avg response time per agent
- Opt-out rate trend
- Message volume chart (inbound vs outbound, by hour)
- Failed delivery count with details
- 10DLC compliance status (brand/campaign registration, trust score)

### Dashboard: Network Quality
- **Call quality summary**: avg MOS (today, trend), calls with MOS < 3.5
- **Trunk quality**: per-trunk MOS trend, jitter, packet loss
- **Worst calls list**: lowest MOS calls today (click to see details)
- **Quality heatmap**: by time of day (when do problems happen?)
- **Phone quality**: per-phone avg MOS (identify problem phones/locations)
- **Encryption status overview**: all endpoints and trunks, encrypted vs not

### Dashboard: Security (MSP Admin)
- Failed login attempts (trend, by IP, by user)
- Active sessions count, by auth method (Entra/Google/password)
- SIP registration failures (trend, by IP, GeoIP map)
- Anomalous call patterns (toll fraud indicators)
- Unencrypted trunk warnings
- Security scan results summary (last SAST/DAST/SCA run)
- Certificate expiry countdown
- Audit log activity summary

### Dashboard: Phone Fleet (MSP Admin)
- Total phones by model, by firmware version, by tenant
- Online/offline breakdown (with offline duration)
- Phones needing firmware update
- Registration flap alerts
- Per-tenant phone health summary

---

### Reports (Scheduled + On-Demand)

All reports support:
- **On-demand generation** from web UI (click to generate, view in browser)
- **Scheduled email delivery** (daily, weekly, monthly — configurable per report)
  - Email to: specific users, distribution lists, or custom email addresses
  - Delivery time: configurable (e.g., "every Monday at 7am")
  - Format: PDF attachment + inline summary in email body
- **Export formats**: PDF, CSV, Excel (XLSX)
- **Date range selection**: today, yesterday, this week, last week, this month, last month, custom range
- **Tenant scoping**: MSP admin can run reports per tenant, across selected tenants, or globally
- **Saved report configurations** (save a report with specific filters, schedule it, give it a name)
- **Report templates** (per tenant, per MSP — pre-configured report definitions)

#### Call Reports
- **Call Summary Report**: total calls by direction (inbound/outbound/internal), disposition, duration
- **Call Detail Report**: full CDR listing with all fields, filterable, sortable
- **Extension Activity Report**: per-extension call count, avg duration, missed calls, voicemail
- **DID Usage Report**: per-DID inbound call count, top callers, peak hours
- **Trunk Utilization Report**: per-trunk call count, concurrent call peak, minutes used, cost
- **Hourly/Daily Call Volume Report**: call count by hour or day, charted
- **Missed Call Report**: missed/unanswered calls with caller ID, time, target extension
- **Call Cost Report**: cost per call, per trunk, per route, per tenant (from rate decks)
- **Call Duration Distribution**: histogram of call lengths (how many <1min, 1-5min, 5-15min, etc.)
- **Top Callers / Top Called Numbers**: ranked by frequency or duration
- **Geographic Call Distribution**: calls by area code, state, country (with map visualization)
- **Outbound Dialing Report**: outbound calls by extension, destination, cost

#### Queue / Call Center Reports
- **Queue Performance Report**: per-queue SLA %, avg wait, avg handle time, abandon rate, overflow count
- **Queue Summary by Date**: day-by-day queue metrics for trend analysis
- **Agent Performance Report**: per-agent calls handled, avg talk time, avg wrapup time, login hours, AUX time
- **Agent Availability Report**: per-agent login/logout times, total available time, break time
- **Abandoned Call Report**: calls that abandoned queue, wait time before abandoning, caller ID
- **SLA Report**: percentage of calls answered within target (configurable: 20s, 30s, 60s, etc.)
- **Queue Callback Report**: callbacks requested, callbacks completed, avg wait for callback
- **Agent Comparison Report**: side-by-side agent metrics for performance reviews
- **Queue Hourly Distribution**: calls entering queue by hour (staffing optimization)

#### SMS / Messaging Reports
- **Conversation Volume Report**: conversations opened/resolved by day, by DID, by queue
- **Agent SMS Performance**: messages sent, avg response time, conversations resolved per agent
- **Response Time Report**: first response time distribution, SLA compliance
- **SMS Cost Report**: messages sent/received, cost per message, per tenant
- **Opt-In / Opt-Out Report**: opt-in and opt-out events by date, by DID, net subscriber trend
- **Failed Delivery Report**: failed SMS deliveries with error codes, by provider
- **10DLC Compliance Report**: brand/campaign status, throughput usage vs limits, complaint rate

#### System / Infrastructure Reports
- **Trunk Health Report**: per-trunk uptime, registration status history, encryption status, quality metrics
- **Phone Fleet Report**: phones by model, firmware, online/offline status, per tenant
- **Platform Resource Report**: CPU, memory, disk usage trends, FreeSWITCH channel count
- **Registration Report**: endpoint registrations/deregistrations over time
- **Recording Storage Report**: storage used per tenant, growth trend, projected costs

#### Security Reports
- **Audit Log Report**: admin actions by user, by date, by type (configurable filters)
- **Auth Activity Report**: logins, failed logins, MFA challenges, lockouts, by user and IP
- **SIP Security Report**: registration failures, blocked IPs, GeoIP violations
- **Vulnerability Scan Report**: latest SAST/DAST/SCA results, open findings, remediation status
- **Encryption Compliance Report**: endpoints and trunks by encryption status, TLS version distribution
- **Call Recording Compliance Report**: recordings with legal hold, recordings accessed/exported, chain-of-custody events

#### Billing / Usage Reports
- **Tenant Usage Summary**: per-tenant extension count, DID count, concurrent call peak, minutes, storage, SMS count
- **Billing Report**: per-tenant charges calculated from rate decks + usage
- **Usage Trend Report**: month-over-month usage growth per tenant
- **Overage Report**: tenants approaching or exceeding plan limits
- **Revenue Report**: total billing across all tenants (MSP admin)

#### Quality Reports
- **Call Quality Report**: avg MOS, calls below threshold, worst calls, by tenant/trunk/extension
- **Quality Trend Report**: MOS/jitter/packet loss trends over time
- **Agent Quality Scorecard**: agent call scoring averages, trends, category breakdowns (if quality management module used)
- **Sentiment Report**: call sentiment distribution (positive/neutral/negative), trends, per queue, per agent

### Alerting
- Trunk down alerts (email, SMS, push, webhook)
- **Trunk encryption warning** (trunk connected without TLS/SRTP)
- High call failure rate alerts
- Resource threshold alerts (CPU, memory, disk)
- Registration failure alerts
- 911 call alerts (already covered in E911 spec)
- Call quality degradation alerts (MOS below threshold)
- Queue SLA breach alerts (SLA drops below target)
- SMS delivery failure spike alerts
- Toll fraud detection alerts (unusual outbound patterns)
- Certificate expiry alerts (30 day, 7 day, 1 day warnings)
- Phone offline alerts (phone unregistered for >X minutes)
- **Configurable alert rules** per tenant and globally
  - Threshold, duration, severity
  - Notification channels: email, SMS, push notification, webhook
  - Escalation rules (if not acknowledged in X minutes, escalate to next contact)
  - Alert suppression / maintenance windows (suppress during planned maintenance)
- **Alert history**: searchable log of all alerts with resolution status

---

## 10. Billing & Usage Metering

### Usage Tracking
- Per-tenant concurrent call tracking
- Per-tenant extension count
- Per-tenant recording storage (GB)
- Per-tenant minutes (inbound, outbound, toll-free, international)
- Per-tenant DID count
- Per-tenant SMS/MMS count

### Rate Decks
- Configurable rate decks per trunk / per route
- Domestic, international, toll-free, premium rate categories
- Per-tenant markup / pricing tiers

### Billing Integration
- Usage export for external billing (CSV, API)
- Pax8 billing integration (if applicable)
- ConnectWise Manage billing integration
- Stripe/payment gateway integration (for direct-to-customer billing)
- Invoice generation (per tenant, per billing period)
- Usage alerts (approaching limits, overage warnings)

### Tenant Plans / Quotas
- Plan tiers (e.g., Basic: 10 ext, Standard: 50 ext, Enterprise: unlimited)
- Max concurrent calls per tenant
- Max extensions per tenant
- Max recording storage per tenant
- Max DIDs per tenant
- Feature gating by plan (e.g., call center only on Standard+)

---

## 11. Security, Compliance & Security Auditing

### Network Security
- **SIP over TLS for all client/extension signaling (mandatory — no UDP/TCP SIP from endpoints)**
- **SRTP for all client/extension media (mandatory — no unencrypted RTP from endpoints)**
- SIP TLS + SRTP preferred for SIP trunks (carrier-facing), fallback allowed with dashboard warnings
- DTLS-SRTP for all WebRTC sessions (inherent to WebRTC)
- TLS 1.2+ minimum, TLS 1.3 preferred
- Certificate management for SIP TLS (auto-renewal via ACME/Let's Encrypt)
- Firewall integration (fail2ban equivalent — auto-block on auth failures)
- Rate limiting on SIP registration attempts
- IP allowlisting per trunk
- GeoIP blocking (block registrations from unexpected countries)
- SIP intrusion detection
- SBC (Session Border Controller) functionality in Rust SIP proxy
  - Topology hiding (mask internal network from external SIP)
  - SIP message normalization
  - SIP header manipulation rules
  - DoS/DDoS mitigation at SIP layer

### Data Security
- Encryption at rest for recordings and voicemail (AES-256)
- Encryption at rest for database (PostgreSQL TDE or volume encryption)
- Tenant data isolation (PostgreSQL RLS — row-level security)
- Secure API (HTTPS only, JWT auth, rate limiting)
- Secrets management (no plaintext credentials in config — HashiCorp Vault or equivalent)
- Certificate management (auto-renewal via Let's Encrypt / ACME)

### Compliance
- HIPAA-capable (encryption, audit logs, access controls, BAA support)
- PCI-DSS support (pause/resume recording for credit card data)
- GDPR support (data export, data deletion per tenant, right to be forgotten)
- SOC 2 audit trail support
- Call recording consent: announcement playback configurable per trunk/route
- 10DLC / A2P SMS compliance (see Section 3)
- STIR/SHAKEN caller ID authentication (robocall prevention compliance)

### Compliance Recording & Legal Hold
- Tamper-evident recording storage (SHA-256 hash chain per recording)
- Legal hold per conversation, per extension, per date range, per tenant
- Legal hold overrides normal retention auto-deletion
- Export with chain-of-custody metadata for legal discovery
  - Recording hash, timestamps, who accessed, storage location
- Chain-of-custody audit trail (who accessed/downloaded/exported a recording and when)
- Retention policies that can be overridden only by MSP admin or legal hold

### Audit Logging
- All admin actions logged (who, what, when, from where, what changed)
- All auth events logged (login, logout, MFA challenge, failed attempts, password changes)
- All API calls logged (endpoint, method, user, tenant, request/response summary)
- CDR as audit trail for all calls
- SMS conversation audit trail
- Config change audit trail (before/after diff for every config change)
- Log retention policy (configurable, default 1 year, legal hold override)
- Log export (SIEM integration — syslog, webhook, S3)
- Immutable audit log storage (append-only, cannot be deleted by any user including MSP admin)

### Security Auditing & Vulnerability Management

#### Automated Security Scanning (CI/CD integrated)
- **SAST (Static Application Security Testing)**
  - Python: Bandit, Semgrep
  - Rust: cargo-audit, clippy security lints
  - TypeScript/React: ESLint security plugin, Semgrep
  - Flutter/Dart: dart analyze, custom security rules
  - Runs on every PR — blocks merge on critical findings
- **DAST (Dynamic Application Security Testing)**
  - OWASP ZAP automated scans against running API
  - Scheduled scans (weekly) against staging environment
  - Authenticated scanning (tests with valid JWT tokens for each role)
- **SCA (Software Composition Analysis)**
  - Dependency vulnerability scanning (Dependabot, Snyk, or Trivy)
  - Python: pip-audit / safety
  - Rust: cargo-audit
  - Node/TS: npm audit
  - Flutter: pub audit
  - License compliance scanning (flag copyleft in commercial components)
  - Automated PR creation for dependency updates
- **Container Security**
  - Docker image scanning (Trivy, Grype)
  - Base image vulnerability monitoring
  - No-root container enforcement
  - Read-only filesystem where possible
  - Secret scanning in images (no embedded credentials)
- **IaC Security**
  - Docker Compose / Kubernetes manifest scanning
  - Configuration drift detection

#### Penetration Testing
- Annual third-party penetration test (external firm)
- Scope: API, web client, mobile client, SIP/RTP layer, auth flows
- SIP-specific testing:
  - SIP fuzzing (malformed packets)
  - Registration hijacking attempts
  - Call interception testing
  - SRTP downgrade attacks (must reject all unencrypted media)
  - TLS downgrade attacks (must reject UDP/TCP SIP, enforce TLS 1.2+)
  - Certificate validation testing
  - Ooh enumerate extension scanning
  - Ooh toll fraud testing (unauthorized outbound calls)
- Findings tracked in issue tracker with severity and remediation deadline
- Re-test after remediation

#### Security Monitoring (runtime)
- Failed auth attempt alerting (brute force detection)
- Anomalous API usage patterns (rate spike, unusual endpoints)
- Anomalous call patterns (toll fraud indicators: sudden spike in international calls, calls to premium rate numbers)
- SIP registration from unexpected geographic locations
- Privilege escalation detection (user accessing cross-tenant resources)
- Real-time security event dashboard in MSP admin panel
- Integration with SIEM (Splunk, ELK, Datadog, etc.) via syslog/webhook

#### Security Response
- Incident response playbook (documented procedures)
- Automated account lockout on detected brute force
- Automated trunk disable on suspected toll fraud
- Security incident notification (email + SMS to MSP admins)
- Post-incident review template and process

---

## 12. High Availability & Disaster Recovery

### Platform HA
- FreeSWITCH clustering (multiple instances behind SIP proxy)
- Database replication (PostgreSQL streaming replication or Patroni)
- Redis sentinel / cluster for cache HA
- API layer horizontal scaling (multiple FastAPI instances behind load balancer)
- Stateless API design (any instance can handle any request)

### Backup & Restore
- Automated daily backups (database, configs, recordings)
- Per-tenant backup and restore
- Point-in-time recovery (PostgreSQL WAL archiving)
- Backup to S3/MinIO with encryption
- Restore wizard in MSP admin panel
- Disaster recovery runbook (documented)

### Failover
- SIP trunk failover (primary → backup, automatic)
- Geographic redundancy (multi-site deployment option)
- DNS-based failover for SIP endpoints
- Automatic re-registration of phones on failover

---

## 13. White-Label & Branding

- Per-tenant branding (logo, colors, favicon)
- Custom domain per tenant for web portal (tenant.example.com)
- Branded mobile app (build variants with tenant branding — future)
- Branded email templates (voicemail notifications, fax, alerts)
- MSP branding on the platform itself (your company, not ours)
- Removable "Powered by" attribution

---

## 14. DID Ordering & Number Porting

### In-Platform Number Ordering
- Search available numbers by area code, city, state, prefix, toll-free
- Order numbers directly from ClearlyIP or Twilio via their APIs
- Instant provisioning — ordered DID is immediately available in tenant's pool
- Number type support: local, toll-free, vanity
- SMS-enabled flag (order voice-only or voice+SMS)
- Bulk ordering (order 10, 50, 100 numbers at once)
- Number reservation (hold a number before assigning to tenant)
- MSP admin: order and assign to any tenant
- Tenant admin: order within their quota (if allowed by plan)
- Cost visibility (per-number pricing shown before ordering)

### Number Porting
- Port-in request wizard:
  - Upload LOA (Letter of Authorization) — template provided
  - Enter current carrier info, account number, PIN
  - Select numbers to port
  - Requested port date
  - CSR (Customer Service Record) upload if available
- Port status tracking (submitted, FOC received, scheduled, completed, rejected)
- Port rejection handling (reason displayed, guidance to fix and resubmit)
- Automated notification on port status changes
- Port-out support (when a tenant leaves — provide required info to receiving carrier)
- Emergency routing during port transition (temporary forwarding)
- Bulk porting (port entire blocks of DIDs)

### Number Lifecycle Management
- DID inventory per tenant (assigned, unassigned, porting, reserved)
- Number release/cancellation
- Number reassignment between tenants (MSP admin)
- Regulatory compliance per number (E911 registration required before activation)
- Number aging / quarantine (released numbers held for 30 days before recycling)

---

## 15. Migration & Import Tools

### Source System Importers
- **FreePBX / PBXact**
  - Export: MySQL database dump + config file parsing
  - Import: extensions, ring groups, queues, IVRs, time conditions, feature codes
  - Voicemail greetings and messages (audio files)
  - Call recordings
  - CDR history
  - DID/inbound route mappings
  - Outbound route patterns
  - Phone MAC registrations (EPM data)
- **FusionPBX**
  - Export: PostgreSQL dump + XML config parsing
  - Same entity types as above
- **3CX**
  - Export: backup file parsing
  - Extensions, ring groups, queues, IVRs, DIDs
- **Generic CSV/JSON import**
  - Template files for each entity type (extensions, ring groups, etc.)
  - Bulk import with validation and error reporting
  - Preview/dry-run before committing

### Migration Wizard
- Step-by-step guided migration in MSP admin panel
- Source system selection → connection/upload → entity mapping → preview → import
- Conflict resolution (what if extension 100 already exists?)
- Rollback capability (undo an import within 24 hours)
- Migration report (what was imported, what was skipped, what failed, warnings)

### Data Export (tenant portability)
- Full tenant data export (JSON/CSV):
  - Configuration (extensions, groups, queues, IVRs, routes, etc.)
  - CDR history
  - Call recordings (bulk download or S3 transfer)
  - Voicemail messages and greetings
  - SMS conversation history
  - Contacts/directory
- GDPR Article 20 compliance (right to data portability)
- Scheduled exports (daily/weekly backup to tenant's own S3 bucket)

---

## 16. Receptionist / Operator Console

### Dedicated Switchboard View (web client module)
- Dense, information-rich layout optimized for front-desk operators
- **Live call panel**: all active calls in the tenant (caller, callee, duration, status)
- **Drag-and-drop call handling**:
  - Drag a call to an extension → transfer
  - Drag a call to a parking slot → park
  - Drag a call to a queue → send to queue
  - Drag between calls → conference/bridge
- **Extension status grid**: all extensions at a glance
  - Color-coded: available (green), ringing (yellow), in-call (red), DND (gray), offline (dark)
  - Click to call, right-click for actions (transfer to, page, voicemail)
- **Directory search**: instant search by name, extension, department
- **Parking lot panel**: visual parking slots with caller ID and wait time
- **Queue summary**: active calls in queue, agents available, wait times
- **Speed dial panel**: configurable favorites/frequently contacted
- **Incoming call popup**: caller ID, CNAM, CRM lookup, click to answer/reject/send to VM
- **Call notes**: quick note entry during/after call (stored in CDR)
- **Multi-tenant**: MSP receptionist can switch between tenants

---

## 17. AI / LLM Features

### Transcription Engine
- Real-time call transcription (live, streamed to web/mobile client)
- Post-call transcription (batch, for recordings)
- Engine options: OpenAI Whisper (self-hosted), Deepgram, AssemblyAI
- Configurable per tenant (choose engine, language, accuracy vs. speed)
- Speaker diarization (label who said what)
- Transcript stored alongside recording in CDR
- Searchable transcripts (find calls where "refund" was mentioned)

### Call Summarization
- AI-generated call summary after each call (1-3 sentences)
- Key points extraction (decisions made, action items, follow-ups)
- Summary pushed to:
  - CDR record
  - CRM integration (auto-logged as activity note)
  - Agent's call history in web/mobile client
  - Email to agent (optional)
- Customizable summary prompt per tenant/queue (e.g., "focus on technical issues mentioned")

### AI Auto-Attendant
- Voice bot that handles first-contact routing by intent, not DTMF
- Caller speaks naturally: "I need to talk to someone about my bill"
- AI routes to correct queue/extension based on intent classification
- Fallback to traditional IVR if AI confidence is low
- Customizable intents per tenant (map intent → destination)
- Conversation context passed to agent when transferred (AI heard: "billing dispute about February charge")
- Multi-language support

### SMS AI Assist
- **Suggested replies**: agent sees AI-drafted response options based on conversation context
- Agent can accept, edit, or reject suggestions
- **Auto-categorization**: AI tags SMS conversations by topic
- **Sentiment indicator**: conversation sentiment shown to agent (positive/neutral/negative)
- AI suggestions are tenant-configurable (enable/disable, tone settings)

### Voicemail Intelligence
- Beyond transcription: 1-line AI summary ("Client wants to reschedule Thursday meeting to Friday")
- Urgency detection (AI flags voicemails that sound urgent)
- Callback priority suggestions
- Summary delivered via email, push notification, visual voicemail view

### Call Sentiment Analysis
- Real-time sentiment score during live calls (positive/neutral/negative)
- Sentiment visible to queue supervisor dashboard
- Sentiment-triggered escalation rules ("if sentiment drops to negative for >30 seconds, alert supervisor")
- Historical sentiment trends per agent, per queue, per tenant
- Sentiment as a dimension in call center reports

### AI Cost Management
- Per-tenant AI feature enable/disable (transcription, summarization, sentiment are independent toggles)
- AI usage metering (transcription minutes, summarization calls, etc.)
- Cost tracking per tenant (AI API costs passed through or included in plan)
- Quality vs. cost tier selection (Whisper large vs. small, etc.)

---

## 18. Desk Phone Remote Management

### Phone Fleet Dashboard
- All provisioned phones across all tenants in one view
- Per-phone status: online/offline, registered/unregistered
- Firmware version, model, MAC address, IP address
- Uptime, last registration time
- Network info (VLAN, LLDP/CDP neighbor)
- Filter/search by tenant, model, firmware, status, location

### Remote Operations
- **Remote reboot** (single phone or bulk by tenant/model/location)
- **Remote factory reset** (with confirmation — destructive)
- **Remote config push** (push updated config without reboot where supported)
- **Firmware push** with staged rollouts:
  - Select target firmware version
  - Roll out to X% of phones, wait, monitor for issues, continue
  - Auto-rollback if phones fail to re-register after firmware update
- **Remote screenshot / screen capture** (models that support it)
- **Remote syslog collection** (pull phone logs for troubleshooting)
- **Remote packet capture** (phone-side, models that support it)

### Phone Health Monitoring
- Registration flap detection (phone keeps registering/unregistering)
- Audio quality metrics from phone (if reported via SIP headers)
- Phone reboot detection (unexpected reboots logged)
- Alert on phone offline for >X minutes
- Bulk phone health report per tenant

---

## 19. Network Quality & QoS Tools

### Per-Call Quality Metrics (in CDR)
- MOS (Mean Opinion Score) — calculated from RTP stats
- Jitter (ms)
- Packet loss (%)
- Round-trip time / latency (ms)
- Codec used
- SRTP status verification (all calls must be encrypted — alert on any failure)
- Quality score color-coding in CDR (green/yellow/red)
- Click on any call → see quality timeline graph

### Quality Dashboards
- Tenant quality overview (avg MOS, worst calls, trends)
- Per-trunk quality (is a specific carrier degraded?)
- Per-phone quality (is a specific phone/location having issues?)
- Quality trends over time (hourly, daily, weekly)
- Quality heatmap by time of day (when do problems occur?)

### Quality-Based Routing
- If primary trunk MOS drops below threshold → auto-failover to backup trunk
- If a specific codec path is degraded → switch codecs
- Configurable thresholds per tenant

### Network Assessment Tools
- **Echo test extension** (dial *43 → hear your own audio with latency measurement)
- **Network quality test** (built-in tool for new tenant onboarding):
  - Jitter test
  - Packet loss test
  - Bandwidth test
  - Latency test
  - Report: "this network can support X concurrent calls"
- **SIP OPTIONS monitoring** on all registered endpoints (heartbeat, measure RTT)
- **Traceroute / SIP path analysis** from platform to endpoint

---

## 20. Developer Portal & Webhook Tools

### Tenant-Facing Developer Portal
- Self-service API key management (tenant admin creates/revokes keys)
- Scoped API keys (read-only, read-write, specific resources only)
- API key usage stats (calls per day, rate limit status)
- Interactive API sandbox (test against staging tenant, not production)
- Code examples per language: Python, Node.js/TypeScript, Go, PHP, cURL
- SDKs: auto-generated from OpenAPI spec (Python, JS/TS, Go)
- Quickstart guides ("send your first SMS in 5 minutes")

### Webhook Management & Debugging
- Create/edit/delete webhook subscriptions per tenant
- Event catalog with example payloads for every event type
- **Webhook debugger** (live view, like Stripe's):
  - See every delivery attempt in real-time
  - Request payload, response code, response body, latency
  - Success/failure indicators
  - Retry status (next retry time, attempt count)
  - Replay button (re-send a specific webhook delivery)
- Webhook signature verification documentation (HMAC-SHA256)
- Test mode: send test events to webhook endpoint on demand
- Webhook delivery logs (searchable, filterable, 30-day retention)

### Event System
- Event types organized by category:
  - **Call events**: call.started, call.answered, call.ended, call.missed, call.transferred, call.parked, call.recording.started, call.recording.completed
  - **SMS events**: sms.received, sms.sent, sms.delivered, sms.failed, conversation.created, conversation.assigned, conversation.resolved
  - **Queue events**: queue.call.joined, queue.call.answered, queue.call.abandoned, queue.agent.login, queue.agent.logout, queue.sla.breached
  - **Voicemail events**: voicemail.received, voicemail.transcribed
  - **Fax events**: fax.received, fax.sent
  - **Presence events**: presence.changed
  - **Admin events**: extension.created, extension.updated, tenant.created, user.login
  - **Emergency events**: e911.called
  - **System events**: trunk.down, trunk.up, quality.degraded
- WebSocket subscription for real-time events (alternative to webhooks for connected clients)
- Event filtering (subscribe to specific event types only)

---

## 21. Multi-Channel Expansion (Omnichannel)

### Architecture: Channel-Agnostic Conversation Model
The SMS conversation model (Section 3) is designed to be channel-agnostic.
Each conversation has a `channel` field. Adding new channels means:
1. Build a provider adapter (API integration)
2. Handle inbound webhooks from the provider
3. Map to the existing conversation model
4. Existing queue routing, agent assignment, and UI all work automatically

### Planned Channels (beyond voice + SMS)

#### Web Chat Widget
- Embeddable JavaScript widget for tenant's website
- Customer initiates chat → creates conversation in queue
- Real-time messaging via WebSocket
- Pre-chat form (name, email, question topic)
- Chat transcript emailed to customer after resolution
- Offline mode (leave a message → creates SMS or email follow-up)
- Brandable per tenant (colors, logo, greeting text)
- Typing indicators, read receipts
- File/image sharing
- Chat rating (post-conversation satisfaction survey)

#### WhatsApp Business (future)
- WhatsApp Business API integration
- Inbound customer messages → queue conversation
- Template messages (WhatsApp-approved outbound)
- Media support (images, documents, audio)
- Provider: Twilio WhatsApp or Meta Business API directly

#### Facebook Messenger (future)
- Facebook Page integration
- Inbound messages → queue conversation
- Quick replies, buttons, structured messages

#### Email-to-Queue (future)
- Inbound email to designated address → creates conversation in queue
- Agent replies from web client → sent as email
- Thread tracking (email subject-based threading)
- Attachment support
- HTML email rendering in agent view

### Unified Agent Experience
- All channels appear in the same conversation panel
- Agent doesn't need to switch tools — SMS, web chat, WhatsApp all in one inbox
- Conversation can be escalated cross-channel (chat → voice call, SMS → voice call)
- Customer history spans all channels (see that this phone number also chatted last week)
- Per-agent channel skills (agent A handles voice+SMS, agent B handles voice+chat+WhatsApp)

---

## 22. Tenant Lifecycle Management

### Onboarding Wizard (MSP Admin)
Step-by-step guided tenant creation:
1. **Company info**: name, domain, industry, address, primary contact
2. **Plan selection**: choose tier, set quotas (extensions, concurrent calls, DIDs, storage)
3. **Auth configuration**: Entra ID, Google, or traditional (provide tenant's Entra tenant ID if SSO)
4. **Trunk setup**: assign SIP trunk (shared MSP trunk or tenant-dedicated), E911 configuration
5. **DID ordering**: search and order initial DIDs, assign SMS capability
6. **10DLC registration**: brand registration, campaign setup, compliance documents generated
7. **Initial config**: import from existing system or start from template
8. **Phone provisioning**: register MAC addresses, assign to extensions, push firmware
9. **User creation**: bulk import from CSV/AD/Entra, send welcome emails with login instructions
10. **Go-live checklist**: verify calls work, verify E911, verify SMS, verify recording, sign-off

### Tenant Cloning
- "Set up Client B exactly like Client A"
- Copy: ring groups, queues, IVRs, time conditions, feature codes, class of service, MOH, templates
- Don't copy: extensions, DIDs, recordings, CDR, users (tenant-specific data)
- Clone as template: save a tenant config as a reusable template

### Tenant Suspension
- MSP admin can suspend a tenant (non-payment, contract issue, etc.)
- Suspended state:
  - Inbound calls → "service suspended" announcement
  - Outbound calls blocked (except 911)
  - Admin portal → read-only
  - Web/mobile client → read-only (can view history but not make calls/send SMS)
  - Recordings and data preserved (not deleted)
  - API calls return 403 with suspension notice
- Unsuspend: full service restored immediately

### Offboarding Workflow
1. **Data export**: full tenant data export (config, CDR, recordings, SMS, voicemail)
2. **Number porting out**: provide LOA and required info to receiving carrier
3. **Number release**: release any non-ported DIDs
4. **Decommission**: deactivate extensions, stop recordings, disable API keys
5. **Data retention**: hold data for configurable period (default 30 days) before permanent deletion
6. **Permanent deletion**: remove all tenant data from all systems (database, object storage, Redis, backups)
7. **Confirmation**: generate offboarding completion report
- Each step requires MSP admin confirmation
- Offboarding can be paused/resumed

---

## 23. Mass Notification System

### Multi-Channel Blast
- Send notifications via multiple channels simultaneously:
  - Voice call (recorded message or TTS)
  - SMS
  - Email
  - Push notification (mobile app)
- Recipient lists: by extension group, ring group, queue, custom list, entire tenant
- Template-based messages (per channel, with variable substitution: {name}, {date}, etc.)

### Use Cases
- Emergency notifications (fire, active threat, severe weather)
- IT outage alerts
- Snow day / office closure
- Appointment reminders (batch)
- Company-wide announcements

### Capabilities
- Schedule notifications (send now or schedule for future)
- Delivery tracking per channel per recipient
- Retry logic (voice: retry if no answer, configurable attempts)
- Voice notification options:
  - Play recording or TTS
  - DTMF interaction ("Press 1 to confirm, Press 2 to repeat")
  - Escalation on no-answer (try next number for recipient)
- Campaign reporting: sent, delivered, confirmed, failed per channel
- Per-tenant templates (tenant admin creates and manages)
- MSP-wide notifications (MSP admin → blast to all tenants)

---

## 24. Call Center Quality Management

### Agent Scoring
- Supervisor scores recorded calls on a configurable rubric
  - Categories: greeting, empathy, accuracy, resolution, professionalism
  - Per-category score (1-5) + overall score
  - Notes/comments per category
- Scoring integrated into CDR/recording browser (listen + score in one view)
- Agent scorecard: trend over time, comparison to team average

### Screen Recording (web client only)
- Record agent's screen during calls (opt-in per tenant, per queue)
- Synchronized playback: call audio + screen recording side by side
- Storage in object storage alongside call recordings
- Retention policy applies (same as call recordings)
- PCI pause/resume applies to screen recording too

### Call Tagging & Categorization
- Agent tags calls after completion (drop-down categories per tenant)
  - e.g., "billing inquiry", "technical support", "complaint", "sales lead"
- Tags visible in CDR and reports
- AI auto-tagging suggestion (from transcription/summary)
- Tag-based reporting (how many calls per category per day/week/month)

### Quality Reports
- Per-agent quality score trends
- Per-team quality score comparison
- Per-category breakdown (which skills need improvement?)
- Correlation: quality score vs. customer sentiment (from AI)
- Exportable for HR / performance reviews

---

## 25. Hospitality Module

### Wake-Up Calls
- Schedule wake-up call per room/extension (front desk or guest self-service)
- Configurable message (TTS or recorded)
- Retry logic (if no answer, retry in X minutes, up to Y attempts)
- Wake-up call report (confirmed, no answer, failed)
- Snooze option (press * to snooze 10 minutes)

### Room Management
- Check-in: assign extension to guest name, set caller ID, enable outbound calling
- Check-out: reset extension, clear voicemail, clear call history, disable outbound
- Room status codes (via feature codes from room phone):
  - Housekeeping status (clean, dirty, inspected)
  - Maintenance request
  - Minibar restock
- Status board in admin view (room grid with status indicators)

### Guest Features
- Direct inward dialing to room
- Internal dialing (room-to-room, front desk, restaurant, spa)
- Speed dials for hotel services (pre-programmed on room phone)
- Outbound call restrictions (local only, domestic, international — per room/guest)
- Do not disturb (blocks calls to room, caller hears DND message)
- Voicemail per room (reset on check-out)

### Billing Integration
- Call cost tracking per room
- Integration with PMS (Property Management System) — FIAS/OHC protocol or API
- Room charges for phone calls posted to guest folio
- Rate decks per call type (local free, long distance billed, international billed)

---

## 26. Robocall & Spam Filtering (Inbound)

### STIR/SHAKEN Verification (Inbound)
- Verify STIR/SHAKEN attestation on all inbound calls from PSTN
- Attestation levels displayed to user:
  - **A (Full)**: carrier verified caller owns the number — green checkmark on caller ID
  - **B (Partial)**: carrier verified caller but not the number — yellow indicator
  - **C (Gateway)**: carrier cannot verify — no indicator
  - **No attestation**: call did not pass through STIR/SHAKEN — gray/unknown
- Attestation level logged in CDR for every call
- Configurable policies per tenant:
  - Allow all calls regardless of attestation
  - Send no-attestation calls to voicemail
  - Reject no-attestation calls (aggressive, not recommended)
  - Ring differently for unverified calls (distinctive ring / alert info header)

### Caller Reputation / Spam Scoring
- Integration with spam reputation databases:
  - Nomorobo, Hiya, First Orion, or equivalent API
  - Lookup on inbound call, return spam score
- Spam score displayed on caller ID: "Suspected Spam" label
  - On desk phone display (via caller name manipulation)
  - On web client (visual indicator)
  - On mobile client (visual indicator)
- Configurable actions per tenant based on spam score:
  - Low risk: ring normally
  - Medium risk: ring with "Suspected Spam" label
  - High risk: send to voicemail, or play "number not in service" and disconnect
  - Known spam: auto-reject
- Tenant-managed blocklist (block specific numbers or patterns) — manual additions
- Tenant-managed allowlist (always ring, even if flagged as spam) — override
- MSP-managed global blocklist (block known bad actors across all tenants)
- Spam score logged in CDR

### Reporting
- Spam call volume per tenant (how many flagged calls per day/week)
- Block rate (how many calls were auto-rejected or sent to VM)
- False positive tracking (tenant marks a blocked call as legitimate)

---

## 27. NAT Traversal / STUN / TURN

### STUN Server
- Built-in STUN server (or configurable to use external STUN servers)
- Used by WebRTC clients (web + mobile) and SIP endpoints for NAT detection
- Lightweight, low resource usage

### TURN Server
- Built-in TURN server (coturn or integrated into Rust SIP proxy)
- Required for WebRTC when symmetric NAT or restrictive firewalls block direct media
- TURN credential provisioning: short-lived credentials generated per session via API
- TLS-encrypted TURN (TURNS) for media relay
- Bandwidth monitoring (TURN relay is CPU/bandwidth intensive — track usage)

### SIP NAT Handling
- Rust SIP proxy handles NAT for desk phones:
  - Detect NATed endpoints (compare Contact header vs source IP)
  - Rewrite SDP for NATed endpoints (replace private IP with public IP)
  - SIP keep-alive / OPTIONS ping to maintain NAT bindings
  - Handle re-INVITE for media IP changes
  - rport support (RFC 3581)
- FreeSWITCH NDLB (Network Device Load Balancing) settings for NAT
- Per-endpoint NAT configuration (auto-detect or manual override)

### ICE / ICE-Lite
- ICE candidate gathering for WebRTC clients (host, srflx, relay candidates)
- ICE-Lite on FreeSWITCH / SIP proxy side (server doesn't need full ICE)
- DTLS-SRTP key exchange through ICE for WebRTC

### Deployment Considerations
- TURN server should be on a public IP with sufficient bandwidth
- Docker: TURN container with host networking or mapped UDP ports
- Geographic TURN servers for low-latency media relay (future, multi-region)

---

## 28. SIP Debugging Tools

### SIP Trace Viewer (in MSP Admin Panel)
- Capture and view SIP messages in real-time from the browser
- Filter by:
  - Extension / endpoint
  - DID / phone number
  - Call-ID (SIP header)
  - Source/destination IP
  - Time range
  - Tenant
- **SIP ladder diagram**: visual representation of SIP message flow
  - INVITE → 100 Trying → 180 Ringing → 200 OK → ACK → BYE → 200 OK
  - Color-coded by message type (request vs response, success vs error)
  - Click on any message to see full SIP headers and body
- **RTP stream analysis** (alongside SIP trace):
  - Codec in use
  - Packet count, jitter graph, packet loss graph
  - MOS estimate from RTP stats
- **One-click targeted capture**:
  - "Capture next call from extension 1042" → starts capture, waits, stops when call ends
  - "Capture next call to DID 555-0100" → same
  - Returns complete SIP trace + RTP analysis for that call
- **Export**: download trace as pcap (for Wireshark) or JSON (for API consumption)

### FreeSWITCH Debug Controls
- Sofia SIP profile debug level control from admin UI (toggle verbose SIP logging)
- ESL command execution from admin UI (for MSP admin troubleshooting)
- FreeSWITCH log viewer (filter by level, module, tenant)
- Active channel inspection (show all active channels with detailed SIP info)

### Phone-Side Debugging
- Request syslog from phone (remote syslog collection — see Section 18)
- Phone web UI proxy (access phone's admin page through the platform, without needing LAN access)
- Provision phone with debug logging enabled temporarily, collect logs, then revert

---

## 29. Business Continuity / Tenant Failover

### Automatic Failover
- Monitor registered endpoint count per tenant
- If **all endpoints go offline** for >X minutes (configurable, default 5 min):
  - Activate tenant failover routing
  - Notify tenant admin and MSP admin (email, SMS, push)
- **Per-tenant failover plan** (configurable by tenant admin or MSP admin):
  - Forward all inbound calls to a list of cell phone numbers (sequential or simultaneous ring)
  - Forward to an emergency IVR ("We are experiencing technical difficulties...")
  - Forward to voicemail (all DIDs → shared voicemail box)
  - Forward to another tenant (e.g., answering service)
  - Custom per-DID failover rules (main line → cell, support DID → voicemail)

### Per-Extension Failover
- Each user can configure a personal failover number (cell phone)
- If their extension is unreachable, calls forward to their failover number
- Independent of tenant-wide failover (works for individual remote workers too)
- Configurable via web client, mobile client, or phone portal

### Recovery
- When endpoints re-register, auto-deactivate failover
- Notification: "Office phones back online, failover deactivated"
- Configurable cooldown (don't flap between failover/normal if connection is unstable)
- Manual override: tenant admin can force failover on/off regardless of endpoint status

### Manual Failover Toggle
- Tenant admin can activate failover for planned outages (office move, ISP maintenance)
- MSP admin can activate failover for any tenant
- BLF key option for failover toggle (physical button on receptionist phone)

### SMS During Failover
- SMS continues to work (routed through cloud platform, not dependent on office connectivity)
- Auto-reply on inbound SMS during failover: "We're experiencing a phone outage. Please text us and we'll respond as soon as possible." (configurable)

---

## 30. Platform Status Page

### Public Status Page
- Hosted at configurable URL (e.g., status.yourplatform.com or status.yourmsp.com)
- White-labeled with MSP branding
- **Component status indicators** (operational / degraded / partial outage / major outage):
  - SIP / Voice Service
  - WebRTC / Web Client
  - Mobile Client (push notifications)
  - SMS / Messaging
  - API
  - Admin Portal
  - SIP Trunks (per provider: ClearlyIP, Twilio)
  - Recording / Storage
  - Phone Provisioning
- **Uptime percentage** per component (90-day rolling)
- **Incident history**: past incidents with timeline, updates, and resolution notes
- **Scheduled maintenance**: upcoming maintenance windows with expected impact

### Auto-Population from Monitoring
- Monitoring system automatically updates status page when issues detected:
  - Trunk down → SIP Trunks component → degraded
  - FreeSWITCH overloaded → Voice Service → degraded
  - API response time >5s → API → degraded
- MSP admin can override automatic status (manual incident creation/resolution)
- Auto-resolve when monitoring confirms recovery

### Subscriptions
- Subscribe to status updates via:
  - Email (per-component or all)
  - SMS
  - RSS feed
  - Webhook (for custom integrations)
- Tenant admins auto-subscribed on tenant creation (configurable)

### Incident Management
- Create incident from MSP admin panel
- Incident updates with timestamps ("Investigating", "Identified", "Monitoring", "Resolved")
- Post-incident report (root cause, impact, resolution, prevention measures)
- Incident templates (common scenarios pre-written)

---

## 31. Post-Call Surveys

### IVR-Based Survey (after call)
- Agent hangs up → caller automatically transferred to survey IVR
- Configurable per queue (enable/disable, which survey template)
- Survey questions (DTMF input):
  - "On a scale of 1 to 5, how would you rate your experience? Press 1 for poor, 5 for excellent."
  - Multiple questions supported (up to 5)
  - Open-ended: "Please leave a brief comment after the tone" (recorded, transcribed by AI)
- Skip option: caller can hang up or press # to skip
- Thank you message after completion

### SMS-Based Survey (after call)
- After call ends, send SMS to caller with survey link
- Web-based survey form (hosted, branded per tenant)
- Configurable delay (send immediately, 5 min after, 1 hour after)
- Survey questions: rating scale, multiple choice, free text
- Link expiry (survey link valid for X hours/days)

### Survey Results
- Tied to CDR record (survey results linked to the specific call)
- Tied to agent (agent's satisfaction scores)
- Survey results visible in:
  - CDR detail view
  - Agent performance reports
  - Queue performance reports
- Survey reports:
  - Avg satisfaction score per agent, per queue, per tenant
  - Score distribution (how many 1s, 2s, 3s, etc.)
  - Trend over time
  - Correlation with call metrics (longer wait → lower score?)
  - Free-text response review (with AI sentiment/topic extraction)
- Survey response rate tracking

---

## 32. Scheduled Callbacks from Queues

### Caller-Initiated Scheduled Callback
- When caller is in queue, offer: "Press 2 to schedule a callback at a specific time"
- System prompts for preferred time:
  - "Press 1 for this afternoon, Press 2 for tomorrow morning, Press 3 to enter a specific time"
  - Or: DTMF entry of hour (e.g., "Enter the hour you'd like us to call, followed by pound")
- Calendar-aware: only offer times during business hours (uses tenant's time conditions)
- Confirmation: "We'll call you back at [time]. You'll receive a text confirmation. Goodbye."
- SMS confirmation sent to caller with scheduled time

### Callback Execution
- Callbacks managed in a scheduled callback queue
- System auto-dials customer at scheduled time
- When customer answers, system bridges to next available agent in the queue
- If customer doesn't answer:
  - Retry logic (configurable: retry in 15 min, up to 3 attempts)
  - After max retries: send SMS "We tried to reach you. Please call us at [number]."

### Management
- Scheduled callbacks visible in queue dashboard (upcoming callbacks with times)
- Supervisor can reschedule, cancel, or manually trigger callbacks
- Callback reports:
  - Callbacks scheduled, completed, failed, rescheduled
  - Avg time between request and completion
  - Customer satisfaction on callback vs. waited-in-queue calls

---

## 33. Custom Messages on Hold

### Messages on Hold (MOH) Composer
- Per-tenant, per-queue configurable message-on-hold playlists
- **Playlist structure**: music segment → message → music segment → message → ...
  - Configurable segment durations (e.g., 30s music, 15s message, repeat)
  - Configurable message interval (play a message every X seconds)
- **Message types**:
  - Uploaded audio files (professionally recorded)
  - TTS-generated messages (type text → system generates audio)
  - Position/wait time announcements interspersed with messages
- **Message scheduling**:
  - Seasonal messages (holiday promotion active Dec 1-25)
  - Time-of-day messages (lunch specials during 11am-1pm)
  - Permanent messages (company info, website, hours)
- **Message rotation**: sequential, random, or weighted
- **Preview**: listen to the full MOH experience before publishing

### Use Cases
- Promotional: "Ask about our winter special — 20% off all services this month"
- Informational: "Visit our website at example.com for self-service options"
- Reassurance: "Your call is important to us. An agent will be with you shortly"
- Upsell: "Did you know we also offer managed IT services? Ask your agent for details"

### Management
- Drag-and-drop playlist builder in web admin
- Upload audio files or generate via TTS
- Per-queue assignment (sales queue gets sales messages, support queue gets support messages)
- Analytics: track which messages play most, correlate with hold time (do callers hang up during specific messages?)

---

## 34. Wrap-Up / Disposition Codes

### Configuration
- Per-queue and/or per-tenant disposition code list
- Codes are customizable: label + optional category/group
  - e.g., "Billing Inquiry" (category: Billing), "Password Reset" (category: Technical Support)
- Codes can be required or optional after each call (configurable per queue)
- Configurable wrap-up time limit (agent must enter disposition within X seconds)

### Agent Experience
- After call ends, disposition prompt appears in web/mobile client
  - Dropdown of codes, with search/filter for long lists
  - Optional free-text notes field
  - "Not ready" status until disposition is entered (if required)
- Phone-based disposition: DTMF input (press 1 for Billing, 2 for Support, etc.) — for agents on desk phones only
- AI suggested disposition (from call transcription/summary) — agent confirms or overrides

### Integration
- Disposition attached to CDR record
- Disposition included in CRM activity logging (auto-tagged in Salesforce, HubSpot, etc.)
- Disposition available in webhook payloads (call.ended event includes disposition)
- Disposition available via API (query CDR by disposition code)

### Reporting
- Calls by disposition code (count, percentage, trend)
- Disposition breakdown per queue, per agent
- Avg handle time by disposition (billing calls take longer than password resets)
- Disposition trends over time (are billing complaints increasing?)
- Cross-reference: disposition + sentiment score (are "complaint" calls actually negative sentiment?)

---

## 35. Localization / Internationalization (i18n)

### Web Client & Admin UI
- UI fully translatable (all labels, buttons, messages, errors)
- Language files: JSON-based, loadable at runtime
- Initial languages: English, Spanish, French
- Per-user language preference (stored in user profile)
- Per-tenant default language
- RTL (right-to-left) layout support (for Arabic, Hebrew — future)
- Date/time format localization (MM/DD/YYYY vs DD/MM/YYYY, 12h vs 24h)
- Number format localization (comma vs period for thousands/decimals)
- Currency format per tenant

### Mobile Client
- Same language support as web client (synced language files)
- Follows device language setting by default, overridable in app settings

### IVR / Voice Prompts
- Multi-language prompt packs:
  - English (US), English (UK), Spanish (US), Spanish (Latin America), French (Canada), French (France)
  - Additional languages addable as prompt packs
- Per-IVR language selection: "Press 1 for English, Press 2 for Spanish"
- Per-tenant default prompt language
- Custom prompt recording per language (tenant uploads their own recordings per language)
- TTS engine language/voice selection per tenant

### System Notifications
- Email templates localized (voicemail notification, fax notification, alerts)
- SMS auto-responses localized
- Push notification text localized

### Translation Management
- Translation files stored in repo, editable by MSP admin
- Community/customer-contributed translations (future — translation portal)
- Machine translation fallback for missing strings (with flag for human review)

---

## 36. Plugin / Marketplace Architecture

### Plugin System
- **Plugin API**: defined hooks and events that plugins can subscribe to
  - Call lifecycle hooks (pre-route, post-answer, post-hangup)
  - SMS hooks (pre-send, post-receive)
  - Admin UI hooks (add tabs, add widgets, add menu items)
  - CDR hooks (enrich CDR with custom data)
  - Webhook hooks (add custom event types)
- **Plugin types**:
  - CRM connectors (new CRM integrations without core changes)
  - Reporting widgets (custom dashboard widgets)
  - Phone provisioning templates (new phone brand/model support)
  - Custom IVR actions (e.g., database lookup, API call during IVR)
  - Notification channels (e.g., Slack, Microsoft Teams, PagerDuty)
  - AI/ML processors (custom transcription engine, custom sentiment model)
  - Billing integrations (new PSA/billing platform connectors)
- **Plugin packaging**: standard format (manifest.json + code + assets)
- **Plugin lifecycle**: install, enable, disable, uninstall, update

### Sandboxing & Security
- Plugins run in isolated containers or sandboxed processes
- Plugins can only access data for the tenant(s) they're enabled on
- Plugin permissions declared in manifest (what hooks, what data access)
- MSP admin approves plugin permissions on install
- Plugin audit logging (what the plugin accessed/modified)

### Marketplace (future)
- Plugin store within MSP admin panel
- Internal plugins (built by MSP team) — private
- Third-party plugins (future) — reviewed and approved by MSP admin
- Plugin versioning and update notifications
- Plugin ratings/reviews (if third-party marketplace)

### Per-Tenant Plugin Management
- MSP admin: install plugins, make available to tenants
- Tenant admin: enable/disable available plugins for their tenant
- Plugin configuration per tenant (e.g., CRM connector needs tenant-specific API key)

---

## 37. Inter-Tenant Calling

### Configuration
- MSP admin enables inter-tenant calling between specific tenant pairs
- Bilateral: if Tenant A can call Tenant B, Tenant B can call Tenant A
- Global option: enable inter-tenant calling for all tenants on the platform (MSP-wide)
- Per-tenant opt-out: tenant admin can decline inter-tenant calling

### Dialing Plan
- **Option 1: Prefix dialing**: dial a short prefix + extension (e.g., 8-[tenant_code]-[ext])
  - Tenant codes assigned by MSP admin (3-4 digits)
  - Example: Tenant A (code 100), extension 1042 → dial 8-100-1042
- **Option 2: Full number dialing**: dial the DID of the other tenant's extension
  - Platform recognizes the DID belongs to another tenant → routes internally
  - No trunk charges (internal media path, never hits PSTN)
- Platform automatically selects internal routing when destination is on-platform

### Features
- Internal media path (media stays within the platform — lower latency, no trunk cost)
- Caller ID: shows internal extension info (not DID) when calling inter-tenant
- Presence sharing between inter-tenant pairs (optional, configurable per pair)
  - Tenant A can see Tenant B's extension status on BLF keys
- Transfer between tenants (blind and attended transfer to extension on other tenant)
- Inter-tenant directory (shared directory entries for paired tenants)

### Billing
- Inter-tenant calls are free (no trunk charges — internal routing)
- Inter-tenant calls logged in CDR for both tenants
- Usage visible in reports but not billed

### Security
- Inter-tenant calling does not grant access to each other's admin panels, CDR, recordings, or config
- Only call routing and optional presence sharing are exposed
- Call recording policies of the receiving tenant apply to the receiving side

---

## 38. Documentation Portal

### User-Facing Documentation Site
- Hosted as part of the platform (docs.yourplatform.com or per-MSP branded)
- Searchable, versioned, mobile-responsive
- White-label brandable (MSP logo, colors, custom domain)

### Documentation Categories

#### End-User Guides
- Getting started (first login, set up your profile, configure voicemail)
- Desk phone user guide (per model: Sangoma P-series, Yealink, Polycom, etc.)
  - Feature codes cheat sheet (printable PDF)
- Web client user guide (making calls, SMS, chat, voicemail, presence)
- Mobile app user guide (iOS and Android)
- Voicemail guide (recording greetings, accessing messages, visual voicemail)
- SMS guide (personal messaging, shared inbox)
- Video conferencing guide (web client)
- FAQ / troubleshooting (common issues: no audio, can't register, one-way audio)

#### Tenant Admin Guides
- Admin portal walkthrough
- Managing extensions (create, edit, bulk operations)
- Setting up ring groups, queues, IVRs
- Time conditions and holiday calendars
- DID management (ordering, assigning, porting)
- Call recording configuration
- E911 location management
- SMS setup (10DLC registration, DID assignment, queue SMS)
- Phone provisioning (adding phones, firmware, templates)
- Reports and dashboards guide
- User/role management
- Branding customization
- Failover configuration
- API key management

#### MSP Admin Guides
- Platform administration overview
- Tenant provisioning workflow
- Trunk management
- Monitoring and alerting
- Security and audit log review
- Migration/import tools
- Phone fleet management
- SIP debugging tools
- Troubleshooting runbook (common issues and resolution steps)
- Disaster recovery procedures

#### API Documentation
- Swagger UI (interactive, auto-generated from OpenAPI spec)
- Written API guides (authentication, pagination, error handling, webhooks)
- Code examples (Python, Node.js, Go, cURL)
- Quickstart tutorials

### Contextual Help
- Every page in the web admin has a "?" icon → opens relevant documentation section
- Tooltips on complex settings with "Learn more" links to docs
- First-time setup wizards link to relevant guides at each step

### Video Tutorials (optional)
- Embedded video walkthroughs for common tasks
- Organized by role (end user, tenant admin, MSP admin)
- Hosted on platform (not YouTube) for white-label compliance

### Maintenance
- Documentation versioned alongside platform releases
- Docs updated as part of definition of done for every feature
- Search indexing for instant full-text search
- Community feedback: "Was this helpful?" + "Suggest an edit" on every page

---

## 39. Platform Changelog & Release Notes

### In-App Changelog
- Accessible from web client navigation: "What's New" link
- Badge notification on new releases: "3 new updates" indicator
- Per-release entry:
  - Version number and date
  - New features (with brief description + link to docs)
  - Improvements / enhancements
  - Bug fixes
  - Breaking changes (if any, with migration notes)
  - Screenshots or short GIFs for visual features

### Release Process
- MSP admin previews release notes before they're visible to tenants
- MSP admin can customize release notes (add MSP-specific context, remove irrelevant items)
- MSP admin controls when release notes are published to tenants

### Notification
- Email to tenant admins on new release (opt-in, configurable per tenant)
- In-app notification for all users (dismissible badge)
- Release notes included in status page as "maintenance completed" updates

### API Changelog
- Separate changelog for API changes (new endpoints, deprecated endpoints, breaking changes)
- Versioned alongside API versions (v1, v2, etc.)
- Published in developer portal

---

## 40. Phone Compatibility Testing & Validation

### Validated Phone Matrix
- Maintained list of tested phone models with compatibility status:
  - **Fully supported**: all features work, provisioning templates available, regularly tested
  - **Supported**: core features work, provisioning templates available, periodically tested
  - **Community supported**: basic SIP works, no official provisioning template, untested
  - **Unsupported**: known issues, not recommended
- Per-model feature compatibility:
  - SIP TLS registration
  - SRTP media encryption
  - BLF / presence
  - Auto-provisioning (HTTP/HTTPS)
  - Visual voicemail (if phone supports it)
  - DPMA replacement protocol (Sangoma only)
  - Multicast paging
  - Hot desking
  - Video (if phone supports it)

### Automated Compatibility Testing (CI)
- SIP registration tests per phone model (using SIPp or pjsua simulating each phone's User-Agent)
- TLS/SRTP negotiation tests per model
- Provisioning template generation and validation per model
- BLF subscription and notification tests
- Run on every release (catch regressions)
- Test matrix: phone model × firmware version × feature

### Phone Model Database
- Maintained in platform database (model, manufacturer, firmware versions, capabilities)
- Exposed in admin UI: when provisioning a phone, show compatibility status
- Provisioning templates auto-selected based on detected model (via User-Agent or MAC OUI)
- Firmware version recommendations per model (tested firmware → recommended)

### Published Compatibility List
- Available in documentation portal
- Updated with each release
- Searchable by manufacturer, model, feature
- Includes known issues and workarounds per model

---

## 41. Headset Integration (Web & Desktop Client)

### Supported Headset SDKs
- **Jabra** — Jabra Chrome SDK (JavaScript, browser-native)
- **Poly/Plantronics** — Plantronics Hub SDK (requires Hub desktop app + browser extension)
- **EPOS** — EPOS Connect SDK
- **Yealink** — Yealink USB headset SDK (future)

### Button Mapping
- **Answer/end call** button → accept incoming call / hang up active call
- **Mute/unmute** button → toggle microphone mute (synced bidirectionally with web client UI)
- **Volume up/down** → adjust call volume
- **Hold** button (if headset supports) → hold/resume active call
- **Reject call** (long press or second button) → reject incoming call to voicemail
- **Flash** button (if supported) → swap between held calls

### Status Indicators
- Headset LED / busylight synced to call state:
  - Idle: off or green
  - Ringing: flashing
  - In call: solid red
  - Muted: pulsing red
- Compatible with standalone busylights (Kuando, Embrava) via SDK

### Implementation
- Headset SDK loaded conditionally (detect connected headset brand)
- Bidirectional sync: physical button → UI state, UI control → headset state
- Headset selection in web client settings (choose audio input/output device)
- Works in browser (Chrome, Edge) and in desktop app (Electron — see Section 52)
- Fallback: if no SDK detected, standard browser audio device selection still works

---

## 42. TCPA Compliance & DNC List Integration

### National DNC Registry
- Integration with FTC National Do Not Call Registry
- Automated DNC list download and refresh (updated regularly)
- Scrub contact lists against DNC before any broadcast/auto-dialer campaign
- Per-number DNC check available via API (for programmatic dialing)
- Block outbound call if number is on DNC and no prior express written consent on file

### State-Level DNC Lists
- Support for state-specific DNC registries (states with their own lists)
- Configurable per tenant based on state(s) they operate in
- Combined scrub: federal + applicable state lists

### Internal DNC List (per tenant)
- Tenant-managed opt-out list (separate from SMS opt-out)
- Contacts can be added manually, via API, or automatically (caller requests removal)
- Internal DNC honored across all outbound campaigns and auto-dialer
- Synced with SMS opt-out list (opted out of SMS → added to voice DNC too, if configured)

### Calling Time Window Enforcement
- No automated/broadcast calls before 8:00 AM or after 9:00 PM **callee's local time**
- Time zone determination by area code / NPA-NXX lookup
- Override for emergency notifications (exempt from time restrictions)
- Configurable per campaign (tighter windows if desired)

### Consent Management
- Prior express written consent tracking per contact:
  - Consent record: timestamp, method (web form, verbal, paper), disclosure text shown
  - Consent stored in database, tied to contact + campaign
  - Consent revocation tracking (when STOP/DNC received)
- Consent required before broadcast/auto-dialer can call a number
- Consent audit trail (immutable, exportable for legal defense)

### Campaign Compliance Checks
- Before a broadcast campaign launches, platform validates:
  - All contacts scrubbed against federal + state DNC
  - All contacts have valid consent on file (if required by campaign type)
  - Calling window configured correctly
  - Caller ID set to a valid, answerable number (TCPA requirement)
  - Opt-out mechanism included in message (TCPA requirement)
- Campaign blocked from launching if compliance checks fail
- Compliance report per campaign (contacts scrubbed, contacts blocked, consent status)

---

## 43. Boss/Admin (Executive/Assistant)

### Configuration
- Executive assigns one or more assistants (via admin portal or self-service)
- Assistant can manage one or more executives
- Relationship stored in tenant config, exposed via API

### Call Filtering Modes (configurable per executive)
- **All calls to assistant first**: every call to executive rings assistant's phone, assistant decides to put through or handle
- **Simultaneous ring**: executive + assistant ring at the same time, either can answer
- **Assistant overflow**: executive's phone rings first, if no answer within X seconds, rings assistant
- **Screening**: assistant answers, announces caller, executive accepts or declines
- **VIP bypass**: configured list of caller IDs that ring executive directly, all others go through assistant
- **DND override**: assistant can ring through executive's DND (for urgent calls)

### Shared Line Appearance (SLA)
- Assistant's phone shows executive's line(s) as BLF/SLA keys
- Assistant can see: executive's line idle, ringing, in-call, on hold
- Assistant can:
  - Pick up ringing call on executive's line
  - Place executive's active call on hold
  - Resume a call held on executive's line
  - Bridge into executive's call (if permitted)
- Executive's phone shows held calls that assistant parked for them

### Web / Mobile Client
- Assistant sees executive's call status in real-time in web/mobile client
- One-click answer/transfer/hold for executive's calls
- Call log shows calls handled on behalf of executive (tagged in CDR)

### CDR
- Calls handled by assistant on behalf of executive tagged in CDR:
  - Answered by: assistant
  - On behalf of: executive
  - Disposition and notes attached

---

## 44. Multi-Site / Multi-Timezone per Tenant

### Site Definition
- Tenant can have multiple **sites** (locations / offices)
- Per-site configuration:
  - Name, physical address
  - Timezone
  - E911 location (tied to site address)
  - Local outbound caller ID (site-specific DID)
  - Site-specific paging groups
  - Site-specific parking lots
  - Site-specific MOH

### Extension-to-Site Assignment
- Each extension assigned to a site
- Extension inherits site's timezone, E911 location, caller ID defaults
- Override possible per extension (remote worker at a different address)

### Site-Based Time Conditions
- Time conditions scoped to site timezone
- Example: NY office (Eastern) business hours 9am-5pm ET, LA office (Pacific) 9am-5pm PT
- Single IVR can reference site-specific time conditions:
  - "If NY hours → ring NY group. If NY after-hours but LA hours → ring LA group. If both after-hours → voicemail."

### Site-Based Routing
- Inbound calls to site-specific DID → routed using that site's time conditions and groups
- Inter-site calling (extension at NY calls extension at LA — internal, no trunk)
- Site failover: if NY site offline, failover rules can route to LA site

### Site Dashboard
- Per-site view: extensions, phones, call volume, quality, alerts
- Cross-site comparison: call volume by site, quality by site
- MSP admin: see all sites across all tenants

### Reporting
- Reports filterable by site
- Per-site call volume, per-site cost, per-site agent performance
- Site comparison reports

---

## 45. AI Compliance Monitoring

### Compliance Rules Engine
- Configurable compliance rules per queue, per campaign, per tenant
- Rules defined as natural language checks against call transcripts:
  - **Greeting compliance**: "Agent must state their name within first 15 seconds"
  - **Recording disclosure**: "Agent must mention that the call is being recorded"
  - **Verification**: "Agent must verify caller's identity before discussing account details"
  - **Required disclosures**: "Agent must read cancellation policy before processing cancellation"
  - **Prohibited language**: "Agent must not promise a specific resolution date"
  - **Closing compliance**: "Agent must offer additional assistance before ending call"
- Custom rules definable by tenant admin or MSP admin

### Automated Scanning
- Post-call: AI scans transcript against configured rules
- Each rule scored: pass / fail / not applicable
- Overall compliance score per call (percentage of rules passed)
- Flagged calls: calls that fail critical rules are flagged for supervisor review

### Results & Reporting
- Compliance score attached to CDR record
- Per-agent compliance score (average, trend)
- Per-queue compliance score
- Per-rule pass rate (which rules are agents failing most?)
- Compliance trend over time (are agents improving after training?)
- Flagged call review queue (supervisor sees flagged calls, listens, confirms/dismisses)

### Alerting
- Real-time alert to supervisor when critical rule violated (requires real-time transcription)
- Daily compliance summary email per queue/tenant
- Threshold alerts: "Agent X compliance dropped below 80% this week"

### Integration
- Compliance score included in agent quality scorecard (Section 24)
- Compliance data available via API and webhooks
- Compliance reports in scheduled email reports (Section 9)

---

## 46. Workforce Management (Call Center Staffing)

### Historical Analysis
- Call volume analysis by: hour of day, day of week, week of year, month
- Seasonality detection (holiday peaks, summer lulls)
- Average handle time trends
- Abandon rate by time of day (when are callers giving up?)

### Staffing Forecasts
- Predict future call volume based on historical patterns
- Erlang C calculator: given predicted volume + target SLA → recommended agents needed
- Forecast by: hour, day, week
- Visual forecast: chart showing predicted volume with recommended staffing levels
- Adjustable parameters: shrinkage factor (breaks, meetings, PTO), target SLA, target ASA (avg speed of answer)

### Agent Scheduling
- Drag-and-drop schedule builder (web UI)
- Define shifts: start time, end time, break times
- Assign agents to shifts
- Schedule templates (reusable weekly patterns)
- Schedule publication (publish to agents via web/mobile client, email)
- Shift swap requests (agent-to-agent, supervisor approval)
- PTO / time-off requests (agent submits, supervisor approves/denies)
- Schedule export (CSV, PDF, calendar integration — iCal)

### Schedule Adherence
- Real-time adherence monitoring:
  - Is the agent logged in when they should be?
  - Is the agent on break when scheduled?
  - Is the agent in after-call work longer than expected?
- Adherence score per agent (% of scheduled time actually logged in and available)
- Adherence dashboard (real-time view of who is in/out of adherence)
- Adherence reports (daily, weekly, per-agent, per-team)

### Overtime & Alerts
- Overtime alerts: agent approaching scheduled hours limit
- Understaffing alerts: fewer agents logged in than forecast requires
- Overstaffing alerts: more agents than needed (cost optimization)

### Reporting
- Forecast vs. actual comparison (how accurate were our predictions?)
- Staffing efficiency report (agents needed vs. agents available vs. calls handled)
- Schedule adherence report per agent, per team
- Cost analysis (labor hours × hourly rate vs. call volume)

---

## 47. Click-to-Call Browser Extension

### Chrome / Edge Extension
- Detects phone numbers on any web page (regex pattern matching)
- Highlights detected numbers with a subtle indicator
- Click or right-click on any phone number → "Call via [Platform Name]"
- Initiates call via:
  - Web client (opens/focuses web client, starts call) — default
  - Desk phone (API call → platform rings agent's desk phone, then dials the number) — click-to-dial
  - Mobile app (deep link → opens mobile app, starts call)
- Configurable default call method in extension settings

### Features
- **Contact lookup**: if number matches a tenant extension or CRM contact, show name on hover
- **Presence preview**: if number is an internal extension, show availability status on hover
- **Call history**: quick view of recent calls to/from this number
- **Quick actions**: call, SMS, add to contacts
- **CRM integration**: if on a CRM page, link call back to CRM record automatically

### Authentication
- Login with platform credentials (same auth — Entra/Google/password+MFA)
- Inherits user's tenant and permissions
- Auto-connect to web client session if web client is open

### Distribution
- Published on Chrome Web Store (and Edge Add-ons — same extension)
- MSP-branded extension (white-label name and icon)
- Enterprise deployment via Chrome policy (auto-install for managed browsers)

---

## 48. Emergency & Physical Security Integration

### Panic Button
- **Soft panic button**: button in web client + mobile app
  - Silent alarm: no sound, sends alert to security team
  - Audible alarm: triggers page group or overhead PA announcement
  - Configurable per tenant: what happens when panic button is pressed
- **Desk phone panic button**: programmable key on desk phone triggers alert
  - Feature code (e.g., **911 or *0911) for silent alarm
  - BLF key with panic function
- **Notification targets** (configurable per tenant):
  - Security team (email, SMS, push, page group)
  - MSP admin (if contracted for security monitoring)
  - Local emergency services (optional — 911 auto-dial)
  - Webhook (integration with building security systems)
- **Location context**: panic alert includes:
  - Extension / user who triggered
  - E911 location (physical address, floor, room)
  - Timestamp
  - Optional: live audio feed from phone microphone (Silent Intercom — see below)

### Silent Intercom / Remote Listen
- Authorized security personnel can remotely activate a phone's microphone
- One-way audio: security listens, phone does not broadcast to the room
- **Strict access controls**:
  - Only available to designated security role (not regular admin)
  - Requires explicit tenant opt-in (feature disabled by default)
  - Immutable audit log of every activation (who, when, which phone, duration)
  - Legal compliance notice in tenant agreement
- Use case: active threat verification before dispatching emergency services
- Auto-timeout (max duration configurable, e.g., 5 minutes)

### Door Phone / Intercom Integration
- SIP-based door stations (2N, Algo, Cyberdata, Akuvox)
- Register as SIP endpoints on the platform
- Inbound call from door station → rings receptionist or ring group
- **DTMF door unlock**: press key during call → triggers relay on door station
  - Relay control via SIP INFO message or HTTP API to door station
  - Configurable per door station (which DTMF key, which relay)
- **Video intercom**: SIP video from door station displayed in web client
  - Video preview before answering
  - Video during call
- **Access log**: CDR records all door station calls (who buzzed in, who answered, was door opened)

### Overhead Paging Integration
- SIP-based PA systems (Algo, Bogen, Atlas/IED, Valcom)
- PA endpoints register as SIP extensions
- Paging zones: group PA endpoints into zones (lobby, warehouse, office, all-call)
- Page group can include both phones + PA endpoints
- Emergency all-call: override all zones, maximum volume, priority interrupt
- Scheduled paging (bell schedules — schools, factories)

### Integration with Building Systems
- Webhook-based integration with building management systems:
  - Fire alarm activation → auto-trigger emergency notification to all phones
  - Intrusion alarm → silent panic alert to security team
  - Building lockdown → door phones auto-lock, PA announcement
- API for third-party security platforms to trigger platform actions

---

## 49. CDR Enrichment from CRM

### Automatic Caller Lookup
- On inbound call, API queries configured CRM for caller's phone number
- If match found, attach to CDR record:
  - Customer name / contact name
  - Company name
  - Account number / customer ID
  - Account status (active, VIP, delinquent, etc.)
  - Custom fields (configurable per CRM integration)
- Enrichment happens in real-time (during call routing, before agent answers)

### Enriched CDR Display
- CDR browser shows customer name alongside phone number
- Search CDR by customer name, company name, account number (not just phone number)
- Click on customer name → opens CRM record (deep link to Salesforce, HubSpot, etc.)
- Enrichment badge on CDR entry: "CRM matched" indicator

### Outbound Enrichment
- Outbound calls: look up dialed number in CRM
- Attach same customer context to CDR
- Pre-call popup on agent's screen: "You're calling John Smith at Acme Corp" (web/mobile client)

### Supported CRMs
- Salesforce (SOQL lookup by phone)
- HubSpot (contact search API)
- ConnectWise Manage (contact/company lookup)
- Zoho CRM
- Custom: webhook-based lookup (tenant provides endpoint, platform sends number, receives enrichment data)

### Caching
- CRM lookup results cached (Redis) for configurable TTL (default 1 hour)
- Reduces CRM API calls for frequent callers
- Cache invalidation on CRM webhook (if CRM supports change notifications)

---

## 50. Call Recording Storage Tiering

### Storage Tiers
- **Hot tier** (fast access — MinIO/S3 SSD-backed):
  - Recent recordings (configurable age: 30, 60, 90 days)
  - Instant playback, instant download
  - Higher storage cost per GB
- **Cold tier** (archival — S3 Glacier, Backblaze B2, or equivalent):
  - Older recordings that have aged out of hot tier
  - Retrieval delay: 1-4 hours (depending on provider/tier)
  - Significantly lower storage cost per GB
- **Deleted**: past retention policy, permanently removed (unless legal hold)

### Automatic Tiering
- Background job evaluates recording age daily
- Recordings older than hot tier threshold → moved to cold tier
- Recordings older than retention policy → deleted (unless legal hold active)
- Tiering is transparent: CDR still shows the recording, just with retrieval delay for cold

### User Experience
- Hot recordings: play button works instantly
- Cold recordings: "This recording is archived. Click to retrieve." → request submitted
  - Notification when retrieval is complete (email, push, in-app)
  - Retrieved recording stays in hot tier for configurable re-cache period (e.g., 7 days)
- Legal hold recordings: never tiered to cold or deleted, always in hot (or configurable)

### Per-Tenant Configuration
- Hot tier duration configurable per tenant (some need 90 days hot, others need 30)
- Cold tier retention configurable per tenant (some need 7 years for compliance, others need 1 year)
- Storage usage dashboard: hot GB, cold GB, total GB, cost estimate, growth trend
- Overage alerts: approaching storage quota

### Cost Tracking
- Storage cost calculated per tenant per tier
- Included in billing/usage reports (Section 10)
- Retrieval cost tracked (cold tier retrievals may incur per-GB cost)

---

## 51. Camp-On / Automatic Callback on Busy

### User Experience
- Call an extension → busy or no answer
- System offers: "Extension 1042 is busy. Press 1 to be called back when they become available."
- Caller presses 1 → system confirms: "We'll call you back when extension 1042 is available. Goodbye."

### Monitoring & Callback
- System subscribes to presence for the target extension
- When target becomes available (call ends, DND removed):
  - System calls back the original caller
  - When caller answers: "Extension 1042 is now available. Connecting you."
  - Bridges the two calls
- If caller doesn't answer callback: retry once, then cancel with SMS notification

### Timeout
- Camp-on expires after configurable duration (default 30 minutes)
- If target doesn't become available within timeout:
  - Caller notified via SMS: "Extension 1042 did not become available. Please try again."
  - Camp-on cancelled

### Configuration
- Feature enabled/disabled per tenant (default: enabled)
- Feature code to activate (e.g., *engagement ring tone then prompt)
- Max simultaneous camp-ons per extension (prevent 50 people camping on the CEO)
- Camp-on timeout configurable per tenant

### CDR
- Camp-on events logged: who camped on whom, duration, outcome (connected, expired, cancelled)

---

## 52. Desktop Application (Electron)

### Overview
- Native desktop application wrapping the web client (Electron framework)
- Windows + macOS + Linux
- Same functionality as web client, plus native OS integrations

### Native OS Integrations (beyond browser)
- **System tray icon**: shows status (available/busy/DND), notification count
  - Right-click menu: set status, open client, quit
- **Native notifications**: OS-level notification popups for incoming calls, SMS, voicemail
  - More reliable than browser notifications (persist even if app not focused)
  - Click notification → answer call / open conversation
- **Global keyboard shortcuts**: configurable hotkeys that work from any application
  - Answer/reject incoming call
  - Toggle mute
  - Open dial pad
- **Auto-launch on login**: start with OS, minimize to tray
- **Dock/taskbar badge**: unread count (missed calls, voicemails, SMS)

### Headset Integration (enhanced)
- Native headset SDK integration (easier in Electron than browser):
  - Jabra Direct SDK (native Node.js bindings)
  - Poly Hub integration
  - EPOS Connect
- More reliable button mapping than browser-only approach
- Busylight control

### Audio
- System audio device management (select input/output/ringtone device independently)
- Acoustic echo cancellation tuning
- Noise suppression
- Ring on all devices / ring on selected device

### Updates
- Auto-update mechanism (Electron autoUpdater)
- MSP-controlled update channel (beta, stable)
- Rollback capability if update causes issues
- Version pinning per tenant (if needed)

### Distribution
- Direct download from platform portal
- MSP-branded installer (custom name, icon, splash screen)
- Enterprise deployment: MSI installer (Windows), PKG (macOS), for SCCM/Intune/Jamf deployment
- Automatic enrollment: app authenticates, discovers tenant, pulls config

### Build Phasing
- **Phase 1**: web client in browser (fully functional, no Electron needed)
- **Phase 2**: Electron wrapper with native integrations (tray, notifications, shortcuts, headset)
- Web client and desktop app share 95%+ of codebase (Electron just wraps it)

---

## 54. Desk Phone XML Apps (Yealink, Polycom, Cisco)

On-screen apps that run directly on the desk phone's display, providing visual features beyond basic calling.

### Architecture
- **XML browser service**: FastAPI endpoint serving phone-native XML/HTML pages
  - Yealink: XML browser (proprietary Yealink XML format)
  - Polycom: Microbrowser + Web App Platform (XHTML)
  - Cisco: Cisco IP Phone XML Services
- **Phone ↔ Platform communication**:
  - Phone requests XML pages via HTTP(S) from platform API
  - Platform authenticates phone by MAC address + extension credentials (HTTP digest or token in URL)
  - Pages are tenant-scoped (phone only sees data for its tenant)
- **Action URLs / webhook callbacks**: phone sends button press events back to platform API
  - Yealink Action URLs: events on incoming call, call answered, call ended, DND toggle, etc.
  - Platform can trigger phone actions: open URL, display notification, play tone

### Apps Available on Phone Screen

#### Company Directory
- Searchable tenant directory rendered on phone display
- Search by name (first/last), extension, department
- Pagination for large directories
- Tap-to-dial from directory results
- Favorites / speed dial list (per user)
- Photo display (models with color screen)

#### Visual Voicemail
- List of voicemails with caller ID, time, duration on phone screen
- Play/delete voicemail directly from phone (no need to dial into mailbox)
- Mark as read/unread
- AI transcription preview on screen (first ~100 chars)
- Urgency indicator (AI-flagged urgent voicemails highlighted)

#### Call History (Enhanced)
- Recent calls: missed, received, placed — on phone display
- Caller name from directory/CRM lookup (not just number)
- Tap-to-call from history
- Date/time grouping
- Call duration shown

#### BLF / Parking Panel
- Visual parking lot display (which slots are occupied, by whom)
- Tap to park / tap to retrieve from visual panel
- BLF overview: extension status grid (available/ringing/in-call/DND)
- Tap-to-dial or tap-to-transfer from BLF panel

#### Queue Agent Dashboard (Phone Screen)
- Agent login/logout from phone screen
- Current queue stats: calls waiting, longest wait time
- Agent status toggle: available, break, wrap-up
- Missed/abandoned call count for today
- Simplified version of the web queue dashboard

#### Weather / Clock / Info Widgets
- Idle-screen widgets (models that support screen saver apps)
- Company logo display on idle screen
- Custom tenant-branded idle screen

#### Phone-Based Settings
- DND toggle with visual confirmation
- Call forwarding configuration (forward to number, to voicemail)
- Presence status change
- Hotdesking login/logout from phone screen (enter extension + PIN)

### Action URL Integration (Yealink-Specific)
- **Events captured from phone → platform**:
  - Incoming call (caller ID, called number)
  - Call answered, call ended (duration)
  - Transfer initiated
  - DND on/off
  - Hold/resume
  - Phone boot/reboot
- **Platform actions → phone**:
  - Push notification to phone screen ("New voicemail from John Smith")
  - Open XML page on phone (remote trigger)
  - Display alert message
  - Trigger phone reboot (remote management)
- **CRM/ConnectWise integration via Action URLs**:
  - Incoming call → Action URL fires → platform does CRM lookup → pushes contact name to phone display
  - Provides screen pop even on phones without a thick client

### Phone Model Support
- **Yealink**: T3x, T4x, T5x series (XML browser + Action URLs)
- **Polycom/Poly**: VVX series (Microbrowser, XHTML)
- **Cisco**: 7800, 8800 series (Cisco XML Services)
- **Sangoma P-series**: handled by DPMA Replacement (Section 4)
- **Grandstream**: GRP/GXP series (XML browser, similar to Yealink)
- **Fanvil**: X series (XML browser support)
- Feature matrix per manufacturer (which apps work on which models) maintained in docs

### Per-Tenant Customization
- Enable/disable specific phone apps per tenant
- Custom directory fields (show department, location, or custom fields)
- Custom idle screen branding (logo, colors, message)
- Admin can preview phone app rendering in web UI before pushing to phones

---

## 55. AI Voice Agent System

Full-featured interactive AI voice agent — replicating and extending the capabilities of the Asterisk-AI-Voice-Agent project, adapted for the FreeSWITCH-based multi-tenant platform.

### Purpose
AI-powered voice agents that can have natural, two-way conversations with callers, understand intent, take actions (transfer, schedule, look up info), and hand off to human agents when needed. This goes beyond the AI Auto-Attendant (Section 17) — these are fully conversational agents, not just intent-routing bots.

### Architecture

```
┌───────────────────────────────────────────────────────────────────┐
│  Caller → FreeSWITCH → ESL Event → AI Voice Agent Engine         │
│                                                                   │
│  ┌─────────────┐    ┌──────────────────────────────────────────┐  │
│  │ Audio       │    │ AI Voice Agent Engine (Python)            │  │
│  │ Transport   │    │                                          │  │
│  │             │◄──►│  Session Manager (per-call state)        │  │
│  │ WebSocket   │    │  Conversation Coordinator (turn-taking)  │  │
│  │ or RTP      │    │  Audio Gating (VAD, barge-in detection)  │  │
│  │ stream      │    │  Pipeline Orchestrator (STT→LLM→TTS)    │  │
│  │             │    │  Tool Registry & Executor                │  │
│  │             │    │  Streaming Playback Manager              │  │
│  └─────────────┘    └──────────┬───────────────────────────────┘  │
│                                │                                  │
│                     ┌──────────▼───────────────────────────────┐  │
│                     │  Provider Layer (pluggable)              │  │
│                     │                                          │  │
│                     │  Monolithic Providers:                   │  │
│                     │  • OpenAI Realtime (GPT-4o voice)        │  │
│                     │  • Deepgram Voice Agent                  │  │
│                     │  • Google Gemini Live                    │  │
│                     │  • ElevenLabs Conversational AI          │  │
│                     │                                          │  │
│                     │  Modular Pipeline:                       │  │
│                     │  • STT: Vosk, Sherpa, Deepgram, Whisper  │  │
│                     │  • LLM: OpenAI, Anthropic, Ollama, local │  │
│                     │  • TTS: Piper, Kokoro, ElevenLabs, gTTS │  │
│                     └──────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────┘
```

### Provider Architecture
Two modes of operation (configurable per agent context):

#### Monolithic Providers
- **OpenAI Realtime**: WebSocket-based, STT+LLM+TTS in one stream, ultra-low latency
- **Deepgram Voice Agent**: WebSocket-based, with "think" stage for complex reasoning
- **Google Gemini Live**: multimodal (can process audio natively), ExternalMedia RTP
- **ElevenLabs Conversational AI**: premium voice quality, natural prosody
- Each provider handles the full pipeline internally
- Provider selection configurable per agent context (tenant can choose)

#### Modular Pipeline (Mix-and-Match)
- **STT backends** (choose one per agent):
  - Vosk (offline, self-hosted, good accuracy)
  - Sherpa-ONNX (low-latency streaming, ONNX runtime)
  - Deepgram (cloud, high accuracy, streaming)
  - OpenAI Whisper (self-hosted, batch or near-real-time)
  - Kroko ASR (hosted or on-premise, 12+ languages)
- **LLM backends** (choose one per agent):
  - OpenAI GPT-4o / GPT-4 (cloud)
  - Anthropic Claude (cloud)
  - Ollama (self-hosted, any open model)
  - llama.cpp (self-hosted, quantized models)
- **TTS backends** (choose one per agent):
  - Piper (offline, fast, multiple voices)
  - Kokoro (high-quality neural, natural prosody)
  - ElevenLabs (cloud, premium voices)
  - OpenAI TTS (cloud)
  - Google Cloud TTS (cloud)
- Each component is independently swappable — choose best-of-breed per use case

### Conversation Management

#### Session State
- Per-call session tracking: caller info, agent context, conversation history, tool call results
- Transcript maintained throughout call (speaker-diarized)
- Session state available to tools (agent knows what was discussed)

#### Turn-Taking & Barge-In
- **VAD (Voice Activity Detection)**: WebRTC VAD + energy threshold for speech detection
- **Barge-in handling**: caller interrupts AI mid-speech → AI stops talking, listens
  - Configurable barge-in sensitivity (aggressive, normal, conservative)
  - Protection window after AI starts speaking (prevents false barge-in from echo)
- **Silence detection**: configurable timeout for caller silence before AI prompts
- **Audio gating**: prevents AI from hearing its own playback audio as speech

#### Streaming Playback
- **Adaptive streaming**: TTS audio streamed to caller with jitter buffering
- **Chunk management**: 20ms audio frames, synchronized with FreeSWITCH
- **Fallback**: if streaming fails, fall back to file-based playback (save audio → play file)

### Tool Calling System
AI agents can take actions during conversation via function calling:

#### Built-In Telephony Tools
- **Transfer**: transfer caller to extension, queue, ring group, or external number
  - Blind transfer or attended transfer (AI introduces caller to agent)
- **Cancel Transfer**: cancel an in-progress transfer if caller changes mind
- **Voicemail**: route caller to specific extension's voicemail
- **Hangup**: end call gracefully (AI says goodbye, then hangs up)
- **Hold**: place caller on hold with MOH, resume when ready
- **Conference**: add a third party to the call

#### Built-In Business Tools
- **Email Summary**: AI sends call summary to configured email after call ends
- **Request Transcript**: caller asks for transcript, AI emails it to provided address
- **Schedule Appointment**: integrate with calendar API to book appointments
- **Look Up Information**: query knowledge base, FAQ, or external API for answers
- **Create Ticket**: auto-create ConnectWise/CRM ticket from call (with AI-extracted details)

#### Custom Tool Framework
- Tenant-configurable custom tools via:
  - **Webhook tools**: AI calls a webhook URL with parameters, gets response, uses it in conversation
  - **MCP tools** (Model Context Protocol): external tool servers for extensibility
  - **Database query tools**: AI queries tenant-specific data (e.g., order status lookup)
- Tool definitions: name, description, parameters (JSON schema), endpoint/handler
- Tool results fed back to LLM for natural response ("I found your order — it shipped yesterday.")

### Agent Contexts (Per-Tenant Configuration)
Each tenant can define multiple AI agent personalities/behaviors:

- **Context name**: e.g., "main-receptionist", "after-hours", "billing-support"
- **System prompt**: defines personality, instructions, knowledge, constraints
  - e.g., "You are the receptionist for Acme Corp. You are friendly and professional. You can transfer callers to Sales (ext 200), Support (ext 300), or take a message."
- **Greeting**: initial message the AI speaks when call connects
  - e.g., "Thank you for calling Acme Corp. How can I help you today?"
- **Provider/pipeline selection**: which AI provider or pipeline to use for this context
- **Available tools**: which tools this agent context can use (e.g., receptionist can transfer but not access billing)
- **Voice selection**: TTS voice for this context (e.g., professional female voice for receptionist)
- **Language**: primary language for STT and TTS
- **Escalation rules**: when to transfer to human (e.g., "if caller asks for a human 3 times", "if sentiment is negative for >30 seconds")
- **Business hours awareness**: context can change based on time of day
- **Knowledge base**: per-context FAQ or knowledge base the LLM can reference

### Call Routing Integration
- **IVR replacement**: AI agent as the first contact instead of traditional IVR
  - DID → AI Voice Agent (context: main-receptionist) → AI routes based on conversation
- **Queue front-end**: AI agent handles initial triage, then transfers to appropriate queue
  - Passes conversation context to human agent ("AI summary: caller needs help with billing, account #12345")
- **After-hours agent**: AI handles calls outside business hours
  - Takes messages, creates tickets, provides basic info, schedules callbacks
- **Overflow agent**: when all agents are busy, AI takes the call temporarily
  - Gathers initial info, creates ticket, promises callback
- **Per-DID routing**: different DIDs can route to different AI contexts
- **FreeSWITCH integration**: ESL commands to bridge caller to AI engine, receive events for call control

### Web Admin Interface
- **Agent builder UI**: visual interface for creating/editing AI agent contexts
  - System prompt editor with syntax highlighting
  - Tool selection checkboxes
  - Voice preview (listen to sample with selected TTS voice)
  - Greeting editor with audio preview
  - Test chat interface (text-based test of the AI agent before going live)
- **Conversation log viewer**: review past AI agent conversations
  - Full transcript with speaker labels
  - Tool calls logged with parameters and results
  - Audio playback of the original call
  - Latency metrics per turn (STT time, LLM time, TTS time)
- **Performance dashboard**:
  - Calls handled by AI vs. transferred to human
  - Average conversation length
  - Common intents/topics (AI-extracted)
  - Tool usage stats
  - STT→LLM→TTS latency breakdown (p50, p95, p99)
  - Provider cost tracking
- **Model hot-swap**: change STT/LLM/TTS provider on the fly without restarting service

### API Endpoints
- `POST /api/v1/ai-agents/contexts` — create agent context
- `GET /api/v1/ai-agents/contexts` — list contexts (per tenant)
- `PUT /api/v1/ai-agents/contexts/{id}` — update context (prompt, tools, voice, etc.)
- `DELETE /api/v1/ai-agents/contexts/{id}` — delete context
- `POST /api/v1/ai-agents/contexts/{id}/test` — test agent context (text-based, returns AI response)
- `GET /api/v1/ai-agents/conversations` — list past AI conversations (per tenant)
- `GET /api/v1/ai-agents/conversations/{id}` — full transcript + tool calls + metrics
- `GET /api/v1/ai-agents/conversations/{id}/audio` — audio playback URL
- `GET /api/v1/ai-agents/stats` — performance metrics (calls, latency, transfer rate)
- `POST /api/v1/ai-agents/tools` — register custom tool
- `GET /api/v1/ai-agents/providers` — list available STT/LLM/TTS providers and their status
- `POST /api/v1/ai-agents/providers/test` — test provider connectivity

### Monitoring & Metrics (Prometheus)
- `ai_agent_active_calls` — current active AI agent calls
- `ai_agent_stt_latency_seconds` — STT processing time (histogram)
- `ai_agent_llm_latency_seconds` — LLM response time (histogram)
- `ai_agent_tts_latency_seconds` — TTS synthesis time (histogram)
- `ai_agent_turn_response_seconds` — full turn latency (caller speaks → AI responds)
- `ai_agent_barge_in_count` — barge-in events
- `ai_agent_tool_calls_total` — tool call count by tool name and result
- `ai_agent_transfer_to_human_total` — calls escalated to human agent
- `ai_agent_call_duration_seconds` — AI-handled call duration (histogram)
- `ai_agent_provider_errors_total` — provider failures by provider name

### AI Cost Management
- Per-tenant AI Voice Agent enable/disable
- Per-tenant provider selection (tenant A uses OpenAI, tenant B uses local)
- Per-tenant usage metering: AI agent minutes, STT minutes, LLM tokens, TTS characters
- Cost allocation per tenant (pass-through or included in plan)
- Usage caps: configurable max AI agent minutes per tenant per month
- Cost dashboard: per-tenant, per-provider cost breakdown

### Multi-Tenant Isolation
- Each tenant's AI agent contexts are fully isolated
- Tenant A's custom tools cannot be accessed by tenant B
- Conversation transcripts are tenant-scoped (RLS)
- Provider API keys can be per-tenant (tenant brings their own OpenAI key) or platform-shared
- Rate limiting per tenant to prevent one tenant from consuming all AI capacity

---

## 56. Testing Strategy

### Testing Terminology
Yes, you're using the right terms. Here's the hierarchy:
- **Unit tests**: test individual functions/methods in isolation
- **Integration tests**: test how components work together (API + database, event router + FreeSWITCH)
- **Component tests**: test a single service end-to-end in isolation (API layer with mocked dependencies)
- **System tests / E2E tests**: test the entire platform as a whole (make a real call, verify CDR, recording, billing all work)

### Unit Tests

#### API Layer (Python / FastAPI)
- Test every endpoint handler in isolation (mocked DB, mocked services)
- Test RBAC/permission checks (can tenant A access tenant B's data? → no)
- Test input validation (malformed requests, missing fields, invalid types)
- Test business logic functions (call routing decisions, rate calculations, 10DLC validation)
- Test tenant isolation at the query level (RLS filters applied correctly)
- Framework: **pytest** + **pytest-asyncio**
- Coverage target: **90%+ on business logic**, 80%+ overall

#### Rust Services
- Test SIP message parsing and construction
- Test DPMA protocol message handling
- Test parking state machine transitions
- Test E911 PIDF-LO generation
- Test SMS provider abstraction (ClearlyIP adapter, Twilio adapter)
- Test event routing logic
- Framework: **Rust built-in test framework** + **tokio::test** for async
- Coverage target: **90%+** (Rust makes untested code more dangerous)

#### Web Client (React / TypeScript)
- Test React components in isolation (rendering, user interaction, state changes)
- Test hooks and state management logic
- Test WebRTC call state machine
- Test SMS conversation rendering and interaction
- Test form validation (extension creation, IVR builder, etc.)
- Framework: **Vitest** + **React Testing Library**
- Coverage target: **80%+**

#### Mobile Client (Flutter / Dart)
- Test widget rendering and interaction
- Test call state management
- Test push notification handling logic
- Test offline/online transition behavior
- Test SMS conversation sync logic
- Framework: **flutter_test** + **mockito**
- Coverage target: **80%+**

### Integration Tests

#### API ↔ Database
- Test real PostgreSQL queries (not mocked)
- Test RLS enforcement (connect as tenant A, verify can't read tenant B's rows)
- Test migrations (up and down)
- Test concurrent access patterns (two agents claim same SMS conversation)
- Run against: **PostgreSQL in Docker** (testcontainers)

#### API ↔ FreeSWITCH (ESL)
- Test ESL command sending and event parsing
- Test call origination, bridging, parking, transfer via ESL
- Test dynamic config loading (extension registration, routing)
- Run against: **FreeSWITCH in Docker** (real instance, test tenant)

#### API ↔ SMS Providers
- Test ClearlyIP API integration (send, receive webhook, status callback)
- Test Twilio API integration (send, receive webhook, status callback)
- Test provider failover (primary fails → secondary picks up)
- Test opt-out keyword handling
- Run against: **provider sandbox/test environments** (Twilio test credentials, ClearlyIP test mode)

#### API ↔ Redis
- Test pub/sub event delivery
- Test caching behavior (cache hit, miss, invalidation)
- Test parking slot state in Redis
- Run against: **Redis in Docker**

#### API ↔ Object Storage
- Test recording upload/download/delete
- Test per-tenant path isolation
- Test retention policy enforcement
- Run against: **MinIO in Docker**

#### Rust Services ↔ FreeSWITCH
- Test SIP proxy forwarding and response handling
- Test ESL event consumption and routing
- Run against: **FreeSWITCH in Docker**

### Component Tests

#### API Layer (isolated, full service)
- Stand up the FastAPI service with real DB but mocked external services
- Test complete request/response cycles through all middleware (auth, tenant scoping, rate limiting)
- Test error handling (DB down, FreeSWITCH unreachable, SMS provider timeout)
- Test WebSocket connections (subscribe to events, verify delivery)
- Framework: **pytest** + **httpx** (async test client)

#### Rust SIP Proxy (isolated)
- Send real SIP packets, verify correct routing decisions
- Test with multiple simulated endpoints (SIPp or pjsua)
- Test topology hiding, header manipulation, DoS protection
- Framework: **Rust tests** + **SIPp** for SIP traffic generation

### System Tests (End-to-End)

#### Call Flow E2E Tests
- **Basic call**: extension A calls extension B → verify CDR, verify recording, verify billing
- **IVR flow**: call DID → IVR answers → press 1 → rings sales group → agent answers
- **Queue flow**: call DID → enters queue → hear position announcement → agent answers → verify queue stats
- **Parking flow**: call in → agent parks → verify BLF → retrieve from slot → verify CDR
- **Transfer flow**: blind transfer, attended transfer, verify CDR chain
- **Conference flow**: create conference → multiple participants join → verify recording
- **Voicemail flow**: call extension → no answer → leave voicemail → verify MWI, email, transcription
- **E911 flow**: dial 933 (test line) → verify PIDF-LO/Geolocation header sent correctly
- **Fax flow**: send fax → verify T.38 negotiation → verify fax-to-email delivery

#### SMS E2E Tests
- **Personal SMS**: send SMS from web client → verify delivery → receive reply → verify conversation threading
- **Queue SMS**: inbound SMS to queue DID → verify assignment → agent responds → verify delivery
- **Opt-out flow**: customer texts STOP → verify auto-reply → verify blocked from further messages → texts START → verify re-subscribe
- **MMS**: send image → verify delivery and rendering in client
- **Auto-responder**: inbound to DID with auto-reply configured → verify auto-reply sent

#### Multi-Tenant Isolation E2E
- Create two tenants → verify tenant A cannot access tenant B's:
  - Extensions, CDR, recordings, voicemail, SMS conversations, DIDs, config
- Verify tenant A's calls don't appear in tenant B's CDR
- Verify tenant A's recording URLs return 403 for tenant B's API key

#### Auth E2E Tests
- Entra ID SSO login flow (browser automation)
- Google SSO login flow (browser automation)
- Traditional login → MFA TOTP challenge → success
- Traditional login → wrong MFA code → reject
- Failed login lockout after X attempts
- API key authentication and scoping
- Role-based access (user tries admin endpoint → 403)

#### Encryption Enforcement E2E
- **Client/extension enforcement:**
  - Attempt SIP registration over UDP → verify rejected
  - Attempt SIP registration over TCP (no TLS) → verify rejected
  - Attempt SIP registration over TLS → verify accepted
  - Attempt RTP (unencrypted) media stream from extension → verify rejected
  - Attempt SRTP media stream from extension → verify accepted
- **Trunk encryption (preferred, not mandatory):**
  - Connect trunk via TLS → verify accepted, dashboard shows green/encrypted
  - Connect trunk via UDP → verify accepted with fallback, dashboard shows amber/warning
  - Verify security warning is generated when trunk is unencrypted
- Verify TLS 1.1 and below are rejected for all connections
- Verify all call recordings are encrypted at rest
- Verify all inter-service communication is encrypted (API ↔ FreeSWITCH, API ↔ Redis, etc.)

#### Performance / Load Tests
- Concurrent call capacity: ramp up to target concurrent calls, measure quality
- API throughput: requests per second under load, p50/p95/p99 latency
- SMS throughput: messages per second send/receive
- WebSocket connection scaling: 1000+ concurrent WebSocket clients
- Database performance under load (query latency, connection pool behavior)
- Framework: **Locust** (API load), **SIPp** (SIP/RTP load), **k6** (WebSocket load)

#### Chaos / Resilience Tests
- Kill FreeSWITCH → verify active calls handled gracefully, new calls fail cleanly, service recovers on restart
- Kill database → verify API returns appropriate errors, recovers when DB returns
- Kill Redis → verify fallback behavior (cache miss, pubsub reconnect)
- Kill SMS provider → verify failover to secondary
- Network partition between API and FreeSWITCH → verify timeout handling
- Disk full on recording storage → verify graceful failure, alert generated

### CI/CD Pipeline Integration
- **Pre-commit**: linting, formatting, type checking (all languages)
- **PR checks (must pass to merge)**:
  - Unit tests (all languages, parallelized)
  - Integration tests (Docker Compose test environment spun up)
  - Security scans (SAST, SCA — see Section 11)
  - Coverage check (fail if below threshold)
- **Nightly**:
  - Full system E2E test suite
  - Performance/load tests
  - DAST security scans
  - Container image scans
- **Pre-release**:
  - Full E2E suite
  - Chaos/resilience tests
  - Manual QA sign-off checklist

### Test Environment
- **Docker Compose test stack**: full platform in containers (FreeSWITCH, PostgreSQL, Redis, MinIO, API, Rust services)
- Spun up and torn down per test run (clean state)
- Seed data: pre-created test tenants, extensions, DIDs, configurations
- SIPp for SIP traffic generation (simulated phones)
- Test SIP provider accounts (Twilio test credentials, ClearlyIP sandbox)
- Separate from staging and production

---

## Architecture Reference

```
┌──────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                              │
├──────────────┬──────────────┬─────────────────┬──────────────────┤
│ Web Admin    │ Web Softphone│  Mobile Clients  │ Desk Phone Apps  │
│ (React/TS)   │ (React/TS    │  (Flutter/Dart)  │ (XML Browser)    │
│              │  + WebRTC)   │  iOS CallKit     │ Yealink/Polycom  │
│ Tenant Admin │              │  Android CS      │ Cisco/Grandstream│
│ MSP Admin    │  Verto/SIP   │  Push notifs     │ Action URLs      │
│ AI Agent UI  │              │                  │ Visual VM/Dir    │
└──────┬───────┴──────┬───────┴──────────┬───────┴─────────────────┘
       │              │                  │
       │         Auth: Entra ID / Google / Email+MFA
       │              │                  │
┌──────▼──────────────▼──────────────────▼─────────────────────────┐
│                         API LAYER                                 │
│              FastAPI (Python) — tenant-aware                      │
│              JWT auth — RBAC — rate limiting                      │
│              WebSocket for realtime events                        │
│              REST API + OpenAPI docs                              │
│              Webhook engine                                       │
│              Phone XML app server (Yealink/Polycom/Cisco XML)    │
└──────┬───────────────────────────────────┬───────────────────────┘
       │                                   │
┌──────▼──────────┐  ┌───────────────────┐ │ ┌────────▼────────────┐
│   DATA LAYER    │  │  EXTERNAL         │ │ │   RUST SERVICES     │
│                 │  │  INTEGRATIONS     │ │ │                     │
│ PostgreSQL      │  │                   │ │ │ SIP Proxy/LB        │
│ (RLS per tenant)│  │ ClearlyIP API ◄───┤ │ │ DPMA Replacement    │
│                 │  │ Twilio API    ◄───┤ │ │ RTP Relay           │
│ Redis           │  │                   │ │ │ Event Router        │
│ (cache + pubsub)│  │ ConnectWise PSA◄──┤ │ │ (ESL ↔ DB ↔ API)   │
│                 │  │ CRM APIs     ◄───┤ │ │ Parking Manager     │
│ MinIO/S3        │  │ (SF/HubSpot/Zoho)│ │ │ E911 Handler        │
│ (recordings,    │  │                   │ │ │ SMS Gateway         │
│  voicemail,     │  │ Inbound webhooks  │ │ │ (provider abstract) │
│  fax)           │  │ Status callbacks  │ │ │                     │
│                 │  │ Delivery receipts │ │ │                     │
│ Prometheus      │  └───────────────────┘ │ └────────┬────────────┘
│ (metrics/TSDB)  │                        │          │
│                 │                        │ ┌────────▼────────────┐
│ cAdvisor        │                        │ │   MEDIA LAYER       │
│ Node Exporter   │                        │ │                     │
│ (infra metrics) │                        │ │ FreeSWITCH          │
└─────────────────┘                        │ │ (ESL-controlled)    │
                                           │ │ Multi-tenant domains│
                                           │ │ WebRTC/Verto        │
┌──────────────────────────────────────────┘ │ SIP endpoint hdlg   │
│                                            │ Codec transcoding   │
│  ┌─────────────────────────────────────┐   │ Conference bridges  │
│  │   AI VOICE AGENT ENGINE (Python)    │   │ T.38 fax            │
│  │                                     │   └─────────────────────┘
│  │ Session Manager (per-call state)    │
│  │ Conversation Coordinator            │
│  │ Audio Gating (VAD, barge-in)        │
│  │ Pipeline Orchestrator (STT→LLM→TTS)│
│  │ Tool Registry & Executor            │
│  │ Streaming Playback Manager          │
│  │                                     │
│  │ Providers:                          │
│  │  OpenAI Realtime | Deepgram         │
│  │  Google Gemini   | ElevenLabs       │
│  │  Local Pipeline (Vosk/Piper/Ollama) │
│  └─────────────────────────────────────┘
```
