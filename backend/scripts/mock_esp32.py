import json
import math
import time
import paho.mqtt.client as mqtt

BROKER_HOST = "localhost"
BROKER_PORT = 1883
NODE_ID = "node_01"

STATUS_TOPIC = f"flood_system/nodes/{NODE_ID}/status"
TELEMETRY_TOPIC = f"flood_system/nodes/{NODE_ID}/telemetry"
COMMAND_TOPIC = f"flood_system/nodes/{NODE_ID}/command"

state = {"mode": "AUTO", "pump_active": False}


def on_connect(client, userdata, flags, reason_code, properties):
    print(f"[ESP32-MOCK] Connected (rc={reason_code})")
    client.publish(STATUS_TOPIC, json.dumps({"status": "online"}), qos=1, retain=True)
    client.subscribe(COMMAND_TOPIC, qos=1)


def on_message(client, userdata, msg):
    data = json.loads(msg.payload.decode("utf-8"))
    state["mode"] = data.get("mode", "AUTO")
    if state["mode"] == "MANUAL":
        state["pump_active"] = bool(data.get("pump_command", False))
    print(f"[ESP32-MOCK] Received command: {data}")


def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"mock_{NODE_ID}")
    client.will_set(STATUS_TOPIC, json.dumps({"status": "offline"}), qos=1, retain=True)
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
    client.loop_start()

    step = 0
    try:
        while True:
            water_level = round(10.0 + 9.0 * math.sin(step * 0.25), 2)
            if water_level >= 16.0:
                alert_level = "DANGER"
            elif water_level >= 12.0:
                alert_level = "WARNING"
            else:
                alert_level = "NORMAL"

            if state["mode"] == "AUTO":
                state["pump_active"] = alert_level in {"WARNING", "DANGER"}

            flow_rate = round(2.4 if state["pump_active"] else 0.35, 2)
            payload = {
                "node_id": NODE_ID,
                "water_level_cm": water_level,
                "flow_rate_lpm": flow_rate,
                "pump_active": state["pump_active"],
                "alert_level": alert_level,
            }
            client.publish(TELEMETRY_TOPIC, json.dumps(payload), qos=0)
            print(f"[ESP32-MOCK] Published: {payload}")
            step += 1
            time.sleep(2)
    except KeyboardInterrupt:
        client.publish(STATUS_TOPIC, json.dumps({"status": "offline"}), qos=1, retain=True)
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
