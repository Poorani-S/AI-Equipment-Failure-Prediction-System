"""Advanced AI insight generation for the industrial monitoring platform.

This module turns the synchronized prediction state into forecasting,
explainability, maintenance guidance, and fleet intelligence payloads that all
pages can reuse.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List

from database.models import Alert, Equipment, Prediction
from utils.monitoring import RecommendationEngine, SensorSimulator, HealthScoreCalculator
from utils.prediction_state import (
    build_latest_fleet_snapshot,
    derive_equipment_status,
    derive_health_status,
    normalize_risk_level,
)


def _clamp(value: float, lower: float = 0.0, upper: float = 100.0) -> float:
    return max(lower, min(upper, value))


def _format_pct(value: float) -> str:
    return f"{_clamp(value):.1f}%"


def _sensor_contributions(sensor_values: Dict[str, float], equipment_type: str) -> List[Dict[str, Any]]:
    ranges = SensorSimulator.SENSOR_RANGES.get(equipment_type, SensorSimulator.SENSOR_RANGES["Turbine"])
    contributions: List[Dict[str, Any]] = []

    for sensor_name, value in sensor_values.items():
        if sensor_name not in ranges:
            continue

        min_val, max_val = ranges[sensor_name]
        midpoint = (min_val + max_val) / 2
        span = max(max_val - min_val, 1e-6)
        deviation = abs(value - midpoint) / span
        contribution = _clamp(deviation * 120, 0, 100)

        direction = "stable"
        if value > max_val:
            direction = "high"
        elif value < min_val:
            direction = "low"

        contributions.append(
            {
                "sensor": sensor_name,
                "value": round(value, 2),
                "expected_range": [round(min_val, 2), round(max_val, 2)],
                "direction": direction,
                "contribution": round(contribution, 1),
            }
        )

    contributions.sort(key=lambda item: item["contribution"], reverse=True)
    total = sum(item["contribution"] for item in contributions) or 1.0
    for item in contributions:
        item["contribution_pct"] = round((item["contribution"] / total) * 100, 1)
    return contributions


def _root_cause(sensor_values: Dict[str, float], equipment_type: str) -> Dict[str, str]:
    contributions = _sensor_contributions(sensor_values, equipment_type)
    if not contributions:
        return {
            "cause": "No dominant anomaly detected",
            "subsystem": "General",
            "summary": "Sensor values are within expected bounds.",
        }

    top = contributions[0]
    mapping = {
        "Temperature": "Cooling / thermal subsystem",
        "Vibration": "Rotating assembly / bearings",
        "Pressure": "Fluid / pneumatic path",
        "Humidity": "Environmental sealing / corrosion control",
        "Runtime Hours": "Lifecycle / wear management",
    }
    cause_map = {
        "Temperature": "thermal stress or cooling inefficiency",
        "Vibration": "mechanical instability or misalignment",
        "Pressure": "pressure control drift or blockage",
        "Humidity": "environmental exposure or moisture ingress",
        "Runtime Hours": "end-of-life wear accumulation",
    }

    return {
        "cause": f"{top['sensor']} indicates {cause_map.get(top['sensor'], 'abnormal operating behavior')}.",
        "subsystem": mapping.get(top["sensor"], "General"),
        "summary": f"{top['sensor']} is the dominant factor with a {top['contribution_pct']:.1f}% contribution.",
    }


def _forecast_from_score(health_score: float, risk_level: str, history_len: int) -> Dict[str, Any]:
    base_failure = _clamp((100.0 - health_score) * 0.9, 0, 100)
    trend_penalty = _clamp(history_len * 1.2, 0, 18)

    if risk_level == "Critical":
        base_failure = max(base_failure, 72)
    elif risk_level == "Medium":
        base_failure = max(base_failure, 38)

    failure_24h = _clamp(base_failure + trend_penalty * 0.8, 0, 100)
    failure_7d = _clamp(base_failure + trend_penalty * 1.8 + 8, 0, 100)
    remaining_days = max(1, int(round((health_score / 100.0) * 30 - trend_penalty / 2)))

    return {
        "failure_24h": round(failure_24h, 1),
        "failure_7d": round(failure_7d, 1),
        "estimated_remaining_life_days": remaining_days,
        "degradation_index": round(_clamp(100.0 - health_score, 0, 100), 1),
    }


def _maintenance_plan(health_score: float, risk_level: str, sensor_values: Dict[str, float], equipment_type: str) -> Dict[str, Any]:
    recommendations = RecommendationEngine.generate_recommendations(sensor_values)
    urgency = "Low"
    eta_hours = 72
    if risk_level == "Critical" or health_score < 40:
        urgency = "Urgent"
        eta_hours = 4
    elif risk_level == "Medium" or health_score < 70:
        urgency = "High"
        eta_hours = 24

    top_action = recommendations[0]["action"] if recommendations else "Perform routine inspection"
    if recommendations:
        top_action = recommendations[0]["action"]

    severity = "High" if health_score < 40 else "Medium" if health_score < 70 else "Low"

    return {
        "urgency": urgency,
        "estimated_severity": severity,
        "recommended_action": top_action,
        "inspection_priority": 1 if urgency == "Urgent" else 2 if urgency == "High" else 3,
        "timeline_hours": eta_hours,
        "timeline_summary": f"Inspect {equipment_type.lower()} within {eta_hours} hours.",
        "recommendations": recommendations[:5],
    }


def _history_trend(equipment_id: str) -> Dict[str, Any]:
    history = Prediction.get_equipment_history(equipment_id, limit=30)
    ordered = list(reversed(history))
    points = []
    for item in ordered:
        ts = item.get("timestamp")
        if hasattr(ts, "isoformat"):
            ts = ts.isoformat()
        points.append(
            {
                "timestamp": str(ts),
                "health_score": round(float(item.get("health_score", 0) or 0), 2),
                "risk_level": normalize_risk_level(item.get("risk_level")),
                "prediction_value": int(item.get("prediction_value", item.get("prediction", 0)) or 0),
            }
        )

    if points:
        first = points[0]["health_score"]
        last = points[-1]["health_score"]
        trend_delta = round(last - first, 2)
    else:
        trend_delta = 0.0

    return {
        "points": points[-14:],
        "trend_delta": trend_delta,
        "direction": "improving" if trend_delta > 0.5 else "degrading" if trend_delta < -0.5 else "stable",
    }


def _activity_feed(limit: int = 10) -> List[Dict[str, Any]]:
    alerts = Alert.get_active_alerts()
    predictions = Prediction.get_recent_predictions(limit=limit)

    entries: List[Dict[str, Any]] = []
    for alert in alerts[: limit // 2]:
        entries.append(
            {
                "timestamp": alert.get("created_at").isoformat() if alert.get("created_at") else datetime.utcnow().isoformat(),
                "type": "alert",
                "message": f"{alert.get('equipment_id', 'Unknown')} entered {alert.get('severity', 'Medium')} state",
                "severity": alert.get("severity", "Medium"),
            }
        )

    for item in predictions[:limit]:
        entries.append(
            {
                "timestamp": item.get("timestamp").isoformat() if hasattr(item.get("timestamp"), "isoformat") else str(item.get("timestamp")),
                "type": "prediction",
                "message": f"Prediction updated for {item.get('equipment_id', 'Unknown')} -> {item.get('prediction_text', 'Unknown')}",
                "severity": item.get("risk_level", "Low"),
            }
        )

    entries.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return entries[:limit]


def _fleet_summary(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    total = max(snapshot["total_equipment"], 1)
    healthy = snapshot["counts"]["online"]
    warning = snapshot["counts"]["warning"]
    critical = snapshot["counts"]["critical"]
    avg_health = 0.0
    if snapshot["equipment_list"]:
        avg_health = sum(float(eq.get("health_score", 0) or 0) for eq in snapshot["equipment_list"]) / len(snapshot["equipment_list"])

    fleet_stability = _clamp((healthy / total) * 100 - (critical / total) * 25 + (avg_health / 10), 0, 100)
    risky = sorted(
        snapshot["rows"],
        key=lambda row: (row["status"] == "critical", row["health_score"]),
        reverse=True,
    )[:5]

    return {
        "overall_system_health": round(avg_health, 1),
        "average_health_score": round(avg_health, 1),
        "total_healthy_equipment": healthy,
        "total_warning_equipment": warning,
        "critical_equipment_ranking": [
            {
                "equipment_id": row["equipment_id"],
                "name": row["equipment"].get("equipment_name") or row["equipment_id"],
                "status": row["status"],
                "health_score": row["health_score"],
            }
            for row in risky
        ],
        "fleet_stability_score": round(fleet_stability, 1),
        "top_risky_machines": [
            {
                "equipment_id": row["equipment_id"],
                "name": row["equipment"].get("equipment_name") or row["equipment_id"],
                "health_score": row["health_score"],
                "risk_level": row["risk_level"],
            }
            for row in risky
        ],
    }


def build_equipment_intelligence(equipment_id: str) -> Dict[str, Any]:
    equipment = Equipment.find_by_id(equipment_id) or {}
    latest_prediction = Prediction.get_latest_by_equipment().get(equipment_id, {})
    history = Prediction.get_equipment_history(equipment_id, limit=30)
    sensor_values = {
        "Temperature": float(latest_prediction.get("temperature", 0) or 0),
        "Vibration": float(latest_prediction.get("vibration", 0) or 0),
        "Pressure": float(latest_prediction.get("pressure", 0) or 0),
        "Humidity": float(latest_prediction.get("humidity", 0) or 0),
        "Runtime Hours": float(latest_prediction.get("runtime_hours", 0) or 0),
    }

    equipment_type = equipment.get("equipment_type") or "Turbine"
    health_score = float(latest_prediction.get("health_score", equipment.get("health_score", 0)) or 0)
    health_status = derive_health_status(latest_prediction, equipment)
    risk_level = normalize_risk_level(latest_prediction.get("risk_level"))
    status = derive_equipment_status(latest_prediction, equipment)

    return {
        "equipment_id": equipment_id,
        "equipment_name": equipment.get("equipment_name") or equipment_id,
        "equipment_type": equipment_type,
        "location": equipment.get("location"),
        "health_score": round(health_score, 2),
        "health_status": health_status,
        "equipment_status": status,
        "risk_level": risk_level,
        "prediction_text": latest_prediction.get("prediction_text") or ("Equipment Failure Predicted" if int(latest_prediction.get("prediction_value", latest_prediction.get("prediction", 0)) or 0) == 1 else "Equipment Working Normally"),
        "root_cause": _root_cause(sensor_values, equipment_type),
        "sensor_contributions": _sensor_contributions(sensor_values, equipment_type),
        "forecast": _forecast_from_score(health_score, risk_level, len(history)),
        "maintenance": _maintenance_plan(health_score, risk_level, sensor_values, equipment_type),
        "health_trend": _history_trend(equipment_id),
        "recommendations": RecommendationEngine.generate_recommendations(sensor_values),
        "confidence": round(float(latest_prediction.get("failure_probability", latest_prediction.get("probability", 0)) or 0), 2),
        "anomaly_flags": [
            item["sensor"] for item in _sensor_contributions(sensor_values, equipment_type) if item["direction"] != "stable" and item["contribution"] >= 25
        ],
    }


def build_platform_intelligence(selected_id: str = None) -> Dict[str, Any]:
    snapshot = build_latest_fleet_snapshot()
    fleet = _fleet_summary(snapshot)
    activities = _activity_feed(limit=12)
    selected_equipment = None

    heatmap = []
    for row in snapshot["rows"]:
        heatmap.append(
            {
                "equipment_id": row["equipment_id"],
                "name": row["equipment"].get("equipment_name") or row["equipment_id"],
                "type": row["equipment"].get("equipment_type") or "Unknown",
                "location": row["equipment"].get("location") or "Unknown",
                "health_score": round(float(row["health_score"] or 0), 2),
                "status": row["status"],
                "risk_level": row["risk_level"],
            }
        )

    if heatmap:
        if selected_id and any(item["equipment_id"] == selected_id for item in heatmap):
            selected_equipment = build_equipment_intelligence(selected_id)
        else:
            selected_equipment = build_equipment_intelligence(heatmap[0]["equipment_id"])

    return {
        "fleet": fleet,
        "heatmap": heatmap,
        "selected_equipment": selected_equipment,
        "activity_feed": activities,
        "timestamp": datetime.utcnow().isoformat(),
        "model_monitoring": {
            "average_prediction_confidence": round(
                sum(float(p.get("failure_probability", p.get("probability", 0)) or 0) for p in Prediction.get_recent_predictions(limit=100)) / max(len(Prediction.get_recent_predictions(limit=100)), 1),
                2,
            ),
            "prediction_volume_24h": len(Prediction.get_recent_predictions(limit=100)),
            "alert_volume": len(Alert.get_active_alerts()),
        },
    }