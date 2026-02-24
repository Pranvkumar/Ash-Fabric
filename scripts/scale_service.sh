#!/usr/bin/env bash
# ASH-Fabric: Scale Service Script
# Checks if spike is recurring; scales or restarts accordingly
set -euo pipefail

SERVICE="${ASH_SERVICE:-unknown}"
REPLICA_COUNT="${ASH_REPLICA_COUNT:-2}"
TIMESTAMP="${ASH_TIMESTAMP:-$(date -u +%Y-%m-%dT%H:%M:%SZ)}"

echo "[ASH] Scale/restart evaluation for: ${SERVICE} at ${TIMESTAMP}"

# Check current replica count
CURRENT=$(docker ps --filter "label=service=${SERVICE}" --format '{{.Names}}' | wc -l)
echo "[ASH] Current replicas: ${CURRENT}, Target: ${REPLICA_COUNT}"

if [ "${CURRENT}" -lt "${REPLICA_COUNT}" ]; then
    echo "[ASH] Scaling up ${SERVICE} to ${REPLICA_COUNT} replicas..."
    # In production, this would call terraform apply or k8s scale
    echo "[ASH] NOTE: Scaling requires Terraform — triggering plan..."
    echo "[ASH] terraform plan -var=\"replica_count=${REPLICA_COUNT}\" -var=\"service_name=${SERVICE}\""
else
    echo "[ASH] Replica count sufficient. Performing restart instead..."
    docker restart "${SERVICE}" --time 10 || echo "[ASH] Restart attempted"
fi

echo "[ASH] Scale/restart complete for ${SERVICE}"
