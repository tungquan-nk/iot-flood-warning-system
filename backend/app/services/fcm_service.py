import logging
import os
import firebase_admin
from firebase_admin import credentials, messaging
from app.models import FcmToken, NodeSubscription

logger = logging.getLogger(__name__)
_fcm_initialized = False


def init_fcm(cred_path: str):
    global _fcm_initialized
    if _fcm_initialized or not cred_path or not os.path.exists(cred_path):
        return
    try:
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        _fcm_initialized = True
        logger.info("Firebase Admin SDK initialized.")
    except Exception as exc:
        logger.warning("FCM init skipped: %s", exc)


def send_node_push(node_id: str, category: str, title: str, body: str, data: dict | None = None):
    """
    Send push notifications only to devices owned by users subscribed to `node_id`.
    category: 'alert' (water level warning/danger) or 'pump' (pump state change).
    """
    sub_query = NodeSubscription.query.filter_by(node_id=node_id)
    if category == "alert":
        sub_query = sub_query.filter_by(notify_alert=True)
    elif category == "pump":
        sub_query = sub_query.filter_by(notify_pump=True)

    subscribed_user_ids = [s.user_id for s in sub_query.all()]
    if not subscribed_user_ids:
        return

    tokens = [
        row.token
        for row in FcmToken.query.filter(FcmToken.user_id.in_(subscribed_user_ids)).all()
    ]
    if not tokens:
        return

    if not _fcm_initialized:
        logger.info("[FCM MOCK -> node=%s, users=%s] %s: %s", node_id, subscribed_user_ids, title, body)
        return

    message = messaging.MulticastMessage(
        notification=messaging.Notification(title=title, body=body),
        data={k: str(v) for k, v in (data or {}).items()},
        tokens=tokens,
    )
    try:
        response = messaging.send_each_for_multicast(message)
        logger.info("FCM sent for %s: success=%d, failure=%d", node_id, response.success_count, response.failure_count)
    except Exception as exc:
        logger.error("FCM send error: %s", exc)
