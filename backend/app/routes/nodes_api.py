from flask import Blueprint, jsonify, request, g
from app import db, socketio
from app.models import Node, NodeSubscription, TelemetryLog, AlertLog, FcmToken
from app.mqtt_client import mqtt_manager
from app.services.auth_service import get_optional_current_user, login_required

nodes_bp = Blueprint("nodes_api", __name__, url_prefix="/api")


def _get_user_subscribed_ids() -> set[str]:
    user = get_optional_current_user()
    if user is None:
        return set()
    return {s.node_id for s in user.subscriptions.all()}


@nodes_bp.get("/health")
def health_check():
    mqtt_ok = bool(mqtt_manager.client and mqtt_manager.client.is_connected())
    return jsonify({"status": "ok", "mqtt_connected": mqtt_ok}), 200


@nodes_bp.get("/nodes")
def list_nodes():
    """Use Case: Xem được bản đồ các nút (trả về tọa độ lat/lng + trạng thái từng nút)"""
    sub_ids = _get_user_subscribed_ids()
    nodes = Node.query.order_by(Node.node_id.asc()).all()
    return jsonify({"nodes": [n.to_dict(sub_ids) for n in nodes]}), 200


@nodes_bp.get("/nodes/<node_id>")
def get_node_detail(node_id: str):
    """
    Use Case: Xem chi tiết một nút:
    - Xem mực nước hiện tại (water_level_cm, alert_level)
    - Xem tốc độ thoát nước hiện tại (flow_rate_lpm)
    - Nhận thông tin máy bơm (pump_active, mode, lịch sử bơm gần nhất)
    - Nhận thông báo cảnh báo (recent_alerts của riêng nút này)
    """
    node = db.session.get(Node, node_id)
    if node is None:
        return jsonify({"error": "Node not found"}), 404

    sub_ids = _get_user_subscribed_ids()
    limit = min(max(request.args.get("limit", default=30, type=int), 1), 500)

    telemetry_rows = (
        TelemetryLog.query.filter_by(node_id=node_id)
        .order_by(TelemetryLog.created_at.desc())
        .limit(limit)
        .all()
    )
    telemetry_rows.reverse()

    recent_alerts = (
        AlertLog.query.filter_by(node_id=node_id)
        .order_by(AlertLog.created_at.desc())
        .limit(10)
        .all()
    )

    return jsonify({
        "node": node.to_dict(sub_ids),
        "telemetry": [t.to_dict() for t in telemetry_rows],
        "recent_alerts": [a.to_dict() for a in recent_alerts],
    }), 200


@nodes_bp.post("/nodes")
def create_node():
    data = request.get_json(silent=True) or {}
    node_id = str(data.get("node_id", "")).strip()
    name = str(data.get("name", "")).strip()
    if not node_id or not name:
        return jsonify({"error": "node_id and name are required"}), 400

    if db.session.get(Node, node_id):
        return jsonify({"error": "node_id already exists"}), 409

    node = Node(
        node_id=node_id,
        name=name,
        location_desc=data.get("location_desc", ""),
        latitude=float(data.get("latitude", 21.0075)),
        longitude=float(data.get("longitude", 105.8394)),
        is_virtual=bool(data.get("is_virtual", False)),
    )
    db.session.add(node)
    db.session.commit()
    return jsonify({"node": node.to_dict()}), 201


@nodes_bp.get("/nodes/<node_id>/telemetry")
def get_node_telemetry(node_id: str):
    node = db.session.get(Node, node_id)
    if node is None:
        return jsonify({"error": "Node not found"}), 404

    limit = min(max(request.args.get("limit", default=30, type=int), 1), 500)
    rows = (
        TelemetryLog.query.filter_by(node_id=node_id)
        .order_by(TelemetryLog.created_at.desc())
        .limit(limit)
        .all()
    )
    rows.reverse()
    return jsonify({"node_id": node_id, "count": len(rows), "telemetry": [r.to_dict() for r in rows]}), 200


@nodes_bp.post("/nodes/<node_id>/subscribe")
@login_required
def subscribe_node(node_id: str):
    """Use Case: Đăng ký theo dõi 1 nút"""
    node = db.session.get(Node, node_id)
    if node is None:
        return jsonify({"error": "Node not found"}), 404

    data = request.get_json(silent=True) or {}
    notify_alert = bool(data.get("notify_alert", True))
    notify_pump = bool(data.get("notify_pump", True))

    sub = NodeSubscription.query.filter_by(user_id=g.current_user.id, node_id=node_id).first()
    if sub is None:
        sub = NodeSubscription(
            user_id=g.current_user.id,
            node_id=node_id,
            notify_alert=notify_alert,
            notify_pump=notify_pump,
        )
        db.session.add(sub)
    else:
        sub.notify_alert = notify_alert
        sub.notify_pump = notify_pump

    db.session.commit()
    return jsonify({
        "status": "subscribed",
        "subscription": sub.to_dict(),
        "node": node.to_dict({node_id}),
    }), 200


@nodes_bp.delete("/nodes/<node_id>/subscribe")
@login_required
def unsubscribe_node(node_id: str):
    sub = NodeSubscription.query.filter_by(user_id=g.current_user.id, node_id=node_id).first()
    if sub is not None:
        db.session.delete(sub)
        db.session.commit()
    return jsonify({"status": "unsubscribed", "node_id": node_id}), 200


@nodes_bp.get("/subscriptions")
@login_required
def list_my_subscriptions():
    subs = NodeSubscription.query.filter_by(user_id=g.current_user.id).all()
    sub_ids = {s.node_id for s in subs}
    nodes = Node.query.filter(Node.node_id.in_(sub_ids)).all() if sub_ids else []
    return jsonify({
        "subscriptions": [s.to_dict() for s in subs],
        "nodes": [n.to_dict(sub_ids) for n in nodes],
    }), 200


@nodes_bp.post("/nodes/<node_id>/command")
def send_node_command(node_id: str):
    node = db.session.get(Node, node_id)
    if node is None:
        return jsonify({"error": "Node not found"}), 404

    data = request.get_json(silent=True) or {}
    mode = str(data.get("mode", "MANUAL")).upper()
    if mode not in {"AUTO", "MANUAL"}:
        return jsonify({"error": "mode must be AUTO or MANUAL"}), 400

    pump_command = bool(data.get("pump_command", False))
    published = mqtt_manager.publish_command(node_id, mode, pump_command)

    node.mode = mode
    if mode == "MANUAL":
        node.pump_active = pump_command
    db.session.commit()

    ack_payload = {
        "node_id": node_id,
        "mode": mode,
        "pump_command": pump_command,
        "mqtt_delivered": published,
    }
    socketio.emit("command_ack", ack_payload, room=f"node:{node_id}")
    return jsonify(ack_payload), 200


@nodes_bp.post("/devices/fcm-token")
def register_fcm_token():
    data = request.get_json(silent=True) or {}
    token = str(data.get("token", "")).strip()
    if not token:
        return jsonify({"error": "token is required"}), 400

    user = get_optional_current_user()
    existing = FcmToken.query.filter_by(token=token).first()
    if existing is None:
        db.session.add(
            FcmToken(
                user_id=user.id if user else None,
                token=token,
                device_name=data.get("device_name"),
            )
        )
    else:
        if user is not None:
            existing.user_id = user.id
        if data.get("device_name"):
            existing.device_name = data.get("device_name")

    db.session.commit()
    return jsonify({"status": "registered", "linked_user_id": user.id if user else None}), 201
