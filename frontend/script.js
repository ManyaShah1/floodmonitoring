/**
 * Flood Monitoring System - Real-Time Dashboard Client
 * 
 * Beginner-Friendly Vanilla JavaScript:
 * - Polls FastAPI every 2 seconds.
 * - Updates DOM metrics, vertical water tank, and 3 LED indicators.
 * - Streams live points into Chart.js (keeps 50 latest points).
 * - Implements Web Audio API buzzer for danger alarms with user gesture handling.
 */

// =============================================================================
// 1. Global State & DOM Element References
// =============================================================================

const API_BASE = ""; // Relative paths work seamlessly because FastAPI serves frontend directly
const POLL_INTERVAL_MS = 2000;
const MAX_CHART_POINTS = 50;

// Current state object
const state = {
  isOnline: false,
  latestReading: null,
  isAudioPermitted: false,
  isMuted: false,
  isDangerAlarmPlaying: false,
};

// DOM Elements
const connectionBadge = document.getElementById("connectionBadge");
const connectionText = document.getElementById("connectionText");

const btnEnableAudio = document.getElementById("btnEnableAudio");
const btnTestAudio = document.getElementById("btnTestAudio");
const btnMuteAudio = document.getElementById("btnMuteAudio");
const audioStatusText = document.getElementById("audioStatusText");

const alertBanner = document.getElementById("alertBanner");
const alertIcon = document.getElementById("alertIcon");
const alertTitle = document.getElementById("alertTitle");
const alertMessage = document.getElementById("alertMessage");
const alertTimestamp = document.getElementById("alertTimestamp");

const ledItemGreen = document.getElementById("ledItemGreen");
const ledItemYellow = document.getElementById("ledItemYellow");
const ledItemRed = document.getElementById("ledItemRed");

const waterFill = document.getElementById("waterFill");
const valPercent = document.getElementById("valPercent");
const valDepth = document.getElementById("valDepth");
const valDistance = document.getElementById("valDistance");

const valRainDetected = document.getElementById("valRainDetected");
const valRainRaw = document.getElementById("valRainRaw");
const valFloatState = document.getElementById("valFloatState");
const valFloatSub = document.getElementById("valFloatSub");
const valRiseRate = document.getElementById("valRiseRate");
const valLastUpdated = document.getElementById("valLastUpdated");
const valLastSeen = document.getElementById("valLastSeen");

// =============================================================================
// 2. Web Audio API Buzzer (Audible Danger Alert)
// =============================================================================

let audioCtx = null;
let buzzerInterval = null;

/**
 * Initializes the AudioContext upon user click.
 * Modern browsers require user interaction before playing audio.
 */
async function initAudio() {
  try {
    if (!audioCtx) {
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      if (AudioContextClass) {
        audioCtx = new AudioContextClass();
      }
    }

    if (audioCtx && audioCtx.state === "suspended") {
      await audioCtx.resume();
    }

    state.isAudioPermitted = true;
    state.isMuted = false;

    btnEnableAudio.style.display = "none";
    btnMuteAudio.style.display = "inline-block";
    btnTestAudio.style.display = "inline-block";
    btnMuteAudio.textContent = "🔇 Mute";
    btnMuteAudio.classList.remove("btn-muted");
    audioStatusText.textContent = "Sound: Active";

    // Play a friendly confirmation chirp so the user knows speaker is working
    playBeep(660, 0.12);

    // If danger is already active when permission is granted, start sounding immediately
    checkAlarmCondition();
  } catch (err) {
    console.error("Failed to initialize audio:", err);
    alert("Audio initialization error: " + err.message);
  }
}

/**
 * Plays a short manual test sound when clicking the 'Test Sound' button.
 */
async function triggerAudioTest() {
  if (!state.isAudioPermitted) {
    await initAudio();
    return;
  }
  if (audioCtx && audioCtx.state === "suspended") {
    await audioCtx.resume();
  }
  // Play two distinct test beeps
  playBeep(880, 0.18);
  setTimeout(() => playBeep(1100, 0.22), 220);
}

