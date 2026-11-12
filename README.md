# ESP32 Wi-Fi Based Flood Monitoring Dashboard

A clean, modern, beginner-friendly IoT flood monitoring dashboard powered by **FastAPI**, **SQLite**, and **Vanilla HTML5/CSS3/JavaScript** with **Chart.js**.

---

## 📁 1. Project Folder Structure & File Explanations

```text
floodmonitoring/
│
├── backend/
│   ├── main.py              # FastAPI server, REST API endpoints, and static file serving
│   ├── database.py          # SQLite database connection, table creation, and queries
│   ├── models.py            # Pydantic schemas for data validation and alert priority logic
│   └── flood_monitor.db     # SQLite database file storing telemetry readings
│
├── frontend/
│   ├── index.html           # Dashboard layout: cards, water tank visualizer, LEDs, chart
│   ├── style.css            # Responsive styles, LED glowing animations, water tank wave effect
│   └── script.js            # 2s polling, Chart.js live stream, and Web Audio API danger buzzer
│
├── esp32_firmware_sample.ino # Ready-to-flash Arduino C++ firmware sketch (USB Serial)
├── serial_bridge.py         # Reads USB Serial data from ESP32 and posts to FastAPI
├── simulate_esp32.py        # Python telemetry simulator for testing without hardware
├── requirements.txt         # Python dependencies (fastapi, uvicorn, pydantic, pyserial, requests)
└── README.md                # Complete documentation and step-by-step setup guide
```

---

## ⚡ 2. Quick Start: Install Dependencies

Make sure Python 3.9+ is installed on your computer.

Open your terminal or command prompt in the project root folder:

```bash
pip install -r requirements.txt
```

---

## 🚀 3. Run the FastAPI Backend Server

Run the server using Uvicorn:

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

- `--host 0.0.0.0` ensures the server listens on all network interfaces, allowing both your computer's browser and your ESP32 on the Wi-Fi network to reach it.
- `--port 8000` starts the server on port `8000`.
- `--reload` auto-reloads the server whenever you edit a Python file.

---

## 🌐 4. How to Open the Dashboard in a Browser

Once the server is running:

1. Open your web browser (Chrome, Edge, Firefox, or Safari).
2. Visit:
   ```text
   http://localhost:8000
   ```
   Or visit using your local computer IP address:
   ```text
   http://<YOUR_COMPUTER_IP>:8000
   ```
3. Click the **"🔊 Enable Sound Alerts"** button in the top-right corner to allow the browser to sound the audible alarm if water reaches critical danger levels.

---

## 🔍 5. How to Find Your Computer's Local IPv4 Address

Your ESP32 needs your computer's local IP address on your home or lab Wi-Fi network (e.g. `192.168.1.15`).

### On macOS:
Open Terminal and run:
```bash
ipconfig getifaddr en0
```
*(If on Wi-Fi and nothing shows, try `en1` or check System Settings > Wi-Fi > Details > IP address).*

### On Windows:
Open Command Prompt (`cmd`) and run:
```cmd
ipconfig
```
Look for **IPv4 Address** under your active Wi-Fi adapter (e.g., `192.168.x.x`).

### On Linux:
Open Terminal and run:
```bash
hostname -I | awk '{print $1}'
```

---

## 📶 6. Connecting ESP32 and Computer to the Same Wi-Fi

1. Both your computer and your ESP32 **must be connected to the exact same Wi-Fi router / SSID**.
2. **Note on 5 GHz vs 2.4 GHz**: ESP32 only supports **2.4 GHz Wi-Fi**. Ensure your Wi-Fi network broadcasts 2.4 GHz.
3. If using a mobile hotspot, connect both your laptop and ESP32 to the hotspot.

---

## ⚙️ 7. Updating the ESP32 Firmware

Open `esp32_firmware_sample.ino` in the Arduino IDE:

