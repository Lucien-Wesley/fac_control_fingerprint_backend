from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

from utils.db import db


class TimestampMixin:
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class Student(db.Model, TimestampMixin):
    __tablename__ = "students"
    id = db.Column(db.Integer, primary_key=True)
    # Keep legacy full-name field but prefer first/last
    name = db.Column(db.String(120), nullable=True)
    first_name = db.Column(db.String(80), nullable=True)
    last_name = db.Column(db.String(80), nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    major = db.Column(db.String(120), nullable=True)
    # New fields requested by the frontend interface
    student_number = db.Column(db.String(64), unique=True, nullable=True)
    year = db.Column(db.Integer, nullable=True)
    fingerprint_id = db.Column(db.String(128), nullable=True)
    fingerprint_verified = db.Column(db.Boolean, default=False, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            # Prefer firstName/lastName for the frontend; fall back to legacy name
            "firstName": self.first_name if self.first_name else (self.name.split()[0] if self.name else None),
            "lastName": self.last_name if self.last_name else (" ".join(self.name.split()[1:]) if self.name and len(self.name.split()) > 1 else None),
            "email": self.email,
            "major": self.major,
            "studentNumber": self.student_number,
            "year": self.year,
            "fingerprintId": self.fingerprint_id,
            "fingerprint_verified": self.fingerprint_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Professor(db.Model, TimestampMixin):
    __tablename__ = "professors"
    id = db.Column(db.Integer, primary_key=True)
    # Keep legacy single-name field for backwards compatibility but prefer first/last
    name = db.Column(db.String(120), nullable=True)
    first_name = db.Column(db.String(80), nullable=True)
    last_name = db.Column(db.String(80), nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    department = db.Column(db.String(120), nullable=True)
    # New fields requested by the frontend interface
    employee_number = db.Column(db.String(64), unique=True, nullable=True)
    title = db.Column(db.String(120), nullable=True)
    fingerprint_id = db.Column(db.String(128), nullable=True)
    fingerprint_verified = db.Column(db.Boolean, default=False, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            # Provide firstName/lastName for the frontend; fall back to legacy name when missing
            "firstName": self.first_name if self.first_name else (self.name.split()[0] if self.name else None),
            "lastName": self.last_name if self.last_name else (" ".join(self.name.split()[1:]) if self.name and len(self.name.split()) > 1 else None),
            "email": self.email,
            "department": self.department,
            "employeeNumber": self.employee_number,
            "title": self.title,
            "fingerprintId": self.fingerprint_id,
            "fingerprint_verified": self.fingerprint_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class User(db.Model, TimestampMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="user")  # admin, student, professor, user

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class AccessLog(db.Model):
    __tablename__ = "access_logs"
    id = db.Column(db.Integer, primary_key=True)
    entity_type = db.Column(db.String(20), nullable=False)  # 'student' or 'professor'
    entity_id = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), nullable=False)  # 'granted' or 'denied'
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
