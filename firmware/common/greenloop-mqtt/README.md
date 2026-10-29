# GreenLoopMqtt

Shared Arduino helpers for the GreenLoop MQTT topic and payload contract.

`topicFor(nodeId, channel)` creates `greenloop/<nodeId>/<channel>`, where the
channels are `telemetry`, `status`, `event`, and `cmd`. The helpers configure a
retained QoS 1 `offline` status will, publish retained QoS 1 statuses, publish
QoS 0 telemetry, publish QoS 1 events, and subscribe to commands at QoS 1.

Telemetry wraps caller-owned metrics:

```json
{"ts": 1730000000, "metrics": {"soil_moisture_pct": 42.5}}
```

Event payloads merge caller-owned fields with the timestamp:

```json
{"ts": 1730000000, "type": "pump", "state": "started", "reason": "manual"}
```
