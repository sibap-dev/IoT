"""
Simulation Module - Sensor Data Simulation

This module handles realistic sensor data simulation including:
- Physiologically realistic vital sign generation
- Activity-based sensor patterns
- Anomaly injection for testing
- Time-series data generation
- Environmental sensor simulation
"""

import numpy as np
import pandas as pd
from typing import Optional, List, Dict, Tuple
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Health Condition Profiles for realistic simulation
HEALTH_CONDITION_PROFILES = {
    "NORMAL": {
        "BPM": {"min": 60, "max": 100, "mean": 75, "std": 8},
        "SPO2": {"min": 95, "max": 100, "mean": 97.5, "std": 1.2},
        "Body_Temp": {"min": 36.5, "max": 37.5, "mean": 37.0, "std": 0.3},
        "description": "Normal healthy condition"
    },
    "TACHYCARDIA": {
        "BPM": {"min": 100, "max": 150, "mean": 120, "std": 12},
        "SPO2": {"min": 92, "max": 98, "mean": 95, "std": 1.5},
        "Body_Temp": {"min": 36.5, "max": 38, "mean": 37.2, "std": 0.4},
        "description": "Elevated heart rate condition"
    },
    "HYPOXIA": {
        "BPM": {"min": 80, "max": 120, "mean": 95, "std": 10},
        "SPO2": {"min": 85, "max": 92, "mean": 88, "std": 2},
        "Body_Temp": {"min": 36, "max": 37, "mean": 36.5, "std": 0.3},
        "description": "Low oxygen saturation condition"
    },
    "FEVER": {
        "BPM": {"min": 90, "max": 130, "mean": 105, "std": 10},
        "SPO2": {"min": 93, "max": 98, "mean": 95.5, "std": 1.3},
        "Body_Temp": {"min": 38, "max": 40, "mean": 38.8, "std": 0.5},
        "description": "Elevated body temperature condition"
    },
    "CRITICAL": {
        "BPM": {"min": 40, "max": 180, "mean": 110, "std": 35},
        "SPO2": {"min": 70, "max": 90, "mean": 80, "std": 5},
        "Body_Temp": {"min": 35, "max": 41, "mean": 37.5, "std": 1.5},
        "description": "Critical condition with unstable vitals"
    }
}


