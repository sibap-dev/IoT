from datetime import datetime, timezone
from database.db import db
from database.models import AlertHistory
from config import Config


class AlertService:
    """
    Alert engine that checks vital sign thresholds and persists alerts.

    Architecture supports future notification channels without changes:
      - Email alerts      (add send_email() method)
      - SMS alerts        (add send_sms() method)
      - Telegram alerts   (add send_telegram() method)
      - Push notifications (add send_push() method)

    Usage:
        alerts = AlertService.check_reading(hr=72, spo2=98, temp=36.8, fall=False)
        for a in alerts:
            AlertService.send_email(a)   # future
            AlertService.send_sms(a)     # future
    """

    THRESHOLDS = {
        "heart_rate": {
            "min": Config.HR_MIN,
            "max": Config.HR_MAX,
            "warn_max": Config.HR_WARN_MAX,
            "crit_max": Config.HR_CRIT_MAX,
            "crit_min": Config.HR_CRIT_MIN,
        },
        "spo2": {
            "min": Config.SPO2_MIN,
            "warn_min": Config.SPO2_WARN_MIN,
            "crit_min": Config.SPO2_CRIT_MIN,
        },
        "temperature": {
            "min": Config.TEMP_MIN,
            "max": Config.TEMP_MAX,
            "warn_min": Config.TEMP_WARN_MIN,
            "warn_max": Config.TEMP_WARN_MAX,
            "crit_min": Config.TEMP_CRIT_MIN,
            "crit_max": Config.TEMP_CRIT_MAX,
        },
    }

    @classmethod
    def check_reading(cls, heart_rate, spo2, temperature, fall_detected,
                      reading_id=None, patient_id=None,
                      risk_level=None, risk_score=None):
        alerts = []

        hr_t = cls.THRESHOLDS["heart_rate"]
        if heart_rate > hr_t["crit_max"]:
            alerts.append(cls._build_alert(
                "heart_rate", "critical",
                f"Heart rate {heart_rate} bpm – dangerously high! Immediate attention needed.",
                heart_rate, hr_t["crit_max"], reading_id, patient_id))
        elif heart_rate < hr_t["crit_min"]:
            alerts.append(cls._build_alert(
                "heart_rate", "critical",
                f"Heart rate {heart_rate} bpm – dangerously low! Immediate attention needed.",
                heart_rate, hr_t["crit_min"], reading_id, patient_id))
        elif heart_rate > hr_t["warn_max"]:
            alerts.append(cls._build_alert(
                "heart_rate", "high",
                f"Heart rate {heart_rate} bpm – elevated. Monitor closely.",
                heart_rate, hr_t["warn_max"], reading_id, patient_id))
        elif heart_rate < hr_t["min"]:
            alerts.append(cls._build_alert(
                "heart_rate", "high",
                f"Heart rate {heart_rate} bpm – below normal. Monitor closely.",
                heart_rate, hr_t["min"], reading_id, patient_id))
        elif heart_rate > hr_t["max"]:
            alerts.append(cls._build_alert(
                "heart_rate", "medium",
                f"Heart rate {heart_rate} bpm – slightly elevated.",
                heart_rate, hr_t["max"], reading_id, patient_id))

        spo2_t = cls.THRESHOLDS["spo2"]
        if spo2 < spo2_t["crit_min"]:
            alerts.append(cls._build_alert(
                "spo2", "critical",
                f"SpO2 {spo2}% – critically low! Oxygen support may be needed.",
                spo2, spo2_t["crit_min"], reading_id, patient_id))
        elif spo2 < spo2_t["warn_min"]:
            alerts.append(cls._build_alert(
                "spo2", "high",
                f"SpO2 {spo2}% – below normal range. Monitor breathing.",
                spo2, spo2_t["warn_min"], reading_id, patient_id))

        temp_t = cls.THRESHOLDS["temperature"]
        if temperature > temp_t["crit_max"]:
            alerts.append(cls._build_alert(
                "temperature", "critical",
                f"Temperature {temperature}°C – dangerously high fever! Immediate cooling needed.",
                temperature, temp_t["crit_max"], reading_id, patient_id))
        elif temperature < temp_t["crit_min"]:
            alerts.append(cls._build_alert(
                "temperature", "critical",
                f"Temperature {temperature}°C – dangerously low! Warming required.",
                temperature, temp_t["crit_min"], reading_id, patient_id))
        elif temperature > temp_t["warn_max"]:
            alerts.append(cls._build_alert(
                "temperature", "high",
                f"Temperature {temperature}°C – elevated. Watch for fever.",
                temperature, temp_t["warn_max"], reading_id, patient_id))
        elif temperature < temp_t["warn_min"]:
            alerts.append(cls._build_alert(
                "temperature", "high",
                f"Temperature {temperature}°C – below normal. Monitor for hypothermia.",
                temperature, temp_t["warn_min"], reading_id, patient_id))

        if fall_detected:
            alerts.append(cls._build_alert(
                "fall", "emergency",
                "Fall detected! Immediate assistance required.",
                1, 0, reading_id, patient_id))

        if risk_level and risk_score is not None:
            if risk_level == "Critical":
                alerts.append(cls._build_alert(
                    "ml_risk", "critical",
                    "Critical risk detected by AI analysis – immediate intervention required!",
                    risk_score, 80.0, reading_id, patient_id))
            elif risk_level == "High":
                alerts.append(cls._build_alert(
                    "ml_risk", "high",
                    "High risk detected by AI analysis – medical assessment recommended.",
                    risk_score, 50.0, reading_id, patient_id))
            elif risk_level == "Medium":
                alerts.append(cls._build_alert(
                    "ml_risk", "medium",
                    "Moderate risk detected by AI analysis – monitor patient closely.",
                    risk_score, 25.0, reading_id, patient_id))

        # Auto-resolve: mark previous unread alerts as read when condition normalizes
        fired_types = {a.alert_type for a in alerts}
        SEVERITY_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3, "emergency": 4}
        filter_kwargs = {"patient_id": patient_id} if patient_id else {"patient_id": None}
        prev_unread = AlertHistory.query.filter_by(
            is_read=False, **filter_kwargs
        ).all()
        for prev in prev_unread:
            should_resolve = False
            if prev.alert_type == "ml_risk":
                if risk_level == "Low":
                    should_resolve = True
                elif risk_level in ("Medium", "High", "Critical"):
                    current_sev = SEVERITY_ORDER.get(risk_level.lower(), 0)
                    prev_sev = SEVERITY_ORDER.get(prev.severity.lower(), 0)
                    if current_sev < prev_sev:
                        should_resolve = True
            elif prev.alert_type == "fall":
                if not fall_detected:
                    should_resolve = True
            elif prev.alert_type in ("heart_rate", "spo2", "temperature"):
                if prev.alert_type not in fired_types:
                    should_resolve = True
            if should_resolve:
                prev.is_read = True

        for alert in alerts:
            db.session.add(alert)
        # NOTE: caller is responsible for db.session.commit()

        return alerts

    @classmethod
    def _build_alert(cls, alert_type, severity, message, value, threshold,
                     reading_id=None, patient_id=None):
        return AlertHistory(
            health_reading_id=reading_id,
            patient_id=patient_id,
            timestamp=datetime.now(timezone.utc),
            alert_type=alert_type,
            severity=severity,
            message=message,
            value=float(value),
            threshold=float(threshold),
        )

    @staticmethod
    def get_recent_alerts(limit=20, patient_id=None, unread_only=False):
        q = AlertHistory.query.order_by(AlertHistory.created_at.desc())
        if patient_id:
            q = q.filter_by(patient_id=patient_id)
        if unread_only:
            q = q.filter_by(is_read=False)
        return q.limit(limit).all()

    @staticmethod
    def mark_as_read(alert_id):
        alert = AlertHistory.query.get(alert_id)
        if alert:
            alert.is_read = True
            db.session.commit()
            return True
        return False

    @staticmethod
    def mark_all_read(patient_id=None):
        q = AlertHistory.query.filter_by(is_read=False)
        if patient_id:
            q = q.filter_by(patient_id=patient_id)
        q.update({"is_read": True})
        db.session.commit()
        return True

    # Future notification stubs — implement when email / SMS / Telegram is wired up
    @staticmethod
    def send_email(alert):
        pass

    @staticmethod
    def send_sms(alert):
        pass

    @staticmethod
    def send_telegram(alert):
        pass
