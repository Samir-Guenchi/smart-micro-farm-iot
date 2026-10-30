#include <Arduino.h>
#include <ArduinoJson.h>
#include <Adafruit_SHT31.h>
#include <MQTTClient.h>
#include <WiFi.h>
#include <Wire.h>
#include <esp_system.h>
#include <time.h>

#include "secrets.h"
#include "config.h"
#include "GreenLoopMqtt.h"

enum class PumpReason : uint8_t { Automatic, Manual, Timeout };

struct PumpEvent {
  const char* state;
  PumpReason reason;
};

WiFiClient networkClient;
MQTTClient mqttClient(256);
Adafruit_SHT31 sht31;

bool sht31Available = false;
bool pumpRunning = false;
bool automaticWateringArmed = true;
bool telemetryDue = true;
bool pendingPumpRequest = false;
bool soilReadingAvailable = false;
bool sntpRequested = false;
uint32_t pendingPumpDurationS = 0;
uint32_t pumpStartedAtMs = 0;
uint32_t pumpDurationS = 0;
uint32_t lastSensorAtMs = 0;
uint32_t lastTelemetryAtMs = 0;
uint32_t lastMqttAttemptAtMs = 0;
uint32_t lastSntpRequestAtMs = 0;
uint32_t droppedPumpEventCount = 0;
uint8_t pumpEventHead = 0;
uint8_t pumpEventTail = 0;
uint8_t pumpEventCount = 0;
PumpEvent pumpEventQueue[PUMP_EVENT_QUEUE_CAPACITY];
float soilMoisturePct = 0.0F;
float airTempC = NAN;
float airHumidityPct = NAN;

const char* reasonName(PumpReason reason) {
  switch (reason) {
    case PumpReason::Automatic:
      return "automatic";
    case PumpReason::Manual:
      return "manual";
    case PumpReason::Timeout:
      return "timeout";
  }
  return "unknown";
}

uint32_t unixTimestamp() {
  const time_t now = time(nullptr);
  return static_cast<uint32_t>(now);
}

bool timeSynchronized() {
  // Reject the ESP32's unset epoch so shared event and telemetry timestamps are Unix seconds.
  return time(nullptr) >= 1704067200;  // 2024-01-01T00:00:00Z
}

void requestSntpTime(uint32_t nowMs) {
  if (timeSynchronized() ||
      (sntpRequested && uint32_t(nowMs - lastSntpRequestAtMs) < SNTP_RETRY_INTERVAL_MS)) {
    return;
  }
  configTime(0, 0, "pool.ntp.org", "time.nist.gov");
  lastSntpRequestAtMs = nowMs;
  sntpRequested = true;
}

void writeRelay(bool on) {
  const bool level = RELAY_ACTIVE_HIGH ? on : !on;
  digitalWrite(PUMP_RELAY_PIN, level ? HIGH : LOW);
}

float soilPercentFromAdc(int rawAdc) {
  const float span = static_cast<float>(SOIL_ADC_WET - SOIL_ADC_DRY);
  if (span == 0.0F) {
    return 0.0F;
  }
  const float percent = (static_cast<float>(rawAdc - SOIL_ADC_DRY) * 100.0F) / span;
  return constrain(percent, 0.0F, 100.0F);
}

void enqueuePumpEvent(const char* state, PumpReason reason) {
  if (pumpEventCount == PUMP_EVENT_QUEUE_CAPACITY) {
    ++droppedPumpEventCount;
    Serial.printf("Pump event queue full; dropped newest event (%lu total).\n",
                  static_cast<unsigned long>(droppedPumpEventCount));
    return;
  }

  pumpEventQueue[pumpEventTail] = {state, reason};
  pumpEventTail = (pumpEventTail + 1) % PUMP_EVENT_QUEUE_CAPACITY;
  ++pumpEventCount;
}

void flushPumpEvents() {
  if (!mqttClient.connected() || !timeSynchronized()) {
    return;
  }

  while (pumpEventCount > 0) {
    const PumpEvent& event = pumpEventQueue[pumpEventHead];
    JsonDocument payload;
    payload["type"] = "pump";
    payload["state"] = event.state;
    payload["reason"] = reasonName(event.reason);
    if (!greenloop::publishEvent(mqttClient, NODE_ID, unixTimestamp(),
                                 payload.as<JsonObjectConst>())) {
      return;
    }
    pumpEventHead = (pumpEventHead + 1) % PUMP_EVENT_QUEUE_CAPACITY;
    --pumpEventCount;
  }
}

void publishPumpEvent(const char* state, PumpReason reason) {
  enqueuePumpEvent(state, reason);
  flushPumpEvents();
}

bool startPump(uint32_t durationSeconds, PumpReason reason, uint32_t nowMs) {
  if (pumpRunning || durationSeconds == 0) {
    return false;
  }

  pumpDurationS = min(durationSeconds, MAX_PUMP_S);
  pumpStartedAtMs = nowMs;
  pumpRunning = true;
  writeRelay(true);
  publishPumpEvent("started", reason);
  return true;
}

void stopPump(PumpReason reason) {
  if (!pumpRunning) {
    return;
  }

  writeRelay(false);
  pumpRunning = false;
  publishPumpEvent("stopped", reason);
}

