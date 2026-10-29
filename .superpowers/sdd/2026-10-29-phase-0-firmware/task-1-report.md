# Task 1 Report — Shared MQTT Contract Library

## Status

Implemented the shared `GreenLoopMqtt` PlatformIO library.

## Implementation commit

- `703137e26b1ff0483cce34c02f2ae0a314c96be9` — `feat(firmware): add shared MQTT contract library`

## Files changed

- `firmware/common/greenloop-mqtt/library.json`
- `firmware/common/greenloop-mqtt/src/GreenLoopMqtt.h`
- `firmware/common/greenloop-mqtt/src/GreenLoopMqtt.cpp`
- `firmware/common/greenloop-mqtt/README.md`

## Verification

- Passed `git diff --check` before committing.
- Parsed `library.json` successfully with PowerShell `ConvertFrom-Json`.
- Checked each required helper signature and MQTT QoS/retained expression against
  the task brief.
- Tests were not added or run per developer instruction.
- No build was run: Task 1 contains no PlatformIO project or build target.

## Self-review

- `Channel` is the single source of the four contract channel names and maps to
  `telemetry`, `status`, `event`, and `cmd` below the exact `greenloop/` prefix.
- The last will and status use retained QoS 1. Telemetry uses non-retained QoS
  0; events use non-retained QoS 1; command subscriptions request QoS 1.
- Telemetry and events serialize a new JSON envelope into a temporary `String`.
  Event fields are copied before assigning `ts`, so caller-provided fields
  cannot replace the envelope timestamp.
- The README documents the contract and includes telemetry and event examples.

## Concerns

- Runtime compilation and broker interaction remain unverified because no
  firmware project exists for Task 1 and testing was explicitly prohibited.
