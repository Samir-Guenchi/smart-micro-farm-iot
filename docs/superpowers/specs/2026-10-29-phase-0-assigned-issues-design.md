# Phase 0 Assigned Issues: Implementation Design

**Date:** 2026-10-29  
**Status:** Proposed for review  
**Scope:** GitHub issues #4, #5, #6, #7, and #11

## Context

The repository currently contains the README, roadmap, brand assets, farm photos, and startup documents. It has no firmware, hardware guides, or CI workflow. The assigned tickets establish the first three ESP32 nodes, the hardware documentation, and firmware build automation.

The roadmap calls for a common MQTT contract: node ids `irrigation-1`, `hive-1`, and `coop-1`; telemetry every 60 seconds; retained online/offline status with an MQTT last will; change events at QoS 1; and QoS 1 command messages. The ticket descriptions repeat that contract, so the implementation will preserve its topic and payload format.

## Proposed structure

```text
firmware/
  common/greenloop-mqtt/       shared MQTT contract and connection helper
  irrigation-node/             PlatformIO project
  hive-node/                   PlatformIO project
  coop-node/                   PlatformIO project
hardware/
  README.md                    component inventory, BOM, and solar sizing
  irrigation-node.svg           wiring overview
  hive-node.svg                 wiring overview
  coop-node.svg                 wiring overview
.github/workflows/firmware.yml  build every PlatformIO project
```

Each node remains an independent PlatformIO project. A small shared library holds node ids, topic construction, status/LWT setup, and JSON message helpers so the three projects cannot drift from the shared contract. Actual Wi-Fi and broker credentials live in each project's ignored `include/secrets.h`; a credential-free `include/secrets.example.h` is committed for developers and CI.

The projects target the generic ESP32 DevKit-compatible board shown in the repository photos (`esp32dev`). Hardware documentation will call this a reference pinout and note that the exact board revision must be matched before field wiring.

## Node behavior

### Irrigation node — issue #4

- Read a capacitive soil sensor and an SHT31 temperature/humidity sensor; publish calibrated soil percentage, `air_temp_c`, and `air_humidity_pct`.
- Drive a relay from a non-blocking pump state machine. Local threshold watering continues when Wi-Fi or MQTT is unavailable.
- Enforce `MAX_PUMP_S` in firmware for automatic runs and remote commands. The example limit is 900 seconds; an active run cannot be extended by another command.
- Read the pump relay in its safe/off state during startup and reconnects. Store the configurable moisture threshold and maximum run time in a single settings header.

The exact pump model and its voltage/current are not stated in the repository. The wiring diagram will show the controller side and relay contacts; the bill of materials will specify that relay selection must meet the installed pump nameplate rating. The guide will avoid claiming a specific pump-side wiring configuration without that rating.

### Hive node — issue #6

- Read hive load with an HX711 load-cell interface, plus an SHT31 temperature/humidity sensor and battery voltage divider.
- Publish `hive_weight_kg`, `hive_temp_c`, `air_humidity_pct`, and `battery_v` on `greenloop/hive-1/telemetry`.
- Include a tare and calibration procedure in the node README.
- Wake, sample, publish, disconnect cleanly, and enter deep sleep between 60-second readings. Publish an offline status before planned sleep; configure the same retained offline value as the MQTT last will for unexpected loss.

The shared metric list has no `hive_humidity_pct` field. This design uses the existing `air_humidity_pct` key on the hive node's topic, keeping the shared schema unchanged.

### Coop node — issue #5

- Debounce a reed switch and publish a `door` event when its state changes.
- Include the current door state in telemetry as `door_open` (`1` for open, `0` for closed).
- Load credentials from the same ignored/example header pattern.
- Leave the optional light sensor out of this implementation; the ticket marks it optional and the existing door already controls its own sunrise/sunset behavior.

## MQTT and reconnection behavior

The common helper will publish JSON payloads with Unix timestamps and use the documented topic forms:

- `greenloop/<node_id>/telemetry`
- `greenloop/<node_id>/status`
- `greenloop/<node_id>/event`
- `greenloop/<node_id>/cmd`

Telemetry is QoS 0 every 60 seconds. Status is retained, with `offline` configured as the last will. State-change events use QoS 1. The irrigation node continues local sensor control if network services fail; the coop node keeps sampling the door state and publishes when connectivity returns. The hive node makes one publish attempt per wake cycle, then sleeps to meet its power-saving requirement.

## Hardware guide and cost assumptions

The hardware guide will provide pin tables and clear SVG wiring diagrams, along with a dated EUR bill of materials and supplier links for the recommended sensor-node parts. It will estimate daily consumption and show panel/battery sizing calculations with the assumptions visible.

The README and startup document confirm that three ESP32 boards, the Okköbi door, the camera, and an on-site solar panel are already acquired, but provide no model numbers, receipts, or system capacity. The BOM will list those as existing owner-supplied assets with unknown purchase prices, price the recommended add-on modules separately, and calculate the remaining headroom under the €3,000 hardware claim. The guide will state that the complete historical farm total cannot be verified until the existing equipment costs are supplied.

## CI behavior

The GitHub Actions workflow will find PlatformIO projects one directory below `firmware/`, prepare `include/secrets.h` from the project's example file, and run `pio run` for every discovered project. It will exit successfully when no projects exist. The README will link to the firmware workflow badge. The root `.gitignore` will exclude PlatformIO build output and all real `secrets.h` files.

## Acceptance signals

- Three independent PlatformIO projects build against the same documented MQTT contract.
- The irrigation control path applies the same hard pump runtime limit to local and remote starts and remains functional without network connectivity.
- Coop state transitions produce events, and telemetry reports the current state.
- Hive telemetry includes calibrated weight, hive temperature, humidity, and battery voltage while the node sleeps between readings.
- The hardware directory contains pin tables, wiring diagrams, a dated and linked BOM, solar sizing, and an explicit cost comparison with the €3,000 claim.
- CI builds every present project, prepares example credentials, and passes with an empty firmware directory.

## Scope boundary

This design covers the five assigned tickets only. It does not add the separate MQTT database backend, Grafana dashboard, or Telegram alert service described elsewhere in the roadmap.
