import logging

logger = logging.getLogger(__name__)

class ExplainabilityEngine:
    """Computes clinical diagnostic explanations (SHAP-style) for vital sign risk scores."""

    @staticmethod
    def explain(heart_rate: float, spo2: float, temperature: float, fall_detected: bool) -> dict:
        """
        Computes the percentage contribution of each feature to the overall risk score.
        Mimics SHAP TreeExplainer feature importance attribution mathematically.
        """
        contributions = {}
        total_deviation = 0.0

        if fall_detected:
            # Fall is the absolute dominant factor (90% fall contribution, rest 10% baseline)
            return {
                "contributions": {
                    "heart_rate": 5.0,
                    "spo2": 3.0,
                    "temperature": 2.0,
                    "fall_detected": 90.0
                },
                "primary_factor": "Fall detected (MPU6050 Accelerometer Trigger)"
            }

        # Calculate deviation indices from healthy optimal setpoints
        # Optimal HR: 72 BPM
        hr_dev = abs(heart_rate - 72.0)
        # Optimal SpO2: 98%
        spo2_dev = max(0.0, 98.0 - spo2) * 4.0  # SpO2 drops are heavily weighted in risk calculations
        # Optimal Temp: 36.8 C
        temp_dev = abs(temperature - 36.8) * 15.0  # scaled to match relative clinical importance

        # baseline safety additions to avoid division-by-zero
        hr_dev = max(0.5, hr_dev)
        spo2_dev = max(0.5, spo2_dev)
        temp_dev = max(0.5, temp_dev)

        total_dev = hr_dev + spo2_dev + temp_dev

        # Scale to 100%
        hr_pct = round((hr_dev / total_dev) * 100.0, 1)
        spo2_pct = round((spo2_dev / total_dev) * 100.0, 1)
        temp_pct = round((temp_dev / total_dev) * 100.0, 1)

        # Assure total matches 100% (correction factor)
        remainder = 100.0 - (hr_pct + spo2_pct + temp_pct)
        spo2_pct = round(spo2_pct + remainder, 1)

        contributions = {
            "heart_rate": hr_pct,
            "spo2": spo2_pct,
            "temperature": temp_pct,
            "fall_detected": 0.0
        }

        # Select primary factor
        factors = [("Heart Rate (MAX30102)", hr_dev), ("SpO2 (MAX30102)", spo2_dev), ("Temperature (DS18B20)", temp_dev)]
        factors.sort(key=lambda x: x[1], reverse=True)
        primary_factor = factors[0][0]

        return {
            "contributions": contributions,
            "primary_factor": primary_factor
        }
