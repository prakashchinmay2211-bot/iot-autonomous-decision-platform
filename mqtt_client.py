import json
import time
import threading
from collections import deque
from typing import Dict, Any, List, Optional, Callable

try:
    import paho.mqtt.client as mqtt
    PAHO_AVAILABLE = True
except ImportError:
    PAHO_AVAILABLE = False


class MQTTManager:
    """
    Robust MQTT Pub/Sub manager for Autonomous IoT.
    Supports real MQTT brokers (EMQX, Mosquitto, HiveMQ)
    with seamless automatic failover to an internal memory broker
    to guarantee zero downtime on cloud platforms like Streamlit Cloud.
    """
    def __init__(
        self,
        broker: str = "broker.emqx.io",
        port: int = 1883,
        client_id: str = "iot_decision_platform_hub",
        keepalive: int = 60
    ):
        self.broker = broker
        self.port = port
        self.client_id = f"{client_id}_{int(time.time())}"
        self.keepalive = keepalive
        
        self.connected = False
        self.using_internal_broker = False
        self.client: Optional[Any] = None
        
        # Message log / buffers (thread-safe deque)
        self.telemetry_history: deque = deque(maxlen=200)
        self.decision_history: deque = deque(maxlen=100)
        self.alert_history: deque = deque(maxlen=100)
        self.raw_message_log: deque = deque(maxlen=300)
        
        self.callbacks: Dict[str, List[Callable]] = {}
        self.lock = threading.Lock()

    def connect(self, timeout: float = 3.0) -> bool:
        """Attempts connection to external MQTT broker, falls back gracefully."""
        if not PAHO_AVAILABLE:
            self.using_internal_broker = True
            self.connected = True
            return True

        def _on_connect(client, userdata, flags, rc):
            if rc == 0:
                self.connected = True
                self.using_internal_broker = False
                # Subscribe to key IoT topics
                client.subscribe([
                    ("iot/telemetry/+", 0),
                    ("iot/decisions/+", 0),
                    ("iot/alerts/+", 0),
                    ("iot/control/+", 0),
                ])
            else:
                self.connected = False
                self.using_internal_broker = True

        def _on_message(client, userdata, msg):
            try:
                payload_str = msg.payload.decode("utf-8")
                data = json.loads(payload_str)
            except Exception:
                payload_str = str(msg.payload)
                data = {"raw": payload_str}

            self._record_message(msg.topic, data)

        try:
            self.client = mqtt.Client(self.client_id)
            self.client.on_connect = _on_connect
            self.client.on_message = _on_message
            self.client.connect_async(self.broker, self.port, self.keepalive)
            self.client.loop_start()

            # Wait briefly for connection
            start = time.time()
            while time.time() - start < timeout:
                if self.connected:
                    break
                time.sleep(0.1)

            if not self.connected:
                # Fall back to internal memory broker
                self.using_internal_broker = True
                self.connected = True
        except Exception:
            self.using_internal_broker = True
            self.connected = True

        return self.connected

    def _record_message(self, topic: str, data: Dict[str, Any]):
        entry = {
            "timestamp": time.strftime("%H:%M:%S"),
            "topic": topic,
            "data": data
        }
        with self.lock:
            self.raw_message_log.append(entry)
            if "telemetry" in topic:
                self.telemetry_history.append(data)
            elif "decisions" in topic or "actuators" in topic:
                self.decision_history.append(data)
            elif "alerts" in topic:
                self.alert_history.append(data)

    def publish(self, topic: str, payload: Dict[str, Any]) -> bool:
        """Publishes a message to both external MQTT broker and internal event stream."""
        self._record_message(topic, payload)

        if self.client and self.connected and not self.using_internal_broker:
            try:
                json_str = json.dumps(payload)
                self.client.publish(topic, json_str, qos=0)
                return True
            except Exception:
                return False
        return True

    def get_latest_telemetry(self) -> Optional[Dict[str, Any]]:
        with self.lock:
            if self.telemetry_history:
                return self.telemetry_history[-1]
        return None

    def get_telemetry_df(self):
        import pandas as pd
        with self.lock:
            items = list(self.telemetry_history)
        if not items:
            return pd.DataFrame()
        # Flatten if nested
        flattened = []
        for it in items:
            row = {}
            if "telemetry" in it and isinstance(it["telemetry"], dict):
                row.update(it["telemetry"])
            else:
                row.update({k: v for k, v in it.items() if not isinstance(v, (dict, list))})
            if "health_index" in it:
                row["health_index"] = it["health_index"]
            if "ml_anomaly" in it:
                row["ml_anomaly"] = it["ml_anomaly"]
            if "severity" in it:
                row["severity"] = it["severity"]
            flattened.append(row)
        return pd.DataFrame(flattened)

    def disconnect(self):
        if self.client:
            try:
                self.client.loop_stop()
                self.client.disconnect()
            except Exception:
                pass
        self.connected = False
