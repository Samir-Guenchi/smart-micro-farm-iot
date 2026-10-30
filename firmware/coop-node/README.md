# GreenLoop coop node

This ESP32 monitors a reed switch on a coop door and publishes its stable state
and transitions over MQTT. The node continues sampling while Wi-Fi or MQTT is
unavailable.

## Setup and wiring

Copy `include/secrets.example.h` to the untracked `include/secrets.h`, then enter
Wi-Fi and MQTT credentials. Connect GPIO27 to one reed-switch terminal and the
other terminal to ground. Fit an external pull-up from GPIO27 to 3.3 V; the
firmware configures GPIO27 as `INPUT` and does not enable an internal pull-up.
With this wiring, an open circuit reads HIGH and means the door is open; a
closed reed contact reads LOW and means the door is closed.

The firmware requires the initial reed reading to remain unchanged for 50 ms
before treating it as the baseline or publishing telemetry. Initialization does
not create an event. Later readings are also accepted only after 50 ms unchanged;
each stable transition creates an event. When MQTT is disconnected, up to 16
events are buffered in a fixed ring; on overflow the oldest event is discarded
and the loss is logged over serial.

## MQTT contract

Node id: `coop-1`.

| Topic | Direction | Details |
| --- | --- | --- |
| `greenloop/coop-1/telemetry` | publish | QoS 0 immediately after MQTT and valid time are available, then every 60 seconds; `door_open` is `1` for open and `0` for closed |
| `greenloop/coop-1/status` | publish | Retained `online` after connection; retained `offline` is configured as the will and sent before planned shutdown |
| `greenloop/coop-1/event` | publish | QoS 1 transition event: `{"type":"door","state":"open"}` or `{"type":"door","state":"closed"}`, with Unix-seconds `ts` |

After SNTP synchronization, events store the Unix time at debounce acceptance.
For transitions captured before SNTP is available, exact Unix time is impossible
without an RTC. The firmware retains each monotonic capture time and estimates
Unix seconds from one Unix/millis clock anchor when draining the queue; those
pre-sync timestamps are estimates. SNTP is retried while Wi-Fi is connected.

## Build

```sh
pio run --project-dir firmware/coop-node
```
