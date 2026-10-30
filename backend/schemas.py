from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

# --- Probe Schemas ---
class ProbeRegister(BaseModel):
    probe_id: str = Field(..., example="blr-probe-01")
    name: Optional[str] = Field("Telemetry Probe", example="Bangalore Primary Probe")
    location: Optional[str] = Field("Unknown Location", example="Bangalore, IN")

class ProbeResponse(BaseModel):
    probe_id: str
    name: str
    location: str
    status: str
    last_heartbeat: datetime
    created_at: datetime

# --- Target Schemas ---
class TargetCreate(BaseModel):
    name: str = Field(..., example="GitHub")
    url: str = Field(..., example="https://github.com")
    category: Optional[str] = Field("Web Service", example="Developer Platform")

class TargetResponse(BaseModel):
    id: int
    name: str
    url: str
    category: str
    is_active: bool
    created_at: datetime

# --- Measurement Schemas ---
class MeasurementCreate(BaseModel):
    probe_id: str = Field(..., example="blr-probe-01")
    target: str = Field(..., example="https://github.com")
    http_latency_ms: Optional[float] = Field(None, example=45.2)
    dns_latency_ms: Optional[float] = Field(None, example=12.5)
    tcp_latency_ms: Optional[float] = Field(None, example=24.1)
    ping_latency_ms: Optional[float] = Field(None, example=35.0)
    packet_loss_pct: Optional[float] = Field(0.0, example=0.0)
    status_code: Optional[int] = Field(None, example=200)
    success: bool = Field(..., example=True)
    error_message: Optional[str] = Field(None, example=None)
    timestamp: Optional[datetime] = None

class MeasurementResponse(BaseModel):
    id: int
    timestamp: datetime
    probe_id: str
    target: str
    http_latency_ms: Optional[float]
    dns_latency_ms: Optional[float]
    tcp_latency_ms: Optional[float]
    ping_latency_ms: Optional[float]
    packet_loss_pct: Optional[float]
    status_code: Optional[int]
    success: bool
    error_message: Optional[str]

# --- Analytics Schemas ---
class PercentilesResponse(BaseModel):
    target: Optional[str]
    sample_count: int
    avg_latency_ms: Optional[float]
    p50_latency_ms: Optional[float]
    p90_latency_ms: Optional[float]
    p95_latency_ms: Optional[float]
    p99_latency_ms: Optional[float]

class SummaryMetricsResponse(BaseModel):
    total_checks: int
    uptime_pct: float
    avg_http_latency_ms: float
    avg_dns_latency_ms: float
    avg_tcp_latency_ms: float
    avg_packet_loss_pct: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    active_probes_count: int
    active_targets_count: int
    time_window_minutes: int

class TimeseriesPoint(BaseModel):
    timestamp: str
    target: Optional[str] = None
    avg_http_latency_ms: Optional[float] = None
    avg_dns_latency_ms: Optional[float] = None
    avg_tcp_latency_ms: Optional[float] = None
    avg_packet_loss_pct: Optional[float] = None
    p95_latency_ms: Optional[float] = None
    uptime_pct: Optional[float] = None
    sample_count: int

class TargetHealthSummary(BaseModel):
    target: str
    uptime_pct: float
    avg_http_latency_ms: Optional[float]
    p95_latency_ms: Optional[float]
    avg_packet_loss_pct: Optional[float]
    latest_status_code: Optional[int]
    latest_check_time: Optional[datetime]
    total_checks: int
