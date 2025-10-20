from flask import Blueprint, jsonify, request
from utils.arduino import arduino_manager
import uuid

from services.student_service import (
    get_all_students,
    create_student,
    update_student,
    delete_student,
)

students_bp = Blueprint("students", __name__)

# In-memory session store for biometric enrollment (for demo; replace with DB/cache in prod)
biometric_sessions = {}
@students_bp.post("/biometric/enroll")
def start_biometric_enrollment():
    data = request.get_json(force=True, silent=True) or {}
    student_id = data.get("studentId")
    try:
        student_id = int(student_id)
    except Exception:
        print(f"Invalid studentId: {student_id}")
        return jsonify({"success": False, "error": "Invalid studentId"}), 400
    session_id = str(uuid.uuid4())
    biometric_sessions[session_id] = {
        "student_id": student_id,
        "status": "pending",
        "result": None
    }
    print(f"Starting biometric enrollment for student ID {student_id} with session ID {session_id}")
    # Start enrollment (simulate async, but run inline for now)
    max_retries: int = 3
    per_try_timeout: float = 40.0
    success, message = arduino_manager.enroll_fingerprint(entity_id=student_id, max_retries=max_retries, per_try_timeout=per_try_timeout)
    biometric_sessions[session_id]["status"] = "success" if success else "failed"
    biometric_sessions[session_id]["result"] = message
    return jsonify({"success": success, "sessionId": session_id, "message": message})


@students_bp.get("/biometric/status/<session_id>")
def get_biometric_status(session_id):
    session = biometric_sessions.get(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404
    return jsonify({"status": session["status"], "result": session["result"]})


@students_bp.delete("/biometric/session/<session_id>")
def cancel_biometric_session(session_id):
    session = biometric_sessions.get(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404
    # Simulate cancel (real implementation would signal hardware)
    session["status"] = "cancelled"
    return jsonify({"success": True})


@students_bp.post("/biometric/verify")
def verify_student_fingerprint():
    data = request.get_json(force=True, silent=True) or {}
    student_id = data.get("studentId")
    try:
        student_id = int(student_id)
    except Exception:
        return jsonify({"success": False, "error": "Invalid studentId"}), 400
    success, message, matched_id = arduino_manager.verify_fingerprint(expected_id=student_id)
    confidence = 100 if success else 0  # Simulate confidence
    return jsonify({"success": success, "confidence": confidence, "message": message, "matchedId": matched_id})


@students_bp.get("")
def list_students():
    students = get_all_students()
    print(students)
    return jsonify(students)


@students_bp.post("")
def add_student():
    data = request.get_json(force=True, silent=True) or {}
    try:
        student = create_student(data)
        return jsonify(student), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception:
        return jsonify({"error": "Failed to create student"}), 500


@students_bp.put("/<int:student_id>")
def edit_student(student_id: int):
    data = request.get_json(force=True, silent=True) or {}
    try:
        student = update_student(student_id, data)
        if not student:
            return jsonify({"error": "Student not found"}), 404
        return jsonify(student)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception:
        return jsonify({"error": "Failed to update student"}), 500


@students_bp.delete("/<int:student_id>")
def remove_student(student_id: int):
    try:
        deleted = delete_student(student_id)
        if not deleted:
            return jsonify({"error": "Student not found"}), 404
        return jsonify({"success": True})
    except Exception:
        return jsonify({"error": "Failed to delete student"}), 500


