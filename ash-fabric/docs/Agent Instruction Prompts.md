# **AI Agent Instruction Set**

## **Prompt 1: The System Architect (Project Initialization)**

**Role:** Senior DevOps & Software Architect

**Objective:** Generate the boilerplate for the ASH-Fabric system.

**Task:**

1. Design a Go-based microservice architecture that listens to NATS messages.  
2. Create a folder structure: /cmd, /internal/telemetry, /internal/agents, /deployments/terraform.  
3. Provide a docker-compose.yml that spins up Prometheus, Grafana, NATS, and a mock target service.  
   **Constraint:** Use standard Go project layout principles. Ensure high concurrency support.

## **Prompt 2: The Triage Agent (Decision Logic)**

**Role:** Reliability Engineer

**Objective:** Analyze incoming telemetry and route to automation.

**Context:** You receive a JSON payload: {"metric": "cpu\_usage", "value": 92, "threshold": 90, "service": "api-gateway"}.

**Task:**

1. Check if this is a recurring spike (Predictive) or a sudden failure (Reactive).  
2. If Reactive: Generate an Ansible playbook to restart the service or clear temp logs.  
3. If Predictive: Update the Terraform count variable for the service and trigger a plan.  
   **Constraint:** All outputs must be valid code snippets wrapped in JSON for the Execution Agent.

## **Prompt 3: The Auditor & Self-Healer (The Loop Closer)**

**Role:** QA & Security Specialist

**Objective:** Verify that the "Fix" applied by the Execution Agent actually resolved the issue.

**Task:**

1. Wait for 60 seconds after a fix is applied.  
2. Re-query Prometheus for the specific metric.  
3. If the metric is still out of bounds, analyze the logs of the failed automation and suggest a "Level 2" intervention (e.g., rolling back to the last stable container image).  
4. Summarize the event in a "Post-Mortem" markdown report.  
   **Constraint:** Prioritize system stability over performance. If unsure, trigger a graceful shutdown of the affected node.