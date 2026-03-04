#!/usr/bin/env bash
# =============================================================================
# New Phone — PostgreSQL Database Backup Script
# =============================================================================
# Creates a compressed pg_dump backup, uploads to MinIO/S3 with tiered
# retention, verifies by restoring to a temp database, and notifies on error.
#
# Usage:
#   ./scripts/backup-db.sh
#
# Environment (sourced from ~/.secrets/.env if present):
#   NP_DB_HOST             PostgreSQL host (default: localhost)
#   NP_DB_PORT             PostgreSQL port (default: 5434)
#   NP_DB_NAME             Database name (default: new_phone)
#   NP_DB_ADMIN_USER       Admin user (default: new_phone_admin)
#   NP_DB_ADMIN_PASSWORD   Admin password (required)
#   NP_MINIO_ALIAS         mc alias name (default: np-minio)
#   NP_MINIO_ENDPOINT      MinIO endpoint (default: http://localhost:9000)
#   NP_MINIO_ACCESS_KEY    MinIO access key (required for MinIO upload)
#   NP_MINIO_SECRET_KEY    MinIO secret key (required for MinIO upload)
#   NP_BACKUP_BUCKET       Bucket name (default: np-db-backups)
#   NP_BACKUP_WEBHOOK_URL  Webhook URL for error notifications (optional)
#   NP_BACKUP_VERIFY       Verify backup by restoring to temp DB (default: true)
#   NP_BACKUP_VERIFY_HOST  PG host for verification restore (default: same as NP_DB_HOST)
#   NP_BACKUP_LOCAL_DIR    Also keep local copy (default: /backups/postgres)
#   NP_BACKUP_SKIP_MINIO   Set to "true" to skip MinIO upload (default: false)
#
# Retention policy:
#   Daily:   7 backups
#   Weekly:  4 backups  (created on Sundays)
#   Monthly: 12 backups (created on 1st of month)
#
# Crontab example (daily at 2 AM UTC):
#   0 2 * * * /opt/new-phone/scripts/backup-db.sh >> /var/log/np-backup.log 2>&1
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Load secrets
# ---------------------------------------------------------------------------
if [[ -f "${HOME}/.secrets/.env" ]]; then
    # shellcheck source=/dev/null
    source "${HOME}/.secrets/.env"
fi

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DB_HOST="${NP_DB_HOST:-localhost}"
DB_PORT="${NP_DB_PORT:-5434}"
DB_NAME="${NP_DB_NAME:-new_phone}"
DB_USER="${NP_DB_ADMIN_USER:-new_phone_admin}"
DB_PASSWORD="${NP_DB_ADMIN_PASSWORD:?ERROR: NP_DB_ADMIN_PASSWORD is required}"

MINIO_ALIAS="${NP_MINIO_ALIAS:-np-minio}"
MINIO_ENDPOINT="${NP_MINIO_ENDPOINT:-http://localhost:9000}"
MINIO_ACCESS_KEY="${NP_MINIO_ACCESS_KEY:-}"
MINIO_SECRET_KEY="${NP_MINIO_SECRET_KEY:-}"
BACKUP_BUCKET="${NP_BACKUP_BUCKET:-np-db-backups}"
SKIP_MINIO="${NP_BACKUP_SKIP_MINIO:-false}"

WEBHOOK_URL="${NP_BACKUP_WEBHOOK_URL:-}"
DO_VERIFY="${NP_BACKUP_VERIFY:-true}"
VERIFY_HOST="${NP_BACKUP_VERIFY_HOST:-${DB_HOST}}"
VERIFY_DB="np_backup_verify_$$"

LOCAL_DIR="${NP_BACKUP_LOCAL_DIR:-/backups/postgres}"

# Retention counts
RETAIN_DAILY=7
RETAIN_WEEKLY=4
RETAIN_MONTHLY=12

# Timestamps
NOW_UTC=$(date -u +"%Y-%m-%dT%H-%M-%SZ")
DATE_STAMP=$(date -u +"%Y-%m-%d")
DAY_OF_WEEK=$(date -u +"%u")  # 1=Monday, 7=Sunday
DAY_OF_MONTH=$(date -u +"%d")

# Temp directory
WORK_DIR="${TMPDIR:-/tmp}/np-backup-${NOW_UTC}"
BACKUP_FILE="${WORK_DIR}/${DATE_STAMP}-${DB_NAME}.sql.gz"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
log() {
    echo "[$(date -u +"%Y-%m-%d %H:%M:%S UTC")] $*"
}

