"""
Database Module for ESP32 Flood Monitoring System
Uses Python's built-in sqlite3 library.
"""

import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

# Resolve the database path relative to this file's folder (backend/flood_monitor.db)
DB_PATH = Path(__file__).resolve().parent / "flood_monitor.db"


def get_db_connection() -> sqlite3.Connection:
    """
    Creates and returns a connection to the SQLite database.
    row_factory is set to sqlite3.Row so columns can be accessed by name like dictionaries.
    """
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """
    Initializes the SQLite database and creates the 'readings' table if it doesn't already exist.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create readings table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS readings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        water_level_percent REAL NOT NULL,
        water_depth_cm REAL NOT NULL,
        distance_cm REAL NOT NULL,
        water_rise_rate REAL NOT NULL,
        rain_value REAL NOT NULL,
        rain_detected INTEGER NOT NULL,
        float_activated INTEGER NOT NULL,
        status TEXT NOT NULL,
        timestamp TEXT NOT NULL
    );
    """)

    # Create an index on timestamp for fast history ordering
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_readings_timestamp ON readings (timestamp);
    """)

    conn.commit()
    conn.close()


def insert_reading(data: Dict[str, Any]) -> int:
    """
    Inserts a validated sensor reading from the ESP32 into the database.
    Returns the newly created row ID.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # If timestamp is not provided, use current UTC ISO-8601 string
    timestamp = data.get("timestamp") or datetime.now(timezone.utc).isoformat()

    cursor.execute("""
    INSERT INTO readings (
        water_level_percent,
        water_depth_cm,
        distance_cm,
        water_rise_rate,
        rain_value,
        rain_detected,
        float_activated,
        status,
        timestamp
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        float(data["water_level_percent"]),
        float(data["water_depth_cm"]),
        float(data["distance_cm"]),
        float(data["water_rise_rate"]),
        float(data["rain_value"]),
        1 if data["rain_detected"] else 0,
        1 if data["float_activated"] else 0,
        str(data["status"]),
        timestamp
    ))

    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id


def row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    """Helper function to convert a sqlite3.Row object to a clean JSON-serializable dictionary."""
    return {
        "id": row["id"],
        "water_level_percent": float(row["water_level_percent"]),
        "water_depth_cm": float(row["water_depth_cm"]),
        "distance_cm": float(row["distance_cm"]),
        "water_rise_rate": float(row["water_rise_rate"]),
        "rain_value": float(row["rain_value"]),
        "rain_detected": bool(row["rain_detected"]),
        "float_activated": bool(row["float_activated"]),
        "status": row["status"],
        "timestamp": row["timestamp"],
    }


def get_latest_reading() -> Optional[Dict[str, Any]]:
    """
    Retrieves the most recent sensor reading from the database.
    Returns None if the database has no records yet.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT * FROM readings
    ORDER BY id DESC
    LIMIT 1;
    """)

    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None

    return row_to_dict(row)


def get_history_readings(limit: int = 100) -> List[Dict[str, Any]]:
    """
    Retrieves the latest readings up to 'limit' items.
    Returns them in chronological order (oldest to newest)
    so frontend charts can render the time series from left to right.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Subquery fetches the latest N records, then outer query orders them chronologically (ASC)
    cursor.execute("""
    SELECT * FROM (
        SELECT * FROM readings
        ORDER BY id DESC
        LIMIT ?
    ) ORDER BY id ASC;
    """, (limit,))

    rows = cursor.fetchall()
    conn.close()

    return [row_to_dict(row) for row in rows]

