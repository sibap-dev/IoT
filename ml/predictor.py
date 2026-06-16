import os
import sys
import json
import logging
import requests
from pathlib import Path
from ml.anomaly_detector import AnomalyDetector
from ml.explainability import ExplainabilityEngine
from ml.recommendation_engine import RecommendationEngine

logger = logging.getLogger(__name__)

# ── Remote ML Service (HuggingFace Spaces) ────────────────────────────────────
# Set ML_SERVICE_URL in your .env / Vercel environment variables
# e.g. ML_SERVICE_URL=https://your-username-medicare-ml.hf.space
_ML_SERVICE_URL = os.environ.get("ML_SERVICE_URL", "").rstrip("/")

_MACHINL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "machinL")
if _MACHINL_DIR not in sys.path:
    sys.path.insert(0, _MACHINL_DIR)

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    import numpy as np
    MACHINL_AVAILABLE = True
except ImportError:
    MACHINL_AVAILABLE = False
    logger.warning("machinL (PyTorch) not available. Will use remote ML service or rule engine.")


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


MODEL_DIR = Path(os.path.dirname(os.path.dirname(__file__))) / "machinL" / "ai_health_elite_output" / "models"


MODEL_CONFIGS = {
    "body_temperature": {"file": "model_bt.pth",  "input_dim": 15,  "h1": 128, "h2": 128, "h3": 64,  "out": 2},
    "heart_rate":       {"file": "model_hr.pth",  "input_dim": 29,  "h1": 64,  "h2": 64,  "h3": 32,  "out": 3},
    "fall_detection":   {"file": "model_fall.pth", "input_dim": 561, "h1": 128, "h2": 128, "h3": 64,  "out": 6},
    "spo2":             {"file": "model_sp2.pth",  "input_dim": 15,  "h1": 128, "h2": 128, "h3": 64,  "out": 2},
    "fusion":           {"file": "model_fusion.pth","input_dim": 16,  "h1": 32,  "h2": 32,  "h3": 16,  "out": 2},
}


def _load_model(cfg):
    path = MODEL_DIR / cfg["file"]
    if not path.exists():
        logger.warning(f"Model file not found: {path}")
        return None
    try:
        state = torch.load(path, map_location="cpu", weights_only=False)
        model = SimpleNet(input_dim=cfg["input_dim"], h1=cfg["h1"], h2=cfg["h2"], h3=cfg["h3"], num_classes=cfg["out"])
        model.load_state_dict(state)
        model.eval()
        return model
    except Exception as e:
        logger.error(f"Failed to load {cfg['file']}: {e}")
        return None


def _make_bt_feat(hr, spo2, temp, fall):
    x = torch.zeros(15)
    x[0] = temp; x[1] = spo2; x[2] = hr
    x[3] = float(fall)
    x[4] = temp - 36.8
    x[5] = (temp - 36.8) ** 2
    x[6] = hr / 100.0
    x[7] = spo2 / 100.0
    x[8] = temp * hr / 3700.0
    x[9] = temp * spo2 / 3700.0
    x[10] = hr * spo2 / 10000.0
    x[11] = abs(temp - 36.8) * 5
    x[12] = (hr - 72) / 68.0
    x[13] = (98.0 - spo2) / 15.0
    x[14] = 1.0 if fall else 0.0
    return x.unsqueeze(0)


def _make_hr_feat(hr, spo2, temp, fall):
    x = torch.zeros(29)
    x[0] = hr; x[1] = spo2; x[2] = temp
    x[3] = float(fall)
    x[4] = hr / 100.0
    x[5] = (hr - 72) / 68.0
    x[6] = (hr - 72) ** 2 / 4624.0
    x[7] = hr * spo2 / 10000.0
    x[8] = hr * temp / 3700.0
    x[9] = abs(hr - 72) / 72.0
    x[10:18] = torch.tensor([hr + i * 5 for i in range(8)]) / 200.0
    x[18] = spo2 / 100.0
    x[19] = temp / 40.0
    x[20] = (spo2 - 95) / 5.0
    x[21] = (temp - 36.5) * 2
    x[22] = 1.0 if hr > 100 or hr < 60 else 0.0
    x[23] = (hr - 72) * (spo2 - 98) / 1000.0
    x[24] = torch.sin(torch.tensor(hr / 20.0))
    x[25] = torch.cos(torch.tensor(hr / 20.0))
    x[26] = hr / (spo2 + 0.1)
    x[27] = temp * hr / (spo2 + 0.1)
    x[28] = float(fall) * hr / 100.0
    return x.unsqueeze(0)


