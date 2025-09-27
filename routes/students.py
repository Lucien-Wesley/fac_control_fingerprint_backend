from flask import Blueprint, jsonify, request

from services.student_service import (
    get_all_students,
    create_student,
    update_student,
    delete_student,
)

students_bp = Blueprint("students", __name__)


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
