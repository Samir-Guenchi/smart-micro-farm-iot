# Phase 0 Firmware Nodes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task by task.

**Goal:** Build three independent ESP32 PlatformIO projects that publish the GreenLoop MQTT contract and implement irrigation, hive, and coop sensing.

**Architecture:** Each node is an independent PlatformIO project with a small shared local library for topic construction, JSON envelopes, status, last will, and QoS policy. Sensor code and node behavior remain local to their project.

**Tech Stack:** PlatformIO, Arduino framework, `esp32dev`, ArduinoJson 7.4.3, 256dpi MQTT 2.4.6, Adafruit SHT31 2.2.2, HX711 0.7.5.

**Spec:** `docs/superpowers/specs/2026-10-29-phase-0-assigned-issues-design.md`

## Global Constraints

- Node ids are `irrigation-1`, `hive-1`, and `coop-1`.
- Topics are `greenloop/<node_id>/telemetry`, `status`, `event`, and `cmd`.
- Telemetry is sent every 60 seconds at QoS 0.
- Status is retained; `offline` is the MQTT last will.
- State-change events and pump commands use QoS 1.
- The irrigation pump is limited to `MAX_PUMP_S` (example value 900 seconds); a new command cannot extend an active run.
- Hive humidity uses `air_humidity_pct`; coop telemetry uses `door_open` with `1` for open and `0` for closed.
- Each node includes `include/secrets.example.h`; the real `include/secrets.h` remains untracked.
- Use `256dpi/MQTT` because its MQTT client supports a retained QoS-configurable will and QoS-configurable publishes; `PubSubClient` only exposes QoS 0 publish calls. See [MQTTClient API](https://github.com/256dpi/arduino-mqtt/blob/v2.4.6/src/MQTTClient.h) and [PubSubClient API](https://github.com/knolleary/pubsubclient/blob/master/src/PubSubClient.h).
- Use PlatformIO local symlink dependencies for the shared library; `lib_extra_dirs` is deprecated. See [PlatformIO `lib_deps`](https://docs.platformio.org/en/latest/projectconf/sections/env/options/library/lib_deps.html) and [`lib_extra_dirs`](https://docs.platformio.org/en/latest/projectconf/sections/env/options/library/lib_extra_dirs.html).

---

## File Structure

- `firmware/common/greenloop-mqtt/library.json`: shared library metadata and JSON/MQTT dependencies.
- `firmware/common/greenloop-mqtt/src/GreenLoopMqtt.h/.cpp`: topic and payload helpers.
- `firmware/common/greenloop-mqtt/README.md`: shared helper usage and payload examples.
- `firmware/irrigation-node/`: soil/environment sensors, relay safety, commands, and local auto-watering.
- `firmware/hive-node/`: HX711, SHT31, voltage measurement, calibration, and deep sleep.
- `firmware/coop-node/`: reed switch debounce, telemetry, and door events.
- Each project's `platformio.ini`, `include/config.h`, `include/secrets.example.h`, `src/main.cpp`, and `README.md` stay with that node.

## Task 1: Shared MQTT Contract Library

**Files:**
- Create: `firmware/common/greenloop-mqtt/library.json`
- Create: `firmware/common/greenloop-mqtt/src/GreenLoopMqtt.h`
- Create: `firmware/common/greenloop-mqtt/src/GreenLoopMqtt.cpp`

**Interfaces:**
- `topicFor(nodeId, channel)` returns `greenloop/<nodeId>/<channel>`.
- `configureOfflineWill(client, nodeId)` sets retained `offline` on the status topic at QoS 1 before connection.
- `publishStatus(client, nodeId, status)` publishes retained status at QoS 1.
- `publishTelemetry(client, nodeId, ts, metrics)` publishes `{"ts": ts, "metrics": metrics}` at QoS 0.
- `publishEvent(client, nodeId, ts, fields)` publishes `{"ts": ts, ...fields}` at QoS 1.
- `subscribeCommands(client, nodeId)` subscribes to the node command topic at QoS 1.

```cpp
namespace greenloop {
enum class Channel : uint8_t { Telemetry, Status, Event, Command };
String topicFor(const char* nodeId, Channel channel);
void configureOfflineWill(MQTTClient& client, const char* nodeId);
bool publishStatus(MQTTClient& client, const char* nodeId, const char* status);
bool publishTelemetry(MQTTClient& client, const char* nodeId,
                      uint32_t ts, JsonObjectConst metrics);
bool publishEvent(MQTTClient& client, const char* nodeId,
                  uint32_t ts, JsonObjectConst fields);
bool subscribeCommands(MQTTClient& client, const char* nodeId);
}
```

- [ ] Create `library.json` for `GreenLoopMqtt`, declaring `256dpi/MQTT` 2.4.6 and `bblanchon/ArduinoJson` 7.4.3.
- [ ] Use this PlatformIO local dependency line in each node project: `GreenLoopMqtt=symlink://../common/greenloop-mqtt`.
- [ ] Define the four channel names in one enum and implement `topicFor()` with the exact `greenloop/` prefix.
- [ ] Implement the will, status, telemetry, event, and command-subscription helpers using the interface above.
- [ ] Use JSON documents with caller-owned fields; serialize each envelope into a temporary `String` before publishing.
- [ ] Instantiate each MQTT client with a 256-byte read/write buffer so command and telemetry payloads fit.
- [ ] Ensure telemetry uses `retained=false, qos=0`, event uses `retained=false, qos=1`, status uses `retained=true, qos=1`, and the will uses `retained=true, qos=1`.
- [ ] Add a short library README with the helper contract and one example telemetry/event payload.

## Task 2: Irrigation Node

**Files:**
- Create: `firmware/irrigation-node/platformio.ini`
- Create: `firmware/irrigation-node/include/config.h`
- Create: `firmware/irrigation-node/include/secrets.example.h`
- Create: `firmware/irrigation-node/src/main.cpp`
- Create: `firmware/irrigation-node/README.md`

**Interfaces:**
- Pin and calibration values live in `config.h`; Wi-Fi and MQTT connection values live in `secrets.h`.
- The pump state machine exposes `bool startPump(uint32_t durationSeconds, PumpReason reason, uint32_t nowMs)`, `void updatePump(uint32_t nowMs, float soilMoisturePct)`, and `void stopPump(PumpReason reason)`.
- The MQTT command callback only validates and stores a pending request; the main loop applies it outside the callback.

```ini
[env:esp32dev]
platform = espressif32
board = esp32dev
framework = arduino
monitor_speed = 115200
lib_deps =
  GreenLoopMqtt=symlink://../common/greenloop-mqtt
  adafruit/Adafruit SHT31 Library@2.2.2
```

- [ ] Configure a PlatformIO Arduino project for board `esp32dev`; add local `GreenLoopMqtt`, ArduinoJson, and Adafruit SHT31 dependencies.
- [ ] Add example credentials with empty Wi-Fi and broker values, and declare the same macro names in `config.h` for the sketch to consume.
- [ ] Add soil ADC dry/wet calibration constants and a conversion that clamps the result to 0–100 percent; use GPIO34 for the capacitive sensor.
- [ ] Add SHT31 reads on I2C GPIO21/GPIO22; omit invalid sensor readings instead of publishing `NaN`.
- [ ] Implement a non-blocking pump state machine on GPIO26. Initialize the relay to off before connecting Wi-Fi; cap all requested durations at `MAX_PUMP_S` and ignore requests that would extend a running cycle.
- [ ] Measure run time with unsigned elapsed arithmetic (`uint32_t(nowMs - startedAtMs)`) so the cutoff remains correct across `millis()` rollover; add an external pull resistor appropriate to the relay's active polarity to keep it off during reset.
- [ ] Implement local watering below the configurable threshold and re-arm only after moisture recovers above the threshold plus hysteresis. Keep this logic running without Wi-Fi/MQTT.
- [ ] Subscribe to `greenloop/irrigation-1/cmd`; accept only `{"action":"pump","duration_s":N}` with a positive integer, cap it at `MAX_PUMP_S`, and queue the request for the main loop.
- [ ] Configure the retained offline will before connecting; publish retained `online` after each successful MQTT connection and `offline` before a planned disconnect.
- [ ] Publish `soil_moisture_pct`, `air_temp_c`, `air_humidity_pct`, and `pump_on`; publish pump start/stop events with `reason` and the shared timestamp format.
- [ ] Add reconnect backoff so broker loss does not block sensor sampling or pump cutoff; use SNTP when connected to supply Unix timestamps.
- [ ] Document the dry/wet ADC calibration steps, relay input polarity, `MAX_PUMP_S`, moisture threshold, MQTT topics, and the requirement to match relay contacts to the installed pump nameplate.
- [ ] Build the project with `pio run --project-dir firmware/irrigation-node` as the compile command used by the required firmware workflow.

## Task 3: Hive Node

**Files:**
- Create: `firmware/hive-node/platformio.ini`
- Create: `firmware/hive-node/include/config.h`
- Create: `firmware/hive-node/include/secrets.example.h`
- Create: `firmware/hive-node/src/main.cpp`
- Create: `firmware/hive-node/README.md`

**Interfaces:**
- `config.h` holds GPIO assignments, scale calibration, voltage divider ratio, and the 60-second wake period.
- The load-cell conversion uses `HX711::set_scale()`, `set_offset()`, and `get_units(10)`.

```ini
[env:esp32dev]
platform = espressif32
board = esp32dev
framework = arduino
monitor_speed = 115200
lib_deps =
  GreenLoopMqtt=symlink://../common/greenloop-mqtt
  adafruit/Adafruit SHT31 Library@2.2.2
  bogde/HX711@0.7.5
```

- [ ] Configure `esp32dev` Arduino project with the shared library, ArduinoJson, Adafruit SHT31, and bogde HX711 0.7.5.
- [ ] Add the common credential example and use GPIO32 for HX711 DOUT, GPIO33 for SCK, GPIO21/GPIO22 for SHT31, and GPIO34 for battery ADC.
- [ ] Read the load cell with a bounded ready timeout; skip the weight metric if HX711 is unavailable rather than blocking startup.
- [ ] Compute weight in kilograms from the documented scale factor and offset; read `hive_temp_c`, `air_humidity_pct`, and `battery_v` from the SHT31 and calibrated divider.
- [ ] Connect Wi-Fi, synchronize time, connect MQTT, configure retained offline will before connecting, publish retained online, publish telemetry, then publish retained offline and disconnect before sleep.
- [ ] Enter timer deep sleep for 60 seconds and power down HX711 before sleeping; skip MQTT cleanly when Wi-Fi or NTP is unavailable and still return to sleep.
- [ ] Document tare, known-mass calibration, battery divider calculation, pinout, expected metrics, and the 60-second wake cycle.
- [ ] Build the project with `pio run --project-dir firmware/hive-node` as the compile command used by the required firmware workflow.

## Task 4: Coop Node

**Files:**
- Create: `firmware/coop-node/platformio.ini`
- Create: `firmware/coop-node/include/config.h`
- Create: `firmware/coop-node/include/secrets.example.h`
- Create: `firmware/coop-node/src/main.cpp`
- Create: `firmware/coop-node/README.md`

**Interfaces:**
- The stable reed state is `enum class DoorState : uint8_t { Closed, Open };`; pending events use `struct DoorEvent { DoorState state; uint32_t ts; };` in a fixed 16-entry ring queue.
- GPIO27 uses an external pull-up and a 50 ms stable-read debounce interval.

```ini
[env:esp32dev]
platform = espressif32
board = esp32dev
framework = arduino
monitor_speed = 115200
lib_deps = GreenLoopMqtt=symlink://../common/greenloop-mqtt
```

- [ ] Configure `esp32dev` Arduino project with the shared MQTT library and ArduinoJson.
- [ ] Add the common credential example and document GPIO27-to-reed-to-ground wiring with the external pull-up.
- [ ] Sample the reed switch without blocking; accept a new state only after 50 ms of unchanged readings.
- [ ] Publish a `door` event for each stable state transition and publish current state as `door_open` (`1` open, `0` closed) in telemetry every 60 seconds.
- [ ] Set each coop event's fields to `{"type":"door","state":"open"}` or `{"type":"door","state":"closed"}`; stamp the event with Unix seconds when it is captured.
- [ ] If MQTT is unavailable, retain pending transition states in a fixed 16-entry ring queue and drain them in order after reconnect; when full, discard the oldest queued transition and log the overflow.
- [ ] Synchronize Unix time with SNTP when Wi-Fi is connected; publish current coop telemetry immediately after the first valid connection and continue at 60-second intervals.
- [ ] Keep sensor sampling active during Wi-Fi/MQTT loss and publish current state after reconnection; configure the shared status will and reconnect backoff.
- [ ] Publish retained `online` after successful MQTT connection and retained `offline` before planned disconnects.
- [ ] Document reed logic, debounce behavior, telemetry field, event shape, and MQTT topics. Do not add the optional light sensor.
- [ ] Build the project with `pio run --project-dir firmware/coop-node` as the compile command used by the required firmware workflow.

## Dependency References

- [PlatformIO `esp32dev` board](https://docs.platformio.org/en/stable/boards/espressif32/esp32dev.html)
- [256dpi MQTT Arduino library and API](https://github.com/256dpi/arduino-mqtt)
- [ArduinoJson 7 deserialization API](https://arduinojson.org/v7/tutorial/deserialization/)
- [Adafruit SHT31 library version 2.2.2](https://github.com/adafruit/Adafruit_SHT31/blob/master/library.properties)
- [HX711 library 0.7.5](https://registry.platformio.org/libraries/bogde/HX711)
