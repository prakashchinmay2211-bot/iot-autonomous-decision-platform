import time
import uuid
import numpy as np
import pandas as pd
from dataclasses import dataclass, asdict, field
from typing import Dict, Any, Tuple, List, Optional
from collections import deque
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

# Device Specifications according to SRS
DEVICE_SPECS = {
    "MCH-007": {
        "name": "Bottle Filling Machine",
        "primary_sensors": ["temperature", "vibration", "pressure", "energy", "fill_rate"],
        "units": {"temperature": "°C", "vibration": "mm/s", "pressure": "bar", "energy": "kWh", "fill_rate": "bpm"},
        "baselines": {"temperature": 62.0, "vibration": 1.8, "pressure": 5.8, "energy": 14.2, "fill_rate": 120.0},
        "limits": {
            "temp_critical": 88.0,
            "vib_critical": 4.0,
            "pressure_min_critical": 4.0,
            "pressure_max_critical": 8.5
        },
        "default_actuators": {"fill_valve": "OPEN", "conveyor_speed": "100%", "cooling_pump": "NORMAL"}
    },
    "CNC-003": {
        "name": "Precision Milling Machine",
        "primary_sensors": ["spindle_temp", "vibration", "coolant_flow", "spindle_rpm", "motor_current"],
        "units": {"spindle_temp": "°C", "vibration": "mm/s", "coolant_flow": "L/min", "spindle_rpm": "RPM", "motor_current": "A"},
        "baselines": {"spindle_temp": 52.0, "vibration": 2.1, "coolant_flow": 18.5, "spindle_rpm": 3200.0, "motor_current": 16.5},
        "limits": {
            "temp_critical": 85.0,
            "vib_critical": 5.5,
            "coolant_min_critical": 8.0
        },
        "default_actuators": {"spindle": "RUNNING", "coolant": "AUTO", "brake": "DISENGAGED"}
    },
    "CONV-012": {
        "name": "Logistics Conveyor",
        "primary_sensors": ["motor_temp", "belt_tension", "belt_speed", "motor_current"],
        "units": {"motor_temp": "°C", "belt_tension": "N", "belt_speed": "m/s", "motor_current": "A"},
        "baselines": {"motor_temp": 48.0, "belt_tension": 450.0, "belt_speed": 1.8, "motor_current": 12.0},
        "limits": {
            "temp_critical": 80.0,
            "tension_critical": 620.0
        },
        "default_actuators": {"drive_motor": "RUNNING", "diverter": "NORMAL"}
    },
    "ENV-001": {
        "name": "Air Quality & Safety Unit",
        "primary_sensors": ["gas_level", "smoke_level", "ambient_temp", "humidity"],
        "units": {"gas_level": "ppm", "smoke_level": "ppm", "ambient_temp": "°C", "humidity": "%"},
        "baselines": {"gas_level": 45.0, "smoke_level": 12.0, "ambient_temp": 24.0, "humidity": 50.0},
        "limits": {
            "gas_critical": 250.0,
            "smoke_critical": 80.0
        },
        "default_actuators": {"exhaust_fan": "LOW", "evacuation_siren": "OFF", "air_damper": "AUTO"}
    }
}


@dataclass
class AssetReading:
    device_id: str
    readings: Dict[str, float]
    state: str = "RUNNING"
    timestamp: float = 0.0

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "device_id": self.device_id,
            "timestamp": self.timestamp,
            "state": self.state,
            "readings": self.readings,
            "units": DEVICE_SPECS.get(self.device_id, {}).get("units", {})
        }


