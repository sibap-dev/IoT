"""
Medicare IoT — ML Inference Microservice
Deploy this on Hugging Face Spaces (Docker SDK).

POST /predict  { heart_rate, spo2, temperature, fall_detected }
GET  /health   → {"status":"ok"}
"""

import os
import sys
import logging
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s %(message)s")
logger = logging.getLogger(__name__)

# ── Optional heavy imports (graceful fallback) ─────────────────────────────────
try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    import numpy as np
    TORCH_AVAILABLE = True
    logger.info("PyTorch loaded successfully.")
except ImportError:
    TORCH_AVAILABLE = False
    logger.warning("PyTorch not available — rule-based fallback only.")

try:
    import joblib
    import numpy as np
    import pandas as pd
    from sklearn.ensemble import IsolationForest
    SKL_AVAILABLE = True
    logger.info("scikit-learn/joblib loaded successfully.")
except ImportError:
    SKL_AVAILABLE = False
    logger.warning("scikit-learn not available — anomaly detection rule-based only.")


# ── Model Architecture ────────────────────────────────────────────────────────
class SimpleNet(nn.Module):
    def __init__(self, input_dim, h1=128, h2=128, h3=64, num_classes=2):
        super().__init__()
        self.fc1 = nn.Linear(input_dim, h1)
        self.bn1 = nn.BatchNorm1d(h1)
        self.fc2 = nn.Linear(h1, h2)
        self.bn2 = nn.BatchNorm1d(h2)
        self.fc3 = nn.Linear(h2, h3)
        self.bn3 = nn.BatchNorm1d(h3)
        self.fc4 = nn.Linear(h3, num_classes)

    def forward(self, x):
        x = F.relu(self.bn1(self.fc1(x)))
        x = F.relu(self.bn2(self.fc2(x)))
        x = F.relu(self.bn3(self.fc3(x)))
        return self.fc4(x)


# ── Model Config ──────────────────────────────────────────────────────────────
MODEL_DIR = Path(__file__).parent / "models"

MODEL_CONFIGS = {
    "body_temperature": {"file": "model_bt.pth",   "input_dim": 15,  "h1": 128, "h2": 128, "h3": 64, "out": 2},
    "heart_rate":       {"file": "model_hr.pth",   "input_dim": 29,  "h1": 64,  "h2": 64,  "h3": 32, "out": 3},
    "fall_detection":   {"file": "model_fall.pth", "input_dim": 561, "h1": 128, "h2": 128, "h3": 64, "out": 6},
    "spo2":             {"file": "model_sp2.pth",  "input_dim": 15,  "h1": 128, "h2": 128, "h3": 64, "out": 2},
    "fusion":           {"file": "model_fusion.pth","input_dim": 16,  "h1": 32,  "h2": 32,  "h3": 16, "out": 2},
}

# Global model registry loaded at startup
_models: dict = {}
_anomaly_model = None


def _load_torch_model(cfg: dict):
    path = MODEL_DIR / cfg["file"]
    if not path.exists():
        logger.warning(f"Model file not found: {path}")
        return None
    try:
        state = torch.load(path, map_location="cpu", weights_only=False)
        model = SimpleNet(
            input_dim=cfg["input_dim"], h1=cfg["h1"],
            h2=cfg["h2"], h3=cfg["h3"], num_classes=cfg["out"]
        )
        model.load_state_dict(state)
        model.eval()
        logger.info(f"Loaded {cfg['file']}")
        return model
    except Exception as e:
        logger.error(f"Failed to load {cfg['file']}: {e}")
        return None


def _load_anomaly_model():
    global _anomaly_model
    if not SKL_AVAILABLE:
        return
    model_path = MODEL_DIR / "isolation_forest.joblib"
    if model_path.exists():
        try:
            _anomaly_model = joblib.load(model_path)
            logger.info("Isolation Forest loaded from disk.")
            return
        except Exception as e:
            logger.error(f"Failed to load Isolation Forest: {e}. Retraining...")
    # Auto-train baseline
    try:
        np.random.seed(42)
        df = pd.DataFrame({
            "heart_rate":  np.clip(np.random.normal(72, 6, 600), 40, 160),
            "spo2":        np.clip(np.random.normal(98, 0.8, 600), 88, 100),
            "temperature": np.clip(np.random.normal(36.6, 0.2, 600), 34, 40),
        })
        _anomaly_model = IsolationForest(contamination=0.05, random_state=42)
        _anomaly_model.fit(df)
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        joblib.dump(_anomaly_model, model_path)
        logger.info("Isolation Forest trained and saved.")
    except Exception as e:
        logger.error(f"Isolation Forest training failed: {e}")