/**
 * Toggles Mute / Unmute state.
 */
function toggleMute() {
  state.isMuted = !state.isMuted;
  if (state.isMuted) {
    btnMuteAudio.textContent = "🔊 Unmute";
    audioStatusText.textContent = "Sound: Muted";
    audioStatusText.style.color = "";
    stopBuzzerTone();
  } else {
    btnMuteAudio.textContent = "🔇 Mute";
    audioStatusText.textContent = "Sound: Active";
    checkAlarmCondition();
  }
}

/**
 * Plays a single synthesizer beep pulse using Web Audio API.
 * Frequency 880Hz / 920Hz creates an unmistakable piercing alert beep.
 */
function playBeep(frequency = 880, duration = 0.18) {
  if (!audioCtx || state.isMuted || !state.isAudioPermitted) return;

  if (audioCtx.state === "suspended") {
    audioCtx.resume();
  }

  try {
    const osc = audioCtx.createOscillator();
    const gainNode = audioCtx.createGain();

    osc.type = "sawtooth"; // piercing buzzer timbre
    osc.frequency.setValueAtTime(frequency, audioCtx.currentTime);

    const now = audioCtx.currentTime;
    gainNode.gain.setValueAtTime(0.001, now);
    gainNode.gain.linearRampToValueAtTime(0.4, now + 0.02);
    gainNode.gain.linearRampToValueAtTime(0.001, now + duration);

    osc.connect(gainNode);
    gainNode.connect(audioCtx.destination);

    osc.start(now);
    osc.stop(now + duration + 0.02);
  } catch (err) {
    console.warn("Audio playback error:", err);
  }
}

/**
 * Starts repeating buzzer pattern if not already active.
 * Avoids creating overlapping intervals or duplicate audio oscillators.
 */
function startBuzzerTone() {
  if (state.isDangerAlarmPlaying) return; // Prevent duplicate alarms
  state.isDangerAlarmPlaying = true;

  audioStatusText.textContent = "🚨 ALARM BUZZING!";
  audioStatusText.style.color = "#dc2626";

  // Immediate first beep
  playBeep(880, 0.18);

  // Repeating tone every 400ms: alternate between high and mid tone
  let toggle = false;
  buzzerInterval = setInterval(() => {
    if (state.isMuted || !state.isAudioPermitted) return;
    const freq = toggle ? 700 : 920;
    playBeep(freq, 0.16);
    toggle = !toggle;
  }, 400);
}

/**
 * Stops the repeating buzzer tone when danger clears.
 */
function stopBuzzerTone() {
  if (buzzerInterval) {
    clearInterval(buzzerInterval);
    buzzerInterval = null;
  }
  state.isDangerAlarmPlaying = false;
  audioStatusText.style.color = "";
  audioStatusText.textContent = state.isMuted
    ? "Sound: Muted"
    : (state.isAudioPermitted ? "Sound: Active" : "Sound: Disabled");
}

/**
 * Evaluates whether danger alarm should be buzzing based on current state.
 */
function checkAlarmCondition() {
  if (!state.latestReading || !state.isOnline) {
    stopBuzzerTone();
    return;
  }

  const reading = state.latestReading;
  const waterPercent = Number(reading.water_level_percent);

  // Robust boolean coercion for float_activated (handles true, 1, "true", etc.)
  const floatActive = Boolean(
    reading.float_activated === true ||
    reading.float_activated === 1 ||
    reading.float_activated === "true"
  );

  const statusStr = String(reading.status || "").trim().toUpperCase();

  // DANGER if water >= 85%, or float switch triggered, or status is explicitly DANGER
  const isDanger = (statusStr === "DANGER") || (waterPercent >= 85) || floatActive;

  if (isDanger && state.isAudioPermitted && !state.isMuted) {
    startBuzzerTone();
  } else {
    stopBuzzerTone();
  }
}

// Setup audio button event listeners
btnEnableAudio.addEventListener("click", initAudio);
btnTestAudio.addEventListener("click", triggerAudioTest);
btnMuteAudio.addEventListener("click", toggleMute);

