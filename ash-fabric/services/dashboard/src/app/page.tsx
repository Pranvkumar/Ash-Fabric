"use client";

import { useEffect, useState } from "react";

// ── Types ──────────────────────────────────────────────────

interface StatusData {
  service: string;
  nats_connected: boolean;
  agents_loaded: number;
  scripts_available: number;
  activity_log_size: number;
}

interface ActivityEntry {
  type: string;
  alert: string;
  result: string;
  timestamp: string;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ── Dashboard Page ─────────────────────────────────────────

export default function Dashboard() {
  const [status, setStatus] = useState<StatusData | null>(null);
  const [activity, setActivity] = useState<ActivityEntry[]>([]);
  const [scripts, setScripts] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000); // Poll every 5s
    return () => clearInterval(interval);
  }, []);

  async function fetchData() {
    try {
      const [statusRes, activityRes, scriptsRes] = await Promise.all([
        fetch(`${API_URL}/api/v1/status`).then((r) => r.json()),
        fetch(`${API_URL}/api/v1/activity?limit=20`).then((r) => r.json()),
        fetch(`${API_URL}/api/v1/scripts`).then((r) => r.json()),
      ]);
      setStatus(statusRes);
      setActivity(activityRes.entries || []);
      setScripts(scriptsRes.scripts || []);
    } catch (err) {
      console.error("Failed to fetch data:", err);
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="flex h-[60vh] items-center justify-center">
        <div className="animate-spin h-8 w-8 rounded-full border-2 border-ash-accent border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* ── Status Cards ──────────────────────────────────── */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatusCard
          label="NATS"
          value={status?.nats_connected ? "Connected" : "Disconnected"}
          color={status?.nats_connected ? "success" : "danger"}
        />
        <StatusCard
          label="Agents Loaded"
          value={String(status?.agents_loaded ?? 0)}
          color="accent"
        />
        <StatusCard
          label="Scripts Available"
          value={String(status?.scripts_available ?? 0)}
          color="accent"
        />
        <StatusCard
          label="Events Processed"
          value={String(status?.activity_log_size ?? 0)}
          color="warning"
        />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* ── Activity Log ──────────────────────────────── */}
        <div className="lg:col-span-2 rounded-xl border border-ash-border bg-ash-card p-5">
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-ash-muted">
            Live Activity Log
          </h2>
          {activity.length === 0 ? (
            <p className="text-ash-muted text-sm">
              No activity yet. Waiting for alerts...
            </p>
          ) : (
            <div className="space-y-2 max-h-[500px] overflow-y-auto">
              {activity
                .slice()
                .reverse()
                .map((entry, i) => (
                  <div
                    key={i}
                    className="flex items-start gap-3 rounded-lg border border-ash-border/50 bg-ash-bg/50 p-3 text-sm"
                  >
                    <TypeBadge type={entry.type} />
                    <div className="flex-1 min-w-0">
                      <div className="font-medium">{entry.alert}</div>
                      <div className="text-ash-muted truncate">
                        {entry.result}
                      </div>
                    </div>
                    <time className="text-xs text-ash-muted whitespace-nowrap">
                      {new Date(entry.timestamp).toLocaleTimeString()}
                    </time>
                  </div>
                ))}
            </div>
          )}
        </div>

        {/* ── Scripts Panel ─────────────────────────────── */}
        <div className="rounded-xl border border-ash-border bg-ash-card p-5">
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-ash-muted">
            Remediation Scripts
          </h2>
          {scripts.length === 0 ? (
            <p className="text-ash-muted text-sm">No scripts loaded.</p>
          ) : (
            <ul className="space-y-2">
              {scripts.map((script) => (
                <li
                  key={script}
                  className="flex items-center gap-2 rounded-lg border border-ash-border/50 bg-ash-bg/50 px-3 py-2 text-sm font-mono"
                >
                  <span className="text-ash-accent">$</span>
                  {script}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Sub-Components ──────────────────────────────────────────

function StatusCard({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color: "success" | "danger" | "warning" | "accent";
}) {
  const colorMap = {
    success: "bg-ash-success/10 text-ash-success border-ash-success/20",
    danger: "bg-ash-danger/10 text-ash-danger border-ash-danger/20",
    warning: "bg-ash-warning/10 text-ash-warning border-ash-warning/20",
    accent: "bg-ash-accent/10 text-ash-accent border-ash-accent/20",
  };

  return (
    <div className="rounded-xl border border-ash-border bg-ash-card p-4">
      <div className="text-xs font-semibold uppercase tracking-wider text-ash-muted mb-2">
        {label}
      </div>
      <div
        className={`inline-block rounded-full px-3 py-1 text-sm font-semibold border ${colorMap[color]}`}
      >
        {value}
      </div>
    </div>
  );
}

function TypeBadge({ type }: { type: string }) {
  const styles: Record<string, string> = {
    triage: "bg-blue-500/20 text-blue-400",
    execute: "bg-amber-500/20 text-amber-400",
    audit: "bg-emerald-500/20 text-emerald-400",
  };

  return (
    <span
      className={`mt-0.5 rounded px-1.5 py-0.5 text-xs font-semibold uppercase ${
        styles[type] || "bg-gray-500/20 text-gray-400"
      }`}
    >
      {type}
    </span>
  );
}
