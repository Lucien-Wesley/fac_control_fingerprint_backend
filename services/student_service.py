from typing import List, Optional, Dict, Any
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func

from utils.db import db
from utils.validators import is_valid_email, require_non_empty
from models import Student
from utils.arduino import arduino_manager


def get_all_students() -> List[dict]:
    students = Student.query.order_by(Student.id.desc()).all()
    return [s.to_dict() for s in students]


def create_student(data: Dict[str, Any]) -> dict:
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
    major = (data.get("major") or "").strip() or None
    student_number = (data.get("studentNumber") or data.get("student_number") or "").strip() or None
    year = data.get("year")
    if year is not None and year != "":
        try:
            year = int(year)
        except Exception:
            raise ValueError("'year' must be an integer")
    fingerprint_id = (data.get("fingerprintId") or data.get("fingerprint_id") or None)
    max_retries = int(data.get("fingerprint_retries") or 3)

    # Create the student transiently to get an auto-incremented ID
    student = Student(
        name=name,
        first_name=first_name,
        last_name=last_name,
        email=email,
        major=major,
        student_number=student_number,
        year=year,
        fingerprint_id=fingerprint_id,
    )
    db.session.add(student)
    try:
        # Flush to assign ID without committing
        db.session.flush()
        # Compute fingerprint numeric id as the sum of IDs created before this record.
        # We approximate "created before" by summing student IDs < this id and all professor IDs.
        sum_students_before = db.session.query(func.coalesce(func.sum(Student.id), 0)).filter(Student.id < student.id).scalar() or 0
        # Import Professor lazily to avoid circular imports at module load
        from models import Professor

        sum_professors = db.session.query(func.coalesce(func.sum(Professor.id), 0)).scalar() or 0
        fingerprint_num = int(sum_students_before + sum_professors)
        # Ensure fingerprint id is at least 1
        if fingerprint_num < 1:
            fingerprint_num = 1
        # Tentatively set numeric fingerprint_id on the model as string
        student.fingerprint_id = str(fingerprint_num)
    except IntegrityError:
        db.session.rollback()
        raise ValueError("A unique constraint was violated (email/student number?)")

    # # Perform biometric capture via Arduino before final commit using the computed fingerprint id
    # try:
    #     fid_int = int(student.fingerprint_id)
    # except Exception:
    #     fid_int = int(student.id)

    # success, message = arduino_manager.capture_fingerprint(
    #     entity="student", entity_id=fid_int, max_retries=max_retries
    # )
    # if not success:
    #     db.session.rollback()
    #     raise ValueError(f"Fingerprint verification failed: {message}")

    # # Mark verified (fingerprint_id already set to computed value)
    # student.fingerprint_verified = True
    # try:
    #     db.session.commit()
    # except IntegrityError:
    #     db.session.rollback()
    #     raise ValueError("A unique constraint was violated (email/student number?)")

    return student.to_dict()


def update_student(student_id: int, data: Dict[str, Any]) -> Optional[dict]:
    student = Student.query.get(student_id)
    if not student:
        return None
    # Updates: accept name parts and new fields
    if "name" in data:
        student.name = require_non_empty(data.get("name"), "name")
    if "firstName" in data or "first_name" in data:
        student.first_name = (data.get("firstName") or data.get("first_name") or "").strip() or None
    if "lastName" in data or "last_name" in data:
        student.last_name = (data.get("lastName") or data.get("last_name") or "").strip() or None
    if "email" in data:
        email = require_non_empty(data.get("email"), "email")
        if not is_valid_email(email):
            raise ValueError("Invalid email format")
        student.email = email
    if "major" in data:
        major = (data.get("major") or "").strip() or None
        student.major = major
    if "studentNumber" in data or "student_number" in data:
        student.student_number = (data.get("studentNumber") or data.get("student_number") or "").strip() or None
    if "year" in data:
        year = data.get("year")
        if year is not None and year != "":
            try:
                student.year = int(year)
            except Exception:
                raise ValueError("'year' must be an integer")
        else:
            student.year = None
    if "fingerprintId" in data or "fingerprint_id" in data:
        student.fingerprint_id = (data.get("fingerprintId") or data.get("fingerprint_id") or None)
    if "fingerprint_verified" in data:
        student.fingerprint_verified = bool(data.get("fingerprint_verified"))

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
