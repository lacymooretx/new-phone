# New Phone API Load Tests

Performance and load tests for the New Phone PBX API using [Locust](https://locust.io).

## Prerequisites

- Python 3.12+
- Running API stack (`docker compose up` or local dev server on port 8000)
- At least one test user account with access to a tenant

## Install

```bash
cd tests/load
pip install -r requirements.txt
```

## Configuration

All settings are configurable via environment variables:

| Variable | Default | Description |
|---|---|---|
| `NP_LOAD_HOST` | `http://localhost:8000` | API base URL |
| `NP_LOAD_API_PREFIX` | `/api/v1` | API version prefix |
| `NP_LOAD_USER_EMAIL` | `admin@test.local` | Test user email |
| `NP_LOAD_USER_PASSWORD` | `TestPassword123!` | Test user password |
| `NP_LOAD_USERS` | _(empty)_ | Comma-separated `email:password` pairs for multiple users |
| `NP_LOAD_TENANT_ID` | _(auto-discover)_ | Target tenant UUID (skips discovery if set) |

### Multiple test users

For realistic load distribution across tenants, provide multiple accounts:

```bash
export NP_LOAD_USERS="admin@tenant1.local:Pass1!,admin@tenant2.local:Pass2!,user@tenant3.local:Pass3!"
```

## Quick test (smoke)

```bash
locust -f locustfile.py --headless -u 10 -r 2 -t 30s
```

10 users, spawning 2 per second, running for 30 seconds.

## Standard load test

```bash
locust -f locustfile.py --headless -u 100 -r 10 -t 5m
```

100 concurrent users, spawning 10 per second, running for 5 minutes.

## Full load test (target capacity)

```bash
locust -f locustfile.py --headless -u 200 -r 10 -t 10m
```

200 concurrent users simulating peak load across 50 tenants.

## Web UI

```bash
locust -f locustfile.py
```

Open http://localhost:8089 in your browser to configure and monitor tests interactively.

## Test scenarios

### Traffic distribution

| Scenario | Weight | Description |
|---|---|---|
| `ReadHeavyBehavior` | 5 | Dashboard browsing, CDR views, recordings, extensions |
| `ApiCrudBehavior` | 3 | Admin CRUD on extensions, users, queues |
| `ConcurrentCallsBehavior` | 2 | Wallboard polling, queue stats, parking slots |
| `AuthBehavior` | 1 | Login/refresh token cycles |

### Scenario details

**Auth** (`scenarios/auth.py`):
- Login with test credentials
- Token refresh cycle
- Validate token on protected endpoints

**API CRUD** (`scenarios/api_crud.py`):
- Create, read, update, delete extensions
- List users and queues
- Tracks created resources for cleanup

**Read Heavy** (`scenarios/read_heavy.py`):
- List CDRs (with and without date filters)
- List recordings, extensions, queues, voicemail boxes
- Health check polling

**Concurrent Calls** (`scenarios/concurrent_calls.py`):
- Wallboard-style CDR polling (tight time windows)
- Queue stats polling
- Parking slot state polling
- Agent status monitoring

## Performance targets

| Category | Metric | Target |
|---|---|---|
| Auth endpoints | p95 latency | < 500ms |
| Read endpoints | p95 latency | < 200ms |
| Write endpoints | p95 latency | < 500ms |
| Overall | Error rate | < 1% |
| Overall | Throughput | > 50 req/s at 100 users |

The test automatically checks error rate against the 1% threshold when
running in headless mode and returns a non-zero exit code on failure.

## CI integration

```bash
# Run in CI with strict thresholds
locust -f locustfile.py \
  --headless \
  -u 100 -r 10 -t 5m \
  --csv=results/load \
  --html=results/load-report.html

# Check exit code
echo "Exit code: $?"
```

The `--csv` flag exports raw data for trend analysis.  The `--html` flag
generates a self-contained report.

## Distributed mode

For higher load generation, run Locust in distributed mode:

```bash
# Master (coordinates workers, serves web UI)
locust -f locustfile.py --master

# Workers (each on a separate machine or process)
locust -f locustfile.py --worker --master-host=MASTER_IP
```

## Troubleshooting

**"Login failed" errors**: Verify test credentials work manually:
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@test.local", "password": "TestPassword123!"}'
```

**"No tenants found"**: The test user needs MSP-level access to list tenants,
or set `NP_LOAD_TENANT_ID` to a specific tenant UUID.

**MFA-enabled accounts**: Load test users should not have MFA enabled.
The test cannot complete TOTP challenges automatically.

**Connection refused**: Ensure the API is running and accessible from the
test runner machine.
