from flask import Blueprint, jsonify, request, g
from app import db
from app.models import User
from app.services.auth_service import generate_auth_token, login_required

auth_bp = Blueprint("auth_api", __name__, url_prefix="/api/auth")


@auth_bp.post("/register")
def register():
    """Use Case: Tạo tài khoản"""
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    full_name = str(data.get("full_name", "")).strip() or username

    if not username or not email or len(password) < 6:
        return jsonify({"error": "username, email and password (min 6 chars) are required"}), 400

    if User.query.filter((User.username == username) | (User.email == email)).first():
        return jsonify({"error": "Username or email already exists"}), 409

    user = User(username=username, email=email, full_name=full_name)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    token = generate_auth_token(user.id)
    return jsonify({"token": token, "user": user.to_dict()}), 201


@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    identifier = str(data.get("username", "") or data.get("email", "")).strip()
    password = str(data.get("password", ""))

    if not identifier or not password:
        return jsonify({"error": "username/email and password are required"}), 400

    user = User.query.filter(
        (User.username == identifier) | (User.email == identifier.lower())
    ).first()
    if user is None or not user.check_password(password):
        return jsonify({"error": "Invalid credentials"}), 401

    token = generate_auth_token(user.id)
    return jsonify({"token": token, "user": user.to_dict()}), 200


@auth_bp.get("/me")
@login_required
def get_me():
    return jsonify({"user": g.current_user.to_dict()}), 200
