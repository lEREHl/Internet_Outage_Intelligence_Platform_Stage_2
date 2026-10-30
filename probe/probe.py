import os
import platform
import re
import socket
import subprocess
import time
from datetime import datetime, timezone
from urllib.parse import urlparse
import requests
from dotenv import load_dotenv

# Load configuration from probe/.env
load_dotenv()

PROBE_ID = os.getenv("PROBE_ID", "blr-probe-01")
PROBE_NAME = os.getenv("PROBE_NAME", "Bangalore Primary Probe")
PROBE_LOCATION = os.getenv("PROBE_LOCATION", "Bangalore, IN")
BACKEND_BASE_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
CHECK_INTERVAL_SECONDS = int(os.getenv("CHECK_INTERVAL_SECONDS", "10"))
TARGET_URLS_RAW = os.getenv(
    "TARGET_URLS",
    "https://www.google.com,https://github.com,https://1.1.1.1,https://aws.amazon.com,https://www.youtube.com"
)
TARGET_URLS = [url.strip() for url in TARGET_URLS_RAW.split(",") if url.strip()]

def register_probe():
    """Registers this probe agent with the backend API on startup."""
    url = f"{BACKEND_BASE_URL}/api/probe/register"
    payload = {
        "probe_id": PROBE_ID,
        "name": PROBE_NAME,
        "location": PROBE_LOCATION
    }
    try:
        res = requests.post(url, json=payload, timeout=4.0)
        if res.status_code in (200, 201):
            print(f"[REGISTER] Successfully registered probe '{PROBE_ID}' ({PROBE_LOCATION}).")
            return True
        else:
            print(f"[REGISTER-WARN] Backend responded with status {res.status_code}: {res.text}")
    except Exception as e:
        print(f"[REGISTER-WARN] Could not register probe on boot: {e}")
    return False

def measure_dns(hostname: str):
    """Measures DNS lookup time in milliseconds."""
    start = time.perf_counter()
    try:
        socket.getaddrinfo(hostname, None)
        duration_ms = (time.perf_counter() - start) * 1000
        return round(duration_ms, 2), None
    except Exception as e:
        duration_ms = (time.perf_counter() - start) * 1000
        return round(duration_ms, 2), f"DNS lookup failed: {e}"

def measure_tcp(hostname: str, port: int = 443):
    """Measures TCP handshake latency in milliseconds."""
    start = time.perf_counter()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(3.0)
    try:
        sock.connect((hostname, port))
        duration_ms = (time.perf_counter() - start) * 1000
        sock.close()
        return round(duration_ms, 2), None
    except Exception as e:
        duration_ms = (time.perf_counter() - start) * 1000
        try:
            sock.close()
        except Exception:
            pass
        return None, f"TCP connect failed: {e}"

def measure_ping(hostname: str):
    """
    Executes ICMP ping to measure round-trip ping latency and packet loss %.
    Compatible with Windows and Unix-like operating systems.
    """
    is_windows = platform.system().lower() == "windows"
    cmd = (
        ["ping", "-n", "3", "-w", "1000", hostname]
        if is_windows
        else ["ping", "-c", "3", "-W", "1", hostname]
    )
    
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5.0
        )
        out = result.stdout
        
        # Parse packet loss percentage
        packet_loss = 0.0
        loss_match = re.search(r"(\d+(?:\.\d+)?)%\s*(?:packet\s*)?loss", out, re.IGNORECASE)
        if loss_match:
            packet_loss = float(loss_match.group(1))
        elif result.returncode != 0:
            packet_loss = 100.0

        # Parse average ping latency
        avg_ping = None
        if is_windows:
            avg_match = re.search(r"Average\s*=\s*(\d+)ms", out, re.IGNORECASE)
            if avg_match:
                avg_ping = float(avg_match.group(1))
        else:
            avg_match = re.search(r"min/avg/max.*?=\s*[\d\.]+/([\d\.]+)/", out, re.IGNORECASE)
            if avg_match:
                avg_ping = float(avg_match.group(1))

        return avg_ping, packet_loss, None
    except subprocess.TimeoutExpired:
        return None, 100.0, "ICMP ping timed out"
    except Exception as e:
        return None, 0.0, f"Ping error: {e}"