1. Update the Wi-Fi credentials:
   ```cpp
   const char* WIFI_SSID     = "Your_WiFi_Name";
   const char* WIFI_PASSWORD = "Your_WiFi_Password";
   ```
2. Update the `SERVER_URL` with your computer's local IP:
   ```cpp
   // Example if your computer's IP is 192.168.1.50:
   const char* SERVER_URL = "http://192.168.1.50:8000/api/readings";
   ```
3. Upload the sketch to your ESP32.
4. Open the Arduino Serial Monitor at **115200 baud** to see Wi-Fi connection and HTTP response codes.

---

## 🧪 8. Testing the API Without an ESP32 (Sample Data)

You can test the entire dashboard and alarm system without physical hardware using either `curl` or the included Python simulator script.

### Option A: Using the Python Simulator (`simulate_esp32.py`)
Run the interactive simulator in a separate terminal:
```bash
python simulate_esp32.py
```
You can choose:
- `1` - Send a **NORMAL** reading (< 60%).
- `2` - Send a **WARNING** reading (60% to 84.99%).
- `3` - Send a **DANGER** reading (≥ 85% with float switch active).
- `4` - Run a continuous simulation loop updating every 2 seconds with simulated rising and falling water levels.

### Option B: Using `curl` Commands

#### Test 1: Send a NORMAL reading (< 60%)
```bash
curl -X POST http://127.0.0.1:8000/api/readings \
  -H "Content-Type: application/json" \
  -d '{
    "water_level_percent": 35.0,
    "water_depth_cm": 10.5,
    "distance_cm": 19.5,
    "water_rise_rate": 0.05,
    "rain_value": 450,
    "rain_detected": false,
    "float_activated": false,
    "status": "NORMAL"
  }'
```

#### Test 2: Send a WARNING reading (60% - 84.99%)
```bash
curl -X POST http://127.0.0.1:8000/api/readings \
  -H "Content-Type: application/json" \
  -d '{
    "water_level_percent": 68.0,
    "water_depth_cm": 20.4,
    "distance_cm": 9.6,
    "water_rise_rate": 0.35,
    "rain_value": 1600,
    "rain_detected": true,
    "float_activated": false,
    "status": "WARNING"
  }'
```

#### Test 3: Send a DANGER reading (≥ 85% or Float Switch Active)
```bash
curl -X POST http://127.0.0.1:8000/api/readings \
  -H "Content-Type: application/json" \
  -d '{
    "water_level_percent": 91.5,
    "water_depth_cm": 27.45,
    "distance_cm": 2.55,
    "water_rise_rate": 0.85,
    "rain_value": 3100,
    "rain_detected": true,
    "float_activated": true,
    "status": "DANGER"
  }'
```

---

## 📡 9. REST API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/readings` | Receives JSON telemetry from ESP32, validates schema, saves to SQLite |
| `GET` | `/api/latest` | Returns the most recent reading and server timestamp |
| `GET` | `/api/history` | Returns up to the latest 100 readings chronologically for charting |
| `GET` | `/api/status` | Returns whether ESP32 is online (telemetry received in last 10s) |
| `GET` | `/` | Serves the web dashboard HTML interface |

---

## 🚨 10. Alert & Sound Logic

- **NORMAL**: Water level < 60%
  - Green LED lights up.
  - Water tank fill is aqua-blue.
  - Audible alarm is silent.
- **WARNING**: Water level between 60% and 84.99%
  - Yellow LED lights up.
  - Water tank fill turns amber.
  - Audible alarm remains silent.
- **DANGER**: Water level ≥ 85% OR Emergency Float Switch is triggered
  - Red LED pulses urgently.
  - Water tank fill turns red.
  - Audible browser buzzer sounds repeating warning tones (Web Audio API).
- **OFFLINE / DISCONNECTED**: No readings received for > 10 seconds
  - Header badge switches to `ESP32 OFFLINE`.
  - Alert banner informs the operator that connection was lost.
  - Stale readings are never displayed as active telemetry.

