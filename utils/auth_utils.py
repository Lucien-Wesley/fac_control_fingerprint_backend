from functools import wraps
from typing import Callable

from flask import jsonify
from flask_jwt_extended import get_jwt


def roles_required(*roles: str) -> Callable:
    """
    Require that the authenticated user has one of the specified roles.
    Should be used together with @jwt_required().
    Example:
        @jwt_required()
        @roles_required("admin")
        def route(): ...
    """

    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            claims = get_jwt() or {}
            role = claims.get("role")
            if roles and role not in roles:
                return jsonify({"error": "Forbidden: insufficient role"}), 403
            return fn(*args, **kwargs)

        return wrapper

    return decorator
