# Disaster Recovery Runbook

## Recovery Objectives

| Metric | Target | Notes |
|---|---|---|
| **RTO** (Recovery Time Objective) | 4 hours | Time from disaster declaration to service restored |
| **RPO** (Recovery Point Objective) | 1 hour | Maximum acceptable data loss window |

---

## Backup Schedule

### PostgreSQL

| Type | Frequency | Retention | Storage |
|---|---|---|---|
| Continuous WAL archiving | Real-time | 7 days | MinIO `np-wal-archive` bucket |
| Full `pg_dump` | Daily at 02:00 UTC | 7 daily, 4 weekly, 12 monthly | MinIO `np-db-backups` bucket |
| Streaming replication | Continuous | N/A (live standby) | `pg-standby` volume |

### Redis

| Type | Frequency | Retention | Storage |
|---|---|---|---|
| RDB snapshot | Every 30 minutes | 48 hours (96 snapshots) | MinIO `np-redis-backups` bucket |
| AOF persistence | Continuous (on master + slave) | Current only | Local volume |

### MinIO (Recordings, Voicemail, Fax)

| Type | Frequency | Retention | Storage |
|---|---|---|---|
| Bucket replication | Hourly incremental | Indefinite (same as source) | Secondary MinIO or S3 |
| Full bucket sync | Weekly (Sunday 03:00 UTC) | 4 weekly | Cross-region S3 bucket |

### FreeSWITCH Configuration

| Type | Frequency | Retention | Storage |
|---|---|---|---|
| Config directory tarball | Daily at 01:00 UTC | 30 daily | MinIO `np-config-backups` bucket |
| TLS certificates | On change (inotify trigger) | 5 versions | MinIO `np-config-backups` bucket |

### Application Configuration

| Type | Frequency | Retention | Storage |
|---|---|---|---|
| Docker Compose + env files | On change (git commit) | Full git history | Git repository |
| Prometheus/Grafana config | Daily | 30 daily | MinIO `np-config-backups` bucket |

---

## Automated Backup Script

The primary backup script is `scripts/backup-db.sh`. It handles:
- PostgreSQL full dumps with compression
- Upload to MinIO with retention policy enforcement
- Backup verification (restore to temp DB and run schema check)
- Error notification via webhook

### Running backups

```bash
# Manual full backup
./scripts/backup-db.sh

# Cron entry (add to Docker host crontab)
0 2 * * * /path/to/new-phone/scripts/backup-db.sh >> /var/log/np-backup.log 2>&1
```

---

## Backup Verification Procedures

### Daily Automated Verification

The `backup-db.sh` script automatically verifies each backup by:
1. Restoring the dump to a temporary database (`np_backup_verify`)
2. Checking that all expected tables exist
3. Running a row count comparison on critical tables
4. Dropping the temporary database
5. Recording pass/fail in the backup log

### Weekly Manual Verification (Recommended)

```bash
# 1. Download the latest backup from MinIO
mc cp minio/np-db-backups/daily/$(date -u +%Y-%m-%d)-new_phone.sql.gz /tmp/

# 2. Restore to a test instance
gunzip -c /tmp/$(date -u +%Y-%m-%d)-new_phone.sql.gz | \
  docker exec -i <test-pg-container> psql -U new_phone_admin -d np_test_restore

# 3. Run the API health check against test DB
NP_DB_HOST=<test-pg-host> NP_DB_NAME=np_test_restore python -c "
from api.db import get_engine
engine = get_engine()
with engine.connect() as conn:
    result = conn.execute('SELECT count(*) FROM tenants')
    print(f'Tenants: {result.scalar()}')
"

# 4. Verify recording files exist in MinIO backup
mc ls minio-backup/np-recordings-backup/ --summarize
```

### Quarterly Full DR Test

See "DR Testing Procedure" section below.

---

## Cross-Region Replication Setup

For multi-region DR, see `docs/multi-region.md` for full architecture. Summary:

- PostgreSQL: logical replication to secondary region (async, lag < 1 hour)
- MinIO: bucket replication via `mc mirror --watch` or MinIO site replication
- Redis: not replicated cross-region (rebuilt from PG on recovery)
- FreeSWITCH config: synced via MinIO config bucket

---

## DR Failover Step-by-Step

### Triggering Criteria

Declare a DR event when:
- Primary region is completely unreachable for > 10 minutes
- Data corruption detected that cannot be fixed in place
- Infrastructure provider declares an outage with ETA > 2 hours

### Phase 1: Assessment (0-5 minutes)

