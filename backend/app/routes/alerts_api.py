from flask import Blueprint, jsonify, request
from app.models import AlertLog
from app.services.auth_service import get_optional_current_user

alerts_bp = Blueprint("alerts_api", __name__, url_prefix="/api")


@alerts_bp.get("/alerts")
def list_alerts():
    """
    Use Case: Nhận thông báo cảnh báo & Nhận thông tin máy bơm
    Supports:
      - ?node_id=node_01
      - ?category=alert | pump
      - ?only_subscribed=true (chỉ lấy thông báo của các nút user đã đăng ký theo dõi)
    """
    limit = min(max(request.args.get("limit", default=20, type=int), 1), 200)
    node_id = request.args.get("node_id", type=str)
    category = request.args.get("category", type=str)
    only_subscribed = request.args.get("only_subscribed", default="false").lower() == "true"

    query = AlertLog.query
    if node_id:
        query = query.filter_by(node_id=node_id)
    elif only_subscribed:
        user = get_optional_current_user()
        if user is not None:
            sub_ids = [s.node_id for s in user.subscriptions.all()]
            query = query.filter(AlertLog.node_id.in_(sub_ids)) if sub_ids else query.filter(False)

    if category == "alert":
        query = query.filter(AlertLog.event_type.in_(["LEVEL_WARNING", "LEVEL_DANGER", "LEVEL_NORMAL"]))
    elif category == "pump":
        query = query.filter(AlertLog.event_type.in_(["PUMP_ON", "PUMP_OFF"]))

    alerts = query.order_by(AlertLog.created_at.desc()).limit(limit).all()
    return jsonify({"alerts": [a.to_dict() for a in alerts]}), 200
