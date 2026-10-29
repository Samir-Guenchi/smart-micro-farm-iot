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

constexpr char NODE_ID[] = "coop-1";

constexpr uint8_t REED_SWITCH_PIN = 27;
constexpr uint32_t DEBOUNCE_INTERVAL_MS = 50;
constexpr uint32_t TELEMETRY_INTERVAL_MS = 60000;
constexpr uint32_t MQTT_RECONNECT_INTERVAL_MS = 5000;
constexpr uint32_t SNTP_RETRY_INTERVAL_MS = 30000;
constexpr time_t NTP_VALID_AFTER = 1704067200;  // 2024-01-01T00:00:00Z
constexpr uint8_t DOOR_EVENT_QUEUE_CAPACITY = 16;