```
1. [ ] Confirm primary region is actually down (not a monitoring false positive)
      - Check from multiple network paths
      - Verify with infrastructure provider status page
2. [ ] Notify the DR lead and on-call engineer
3. [ ] Open incident channel (Slack/Teams #incident-YYYYMMDD)
4. [ ] Decision: declare DR event or wait
```

### Phase 2: Activate Secondary (5-20 minutes)

```
1. [ ] SSH to secondary region Docker host

2. [ ] Verify latest backup availability:
      mc ls minio-dr/np-db-backups/daily/ | tail -5
      mc ls minio-dr/np-wal-archive/ | tail -20

3. [ ] Restore PostgreSQL from latest backup:
      # If using cross-region streaming replication, promote standby:
      docker exec <pg-standby> pg_ctl promote -D /var/lib/postgresql/data

      # If restoring from backup:
      gunzip -c latest-backup.sql.gz | docker exec -i pg psql -U new_phone_admin -d new_phone

4. [ ] Restore Redis from latest RDB:
      mc cp minio-dr/np-redis-backups/latest/dump.rdb /tmp/
      docker cp /tmp/dump.rdb redis:/data/dump.rdb
      docker restart redis

5. [ ] Verify MinIO bucket replication is current:
      mc ls minio-dr/recordings/ --summarize

6. [ ] Start application services:
      docker compose -f docker-compose.yml up -d api web freeswitch ai-engine

7. [ ] Run health checks:
      curl -f http://localhost:8000/api/v1/health
      docker exec freeswitch fs_cli -x "status"
```

### Phase 3: DNS Cutover (20-30 minutes)

```
1. [ ] Update DNS records to point to secondary region IPs:
      - api.newphone.example.com -> secondary API IP
      - sip.newphone.example.com -> secondary FreeSWITCH IP
      - pbx.newphone.example.com -> secondary web IP

2. [ ] Reduce DNS TTL to 60s (should have been pre-set, verify)

3. [ ] Wait for DNS propagation (check from multiple resolvers):
      dig +short api.newphone.example.com @8.8.8.8
      dig +short api.newphone.example.com @1.1.1.1

4. [ ] Update SIP trunk provider routing (ClearlyIP/Twilio):
      - Point inbound routes to secondary FreeSWITCH IP
      - Verify outbound calls route correctly

5. [ ] Notify SIP phone endpoints to re-register:
      - Phones with DNS hostnames will follow DNS automatically
      - Phones with hard-coded IPs need manual config push
```

### Phase 4: Validation (30-45 minutes)

```
1. [ ] Test inbound call flow end-to-end
2. [ ] Test outbound call flow end-to-end
3. [ ] Test web UI login and basic operations
4. [ ] Test voicemail deposit and retrieval
5. [ ] Test SMS send and receive
6. [ ] Verify all tenant data is accessible
7. [ ] Check monitoring dashboards are populated
8. [ ] Verify call recordings are accessible
```

### Phase 5: Stabilize (45-60 minutes)

```
1. [ ] Enable backup schedule on DR site
2. [ ] Set up monitoring alerts for DR site
3. [ ] Document any data loss (compare WAL position / timestamps)
4. [ ] Communicate status to stakeholders
5. [ ] Plan primary region recovery (when available)
```

---

## Recovery Procedures Per Component

### PostgreSQL Recovery

**From streaming replication (fastest, lowest data loss):**

```bash
# Promote standby
docker exec <pg-standby> pg_ctl promote -D /var/lib/postgresql/data
# Verify it accepts writes
docker exec <pg-standby> psql -U new_phone_admin -d new_phone -c "CREATE TABLE dr_test(); DROP TABLE dr_test;"
```

**From WAL archive (point-in-time recovery):**

```bash
# 1. Get base backup + WAL files
mc cp --recursive minio/np-db-backups/daily/latest/ /tmp/pg-restore/
mc cp --recursive minio/np-wal-archive/ /tmp/pg-wal/

# 2. Configure recovery.conf (PG 17 uses postgresql.auto.conf)
cat >> /tmp/pg-restore/postgresql.auto.conf <<EOF
restore_command = 'cp /wal-archive/%f %p'
recovery_target_time = '2026-03-04 12:00:00 UTC'
recovery_target_action = 'promote'
EOF

# 3. Start postgres with recovery
docker run -v /tmp/pg-restore:/var/lib/postgresql/data \
           -v /tmp/pg-wal:/wal-archive \
           postgres:17-bookworm
```

**From pg_dump (cold restore):**

```bash
# Create fresh database
docker exec <pg-container> createdb -U new_phone_admin new_phone

# Restore
gunzip -c backup.sql.gz | docker exec -i <pg-container> psql -U new_phone_admin -d new_phone
```

