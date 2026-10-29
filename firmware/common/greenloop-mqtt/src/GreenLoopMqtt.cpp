#include "GreenLoopMqtt.h"

namespace greenloop {
namespace {

const char* channelName(Channel channel) {
  switch (channel) {
    case Channel::Telemetry:
      return "telemetry";
    case Channel::Status:
      return "status";
    case Channel::Event:
      return "event";
    case Channel::Command:
      return "cmd";
  }

  return "";
}

}  // namespace

String topicFor(const char* nodeId, Channel channel) {
  return String("greenloop/") + nodeId + "/" + channelName(channel);
}

void configureOfflineWill(MQTTClient& client, const char* nodeId) {
  const String topic = topicFor(nodeId, Channel::Status);
  client.setWill(topic.c_str(), "offline", true, 1);
}

bool publishStatus(MQTTClient& client, const char* nodeId, const char* status) {
  const String topic = topicFor(nodeId, Channel::Status);
  return client.publish(topic.c_str(), status, true, 1);
}

bool publishTelemetry(MQTTClient& client, const char* nodeId, uint32_t ts,
                      JsonObjectConst metrics) {
  JsonDocument document;
  document["ts"] = ts;
  document["metrics"] = metrics;

  String payload;
  serializeJson(document, payload);

  const String topic = topicFor(nodeId, Channel::Telemetry);
  return client.publish(topic.c_str(), payload, false, 0);
}

bool publishEvent(MQTTClient& client, const char* nodeId, uint32_t ts,
                  JsonObjectConst fields) {
  JsonDocument document;
  for (JsonPairConst field : fields) {
    document[field.key()] = field.value();
  }
  document["ts"] = ts;

  String payload;
  serializeJson(document, payload);

  const String topic = topicFor(nodeId, Channel::Event);
  return client.publish(topic.c_str(), payload, false, 1);
}

bool subscribeCommands(MQTTClient& client, const char* nodeId) {
  const String topic = topicFor(nodeId, Channel::Command);
  return client.subscribe(topic.c_str(), 1);
}

}  // namespace greenloop
