from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from utils.db import db
from utils.arduino import arduino_manager
from utils.sse import sse_broker
from models import AccessLog, Student, Professor


def _find_entity(entity_type: str, entity_id: int):
    if entity_type == "student":
        return Student.query.get(entity_id)
    if entity_type == "professor":
        return Professor.query.get(entity_id)
    return None


def verify_access(entity_type: str, entity_id: int, max_retries: int = 3) -> Dict:
    """
    Triggers the Arduino capture and records an access log with status granted/denied.
    Publishes the event via SSE on success or failure.
    """
    if entity_type not in {"student", "professor"}:
        raise ValueError("entity_type must be 'student' or 'professor'")

    # Validate entity exists and is fingerprint-registered
    entity = _find_entity(entity_type, entity_id)
    if not entity:
        log = _create_log(entity_type, entity_id, status="denied")
        return {"success": False, "message": "Entity not found", "log": log}

    if not getattr(entity, "fingerprint_verified", False):
        log = _create_log(entity_type, entity_id, status="denied")
        return {"success": False, "message": "Fingerprint not registered", "log": log}

    # Perform capture
    ok, message, matched_id = arduino_manager.verify_fingerprint(expected_id=entity_id)
    if ok:
        log = _create_log(entity_type, entity_id, status="granted")
        return {"success": True, "message": message, "matched_id": matched_id, "log": log}
    else:
        log = _create_log(entity_type, entity_id, status="denied")
        return {"success": False, "message": message, "matched_id": matched_id, "log": log}


def _create_log(entity_type: str, entity_id: int, status: str) -> Dict:
    log = AccessLog(
        entity_type=entity_type,
        entity_id=entity_id,
        status=status,
    )
    db.session.add(log)
    db.session.commit()

    payload = log.to_dict()
    sse_broker.publish("access", payload)
    return payload


def list_logs(
    period: str = "day",
    entity_type: Optional[str] = None,
    role: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[Dict]:
    """
    Returns access logs filtered by period (day, week, month, all) and optionally entity_type.
    Role is a placeholder (if you later store verifier role in logs or want to filter by entity role).
    """
    q = AccessLog.query

    # Period filter
    now = datetime.utcnow()
    if period == "day":
        since = now - timedelta(days=1)
        q = q.filter(AccessLog.created_at >= since)
    elif period == "week":
        since = now - timedelta(weeks=1)
        q = q.filter(AccessLog.created_at >= since)
    elif period == "month":
        since = now - timedelta(days=30)
        q = q.filter(AccessLog.created_at >= since)
    elif period == "all":
        pass
    else:
        # default day if unknown
        since = now - timedelta(days=1)
        q = q.filter(AccessLog.created_at >= since)

    if entity_type in {"student", "professor"}:
        q = q.filter(AccessLog.entity_type == entity_type)

    # 'role' left for future use; not stored in AccessLog yet

    logs = (
        q.order_by(AccessLog.id.desc())
        .offset(max(offset, 0))
        .limit(max(min(limit, 500), 1))
        .all()
    )
    return [l.to_dict() for l in logs]
