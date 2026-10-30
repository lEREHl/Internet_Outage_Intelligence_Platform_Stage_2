import React from 'react';

export default function TargetHealthGrid({ targetsHealth, onSelectTarget, selectedTarget }) {
  if (!targetsHealth || targetsHealth.length === 0) {
    return (
      <div className="empty-state">
        <p>No target telemetry aggregated yet.</p>
      </div>
    );
  }

  return (
    <div className="target-cards-grid">
      {targetsHealth.map((t) => {
        const isSelected = selectedTarget === t.target;
        const uptime = t.uptime_pct ?? 100.0;
        const loss = t.avg_packet_loss_pct ?? 0.0;

        let badgeClass = 'healthy';
        let badgeLabel = 'Healthy';

        if (uptime < 90.0 || loss > 25.0) {
          badgeClass = 'down';
          badgeLabel = 'Outage';
        } else if (uptime < 98.0 || loss > 2.0 || (t.p95_latency_ms || 0) > 350) {
          badgeClass = 'degraded';
          badgeLabel = 'Degraded';
        }

        const cleanName = t.target
          .replace('https://', '')
          .replace('http://', '')
          .replace('www.', '');

        return (
          <div
            key={t.target}
            className={`target-card ${isSelected ? 'selected' : ''}`}
            onClick={() => onSelectTarget(isSelected ? null : t.target)}
            style={{
              cursor: 'pointer',
              borderLeft: isSelected ? '4px solid var(--accent-blue)' : undefined,
              boxShadow: isSelected ? '0 0 12px rgba(59,130,246,0.3)' : undefined
            }}
          >
            <div className="target-card-top">
              <div>
                <div className="target-name">{cleanName}</div>
                <div className="target-url-sub" title={t.target}>{t.target}</div>
              </div>
              <span className={`status-badge ${badgeClass}`}>{badgeLabel}</span>
            </div>

            <div className="target-metrics-mini">
              <div className="mini-metric-item">
                <div className="label">Uptime</div>
                <div className="val" style={{ color: uptime >= 98 ? 'var(--status-green)' : 'var(--status-red)' }}>
                  {uptime}%
                </div>
              </div>

              <div className="mini-metric-item">
                <div className="label">P95 Lat</div>
                <div className="val" style={{ color: 'var(--accent-cyan)' }}>
                  {t.p95_latency_ms ? `${t.p95_latency_ms}ms` : '—'}
                </div>
              </div>

              <div className="mini-metric-item">
                <div className="label">Loss</div>
                <div className="val" style={{ color: loss > 0 ? 'var(--status-yellow)' : 'var(--text-secondary)' }}>
                  {loss}%
                </div>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
