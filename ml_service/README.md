---
title: Medicare IoT ML Inference Service
emoji: 🏥
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
license: mit
short_description: PyTorch health risk prediction microservice for IoT wearable
---

# Medicare IoT — ML Inference Microservice

FastAPI-based ML inference service for the **Medicare IoT Healthcare Platform**.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/health` | Health check, lists loaded models |
| `POST` | `/predict` | Run inference on sensor readings |

## Example Request

```json
POST /predict
{
  "heart_rate": 88,
  "spo2": 97.5,
  "temperature": 36.9,
  "fall_detected": false
}
```

## Example Response

```json
{
  "risk_level": "Low",
  "risk_score": 18.4,
  "confidence_score": 0.92,
  "explanation": {
    "contributions": {"heart_rate": 28.0, "spo2": 50.0, "temperature": 22.0, "fall_detected": 0.0},
    "primary_factor": "SpO2 (MAX30102)"
  },
  "anomaly_status": {"is_anomaly": false, "anomaly_score": 12.0, "decision_score": 0.18},
  "recommendation": "Vitals are normal. Keep up the good health!"
}
```
