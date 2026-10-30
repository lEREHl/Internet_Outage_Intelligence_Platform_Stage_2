import React from 'react';

export default function GlobalHealthCard({ summary, loading }) {
  if (loading && !summary) {
    return (
      <div className="global-health-banner">
        <div className="health-status-col">
          <div className="loader-spinner"></div>
          <div>Loading system reliability status...</div>
        </div>
      </div>
    );
  }

  const uptime = summary?.uptime_pct ?? 100.0;
  const avgLoss = summary?.avg_packet_loss_pct ?? 0.0;

  let statusText = 'Normal Operational';
  let statusIcon = '🟢';
  let statusColor = 'var(--status-green)';
  let statusDesc = 'All monitored targets and distributed telemetry probes are responding within expected latency thresholds.';

  if (uptime < 90.0 || avgLoss > 20.0) {
    statusText = 'Major Outage Detected';
    statusIcon = '🔴';
    statusColor = 'var(--status-red)';
    statusDesc = 'Critical packet loss or elevated failure rates observed across multi-target probe measurements.';
  } else if (uptime < 98.0 || avgLoss > 2.0 || (summary?.p95_latency_ms ?? 0) > 400) {
    statusText = 'Performance Degraded';
    statusIcon = '🟡';
    statusColor = 'var(--status-yellow)';
    statusDesc = 'Noticeable packet loss or elevated P95 latency detected across one or more monitored endpoints.';
  }

  return (
    <div className="global-health-banner" style={{ borderLeft: `5px solid ${statusColor}` }}>
      <div className="health-status-col">
        <span className="health-icon-large">{statusIcon}</span>
        <div className="health-status-text">
          <h2 style={{ color: statusColor }}>{statusText}</h2>
          <p>{statusDesc}</p>
        </div>
      </div>

      <div className="health-stat-pills">
        <div className="stat-pill">
          <div className="label">Active Probes</div>
          <div className="value">{summary?.active_probes_count || 1}</div>
        </div>
        <div className="stat-pill">
          <div className="label">Monitored Targets</div>
          <div className="value">{summary?.active_targets_count || 5}</div>
        </div>
        <div className="stat-pill">
          <div className="label">Telemetry Checks</div>
          <div className="value">{summary?.total_checks?.toLocaleString() || 0}</div>
        </div>
      </div>
    </div>
  );
}
