# High Availability Setup Guide

## Overview

This document describes how to run the New Phone platform in an HA configuration using `docker-compose.ha.yml` as an overlay on the base `docker-compose.yml`.

**Architecture:**

```
                    +-----------+
  Clients -------->| nginx-lb  |-------> api-1, api-2
                    +-----------+
                         |
         +---------------+---------------+
         |                               |
   +------------+               +--------------+
   | pg-primary |<--streaming-->| pg-standby   |
   +------------+  replication  +--------------+
         |
   +---------------+     +--------------+     +------------------+
   | redis-master  |<--->| redis-slave  |<--->| sentinel 1/2/3   |
   +---------------+     +--------------+     +------------------+
         |
   +-------------------+     +---------------------+
   | freeswitch-primary|     | freeswitch-standby   |
   +-------------------+     +---------------------+
```

---

## Prerequisites

- Docker Engine 24+ with Compose V2
- Minimum 8 GB RAM (16 GB recommended for full HA stack)
- All config directories created under `./ha/`:
  - `./ha/postgres/primary/`
  - `./ha/postgres/standby/`
  - `./ha/redis/`
  - `./ha/nginx/`
  - `./ha/nginx/conf.d/`
- Environment variables set in `.env` or `~/.secrets/.env` (see `docs/secrets-required.md`)

### Required Environment Variables (HA-specific)

| Variable | Purpose | Default |
|---|---|---|
| `NP_DB_REPL_USER` | PostgreSQL replication user | `replicator` |
| `NP_DB_REPL_PASSWORD` | Replication user password | `change_me_repl` |
| `NP_REDIS_PASSWORD` | Redis AUTH password (empty = no auth) | _(empty)_ |
| `NP_FS_STANDBY_IP` | IP of the FreeSWITCH standby host | `127.0.0.2` |
| `NP_FS_PRIMARY_IP` | IP of the FreeSWITCH primary host | `127.0.0.1` |
| `NP_FS_STANDBY_SIP_PORT` | SIP port for standby FS | `5090` |
| `NP_FS_STANDBY_ESL_PORT` | ESL port for standby FS | `8022` |

---

## Quick Start

```bash
# Start the full HA stack
docker compose -f docker-compose.yml -f docker-compose.ha.yml up -d

# Verify all services are healthy
docker compose -f docker-compose.yml -f docker-compose.ha.yml ps

# Check replication lag
docker exec new-phone-ha-pg-primary-1 \
  psql -U new_phone_admin -d new_phone \
  -c "SELECT client_addr, state, sent_lsn, write_lsn, flush_lsn, replay_lsn FROM pg_stat_replication;"
```

---

## Component Details

### 1. PostgreSQL Streaming Replication

**How it works:**
- `pg-primary` runs as the writable primary with WAL archiving enabled
- `pg-standby` bootstraps from primary using `pg_basebackup`, then follows via streaming replication
- Synchronous replication is configured (`synchronous_standby_names = 'standby1'`) so commits wait for standby acknowledgment
- The standby is read-only (hot standby) and can serve read queries

**Setup files required:**

Create `./ha/postgres/primary/initdb-replication.sh`:

```bash
#!/bin/bash
set -e

# Create replication user
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE ROLE ${POSTGRES_REPLICATION_USER:-replicator}
      WITH REPLICATION LOGIN PASSWORD '${POSTGRES_REPLICATION_PASSWORD:-change_me_repl}';
EOSQL

# Append replication HBA rules
cat /docker-entrypoint-initdb.d/pg_hba_replication.conf >> "$PGDATA/pg_hba.conf"
pg_ctl reload
```

Create `./ha/postgres/primary/pg_hba_replication.conf`:

```
# Replication connections
host replication replicator 0.0.0.0/0 md5
```

Create `./ha/postgres/standby/setup-standby.sh` (placeholder, actual bootstrap is in compose command):

```bash
#!/bin/bash
# Standby bootstrap is handled by the docker-compose.ha.yml command.
# This file exists for future customization.
echo "Standby init hook — no-op"
```

**Monitoring replication health:**

```bash
# On primary — check connected standbys
docker exec <pg-primary-container> psql -U new_phone_admin -d new_phone \
  -c "SELECT * FROM pg_stat_replication;"

# On standby — check recovery status
docker exec <pg-standby-container> psql -U new_phone_admin \
  -c "SELECT pg_is_in_recovery(), pg_last_wal_receive_lsn(), pg_last_wal_replay_lsn();"

# Check replication lag in bytes
docker exec <pg-primary-container> psql -U new_phone_admin -d new_phone \
  -c "SELECT client_addr, pg_wal_lsn_diff(sent_lsn, replay_lsn) AS lag_bytes FROM pg_stat_replication;"
```

**Promoting standby to primary (manual failover):**

```bash
# 1. Stop the old primary (or it is already down)
docker compose -f docker-compose.yml -f docker-compose.ha.yml stop pg-primary

# 2. Promote the standby
docker exec <pg-standby-container> pg_ctl promote -D /var/lib/postgresql/data

# 3. Update API connection strings to point to the new primary
#    Update NP_DB_HOST env var or DNS to point to pg-standby

# 4. Rebuild a new standby from the promoted primary when ready
```

