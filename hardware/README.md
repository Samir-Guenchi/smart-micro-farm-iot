# GreenLoop hardware inventory

This page records confirmed equipment already on the farm and a dated,
priceable reference bill of materials (BOM) for the first three ESP32 nodes.
Prices were checked on **2026-10-30** and can change. Reference pin tables and
wiring diagrams are included below; power estimates and a cost comparison may
be added in later hardware tasks.

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
Keep ADC34 within the board's allowed input range.

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
