"""
Metrics Reader — Tool for querying VictoriaMetrics (Prometheus-compatible).
Used by agents to verify alerts and read current metric values.
"""

import httpx
import structlog

logger = structlog.get_logger()


class MetricsReader:
    def __init__(self, vm_endpoint: str):
        self.base_url = vm_endpoint
        self.client = httpx.AsyncClient(timeout=10.0)

    async def query(self, promql: str) -> dict:
        """Execute an instant PromQL query."""
        url = f"{self.base_url}/api/v1/query"
        params = {"query": promql}

        logger.debug("metrics_query", promql=promql)
        resp = await self.client.get(url, params=params)
        resp.raise_for_status()

        data = resp.json()
        if data.get("status") != "success":
            raise ValueError(f"VictoriaMetrics query failed: {data}")

        return data

    async def query_value(self, promql: str) -> float:
        """Query and return the first numeric value."""
        data = await self.query(promql)
        results = data.get("data", {}).get("result", [])

        if not results:
            raise ValueError(f"No data for query: {promql}")

        # Value is [timestamp, "value_string"]
        value_str = results[0]["value"][1]
        return float(value_str)

    async def query_range(self, promql: str, start: str, end: str, step: str = "60s") -> dict:
        """Execute a range query (for historical analysis)."""
        url = f"{self.base_url}/api/v1/query_range"
        params = {
            "query": promql,
            "start": start,
            "end": end,
            "step": step,
        }

        resp = await self.client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    async def is_healthy(self) -> bool:
        """Check if VictoriaMetrics is reachable."""
        try:
            resp = await self.client.get(f"{self.base_url}/health")
            return resp.status_code == 200
        except Exception:
            return False

    async def close(self):
        await self.client.aclose()
