#include <Arduino.h>
#include <ArduinoJson.h>
#include <Adafruit_SHT31.h>
#include <HX711.h>
#include <MQTTClient.h>
#include <WiFi.h>
#include <Wire.h>
#include <esp_sleep.h>
#include <time.h>

#include "secrets.h"
#include "config.h"
#include "GreenLoopMqtt.h"

WiFiClient networkClient;
MQTTClient mqttClient(256);
Adafruit_SHT31 sht31;
HX711 hiveScale;

bool waitForWifi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  const uint32_t startedAt = millis();
  while (WiFi.status() != WL_CONNECTED &&
         uint32_t(millis() - startedAt) < WIFI_CONNECT_TIMEOUT_MS) {
    delay(100);
  }
  return WiFi.status() == WL_CONNECTED;
}

bool timeSynchronized() {
  return time(nullptr) >= static_cast<time_t>(NTP_VALID_AFTER);
}

bool synchronizeTime() {
  configTime(0, 0, "pool.ntp.org", "time.nist.gov");
  const uint32_t startedAt = millis();
  while (!timeSynchronized() && uint32_t(millis() - startedAt) < NTP_SYNC_TIMEOUT_MS) {
    delay(100);
  }
  return timeSynchronized();
}

bool readWeightKg(float& weightKg) {
  // wait_ready_timeout avoids the HX711 library's blocking read path when DOUT is absent.
  if (!hiveScale.wait_ready_timeout(HX711_READY_TIMEOUT_MS)) {
    Serial.println("HX711 not ready; omitting hive_weight_kg.");
    return false;
  }

  weightKg = hiveScale.get_units(HX711_SAMPLE_COUNT);
  return isfinite(weightKg);
}

void addSht31Metrics(JsonDocument& metrics) {
  const float temperature = sht31.readTemperature();
  const float humidity = sht31.readHumidity();
  if (isfinite(temperature)) {
    metrics["hive_temp_c"] = temperature;
  }
  if (isfinite(humidity)) {
    metrics["air_humidity_pct"] = humidity;
  }
}

float readBatteryVoltage() {
  // ESP32's calibrated millivolt API avoids assuming that raw ADC counts map linearly to 3.3 V.
  const uint32_t adcMillivolts = analogReadMilliVolts(BATTERY_ADC_PIN);
  return (static_cast<float>(adcMillivolts) / 1000.0F) * BATTERY_DIVIDER_RATIO;
}

void publishOneTelemetryCycle(JsonDocument& metrics) {
  if (!waitForWifi()) {
    Serial.println("Wi-Fi unavailable; skipping MQTT for this wake cycle.");
    return;
  }
  if (!synchronizeTime()) {
    Serial.println("NTP unavailable; skipping MQTT for this wake cycle.");
    return;
  }

  mqttClient.begin(MQTT_HOST, MQTT_PORT, networkClient);
  greenloop::configureOfflineWill(mqttClient, NODE_ID);
  if (!mqttClient.connect(NODE_ID, MQTT_USERNAME, MQTT_PASSWORD)) {
    Serial.println("MQTT unavailable; skipping telemetry for this wake cycle.");
    return;
  }

  greenloop::publishStatus(mqttClient, NODE_ID, "online");
  greenloop::publishTelemetry(mqttClient, NODE_ID, static_cast<uint32_t>(time(nullptr)),
                              metrics.as<JsonObjectConst>());
  // This is a planned shutdown, so replace the retained online status before disconnecting.
  greenloop::publishStatus(mqttClient, NODE_ID, "offline");
  mqttClient.disconnect();
}

[[noreturn]] void sleepUntilNextWake() {
  hiveScale.power_down();
  WiFi.disconnect(true);
  esp_sleep_enable_timer_wakeup(static_cast<uint64_t>(WAKE_PERIOD_S) * 1000000ULL);
  Serial.flush();
  esp_deep_sleep_start();
  while (true) {
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(BATTERY_ADC_PIN, INPUT);
  analogReadResolution(12);
  analogSetPinAttenuation(BATTERY_ADC_PIN, ADC_11db);

  Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN);
  const bool sht31Available = sht31.begin(0x44);
  if (!sht31Available) {
    Serial.println("SHT31 unavailable; omitting temperature and humidity metrics.");
  }

  hiveScale.begin(HX711_DOUT_PIN, HX711_SCK_PIN);
  hiveScale.set_scale(HX711_SCALE_FACTOR);
  hiveScale.set_offset(HX711_OFFSET);

  JsonDocument metrics;
  float weightKg = NAN;
  if (readWeightKg(weightKg)) {
    metrics["hive_weight_kg"] = weightKg;
  }
  if (sht31Available) {
    addSht31Metrics(metrics);
  }
  metrics["battery_v"] = readBatteryVoltage();

  publishOneTelemetryCycle(metrics);
  sleepUntilNextWake();
}

void loop() {
  // setup always enters deep sleep after a bounded one-shot wake cycle.
}
