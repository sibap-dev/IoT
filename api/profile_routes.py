from flask import Blueprint, request, jsonify, session
from database.db import db
from database.models import Patient, HealthReading, User
from routes.auth import login_required
import logging

logger = logging.getLogger(__name__)

profile_bp = Blueprint("profile_api", __name__)


@profile_bp.route("/api/profile", methods=["GET", "PUT"])
@login_required
def profile():
    user = User.query.get(session["user_id"])
    if not user or user.role != "PATIENT" or not user.patient_profile:
        return jsonify({"error": "Only patient accounts have a profile"}), 403

    patient = user.patient_profile

    if request.method == "GET":
        return jsonify({"profile": patient.to_dict()})

    data = request.get_json(silent=True) or {}
    if "name" in data:
        patient.name = data["name"].strip().title()
    if "age" in data:
        try:
            patient.age = int(data["age"])
        except (TypeError, ValueError):
            return jsonify({"error": "Age must be a number"}), 400
    if "gender" in data:
        patient.gender = data["gender"].strip().title()
    if "blood_group" in data:
        patient.blood_group = data["blood_group"].strip().upper()
    if "emergency_contact" in data:
        patient.emergency_contact = data["emergency_contact"].strip()

    db.session.commit()
    return jsonify({"success": True, "profile": patient.to_dict()})


@profile_bp.route("/api/health-history", methods=["GET"])
@login_required
def health_history():
    user = User.query.get(session["user_id"])
    if not user or user.role != "PATIENT" or not user.patient_profile:
        return jsonify({"error": "Only patient accounts have health history"}), 403

    patient = user.patient_profile
    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)

    readings = HealthReading.query.filter_by(
        patient_id=patient.patient_id
    ).order_by(
        HealthReading.created_at.desc()
    ).offset(offset).limit(limit).all()

    return jsonify({
        "readings": [r.to_dict() for r in readings],
        "total": HealthReading.query.filter_by(
            patient_id=patient.patient_id
        ).count(),
        "limit": limit,
        "offset": offset,
    })


@profile_bp.route("/api/claim-readings", methods=["POST"])
@login_required
def claim_readings():
    """Claim all unassigned readings for the logged-in patient."""
    user = User.query.get(session["user_id"])
    if not user or user.role != "PATIENT" or not user.patient_profile:
        return jsonify({"error": "Only patient accounts can claim readings"}), 403

    patient = user.patient_profile
    count = HealthReading.query.filter_by(patient_id=None).update(
        {"patient_id": patient.patient_id}
    )
    db.session.commit()
    return jsonify({"success": True, "claimed": count})