// =============================================================================
// 3. Chart.js Setup (Live Water Level Graph)
// =============================================================================

let waterChart = null;

// Custom Chart.js Plugin to draw constant threshold reference lines (60% and 85%)
const thresholdLinesPlugin = {
  id: "thresholdLines",
  afterDraw(chart) {
    const { ctx, chartArea: { left, right }, scales: { y } } = chart;
    if (!y) return;

    ctx.save();

    // 1. Draw 60% Warning Threshold Line (Dashed Yellow)
    const yWarning = y.getPixelForValue(60);
    ctx.beginPath();
    ctx.setLineDash([5, 5]);
    ctx.lineWidth = 1.5;
    ctx.strokeStyle = "rgba(245, 158, 11, 0.85)";
    ctx.moveTo(left, yWarning);
    ctx.lineTo(right, yWarning);
    ctx.stroke();

    ctx.fillStyle = "#b45309";
    ctx.font = "bold 10px sans-serif";
    ctx.fillText("WARNING THRESHOLD (60%)", left + 8, yWarning - 4);

    // 2. Draw 85% Danger Threshold Line (Dashed Red)
    const yDanger = y.getPixelForValue(85);
    ctx.beginPath();
    ctx.setLineDash([5, 5]);
    ctx.lineWidth = 1.5;
    ctx.strokeStyle = "rgba(239, 68, 68, 0.9)";
    ctx.moveTo(left, yDanger);
    ctx.lineTo(right, yDanger);
    ctx.stroke();

    ctx.fillStyle = "#b91c1c";
    ctx.font = "bold 10px sans-serif";
    ctx.fillText("DANGER THRESHOLD (85%)", left + 8, yDanger - 4);

    ctx.restore();
  }
};

function initChart() {
  const ctx = document.getElementById("waterChart").getContext("2d");

  waterChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: [],
      datasets: [
        {
          label: "Water Level (%)",
          data: [],
          borderColor: "#2563eb",
          backgroundColor: "rgba(37, 99, 235, 0.12)",
          borderWidth: 2.5,
          tension: 0.35,
          fill: true,
          pointRadius: 3,
          pointHoverRadius: 6,
          pointBackgroundColor: "#2563eb",
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: {
        duration: 400,
      },
      scales: {
        x: {
          grid: {
            color: "rgba(226, 232, 240, 0.6)",
          },
          ticks: {
            font: { size: 11 },
            color: "#64748b",
            maxRotation: 0,
            autoSkip: true,
            maxTicksLimit: 8,
          },
        },
        y: {
          min: 0,
          max: 100,
          grid: {
            color: "rgba(226, 232, 240, 0.6)",
          },
          ticks: {
            font: { size: 11 },
            color: "#64748b",
            callback: (val) => `${val}%`,
            stepSize: 20,
          },
        },
      },
      plugins: {
        legend: {
          display: false,
        },
        tooltip: {
          callbacks: {
            label: (context) => `Water Level: ${context.parsed.y.toFixed(1)}%`,
          },
        },
      },
    },
    plugins: [thresholdLinesPlugin],
  });
}

/**
 * Appends a new data point to the line chart and maintains MAX_CHART_POINTS limit.
 */
function updateChart(timeLabel, waterPercent) {
  if (!waterChart) return;

  const labels = waterChart.data.labels;
  const data = waterChart.data.datasets[0].data;

  // Add new point
  labels.push(timeLabel);
  data.push(waterPercent);

  // Keep latest 50 points
  if (labels.length > MAX_CHART_POINTS) {
    labels.shift();
    data.shift();
  }

  // Dynamically change line color if in warning/danger
  if (waterPercent >= 85) {
    waterChart.data.datasets[0].borderColor = "#ef4444";
    waterChart.data.datasets[0].pointBackgroundColor = "#ef4444";
    waterChart.data.datasets[0].backgroundColor = "rgba(239, 68, 68, 0.18)";
  } else if (waterPercent >= 60) {
    waterChart.data.datasets[0].borderColor = "#f59e0b";
    waterChart.data.datasets[0].pointBackgroundColor = "#f59e0b";
    waterChart.data.datasets[0].backgroundColor = "rgba(245, 158, 11, 0.18)";
  } else {
    waterChart.data.datasets[0].borderColor = "#2563eb";
    waterChart.data.datasets[0].pointBackgroundColor = "#2563eb";
    waterChart.data.datasets[0].backgroundColor = "rgba(37, 99, 235, 0.12)";
  }

  waterChart.update("none"); // "none" mode for ultra-smooth live graph streaming
}

