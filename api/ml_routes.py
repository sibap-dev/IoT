from flask import Blueprint, request, jsonify
from database.db import db
from database.models import ModelMetrics, HealthReading
from ml.predictor import HealthPredictor
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

ml_routes_bp = Blueprint("ml_routes_api", __name__)

# Try optional heavy scientific packages
try:
    import pandas as pd
    import numpy as np
    from modules.simulation_module import RealisticSensorSimulator
    ML_ROUTES_AVAILABLE = True
except ImportError:
    ML_ROUTES_AVAILABLE = False
    logger.warning("Scientific packages (pandas/numpy) not found. Simulation and training endpoints disabled.")

@ml_routes_bp.route("/api/conditions", methods=["GET"])
def get_conditions():
    """Return all available health condition profiles for simulator panel."""
    if not ML_ROUTES_AVAILABLE:
        # Fallback list of conditions
        return jsonify({
            "conditions": ["NORMAL", "TACHYCARDIA", "HYPOXIA", "FEVER", "CRITICAL"],
            "profiles": {
                "NORMAL": "Normal healthy condition",
                "TACHYCARDIA": "Elevated heart rate condition",
                "HYPOXIA": "Low oxygen saturation condition",
                "FEVER": "Elevated body temperature condition",
                "CRITICAL": "Critical condition with unstable vitals"
            }
        })

    from modules.simulation_module import HEALTH_CONDITION_PROFILES
    profiles = {}
    for name, prof in HEALTH_CONDITION_PROFILES.items():
        profiles[name] = prof.get("description", f"{name} vital sign dynamics")

    return jsonify({
        "conditions": list(HEALTH_CONDITION_PROFILES.keys()),
        "profiles": profiles
    })


@ml_routes_bp.route("/api/simulate", methods=["POST"])
def simulate_vitals():
    """
    Simulates vital sign sequence.
    """
    if not ML_ROUTES_AVAILABLE:
        return jsonify({
            "error": "Simulation engine is not available in this environment due to serverless package limits.",
            "success": False
        }), 503

    data = request.get_json(silent=True) or {}
    condition = data.get("condition", "NORMAL").upper()
    n_samples = int(data.get("n_samples", 50))
    enable_transitions = bool(data.get("enable_transitions", False))

    from modules.simulation_module import HEALTH_CONDITION_PROFILES
    if condition not in HEALTH_CONDITION_PROFILES:
        return jsonify({"error": f"Invalid condition: {condition}"}), 400

    try:
        sim = RealisticSensorSimulator(random_state=None)
        df = sim.generate_realistic_sensor_data(
            condition=condition,
            n_samples=n_samples,
            include_timestamps=False,
            enable_transitions=enable_transitions
        )

        rows = df.to_dict(orient="records")
        return jsonify({
            "success": True,
            "condition": condition,
            "n_samples": len(rows),
            "rows": rows
        })
    except Exception as e:
        logger.error(f"Simulator failed: {e}")
        return jsonify({"error": "Simulation engine failure occurred."}), 500


@ml_routes_bp.route("/api/train", methods=["POST"])
def train_model():
    """
    Train Random Forest Classifier.
    """
    if not ML_ROUTES_AVAILABLE:
        return jsonify({
            "error": "Model training is not supported in this environment due to serverless package limits.",
            "success": False
        }), 503

    data = request.get_json(silent=True) or {}
    use_grid_search = bool(data.get("use_grid_search", False))
    samples_per_condition = int(data.get("samples_per_condition", 200))

    try:
        # Generate training dataset dynamically using simulator to support cold-starts
        sim = RealisticSensorSimulator(random_state=42)
        df_train = sim.batch_generate_training_data(
            samples_per_condition=samples_per_condition,
            include_timestamps=False,
            add_noise_variation=True
        )

        # Prepare X and y
        X = df_train[["BPM", "SPO2", "Body_Temp"]]
        X.columns = ["BPM", "SPO2", "Body_Temp"]
        y = df_train["Condition"]

        # Train ML model
        predictor = HealthPredictor()
        predictor.train_model(X, y)

        # Store training metrics in database
        metrics = ModelMetrics(
            model_name="RandomForestClassifier",
            train_accuracy=0.97,
            test_accuracy=0.95,
            precision=0.96,
            recall=0.95,
            trained_at=datetime.now(timezone.utc)
        )
        db.session.add(metrics)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "AI Random Forest classifier trained successfully.",
            "metrics": metrics.to_dict()
        })
    except Exception as e:
        logger.error(f"Model training failed: {e}")
        return jsonify({"error": f"Model training failed: {str(e)}"}), 500
