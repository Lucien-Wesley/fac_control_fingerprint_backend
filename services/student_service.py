from typing import List, Optional, Dict, Any
from sqlalchemy.exc import IntegrityError

from utils.db import db
from utils.validators import is_valid_email, require_non_empty
from models import Student
from utils.arduino import arduino_manager


def get_all_students() -> List[dict]:
    students = Student.query.order_by(Student.id.desc()).all()
    return [s.to_dict() for s in students]


def create_student(data: Dict[str, Any]) -> dict:
    name = require_non_empty(data.get("name"), "name")
    email = require_non_empty(data.get("email"), "email")
    if not is_valid_email(email):
        raise ValueError("Invalid email format")
    major = (data.get("major") or "").strip() or None
    max_retries = int(data.get("fingerprint_retries") or 3)

    # Create the student transiently to get an auto-incremented ID
    student = Student(name=name, email=email, major=major)
    db.session.add(student)
    try:
        # Flush to assign ID without committing
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        raise ValueError("Email already exists")

    # Perform biometric capture via Arduino before final commit
    success, message = arduino_manager.capture_fingerprint(
        entity="student", entity_id=student.id, max_retries=max_retries
    )
    if not success:
        db.session.rollback()
        raise ValueError(f"Fingerprint verification failed: {message}")

    # Mark verified and commit
    student.fingerprint_verified = True
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ValueError("Email already exists")

    return student.to_dict()


def update_student(student_id: int, data: Dict[str, Any]) -> Optional[dict]:
    student = Student.query.get(student_id)
    if not student:
        return None

    if "name" in data:
        student.name = require_non_empty(data.get("name"), "name")
    if "email" in data:
        email = require_non_empty(data.get("email"), "email")
        if not is_valid_email(email):
            raise ValueError("Invalid email format")
        student.email = email
    if "major" in data:
        major = (data.get("major") or "").strip() or None
        student.major = major

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ValueError("Email already exists")

    return student.to_dict()


def delete_student(student_id: int) -> bool:
    student = Student.query.get(student_id)
    if not student:
        return False
    db.session.delete(student)
    db.session.commit()
    return True
