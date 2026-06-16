import math
import logging
from collections import deque

logger = logging.getLogger(__name__)


class StabilityFilter:
    """
    Per-patient real-time stability and noise filtering system.

    Processes incoming MPU6050 accelerometer data to detect movement,
    and filters MAX30100 / DS18B20 vital sign readings accordingly.

    - Lightweight moving average + low-pass IIR filter on accelerometer
    - Adaptive threshold classification (Stable / Moving)
    - Spike removal and rolling averages for HR & SpO2
    - Median filtering for temperature
    """

    ACCEL_WINDOW_SIZE = 10
    LPF_ALPHA = 0.35
    VITAL_WINDOW_SIZE = 10
    SUSTAINED_MOVEMENT_SAMPLES = 3
    ACCEL_ZERO_TOLERANCE = 0.01
    RECOVERY_DECAY = 1
    MIN_THRESHOLD = 0.005
    MAX_THRESHOLD = 0.3
    NOISE_FLOOR_MULTIPLIER = 5.0

    STABLE = "Stable"
    MOVING = "Moving"

    def __init__(self, patient_id=None):
        self.patient_id = patient_id

        self.accel_history = deque(maxlen=self.ACCEL_WINDOW_SIZE)

        self.ax_lpf = 0.0
        self.ay_lpf = 0.0
        self.az_lpf = 0.0
        self._lpf_initialized = False

        self.movement_history = deque(maxlen=20)
        self.adaptive_threshold = 0.02
        self.noise_floor = 0.005

        self.current_state = self.STABLE
        self._sustained_count = 0
        self._last_movement_mag = 0.0

        self.hr_buffer = deque(maxlen=self.VITAL_WINDOW_SIZE)
        self.spo2_buffer = deque(maxlen=self.VITAL_WINDOW_SIZE)
        self.temp_buffer = deque(maxlen=self.VITAL_WINDOW_SIZE)

        self.filtered_hr = None
        self.filtered_spo2 = None
        self.filtered_temp = None

        self._has_accel_data = False

    def _lpf(self, raw, prev):
        return self.LPF_ALPHA * raw + (1.0 - self.LPF_ALPHA) * prev

    def _movement_variance(self):
        if len(self.accel_history) < 3:
            return 0.0
        n = len(self.accel_history)
        mx = sum(v[0] for v in self.accel_history) / n
        my = sum(v[1] for v in self.accel_history) / n
        mz = sum(v[2] for v in self.accel_history) / n
        var = sum(
            (v[0] - mx) ** 2 + (v[1] - my) ** 2 + (v[2] - mz) ** 2
            for v in self.accel_history
        ) / n
        return math.sqrt(var)

    def _remove_outliers_mad(self, values, n_mad=3.0):
        if len(values) < 4:
            return list(values)
        arr = sorted(values)
        n = len(arr)
        median = arr[n // 2] if n % 2 else (arr[n // 2 - 1] + arr[n // 2]) / 2.0
        mad = sorted(abs(v - median) for v in arr)[n // 2] if n else 0.0
        if mad < 0.001:
            return list(values)
        threshold = n_mad * mad / 0.6745
        return [v for v in values if abs(v - median) <= threshold]

    def _rolling_weighted_avg(self, values, recent_weight=2.0):
        if not values:
            return None
        n = len(values)
        if n == 1:
            return values[0]
        weights = [1.0 + (i / (n - 1)) * (recent_weight - 1.0) for i in range(n)]
        s = sum(v * w for v, w in zip(values, weights))
        return s / sum(weights)

    def process_reading(self, heart_rate, spo2, temperature, fall_detected,
                        accel_x=0.0, accel_y=0.0, accel_z=0.0):
        self._has_accel_data = (
            abs(accel_x) > self.ACCEL_ZERO_TOLERANCE
            or abs(accel_y) > self.ACCEL_ZERO_TOLERANCE
            or abs(accel_z) > self.ACCEL_ZERO_TOLERANCE
        )

        if self._has_accel_data:
            if not self._lpf_initialized:
                self.ax_lpf = accel_x
                self.ay_lpf = accel_y
                self.az_lpf = accel_z
                self._lpf_initialized = True
            else:
                self.ax_lpf = self._lpf(accel_x, self.ax_lpf)
                self.ay_lpf = self._lpf(accel_y, self.ay_lpf)
                self.az_lpf = self._lpf(accel_z, self.az_lpf)

            self.accel_history.append((self.ax_lpf, self.ay_lpf, self.az_lpf))
            movement_mag = self._movement_variance()
        else:
            movement_mag = 0.0

        self._last_movement_mag = movement_mag

        self.movement_history.append(movement_mag)
        if len(self.movement_history) >= 8:
            sorted_mag = sorted(self.movement_history)
            idx = max(0, int(len(sorted_mag) * 0.25))
            self.noise_floor = sorted_mag[idx]
            self.adaptive_threshold = max(
                self.MIN_THRESHOLD,
                min(self.MAX_THRESHOLD, self.noise_floor * self.NOISE_FLOOR_MULTIPLIER)
            )

        if not self._has_accel_data or movement_mag < self.adaptive_threshold:
            self._sustained_count = max(0, self._sustained_count - self.RECOVERY_DECAY)
            if self._sustained_count <= 0 and self.current_state != self.STABLE:
                self.current_state = self.STABLE
        else:
            self._sustained_count += 1
            if self._sustained_count >= self.SUSTAINED_MOVEMENT_SAMPLES:
                if self.current_state != self.MOVING:
                    logger.info(
                        f"[{self.patient_id}] Stable -> Moving "
                        f"(mag={movement_mag:.4f}, thresh={self.adaptive_threshold:.4f})"
                    )
                self.current_state = self.MOVING

        self.hr_buffer.append(heart_rate)
        self.spo2_buffer.append(spo2)
        self.temp_buffer.append(temperature)

        if self.current_state == self.STABLE:
            valid_hr = self._remove_outliers_mad(list(self.hr_buffer))
            valid_spo2 = self._remove_outliers_mad(list(self.spo2_buffer))
            valid_temp = self._remove_outliers_mad(list(self.temp_buffer))

            if len(valid_temp) >= 3:
                valid_temp = sorted(valid_temp)
                mid = len(valid_temp) // 2
                valid_temp = (
                    [valid_temp[mid]]
                    if len(valid_temp) % 2
                    else [valid_temp[mid - 1], valid_temp[mid]]
                )

            self.filtered_hr = self._rolling_weighted_avg(valid_hr) if valid_hr else heart_rate
            self.filtered_spo2 = self._rolling_weighted_avg(valid_spo2) if valid_spo2 else spo2
            self.filtered_temp = self._rolling_weighted_avg(valid_temp) if valid_temp else temperature

        elif self._sustained_count < self.SUSTAINED_MOVEMENT_SAMPLES * 2:
            valid_hr = self._remove_outliers_mad(list(self.hr_buffer), n_mad=2.0)
            valid_spo2 = self._remove_outliers_mad(list(self.spo2_buffer), n_mad=2.0)
            valid_temp = self._remove_outliers_mad(list(self.temp_buffer), n_mad=2.0)

            raw_hr = self._rolling_weighted_avg(valid_hr) if valid_hr else heart_rate
            raw_spo2 = self._rolling_weighted_avg(valid_spo2) if valid_spo2 else spo2
            raw_temp = self._rolling_weighted_avg(valid_temp) if valid_temp else temperature

            if self.filtered_hr is not None:
                self.filtered_hr = 0.7 * self.filtered_hr + 0.3 * raw_hr
            else:
                self.filtered_hr = raw_hr
            if self.filtered_spo2 is not None:
                self.filtered_spo2 = 0.7 * self.filtered_spo2 + 0.3 * raw_spo2
            else:
                self.filtered_spo2 = raw_spo2
            if self.filtered_temp is not None:
                self.filtered_temp = 0.7 * self.filtered_temp + 0.3 * raw_temp
            else:
                self.filtered_temp = raw_temp

        self.filtered_hr = max(30.0, min(250.0, self.filtered_hr if self.filtered_hr is not None else heart_rate))
        self.filtered_spo2 = max(50.0, min(100.0, self.filtered_spo2 if self.filtered_spo2 is not None else spo2))
        self.filtered_temp = max(30.0, min(45.0, self.filtered_temp if self.filtered_temp is not None else temperature))

        return {
            "heart_rate": round(self.filtered_hr, 1),
            "spo2": round(self.filtered_spo2, 1),
            "temperature": round(self.filtered_temp, 1),
            "stability_status": self.current_state,
            "movement_magnitude": round(self._last_movement_mag, 4),
            "adaptive_threshold": round(self.adaptive_threshold, 4),
            "is_moving": self.current_state == self.MOVING,
        }


    def get_state(self):
        return {
            "stability_status": self.current_state,
            "movement_magnitude": round(self._last_movement_mag, 4),
            "adaptive_threshold": round(self.adaptive_threshold, 4),
            "filtered_hr": round(self.filtered_hr, 1) if self.filtered_hr is not None else None,
            "filtered_spo2": round(self.filtered_spo2, 1) if self.filtered_spo2 is not None else None,
            "filtered_temp": round(self.filtered_temp, 1) if self.filtered_temp is not None else None,
        }


_filters = {}


def get_filter(patient_id=None):
    key = patient_id or "_default"
    if key not in _filters:
        _filters[key] = StabilityFilter(patient_id=patient_id)
    return _filters[key]


def process_sensor_data(heart_rate, spo2, temperature, fall_detected,
                        accel_x=0.0, accel_y=0.0, accel_z=0.0,
                        patient_id=None):
    sf = get_filter(patient_id)
    return sf.process_reading(
        heart_rate=heart_rate, spo2=spo2, temperature=temperature,
        fall_detected=fall_detected,
        accel_x=accel_x, accel_y=accel_y, accel_z=accel_z,
    )
