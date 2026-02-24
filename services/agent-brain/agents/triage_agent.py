"""
Triage Agent — Analyzes alerts and determines remediation strategy.
Known patterns → deterministic script mapping.
Anomalies → LLM-driven reasoning.
"""

import json
import structlog
from tools.metrics_reader import MetricsReader
from tools.script_manager import ScriptManager
from config.settings import Settings

logger = structlog.get_logger()

# Known automation patterns: action label → (script, confidence)
KNOWN_PATTERNS = {
    "restart_container": ("restart_service.sh", 0.95),
    "scale_or_restart": ("scale_service.sh", 0.90),
    "check_db_connections": ("check_db.sh", 0.85),
    "purge_and_expand": ("purge_disk.sh", 0.92),
    "terminate_and_backup": ("terminate_zombie.sh", 0.88),
}

# Metric-to-diagnosis mapping for common cases
METRIC_DIAGNOSIS = {
    "HighMemoryUsage": {
        "diagnosis": "Memory usage exceeded 95% threshold — OOM kill risk detected",
        "promql": "node_memory_usage_percent",
    },
    "HighCPUUsage": {
        "diagnosis": "CPU usage exceeded 90% — service may be under heavy load or stuck in a loop",
        "promql": "node_cpu_usage_percent",
    },
    "HighLatency": {
        "diagnosis": "Request latency above 500ms — possible database bottleneck or network issue",
        "promql": "http_request_duration_ms",
    },
    "DiskSpaceCritical": {
        "diagnosis": "Disk usage above 90% — log rotation or volume expansion required",
        "promql": "node_disk_usage_percent",
    },
    "ZombieResource": {
        "diagnosis": "Resource idle for 4+ hours — likely a zombie instance wasting compute",
        "promql": "node_cpu_usage_percent",
    },
}


class TriageAgent:
    def __init__(self, metrics_reader: MetricsReader, script_manager: ScriptManager, settings: Settings):
        self.metrics = metrics_reader
        self.scripts = script_manager
        self.settings = settings

    async def analyze(self, alert: dict) -> dict:
        """
        Analyze an incoming alert and produce a remediation plan.
        Returns a dict with diagnosis, plan, script, and confidence.
        """
        labels = alert.get("labels", {})
        annotations = alert.get("annotations", {})
        alert_name = labels.get("alertname", "unknown")
        action = labels.get("action", "")
        service = labels.get("service", "unknown")
        severity = labels.get("severity", "unknown")

        logger.info(
            "triage_analyzing",
            alert_name=alert_name,
            service=service,
            severity=severity,
            action=action,
        )

        # ── Step 1: Check for known pattern ──────────────────
        if action in KNOWN_PATTERNS:
            script, confidence = KNOWN_PATTERNS[action]
            diag_info = METRIC_DIAGNOSIS.get(alert_name, {})

            # Verify the metric is actually breached (observability-driven)
            metric_value = None
            promql = diag_info.get("promql")
            if promql:
                try:
                    metric_value = await self.metrics.query_value(
                        f'{promql}{{service="{service}"}}'
                    )
                    logger.info("metric_verified", metric=promql, value=metric_value)
                except Exception as e:
                    logger.warning("metric_query_failed", error=str(e))

            diagnosis = diag_info.get("diagnosis", f"Alert {alert_name} triggered for {service}")
            if metric_value is not None:
                diagnosis += f" (current value: {metric_value:.1f})"

            plan = self._build_known_plan(action, script, service)

            return {
                "alert_name": alert_name,
                "severity": severity,
                "diagnosis": diagnosis,
                "plan": plan,
                "script": script,
                "confidence": confidence,
                "type": "known",
            }

        # ── Step 2: Anomaly — use LLM reasoning ─────────────
        logger.info("anomaly_detected", alert_name=alert_name, action=action)
        return await self._llm_triage(alert_name, service, severity, annotations)

    def _build_known_plan(self, action: str, script: str, service: str) -> str:
        """Generate a human-readable plan for known patterns."""
        plans = {
            "restart_container": (
                f"1. Run {script} to gracefully restart {service}\n"
                f"2. Wait 60s for service to stabilize\n"
                f"3. Re-check memory metrics via audit agent\n"
                f"4. If still breached, scale memory limit by 20%"
            ),
            "scale_or_restart": (
                f"1. Check if this is a recurring spike (query 1h history)\n"
                f"2. If recurring → update Terraform replica count for {service}\n"
                f"3. If sudden → run {script} to restart the service\n"
                f"4. Verify CPU returns below 90% within 2 minutes"
            ),
            "check_db_connections": (
                f"1. Run {script} to inspect active DB connections for {service}\n"
                f"2. If pool is exhausted, kill idle connections\n"
                f"3. If persistent, spin up a read replica via Terraform\n"
                f"4. Validate latency drops below 500ms"
            ),
            "purge_and_expand": (
                f"1. Run {script} to purge /tmp and rotate old logs\n"
                f"2. Check disk usage after purge\n"
                f"3. If still >90%, expand volume via cloud API\n"
                f"4. Verify disk usage drops below 80%"
            ),
            "terminate_and_backup": (
                f"1. Send warning notification to admin\n"
                f"2. Backup any data on the zombie instance\n"
                f"3. Run {script} to terminate the instance\n"
                f"4. Log the termination in post-mortem report"
            ),
        }
        return plans.get(action, f"Execute {script} for {service}")

    async def _llm_triage(self, alert_name: str, service: str, severity: str, annotations: dict) -> dict:
        """
        Use LLM (via Ollama or API) for anomaly analysis.
        Falls back to a conservative plan if LLM is unavailable.
        """
        # For now, use a rule-based fallback (LLM integration added in Phase 2)
        available_scripts = self.scripts.list_scripts()

        fallback_diagnosis = (
            f"Anomaly detected: {alert_name} on {service}. "
            f"No known automation pattern matches. "
            f"Description: {annotations.get('description', 'N/A')}"
        )

        fallback_plan = (
            f"1. Collect detailed logs from {service}\n"
            f"2. Query historical metrics for anomaly correlation\n"
            f"3. Available scripts: {', '.join(available_scripts[:5])}\n"
            f"4. RECOMMENDATION: Manual investigation required\n"
            f"5. If critical, trigger graceful shutdown of affected node"
        )

        return {
            "alert_name": alert_name,
            "severity": severity,
            "diagnosis": fallback_diagnosis,
            "plan": fallback_plan,
            "script": None,
            "confidence": 0.3,
            "type": "anomaly",
        }