class VitalSignSimulator:
    """Simulate realistic vital sign readings."""
    
    # Normal ranges and parameters for vital signs
    VITAL_PARAMS = {
        "BPM": {
            "mean": 75,
            "std": 10,
            "min": 40,
            "max": 200,
            "normal_range": (60, 100)
        },
        "SPO2": {
            "mean": 97,
            "std": 1.5,
            "min": 70,
            "max": 100,
            "normal_range": (95, 100)
        },
        "Body_Temp": {
            "mean": 36.8,
            "std": 0.3,
            "min": 35.0,
            "max": 42.0,
            "normal_range": (36.1, 37.2)
        }
    }
    
    def __init__(self, random_state: Optional[int] = None):
        """
        Initialize VitalSignSimulator.
        
        Args:
            random_state: Random seed for reproducibility
        """
        self.random_state = random_state
        if random_state is not None:
            np.random.seed(random_state)
    
    def generate_normal_reading(self, vital: str) -> float:
        """
        Generate a single normal vital sign reading.
        
        Args:
            vital: Vital sign name (BPM, SPO2, Body_Temp)
            
        Returns:
            Simulated reading value
        """
        params = self.VITAL_PARAMS.get(vital)
        if params is None:
            raise ValueError(f"Unknown vital sign: {vital}")
        
        value = np.random.normal(params["mean"], params["std"])
        value = np.clip(value, params["min"], params["max"])
        
        return round(value, 1)
    
    def generate_abnormal_reading(self, vital: str, severity: str = "moderate") -> float:
        """
        Generate an abnormal vital sign reading.
        
        Args:
            vital: Vital sign name
            severity: Severity level (mild, moderate, severe)
            
        Returns:
            Abnormal reading value
        """
        params = self.VITAL_PARAMS.get(vital)
        if params is None:
            raise ValueError(f"Unknown vital sign: {vital}")
        
        # Determine deviation multiplier based on severity
        severity_multipliers = {
            "mild": 1.5,
            "moderate": 2.5,
            "severe": 4.0
        }
        multiplier = severity_multipliers.get(severity, 2.5)
        
        # Randomly choose high or low abnormality
        if np.random.random() < 0.5:
            # Low abnormality
            value = params["mean"] - (params["std"] * multiplier)
        else:
            # High abnormality
            value = params["mean"] + (params["std"] * multiplier)
        
        value = np.clip(value, params["min"], params["max"])
        
        return round(value, 1)
    
    def generate_time_series(
        self,
        vital: str,
        n_samples: int,
        anomaly_rate: float = 0.1,
        trend: Optional[str] = None
    ) -> np.ndarray:
        """
        Generate time series of vital sign readings.
        
        Args:
            vital: Vital sign name
            n_samples: Number of samples to generate
            anomaly_rate: Proportion of abnormal readings
            trend: Optional trend ('increasing', 'decreasing', None)
            
        Returns:
            Array of simulated readings
        """
        readings = []
        n_anomalies = int(n_samples * anomaly_rate)
        anomaly_indices = np.random.choice(n_samples, n_anomalies, replace=False)
        
        for i in range(n_samples):
            if i in anomaly_indices:
                reading = self.generate_abnormal_reading(vital)
            else:
                reading = self.generate_normal_reading(vital)
            
            # Apply trend if specified
            if trend == "increasing":
                reading += (i / n_samples) * self.VITAL_PARAMS[vital]["std"]
            elif trend == "decreasing":
                reading -= (i / n_samples) * self.VITAL_PARAMS[vital]["std"]
            
            readings.append(reading)
        
        return np.array(readings)

    # Health Condition Profiles for realistic simulation
    HEALTH_CONDITION_PROFILES = {
        "NORMAL": {
            "BPM": {"min": 60, "max": 100, "mean": 75, "std": 8},
            "SPO2": {"min": 95, "max": 100, "mean": 97.5, "std": 1.2},
            "Body_Temp": {"min": 36.5, "max": 37.5, "mean": 37.0, "std": 0.3},
            "description": "Normal healthy condition"
        },
        "TACHYCARDIA": {
            "BPM": {"min": 100, "max": 150, "mean": 120, "std": 12},
            "SPO2": {"min": 92, "max": 98, "mean": 95, "std": 1.5},
            "Body_Temp": {"min": 36.5, "max": 38, "mean": 37.2, "std": 0.4},
            "description": "Elevated heart rate condition"
        },
        "HYPOXIA": {
            "BPM": {"min": 80, "max": 120, "mean": 95, "std": 10},
            "SPO2": {"min": 85, "max": 92, "mean": 88, "std": 2},
            "Body_Temp": {"min": 36, "max": 37, "mean": 36.5, "std": 0.3},
            "description": "Low oxygen saturation condition"
        },
        "FEVER": {
            "BPM": {"min": 90, "max": 130, "mean": 105, "std": 10},
            "SPO2": {"min": 93, "max": 98, "mean": 95.5, "std": 1.3},
            "Body_Temp": {"min": 38, "max": 40, "mean": 38.8, "std": 0.5},
            "description": "Elevated body temperature condition"
        },
        "CRITICAL": {
            "BPM": {"min": 40, "max": 180, "mean": 110, "std": 35},
            "SPO2": {"min": 70, "max": 90, "mean": 80, "std": 5},
            "Body_Temp": {"min": 35, "max": 41, "mean": 37.5, "std": 1.5},
            "description": "Critical condition with unstable vitals"
        }
    }





