#!/usr/bin/env bash
# ASH-Fabric: Check Database Connections
# Inspects active DB connections and kills idle ones if pool is exhausted
set -euo pipefail

SERVICE="${ASH_SERVICE:-unknown}"
DB_HOST="${ASH_DB_HOST:-localhost}"
DB_PORT="${ASH_DB_PORT:-5432}"

echo "[ASH] Checking DB connections for service: ${SERVICE}"

# Try PostgreSQL first
if command -v psql &>/dev/null; then
    echo "[ASH] Querying PostgreSQL connection stats..."
    ACTIVE=$(psql -h "${DB_HOST}" -p "${DB_PORT}" -t -c \
        "SELECT count(*) FROM pg_stat_activity WHERE state = 'active';" 2>/dev/null || echo "N/A")
    IDLE=$(psql -h "${DB_HOST}" -p "${DB_PORT}" -t -c \
        "SELECT count(*) FROM pg_stat_activity WHERE state = 'idle';" 2>/dev/null || echo "N/A")
    echo "[ASH] Active connections: ${ACTIVE}"
    echo "[ASH] Idle connections: ${IDLE}"
    
    # Kill idle connections if too many
    if [ "${IDLE}" != "N/A" ] && [ "${IDLE}" -gt 50 ]; then
        echo "[ASH] Too many idle connections, terminating..."
        psql -h "${DB_HOST}" -p "${DB_PORT}" -c \
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle' AND query_start < now() - interval '10 minutes';" 2>/dev/null
    fi
# Try MySQL
elif command -v mysql &>/dev/null; then
    echo "[ASH] Querying MySQL connection stats..."
    mysql -h "${DB_HOST}" -P "${DB_PORT}" -e "SHOW PROCESSLIST;" 2>/dev/null || echo "[ASH] MySQL query failed"
else
    echo "[ASH] No database CLI found — checking via Docker..."
    docker exec "${SERVICE}-db" sh -c 'echo "SELECT count(*) FROM pg_stat_activity;" | psql -U postgres' 2>/dev/null || \
        echo "[ASH] WARNING: Could not check DB connections"
fi

echo "[ASH] DB connection check complete for ${SERVICE}"
