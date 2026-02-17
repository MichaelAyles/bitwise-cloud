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
