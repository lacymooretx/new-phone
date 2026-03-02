# Development Guide

## Prerequisites

| Tool | Version | Purpose |
|---|---|---|
| Docker + Docker Compose | Latest | Run all services |
| Python | 3.12+ | API and AI Engine |
| [uv](https://docs.astral.sh/uv/) | Latest | Python package manager (replaces pip/poetry) |
| Node.js | 20+ | Web UI, Desktop, Extension |
| npm | 10+ | JS/TS package manager |

## Local Setup

### 1. Clone and configure

```bash
git clone <repo-url> new-phone
cd new-phone
cp .env.example .env
```

Edit `.env` and set real values for production. For local development, the defaults work out of the box.

### 2. Generate TLS certificates

FreeSWITCH requires TLS certificates. For local development, generate self-signed certs:

```bash
make tls-cert
```

This creates `freeswitch/tls/cert.pem`, `key.pem`, `agent.pem`, and `cafile.pem`. These files are gitignored.

### 3. Start infrastructure services

```bash
docker compose up -d
```

This starts PostgreSQL, Redis, MinIO, MailHog, FreeSWITCH, the API, Web UI, and AI Engine. On first run, PostgreSQL will execute the init scripts in `db/init/` to create the `new_phone_app` database role.

### 4. Run database migrations

```bash
make migrate
```

This runs Alembic migrations inside the API container using the `new_phone_admin` user.

### 5. (Optional) Load seed data

```bash
make seed
```

Loads `db/seed/dev-seed.sql` with sample tenants, users, extensions, and other test data.

### 6. Verify

```bash
make health
```

Should return a JSON health check response showing all services are connected.

## Environment Variables

All environment variables use the `NP_` prefix. They are loaded by Pydantic Settings in `api/src/new_phone/config.py`.

### Database

| Variable | Default | Description |
|---|---|---|
| `NP_DB_HOST` | `localhost` | PostgreSQL hostname |
| `NP_DB_PORT` | `5432` | PostgreSQL port |
| `NP_DB_NAME` | `new_phone` | Database name |
| `NP_DB_ADMIN_USER` | `new_phone_admin` | Admin user (bypasses RLS, runs migrations) |
| `NP_DB_ADMIN_PASSWORD` | `change_me_admin` | Admin user password |
| `NP_DB_APP_USER` | `new_phone_app` | App user (RLS enforced, used at runtime) |
| `NP_DB_APP_PASSWORD` | `change_me_app` | App user password |

### Redis

| Variable | Default | Description |
|---|---|---|
| `NP_REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |

### JWT

| Variable | Default | Description |
|---|---|---|
| `NP_JWT_SECRET_KEY` | `change-me-...` | HMAC signing key (use a random 64-char string in production) |
| `NP_JWT_ALGORITHM` | `HS256` | JWT algorithm |
| `NP_JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | Access token TTL |
| `NP_JWT_REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token TTL |

### FreeSWITCH

| Variable | Default | Description |
|---|---|---|
| `NP_FREESWITCH_HOST` | `localhost` | FreeSWITCH hostname (use `freeswitch` in Docker) |
| `NP_FREESWITCH_ESL_PORT` | `8021` | Event Socket Layer port |
| `NP_FREESWITCH_ESL_PASSWORD` | `ClueCon` | ESL authentication password |
| `NP_FREESWITCH_WSS_PORT` | `7443` | WebSocket Secure port for WebRTC |
| `NP_FREESWITCH_WSS_HOST` | `localhost` | Browser-accessible WSS hostname |

### API

| Variable | Default | Description |
|---|---|---|
| `NP_API_HOST` | `0.0.0.0` | API listen address |
| `NP_API_PORT` | `8000` | API listen port |
| `NP_DEBUG` | `false` | Enable debug mode (console logging, CORS wildcard) |
| `NP_LOG_LEVEL` | `INFO` | Log level (DEBUG, INFO, WARNING, ERROR) |

### MFA

| Variable | Default | Description |
|---|---|---|
| `NP_MFA_ISSUER` | `NewPhone` | TOTP issuer name shown in authenticator apps |

### MinIO (Object Storage)

| Variable | Default | Description |
|---|---|---|
| `NP_MINIO_ENDPOINT` | `localhost:9000` | MinIO endpoint (use `minio:9000` in Docker) |
| `NP_MINIO_ACCESS_KEY` | `minioadmin` | MinIO access key |
| `NP_MINIO_SECRET_KEY` | `minioadmin` | MinIO secret key |
| `NP_MINIO_BUCKET` | `recordings` | Primary bucket for recordings/voicemail |
| `NP_MINIO_SECURE` | `false` | Use HTTPS for MinIO connections |

### SMTP

| Variable | Default | Description |
|---|---|---|
| `NP_SMTP_HOST` | `localhost` | SMTP server (use `mailhog` in Docker) |
| `NP_SMTP_PORT` | `1025` | SMTP port (1025 for MailHog, 587 for production) |
| `NP_SMTP_USER` | (empty) | SMTP auth username |
| `NP_SMTP_PASSWORD` | (empty) | SMTP auth password |
| `NP_SMTP_FROM_ADDRESS` | `voicemail@newphone.local` | From address for voicemail-to-email |

### SSO

| Variable | Default | Description |
|---|---|---|
| `NP_SSO_CALLBACK_URL` | `http://localhost:8000/api/v1/auth/sso/callback` | OAuth callback URL |
| `NP_SSO_FRONTEND_URL` | `http://localhost:5173` | Frontend URL for post-SSO redirect |

### AI Engine

| Variable | Default | Description |
|---|---|---|
| `NP_AI_WS_HOST_PORT` | `8090` | AI engine WebSocket port |
| `NP_AI_API_HOST_PORT` | `8091` | AI engine REST API port |

### Encryption

| Variable | Default | Description |
|---|---|---|
| `NP_TRUNK_ENCRYPTION_KEY` | (generated) | Fernet key for encrypting SIP trunk credentials and AI provider API keys |

## Running Services Individually

### API (development mode with reload)

```bash
# Install Python dependencies
cd api && uv pip install -e ".[dev]"

# Run with auto-reload (requires local PostgreSQL, Redis, etc.)
NP_DB_HOST=localhost NP_DB_PORT=5434 NP_REDIS_URL=redis://localhost:6379/0 \
    uv run uvicorn new_phone.main:app --reload --host 0.0.0.0 --port 8000
```

Or run inside Docker while keeping infrastructure services up:

```bash
docker compose up -d postgres redis minio mailhog freeswitch
docker compose up api  # foreground, with logs
```

### Web UI (development mode with HMR)

```bash
make web-dev
# or
cd web && npm run dev
```

The Vite dev server runs on `http://localhost:5173` with hot module replacement. API requests are proxied to `http://localhost:8000` (configured in `web/vite.config.ts`).

### Desktop (Electron development mode)

```bash
make desktop-dev
# or
cd desktop && npm run dev
```

Opens the Electron app with the web UI loaded. The desktop app wraps the web UI and adds native OS integrations.

### Extension (Chrome extension development)

```bash
cd extension && npm run dev
```

Builds to `extension/dist/`. Load as an unpacked extension in Chrome at `chrome://extensions`.

### AI Engine

```bash
cd ai-engine
uv pip install -e ".[dev]"
uv run uvicorn ai_engine.main:app --reload --host 0.0.0.0 --port 8091
```

## Running Tests

### API tests (pytest)

```bash
# Run all API tests
make test

# Run with verbose output
uv run python -m pytest api/tests/ -v

# Run a specific test file
uv run python -m pytest api/tests/test_extensions.py -v

# Run only unit tests (no Docker required)
uv run python -m pytest api/tests/ -v -m unit

# Run only integration tests (requires Docker stack)
uv run python -m pytest api/tests/ -v -m integration
```

Tests use `pytest-asyncio` with `asyncio_mode = "auto"`. Test markers:
- `@pytest.mark.unit` -- fast, isolated tests with no external dependencies
- `@pytest.mark.integration` -- tests that hit the running Docker stack

### Web UI tests (Vitest)

```bash
# Run all frontend tests
make web-test

# Watch mode
cd web && npm run test:watch
```

Tests use Vitest with jsdom, Testing Library, and MSW for API mocking.

### AI Engine tests

```bash
cd ai-engine
uv run python -m pytest tests/ -v
```

### Linting

```bash
# Python (ruff)
make lint

# TypeScript (eslint)
make web-lint
```

### Formatting

```bash
# Auto-format Python
make fmt
```

## Code Style

### Python (API, AI Engine)

- Formatter and linter: [Ruff](https://docs.astral.sh/ruff/)
- Target: Python 3.12
- Line length: 100
- Lint rules: E, F, W, I, UP, B, SIM, RUF (see `pyproject.toml`)
- Import sorting: isort-compatible, `new_phone` as first-party

```bash
# Check
cd api && uv run ruff check src/ tests/

# Fix auto-fixable issues
cd api && uv run ruff check src/ tests/ --fix

# Format
cd api && uv run ruff format src/ tests/
```

### TypeScript (Web, Desktop, Extension)

- Linter: ESLint 9 with flat config
- React hooks and refresh plugins enabled
- Strict TypeScript with `noEmit` type checking

```bash
cd web && npm run lint
```

## Database Migrations

Migrations are managed with Alembic. The migration files live in `api/alembic/versions/`.

### Run pending migrations

```bash
make migrate
# or
docker compose exec api alembic upgrade head
```

### Create a new migration

```bash
# Auto-generate from model changes
docker compose exec api alembic revision --autogenerate -m "description_of_change"

# Create empty migration (for manual SQL like RLS policies)
docker compose exec api alembic revision -m "description_of_change"
```

### Migration conventions

- Migrations are numbered sequentially: `0001_`, `0002_`, etc.
- Every table with tenant data gets a companion RLS migration. For example:
  - `0010_queues.py` -- creates the `queues` table
  - `0011_queues_rls.py` -- adds RLS policies for tenant isolation
- RLS migrations follow this pattern:
  ```python
  op.execute("ALTER TABLE queues ENABLE ROW LEVEL SECURITY")
  op.execute("ALTER TABLE queues FORCE ROW LEVEL SECURITY")
  op.execute("""
      CREATE POLICY queues_tenant_isolation ON queues
          USING (tenant_id::text = current_setting('app.current_tenant', true))
  """)
  ```

### Rollback

```bash
# Rollback one migration
docker compose exec api alembic downgrade -1

# Rollback to a specific revision
docker compose exec api alembic downgrade 0010
```

## Adding a New API Endpoint

Follow this pattern when adding a new resource. Example: adding a "call_flows" feature.

### 1. Create the SQLAlchemy model

`api/src/new_phone/models/call_flow.py`:
```python
import uuid
from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from new_phone.db.base import Base, TenantScopedMixin, TimestampMixin

class CallFlow(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "call_flows"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
```

### 2. Create Pydantic schemas

`api/src/new_phone/schemas/call_flow.py`:
```python
import uuid
from pydantic import BaseModel

class CallFlowCreate(BaseModel):
    name: str

class CallFlowResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    model_config = {"from_attributes": True}
```

### 3. Create the service

`api/src/new_phone/services/call_flow_service.py`:
```python
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from new_phone.models.call_flow import CallFlow

class CallFlowService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list(self, tenant_id: uuid.UUID) -> list[CallFlow]:
        result = await self.db.execute(
            select(CallFlow).where(CallFlow.tenant_id == tenant_id)
        )
        return list(result.scalars().all())
```

### 4. Create the router

`api/src/new_phone/routers/call_flows.py`:
```python
import uuid
from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from new_phone.auth.rbac import Permission, is_msp_role
from new_phone.deps.auth import get_admin_db, require_permission
from new_phone.models.user import User
from new_phone.schemas.call_flow import CallFlowResponse
from new_phone.services.call_flow_service import CallFlowService

router = APIRouter(prefix="/tenants/{tenant_id}/call-flows", tags=["call-flows"])

@router.get("", response_model=list[CallFlowResponse])
async def list_call_flows(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_IVR))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    # Check tenant access for non-MSP roles
    if not is_msp_role(user.role) and user.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")
    service = CallFlowService(db)
    return await service.list(tenant_id)
```

### 5. Register the router

In `api/src/new_phone/main.py`, add the import and include:
```python
from new_phone.routers import call_flows
app.include_router(call_flows.router, prefix="/api/v1")
```

### 6. Create migrations

```bash
docker compose exec api alembic revision --autogenerate -m "call_flows"
docker compose exec api alembic revision -m "call_flows_rls"
```

Edit the RLS migration to add tenant isolation policies.

### 7. Run migrations and test

```bash
make migrate
uv run python -m pytest api/tests/test_call_flows.py -v
```

## Common Issues

### "role new_phone_app does not exist"

The init scripts in `db/init/` did not run. This happens when PostgreSQL data already exists from a previous setup. Either:
- Remove the volume: `docker compose down && docker volume rm new_phone_pg_data` (destroys all data)
- Manually create the role by connecting to the database and running `db/init/00-create-roles.sql`

### ESL connection refused

FreeSWITCH takes 10-15 seconds to start. The API health check will show `freeswitch: false` until it is ready. Wait for FreeSWITCH to pass its health check:

```bash
docker compose ps  # Check health status
docker compose logs freeswitch  # Check for errors
```

### TLS certificate errors

Run `make tls-cert` to regenerate self-signed certificates. The certificates in `freeswitch/tls/` are gitignored and must be generated locally.

### Port conflicts

Default ports used by the stack:

| Port | Service |
|---|---|
| 3000 | Web UI (nginx) |
| 5061 | FreeSWITCH SIP TLS |
| 5173 | Web UI dev server (Vite) |
| 6379 | Redis |
| 7443 | FreeSWITCH WSS |
| 8000 | API |
| 8021 | FreeSWITCH ESL (mapped to 8022 on host) |
| 8025 | MailHog web UI |
| 8090 | AI Engine WebSocket |
| 8091 | AI Engine API |
| 9000 | MinIO API |
| 9001 | MinIO Console |

If any port is already in use, either stop the conflicting service or change the port mapping in `docker-compose.yml` or via environment variables.

### MinIO connection errors

MinIO takes a few seconds to initialize. The API will log `minio_connection_failed` on startup if MinIO is not yet ready, but will continue running. Recordings and voicemail storage will fail until MinIO is available.

### Alembic "target database is not up to date"

This means there are pending migrations. Run `make migrate` to apply them. If you have uncommitted migration changes that conflict, check `alembic history` and resolve the revision chain.

### Python "ModuleNotFoundError: No module named 'new_phone'"

The API package needs to be installed in development mode:

```bash
cd api && uv pip install -e ".[dev]"
```
