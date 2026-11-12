"""
FastAPI Backend for ESP32 Wi-Fi Flood Monitoring System
Single server hosting both REST API and Frontend Dashboard.
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .database import (
    init_db,
    insert_reading,
    get_latest_reading,
    get_history_readings,
    get_db_connection,
)
from .models import (
    SensorReadingCreate,
    SensorReadingResponse,
    LatestReadingResponse,
    SystemStatusResponse,
)

# Paths for frontend files
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs on server startup and shutdown.
    Ensures SQLite tables and indexes exist before handling requests.
    """
    print("[STARTUP] Initializing SQLite database...")
    init_db()
    print("[STARTUP] Database ready.")
    yield
    print("[SHUTDOWN] Server shutting down.")


# Initialize FastAPI application
app = FastAPI(
    title="ESP32 Flood Monitoring API",
    description="REST API and Real-Time Dashboard for ESP32 Wi-Fi Flood Monitoring System",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS (Cross-Origin Resource Sharing)
# This allows testing the dashboard from localhost or across a local Wi-Fi network.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------------------------------
# API Endpoints
# --------------------------------------------------------------------------

@app.post(
    "/api/readings",
    status_code=status.HTTP_201_CREATED,
    summary="Receive sensor readings from ESP32",
    response_description="Confirmation of stored reading",
)
def create_reading(payload: SensorReadingCreate):
    """
    Endpoint for ESP32 to send sensor data via HTTP POST.
    Validates data against SensorReadingCreate Pydantic schema and stores in SQLite.
    """
    try:
        data_dict = payload.model_dump()
        new_id = insert_reading(data_dict)
        return {
            "status": "success",
            "message": "Sensor reading recorded successfully",
            "id": new_id,
            "recorded_status": payload.status,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error while saving reading: {str(exc)}",
        )


@app.get(
    "/api/latest",
    response_model=LatestReadingResponse,
    summary="Get the most recent sensor reading",
)
def read_latest():
    """
    Returns the latest sensor reading from SQLite.
    Includes timestamp and server time.
    """
    try:
        latest = get_latest_reading()
        current_time = datetime.now(timezone.utc).isoformat()
        if latest is None:
            return LatestReadingResponse(
                reading=None,
                server_time=current_time,
                message="No readings recorded yet. Awaiting ESP32 connection.",
            )
        return LatestReadingResponse(
            reading=SensorReadingResponse(**latest),
            server_time=current_time,
            message="OK",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query latest reading: {str(exc)}",
        )


@app.get(
    "/api/history",
    response_model=List[SensorReadingResponse],
    summary="Get the latest 100 sensor readings",
)
def read_history(limit: int = 100):
    """
    Returns up to the latest 100 sensor readings sorted chronologically by timestamp.
    Used by the dashboard to draw and update the Chart.js line graph.
    """
    try:
        # Constrain limit between 1 and 500
        safe_limit = max(1, min(limit, 500))
        history = get_history_readings(limit=safe_limit)
        return [SensorReadingResponse(**r) for r in history]
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query history: {str(exc)}",
        )


@app.get(
    "/api/status",
    response_model=SystemStatusResponse,
    summary="Check ESP32 online/offline connection status",
)
def check_device_status():
    """
    Checks if ESP32 has sent a reading within the last 10 seconds.
    If latest reading is < 10 seconds old, the device is considered ONLINE.
    Otherwise, it is marked OFFLINE.
    """
    try:
        latest = get_latest_reading()
        threshold = 10  # seconds

        if latest is None:
            return SystemStatusResponse(
                online=False,
                last_seen_seconds_ago=None,
                latest_timestamp=None,
                threshold_seconds=threshold,
                total_readings=0,
            )

        # Parse reading timestamp
        ts_str = latest["timestamp"]
        try:
            # Attempt parsing ISO format
            reading_time = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except ValueError:
            # Fallback format if needed
            reading_time = datetime.strptime(ts_str[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        elapsed_seconds = (now - reading_time).total_seconds()
        # In case of minor local clock drift, prevent negative elapsed seconds
        elapsed_seconds = max(0.0, elapsed_seconds)

        is_online = elapsed_seconds <= threshold

        # Count total readings
        conn = get_db_connection()
        count_cursor = conn.cursor()
        count_cursor.execute("SELECT COUNT(*) FROM readings;")
        total_count = count_cursor.fetchone()[0]
        conn.close()

        return SystemStatusResponse(
            online=is_online,
            last_seen_seconds_ago=round(elapsed_seconds, 1),
            latest_timestamp=ts_str,
            threshold_seconds=threshold,
            total_readings=total_count,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check device status: {str(exc)}",
        )


# --------------------------------------------------------------------------
# Frontend Static Serving
# --------------------------------------------------------------------------

# Serve index.html explicitly at root
@app.get("/", include_in_schema=False)
def serve_index():
    index_file = FRONTEND_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Frontend index.html not found.")
    return FileResponse(str(index_file))


# Mount the entire frontend folder for static assets (style.css, script.js, etc.)
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    # When run directly with 'python backend/main.py', start Uvicorn
    # Listening on 0.0.0.0 makes the dashboard accessible to other devices on the same Wi-Fi
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)

