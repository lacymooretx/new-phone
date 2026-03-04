# Multi-Region Architecture

## Overview

The New Phone platform supports a primary/secondary region architecture for geographic redundancy and disaster recovery. The secondary region operates in warm-standby mode, receiving continuous data replication, and can be promoted to primary within the RTO target of 4 hours (typical actual failover is under 1 hour).

```
                   Region A (Primary)                    Region B (Secondary)
              ========================              ========================

Users ------> DNS (active) ----+                    DNS (standby)
                               |                         |
                          +---------+               +---------+
                          | nginx   |               | nginx   |
                          +---------+               +---------+
                          | api x2  |               | api x2  |
                          +---------+               +---------+
                               |                         |
                   +-----------+-----------+    (logical replication)
                   |           |           |         |
              +--------+  +-------+  +-------+  +--------+
              | PG pri |->| Redis |  | MinIO |->| PG sec |
              +--------+  +-------+  +-------+  +--------+
                   |                     |           |
              +--------+            (bucket     +-------+
              | FS pri |            repl)       | Redis |
              +--------+                        +-------+
                                                     |
                                                +--------+
                                                | FS stby|
                                                +--------+
```

---

## Architecture Details

### Region Layout

| Component | Region A (Primary) | Region B (Secondary) |
|---|---|---|
| PostgreSQL | Read-write primary | Logical replication subscriber (read-only) |
| Redis | Master + slave + 3 sentinels | Independent master (rebuilt on promotion) |
| MinIO | Primary buckets | Replicated buckets (read-only) |
| FreeSWITCH | Active, handles all calls | Standby, ready to activate |
| API | 2 replicas, serves all traffic | 2 replicas, idle (health checks only) |
| Web UI | Served from Region A | Served from Region B (inactive DNS) |
| Monitoring | Full Prometheus/Grafana stack | Full stack monitoring local services |

### Why Logical Replication (Not Streaming)

Cross-region PostgreSQL uses logical replication instead of streaming replication because:
- Tolerates higher network latency without blocking primary commits
- Allows schema differences (e.g., secondary can have extra indexes for read queries)
- Selective replication possible (skip ephemeral tables)
- Secondary can be writable during split-brain recovery if needed

Trade-off: logical replication has slightly higher lag than streaming (seconds vs. sub-second), but stays within the 1-hour RPO target.

---

## Active-Passive vs Active-Active

### Current Design: Active-Passive (Recommended)

The New Phone platform uses an **active-passive** model:
- **Region A** handles all traffic (API, SIP, media, web)
- **Region B** receives replicated data and runs idle services ready for promotion
- Failover is DNS-based with ~90 second cutover

**Advantages:**
- Simpler to operate and reason about
- No split-brain risk for database writes
- No cross-region latency on API calls or SIP signaling
- Lower cost (secondary region runs minimal compute until activated)

### Active-Active Considerations

An active-active model where both regions serve traffic simultaneously is possible but introduces significant complexity:

**Challenges for voice/PBX:**
- SIP registrations must be region-local (phones register to nearest region)
- Active calls cannot span regions (RTP media must stay local)
- Call transfers between regions require SIP peering between FreeSWITCH instances
- Queue state must be globally consistent (agents in different regions serving same queue)

**Challenges for data:**
- PostgreSQL multi-master replication (BDR/Citus) adds operational complexity
- Conflict resolution for concurrent writes to same tenant data
- Sequence/ID generation must be globally unique (UUIDs or region-prefixed IDs)
- Redis cache invalidation across regions

**When active-active makes sense:**
- Tenants are geographically distributed and need low-latency voice in multiple regions
- Single-region capacity is insufficient
- Regulatory requirements mandate data processing in specific regions

**Recommendation:** Stay with active-passive until tenant count or geographic distribution demands active-active. The active-passive model meets the 4-hour RTO / 1-hour RPO targets and is far simpler to operate.

---

## DNS-Based Failover

### DNS Configuration

Use a DNS provider with health checks and failover (Route 53, Cloudflare, etc.).

| Record | Type | Primary Value | Secondary Value | TTL |
|---|---|---|---|---|
| `api.newphone.example.com` | A | Region A API IP | Region B API IP | 60s |
| `sip.newphone.example.com` | A | Region A FS IP | Region B FS IP | 60s |
| `pbx.newphone.example.com` | A | Region A Web IP | Region B Web IP | 60s |
| `minio.newphone.example.com` | A | Region A MinIO IP | Region B MinIO IP | 300s |

### Health Check Configuration

