import time
import math
import random
from typing import Dict, Any, Optional
from ml.model import DEVICE_SPECS, AssetReading

class MultiAssetSimulator:
    """
    Simulates four industrial edge assets according to SRS specifications:
    - MCH-007: Bottle Filling Machine
    - CNC-003: Precision Milling
    - CONV-012: Logistics Conveyor
    - ENV-001: Air Quality and Safety Unit

    Supports fault injection: SPIKE, DRIFT, OVERLOAD, DROP, and CLEAR.
    """
    def __init__(self):
        self.step = 0
        self.active_faults: Dict[str, Dict[str, Any]] = {}
        # Actuator states applied by autonomous feedback
        self.asset_actuators: Dict[str, Dict[str, str]] = {
            dev_id: dict(spec["default_actuators"])
            for dev_id, spec in DEVICE_SPECS.items()
        }
        self.device_states: Dict[str, str] = {
            dev_id: "RUNNING" for dev_id in DEVICE_SPECS
        }

    def inject_fault(self, device_id: str, fault_type: str, target_sensor: Optional[str] = None):
        """
        Injects test faults:
        - 'SPIKE': Sudden aggressive jump past critical limit
        - 'DRIFT': Gradual creeping drift
        - 'OVERLOAD': Simultaneous thermal and power surge
        - 'DROP': Pressure or flow collapse
        - 'CLEAR': Resets fault
        """
        if fault_type == "CLEAR" or fault_type == "NONE":
            if device_id in self.active_faults:
                del self.active_faults[device_id]
            self.device_states[device_id] = "RUNNING"
            self.asset_actuators[device_id] = dict(DEVICE_SPECS[device_id]["default_actuators"])
        else:
            self.active_faults[device_id] = {
                "type": fault_type,
                "sensor": target_sensor,
                "intensity": 0.0,
                "start_step": self.step
            }

    def apply_actuator_feedback(self, device_id: str, new_actuators: Dict[str, str]):
        """
        Applies autonomous actuator response to bring machine back into safe envelope.
        For example: Cooling MAXIMUM brings temperature back down!
        """
        self.asset_actuators[device_id].update(new_actuators)
        # If emergency stop or trip, machine state becomes FAULT / TRIPPED
        for act, val in new_actuators.items():
            if "STOP" in val or "HALT" in val or "TRIP" in val or "CLOSED" in val:
                self.device_states[device_id] = "FAULT_STOPPED"

    def reset_machine(self, device_id: str):
        """Operator reset command."""
        self.inject_fault(device_id, "CLEAR")
        self.device_states[device_id] = "RUNNING"
        self.asset_actuators[device_id] = dict(DEVICE_SPECS[device_id]["default_actuators"])

    def generate_reading(self, device_id: str) -> AssetReading:
        self.step += 1
        spec = DEVICE_SPECS[device_id]
        baselines = spec["baselines"]
        readings = {}
        t = self.step * 0.15

        # Base nominal oscillations + noise
        for sensor, base in baselines.items():
            wave = math.sin(t + hash(sensor) % 5) * (base * 0.03)
            noise = random.gauss(0, base * 0.015)
            readings[sensor] = round(base + wave + noise, 2)

        # Apply Fault Injection
        if device_id in self.active_faults:
            fault = self.active_faults[device_id]
            ftype = fault["type"]

            if ftype == "SPIKE":
                # Immediately breach critical limit
                if device_id == "MCH-007":
                    readings["temperature"] = round(92.4 + random.uniform(0.5, 3.0), 2)
                    readings["vibration"] = round(4.8 + random.uniform(0.2, 0.8), 2)
                elif device_id == "CNC-003":
                    readings["spindle_temp"] = round(89.5 + random.uniform(0.5, 2.5), 2)
                    readings["vibration"] = round(6.2 + random.uniform(0.3, 1.0), 2)
                elif device_id == "CONV-012":
                    readings["motor_temp"] = round(84.5 + random.uniform(0.5, 2.0), 2)
                    readings["belt_tension"] = round(655.0 + random.uniform(5, 30), 1)
                elif device_id == "ENV-001":
                    readings["gas_level"] = round(285.0 + random.uniform(10, 50), 1)
                    readings["smoke_level"] = round(95.0 + random.uniform(5, 20), 1)

            elif ftype == "DRIFT":
                fault["intensity"] = min(35.0, fault["intensity"] + 1.2)
                tgt = fault.get("sensor") or spec["primary_sensors"][0]
                readings[tgt] = round(readings[tgt] + fault["intensity"], 2)

            elif ftype == "OVERLOAD":
                # Thermal and electrical surge
                if "temperature" in readings: readings["temperature"] += 28.0
                if "spindle_temp" in readings: readings["spindle_temp"] += 32.0
                if "motor_temp" in readings: readings["motor_temp"] += 30.0
                if "energy" in readings: readings["energy"] += 18.0
                if "motor_current" in readings: readings["motor_current"] += 25.0

            elif ftype == "DROP":
                # Sudden pressure or coolant loss
                if "pressure" in readings: readings["pressure"] = round(max(0.5, 2.2 + random.uniform(-0.3, 0.3)), 2)
                if "coolant_flow" in readings: readings["coolant_flow"] = round(max(0.5, 3.5 + random.uniform(-0.5, 0.5)), 2)
                if "fill_rate" in readings: readings["fill_rate"] = 0.0

        # Apply Actuator Feedback Relief (closed-loop effect)
        cur_act = self.asset_actuators[device_id]
        if cur_act.get("cooling_pump") == "MAXIMUM" or cur_act.get("coolant") == "FLOOD_COOLANT_MAX":
            # Cooling drops temp back down gradually
            if "temperature" in readings and readings["temperature"] > baselines["temperature"]:
                readings["temperature"] = round(max(baselines["temperature"], readings["temperature"] - 12.0), 2)
            if "spindle_temp" in readings and readings["spindle_temp"] > baselines["spindle_temp"]:
                readings["spindle_temp"] = round(max(baselines["spindle_temp"], readings["spindle_temp"] - 14.0), 2)

        if cur_act.get("conveyor_speed") == "0%" or cur_act.get("drive_motor") == "STOPPED" or cur_act.get("spindle") == "STOPPED":
            if "vibration" in readings: readings["vibration"] = round(min(readings["vibration"], 0.8), 2)
            if "fill_rate" in readings: readings["fill_rate"] = 0.0
            if "belt_speed" in readings: readings["belt_speed"] = 0.0
            if "spindle_rpm" in readings: readings["spindle_rpm"] = 0.0

        if cur_act.get("exhaust_fan") == "FLUSH_100%":
            if "gas_level" in readings: readings["gas_level"] = round(max(baselines["gas_level"], readings["gas_level"] - 50.0), 1)
            if "smoke_level" in readings: readings["smoke_level"] = round(max(baselines["smoke_level"], readings["smoke_level"] - 25.0), 1)

        return AssetReading(
            device_id=device_id,
            readings=readings,
            state=self.device_states[device_id],
            timestamp=time.time()
        )
