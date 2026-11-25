from functools import wraps
from flask import current_app, jsonify, request, g
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from app import db
from app.models import User


def _get_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="flood-auth-token")


def generate_auth_token(user_id: int) -> str:
    return _get_serializer().dumps({"user_id": user_id})


def verify_auth_token(token: str) -> User | None:
    if not token:
        return None
    max_age = current_app.config.get("TOKEN_MAX_AGE_SECONDS", 604800)
    try:
        data = _get_serializer().loads(token, max_age=max_age)
        return db.session.get(User, data.get("user_id"))
    except (BadSignature, SignatureExpired):
        return None


def get_optional_current_user() -> User | None:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        return verify_auth_token(token)
    return None


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = get_optional_current_user()
        if user is None:
            return jsonify({"error": "Authentication required. Please login."}), 401
        g.current_user = user
        return fn(*args, **kwargs)

    return wrapper
