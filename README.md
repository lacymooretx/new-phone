# New Phone

Multi-tenant, API-first PBX platform for Managed Service Providers.

Built to replace FreePBX/Asterisk with a modern, secure, multi-tenant architecture designed for MSPs managing ~50+ tenant phone systems from a single platform.

## Architecture

```
                           +------------------+
                           |   Client Apps    |
                           |                  |
               +-----------+----+----+--------+-----------+
               |           |    |    |        |           |
            Web UI     Desktop  | Extension  Mobile   Admin CLI
           (React)   (Electron) | (Chrome)  (Flutter)
               |           |    |    |        |
               +-----------+----+----+--------+-----------+
                           |                  |
                       HTTPS/WSS          HTTPS/WSS
                           |                  |
               +-----------v------------------v-----------+
               |                                          |
               |            FastAPI  (api/)                |
               |          /api/v1/* endpoints              |
               |   JWT auth | RBAC | RLS tenant isolation  |
               |                                          |
               +----+--------+--------+--------+----------+
                    |        |        |        |
           +-------v--+ +---v----+ +-v------+ +--v---------+
           |PostgreSQL | | Redis  | | MinIO  | | FreeSWITCH |
           |  17 + RLS | | 7 LRU | | S3 obj | | ESL + TLS  |
           +----------+ +--------+ +--------+ +-----+------+
                                                     |
               +-------------------------------------+
               |                                     |
          +----v---------+                    +------v------+
          |  AI Engine   |                    | SIP Trunks  |
          | STT/LLM/TTS  |                    | (PSTN/VoIP) |
          +--------------+                    +-------------+
```

## Tech Stack

| Layer | Technology |
|---|---|
| API | Python 3.12, FastAPI, SQLAlchemy 2, Pydantic v2 |
| Database | PostgreSQL 17 with Row-Level Security |
| Cache / Pub-Sub | Redis 7 |
| Object Storage | MinIO (S3-compatible) |
| Media Engine | FreeSWITCH (ESL, XML CURL, TLS/SRTP) |
| AI Engine | Python 3.12, FastAPI, WebSockets, STT/LLM/TTS pipeline |
| Web UI | React 19, TypeScript, Vite, Tailwind CSS, Radix UI, TanStack Query |
| Desktop | Electron (electron-vite) wrapping the Web UI |
| Browser Extension | Preact, Chrome Manifest V3, click-to-call |
| Mobile | Flutter/Dart (planned) |
| Auth | JWT (access + refresh), TOTP MFA, SSO (Microsoft Entra, Google Workspace) |
| Migrations | Alembic |
| Linting | Ruff (Python), ESLint (TypeScript) |
| Testing | pytest + pytest-asyncio (API), Vitest + Testing Library (Web) |
| Package Management | uv (Python), npm (JS/TS) |
| Deployment | Docker Compose |

## Quickstart

### Prerequisites

- Docker and Docker Compose
- Node.js 20+
- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (Python package manager)

### Start the platform

```bash
# Clone and configure
cp .env.example .env

# Generate TLS certs for FreeSWITCH (first time only)
make tls-cert

# Start all services
docker compose up -d

# Run database migrations
make migrate

# (Optional) Load development seed data
make seed

# Verify
make health
```

The following services will be available:

| Service | URL |
|---|---|
| API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/api/docs |
| API Docs (ReDoc) | http://localhost:8000/api/redoc |
| Web UI | http://localhost:3000 |
| MinIO Console | http://localhost:9001 |
| MailHog (dev email) | http://localhost:8025 |
| AI Engine API | http://localhost:8091 |
| AI Engine WebSocket | ws://localhost:8090 |

## Project Structure

```
new-phone/
  api/                  FastAPI backend (Python 3.12, uv workspace)
    src/new_phone/        Application source
      auth/                 JWT, MFA, RBAC, password hashing
      db/                   SQLAlchemy engine, RLS context, base models
      deps/                 FastAPI dependency injection (auth, DB sessions)
      events/               Redis pub/sub event publisher
      freeswitch/           XML CURL config server, ESL config sync
      integrations/         ConnectWise, CRM enrichment
      middleware/           Request logging, RFC 7807 error handler
      models/               SQLAlchemy ORM models (53 models)
      phone_apps/           Desk phone XML app endpoints
      provisioning/         Phone auto-provisioning (Yealink, Polycom, Cisco)
      routers/              API route handlers (52 routers)
      schemas/              Pydantic request/response schemas
      services/             Business logic layer (59 services)
      sms/                  SMS webhook ingress
      templates/            Jinja2 email templates
      ws/                   WebSocket connection manager
    alembic/              Database migrations (55 versioned migrations)
    tests/                pytest test suite
  web/                  React/TypeScript frontend (Vite, Tailwind, Radix UI)
    src/
      api/                  API client modules (TanStack Query)
      components/           Reusable UI components (shadcn/ui)
      hooks/                Custom React hooks
      lib/                  Utilities, SIP client, headset manager
      locales/              i18n translation files
      pages/                Route-level page components (37 sections)
      router/               React Router configuration
      stores/               Zustand state stores
  desktop/              Electron desktop app (electron-vite)
  extension/            Chrome extension (Preact, Manifest V3, click-to-call)
  ai-engine/            AI Voice Agent engine (STT/LLM/TTS pipeline)
    src/ai_engine/
      api/                  REST API endpoints
      audio/                Audio processing, VAD
      core/                 Session management
      pipelines/            STT -> LLM -> TTS orchestration
      providers/            Multi-provider adapters (OpenAI, Deepgram, etc.)
      services/             Agent lifecycle, conversation state
      tools/                LLM tool/function calling definitions
  freeswitch/           FreeSWITCH Docker build + config
    conf/                 XML configuration overrides
    tls/                  TLS certificates (gitignored, generated by make tls-cert)
  db/
    init/                 PostgreSQL initialization scripts (role creation)
    seed/                 Development seed data
  docs/                 Project documentation
  docker-compose.yml    Full-stack orchestration
  Makefile              Development shortcuts
  pyproject.toml        Root workspace config (uv, ruff)
```

## Development

See [docs/development.md](docs/development.md) for the full development guide, including:

- Local setup and environment variables
- Running individual services
- Database migrations
- Adding new API endpoints
- Code style and linting
- Common issues and troubleshooting

## Testing

```bash
# API unit tests
make test

# Web UI tests
make web-test

# Lint
make lint         # Python (ruff)
make web-lint     # TypeScript (eslint)

# Format
make fmt          # Python auto-format
```

## Documentation

- [Architecture](docs/architecture.md) -- system design, data flow, multi-tenancy, auth model
- [Development Guide](docs/development.md) -- local setup, workflows, patterns
- [Contributing](CONTRIBUTING.md) -- branch naming, commit format, PR process
- [Feature Plan](docs/feature-plan.md) -- comprehensive feature roadmap (56 sections)
- [Phone Provisioning](docs/phone-provisioning.md) -- desk phone auto-config
- [SMS Messaging](docs/sms-messaging.md) -- SMS/MMS architecture, provider abstraction

## License

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for details.