Configure DNS health checks against each region:

```
Health check: api.newphone.example.com
  Protocol: HTTPS
  Path: /api/v1/health
  Port: 443
  Interval: 10s
  Failure threshold: 3 consecutive failures
  Success threshold: 2 consecutive successes
```

### Failover Behavior

1. DNS health check detects Region A is down (3 consecutive failures = 30 seconds)
2. DNS updates to point to Region B (propagation: 60 seconds with low TTL)
3. Total DNS-level failover: ~90 seconds
4. SIP endpoints using DNS hostnames re-register automatically
5. Web/API clients retry and connect to Region B

### Pre-requisites for Fast DNS Failover

- DNS TTL must be set to 60 seconds **in advance** (not during the incident)
- SIP phones must use DNS hostnames, not hardcoded IPs
- Web UI must use relative API paths (same hostname)
- SSL certificates must be valid for both regions (use wildcard or SAN cert)

---

## Cross-Region PostgreSQL Logical Replication

### Setup on Primary (Region A)

```sql
-- 1. Enable logical replication (requires restart)
-- In postgresql.conf or docker command:
--   wal_level = logical
--   max_replication_slots = 10
--   max_wal_senders = 10

-- 2. Create publication for all tables
CREATE PUBLICATION np_full_publication FOR ALL TABLES;

-- 3. Create replication slot (optional, for monitoring)
SELECT pg_create_logical_replication_slot('region_b_slot', 'pgoutput');
```

### Setup on Secondary (Region B)

```sql
-- 1. Create the same schema (run migrations)
-- Use: alembic upgrade head

-- 2. Create subscription
CREATE SUBSCRIPTION np_region_b_sub
  CONNECTION 'host=<region-a-pg-ip> port=5432 dbname=new_phone user=replicator password=<password> sslmode=require'
  PUBLICATION np_full_publication
  WITH (
    copy_data = true,          -- Initial data copy
    create_slot = true,        -- Create replication slot on primary
    slot_name = 'region_b_slot',
    synchronous_commit = off   -- Async for cross-region performance
  );
```

### Monitoring Replication Lag

```sql
-- On primary: check replication slot lag
SELECT
  slot_name,
  pg_wal_lsn_diff(pg_current_wal_lsn(), confirmed_flush_lsn) AS lag_bytes,
  pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), confirmed_flush_lsn)) AS lag_pretty
FROM pg_replication_slots
WHERE slot_name = 'region_b_slot';

-- On secondary: check subscription status
SELECT
  subname,
  received_lsn,
  latest_end_lsn,
  latest_end_time
FROM pg_stat_subscription;
```

### Promoting Secondary to Primary

```sql
-- On secondary (Region B):
-- 1. Disable subscription (stop receiving from old primary)
ALTER SUBSCRIPTION np_region_b_sub DISABLE;
DROP SUBSCRIPTION np_region_b_sub;

-- 2. Database is now writable — verify
CREATE TABLE dr_promotion_test(); DROP TABLE dr_promotion_test;

-- 3. Update sequences if needed (logical replication does not replicate sequences)
-- Run: SELECT setval(seq_name, max_val + 1000) for all sequences
-- The +1000 buffer prevents ID collisions from any in-flight transactions
```

---

## MinIO Bucket Replication

### Setup Site Replication

```bash
# Add aliases for both regions
mc alias set region-a https://minio-a.newphone.example.com minioadmin <password>
mc alias set region-b https://minio-b.newphone.example.com minioadmin <password>

# Enable site replication (bidirectional sync)
mc admin replicate add region-a region-b

# Verify replication status
mc admin replicate status region-a
```

### Alternative: mc mirror (One-Way)

For simpler one-way replication:

```bash
# Continuous mirror from primary to secondary
mc mirror --watch --overwrite region-a/recordings region-b/recordings &
mc mirror --watch --overwrite region-a/voicemail region-b/voicemail &
mc mirror --watch --overwrite region-a/fax region-b/fax &
```

### Hourly Incremental Sync (Cron)

```bash
# Add to crontab on Region A
0 * * * * mc mirror --newer-than 2h --overwrite region-a/recordings region-b/recordings >> /var/log/minio-sync.log 2>&1
0 * * * * mc mirror --newer-than 2h --overwrite region-a/voicemail region-b/voicemail >> /var/log/minio-sync.log 2>&1
```

---

## Session and State Management Across Regions

### Stateless Components (No Cross-Region Sync Needed)

