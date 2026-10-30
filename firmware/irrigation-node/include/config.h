#pragma once

#include <Arduino.h>

// Network settings are normally supplied by the untracked secrets.h file.
#ifndef WIFI_SSID
#define WIFI_SSID ""
#endif
#ifndef WIFI_PASSWORD
#define WIFI_PASSWORD ""
#endif
#ifndef MQTT_HOST
#define MQTT_HOST ""
#endif
#ifndef MQTT_PORT
#define MQTT_PORT 1883
#endif
#ifndef MQTT_USERNAME
#define MQTT_USERNAME ""
#endif
#ifndef MQTT_PASSWORD
#define MQTT_PASSWORD ""
#endif

constexpr char NODE_ID[] = "irrigation-1";

constexpr uint8_t SOIL_SENSOR_PIN = 34;
constexpr uint8_t FLOW_SENSOR_PIN = 18;
constexpr uint8_t I2C_SDA_PIN = 21;
constexpr uint8_t I2C_SCL_PIN = 22;
constexpr uint8_t PUMP_RELAY_PIN = 26;

// Starting YF-S201 estimate; replace with the measured bucket-calibration result.
constexpr float FLOW_PULSES_PER_LITER = 450.0F;
static_assert(FLOW_PULSES_PER_LITER > 0.0F, "Flow calibration must be positive.");

// Record the raw ADC readings with the probe dry and immersed at its final depth.
constexpr int SOIL_ADC_DRY = 3000;
constexpr int SOIL_ADC_WET = 1300;

// Change RELAY_ACTIVE_HIGH to false for relay boards that energize on a LOW input.
constexpr bool RELAY_ACTIVE_HIGH = true;
constexpr uint32_t MAX_PUMP_S = 900;
constexpr uint32_t AUTO_PUMP_S = 60;
constexpr float MOISTURE_THRESHOLD_PCT = 35.0F;
constexpr float MOISTURE_HYSTERESIS_PCT = 5.0F;

constexpr uint32_t SENSOR_INTERVAL_MS = 2000;
constexpr uint32_t TELEMETRY_INTERVAL_MS = 60000;
constexpr uint32_t MQTT_RECONNECT_INTERVAL_MS = 5000;
constexpr uint32_t SNTP_RETRY_INTERVAL_MS = 30000;
constexpr uint8_t PUMP_EVENT_QUEUE_CAPACITY = 8;
