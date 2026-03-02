# Backup and Restore Procedures

This document covers backup strategies, automated backup scripts, restore procedures, and disaster recovery planning for the Aspendora Connect PBX platform.

---

## 1. What Needs Backup

| Data | Location | Priority | Method |
|------|----------|----------|--------|
| PostgreSQL database | `new_phone_pg_data` volume | **Critical** | `pg_dump` (daily) |
| MinIO object storage | `new_phone_minio_data` volume | **Critical** | `mc mirror` (daily) |
| Environment file | `/opt/new-phone/.env` | **Critical** | File copy |
| TLS certificates | `/etc/letsencrypt/` | **High** | File copy (or re-issue) |
| FreeSWITCH config/data | `new_phone_fs_data` volume | **High** | Volume backup |
| Custom FreeSWITCH TLS | `/opt/new-phone/freeswitch/tls/` | **High** | File copy |
| Prometheus metrics | `new_phone_prometheus_data` volume | Low | Volume backup (optional) |
| Grafana dashboards | `new_phone_grafana_data` volume | Low | Volume backup (provisioned from files) |
| Redis data | `new_phone_redis_data` volume | Low | Ephemeral cache (skip unless session persistence needed) |

**Do NOT back up** source code via these procedures. Source code lives in version control (git).

---

## 2. Backup Directory Structure

```
/backups/
  postgres/          # pg_dump files
  minio/             # mc mirror destination
  volumes/           # docker volume tarballs
  config/            # .env, TLS certs, nginx config
  logs/              # backup operation logs
```

Create the structure:

```bash
sudo mkdir -p /backups/{postgres,minio,volumes,config,logs}
sudo chown -R $USER:$USER /backups
```

---

## 3. Automated PostgreSQL Backup

### 3.1 Backup Script

The script is at `scripts/backup-db.sh`. It performs a compressed `pg_dump` in custom format and rotates old backups.

```bash
# Make executable (if not already)
chmod +x /opt/new-phone/scripts/backup-db.sh

# Run manually
cd /opt/new-phone && ./scripts/backup-db.sh

# With custom settings
BACKUP_DIR=/backups/postgres RETENTION_DAYS=14 ./scripts/backup-db.sh
```

### 3.2 Cron Job (Daily at 2:00 AM)

```bash
# Edit crontab
crontab -e
```

Add:

```cron
# Daily PostgreSQL backup at 2:00 AM
0 2 * * * cd /opt/new-phone && BACKUP_DIR=/backups/postgres RETENTION_DAYS=7 ./scripts/backup-db.sh >> /backups/logs/db-backup.log 2>&1

# Weekly full backup (keep 4 weeks) on Sunday at 3:00 AM
0 3 * * 0 cd /opt/new-phone && BACKUP_DIR=/backups/postgres/weekly RETENTION_DAYS=28 ./scripts/backup-db.sh >> /backups/logs/db-backup.log 2>&1

# Monthly backup (keep 12 months) on 1st at 4:00 AM
0 4 1 * * cd /opt/new-phone && BACKUP_DIR=/backups/postgres/monthly RETENTION_DAYS=365 ./scripts/backup-db.sh >> /backups/logs/db-backup.log 2>&1
```

### 3.3 Verify Backups

Always verify that backup files are valid and restorable:

```bash
# List recent backups
ls -lh /backups/postgres/

# Verify a backup file is valid (reads the TOC without restoring)
docker compose exec -T postgres pg_restore --list < /backups/postgres/new_phone_20260302_020000.dump | head -20

# Check file size (should be non-zero and roughly consistent)
du -h /backups/postgres/*.dump
```

### 3.4 Retention Summary

| Tier | Frequency | Retention | Location |
|------|-----------|-----------|----------|
| Daily | Every day at 2 AM | 7 days | `/backups/postgres/` |
| Weekly | Sunday at 3 AM | 4 weeks | `/backups/postgres/weekly/` |
| Monthly | 1st of month at 4 AM | 12 months | `/backups/postgres/monthly/` |
| Off-site | Synced after daily | 30 days | S3/remote (see section 7) |

---

## 4. Restore Procedures

### 4.1 Full Database Restore

Use `scripts/restore-db.sh` for a guided restore:

```bash
cd /opt/new-phone
./scripts/restore-db.sh /backups/postgres/new_phone_20260302_020000.dump
```

The script will:
1. Prompt for confirmation (destructive operation)
2. Run `pg_restore --clean --if-exists` to replace the current database
3. Run `alembic upgrade head` to ensure schema is current

### 4.2 Manual Restore Steps

If you need more control over the restore process:

