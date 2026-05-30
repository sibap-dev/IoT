from flask import Blueprint, jsonify, request
from services.alert_service import AlertService
from database.models import AlertHistory

alert_bp = Blueprint("alert_api", __name__)


@alert_bp.route("/api/alerts", methods=["GET"])
def get_alerts():
    """
    Return recent alerts.

    Query params:
      - limit       (int,  default 20)
      - patient_id  (str,  optional)
      - unread_only (bool, default false)
    """
    limit       = request.args.get("limit", 20, type=int)
    patient_id  = request.args.get("patient_id")
    unread_only = request.args.get("unread_only", "false").lower() == "true"

    alerts = AlertService.get_recent_alerts(
        limit=limit, patient_id=patient_id, unread_only=unread_only
    )
    unread_count = AlertHistory.query.filter_by(is_read=False).count()

    return jsonify({
        "total": len(alerts),
        "unread_count": unread_count,
        "alerts": [a.to_dict() for a in alerts],
    })


@alert_bp.route("/api/alerts/<int:alert_id>/read", methods=["PATCH"])
def mark_alert_read(alert_id):
    """Mark a single alert as read."""
    success = AlertService.mark_as_read(alert_id)
    if not success:
        return jsonify({"error": "Alert not found"}), 404
    return jsonify({"success": True, "alert_id": alert_id})


@alert_bp.route("/api/alerts/read-all", methods=["PATCH"])
def mark_all_read():
    """Mark all alerts as read (optionally for a specific patient)."""
    patient_id = request.args.get("patient_id")
    AlertService.mark_all_read(patient_id=patient_id)
    return jsonify({"success": True})


@alert_bp.route("/api/alerts/stats", methods=["GET"])
def alert_stats():
    """Return alert counts by severity."""
    from database.db import db
    from sqlalchemy import func
    rows = (
        db.session.query(AlertHistory.severity, func.count(AlertHistory.id))
        .group_by(AlertHistory.severity)
        .all()
    )
    return jsonify({
        "by_severity": {sev: cnt for sev, cnt in rows},
        "total": sum(cnt for _, cnt in rows),
    })
