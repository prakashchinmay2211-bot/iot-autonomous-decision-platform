import time
from typing import Dict, Any, List, Optional
from collections import deque

try:
    import pymongo
    MONGO_LIB_AVAILABLE = True
except ImportError:
    MONGO_LIB_AVAILABLE = False


class MongoStorageManager:
    """
    Manages persistence across the five SRS collections:
    1. telemetry
    2. anomalies
    3. decisions
    4. alerts
    5. device_states

    Connects to MongoDB (port 27017, database: aiot_platform).
    Gracefully falls back to high-speed in-memory collections when running
    in cloud environments (Streamlit Cloud) without breaking queries.
    """
    def __init__(self, host: str = "localhost", port: int = 27017, db_name: str = "aiot_platform"):
        self.host = host
        self.port = port
        self.db_name = db_name
        self.connected_to_real_mongo = False
        self.client = None
        self.db = None

        # Fallback memory collections
        self.collections: Dict[str, deque] = {
            "telemetry": deque(maxlen=500),
            "anomalies": deque(maxlen=200),
            "decisions": deque(maxlen=200),
            "alerts": deque(maxlen=200),
            "device_states": deque(maxlen=50)
        }
        self.attempt_mongo_connection()

    def attempt_mongo_connection(self):
        if not MONGO_LIB_AVAILABLE:
            self.connected_to_real_mongo = False
            return

        try:
            self.client = pymongo.MongoClient(self.host, self.port, serverSelectionTimeoutMS=800)
            self.client.server_info()
            self.db = self.client[self.db_name]
            self.connected_to_real_mongo = True
        except Exception:
            self.connected_to_real_mongo = False

    def insert(self, collection_name: str, document: Dict[str, Any]):
        doc_copy = dict(document)
        if "timestamp" not in doc_copy:
            doc_copy["timestamp"] = time.time()

        # Always store in memory buffer for instant UI access
        if collection_name in self.collections:
            self.collections[collection_name].append(doc_copy)

        # Store in real MongoDB if available
        if self.connected_to_real_mongo and self.db is not None:
            try:
                self.db[collection_name].insert_one(doc_copy)
            except Exception:
                pass

    def get_latest(self, collection_name: str, device_id: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        if collection_name not in self.collections:
            return []
        
        items = list(self.collections[collection_name])
        if device_id:
            items = [it for it in items if it.get("device_id") == device_id]
        
        return items[-limit:][::-1]

    def get_status(self) -> Dict[str, Any]:
        return {
            "status": "ONLINE" if self.connected_to_real_mongo else "SIMULATED_MEMORY_STORE",
            "database": self.db_name,
            "connected_to_mongodb_daemon": self.connected_to_real_mongo,
            "collection_counts": {
                name: len(buf) for name, buf in self.collections.items()
            }
        }
