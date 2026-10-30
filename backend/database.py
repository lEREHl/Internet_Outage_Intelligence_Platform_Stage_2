import os
import logging
from contextlib import contextmanager
from dotenv import load_dotenv
import psycopg
from psycopg.rows import dict_row

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("database")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:password@localhost:5432/outage_db"
)

@contextmanager
def get_db_connection():
    """
    Context manager providing a psycopg 3 connection configured with dict_row.
    Automatically commits on success or rolls back on exception.
    """
    conn = psycopg.connect(DATABASE_URL, row_factory=dict_row)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    """
    Initializes PostgreSQL / TimescaleDB schema for Stage 2:
    - probes table (Application metadata)
    - targets table (Monitored URLs)
    - measurements table (Time-series metrics with hypertable support)
    - Seeds default monitored targets and reference probes
    """
    try:
        with get_db_connection() as conn:
            # Enable autocommit for DDL statements so any failed optional extension creation doesn't abort subsequent DDLs
            conn.autocommit = True
            with conn.cursor() as cur:
                # 1. Probes Table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS probes (
                        probe_id VARCHAR(64) PRIMARY KEY,
                        name VARCHAR(128) NOT NULL,
                        location VARCHAR(128) NOT NULL,
                        status VARCHAR(32) DEFAULT 'active',
                        last_heartbeat TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    );
                """)

                # 2. Targets Table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS targets (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(128) NOT NULL,
                        url TEXT UNIQUE NOT NULL,
                        category VARCHAR(64) DEFAULT 'Web Service',
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    );
                """)

                # 3. Time-Series Measurements Table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS measurements (
                        id BIGSERIAL,
                        timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        probe_id VARCHAR(64) NOT NULL DEFAULT 'blr-probe-01',
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
                """)

                # Evolve schema if table was created during Stage 1
                cur.execute("""
                    ALTER TABLE measurements ADD COLUMN IF NOT EXISTS probe_id VARCHAR(64) DEFAULT 'blr-probe-01';
                    ALTER TABLE measurements ADD COLUMN IF NOT EXISTS http_latency_ms DOUBLE PRECISION;
                    ALTER TABLE measurements ADD COLUMN IF NOT EXISTS dns_latency_ms DOUBLE PRECISION;
                    ALTER TABLE measurements ADD COLUMN IF NOT EXISTS tcp_latency_ms DOUBLE PRECISION;
                    ALTER TABLE measurements ADD COLUMN IF NOT EXISTS ping_latency_ms DOUBLE PRECISION;
                    ALTER TABLE measurements ADD COLUMN IF NOT EXISTS packet_loss_pct DOUBLE PRECISION DEFAULT 0.0;
                """)

                # Backfill http_latency_ms from legacy response_time_ms column if present
                try:
                    cur.execute("""
                        DO $$
                        BEGIN
                            IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'measurements' AND column_name = 'response_time_ms') THEN
                                UPDATE measurements SET http_latency_ms = response_time_ms WHERE http_latency_ms IS NULL;
                            END IF;
                        END $$;
                    """)
                except Exception as b_err:
                    logger.debug(f"Legacy backfill note: {b_err}")

                # 4. Attempt TimescaleDB hypertable conversion (gracefully skips if TimescaleDB extension is absent)
                try:
                    cur.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")
                    cur.execute("SELECT create_hypertable('measurements', 'timestamp', if_not_exists => TRUE, migrate_data => TRUE);")
                    logger.info("TimescaleDB hypertable configured successfully on 'measurements'.")
                except Exception as ext_err:
                    logger.info(f"TimescaleDB hypertable setup note: {ext_err}. Using PostgreSQL optimized time-series indexes.")

                # 5. Composite time-series indexes for ultra-fast range queries and percentile aggregations
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_measurements_ts_target ON measurements (timestamp DESC, target);
                    CREATE INDEX IF NOT EXISTS idx_measurements_probe_ts ON measurements (probe_id, timestamp DESC);
                    CREATE INDEX IF NOT EXISTS idx_measurements_success_ts ON measurements (success, timestamp DESC);
                """)

                # 6. Seed default monitored targets if table is empty
                cur.execute("SELECT COUNT(*) as count FROM targets;")
                row = cur.fetchone()
                if row["count"] == 0:
                    default_targets = [
                        ("Google", "https://www.google.com", "Search & Cloud"),
                        ("GitHub", "https://github.com", "Developer Platform"),
                        ("Cloudflare 1.1.1.1", "https://1.1.1.1", "Anycast DNS & Edge"),
                        ("AWS", "https://aws.amazon.com", "Cloud Infrastructure"),
                        ("YouTube", "https://www.youtube.com", "Streaming & Media")
                    ]
                    cur.executemany(
                        """
                        INSERT INTO targets (name, url, category, is_active)
                        VALUES (%s, %s, %s, TRUE)
                        ON CONFLICT (url) DO NOTHING;
                        """,
                        default_targets
                    )
                    logger.info("Seeded default monitored targets into targets table.")

                # 7. Seed default probe records
                cur.execute("SELECT COUNT(*) as count FROM probes;")
                row = cur.fetchone()
                if row["count"] == 0:
                    default_probes = [
                        ("blr-probe-01", "Bangalore Primary Probe", "Bangalore, IN"),
                        ("mum-probe-01", "Mumbai Secondary Probe", "Mumbai, IN"),
                        ("del-probe-01", "Delhi Edge Probe", "Delhi, IN")
                    ]
                    cur.executemany(
                        """
                        INSERT INTO probes (probe_id, name, location, status)
                        VALUES (%s, %s, %s, 'active')
                        ON CONFLICT (probe_id) DO NOTHING;
                        """,
                        default_probes
                    )
                    logger.info("Seeded default probes.")

        logger.info("Stage 2 database initialization finished successfully.")
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        raise
