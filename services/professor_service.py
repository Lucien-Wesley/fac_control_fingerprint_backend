from typing import List, Optional, Dict, Any
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func

from utils.db import db
from utils.validators import is_valid_email, require_non_empty
from models import Professor
from utils.arduino import arduino_manager


def get_all_professors() -> List[dict]:
    professors = Professor.query.order_by(Professor.id.desc()).all()
    return [p.to_dict() for p in professors]


def create_professor(data: Dict[str, Any]) -> dict:
    # Accept either full name or firstName/lastName
    first_name = (data.get("firstName") or data.get("first_name") or "").strip() or None
    last_name = (data.get("lastName") or data.get("last_name") or "").strip() or None
    raw_name = data.get("name")
    if raw_name:
        name = require_non_empty(raw_name, "name")
    elif first_name:
        name = f"{first_name} {last_name or ''}".strip()
    else:
        raise ValueError("'name' or 'firstName' is required")

    email = require_non_empty(data.get("email"), "email")
    if not is_valid_email(email):
        raise ValueError("Invalid email format")
    department = (data.get("department") or "").strip() or None
    employee_number = (data.get("employeeNumber") or data.get("employee_number") or "").strip() or None
    title = (data.get("title") or "").strip() or None
    fingerprint_id = (data.get("fingerprintId") or data.get("fingerprint_id") or None)
    max_retries = int(data.get("fingerprint_retries") or 3)

    # Create the professor transiently to get an auto-incremented ID
    professor = Professor(
        name=name,
        first_name=first_name,
        last_name=last_name,
        email=email,
        department=department,
        employee_number=employee_number,
        title=title,
        fingerprint_id=fingerprint_id,
    )
    db.session.add(professor)
    # try:
    #     # Flush to assign ID without committing
    #     db.session.flush()
    #     # Compute fingerprint numeric id as the sum of IDs created before this record.
    #     # Sum professor IDs < this id and all student IDs.
    #     sum_professors_before = db.session.query(func.coalesce(func.sum(Professor.id), 0)).filter(Professor.id < professor.id).scalar() or 0
    #     from models import Student
    #     sum_students = db.session.query(func.coalesce(func.sum(Student.id), 0)).scalar() or 0
    #     fingerprint_num = int(sum_professors_before + sum_students)
    #     if fingerprint_num < 1:
    #         fingerprint_num = 1
    #     professor.fingerprint_id = str(fingerprint_num)
    # except IntegrityError:
    #     db.session.rollback()
    #     raise ValueError("A unique constraint was violated (email/employee number?)")

    # # Perform biometric capture via Arduino before final commit using the computed fingerprint id
    # try:
    #     fid_int = int(professor.fingerprint_id)
    # except Exception:
    #     fid_int = int(professor.id)

    # success, message = arduino_manager.capture_fingerprint(
    #     entity="professor", entity_id=fid_int, max_retries=max_retries
    # )
    # if not success:
    #     db.session.rollback()
    #     raise ValueError(f"Fingerprint verification failed: {message}")

    # # Mark verified (fingerprint_id already set to computed value)
    # professor.fingerprint_verified = True
    # try:
    #     db.session.commit()
    # except IntegrityError:
    #     db.session.rollback()
    #     raise ValueError("A unique constraint was violated (email/employee number?)")

    return professor.to_dict()


def update_professor(professor_id: int, data: Dict[str, Any]) -> Optional[dict]:
    professor = Professor.query.get(professor_id)
    if not professor:
        return None

    # Updates: accept name parts and new fields
    if "name" in data:
        professor.name = require_non_empty(data.get("name"), "name")
    if "firstName" in data or "first_name" in data:
        professor.first_name = (data.get("firstName") or data.get("first_name") or "").strip() or None
    if "lastName" in data or "last_name" in data:
        professor.last_name = (data.get("lastName") or data.get("last_name") or "").strip() or None
    if "email" in data:
        email = require_non_empty(data.get("email"), "email")
        if not is_valid_email(email):
            raise ValueError("Invalid email format")
        professor.email = email
    if "department" in data:
        department = (data.get("department") or "").strip() or None
        professor.department = department
    if "employeeNumber" in data or "employee_number" in data:
        professor.employee_number = (data.get("employeeNumber") or data.get("employee_number") or "").strip() or None
    if "title" in data:
        professor.title = (data.get("title") or "").strip() or None
    if "fingerprintId" in data or "fingerprint_id" in data:
        professor.fingerprint_id = (data.get("fingerprintId") or data.get("fingerprint_id") or None)
    if "fingerprint_verified" in data:
        professor.fingerprint_verified = bool(data.get("fingerprint_verified"))

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
