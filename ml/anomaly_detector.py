import os
import logging

logger = logging.getLogger(__name__)

# Try optional heavy scientific packages
try:
    import joblib
    import numpy as np
    import pandas as pd
    from sklearn.ensemble import IsolationForest
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    logger.warning("Scientific packages (pandas/numpy/scikit-learn/joblib) not found. Falling back to rule-based stubs.")

class AnomalyDetector:
    """Uses an Isolation Forest to detect abnormal physiological patterns, or stubs when offline/serverless."""

    def __init__(self):
        self.model_path = os.path.join(os.path.dirname(__file__), "models", "isolation_forest.joblib")
        self.model = None
        if ML_AVAILABLE:
            self._load_or_train_initial()

    def _load_or_train_initial(self):
        """Attempts to load a trained model; falls back to self-training on synthetic normal baseline."""
        if not ML_AVAILABLE:
            return
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        if os.path.exists(self.model_path):
            try:
                self.model = joblib.load(self.model_path)
                logger.info("Successfully loaded Isolation Forest model from disk.")
                return
            except Exception as e:
                logger.error(f"Error loading Isolation Forest: {e}. Retraining...")

        # Dynamically fit on a synthetic "normal" vitals dataset
        logger.info("No Isolation Forest model found. Training self-healing baseline...")
        try:
            np.random.seed(42)
            normal_hr = np.random.normal(72, 6, 500)
            normal_spo2 = np.random.normal(98, 0.8, 500)
            normal_temp = np.random.normal(36.6, 0.2, 500)

            # Clip values to standard range
            normal_spo2 = np.clip(normal_spo2, 94.0, 100.0)

            df = pd.DataFrame({
                "heart_rate": normal_hr,
                "spo2": normal_spo2,
                "temperature": normal_temp
            })

            self.model = IsolationForest(contamination=0.05, random_state=42)
            self.model.fit(df)

            joblib.dump(self.model, self.model_path)
            logger.info(f"Successfully saved dynamic Isolation Forest baseline to {self.model_path}")
        except Exception as e:
            logger.error(f"Failed to fit/persist Isolation Forest: {e}")

    def predict(self, heart_rate: float, spo2: float, temperature: float) -> dict:
        """
        Runs anomaly check using Isolation Forest or simple clinical rule fallback.
        """
        # Clinical fallback logic
        is_anomaly = bool(heart_rate > 105 or heart_rate < 55 or spo2 < 93 or temperature > 38.0 or temperature < 35.5)

        if not ML_AVAILABLE or self.model is None:
            return {
                "is_anomaly": is_anomaly,
                "anomaly_score": 75.0 if is_anomaly else 10.0,
                "decision_score": -0.2 if is_anomaly else 0.2
            }

        try:
            df = pd.DataFrame([[heart_rate, spo2, temperature]], columns=["heart_rate", "spo2", "temperature"])
            pred = self.model.predict(df)[0]  # 1 = normal, -1 = anomaly
            score = self.model.decision_function(df)[0]  # lower means more anomalous

            is_anomaly_model = bool(pred == -1)
            anomaly_intensity = float(np.clip((0.5 - score) * 100, 0, 100))

            return {
                "is_anomaly": is_anomaly_model,
                "anomaly_score": round(anomaly_intensity, 2),
                "decision_score": round(float(score), 4)
            }
        except Exception as e:
            logger.error(f"Isolation Forest inference exception: {e}")
            return {
                "is_anomaly": is_anomaly,
                "anomaly_score": 75.0 if is_anomaly else 10.0,
                "decision_score": -0.2 if is_anomaly else 0.2
            }

    def retrain(self, df_vitals):
        """Retrains the Isolation Forest with actual clinical patient logs (no-op if ML disabled)."""
        if not ML_AVAILABLE:
            logger.warning("Retraining skipped: ML dependencies not installed.")
            return

        if df_vitals.empty or len(df_vitals) < 10:
            logger.warning("Insufficient data logs to retrain Isolation Forest.")
            return

        try:
            new_model = IsolationForest(contamination=0.04, random_state=42)
            vitals_df = df_vitals[["heart_rate", "spo2", "temperature"]]
            new_model.fit(vitals_df)
            self.model = new_model
            joblib.dump(self.model, self.model_path)
            logger.info("Successfully retrained and persisted new Isolation Forest model.")
        except Exception as e:
            logger.error(f"Retraining Isolation Forest failed: {e}")