```bash
cd /opt/new-phone

# 1. Stop the API to prevent writes during restore
docker compose stop api ai-engine

# 2. Drop and recreate connections (optional, for clean state)
docker compose exec -T postgres psql -U new_phone_admin -d postgres -c "
  SELECT pg_terminate_backend(pid) FROM pg_stat_activity
  WHERE datname = 'new_phone' AND pid <> pg_backend_pid();
"

# 3. Restore from backup
docker compose exec -T postgres pg_restore \
  -U new_phone_admin \
  -d new_phone \
  --clean \
  --if-exists \
  --no-owner \
  --no-privileges \
  < /backups/postgres/new_phone_20260302_020000.dump

# 4. Verify RLS policies and app user permissions
docker compose exec -T postgres psql -U new_phone_admin -d new_phone -c "
  SELECT schemaname, tablename, policyname FROM pg_policies ORDER BY tablename;
"

# 5. Run migrations to catch up if needed
docker compose exec api alembic upgrade head

# 6. Restart services
docker compose start api ai-engine

# 7. Verify
curl -s https://pbx.example.com/api/v1/health | jq .
```

### 4.3 Restore a Single Table

```bash
# List tables in the backup
docker compose exec -T postgres pg_restore --list < /backups/postgres/new_phone_20260302_020000.dump | grep "TABLE DATA"

# Restore only one table (e.g., call_detail_records)
docker compose exec -T postgres pg_restore \
  -U new_phone_admin \
  -d new_phone \
  --data-only \
  --table=call_detail_records \
  < /backups/postgres/new_phone_20260302_020000.dump
```

### 4.4 Restore to a New Server

To restore onto a fresh server:

```bash
# On the new server, after completing initial deployment (sections 1-6 of deployment.md):

cd /opt/new-phone

# 1. Start only postgres
docker compose up -d postgres
# Wait for healthy
docker compose exec postgres pg_isready

# 2. Copy backup file to the new server
scp user@old-server:/backups/postgres/new_phone_latest.dump /backups/postgres/

# 3. The init scripts in db/init/ create the app user and RLS setup.
#    Wait for those to complete on first startup, then restore data:
docker compose exec -T postgres pg_restore \
  -U new_phone_admin \
  -d new_phone \
  --clean \
  --if-exists \
  < /backups/postgres/new_phone_latest.dump

# 4. Start the rest of the stack
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 5. Run migrations
docker compose exec api alembic upgrade head

# 6. Verify
docker compose ps
curl -s http://localhost:8000/api/v1/health | jq .
```

---

## 5. MinIO Object Storage Backup

### 5.1 Configure MinIO Client

```bash
# Install mc (MinIO client) on the host
curl -O https://dl.min.io/client/mc/release/linux-amd64/mc
chmod +x mc
sudo mv mc /usr/local/bin/

# Configure alias for local MinIO
mc alias set newphone http://127.0.0.1:9000 "$NP_MINIO_ACCESS_KEY" "$NP_MINIO_SECRET_KEY"

# Verify connection
mc ls newphone/
```

### 5.2 Mirror to Local Backup

```bash
# Full mirror (copies all objects, skips existing unchanged files)
mc mirror newphone/recordings /backups/minio/recordings/

# Mirror all buckets
mc mirror newphone/ /backups/minio/
```

### 5.3 Automated MinIO Backup

Add to crontab alongside the database backup:

```cron
# Daily MinIO mirror at 2:30 AM
30 2 * * * /usr/local/bin/mc mirror --overwrite newphone/ /backups/minio/ >> /backups/logs/minio-backup.log 2>&1
```

### 5.4 MinIO Restore

```bash
# Restore all objects back to MinIO
mc mirror /backups/minio/recordings/ newphone/recordings/

# Restore a specific file
mc cp /backups/minio/recordings/tenant-abc/2026/03/call-123.wav newphone/recordings/tenant-abc/2026/03/call-123.wav
```

### 5.5 Enable Versioning (Recommended)

Object versioning protects against accidental overwrites and deletions:

```bash
mc version enable newphone/recordings
```

---

## 6. Docker Volume Backup

For volumes that do not have a native export tool (FreeSWITCH data, Grafana, Prometheus):

### 6.1 Backup a Named Volume

