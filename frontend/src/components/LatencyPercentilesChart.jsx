import React from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend
} from 'recharts';

export default function LatencyPercentilesChart({ timeseriesData }) {
  if (!timeseriesData || timeseriesData.length === 0) {
    return (
      <div className="empty-state">
        <p>No time-series latency data recorded for this window yet.</p>
        <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
          Ensure the Python telemetry probe is running.
        </span>
      </div>
    );
  }

  return (
    <div style={{ width: '100%', height: 320 }}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={timeseriesData} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
          <defs>
            <linearGradient id="p95Grad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0.0} />
            </linearGradient>
            <linearGradient id="p50Grad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.0} />
            </linearGradient>
          </defs>
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
          <Legend
            wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }}
          />
          <Area
            type="monotone"
            dataKey="p95_latency_ms"
            name="P95 Latency"
            stroke="#8b5cf6"
            strokeWidth={2}
            fillOpacity={1}
            fill="url(#p95Grad)"
          />
          <Area
            type="monotone"
            dataKey="avg_http_latency_ms"
            name="Avg Latency"
            stroke="#06b6d4"
            strokeWidth={2}
            fillOpacity={0}
          />
          <Line
            type="monotone"
            dataKey="uptime_pct"
            yAxisId={0}
            name="Uptime %"
            stroke="#10b981"
            strokeWidth={1.5}
            strokeDasharray="4 4"
            dot={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
