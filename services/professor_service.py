from typing import List, Optional, Dict, Any
from sqlalchemy.exc import IntegrityError

from utils.db import db
from utils.validators import is_valid_email, require_non_empty
from models import Professor
from utils.arduino import arduino_manager


def get_all_professors() -> List[dict]:
    professors = Professor.query.order_by(Professor.id.desc()).all()
    return [p.to_dict() for p in professors]


def create_professor(data: Dict[str, Any]) -> dict:
    name = require_non_empty(data.get("name"), "name")
    email = require_non_empty(data.get("email"), "email")
    if not is_valid_email(email):
        raise ValueError("Invalid email format")
    department = (data.get("department") or "").strip() or None
    max_retries = int(data.get("fingerprint_retries") or 3)

    # Create the professor transiently to get an auto-incremented ID
    professor = Professor(name=name, email=email, department=department)
    db.session.add(professor)
    try:
        # Flush to assign ID without committing
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        raise ValueError("Email already exists")

    # Perform biometric capture via Arduino before final commit
    success, message = arduino_manager.capture_fingerprint(
        entity="professor", entity_id=professor.id, max_retries=max_retries
    )
    if not success:
        db.session.rollback()
        raise ValueError(f"Fingerprint verification failed: {message}")

    # Mark verified and commit
    professor.fingerprint_verified = True
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ValueError("Email already exists")

    return professor.to_dict()


def update_professor(professor_id: int, data: Dict[str, Any]) -> Optional[dict]:
    professor = Professor.query.get(professor_id)
    if not professor:
        return None

    if "name" in data:
        professor.name = require_non_empty(data.get("name"), "name")
    if "email" in data:
        email = require_non_empty(data.get("email"), "email")
        if not is_valid_email(email):
            raise ValueError("Invalid email format")
        professor.email = email
    if "department" in data:
        department = (data.get("department") or "").strip() or None
        professor.department = department

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ValueError("Email already exists")

    return professor.to_dict()


def delete_professor(professor_id: int) -> bool:
    professor = Professor.query.get(professor_id)
    if not professor:
        return False
    db.session.delete(professor)
    db.session.commit()
    return True
