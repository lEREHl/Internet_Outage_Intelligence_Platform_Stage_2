import math
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from database import get_db_connection, init_db
from schemas import (
    ProbeRegister,
    ProbeResponse,
    TargetCreate,
    TargetResponse,
    MeasurementCreate,
    MeasurementResponse,
    PercentilesResponse,
    SummaryMetricsResponse,
    TimeseriesPoint,
    TargetHealthSummary,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables and hypertable configuration on startup
    init_db()
    yield

app = FastAPI(
    title="Internet Outage & Reliability Intelligence API",
    description="Stage 2 — Real-time Time-Series Telemetry & Analytics Platform",
    version="2.0.0",
    lifespan=lifespan
)

# Enable Cross-Origin Resource Sharing for the React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 1. Health & Status
# ==========================================
@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "stage": "Stage 2 — Time-Series System",
        "service": "Internet Outage Intelligence Platform",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

# ==========================================
# 2. Probe Management Endpoints
# ==========================================
@app.get("/api/probes", response_model=List[ProbeResponse])
def get_probes():
    """Returns all registered telemetry probe agents."""
    query = """
        SELECT probe_id, name, location, status, last_heartbeat, created_at
        FROM probes
        ORDER BY probe_id ASC;
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                return [dict(row) for row in cur.fetchall()]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database fetch error: {str(e)}")

@app.post("/api/probe/register", response_model=ProbeResponse, status_code=status.HTTP_201_CREATED)
@app.post("/api/probes", response_model=ProbeResponse, status_code=status.HTTP_201_CREATED)
def register_probe(payload: ProbeRegister):
    """
    Registers or updates a probe agent's heartbeat, status, and metadata.
    """
    query = """
        INSERT INTO probes (probe_id, name, location, status, last_heartbeat)
        VALUES (%s, %s, %s, 'active', CURRENT_TIMESTAMP)
        ON CONFLICT (probe_id) DO UPDATE SET
            name = EXCLUDED.name,
            location = EXCLUDED.location,
            status = 'active',
            last_heartbeat = CURRENT_TIMESTAMP
        RETURNING probe_id, name, location, status, last_heartbeat, created_at;
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (payload.probe_id, payload.name, payload.location))
                row = cur.fetchone()
                return dict(row)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Probe registration error: {str(e)}")

# ==========================================
# 3. Target Endpoints
# ==========================================
@app.get("/api/targets", response_model=List[TargetResponse])
def get_targets():
    """Returns list of monitored internet endpoints."""
    query = """
        SELECT id, name, url, category, is_active, created_at
        FROM targets
        ORDER BY id ASC;
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                return [dict(row) for row in cur.fetchall()]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch targets: {str(e)}")

@app.post("/api/targets", response_model=TargetResponse, status_code=status.HTTP_201_CREATED)
def create_target(payload: TargetCreate):
    """Registers a new target endpoint to monitor."""
    query = """
        INSERT INTO targets (name, url, category, is_active)
        VALUES (%s, %s, %s, TRUE)
        ON CONFLICT (url) DO UPDATE SET
            name = EXCLUDED.name,
            category = EXCLUDED.category,
            is_active = TRUE
        RETURNING id, name, url, category, is_active, created_at;
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (payload.name, payload.url, payload.category))
                row = cur.fetchone()
                return dict(row)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create target: {str(e)}")

