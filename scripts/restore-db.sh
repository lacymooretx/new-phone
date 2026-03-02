#!/bin/bash
# =============================================================================
# New Phone — PostgreSQL Database Restore Script
# =============================================================================
# Restores a pg_dump backup file to the running PostgreSQL container.
# After restore, runs Alembic migrations to ensure schema is current.
#
# Usage:
#   ./scripts/restore-db.sh <backup-file.dump>
#
# Example:
#   ./scripts/restore-db.sh /backups/postgres/new_phone_20260302_020000.dump
#
# WARNING: This is a destructive operation. It will overwrite the current
#          database contents with the backup data.
# =============================================================================

set -euo pipefail

# --- Argument validation ---

if [ $# -ne 1 ]; then
    echo "Usage: $0 <backup-file.dump>"
    echo ""
    echo "Available backups:"
    find /backups/postgres -name "new_phone_*.dump" -type f -printf "  %T@ %Tc  %p\n" 2>/dev/null | sort -rn | head -10 | cut -d' ' -f2-
    exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Error: Backup file not found: $BACKUP_FILE"
    exit 1
fi

if [ ! -s "$BACKUP_FILE" ]; then
    echo "Error: Backup file is empty: $BACKUP_FILE"
    exit 1
fi

# --- Pre-restore checks ---

BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo "============================================="
echo "  New Phone — Database Restore"
echo "============================================="
echo "  Backup file: $BACKUP_FILE"
echo "  File size:   $BACKUP_SIZE"
echo "  Target DB:   new_phone"
echo "  Target user: new_phone_admin"
echo "============================================="
echo ""
echo "WARNING: This will OVERWRITE the current database with backup data!"
echo "         All data written since this backup was taken will be LOST."
echo ""

read -p "Type 'yes' to continue, anything else to abort: " confirm
if [ "$confirm" != "yes" ]; then
    echo "Aborted. No changes were made."
    exit 0
fi

# Verify postgres container is running
if ! docker compose ps postgres --format '{{.Health}}' 2>/dev/null | grep -q "healthy"; then
    echo "[$(date)] ERROR: PostgreSQL container is not healthy. Cannot restore."
    exit 1
fi

# Verify backup file integrity before starting
echo ""
echo "[$(date)] Verifying backup file integrity..."
if ! docker compose exec -T postgres pg_restore --list < "$BACKUP_FILE" > /dev/null 2>&1; then
    echo "[$(date)] ERROR: Backup file appears corrupt (cannot read TOC). Aborting."
    exit 1
fi
echo "[$(date)] Backup file integrity OK"

# --- Stop API services to prevent writes during restore ---

echo "[$(date)] Stopping API services to prevent writes during restore..."
docker compose stop api ai-engine 2>/dev/null || true

# --- Terminate existing connections ---

echo "[$(date)] Terminating active database connections..."
docker compose exec -T postgres psql -U new_phone_admin -d postgres -c "
    SELECT pg_terminate_backend(pid)
    FROM pg_stat_activity
    WHERE datname = 'new_phone'
      AND pid <> pg_backend_pid();
" > /dev/null 2>&1 || true

# --- Perform restore ---

echo "[$(date)] Restoring database from backup..."
echo "  This may take several minutes for large databases."
echo ""

if docker compose exec -T postgres pg_restore \
    -U new_phone_admin \
    -d new_phone \
    --clean \
    --if-exists \
    --no-owner \
    --no-privileges \
    < "$BACKUP_FILE" 2>&1; then
    echo ""
    echo "[$(date)] pg_restore completed successfully"
else
    RESTORE_EXIT=$?
    echo ""
    # pg_restore returns non-zero for warnings (e.g., "relation does not exist" during --clean)
    # This is usually harmless. Only fail on exit code > 1.
    if [ "$RESTORE_EXIT" -gt 1 ]; then
        echo "[$(date)] ERROR: pg_restore failed with exit code $RESTORE_EXIT"
        echo "  The database may be in an inconsistent state."
        echo "  Review the output above for errors."
        # Restart services anyway so the system is accessible
        docker compose start api ai-engine 2>/dev/null || true
        exit 1
    else
        echo "[$(date)] pg_restore completed with warnings (this is usually OK)"
    fi
fi

# --- Run migrations ---

echo "[$(date)] Starting API service for migrations..."
docker compose start api 2>/dev/null || true

# Wait for API to be healthy
echo "[$(date)] Waiting for API to be ready..."
for i in $(seq 1 30); do
    if docker compose ps api --format '{{.Health}}' 2>/dev/null | grep -q "healthy"; then
        break
    fi
    sleep 2
done

echo "[$(date)] Running database migrations..."
if docker compose exec api alembic upgrade head; then
    echo "[$(date)] Migrations completed successfully"
else
    echo "[$(date)] WARNING: Migration failed. Check alembic output above."
    echo "  You may need to run migrations manually: docker compose exec api alembic upgrade head"
fi

# --- Restart all services ---

echo "[$(date)] Restarting all services..."
docker compose start ai-engine 2>/dev/null || true

# --- Post-restore verification ---

echo ""
echo "[$(date)] Running post-restore verification..."

# Check table counts for key tables
echo ""
echo "  Table row counts:"
docker compose exec -T postgres psql -U new_phone_admin -d new_phone -c "
    SELECT 'tenants' as table_name, count(*) FROM tenants
    UNION ALL SELECT 'users', count(*) FROM users
    UNION ALL SELECT 'extensions', count(*) FROM extensions
    UNION ALL SELECT 'call_detail_records', count(*) FROM call_detail_records
    ORDER BY table_name;
" 2>/dev/null || echo "  (Could not query table counts — some tables may not exist yet)"

# Check RLS policies
echo ""
echo "  RLS policies:"
docker compose exec -T postgres psql -U new_phone_admin -d new_phone -c "
    SELECT count(*) as policy_count FROM pg_policies;
" 2>/dev/null || echo "  (Could not check RLS policies)"

echo ""
echo "============================================="
echo "[$(date)] Restore complete!"
echo "============================================="
echo ""
echo "Next steps:"
echo "  1. Verify the application: curl -s https://pbx.example.com/api/v1/health"
echo "  2. Test a SIP registration"
echo "  3. Check Grafana dashboards for any anomalies"
echo "  4. Review docker compose ps for service health"