void updatePump(uint32_t nowMs, float moisturePct) {
  if (pumpRunning && uint32_t(nowMs - pumpStartedAtMs) >= pumpDurationS * 1000UL) {
    stopPump(PumpReason::Timeout);
  }

  if (moisturePct >= MOISTURE_THRESHOLD_PCT + MOISTURE_HYSTERESIS_PCT) {
    automaticWateringArmed = true;
  }

  if (automaticWateringArmed && !pumpRunning && moisturePct < MOISTURE_THRESHOLD_PCT) {
    if (startPump(AUTO_PUMP_S, PumpReason::Automatic, nowMs)) {
      automaticWateringArmed = false;
    }
  }
}

void readSensors(uint32_t nowMs) {
  if (soilReadingAvailable && uint32_t(nowMs - lastSensorAtMs) < SENSOR_INTERVAL_MS) {
    return;
  }
  lastSensorAtMs = nowMs;
  soilMoisturePct = soilPercentFromAdc(analogRead(SOIL_SENSOR_PIN));
  soilReadingAvailable = true;

  if (!sht31Available) {
    return;
  }
  const float temperature = sht31.readTemperature();
  const float humidity = sht31.readHumidity();
  airTempC = isnan(temperature) ? NAN : temperature;
  airHumidityPct = isnan(humidity) ? NAN : humidity;
}

void publishTelemetry(uint32_t nowMs) {
  if (!mqttClient.connected() || !timeSynchronized() ||
      (!telemetryDue && uint32_t(nowMs - lastTelemetryAtMs) < TELEMETRY_INTERVAL_MS)) {
    return;
  }

  JsonDocument metrics;
  metrics["soil_moisture_pct"] = soilMoisturePct;
  if (!isnan(airTempC)) {
    metrics["air_temp_c"] = airTempC;
  }
  if (!isnan(airHumidityPct)) {
    metrics["air_humidity_pct"] = airHumidityPct;
  }
  metrics["pump_on"] = pumpRunning;
  if (greenloop::publishTelemetry(mqttClient, NODE_ID, unixTimestamp(),
                                  metrics.as<JsonObjectConst>())) {
    lastTelemetryAtMs = nowMs;
    telemetryDue = false;
  }
}

void queuePumpCommand(String &topic, String &payload) {
  if (topic != greenloop::topicFor(NODE_ID, greenloop::Channel::Command)) {
    return;
  }

  JsonDocument command;
  if (deserializeJson(command, payload) != DeserializationError::Ok || !command.is<JsonObject>()) {
    return;
  }
  JsonObject object = command.as<JsonObject>();
  JsonVariant duration = object["duration_s"];
  if (object.size() != 2 || !object["action"].is<const char*>() ||
      strcmp(object["action"].as<const char*>(), "pump") != 0 ||
      !duration.is<uint32_t>()) {
    return;
  }

  const uint32_t requestedSeconds = duration.as<uint32_t>();
  // Admission is decided at receipt: an active cycle cannot be extended later.
  if (requestedSeconds == 0 || pumpRunning || pendingPumpRequest) {
    return;
  }
  pendingPumpDurationS = min(requestedSeconds, MAX_PUMP_S);
  pendingPumpRequest = true;
}

void connectMqtt(uint32_t nowMs) {
  if (WiFi.status() != WL_CONNECTED || mqttClient.connected() ||
      uint32_t(nowMs - lastMqttAttemptAtMs) < MQTT_RECONNECT_INTERVAL_MS) {
    return;
  }
  lastMqttAttemptAtMs = nowMs;
  greenloop::configureOfflineWill(mqttClient, NODE_ID);
  if (mqttClient.connect(NODE_ID, MQTT_USERNAME, MQTT_PASSWORD)) {
    greenloop::publishStatus(mqttClient, NODE_ID, "online");
    greenloop::subscribeCommands(mqttClient, NODE_ID);
    telemetryDue = true;
  }
}

void disconnectMqttForPlannedShutdown() {
  if (mqttClient.connected()) {
    greenloop::publishStatus(mqttClient, NODE_ID, "offline");
    mqttClient.disconnect();
  }
}

void setup() {
  writeRelay(false);  // Preload the inactive level before enabling the relay output.
  pinMode(PUMP_RELAY_PIN, OUTPUT);
  pinMode(SOIL_SENSOR_PIN, INPUT);
  Serial.begin(115200);

  Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN);
  sht31Available = sht31.begin(0x44);

  mqttClient.begin(MQTT_HOST, MQTT_PORT, networkClient);
  mqttClient.onMessage(queuePumpCommand);
  esp_register_shutdown_handler(disconnectMqttForPlannedShutdown);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
}

void loop() {
  const uint32_t nowMs = millis();
  readSensors(nowMs);
  if (soilReadingAvailable) {
    updatePump(nowMs, soilMoisturePct);
  }

  if (pendingPumpRequest) {
    const uint32_t requestedDurationS = pendingPumpDurationS;
    pendingPumpRequest = false;
    startPump(requestedDurationS, PumpReason::Manual, nowMs);
  }

  if (WiFi.status() == WL_CONNECTED) {
    requestSntpTime(nowMs);
    connectMqtt(nowMs);
  } else {
    sntpRequested = false;
  }
  if (mqttClient.connected()) {
    mqttClient.loop();
    flushPumpEvents();
    publishTelemetry(nowMs);
  }
}
