#!/usr/bin/env bash
set -euo pipefail

# Daily PostgreSQL backup for bitwise-cloud
# Usage: ./scripts/backup-postgres.sh
# Cron:  0 3 * * * /opt/bitwise-cloud/scripts/backup-postgres.sh

BACKUP_DIR="${BACKUP_DIR:-/opt/bitwise-cloud/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
COMPOSE_DIR="${COMPOSE_DIR:-/opt/bitwise-cloud}"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/bitwise-${TIMESTAMP}.sql.gz"

mkdir -p "$BACKUP_DIR"

echo "Starting backup: ${BACKUP_FILE}"

docker compose -f "${COMPOSE_DIR}/docker-compose.yml" \
  exec -T postgres \
  pg_dump -U "${POSTGRES_USER:-bitwise}" "${POSTGRES_DB:-bitwise}" \
  | gzip > "$BACKUP_FILE"

# Verify backup is not empty/truncated
MIN_SIZE=1024
ACTUAL_SIZE=$(stat -f%z "$BACKUP_FILE" 2>/dev/null || stat -c%s "$BACKUP_FILE" 2>/dev/null || echo "0")
if [ "$ACTUAL_SIZE" -lt "$MIN_SIZE" ]; then
    echo "ERROR: Backup file is empty or too small (${ACTUAL_SIZE} bytes)" >&2
    rm -f "$BACKUP_FILE"
    exit 1
fi

echo "Backup complete: $(du -h "$BACKUP_FILE" | cut -f1)"

# Remove backups older than retention period
find "$BACKUP_DIR" -name "bitwise-*.sql.gz" -mtime +"$RETENTION_DAYS" -delete
echo "Cleaned backups older than ${RETENTION_DAYS} days"

# Optional: upload to Cloudflare R2 via rclone
if command -v rclone &>/dev/null && rclone listremotes | grep -q "^r2:"; then
  echo "Uploading to R2..."
  rclone copy "$BACKUP_FILE" r2:bitwise-backups/
  echo "R2 upload complete"
fi