```bash
# Generic volume backup using a temporary container
backup_volume() {
  local VOLUME_NAME=$1
  local BACKUP_FILE="/backups/volumes/${VOLUME_NAME}_$(date +%Y%m%d_%H%M%S).tar.gz"
  docker run --rm \
    -v "${VOLUME_NAME}:/source:ro" \
    -v /backups/volumes:/backup \
    alpine \
    tar czf "/backup/$(basename $BACKUP_FILE)" -C /source .
  echo "Backed up $VOLUME_NAME to $BACKUP_FILE"
}

# Backup specific volumes
backup_volume new_phone_fs_data
backup_volume new_phone_grafana_data
backup_volume new_phone_prometheus_data
```

### 6.2 Restore a Named Volume

```bash
# Restore a volume from backup
restore_volume() {
  local VOLUME_NAME=$1
  local BACKUP_FILE=$2
  echo "WARNING: This will overwrite all data in volume $VOLUME_NAME"
  read -p "Continue? (yes/no): " confirm
  if [ "$confirm" != "yes" ]; then echo "Aborted."; return 1; fi
  docker run --rm \
    -v "${VOLUME_NAME}:/target" \
    -v "$(dirname $BACKUP_FILE):/backup:ro" \
    alpine \
    sh -c "rm -rf /target/* && tar xzf /backup/$(basename $BACKUP_FILE) -C /target"
  echo "Restored $VOLUME_NAME from $BACKUP_FILE"
}

# Example
restore_volume new_phone_fs_data /backups/volumes/new_phone_fs_data_20260302_020000.tar.gz
```

---

## 7. Off-Site Backup

Local backups protect against data corruption and accidental deletion. Off-site backups protect against hardware failure, theft, and disasters.

### 7.1 Sync to S3-Compatible Storage

```bash
# Install rclone
curl https://rclone.org/install.sh | sudo bash

# Configure a remote (interactive)
rclone config
# Choose: s3, name it "offsite", enter bucket details

# Sync backups off-site
rclone sync /backups/ offsite:newphone-backups/ --progress

# Add to crontab (daily at 5:00 AM, after all local backups complete)
0 5 * * * /usr/bin/rclone sync /backups/ offsite:newphone-backups/ --log-file=/backups/logs/offsite-sync.log --log-level INFO
```

### 7.2 Sync to a Remote Server

```bash
# rsync over SSH
rsync -avz --delete /backups/ backup-user@remote-server:/backups/newphone/

# Crontab entry
0 5 * * * rsync -avz --delete /backups/ backup-user@remote-server:/backups/newphone/ >> /backups/logs/offsite-sync.log 2>&1
```

---

## 8. Configuration Backup

Back up configuration files that are not in version control:

```bash
# Backup script for config files
backup_config() {
  local DEST="/backups/config/config_$(date +%Y%m%d_%H%M%S)"
  mkdir -p "$DEST"

  # .env (contains secrets)
  cp /opt/new-phone/.env "$DEST/dot-env"

  # TLS certificates
  sudo cp -r /etc/letsencrypt/ "$DEST/letsencrypt/" 2>/dev/null || true
  cp -r /opt/new-phone/freeswitch/tls/ "$DEST/freeswitch-tls/" 2>/dev/null || true

  # Nginx config
  sudo cp /etc/nginx/sites-available/newphone "$DEST/nginx-newphone" 2>/dev/null || true

  # Crontab
  crontab -l > "$DEST/crontab.txt" 2>/dev/null || true

  # Sysctl tuning
  sudo cp /etc/sysctl.d/99-newphone.conf "$DEST/" 2>/dev/null || true

  echo "Config backed up to $DEST"
}

backup_config
```

Add to crontab (weekly):

```cron
# Weekly config backup on Sunday at 1:00 AM
0 1 * * 0 /opt/new-phone/scripts/backup-config.sh >> /backups/logs/config-backup.log 2>&1
```

---

## 9. Backup Monitoring

### 9.1 Verify Backup Freshness

Add a monitoring check that alerts if backups are stale:

```bash
#!/bin/bash
# /opt/new-phone/scripts/check-backup-freshness.sh
MAX_AGE_HOURS=26  # Alert if no backup in last 26 hours

LATEST=$(find /backups/postgres -name "new_phone_*.dump" -type f -printf '%T@\n' 2>/dev/null | sort -rn | head -1)

if [ -z "$LATEST" ]; then
  echo "CRITICAL: No database backups found!"
  exit 2
fi

AGE_SECONDS=$(echo "$(date +%s) - ${LATEST%.*}" | bc)
AGE_HOURS=$((AGE_SECONDS / 3600))

if [ "$AGE_HOURS" -gt "$MAX_AGE_HOURS" ]; then
  echo "WARNING: Latest backup is ${AGE_HOURS} hours old (threshold: ${MAX_AGE_HOURS}h)"
  exit 1
fi

echo "OK: Latest backup is ${AGE_HOURS} hours old"
exit 0
```

