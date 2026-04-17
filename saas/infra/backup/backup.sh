#!/bin/sh
set -eu

timestamp="$(date +%Y%m%d_%H%M%S)"
backup_dir="${BACKUP_DIR:-/backups}"
mkdir -p "$backup_dir"

PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump -h "${POSTGRES_HOST:-db}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -Fc > "$backup_dir/patrimoineop_${timestamp}.dump"

find "$backup_dir" -type f -name "patrimoineop_*.dump" -mtime +7 -delete
