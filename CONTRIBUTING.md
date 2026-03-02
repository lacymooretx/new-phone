# Contributing to New Phone

## Getting Started

1. Read the [Development Guide](docs/development.md) to set up your local environment.
2. Read the [Architecture](docs/architecture.md) to understand the system design.
3. Check the issue tracker for open issues or create one before starting work.

## Branch Naming

Use the following naming convention for branches:

```
<type>/<short-description>
```

| Type | Use For |
|---|---|
| `feature/` | New functionality |
| `fix/` | Bug fixes |
| `refactor/` | Code restructuring without behavior change |
| `docs/` | Documentation changes only |
| `test/` | Adding or fixing tests only |
| `chore/` | Build, CI, tooling, dependency updates |

Examples:

```
feature/queue-callback
fix/rls-policy-leak
refactor/extract-tenant-service
docs/add-sms-api-guide
test/parking-lot-edge-cases
chore/upgrade-fastapi-116
```

Keep branch names lowercase, use hyphens as separators, and keep them under 50 characters.

## Commit Format

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short summary>

<optional body>
```

### Types

| Type | Meaning |
|---|---|
| `feat` | New feature |
| `fix` | Bug fix |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `docs` | Documentation only |
| `test` | Adding or correcting tests |
| `chore` | Build process, CI, dependency updates |
| `perf` | Performance improvement |
| `style` | Formatting, whitespace (no logic change) |
| `ci` | CI/CD configuration changes |

### Scopes

Use the component name as the scope:

| Scope | Component |
|---|---|
| `api` | FastAPI backend |
| `web` | React frontend |
| `desktop` | Electron app |
| `extension` | Chrome extension |
| `ai` | AI engine |
| `fs` | FreeSWITCH configuration |
| `db` | Database, migrations |
| `docker` | Docker Compose, Dockerfiles |

### Examples

```
feat(api): add queue callback scheduling endpoint
fix(web): prevent duplicate SMS send on double-click
refactor(api): extract tenant access check into shared dependency
docs(api): document SSO configuration endpoints
test(api): add integration tests for parking lot overflow
chore(docker): upgrade PostgreSQL to 17.2
perf(api): add composite index on cdrs(tenant_id, created_at)
```

### Rules

- Summary line must be under 72 characters.
- Use imperative mood ("add", "fix", "update", not "added", "fixed", "updated").
- Do not end the summary with a period.
- The body (if present) should explain **why**, not **what** (the diff shows what).
- Reference related issues in the body: `Closes #42` or `Refs #42`.

## Pull Request Process

### Before Opening a PR

1. **Create an issue first** (unless it is a trivial fix). Discuss the approach before writing code.
2. **Branch from `main`** using the naming convention above.
3. **Keep PRs focused**. One feature or fix per PR. Large changes should be split into stacked PRs.
4. **Run all checks locally**:
   ```bash
   make lint        # Python linting
   make web-lint    # TypeScript linting
   make test        # API tests
   make web-test    # Web UI tests
   ```
5. **Run the full stack** and manually verify your change works end-to-end.

### Opening a PR

- Title: Use the same format as commit messages (`feat(api): add queue callback scheduling`).
- Description: Include:
  - **What** the PR does (1-3 sentences).
  - **Why** it is needed (link to issue).
  - **How** to test it (steps for the reviewer).
  - **Screenshots** if the change is visual (web UI, desktop).
  - **Migration notes** if the PR includes database changes.
- Target branch: `main`.

### PR Template

```markdown
## What

Brief description of the change.

Closes #<issue-number>

## Why

Context and motivation.

## How to Test

1. Start the stack: `docker compose up -d && make migrate`
2. ...specific steps...
3. Expected result: ...

## Checklist

- [ ] Tests pass (`make test`, `make web-test`)
- [ ] Linting passes (`make lint`, `make web-lint`)
- [ ] New endpoints have Pydantic schemas with validation
- [ ] New tenant-scoped tables have RLS policies
- [ ] Migrations are numbered correctly and have a companion RLS migration
- [ ] API changes are reflected in router imports and `main.py` registration
- [ ] Breaking changes are documented
```

## Code Review Checklist