/**
 * Prepopulates chart with past readings fetched on initial load.
 */
function populateChartHistory(historyList) {
  if (!waterChart || !Array.isArray(historyList)) return;

  const slice = historyList.slice(-MAX_CHART_POINTS);
  waterChart.data.labels = slice.map((item) => formatTimestampShort(item.timestamp));
  waterChart.data.datasets[0].data = slice.map((item) => item.water_level_percent);
  waterChart.update();
}

// =============================================================================
// 4. Formatting Utilities
// =============================================================================

function formatTimestampShort(isoStr) {
  if (!isoStr) return "--:--:--";
  try {
    const d = new Date(isoStr);
    return isNaN(d.getTime()) ? isoStr.slice(11, 19) : d.toLocaleTimeString();
  } catch (e) {
    return isoStr.slice(11, 19) || "--:--:--";
  }
}

function formatRelativeTime(secondsAgo) {
  if (secondsAgo === null || secondsAgo === undefined) return "Never";
  if (secondsAgo < 2) return "Just now";
  if (secondsAgo < 60) return `${Math.floor(secondsAgo)}s ago`;
  const mins = Math.floor(secondsAgo / 60);
  return `${mins}m ago`;
}

// =============================================================================
// 5. UI Render Functions
// =============================================================================

/**
 * Sets the active LED indicator bulb.
 * Only ONE LED is active at a time!
 * Choices: "GREEN", "YELLOW", "RED", or null (none active)
 */
function setActiveLED(activeLed) {
  // Clear all active classes first
  ledItemGreen.classList.remove("active-green");
  ledItemYellow.classList.remove("active-yellow");
  ledItemRed.classList.remove("active-red");

  if (activeLed === "GREEN") {
    ledItemGreen.classList.add("active-green");
  } else if (activeLed === "YELLOW") {
    ledItemYellow.classList.add("active-yellow");
  } else if (activeLed === "RED") {
    ledItemRed.classList.add("active-red");
  }
}

/**
 * Updates the Alert Banner text and styling.
 */
function setAlertBanner(type, title, message, timeStr = "") {
  alertBanner.className = `alert-banner alert-${type}`;

  const iconMap = {
    normal: "✅",
    warning: "⚠️",
    danger: "🚨",
    offline: "🔌",
    info: "ℹ️",
  };

  alertIcon.textContent = iconMap[type] || "ℹ️";
  alertTitle.textContent = title;
  alertMessage.textContent = message;
  alertTimestamp.textContent = timeStr || new Date().toLocaleTimeString();
}

/**
 * Renders the dashboard when ESP32 is offline or disconnected.
 */
function renderOfflineState(statusData) {
  connectionBadge.className = "badge badge-offline";
  connectionText.textContent = "ESP32 OFFLINE";

  setActiveLED(null); // All LEDs unlit when offline
  stopBuzzerTone();

  const lastSeenText = statusData && statusData.last_seen_seconds_ago !== null
    ? `Last reading received ${formatRelativeTime(statusData.last_seen_seconds_ago)}.`
    : "No telemetry data has been received yet.";

  setAlertBanner(
    "offline",
    "ESP32 Connection Lost",
    `ESP32 is offline. ${lastSeenText} Check device power and Wi-Fi connection.`,
    statusData?.latest_timestamp ? formatTimestampShort(statusData.latest_timestamp) : ""
  );

  if (valLastSeen) {
    valLastSeen.textContent = statusData ? formatRelativeTime(statusData.last_seen_seconds_ago) : "Offline";
  }
}

