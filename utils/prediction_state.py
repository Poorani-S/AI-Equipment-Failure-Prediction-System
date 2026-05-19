"""Central prediction state helpers.

This module keeps dashboard, admin, reports, and prediction routes aligned by
deriving the current equipment state from the latest prediction per equipment.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List

from database.models import Equipment, Prediction


def normalize_risk_level(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text in {"critical", "high"}:
        return "Critical"
    if text in {"medium", "caution", "warning", "risk"}:
        return "Medium"
    if text in {"low", "healthy", "good", "online"}:
        return "Low"
    return "Low"


def derive_equipment_status(prediction: Dict[str, Any], equipment: Dict[str, Any] | None = None) -> str:
    equipment = equipment or {}

    explicit_status = str(prediction.get("equipment_status") or "").strip().lower()
    if explicit_status in {"online", "warning", "critical", "offline"}:
        return explicit_status

    health_score = prediction.get("health_score")
    if health_score is None:
        health_score = equipment.get("health_score")
    try:
        health_score = float(health_score)
    except (TypeError, ValueError):
        health_score = None

    if health_score is not None:
        if health_score >= 80:
            return "online"
        if health_score >= 50:
            return "warning"
        return "critical"

    risk_level = normalize_risk_level(prediction.get("risk_level"))
    if risk_level == "Critical":
        return "critical"
    if risk_level == "Medium":
        return "warning"
    return "online"


def derive_health_status(prediction: Dict[str, Any], equipment: Dict[str, Any] | None = None) -> str:
    equipment = equipment or {}

    explicit_status = str(prediction.get("health_status") or "").strip()
    if explicit_status:
        return explicit_status

    health_score = prediction.get("health_score")
    if health_score is None:
        health_score = equipment.get("health_score")
    try:
        health_score = float(health_score)
    except (TypeError, ValueError):
        health_score = None

    if health_score is None:
        return "Healthy"
    if health_score >= 80:
        return "Healthy"
    if health_score >= 50:
        return "Caution"
    return "Critical"


def build_latest_fleet_snapshot() -> Dict[str, Any]:
    """Build the authoritative latest state for all equipment."""
    equipment_list = Equipment.find_all()
    equipment_by_id = {eq.get("equipment_id"): eq for eq in equipment_list if eq.get("equipment_id")}
    latest_predictions = Prediction.get_latest_by_equipment()

    snapshot_rows: List[Dict[str, Any]] = []
    counts = defaultdict(int)

    for equipment_id, equipment in equipment_by_id.items():
        latest_prediction = latest_predictions.get(equipment_id, {})
        status = derive_equipment_status(latest_prediction, equipment)
        health_status = derive_health_status(latest_prediction, equipment)

        counts[f"equipment_{status}"] += 1
        if health_status == "Healthy":
            counts["health_healthy"] += 1
        elif health_status == "Caution":
            counts["health_caution"] += 1
        else:
            counts["health_critical"] += 1

        snapshot_rows.append(
            {
                "equipment_id": equipment_id,
                "equipment": equipment,
                "prediction": latest_prediction,
                "status": status,
                "health_status": health_status,
                "prediction_value": latest_prediction.get("prediction_value", latest_prediction.get("prediction")),
                "risk_level": normalize_risk_level(latest_prediction.get("risk_level")),
                "health_score": latest_prediction.get("health_score", equipment.get("health_score", 0)),
            }
        )

    return {
        "equipment_list": equipment_list,
        "latest_predictions": latest_predictions,
        "rows": snapshot_rows,
        "counts": {
            "online": counts.get("equipment_online", 0),
            "warning": counts.get("equipment_warning", 0),
            "critical": counts.get("equipment_critical", 0),
            "healthy": counts.get("health_healthy", 0),
            "caution": counts.get("health_caution", 0),
            "health_critical": counts.get("health_critical", 0),
        },
        "total_equipment": len(equipment_list),
    }


def sync_equipment_state(debug: bool = False) -> Dict[str, Any]:
    """Update equipment statuses from the latest prediction records."""
    snapshot = build_latest_fleet_snapshot()
    updates = []

    for row in snapshot["rows"]:
        equipment = row["equipment"]
        equipment_id = row["equipment_id"]
        current_status = str(equipment.get("status") or "").strip().lower()
        derived_status = row["status"]
        health_score = row["health_score"]

        if current_status != derived_status or equipment.get("health_score") != health_score:
            if debug:
                print(
                    f"SYNC equipment={equipment_id} status {current_status!r}->{derived_status!r} "
                    f"health {equipment.get('health_score')!r}->{health_score!r}"
                )
            Equipment.update_status(equipment_id, derived_status, health_score)
            updates.append(equipment_id)

    snapshot["updated_equipment_ids"] = updates
    return snapshot