# GreenLoop irrigation node

This ESP32 node reads capacitive soil moisture and SHT31 air measurements, runs a
relay-controlled pump, and publishes the GreenLoop MQTT contract.

## Setup and wiring

Copy `include/secrets.example.h` to the untracked `include/secrets.h`, then enter
Wi-Fi and MQTT credentials. The GPIO assignments are in `include/config.h`:

| Function | ESP32 GPIO |
| --- | --- |
| Capacitive soil sensor ADC output | 34 |
| Flow sensor pulse input | 18 |
| SHT31 SDA / SCL | 21 / 22 |
| Pump relay input | 26 |

The relay must default to **off** while the ESP32 resets. `RELAY_ACTIVE_HIGH`
defaults to `true`, so use an external pull-down on GPIO26 for an active-high
relay input. For an active-low relay, set it to `false` and fit an external
pull-up instead. Verify the relay module's actual input polarity before wiring.

Connect the relay contacts only after confirming their voltage/current ratings
and contact type match the installed pump's nameplate. The ESP32 GPIO drives the
relay input; it must never directly power the pump.

The flow input is configured for a 5 V pulse-output reference sensor through a
10 kΩ series resistor and a 15 kΩ resistor from GPIO18 to GND. This reduces a
5 V high level to about 3.0 V. Join sensor and ESP32 grounds, and verify the
actual sensor's output type and voltage before connecting it; never apply 5 V
directly to GPIO18. See [hardware wiring and calibration](../../hardware/README.md#irrigation-flow-measurement).

## Soil calibration and watering

1. With the probe dry and clean, record the raw ADC value and set `SOIL_ADC_DRY`.
2. Put the probe in the irrigated soil at its final installation depth, record the
   raw value, and set `SOIL_ADC_WET`.
3. Confirm the reported percentage rises from dry toward wet; the conversion is
   clamped to 0–100%.

Local watering starts below `MOISTURE_THRESHOLD_PCT` and does not re-arm until
the reading reaches the threshold plus `MOISTURE_HYSTERESIS_PCT`. It continues
without Wi-Fi or MQTT. Every run, including remote commands, is capped by
`MAX_PUMP_S` (900 seconds by default). A command received during an active run
is ignored and cannot extend it.

## MQTT contract

Node id: `irrigation-1`.

| Topic | Direction | Details |
| --- | --- | --- |
| `greenloop/irrigation-1/telemetry` | publish | QoS 0 every 60 seconds: `soil_moisture_pct`, optional `air_temp_c`, optional `air_humidity_pct`, `pump_on`, and `water_liters` for the current UTC day |
| `greenloop/irrigation-1/status` | publish | Retained `online` after connection; retained `offline` is the will and planned-shutdown status |
| `greenloop/irrigation-1/event` | publish | QoS 1 pump events: `type`, `state`, `reason`, and Unix `ts`; stopped events also include run `water_liters` |
| `greenloop/irrigation-1/cmd` | subscribe | QoS 1 command: `{"action":"pump","duration_s":N}` where `N` is a positive integer |

SNTP is configured while Wi-Fi is connected so telemetry and events use Unix
seconds. Invalid SHT31 readings are omitted rather than serialized as `NaN`.
Water volume is calculated from pulse count divided by
`FLOW_PULSES_PER_LITER` (450 pulses/L is only the initial YF-S201 reference).
The UTC-day pulse total is stored in ESP32 NVS. A run completed before time sync
is assigned to the UTC day when SNTP first becomes valid; a run crossing UTC
midnight is assigned to its stop day. Calibrate the installed sensor with a
measured volume before relying on the values.

## Build

```sh
pio run --project-dir firmware/irrigation-node
```
