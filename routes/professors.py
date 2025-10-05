from flask import Blueprint, jsonify, request
from utils.arduino import arduino_manager
import uuid

from services.professor_service import (
    get_all_professors,
    create_professor,
    update_professor,
    delete_professor,
)

professors_bp = Blueprint("professors", __name__)

# In-memory session store for biometric enrollment (for demo; replace with DB/cache in prod)
biometric_sessions = {}
@professors_bp.post("/biometric/enroll")
def start_biometric_enrollment():
    data = request.get_json(force=True, silent=True) or {}
    professor_id = data.get("professorId")
    try:
        professor_id = int(professor_id)
    except Exception:
        return jsonify({"success": False, "error": "Invalid professorId"}), 400
    session_id = str(uuid.uuid4())
    biometric_sessions[session_id] = {
        "professor_id": professor_id,
        "status": "pending",
        "result": None
    }
    # Start enrollment (simulate async, but run inline for now)
    success, message = arduino_manager.enroll_fingerprint(professor_id)
    biometric_sessions[session_id]["status"] = "success" if success else "failed"
    biometric_sessions[session_id]["result"] = message
    return jsonify({"success": success, "sessionId": session_id, "message": message})


@professors_bp.get("/biometric/status/<session_id>")
def get_biometric_status(session_id):
    session = biometric_sessions.get(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404
    return jsonify({"status": session["status"], "result": session["result"]})


@professors_bp.delete("/biometric/session/<session_id>")
def cancel_biometric_session(session_id):
    session = biometric_sessions.get(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404
    # Simulate cancel (real implementation would signal hardware)
    session["status"] = "cancelled"
    return jsonify({"success": True})


@professors_bp.post("/biometric/verify")
def verify_professor_fingerprint():
    data = request.get_json(force=True, silent=True) or {}
    professor_id = data.get("professorId")
    try:
        professor_id = int(professor_id)
    except Exception:
        return jsonify({"success": False, "error": "Invalid professorId"}), 400
    success, message, matched_id = arduino_manager.verify_fingerprint(expected_id=professor_id)
    confidence = 100 if success else 0  # Simulate confidence
    return jsonify({"success": success, "confidence": confidence, "message": message, "matchedId": matched_id})


@professors_bp.get("")
def list_professors():
    professors = get_all_professors()
    return jsonify(professors)


@professors_bp.post("")
def add_professor():
    data = request.get_json(force=True, silent=True) or {}
    try:
        professor = create_professor(data)
        return jsonify(professor), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception:
        return jsonify({"error": "Failed to create professor"}), 500


@professors_bp.put("/<int:professor_id>")
def edit_professor(professor_id: int):
    data = request.get_json(force=True, silent=True) or {}
    try:
        professor = update_professor(professor_id, data)
        if not professor:
            return jsonify({"error": "Professor not found"}), 404
        return jsonify(professor)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception:
        return jsonify({"error": "Failed to update professor"}), 500


@professors_bp.delete("/<int:professor_id>")
def remove_professor(professor_id: int):
    try:
        deleted = delete_professor(professor_id)
        if not deleted:
            return jsonify({"error": "Professor not found"}), 404
        return jsonify({"success": True})
    except Exception:
        return jsonify({"error": "Failed to delete professor"}), 500
