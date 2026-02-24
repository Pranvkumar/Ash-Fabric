# ASH-Fabric: Autonomous Self-Healing Cloud Fabric

An agentic automation system that monitors, predicts, and remediates cloud infrastructure bottlenecks using LLM-driven agents, event-driven architecture, and Infrastructure as Code.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Layer 4: Dashboard (Next.js)              │
│                   Live Activity Log + Approval Gates        │
├─────────────────────────────────────────────────────────────┤
│                   Layer 3: Execution (The Hands)            │
│            Terraform │ Ansible │ Shell Scripts              │
├─────────────────────────────────────────────────────────────┤
│                   Layer 2: Decision (The Brain)             │
│       Triage Agent │ Execution Agent │ Audit Agent          │
│              CrewAI + Ollama/Gemini Flash                   │
├─────────────────────────────────────────────────────────────┤
│                   Layer 1: Telemetry (The Senses)           │
│       VictoriaMetrics │ Alertmanager │ NATS Event Bus       │
└─────────────────────────────────────────────────────────────┘
```

## Tech Stack

| Layer        | Technology                              |
|-------------|------------------------------------------|
| Event Bus   | NATS JetStream                           |
| Metrics     | VictoriaMetrics (Prometheus-compatible)  |
| Orchestrator| Go (high-performance NATS subscriber)    |
| Agent Brain | Python (FastAPI + CrewAI)                |
| Dashboard   | Next.js 14 + Tailwind CSS                |
| IaC         | Terraform (Docker provider) + Ansible    |
| LLM         | Ollama (local) / Gemini Flash (cloud)    |
| Database    | SQLite (metadata) + NATS JetStream (logs)|

## Project Structure

```
/ash-fabric
├── /services
│   ├── /orchestrator (Go)      # Routes NATS messages, receives Alertmanager webhooks
│   ├── /agent-brain (Python)   # CrewAI triage, execution, and audit agents
│   └── /dashboard (Next.js)    # Real-time command center UI
├── /infrastructure
│   ├── /terraform              # IaC templates (Docker provider for dev)
│   └── /ansible/playbooks      # Remediation playbooks
├── /telemetry
│   ├── alerts.rules.yml        # VMAlert rules (threshold triggers)
│   ├── alertmanager.yml        # Webhook routing to orchestrator
│   ├── victoria-metrics.yml    # Scrape configuration
│   └── mock_exporter.py        # Fake metric generator for dev
├── /scripts                    # Deterministic remediation scripts
│   ├── restart_service.sh
│   ├── scale_service.sh
│   ├── check_db.sh
│   ├── purge_disk.sh
│   └── terminate_zombie.sh
├── /data
│   └── /logs                   # Agent reasoning & post-mortem logs
└── docker-compose.yml          # Full stack orchestration
```

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Go 1.22+ (for local development)
- Python 3.12+ (for local development)
- Node.js 20+ (for dashboard development)

### Run the Full Stack

```bash
cd ash-fabric
docker compose up -d
```

This starts:
- **NATS** on `:4222` (event bus) + `:8222` (monitoring)
- **VictoriaMetrics** on `:8428` (metrics)
- **Alertmanager** on `:9093` (alerts)
- **Mock Exporter** pushing fake metrics every 30s
- **Go Orchestrator** on `:8080` (webhook receiver)
- **Python Agent Brain** on `:8000` (API + agents)
- **Dashboard** on `:3000` (UI)
- **Grafana** on `:3001` (optional visualization)

### Verify Services

```bash
# Check orchestrator health
curl http://localhost:8080/health

# Check agent brain status
curl http://localhost:8000/api/v1/status

# View available scripts
curl http://localhost:8000/api/v1/scripts

# Check NATS monitoring
curl http://localhost:8222/varz
```

### Simulate an Alert

```bash
curl -X POST http://localhost:8080/api/v1/alerts \
  -H "Content-Type: application/json" \
  -d '{
    "alerts": [{
      "status": "firing",
      "labels": {
        "alertname": "HighCPUUsage",
        "service": "api-gateway",
        "severity": "warning",
        "action": "scale_or_restart"
      },
      "annotations": {
        "summary": "CPU above 90% on api-gateway",
        "description": "Service api-gateway CPU at 94%"
      }
    }]
  }'
```

## Automation Logic

| Event | Condition | Automated Action | Secondary Action |
|-------|-----------|-----------------|------------------|
| OOM Kill | Memory > 95% | Restart Container | Scale memory +20% |
| Latency Spike | Latency > 500ms | Check DB connections | Spin up Read Replica |
| Zombie Resource | CPU < 1% for 4hrs | Send Warning | Terminate + backup |
| Disk Full | Storage > 90% | Purge /tmp & logs | Expand volume |
| Predictive Peak | Forecast > Capacity | Warm-up instances | Pre-fetch to Redis |

## Design Principles

1. **Deterministic First** — 80% of fixes use hard-coded scripts; LLMs only for unseen issues
2. **Human-in-the-Loop** — Destructive actions require approval via dashboard
3. **Idempotent** — All scripts are safe to run multiple times
4. **Observability-Driven** — Every fix is preceded by a metric query and followed by validation
5. **Resource Conservative** — Small LLM models, lightweight infra (K3s, NATS, SQLite)

## Development Roadmap

- [x] **Phase 1:** Foundation — NATS, VictoriaMetrics, Go Listener, Mock Exporter
- [ ] **Phase 2:** Agent Brain — CrewAI integration, LLM triage with Ollama
- [ ] **Phase 3:** Execution Loop — Terraform/Ansible automation with audit verification
- [ ] **Phase 4:** Dashboard & Security — Approval gates, live activity stream, post-mortem logger

---

*Built with the ASH-Fabric design philosophy: Monitor → Predict → Heal → Verify*
