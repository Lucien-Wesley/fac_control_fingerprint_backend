from typing import Optional, Dict, Any
from sqlalchemy.exc import IntegrityError

from utils.db import db
from utils.validators import is_valid_email, require_non_empty
from models import User


def register_user(data: Dict[str, Any]) -> dict:
    username = require_non_empty(data.get("username"), "username")
    email = require_non_empty(data.get("email"), "email")
    if not is_valid_email(email):
        raise ValueError("Invalid email format")
    password = require_non_empty(data.get("password"), "password")
    role = (data.get("role") or "user").strip() or "user"

    user = User(username=username, email=email, role=role)
    user.set_password(password)

    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ValueError("Username or email already exists")

    return user.to_dict()


def authenticate_user(data: Dict[str, Any]) -> Optional[dict]:
    identifier = require_non_empty(data.get("identifier"), "identifier (username or email)")
    password = require_non_empty(data.get("password"), "password")

    # Find by username or email
    user = User.query.filter(
        (User.username == identifier) | (User.email == identifier)
    ).first()

    if not user or not user.check_password(password):
        return None

    return user.to_dict()
