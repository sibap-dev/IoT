import logging

logger = logging.getLogger(__name__)

class RecommendationEngine:
    """Generates personalized, clinical-grade medical guidelines based on physiological states."""

    @staticmethod
    def generate(heart_rate: float, spo2: float, temperature: float, fall_detected: bool) -> str:
        advices = []

        if fall_detected:
            return "Emergency: Fall detected! Please remain still. An alert has been dispatched to your assigned healthcare provider and emergency contacts immediately."

        # SpO2 checks (highest priority after falls)
        if spo2 < 90:
            advices.append("Critical hypoxia (SpO2 < 90%). Sit upright, breathe deeply, and seek IMMEDIATE medical attention.")
        elif spo2 < 95:
            advices.append("Mild blood oxygen desaturation. Rest, sit in a well-ventilated space, and focus on deep breathing exercises.")

        # Heart rate checks
        if heart_rate > 120:
            advices.append("Significant tachycardia. Sit down immediately, drink water, practice slow breathing, and avoid physical exertion.")
        elif heart_rate > 100:
            advices.append("Elevated heart rate. Avoid caffeine or stress. Rest quietly and monitor your heart rate over the next 15 minutes.")
        elif heart_rate < 50:
            advices.append("Bradycardia detected. If you feel dizzy, faint, or weak, sit or lie down immediately and alert your caregiver.")

        # Temperature checks
        if temperature > 38.5:
            advices.append("High fever detected. Stay well-hydrated, apply a cool damp compress, and rest. Monitor for headache or breathing difficulties.")
        elif temperature > 37.5:
            advices.append("Low-grade fever. Increase fluid intake, rest, and keep the ambient room temperature comfortable.")
        elif temperature < 35.0:
            advices.append("Hypothermia warning. Wear warm clothing layers, wrap in blankets, and consume warm fluids. Avoid cold drafts.")

        if not advices:
            # All vitals within optimal bounds
            return "Vitals are normal. Keep up the good health! Ensure you stay hydrated, eat balanced meals, and aim for 7-8 hours of sleep."

        # Join individual advices together
        return " ".join(advices)
