"""
IoT Healthcare Platform — Main Flask Application

Architecture:
  - api/sensor_routes.py    POST /api/sensor-data, GET /api/latest-data, GET /api/sensor-history
  - api/prediction_routes.py POST /api/predict, GET /api/latest-prediction, GET /api/predictions
  - api/alert_routes.py     GET /api/alerts, PATCH /api/alerts/<id>/read, PATCH /api/alerts/read-all
  - database/models.py      Patient, HealthReading, PredictionHistory, AlertHistory
  - services/               PredictionService, AlertService
  - ml/predictor.py         Rule-based risk engine (swap-ready for ML models)
  - sensor_simulator.py     Test data generator (replaces ESP32 during development)

Run:  python app.py
Open: http://localhost:5000

ESP32 Integration (future):
  Send POST http://<server-ip>:5000/api/sensor-data
  Body: { "heart_rate": 78, "spo2": 98, "temperature": 36.8, "fall_detected": false }
"""
import logging
from flask import Flask, render_template, jsonify

from config import Config
from database.db import init_db
from api import sensor_bp, prediction_bp, alert_bp
from routes.auth import auth_bp
from api.ml_routes import ml_routes_bp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.secret_key = app.config.get("SECRET_KEY")

    # ── Database ──────────────────────────────────────────────────────────────
    init_db(app)

    # ── API Blueprints ────────────────────────────────────────────────────────
    app.register_blueprint(sensor_bp)       # /api/sensor-data, /api/latest-data, /api/sensor-history
    app.register_blueprint(prediction_bp)   # /api/predict, /api/latest-prediction, /api/predictions
    app.register_blueprint(alert_bp)        # /api/alerts, /api/alerts/<id>/read
    app.register_blueprint(auth_bp)         # /api/auth/signup, /api/auth/login, /api/auth/logout, /api/auth/session
    app.register_blueprint(ml_routes_bp)    # /api/train, /api/simulate, /api/conditions

    # ── Dashboard ─────────────────────────────────────────────────────────────
    @app.route("/")
    def index():
        return render_template("index.html")

    # ── Health check ──────────────────────────────────────────────────────────
    @app.route("/health")
    def health():
        from database.models import HealthReading
        with app.app_context():
            total = HealthReading.query.count()
            latest = HealthReading.query.order_by(HealthReading.created_at.desc()).first()
        return jsonify({
            "status": "healthy",
            "total_readings": total,
            "last_reading": latest.to_dict() if latest else None,
        })

    # ── Catch-all 404 ─────────────────────────────────────────────────────────
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Endpoint not found", "hint": "See /health for status"}), 404

    @app.errorhandler(500)
    def server_error(e):
        logger.exception("Unhandled error")
        return jsonify({"error": "Internal server error"}), 500

    return app


def start_simulator():
    import subprocess
    import time
    import os
    # Wait for the Flask development server to boot and bind to port 5001
    time.sleep(3)
    port = 5001
    url = f"http://127.0.0.1:{port}/api/sensor-data"
    try:
        subprocess.Popen(
            ["python", "sensor_simulator.py", "--url", url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True if os.name != 'nt' else False
        )
        print(f"\n  [Auto-Bootstrap] Sensor simulator successfully started targeting: {url}\n")
    except Exception as e:
        print(f"\n  [Auto-Bootstrap] Failed to start simulator: {e}\n")


app = create_app()

if __name__ == "__main__":
    import os, threading
    IS_VERCEL = os.environ.get("VERCEL") == "1"

    print("\n  IoT Healthcare Platform")
    print("  Dashboard  -> http://localhost:5001")
    print("  Health     -> http://localhost:5001/health")
    print("  Sensor API -> POST http://localhost:5001/api/sensor-data")
    if IS_VERCEL:
        print("  [Vercel]  Running in serverless mode — simulator disabled\n")
    else:
        print("  Simulator  -> python sensor_simulator.py\n")
        # Spawn background simulator only in local dev, only in the active worker
        if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
            threading.Thread(target=start_simulator, daemon=True).start()
        elif not os.environ.get("WERKZEUG_RUN_MAIN"):
            threading.Thread(target=start_simulator, daemon=True).start()

    app.run(debug=not IS_VERCEL, host="0.0.0.0", port=5001, use_reloader=not IS_VERCEL)

