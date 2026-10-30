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

constexpr char NODE_ID[] = "hive-1";

constexpr uint8_t HX711_DOUT_PIN = 32;
constexpr uint8_t HX711_SCK_PIN = 33;
constexpr uint8_t I2C_SDA_PIN = 21;
constexpr uint8_t I2C_SCL_PIN = 22;
constexpr uint8_t BATTERY_ADC_PIN = 34;

// Calibrate these values in place; see README for the tare and known-mass procedure.
// HX711 returns kilograms when SCALE_FACTOR and OFFSET match the installed load cell.
constexpr float HX711_SCALE_FACTOR = -7050.0F;
constexpr long HX711_OFFSET = 0;
constexpr uint8_t HX711_SAMPLE_COUNT = 10;
constexpr uint32_t HX711_READY_TIMEOUT_MS = 1500;

// V_battery = V_adc * BATTERY_DIVIDER_RATIO.  A 100k/100k divider has a ratio of 2.
constexpr float BATTERY_DIVIDER_RATIO = 2.0F;

constexpr uint32_t WAKE_PERIOD_S = 60;
constexpr uint32_t WIFI_CONNECT_TIMEOUT_MS = 15000;
constexpr uint32_t NTP_SYNC_TIMEOUT_MS = 10000;
constexpr uint32_t NTP_VALID_AFTER = 1704067200;  // 2024-01-01T00:00:00Z