### 9.2 Backup Size Tracking

Monitor backup sizes to detect anomalies (sudden drops may indicate incomplete backups):

```bash
# Log backup sizes for trending
du -h /backups/postgres/*.dump | tail -7
```

---

## 10. Disaster Recovery

### 10.1 Recovery Targets

| Metric | Target |
|--------|--------|
| **RPO** (Recovery Point Objective) | 24 hours (last daily backup) |
| **RTO** (Recovery Time Objective) | 2 hours (fresh server + restore) |

To achieve a lower RPO (e.g., 1 hour), enable PostgreSQL WAL archiving for point-in-time recovery (PITR).

### 10.2 Point-in-Time Recovery (Advanced)

For RPO measured in minutes rather than hours, configure WAL archiving:

1. Enable WAL archiving in `docker-compose.prod.yml` PostgreSQL command:
   ```
   - -c
   - archive_mode=on
   - -c
   - archive_command=cp %p /backups/postgres/wal/%f
   ```
2. Mount the WAL backup directory into the PostgreSQL container
3. Use `pg_basebackup` for base backups
4. Replay WAL files to any point in time during restore

This is more complex to set up but provides near-zero data loss recovery.

### 10.3 Full Disaster Recovery Procedure

If the server is completely lost, follow this runbook:

```
1. Provision new server (see deployment.md sections 1-3)
   - Ubuntu 22.04+, Docker, firewall, DNS updated to new IP

2. Restore configuration
   - Copy .env from off-site backup
   - Restore TLS certificates (or re-issue with certbot)
   - Restore Nginx config

3. Clone repository
   git clone <repo-url> /opt/new-phone
   cd /opt/new-phone

4. Copy .env into place
   cp /backups/config/dot-env /opt/new-phone/.env

5. Start infrastructure services only
   docker compose up -d postgres redis minio

6. Wait for postgres to be healthy
   docker compose ps

7. Restore database
   ./scripts/restore-db.sh /backups/postgres/latest.dump

8. Restore MinIO objects
   mc mirror /backups/minio/ newphone/

9. Start remaining services
   docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

10. Verify
    docker compose ps
    curl -s https://pbx.example.com/api/v1/health
    # Test a SIP registration
    # Test a call
    # Verify recordings playback

11. Restore FreeSWITCH data volume (if needed)
    # Only if custom sounds, MOH, or other FS data was stored
    restore_volume new_phone_fs_data /backups/volumes/new_phone_fs_data_latest.tar.gz
    docker compose restart freeswitch

12. Update monitoring
    - Verify Grafana dashboards load
    - Verify Alertmanager is sending test alerts
    - Check Prometheus targets are all UP
```

### 10.4 DR Testing

Test your disaster recovery procedure quarterly:

1. Provision a test server (separate from production)
2. Follow the full DR runbook above using production backups
3. Verify all services start and data is present
4. Document the time taken and any issues encountered
5. Tear down the test server

---

## 11. Complete Crontab Reference

```cron
# PostgreSQL daily backup (keep 7 days)
0 2 * * * cd /opt/new-phone && BACKUP_DIR=/backups/postgres RETENTION_DAYS=7 ./scripts/backup-db.sh >> /backups/logs/db-backup.log 2>&1

# PostgreSQL weekly backup (keep 4 weeks)
0 3 * * 0 cd /opt/new-phone && BACKUP_DIR=/backups/postgres/weekly RETENTION_DAYS=28 ./scripts/backup-db.sh >> /backups/logs/db-backup.log 2>&1

# PostgreSQL monthly backup (keep 12 months)
0 4 1 * * cd /opt/new-phone && BACKUP_DIR=/backups/postgres/monthly RETENTION_DAYS=365 ./scripts/backup-db.sh >> /backups/logs/db-backup.log 2>&1

# MinIO mirror (daily)
30 2 * * * /usr/local/bin/mc mirror --overwrite newphone/ /backups/minio/ >> /backups/logs/minio-backup.log 2>&1

# Config backup (weekly)
0 1 * * 0 /opt/new-phone/scripts/backup-config.sh >> /backups/logs/config-backup.log 2>&1

# Off-site sync (daily, after all local backups)
0 5 * * * /usr/bin/rclone sync /backups/ offsite:newphone-backups/ --log-file=/backups/logs/offsite-sync.log --log-level INFO

# Backup freshness check (daily at 8 AM)
0 8 * * * /opt/new-phone/scripts/check-backup-freshness.sh >> /backups/logs/backup-check.log 2>&1
```
