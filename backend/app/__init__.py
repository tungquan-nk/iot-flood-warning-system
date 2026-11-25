from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, join_room, leave_room
from flask_cors import CORS
from app.config import Config

db = SQLAlchemy()
socketio = SocketIO(cors_allowed_origins="*", async_mode="threading")


@socketio.on("join_node")
def handle_join_node(data):
    node_id = (data or {}).get("node_id")
    if node_id:
        join_room(f"node:{node_id}")


@socketio.on("leave_node")
def handle_leave_node(data):
    node_id = (data or {}).get("node_id")
    if node_id:
        leave_room(f"node:{node_id}")


def _seed_initial_nodes():
    from app.models import Node

    default_nodes = [
        {
            "node_id": "node_01",
            "name": "Hầm chui Kim Liên",
            "location_desc": "Nút giao Xã Đàn - Giải Phóng, Đống Đa, Hà Nội",
            "latitude": 21.0075,
            "longitude": 105.8394,
            "is_virtual": False,
        },
        {
            "node_id": "node_02",
            "name": "Cống thoát nước Nguyễn Trãi",
            "location_desc": "Đường Nguyễn Trãi, Thanh Xuân, Hà Nội (Node ảo)",
            "latitude": 20.9952,
            "longitude": 105.8124,
            "is_virtual": True,
        },
        {
            "node_id": "node_03",
            "name": "Hầm chui Trung Hòa",
            "location_desc": "Đại lộ Thăng Long - Trần Duy Hưng, Cầu Giấy, Hà Nội (Node ảo)",
            "latitude": 21.0089,
            "longitude": 105.7925,
            "is_virtual": True,
        },
    ]
    created = False
    for item in default_nodes:
        if db.session.get(Node, item["node_id"]) is None:
            db.session.add(Node(**item, status="offline"))
            created = True
    if created:
        db.session.commit()


def create_app(config_class=Config, start_mqtt=True):
    app = Flask(__name__)
    app.config.from_object(config_class)

    CORS(app)
    db.init_app(app)
    socketio.init_app(app)

    from app.routes.auth_api import auth_bp
    from app.routes.nodes_api import nodes_bp
    from app.routes.alerts_api import alerts_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(nodes_bp)
    app.register_blueprint(alerts_bp)

    with app.app_context():
        db.create_all()
        _seed_initial_nodes()

    from app.services.fcm_service import init_fcm
    init_fcm(app.config.get("FIREBASE_CRED_PATH", ""))

    if start_mqtt:
        from app.mqtt_client import mqtt_manager
        mqtt_manager.init_app(app)

    return app
