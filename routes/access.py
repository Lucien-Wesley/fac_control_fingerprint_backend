from __future__ import annotations

from flask import Blueprint, jsonify, request, Response
from flask_jwt_extended import jwt_required

from utils.auth_utils import roles_required
from utils.sse import sse_broker
from services.access_service import verify_access, list_logs

access_bp = Blueprint("access", __name__)



@access_bp.get("/logs")
@jwt_required()
@roles_required("admin")
def access_logs():
    period = (request.args.get("period") or "day").lower()  # day|week|month|all
    entity_type = request.args.get("entity_type")
    role = request.args.get("role")
    limit = int(request.args.get("limit") or 100)
    offset = int(request.args.get("offset") or 0)

    logs = list_logs(period=period, entity_type=entity_type, role=role, limit=limit, offset=offset)
    return jsonify({"items": logs, "count": len(logs)})


@access_bp.get("/stream")
@jwt_required()
@roles_required("admin")
def access_stream():
    def event_stream():
        for msg in sse_broker.stream():
            yield msg

    headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return Response(event_stream(), headers=headers)
