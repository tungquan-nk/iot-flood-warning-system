import json
import logging
import paho.mqtt.client as mqtt
from app.services.telemetry_service import process_telemetry, process_node_status

logger = logging.getLogger(__name__)


class MqttManager:
    def __init__(self):
        self.client = None
        self.app = None
        self.topic_prefix = "flood_system/nodes"

    def init_app(self, app):
        self.app = app
        self.topic_prefix = app.config["MQTT_TOPIC_PREFIX"]
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="flask_flood_backend")

        username = app.config.get("MQTT_USERNAME")
        password = app.config.get("MQTT_PASSWORD")
        if username:
            self.client.username_pw_set(username, password)

        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

        host = app.config["MQTT_BROKER_HOST"]
        port = app.config["MQTT_BROKER_PORT"]
        try:
            self.client.connect_async(host, port, keepalive=60)
            self.client.loop_start()
            logger.info("MQTT client started connecting to %s:%s", host, port)
        except Exception as exc:
            logger.error("Failed to start MQTT client: %s", exc)

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            topic = f"{self.topic_prefix}/+/+"
            client.subscribe(topic, qos=1)
            logger.info("Subscribed to %s", topic)
        else:
            logger.warning("MQTT connection failed with code: %s", reason_code)

    def _on_message(self, client, userdata, msg):
        if self.app is None:
            return
        try:
            parts = msg.topic.split("/")
            if len(parts) < 4:
                return
            node_id = parts[-2]
            channel = parts[-1]
            payload = json.loads(msg.payload.decode("utf-8"))

            with self.app.app_context():
                if channel == "telemetry":
                    payload.setdefault("node_id", node_id)
                    process_telemetry(
                        payload,
                        retention_hours=self.app.config.get("TELEMETRY_RETENTION_HOURS", 24),
                    )
                elif channel == "status":
                    process_node_status(node_id, payload.get("status", ""))
        except Exception as exc:
            logger.error("Error handling MQTT message on %s: %s", msg.topic, exc)

    def publish_command(self, node_id: str, mode: str, pump_command: bool) -> bool:
        if self.client is None or not self.client.is_connected():
            return False
        topic = f"{self.topic_prefix}/{node_id}/command"
        payload = json.dumps({"mode": mode, "pump_command": pump_command})
        info = self.client.publish(topic, payload, qos=1)
        return info.rc == mqtt.MQTT_ERR_SUCCESS


mqtt_manager = MqttManager()
