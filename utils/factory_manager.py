"""
Multi-Factory Support - Factory Management & Equipment Organization
Provides factory selection, filtering, and management capabilities
"""

from datetime import datetime
from typing import Dict, List, Any, Optional
from database.models import Equipment, db
import json
import os

class FactoryManager:
    """Manages multiple factories and factory-based equipment filtering"""
    
    FACTORIES_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database", "factories.json")
    DEFAULT_FACTORIES = [
        {"factory_id": "factory_main", "factory_name": "Main Plant", "location": "New York, USA", "status": "online"},
        {"factory_id": "factory_secondary", "factory_name": "Secondary Plant", "location": "Chicago, USA", "status": "online"},
    ]
    
    _factories_cache = None
    
    @classmethod
    def _load_factories(cls) -> List[Dict[str, Any]]:
        """Load factories from file or return defaults"""
        if cls._factories_cache is not None:
            return cls._factories_cache
        
        if os.path.exists(cls.FACTORIES_FILE):
            try:
                with open(cls.FACTORIES_FILE, 'r') as f:
                    cls._factories_cache = json.load(f)
                    return cls._factories_cache
            except Exception as e:
                print(f"Error loading factories: {e}")
        
        cls._factories_cache = cls.DEFAULT_FACTORIES
        cls._save_factories()
        return cls._factories_cache
    
    @classmethod
    def _save_factories(cls) -> None:
        """Save factories to file"""
        try:
            os.makedirs(os.path.dirname(cls.FACTORIES_FILE), exist_ok=True)
            with open(cls.FACTORIES_FILE, 'w') as f:
                json.dump(cls._factories_cache or cls.DEFAULT_FACTORIES, f, indent=2)
        except Exception as e:
            print(f"Error saving factories: {e}")
    
    @staticmethod
    def get_all_factories() -> List[Dict[str, Any]]:
        """Get all factories"""
        factories = FactoryManager._load_factories()
        return [
            {
                "factory_id": f["factory_id"],
                "factory_name": f["factory_name"],
                "location": f["location"],
                "status": f.get("status", "online"),
                "equipment_count": len(Equipment.find_by_factory(f["factory_id"]))
            }
            for f in factories
        ]
    
    @staticmethod
    def get_factory(factory_id: str) -> Optional[Dict[str, Any]]:
        """Get single factory details"""
        factories = FactoryManager._load_factories()
        factory = next((f for f in factories if f["factory_id"] == factory_id), None)
        
        if factory:
            equipment_count = len(Equipment.find_by_factory(factory_id))
            return {
                "factory_id": factory["factory_id"],
                "factory_name": factory["factory_name"],
                "location": factory["location"],
                "status": factory.get("status", "online"),
                "equipment_count": equipment_count,
                "created_at": factory.get("created_at", datetime.utcnow().isoformat())
            }
        return None
    
    @staticmethod
    def create_factory(factory_name: str, location: str) -> Dict[str, Any]:
        """Create a new factory"""
        factories = FactoryManager._load_factories()
        
        factory_id = f"factory_{len(factories) + 1}"
        factory = {
            "factory_id": factory_id,
            "factory_name": factory_name,
            "location": location,
            "status": "online",
            "created_at": datetime.utcnow().isoformat()
        }
        
        factories.append(factory)
        FactoryManager._factories_cache = factories
        FactoryManager._save_factories()
        
        return factory
    
    @staticmethod
    def get_factory_analytics(factory_id: str) -> Dict[str, Any]:
        """Get analytics for a specific factory"""
        equipment_list = Equipment.find_by_factory(factory_id)
        
        total = len(equipment_list)
        online_count = len([e for e in equipment_list if e.get("status") == "online"])
        warning_count = len([e for e in equipment_list if e.get("status") == "warning"])
        critical_count = len([e for e in equipment_list if e.get("status") == "critical"])
        
        avg_health = sum(e.get("health_score", 0) for e in equipment_list) / total if total > 0 else 0
        
        return {
            "factory_id": factory_id,
            "total_equipment": total,
            "online_equipment": online_count,
            "warning_equipment": warning_count,
            "critical_equipment": critical_count,
            "average_health": round(avg_health, 2),
            "health_percentage": f"{avg_health:.1f}%"
        }


class Equipment:
    """Extended Equipment model with factory support"""
    
    COLLECTION_NAME = "equipment"
    
    @staticmethod
    def get_collection():
        if db is None:
            return None
        return db[Equipment.COLLECTION_NAME]
    
    @staticmethod
    def find_by_factory(factory_id: str) -> List[Dict[str, Any]]:
        """Find all equipment in a factory"""
        from database.models import Equipment as OriginalEquipment, _FALLBACK_EQUIPMENT
        
        try:
            collection = Equipment.get_collection()
            if collection is None:
                return [e for e in _FALLBACK_EQUIPMENT if e.get("factory_id") == factory_id]
            
            return list(collection.find({"factory_id": factory_id}))
        except Exception as e:
            print(f"DB Error (Equipment.find_by_factory): {e}")
            return [e for e in _FALLBACK_EQUIPMENT if e.get("factory_id") == factory_id]
    
    @staticmethod
    def assign_to_factory(equipment_id: str, factory_id: str) -> bool:
        """Assign equipment to a factory"""
        from database.models import Equipment as OriginalEquipment, _FALLBACK_EQUIPMENT
        
        try:
            collection = Equipment.get_collection()
            if collection is None:
                for e in _FALLBACK_EQUIPMENT:
                    if e["equipment_id"] == equipment_id:
                        e["factory_id"] = factory_id
                        e["updated_at"] = datetime.utcnow()
                        from database.models import _persist_fallback_data
                        _persist_fallback_data()
                        return True
            else:
                result = collection.update_one(
                    {"equipment_id": equipment_id},
                    {"$set": {"factory_id": factory_id, "updated_at": datetime.utcnow()}}
                )
                return result.modified_count > 0
        except Exception as e:
            print(f"DB Error (assign_to_factory): {e}")
        
        return False


class FactoryFleetAnalytics:
    """Analytics across multiple factories"""
    
    @staticmethod
    def get_cross_factory_comparison() -> Dict[str, Any]:
        """Compare metrics across all factories"""
        factories = FactoryManager.get_all_factories()
        
        comparison = {
            "total_factories": len(factories),
            "total_equipment": sum(f["equipment_count"] for f in factories),
            "factories": factories,
            "factory_rankings": sorted(factories, key=lambda f: f.get("equipment_count", 0), reverse=True)
        }
        
        return comparison
    
    @staticmethod
    def get_critical_equipment_by_factory() -> List[Dict[str, Any]]:
        """Get critical equipment grouped by factory"""
        critical_by_factory = []
        
        for factory in FactoryManager.get_all_factories():
            equipment_list = Equipment.find_by_factory(factory["factory_id"])
            critical = [e for e in equipment_list if e.get("status") == "critical"]
            
            if critical:
                critical_by_factory.append({
                    "factory_id": factory["factory_id"],
                    "factory_name": factory["factory_name"],
                    "critical_count": len(critical),
                    "critical_equipment": critical[:5]  # Top 5
                })
        
        return sorted(critical_by_factory, key=lambda f: f["critical_count"], reverse=True)
