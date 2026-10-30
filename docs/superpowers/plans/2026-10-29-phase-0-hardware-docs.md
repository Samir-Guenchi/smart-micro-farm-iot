# Phase 0 Hardware Docs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task by task.

**Goal:** Publish reproducible wiring, a dated EUR BOM, solar sizing, and a transparent cost check for the three ESP32 node builds.

**Architecture:** One `hardware/README.md` is the source of truth for inventory, assumptions, prices, and calculations. Three SVGs visualize the corresponding pin tables and connections without claiming unspecified installed hardware models.

**Tech Stack:** Markdown tables and SVG diagrams; current European supplier listings and ESP32/sensor primary documentation for sourced values.

**Spec:** `docs/superpowers/specs/2026-10-29-phase-0-assigned-issues-design.md`

## Global Constraints

- Use the generic ESP32 DevKit reference pinout (`esp32dev`) shown by the repo photos; call out that exact board revisions must be matched before field wiring.
- Document SHT31, capacitive soil sensor, HX711/load cell, reed switch, battery divider, and a pump relay selected for the installed pump nameplate.
- Use `air_humidity_pct` for hive humidity and `door_open` (`1` open, `0` closed) for coop state.
- Existing ESP32 boards, Okköbi door, camera, and on-site solar panel are owner-supplied assets whose models and historical purchase prices are absent from the repo.
- Give each sourced price a EUR amount, direct supplier link, and lookup date; show totals separately for priced recommended parts and unknown existing assets.
- Show the €3,000 comparison as a conditional headroom calculation; do not present missing historical costs as zero.

---

## File Structure

- `hardware/README.md`: inventory, reference pin tables, sourced BOM, solar-sizing method, costs, assumptions, and calibration notes.
- `hardware/irrigation-node.svg`: ESP32, capacitive probe, SHT31, and relay interface.
- `hardware/hive-node.svg`: ESP32, HX711/load cell, SHT31, battery divider, and power path.
- `hardware/coop-node.svg`: ESP32 and reed-switch circuit.

## Task 1: Inventory and Source the Reference Parts

**Files:**
- Create: `hardware/README.md`

- [ ] List existing assets confirmed by `README.md` and the founder document: ESP32 boards ×3, Okköbi automatic door, solar camera, and installed solar panel. Mark model and purchase price as unreported.
- [ ] Select the reference node parts already fixed by the approved spec: SHT31 modules, capacitive soil probe, HX711 plus load cell, reed switch, battery divider parts, and a relay interface rated to the installed pump's nameplate.
- [ ] Find direct European supplier pages for each recommended add-on part; record the current listed EUR price, supplier, product URL, and lookup date in the BOM.
- [ ] Since the installed pump nameplate is absent, price one reference relay module for a clearly labeled 12 V DC / 10 A example load, label that line conditional and not field-approved, and state that the installed pump requires a relay selected from its actual voltage/current nameplate.
- [ ] Record which prices include VAT, shipping, or neither; use one clear subtotal convention for all recommended parts.

## Task 2: Add Reference Pin Tables and Wiring Drawings

**Files:**
- Modify: `hardware/README.md`
- Create: `hardware/irrigation-node.svg`
- Create: `hardware/hive-node.svg`
- Create: `hardware/coop-node.svg`

- [ ] Add an irrigation table for GPIO34 soil ADC, GPIO21/GPIO22 I2C, and GPIO26 relay input, plus shared 3V3/GND connections.
- [ ] Draw the irrigation SVG with probe output to ADC34, SHT31 SDA/SCL to GPIO21/22, and GPIO26 to a relay input; show pump contacts as a separately rated load side.
- [ ] Add a hive table for HX711 DOUT GPIO32/SCK GPIO33, SHT31 I2C GPIO21/GPIO22, and battery-divider output GPIO34.
- [ ] Draw the hive SVG with the load cell wired to HX711 E+/E-/A+/A-, the HX711 digital pins to the ESP32, and battery measurement through the divider.
- [ ] Add a coop table and SVG for GPIO27 with an external pull-up to 3V3 and a reed switch to ground; show the optional light sensor as out of scope.
- [ ] Label diagrams as reference wiring and note 3.3 V ESP32 GPIO limits; list the need to verify the actual board and pump ratings before connecting field hardware.

## Task 3: Calculate Solar Use and Check the Cost Claim

**Files:**
- Modify: `hardware/README.md`

- [ ] Create a node energy table with active current, sleep current, active duration, and daily Wh assumptions for each node; separate cited chip/module specifications from values that require field measurement.
- [ ] Show the formulas `Wh/day = sum(W × hours)` and `panel_Wp >= Wh/day / (peak_sun_hours × system_efficiency)`; state chosen sun-hours, efficiency, autonomy days, and battery usable depth of discharge.
- [ ] Show battery capacity as `battery_Wh >= daily_Wh × autonomy_days / usable_depth_of_discharge` and convert Wh to Ah at the documented battery voltage.
- [ ] Include a sensitivity line for lower winter sun-hours and state that the farm's installed panel capacity is unreported, so site-system adequacy cannot be confirmed from the repository.
- [ ] Sum the priced recommended node additions, calculate `€3,000 - priced_recommended_parts`, and display existing assets as unknown cost rather than zero.
- [ ] State that the documented parts estimate fits the claim only if the unpriced existing hardware and other included kit remain within the displayed headroom.
- [ ] Add setup and calibration notes: dry/wet soil ADC endpoints, load-cell tare and known-mass calibration, reed switch logic, and relay rating check.

## Reference Documentation

- [PlatformIO `esp32dev` board](https://docs.platformio.org/en/stable/boards/espressif32/esp32dev.html)
- [Adafruit SHT31 product and library](https://www.adafruit.com/product/2857)
- [HX711 calibration and supported ESP32 targets](https://registry.platformio.org/libraries/bogde/HX711)
- [ESP32 datasheet and chip power modes](https://www.espressif.com/sites/default/files/documentation/esp32_datasheet_en.pdf)