/**
 * Renders full sensor data onto cards, vertical water tank, and indicators.
 */
function renderDashboard(reading, statusData) {
  // 1. Connection Badge
  connectionBadge.className = "badge badge-online";
  connectionText.textContent = "ESP32 ONLINE";

  // Validate incoming fields exist and are valid numbers
  const waterPercent = Number(reading.water_level_percent);
  const waterDepth = Number(reading.water_depth_cm);
  const distance = Number(reading.distance_cm);
  const riseRate = Number(reading.water_rise_rate);
  const rainRaw = Number(reading.rain_value);
  const rainDetected = Boolean(reading.rain_detected);
  const floatActive = Boolean(reading.float_activated);

  if (isNaN(waterPercent) || isNaN(waterDepth) || isNaN(distance)) {
    // Sensor Error condition
    setActiveLED(null);
    setAlertBanner("warning", "SENSOR ERROR", "Invalid or missing sensor data received from ESP32.");
    valPercent.textContent = "ERR";
    valDepth.textContent = "--";
    valDistance.textContent = "--";
    waterFill.style.height = "0%";
    return;
  }

  // Check if sensor reading indicates a hardware sensor error (e.g. timeout / -1.0)
  const isSensorError = reading.status === "SENSOR_ERROR" || waterPercent < 0 || distance < 0;

  if (isSensorError && !floatActive) {
    setActiveLED(null);
    waterFill.style.height = "0%";
    valPercent.textContent = "ERR";
    valDepth.textContent = "--";
    valDistance.textContent = "--";
    const timeShort = formatTimestampShort(reading.timestamp);
    setAlertBanner("warning", "SENSOR ERROR", "Ultrasonic echo timeout or reading outside valid range.", timeShort);
    
    // Still render rain and float status cards
    renderSensorCards(rainDetected, rainRaw, floatActive, riseRate, timeShort, statusData);
    stopBuzzerTone();
    return;
  }

  // 2. Numerical Values in Water Tank Card
  valPercent.textContent = waterPercent.toFixed(1);
  valDepth.textContent = waterDepth.toFixed(2);
  valDistance.textContent = distance.toFixed(2);

  // 3. Vertical Tank Visualization
  const clampedPercent = Math.max(0, Math.min(100, waterPercent));
  waterFill.style.height = `${clampedPercent}%`;

  // 4. Alert & Indicator Priority Logic:
  //    - DANGER:  water_level_percent >= 85 OR float_activated == true
  //    - WARNING: water_level_percent >= 60 AND water_level_percent < 85
  //    - NORMAL:  water_level_percent < 60
  const isDanger = (waterPercent >= 85) || floatActive;
  const isWarning = !isDanger && (waterPercent >= 60);
  const isNormal = !isDanger && !isWarning;

  const timeShort = formatTimestampShort(reading.timestamp);

  if (isDanger) {
    // RED LED
    setActiveLED("RED");
    waterFill.className = "water-fill water-danger";

    const reason = floatActive && waterPercent < 85
      ? "Emergency float switch activated!"
      : "DANGER: Critical water level detected!";

    setAlertBanner("danger", "CRITICAL FLOOD WARNING", reason, timeShort);
  } else if (isWarning) {
    // YELLOW LED
    setActiveLED("YELLOW");
    waterFill.className = "water-fill water-warning";
    setAlertBanner("warning", "Water Level Rising", "Warning: Water level is rising. Monitoring actively.", timeShort);
  } else {
    // GREEN LED
    setActiveLED("GREEN");
    waterFill.className = "water-fill water-normal";
    setAlertBanner("normal", "System Normal", "Water level is normal. No immediate flood risk detected.", timeShort);
  }

  // 5. Sensor Status Cards
  renderSensorCards(rainDetected, rainRaw, floatActive, riseRate, timeShort, statusData);

  // 6. Sound Alert Check
  checkAlarmCondition();
}

