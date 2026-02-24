#!/usr/bin/env bash
# ASH-Fabric: Purge Disk Space
# Cleans /tmp, old logs, and Docker artifacts. Idempotent.
set -euo pipefail

SERVICE="${ASH_SERVICE:-unknown}"
LOG_RETENTION_DAYS="${ASH_LOG_RETENTION_DAYS:-7}"

echo "[ASH] Disk cleanup started for: ${SERVICE}"

# Step 1: Show current disk usage
echo "[ASH] Current disk usage:"
df -h / | tail -1

# Step 2: Purge /tmp (idempotent — mkdir -p)
echo "[ASH] Cleaning /tmp..."
find /tmp -type f -mtime +1 -delete 2>/dev/null || true
echo "[ASH] /tmp cleaned"

# Step 3: Rotate old logs
echo "[ASH] Removing logs older than ${LOG_RETENTION_DAYS} days..."
find /var/log -name "*.log" -type f -mtime +"${LOG_RETENTION_DAYS}" -delete 2>/dev/null || true
find /var/log -name "*.log.gz" -type f -mtime +"${LOG_RETENTION_DAYS}" -delete 2>/dev/null || true
echo "[ASH] Old logs purged"

# Step 4: Docker cleanup (if available)
if command -v docker &>/dev/null; then
    echo "[ASH] Pruning Docker system..."
    docker system prune -f --volumes 2>/dev/null || true
    echo "[ASH] Docker prune complete"
fi

# Step 5: Show updated disk usage
echo "[ASH] Updated disk usage:"
df -h / | tail -1

echo "[ASH] Disk cleanup complete for ${SERVICE}"