- **API servers**: stateless, JWT-based auth. Any instance in any region can handle requests.
- **Web UI**: static build, served from either region.

### Stateful Components

| State | Storage | Cross-Region Strategy |
|---|---|---|
| User sessions / JWT tokens | Stateless (JWT) | No sync needed — tokens are self-contained |
| Active calls | FreeSWITCH memory | Not replicated — calls drop on failover |
| Call recordings | MinIO | Bucket replication (see above) |
| CDR / call logs | PostgreSQL | Logical replication |
| Voicemail | MinIO + PostgreSQL metadata | Both replicated |
| SMS conversations | PostgreSQL | Logical replication |
| Tenant config | PostgreSQL | Logical replication |
| SIP registrations | PostgreSQL (via xml_curl) | Logical replication |
| Redis cache | Redis | Not replicated — rebuilt on failover |
| Redis pub/sub channels | Redis | Not replicated — reconnect on failover |

### Active Call Handling During Failover

Active calls in progress **will be dropped** during a region failover. This is inherent to SIP/RTP — media streams cannot be migrated between FreeSWITCH instances. Mitigation strategies:

1. SIP endpoints will re-register to the new region via DNS
2. Calls in queue will be re-queued when agents reconnect
3. CDRs for interrupted calls are written to PostgreSQL (replicated)
4. Callers can redial and reach the secondary region

---

## Data Residency Considerations

### Tenant Data Location

For regulatory compliance (GDPR, CCPA, PIPEDA, etc.):

- **Default**: all tenant data stored in the primary region
- **Replication**: secondary region receives copies for DR purposes only
- **Encryption at rest**: all data encrypted in both regions (PostgreSQL TDE, MinIO server-side encryption)
- **Encryption in transit**: TLS between regions for all replication traffic

### Restricting Data Replication by Tenant

If a tenant requires data to stay in a specific region:

1. Use PostgreSQL logical replication with publication filtering:
   ```sql
   -- Exclude specific tenant data from cross-region replication
   CREATE PUBLICATION np_dr_publication FOR ALL TABLES
     WHERE (tenant_id NOT IN ('restricted-tenant-uuid'));
   ```

2. MinIO: use separate buckets per restricted tenant, exclude from replication

3. Document tenant-specific residency requirements in the tenant configuration table

### Compliance Checklist

```
[ ] Data processing agreements updated to cover secondary region
[ ] Secondary region meets same compliance certifications as primary
[ ] Encryption at rest enabled in both regions
[ ] Encryption in transit (TLS) for all cross-region traffic
[ ] Audit logs replicated to both regions
[ ] Data retention policies enforced in both regions
[ ] Tenant notification about data residency in ToS
```

---

## Network Requirements

### Latency

| Path | Maximum Acceptable Latency | Notes |
|---|---|---|
| Region A <-> Region B (replication) | < 100ms RTT | Higher latency increases replication lag |
| Client <-> Active Region (API) | < 200ms RTT | End-user experience target |
| Client <-> Active Region (SIP/RTP) | < 150ms one-way | Voice quality degrades above this |
| Region A PG <-> Region B PG | < 50ms RTT | For logical replication slot health |

### Bandwidth

| Flow | Estimated Bandwidth | Calculation |
|---|---|---|
| PostgreSQL logical replication | 1-10 Mbps | Depends on write volume |
| MinIO bucket replication | 10-50 Mbps | Based on recording volume (~50 concurrent calls) |
| WAL archive shipping | 1-5 Mbps | Continuous WAL segments |
| Redis RDB snapshots (every 15 min) | Burst: 50 Mbps | ~50 MB RDB, transferred in 8 seconds |
| **Total sustained** | **15-70 Mbps** | Size appropriately for peak |

### Network Security

- All cross-region traffic over VPN or private peering (WireGuard, IPsec, cloud VPC peering)
- PostgreSQL replication over SSL (`sslmode=require`)
- MinIO replication over TLS
- No replication traffic over public internet without encryption

### Firewall Rules (Region A -> Region B)

| Source | Destination | Port | Protocol | Purpose |
|---|---|---|---|---|
| PG primary | PG secondary | 5432 | TCP/TLS | Logical replication |
| MinIO primary | MinIO secondary | 9000 | TCP/TLS | Bucket replication |
| Monitoring | All services | various | TCP | Prometheus scraping |

### Firewall Rules (Region B -> Region A)

| Source | Destination | Port | Protocol | Purpose |
|---|---|---|---|---|
| PG secondary | PG primary | 5432 | TCP/TLS | Subscription connection |
| MinIO secondary | MinIO primary | 9000 | TCP/TLS | Sync status |

