# GreenLoop hardware inventory

This page records confirmed equipment already on the farm and a dated,
priceable reference bill of materials (BOM) for the first three ESP32 nodes.
Prices were checked on **2026-10-30** and can change. Reference pin tables,
wiring diagrams, illustrative energy sizing, and a conditional cost comparison
are included below.

## Existing farm equipment

The project README and founder's startup application confirm these assets are
already acquired or installed. Their exact models and historical purchase
prices are not reported, so they are excluded from the add-on subtotal and any
complete farm hardware cost calculation.

| Existing asset | Confirmed quantity/status | Model | Purchase price |
| --- | --- | --- | --- |
| ESP32 development boards | 3 boards | Unreported | Unreported |
| Okköbi automatic coop door | Installed and operational | Unreported | Unreported |
| Solar-powered camera | Installed | Unreported | Unreported |
| Solar panel / photovoltaic system | Installed on site | Unreported | Unreported |

## Reference add-on BOM

The following quantities cover the irrigation, hive, and coop sensing
references: two SHT31 modules (irrigation and hive), one soil probe, one
HX711/load-cell pair, one reed contact and separate magnet, one battery
divider resistor pack, and a pack of 10 kΩ pull-up resistors (one resistor
used). The relay is included only as a conditional example.

**Price convention:** each unit price is the supplier's displayed EUR retail
price including displayed VAT, excluding shipping, checked on 2026-10-30.
Shipping is excluded for every row, including where a supplier publishes a
threshold or flat delivery charge. No price below is a shipping-inclusive
quote. This keeps the subtotal comparable across suppliers; checkout delivery
costs may vary by destination and basket.

