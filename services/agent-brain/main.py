"""
ASH-Fabric Agent Brain — FastAPI Application
The LLM-driven decision engine for cloud infrastructure self-healing.
"""

import os
import json
import asyncio
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import structlog
import nats

from agents.triage_agent import TriageAgent
from agents.execution_agent import ExecutionAgent
from agents.audit_agent import AuditAgent
from tools.metrics_reader import MetricsReader
from tools.script_manager import ScriptManager
from config.settings import Settings

# ── Logging ──────────────────────────────────────────────────
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ]
)
logger = structlog.get_logger()

# ── Settings ─────────────────────────────────────────────────
settings = Settings()

# ── Shared state ─────────────────────────────────────────────
app_state = {
    "nats_client": None,
    "activity_log": [],  # In-memory log for dashboard
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup/shutdown lifecycle."""
    logger.info("agent_brain_starting", nats_url=settings.nats_url)

    # Connect to NATS
    try:
        nc = await nats.connect(settings.nats_url)
        app_state["nats_client"] = nc
        logger.info("nats_connected")

        # Subscribe to decision requests
        await nc.subscribe("agent.decisions", cb=on_decision_request)
        logger.info("subscribed_to_agent_decisions")
    except Exception as e:
        logger.warning("nats_connection_failed", error=str(e))

    yield  # App is running

    # Shutdown
    if app_state["nats_client"]:
        await app_state["nats_client"].drain()
        logger.info("nats_drained")


app = FastAPI(
    title="ASH-Fabric Agent Brain",
    version="0.1.0",
    description="LLM-driven decision engine for autonomous cloud healing",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Initialize tools ─────────────────────────────────────────
metrics_reader = MetricsReader(settings.vm_endpoint)
script_manager = ScriptManager(settings.scripts_dir)

# ── Initialize agents ────────────────────────────────────────
triage_agent = TriageAgent(metrics_reader, script_manager, settings)
execution_agent = ExecutionAgent(script_manager, settings)
audit_agent = AuditAgent(metrics_reader, settings)


# ── Request/Response Models ──────────────────────────────────

class TriageRequest(BaseModel):
    alert: dict
    action: str = "triage"


class TriageResponse(BaseModel):
    alert_name: str
    severity: str
    diagnosis: str
    plan: str
    recommended_script: str | None = None
    confidence: float
    timestamp: str


class ExecuteRequest(BaseModel):
    script: str
    service: str
    variables: dict = {}


class AuditRequest(BaseModel):
    metric: str
    threshold: float
    service: str
    action_taken: str


class StatusResponse(BaseModel):
    service: str = "ash-agent-brain"
    nats_connected: bool
    agents_loaded: int
    scripts_available: int
    activity_log_size: int


# ── API Endpoints ────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/api/v1/status", response_model=StatusResponse)
async def status():
    return StatusResponse(
        nats_connected=app_state["nats_client"] is not None
        and not app_state["nats_client"].is_closed,
        agents_loaded=3,
        scripts_available=script_manager.count_scripts(),
        activity_log_size=len(app_state["activity_log"]),
    )


@app.post("/api/v1/triage", response_model=TriageResponse)
async def triage(request: TriageRequest, background_tasks: BackgroundTasks):
    """
    Analyze an alert and produce a remediation plan.
    Known patterns → deterministic script selection.
    Anomalies → LLM-driven analysis.
    """
    logger.info("triage_request", alert=request.alert)

    try:
        result = await triage_agent.analyze(request.alert)
    except Exception as e:
        logger.error("triage_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Triage failed: {e}")

    # Log activity
    log_entry = {
        "type": "triage",
        "alert": request.alert.get("labels", {}).get("alertname", "unknown"),
        "result": result.get("diagnosis", ""),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    app_state["activity_log"].append(log_entry)

    # Publish result to NATS
    if app_state["nats_client"] and not app_state["nats_client"].is_closed:
        await app_state["nats_client"].publish(
            "agent.triage.result", json.dumps(log_entry).encode()
        )

    return TriageResponse(
        alert_name=result.get("alert_name", "unknown"),
        severity=result.get("severity", "unknown"),
        diagnosis=result.get("diagnosis", ""),
        plan=result.get("plan", ""),
        recommended_script=result.get("script"),
        confidence=result.get("confidence", 0.0),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@app.post("/api/v1/execute")
async def execute(request: ExecuteRequest, background_tasks: BackgroundTasks):
    """Execute a remediation script with dynamic variables."""
    logger.info("execute_request", script=request.script, service=request.service)

    try:
        result = await execution_agent.run_script(
            request.script, request.service, request.variables
        )
    except Exception as e:
        logger.error("execution_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Execution failed: {e}")

    # Schedule audit after 60 seconds
    background_tasks.add_task(
        audit_agent.verify_after_delay,
        delay_seconds=60,
        service=request.service,
        action_taken=request.script,
    )

    return {"status": "executed", "result": result}


@app.post("/api/v1/audit")
async def audit(request: AuditRequest):
    """Manually trigger an audit check for a service metric."""
    result = await audit_agent.check(
        metric=request.metric,
        threshold=request.threshold,
        service=request.service,
        action_taken=request.action_taken,
    )
    return result


@app.get("/api/v1/activity")
async def activity_log(limit: int = 50):
    """Return recent activity log for the dashboard."""
    return {"entries": app_state["activity_log"][-limit:]}


@app.get("/api/v1/scripts")
async def list_scripts():
    """List available remediation scripts."""
    return {"scripts": script_manager.list_scripts()}


# ── NATS Callback ────────────────────────────────────────────

async def on_decision_request(msg):
    """Handle decision requests from the orchestrator via NATS."""
    try:
        data = json.loads(msg.data.decode())
        logger.info("nats_decision_request", data=data)

        if data.get("type") == "anomaly":
            result = await triage_agent.analyze(data)
            if msg.reply:
                await app_state["nats_client"].publish(
                    msg.reply, json.dumps(result).encode()
                )
    except Exception as e:
        logger.error("nats_callback_error", error=str(e))
