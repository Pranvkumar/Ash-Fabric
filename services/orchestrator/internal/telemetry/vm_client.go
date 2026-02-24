package telemetry

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"time"

	"github.com/rs/zerolog/log"
)

// VMClient is a lightweight client for VictoriaMetrics queries.
type VMClient struct {
	baseURL    string
	httpClient *http.Client
}

// NewVMClient creates a new VictoriaMetrics client.
func NewVMClient(baseURL string) *VMClient {
	return &VMClient{
		baseURL: baseURL,
		httpClient: &http.Client{
			Timeout: 10 * time.Second,
		},
	}
}

// QueryResult represents a VictoriaMetrics instant query result.
type QueryResult struct {
	Status string `json:"status"`
	Data   struct {
		ResultType string `json:"resultType"`
		Result     []struct {
			Metric map[string]string `json:"metric"`
			Value  [2]interface{}    `json:"value"`
		} `json:"result"`
	} `json:"data"`
}

// Query executes an instant PromQL query against VictoriaMetrics.
func (c *VMClient) Query(promql string) (*QueryResult, error) {
	endpoint := fmt.Sprintf("%s/api/v1/query?query=%s", c.baseURL, url.QueryEscape(promql))
	log.Debug().Str("query", promql).Msg("Querying VictoriaMetrics")

	resp, err := c.httpClient.Get(endpoint)
	if err != nil {
		return nil, fmt.Errorf("VM query failed: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("read VM response: %w", err)
	}

	var result QueryResult
	if err := json.Unmarshal(body, &result); err != nil {
		return nil, fmt.Errorf("parse VM response: %w", err)
	}

	if result.Status != "success" {
		return nil, fmt.Errorf("VM query returned status: %s", result.Status)
	}

	return &result, nil
}

// QueryMetricValue returns the latest float value for a PromQL expression.
func (c *VMClient) QueryMetricValue(promql string) (float64, error) {
	result, err := c.Query(promql)
	if err != nil {
		return 0, err
	}

	if len(result.Data.Result) == 0 {
		return 0, fmt.Errorf("no data for query: %s", promql)
	}

	// Value is [timestamp, "value_string"]
	valStr, ok := result.Data.Result[0].Value[1].(string)
	if !ok {
		return 0, fmt.Errorf("unexpected value type in VM response")
	}

	var val float64
	_, err = fmt.Sscanf(valStr, "%f", &val)
	if err != nil {
		return 0, fmt.Errorf("parse metric value '%s': %w", valStr, err)
	}

	return val, nil
}

// Push writes a metric to VictoriaMetrics via the import API.
func (c *VMClient) Push(metricLine string) error {
	endpoint := fmt.Sprintf("%s/api/v1/import/prometheus", c.baseURL)
	resp, err := c.httpClient.Post(endpoint, "text/plain", nil)
	if err != nil {
		return fmt.Errorf("push metric: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 400 {
		body, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("push metric failed (%d): %s", resp.StatusCode, string(body))
	}
	return nil
}

// IsHealthy checks if VictoriaMetrics is reachable.
func (c *VMClient) IsHealthy() bool {
	endpoint := fmt.Sprintf("%s/health", c.baseURL)
	resp, err := c.httpClient.Get(endpoint)
	if err != nil {
		return false
	}
	defer resp.Body.Close()
	return resp.StatusCode == http.StatusOK
}
