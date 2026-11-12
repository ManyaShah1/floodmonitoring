/*
  ESP32 Flood Monitoring System - USB Serial Version
  Board: ESP32 Dev Module
  
  Communication: USB Serial (115200 baud) directly to Python Bridge.
  No Wi-Fi credentials or IP configuration needed!
*/

#include <Arduino.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

// ==================================================
// 1. PIN DEFINITIONS
// ==================================================

// Ultrasonic sensor
#define TRIG_PIN 17
#define ECHO_PIN 16

// LCD (I2C)
#define LCD_SDA 21
#define LCD_SCL 22

// Float switch
#define FLOAT_PIN 33

// Rain sensor (Analog)
#define RAIN_PIN 34

// Buzzer
#define BUZZER_PIN 25

// Physical Status LEDs
#define GREEN_LED 26
#define YELLOW_LED 27
#define RED_LED 14


// ==================================================
// 2. TANK AND ALERT CONFIGURATION
// ==================================================

// Total height of your container/tank in cm (sensor face to bottom)
const float TANK_HEIGHT_CM = 30.0;

const float WARNING_LEVEL = 60.0;
const float DANGER_LEVEL = 85.0;

// Rain sensor threshold (typical 0-4095 ADC)
const int RAIN_THRESHOLD = 2000;

// Most rain sensor modules give lower analog values when wet
const bool RAIN_WET_IS_LOWER = true;

// Float switch connected between GPIO33 and GND (internal pull-up)
const bool FLOAT_ACTIVE_LOW = true;

// Buzzer polarity
#define BUZZER_ON HIGH
#define BUZZER_OFF LOW

// LCD address: commonly 0x27 or 0x3F for 16x2 I2C displays
LiquidCrystal_I2C lcd(0x27, 16, 2);


// ==================================================
// 3. GLOBAL VARIABLES
// ==================================================

float waterDistance = -1.0;
float waterDepth = -1.0;
float waterLevelPercent = -1.0;

float waterRiseRate = 0.0;
float previousWaterLevel = -1.0;

int rainValue = 0;

bool rainDetected = false;
bool floatActivated = false;

String systemStatus = "SENSOR_ERROR";

unsigned long previousMillis = 0;
unsigned long previousRiseMillis = 0;

const unsigned long UPDATE_INTERVAL = 2000; // 2 seconds


// ==================================================
// 4. READ ULTRASONIC SENSOR
// ==================================================

float readDistance() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);

  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);

  digitalWrite(TRIG_PIN, LOW);

  unsigned long duration = pulseIn(ECHO_PIN, HIGH, 30000); // 30ms timeout (~5m max)

  if (duration == 0) {
    return -1.0;
  }

  float distance = (duration * 0.0343) / 2.0;

  if (distance < 2.0 || distance > 400.0) {
    return -1.0;
  }

  return distance;
}


// ==================================================
// 5. CALCULATE WATER LEVEL
// ==================================================

void calculateWaterLevel() {
  waterDistance = readDistance();

  // Reject readings outside the tank
  if (waterDistance < 0 || waterDistance > TANK_HEIGHT_CM) {
    waterDepth = -1.0;
    waterLevelPercent = -1.0;
    return;
  }

  waterDepth = TANK_HEIGHT_CM - waterDistance;
  waterDepth = constrain(waterDepth, 0.0, TANK_HEIGHT_CM);
  waterLevelPercent = (waterDepth / TANK_HEIGHT_CM) * 100.0;
}


// ==================================================
// 6. READ FLOAT SWITCH
// ==================================================

void readFloatSwitch() {
  int state = digitalRead(FLOAT_PIN);

  if (FLOAT_ACTIVE_LOW) {
    floatActivated = (state == LOW);
  } else {
    floatActivated = (state == HIGH);
  }
}


// ==================================================
// 7. READ RAIN SENSOR
// ==================================================

void readRainSensor() {
  long total = 0;

  for (int i = 0; i < 5; i++) {
    total += analogRead(RAIN_PIN);
    delay(5);
  }

  rainValue = total / 5;

  if (RAIN_WET_IS_LOWER) {
    rainDetected = rainValue < RAIN_THRESHOLD;
  } else {
    rainDetected = rainValue > RAIN_THRESHOLD;
  }
}


// ==================================================
// 8. CALCULATE WATER RISE RATE
// ==================================================

void calculateRiseRate() {
  unsigned long now = millis();

  if (waterLevelPercent < 0) {
    waterRiseRate = 0;
    return;
  }

  if (previousWaterLevel >= 0 && previousRiseMillis > 0) {
    float elapsedSeconds = (now - previousRiseMillis) / 1000.0;

    if (elapsedSeconds > 0) {
      waterRiseRate = (waterLevelPercent - previousWaterLevel) / elapsedSeconds;
    }
  }

  previousWaterLevel = waterLevelPercent;
  previousRiseMillis = now;
}


