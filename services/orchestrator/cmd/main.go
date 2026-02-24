package main

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/ash-fabric/orchestrator/internal/agents"
	natsbus "github.com/ash-fabric/orchestrator/internal/nats"
	"github.com/ash-fabric/orchestrator/internal/telemetry"
	"github.com/rs/zerolog"
	"github.com/rs/zerolog/log"
)

func main() {
	// ── Pretty logging ──────────────────────────────────────
	zerolog.TimeFieldFormat = time.RFC3339
	log.Logger = log.Output(zerolog.ConsoleWriter{Out: os.Stdout, TimeFormat: time.RFC3339})

	log.Info().Msg("🚀 ASH-Fabric Orchestrator starting...")

	// ── Configuration ───────────────────────────────────────
	natsURL := envOrDefault("NATS_URL", "nats://localhost:4222")
	vmEndpoint := envOrDefault("VM_ENDPOINT", "http://localhost:8428")
	agentBrainURL := envOrDefault("AGENT_BRAIN_URL", "http://localhost:8000")
	listenAddr := envOrDefault("LISTEN_ADDR", ":8080")

	// ── Connect to NATS ─────────────────────────────────────
	bus, err := natsbus.Connect(natsURL)
	if err != nil {
		log.Fatal().Err(err).Msg("Failed to connect to NATS")
	}
	defer bus.Close()
	log.Info().Str("url", natsURL).Msg("Connected to NATS")

	// ── Initialize subsystems ───────────────────────────────
	metricsClient := telemetry.NewVMClient(vmEndpoint)
	triageRouter := agents.NewTriageRouter(agentBrainURL, metricsClient, bus)

	// ── Subscribe to alert topics ───────────────────────────
	if err := bus.Subscribe("telemetry.alerts", triageRouter.HandleAlert); err != nil {
		log.Fatal().Err(err).Msg("Failed to subscribe to telemetry.alerts")
	}
	log.Info().Msg("Subscribed to telemetry.alerts")

	if err := bus.Subscribe("telemetry.metrics", triageRouter.HandleMetric); err != nil {
		log.Fatal().Err(err).Msg("Failed to subscribe to telemetry.metrics")
	}
	log.Info().Msg("Subscribed to telemetry.metrics")

	// ── HTTP API (receives Alertmanager webhooks) ───────────
	mux := http.NewServeMux()
	mux.HandleFunc("/api/v1/alerts", alertWebhookHandler(bus))
	mux.HandleFunc("/api/v1/status", statusHandler(bus, metricsClient))
	mux.HandleFunc("/metrics", metricsHandler())
	mux.HandleFunc("/health", healthHandler())

	server := &http.Server{
		Addr:         listenAddr,
		Handler:      mux,
		ReadTimeout:  10 * time.Second,
		WriteTimeout: 30 * time.Second,
	}

	// ── Graceful shutdown ───────────────────────────────────
	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	go func() {
		log.Info().Str("addr", listenAddr).Msg("HTTP server listening")
		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatal().Err(err).Msg("HTTP server failed")
		}
	}()

	<-ctx.Done()
	log.Info().Msg("Shutdown signal received, draining...")

	shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	_ = server.Shutdown(shutdownCtx)

	log.Info().Msg("ASH-Fabric Orchestrator stopped.")
}

// ── HTTP Handlers ──────────────────────────────────────────────

// alertWebhookHandler receives Alertmanager webhook POSTs and publishes to NATS
func alertWebhookHandler(bus *natsbus.Bus) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}

		var payload AlertmanagerPayload
		if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
			log.Error().Err(err).Msg("Invalid alertmanager payload")
			http.Error(w, "Invalid JSON", http.StatusBadRequest)
			return
		}

		for _, alert := range payload.Alerts {
			data, _ := json.Marshal(alert)
			if err := bus.Publish("telemetry.alerts", data); err != nil {
				log.Error().Err(err).Str("alertname", alert.Labels["alertname"]).Msg("Failed to publish alert")
				continue
			}
			log.Info().
				Str("alertname", alert.Labels["alertname"]).
				Str("status", alert.Status).
				Msg("Alert forwarded to NATS")
		}

		w.WriteHeader(http.StatusOK)
		fmt.Fprintf(w, `{"status":"ok","forwarded":%d}`, len(payload.Alerts))
	}
}

func statusHandler(bus *natsbus.Bus, mc *telemetry.VMClient) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		status := map[string]interface{}{
			"service":   "ash-orchestrator",
			"nats":      bus.IsConnected(),
			"timestamp": time.Now().UTC().Format(time.RFC3339),
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(status)
	}
}

func metricsHandler() http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		// Minimal Prometheus metrics endpoint
		fmt.Fprintf(w, `# HELP ash_orchestrator_up Whether the orchestrator is running
# TYPE ash_orchestrator_up gauge
ash_orchestrator_up 1
# HELP ash_alerts_received_total Total alerts received
# TYPE ash_alerts_received_total counter
ash_alerts_received_total 0
`)
	}
}

func healthHandler() http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		fmt.Fprint(w, `{"status":"healthy"}`)
	}
}

// ── Types ──────────────────────────────────────────────────────

type AlertmanagerPayload struct {
	Alerts []Alert `json:"alerts"`
}

type Alert struct {
	Status      string            `json:"status"`
	Labels      map[string]string `json:"labels"`
	Annotations map[string]string `json:"annotations"`
	StartsAt    string            `json:"startsAt"`
	EndsAt      string            `json:"endsAt"`
}

// ── Helpers ────────────────────────────────────────────────────

func envOrDefault(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}
