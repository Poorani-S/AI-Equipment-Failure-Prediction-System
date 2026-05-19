"""Advanced Search & Filtering - Complex search across equipment and predictions."""

from typing import Dict, List, Any
from datetime import datetime, timedelta
from database.models import Equipment, Prediction, Alert
import re


class AdvancedSearch:
    """Advanced search and filtering for equipment and predictions."""

    @staticmethod
    def search_equipment(
        query: str = "",
        filters: Dict[str, Any] = None,
        limit: int = 50
    ) -> Dict[str, Any]:
        """Search and filter equipment with advanced criteria."""
        filters = filters or {}
        equipment_list = Equipment.find_all()

        # Text search
        if query:
            query_lower = query.lower()
            equipment_list = [
                eq for eq in equipment_list
                if query_lower in eq.get("equipment_id", "").lower()
                or query_lower in eq.get("equipment_name", "").lower()
                or query_lower in eq.get("location", "").lower()
                or query_lower in eq.get("equipment_type", "").lower()
            ]

        # Status filter
        if "status" in filters and filters["status"]:
            equipment_list = [eq for eq in equipment_list if eq.get("status") in filters["status"]]

        # Risk level filter
        if "risk_levels" in filters and filters["risk_levels"]:
            equipment_list = [
                eq for eq in equipment_list
                if AdvancedSearch._get_equipment_risk_level(eq.get("equipment_id")) in filters["risk_levels"]
            ]

        # Health score range
        if "health_score_min" in filters or "health_score_max" in filters:
            min_health = filters.get("health_score_min", 0)
            max_health = filters.get("health_score_max", 100)
            equipment_list = [
                eq for eq in equipment_list
                if min_health <= float(eq.get("health_score", 0) or 0) <= max_health
            ]

        # Equipment type filter
        if "equipment_types" in filters and filters["equipment_types"]:
            equipment_list = [eq for eq in equipment_list if eq.get("equipment_type") in filters["equipment_types"]]

        # Location filter
        if "locations" in filters and filters["locations"]:
            equipment_list = [eq for eq in equipment_list if eq.get("location") in filters["locations"]]

        # Date range filter
        if "created_after" in filters or "created_before" in filters:
            created_after = filters.get("created_after")
            created_before = filters.get("created_before")
            equipment_list = AdvancedSearch._filter_by_date(equipment_list, created_after, created_before)

        # Sort
        sort_by = filters.get("sort_by", "health_score")
        sort_order = filters.get("sort_order", "desc")
        equipment_list = AdvancedSearch._sort_results(equipment_list, sort_by, sort_order)

        # Limit results
        total_results = len(equipment_list)
        equipment_list = equipment_list[:limit]

        return {
            "success": True,
            "query": query,
            "total_results": total_results,
            "returned_results": len(equipment_list),
            "filters_applied": filters,
            "data": equipment_list,
        }

    @staticmethod
    def search_predictions(
        equipment_id: str = "",
        filters: Dict[str, Any] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Search prediction history with advanced filters."""
        filters = filters or {}

        if equipment_id:
            predictions = Prediction.get_equipment_history(equipment_id, limit=limit * 2)
        else:
            predictions = Prediction.get_recent_predictions(limit=limit * 2)

        # Risk level filter
        if "risk_levels" in filters and filters["risk_levels"]:
            predictions = [p for p in predictions if p.get("risk_level") in filters["risk_levels"]]

        # Prediction type filter
        if "prediction_type" in filters and filters["prediction_type"]:
            pred_type = filters["prediction_type"]
            if pred_type == "failure":
                predictions = [p for p in predictions if p.get("prediction") == 1]
            elif pred_type == "normal":
                predictions = [p for p in predictions if p.get("prediction") == 0]

        # Probability threshold
        if "min_probability" in filters:
            min_prob = filters["min_probability"]
            predictions = [
                p for p in predictions
                if float(p.get("probability", p.get("failure_probability", 0)) or 0) >= min_prob
            ]

        # Date range
        if "date_after" in filters or "date_before" in filters:
            predictions = AdvancedSearch._filter_predictions_by_date(
                predictions,
                filters.get("date_after"),
                filters.get("date_before")
            )

        # Sort
        sort_by = filters.get("sort_by", "timestamp")
        sort_order = filters.get("sort_order", "desc")
        predictions = AdvancedSearch._sort_predictions(predictions, sort_by, sort_order)

        total = len(predictions)
        predictions = predictions[:limit]

        return {
            "success": True,
            "equipment_id": equipment_id,
            "total_results": total,
            "returned_results": len(predictions),
            "data": predictions,
        }

    @staticmethod
    def advanced_filter(
        equipment_list: List[Dict],
        criteria: Dict[str, Any]
    ) -> List[Dict]:
        """Apply advanced filtering with multiple criteria."""
        results = equipment_list

        # Health-based filtering
        if "health_critical" in criteria and criteria["health_critical"]:
            results = [eq for eq in results if float(eq.get("health_score", 0) or 0) < 40]

        if "health_warning" in criteria and criteria["health_warning"]:
            results = [eq for eq in results if 40 <= float(eq.get("health_score", 0) or 0) < 70]

        # Performance clustering
        if "performance_group" in criteria:
            group = criteria["performance_group"]
            if group == "top_performers":
                results = sorted(results, key=lambda x: float(x.get("health_score", 0) or 0), reverse=True)[:10]
            elif group == "at_risk":
                results = [eq for eq in results if float(eq.get("health_score", 0) or 0) < 60]
            elif group == "degrading":
                results = [eq for eq in results if 40 <= float(eq.get("health_score", 0) or 0) <= 70]

        # Maintenance grouping
        if "maintenance_status" in criteria:
            status = criteria["maintenance_status"]
            if status == "urgent":
                results = [
                    eq for eq in results
                    if AdvancedSearch._get_equipment_risk_level(eq.get("equipment_id")) in ["High", "Critical"]
                ]
            elif status == "scheduled":
                results = [
                    eq for eq in results
                    if AdvancedSearch._get_equipment_risk_level(eq.get("equipment_id")) == "Medium"
                ]

        return results

    @staticmethod
    def _get_equipment_risk_level(equipment_id: str) -> str:
        """Get risk level for equipment."""
        history = Prediction.get_equipment_history(equipment_id, limit=1)
        if history:
            return history[0].get("risk_level", "Low")
        return "Low"

    @staticmethod
    def _sort_results(equipment: List[Dict], sort_by: str, sort_order: str = "desc") -> List[Dict]:
        """Sort equipment by various criteria."""
        reverse = sort_order.lower() == "desc"

        if sort_by == "health_score":
            return sorted(equipment, key=lambda x: float(x.get("health_score", 0) or 0), reverse=reverse)
        elif sort_by == "name":
            return sorted(equipment, key=lambda x: x.get("equipment_name", ""), reverse=reverse)
        elif sort_by == "type":
            return sorted(equipment, key=lambda x: x.get("equipment_type", ""), reverse=reverse)
        elif sort_by == "location":
            return sorted(equipment, key=lambda x: x.get("location", ""), reverse=reverse)
        elif sort_by == "updated":
            return sorted(equipment, key=lambda x: str(x.get("updated_at", "")), reverse=reverse)
        else:
            return equipment

    @staticmethod
    def _sort_predictions(predictions: List[Dict], sort_by: str, sort_order: str = "desc") -> List[Dict]:
        """Sort predictions by criteria."""
        reverse = sort_order.lower() == "desc"

        if sort_by == "probability":
            return sorted(
                predictions,
                key=lambda x: float(x.get("probability", x.get("failure_probability", 0)) or 0),
                reverse=reverse
            )
        elif sort_by == "health_score":
            return sorted(
                predictions,
                key=lambda x: float(x.get("health_score", 0) or 0),
                reverse=reverse
            )
        else:  # timestamp (default)
            return sorted(
                predictions,
                key=lambda x: str(x.get("timestamp", "")),
                reverse=reverse
            )

    @staticmethod
    def _filter_by_date(equipment: List[Dict], after: str = None, before: str = None) -> List[Dict]:
        """Filter equipment by creation date."""
        if not after and not before:
            return equipment

        try:
            after_dt = datetime.fromisoformat(after) if after else datetime.min
            before_dt = datetime.fromisoformat(before) if before else datetime.max

            return [
                eq for eq in equipment
                if after_dt <= eq.get("created_at", datetime.min) <= before_dt
            ]
        except:
            return equipment

    @staticmethod
    def _filter_predictions_by_date(
        predictions: List[Dict],
        after: str = None,
        before: str = None
    ) -> List[Dict]:
        """Filter predictions by date range."""
        if not after and not before:
            return predictions

        try:
            after_dt = datetime.fromisoformat(after) if after else datetime.min
            before_dt = datetime.fromisoformat(before) if before else datetime.max

            return [
                p for p in predictions
                if after_dt <= p.get("timestamp", datetime.min) <= before_dt
            ]
        except:
            return predictions

    @staticmethod
    def get_available_filters() -> Dict[str, Any]:
        """Get available filter options."""
        equipment = Equipment.find_all()
        predictions = Prediction.get_recent_predictions(limit=100)

        return {
            "statuses": list(set(eq.get("status", "online") for eq in equipment)),
            "equipment_types": list(set(eq.get("equipment_type", "Unknown") for eq in equipment)),
            "locations": list(set(eq.get("location", "Unknown") for eq in equipment)),
            "risk_levels": ["Low", "Medium", "High", "Critical"],
            "prediction_types": ["failure", "normal"],
            "health_score_ranges": [
                {"min": 0, "max": 40, "label": "Critical"},
                {"min": 40, "max": 70, "label": "Warning"},
                {"min": 70, "max": 100, "label": "Healthy"},
            ],
        }
