import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

class DataPipeline:
    """Preprocesses and validates clinical vital sign streams before inference."""

    PHYSIOLOGICAL_RANGES = {
        "heart_rate": (40.0, 200.0),
        "spo2": (50.0, 100.0),
        "temperature": (30.0, 45.0)
    }

    @classmethod
    def clean_reading(cls, heart_rate: float, spo2: float, temperature: float) -> dict:
        """ physiological boundary capping for robustness against sensor noise. """
        cleaned = {
            "heart_rate": float(np.clip(heart_rate, cls.PHYSIOLOGICAL_RANGES["heart_rate"][0], cls.PHYSIOLOGICAL_RANGES["heart_rate"][1])),
            "spo2": float(np.clip(spo2, cls.PHYSIOLOGICAL_RANGES["spo2"][0], cls.PHYSIOLOGICAL_RANGES["spo2"][1])),
            "temperature": float(np.clip(temperature, cls.PHYSIOLOGICAL_RANGES["temperature"][0], cls.PHYSIOLOGICAL_RANGES["temperature"][1]))
        }
        return cleaned

    @classmethod
    def validate_reading(cls, heart_rate: float, spo2: float, temperature: float) -> list:
        """ Returns a list of physiological alert warnings if readings are abnormal. """
        warnings = []
        if heart_rate < 60 or heart_rate > 100:
            warnings.append("Heart rate is out of normal resting bounds (60-100 BPM).")
        if spo2 < 95:
            warnings.append("SpO2 level is below normal (95-100%).")
        if temperature < 36.1 or temperature > 37.5:
            warnings.append("Body temperature deviates from normal range (36.1-37.5 C).")
        return warnings