class EnvironmentalSimulator:
    """Simulate environmental sensor readings."""
    
    ENV_PARAMS = {
        "Ambient_Temp": {
            "mean": 23,
            "std": 2,
            "min": 15,
            "max": 40
        },
        "Humidity": {
            "mean": 50,
            "std": 10,
            "min": 20,
            "max": 100
        }
    }
    
    def __init__(self, random_state: Optional[int] = None):
        """
        Initialize EnvironmentalSimulator.
        
        Args:
            random_state: Random seed for reproducibility
        """
        self.random_state = random_state
        if random_state is not None:
            np.random.seed(random_state)
    
    def generate_reading(self, sensor: str) -> float:
        """
        Generate environmental sensor reading.
        
        Args:
            sensor: Sensor name (Ambient_Temp, Humidity)
            
        Returns:
            Simulated reading value
        """
        params = self.ENV_PARAMS.get(sensor)
        if params is None:
            raise ValueError(f"Unknown sensor: {sensor}")
        
        value = np.random.normal(params["mean"], params["std"])
        value = np.clip(value, params["min"], params["max"])
        
        return round(value, 1)
    
    def generate_time_series(
        self,
        sensor: str,
        n_samples: int,
        daily_pattern: bool = True
    ) -> np.ndarray:
        """
        Generate time series of environmental readings.
        
        Args:
            sensor: Sensor name
            n_samples: Number of samples to generate
            daily_pattern: Whether to include daily variation pattern
            
        Returns:
            Array of simulated readings
        """
        params = self.ENV_PARAMS[sensor]
        base_values = np.random.normal(params["mean"], params["std"], n_samples)
        
        if daily_pattern:
            # Add sinusoidal daily pattern
            time_points = np.linspace(0, 2 * np.pi, n_samples)
            daily_variation = np.sin(time_points) * params["std"]
            base_values += daily_variation
        
        # Clip to valid range
        values = np.clip(base_values, params["min"], params["max"])
        
        return np.round(values, 1)


class ActivitySimulator:
    """Simulate sensor readings based on patient activity."""
    
    ACTIVITY_PROFILES = {
        "resting": {
            "BPM": (60, 75),
            "SPO2": (96, 99),
            "Body_Temp": (36.5, 37.0)
        },
        "light_activity": {
            "BPM": (80, 100),
            "SPO2": (95, 98),
            "Body_Temp": (36.8, 37.3)
        },
        "moderate_activity": {
            "BPM": (100, 130),
            "SPO2": (93, 97),
            "Body_Temp": (37.0, 37.5)
        },
        "intense_activity": {
            "BPM": (130, 170),
            "SPO2": (90, 95),
            "Body_Temp": (37.3, 38.0)
        },
        "sleeping": {
            "BPM": (50, 65),
            "SPO2": (95, 99),
            "Body_Temp": (36.2, 36.8)
        }
    }
    
    def __init__(self, random_state: Optional[int] = None):
        """
        Initialize ActivitySimulator.
        
        Args:
            random_state: Random seed for reproducibility
        """
        self.random_state = random_state
        if random_state is not None:
            np.random.seed(random_state)
    
    def generate_reading_for_activity(
        self,
        activity: str,
        vital: str
    ) -> float:
        """
        Generate vital sign reading for specific activity.
        
        Args:
            activity: Activity type
            vital: Vital sign name
            
        Returns:
            Simulated reading value
        """
        profile = self.ACTIVITY_PROFILES.get(activity)
        if profile is None:
            raise ValueError(f"Unknown activity: {activity}")
        
        if vital not in profile:
            raise ValueError(f"Vital {vital} not in activity profile")
        
        min_val, max_val = profile[vital]
        value = np.random.uniform(min_val, max_val)
        
        return round(value, 1)
    
    def generate_daily_pattern(
        self,
        n_samples: int = 288
    ) -> pd.DataFrame:
        """
        Generate 24-hour daily activity pattern (5-minute intervals).
        
        Args:
            n_samples: Number of samples (default 288 = 24h * 12 samples/hour)
            
        Returns:
            DataFrame with simulated daily readings
        """
        # Define activity schedule (hour ranges)
        schedule = [
            (0, 6, "sleeping"),
            (6, 7, "resting"),
            (7, 8, "light_activity"),
            (8, 12, "resting"),
            (12, 13, "light_activity"),
            (13, 17, "resting"),
            (17, 18, "moderate_activity"),
            (18, 22, "resting"),
            (22, 24, "sleeping")
        ]
        
        data = []
        samples_per_hour = n_samples // 24
        
        for start_hour, end_hour, activity in schedule:
            n_activity_samples = (end_hour - start_hour) * samples_per_hour
            
            for _ in range(n_activity_samples):
                reading = {
                    "Activity": activity,
                    "BPM": self.generate_reading_for_activity(activity, "BPM"),
                    "SPO2": self.generate_reading_for_activity(activity, "SPO2"),
                    "Body_Temp": self.generate_reading_for_activity(activity, "Body_Temp")
                }
                data.append(reading)
        
        return pd.DataFrame(data)


