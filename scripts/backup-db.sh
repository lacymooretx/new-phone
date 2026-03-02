#!/bin/bash
# =============================================================================
# New Phone — PostgreSQL Database Backup Script
# =============================================================================
# Creates a compressed pg_dump backup and rotates old files.
#
# Usage:
#   ./scripts/backup-db.sh
#
# Environment variables:
#   BACKUP_DIR      — Destination directory (default: /backups/postgres)
#   RETENTION_DAYS  — Delete backups older than N days (default: 7)
#   COMPOSE_FILE    — Docker Compose file(s) (default: uses docker compose defaults)
#
# Crontab example (daily at 2 AM):
#   0 2 * * * cd /opt/new-phone && BACKUP_DIR=/backups/postgres ./scripts/backup-db.sh >> /backups/logs/db-backup.log 2>&1
# =============================================================================

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/backups/postgres}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
DATE=$(date +%Y%m%d_%H%M%S)
FILENAME="new_phone_${DATE}.dump"
BACKUP_PATH="${BACKUP_DIR}/${FILENAME}"

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

echo "============================================="
echo "[$(date)] Starting database backup"
echo "  Destination: ${BACKUP_PATH}"
echo "  Retention:   ${RETENTION_DAYS} days"
echo "============================================="

# Verify postgres container is running and healthy
if ! docker compose ps postgres --format '{{.Health}}' 2>/dev/null | grep -q "healthy"; then
    echo "[$(date)] ERROR: PostgreSQL container is not healthy. Aborting backup."
    exit 1
fi

# Perform the backup using custom format (-Fc) for efficient compression and selective restore
docker compose exec -T postgres pg_dump \
    -U new_phone_admin \
    -d new_phone \
    -Fc \
    --no-owner \
    --no-privileges \
    > "$BACKUP_PATH"

# Verify the backup file exists and is non-empty
if [ ! -s "$BACKUP_PATH" ]; then
    echo "[$(date)] ERROR: Backup file is empty or was not created!"
    rm -f "$BACKUP_PATH"
    exit 1
fi

SIZE=$(du -h "$BACKUP_PATH" | cut -f1)
echo "[$(date)] Backup complete: ${FILENAME} (${SIZE})"

# Verify backup integrity by reading the table of contents
if ! docker compose exec -T postgres pg_restore --list < "$BACKUP_PATH" > /dev/null 2>&1; then
    echo "[$(date)] WARNING: Backup verification failed — file may be corrupt!"
    exit 1
fi
echo "[$(date)] Backup verification passed (TOC readable)"

# Rotate old backups
DELETED_COUNT=$(find "$BACKUP_DIR" -maxdepth 1 -name "new_phone_*.dump" -mtime +"$RETENTION_DAYS" -type f | wc -l)
if [ "$DELETED_COUNT" -gt 0 ]; then
    find "$BACKUP_DIR" -maxdepth 1 -name "new_phone_*.dump" -mtime +"$RETENTION_DAYS" -type f -delete
    echo "[$(date)] Rotated ${DELETED_COUNT} backup(s) older than ${RETENTION_DAYS} days"
else
    echo "[$(date)] No backups to rotate"
fi

# Summary
TOTAL_BACKUPS=$(find "$BACKUP_DIR" -maxdepth 1 -name "new_phone_*.dump" -type f | wc -l)
TOTAL_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
echo "============================================="
echo "[$(date)] Backup summary:"
echo "  Total backups: ${TOTAL_BACKUPS}"
echo "  Total size:    ${TOTAL_SIZE}"
echo "============================================="