def _make_sp2_feat(hr, spo2, temp, fall):
    x = torch.zeros(15)
    x[0] = spo2; x[1] = temp; x[2] = hr
    x[3] = float(fall)
    x[4] = (100 - spo2) / 15.0
    x[5] = (spo2 - 95) ** 2 / 25.0
    x[6] = spo2 / 100.0
    x[7] = hr / 200.0
    x[8] = temp / 40.0
    x[9] = spo2 * hr / 10000.0
    x[10] = spo2 * temp / 3800.0
    x[11] = (spo2 - 97) * 10
    x[12] = 1.0 if spo2 < 95 else 0.0
    x[13] = 1.0 if hr > 100 or hr < 60 else 0.0
    x[14] = float(fall)
    return x.unsqueeze(0)


def _make_fall_feat(hr, spo2, temp, fall):
    x = torch.zeros(561)
    x[0] = float(fall)
    x[1] = hr / 200.0
    x[2] = spo2 / 100.0
    x[3] = temp / 40.0
    x[4] = 1.0 if fall else 0.0
    x[5] = abs(hr - 72) / 72.0
    x[6] = (100 - spo2) / 15.0
    x[7] = abs(temp - 36.8) / 5.0
    x[8] = hr * float(fall) / 100.0
    x[9] = (hr - 72) * (60 - hr + spo2) / 5000.0
    x[10] = 1.0 if fall else (0.3 if hr > 100 else 0.0)
    x[11] = float(fall) * 10.0
    x[12] = hr / (spo2 + 0.1) if fall else 0.0
    x[13:561] = torch.randn(561 - 13) * 0.01
    return x.unsqueeze(0)


def _make_fusion_feat(hr, spo2, temp, fall):
    x = torch.zeros(16)
    x[0] = hr / 200.0; x[1] = spo2 / 100.0
    x[2] = temp / 40.0; x[3] = 1.0 if fall else 0.0
    x[4] = abs(hr - 72) / 72.0
    x[5] = (100 - spo2) / 15.0
    x[6] = abs(temp - 36.8) / 5.0
    x[7] = (hr - 72) * (100 - spo2) / 1000.0
    x[8] = temp * hr / 3700.0
    x[9] = spo2 * temp / 3800.0
    x[10] = (hr - 72) ** 2 / 5184.0
    x[11] = (100 - spo2) ** 2 / 225.0
    x[12] = abs(temp - 36.8) ** 2 / 25.0
    x[13] = hr / (spo2 + 0.1) / 2.0
    x[14] = 1.0 if hr > 100 or hr < 60 or spo2 < 95 else 0.0
    x[15] = float(fall) * 5.0
    return x.unsqueeze(0)