### Redis Recovery

```bash
# From RDB snapshot
docker cp dump.rdb <redis-container>:/data/dump.rdb
docker restart <redis-container>

# Verify
docker exec <redis-container> redis-cli dbsize
```

### MinIO Recovery

```bash
# From replicated bucket
mc mirror minio-dr/recordings/ minio-primary/recordings/

# From S3 backup
mc mirror s3/np-recordings-backup/ minio-primary/recordings/
```

### FreeSWITCH Recovery

```bash
# FreeSWITCH is stateless — config comes from xml_curl (API + PostgreSQL)
# Just start a fresh instance and it will pull config from the API

docker compose up -d freeswitch

# Verify
docker exec <fs-container> fs_cli -x "sofia status"
```

---

## DR Testing Procedure (Quarterly)

### Schedule
- **Frequency:** Every quarter (January, April, July, October)
- **Window:** Saturday 06:00-12:00 UTC (low traffic)
- **Duration:** 4-6 hours including rollback

### Test Plan

```
Pre-test (Week before):
1. [ ] Announce maintenance window to tenants
2. [ ] Verify all backups are current and verified
3. [ ] Confirm DR environment is provisioned and accessible
4. [ ] Prepare rollback plan

Test execution:
1. [ ] Take fresh backup of all components
2. [ ] Simulate primary failure (stop primary services)
3. [ ] Execute DR failover procedure (timed)
4. [ ] Record actual RTO (time to first successful health check)
5. [ ] Run validation checklist from Phase 4 above
6. [ ] Test 5 inbound calls across different tenants
7. [ ] Test 5 outbound calls across different tenants
8. [ ] Verify voicemail, recording playback, SMS
9. [ ] Measure data loss (compare with RPO target)
10. [ ] Document issues encountered

Rollback:
1. [ ] Restore primary services
2. [ ] Verify primary is healthy
3. [ ] Cut DNS back to primary
4. [ ] Verify all services normal
5. [ ] Debrief and update runbook with lessons learned
```

### Test Report Template

```markdown
# DR Test Report — YYYY-QN

**Date:** YYYY-MM-DD
**Participants:** [names]
**Result:** PASS / FAIL

## Metrics
- Actual RTO: XX minutes (target: 4 hours / 240 minutes)
- Actual RPO: XX minutes (target: 1 hour / 60 minutes)
- Data loss: None / [describe]

## Issues Found
1. [issue] — [resolution]

## Action Items
1. [ ] [action] — owner: [name] — due: [date]

## Runbook Updates
- [changes made to this document]
```

---

## Communication Plan During DR Event

### Notification Chain

| Time | Action | Who | Channel |
|---|---|---|---|
| T+0 min | DR declared | On-call engineer | PagerDuty / phone |
| T+2 min | Incident channel opened | On-call engineer | Slack #incident |
| T+5 min | Team notified | DR lead | Slack #incident |
| T+10 min | Management notified | DR lead | Email + Slack DM |
| T+15 min | Initial tenant notification | Support lead | Email blast |
| T+30 min | Status update (ETA) | DR lead | Slack #incident + tenant email |
| T+60 min | Service restored or escalation | DR lead | All channels |
| T+N | Post-incident review scheduled | DR lead | Calendar invite |

### Tenant Communication Templates

**Initial notification:**
> Subject: [New Phone] Service Disruption — We Are Working On It
>
> We are experiencing a service disruption affecting phone services.
> Our team is actively working to restore service. Estimated recovery: within 4 hours.
> We will provide updates every 30 minutes.

**Resolution notification:**
> Subject: [New Phone] Service Restored
>
> Phone services have been fully restored as of [TIME UTC].
> If you experience any issues, please contact support.
> A post-incident report will follow within 48 hours.

---

## Appendix: Backup Storage Layout (MinIO)

```
np-db-backups/
  daily/
    2026-03-04-new_phone.sql.gz
    2026-03-03-new_phone.sql.gz
    ...
  weekly/
    2026-W09-new_phone.sql.gz
    ...
  monthly/
    2026-03-new_phone.sql.gz
    ...

np-wal-archive/
  0000000100000000000000A1
  0000000100000000000000A2
  ...

np-redis-backups/
  2026-03-04T02-00/dump.rdb
  2026-03-04T02-15/dump.rdb
  ...

np-config-backups/
  freeswitch/
    2026-03-04-freeswitch-conf.tar.gz
  monitoring/
    2026-03-04-prometheus.tar.gz
    2026-03-04-grafana.tar.gz
```
