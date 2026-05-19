"""Downtime Cost Estimation - Calculate financial impact of equipment failures."""

from typing import Dict, Any
from database.models import Equipment, Prediction


class DowntimeCostEstimator:
    """Estimate operational costs and financial impact of equipment failures."""

    # Default cost parameters (in USD)
    DEFAULT_HOURLY_RATE = 500  # Revenue loss per hour of downtime
    DEFAULT_MAINTENANCE_COST = 2000  # Average maintenance cost
    DEFAULT_REPLACEMENT_COST = 50000  # Equipment replacement cost

    # Risk multipliers
    RISK_MULTIPLIERS = {
        "Low": 0.5,
        "Medium": 1.0,
        "High": 2.0,
        "Critical": 4.0,
    }

    @staticmethod
    def estimate_equipment_cost(equipment_id: str, config: Dict = None) -> Dict[str, Any]:
        """Estimate financial impact for a specific equipment."""
        equipment = Equipment.find_by_id(equipment_id)
        if not equipment:
            return {"error": "Equipment not found"}

        latest_pred = Prediction.get_equipment_history(equipment_id, limit=1)
        if not latest_pred:
            return {"error": "No prediction data available"}

        pred = latest_pred[0]
        config = config or {}

        hourly_rate = config.get("hourly_rate", DowntimeCostEstimator.DEFAULT_HOURLY_RATE)
        maint_cost = config.get("maintenance_cost", DowntimeCostEstimator.DEFAULT_MAINTENANCE_COST)
        replacement_cost = config.get("replacement_cost", DowntimeCostEstimator.DEFAULT_REPLACEMENT_COST)

        risk_level = pred.get("risk_level", "Low")
        health_score = float(pred.get("health_score", 100) or 100)
        failure_prob = float(pred.get("probability", pred.get("failure_probability", 0)) or 0)

        # Estimate downtime duration (hours) based on risk
        base_downtime = 4 if risk_level == "Critical" else 2 if risk_level == "High" else 1 if risk_level == "Medium" else 0.5
        estimated_downtime = base_downtime * (1 + (1 - health_score / 100) * 2)

        # Calculate costs
        downtime_cost = estimated_downtime * hourly_rate
        maintenance_immediate = maint_cost if risk_level in ["High", "Critical"] else maint_cost * 0.5
        replacement_risk = replacement_cost * failure_prob if failure_prob > 0.6 else 0

        total_estimated_cost = downtime_cost + maintenance_immediate + replacement_risk
        urgency_score = (1 - health_score / 100) * 100 * (1 + failure_prob * 2)

        return {
            "equipment_id": equipment_id,
            "equipment_name": equipment.get("equipment_name", equipment_id),
            "risk_level": risk_level,
            "health_score": round(health_score, 2),
            "estimated_downtime_hours": round(estimated_downtime, 1),
            "downtime_cost": round(downtime_cost, 2),
            "maintenance_cost": round(maintenance_immediate, 2),
            "replacement_risk_cost": round(replacement_risk, 2),
            "total_estimated_cost": round(total_estimated_cost, 2),
            "urgency_score": round(urgency_score, 1),
            "recommendation": DowntimeCostEstimator._get_recommendation(total_estimated_cost, urgency_score),
        }

    @staticmethod
    def estimate_fleet_cost(config: Dict = None) -> Dict[str, Any]:
        """Estimate total cost impact for entire fleet."""
        equipment_list = Equipment.find_all()
        cost_estimates = []
        total_cost = 0
        critical_count = 0

        for eq in equipment_list:
            eq_id = eq.get("equipment_id")
            cost = DowntimeCostEstimator.estimate_equipment_cost(eq_id, config)
            if "error" not in cost:
                cost_estimates.append(cost)
                total_cost += cost.get("total_estimated_cost", 0)
                if cost.get("risk_level") == "Critical":
                    critical_count += 1

        # Sort by cost
        cost_estimates.sort(key=lambda x: x.get("total_estimated_cost", 0), reverse=True)

        return {
            "total_equipment": len(equipment_list),
            "estimated_equipment_analyzed": len(cost_estimates),
            "total_fleet_risk_cost": round(total_cost, 2),
            "critical_equipment_count": critical_count,
            "top_risk_equipment": cost_estimates[:5],
            "average_cost_per_equipment": round(total_cost / len(cost_estimates), 2) if cost_estimates else 0,
            "priority_actions": DowntimeCostEstimator._fleet_recommendations(cost_estimates),
        }

    @staticmethod
    def _get_recommendation(total_cost: float, urgency: float) -> str:
        """Get recommendation based on cost and urgency."""
        if urgency > 80 or total_cost > 15000:
            return "🔴 URGENT: Immediate maintenance required to prevent catastrophic failure"
        elif urgency > 50 or total_cost > 8000:
            return "🟠 HIGH: Schedule maintenance within 24 hours"
        elif urgency > 30 or total_cost > 3000:
            return "🟡 MEDIUM: Plan maintenance within one week"
        else:
            return "🟢 LOW: Continue monitoring, schedule routine maintenance"

    @staticmethod
    def _fleet_recommendations(cost_estimates: list) -> list:
        """Generate fleet-level recommendations."""
        recommendations = []

        # Total cost threshold
        total = sum(ce.get("total_estimated_cost", 0) for ce in cost_estimates)
        if total > 100000:
            recommendations.append(f"⚠️ Fleet-wide risk cost exceeds $100K ({round(total, 0)}). Urgent capital allocation needed.")

        # Critical count
        critical = [ce for ce in cost_estimates if ce.get("risk_level") == "Critical"]
        if len(critical) > 2:
            recommendations.append(f"🔴 {len(critical)} critical equipment. Initiate emergency response procedures.")

        # Maintenance backlog
        high_cost = [ce for ce in cost_estimates if ce.get("total_estimated_cost", 0) > 5000]
        if len(high_cost) > 3:
            recommendations.append(f"📋 {len(high_cost)} equipment need expensive repairs. Consider preventive strategy.")

        # Equipment efficiency
        avg_cost = total / len(cost_estimates) if cost_estimates else 0
        if avg_cost > 5000:
            recommendations.append("📊 Average equipment cost is high. Consider fleet modernization or lifecycle assessment.")

        return recommendations[:4]

    @staticmethod
    def calculate_roi_for_maintenance(equipment_id: str, maintenance_cost: float) -> Dict[str, float]:
        """Calculate ROI of performing maintenance now vs waiting."""
        cost_now = DowntimeCostEstimator.estimate_equipment_cost(equipment_id)
        if "error" in cost_now:
            return {}

        # Estimate cost if failure occurs
        cost_if_fail = cost_now.get("total_estimated_cost", 0) * 3  # Assume 3x cost if failure occurs

        # Calculate savings
        savings = cost_if_fail - maintenance_cost - cost_now.get("downtime_cost", 0) * 0.5
        roi_percentage = (savings / maintenance_cost * 100) if maintenance_cost > 0 else 0

        return {
            "maintenance_cost": round(maintenance_cost, 2),
            "estimated_cost_if_fails": round(cost_if_fail, 2),
            "estimated_savings": round(savings, 2),
            "roi_percentage": round(roi_percentage, 1),
            "is_worth_maintaining": savings > 0,
            "payback_period_months": round(12 / (roi_percentage / 100)) if roi_percentage > 0 else 999,
        }
