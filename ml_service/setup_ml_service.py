"""
Run this once to copy model files into ml_service/models/
  python setup_ml_service.py
"""
import os
import shutil

BASE = os.path.dirname(os.path.abspath(__file__))
DST  = os.path.join(BASE, "models")
os.makedirs(DST, exist_ok=True)

SOURCES = [
    (os.path.join(BASE, "..", "machinL", "ai_health_elite_output", "models", "model_bt.pth"),    "model_bt.pth"),
    (os.path.join(BASE, "..", "machinL", "ai_health_elite_output", "models", "model_hr.pth"),    "model_hr.pth"),
    (os.path.join(BASE, "..", "machinL", "ai_health_elite_output", "models", "model_fall.pth"),  "model_fall.pth"),
    (os.path.join(BASE, "..", "machinL", "ai_health_elite_output", "models", "model_sp2.pth"),   "model_sp2.pth"),
    (os.path.join(BASE, "..", "machinL", "ai_health_elite_output", "models", "model_fusion.pth"),"model_fusion.pth"),
    (os.path.join(BASE, "..", "ml",      "models", "isolation_forest.joblib"),                   "isolation_forest.joblib"),
]

for src, name in SOURCES:
    dst = os.path.join(DST, name)
    if os.path.exists(src):
        shutil.copy2(src, dst)
        size = os.path.getsize(dst)
        print(f"  ✓  {name:40s}  ({size:,} bytes)")
    else:
        print(f"  ✗  {name} — source not found: {src}")

print("\nDone! ml_service/models contents:")
for f in os.listdir(DST):
    print(f"  {f}")