// ==================================================
// 9. DETERMINE SYSTEM STATUS
// ==================================================

void determineStatus() {
  // Float switch has emergency priority
  if (floatActivated) {
    systemStatus = "DANGER";
  } else if (waterLevelPercent < 0) {
    systemStatus = "SENSOR_ERROR";
  } else if (waterLevelPercent >= DANGER_LEVEL) {
    systemStatus = "DANGER";
  } else if (waterLevelPercent >= WARNING_LEVEL) {
    systemStatus = "WARNING";
  } else {
    systemStatus = "NORMAL";
  }
}


// ==================================================
// 10. CONTROL PHYSICAL LEDS AND BUZZER
// ==================================================

void controlAlerts() {
  digitalWrite(GREEN_LED, LOW);
  digitalWrite(YELLOW_LED, LOW);
  digitalWrite(RED_LED, LOW);

  if (systemStatus == "DANGER") {
    digitalWrite(RED_LED, HIGH);
    digitalWrite(BUZZER_PIN, BUZZER_ON);
  } else if (systemStatus == "WARNING") {
    digitalWrite(YELLOW_LED, HIGH);
    digitalWrite(BUZZER_PIN, BUZZER_OFF);
  } else if (systemStatus == "NORMAL") {
    digitalWrite(GREEN_LED, HIGH);
    digitalWrite(BUZZER_PIN, BUZZER_OFF);
  } else {
    // Sensor Error: yellow LED
    digitalWrite(YELLOW_LED, HIGH);
    digitalWrite(BUZZER_PIN, BUZZER_OFF);
  }
}


// ==================================================
// 11. UPDATE LCD
// ==================================================

void updateLCD() {
  lcd.setCursor(0, 0);

  if (waterLevelPercent < 0) {
    lcd.print("Water: Sensor Err");
  } else {
    lcd.print("Water: ");
    lcd.print(waterLevelPercent, 1);
    lcd.print("%       ");
  }

  lcd.setCursor(0, 1);

  if (systemStatus == "DANGER") {
    lcd.print("DANGER!         ");
  } else if (systemStatus == "WARNING") {
    lcd.print("WARNING         ");
  } else if (systemStatus == "NORMAL") {
    lcd.print("NORMAL          ");
  } else {
    lcd.print("SENSOR ERROR    ");
  }
}


// ==================================================
// 12. SEND DATA OVER USB SERIAL TO PYTHON
// ==================================================

void sendDataToPython() {
  String json = "{";
  json += "\"water_level_percent\":" + String(waterLevelPercent, 2) + ",";
  json += "\"water_depth_cm\":" + String(waterDepth, 2) + ",";
  json += "\"distance_cm\":" + String(waterDistance, 2) + ",";
  json += "\"water_rise_rate\":" + String(waterRiseRate, 3) + ",";
  json += "\"rain_value\":" + String(rainValue) + ",";
  json += "\"rain_detected\":" + String(rainDetected ? "true" : "false") + ",";
  json += "\"float_activated\":" + String(floatActivated ? "true" : "false") + ",";
  json += "\"status\":\"" + systemStatus + "\"";
  json += "}";

  // Send one complete JSON line over USB
  Serial.println(json);
}


// ==================================================
// 13. SETUP
// ==================================================

void setup() {
  // Start Serial communication for USB bridge
  Serial.begin(115200);

  // Sensor pins
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  pinMode(FLOAT_PIN, INPUT_PULLUP);

  // Output pins
  pinMode(GREEN_LED, OUTPUT);
  pinMode(YELLOW_LED, OUTPUT);
  pinMode(RED_LED, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);

  digitalWrite(TRIG_PIN, LOW);
  digitalWrite(BUZZER_PIN, BUZZER_OFF);

  // ESP32 ADC configuration (12-bit = 0 to 4095)
  analogReadResolution(12);

  // LCD initialization
  Wire.begin(LCD_SDA, LCD_SCL);
  lcd.init();
  lcd.backlight();

  lcd.setCursor(0, 0);
  lcd.print("Flood Monitoring");
  lcd.setCursor(0, 1);
  lcd.print("USB Serial Mode ");
  delay(1500);
  lcd.clear();
}


// ==================================================
// 14. MAIN LOOP
// ==================================================

void loop() {
  unsigned long currentMillis = millis();

  if (currentMillis - previousMillis >= UPDATE_INTERVAL) {
    previousMillis = currentMillis;

    // Read sensors
    calculateWaterLevel();
    readFloatSwitch();
    readRainSensor();

    // Process readings
    calculateRiseRate();
    determineStatus();

    // Physical alerts and LCD
    controlAlerts();
    updateLCD();

    // Send JSON telemetry through USB cable to Python bridge
    sendDataToPython();
  }
}
