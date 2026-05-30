import os
import joblib
import numpy as np
import pandas as pd
import logging
from ml.explainability import ExplainabilityEngine
from ml.recommendation_engine import RecommendationEngine
from ml.anomaly_detector import AnomalyDetector

logger = logging.getLogger(__name__)

class HealthPredictor:
    """
    Production-grade AI Health Predictor engine.
    Supports Random Forest ML predictions, SHAP diagnostic explanations, 
    Isolation Forest anomaly analysis, and falls back gracefully to expert rules.
    """

    def __init__(self):
        self.model_path = os.path.join(os.path.dirname(__file__), "models", "rf_health_model.joblib")
        self.scaler_path = os.path.join(os.path.dirname(__file__), "models", "scaler.joblib")
        self.model = None
        self.scaler = None
        self.anomaly_detector = AnomalyDetector()
        self._load_model()

    def _load_model(self):
        """Attempts to load a trained Random Forest classifier from ml/models/."""
        if os.path.exists(self.model_path) and os.path.exists(self.scaler_path):
            try:
                self.model = joblib.load(self.model_path)
                self.scaler = joblib.load(self.scaler_path)
                logger.info("Successfully loaded Random Forest classifier and scaler.")
            except Exception as e:
                logger.error(f"Error loading trained ML model weights: {e}. Falling back to rule engine.")

    def predict(self, heart_rate: float, spo2: float, temperature: float, fall_detected: bool) -> dict:
        """
        Calculates health risk, anomaly indicators, explainability attribution, and recommendations.
        """
        # 1. Run Anomaly Check (Isolation Forest)
        anomaly_res = self.anomaly_detector.predict(heart_rate, spo2, temperature)

        # 2. Run SHAP Attribution
        shap_res = ExplainabilityEngine.explain(heart_rate, spo2, temperature, fall_detected)

        # 3. Calculate Risk Score
        risk_score = 0.0
        confidence = 1.0

        if self.model and self.scaler:
            # ML Model Prediction path
            try:
                features = pd.DataFrame([[heart_rate, spo2, temperature]], columns=["BPM", "SPO2", "Body_Temp"])
                scaled = self.scaler.transform(features)
                # Predict class probabilities (e.g. [Low, Medium, High, Critical])
                probs = self.model.predict_proba(scaled)[0]
                classes = self.model.classes_

                # Custom risk score calculation based on probability distributions
                class_weights = {"Low": 10.0, "Medium": 40.0, "High": 75.0, "Critical": 95.0}
                for idx, cls_name in enumerate(classes):
                    weight = class_weights.get(cls_name, 10.0)
                    risk_score += float(probs[idx]) * weight

                confidence = float(np.max(probs))
                logger.info(f"ML Model Risk Prediction: {risk_score:.1f} (Confidence: {confidence:.2f})")
            except Exception as e:
                logger.error(f"ML model prediction failed: {e}. Falling back to clinical expert rules.")
                risk_score, confidence = self._rule_based_risk(heart_rate, spo2, temperature, fall_detected)
        else:
            # Rule Engine Fallback path
            risk_score, confidence = self._rule_based_risk(heart_rate, spo2, temperature, fall_detected)

        # Ensure bounds
        risk_score = min(100.0, max(0.0, risk_score))

        # Categorize Risk Level
        if risk_score >= 80.0 or fall_detected:
            risk_level = "Critical"
        elif risk_score >= 50.0:
            risk_level = "High"
        elif risk_score >= 25.0:
            risk_level = "Medium"
        else:
            risk_level = "Low"

        # 4. Generate Patient Advices
        recommendation = RecommendationEngine.generate(heart_rate, spo2, temperature, fall_detected)

        return {
            "risk_level": risk_level,
            "risk_score": round(risk_score, 1),
            "confidence_score": round(confidence, 2),
            "explanation": shap_res,
            "anomaly_status": anomaly_res,
            "recommendation": recommendation
        }

    def _rule_based_risk(self, hr: float, spo2: float, temp: float, fall: bool) -> tuple:
        """Fallback clinical rule-based engine calculating risk score + confidence."""
        scores = []
        if hr < 60:
            scores.append(40.0)
        elif hr > 100:
            scores.append(80.0 if hr > 120 else 50.0)
        else:
            scores.append(10.0)

        if spo2 < 90:
            scores.append(95.0)
        elif spo2 < 95:
            scores.append(60.0)
        else:
            scores.append(10.0)

        if temp > 38.5:
            scores.append(80.0)
        elif temp > 37.5:
            scores.append(40.0)
        elif temp < 35.0:
            scores.append(80.0)
        elif temp < 36.1:
            scores.append(40.0)
        else:
            scores.append(10.0)

        if fall:
            scores.append(95.0)

        avg_score = sum(scores) / max(len(scores), 1)
        # Baseline confidence is high for standard clinical boundaries
        return avg_score, 0.95

    def train_model(self, X: pd.DataFrame, y: pd.Series):
        """Train the classifier model and save it to models/ folder."""
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.preprocessing import StandardScaler

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        model = RandomForestClassifier(n_estimators=100, max_depth=8, random_state=42)
        model.fit(X_scaled, y)

        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        joblib.dump(model, self.model_path)
        joblib.dump(scaler, self.scaler_path)

        self.model = model
        self.scaler = scaler
        logger.info(f"Model trained and saved to {self.model_path}")
