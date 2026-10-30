"""Publishes commands to the nodes over MQTT."""

import json

import paho.mqtt.publish as publish


class MqttPublisher:
    def __init__(self, settings):
        self.s = settings

    def command(self, node, payload):
        auth = {"username": self.s.mqtt_user, "password": self.s.mqtt_password} if self.s.mqtt_user else None
        publish.single(
            f"greenloop/{node}/cmd",
            json.dumps(payload),
            qos=1,
            hostname=self.s.mqtt_host,
            port=self.s.mqtt_port,
            auth=auth,
            tls={} if self.s.mqtt_tls else None,
            client_id="",
        )
