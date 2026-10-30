# Phase 2 Water-use Logging Implementation Plan

> **For agentic workers:** Execute this plan with `superpowers:executing-plans` or inline under the user's approval to implement phase 2 issue #21.

**Goal:** Measure irrigation water with a pulse flow sensor and publish per-run and daily liter totals.

**Architecture:** The irrigation ESP32 counts flow pulses through a GPIO interrupt. It snapshots the count at pump start and stop, adds the measured run to a persisted UTC-day total, and includes the run volume in the queued `stopped` event. Existing MQTT helpers carry the event and telemetry without changing their envelope.

**Tech Stack:** ESP32 Arduino, PlatformIO, `Preferences`, GreenLoop MQTT, Markdown hardware documentation.

**Spec:** GitHub issue [#21: Water-use logging with a flow sensor](https://github.com/Samir-Guenchi/smart-micro-farm-iot/issues/21).

## Global Constraints

- Use GPIO18 for the flow pulse input; keep the irrigation relay on GPIO26, soil ADC on GPIO34, and SHT31 on GPIO21/GPIO22.
- Use a YF-S201 as a reference only when the measured drip-line flow is inside the sensor's rated range.
- Start with 450 pulses/L and make the calibration value configurable.
- Do not apply the sensor's 5 V pulse output directly to an ESP32 GPIO; use the documented level divider and common ground.
- Include `water_liters` in each `pump` `stopped` event and as the UTC-day total in irrigation telemetry.
- Persist the UTC-day pulse count so a restart during that day does not reset the reported total.

---

### Task 1: Count pulses and report water use

**Files:**
- Modify: `firmware/irrigation-node/include/config.h`
- Modify: `firmware/irrigation-node/src/main.cpp`
- Modify: `firmware/irrigation-node/README.md`

- [x] Add the flow input pin and pulses-per-liter calibration constant.
- [x] Count pulses in an interrupt-safe counter, capture start and stop counts around each pump run, and convert the difference to liters.
- [x] Extend queued pump events so only `stopped` events carry their run's `water_liters` value.
- [x] Store the daily pulse count and UTC day key in ESP32 NVS; reset the bucket when synchronized UTC moves to a new day.
- [x] Publish the daily `water_liters` total with existing irrigation telemetry.
- [x] Document the pin, initial calibration, event field, UTC-day semantics, and reboot persistence.

### Task 2: Document reference wiring and calibration

**Files:**
- Modify: `hardware/README.md`
- Modify: `hardware/irrigation-node.svg`

- [x] Add the YF-S201 reference wiring with a rated supply, common ground, and divider from signal to GPIO18.
- [x] State the reference flow range and that the actual line flow must be measured before selecting this sensor.
- [x] Document bucket calibration using known volume and pulse count; replace the initial pulses-per-liter value with the measured value.
- [x] Note that pond water may need filtration and that the sensor must be installed in the common line before the drip manifold.

### Task 3: Verify the firmware and MQTT contract

- [x] Confirm the architecture documentation describes `water_liters` in stopped events and daily telemetry.
- [x] Run the firmware workflow and confirm all PlatformIO projects build.
