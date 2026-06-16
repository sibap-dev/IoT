import logging
from datetime import datetime, timezone
from sqlalchemy import or_
from flask import Blueprint, jsonify, request
from database.db import db
from database.models import HealthReading
from services.prediction_service import PredictionService
from services.alert_service import AlertService
from services.stability_filter import process_sensor_data, get_filter

logger = logging.getLogger(__name__)

sensor_bp = Blueprint("sensor_api", __name__)

REQUIRED_FIELDS = ["heart_rate", "spo2", "temperature"]
OPTIONAL_FIELDS = ["fall_detected", "patient_id"]


# NOTE: Auto-simulator removed — data now comes exclusively from the ESP32 wearable.
# To re-enable simulated data for testing, run: python sensor_simulator.py


def validate_payload(data):
    missing = [f for f in REQUIRED_FIELDS if f not in data]
    if missing:
        return {"error": f"Missing required fields: {', '.join(missing)}"}, 400

    for field in REQUIRED_FIELDS:
        try:
            val = float(data[field])
            if field == "heart_rate" and (val < 20 or val > 250):
                return {"error": f"heart_rate {val} out of range (20-250)"}, 400
            if field == "spo2" and (val < 50 or val > 100):
                return {"error": f"spo2 {val} out of range (50-100)"}, 400
            if field == "temperature" and (val < 30 or val > 45):
                return {"error": f"temperature {val} out of range (30-45)"}, 400
        except (TypeError, ValueError):
            return {"error": f"{field} must be numeric"}, 400

    return None


@sensor_bp.route("/api/sensor-data", methods=["POST"])
def receive_sensor_data():
    """
    Accept sensor data from ESP32 or any IoT device.

    Expected payload (JSON):
    {
        "heart_rate": 78,
        "spo2": 98,
        "temperature": 36.8,
        "fall_detected": false,
        "patient_id": "optional_device_id"
    }

    Returns the stored reading, auto-generated prediction, and any alerts.
    """
    data = request.get_json(silent=True)
    if not data:
        logger.error("[ESP32] 400: Raw body = %s", request.data)
        return jsonify({"error": "Request body must be valid JSON"}), 400

    logger.info("[ESP32] Received: %s", data)
    validation_error = validate_payload(data)
    if validation_error:
        logger.error("[ESP32] 400 Validation failed: %s | Data was: %s", validation_error[0], data)
        return jsonify(validation_error[0]), validation_error[1]

    heart_rate = float(data["heart_rate"])
    spo2 = float(data["spo2"])
    temperature = float(data["temperature"])
    fall_detected = bool(data.get("fall_detected", data.get("fall", data.get("is_fall", False))))
    patient_id = data.get("patient_id")

    acc_x = float(data.get("acceleration_x", 0.0))
    acc_y = float(data.get("acceleration_y", 0.0))
    acc_z = float(data.get("acceleration_z", 0.0))

    reading = HealthReading(
        patient_id=patient_id,
        timestamp=datetime.now(timezone.utc),
        heart_rate=heart_rate,
        spo2=spo2,
        temperature=temperature,
        fall_detected=fall_detected,
        acceleration_x=acc_x,
        acceleration_y=acc_y,
        acceleration_z=acc_z,
    )
    db.session.add(reading)
    db.session.flush()

    filtered = process_sensor_data(
        heart_rate=heart_rate,
        spo2=spo2,
        temperature=temperature,
        fall_detected=fall_detected,
        accel_x=acc_x,
        accel_y=acc_y,
        accel_z=acc_z,
        patient_id=patient_id,
    )

    prediction, pred_result = PredictionService.run_prediction(
        heart_rate=filtered["heart_rate"],
        spo2=filtered["spo2"],
        temperature=filtered["temperature"],
        fall_detected=fall_detected,
        health_reading_id=reading.id,
        patient_id=patient_id,
    )

    alerts = AlertService.check_reading(
        heart_rate=filtered["heart_rate"],
        spo2=filtered["spo2"],
        temperature=filtered["temperature"],
        fall_detected=fall_detected,
        reading_id=reading.id,
        patient_id=patient_id,
        risk_level=pred_result.get("risk_level"),
        risk_score=pred_result.get("risk_score"),
    )

    db.session.commit()

    return jsonify({
        "status": "success",
        "reading": reading.to_dict(),
        "filtered": {
            "heart_rate": filtered["heart_rate"],
            "spo2": filtered["spo2"],
            "temperature": filtered["temperature"],
            "stability_status": filtered["stability_status"],
        },
        "prediction": pred_result,
        "alerts": [a.to_dict() for a in alerts],
    }), 201


@sensor_bp.route("/api/latest-data", methods=["GET"])
def get_latest_data():
    """
    Return the most recent HealthReading from the database.
    Includes is_live=True only if data arrived within the last 30 seconds.
    """
    patient_id = request.args.get("patient_id")
    q = HealthReading.query.order_by(HealthReading.created_at.desc())
    if patient_id:
        q = q.filter_by(patient_id=patient_id)
    reading = q.first()

    if not reading:
        return jsonify({"error": "No data available yet", "is_live": False}), 404

    # Freshness check — data must be < 30 seconds old to be considered live
    now = datetime.now(timezone.utc)
    created = reading.created_at.replace(tzinfo=timezone.utc) if reading.created_at.tzinfo is None else reading.created_at
    seconds_ago = (now - created).total_seconds()
    is_live = seconds_ago < 30

    return jsonify({
        "reading": reading.to_dict(),
        "is_live": is_live,
        "seconds_ago": round(seconds_ago)
    })


@sensor_bp.route("/api/sensor-history", methods=["GET"])
@sensor_bp.route("/api/history", methods=["GET"])
def get_sensor_history():
    """
    Return paginated sensor reading history from the database.

    Query params:
      - limit   (int, default 50)
      - offset  (int, default 0)
      - patient_id (str, optional)
      - since   (ISO datetime string, optional)
    """
    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)
    patient_id = request.args.get("patient_id")
    since = request.args.get("since")

    # Real-time mode: no auto-simulation — waits for live ESP32 data
    q = HealthReading.query.order_by(HealthReading.created_at.desc())


    if patient_id:
        q = q.filter(or_(HealthReading.patient_id == patient_id, HealthReading.patient_id.is_(None)))
    if since:
        try:
            since_dt = datetime.fromisoformat(since)
            q = q.filter(HealthReading.timestamp >= since_dt)
        except ValueError:
            return jsonify({"error": "Invalid since format. Use ISO 8601."}), 400

    total = q.count()
    readings = q.offset(offset).limit(limit).all()

    return jsonify({
        "total": total,
        "limit": limit,
        "offset": offset,
        "readings": [r.to_dict() for r in readings],
    })


@sensor_bp.route("/api/stability-status", methods=["GET"])
def get_stability_status():
    patient_id = request.args.get("patient_id")
    sf = get_filter(patient_id)
    state = sf.get_state()
    return jsonify(state)
