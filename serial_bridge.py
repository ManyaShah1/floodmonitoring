"""
ESP32 USB Serial to FastAPI HTTP Bridge
Reads JSON sensor readings from ESP32 over USB Serial and forwards them
to the local FastAPI backend at http://127.0.0.1:8000/api/readings.
"""

import sys
import time
import json
import glob
import serial
import requests

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
# Your ESP32 port detected on macOS:
DEFAULT_PORT = "/dev/cu.usbserial-0001"
BAUD_RATE = 115200
API_URL = "http://127.0.0.1:8000/api/readings"


def find_esp32_port() -> str:
    """Finds available USB serial ports on macOS."""
    # First check default port
    ports = glob.glob("/dev/cu.usbserial*") + glob.glob("/dev/cu.SLAB_USBtoUART*") + glob.glob("/dev/cu.wchusbserial*")
    if DEFAULT_PORT in ports:
        return DEFAULT_PORT
    if ports:
        return ports[0]
    return DEFAULT_PORT


def run_bridge(port: str):
    print("=" * 65)
    print("   🌊 ESP32 USB Serial Bridge -> FastAPI")
    print("=" * 65)
    print(f"Target Serial Port : {port}")
    print(f"Baud Rate          : {BAUD_RATE}")
    print(f"FastAPI Endpoint   : {API_URL}")
    print("=" * 65)
    print("⚠️  Make sure the Arduino IDE Serial Monitor is CLOSED.")
    print("Press CTRL+C anytime to stop.\n")

    while True:
        try:
            print(f"Connecting to {port} at {BAUD_RATE} baud...")
            with serial.Serial(port, BAUD_RATE, timeout=2.0) as esp32:
                print("✅ ESP32 connected successfully over USB!")
                print("Awaiting sensor data...\n")
                
                # Allow connection to settle
                time.sleep(2)
                
                # Flush startup gibberish/bootloader characters
                esp32.reset_input_buffer()

                while True:
                    raw_line = esp32.readline()
                    if not raw_line:
                        continue

                    line = raw_line.decode("utf-8", errors="ignore").strip()
                    if not line:
                        continue

                    # Ignore boot messages, debug logs, or non-JSON lines
                    if not line.startswith("{"):
                        print(f"[ESP32 Log] {line}")
                        continue

                    try:
                        data = json.loads(line)
                        water_lvl = data.get("water_level_percent", "--")
                        status_str = data.get("status", "--")
                        rise_rate = data.get("water_rise_rate", "--")

                        # Forward readings to FastAPI via HTTP POST
                        response = requests.post(API_URL, json=data, timeout=3.0)

                        if response.status_code in (200, 201):
                            print(f"[OK] Level: {water_lvl}% | Rate: {rise_rate}%/s | Status: {status_str} -> Backend {response.status_code}")
                        else:
                            print(f"[WARN] Backend returned status {response.status_code}: {response.text}")

                    except json.JSONDecodeError:
                        print(f"[WARN] Incomplete JSON received: {line}")
                    except requests.RequestException as error:
                        print(f"[ERROR] Could not forward to FastAPI: {error}")
                        print("       Make sure FastAPI is running (uvicorn backend.main:app)")

        except serial.SerialException as error:
            print(f"\n❌ Serial connection error: {error}")
            print("Retrying in 3 seconds (check if cable is plugged in)...")
            time.sleep(3)
        except KeyboardInterrupt:
            print("\n🛑 Serial bridge stopped by user.")
            break


def main():
    selected_port = sys.argv[1] if len(sys.argv) > 1 else find_esp32_port()
    run_bridge(selected_port)


if __name__ == "__main__":
    main()

