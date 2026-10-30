-- ============================================================================
-- Internet Outage & Reliability Intelligence Platform — Stage 2
-- TimescaleDB Hypertable Setup & Continuous Aggregates
-- ============================================================================

-- 1. Enable TimescaleDB Extension
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- 2. Create Application Tables (Relational Metadata)
CREATE TABLE IF NOT EXISTS probes (
    probe_id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    location VARCHAR(128) NOT NULL,
    status VARCHAR(32) DEFAULT 'active',
    last_heartbeat TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS targets (
    id SERIAL PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    url TEXT UNIQUE NOT NULL,
    category VARCHAR(64) DEFAULT 'Web Service',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Create Time-Series Measurements Table
CREATE TABLE IF NOT EXISTS measurements (
    id BIGSERIAL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    probe_id VARCHAR(64) NOT NULL,
    target TEXT NOT NULL,
    http_latency_ms DOUBLE PRECISION,
    dns_latency_ms DOUBLE PRECISION,
    tcp_latency_ms DOUBLE PRECISION,
    ping_latency_ms DOUBLE PRECISION,
    packet_loss_pct DOUBLE PRECISION DEFAULT 0.0,
    status_code INT,
    success BOOLEAN NOT NULL,
    error_message TEXT
);

-- 4. Convert measurements into a TimescaleDB Hypertable partitioned by time (chunk_time_interval = 1 day)
SELECT create_hypertable(
    'measurements',
    'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE,
    migrate_data => TRUE
);

-- 5. Create Time-Series Compound Indexes
CREATE INDEX IF NOT EXISTS idx_measurements_ts_target ON measurements (target, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_measurements_probe_ts ON measurements (probe_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_measurements_success_ts ON measurements (success, timestamp DESC);

-- 6. TimescaleDB Continuous Aggregate: 1-Minute Downsampling Rollup
CREATE MATERIALIZED VIEW IF NOT EXISTS measurements_1m_rollup
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 minute', timestamp) AS bucket,
    target,
    probe_id,
    COUNT(*) as total_samples,
    SUM(CASE WHEN success = TRUE THEN 1 ELSE 0 END) as successful_samples,
    AVG(http_latency_ms) as avg_http_latency,
    AVG(dns_latency_ms) as avg_dns_latency,
    AVG(tcp_latency_ms) as avg_tcp_latency,
    AVG(packet_loss_pct) as avg_packet_loss,
    percentile_cont(0.50) WITHIN GROUP (ORDER BY http_latency_ms) as p50_latency,
    percentile_cont(0.95) WITHIN GROUP (ORDER BY http_latency_ms) as p95_latency,
    percentile_cont(0.99) WITHIN GROUP (ORDER BY http_latency_ms) as p99_latency
FROM measurements
GROUP BY bucket, target, probe_id
WITH NO DATA;

-- 7. Add Continuous Aggregate Refresh Policy (Refreshes every minute for the last 2 hours)
SELECT add_continuous_aggregate_policy('measurements_1m_rollup',
    start_offset => INTERVAL '2 hours',
    end_offset => INTERVAL '1 minute',
    schedule_interval => INTERVAL '1 minute',
    if_not_exists => TRUE
);

-- 8. Data Retention Policy (Automatically purge raw telemetry older than 30 days)
SELECT add_retention_policy('measurements', INTERVAL '30 days', if_not_exists => TRUE);