class CompleteSensorSimulator:
    """Complete sensor simulation combining all sensor types."""
    
    def __init__(self, random_state: Optional[int] = None):
        """
        Initialize CompleteSensorSimulator.
        
        Args:
            random_state: Random seed for reproducibility
        """
        self.vital_sim = VitalSignSimulator(random_state)
        self.env_sim = EnvironmentalSimulator(random_state)
        self.activity_sim = ActivitySimulator(random_state)
    
    def generate_complete_dataset(
        self,
        n_samples: int = 100,
        anomaly_rate: float = 0.1,
        include_timestamps: bool = True
    ) -> pd.DataFrame:
        """
        Generate complete dataset with all sensors.
        
        Args:
            n_samples: Number of samples to generate
            anomaly_rate: Proportion of abnormal readings
            include_timestamps: Whether to include timestamp column
            
        Returns:
            DataFrame with complete sensor readings
        """
        data = {
            "BPM": self.vital_sim.generate_time_series("BPM", n_samples, anomaly_rate),
            "SPO2": self.vital_sim.generate_time_series("SPO2", n_samples, anomaly_rate),
            "Body_Temp": self.vital_sim.generate_time_series("Body_Temp", n_samples, anomaly_rate),
            "Ambient_Temp": self.env_sim.generate_time_series("Ambient_Temp", n_samples),
            "Humidity": self.env_sim.generate_time_series("Humidity", n_samples)
        }
        
        df = pd.DataFrame(data)
        
        if include_timestamps:
            start_time = datetime.now()
            timestamps = [start_time + timedelta(seconds=i*5) for i in range(n_samples)]
            df.insert(0, "Timestamp", timestamps)
        
        logger.info(f"Generated {n_samples} sensor readings with {anomaly_rate*100}% anomaly rate")
        
        return df
    
    def generate_scenario_dataset(
        self,
        scenario: str,
        n_samples: int = 100
    ) -> pd.DataFrame:
        """
        Generate dataset for specific health scenario.
        
        Args:
            scenario: Scenario name (normal, fever, hypoxia, tachycardia)
            n_samples: Number of samples to generate
            
        Returns:
            DataFrame with scenario-specific readings
        """
        if scenario == "normal":
            return self.generate_complete_dataset(n_samples, anomaly_rate=0.0)
        
        elif scenario == "fever":
            data = {
                "BPM": self.vital_sim.generate_time_series("BPM", n_samples, 0.0, trend="increasing"),
                "SPO2": self.vital_sim.generate_time_series("SPO2", n_samples, 0.0),
                "Body_Temp": np.random.uniform(37.5, 39.5, n_samples),
                "Ambient_Temp": self.env_sim.generate_time_series("Ambient_Temp", n_samples),
                "Humidity": self.env_sim.generate_time_series("Humidity", n_samples)
            }
        
        elif scenario == "hypoxia":
            data = {
                "BPM": self.vital_sim.generate_time_series("BPM", n_samples, 0.0, trend="increasing"),
                "SPO2": np.random.uniform(85, 93, n_samples),
                "Body_Temp": self.vital_sim.generate_time_series("Body_Temp", n_samples, 0.0),
                "Ambient_Temp": self.env_sim.generate_time_series("Ambient_Temp", n_samples),
                "Humidity": self.env_sim.generate_time_series("Humidity", n_samples)
            }
        
        elif scenario == "tachycardia":
            data = {
                "BPM": np.random.uniform(110, 150, n_samples),
                "SPO2": self.vital_sim.generate_time_series("SPO2", n_samples, 0.0),
                "Body_Temp": self.vital_sim.generate_time_series("Body_Temp", n_samples, 0.0),
                "Ambient_Temp": self.env_sim.generate_time_series("Ambient_Temp", n_samples),
                "Humidity": self.env_sim.generate_time_series("Humidity", n_samples)
            }
        
        else:
            raise ValueError(f"Unknown scenario: {scenario}")
        
        df = pd.DataFrame(data)
        logger.info(f"Generated {scenario} scenario with {n_samples} samples")
        
        return df



