"""
GuardX — Database Manager (Layer 5)

SQLite database with WAL mode for concurrent read/write.
Creates and manages all 6 tables.
"""

import sqlite3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_PATH


def get_connection() -> sqlite3.Connection:
    """Get a database connection with WAL mode and row factory."""
    os.makedirs(os.path.dirname(DB_PATH) if os.path.dirname(DB_PATH) else ".", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create all tables if they don't exist."""
    conn = get_connection()
    cursor = conn.cursor()

    # Table 3: Anomaly detection results
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS anomaly_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            anomaly_score REAL NOT NULL,
            is_anomaly INTEGER NOT NULL DEFAULT 0,
            model_type TEXT NOT NULL DEFAULT 'isolation_forest',
            fault_prediction TEXT,
            fault_probability REAL,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    # Table 4: Health scores
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS health_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            health_score REAL NOT NULL,
            risk_level TEXT NOT NULL,
            anomaly_risk REAL,
            vibration_risk REAL,
            temperature_risk REAL,
            current_risk REAL,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    # Table 5: Fault labels (human-in-the-loop)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fault_labels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_timestamp TEXT NOT NULL,
            end_timestamp TEXT NOT NULL,
            fault_type TEXT NOT NULL,
            severity TEXT DEFAULT 'medium',
            notes TEXT,
            labeled_by TEXT DEFAULT 'operator',
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    # Table 6: Alerts
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            alert_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            message TEXT NOT NULL,
            health_score REAL,
            acknowledged INTEGER DEFAULT 0,
            acknowledged_at TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    # Create indices for performance (only on SQLite tables — raw/features are in InfluxDB)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_anomaly_timestamp ON anomaly_results(timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_health_timestamp ON health_scores(timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts(timestamp)")

    conn.commit()
    conn.close()
    return True


if __name__ == "__main__":
    init_db()
    print(f"[OK] Database initialized at {DB_PATH}")