notify_error() {
    local message="$1"
    log "ERROR: ${message}"

    if [[ -n "${WEBHOOK_URL}" ]]; then
        curl -sf -X POST "${WEBHOOK_URL}" \
            -H "Content-Type: application/json" \
            -d "{
                \"text\": \"Database Backup FAILED\",
                \"attachments\": [{
                    \"color\": \"danger\",
                    \"title\": \"New Phone DB Backup Failure\",
                    \"text\": \"${message}\",
                    \"fields\": [
                        {\"title\": \"Host\", \"value\": \"${DB_HOST}\", \"short\": true},
                        {\"title\": \"Database\", \"value\": \"${DB_NAME}\", \"short\": true},
                        {\"title\": \"Time (UTC)\", \"value\": \"${NOW_UTC}\", \"short\": true}
                    ]
                }]
            }" 2>/dev/null || log "WARNING: Failed to send webhook notification"
    fi
}

notify_success() {
    local size="$1"
    local duration="$2"

    if [[ -n "${WEBHOOK_URL}" ]]; then
        curl -sf -X POST "${WEBHOOK_URL}" \
            -H "Content-Type: application/json" \
            -d "{
                \"text\": \"Database Backup Succeeded\",
                \"attachments\": [{
                    \"color\": \"good\",
                    \"title\": \"New Phone DB Backup Success\",
                    \"fields\": [
                        {\"title\": \"Database\", \"value\": \"${DB_NAME}\", \"short\": true},
                        {\"title\": \"Size\", \"value\": \"${size}\", \"short\": true},
                        {\"title\": \"Duration\", \"value\": \"${duration}s\", \"short\": true},
                        {\"title\": \"Time (UTC)\", \"value\": \"${NOW_UTC}\", \"short\": true}
                    ]
                }]
            }" 2>/dev/null || true
    fi
}

cleanup() {
    log "Cleaning up temp files..."
    rm -rf "${WORK_DIR}"

    # Drop verification DB if it exists
    if [[ "${DO_VERIFY}" == "true" ]]; then
        PGPASSWORD="${DB_PASSWORD}" psql -h "${VERIFY_HOST}" -p "${DB_PORT}" \
            -U "${DB_USER}" -d postgres \
            -c "DROP DATABASE IF EXISTS ${VERIFY_DB};" 2>/dev/null || true
    fi
}

trap cleanup EXIT

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------
log "============================================="
log "New Phone Database Backup"
log "  Host:     ${DB_HOST}:${DB_PORT}"
log "  Database: ${DB_NAME}"
log "  MinIO:    ${SKIP_MINIO} (skip=${SKIP_MINIO})"
log "============================================="

# Check pg_dump is available — try local binary first, then Docker fallback
USE_DOCKER_PG=false
if command -v pg_dump &>/dev/null; then
    log "Using local pg_dump"
elif command -v docker &>/dev/null; then
    USE_DOCKER_PG=true
    log "Using Docker-based pg_dump (no local pg_dump found)"
else
    notify_error "Neither pg_dump nor docker found in PATH"
    exit 1
fi

# Test database connectivity
log "Testing database connectivity..."
if [[ "${USE_DOCKER_PG}" == "true" ]]; then
    if ! docker compose ps postgres --format '{{.Health}}' 2>/dev/null | grep -q "healthy"; then
        notify_error "PostgreSQL container is not healthy"
        exit 1
    fi
else
    if ! PGPASSWORD="${DB_PASSWORD}" pg_isready -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" &>/dev/null; then
        notify_error "Cannot connect to PostgreSQL at ${DB_HOST}:${DB_PORT}"
        exit 1
    fi
fi

# Configure MinIO client if needed
MINIO_AVAILABLE=false
if [[ "${SKIP_MINIO}" != "true" ]] && [[ -n "${MINIO_ACCESS_KEY}" ]] && [[ -n "${MINIO_SECRET_KEY}" ]]; then
    if command -v mc &>/dev/null; then
        mc alias set "${MINIO_ALIAS}" "${MINIO_ENDPOINT}" "${MINIO_ACCESS_KEY}" "${MINIO_SECRET_KEY}" --api s3v4 >/dev/null 2>&1
        mc mb --ignore-existing "${MINIO_ALIAS}/${BACKUP_BUCKET}" >/dev/null 2>&1
        MINIO_AVAILABLE=true
    else
        log "WARNING: mc (MinIO client) not found — will only keep local backup"
    fi
elif [[ "${SKIP_MINIO}" != "true" ]]; then
    log "WARNING: MinIO credentials not set — will only keep local backup"
fi

# ---------------------------------------------------------------------------
# Step 1: Create backup
# ---------------------------------------------------------------------------
mkdir -p "${WORK_DIR}"
mkdir -p "${LOCAL_DIR}"

log "Starting pg_dump..."
START_TIME=$(date +%s)

