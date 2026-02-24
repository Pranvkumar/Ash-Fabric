package agents

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"

	natsbus "github.com/ash-fabric/orchestrator/internal/nats"
	"github.com/ash-fabric/orchestrator/internal/telemetry"
	"github.com/rs/zerolog/log"
)

// TriageRouter determines whether an alert is a known pattern or anomaly,
// then routes it to the appropriate handler.
type TriageRouter struct {
	agentBrainURL string
	metricsClient *telemetry.VMClient
	bus           *natsbus.Bus
	httpClient    *http.Client
	// knownPatterns maps alert action labels to script names
	knownPatterns map[string]string
}

// NewTriageRouter creates a new TriageRouter.
func NewTriageRouter(agentBrainURL string, mc *telemetry.VMClient, bus *natsbus.Bus) *TriageRouter {
	return &TriageRouter{
		agentBrainURL: agentBrainURL,
		metricsClient: mc,
		bus:           bus,
		httpClient:    &http.Client{Timeout: 30 * time.Second},
		knownPatterns: map[string]string{
			"restart_container":   "restart_service.sh",
			"scale_or_restart":    "scale_service.sh",
			"check_db_connections": "check_db.sh",
			"purge_and_expand":    "purge_disk.sh",
			"terminate_and_backup": "terminate_zombie.sh",
		},
	}
}

// AlertPayload is the JSON structure from Alertmanager.
type AlertPayload struct {
	Status      string            `json:"status"`
	Labels      map[string]string `json:"labels"`
	Annotations map[string]string `json:"annotations"`
	StartsAt    string            `json:"startsAt"`
}

// TriageDecision is published to NATS after analysis.
type TriageDecision struct {
	AlertName  string `json:"alert_name"`
	Service    string `json:"service"`
	Severity   string `json:"severity"`
	Type       string `json:"type"` // "known" or "anomaly"
	Action     string `json:"action"`
	Script     string `json:"script,omitempty"`
	AgentPlan  string `json:"agent_plan,omitempty"`
	Timestamp  string `json:"timestamp"`
}

// HandleAlert processes an alert from the telemetry.alerts NATS subject.
func (tr *TriageRouter) HandleAlert(msg []byte) {
	var alert AlertPayload
	if err := json.Unmarshal(msg, &alert); err != nil {
		log.Error().Err(err).Msg("Failed to parse alert payload")
		return
	}

	alertName := alert.Labels["alertname"]
	service := alert.Labels["service"]
	severity := alert.Labels["severity"]
	action := alert.Labels["action"]

	log.Info().
		Str("alert", alertName).
		Str("service", service).
		Str("severity", severity).
		Str("action", action).
		Msg("Processing alert")

	decision := TriageDecision{
		AlertName: alertName,
		Service:   service,
		Severity:  severity,
		Timestamp: time.Now().UTC().Format(time.RFC3339),
	}

	// ── Check if this is a known pattern ────────────────────
	if script, ok := tr.knownPatterns[action]; ok {
		decision.Type = "known"
		decision.Action = action
		decision.Script = script
		log.Info().Str("script", script).Msg("Known pattern matched — executing script")
	} else {
		// ── Anomaly: consult the LLM Agent Brain ────────────
		decision.Type = "anomaly"
		decision.Action = "consult_agent"
		plan, err := tr.consultAgentBrain(alert)
		if err != nil {
			log.Error().Err(err).Msg("Agent brain consultation failed")
			decision.AgentPlan = fmt.Sprintf("ERROR: %v", err)
		} else {
			decision.AgentPlan = plan
		}
		log.Info().Str("plan", decision.AgentPlan).Msg("Agent brain response")
	}

	// ── Publish decision to NATS ────────────────────────────
	data, _ := json.Marshal(decision)
	if err := tr.bus.Publish("agent.decisions", data); err != nil {
		log.Error().Err(err).Msg("Failed to publish triage decision")
	}
}

// HandleMetric processes a metric message (for predictive analysis).
func (tr *TriageRouter) HandleMetric(msg []byte) {
	var metric map[string]interface{}
	if err := json.Unmarshal(msg, &metric); err != nil {
		log.Error().Err(err).Msg("Failed to parse metric payload")
		return
	}
	log.Debug().Interface("metric", metric).Msg("Metric received (predictive pipeline)")
	// Future: feed into predictive model
}

// consultAgentBrain sends the alert to the Python agent-brain service.
func (tr *TriageRouter) consultAgentBrain(alert AlertPayload) (string, error) {
	payload, _ := json.Marshal(map[string]interface{}{
		"alert":  alert,
		"action": "triage",
	})

	resp, err := tr.httpClient.Post(
		fmt.Sprintf("%s/api/v1/triage", tr.agentBrainURL),
		"application/json",
		bytes.NewReader(payload),
	)
	if err != nil {
		return "", fmt.Errorf("agent brain request failed: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", fmt.Errorf("read agent brain response: %w", err)
	}

	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("agent brain returned %d: %s", resp.StatusCode, string(body))
	}

	var result map[string]interface{}
	if err := json.Unmarshal(body, &result); err != nil {
		return string(body), nil
	}

	if plan, ok := result["plan"].(string); ok {
		return plan, nil
	}
	return string(body), nil
}
