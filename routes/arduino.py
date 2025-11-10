from flask import Blueprint, jsonify, request, Response, stream_with_context, json
from flask_jwt_extended import jwt_required
from models import AccessLog, Student, Professor

from utils.arduino import arduino_manager, STATUS_FILE_PATH
import os
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


@arduino_bp.route('/output', methods=['GET'])
def get_status():
    """
    Récupère le dernier message lu par le thread série
    et l'état de la connexion.
    """
    last_msg = arduino_manager.get_last_message()
    
    # On vérifie si le fichier de statut existe pour confirmation
    file_exists = os.path.exists(STATUS_FILE_PATH)
    
    # Lecture optionnelle du contenu brut du fichier pour vérification
    file_content = ""
    if file_exists:
        try:
            with open(STATUS_FILE_PATH, 'r', encoding='utf-8') as f:
                file_content = f.read().strip()
        except IOError:
            file_content = "Erreur de lecture du fichier."

    return jsonify({
        "status": "OK",
        "is_connected": arduino_manager._ser is not None,
        "last_message": last_msg,
        "status_file_content": file_content
    })


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

@arduino_bp.route('/verify', methods=['POST'])
def set_verify_mode():
    """
    Envoie la commande 'V' pour passer en mode VERIFICATION.
    """
    success, message = arduino_manager.send_command('V')
    if success:
        return jsonify({"success": True, "message": message}), 200
    else:
        return jsonify({"success": False, "error": message}), 503

@arduino_bp.route('/enroll/<int:id>', methods=['POST'])
def start_enrollment(id):
    """
    Définit l'ID ('I:<id>') puis passe en mode ENREGISTREMENT ('E').
    L'ID doit être entre 0 et 127 selon le code Arduino.
    """
    if not 0 <= id <= 127:
        return jsonify({"success": False, "error": "L'ID doit être entre 0 et 127."}), 400

    # 1. Définir l'ID
    id_command = f"I{id}" 
    success_id, msg_id = arduino_manager.send_command(id_command)

    if not success_id:
        return jsonify({"success": False, "error": f"Échec de la commande ID: {msg_id}"}), 503

    # 2. Passer en mode ENREGISTREMENT
    success_enroll, msg_enroll = arduino_manager.send_command('E')

    if success_enroll:
        return jsonify({
            "success": True, 
            "message": f"ID {id} défini. Mode ENREGISTREMENT activé. Suivez les instructions Arduino."
        }), 200
    else:
        return jsonify({"success": False, "error": f"Échec de la commande ENROLL: {msg_enroll}"}), 503


@arduino_bp.route('/cancel', methods=['POST'])
def cancel_enrollment():
    """
    Envoie la commande 'C' pour annuler l'enregistrement en cours.
    """
    success, message = arduino_manager.send_command('C')
    if success:
        return jsonify({"success": True, "message": message}), 200
    else:
        return jsonify({"success": False, "error": message}), 503





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
