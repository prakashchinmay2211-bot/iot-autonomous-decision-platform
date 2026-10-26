import time
import random
import math
from ml.model import SensorReading

class IoTSensorSimulator:
    """
    Simulates real-world industrial IoT sensors with natural drift,
    harmonics, noise, and on-demand fault injection scenarios.
    """
    def __init__(self, device_id: str = "PUMP_TURBINE_01"):
        self.device_id = device_id
        self.step = 0
        self.active_fault = "NONE"
        
        # Baseline setpoints
        self.base_temp = 55.0
        self.base_vibration = 2.2
        self.base_pressure = 4.2
        self.base_current = 22.0
        self.base_humidity = 48.0
        
        # Dynamic offsets
        self.temp_offset = 0.0
        self.vib_offset = 0.0
        self.press_offset = 0.0
        self.curr_offset = 0.0

    def inject_fault(self, fault_type: str):
        """
        Fault Types:
        - 'NONE': Normal operation
        - 'THERMAL_RUNAWAY': Rapid heating > 85°C
        - 'BEARING_DAMAGE': High vibration spikes > 7.5 mm/s
        - 'PRESSURE_SURGE': Dangerous hydraulic pressure > 8.5 bar
        - 'MOTOR_OVERLOAD': Electrical spike > 48 A
        - 'ML_CORRELATED_DRIFT': Multi-sensor subtle anomaly (caught by ML)
        """
        self.active_fault = fault_type

    def generate_next_reading(self) -> SensorReading:
        self.step += 1
        t = self.step * 0.1

        # Periodic fluctuations + Gaussian noise
        t_wave = math.sin(t * 0.5) * 1.5
        v_wave = math.sin(t * 1.2) * 0.3
        p_wave = math.cos(t * 0.8) * 0.2
        c_wave = math.sin(t * 0.6) * 1.0
        h_wave = math.cos(t * 0.3) * 1.5

        # Normal random noise
        temp = self.base_temp + t_wave + random.gauss(0, 0.4)
        vib = self.base_vibration + v_wave + random.gauss(0, 0.15)
        press = self.base_pressure + p_wave + random.gauss(0, 0.1)
        curr = self.base_current + c_wave + random.gauss(0, 0.8)
        humid = self.base_humidity + h_wave + random.gauss(0, 0.5)

        # Apply Fault Injection
        if self.active_fault == "THERMAL_RUNAWAY":
            self.temp_offset = min(40.0, self.temp_offset + 2.5)
            temp += self.temp_offset
            vib += self.temp_offset * 0.05
        elif self.active_fault == "BEARING_DAMAGE":
            self.vib_offset = min(6.0, self.vib_offset + 0.8)
            vib += self.vib_offset + random.uniform(0.5, 2.0)
            temp += self.vib_offset * 0.8
        elif self.active_fault == "PRESSURE_SURGE":
            self.press_offset = min(4.5, self.press_offset + 0.6)
            press += self.press_offset
            curr += self.press_offset * 1.5
        elif self.active_fault == "MOTOR_OVERLOAD":
            self.curr_offset = min(30.0, self.curr_offset + 3.0)
            curr += self.curr_offset
            temp += self.curr_offset * 0.4
        elif self.active_fault == "ML_CORRELATED_DRIFT":
            # Values stay technically within individual warning thresholds,
            # but multivariate correlation is abnormal (Isolation Forest catches it)
            temp += 10.0
            press -= 1.8
            vib += 1.6
            curr += 8.0
        else:
            # Gradually cool down offsets back to normal
            self.temp_offset = max(0.0, self.temp_offset - 1.0)
            self.vib_offset = max(0.0, self.vib_offset - 0.4)
            self.press_offset = max(0.0, self.press_offset - 0.3)
            self.curr_offset = max(0.0, self.curr_offset - 1.2)

        return SensorReading(
            device_id=self.device_id,
            temperature=round(temp, 2),
            vibration=round(vib, 2),
            pressure=round(press, 2),
            current=round(curr, 2),
            humidity=round(humid, 2),
            timestamp=time.time()
        )