# ==========================================
# 4. Ingestion & Raw Measurements
# ==========================================
@app.post("/api/measurements", response_model=MeasurementResponse, status_code=status.HTTP_201_CREATED)
def record_measurement(payload: MeasurementCreate):
    """
    Ingests rich probe telemetry into PostgreSQL / TimescaleDB hypertable.
    Tracks DNS latency, TCP latency, HTTP latency, ping latency, and packet loss.
    """
    insert_query = """
        INSERT INTO measurements (
            probe_id, target, http_latency_ms, dns_latency_ms, tcp_latency_ms,
            ping_latency_ms, packet_loss_pct, status_code, success, error_message, timestamp
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, COALESCE(%s, CURRENT_TIMESTAMP))
        RETURNING id, timestamp, probe_id, target, http_latency_ms, dns_latency_ms,
                  tcp_latency_ms, ping_latency_ms, packet_loss_pct, status_code, success, error_message;
    """
    heartbeat_query = """
        INSERT INTO probes (probe_id, name, location, status, last_heartbeat)
        VALUES (%s, 'Telemetry Probe', 'Auto-registered', 'active', CURRENT_TIMESTAMP)
        ON CONFLICT (probe_id) DO UPDATE SET
            status = 'active',
            last_heartbeat = CURRENT_TIMESTAMP;
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Update probe heartbeat
                cur.execute(heartbeat_query, (payload.probe_id,))
                
                # Insert measurement record
                cur.execute(
                    insert_query,
                    (
                        payload.probe_id,
                        payload.target,
                        payload.http_latency_ms,
                        payload.dns_latency_ms,
                        payload.tcp_latency_ms,
                        payload.ping_latency_ms,
                        payload.packet_loss_pct,
                        payload.status_code,
                        payload.success,
                        payload.error_message,
                        payload.timestamp,
                    )
                )
                row = cur.fetchone()
                return dict(row)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Measurement ingestion error: {str(e)}")

@app.get("/api/measurements", response_model=List[MeasurementResponse])
def get_measurements(
    limit: int = Query(100, ge=1, le=1000, description="Max records to return"),
    target: Optional[str] = Query(None, description="Filter by target URL"),
    probe_id: Optional[str] = Query(None, description="Filter by probe ID"),
    minutes: Optional[int] = Query(None, ge=1, description="Limit to last X minutes")
):
    """Retrieves recent raw probe telemetry with optional target, probe, or time filters."""
    if not isinstance(limit, int):
        limit = 100
    if not isinstance(target, str):
        target = None
    if not isinstance(probe_id, str):
        probe_id = None
    if not isinstance(minutes, int):
        minutes = None

    conditions = []
    params = []

    if target:
        conditions.append("target = %s")
        params.append(target)
    if probe_id:
        conditions.append("probe_id = %s")
        params.append(probe_id)
    if minutes:
        conditions.append("timestamp >= NOW() - (%s || ' minutes')::INTERVAL")
        params.append(str(minutes))

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    query = f"""
        SELECT id, timestamp, probe_id, target, http_latency_ms, dns_latency_ms,
               tcp_latency_ms, ping_latency_ms, packet_loss_pct, status_code, success, error_message
        FROM measurements
        {where_clause}
        ORDER BY timestamp DESC
        LIMIT %s;
    """
    params.append(limit)

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, tuple(params))
                return [dict(row) for row in cur.fetchall()]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query error: {str(e)}")

# ==========================================
# 5. Time-Series Analytics & Percentiles
# ==========================================
@app.get("/api/analytics/summary", response_model=SummaryMetricsResponse)
def get_summary_metrics(
    minutes: int = Query(60, ge=1, le=43200, description="Time window in minutes (default 60)")
):
    """
    Computes real-time aggregate reliability KPIs:
    Uptime %, latency percentiles (P50, P95, P99), protocol breakdown averages, and packet loss.
    """
    if not isinstance(minutes, int):
        minutes = 60

    query = """
        SELECT
            COUNT(*) as total_checks,
            COALESCE(SUM(CASE WHEN success = TRUE THEN 1 ELSE 0 END), 0) as success_checks,
            COALESCE(AVG(CASE WHEN success = TRUE THEN http_latency_ms END), 0) as avg_http,
            COALESCE(AVG(dns_latency_ms), 0) as avg_dns,
            COALESCE(AVG(tcp_latency_ms), 0) as avg_tcp,
            COALESCE(AVG(packet_loss_pct), 0) as avg_loss,
            COALESCE(percentile_cont(0.50) WITHIN GROUP (ORDER BY http_latency_ms) FILTER (WHERE success = TRUE), 0) as p50,
            COALESCE(percentile_cont(0.95) WITHIN GROUP (ORDER BY http_latency_ms) FILTER (WHERE success = TRUE), 0) as p95,
            COALESCE(percentile_cont(0.99) WITHIN GROUP (ORDER BY http_latency_ms) FILTER (WHERE success = TRUE), 0) as p99,
            COUNT(DISTINCT probe_id) as active_probes,
            COUNT(DISTINCT target) as active_targets
        FROM measurements
        WHERE timestamp >= NOW() - (%s || ' minutes')::INTERVAL;
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (str(minutes),))
                row = cur.fetchone()

                total = row["total_checks"] or 0
                success = row["success_checks"] or 0
                uptime_pct = round((success / total) * 100, 2) if total > 0 else 100.0

                return {
                    "total_checks": total,
                    "uptime_pct": uptime_pct,
                    "avg_http_latency_ms": round(float(row["avg_http"] or 0), 2),
                    "avg_dns_latency_ms": round(float(row["avg_dns"] or 0), 2),
                    "avg_tcp_latency_ms": round(float(row["avg_tcp"] or 0), 2),
                    "avg_packet_loss_pct": round(float(row["avg_loss"] or 0), 2),
                    "p50_latency_ms": round(float(row["p50"] or 0), 2),
                    "p95_latency_ms": round(float(row["p95"] or 0), 2),
                    "p99_latency_ms": round(float(row["p99"] or 0), 2),
                    "active_probes_count": row["active_probes"] or 0,
                    "active_targets_count": row["active_targets"] or 0,
                    "time_window_minutes": minutes
                }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summary analytics error: {str(e)}")

