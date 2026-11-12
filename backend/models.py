"""
Pydantic Data Models and Validation for ESP32 Flood Monitoring
"""

from pydantic import BaseModel, Field, model_validator
from typing import Optional, List
from datetime import datetime, timezone


def determine_flood_status(water_level_percent: float, float_activated: bool) -> str:
    """
    Standard Alert Priority Logic:
    - SENSOR_ERROR: water_level_percent < 0 (sensor timeout/echo error)
    - DANGER:  water_level_percent >= 85 OR float_activated == True
    - WARNING: water_level_percent >= 60 AND water_level_percent < 85
    - NORMAL:  water_level_percent >= 0 AND water_level_percent < 60
    """
    if float_activated:
        return "DANGER"
    elif water_level_percent < 0:
        return "SENSOR_ERROR"
    elif water_level_percent >= 85.0:
        return "DANGER"
    elif water_level_percent >= 60.0:
        return "WARNING"
    else:
        return "NORMAL"


class SensorReadingCreate(BaseModel):
    """
    Schema for validating incoming HTTP POST JSON payloads from the ESP32.
    Example:
    {
      "water_level_percent": 65.5,
      "water_depth_cm": 19.65,
      "distance_cm": 10.35,
      "water_rise_rate": 0.25,
      "rain_value": 1500,
      "rain_detected": true,
      "float_activated": false,
      "status": "WARNING"
    }
    """
    water_level_percent: float = Field(..., description="Calculated water percentage (0-100%)")
    water_depth_cm: float = Field(..., description="Depth of water column in centimeters")
    distance_cm: float = Field(..., description="Ultrasonic distance from sensor to water level in cm")
    water_rise_rate: float = Field(..., description="Rate of water level rise in %/s or cm/s")
    rain_value: float = Field(..., description="Raw analog rain sensor reading (e.g. 0-4095)")
    rain_detected: bool = Field(..., description="Whether rain is currently detected")
    float_activated: bool = Field(..., description="Emergency float switch trigger state")
    status: Optional[str] = Field(None, description="Reported status string: NORMAL, WARNING, DANGER")

    @model_validator(mode="after")
    def validate_and_compute_status(self) -> "SensorReadingCreate":
        """
        Validates the status. If omitted or inconsistent, applies the strict alert logic:
        DANGER >= 85% or float switch active, WARNING >= 60%, NORMAL < 60%, SENSOR_ERROR < 0.
        """
        computed = determine_flood_status(self.water_level_percent, self.float_activated)

        if self.status:
            v_upper = self.status.strip().upper()
            if computed == "DANGER":
                self.status = "DANGER"
            elif v_upper in {"NORMAL", "WARNING", "DANGER", "SENSOR_ERROR"}:
                self.status = v_upper
            else:
                self.status = computed
        else:
            self.status = computed

        return self


class SensorReadingResponse(BaseModel):
    """Schema for returning sensor reading details."""
    id: int
    water_level_percent: float
    water_depth_cm: float
    distance_cm: float
    water_rise_rate: float
    rain_value: float
    rain_detected: bool
    float_activated: bool
    status: str
    timestamp: str


class LatestReadingResponse(BaseModel):
    """Schema for the GET /api/latest endpoint."""
    reading: Optional[SensorReadingResponse] = None
    server_time: str
    message: Optional[str] = None


class SystemStatusResponse(BaseModel):
    """Schema for the GET /api/status endpoint."""
    online: bool
    last_seen_seconds_ago: Optional[float]
    latest_timestamp: Optional[str]
    threshold_seconds: int = 10
    total_readings: Optional[int] = None

