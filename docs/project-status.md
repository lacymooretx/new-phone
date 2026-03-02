# New Phone Platform — Project Status

> Last updated: 2026-02-27

---

## What's Built

### Backend (API) — FastAPI/Python
- **174 Python files**, ~18,600 lines
- **26 API routers** covering all telephony CRUD + auth + admin
- Multi-tenant PostgreSQL with Row-Level Security (2-user pattern)
- JWT auth with refresh token rotation, TOTP MFA, 5-role RBAC
- FreeSWITCH ESL integration for health checks
- Redis for caching/pubsub
- MinIO/S3 for object storage (recordings, voicemail, audio prompts)
- Structured logging, RFC 7807 error responses
- 19 backend tests passing
- Docker Compose with 7 services (api, postgres, redis, freeswitch, minio, web, nginx)

### Frontend (Web UI) — React/TypeScript/Vite
- **152 source files**, ~15,400 lines
- **25 page modules** (each with page + form + columns files)
- **23 API hook files** with TanStack Query (query keys factory pattern)
- **36 tests** (jwt, api-client, auth-store, rbac-constants, csv-export)

#### Pages & Features
| Page | CRUD | Bulk Delete | CSV Export | Filters | Error State |
|------|------|-------------|------------|---------|-------------|
| Dashboard | - | - | - | - | Yes |
| Extensions | Full | Yes | Yes | Search | Yes |
| Follow-Me | Edit | - | - | - | - |
| Ring Groups | Full | Yes | Yes | Search | Yes |
| Queues | Full | Yes | Yes | Search | Yes |
| IVR Menus | Full | Yes | Yes | Search | Yes |
| Conferences | Full | Yes | Yes | Search | Yes |
| Paging | Full | Yes | Yes | Search | Yes |
| SIP Trunks | Full | Yes | Yes | Search | Yes |
| DIDs | Full | Yes | Yes | Search | Yes |
| Inbound Routes | Full | Yes | Yes | Search | Yes |
| Outbound Routes | Full | Yes | Yes | Search | Yes |
| Users | Full | Yes | Yes | Search | Yes |
| CDRs | Read | - | - | Date/Direction | Yes |
| Recordings | Read/Delete | - | Yes | Date Range | Yes |
| Voicemail | Full | - | - | - | - |
| Audio Prompts | Full | - | Yes | Search | Yes |
| Time Conditions | Full | Yes | Yes | Search | Yes |
| Holiday Calendars | Full | Yes | Yes | Search | Yes |
| Caller ID Rules | Full | Yes | Yes | Search | Yes |
| Audit Logs | Read | - | - | Date/Action | - |
| Tenants (MSP) | Full | Yes | Yes | Search | Yes |
| Tenant Settings | Edit | - | - | - | - |
| Profile | Edit | - | - | - | - |
| Login | - | - | - | - | - |
| Forgot Password | - | - | - | - | - |
| Reset Password | - | - | - | - | - |

#### Shared Components
- DataTable (sort, filter, paginate, column visibility, row selection, export, bulk delete)
- PageHeader, StatusBadge, AudioPlayer, EmptyState, ErrorBoundary
- ConfirmDialog (all destructive actions)
- DestinationPicker (extension/ring-group/queue/IVR/voicemail selector)
- Command Palette (Cmd+K) with keyboard shortcuts dialog (Cmd+?)
- Dark mode toggle (next-themes)
- Skip-to-content accessibility link
- Unsaved changes protection (beforeunload on all CRUD dialogs)

