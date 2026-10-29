# GreenLoop hive node

This ESP32 wakes once per minute to measure hive weight, SHT31 conditions, and
battery voltage. It makes one bounded Wi-Fi/NTP/MQTT telemetry attempt, then
powers down the HX711 and deep-sleeps for 60 seconds.

## Setup and wiring

Copy `include/secrets.example.h` to the untracked `include/secrets.h`, then
enter the Wi-Fi and MQTT credentials. GPIO assignments are in `include/config.h`.

| Function | ESP32 GPIO | Notes |
| --- | --- | --- |
| HX711 DOUT | 32 | HX711 data output |
| HX711 SCK | 33 | HX711 clock |
| SHT31 SDA / SCL | 21 / 22 | I2C bus, normally address `0x44` |
| Battery divider output | 34 | ADC-only input; keep the divided voltage within the ESP32 ADC range |

Connect the load cell to the HX711's `E+`, `E-`, `A+`, and `A-` terminals as
marked by the load-cell manufacturer. Do not attach battery voltage directly to
GPIO34: use the divider and a common ground.

## Weight calibration

The defaults (`HX711_SCALE_FACTOR = -7050.0`, `HX711_OFFSET = 0`) are only
starting values; calibrate with the installed hive platform before relying on
measurements.

1. Empty the platform and record an averaged raw HX711 reading. Put that value
   in `HX711_OFFSET` (tare).
2. Add a known mass in kilograms, observe the raw change, and set
   `HX711_SCALE_FACTOR` so `get_units(10)` returns that mass. Reverse its sign
   if loading lowers the reported value.
3. Repeat with a second known mass and update the factor if necessary.

The firmware calls `set_scale()`, `set_offset()`, then `get_units(10)`. It waits
at most `HX711_READY_TIMEOUT_MS` for DOUT before that conversion; an unavailable
HX711 simply omits `hive_weight_kg` for the wake cycle.

## Battery divider

`battery_v = analogReadMilliVolts(GPIO34) / 1000 * BATTERY_DIVIDER_RATIO`.
For equal 100 kOhm resistors, the ratio is 2.0. Use the actual resistor ratio
`(R_top + R_bottom) / R_bottom`, account for tolerances, and ensure the divider
output remains inside the selected ESP32 ADC attenuation range at maximum battery
voltage. The code uses calibrated ADC millivolts with 11 dB attenuation.

## MQTT contract and wake cycle

Node id: `hive-1`.

| Topic | Details |
| --- | --- |
| `greenloop/hive-1/telemetry` | QoS 0 once per 60-second wake cycle: optional `hive_weight_kg`, optional `hive_temp_c`, optional `air_humidity_pct`, and `battery_v` |
| `greenloop/hive-1/status` | Retained `online` after connection; retained `offline` is configured as the last will and published before planned sleep |

The wake sequence is: sample sensors; wait up to 15 seconds for Wi-Fi; wait up
to 10 seconds for NTP; configure the retained offline MQTT will; connect; publish
online, telemetry, and offline; disconnect; power down the HX711; then timer deep
sleep for `WAKE_PERIOD_S` (60) seconds. Wi-Fi, NTP, or MQTT failure skips the
network step and still reaches deep sleep.

## Build

```sh
pio run --project-dir firmware/hive-node
```
