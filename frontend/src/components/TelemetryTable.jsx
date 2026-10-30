import React from 'react';

export default function TelemetryTable({ measurements }) {
  if (!measurements || measurements.length === 0) {
    return (
      <div className="empty-state">
        <p>No telemetry records available yet.</p>
      </div>
    );
  }

  return (
    <div className="table-responsive">
      <table className="telemetry-table">
        <thead>
          <tr>
            <th>Timestamp</th>
            <th>Probe</th>
            <th>Target</th>
            <th>HTTP Latency</th>
            <th>DNS Resolution</th>
            <th>TCP Handshake</th>
            <th>Ping / Loss</th>
            <th>HTTP Status</th>
            <th>Result</th>
          </tr>
        </thead>
        <tbody>
          {measurements.map((m) => {
            const timeStr = new Date(m.timestamp).toLocaleTimeString([], {
              hour: '2-digit',
              minute: '2-digit',
              second: '2-digit'
            });

            const cleanTarget = m.target.replace('https://', '').replace('http://', '');

            return (
              <tr key={m.id}>
                <td className="code-cell" style={{ color: 'var(--text-secondary)' }}>
                  {timeStr}
                </td>
                <td className="code-cell">
                  <span style={{ color: '#93c5fd' }}>{m.probe_id}</span>
                </td>
                <td style={{ fontWeight: 600, color: '#f1f5f9' }}>
                  {cleanTarget}
                </td>
                <td className="code-cell" style={{ color: m.success ? 'var(--accent-cyan)' : 'var(--status-red)' }}>
                  {m.http_latency_ms !== null ? `${m.http_latency_ms} ms` : '—'}
                </td>
                <td className="code-cell">
                  {m.dns_latency_ms !== null ? `${m.dns_latency_ms} ms` : '—'}
                </td>
                <td className="code-cell">
                  {m.tcp_latency_ms !== null ? `${m.tcp_latency_ms} ms` : '—'}
                </td>
                <td className="code-cell">
                  {m.ping_latency_ms !== null ? `${m.ping_latency_ms} ms` : '—'}
                  {m.packet_loss_pct > 0 && (
                    <span style={{ color: 'var(--status-red)', marginLeft: '6px' }}>
                      ({m.packet_loss_pct}% loss)
                    </span>
                  )}
                </td>
                <td>
                  {m.status_code ? (
                    <span className={`code-pill ${m.success ? 'success' : 'fail'}`}>
                      {m.status_code}
                    </span>
                  ) : (
                    <span className="code-pill fail">ERR</span>
                  )}
                </td>
                <td>
                  {m.success ? (
                    <span className="badge-success">✓ OK</span>
                  ) : (
                    <span className="badge-fail" title={m.error_message || 'Check failed'}>
                      ✕ FAIL
                    </span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
