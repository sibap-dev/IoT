from datetime import datetime, timezone
from database.db import db
from werkzeug.security import generate_password_hash, check_password_hash
import json


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="PATIENT")  # PATIENT, DOCTOR, ADMIN
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    patient_profile = db.relationship("Patient", backref="user", uselist=False, cascade="all, delete-orphan")
    doctor_profile = db.relationship("Doctor", backref="user", uselist=False, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "role": self.role,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class Doctor(db.Model):
    __tablename__ = "doctors"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    name = db.Column(db.String(200), nullable=False)
    specialty = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    patients = db.relationship("Patient", backref="doctor", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "specialty": self.specialty,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class Patient(db.Model):
    __tablename__ = "patients"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    name = db.Column(db.String(200), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    age = db.Column(db.Integer, nullable=True)
    gender = db.Column(db.String(20), nullable=True)
    blood_group = db.Column(db.String(10), nullable=True)
    emergency_contact = db.Column(db.String(200), nullable=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id"), nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    readings = db.relationship("HealthReading", backref="patient", lazy="dynamic")
    predictions = db.relationship("PredictionHistory", backref="patient", lazy="dynamic")
    alerts = db.relationship("AlertHistory", backref="patient", lazy="dynamic")
    recommendations = db.relationship("Recommendation", backref="patient", lazy="dynamic")
    devices = db.relationship("Device", backref="patient", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "patient_id": self.patient_id,
            "name": self.name,
            "user_id": self.user_id,
            "age": self.age,
            "gender": self.gender,
            "blood_group": self.blood_group,
            "emergency_contact": self.emergency_contact,
            "doctor_id": self.doctor_id,
            "doctor_name": self.doctor.name if self.doctor else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Device(db.Model):
    __tablename__ = "devices"

    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    patient_id = db.Column(db.String(100), db.ForeignKey("patients.patient_id"), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "device_id": self.device_id,
            "patient_id": self.patient_id,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class HealthReading(db.Model):
    __tablename__ = "health_readings"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(
        db.String(100), db.ForeignKey("patients.patient_id"), nullable=True, index=True
    )
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    heart_rate = db.Column(db.Float, nullable=False)
    spo2 = db.Column(db.Float, nullable=False)
    temperature = db.Column(db.Float, nullable=False)
    fall_detected = db.Column(db.Boolean, default=False)

    # Accelerometer / falling vector dynamics placeholders
    acceleration_x = db.Column(db.Float, nullable=True, default=0.0)
    acceleration_y = db.Column(db.Float, nullable=True, default=0.0)
    acceleration_z = db.Column(db.Float, nullable=True, default=0.0)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    predictions = db.relationship("PredictionHistory", backref="health_reading", lazy="dynamic")
    alerts = db.relationship("AlertHistory", backref="health_reading", lazy="dynamic")

    def to_dict(self):
        def _safe_iso(dt):
            if dt is None:
                return None
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat()

        return {
            "id": self.id,
            "patient_id": self.patient_id,
            "timestamp": _safe_iso(self.timestamp),
            "heart_rate": self.heart_rate,
            "spo2": self.spo2,
            "temperature": self.temperature,
            "fall_detected": self.fall_detected,
            "acceleration_x": self.acceleration_x,
            "acceleration_y": self.acceleration_y,
            "acceleration_z": self.acceleration_z,
            "created_at": _safe_iso(self.created_at),
        }


class PredictionHistory(db.Model):
    __tablename__ = "prediction_history"

    id = db.Column(db.Integer, primary_key=True)
    health_reading_id = db.Column(
        db.Integer, db.ForeignKey("health_readings.id"), nullable=True, index=True
    )
    patient_id = db.Column(
        db.String(100), db.ForeignKey("patients.patient_id"), nullable=True, index=True
    )
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    heart_rate = db.Column(db.Float, nullable=False)
    spo2 = db.Column(db.Float, nullable=False)
    temperature = db.Column(db.Float, nullable=False)
    fall_detected = db.Column(db.Boolean, default=False)
    risk_level = db.Column(db.String(20), nullable=False)
    risk_score = db.Column(db.Float, nullable=False)

    confidence_score = db.Column(db.Float, nullable=True, default=1.0)
    explanation = db.Column(db.Text, nullable=True)  # SHAP / contribution metrics JSON string

    recommendation = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        try:
            exp_data = json.loads(self.explanation) if self.explanation else None
        except Exception:
            exp_data = self.explanation

        def _safe_iso(dt):
            if dt is None:
                return None
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat()

        return {
            "id": self.id,
            "health_reading_id": self.health_reading_id,
            "patient_id": self.patient_id,
            "timestamp": _safe_iso(self.timestamp),
            "heart_rate": self.heart_rate,
            "spo2": self.spo2,
            "temperature": self.temperature,
            "fall_detected": self.fall_detected,
            "risk_level": self.risk_level,
            "risk_score": self.risk_score,
            "confidence_score": self.confidence_score,
            "explanation": exp_data,
            "recommendation": self.recommendation,
            "created_at": _safe_iso(self.created_at),
        }


class AlertHistory(db.Model):
    __tablename__ = "alert_history"

    id = db.Column(db.Integer, primary_key=True)
    health_reading_id = db.Column(
        db.Integer, db.ForeignKey("health_readings.id"), nullable=True, index=True
    )
    patient_id = db.Column(
        db.String(100), db.ForeignKey("patients.patient_id"), nullable=True, index=True
    )
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    alert_type = db.Column(db.String(50), nullable=False)
    severity = db.Column(db.String(20), nullable=False)  # LOW, MEDIUM, HIGH, CRITICAL, EMERGENCY
    message = db.Column(db.Text, nullable=False)
    value = db.Column(db.Float, nullable=True)
    threshold = db.Column(db.Float, nullable=True)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        def _safe_iso(dt):
            if dt is None:
                return None
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat()

        return {
            "id": self.id,
            "health_reading_id": self.health_reading_id,
            "patient_id": self.patient_id,
            "timestamp": _safe_iso(self.timestamp),
            "alert_type": self.alert_type,
            "severity": self.severity,
            "message": self.message,
            "value": self.value,
            "threshold": self.threshold,
            "is_read": self.is_read,
            "created_at": _safe_iso(self.created_at),
        }


class Recommendation(db.Model):
    __tablename__ = "recommendations"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(
        db.String(100), db.ForeignKey("patients.patient_id"), nullable=True, index=True
    )
    recommendation_text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "patient_id": self.patient_id,
            "recommendation_text": self.recommendation_text,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ModelMetrics(db.Model):
    __tablename__ = "model_metrics"

    id = db.Column(db.Integer, primary_key=True)
    model_name = db.Column(db.String(100), nullable=False)
    train_accuracy = db.Column(db.Float, nullable=True)
    test_accuracy = db.Column(db.Float, nullable=True)
    precision = db.Column(db.Float, nullable=True)
    recall = db.Column(db.Float, nullable=True)
    trained_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "model_name": self.model_name,
            "train_accuracy": self.train_accuracy,
            "test_accuracy": self.test_accuracy,
            "precision": self.precision,
            "recall": self.recall,
            "trained_at": self.trained_at.isoformat() if self.trained_at else None
        }