Reviewers should verify:

### All Changes

- [ ] Code is clear and self-documenting; comments explain **why**, not **what**.
- [ ] No secrets, credentials, or sensitive data committed.
- [ ] No `TODO` or `FIXME` without an associated issue number.

### API Changes

- [ ] New endpoints use `require_permission()` or `require_role()` for authorization.
- [ ] Tenant access is checked (MSP roles can access any tenant; tenant roles are scoped).
- [ ] Pydantic schemas validate all input; no raw `dict` in request/response models.
- [ ] Errors use `HTTPException` and produce RFC 7807 responses.
- [ ] New routes are registered in `main.py` with the `/api/v1` prefix.
- [ ] Database queries use parameterized values (no f-string SQL injection).
- [ ] Service layer is separate from the router (business logic in `services/`, HTTP concerns in `routers/`).

### Database Changes

- [ ] New tenant-scoped tables have a `tenant_id` column with a foreign key to `tenants.id`.
- [ ] RLS policies are created in a companion migration.
- [ ] Migrations are reversible (both `upgrade` and `downgrade` are implemented).
- [ ] Migration numbering is sequential and does not conflict with other branches.
- [ ] Index is added for `tenant_id` and any frequently queried columns.

### Frontend Changes

- [ ] TypeScript types are accurate (no `any` without justification).
- [ ] API calls use the TanStack Query patterns from `web/src/api/`.
- [ ] Forms use react-hook-form with zod validation.
- [ ] Components are accessible (keyboard navigation, ARIA attributes).
- [ ] Translations are added for any user-facing text (see `web/src/locales/`).
- [ ] Error states and loading states are handled.

### Security

- [ ] Authentication is required on all new endpoints (unless explicitly public).
- [ ] RBAC permissions are appropriate for the endpoint's sensitivity.
- [ ] No credentials or API keys in code, config files, or logs.
- [ ] SIP trunk credentials and AI provider keys use Fernet encryption at rest.

## Testing Requirements

### What Must Be Tested

- Every new API endpoint needs at least one happy-path test and one error-path test.
- Business logic in service classes should have unit tests.
- Complex query logic should have integration tests against the real database.
- Frontend components with interactive behavior need Testing Library tests.

### Test File Naming

- API: `api/tests/test_<feature>.py`
- Web: `web/src/<path>/__tests__/<component>.test.tsx`
- AI Engine: `ai-engine/tests/test_<module>.py`

### Test Markers (API)

```python
import pytest

@pytest.mark.unit
async def test_extension_validation():
    """Fast test, no external deps."""
    ...

@pytest.mark.integration
async def test_create_extension_api():
    """Requires running Docker stack."""
    ...
```

## Database Conventions

- Table names: plural, snake_case (`call_flows`, `ring_groups`).
- Column names: snake_case (`created_at`, `tenant_id`).
- Primary keys: UUID v4 (`id` column).
- Foreign keys: `<table_singular>_id` (e.g., `tenant_id`, `extension_id`).
- Timestamps: `created_at` and `updated_at` via `TimestampMixin`.
- Soft deletes: not used. Use hard deletes with `ON DELETE CASCADE` for dependent rows.
- Enums: use PostgreSQL native enums or SQLAlchemy `String` with Python `StrEnum`.

## API Conventions

- URL paths: kebab-case (`/call-flows`, `/ring-groups`).
- Tenant-scoped paths: `/tenants/{tenant_id}/<resource>`.
- List endpoints: `GET /tenants/{tenant_id}/<resource>` returning `list[ResourceResponse]`.
- Detail endpoints: `GET /tenants/{tenant_id}/<resource>/{id}`.
- Create endpoints: `POST /tenants/{tenant_id}/<resource>` with `ResourceCreate` body.
- Update endpoints: `PUT /tenants/{tenant_id}/<resource>/{id}` with `ResourceUpdate` body.
- Delete endpoints: `DELETE /tenants/{tenant_id}/<resource>/{id}`.
- Tags: kebab-case matching the resource name (`tags=["call-flows"]`).
- Always return the created/updated resource in the response body.

## Questions?

Open an issue or reach out to the project maintainer.