| Part / reference | Qty. | Supplier product page | Unit price (VAT incl.) | Line total |
| --- | ---: | --- | ---: | ---: |
| Adafruit SHT31-D breakout | 2 | [Opencircuit](https://opencircuit.shop/product/adafruit-sensirion-sht31-d) | €22.00 | €44.00 |
| DFRobot SEN0193 capacitive soil-moisture probe | 1 | [RobotShop EU](https://eu.robotshop.com/products/gravity-moisture-sensor-corrosion-resistant) | €6.49 | €6.49 |
| HX711 load-cell ADC module | 1 | [Informatica IT](https://www.informaticait.it/en/357-hx711-load-cell-weighing-module-2-5-5-5v-adc-converter-for-arduino.html) | €2.60 | €2.60 |
| Single-point load cell, 50 kg reference capacity | 1 | [Informatica IT](https://www.informaticait.it/en/458-50kg-load-cell-weight-sensor-for-force-measurement-and-scales-arduino-hx711.html) | €5.86 | €5.86 |
| Normally-open reed contact | 1 | [Ben's Electronics](https://www.benselectronics.nl/products/reed-contact-normally-open) | €0.45 | €0.45 |
| 5 × 8 mm magnet for reed contact (sold separately) | 1 | [Opencircuit](https://opencircuit.shop/product/magnet-5x8-mm-also-suitable-reed-contacts) | €0.95 | €0.95 |
| 20-pack of 100 kΩ, 1/4 W, ±5% resistors | 1 pack | [Informatica IT](https://www.informaticait.it/en/2524-20-pack-100k-ohm-carbon-film-resistor-tht-1-4w-5-0-25w-2-3x6mm.html) | €1.31 | €1.31 |
| 10-pack of 10 kΩ, 1/4 W, ±1% resistors (one used as coop pull-up) | 1 pack | [Informatica IT](https://www.informaticait.it/en/2026-10k-ohm-carbon-film-resistor-1-4w-0-25w-1-10-pack.html) | €0.92 | €0.92 |
| **Conditional relay example only: 3.3 V logic module, 10 A / 30 V DC contacts** | 1 | [Partco](https://partco.shop/product/relay-module-1-ch-opto-isolated-3vdc-5283) | €5.60 | €5.60 |
| **Reference add-on subtotal, including conditional relay** |  |  |  | **€68.18** |

The subtotal is the sum of the listed line totals and excludes shipping and all
existing owner-supplied assets with unknown historic cost. The €5.60 relay is a
priced example for a **12 V DC / 10 A example load only**; it is conditional
and **not field-approved** for the installed pump. The pump's model and
nameplate ratings have not been reported. Select a relay only after checking
the actual pump voltage and current nameplate, including its starting/load
requirements.

The load-cell product is rated for 50 kg maximum capacity. This is a reference
part, not confirmation that one cell is suitable for the hive: check the
actual hive/platform mechanical load, load distribution, mounting, and design
margin before selecting and installing a load cell.

For the hive battery-measurement reference, two 100 kΩ resistors form a 2:1
divider and align with the current firmware's `BATTERY_DIVIDER_RATIO = 2.0`.
This reference applies only to a **single-cell battery whose maximum voltage
is 4.2 V**. A different battery pack or maximum voltage requires recalculating
both the divider hardware and the firmware ratio before connection; keep the
ESP32 ADC input within its allowed range.

## Unknown existing costs

No model numbers or purchase prices are recorded here for the three ESP32
boards, Okköbi door, solar camera, or installed solar panel/system. Those
unknown costs are not zero and cannot be used to verify a complete historical
farm hardware total. Keep them separate from this dated add-on subtotal until
records are available.

## Illustrative node energy and solar sizing

The following is a normalized reference calculation for the three new sensing
nodes, not measured consumption or a site forecast. The local startup material
describes a planned pilot in Algeria, but gives no farm coordinates; country
alone is not enough to choose a site-specific solar resource. The 4 and 2
peak-sun-hour values below are sizing assumptions only. Use the European
Commission [PVGIS manual](https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/using-pvgis-5/pvgis-5-user-manual_en)
and [PVGIS calculator](https://re.jrc.ec.europa.eu/pvg_tools/en/) with actual
coordinates, panel orientation, and system details for a site estimate.

| Node | Battery-side active current assumption | Sleep current assumption | Daily time allocation | Reference daily energy |
| --- | ---: | ---: | --- | ---: |
| Irrigation | 100 mA | 0 mA assumed (no sleep allocation) | 24 h active, 0 h sleep | 3.7 V × 0.100 A × 24 h = **8.88 Wh/day** |
| Coop | 100 mA | 0 mA assumed (no sleep allocation) | 24 h active, 0 h sleep | 3.7 V × 0.100 A × 24 h = **8.88 Wh/day** |
| Hive | 150 mA | 10 mA | 4 h active, 20 h sleep | (3.7 V × 0.150 A × 4 h) + (3.7 V × 0.010 A × 20 h) = **2.96 Wh/day** |
| **Total** |  |  |  | **20.72 Wh/day** |

These battery-side currents and durations are **unmeasured planning assumptions**
to be checked on the assembled boards over representative operating cycles.
The hive's active/sleep split is a simplified normalized allocation; measure
actual dev-board current, peripherals, regulator losses, and wake duration.
Irrigation and coop are conservatively modeled as continuously active in this
example. As chip specifications only, the ESP32 datasheet lists 10 µA for the
RTC-timer-plus-RTC-memory deep-sleep configuration, 20–31 mA for a dual-core
chip at 80 MHz, and separate Wi-Fi transmit/receive modes and figures. These
figures describe the SoC, not a development board or battery-side load, and
were **not** substituted for the assumptions in the table. See the official
[Espressif ESP32 Series datasheet](https://www.espressif.com/sites/default/files/documentation/esp32_datasheet_en.pdf).
Actual draw depends on the exact module/board, regulator, sensors, relay state,
radio activity, firmware, and supply path.

Use these formulas for the reference sizing:

```text
Wh/day = sum(W × hours)
panel_Wp >= Wh/day / (peak_sun_hours × system_efficiency)
battery_Wh >= daily_Wh × autonomy_days / usable_depth_of_discharge
battery_Ah >= battery_Wh / battery_voltage_V
```

For this example, use **4 peak-sun-hours/day**, **65% combined PV-to-load
efficiency**, **2 autonomy days**, **80% usable battery depth of discharge**,
and a **3.7 V nominal single-cell battery rail (4.2 V maximum)**. This reference
rail aligns with the hive divider and firmware `BATTERY_DIVIDER_RATIO = 2.0`;
other packs require updating the divider and firmware ratio. The calculations
are:

- Reference panel: `20.72 / (4 × 0.65) = 7.97 Wp` (minimum arithmetic result).
- Lower-winter sensitivity at **2 assumed peak-sun-hours/day**:
  `20.72 / (2 × 0.65) = 15.94 Wp`.
- Battery for two days: `20.72 × 2 / 0.80 = 51.8 Wh`, or
  `51.8 / 3.7 = 14.0 Ah` nominal at 3.7 V.

The winter line is a sensitivity case, not a winter forecast. The installed
panel capacity, battery pack/capacity, system voltage, controller, and pump
load are unreported, so repository information cannot establish site-system
adequacy. The node-only estimate also excludes the pump and other installed or
planned loads; it does not size their power system.

## Cost comparison and conditional headroom

The priced recommended add-on parts total **€68.18 including the conditional
relay example, VAT included, shipping excluded**. Against the stated €3,000
comparison claim, the arithmetic headroom is:

```text
€3,000 - €68.18 = €2,931.82
```

This parts estimate fits within that claim only if the unpriced existing
hardware and any other kit included in the claim remain within **€2,931.82**.
Existing boards, door, camera, installed solar equipment, pump, battery,
controller, wiring, and installation have unknown costs here; they are not
zero and are not included in the €68.18 priced-parts subtotal. The subtotal is
not a complete farm system cost or a verification of the claim.

## Setup and calibration notes

- **Soil probe:** record ADC readings in the actual soil when dry and when
  thoroughly wet, then set and validate the firmware endpoints against those
  readings. Do not treat raw ADC counts as universal moisture percentages.
- **Hive scale:** tare the installed platform with the empty hive/platform in
  place, then apply one or more known masses spanning the operating range to
  determine and verify the HX711 scale factor and offset. Recheck after final
  mounting; ensure the load cell and mechanics have adequate capacity and
  margin.
- **Coop reed contact:** verify the normally-open contact closes to GND when
  the door/magnet position represents closed, with the GPIO pull-up enabled.
  Confirm firmware `door_open` reports `1` for open and `0` for closed through
  several physical open/close cycles.
- **Battery divider:** for the documented 100 kΩ / 100 kΩ divider, verify ADC
  readings and calibrated battery voltage across the single-cell range,
  especially up to 4.2 V at the battery input. Keep the ADC pin within the
  exact board's permitted input range. Recalculate divider values and set
  `BATTERY_DIVIDER_RATIO` for any different battery pack.
- **Pump relay:** choose and approve a relay only after reading the installed
  pump nameplate and checking voltage, running and starting current, contact
  DC/AC rating, and load type. The priced 12 V DC / 10 A module is a conditional
  example, not confirmation of suitability.

## Reference wiring and pin assignments

These diagrams show reference wiring for a generic `esp32dev` board only.
Confirm the exact board revision, connector labels, sensor supply limits, and
module pinout before wiring. ESP32 GPIO signals are **3.3 V logic**; never
apply 5 V to a GPIO or drive an external load from a GPIO. Shared 3V3 and GND
shown below are for low-voltage logic and sensors only.

### Irrigation node

| Function | ESP32 pin | Reference connection |
| --- | --- | --- |
| Soil probe analog output | GPIO34 / ADC34 | Probe AO to ADC34; power probe per its module rating |
| SHT31 I2C data | GPIO21 / SDA | SHT31 SDA |
| SHT31 I2C clock | GPIO22 / SCL | SHT31 SCL |
| Relay module control | GPIO26 | Relay IN only; use a compatible 3.3 V logic input |
| Logic/sensor supply | 3V3 and GND | Common low-voltage logic supply/ground as supported by modules |

See [irrigation reference wiring](irrigation-node.svg). The relay contacts and
pump supply form a separate power circuit. The priced relay is a conditional
example for a **12 V DC / 10 A load only**; the installed pump's rating is
unknown and this example is not approved for it. Verify the actual pump
nameplate, startup current, and relay/contact ratings before field connection.
Do not connect mains voltage using this reference diagram.

### Hive weighing and battery node

| Function | ESP32 pin | Reference connection |
| --- | --- | --- |
| HX711 data out | GPIO32 | HX711 DOUT/DT |
| HX711 clock | GPIO33 | HX711 SCK/CLK |
| SHT31 I2C data | GPIO21 / SDA | SHT31 SDA |
| SHT31 I2C clock | GPIO22 / SCL | SHT31 SCL |
| Battery divider midpoint | GPIO34 / ADC34 | Divider midpoint to ADC34 |
| Logic/sensor supply | 3V3 and GND | Common low-voltage logic ground; supply modules within their ratings |

See [hive reference wiring](hive-node.svg). The load cell's E+, E−, A+, and
A− leads connect to the matching HX711 excitation and channel A terminals;
confirm the load-cell color code because it varies by manufacturer. The
divider drawing uses two **100 kΩ** resistors, ratio 2.0, and is for a
single-cell battery with maximum voltage **4.2 V** only. Other pack voltages
require recalculating both divider hardware and firmware before connection.
The hive humidity telemetry key is `air_humidity_pct`. Keep ADC34 within the
board's allowed input range. The divider is for battery measurement only;
do not connect the measured single-cell battery directly to ESP32 VCC. The
board power and charger/regulator path is unspecified and must be selected for
the actual panel, battery chemistry and voltage, and ESP32 board input.

### Coop door contact

| Function | ESP32 pin | Reference connection |
| --- | --- | --- |
| Reed contact input | GPIO27 | GPIO27 node with external pull-up to 3V3; normally-open contact closes to GND |
| Logic supply/return | 3V3 and GND | Pull-up reference and switch return |
| Optional light sensor | — | Out of scope for this reference |

See [coop reference wiring](coop-node.svg). Use an external pull-up resistor
from the GPIO27 signal to 3V3. The normally-open reed contact connects the
signal to GND when closed; do not connect the reed circuit to a higher voltage.

All drawings are reference wiring, not a field installation approval. Verify
the exact ESP32 board revision and all hardware ratings before connecting
field equipment.