#### Patroni (Recommended for Production Auto-Failover)

For production deployments, replace the manual primary/standby setup with Patroni for automatic failover. Patroni manages PostgreSQL HA with leader election via a distributed consensus store (etcd).

**Why Patroni over manual failover:**
- Automatic failover without human intervention (detects primary failure in seconds)
- Prevents split-brain with distributed consensus (etcd quorum)
- Handles standby re-initialization automatically after failover
- Provides REST API for health checks and cluster status

**Architecture with Patroni:**

```
  +-------+     +-------+     +-------+
  | etcd1 |-----| etcd2 |-----| etcd3 |
  +-------+     +-------+     +-------+
       |             |              |
  +---------+   +---------+
  | Patroni |   | Patroni |
  | (PG pri)|   | (PG stby)|
  +---------+   +---------+
```

**Patroni configuration example (`patroni.yml`):**

```yaml
scope: new-phone-pg
name: pg-node-1

restapi:
  listen: 0.0.0.0:8008
  connect_address: pg-node-1:8008

etcd3:
  hosts:
    - etcd1:2379
    - etcd2:2379
    - etcd3:2379

bootstrap:
  dcs:
    ttl: 30
    loop_wait: 10
    retry_timeout: 10
    maximum_lag_on_failover: 1048576  # 1 MB
    postgresql:
      use_pg_rewind: true
      parameters:
        wal_level: replica
        hot_standby: "on"
        max_wal_senders: 5
        max_replication_slots: 5
        wal_keep_size: 256MB
        synchronous_commit: "on"
        synchronous_standby_names: "*"

  initdb:
    - encoding: UTF8
    - data-checksums

  pg_hba:
    - host replication replicator 0.0.0.0/0 md5
    - host all all 0.0.0.0/0 md5

  users:
    new_phone_admin:
      password: ${NP_DB_ADMIN_PASSWORD}
      options:
        - createrole
        - createdb
    replicator:
      password: ${NP_DB_REPL_PASSWORD}
      options:
        - replication

postgresql:
  listen: 0.0.0.0:5432
  connect_address: pg-node-1:5432
  data_dir: /var/lib/postgresql/data
  authentication:
    superuser:
      username: new_phone_admin
      password: ${NP_DB_ADMIN_PASSWORD}
    replication:
      username: replicator
      password: ${NP_DB_REPL_PASSWORD}
```

**Patroni health check endpoints:**

| Endpoint | Returns 200 When |
|---|---|
| `GET /primary` | Node is the current leader |
| `GET /replica` | Node is a healthy replica |
| `GET /health` | Node is running (any role) |
| `GET /cluster` | Cluster status JSON |

**Migrating from manual HA to Patroni:**

1. Stop the manual HA stack
2. Deploy etcd cluster (3 nodes)
3. Initialize Patroni on the primary node with existing data directory
4. Join Patroni on the standby node (it will re-bootstrap from primary)
5. Point nginx/API health checks at Patroni REST API instead of `pg_isready`
6. Update API connection strings to use Patroni-aware connection (e.g., via PgBouncer with Patroni callback)

### 2. Redis Sentinel

**How it works:**
- `redis-master` is the writable primary
- `redis-slave` replicates from master
- Three sentinel instances (`redis-sentinel-1/2/3`) monitor the master
- Quorum of 2 sentinels required to trigger failover
- Failover timeout: 10 seconds
- Down-after-milliseconds: 5 seconds

**Application configuration:**

The API should be configured to use Redis Sentinel for automatic failover. Update the connection to use sentinel-aware client:

```python
# In API config, use sentinel connection
from redis.sentinel import Sentinel

sentinel = Sentinel(
    [('redis-sentinel-1', 26379), ('redis-sentinel-2', 26379), ('redis-sentinel-3', 26379)],
    socket_timeout=0.5
)
master = sentinel.master_for('np-master', socket_timeout=0.5)
slave = sentinel.slave_for('np-master', socket_timeout=0.5)
```

**Monitoring sentinel status:**

```bash
# Check sentinel's view of the master
docker exec <sentinel-container> redis-cli -p 26379 sentinel master np-master

# Check known slaves
docker exec <sentinel-container> redis-cli -p 26379 sentinel slaves np-master

# Check sentinel quorum
docker exec <sentinel-container> redis-cli -p 26379 sentinel ckquorum np-master
```

### 3. API Load Balancing (nginx)

**How it works:**
- `api-1` and `api-2` run identical API instances
- `nginx-lb` distributes requests across both using least-connections
- Health checks remove unhealthy backends automatically
- JWT tokens are stateless so any instance can handle any request
- Session/state stored in Redis (shared), not in-process

**Create `./ha/nginx/nginx.conf`:**