@app.get("/api/analytics/percentiles", response_model=PercentilesResponse)
def get_latency_percentiles(
    target: Optional[str] = Query(None, description="Optional target filter"),
    minutes: int = Query(60, ge=1, le=43200, description="Time window in minutes")
):
    """
    Calculates exact latency percentiles (P50, P90, P95, P99) for a target or global traffic.
    """
    if not isinstance(target, str):
        target = None
    if not isinstance(minutes, int):
        minutes = 60

    conditions = ["timestamp >= NOW() - (%s || ' minutes')::INTERVAL", "success = TRUE", "http_latency_ms IS NOT NULL"]
    params = [str(minutes)]

    if target:
        conditions.append("target = %s")
        params.append(target)

    query = f"""
        SELECT
            COUNT(*) as sample_count,
            AVG(http_latency_ms) as avg_lat,
            percentile_cont(0.50) WITHIN GROUP (ORDER BY http_latency_ms) as p50,
            percentile_cont(0.90) WITHIN GROUP (ORDER BY http_latency_ms) as p90,
            percentile_cont(0.95) WITHIN GROUP (ORDER BY http_latency_ms) as p95,
            percentile_cont(0.99) WITHIN GROUP (ORDER BY http_latency_ms) as p99
        FROM measurements
        WHERE {' AND '.join(conditions)};
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, tuple(params))
                row = cur.fetchone()
                count = row["sample_count"] or 0
                return {
                    "target": target,
                    "sample_count": count,
                    "avg_latency_ms": round(float(row["avg_lat"]), 2) if row["avg_lat"] is not None else None,
                    "p50_latency_ms": round(float(row["p50"]), 2) if row["p50"] is not None else None,
                    "p90_latency_ms": round(float(row["p90"]), 2) if row["p90"] is not None else None,
                    "p95_latency_ms": round(float(row["p95"]), 2) if row["p95"] is not None else None,
                    "p99_latency_ms": round(float(row["p99"]), 2) if row["p99"] is not None else None,
                }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Percentiles error: {str(e)}")

@app.get("/api/analytics/timeseries", response_model=List[TimeseriesPoint])
def get_timeseries_analytics(
    target: Optional[str] = Query(None, description="Optional target filter"),
    minutes: int = Query(60, ge=1, le=43200, description="Time window in minutes"),
    bucket_seconds: Optional[int] = Query(None, ge=5, description="Bucket interval in seconds")
):
    """
    Produces downsampled time-series buckets for time-series charts.
    Auto-scales the bucket interval (e.g. 10s for 15m, 60s for 1h, 300s for 6h).
    """
    if not isinstance(target, str):
        target = None
    if not isinstance(minutes, int):
        minutes = 60

    # Auto-determine bucket interval if not provided or passed as Query sentinel
    if not isinstance(bucket_seconds, int):
        if minutes <= 15:
            bucket_seconds = 10
        elif minutes <= 60:
            bucket_seconds = 30
        elif minutes <= 360:
            bucket_seconds = 120
        elif minutes <= 1440:
            bucket_seconds = 300
        else:
            bucket_seconds = 900

    conditions = ["timestamp >= NOW() - (%s || ' minutes')::INTERVAL"]
    params = [str(minutes), bucket_seconds]

    target_filter_clause = ""
    if target:
        target_filter_clause = "AND target = %s"
        params.append(target)

    # Universally supported epoch bucket calculation across standard Postgres and TimescaleDB
    query = f"""
        SELECT
            to_timestamp(floor(extract(epoch from timestamp) / %s) * %s) AT TIME ZONE 'UTC' as bucket_time,
            COUNT(*) as sample_count,
            COALESCE(AVG(CASE WHEN success = TRUE THEN http_latency_ms END), 0) as avg_http,
            COALESCE(percentile_cont(0.95) WITHIN GROUP (ORDER BY http_latency_ms) FILTER (WHERE success = TRUE), 0) as p95_lat,
            COALESCE(AVG(dns_latency_ms), 0) as avg_dns,
            COALESCE(AVG(tcp_latency_ms), 0) as avg_tcp,
            COALESCE(AVG(packet_loss_pct), 0) as avg_loss,
            ROUND((SUM(CASE WHEN success = TRUE THEN 1 ELSE 0 END)::NUMERIC / COUNT(*)) * 100, 2) as uptime_pct
        FROM measurements
        WHERE {conditions[0]} {target_filter_clause}
        GROUP BY bucket_time
        ORDER BY bucket_time ASC;
    """

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # The parameters order: minutes, bucket_seconds, bucket_seconds, (target)
                param_list = [str(minutes), bucket_seconds, bucket_seconds]
                if target:
                    param_list.append(target)

                cur.execute(query, tuple(param_list))
                rows = cur.fetchall()

                result = []
                for r in rows:
                    bt = r["bucket_time"]
                    bt_str = bt.strftime("%H:%M:%S") if hasattr(bt, "strftime") else str(bt)
                    result.append({
                        "timestamp": bt_str,
                        "target": target,
                        "avg_http_latency_ms": round(float(r["avg_http"] or 0), 2),
                        "p95_latency_ms": round(float(r["p95_lat"] or 0), 2),
                        "avg_dns_latency_ms": round(float(r["avg_dns"] or 0), 2),
                        "avg_tcp_latency_ms": round(float(r["avg_tcp"] or 0), 2),
                        "avg_packet_loss_pct": round(float(r["avg_loss"] or 0), 2),
                        "uptime_pct": float(r["uptime_pct"] or 100.0),
                        "sample_count": r["sample_count"]
                    })
                return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Timeseries query error: {str(e)}")

@app.get("/api/analytics/targets-health", response_model=List[TargetHealthSummary])
def get_targets_health(
    minutes: int = Query(60, ge=1, le=43200, description="Time window in minutes")
):
    """
    Computes breakdown health and reliability status for each monitored target.
    """
    if not isinstance(minutes, int):
        minutes = 60

    query = """
        SELECT
            m.target,
            COUNT(*) as total_checks,
            ROUND((SUM(CASE WHEN m.success = TRUE THEN 1 ELSE 0 END)::NUMERIC / COUNT(*)) * 100, 2) as uptime_pct,
            COALESCE(AVG(CASE WHEN m.success = TRUE THEN m.http_latency_ms END), 0) as avg_http,
            COALESCE(percentile_cont(0.95) WITHIN GROUP (ORDER BY m.http_latency_ms) FILTER (WHERE m.success = TRUE), 0) as p95_lat,
            COALESCE(AVG(m.packet_loss_pct), 0) as avg_loss,
            (
                SELECT status_code
                FROM measurements sub
                WHERE sub.target = m.target
                ORDER BY sub.timestamp DESC
                LIMIT 1
            ) as latest_code,
            MAX(m.timestamp) as latest_time
        FROM measurements m
        WHERE m.timestamp >= NOW() - (%s || ' minutes')::INTERVAL
        GROUP BY m.target
        ORDER BY uptime_pct DESC, avg_http ASC;
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (str(minutes),))
                rows = cur.fetchall()

                result = []
                for r in rows:
                    result.append({
                        "target": r["target"],
                        "total_checks": r["total_checks"],
                        "uptime_pct": float(r["uptime_pct"] or 0.0),
                        "avg_http_latency_ms": round(float(r["avg_http"] or 0), 2),
                        "p95_latency_ms": round(float(r["p95_lat"] or 0), 2),
                        "avg_packet_loss_pct": round(float(r["avg_loss"] or 0), 2),
                        "latest_status_code": r["latest_code"],
                        "latest_check_time": r["latest_time"]
                    })
                return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Target health calculation error: {str(e)}")
