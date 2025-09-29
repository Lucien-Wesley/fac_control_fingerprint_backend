from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from utils.arduino import arduino_manager
from utils.auth_utils import roles_required

arduino_bp = Blueprint("arduino", __name__)


@arduino_bp.get("/ports")
@jwt_required()
def list_ports():
    print([ {"port": port["device"],"name":port["name"] ,"description": port["description"], "manufacturer": port["manufacturer"]}
        for port in arduino_manager.list_ports()
    ])
    return jsonify([ {"port": port["device"],"name":port["name"] ,"description": port["description"], "manufacturer": port["manufacturer"]}
        for port in arduino_manager.list_ports()
    ])
    #return jsonify( arduino_manager.list_ports())


@arduino_bp.get("/status")
@jwt_required()
def status():
    return jsonify(arduino_manager.status())


@arduino_bp.post("/connect")
@jwt_required()
@roles_required("admin")
def connect():
    data = request.get_json(force=True, silent=True) or {}
    port = data.get("port")
    baudrate = int(data.get("baudrate") or 9600)
    if not port:
        return jsonify({"error": "'port' is required"}), 400
    ok, msg = arduino_manager.connect(port=port, baudrate=baudrate)
    return jsonify({"success": ok, "message": msg, "status": arduino_manager.status()}), (200 if ok else 500)


@arduino_bp.post("/disconnect")
@jwt_required()
@roles_required("admin")
def disconnect():
    ok, msg = arduino_manager.disconnect()
    return jsonify({"success": ok, "message": msg, "status": arduino_manager.status()})


@arduino_bp.get("/refresh-ports")
@jwt_required()
def refresh():
    # Alias to list ports (forces re-enumeration)
    print([ {"port": port["device"],"name":port["name"] ,"description": port["description"], "manufacturer": port["manufacturer"]}
        for port in arduino_manager.list_ports()
    ])
    return jsonify([ {"port": port["device"],"name":port["name"] ,"description": port["description"], "manufacturer": port["manufacturer"]}
        for port in arduino_manager.list_ports()
    ])


@arduino_bp.post("/test-capture")
@jwt_required()
@roles_required("admin")
def test_capture():
    data = request.get_json(force=True, silent=True) or {}
    entity = (data.get("entity") or "").strip().lower()
    entity_id = data.get("entity_id")
    max_retries = int(data.get("max_retries") or 3)
    if entity not in {"student", "professor"}:
        return jsonify({"error": "'entity' must be 'student' or 'professor'"}), 400
    try:
        entity_id = int(entity_id)
    except Exception:
        return jsonify({"error": "'entity_id' must be an integer"}), 400

    success, message = arduino_manager.capture_fingerprint(entity=entity, entity_id=entity_id, max_retries=max_retries)
    return jsonify({"success": success, "response": message}) , (200 if success else 400)