class IsolationForestAnomalyDetector:
    """Multi-asset Isolation Forest & Rolling Z-Score Anomaly Detector."""
    def __init__(self, contamination: float = 0.04):
        self.contamination = contamination
        self.models: Dict[str, IsolationForest] = {}
        self.scalers: Dict[str, StandardScaler] = {}
        self.rolling_buffers: Dict[str, deque] = {}
        self.fit_all_baselines()

    def fit_all_baselines(self):
        np.random.seed(42)
        for dev_id, spec in DEVICE_SPECS.items():
            features = spec["primary_sensors"]
            baselines = spec["baselines"]
            n_samples = 800
            data_cols = []
            for feat in features:
                base = baselines[feat]
                std = max(1.0, base * 0.08)
                data_cols.append(np.random.normal(base, std, n_samples))
            X = np.column_stack(data_cols)
            
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            iso = IsolationForest(contamination=self.contamination, random_state=42, n_estimators=100)
            iso.fit(X_scaled)

            self.models[dev_id] = iso
            self.scalers[dev_id] = scaler
            self.rolling_buffers[dev_id] = deque(maxlen=40)

    def evaluate(self, reading: AssetReading) -> Dict[str, Any]:
        dev_id = reading.device_id
        spec = DEVICE_SPECS.get(dev_id)
        if not spec or dev_id not in self.models:
            return {"risk_score": 0.0, "is_anomaly": False, "feature_contributors": {}}

        features = spec["primary_sensors"]
        vals = [float(reading.readings.get(f, spec["baselines"].get(f, 0.0))) for f in features]
        X = np.array([vals])
        
        # Buffer for rolling Z-Score
        self.rolling_buffers[dev_id].append(vals)
        buf_arr = np.array(self.rolling_buffers[dev_id])
        
        # Rolling Z-score computation
        z_scores = {}
        top_contributor = None
        max_abs_z = 0.0

        if len(buf_arr) >= 5:
            means = np.mean(buf_arr, axis=0)
            stds = np.std(buf_arr, axis=0)
            stds[stds == 0] = 1.0
            cur_z = (vals - means) / stds
            for idx, feat in enumerate(features):
                z_val = round(float(cur_z[idx]), 2)
                z_scores[feat] = z_val
                if abs(z_val) > max_abs_z:
                    max_abs_z = abs(z_val)
                    top_contributor = feat

        # Isolation Forest scoring
        X_scaled = self.scalers[dev_id].transform(X)
        pred = self.models[dev_id].predict(X_scaled)[0]
        decision_val = self.models[dev_id].decision_function(X_scaled)[0]
        # Normalize risk score to [0.0 - 1.0] where 1.0 = extreme risk
        risk_score = round(float(1.0 - (1.0 / (1.0 + np.exp(-decision_val * 6.0)))), 3)
        is_anomaly = bool(pred == -1 or risk_score >= 0.65)

        return {
            "risk_score": risk_score,
            "is_anomaly": is_anomaly,
            "anomaly_type": "MULTIVARIATE_DRIFT" if is_anomaly else "NORMAL",
            "feature_contributors": z_scores,
            "top_contributor": top_contributor
        }


