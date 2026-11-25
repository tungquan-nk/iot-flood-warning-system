import random
from datetime import timedelta
from app import db, socketio
from app.models import Node, TelemetryLog, AlertLog, utc_now, to_iso_utc
from app.services.fcm_service import send_node_push

VALID_ALERTS = {"NORMAL", "WARNING", "DANGER"}


def _ensure_node(node_id: str, is_virtual: bool = False) -> Node:
    node = db.session.get(Node, node_id)
    if node is None:
        node = Node(
            node_id=node_id,
            name=f"Điểm đo {node_id.upper()}",
            location_desc="Sa bàn mô phỏng Hà Nội",
            is_virtual=is_virtual,
            status="online",
        )
        db.session.add(node)
        db.session.flush()
    return node


def _record_event(
    node_id: str,
    event_type: str,
    message: str,
    water_level_cm: float | None,
    pump_active: bool | None,
    now,
):
    alert = AlertLog(
        node_id=node_id,
        event_type=event_type,
        message=message,
        water_level_cm=water_level_cm,
        pump_active=pump_active,
        created_at=now,
    )
    db.session.add(alert)
    db.session.flush()
    payload = alert.to_dict()
    socketio.emit("new_alert", payload, room=f"node:{node_id}")
    socketio.emit("new_alert", payload)
    return alert


def _emit_node_updates(node: Node, timestamp_iso: str):
    detail_payload = {
        "node_id": node.node_id,
        "name": node.name,
        "status": node.status,
        "mode": node.mode,
        "water_level_cm": round(node.water_level_cm, 2),
        "flow_rate_lpm": round(node.flow_rate_lpm, 2),
        "pump_active": node.pump_active,
        "alert_level": node.alert_level,
        "timestamp": timestamp_iso,
    }
    # For users viewing single node details (water level, flow rate, pump status)
    socketio.emit("telemetry_update", detail_payload, room=f"node:{node.node_id}")
    # For users viewing the overall map of nodes
    socketio.emit("map_node_update", detail_payload)