class HealthPredictor:
    def __init__(self):
        self.anomaly_detector = AnomalyDetector()
        self.models = {}
        if MACHINL_AVAILABLE:
            self._load_models()

    def _load_models(self):
        for name, cfg in MODEL_CONFIGS.items():
            model = _load_model(cfg)
            if model is not None:
                self.models[name] = model
        logger.info(f"Loaded {len(self.models)}/{len(MODEL_CONFIGS)} models")
        if not self.models:
            logger.warning("No models loaded, rule-based fallback will be used")

    def predict(self, heart_rate: float, spo2: float, temperature: float, fall_detected: bool) -> dict:
        # ── 1. Try remote HuggingFace ML microservice ──────────────────────────
        if _ML_SERVICE_URL:
            try:
                resp = requests.post(
                    f"{_ML_SERVICE_URL}/predict",
                    json={
                        "heart_rate":    heart_rate,
                        "spo2":          spo2,
                        "temperature":   temperature,
                        "fall_detected": fall_detected,
                    },
                    timeout=8,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    logger.debug(f"Remote ML service responded: risk={data.get('risk_score')}")
                    return data
                else:
                    logger.warning(f"Remote ML service returned {resp.status_code}. Falling back locally.")
            except requests.exceptions.Timeout:
                logger.warning("Remote ML service timed out. Falling back locally.")
            except requests.exceptions.ConnectionError:
                logger.warning("Remote ML service unreachable. Falling back locally.")
            except Exception as e:
                logger.warning(f"Remote ML service error: {e}. Falling back locally.")

        # ── 2. Local computation ───────────────────────────────────────────────
        anomaly_res = self.anomaly_detector.predict(heart_rate, spo2, temperature)
        shap_res = ExplainabilityEngine.explain(heart_rate, spo2, temperature, fall_detected)

        risk_score = 0.0
        confidence = 1.0

        if MACHINL_AVAILABLE and self.models:
            try:
                risk_score, confidence = self._ensemble_predict(heart_rate, spo2, temperature, fall_detected)
            except Exception as e:
                logger.error(f"Ensemble failed: {e}. Falling back to clinical rules.")
                risk_score, confidence = self._rule_based_risk(heart_rate, spo2, temperature, fall_detected)
        else:
            risk_score, confidence = self._rule_based_risk(heart_rate, spo2, temperature, fall_detected)

        risk_score = min(100.0, max(0.0, risk_score))

        if risk_score >= 80.0 or fall_detected:
            risk_level = "Critical"
        elif risk_score >= 50.0:
            risk_level = "High"
        elif risk_score >= 25.0:
            risk_level = "Medium"
        else:
            risk_level = "Low"

        recommendation = RecommendationEngine.generate(heart_rate, spo2, temperature, fall_detected)

        return {
            "risk_level":       risk_level,
            "risk_score":       round(risk_score, 1),
            "confidence_score": round(confidence, 2),
            "explanation":      shap_res,
            "anomaly_status":   anomaly_res,
            "recommendation":   recommendation,
        }

    def _ensemble_predict(self, hr, spo2, temp, fall):
        scores = []

        FEAT_MAKERS = {
            "body_temperature": (_make_bt_feat, 80.0),
            "heart_rate":       (_make_hr_feat, 80.0),
            "spo2":             (_make_sp2_feat, 80.0),
            "fusion":           (_make_fusion_feat, None),
        }

        for name, (fn, scale) in FEAT_MAKERS.items():
            model = self.models.get(name)
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

        fall_model = self.models.get("fall_detection")
        if fall_model is not None:
            feat = _make_fall_feat(hr, spo2, temp, fall)
            with torch.no_grad():
                out = fall_model(feat)
            probs = F.softmax(out, dim=1)[0]
            if len(probs) >= 6:
                fall_class_prob = float(probs[1])
                scores.append(90.0 if fall_class_prob > 0.3 else 10.0)
            elif len(probs) >= 2:
                scores.append(90.0 if float(probs[1]) > 0.5 else 10.0)
            else:
                scores.append(50.0)

        if not scores:
            return self._rule_based_risk(hr, spo2, temp, fall)

        ml_score = sum(scores) / len(scores)
        rule_score, _ = self._rule_based_risk(hr, spo2, temp, fall)
        risk_score = 0.6 * ml_score + 0.4 * rule_score
        confidence = 0.80 + 0.15 * (len(scores) / 5.0)
        return risk_score, confidence

    def _rule_based_risk(self, hr, spo2, temp, fall):
        base = 5.0
        hr_dev = abs(hr - 72.0)
        hr_score = min(100.0, hr_dev / 68.0 * 100.0)
        spo2_dev = max(0.0, 98.0 - spo2)
        spo2_score = min(100.0, spo2_dev / 15.0 * 100.0)
        temp_dev = abs(temp - 36.8)
        temp_score = min(100.0, temp_dev / 5.0 * 100.0)
        fall_score = 100.0 if fall else 0.0
        risk = base + hr_score * 0.30 + spo2_score * 0.35 + temp_score * 0.25 + fall_score * 0.10
        risk = min(100.0, risk)
        confidence = max(0.70, 0.95 - hr_dev / 200.0 - spo2_dev / 200.0 - temp_dev / 20.0)
        return risk, confidence

    def train_model(self, X, y):
        if not MACHINL_AVAILABLE:
            raise RuntimeError("Cannot train: machinL dependencies (torch) not installed.")
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.preprocessing import StandardScaler
        import joblib
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        model = RandomForestClassifier(n_estimators=100, max_depth=8, random_state=42)
        model.fit(X_scaled, y)
        models_dir = os.path.join(os.path.dirname(__file__), "models")
        os.makedirs(models_dir, exist_ok=True)
        joblib.dump(model, os.path.join(models_dir, "rf_health_model.joblib"))
        joblib.dump(scaler, os.path.join(models_dir, "scaler.joblib"))
        logger.info("Fallback sklearn model trained and saved")
