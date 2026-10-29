# GreenLoop hardware inventory

This page records confirmed equipment already on the farm and a dated,
priceable reference bill of materials (BOM) for the first three ESP32 nodes.
Prices were checked on **2026-10-30** and can change. The wiring diagrams,
power estimates, and cost comparison will be added in later hardware tasks.

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
HX711/load-cell pair, one reed contact and separate magnet, and one battery
divider resistor pack. The relay is included only as a conditional example.

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
| **Conditional relay example only: 3.3 V logic module, 10 A / 30 V DC contacts** | 1 | [Partco](https://partco.shop/product/relay-module-1-ch-opto-isolated-3vdc-5283) | €5.60 | €5.60 |
| **Reference add-on subtotal, including conditional relay** |  |  |  | **€67.26** |

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

## Planned sections

Subsequent hardware documentation can extend this page with node pin tables,
reference wiring diagrams, solar sizing assumptions, and a transparent cost
comparison. Any added prices should retain the dated, VAT-included, shipping-
excluded convention above or state a clearly revised convention.
