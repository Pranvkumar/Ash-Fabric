#!/usr/bin/env bash
# ASH-Fabric: Restart Service Script
# Idempotent — safe to run multiple times
set -euo pipefail

SERVICE="${ASH_SERVICE:-unknown}"
TIMESTAMP="${ASH_TIMESTAMP:-$(date -u +%Y-%m-%dT%H:%M:%SZ)}"

echo "[ASH] Restarting service: ${SERVICE} at ${TIMESTAMP}"

# Check if running as Docker container
if docker ps --filter "name=${SERVICE}" --format '{{.Names}}' | grep -q "${SERVICE}"; then
    echo "[ASH] Found running container: ${SERVICE}"
    docker restart "${SERVICE}" --time 10
    echo "[ASH] Container restarted successfully"
    
    # Wait for health check
    sleep 5
    STATUS=$(docker inspect --format='{{.State.Status}}' "${SERVICE}" 2>/dev/null || echo "unknown")
    echo "[ASH] Post-restart status: ${STATUS}"
else
    echo "[ASH] Container ${SERVICE} not found — checking systemd..."
    if systemctl is-active --quiet "${SERVICE}" 2>/dev/null; then
        systemctl restart "${SERVICE}"
        echo "[ASH] Systemd service restarted"
    else
        echo "[ASH] WARNING: Service ${SERVICE} not found in Docker or systemd"
        exit 1
    fi
fi

echo "[ASH] Restart complete for ${SERVICE}"
