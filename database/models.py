"""
Database models for AI Equipment Failure Prediction System.
Defines MongoDB collections for users, equipment, predictions, and alerts.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pymongo import MongoClient
import os
import uuid
import traceback
import json
from dotenv import load_dotenv

load_dotenv()

# MongoDB Connection
MONGO_URI = (
    os.getenv("MONGODB_URI")
    or os.getenv("MONGO_URI")
    or os.getenv("MONGODB_ATLAS_URI")
    or "mongodb://localhost:27017"
)

DB_NAME = os.getenv("MONGODB_DB_NAME", "equipment_failure_db")


def _connect_to_mongo(uri: str):
    return MongoClient(
        uri,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
        tlsAllowInvalidCertificates=True,
    )


db = None
connection_error = None

for candidate_uri, label in ((MONGO_URI, "configured"), ("mongodb://localhost:27017", "local fallback")):
    try:
        client = _connect_to_mongo(candidate_uri)
        client.admin.command("ping")
        db = client[DB_NAME]
        if label == "configured":
            print("MongoDB Connected")
        else:
            print("MongoDB Connected via local fallback")
        break
    except Exception as exc:
        connection_error = exc
        db = None

if db is None:
    pass


_FALLBACK_USERS: List[Dict[str, Any]] = []
_FALLBACK_EQUIPMENT: List[Dict[str, Any]] = []
_FALLBACK_PREDICTIONS: List[Dict[str, Any]] = []
_FALLBACK_ALERTS: List[Dict[str, Any]] = []

_FALLBACK_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database")
_FALLBACK_FILE = os.path.join(_FALLBACK_DIR, "fallback_data.json")


def _json_default(value):
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _persist_fallback_data() -> None:
    if db is not None:
        return

    try:
        os.makedirs(_FALLBACK_DIR, exist_ok=True)
        payload = {
            "users": _FALLBACK_USERS,
            "equipment": _FALLBACK_EQUIPMENT,
            "predictions": _FALLBACK_PREDICTIONS,
            "alerts": _FALLBACK_ALERTS,
        }
        with open(_FALLBACK_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=True, indent=2, default=_json_default)
    except Exception as e:
        print(f"Fallback persistence error: {e}")


def _load_fallback_data() -> None:
    if not os.path.exists(_FALLBACK_FILE):
        return

    try:
        with open(_FALLBACK_FILE, "r", encoding="utf-8") as f:
            payload = json.load(f)

        _FALLBACK_USERS[:] = payload.get("users", [])
        _FALLBACK_EQUIPMENT[:] = payload.get("equipment", [])
        _FALLBACK_PREDICTIONS[:] = payload.get("predictions", [])
        _FALLBACK_ALERTS[:] = payload.get("alerts", [])
    except Exception as e:
        print(f"Fallback load error: {e}")


_load_fallback_data()


def _seed_fallback_equipment() -> None:
    pass  # Fallback seeding disabled to ensure only real user data is displayed


class User:
    """User model for managing system users."""
    
    COLLECTION_NAME = "users"
    
    @staticmethod
    def get_collection():
        if db is None:
            return None
        return db[User.COLLECTION_NAME]
    
    @staticmethod
    def create_user(username: str, email: str, password_hash: str, role: str = "operator"):
        """Create a new user document."""
        try:
            user_doc = {
                "username": username,
                "email": email,
                "password_hash": password_hash,
                "role": role,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "is_active": True,
            }
            collection = User.get_collection()
            if collection is None:
                user_doc["_id"] = str(uuid.uuid4())
                _FALLBACK_USERS.append(user_doc)
                _persist_fallback_data()
                return user_doc["_id"]
            
            result = collection.insert_one(user_doc)
            return str(result.inserted_id)
        except Exception as e:
            print(f"DB Error (User.create_user): {e}")
            return str(uuid.uuid4())
    
    @staticmethod
    def find_by_username(username: str) -> Optional[Dict[str, Any]]:
        """Find user by username."""
        try:
            collection = User.get_collection()
            if collection is None:
                return next((user for user in _FALLBACK_USERS if user.get("username") == username), None)
            return collection.find_one({"username": username})
        except Exception as e:
            print(f"DB Error (User.find_by_username): {e}")
            return next((user for user in _FALLBACK_USERS if user.get("username") == username), None)
    
    @staticmethod
    def find_by_email(email: str) -> Optional[Dict[str, Any]]:
        """Find user by email."""
        try:
            collection = User.get_collection()
            if collection is None:
                return next((user for user in _FALLBACK_USERS if user.get("email") == email), None)
            return collection.find_one({"email": email})
        except Exception as e:
            print(f"DB Error (User.find_by_email): {e}")
            return next((user for user in _FALLBACK_USERS if user.get("email") == email), None)
    
    @staticmethod
    def find_by_id(user_id: str) -> Optional[Dict[str, Any]]:
        """Find user by ID."""
        try:
            from bson.objectid import ObjectId
            collection = User.get_collection()
            if collection is None:
                return next((user for user in _FALLBACK_USERS if user.get("_id") == user_id), None)
            try:
                return collection.find_one({"_id": ObjectId(user_id)})
            except:
                return next((user for user in _FALLBACK_USERS if user.get("_id") == user_id), None)
        except Exception as e:
            print(f"DB Error (User.find_by_id): {e}")
            return None

    @staticmethod
    def find_all() -> List[Dict[str, Any]]:
        """Return all users."""
        try:
            collection = User.get_collection()
            if collection is None:
                return list(_FALLBACK_USERS)
            return list(collection.find())
        except Exception as e:
            print(f"DB Error (User.find_all): {e}")
            return list(_FALLBACK_USERS)


class Equipment:
    """Equipment model for managing industrial machines."""
    
    COLLECTION_NAME = "equipment"
    
    @staticmethod
    def get_collection():
        if db is None:
            return None
        return db[Equipment.COLLECTION_NAME]
    
    @staticmethod
    def create_equipment(equipment_id: str, equipment_name: str, location: str, equipment_type: str):
        """Create a new equipment document."""
        try:
            equipment_doc = {
                "equipment_id": equipment_id,
                "equipment_name": equipment_name,
                "location": location,
                "equipment_type": equipment_type,
                "status": "online",
                "health_score": 100.0,
                "last_maintenance": datetime.utcnow(),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
            collection = Equipment.get_collection()
            if collection is None:
                equipment_doc["_id"] = str(uuid.uuid4())
                _FALLBACK_EQUIPMENT.append(equipment_doc)
                _persist_fallback_data()
                return equipment_doc["_id"]
            
            result = collection.insert_one(equipment_doc)
            return str(result.inserted_id)
        except Exception as e:
            print(f"DB Error (Equipment.create_equipment): {e}")
            equipment_doc["_id"] = str(uuid.uuid4())
            _FALLBACK_EQUIPMENT.append(equipment_doc)
            _persist_fallback_data()
            return equipment_doc["_id"]
    
    @staticmethod
    def find_all() -> List[Dict[str, Any]]:
        """Get all equipment."""
        try:
            collection = Equipment.get_collection()
            if collection is None:
                return list(_FALLBACK_EQUIPMENT)
            return list(collection.find())
        except Exception as e:
            print(f"DB Error (Equipment.find_all): {e}")
            return list(_FALLBACK_EQUIPMENT)
    
    @staticmethod
    def find_by_id(equipment_id: str) -> Optional[Dict[str, Any]]:
        """Find equipment by ID."""
        try:
            collection = Equipment.get_collection()
            if collection is None:
                return next((e for e in _FALLBACK_EQUIPMENT if e["equipment_id"] == equipment_id), None)
            return collection.find_one({"equipment_id": equipment_id})
        except Exception as e:
            print(f"DB Error (Equipment.find_by_id): {e}")
            return next((e for e in _FALLBACK_EQUIPMENT if e["equipment_id"] == equipment_id), None)

    @staticmethod
    def update_status(equipment_id: str, status: str, health_score: float):
        """Update equipment status and health score."""
        try:
            collection = Equipment.get_collection()
            if collection is None:
                for e in _FALLBACK_EQUIPMENT:
                    if e["equipment_id"] == equipment_id:
                        e["status"] = status
                        e["health_score"] = health_score
                        e["updated_at"] = datetime.utcnow()
                        _persist_fallback_data()
                return True
            result = collection.update_one(
                {"equipment_id": equipment_id},
                {"$set": {"status": status, "health_score": health_score, "updated_at": datetime.utcnow()}}
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"DB Error (Equipment.update_status): {e}")
            return False

    @staticmethod
    def delete_by_equipment_id(equipment_id: str) -> bool:
        """Delete one equipment by equipment_id."""
        try:
            collection = Equipment.get_collection()
            if collection is None:
                before = len(_FALLBACK_EQUIPMENT)
                _FALLBACK_EQUIPMENT[:] = [e for e in _FALLBACK_EQUIPMENT if e.get("equipment_id") != equipment_id]
                changed = len(_FALLBACK_EQUIPMENT) < before
                if changed:
                    _persist_fallback_data()
                return changed

            result = collection.delete_one({"equipment_id": equipment_id})
            return result.deleted_count > 0
        except Exception as e:
            print(f"DB Error (Equipment.delete_by_equipment_id): {e}")
            return False

    @staticmethod
    def delete_all() -> int:
        """Delete all equipment records and return count."""
        try:
            collection = Equipment.get_collection()
            if collection is None:
                count = len(_FALLBACK_EQUIPMENT)
                _FALLBACK_EQUIPMENT.clear()
                _persist_fallback_data()
                return count

            result = collection.delete_many({})
            return int(result.deleted_count)
        except Exception as e:
            print(f"DB Error (Equipment.delete_all): {e}")
            return 0


class Prediction:
    """Prediction model for storing ML predictions."""
    
    COLLECTION_NAME = "predictions"
    
    @staticmethod
    def get_collection():
        if db is None:
            return None
        return db[Prediction.COLLECTION_NAME]
    
    @staticmethod
    def store_prediction(
        equipment_id: str,
        sensor_values: Dict[str, float],
        prediction: int,
        probability: float,
        risk_level: str,
        health_score: Optional[float] = None,
        health_status: Optional[str] = None,
        equipment_status: Optional[str] = None,
    ):
        """Store a prediction record."""
        try:
            prediction_doc = {
                "equipment_id": equipment_id,
                "temperature": sensor_values.get("Temperature"),
                "vibration": sensor_values.get("Vibration"),
                "pressure": sensor_values.get("Pressure"),
                "humidity": sensor_values.get("Humidity"),
                "runtime_hours": sensor_values.get("Runtime Hours"),
                "prediction": prediction,
                "prediction_text": "Equipment Failure Predicted" if prediction == 1 else "Equipment Working Normally",
                "probability": probability,
                "risk_level": risk_level,
                "timestamp": datetime.utcnow(),
            }
            if health_score is not None:
                prediction_doc["health_score"] = health_score
            if health_status is not None:
                prediction_doc["health_status"] = health_status
            if equipment_status is not None:
                prediction_doc["equipment_status"] = equipment_status
            collection = Prediction.get_collection()
            if collection is None:
                prediction_doc["_id"] = str(uuid.uuid4())
                _FALLBACK_PREDICTIONS.insert(0, prediction_doc)
                _persist_fallback_data()
                return prediction_doc["_id"]
            
            result = collection.insert_one(prediction_doc)
            return str(result.inserted_id)
        except Exception as e:
            print(f"DB Error (Prediction.store_prediction): {e}")
            prediction_doc["_id"] = str(uuid.uuid4())
            _FALLBACK_PREDICTIONS.insert(0, prediction_doc)
            _persist_fallback_data()
            return prediction_doc["_id"]
    
    @staticmethod
    def get_equipment_history(equipment_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get prediction history for an equipment."""
        try:
            collection = Prediction.get_collection()
            if collection is None:
                return sorted(
                    [p for p in _FALLBACK_PREDICTIONS if p.get("equipment_id") == equipment_id],
                    key=lambda x: x.get("timestamp", datetime.utcnow()),
                    reverse=True
                )[:limit]
            return list(collection.find({"equipment_id": equipment_id}).sort("timestamp", -1).limit(limit))
        except Exception as e:
            print(f"DB Error (Prediction.get_equipment_history): {e}")
            return []
    
    @staticmethod
    def get_recent_predictions(limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent predictions."""
        try:
            collection = Prediction.get_collection()
            if collection is None:
                return list(_FALLBACK_PREDICTIONS)[:limit]
            return list(collection.find().sort("timestamp", -1).limit(limit))
        except Exception as e:
            print(f"DB Error (Prediction.get_recent_predictions): {e}")
            return list(_FALLBACK_PREDICTIONS)[:limit]

    @staticmethod
    def get_latest_by_equipment() -> Dict[str, Dict[str, Any]]:
        """Return the latest prediction for each equipment_id."""
        try:
            latest: Dict[str, Dict[str, Any]] = {}
            for item in Prediction.get_recent_predictions(limit=5000):
                equipment_id = item.get("equipment_id")
                if not equipment_id or equipment_id in latest:
                    continue
                latest[equipment_id] = item
            return latest
        except Exception as e:
            print(f"DB Error (Prediction.get_latest_by_equipment): {e}")
            return {}

    @staticmethod
    def delete_by_equipment_id(equipment_id: str) -> int:
        """Delete predictions for a single equipment."""
        try:
            collection = Prediction.get_collection()
            if collection is None:
                before = len(_FALLBACK_PREDICTIONS)
                _FALLBACK_PREDICTIONS[:] = [
                    p for p in _FALLBACK_PREDICTIONS if p.get("equipment_id") != equipment_id
                ]
                removed = before - len(_FALLBACK_PREDICTIONS)
                if removed > 0:
                    _persist_fallback_data()
                return removed

            result = collection.delete_many({"equipment_id": equipment_id})
            return int(result.deleted_count)
        except Exception as e:
            print(f"DB Error (Prediction.delete_by_equipment_id): {e}")
            return 0

    @staticmethod
    def delete_all() -> int:
        """Delete all predictions."""
        try:
            collection = Prediction.get_collection()
            if collection is None:
                count = len(_FALLBACK_PREDICTIONS)
                _FALLBACK_PREDICTIONS.clear()
                _persist_fallback_data()
                return count

            result = collection.delete_many({})
            return int(result.deleted_count)
        except Exception as e:
            print(f"DB Error (Prediction.delete_all): {e}")
            return 0


class Alert:
    """Alert model for managing system alerts."""
    
    COLLECTION_NAME = "alerts"
    
    @staticmethod
    def get_collection():
        if db is None:
            return None
        return db[Alert.COLLECTION_NAME]
    
    @staticmethod
    def create_alert(
        equipment_id: str,
        alert_type: str,
        severity: str,
        message: str,
        recommendations: str = "",
    ):
        """Create a new alert."""
        try:
            alert_doc = {
                "equipment_id": equipment_id,
                "alert_type": alert_type,
                "severity": severity,
                "message": message,
                "recommendations": recommendations,
                "is_resolved": False,
                "created_at": datetime.utcnow(),
                "resolved_at": None,
            }
            collection = Alert.get_collection()
            if collection is None:
                alert_doc["_id"] = str(uuid.uuid4())
                _FALLBACK_ALERTS.insert(0, alert_doc)
                _persist_fallback_data()
                return alert_doc["_id"]
            
            result = collection.insert_one(alert_doc)
            return str(result.inserted_id)
        except Exception as e:
            print(f"DB Error (Alert.create_alert): {e}")
            return str(uuid.uuid4())
    
    @staticmethod
    def get_active_alerts() -> List[Dict[str, Any]]:
        """Get all active (unresolved) alerts."""
        try:
            collection = Alert.get_collection()
            if collection is None:
                return [a for a in _FALLBACK_ALERTS if not a.get("is_resolved")]
            return list(collection.find({"is_resolved": False}).sort("created_at", -1))
        except Exception as e:
            print(f"DB Error (Alert.get_active_alerts): {e}")
            return [a for a in _FALLBACK_ALERTS if not a.get("is_resolved")]
    
    @staticmethod
    def resolve_alert(alert_id: str):
        """Mark an alert as resolved."""
        try:
            from bson.objectid import ObjectId
            collection = Alert.get_collection()
            if collection is None:
                for alert in _FALLBACK_ALERTS:
                    if alert.get("_id") == alert_id:
                        alert["is_resolved"] = True
                        alert["resolved_at"] = datetime.utcnow()
                        _persist_fallback_data()
                        return True
                return False
            result = collection.update_one(
                {"_id": ObjectId(alert_id)},
                {"$set": {"is_resolved": True, "resolved_at": datetime.utcnow()}}
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"DB Error (Alert.resolve_alert): {e}")
            return False

    @staticmethod
    def delete_by_equipment_id(equipment_id: str) -> int:
        """Delete alerts for one equipment."""
        try:
            collection = Alert.get_collection()
            if collection is None:
                before = len(_FALLBACK_ALERTS)
                _FALLBACK_ALERTS[:] = [a for a in _FALLBACK_ALERTS if a.get("equipment_id") != equipment_id]
                removed = before - len(_FALLBACK_ALERTS)
                if removed > 0:
                    _persist_fallback_data()
                return removed

            result = collection.delete_many({"equipment_id": equipment_id})
            return int(result.deleted_count)
        except Exception as e:
            print(f"DB Error (Alert.delete_by_equipment_id): {e}")
            return 0

    @staticmethod
    def delete_all() -> int:
        """Delete all alerts."""
        try:
            collection = Alert.get_collection()
            if collection is None:
                count = len(_FALLBACK_ALERTS)
                _FALLBACK_ALERTS.clear()
                _persist_fallback_data()
                return count

            result = collection.delete_many({})
            return int(result.deleted_count)
        except Exception as e:
            print(f"DB Error (Alert.delete_all): {e}")
            return 0


class MaintenanceSchedule:
    """Maintenance schedule model."""
    
    COLLECTION_NAME = "maintenance_schedules"
    
    @staticmethod
    def get_collection():
        if db is None:
            return None
        return db[MaintenanceSchedule.COLLECTION_NAME]
    
    @staticmethod
    def create_schedule(
        equipment_id: str,
        scheduled_date: datetime,
        maintenance_type: str,
        estimated_duration: int,
        priority: str = "Normal",
    ):
        """Create a maintenance schedule."""
        try:
            schedule_doc = {
                "equipment_id": equipment_id,
                "scheduled_date": scheduled_date,
                "maintenance_type": maintenance_type,
                "estimated_duration": estimated_duration,
                "priority": priority,
                "status": "scheduled",
                "created_at": datetime.utcnow(),
            }
            collection = MaintenanceSchedule.get_collection()
            if collection is None:
                return str(uuid.uuid4())
            result = collection.insert_one(schedule_doc)
            return str(result.inserted_id)
        except Exception as e:
            print(f"DB Error (MaintenanceSchedule.create_schedule): {e}")
            return str(uuid.uuid4())
    
    @staticmethod
    def get_upcoming_schedules(days_ahead: int = 30) -> List[Dict[str, Any]]:
        """Get upcoming maintenance schedules."""
        try:
            from datetime import timedelta
            collection = MaintenanceSchedule.get_collection()
            if collection is None:
                return []
            
            now = datetime.utcnow()
            future_date = now + timedelta(days=days_ahead)
            
            return list(
                collection.find({
                    "scheduled_date": {"$gte": now, "$lte": future_date},
                    "status": "scheduled",
                }).sort("scheduled_date", 1)
            )
        except Exception as e:
            print(f"DB Error (MaintenanceSchedule.get_upcoming_schedules): {e}")
            return []


# Initialize collections with indexes
def init_db():
    """Initialize database with proper indexes."""
    if db is None:
        return
    
    try:
        # Users collection indexes
        db[User.COLLECTION_NAME].create_index("username", unique=True)
        db[User.COLLECTION_NAME].create_index("email", unique=True)
        
        # Equipment collection indexes
        db[Equipment.COLLECTION_NAME].create_index("equipment_id", unique=True)
        
        # Predictions collection indexes
        db[Prediction.COLLECTION_NAME].create_index("equipment_id")
        db[Prediction.COLLECTION_NAME].create_index("timestamp")
        
        # Alerts collection indexes
        db[Alert.COLLECTION_NAME].create_index("equipment_id")
        db[Alert.COLLECTION_NAME].create_index("created_at")
        
        # Maintenance schedules indexes
        db[MaintenanceSchedule.COLLECTION_NAME].create_index("equipment_id")
        db[MaintenanceSchedule.COLLECTION_NAME].create_index("scheduled_date")
        
        print("Database indexes created successfully")
    except Exception as e:
        print("Error creating indexes:", e)