#### Auth & UX
- JWT login with refresh token rotation
- MFA challenge flow (TOTP)
- Password change + MFA setup/disable from profile
- Forgot/reset password flow
- Role-based sidebar navigation (MSP vs tenant views)
- Tenant picker for MSP admins
- Auth redirect (authenticated users can't visit login pages)
- API error banners on all pages (not just empty state)
- User-friendly error messages for common HTTP status codes

#### Build Quality
- TypeScript strict mode — 0 errors
- ESLint — 0 errors (43 warnings, all pre-existing/non-blocking)
- Bundle optimized with manual chunks (vendor-react, vendor-tanstack, vendor-ui)
- Index chunk: 366KB (optimized from 549KB)
- All routes lazy-loaded with Suspense + loading spinner

---

## Phases Completed: 28

| Phase | Focus |
|-------|-------|
| 1 | Foundation Stack (API, DB, Auth, FreeSWITCH) |
| 2 | Core Telephony Data Layer (Extensions, Ring Groups, Trunks, DIDs, Routes) |
| 3 | FreeSWITCH Integration (Dialplan, SIP profiles, ESL commands) |
| 4 | CDR, Call Recording & Object Storage |
| 5 | Voicemail, Time Conditions & IVR/Auto-Attendant |
| 6 | Call Queues (ACD) |
| 7 | Conference Bridges, Paging/Intercom & Call Pickup |
| 8 | Audit Logging, Follow Me & Telephony Polish |
| 9 | MOH Wiring, Caller ID Rules & Time Condition Enhancements |
| 10 | Web Client MVP (all pages, auth, routing, 12 tests) |
| 11 | Remaining Telephony Admin Pages |
| 12 | Complex Sub-Forms, API Type Fixes & Code Splitting |
| 13 | Follow-Me Fix, Queue Stats Hooks & Dashboard Enhancement |
| 14 | Voicemail Box CRUD, Recording Delete & Dashboard Analytics |
| 15 | Dark Mode, Command Palette & Table Search |
| 16 | Tenant Management CRUD & Confirmation Dialogs |
| 17 | Profile Page, 404, Session UX & Nav Cleanup |
| 18 | Destination Pickers, Search UX & Error Boundary |
| 19 | Form Completeness, Accessibility & Dark Mode |
| 20 | DataTable UX, Dialog Safety & Duplicate Actions |
| 21 | Empty States, Responsive Forms, Sortable Columns & Dashboard Polish |
| 22 | Bulk Operations, CSV Export, Mobile Polish & Form Placeholders |
| 23 | Call Forwarding, E911, Recording Filters & Agent Status |
| 24 | Password Change, MFA Management, Outbound CID & Loading Spinner |
| 25 | Password Reset, Keyboard Shortcuts & Login Polish |
| 26 | Login Redirect, Error Handling, Form Protection & Help Text |
| 27 | Test Coverage (12→36), Bundle Optimization, Accessibility |
| 28 | Error Handling, Dialog State, Voicemail Safety & DataTable Polish |

---

## What's NOT Built Yet (from feature-plan.md)

The feature plan has **56 sections**. Phases 1-9 built the backend for sections 1-2 (core telephony) plus parts of sections 9 (dashboards) and 11 (security). Phases 10-28 built the web admin UI.

### Remaining major areas (grouped by effort):

#### Tier 1 — Large standalone systems (each is a multi-phase project)
| # | Feature Plan Section | Description |
|---|---------------------|-------------|
| 3 | SMS & Messaging Subsystem | Full SMS/MMS gateway, conversation threading, shared inboxes, 10DLC compliance, queue routing |
| 4 | DPMA Replacement | Rust service for Sangoma P-series phone integration |
| 5 | Web Client — WebRTC softphone | In-browser calling via Verto/WebRTC (the admin UI exists but no softphone) |
| 6 | Mobile Client | Flutter/Dart app with iOS CallKit, Android ConnectionService |
| 55 | AI Voice Agent System | Conversational AI with STT/LLM/TTS pipeline, tool calling |
| 52 | Desktop Application | Electron wrapper for the web client |

#### Tier 2 — Medium features (1-3 phases each)
| # | Feature Plan Section | Description |
|---|---------------------|-------------|
| 7 | Phone Provisioning | Auto-provisioning for Yealink/Polycom/Cisco |
| 8 | Integrations | ConnectWise PSA, CRM, MS Teams, Slack, Google |
| 14 | DID Ordering & Number Porting | Automated number purchasing + LNP |
| 15 | Migration & Import Tools | FreePBX/3CX import, bulk CSV, config templates |
| 16 | Receptionist Console | Drag-and-drop operator panel |
| 17 | AI/LLM Features | Transcription, summarization, sentiment, auto-attendant |
| 20 | Developer Portal & Webhooks | API key management, webhook subscriptions |
| 24 | Call Center Quality Management | Score cards, screen recording, QA workflows |
| 46 | Workforce Management | Shift scheduling, forecasting, adherence |
| 54 | Desk Phone XML Apps | On-phone apps (directory, visual VM, parking panel) |

#### Tier 3 — Smaller features / enhancements (< 1 phase each)
| # | Feature Plan Section | Description |
|---|---------------------|-------------|
| 10 | Billing & Usage Metering | Usage tracking, tenant billing |
| 13 | White-Label & Branding | Custom logos, colors, domains per tenant |
| 21 | Multi-Channel Expansion | Video, fax, social media channels |
| 22 | Tenant Lifecycle Management | Trial → active → suspended → archived |
| 23 | Mass Notification System | Blast calls/SMS to groups |
| 25 | Hospitality Module | Wake-up calls, room status, housekeeping |
| 26 | Robocall & Spam Filtering | STIR/SHAKEN, reputation scoring |
| 27 | NAT Traversal / STUN / TURN | Media relay infrastructure |
| 28 | SIP Debugging Tools | Packet capture, call trace, ladder diagrams |
| 29 | Business Continuity / Failover | Automatic failover between sites |
| 30 | Platform Status Page | Public status page with incident management |
| 31 | Post-Call Surveys | IVR-based CSAT/NPS collection |
| 32 | Scheduled Callbacks from Queues | Callback queue management |
| 33 | Custom Messages on Hold | Per-queue, per-time MOH management |
| 34 | Wrap-Up / Disposition Codes | Post-call categorization |
| 35 | Localization / i18n | Multi-language UI and prompts |
| 36 | Plugin / Marketplace Architecture | Extension system for third-party modules |
| 37 | Inter-Tenant Calling | Cross-tenant routing |
| 38 | Documentation Portal | User/admin/API docs site |
| 39 | Changelog & Release Notes | Version tracking, upgrade notes |
| 40 | Phone Compatibility Testing | Device certification matrix |
| 41 | Headset Integration | Jabra, Poly, Plantronics button control |
| 42 | TCPA Compliance & DNC | Consent management, do-not-call enforcement |
| 43 | Boss/Admin (Executive/Assistant) | Secretary filtering, shared line appearance |
| 44 | Multi-Site / Multi-Timezone | Per-tenant location management |
| 45 | AI Compliance Monitoring | Keyword detection, policy enforcement |
| 47 | Click-to-Call Browser Extension | Chrome/Edge extension |
| 48 | Emergency & Physical Security | Panic button, E911 enhancements |
| 49 | CDR Enrichment from CRM | Contact matching, deal attribution |
| 50 | Call Recording Storage Tiering | Hot/warm/cold storage lifecycle |
| 51 | Camp-On / Callback on Busy | Auto-callback when extension becomes free |
| 56 | Testing Strategy | Full test framework (unit, integration, E2E, perf, chaos) |

---

## How Many Phases Are Left?

**For the web admin UI specifically**: The admin UI is essentially feature-complete for the current backend API surface. Remaining web UI polish work could justify **1-2 more phases** (audit log enhancements, remaining column visibility labels, login form validation consistency, QR code for MFA setup). After that, the admin UI is done.

**For the full platform** (all 56 feature plan sections): This is a very large project. Rough estimates:

| Tier | Items | Estimated Phases |
|------|-------|-----------------|
| Tier 1 (large systems) | 6 | 30-50+ phases |
| Tier 2 (medium features) | 10 | 15-25 phases |
| Tier 3 (small features) | 28 | 15-30 phases |
| **Total** | **44 remaining** | **~60-100+ phases** |

The most impactful next areas to build would be:
1. **WebRTC softphone** in the web client (section 5) — makes the admin UI a usable phone
2. **SMS subsystem** (section 3) — second channel for omnichannel queues
3. **Phone provisioning** (section 7) — critical for deploying desk phones
4. **Integrations** (section 8) — ConnectWise PSA integration is key for MSP workflow
5. **AI features** (section 17) — transcription/summarization adds immediate value

---

## Current Codebase Stats

| Metric | Value |
|--------|-------|
| Backend Python files | 174 |
| Backend Python lines | ~18,600 |
| Frontend TS/TSX files | 152 |
| Frontend TS/TSX lines | ~15,400 |
| API routers | 26 |
| Web pages | 25 modules |
| API hook files | 23 |
| Tests (backend) | 19 |
| Tests (frontend) | 36 |
| Docker services | 7 |
| Build phases completed | 28 |
| Build size (index chunk) | 366KB |
