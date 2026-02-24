"""
Mock Telemetry Exporter — Generates fake metrics for development.
Pushes to VictoriaMetrics and publishes alerts to NATS when thresholds breach.
"""

import os
import time
import random
import json
import requests
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("mock-exporter")

VM_ENDPOINT = os.getenv("VM_ENDPOINT", "http://localhost:8428")
PUSH_INTERVAL = int(os.getenv("PUSH_INTERVAL", "30"))

# Simulated services
SERVICES = ["api-gateway", "auth-service", "payment-service", "user-service"]

# Metric templates
METRICS = {
    "node_cpu_usage_percent": {"min": 20, "max": 100, "spike_prob": 0.15},
    "node_memory_usage_percent": {"min": 30, "max": 100, "spike_prob": 0.10},
    "node_disk_usage_percent": {"min": 40, "max": 100, "spike_prob": 0.05},
    "http_request_duration_ms": {"min": 50, "max": 800, "spike_prob": 0.12},
}


def generate_metric_value(config: dict) -> float:
    """Generate a metric value with occasional spikes."""
    if random.random() < config["spike_prob"]:
        # Spike: high end of range
        return round(random.uniform(config["max"] * 0.85, config["max"]), 1)
    else:
        # Normal: lower half
        return round(random.uniform(config["min"], config["max"] * 0.65), 1)


def format_prometheus_line(metric: str, value: float, labels: dict) -> str:
    """Format a single Prometheus text line."""
    label_str = ",".join(f'{k}="{v}"' for k, v in labels.items())
    timestamp_ms = int(time.time() * 1000)
    return f"{metric}{{{label_str}}} {value} {timestamp_ms}"


def push_metrics(lines: list[str]):
    """Push metrics to VictoriaMetrics via the Prometheus import API."""
    url = f"{VM_ENDPOINT}/api/v1/import/prometheus"
    payload = "\n".join(lines) + "\n"
    try:
        resp = requests.post(url, data=payload, headers={"Content-Type": "text/plain"})
        if resp.status_code < 300:
            logger.info(f"Pushed {len(lines)} metrics to VictoriaMetrics")
        else:
            logger.warning(f"VM push returned {resp.status_code}: {resp.text}")
    except requests.ConnectionError:
        logger.warning("VictoriaMetrics not reachable, retrying next cycle...")


def main():
    logger.info(f"Mock Exporter starting — pushing every {PUSH_INTERVAL}s to {VM_ENDPOINT}")

    while True:
        lines = []
        alerts = []

        for service in SERVICES:
            instance = f"{service}:9100"
            labels = {"service": service, "instance": instance, "job": "mock-exporter"}

            for metric_name, config in METRICS.items():
                value = generate_metric_value(config)
                lines.append(format_prometheus_line(metric_name, value, labels))

                # Check thresholds for alert simulation
                thresholds = {
                    "node_cpu_usage_percent": 90,
                    "node_memory_usage_percent": 95,
                    "node_disk_usage_percent": 90,
                    "http_request_duration_ms": 500,
                }
                threshold = thresholds.get(metric_name, 100)
                if value > threshold:
                    alert = {
                        "metric": metric_name,
                        "value": value,
                        "threshold": threshold,
                        "service": service,
                        "instance": instance,
                    }
                    alerts.append(alert)
                    logger.warning(
                        f"THRESHOLD BREACH: {metric_name}={value} "
                        f"(>{threshold}) on {service}"
                    )

        # Push all metrics
        push_metrics(lines)

        # Log alerts (in production these come from Alertmanager)
        if alerts:
            logger.info(f"Generated {len(alerts)} alert(s) this cycle")
            for a in alerts:
                logger.info(f"  -> {a['metric']} = {a['value']} on {a['service']}")

        time.sleep(PUSH_INTERVAL)


if __name__ == "__main__":
    main()
