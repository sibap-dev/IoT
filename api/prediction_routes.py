from flask import Blueprint, jsonify, request
from services.prediction_service import PredictionService
from services.alert_service import AlertService
from database.db import db
from database.models import HealthReading

prediction_bp = Blueprint("prediction_api", __name__)


@prediction_bp.route("/api/predict", methods=["POST"])
def predict():
    """
    Run a health risk prediction on provided vital signs.

    Expected payload (JSON):
    {
        "heart_rate": 78,
        "spo2": 98,
        "temperature": 36.8,
        "fall_detected": false,
        "patient_id": "optional"
    }

    Optionally saves the prediction if health_reading_id is provided.
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be valid JSON"}), 400

    required = ["heart_rate", "spo2", "temperature"]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"error": f"Missing: {', '.join(missing)}"}), 400

    try:
        heart_rate = float(data["heart_rate"])
        spo2 = float(data["spo2"])
        temperature = float(data["temperature"])
    except (TypeError, ValueError):
        return jsonify({"error": "Values must be numeric"}), 400

    fall_detected = bool(data.get("fall_detected", False))
    patient_id = data.get("patient_id")
    health_reading_id = data.get("health_reading_id")

    pred, result = PredictionService.run_prediction(
        heart_rate=heart_rate,
        spo2=spo2,
        temperature=temperature,
        fall_detected=fall_detected,
        health_reading_id=health_reading_id,
        patient_id=patient_id,
    )

    alerts = AlertService.check_reading(
        heart_rate=heart_rate,
        spo2=spo2,
        temperature=temperature,
        fall_detected=fall_detected,
        reading_id=health_reading_id,
        patient_id=patient_id,
        risk_level=result.get("risk_level"),
        risk_score=result.get("risk_score"),
    )

    return jsonify({
        "prediction": result,
        "prediction_id": pred.id,
        "alerts": [a.to_dict() for a in alerts],
    })


@prediction_bp.route("/api/latest-prediction", methods=["GET"])
def get_latest_prediction():
    """
    Return the most recent prediction from the database.
    """
    patient_id = request.args.get("patient_id")
    pred = PredictionService.get_latest_prediction(patient_id=patient_id)

    if not pred:
        return jsonify({"error": "No predictions available yet"}), 404

    return jsonify({"prediction": pred.to_dict()})


@prediction_bp.route("/api/predictions", methods=["GET"])
def get_predictions():
    """
    Return paginated prediction history.

    Query params:
      - limit   (int, default 50)
      - offset  (int, default 0)
      - patient_id (str, optional)
    """
    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)
    patient_id = request.args.get("patient_id")

    preds = PredictionService.get_prediction_history(
        limit=limit, offset=offset, patient_id=patient_id
    )

    return jsonify({
        "total": len(preds),
        "limit": limit,
        "offset": offset,
        "predictions": [p.to_dict() for p in preds],
    })