def check_target_comprehensive(target_url: str) -> dict:
    """
    Performs multi-protocol telemetry check against a target URL:
    - DNS resolution latency
    - TCP handshake latency
    - ICMP ping and packet loss
    - HTTP response latency and status code
    """
    parsed = urlparse(target_url)
    hostname = parsed.hostname or target_url
    port = parsed.port or (443 if parsed.scheme == "https" else 80)

    # 1. DNS Measurement
    dns_ms, dns_err = measure_dns(hostname)

    # 2. TCP Handshake Measurement
    tcp_ms, tcp_err = measure_tcp(hostname, port)

    # 3. ICMP Ping & Packet Loss Measurement
    ping_ms, packet_loss, ping_err = measure_ping(hostname)

    # 4. HTTP / HTTPS Request Measurement
    start_http = time.perf_counter()
    status_code = None
    http_ms = None
    http_success = False
    http_err = None

    try:
        resp = requests.get(target_url, timeout=5.0, headers={"User-Agent": "OutageIntelProbe/2.0"})
        http_ms = round((time.perf_counter() - start_http) * 1000, 2)
        status_code = resp.status_code
        http_success = (200 <= status_code < 400)
    except requests.RequestException as e:
        http_ms = round((time.perf_counter() - start_http) * 1000, 2)
        http_success = False
        http_err = str(e)

    # Overall error message compilation
    error_parts = [e for e in (dns_err, tcp_err, ping_err, http_err) if e]
    overall_error = "; ".join(error_parts) if error_parts else None

    return {
        "probe_id": PROBE_ID,
        "target": target_url,
        "http_latency_ms": http_ms,
        "dns_latency_ms": dns_ms,
        "tcp_latency_ms": tcp_ms,
        "ping_latency_ms": ping_ms,
        "packet_loss_pct": packet_loss,
        "status_code": status_code,
        "success": http_success,
        "error_message": overall_error,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

def send_telemetry(payload: dict):
    """Sends telemetry payload to FastAPI ingestion endpoint."""
    url = f"{BACKEND_BASE_URL}/api/measurements"
    try:
        res = requests.post(url, json=payload, timeout=3.5)
        return res.status_code in (200, 201)
    except Exception as e:
        print(f"[INGEST-FAIL] Could not send to backend: {e}")
        return False

def run_probe_cycle():
    """Runs one telemetry measurement round across all targets."""
    cycle_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n[{cycle_time}] 🛰️  PROBE CYCLE — {PROBE_ID} ({PROBE_LOCATION})")
    print("━" * 70)

    for target in TARGET_URLS:
        telemetry = check_target_comprehensive(target)
        sent = send_telemetry(telemetry)

        # Pretty terminal output
        res_symbol = "🟢" if telemetry["success"] else "🔴"
        status_str = f"HTTP {telemetry['status_code']}" if telemetry['status_code'] else "ERR"
        dns_str = f"DNS:{telemetry['dns_latency_ms']}ms" if telemetry['dns_latency_ms'] is not None else "DNS:N/A"
        tcp_str = f"TCP:{telemetry['tcp_latency_ms']}ms" if telemetry['tcp_latency_ms'] is not None else "TCP:N/A"
        http_str = f"HTTP:{telemetry['http_latency_ms']}ms" if telemetry['http_latency_ms'] is not None else "HTTP:N/A"
        loss_str = f"Loss:{telemetry['packet_loss_pct']}%"
        sent_str = "DB:✓" if sent else "DB:✗"

        print(f"{res_symbol} {target:<28} | {status_str:<9} | {http_str:<12} | {dns_str:<11} | {tcp_str:<11} | {loss_str:<9} | {sent_str}")

def main():
    print("==================================================================")
    print("  Internet Outage & Reliability Intelligence Platform — Probe V2  ")
    print(f"  Probe ID   : {PROBE_ID} ({PROBE_NAME})")
    print(f"  Location   : {PROBE_LOCATION}")
    print(f"  Backend API: {BACKEND_BASE_URL}")
    print(f"  Interval   : {CHECK_INTERVAL_SECONDS}s")
    print(f"  Targets    : {len(TARGET_URLS)} endpoints configured")
    print("==================================================================")

    # Register probe on startup
    register_probe()

    while True:
        try:
            run_probe_cycle()
            time.sleep(CHECK_INTERVAL_SECONDS)
        except KeyboardInterrupt:
            print("\n[INFO] Probe execution terminated by user.")
            break
        except Exception as e:
            print(f"\n[ERROR] Unexpected error in probe loop: {e}")
            time.sleep(CHECK_INTERVAL_SECONDS)

if __name__ == "__main__":
    main()
