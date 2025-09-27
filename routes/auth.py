from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token

from services.auth_service import register_user, authenticate_user

auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/register")
def register():
    data = request.get_json(force=True, silent=True) or {}
    try:
        user = register_user(data)
        return jsonify(user), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception:
        return jsonify({"error": "Registration failed"}), 500


@auth_bp.post("/login")
def login():
    data = request.get_json(force=True, silent=True) or {}
    print(data)
    try:
        user = authenticate_user(data)
        print(user)
        if not user:
            return jsonify({"error": "Invalid credentials"}), 401
        # Identity must be a string to avoid 422 errors; include role as additional claim
        token = create_access_token(
            identity=str(user["id"]),
            additional_claims={"role": user["role"], "username": user.get("username")},
        )
        return jsonify({"access_token": token, "user": user, "success": True}), 200
    except ValueError as e:
        print(e)
        return jsonify({"error": str(e)}), 400
    except Exception:
        return jsonify({"error": "Login failed"}), 500
