from flask import Blueprint, jsonify, request

from services.professor_service import (
    get_all_professors,
    create_professor,
    update_professor,
    delete_professor,
)

professors_bp = Blueprint("professors", __name__)


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