class RealisticSensorSimulator:
    """
    Advanced simulation engine with health condition profiles, 
    temporal patterns, and state transitions.
    """
    
    def __init__(self, random_state: Optional[int] = None):
        """
        Initialize RealisticSensorSimulator.
        
        Args:
            random_state: Random seed for reproducibility
        """
        self.random_state = random_state
        if random_state is not None:
            np.random.seed(random_state)
        
        self.current_condition = "NORMAL"
        self.time_in_condition = 0
        self.env_sim = EnvironmentalSimulator(random_state)
    
    def _generate_vital_with_noise(
        self,
        profile: Dict,
        vital: str,
        time_of_day: float = 0.5,
        activity_level: float = 0.0
    ) -> float:
        """
        Generate vital sign with realistic noise and variability.
        
        Args:
            profile: Health condition profile
            vital: Vital sign name (BPM, SPO2, Body_Temp)
            time_of_day: Time of day factor (0-1, affects circadian rhythm)
            activity_level: Activity level factor (0-1, affects vitals)
            
        Returns:
            Simulated vital sign value with noise
        """
        params = profile[vital]
        
        # Base value from normal distribution
        base_value = np.random.normal(params["mean"], params["std"])
        
        # Add circadian rhythm (sinusoidal pattern)
        if vital == "Body_Temp":
            # Temperature lowest at 4 AM, highest at 6 PM
            circadian_effect = 0.3 * np.sin(2 * np.pi * time_of_day - np.pi/2)
            base_value += circadian_effect
        elif vital == "BPM":
            # Heart rate varies with circadian rhythm
            circadian_effect = params["std"] * 0.5 * np.sin(2 * np.pi * time_of_day)
            base_value += circadian_effect
        
        # Add activity effect
        if vital == "BPM":
            base_value += activity_level * 30  # Up to +30 BPM for activity
        elif vital == "SPO2":
            base_value -= activity_level * 2  # Slight decrease with intense activity
        elif vital == "Body_Temp":
            base_value += activity_level * 0.5  # Slight increase with activity
        
        # Add measurement noise (realistic sensor variability)
        noise_levels = {"BPM": 2, "SPO2": 0.5, "Body_Temp": 0.1}
        noise = np.random.normal(0, noise_levels.get(vital, 0.5))
        base_value += noise
        
        # Clip to valid range
        value = np.clip(base_value, params["min"], params["max"])
        
        # Round appropriately
        if vital == "SPO2":
            return round(value, 1)
        elif vital == "Body_Temp":
            return round(value, 1)
        else:  # BPM
            return round(value, 0)
    
    def _should_transition(self, current_condition: str, time_in_condition: int) -> bool:
        """
        Determine if condition should transition to another state.
        
        Args:
            current_condition: Current health condition
            time_in_condition: Number of samples in current condition
            
        Returns:
            Boolean indicating if transition should occur
        """
        # Transition probabilities based on condition stability
        transition_thresholds = {
            "NORMAL": 100,      # Stay normal longer
            "TACHYCARDIA": 30,  # Moderate duration
            "HYPOXIA": 20,      # Shorter duration (urgent)
            "FEVER": 50,        # Can persist
            "CRITICAL": 15      # Very short (emergency)
        }
        
        threshold = transition_thresholds.get(current_condition, 50)
        
        # Probabilistic transition after threshold
        if time_in_condition > threshold:
            transition_prob = min(0.3, (time_in_condition - threshold) * 0.01)
            return np.random.random() < transition_prob
        
        return False
    
    def _get_next_condition(self, current_condition: str) -> str:
        """
        Determine next health condition based on transition logic.
        
        Args:
            current_condition: Current health condition
            
        Returns:
            Next health condition
        """
        # Transition probability matrix
        transitions = {
            "NORMAL": {
                "NORMAL": 0.7,
                "TACHYCARDIA": 0.1,
                "HYPOXIA": 0.05,
                "FEVER": 0.1,
                "CRITICAL": 0.05
            },
            "TACHYCARDIA": {
                "NORMAL": 0.5,
                "TACHYCARDIA": 0.2,
                "HYPOXIA": 0.1,
                "FEVER": 0.1,
                "CRITICAL": 0.1
            },
            "HYPOXIA": {
                "NORMAL": 0.4,
                "TACHYCARDIA": 0.2,
                "HYPOXIA": 0.1,
                "FEVER": 0.05,
                "CRITICAL": 0.25
            },
            "FEVER": {
                "NORMAL": 0.5,
                "TACHYCARDIA": 0.15,
                "HYPOXIA": 0.05,
                "FEVER": 0.2,
                "CRITICAL": 0.1
            },
            "CRITICAL": {
                "NORMAL": 0.2,
                "TACHYCARDIA": 0.2,
                "HYPOXIA": 0.3,
                "FEVER": 0.1,
                "CRITICAL": 0.2
            }
        }
        
        probs = transitions.get(current_condition, transitions["NORMAL"])
        conditions = list(probs.keys())
        probabilities = list(probs.values())
        
        return np.random.choice(conditions, p=probabilities)
    
    def generate_realistic_sensor_data(
        self,
        condition: str = "NORMAL",
        n_samples: int = 100,
        include_timestamps: bool = True,
        enable_transitions: bool = False
    ) -> pd.DataFrame:
        """
        Generate realistic sensor data with noise, variability, and temporal patterns.
        
        Args:
            condition: Initial health condition profile
            n_samples: Number of samples to generate
            include_timestamps: Whether to include timestamp column
            enable_transitions: Whether to enable state transitions
            
        Returns:
            DataFrame with realistic sensor readings
        """
        if condition not in HEALTH_CONDITION_PROFILES:
            raise ValueError(f"Unknown condition: {condition}. Available: {list(HEALTH_CONDITION_PROFILES.keys())}")
        
        data = []
        self.current_condition = condition
        self.time_in_condition = 0
        
        for i in range(n_samples):
            # Calculate time of day (0-1 representing 24 hours)
            time_of_day = (i % 288) / 288  # Assuming 5-min intervals, 288 samples = 24h
            
            # Calculate activity level (varies throughout day)
            # Higher during day (0.3-0.7), lower at night
            hour = time_of_day * 24
            if 6 <= hour < 22:  # Daytime
                activity_level = 0.3 + 0.4 * np.random.random()
            else:  # Nighttime
                activity_level = 0.0 + 0.2 * np.random.random()
            
            # Get current profile
            profile = HEALTH_CONDITION_PROFILES[self.current_condition]
            
            # Generate vitals with noise and patterns
            reading = {
                "BPM": self._generate_vital_with_noise(profile, "BPM", time_of_day, activity_level),
                "SPO2": self._generate_vital_with_noise(profile, "SPO2", time_of_day, activity_level),
                "Body_Temp": self._generate_vital_with_noise(profile, "Body_Temp", time_of_day, activity_level),
                "Ambient_Temp": self.env_sim.generate_reading("Ambient_Temp"),
                "Humidity": self.env_sim.generate_reading("Humidity"),
                "Condition": self.current_condition
            }
            
            data.append(reading)
            self.time_in_condition += 1
            
            # Check for state transition
            if enable_transitions and self._should_transition(self.current_condition, self.time_in_condition):
                self.current_condition = self._get_next_condition(self.current_condition)
                self.time_in_condition = 0
                logger.info(f"Condition transitioned to {self.current_condition} at sample {i}")
        
        df = pd.DataFrame(data)
        
        if include_timestamps:
            start_time = datetime.now()
            timestamps = [start_time + timedelta(seconds=i*5) for i in range(n_samples)]
            df.insert(0, "Timestamp", timestamps)
        
        logger.info(f"Generated {n_samples} realistic sensor readings for condition: {condition}")
        
        return df
    
    def batch_generate_training_data(
        self,
        samples_per_condition: int = 200,
        include_timestamps: bool = False,
        add_noise_variation: bool = True
    ) -> pd.DataFrame:
        """
        Generate batch training data across all health conditions.
        
        Args:
            samples_per_condition: Number of samples per condition
            include_timestamps: Whether to include timestamps
            add_noise_variation: Whether to add extra noise variation
            
        Returns:
            DataFrame with training data for all conditions
        """
        all_data = []
        
        for condition in HEALTH_CONDITION_PROFILES.keys():
            logger.info(f"Generating training data for {condition}...")
            
            # Generate data for this condition
            condition_data = self.generate_realistic_sensor_data(
                condition=condition,
                n_samples=samples_per_condition,
                include_timestamps=include_timestamps,
                enable_transitions=False
            )
            
            # Add label column
            condition_data["Label"] = "Abnormal" if condition != "NORMAL" else "Normal"
            
            # Add extra noise variation if requested
            if add_noise_variation:
                noise_factor = np.random.uniform(0.8, 1.2, len(condition_data))
                condition_data["BPM"] = condition_data["BPM"] * noise_factor
                condition_data["SPO2"] = np.clip(condition_data["SPO2"] * noise_factor, 70, 100)
                condition_data["Body_Temp"] = condition_data["Body_Temp"] * noise_factor
            
            all_data.append(condition_data)
        
        # Combine all conditions
        combined_df = pd.concat(all_data, ignore_index=True)
        
        # Shuffle the data
        combined_df = combined_df.sample(frac=1, random_state=self.random_state).reset_index(drop=True)
        
        logger.info(f"Generated {len(combined_df)} total training samples across {len(HEALTH_CONDITION_PROFILES)} conditions")
        
        return combined_df