```nginx
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 2048;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" upstream=$upstream_addr '
                    'response_time=$upstream_response_time';

    access_log /var/log/nginx/access.log main;
    sendfile on;
    keepalive_timeout 65;

    # API upstream — least connections for even distribution
    upstream api_backend {
        least_conn;
        server api-1:8000 max_fails=3 fail_timeout=10s;
        server api-2:8000 max_fails=3 fail_timeout=10s;
    }

    # WebSocket upstream — sticky by IP for Verto/WebRTC
    upstream api_websocket {
        ip_hash;
        server api-1:8000 max_fails=3 fail_timeout=10s;
        server api-2:8000 max_fails=3 fail_timeout=10s;
    }

    server {
        listen 8000;
        server_name _;

        # Regular API traffic
        location /api/ {
            proxy_pass http://api_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_connect_timeout 5s;
            proxy_read_timeout 60s;
            proxy_next_upstream error timeout http_502 http_503;
            proxy_next_upstream_tries 2;
        }

        # WebSocket connections (Verto, real-time events)
        location /ws/ {
            proxy_pass http://api_websocket;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_read_timeout 3600s;
            proxy_send_timeout 3600s;
        }

        # Health check endpoint for external monitoring
        location /health {
            proxy_pass http://api_backend/api/v1/health;
            proxy_connect_timeout 2s;
            proxy_read_timeout 5s;
        }
    }

    # Web frontend pass-through (optional, if web is behind LB too)
    server {
        listen 3000;
        server_name _;

        location / {
            proxy_pass http://web:80;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
    }
}
```

### 4. FreeSWITCH Active/Standby

**How it works:**
- `freeswitch-primary` handles all live calls
- `freeswitch-standby` runs in standby mode with the same configuration but on alternate ports
- Both connect to the same PostgreSQL database for configuration
- Failover is manual or script-driven (SIP proxy/DNS update)
- Active calls in progress are lost during failover (SIP re-INVITE recovery depends on endpoints)

**Failover procedure:**

```bash
# 1. Verify primary is actually down
docker exec <fs-primary-container> fs_cli -x "status" || echo "Primary is down"

# 2. Promote standby — update SIP proxy / DNS to point to standby IP
# If using the Rust SIP proxy, update its config to route to standby

# 3. Update API to point to new FreeSWITCH
# Set NP_FREESWITCH_HOST to standby hostname/IP
# Set NP_FREESWITCH_ESL_PORT to standby ESL port (8022 default)

# 4. Restart API instances to pick up new FS target
docker compose -f docker-compose.yml -f docker-compose.ha.yml restart api-1 api-2

# 5. Verify calls route through standby
docker exec <fs-standby-container> fs_cli -x "show calls"
```

**Shared state considerations:**
- Call recordings: primary writes to `recordings` volume; standby has a separate `recordings_standby` volume. Configure MinIO sync or shared NFS for shared storage.
- CDR records: both instances write CDRs to PostgreSQL, so no data loss on failover.
- Voicemail: stored in MinIO (shared), accessible from both instances.
- Registrations: stored in PostgreSQL via `xml_curl`, so standby picks them up immediately.

---

## Health Check Endpoints

| Component | Endpoint | Expected |
|---|---|---|
| API (via nginx) | `GET http://localhost:8000/api/v1/health` | 200 OK |
| API-1 direct | `GET http://api-1:8000/api/v1/health` | 200 OK |
| API-2 direct | `GET http://api-2:8000/api/v1/health` | 200 OK |
| PostgreSQL primary | `pg_isready -h pg-primary -U new_phone_admin` | exit 0 |
| PostgreSQL standby | `pg_isready -h pg-standby` | exit 0 |
| Redis master | `redis-cli -h redis-master ping` | PONG |
| Redis slave | `redis-cli -h redis-slave ping` | PONG |
| Redis sentinel | `redis-cli -h redis-sentinel-1 -p 26379 ping` | PONG |
| FreeSWITCH primary | `fs_cli -x "status"` | Running |
| FreeSWITCH standby | `fs_cli -x "status"` | Running |
| nginx | `GET http://localhost:8000/health` | 200 OK |

---

## Monitoring Recommendations

1. **Prometheus targets** — add all HA services to `monitoring/prometheus/prometheus.yml`:
   - `pg-primary:9187` and `pg-standby:9187` (postgres-exporter on each)
   - `redis-master:9121` and `redis-slave:9121` (redis-exporter on each)
   - `api-1:8000/metrics` and `api-2:8000/metrics`
   - `nginx-lb` via nginx-exporter or stub_status

2. **Alert on:**
   - PostgreSQL replication lag > 1 MB
   - PostgreSQL standby disconnected
   - Redis sentinel quorum lost
   - Redis slave disconnected
   - Any API instance health check failing
   - nginx upstream failures > 0/min
   - FreeSWITCH standby unreachable

3. **Grafana dashboards** — create HA-specific dashboard showing:
   - Replication lag (PG and Redis)
   - API request distribution across instances
   - Sentinel failover events
   - Per-instance CPU/memory

---

## Rollback to Single-Instance

To revert to non-HA mode:

```bash
# Stop the HA stack
docker compose -f docker-compose.yml -f docker-compose.ha.yml down

# Start base stack only
docker compose up -d
```

Data in `pg_primary_data` is compatible with the base `pg_data` volume. To migrate data back, use `pg_dump`/`pg_restore` from the primary.
