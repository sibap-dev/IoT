import pandas as pd
import numpy as np
import logging
from database.models import HealthReading

logger = logging.getLogger(__name__)

class FeatureEngineer:
    """Calculates temporal, trend, and variability features from patient health history."""

    @staticmethod
    def extract_history_features(patient_id: str, limit: int = 15) -> dict:
        """
        Queries patient history and computes rolling averages, HRV, trends, and activity metrics.
        Returns engineered features to augment current predictions.
        """
        # Fetch latest readings
        readings = HealthReading.query.filter_by(patient_id=patient_id).order_by(HealthReading.timestamp.desc()).limit(limit).all()

        if not readings:
            # Cold-start defaults
            return {
                "rolling_avg_hr": 75.0,
                "hrv": 8.0,
                "spo2_trend": 0.0,
                "temp_trend": 0.0,
                "activity_level": "RESTING",
                "fall_frequency": 0,
                "historical_risk_trend": 0.0
            }

        # Reverse so they are in chronological order
        readings = list(reversed(readings))
        hrs = [r.heart_rate for r in readings]
        spo2s = [r.spo2 for r in readings]
        temps = [r.temperature for r in readings]
        falls = [r.fall_detected for r in readings]

        # 1. Rolling average heart rate
        rolling_avg_hr = float(np.mean(hrs))

        # 2. HRV (Heart Rate Variability approximation - standard deviation)
        hrv = float(np.std(hrs)) if len(hrs) > 1 else 5.0
        if hrv < 1.0:
            hrv = 5.0  # sensible minimum baseline

        # 3. Trends (current - rolling mean)
        latest_hr = hrs[-1]
        latest_spo2 = spo2s[-1]
        latest_temp = temps[-1]

        spo2_trend = float(latest_spo2 - np.mean(spo2s))
        temp_trend = float(latest_temp - np.mean(temps))

        # 4. Activity level approximation matching modules/data_module.py
        activity_level = "RESTING"
        if latest_hr > 130:
            activity_level = "INTENSE_ACTIVITY"
        elif latest_hr > 100:
            activity_level = "MODERATE_ACTIVITY"
        elif latest_hr > 75:
            activity_level = "LIGHT_ACTIVITY"

        # 5. Fall frequency
        fall_frequency = int(sum(1 for f in falls if f))

        return {
            "rolling_avg_hr": round(rolling_avg_hr, 1),
            "hrv": round(hrv, 1),
            "spo2_trend": round(spo2_trend, 2),
            "temp_trend": round(temp_trend, 2),
            "activity_level": activity_level,
            "fall_frequency": fall_frequency,
            "historical_risk_trend": round(float(np.std(hrs)) * 0.1, 2)  # proxy risk score trend
        }
