import React, { useState, useEffect, useCallback } from 'react';
import GlobalHealthCard from './components/GlobalHealthCard';
import LatencyPercentilesChart from './components/LatencyPercentilesChart';
import ProtocolBreakdownChart from './components/ProtocolBreakdownChart';
import TargetHealthGrid from './components/TargetHealthGrid';
import ProbesList from './components/ProbesList';
import TelemetryTable from './components/TelemetryTable';

const API_BASE = 'http://127.0.0.1:8000/api';

export default function App() {
  const [timeWindow, setTimeWindow] = useState(60); // minutes
  const [selectedTarget, setSelectedTarget] = useState(null);
  const [summary, setSummary] = useState(null);
  const [timeseries, setTimeseries] = useState([]);
  const [targetsHealth, setTargetsHealth] = useState([]);
  const [probes, setProbes] = useState([]);
  const [measurements, setMeasurements] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [lastRefreshed, setLastRefreshed] = useState(null);

  const fetchData = useCallback(async () => {
    try {
      const targetQuery = selectedTarget ? `&target=${encodeURIComponent(selectedTarget)}` : '';
      
      const [summaryRes, tsRes, targetsRes, probesRes, rawRes] = await Promise.all([
        fetch(`${API_BASE}/analytics/summary?minutes=${timeWindow}`),
        fetch(`${API_BASE}/analytics/timeseries?minutes=${timeWindow}${targetQuery}`),
        fetch(`${API_BASE}/analytics/targets-health?minutes=${timeWindow}`),
        fetch(`${API_BASE}/probes`),
        fetch(`${API_BASE}/measurements?limit=100${targetQuery}`)
      ]);

      if (!summaryRes.ok || !rawRes.ok) {
        throw new Error('API server returned error');
      }

      const summaryData = await summaryRes.json();
      const tsData = await tsRes.json();
      const targetsData = await targetsRes.json();
      const probesData = await probesRes.json();
      const rawData = await rawRes.json();

      setSummary(summaryData);
      setTimeseries(tsData);
      setTargetsHealth(targetsData);
      setProbes(probesData);
      setMeasurements(rawData);
      setError(null);
      setLastRefreshed(new Date().toLocaleTimeString());
    } catch (err) {
      console.error('Data refresh error:', err);
      setError('Unable to reach FastAPI backend on port 8000. Ensure the backend server is running.');
    } finally {
      setLoading(false);
    }
  }, [timeWindow, selectedTarget]);

  useEffect(() => {
    fetchData();
    if (!autoRefresh) return;
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, [fetchData, autoRefresh]);

  return (
    <div className="app-wrapper">
      {/* Top Header */}
      <header className="top-header">
        <div className="brand-section">
          <div className="brand-icon">🌐</div>
          <div className="brand-title">
            <h1>
              Internet Outage & Reliability Intelligence
              <span className="stage-badge">Stage 2 • Time-Series</span>
            </h1>
            <p>Distributed Telemetry, Multi-Protocol Probing & Historical Percentile Analytics</p>
          </div>
        </div>

        <div className="controls-bar">
          <select
            className="select-window"
            value={timeWindow}
            onChange={(e) => setTimeWindow(Number(e.target.value))}
          >
            <option value={15}>Window: Last 15 Mins</option>
            <option value={60}>Window: Last 1 Hour</option>
            <option value={360}>Window: Last 6 Hours</option>
            <option value={1440}>Window: Last 24 Hours</option>
          </select>

          <button
            className="refresh-button"
            onClick={() => setAutoRefresh(!autoRefresh)}
            title="Toggle real-time auto-refresh"
          >
            {autoRefresh ? (
              <span className="auto-refresh-pill">
                <span className="pulse-dot"></span>
                Live (5s)
              </span>
            ) : (
              <span style={{ color: 'var(--text-muted)' }}>⏸ Paused</span>
            )}
          </button>

          <button className="refresh-button" onClick={fetchData}>
            🔄 Refresh
          </button>
        </div>
      </header>

      {/* Error Notice */}
      {error && (
        <div className="error-banner">
          <span>⚠️</span>
          <div>
            <strong>Backend Connection Notice:</strong> {error}
          </div>
        </div>
      )}

      {/* Global Reliability Status Card */}
      <GlobalHealthCard summary={summary} loading={loading} />

      {/* KPI Cards Grid */}
      <section className="kpi-grid">
        <div className="kpi-card">
          <div className="kpi-label">Availability Uptime</div>
          <div
            className="kpi-value"
            style={{
              color: (summary?.uptime_pct ?? 100) >= 98.0 ? 'var(--status-green)' : 'var(--status-red)'
            }}
          >
            {loading ? '...' : `${summary?.uptime_pct ?? 100}%`}
          </div>
          <div className="kpi-subtext">Overall success rate across probes</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label">P50 Latency (Median)</div>
          <div className="kpi-value" style={{ color: 'var(--accent-blue)' }}>
            {loading ? '...' : `${summary?.p50_latency_ms ?? 0} ms`}
          </div>
          <div className="kpi-subtext">50th percentile response time</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label">P95 Tail Latency</div>
          <div className="kpi-value" style={{ color: 'var(--accent-purple)' }}>
            {loading ? '...' : `${summary?.p95_latency_ms ?? 0} ms`}
          </div>
          <div className="kpi-subtext">95th percentile response time</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label">P99 Latency (Outliers)</div>
          <div className="kpi-value" style={{ color: 'var(--accent-cyan)' }}>
            {loading ? '...' : `${summary?.p99_latency_ms ?? 0} ms`}
          </div>
          <div className="kpi-subtext">Worst 1% tail latency</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label">Avg Packet Loss</div>
          <div
            className="kpi-value"
            style={{
              color: (summary?.avg_packet_loss_pct ?? 0) > 2.0 ? 'var(--status-yellow)' : 'var(--text-secondary)'
            }}
          >
            {loading ? '...' : `${summary?.avg_packet_loss_pct ?? 0}%`}
          </div>
          <div className="kpi-subtext">ICMP round-trip packet drop</div>
        </div>
      </section>

      {/* Target Reliability Grid */}
      <section style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
          <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#f1f5f9' }}>
            Monitored Target Endpoints
          </h3>
          {selectedTarget && (
            <button
              className="refresh-button"
              style={{ fontSize: '0.75rem', padding: '4px 10px' }}
              onClick={() => setSelectedTarget(null)}
            >
              Clear Filter: {selectedTarget.replace('https://', '')} ✕
            </button>
          )}
        </div>
        <TargetHealthGrid
          targetsHealth={targetsHealth}
          onSelectTarget={setSelectedTarget}
          selectedTarget={selectedTarget}
        />
      </section>

      {/* Visualizations Grid */}
      <div className="charts-2col">
        {/* Chart 1: Latency Percentiles & Trends */}
        <div className="dashboard-card">
          <div className="card-header">
            <div className="card-title">
              <h3>📈 Latency Trends & Tail Percentiles</h3>
              <p>P95 tail latency vs Average HTTP response time</p>
            </div>
            {selectedTarget && (
              <span className="badge-success">Filter: {selectedTarget.replace('https://', '')}</span>
            )}
          </div>
          <LatencyPercentilesChart timeseriesData={timeseries} />
        </div>

        {/* Chart 2: Protocol Latency Decomposition */}
        <div className="dashboard-card">
          <div className="card-header">
            <div className="card-title">
              <h3>🔍 Protocol Decomposition</h3>
              <p>DNS Resolution vs TCP Handshake vs HTTP vs Packet Loss</p>
            </div>
          </div>
          <ProtocolBreakdownChart timeseriesData={timeseries} />
        </div>
      </div>

      {/* Probes & Telemetry Logs */}
      <div className="section-grid-2col">
        {/* Recent Telemetry Stream */}
        <div className="dashboard-card">
          <div className="card-header">
            <div className="card-title">
              <h3>📡 Real-Time Telemetry Stream</h3>
              <p>Latest {measurements.length} probe checks with multi-protocol metrics</p>
            </div>
          </div>
          <TelemetryTable measurements={measurements} />
        </div>

        {/* Registered Probes Panel */}
        <div className="dashboard-card">
          <div className="card-header">
            <div className="card-title">
              <h3>🛰️ Active Telemetry Probes</h3>
              <p>Distributed probe nodes and heartbeat health</p>
            </div>
          </div>
          <ProbesList probes={probes} />
        </div>
      </div>
    </div>
  );
}
