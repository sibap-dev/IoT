from datetime import datetime, timezone
from database.db import db
from database.models import HealthReading, PredictionHistory
from ml.predictor import HealthPredictor

predictor = HealthPredictor()


class PredictionService:

    @staticmethod
    def run_prediction(
        heart_rate, spo2, temperature, fall_detected,
        health_reading_id=None, patient_id=None
    ):
        import json
        result = predictor.predict(heart_rate, spo2, temperature, fall_detected)

        pred = PredictionHistory(
            health_reading_id=health_reading_id,
            patient_id=patient_id,
            timestamp=datetime.now(timezone.utc),
            heart_rate=heart_rate,
            spo2=spo2,
            temperature=temperature,
            fall_detected=fall_detected,
            risk_level=result["risk_level"],
            risk_score=result["risk_score"],
            confidence_score=result.get("confidence_score", 1.0),
            explanation=json.dumps(result.get("explanation")),
            recommendation=result["recommendation"],
        )
        db.session.add(pred)
        db.session.commit()

        return pred, result

    @staticmethod
    def get_latest_prediction(patient_id=None):
        q = PredictionHistory.query.order_by(PredictionHistory.created_at.desc())
        if patient_id:
            q = q.filter_by(patient_id=patient_id)
        return q.first()

    @staticmethod
    def get_prediction_history(limit=50, offset=0, patient_id=None):
        q = PredictionHistory.query.order_by(PredictionHistory.created_at.desc())
        if patient_id:
            q = q.filter_by(patient_id=patient_id)
        return q.offset(offset).limit(limit).all()
