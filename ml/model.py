import time
import numpy as np
import pandas as pd
from dataclasses import dataclass, asdict
from typing import Dict, Any, Tuple, List
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

@dataclass
class SensorReading:
    device_id: str
    temperature: float      # Celsius (e.g. 20 - 100)
    vibration: float        # mm/s RMS (e.g. 0.5 - 12.0)
    pressure: float         # bar (e.g. 1.0 - 10.0)
    current: float          # Amperes (e.g. 5.0 - 50.0)
    humidity: float         # % (e.g. 20 - 90)
    timestamp: float = 0.0

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def feature_vector(self) -> np.ndarray:
        return np.array([[self.temperature, self.vibration, self.pressure, self.current, self.humidity]])


class IoTDecisionEngine:
    """
    Autonomous Machine Learning Decision & Alert Management Engine.
    Combines Isolation Forest Anomaly Detection, Health Index Scoring,
    and a Multi-Stage Autonomous Actuator Decision Matrix.
    """
    def __init__(self, contamination: float = 0.05, random_state: int = 42):
        self.contamination = contamination
        self.random_state = random_state
        self.model = IsolationForest(
            contamination=self.contamination,
            random_state=self.random_state,
            n_estimators=100
        )
        self.scaler = StandardScaler()
        self.is_trained = False
        self.feature_names = ["temperature", "vibration", "pressure", "current", "humidity"]
        
        # User-customizable thresholds (defaults)
        self.thresholds = {
            "temp_warning": 70.0,
            "temp_critical": 85.0,
            "vibration_warning": 4.5,
            "vibration_critical": 7.0,
            "pressure_warning": 6.5,
            "pressure_critical": 8.0,
            "current_warning": 35.0,
            "current_critical": 45.0,
        }
        
        # Autonomous Operation Mode: "autonomous", "supervised", "manual"
        self.decision_mode = "autonomous"
        
        # Train default baseline model so it works immediately
        self.train_baseline_model()

    def update_thresholds(self, new_thresholds: Dict[str, float]):
        """Allows user to dynamically update decision thresholds."""
        self.thresholds.update(new_thresholds)

    def set_decision_mode(self, mode: str):
        """Toggle between 'autonomous', 'supervised', and 'manual'."""
        if mode in ["autonomous", "supervised", "manual"]:
            self.decision_mode = mode

    def train_baseline_model(self, n_samples: int = 1000):
        """Generates realistic normal industrial IoT telemetry and fits Isolation Forest."""
        np.random.seed(self.random_state)
        # Normal nominal ranges
        temps = np.random.normal(55.0, 5.0, n_samples)
        vibrations = np.random.normal(2.2, 0.6, n_samples)
        pressures = np.random.normal(4.2, 0.5, n_samples)
        currents = np.random.normal(22.0, 3.5, n_samples)
        humidities = np.random.normal(48.0, 6.0, n_samples)

        X = np.column_stack([temps, vibrations, pressures, currents, humidities])
        self.scaler.fit(X)
        X_scaled = self.scaler.transform(X)
        self.model.fit(X_scaled)
        self.is_trained = True

    def retrain_with_data(self, df: pd.DataFrame, contamination: float = None):
        """Retrains ML model on collected telemetry data with user-chosen contamination."""
        if contamination is not None:
            self.contamination = contamination
            self.model = IsolationForest(
                contamination=self.contamination,
                random_state=self.random_state,
                n_estimators=100
            )

        X = df[self.feature_names].values
        self.scaler.fit(X)
        X_scaled = self.scaler.transform(X)
        self.model.fit(X_scaled)
        self.is_trained = True

    def calculate_health_index(self, reading: SensorReading) -> float:
        """
        Computes equipment Health Index (0% to 100%).
        100% = Pristine operating state.
        <50% = Maintenance advisory.
        <25% = Critical state.
        """
        penalties = 0.0

        # Temperature penalty
        if reading.temperature > self.thresholds["temp_critical"]:
            penalties += 35.0
        elif reading.temperature > self.thresholds["temp_warning"]:
            penalties += 15.0 * ((reading.temperature - self.thresholds["temp_warning"]) / 
                                  max(1.0, (self.thresholds["temp_critical"] - self.thresholds["temp_warning"])))

        # Vibration penalty
        if reading.vibration > self.thresholds["vibration_critical"]:
            penalties += 35.0
        elif reading.vibration > self.thresholds["vibration_warning"]:
            penalties += 15.0 * ((reading.vibration - self.thresholds["vibration_warning"]) / 
                                  max(1.0, (self.thresholds["vibration_critical"] - self.thresholds["vibration_warning"])))

        # Pressure penalty
        if reading.pressure > self.thresholds["pressure_critical"]:
            penalties += 20.0
        elif reading.pressure > self.thresholds["pressure_warning"]:
            penalties += 10.0 * ((reading.pressure - self.thresholds["pressure_warning"]) / 
                                  max(1.0, (self.thresholds["pressure_critical"] - self.thresholds["pressure_warning"])))

        # Current penalty
        if reading.current > self.thresholds["current_critical"]:
            penalties += 20.0
        elif reading.current > self.thresholds["current_warning"]:
            penalties += 10.0 * ((reading.current - self.thresholds["current_warning"]) / 
                                  max(1.0, (self.thresholds["current_critical"] - self.thresholds["current_warning"])))

        health = max(0.0, min(100.0, 100.0 - penalties))
        return round(health, 1)

    def evaluate(self, reading: SensorReading) -> Dict[str, Any]:
        """
        Full inference step:
        1. ML Anomaly Score (Isolation Forest)
        2. Health Index (0-100%)
        3. Alert Severity (NORMAL, WARNING, CRITICAL)
        4. Autonomous Actuator Decision
        """
        # Feature scaling & ML prediction
        vec = reading.feature_vector()
        vec_scaled = self.scaler.transform(vec)
        
        # is_anomaly: -1 = anomaly, 1 = normal
        pred = self.model.predict(vec_scaled)[0]
        # anomaly_score: negative scores are anomalies
        raw_score = self.model.decision_function(vec_scaled)[0]
        # Normalized score: 0 to 1 (lower = more abnormal)
        normalized_ml_score = round(float(1.0 / (1.0 + np.exp(-raw_score * 5.0))), 3)
        is_anomaly = bool(pred == -1)

        health_index = self.calculate_health_index(reading)

        # Alert evaluation
        alerts: List[Dict[str, str]] = []
        severity = "NORMAL"

        if reading.temperature > self.thresholds["temp_critical"]:
            alerts.append({"type": "TEMP_CRITICAL", "msg": f"Temperature {reading.temperature:.1f}°C exceeds critical threshold ({self.thresholds['temp_critical']}°C)"})
            severity = "CRITICAL"
        elif reading.temperature > self.thresholds["temp_warning"]:
            alerts.append({"type": "TEMP_WARNING", "msg": f"Temperature {reading.temperature:.1f}°C exceeds warning threshold ({self.thresholds['temp_warning']}°C)"})
            if severity != "CRITICAL":
                severity = "WARNING"

        if reading.vibration > self.thresholds["vibration_critical"]:
            alerts.append({"type": "VIB_CRITICAL", "msg": f"Vibration {reading.vibration:.2f} mm/s exceeds critical limit ({self.thresholds['vibration_critical']} mm/s)"})
            severity = "CRITICAL"
        elif reading.vibration > self.thresholds["vibration_warning"]:
            alerts.append({"type": "VIB_WARNING", "msg": f"Vibration {reading.vibration:.2f} mm/s exceeds warning limit ({self.thresholds['vibration_warning']} mm/s)"})
            if severity != "CRITICAL":
                severity = "WARNING"

        if reading.pressure > self.thresholds["pressure_critical"]:
            alerts.append({"type": "PRESS_CRITICAL", "msg": f"Pressure {reading.pressure:.2f} bar exceeds critical limit ({self.thresholds['pressure_critical']} bar)"})
            severity = "CRITICAL"
        elif reading.pressure > self.thresholds["pressure_warning"]:
            alerts.append({"type": "PRESS_WARNING", "msg": f"Pressure {reading.pressure:.2f} bar exceeds warning limit ({self.thresholds['pressure_warning']} bar)"})
            if severity != "CRITICAL":
                severity = "WARNING"

        if reading.current > self.thresholds["current_critical"]:
            alerts.append({"type": "CURRENT_CRITICAL", "msg": f"Current {reading.current:.1f}A exceeds critical limit ({self.thresholds['current_critical']}A)"})
            severity = "CRITICAL"

        if is_anomaly and severity == "NORMAL":
            alerts.append({"type": "ML_ANOMALY", "msg": f"ML detected statistical multi-sensor anomaly pattern (Score: {normalized_ml_score})"})
            severity = "WARNING"

        # Autonomous Decision Logic
        actuator_actions: List[Dict[str, Any]] = []

        if self.decision_mode == "autonomous":
            if reading.temperature > self.thresholds["temp_critical"]:
                actuator_actions.append({
                    "actuator": "COOLING_SYSTEM",
                    "action": "ENGAGE_MAX_COOLING_CYCLE",
                    "reason": "Autonomous thermal runaway mitigation",
                    "target_topic": "iot/actuators/cooling"
                })
            elif reading.temperature > self.thresholds["temp_warning"]:
                actuator_actions.append({
                    "actuator": "COOLING_SYSTEM",
                    "action": "START_AUXILIARY_FAN",
                    "reason": "Proactive temperature regulation",
                    "target_topic": "iot/actuators/cooling"
                })

            if reading.pressure > self.thresholds["pressure_critical"]:
                actuator_actions.append({
                    "actuator": "RELIEF_VALVE",
                    "action": "OPEN_PRESSURE_RELEASE_VALVE_50%",
                    "reason": "Autonomous overpressure relief",
                    "target_topic": "iot/actuators/valves"
                })

            if reading.vibration > self.thresholds["vibration_critical"]:
                actuator_actions.append({
                    "actuator": "MOTOR_DRIVE",
                    "action": "DERATE_RPM_TO_40%",
                    "reason": "Autonomous bearing stress mitigation",
                    "target_topic": "iot/actuators/motors"
                })

            if severity == "CRITICAL" and health_index < 25.0:
                actuator_actions.append({
                    "actuator": "MAIN_BREAKER",
                    "action": "EMERGENCY_SAFE_SHUTDOWN",
                    "reason": "Critical health breach autonomous trip",
                    "target_topic": "iot/actuators/breaker"
                })

            if not actuator_actions:
                actuator_actions.append({
                    "actuator": "ALL_SYSTEMS",
                    "action": "MAINTAIN_NOMINAL_STATE",
                    "reason": "Autonomous optimal operation active",
                    "target_topic": "iot/actuators/nominal"
                })
        elif self.decision_mode == "supervised":
            actuator_actions.append({
                "actuator": "OPERATOR_QUEUE",
                "action": "RECOMMEND_ACTIONS_AWAITING_CONFIRMATION",
                "reason": f"Supervised mode: {len(alerts)} alerts require operator sign-off",
                "target_topic": "iot/decisions/pending"
            })
        else:
            actuator_actions.append({
                "actuator": "MANUAL_OVERRIDE",
                "action": "AWAITING_MANUAL_DISPATCH",
                "reason": "Manual control mode active - autonomous decisions bypassed",
                "target_topic": "iot/control/manual"
            })

        return {
            "device_id": reading.device_id,
            "timestamp": reading.timestamp,
            "telemetry": reading.to_dict(),
            "ml_anomaly": is_anomaly,
            "ml_confidence_score": normalized_ml_score,
            "health_index": health_index,
            "severity": severity,
            "alerts": alerts,
            "decision_mode": self.decision_mode,
            "actuator_actions": actuator_actions
        }
