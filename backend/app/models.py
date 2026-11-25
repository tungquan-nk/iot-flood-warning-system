from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from app import db


def utc_now():
    return datetime.now(timezone.utc)


def to_iso_utc(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)

    subscriptions = db.relationship(
        "NodeSubscription", backref="user", lazy="dynamic", cascade="all, delete-orphan"
    )
    fcm_tokens = db.relationship(
        "FcmToken", backref="user", lazy="dynamic", cascade="all, delete-orphan"
    )

    def set_password(self, raw_password: str):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)

    def to_dict(self):
        subscribed_ids = [s.node_id for s in self.subscriptions.all()]
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "subscribed_node_ids": subscribed_ids,
            "created_at": to_iso_utc(self.created_at),
        }


class Node(db.Model):
    __tablename__ = "nodes"

    node_id = db.Column(db.String(32), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    location_desc = db.Column(db.String(255), nullable=True)
    latitude = db.Column(db.Float, nullable=False, default=21.0075)
    longitude = db.Column(db.Float, nullable=False, default=105.8394)
    is_virtual = db.Column(db.Boolean, nullable=False, default=False)
    status = db.Column(db.String(16), nullable=False, default="offline")
    mode = db.Column(db.String(16), nullable=False, default="AUTO")
    water_level_cm = db.Column(db.Float, nullable=False, default=0.0)
    flow_rate_lpm = db.Column(db.Float, nullable=False, default=0.0)
    pump_active = db.Column(db.Boolean, nullable=False, default=False)
    alert_level = db.Column(db.String(16), nullable=False, default="NORMAL")
    last_seen = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)

    telemetry_logs = db.relationship(
        "TelemetryLog", backref="node", lazy="dynamic", cascade="all, delete-orphan"
    )
    alert_logs = db.relationship(
        "AlertLog", backref="node", lazy="dynamic", cascade="all, delete-orphan"
    )
    subscribers = db.relationship(
        "NodeSubscription", backref="node", lazy="dynamic", cascade="all, delete-orphan"
    )

    def to_dict(self, subscribed_node_ids: set[str] | None = None):
        is_sub = (self.node_id in subscribed_node_ids) if subscribed_node_ids is not None else False
        return {
            "node_id": self.node_id,
            "name": self.name,
            "location_desc": self.location_desc,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "is_virtual": self.is_virtual,
            "status": self.status,
            "mode": self.mode,
            "water_level_cm": round(self.water_level_cm, 2),
            "flow_rate_lpm": round(self.flow_rate_lpm, 2),
            "pump_active": self.pump_active,
            "alert_level": self.alert_level,
            "is_subscribed": is_sub,
            "subscriber_count": self.subscribers.count(),
            "last_seen": to_iso_utc(self.last_seen),
        }


class NodeSubscription(db.Model):
    __tablename__ = "node_subscriptions"
    __table_args__ = (
        db.UniqueConstraint("user_id", "node_id", name="uq_user_node_subscription"),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    node_id = db.Column(
        db.String(32), db.ForeignKey("nodes.node_id", ondelete="CASCADE"), nullable=False, index=True
    )
    notify_alert = db.Column(db.Boolean, nullable=False, default=True)
    notify_pump = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "node_id": self.node_id,
            "notify_alert": self.notify_alert,
            "notify_pump": self.notify_pump,
            "created_at": to_iso_utc(self.created_at),
        }


class TelemetryLog(db.Model):
    __tablename__ = "telemetry_logs"
    __table_args__ = (
        db.Index("idx_telemetry_node_time", "node_id", "created_at"),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    node_id = db.Column(
        db.String(32), db.ForeignKey("nodes.node_id", ondelete="CASCADE"), nullable=False
    )
    water_level_cm = db.Column(db.Float, nullable=False)
    flow_rate_lpm = db.Column(db.Float, nullable=False)
    pump_active = db.Column(db.Boolean, nullable=False)
    alert_level = db.Column(db.String(16), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "node_id": self.node_id,
            "water_level_cm": round(self.water_level_cm, 2),
            "flow_rate_lpm": round(self.flow_rate_lpm, 2),
            "pump_active": self.pump_active,
            "alert_level": self.alert_level,
            "timestamp": to_iso_utc(self.created_at),
        }


class AlertLog(db.Model):
    __tablename__ = "alert_logs"
    __table_args__ = (
        db.Index("idx_alert_node_time", "node_id", "created_at"),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    node_id = db.Column(
        db.String(32), db.ForeignKey("nodes.node_id", ondelete="CASCADE"), nullable=False
    )
    event_type = db.Column(db.String(32), nullable=False)
    message = db.Column(db.Text, nullable=False)
    water_level_cm = db.Column(db.Float, nullable=True)
    pump_active = db.Column(db.Boolean, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "node_id": self.node_id,
            "event_type": self.event_type,
            "message": self.message,
            "water_level_cm": round(self.water_level_cm, 2) if self.water_level_cm is not None else None,
            "pump_active": self.pump_active,
            "created_at": to_iso_utc(self.created_at),
        }


class FcmToken(db.Model):
    __tablename__ = "fcm_tokens"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    token = db.Column(db.String(255), unique=True, nullable=False)
    device_name = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
