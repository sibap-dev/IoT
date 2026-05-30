import os
import shutil

# Unused legacy files to purge from the directory
FILES_TO_DELETE = [
    "recreate_db.py",
    "server_log.txt",
    "test_endpoints.py",
    "scaler.pkl",
    "anomaly_model.pkl",
    "iot_data.csv",
    "modules/data_module.py",
    "modules/ml_module.py",
    "modules/utils_module.py",
    "modules/visualization_module.py"
]

base_dir = "d:\\intern IIT\\IoT"

print("=======================================================")
print("🧹 IoT Healthcare Platform Project Cleanup")
print("=======================================================")

for file in FILES_TO_DELETE:
    full_path = os.path.join(base_dir, file)
    if os.path.exists(full_path):
        try:
            os.remove(full_path)
            print(f"✓ Removed legacy junk file: {file}")
        except Exception as e:
            print(f"✗ Failed to remove {file}: {e}")
    else:
        print(f"· Already removed: {file}")

# Clean up __pycache__ folders
for root, dirs, files in os.walk(base_dir):
    for d in dirs:
        if d == "__pycache__":
            pycache_path = os.path.join(root, d)
            try:
                shutil.rmtree(pycache_path)
                print(f"✓ Purged temporary pycache: {os.path.relpath(pycache_path, base_dir)}")
            except Exception:
                pass

print("-------------------------------------------------------")
print("✨ Project directory is completely clean and pristine!")
print("=======================================================")
