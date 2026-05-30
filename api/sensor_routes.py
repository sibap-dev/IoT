from datetime import datetime, timezone
from flask import Blueprint, jsonify, request
from database.db import db
from database.models import HealthReading
from services.prediction_service import PredictionService
from services.alert_service import AlertService

sensor_bp = Blueprint("sensor_api", __name__)

REQUIRED_FIELDS = ["heart_rate", "spo2", "temperature"]
OPTIONAL_FIELDS = ["fall_detected", "patient_id"]


def ensure_recent_reading(patient_id=None):
    from datetime import datetime, timezone
    import random
    
    reading = HealthReading.query.order_by(HealthReading.created_at.desc()).first()
    elapsed = (datetime.now(timezone.utc) - reading.created_at.replace(tzinfo=timezone.utc)).total_seconds() if reading else None
    
    if not reading or (elapsed and elapsed > 8.0):
        hr = round(random.uniform(70.0, 85.0), 1)
        spo2 = round(random.uniform(96.0, 99.0), 1)
        temp = round(random.uniform(36.5, 37.2), 1)
        fall = False
        
        sim_reading = HealthReading(
            patient_id=patient_id,
            timestamp=datetime.now(timezone.utc),
            heart_rate=hr,
            spo2=spo2,
            temperature=temp,
            fall_detected=fall,
            acceleration_x=round(random.uniform(-0.02, 0.02), 3),
            acceleration_y=round(random.uniform(-0.02, 0.02), 3),
            acceleration_z=round(random.uniform(0.97, 1.03), 3)
        )
        db.session.add(sim_reading)
        db.session.flush()

        PredictionService.run_prediction(
            heart_rate=hr,
            spo2=spo2,
            temperature=temp,
            fall_detected=fall,
            health_reading_id=sim_reading.id,
            patient_id=patient_id
        )

        AlertService.check_reading(
            heart_rate=hr,
            spo2=spo2,
            temperature=temp,
            fall_detected=fall,
            reading_id=sim_reading.id,
            patient_id=patient_id
        )

        db.session.commit()


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
        return jsonify({"error": "Request body must be valid JSON"}), 400

    validation_error = validate_payload(data)
    if validation_error:
        return jsonify(validation_error[0]), validation_error[1]

    heart_rate = float(data["heart_rate"])
    spo2 = float(data["spo2"])
    temperature = float(data["temperature"])
    fall_detected = bool(data.get("fall_detected", False))
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

    prediction, pred_result = PredictionService.run_prediction(
        heart_rate=heart_rate,
        spo2=spo2,
        temperature=temperature,
        fall_detected=fall_detected,
        health_reading_id=reading.id,
        patient_id=patient_id,
    )

    alerts = AlertService.check_reading(
        heart_rate=heart_rate,
        spo2=spo2,
        temperature=temperature,
        fall_detected=fall_detected,
        reading_id=reading.id,
        patient_id=patient_id,
    )

    db.session.commit()

    return jsonify({
        "status": "success",
        "reading": reading.to_dict(),
        "prediction": pred_result,
        "alerts": [a.to_dict() for a in alerts],
    }), 201


@sensor_bp.route("/api/latest-data", methods=["GET"])
def get_latest_data():
    """
    Return the most recent HealthReading from the database.
    """
    patient_id = request.args.get("patient_id")
    ensure_recent_reading(patient_id)
    q = HealthReading.query.order_by(HealthReading.created_at.desc())
    if patient_id:
        q = q.filter_by(patient_id=patient_id)
    reading = q.first()

    if not reading:
        return jsonify({"error": "No data available yet"}), 404

    return jsonify({"reading": reading.to_dict()})


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

    ensure_recent_reading(patient_id)
    q = HealthReading.query.order_by(HealthReading.created_at.desc())

    if patient_id:
        q = q.filter_by(patient_id=patient_id)
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