if [[ "${USE_DOCKER_PG}" == "true" ]]; then
    docker compose exec -T postgres pg_dump \
        -U "${DB_USER}" \
        -d "${DB_NAME}" \
        --format=plain \
        --no-owner \
        --no-privileges \
        2>"${WORK_DIR}/pg_dump.log" | gzip -9 > "${BACKUP_FILE}"
else
    PGPASSWORD="${DB_PASSWORD}" pg_dump \
        -h "${DB_HOST}" \
        -p "${DB_PORT}" \
        -U "${DB_USER}" \
        -d "${DB_NAME}" \
        --format=plain \
        --no-owner \
        --no-privileges \
        2>"${WORK_DIR}/pg_dump.log" | gzip -9 > "${BACKUP_FILE}"
fi

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

# Check file is non-empty
if [[ ! -s "${BACKUP_FILE}" ]]; then
    notify_error "Backup file is empty or was not created"
    exit 1
fi

BACKUP_SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
log "Backup complete: ${BACKUP_FILE} (${BACKUP_SIZE}, ${DURATION}s)"

# Verify gzip integrity
if ! gzip -t "${BACKUP_FILE}" 2>/dev/null; then
    notify_error "Backup file is corrupt (gzip test failed)"
    exit 1
fi

# ---------------------------------------------------------------------------
# Step 2: Verify backup (restore to temp DB)
# ---------------------------------------------------------------------------
if [[ "${DO_VERIFY}" == "true" ]]; then
    log "Verifying backup by restoring to temp database ${VERIFY_DB}..."

    if [[ "${USE_DOCKER_PG}" == "true" ]]; then
        # Docker-based verification
        docker compose exec -T postgres psql -U "${DB_USER}" -d postgres \
            -c "DROP DATABASE IF EXISTS ${VERIFY_DB};" \
            -c "CREATE DATABASE ${VERIFY_DB};"

        if gunzip -c "${BACKUP_FILE}" | docker compose exec -T postgres psql \
            -U "${DB_USER}" -d "${VERIFY_DB}" -q 2>"${WORK_DIR}/restore.log"; then
            log "Restore to temp DB succeeded"
        else
            notify_error "Backup verification FAILED: restore error"
            exit 1
        fi

        # Verify critical tables
        CRITICAL_TABLES=("tenants" "users" "extensions" "call_detail_records" "voicemails" "sip_trunks")
        VERIFY_PASS=true

        for table in "${CRITICAL_TABLES[@]}"; do
            if docker compose exec -T postgres psql -U "${DB_USER}" -d "${VERIFY_DB}" -tAc \
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name='${table}');" 2>/dev/null | grep -q "t"; then
                log "  Verified table: ${table}"
            else
                log "  WARNING: Missing table: ${table}"
                VERIFY_PASS=false
            fi
        done

        # Clean up
        docker compose exec -T postgres psql -U "${DB_USER}" -d postgres \
            -c "DROP DATABASE IF EXISTS ${VERIFY_DB};" 2>/dev/null || true
    else
        # Local pg_dump verification
        PGPASSWORD="${DB_PASSWORD}" psql -h "${VERIFY_HOST}" -p "${DB_PORT}" \
            -U "${DB_USER}" -d postgres \
            -c "DROP DATABASE IF EXISTS ${VERIFY_DB};" \
            -c "CREATE DATABASE ${VERIFY_DB};"

        if gunzip -c "${BACKUP_FILE}" | PGPASSWORD="${DB_PASSWORD}" psql \
            -h "${VERIFY_HOST}" -p "${DB_PORT}" -U "${DB_USER}" \
            -d "${VERIFY_DB}" -q 2>"${WORK_DIR}/restore.log"; then
            log "Restore to temp DB succeeded"
        else
            notify_error "Backup verification FAILED: restore error"
            exit 1
        fi

        CRITICAL_TABLES=("tenants" "users" "extensions" "call_detail_records" "voicemails" "sip_trunks")
        VERIFY_PASS=true

        for table in "${CRITICAL_TABLES[@]}"; do
            if PGPASSWORD="${DB_PASSWORD}" psql -h "${VERIFY_HOST}" -p "${DB_PORT}" \
                -U "${DB_USER}" -d "${VERIFY_DB}" -tAc \
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name='${table}');" 2>/dev/null | grep -q "t"; then
                log "  Verified table: ${table}"
            else
                log "  WARNING: Missing table: ${table}"
                VERIFY_PASS=false
            fi
        done

        PGPASSWORD="${DB_PASSWORD}" psql -h "${VERIFY_HOST}" -p "${DB_PORT}" \
            -U "${DB_USER}" -d postgres \
            -c "DROP DATABASE IF EXISTS ${VERIFY_DB};" 2>/dev/null || true
    fi

    if [[ "${VERIFY_PASS}" == "true" ]]; then
        log "Backup verification PASSED"
    else
        log "WARNING: Some tables missing — backup may be partial (pre-migration state)"
    fi
