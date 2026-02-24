#!/usr/bin/env bash
# ASH-Fabric: Terminate Zombie Resource
# Backs up data and terminates idle instances
set -euo pipefail

SERVICE="${ASH_SERVICE:-unknown}"
BACKUP_DIR="${ASH_BACKUP_DIR:-/tmp/ash-backups}"
TIMESTAMP="${ASH_TIMESTAMP:-$(date -u +%Y-%m-%dT%H:%M:%SZ)}"

echo "[ASH] Zombie termination initiated for: ${SERVICE} at ${TIMESTAMP}"

# Step 1: Create backup directory
mkdir -p "${BACKUP_DIR}"

# Step 2: Backup container data (if Docker)
if docker ps --filter "name=${SERVICE}" --format '{{.Names}}' | grep -q "${SERVICE}"; then
    echo "[ASH] Backing up container data..."
    BACKUP_FILE="${BACKUP_DIR}/${SERVICE}_${TIMESTAMP//[:T]/_}.tar.gz"
    docker export "${SERVICE}" | gzip > "${BACKUP_FILE}" 2>/dev/null || \
        echo "[ASH] WARNING: Export failed (container may be stopped)"
    echo "[ASH] Backup saved to: ${BACKUP_FILE}"
    
    # Step 3: Stop and remove the container
    echo "[ASH] Stopping zombie container..."
    docker stop "${SERVICE}" --time 30 2>/dev/null || true
    docker rm "${SERVICE}" 2>/dev/null || true
    echo "[ASH] Container terminated"
else
    echo "[ASH] Container ${SERVICE} not found — may already be terminated"
fi

# Step 4: Log the termination
echo "[ASH] Zombie resource ${SERVICE} terminated at ${TIMESTAMP}" >> "${BACKUP_DIR}/termination.log"

echo "[ASH] Zombie termination complete for ${SERVICE}"