---

## SIP Trunk Regional Configuration

### Provider Setup per Region

Each region needs its own SIP trunk termination to avoid cross-region media paths:

| Provider | Region A | Region B |
|---|---|---|
| ClearlyIP | Trunk pointed to Region A FreeSWITCH IP | Trunk pointed to Region B FreeSWITCH IP |
| Twilio | Elastic SIP Trunk with Region A origination URI | Elastic SIP Trunk with Region B origination URI |

### ClearlyIP Configuration

ClearlyIP trunks are configured per-DID. During failover:

1. Update DID routing in ClearlyIP portal to point to Region B FreeSWITCH IP
2. Alternatively, use ClearlyIP's failover destination feature:
   - Primary destination: Region A FreeSWITCH
   - Failover destination: Region B FreeSWITCH
   - Failover trigger: primary unreachable for 30 seconds

### Twilio Configuration

Twilio Elastic SIP Trunking supports multiple origination URIs with priority/weight:

```
Origination URI: sip:sip-a.newphone.example.com:5061;transport=tls
  Priority: 10, Weight: 100, Enabled: true

Origination URI: sip:sip-b.newphone.example.com:5061;transport=tls
  Priority: 20, Weight: 100, Enabled: true
```

Twilio automatically fails over to the lower-priority URI when the primary is unreachable. No manual intervention required for inbound call routing.

### Outbound Calls During Failover

Outbound calls from Region B use the same SIP trunk credentials. Ensure:
- Region B FreeSWITCH has the same gateway configurations (shared via `fs_gateways` volume or MinIO sync)
- Trunk provider ACLs/IP allowlists include Region B's public IP
- STIR/SHAKEN attestation certificates are available in both regions

### Media Server Regional Deployment

FreeSWITCH must run in each region to keep RTP media local:
- RTP media adds ~87 kbps per call (G.711) -- routing media cross-region wastes bandwidth and adds latency
- Each region's FreeSWITCH connects to its local API instance via xml_curl
- Recordings are written to the local MinIO instance and replicated cross-region
- Codec negotiation and SRTP are handled identically in both regions

---

## Deployment Procedure

### Initial Secondary Region Setup

```
Phase 1: Infrastructure (Day 1)
1. [ ] Provision Docker host(s) in Region B
2. [ ] Set up VPN/peering between Region A and Region B
3. [ ] Verify network connectivity and latency
4. [ ] Configure firewall rules (see above)
5. [ ] Install Docker Engine + Compose V2
6. [ ] Clone repository to Region B host

Phase 2: Data Layer (Day 1-2)
7.  [ ] Deploy PostgreSQL in Region B
8.  [ ] Run migrations (alembic upgrade head)
9.  [ ] Set up logical replication subscription
10. [ ] Wait for initial data copy to complete
11. [ ] Verify replication lag is within RPO target
12. [ ] Deploy MinIO in Region B
13. [ ] Configure bucket replication
14. [ ] Wait for initial bucket sync to complete
15. [ ] Deploy Redis in Region B

Phase 3: Application Layer (Day 2)
16. [ ] Deploy API instances in Region B (idle mode)
17. [ ] Deploy Web UI in Region B
18. [ ] Deploy FreeSWITCH standby in Region B
19. [ ] Deploy monitoring stack in Region B
20. [ ] Configure health checks for Region B services

Phase 4: DNS & Failover (Day 2-3)
21. [ ] Configure DNS failover records (low TTL)
22. [ ] Configure DNS health checks
23. [ ] Test failover by stopping Region A health check endpoint
24. [ ] Verify DNS cuts over to Region B
25. [ ] Test rollback (restore Region A, verify DNS returns)

Phase 5: Validation (Day 3)
26. [ ] Run full DR test (see dr-runbook.md)
27. [ ] Verify RTO and RPO met
28. [ ] Document any issues and remediate
29. [ ] Set up alerting for replication lag
30. [ ] Schedule quarterly DR tests
```

### Ongoing Operations

| Task | Frequency | Owner |
|---|---|---|
| Monitor replication lag | Continuous (alerting) | Prometheus/Grafana |
| Verify backups in secondary region | Weekly | Automated + manual review |
| DR failover test | Quarterly | Platform team |
| Network latency check | Daily (automated) | Monitoring |
| SSL certificate renewal | Before expiry | Automated (certbot/ACME) |
| Security patching | Monthly | Platform team |
| Capacity review | Monthly | Platform team |