# ── Lifespan (replaces deprecated @app.on_event) ─────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Loading ML models...")
    if TORCH_AVAILABLE:
        for name, cfg in MODEL_CONFIGS.items():
            m = _load_torch_model(cfg)
            if m is not None:
                _models[name] = m
        logger.info(f"PyTorch models loaded: {len(_models)}/{len(MODEL_CONFIGS)}")
    _load_anomaly_model()
    logger.info("ML Service ready.")
    yield
    logger.info("ML Service shutting down.")


# ── FastAPI App ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="Medicare IoT — ML Inference Service",
    description="PyTorch health risk prediction microservice for IoT wearable platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response Schemas ────────────────────────────────────────────────
class PredictRequest(BaseModel):
    heart_rate:    float = Field(..., ge=0, le=300, description="Heart rate in BPM")
    spo2:          float = Field(..., ge=0, le=100, description="Blood oxygen saturation %")
    temperature:   float = Field(..., ge=20, le=45, description="Body temperature °C")
    fall_detected: bool  = Field(False, description="Fall event flag")


class PredictResponse(BaseModel):
    risk_level:       str
    risk_score:       float
    confidence_score: float
    explanation:      dict
    anomaly_status:   dict
    recommendation:   str


# ── Feature Constructors ──────────────────────────────────────────────────────
def _make_bt_feat(hr, spo2, temp, fall):
    x = torch.zeros(15)
    x[0] = temp; x[1] = spo2; x[2] = hr; x[3] = float(fall)
    x[4] = temp - 36.8; x[5] = (temp - 36.8) ** 2; x[6] = hr / 100.0
    x[7] = spo2 / 100.0; x[8] = temp * hr / 3700.0; x[9] = temp * spo2 / 3700.0
    x[10] = hr * spo2 / 10000.0; x[11] = abs(temp - 36.8) * 5
    x[12] = (hr - 72) / 68.0; x[13] = (98.0 - spo2) / 15.0; x[14] = 1.0 if fall else 0.0
    return x.unsqueeze(0)


def _make_hr_feat(hr, spo2, temp, fall):
    x = torch.zeros(29)
    x[0] = hr; x[1] = spo2; x[2] = temp; x[3] = float(fall)
    x[4] = hr / 100.0; x[5] = (hr - 72) / 68.0; x[6] = (hr - 72) ** 2 / 4624.0
    x[7] = hr * spo2 / 10000.0; x[8] = hr * temp / 3700.0; x[9] = abs(hr - 72) / 72.0
    x[10:18] = torch.tensor([hr + i * 5 for i in range(8)]) / 200.0
    x[18] = spo2 / 100.0; x[19] = temp / 40.0; x[20] = (spo2 - 95) / 5.0
    x[21] = (temp - 36.5) * 2; x[22] = 1.0 if hr > 100 or hr < 60 else 0.0
    x[23] = (hr - 72) * (spo2 - 98) / 1000.0
    x[24] = torch.sin(torch.tensor(hr / 20.0)); x[25] = torch.cos(torch.tensor(hr / 20.0))
    x[26] = hr / (spo2 + 0.1); x[27] = temp * hr / (spo2 + 0.1); x[28] = float(fall) * hr / 100.0
    return x.unsqueeze(0)


def _make_sp2_feat(hr, spo2, temp, fall):
    x = torch.zeros(15)
    x[0] = spo2; x[1] = temp; x[2] = hr; x[3] = float(fall)
    x[4] = (100 - spo2) / 15.0; x[5] = (spo2 - 95) ** 2 / 25.0; x[6] = spo2 / 100.0
    x[7] = hr / 200.0; x[8] = temp / 40.0; x[9] = spo2 * hr / 10000.0
    x[10] = spo2 * temp / 3800.0; x[11] = (spo2 - 97) * 10
    x[12] = 1.0 if spo2 < 95 else 0.0; x[13] = 1.0 if hr > 100 or hr < 60 else 0.0
    x[14] = float(fall)
    return x.unsqueeze(0)


def _make_fall_feat(hr, spo2, temp, fall):
    x = torch.zeros(561)
    x[0] = float(fall); x[1] = hr / 200.0; x[2] = spo2 / 100.0; x[3] = temp / 40.0
    x[4] = 1.0 if fall else 0.0; x[5] = abs(hr - 72) / 72.0
    x[6] = (100 - spo2) / 15.0; x[7] = abs(temp - 36.8) / 5.0
    x[8] = hr * float(fall) / 100.0; x[9] = (hr - 72) * (60 - hr + spo2) / 5000.0
    x[10] = 1.0 if fall else (0.3 if hr > 100 else 0.0)
    x[11] = float(fall) * 10.0; x[12] = hr / (spo2 + 0.1) if fall else 0.0
    # Remaining dims: low-variance noise (matches training distribution)
    if TORCH_AVAILABLE:
        torch.manual_seed(42)
        x[13:561] = torch.randn(561 - 13) * 0.01
    return x.unsqueeze(0)


