#include <Arduino.h>
#include <ArduinoJson.h>
#include <MQTTClient.h>
#include <WiFi.h>
#include <esp_system.h>
#include <time.h>

#include "config.h"
#include "secrets.h"
#include "GreenLoopMqtt.h"

enum class DoorState : uint8_t { Closed, Open };

struct DoorEvent {
  DoorState state;
  uint32_t ts;
};

WiFiClient networkClient;
MQTTClient mqttClient(256);

DoorState stableDoorState = DoorState::Closed;
DoorState candidateDoorState = DoorState::Closed;
bool candidateInitialized = false;
bool stableStateAvailable = false;
uint32_t candidateSinceMs = 0;
uint32_t lastTelemetryAtMs = 0;
uint32_t lastMqttAttemptAtMs = 0;
uint32_t lastSntpRequestAtMs = 0;
bool telemetryDue = false;
bool sntpRequested = false;
uint32_t droppedDoorEventCount = 0;
uint8_t doorEventHead = 0;
uint8_t doorEventTail = 0;
uint8_t doorEventCount = 0;
DoorEvent doorEventQueue[DOOR_EVENT_QUEUE_CAPACITY];
bool doorEventNeedsEstimate[DOOR_EVENT_QUEUE_CAPACITY];

uint32_t unixTimestamp() {
  return static_cast<uint32_t>(time(nullptr));
}

bool timeSynchronized() {
  return time(nullptr) >= NTP_VALID_AFTER;
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

DoorState readDoorState() {
  // The external pull-up makes an open reed circuit HIGH; the magnet closes it to ground.
  return digitalRead(REED_SWITCH_PIN) == LOW ? DoorState::Closed : DoorState::Open;
}

void enqueueDoorEvent(DoorState state, uint32_t capturedAt, bool needsEstimate) {
  if (doorEventCount == DOOR_EVENT_QUEUE_CAPACITY) {
    doorEventHead = (doorEventHead + 1) % DOOR_EVENT_QUEUE_CAPACITY;
    --doorEventCount;
    ++droppedDoorEventCount;
    Serial.printf("Door event queue full; discarded oldest transition (%lu total).\n",
                  static_cast<unsigned long>(droppedDoorEventCount));
  }

  doorEventQueue[doorEventTail] = {state, capturedAt};
  doorEventNeedsEstimate[doorEventTail] = needsEstimate;
  doorEventTail = (doorEventTail + 1) % DOOR_EVENT_QUEUE_CAPACITY;
  ++doorEventCount;
}

void sampleDoor(uint32_t nowMs) {
  const DoorState reading = readDoorState();
  if (!candidateInitialized || reading != candidateDoorState) {
    candidateDoorState = reading;
    candidateSinceMs = nowMs;
    candidateInitialized = true;
    return;
  }

  if (uint32_t(nowMs - candidateSinceMs) < DEBOUNCE_INTERVAL_MS) {
    return;
  }

  if (!stableStateAvailable) {
    // Establish the initial state only after a full debounce interval; it is not an event.
    stableDoorState = candidateDoorState;
    stableStateAvailable = true;
    telemetryDue = true;
    return;
  }

  if (candidateDoorState != stableDoorState) {
    stableDoorState = candidateDoorState;
    const bool needsEstimate = !timeSynchronized();
    // Before SNTP, retain the monotonic acceptance time for later Unix-time estimation.
    enqueueDoorEvent(stableDoorState, needsEstimate ? nowMs : unixTimestamp(), needsEstimate);
  }
}

void flushDoorEvents() {
  if (!mqttClient.connected() || !timeSynchronized()) {
    return;
  }

  // Use one clock pair for every pre-SNTP event drained in this pass.
  const uint32_t anchorMs = millis();
  const uint32_t anchorUnix = unixTimestamp();
  while (doorEventCount > 0) {
    DoorEvent& event = doorEventQueue[doorEventHead];
    if (doorEventNeedsEstimate[doorEventHead]) {
      // Estimate capture-time Unix seconds from this single synchronized clock anchor.
      event.ts = anchorUnix - uint32_t(anchorMs - event.ts) / 1000UL;
      doorEventNeedsEstimate[doorEventHead] = false;
    }
    JsonDocument fields;
    fields["type"] = "door";
    fields["state"] = event.state == DoorState::Open ? "open" : "closed";
    if (!greenloop::publishEvent(mqttClient, NODE_ID, event.ts,
                                 fields.as<JsonObjectConst>())) {
      return;
    }
    doorEventHead = (doorEventHead + 1) % DOOR_EVENT_QUEUE_CAPACITY;
    --doorEventCount;
  }
}

void publishTelemetry(uint32_t nowMs) {
  if (!mqttClient.connected() || !stableStateAvailable || !timeSynchronized() ||
      (!telemetryDue && uint32_t(nowMs - lastTelemetryAtMs) < TELEMETRY_INTERVAL_MS)) {
    return;
  }

  JsonDocument metrics;
  metrics["door_open"] = stableDoorState == DoorState::Open ? 1 : 0;
  if (greenloop::publishTelemetry(mqttClient, NODE_ID, unixTimestamp(),
                                  metrics.as<JsonObjectConst>())) {
    lastTelemetryAtMs = nowMs;
    telemetryDue = false;
  }
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
  Serial.begin(115200);
  pinMode(REED_SWITCH_PIN, INPUT);  // External pull-up is required by the wiring.

  mqttClient.begin(MQTT_HOST, MQTT_PORT, networkClient);
  esp_register_shutdown_handler(disconnectMqttForPlannedShutdown);

  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
}

void loop() {
  const uint32_t nowMs = millis();
  sampleDoor(nowMs);

  if (WiFi.status() == WL_CONNECTED) {
    requestSntpTime(nowMs);
    connectMqtt(nowMs);
  } else {
    sntpRequested = false;
  }

  if (mqttClient.connected()) {
    mqttClient.loop();
    flushDoorEvents();
    publishTelemetry(nowMs);
  }
}
