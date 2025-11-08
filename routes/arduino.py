from flask import Blueprint, jsonify, request, Response, stream_with_context, json
from flask_jwt_extended import jwt_required
from models import AccessLog, Student, Professor

from utils.arduino import arduino_manager
from utils.auth_utils import roles_required

arduino_bp = Blueprint("arduino", __name__)


@arduino_bp.get("/ports")
#@jwt_required()
def list_ports():
    print([ {"port": port["device"],"name":port["name"] ,"description": port["description"], "manufacturer": port["manufacturer"]}
        for port in arduino_manager.list_ports()
    ])
    return jsonify([ {"port": port["device"],"name":port["name"] ,"description": port["description"], "manufacturer": port["manufacturer"]}
        for port in arduino_manager.list_ports()
    ])
    #return jsonify( arduino_manager.list_ports())


@arduino_bp.get("/status")
#@jwt_required()
def status():
    return jsonify(arduino_manager.status())


@arduino_bp.post("/connect")
#@jwt_required()
#@roles_required("admin")
def connect():
    data = request.get_json(force=True, silent=True) or {}
    port = data.get("port")
    baudrate = int(data.get("baudrate") or 9600)
    if not port:
        return jsonify({"error": "'port' is required"}), 400
    ok, msg = arduino_manager.connect(port=port, baudrate=baudrate)
    return jsonify({"success": ok, "message": msg, "status": arduino_manager.status()}), (200 if ok else 500)


@arduino_bp.post("/disconnect")
#@jwt_required()
#@roles_required("admin")
def disconnect():
    ok, msg = arduino_manager.disconnect()
    return jsonify({"success": ok, "message": msg, "status": arduino_manager.status()})


@arduino_bp.get("/refresh-ports")
#@jwt_required()
def refresh():
    # Alias to list ports (forces re-enumeration)
    print([ {"port": port["device"],"name":port["name"] ,"description": port["description"], "manufacturer": port["manufacturer"]}
        for port in arduino_manager.list_ports()
    ])
    return jsonify([ {"port": port["device"],"name":port["name"] ,"description": port["description"], "manufacturer": port["manufacturer"]}
        for port in arduino_manager.list_ports()
    ])


@arduino_bp.post("/test-capture")
#@jwt_required()
#@roles_required("admin")
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

# -------------------- Streaming verification (SSE) --------------------
@arduino_bp.get("/verify-stream")
#@jwt_required()
def verify_stream():
    """
    Server-Sent Events endpoint that streams verification events from the Arduino.
    Query params:
      - expected_id: (optional) integer ID to match against enrolled fingerprint
      - per_try_timeout: (optional) float seconds to wait per read (default 3.0)
      - max_polls: (optional) int max poll iterations (0 = unlimited)
    Example: /arduino/verify-stream?expected_id=5&per_try_timeout=2&max_polls=0
    """
    expected_id = request.args.get("expected_id", default=None, type=int)
    per_try_timeout = float(request.args.get("per_try_timeout", 3.0))
    max_polls = int(request.args.get("max_polls", 0))

    def gen():
        for ev in arduino_manager.verify_fingerprint_stream(
            expected_id=expected_id, per_try_timeout=per_try_timeout, max_polls=max_polls
        ):
            # SSE format: data: <json>\n\n
            yield f"data: {json.dumps(ev)}\n\n"

    return Response(stream_with_context(gen()), mimetype="text/event-stream")



@arduino_bp.get("/access-logs")
# @jwt_required()
def list_access_logs():
    """
    Returns access logs formatted for frontend columns:
      - timestamp
      - userName
      - role
      - method
      - result
      - details (object)
    Query params:
      - limit (int, default=100)
      - offset (int, default=0)
    """
    try:
        limit = int(request.args.get("limit", 100))
        offset = int(request.args.get("offset", 0))
    except Exception:
        return jsonify({"error": "limit and offset must be integers"}), 400

    logs = (
        AccessLog.query
        .order_by(AccessLog.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    out = []
    for l in logs:
        # default values
        user_name = ""
        role = l.entity_type or "unknown"
        method = "fingerprint"
        details = {"entity_type": l.entity_type, "fingerprintId": l.entity_id}

        # try to resolve a friendly name from student/professor
        try:
            if l.entity_type == "student" and l.entity_id:
                s = Student.query.filter_by(fingerprint_id=str(l.entity_id)).first()
                if s:
                    # prefer first/last, fall back to name
                    if getattr(s, "first_name", None) or getattr(s, "last_name", None):
                        user_name = " ".join(filter(None, [s.first_name, s.last_name]))
                    else:
                        user_name = s.name or ""
            elif l.entity_type == "professor" and l.entity_id:
                p = Professor.query.filter_by(fingerprint_id=str(l.entity_id)).first()
                if p:
                    if getattr(p, "first_name", None) or getattr(p, "last_name", None):
                        user_name = " ".join(filter(None, [p.first_name, p.last_name]))
                    else:
                        user_name = p.name or ""
        except Exception:
            # don't fail on lookup issues
            pass

        out.append({
            "timestamp": l.created_at.isoformat() if l.created_at else None,
            "userName": user_name,
            "role": role,
            "method": method,
            "result": l.status,
            "details": details,
        })

    return jsonify(out)