fi

# ---------------------------------------------------------------------------
# Step 3: Store locally
# ---------------------------------------------------------------------------
cp "${BACKUP_FILE}" "${LOCAL_DIR}/${DATE_STAMP}-${DB_NAME}.sql.gz"
log "Local copy stored: ${LOCAL_DIR}/${DATE_STAMP}-${DB_NAME}.sql.gz"

# Local retention (simple: keep RETAIN_DAILY most recent)
LOCAL_COUNT=$(find "${LOCAL_DIR}" -maxdepth 1 -name "*-${DB_NAME}.sql.gz" -type f 2>/dev/null | wc -l | tr -d ' ')
if [[ "${LOCAL_COUNT}" -gt "${RETAIN_DAILY}" ]]; then
    REMOVE_COUNT=$((LOCAL_COUNT - RETAIN_DAILY))
    log "Rotating ${REMOVE_COUNT} old local backup(s)..."
    find "${LOCAL_DIR}" -maxdepth 1 -name "*-${DB_NAME}.sql.gz" -type f -printf '%T@ %p\n' 2>/dev/null | \
        sort -n | head -n "${REMOVE_COUNT}" | awk '{print $2}' | \
        xargs rm -f 2>/dev/null || true
fi

# ---------------------------------------------------------------------------
# Step 4: Upload to MinIO with tiered retention
# ---------------------------------------------------------------------------
if [[ "${MINIO_AVAILABLE}" == "true" ]]; then
    log "Uploading to MinIO..."

    # Always upload as daily
    mc cp "${BACKUP_FILE}" "${MINIO_ALIAS}/${BACKUP_BUCKET}/daily/" >/dev/null

    # Sunday (7) = also store as weekly
    if [[ "${DAY_OF_WEEK}" == "7" ]]; then
        WEEK_NUM=$(date -u +"%Y-W%V")
        mc cp "${BACKUP_FILE}" "${MINIO_ALIAS}/${BACKUP_BUCKET}/weekly/${WEEK_NUM}-${DB_NAME}.sql.gz" >/dev/null
        log "  Also stored as weekly: ${WEEK_NUM}"
    fi

    # 1st of month = also store as monthly
    if [[ "${DAY_OF_MONTH}" == "01" ]]; then
        MONTH_STAMP=$(date -u +"%Y-%m")
        mc cp "${BACKUP_FILE}" "${MINIO_ALIAS}/${BACKUP_BUCKET}/monthly/${MONTH_STAMP}-${DB_NAME}.sql.gz" >/dev/null
        log "  Also stored as monthly: ${MONTH_STAMP}"
    fi

    log "Upload complete"

    # Enforce retention on MinIO
    log "Enforcing MinIO retention policy..."

    enforce_retention() {
        local path="$1"
        local keep="$2"
        local label="$3"

        local files
        files=$(mc ls "${MINIO_ALIAS}/${BACKUP_BUCKET}/${path}/" 2>/dev/null | \
                grep -E '\.sql\.gz$' | \
                awk '{print $NF}' | \
                sort)

        local count
        count=$(echo "${files}" | grep -c . 2>/dev/null || echo "0")

        if [[ "${count}" -gt "${keep}" ]]; then
            local to_remove=$((count - keep))
            log "  ${label}: ${count} backups, removing ${to_remove} oldest"
            echo "${files}" | head -n "${to_remove}" | while read -r file; do
                [[ -z "${file}" ]] && continue
                log "    Removing: ${file}"
                mc rm "${MINIO_ALIAS}/${BACKUP_BUCKET}/${path}/${file}" >/dev/null 2>&1 || true
            done
        else
            log "  ${label}: ${count} backups (limit: ${keep})"
        fi
    }

    enforce_retention "daily" "${RETAIN_DAILY}" "Daily"
    enforce_retention "weekly" "${RETAIN_WEEKLY}" "Weekly"
    enforce_retention "monthly" "${RETAIN_MONTHLY}" "Monthly"
fi

# ---------------------------------------------------------------------------
# Step 5: Summary
# ---------------------------------------------------------------------------
log "============================================="
log "Backup Summary"
log "  Database:    ${DB_NAME}@${DB_HOST}:${DB_PORT}"
log "  File:        ${DATE_STAMP}-${DB_NAME}.sql.gz"
log "  Size:        ${BACKUP_SIZE}"
log "  Duration:    ${DURATION}s"
log "  Verified:    ${DO_VERIFY}"
log "  Local copy:  ${LOCAL_DIR}/"
log "  MinIO:       ${MINIO_AVAILABLE}"
log "============================================="

notify_success "${BACKUP_SIZE}" "${DURATION}"

exit 0