def process_telemetry(payload: dict, retention_hours: int = 24):
    node_id = str(payload.get("node_id", "")).strip()
    if not node_id:
        return

    water_level = round(float(payload["water_level_cm"]), 2)
    flow_rate = round(float(payload["flow_rate_lpm"]), 2)
    pump_active = bool(payload["pump_active"])
    alert_level = str(payload.get("alert_level", "NORMAL")).upper()
    if alert_level not in VALID_ALERTS:
        alert_level = "NORMAL"

    now = utc_now()
    ts_iso = to_iso_utc(now)
    node = _ensure_node(node_id, is_virtual=False)

    old_alert = node.alert_level
    old_pump = node.pump_active

    node.status = "online"
    node.water_level_cm = water_level
    node.flow_rate_lpm = flow_rate
    node.pump_active = pump_active
    node.alert_level = alert_level
    node.last_seen = now

    db.session.add(
        TelemetryLog(
            node_id=node_id,
            water_level_cm=water_level,
            flow_rate_lpm=flow_rate,
            pump_active=pump_active,
            alert_level=alert_level,
            created_at=now,
        )
    )

    # 1. Use case: Nhận thông báo cảnh báo (Water level threshold transitions)
    if alert_level != old_alert:
        if alert_level == "DANGER":
            msg = f"[{node.name}] Mực nước đạt {water_level} cm - Vượt ngưỡng NGUY HIỂM!"
            _record_event(node_id, "LEVEL_DANGER", msg, water_level, pump_active, now)
            send_node_push(
                node_id=node_id,
                category="alert",
                title=f"CẢNH BÁO NGẬP KHẨN CẤP - {node.name}",
                body=msg,
                data={"node_id": node_id, "alert_level": "DANGER", "water_level_cm": water_level},
            )
        elif alert_level == "WARNING":
            msg = f"[{node.name}] Mực nước đạt {water_level} cm - Mức CẢNH BÁO."
            _record_event(node_id, "LEVEL_WARNING", msg, water_level, pump_active, now)
            send_node_push(
                node_id=node_id,
                category="alert",
                title=f"Cảnh báo mực nước - {node.name}",
                body=msg,
                data={"node_id": node_id, "alert_level": "WARNING", "water_level_cm": water_level},
            )
        elif alert_level == "NORMAL" and old_alert in {"WARNING", "DANGER"}:
            msg = f"[{node.name}] Mực nước rút về {water_level} cm - An toàn."
            _record_event(node_id, "LEVEL_NORMAL", msg, water_level, pump_active, now)

    # 2. Use case: Nhận thông tin máy bơm (Pump state change notifications)
    if pump_active != old_pump:
        event_type = "PUMP_ON" if pump_active else "PUMP_OFF"
        state_label = "ĐÃ BẬT" if pump_active else "ĐÃ TẮT"
        msg = f"[{node.name}] Máy bơm thoát nước {state_label} (lưu lượng {flow_rate} L/phút)."
        _record_event(node_id, event_type, msg, water_level, pump_active, now)
        socketio.emit(
            "pump_status_update",
            {
                "node_id": node_id,
                "pump_active": pump_active,
                "mode": node.mode,
                "flow_rate_lpm": flow_rate,
                "timestamp": ts_iso,
            },
            room=f"node:{node_id}",
        )
        send_node_push(
            node_id=node_id,
            category="pump",
            title=f"Thông tin máy bơm - {node.name}",
            body=msg,
            data={"node_id": node_id, "pump_active": pump_active, "flow_rate_lpm": flow_rate},
        )

    _emit_node_updates(node, ts_iso)

    # Mirror telemetry to virtual demo nodes on the map
    virtual_nodes = Node.query.filter_by(is_virtual=True).all()
    for vnode in virtual_nodes:
        v_level = max(0.0, round(water_level + random.uniform(-1.5, 1.5), 2))
        v_flow = max(0.0, round(flow_rate + random.uniform(-0.2, 0.2), 2))
        v_alert = "DANGER" if v_level >= 16.0 else ("WARNING" if v_level >= 12.0 else "NORMAL")
        vnode.status = "online"
        vnode.water_level_cm = v_level
        vnode.flow_rate_lpm = v_flow
        vnode.pump_active = pump_active
        vnode.alert_level = v_alert
        vnode.last_seen = now

        db.session.add(
            TelemetryLog(
                node_id=vnode.node_id,
                water_level_cm=v_level,
                flow_rate_lpm=v_flow,
                pump_active=pump_active,
                alert_level=v_alert,
                created_at=now,
            )
        )
        _emit_node_updates(vnode, ts_iso)

    if random.random() < 0.01:
        cutoff = now - timedelta(hours=retention_hours)
        TelemetryLog.query.filter(TelemetryLog.created_at < cutoff).delete()

    db.session.commit()


def process_node_status(node_id: str, status: str):
    status = status.strip().lower()
    if status not in {"online", "offline"}:
        return

    now = utc_now()
    ts_iso = to_iso_utc(now)
    node = _ensure_node(node_id, is_virtual=False)
    old_status = node.status
    node.status = status
    node.last_seen = now

    if status != old_status:
        event_type = "NODE_ONLINE" if status == "online" else "NODE_OFFLINE"
        msg = (
            f"[{node.name}] Trạm đo đã kết nối trở lại."
            if status == "online"
            else f"[{node.name}] Mất kết nối tới trạm đo (Offline)!"
        )
        _record_event(node_id, event_type, msg, node.water_level_cm, node.pump_active, now)

    db.session.commit()
    status_payload = {
        "node_id": node_id,
        "status": status,
        "last_seen": ts_iso,
    }
    socketio.emit("node_status", status_payload, room=f"node:{node_id}")
    socketio.emit("node_status", status_payload)
