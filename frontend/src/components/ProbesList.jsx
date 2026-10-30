import React from 'react';

export default function ProbesList({ probes }) {
  if (!probes || probes.length === 0) {
    return (
      <div className="empty-state">
        <p>No active probe agents registered.</p>
      </div>
    );
  }

  return (
    <div className="probes-list">
      {probes.map((probe) => {
        const heartbeatTime = new Date(probe.last_heartbeat).toLocaleTimeString();
        return (
          <div key={probe.probe_id} className="probe-row">
            <div className="probe-info-main">
              <div
                className="probe-icon-dot"
                style={{
                  backgroundColor: probe.status === 'active' ? 'var(--status-green)' : 'var(--text-muted)'
                }}
              />
              <div>
                <div className="probe-name-bold">{probe.name}</div>
                <div className="probe-loc">
                  📍 {probe.location} • <span style={{ fontFamily: 'var(--font-mono)' }}>{probe.probe_id}</span>
                </div>
              </div>
            </div>

            <div className="probe-meta-right">
              <span className="badge-success">● Active</span>
              <div className="probe-heartbeat">Heartbeat: {heartbeatTime}</div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
