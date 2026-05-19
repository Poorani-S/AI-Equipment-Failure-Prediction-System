"""Equipment Comparison - Side-by-side equipment analysis."""

from typing import Dict, List, Any
from database.models import Equipment, Prediction
from utils.ai_intelligence import build_equipment_intelligence


class EquipmentComparison:
    """Compare multiple equipment side-by-side."""

    @staticmethod
    def compare_equipment(equipment_ids: List[str]) -> Dict[str, Any]:
        """Compare multiple equipment by ID."""
        if len(equipment_ids) < 2:
            return {"error": "Need at least 2 equipment to compare"}

        equipment_ids = equipment_ids[:5]  # Limit to 5
        comparison_data = []

        for eq_id in equipment_ids:
            try:
                intel = build_equipment_intelligence(eq_id)
                comparison_data.append({
                    "equipment_id": eq_id,
                    "equipment_name": intel.get("equipment_name", eq_id),
                    "equipment_type": intel.get("equipment_type"),
                    "location": intel.get("location"),
                    "health_score": intel.get("health_score", 0),
                    "health_status": intel.get("health_status"),
                    "status": intel.get("equipment_status"),
                    "risk_level": intel.get("risk_level"),
                    "failure_probability": intel.get("confidence", 0),
                    "temperature": intel.get("sensor_contributions", [{}])[0].get("value", 0) if intel.get("sensor_contributions") else 0,
                    "vibration": next((s.get("value", 0) for s in intel.get("sensor_contributions", []) if "vibration" in s.get("sensor", "").lower()), 0),
                    "pressure": next((s.get("value", 0) for s in intel.get("sensor_contributions", []) if "pressure" in s.get("sensor", "").lower()), 0),
                    "prediction_text": intel.get("prediction_text"),
                    "maintenance_urgency": intel.get("maintenance", {}).get("urgency", "Low"),
                    "forecast_24h": intel.get("forecast", {}).get("failure_24h", 0),
                    "forecast_7d": intel.get("forecast", {}).get("failure_7d", 0),
                })
            except Exception as e:
                print(f"Error comparing equipment {eq_id}: {e}")
                continue

        if not comparison_data:
            return {"error": "Could not load equipment for comparison"}

        # Calculate metrics
        metrics = EquipmentComparison._calculate_comparison_metrics(comparison_data)

        return {
            "success": True,
            "equipment_count": len(comparison_data),
            "data": comparison_data,
            "metrics": metrics,
        }

    @staticmethod
    def _calculate_comparison_metrics(equipment_list: List[Dict]) -> Dict[str, Any]:
        """Calculate comparison metrics."""
        metrics = {}

        # Health scores
        health_scores = [eq["health_score"] for eq in equipment_list]
        metrics["avg_health"] = sum(health_scores) / len(health_scores) if health_scores else 0
        metrics["best_health"] = max(health_scores) if health_scores else 0
        metrics["worst_health"] = min(health_scores) if health_scores else 0

        # Failure probabilities
        probs = [eq["failure_probability"] for eq in equipment_list]
        metrics["avg_failure_prob"] = sum(probs) / len(probs) if probs else 0
        metrics["highest_risk"] = max(probs) if probs else 0

        # Risk distribution
        risk_counts = {}
        for eq in equipment_list:
            risk = eq["risk_level"]
            risk_counts[risk] = risk_counts.get(risk, 0) + 1
        metrics["risk_distribution"] = risk_counts

        # Maintenance urgency counts
        urgency_counts = {}
        for eq in equipment_list:
            urgency = eq["maintenance_urgency"]
            urgency_counts[urgency] = urgency_counts.get(urgency, 0) + 1
        metrics["urgency_distribution"] = urgency_counts

        return metrics

    @staticmethod
    def get_comparison_recommendations(equipment_list: List[Dict]) -> List[str]:
        """Get recommendations based on comparison."""
        recommendations = []

        health_scores = [eq["health_score"] for eq in equipment_list]
        worst_eq = min(equipment_list, key=lambda x: x["health_score"])
        best_eq = max(equipment_list, key=lambda x: x["health_score"])

        # Health gap
        if max(health_scores) - min(health_scores) > 30:
            recommendations.append(f"Large health gap detected: {best_eq['equipment_name']} ({best_eq['health_score']}%) vs {worst_eq['equipment_name']} ({worst_eq['health_score']}%)")

        # Critical equipment
        critical = [eq for eq in equipment_list if eq["risk_level"] == "Critical"]
        if critical:
            recommendations.append(f"{len(critical)} critical equipment needs immediate attention")

        # Maintenance backlog
        urgent_maintenance = [eq for eq in equipment_list if eq["maintenance_urgency"] in ["Urgent", "High"]]
        if urgent_maintenance:
            recommendations.append(f"{len(urgent_maintenance)} equipment require urgent maintenance scheduling")

        # Similar issues
        equipment_types = {}
        for eq in equipment_list:
            eq_type = eq.get("equipment_type", "Unknown")
            equipment_types.setdefault(eq_type, []).append(eq)

        for eq_type, eqs in equipment_types.items():
            if len(eqs) > 1 and all(eq["risk_level"] in ["Medium", "Critical"] for eq in eqs):
                recommendations.append(f"All {eq_type} equipment showing elevated risk - consider fleet-wide inspection")

        return recommendations[:5]  # Return top 5 recommendations
