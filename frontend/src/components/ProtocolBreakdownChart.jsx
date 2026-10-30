import React from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend
} from 'recharts';

export default function ProtocolBreakdownChart({ timeseriesData }) {
  if (!timeseriesData || timeseriesData.length === 0) {
    return (
      <div className="empty-state">
        <p>No protocol decomposition telemetry available.</p>
      </div>
    );
  }

  return (
    <div style={{ width: '100%', height: 320 }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={timeseriesData} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
          <XAxis
            dataKey="timestamp"
            stroke="#64748b"
            tick={{ fill: '#64748b', fontSize: 11, fontFamily: 'var(--font-mono)' }}
          />
          <YAxis
            stroke="#64748b"
            unit="ms"
            tick={{ fill: '#64748b', fontSize: 11, fontFamily: 'var(--font-mono)' }}
            domain={[0, 'auto']}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#0f172a',
              borderColor: '#334155',
              borderRadius: '8px',
              color: '#f8fafc',
              fontSize: '12px',
              fontFamily: 'var(--font-mono)',
              boxShadow: '0 8px 24px rgba(0,0,0,0.5)'
            }}
          />
          <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }} />
          <Line
            type="monotone"
            dataKey="avg_dns_latency_ms"
            name="DNS Resolution (ms)"
            stroke="#38bdf8"
            strokeWidth={2}
            dot={{ r: 2 }}
          />
          <Line
            type="monotone"
            dataKey="avg_tcp_latency_ms"
            name="TCP Handshake (ms)"
            stroke="#fbbf24"
            strokeWidth={2}
            dot={{ r: 2 }}
          />
          <Line
            type="monotone"
            dataKey="avg_http_latency_ms"
            name="HTTP Latency (ms)"
            stroke="#a855f7"
            strokeWidth={2}
            dot={{ r: 2 }}
          />
          <Line
            type="monotone"
            dataKey="avg_packet_loss_pct"
            name="Packet Loss (%)"
            stroke="#f43f5e"
            strokeWidth={2}
            strokeDasharray="3 3"
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
