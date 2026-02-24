# **ASH-Fabric: Step-by-Step Implementation Roadmap**

## **Phase 1: The Foundation (Week 1\)**

* **Goal:** Set up the "Central Nervous System."  
* **Tasks:**  
  1. Deploy **NATS** via Docker.  
  2. Create a **Go service** (The Listener) that subscribes to telemetry.alerts.  
  3. Setup **VictoriaMetrics** and a mock "Exporter" that sends fake high-CPU data every 30 seconds.

## **Phase 2: The Agent Brain (Week 2\)**

* **Goal:** Connect the LLM to the event stream.  
* **Tasks:**  
  1. Implement a **Python service** using **CrewAI**.  
  2. Create a "Tool" that allows the agent to read from VictoriaMetrics.  
  3. Create a "Tool" that allows the agent to list files in a /scripts directory.  
  4. **The Test:** Send a "High CPU" alert. The agent should "read" the metric and "suggest" the correct script from the directory.

## **Phase 3: The Execution Loop (Week 3\)**

* **Goal:** Perform real (or mocked) infrastructure changes.  
* **Tasks:**  
  1. Integrate **Terraform** (using a local provider like Docker or Libvirt).  
  2. Write the **Execution Agent** logic to run terraform apply with dynamic variables.  
  3. Build the **Audit Agent** to check the metric again after 2 minutes.

## **Phase 4: Visualization & Security (Week 4\)**

* **Goal:** Monitor the system and prevent "Agent Hallucinations."  
* **Tasks:**  
  1. Build the **Next.js Dashboard**.  
  2. Implement "Approval Gates": The UI must show a "Pending Action" notification where a human clicks "Approve" before Terraform runs.  
  3. Finalize the **Post-Mortem Logger** to save every agent decision into a Markdown file for later review.

## **Critical Directory Structure**

/ash-fabric  
├── /services  
│   ├── /orchestrator (Go)      \# Routes messages between NATS and Agents  
│   ├── /agent-brain (Python)   \# CrewAI / LangGraph logic  
│   └── /dashboard (Next.js)    \# UI  
├── /infrastructure  
│   ├── /terraform              \# IaC templates  
│   └── /ansible                \# Remediation playbooks  
├── /telemetry  
│   ├── victoria-metrics.yml  
│   └── alerts.rules.yml        \# Logic for when to trigger an agent  
└── /data  
    ├── /logs                   \# Agent reasoning logs  
    └── sqlite.db               \# System state  