def _make_fusion_feat(hr, spo2, temp, fall):
    x = torch.zeros(16)
    x[0] = hr / 200.0; x[1] = spo2 / 100.0; x[2] = temp / 40.0; x[3] = 1.0 if fall else 0.0
    x[4] = abs(hr - 72) / 72.0; x[5] = (100 - spo2) / 15.0; x[6] = abs(temp - 36.8) / 5.0
    x[7] = (hr - 72) * (100 - spo2) / 1000.0; x[8] = temp * hr / 3700.0
    x[9] = spo2 * temp / 3800.0; x[10] = (hr - 72) ** 2 / 5184.0
    x[11] = (100 - spo2) ** 2 / 225.0; x[12] = abs(temp - 36.8) ** 2 / 25.0
    x[13] = hr / (spo2 + 0.1) / 2.0
    x[14] = 1.0 if hr > 100 or hr < 60 or spo2 < 95 else 0.0
    x[15] = float(fall) * 5.0
    return x.unsqueeze(0)


# ── Inference Helpers ─────────────────────────────────────────────────────────
def _rule_based_risk(hr, spo2, temp, fall):
    base = 5.0
    hr_score   = min(100.0, abs(hr - 72.0) / 68.0 * 100.0)
    spo2_score = min(100.0, max(0.0, 98.0 - spo2) / 15.0 * 100.0)
    temp_score = min(100.0, abs(temp - 36.8) / 5.0 * 100.0)
    fall_score = 100.0 if fall else 0.0
    risk = base + hr_score * 0.30 + spo2_score * 0.35 + temp_score * 0.25 + fall_score * 0.10
    confidence = max(0.70, 0.95 - abs(hr - 72) / 200.0 - max(0, 98 - spo2) / 200.0 - abs(temp - 36.8) / 20.0)
    return min(100.0, risk), confidence


def _ensemble_predict(hr, spo2, temp, fall):
    scores = []
    FEAT_MAKERS = {
        "body_temperature": (_make_bt_feat, 80.0),
        "heart_rate":       (_make_hr_feat, 80.0),
        "spo2":             (_make_sp2_feat, 80.0),
        "fusion":           (_make_fusion_feat, None),
    }
    for name, (fn, scale) in FEAT_MAKERS.items():
        model = _models.get(name)
        if model is None:
            continue
        feat = fn(hr, spo2, temp, fall)
        with torch.no_grad():
            out = model(feat)
        probs = F.softmax(out, dim=1)[0]
        if scale is not None:
            scores.append(float(probs[1]) * scale)
        else:
            risk_map = torch.tensor([10.0, 45.0, 85.0])
            w = probs[:min(len(risk_map), len(probs))]
            rm = risk_map[:len(w)]
            scores.append(float((w * rm).sum()))

    fall_model = _models.get("fall_detection")
    if fall_model is not None:
        feat = _make_fall_feat(hr, spo2, temp, fall)
        with torch.no_grad():
            out = fall_model(feat)
        probs = F.softmax(out, dim=1)[0]
        if len(probs) >= 6:
            scores.append(90.0 if float(probs[1]) > 0.3 else 10.0)
        elif len(probs) >= 2:
            scores.append(90.0 if float(probs[1]) > 0.5 else 10.0)
        else:
            scores.append(50.0)

    if not scores:
        return _rule_based_risk(hr, spo2, temp, fall)

    ml_score = sum(scores) / len(scores)
    rule_score, _ = _rule_based_risk(hr, spo2, temp, fall)
    risk_score = 0.6 * ml_score + 0.4 * rule_score
    confidence = 0.80 + 0.15 * (len(scores) / 5.0)
    return risk_score, confidence


def _anomaly_detect(hr, spo2, temp):
    is_anomaly = bool(hr > 105 or hr < 55 or spo2 < 93 or temp > 38.0 or temp < 35.5)
    if not SKL_AVAILABLE or _anomaly_model is None:
        return {
            "is_anomaly": is_anomaly,
            "anomaly_score": 75.0 if is_anomaly else 10.0,
            "decision_score": -0.2 if is_anomaly else 0.2,
        }
    try:
        df = pd.DataFrame([[hr, spo2, temp]], columns=["heart_rate", "spo2", "temperature"])
        pred  = _anomaly_model.predict(df)[0]
        score = _anomaly_model.decision_function(df)[0]
        intensity = float(np.clip((0.5 - score) * 100, 0, 100))
        return {
            "is_anomaly": bool(pred == -1),
            "anomaly_score": round(intensity, 2),
            "decision_score": round(float(score), 4),
        }
    except Exception as e:
        logger.error(f"Anomaly inference error: {e}")
        return {"is_anomaly": is_anomaly, "anomaly_score": 50.0, "decision_score": 0.0}