class AutonomousDecisionEngine:
    """
    Autonomous Rule Engine + Explainable Decision Interventions
    Enforces exact protective responses according to SRS Table 11:
    - MCH-007: EMERGENCY_FAULT_STOP
    - CNC-003: SPINDLE_SAFETY_TRIP
    - CONV-012: EMERGENCY_CONVEYOR_HALT
    - ENV-001: HAZMAT_EVACUATION_PURGE
    """
    def __init__(self):
        self.detector = IsolationForestAnomalyDetector()
        self.active_alerts: Dict[str, Dict[str, Any]] = {}
        self.alert_history: deque = deque(maxlen=200)
        self.decision_history: deque = deque(maxlen=200)

    def calculate_health_score(self, dev_id: str, readings: Dict[str, float], risk_score: float) -> float:
        spec = DEVICE_SPECS.get(dev_id, {})
        limits = spec.get("limits", {})
        penalty = risk_score * 40.0  # ML penalty up to 40%

        if dev_id == "MCH-007":
            t = readings.get("temperature", 0.0)
            v = readings.get("vibration", 0.0)
            p = readings.get("pressure", 5.0)
            if t >= limits.get("temp_critical", 88.0):
                penalty += 50.0
            elif t > 75.0:
                penalty += 20.0
            if v >= limits.get("vib_critical", 4.0):
                penalty += 45.0
            if p <= limits.get("pressure_min_critical", 4.0):
                penalty += 35.0

        elif dev_id == "CNC-003":
            t = readings.get("spindle_temp", 0.0)
            v = readings.get("vibration", 0.0)
            if t > limits.get("temp_critical", 85.0):
                penalty += 50.0
            if v > limits.get("vib_critical", 5.5):
                penalty += 45.0

        elif dev_id == "CONV-012":
            t = readings.get("motor_temp", 0.0)
            ten = readings.get("belt_tension", 450.0)
            if t > limits.get("temp_critical", 80.0):
                penalty += 50.0
            if ten > limits.get("tension_critical", 620.0):
                penalty += 50.0

        elif dev_id == "ENV-001":
            g = readings.get("gas_level", 0.0)
            s = readings.get("smoke_level", 0.0)
            if g > limits.get("gas_critical", 250.0):
                penalty += 60.0
            if s > limits.get("smoke_critical", 80.0):
                penalty += 60.0

        health = max(0.0, min(100.0, 100.0 - penalty))
        return round(health, 1)

    def process_telemetry(self, reading: AssetReading) -> Dict[str, Any]:
        dev_id = reading.device_id
        r = reading.readings
        spec = DEVICE_SPECS.get(dev_id, {})
        limits = spec.get("limits", {})

        # Step 1: Run ML Anomaly Detection
        ml_res = self.detector.evaluate(reading)
        risk_score = ml_res["risk_score"]
        is_anomaly = ml_res["is_anomaly"]
        
        # Step 2: Compute Machine Health Score (0 - 100%)
        health_score = self.calculate_health_score(dev_id, r, risk_score)
        
        # Step 3: Autonomous Rule Interventions
        decision = None
        severity = "NORMAL"
        alert_msg = None
        actuator_updates = dict(spec.get("default_actuators", {}))

        # Asset 1: MCH-007 Bottle Filling Machine
        if dev_id == "MCH-007":
            temp = r.get("temperature", 0.0)
            vib = r.get("vibration", 0.0)
            press = r.get("pressure", 5.8)

            if temp >= limits["temp_critical"] or vib >= limits["vib_critical"] or press <= limits["pressure_min_critical"]:
                severity = "CRITICAL"
                reasons = []
                if temp >= limits["temp_critical"]:
                    reasons.append(f"Temperature {temp:.1f}°C >= limit {limits['temp_critical']}°C")
                if vib >= limits["vib_critical"]:
                    reasons.append(f"Vibration {vib:.2f} mm/s >= limit {limits['vib_critical']} mm/s")
                if press <= limits["pressure_min_critical"]:
                    reasons.append(f"Hydraulic pressure {press:.2f} bar <= minimum {limits['pressure_min_critical']} bar")
                
                explanation = "Autonomous EMERGENCY_FAULT_STOP executed: " + "; ".join(reasons) + ". Fill valve closed, conveyor halted to 0, cooling switched to MAXIMUM."
                actuator_updates = {"fill_valve": "CLOSED", "conveyor_speed": "0%", "cooling_pump": "MAXIMUM"}
                alert_msg = f"EMERGENCY FAULT TRIP on {dev_id}: {'; '.join(reasons)}"

                decision = {
                    "decision_id": f"DEC-{uuid.uuid4().hex[:8].upper()}",
                    "device_id": dev_id,
                    "action_taken": "EMERGENCY_FAULT_STOP",
                    "actuator_updates": actuator_updates,
                    "explanation": explanation,
                    "severity": severity,
                    "timestamp": time.time()
                }

        # Asset 2: CNC-003 Precision Milling Machine
        elif dev_id == "CNC-003":
            stemp = r.get("spindle_temp", 0.0)
            vib = r.get("vibration", 0.0)

            if stemp > limits["temp_critical"] or vib > limits["vib_critical"]:
                severity = "CRITICAL"
                reasons = []
                if stemp > limits["temp_critical"]:
                    reasons.append(f"Spindle temperature {stemp:.1f}°C > safety trip limit {limits['temp_critical']}°C")
                if vib > limits["vib_critical"]:
                    reasons.append(f"Spindle vibration {vib:.2f} mm/s > safety limit {limits['vib_critical']} mm/s")

                explanation = "Autonomous SPINDLE_SAFETY_TRIP executed: " + "; ".join(reasons) + ". Spindle cut off, flood coolant activated, spindle brake engaged."
                actuator_updates = {"spindle": "STOPPED", "coolant": "FLOOD_COOLANT_MAX", "brake": "ENGAGED"}
                alert_msg = f"SPINDLE SAFETY TRIP on {dev_id}: {'; '.join(reasons)}"

                decision = {
                    "decision_id": f"DEC-{uuid.uuid4().hex[:8].upper()}",
                    "device_id": dev_id,
                    "action_taken": "SPINDLE_SAFETY_TRIP",
                    "actuator_updates": actuator_updates,
                    "explanation": explanation,
                    "severity": severity,
                    "timestamp": time.time()
                }

        # Asset 3: CONV-012 Logistics Conveyor
        elif dev_id == "CONV-012":
            mtemp = r.get("motor_temp", 0.0)
            tension = r.get("belt_tension", 450.0)

            if mtemp > limits["temp_critical"] or tension > limits["tension_critical"]:
                severity = "CRITICAL"
                reasons = []
                if mtemp > limits["temp_critical"]:
                    reasons.append(f"Conveyor motor temperature {mtemp:.1f}°C > {limits['temp_critical']}°C")
                if tension > limits["tension_critical"]:
                    reasons.append(f"Belt tension {tension:.0f} N > safe threshold {limits['tension_critical']} N")

                explanation = "Autonomous EMERGENCY_CONVEYOR_HALT executed: " + "; ".join(reasons) + ". Drive motor stopped, parcels routed to safety bypass diverter."
                actuator_updates = {"drive_motor": "STOPPED", "diverter": "BYPASS_ENGAGED"}
                alert_msg = f"CONVEYOR HALT on {dev_id}: {'; '.join(reasons)}"

                decision = {
                    "decision_id": f"DEC-{uuid.uuid4().hex[:8].upper()}",
                    "device_id": dev_id,
                    "action_taken": "EMERGENCY_CONVEYOR_HALT",
                    "actuator_updates": actuator_updates,
                    "explanation": explanation,
                    "severity": severity,
                    "timestamp": time.time()
                }

        # Asset 4: ENV-001 Air Quality & Safety Unit
        elif dev_id == "ENV-001":
            gas = r.get("gas_level", 0.0)
            smoke = r.get("smoke_level", 0.0)

            if gas > limits["gas_critical"] or smoke > limits["smoke_critical"]:
                severity = "CRITICAL"
                reasons = []
                if gas > limits["gas_critical"]:
                    reasons.append(f"Combustible/Toxic Gas {gas:.1f} ppm > threshold {limits['gas_critical']} ppm")
                if smoke > limits["smoke_critical"]:
                    reasons.append(f"Smoke particulate {smoke:.1f} ppm > threshold {limits['smoke_critical']} ppm")

                explanation = "Autonomous HAZMAT_EVACUATION_PURGE executed: " + "; ".join(reasons) + ". Industrial exhaust fans 100% active, siren sounded, blast damper opened."
                actuator_updates = {"exhaust_fan": "FLUSH_100%", "evacuation_siren": "ON_ALERT", "air_damper": "100%_OPEN"}
                alert_msg = f"HAZMAT EVACUATION PURGE on {dev_id}: {'; '.join(reasons)}"

                decision = {
                    "decision_id": f"DEC-{uuid.uuid4().hex[:8].upper()}",
                    "device_id": dev_id,
                    "action_taken": "HAZMAT_EVACUATION_PURGE",
                    "actuator_updates": actuator_updates,
                    "explanation": explanation,
                    "severity": severity,
                    "timestamp": time.time()
                }

        # Handle Alert Lifecycle
        created_alert = None
        if alert_msg:
            alert_id = f"ALT-{dev_id}-{int(time.time() * 10) % 100000}"
            created_alert = {
                "alert_id": alert_id,
                "device_id": dev_id,
                "severity": severity,
                "message": alert_msg,
                "status": "ACTIVE",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            self.active_alerts[alert_id] = created_alert
            self.alert_history.append(created_alert)
        elif is_anomaly and severity == "NORMAL":
            severity = "WARNING"
            alert_id = f"ALT-ML-{dev_id}-{int(time.time() * 10) % 100000}"
            created_alert = {
                "alert_id": alert_id,
                "device_id": dev_id,
                "severity": "WARNING",
                "message": f"ML Anomaly detected (Risk: {risk_score:.2f}, Top Contributor: {ml_res.get('top_contributor')})",
                "status": "ACTIVE",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            self.active_alerts[alert_id] = created_alert
            self.alert_history.append(created_alert)

        if decision:
            self.decision_history.append(decision)

        return {
            "device_id": dev_id,
            "timestamp": reading.timestamp,
            "health_score": health_score,
            "severity": severity,
            "readings": r,
            "actuators": actuator_updates,
            "ml_evaluation": ml_res,
            "decision": decision,
            "alert": created_alert
        }

    def update_alert_status(self, alert_id: str, new_status: str):
        """Alert lifecycle transition: ACTIVE -> ACKNOWLEDGED -> RESOLVED."""
        if alert_id in self.active_alerts:
            self.active_alerts[alert_id]["status"] = new_status
            if new_status == "RESOLVED":
                # Remove from active list
                del self.active_alerts[alert_id]
