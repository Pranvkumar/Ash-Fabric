# **ASH-Fabric: Autonomous Self-Healing Cloud Fabric**

## **Project Overview**

An agentic automation system designed to monitor, predict, and remediate cloud infrastructure bottlenecks. It leverages LLM-driven agents to manage resources via Infrastructure as Code (IaC) and event-driven triggers.

### **1\. Core Rules & Design Principles**

* **Deterministic First:** Prioritize hard-coded automation (bash/python scripts) for 80% of known issues. Only use LLMs for high-complexity triage or "unseen" failures.  
* **Human-in-the-loop (Optional):** Define "SafeZones." Destructive actions (deleting volumes, killing databases) require manual approval.  
* **Idempotency:** All scripts must be safe to run multiple times (e.g., mkdir \-p instead of mkdir).  
* **Observability-Driven:** "No data, no action." Every automated fix must be preceded by a Prometheus query and followed by a validation check.  
* **Resource Conservation:** Agents must run on "Small" LLM models (e.g., Llama-3-8B or Gemini Flash) to minimize API/Compute costs.

### **2\. Logical Structure (Expanded)**

#### **Layer 1: Telemetry (The Senses)**

* **Metrics:** Prometheus scrapes CPU, RAM, Disk, and Network IO.  
* **Logs:** Fluent Bit forwards error logs to a lightweight indexer.  
* **Triggers:** Alertmanager sends JSON payloads to the NATS bus when thresholds are breached.

#### **Layer 2: Decision Layer (The Brain)**

* **Triage Agent:** Parses Alertmanager JSON. Determines if the fix is a "Known Pattern" (Run Script) or "Anomaly" (Consult LLM).  
* **Execution Agent:** Manages a library of Terraform and Ansible scripts. It performs "Variable Injection" to customize scripts for specific nodes.  
* **Audit Agent:** Compares "Before" and "After" metrics. If the fix fails, it triggers a rollback.

#### **Layer 3: Execution (The Hands)**

* **Container Orchestration:** K3s (Lightweight Kubernetes) or Docker Swarm.  
* **Cloud Interface:** Terraform providers (AWS/GCP) or local Libvirt/KVM for hardware.  
* **Config Management:** Ansible pulls from a GitOps repository (Local GitLab or GitHub).

#### **Layer 4: Interface (The Command Center)**

* **Dashboard:** Next.js \+ Tailwind. Shows a live "Activity Log" of what the agents are currently "thinking" and "doing."

### **3\. Comprehensive Tech Stack**

* **Languages:** \* **Golang:** Core control plane and NATS subscribers (High performance, low memory).  
  * **Python:** Agent logic (CrewAI/LangGraph) and data science libraries.  
  * **TypeScript:** React/Next.js frontend.  
* **Infrastructure:** \* **Orchestration:** K3s (Uses \< 512MB RAM).  
  * **Event Bus:** NATS (Significantly lighter than Kafka).  
  * **Database:** SQLite (Metadata) \+ VictoriaMetrics (Drop-in, low-resource Prometheus alternative).  
* **AI/LLM:** \* **Local:** Ollama (running Llama-3 or Mistral).  
  * **Cloud:** Gemini-2.5-Flash (High context, lowest cost/latency).

### **4\. Resource Optimization Strategy**

To build this on limited hardware (e.g., a single laptop or a small VPS):

1. **Mock Everything First:** Use "Mock Providers" for Terraform so you don't actually spin up expensive cloud instances during development.  
2. **VictoriaMetrics:** Use this instead of full Prometheus to save 30-50% RAM.  
3. **NATS JetStream:** Use for persistence instead of a heavy database for the event log.  
4. **Quantized Models:** Use 4-bit quantized GGUF models via Ollama to keep LLM memory usage under 6GB.