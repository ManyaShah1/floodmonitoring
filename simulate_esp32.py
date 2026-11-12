"""
ESP32 Telemetry Simulator (Python Standard Library Only)
Use this script to test the Flood Monitoring Dashboard without a physical ESP32.

Features:
- Uses only Python standard library (urllib, json, time). No extra packages required.
- Option 1: Send a single custom test reading (Normal, Warning, or Danger).
- Option 2: Run a live continuous loop simulating realistic water rise and fall.
"""

import sys
import time
import json
import random
import urllib.request
import urllib.error

DEFAULT_URL = "http://127.0.0.1:8000/api/readings"


def send_reading(payload: dict, server_url: str = DEFAULT_URL) -> bool:
    """Sends a single JSON reading to the FastAPI server."""
    data_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        server_url,
        data=data_bytes,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            res_body = response.read().decode("utf-8")
            print(f"[SUCCESS] Sent -> Level: {payload['water_level_percent']:.1f}% | "
                  f"Status: {payload.get('status')} | Server Response: {res_body}")
            return True
    except urllib.error.URLError as e:
        print(f"[ERROR] Could not connect to {server_url}: {e.reason}")
        print(" -> Make sure your FastAPI server is running with: uvicorn backend.main:app --reload")
        return False


def run_continuous_simulation(server_url: str = DEFAULT_URL):
    """
    Simulates water level rising steadily up to danger level,
    activating the float switch, then receding back to normal.
    """
    print(f"\n🌊 Starting live ESP32 simulation to: {server_url}")
    print("   Press CTRL+C anytime to stop.\n")

    water_percent = 35.0  # Start at normal level
    direction = 1.0       # 1 for rising, -1 for draining

    while True:
        # Determine status and float switch based on water level
        float_activated = False
        if water_percent >= 88.0:
            float_activated = True
            status = "DANGER"
        elif water_percent >= 85.0:
            status = "DANGER"
        elif water_percent >= 60.0:
            status = "WARNING"
        else:
            status = "NORMAL"

        # Calculate simulated physical dimensions (assuming a 30cm depth container)
        max_depth = 30.0
        depth_cm = round((water_percent / 100.0) * max_depth, 2)
        distance_cm = round(max_depth - depth_cm + 2.0, 2)
        rise_rate = round((direction * random.uniform(0.3, 0.8)), 2)

        # Rain simulation (rain detected more frequently when water is high)
        rain_detected = water_percent > 55.0
        rain_val = random.randint(1800, 3200) if rain_detected else random.randint(300, 800)

        payload = {
            "water_level_percent": round(water_percent, 2),
            "water_depth_cm": depth_cm,
            "distance_cm": distance_cm,
            "water_rise_rate": rise_rate,
            "rain_value": rain_val,
            "rain_detected": rain_detected,
            "float_activated": float_activated,
            "status": status,
        }

        send_reading(payload, server_url)

        # Update water level for next step
        water_percent += direction * random.uniform(2.5, 4.0)

        # Reverse direction at peaks
        if water_percent >= 94.0:
            direction = -1.0
            print("   --- ⚠️ Peak water level reached. Starting to drain... ---")
        elif water_percent <= 25.0:
            direction = 1.0
            print("   --- 💧 Normal level reached. Starting to fill again... ---")

        time.sleep(2.0)  # Telemetry interval


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL

    print("=" * 60)
    print("   ESP32 Flood Monitoring - Telemetry Simulator")
    print("=" * 60)
    print("1. Send a single NORMAL reading (35.0%)")
    print("2. Send a single WARNING reading (72.5%)")
    print("3. Send a single DANGER reading (90.0% + Float Switch)")
    print("4. Run continuous live simulation (every 2s)")
    print("=" * 60)

    try:
        choice = input("Select an option (1-4) [Default 4]: ").strip()
    except (EOFError, KeyboardInterrupt):
        choice = "4"

    if choice == "1":
        send_reading({
            "water_level_percent": 35.0,
            "water_depth_cm": 10.5,
            "distance_cm": 19.5,
            "water_rise_rate": 0.05,
            "rain_value": 450,
            "rain_detected": False,
            "float_activated": False,
            "status": "NORMAL"
        }, url)
    elif choice == "2":
        send_reading({
            "water_level_percent": 72.5,
            "water_depth_cm": 21.75,
            "distance_cm": 8.25,
            "water_rise_rate": 0.35,
            "rain_value": 1600,
            "rain_detected": True,
            "float_activated": False,
            "status": "WARNING"
        }, url)
    elif choice == "3":
        send_reading({
            "water_level_percent": 90.0,
            "water_depth_cm": 27.0,
            "distance_cm": 3.0,
            "water_rise_rate": 0.85,
            "rain_value": 2800,
            "rain_detected": True,
            "float_activated": True,
            "status": "DANGER"
        }, url)
    else:
        try:
            run_continuous_simulation(url)
        except KeyboardInterrupt:
            print("\nSimulation stopped.")