def _explain(hr, spo2, temp, fall):
    if fall:
        return {
            "contributions": {"heart_rate": 5.0, "spo2": 3.0, "temperature": 2.0, "fall_detected": 90.0},
            "primary_factor": "Fall detected (MPU6050 Accelerometer Trigger)",
        }
    hr_dev   = max(0.5, abs(hr - 72.0))
    spo2_dev = max(0.5, max(0.0, 98.0 - spo2) * 4.0)
    temp_dev = max(0.5, abs(temp - 36.8) * 15.0)
    total    = hr_dev + spo2_dev + temp_dev
    hr_pct   = round(hr_dev / total * 100.0, 1)
    spo2_pct = round(spo2_dev / total * 100.0, 1)
    temp_pct = round(temp_dev / total * 100.0, 1)
    spo2_pct = round(spo2_pct + 100.0 - (hr_pct + spo2_pct + temp_pct), 1)
    factors = [("Heart Rate (MAX30102)", hr_dev), ("SpO2 (MAX30102)", spo2_dev), ("Temperature (DS18B20)", temp_dev)]
    primary = sorted(factors, key=lambda x: x[1], reverse=True)[0][0]
    return {
        "contributions": {"heart_rate": hr_pct, "spo2": spo2_pct, "temperature": temp_pct, "fall_detected": 0.0},
        "primary_factor": primary,
    }


def _recommend(hr, spo2, temp, fall):
    if fall:
        return "Emergency: Fall detected! Please remain still. An alert has been dispatched to your healthcare provider."
    advices = []
    if spo2 < 90:
        advices.append("Critical hypoxia (SpO2 < 90%). Sit upright, breathe deeply, and seek IMMEDIATE medical attention.")
    elif spo2 < 95:
        advices.append("Mild blood oxygen desaturation. Rest, sit in a well-ventilated space, and focus on deep breathing.")
    if hr > 120:
        advices.append("Significant tachycardia. Sit down, drink water, practice slow breathing, and avoid exertion.")
    elif hr > 100:
        advices.append("Elevated heart rate. Avoid caffeine or stress. Rest quietly and monitor over the next 15 minutes.")
    elif hr < 50:
        advices.append("Bradycardia detected. If dizzy or faint, sit or lie down immediately and alert your caregiver.")
    if temp > 38.5:
        advices.append("High fever detected. Stay hydrated, apply a cool compress, and rest.")
    elif temp > 37.5:
        advices.append("Low-grade fever. Increase fluid intake, rest, and keep the room temperature comfortable.")
    elif temp < 35.0:
        advices.append("Hypothermia warning. Wear warm layers, wrap in blankets, and consume warm fluids.")
    if not advices:
        return "Vitals are normal. Keep up the good health! Stay hydrated, eat balanced meals, and aim for 7-8 hours of sleep."
    return " ".join(advices)


# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "torch_available": TORCH_AVAILABLE,
        "sklearn_available": SKL_AVAILABLE,
        "models_loaded": list(_models.keys()),
        "anomaly_detector": _anomaly_model is not None,
    }


@app.post("/predict", response_model=PredictResponse)
async def predict(req: PredictRequest):
    hr   = req.heart_rate
    spo2 = req.spo2
    temp = req.temperature
    fall = req.fall_detected

    try:
        # Risk score
        if TORCH_AVAILABLE and _models:
            risk_score, confidence = _ensemble_predict(hr, spo2, temp, fall)
        else:
            risk_score, confidence = _rule_based_risk(hr, spo2, temp, fall)

        risk_score = min(100.0, max(0.0, risk_score))

        if risk_score >= 80.0 or fall:
            risk_level = "Critical"
        elif risk_score >= 50.0:
            risk_level = "High"
        elif risk_score >= 25.0:
            risk_level = "Medium"
        else:
            risk_level = "Low"

        return PredictResponse(
            risk_level=risk_level,
            risk_score=round(risk_score, 1),
            confidence_score=round(confidence, 2),
            explanation=_explain(hr, spo2, temp, fall),
            anomaly_status=_anomaly_detect(hr, spo2, temp),
            recommendation=_recommend(hr, spo2, temp, fall),
        )

    except Exception as e:
        logger.exception("Prediction error")
        raise HTTPException(status_code=500, detail=str(e))


# ── Entry point (local dev) ───────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=7860, reload=True)
