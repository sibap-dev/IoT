"""
IoT Healthcare Platform — Sensor Simulator

Generates realistic healthcare sensor data and sends it to:

    POST http://localhost:5000/api/sensor-data

Designed to mimic an ESP32 with:
  - MAX30102  → Heart Rate & SpO2
  - MPU6050   → Motion & Fall Detection
  - DS18B20   → Body Temperature

Usage:
    python sensor_simulator.py                      # default: 5 sec interval
    python sensor_simulator.py --interval 2          # send every 2 seconds
    python sensor_simulator.py --count 20            # send 20 readings then stop
    python sensor_simulator.py --url http://...      # custom API URL
    python sensor_simulator.py --patient-id P001     # optional patient ID
    python sensor_simulator.py --simulate-fall       # include fall events
"""

import argparse
import json
import random
import sys
import time
from datetime import datetime

try:
    import requests
except ImportError:
    print("Missing 'requests' library. Install with: pip install requests")
    sys.exit(1)


class VitalSimulator:
    """Generates realistic vital sign readings."""

    def __init__(self, simulate_fall=False):
        self.heart_rate = 72.0
        self.spo2 = 97.0
        self.temperature = 36.6
        self.trend_bpm = 0
        self.trend_spo2 = 0
        self.trend_temp = 0
        self.simulate_fall = simulate_fall

    def generate(self):
        self.trend_bpm += random.uniform(-2, 2)
        self.trend_bpm = max(-5, min(5, self.trend_bpm))
        self.heart_rate += self.trend_bpm * 0.1 + random.uniform(-1, 1)
        self.heart_rate = max(55, min(120, self.heart_rate))

        self.trend_spo2 += random.uniform(-0.3, 0.3)
        self.trend_spo2 = max(-1, min(1, self.trend_spo2))
        self.spo2 += self.trend_spo2 * 0.05 + random.uniform(-0.2, 0.2)
        self.spo2 = max(92, min(100, self.spo2))

        self.trend_temp += random.uniform(-0.1, 0.1)
        self.trend_temp = max(-0.5, min(0.5, self.trend_temp))
        self.temperature += self.trend_temp * 0.05 + random.uniform(-0.1, 0.1)
        self.temperature = max(35.5, min(38.5, self.temperature))

        fall_detected = False
        if self.simulate_fall and random.random() < 0.02:
            fall_detected = True
            self.heart_rate = random.uniform(90, 140)
            self.spo2 = max(90, self.spo2 - random.uniform(2, 5))

        return {
            "heart_rate": round(self.heart_rate, 1),
            "spo2": round(self.spo2, 1),
            "temperature": round(self.temperature, 1),
            "fall_detected": fall_detected,
        }

    def generate_anomaly(self):
        anomaly_type = random.choice(["tachycardia", "hypoxia", "fever", "bradycardia"])
        if anomaly_type == "tachycardia":
            hr = random.uniform(110, 150)
            return {"heart_rate": round(hr, 1), "spo2": round(random.uniform(94, 98), 1),
                    "temperature": round(random.uniform(36.5, 37.5), 1), "fall_detected": False}
        elif anomaly_type == "hypoxia":
            return {"heart_rate": round(random.uniform(80, 110), 1), "spo2": round(random.uniform(85, 92), 1),
                    "temperature": round(random.uniform(36.0, 37.0), 1), "fall_detected": False}
        elif anomaly_type == "fever":
            return {"heart_rate": round(random.uniform(95, 130), 1), "spo2": round(random.uniform(94, 98), 1),
                    "temperature": round(random.uniform(38.0, 40.0), 1), "fall_detected": False}
        else:
            hr = random.uniform(40, 55)
            return {"heart_rate": round(hr, 1), "spo2": round(random.uniform(94, 98), 1),
                    "temperature": round(random.uniform(35.5, 36.5), 1), "fall_detected": False}


def main():
    parser = argparse.ArgumentParser(description="IoT Healthcare Sensor Simulator")
    parser.add_argument("--interval", type=float, default=5.0,
                        help="Seconds between readings (default: 5)")
    parser.add_argument("--count", type=int, default=0,
                        help="Number of readings to send (0 = infinite)")
    parser.add_argument("--url", type=str,
                        default="http://localhost:5001/api/sensor-data",
                        help="API endpoint URL")
    parser.add_argument("--patient-id", type=str, default=None,
                        help="Optional patient/device identifier")
    parser.add_argument("--simulate-fall", action="store_true",
                        help="Randomly simulate fall events")
    parser.add_argument("--anomaly-interval", type=int, default=10,
                        help="Send an anomaly every N readings (0 = no anomalies)")

    args = parser.parse_args()

    simulator = VitalSimulator(simulate_fall=args.simulate_fall)
    api_url = args.url.rstrip("/")
    count = 0
    anomaly_counter = 0

    print("=" * 55)
    print("  IoT Healthcare Sensor Simulator")
    print("=" * 55)
    print(f"  API URL      : {api_url}")
    print(f"  Interval     : {args.interval}s")
    print(f"  Patient ID   : {args.patient_id or 'Not set'}")
    print(f"  Simulate Fall: {'Yes' if args.simulate_fall else 'No'}")
    print(f"  Anomalies    : {'Every ' + str(args.anomaly_interval) + ' readings' if args.anomaly_interval else 'Disabled'}")
    print(f"  Max Readings : {'Infinite' if args.count == 0 else args.count}")
    print("-" * 55)

    while True:
        try:
            if args.anomaly_interval > 0 and anomaly_counter >= args.anomaly_interval:
                payload = simulator.generate_anomaly()
                anomaly_counter = 0
                label = "⚠️  ANOMALY"
            else:
                payload = simulator.generate()
                anomaly_counter += 1
                label = "    NORMAL"

            if args.patient_id:
                payload["patient_id"] = args.patient_id

            resp = requests.post(api_url, json=payload, timeout=10)
            count += 1

            ts = datetime.now().strftime("%H:%M:%S")
            status = "✓" if resp.status_code == 201 else f"✗ ({resp.status_code})"

            print(
                f"  [{ts}] {label}  "
                f"HR={payload['heart_rate']:>5.1f}  "
                f"SpO2={payload['spo2']:>4.1f}%  "
                f"Temp={payload['temperature']:>4.1f}°C  "
                f"Fall={'YES' if payload['fall_detected'] else 'no '}  "
                f"→ {status}"
            )

            if args.count > 0 and count >= args.count:
                print("-" * 55)
                print(f"  Sent {count} readings. Done.")
                break

            time.sleep(args.interval)

        except KeyboardInterrupt:
            print("\n" + "-" * 55)
            print(f"  Simulator stopped. {count} readings sent.")
            break
        except requests.exceptions.ConnectionError:
            print(f"  [!] Cannot connect to {api_url}. Is the server running?")
            print(f"  [!] Retrying in {args.interval}s...")
            time.sleep(args.interval)
        except Exception as e:
            print(f"  [!] Error: {e}")
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
