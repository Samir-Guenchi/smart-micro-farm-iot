#pragma once

#include <Arduino.h>
#include <ArduinoJson.h>
#include <MQTTClient.h>

namespace greenloop {

enum class Channel : uint8_t { Telemetry, Status, Event, Command };

String topicFor(const char* nodeId, Channel channel);
void configureOfflineWill(MQTTClient& client, const char* nodeId);
bool publishStatus(MQTTClient& client, const char* nodeId, const char* status);
bool publishTelemetry(MQTTClient& client, const char* nodeId, uint32_t ts,
                      JsonObjectConst metrics);
bool publishEvent(MQTTClient& client, const char* nodeId, uint32_t ts,
                  JsonObjectConst fields);
bool subscribeCommands(MQTTClient& client, const char* nodeId);

}  // namespace greenloop
