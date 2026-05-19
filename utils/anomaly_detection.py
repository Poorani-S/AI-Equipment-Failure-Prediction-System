"""Intelligent Anomaly Detection - Detect abnormal equipment behavior patterns."""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
from database.models import Prediction, Equipment
from utils.monitoring import SensorSimulator
import statistics


class AnomalyDetector:
    """Detect anomalies in sensor data and equipment behavior."""

    # Thresholds for anomaly detection
    DEVIATION_THRESHOLD = 2.0  # Standard deviations
    SPIKE_THRESHOLD = 1.5  # Ratio of sudden change
    PATTERN_THRESHOLD = 0.85  # Correlation for pattern anomalies

    @staticmethod
    def detect_equipment_anomalies(equipment_id: str) -> Dict[str, Any]:
        """Detect anomalies for a specific equipment."""
        history = Prediction.get_equipment_history(equipment_id, limit=50)
        if not history:
            return {"anomalies": [], "score": 0, "severity": "normal"}

        equipment = Equipment.find_by_id(equipment_id) or {}
        equipment_type = equipment.get("equipment_type", "Turbine")

        anomalies = []
        latest = history[0] if history else {}

        # Statistical anomalies
        stat_anomalies = AnomalyDetector._detect_statistical_anomalies(history, equipment_type)
        anomalies.extend(stat_anomalies)

        # Spike anomalies
        spike_anomalies = AnomalyDetector._detect_spike_anomalies(history, equipment_type)
        anomalies.extend(spike_anomalies)

        # Pattern anomalies
        pattern_anomalies = AnomalyDetector._detect_pattern_anomalies(history, equipment_type)
        anomalies.extend(pattern_anomalies)

        # Trend anomalies
        trend_anomalies = AnomalyDetector._detect_trend_anomalies(history, equipment_type)
        anomalies.extend(trend_anomalies)

        # Calculate severity
        severity = "normal"
        score = 0
        if anomalies:
            score = min(100, len(anomalies) * 15 + sum(a.get("severity_score", 10) for a in anomalies[:5]))
            if score > 70:
                severity = "critical"
            elif score > 40:
                severity = "warning"
            else:
                severity = "caution"

        return {
            "equipment_id": equipment_id,
            "equipment_name": equipment.get("equipment_name", equipment_id),
            "anomalies": sorted(anomalies, key=lambda x: x.get("severity_score", 0), reverse=True)[:10],
            "anomaly_count": len(anomalies),
            "severity": severity,
            "score": round(score, 1),
            "timestamp": datetime.utcnow().isoformat(),
        }

    @staticmethod
    def _detect_statistical_anomalies(history: List, equipment_type: str) -> List[Dict]:
        """Detect statistical outliers using standard deviation."""
        anomalies = []
        sensor_names = ["temperature", "vibration", "pressure", "humidity", "runtime_hours"]
        ranges = SensorSimulator.SENSOR_RANGES.get(equipment_type, SensorSimulator.SENSOR_RANGES["Turbine"])

        for sensor in sensor_names:
            values = [float(h.get(sensor, 0) or 0) for h in history[-20:]]
            if not values or len(values) < 3:
                continue

            mean = statistics.mean(values)
            stdev = statistics.stdev(values) if len(values) > 1 else 0
            latest = values[-1]

            if stdev == 0:
                continue

            z_score = abs((latest - mean) / stdev)
            if z_score > AnomalyDetector.DEVIATION_THRESHOLD:
                anomalies.append({
                    "type": "statistical_outlier",
                    "sensor": sensor.title(),
                    "message": f"{sensor.title()} is {z_score:.1f}σ from normal (value: {latest:.2f})",
                    "severity_score": min(100, z_score * 20),
                    "value": latest,
                    "expected_range": [mean - stdev, mean + stdev],
                })

        return anomalies

    @staticmethod
    def _detect_spike_anomalies(history: List, equipment_type: str) -> List[Dict]:
        """Detect sudden spikes in sensor values."""
        anomalies = []
        sensor_names = ["temperature", "vibration", "pressure", "humidity"]

        for sensor in sensor_names:
            values = [float(h.get(sensor, 0) or 0) for h in history[-10:]]
            if len(values) < 2:
                continue

            for i in range(1, len(values)):
                prev = values[i - 1]
                curr = values[i]
                if prev == 0:
                    continue

                ratio = abs(curr - prev) / prev if prev != 0 else 0
                if ratio > AnomalyDetector.SPIKE_THRESHOLD:
                    anomalies.append({
                        "type": "spike_detected",
                        "sensor": sensor.title(),
                        "message": f"Sudden {ratio:.1f}x spike in {sensor.lower()}",
                        "severity_score": min(80, ratio * 25),
                        "value": curr,
                        "change_ratio": ratio,
                    })

        return anomalies

    @staticmethod
    def _detect_pattern_anomalies(history: List, equipment_type: str) -> List[Dict]:
        """Detect unusual behavior patterns."""
        anomalies = []

        # Check for rapid health degradation
        health_values = [float(h.get("health_score", 100) or 100) for h in history[-15:]]
        if len(health_values) > 1:
            health_change = health_values[-1] - health_values[0]
            if health_change < -30:  # Rapid degradation
                anomalies.append({
                    "type": "degradation_pattern",
                    "sensor": "Health Score",
                    "message": f"Rapid health degradation detected ({health_change:.1f}% in short period)",
                    "severity_score": 75,
                    "degradation_rate": health_change,
                })

        # Check for unstable risk levels
        risk_levels = [h.get("risk_level", "Low") for h in history[-10:]]
        risk_transitions = sum(1 for i in range(1, len(risk_levels)) if risk_levels[i] != risk_levels[i - 1])
        if risk_transitions > 4:
            anomalies.append({
                "type": "unstable_pattern",
                "sensor": "Risk Level",
                "message": f"Erratic risk level changes ({risk_transitions} transitions in 10 predictions)",
                "severity_score": 60,
                "transitions": risk_transitions,
            })

        return anomalies

    @staticmethod
    def _detect_trend_anomalies(history: List, equipment_type: str) -> List[Dict]:
        """Detect anomalous trends."""
        anomalies = []

        # Negative slope in health
        if len(history) > 5:
            recent_health = [float(h.get("health_score", 100) or 100) for h in history[-5:]]
            health_diffs = [recent_health[i] - recent_health[i + 1] for i in range(len(recent_health) - 1)]

            if all(d > 0 for d in health_diffs) and sum(health_diffs) > 10:
                anomalies.append({
                    "type": "negative_trend",
                    "sensor": "Health Trend",
                    "message": "Consistent health score decline detected",
                    "severity_score": 55,
                    "slope": sum(health_diffs) / len(health_diffs),
                })

        # Increasing failure probability
        probs = [float(h.get("probability", h.get("failure_probability", 0)) or 0) for h in history[-5:]]
        if len(probs) > 1 and all(probs[i] <= probs[i + 1] for i in range(len(probs) - 1)):
            if probs[-1] > 0.5:
                anomalies.append({
                    "type": "rising_failure_risk",
                    "sensor": "Failure Probability",
                    "message": f"Failure probability rising consistently ({probs[0]:.1%} → {probs[-1]:.1%})",
                    "severity_score": 70,
                    "start_prob": probs[0],
                    "end_prob": probs[-1],
                })

        return anomalies

    @staticmethod
    def detect_fleet_anomalies() -> Dict[str, Any]:
        """Detect fleet-wide anomalies."""
        equipment_list = Equipment.find_all()
        anomaly_summary = []

        for eq in equipment_list:
            eq_id = eq.get("equipment_id")
            anomalies = AnomalyDetector.detect_equipment_anomalies(eq_id)
            if anomalies["anomaly_count"] > 0:
                anomaly_summary.append({
                    "equipment_id": eq_id,
                    "equipment_name": eq.get("equipment_name", eq_id),
                    "severity": anomalies["severity"],
                    "anomaly_count": anomalies["anomaly_count"],
                    "score": anomalies["score"],
                })

        return {
            "total_equipment": len(equipment_list),
            "anomalous_equipment": len(anomaly_summary),
            "anomalies": sorted(anomaly_summary, key=lambda x: x["score"], reverse=True),
            "fleet_anomaly_level": "normal" if len(anomaly_summary) == 0 else "caution" if len(anomaly_summary) < len(equipment_list) * 0.2 else "warning",
        }