# Convenience functions for easy access
def generate_realistic_sensor_data(
    condition: str = "NORMAL",
    n_samples: int = 100,
    include_timestamps: bool = True,
    enable_transitions: bool = False,
    random_state: Optional[int] = None
) -> pd.DataFrame:
    """
    Convenience function to generate realistic sensor data.
    
    Args:
        condition: Health condition profile
        n_samples: Number of samples to generate
        include_timestamps: Whether to include timestamps
        enable_transitions: Whether to enable state transitions
        random_state: Random seed for reproducibility
        
    Returns:
        DataFrame with realistic sensor readings
    """
    simulator = RealisticSensorSimulator(random_state=random_state)
    return simulator.generate_realistic_sensor_data(
        condition=condition,
        n_samples=n_samples,
        include_timestamps=include_timestamps,
        enable_transitions=enable_transitions
    )


def batch_generate_training_data(
    samples_per_condition: int = 200,
    include_timestamps: bool = False,
    add_noise_variation: bool = True,
    random_state: Optional[int] = None
) -> pd.DataFrame:
    """
    Convenience function to generate batch training data.
    
    Args:
        samples_per_condition: Number of samples per condition
        include_timestamps: Whether to include timestamps
        add_noise_variation: Whether to add extra noise variation
        random_state: Random seed for reproducibility
        
    Returns:
        DataFrame with training data for all conditions
    """
    simulator = RealisticSensorSimulator(random_state=random_state)
    return simulator.batch_generate_training_data(
        samples_per_condition=samples_per_condition,
        include_timestamps=include_timestamps,
        add_noise_variation=add_noise_variation
    )


def get_available_conditions() -> List[str]:
    """
    Get list of available health condition profiles.
    
    Returns:
        List of condition names
    """
    return list(HEALTH_CONDITION_PROFILES.keys())


def get_condition_info(condition: str) -> Dict:
    """
    Get information about a specific health condition profile.
    
    Args:
        condition: Condition name
        
    Returns:
        Dictionary with condition parameters
    """
    if condition not in HEALTH_CONDITION_PROFILES:
        raise ValueError(f"Unknown condition: {condition}")
    
    return HEALTH_CONDITION_PROFILES[condition]