/**
 * Helper to update sensor status cards
 */
function renderSensorCards(rainDetected, rainRaw, floatActive, riseRate, timeShort, statusData) {
  // Rain Sensor
  if (rainDetected) {
    valRainDetected.textContent = "DETECTED";
    valRainDetected.className = "sensor-state state-warn";
  } else {
    valRainDetected.textContent = "DRY";
    valRainDetected.className = "sensor-state state-good";
  }
  valRainRaw.textContent = Number(rainRaw).toFixed(0);

  // Float Switch
  if (floatActive) {
    valFloatState.textContent = "ACTIVATED";
    valFloatState.className = "sensor-state state-danger";
    valFloatSub.textContent = "Switch Tripped (High Water)";
  } else {
    valFloatState.textContent = "NORMAL";
    valFloatState.className = "sensor-state state-good";
    valFloatSub.textContent = "Contact Open (OK)";
  }

  // Water Rise Rate
  const sign = riseRate > 0 ? "+" : "";
  valRiseRate.textContent = `${sign}${Number(riseRate).toFixed(2)} %/s`;
  if (riseRate > 0.5) {
    valRiseRate.className = "sensor-state state-warn";
  } else {
    valRiseRate.className = "sensor-state";
  }

  // Last Updated Time
  valLastUpdated.textContent = timeShort;
  valLastSeen.textContent = formatRelativeTime(statusData ? statusData.last_seen_seconds_ago : 0);
}

// =============================================================================
// 6. Polling & Network Requests
// =============================================================================

/**
 * Periodically polls FastAPI for status and latest reading every 2 seconds.
 */
async function fetchDashboardData() {
  try {
    // 1. Fetch system status (online check)
    const statusRes = await fetch(`${API_BASE}/api/status`);
    if (!statusRes.ok) throw new Error(`Status API error: ${statusRes.status}`);
    const statusData = await statusRes.json();

    state.isOnline = Boolean(statusData.online);

    if (!state.isOnline) {
      renderOfflineState(statusData);
      return;
    }

    // 2. Fetch latest reading
    const latestRes = await fetch(`${API_BASE}/api/latest`);
    if (!latestRes.ok) throw new Error(`Latest API error: ${latestRes.status}`);
    const latestData = await latestRes.json();

    if (!latestData.reading) {
      renderOfflineState(statusData);
      setAlertBanner("info", "Awaiting Data", "Server is running. Waiting for first transmission from ESP32.");
      return;
    }

    const reading = latestData.reading;
    const isNewReading = !state.latestReading || state.latestReading.id !== reading.id;
    state.latestReading = reading;

    // Render UI
    renderDashboard(reading, statusData);

    // Update live line graph with new point (only for valid non-error readings)
    if (isNewReading && reading.water_level_percent >= 0) {
      const timeLabel = formatTimestampShort(reading.timestamp);
      updateChart(timeLabel, reading.water_level_percent);
    }
  } catch (error) {
    console.error("Dashboard poll failed:", error);
    renderOfflineState({
      online: false,
      last_seen_seconds_ago: null,
      latest_timestamp: null,
    });
    setAlertBanner(
      "offline",
      "Server Unreachable",
      "Could not connect to FastAPI server at /api. Ensure backend is running."
    );
  }
}

/**
 * Initial load: sets up Chart, loads history, and starts polling.
 */
async function initializeDashboard() {
  initChart();

  // Load past history to populate the chart initially
  try {
    const historyRes = await fetch(`${API_BASE}/api/history?limit=50`);
    if (historyRes.ok) {
      const historyList = await historyRes.json();
      populateChartHistory(historyList);
    }
  } catch (err) {
    console.warn("Could not pre-fetch history:", err);
  }

  // Initial poll
  fetchDashboardData();

  // Poll every 2 seconds
  setInterval(fetchDashboardData, POLL_INTERVAL_MS);
}

// Start application once DOM is ready
document.addEventListener("DOMContentLoaded", initializeDashboard);

