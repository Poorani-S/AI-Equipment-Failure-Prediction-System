"""
Sensor simulation, AI recommendations, and monitoring utilities.
"""

import random
from datetime import datetime, timedelta
from typing import Dict, List, Tuple


class SensorSimulator:
    """Simulate industrial sensor readings for real-time monitoring."""
    
    # Equipment-specific normal ranges
    SENSOR_RANGES = {
        "Turbine": {
            "Temperature": (65, 75),
            "Vibration": (0.5, 1.2),
            "Pressure": (30, 40),
            "Humidity": (35, 50),
            "Runtime Hours": (100, 8000),
        },
        "Pump": {
            "Temperature": (60, 72),
            "Vibration": (0.4, 1.0),
            "Pressure": (25, 45),
            "Humidity": (30, 60),
            "Runtime Hours": (50, 5000),
        },
        "Compressor": {
            "Temperature": (68, 80),
            "Vibration": (0.6, 1.5),
            "Pressure": (35, 60),
            "Humidity": (40, 70),
            "Runtime Hours": (200, 10000),
        },
    }
    
    # Failure state ranges (abnormal readings)
    FAILURE_RANGES = {
        "Turbine": {
            "Temperature": (80, 150),
            "Vibration": (2.0, 5.0),
            "Pressure": (50, 100),
            "Humidity": (60, 95),
            "Runtime Hours": (8000, 15000),
        },
        "Pump": {
            "Temperature": (75, 120),
            "Vibration": (1.5, 4.0),
            "Pressure": (60, 100),
            "Humidity": (70, 95),
            "Runtime Hours": (5000, 12000),
        },
        "Compressor": {
            "Temperature": (85, 130),
            "Vibration": (2.5, 5.0),
            "Pressure": (80, 120),
            "Humidity": (75, 95),
            "Runtime Hours": (10000, 20000),
        },
    }
    
    @staticmethod
    def generate_sensors(equipment_type: str, is_failure: bool = False) -> Dict[str, float]:
        """Generate simulated sensor readings."""
        ranges = (
            SensorSimulator.FAILURE_RANGES
            if is_failure
            else SensorSimulator.SENSOR_RANGES
        )
        
        if equipment_type not in ranges:
            equipment_type = "Turbine"
        
        sensor_ranges = ranges[equipment_type]
        
        sensors = {}
        for sensor_name, (min_val, max_val) in sensor_ranges.items():
            sensors[sensor_name] = round(random.uniform(min_val, max_val), 2)
        
        return sensors
    
    @staticmethod
    def generate_trends(equipment_type: str, hours: int = 24) -> List[Dict]:
        """Generate sensor trends for the past hours."""
        trends = []
        now = datetime.utcnow()
        
        for i in range(hours):
            timestamp = now - timedelta(hours=hours - i)
            # Gradually transition to potential failure
            is_failing = random.random() < (i / hours * 0.3)
            sensors = SensorSimulator.generate_sensors(equipment_type, is_failing)
            
            trends.append({
                "timestamp": timestamp.isoformat(),
                **sensors,
            })
        
        return trends


class RecommendationEngine:
    """Generate AI-powered maintenance recommendations."""
    
    RECOMMENDATION_RULES = {
        "high_temperature": {
            "threshold": 85,
            "message": "⚠️ Cooling system requires inspection. Temperature exceeding safe limits.",
            "priority": "High",
            "action": "Inspect cooling systems and ventilation",
        },
        "high_vibration": {
            "threshold": 2.0,
            "message": "⚠️ Bearing vibration abnormal. Potential mechanical wear detected.",
            "priority": "High",
            "action": "Check bearing alignment and lubrication",
        },
        "high_pressure": {
            "threshold": 50,
            "message": "⚠️ Pressure levels elevated. Possible blockage or valve issue.",
            "priority": "Medium",
            "action": "Verify pressure relief valves and check for blockages",
        },
        "high_humidity": {
            "threshold": 75,
            "message": "⚠️ Humidity levels critical. Risk of corrosion and electrical failures.",
            "priority": "High",
            "action": "Improve ventilation and add dehumidification",
        },
        "high_runtime": {
            "threshold": 8000,
            "message": "📅 Equipment has reached high operational hours. Routine maintenance recommended.",
            "priority": "Medium",
            "action": "Schedule preventive maintenance",
        },
    }
    
    @staticmethod
    def generate_recommendations(sensor_values: Dict[str, float]) -> List[Dict]:
        """Generate recommendations based on sensor readings."""
        recommendations = []
        
        # Temperature check
        if sensor_values.get("Temperature", 0) > RecommendationEngine.RECOMMENDATION_RULES["high_temperature"]["threshold"]:
            recommendations.append(
                {
                    "type": "high_temperature",
                    **RecommendationEngine.RECOMMENDATION_RULES["high_temperature"],
                }
            )
        
        # Vibration check
        if sensor_values.get("Vibration", 0) > RecommendationEngine.RECOMMENDATION_RULES["high_vibration"]["threshold"]:
            recommendations.append(
                {
                    "type": "high_vibration",
                    **RecommendationEngine.RECOMMENDATION_RULES["high_vibration"],
                }
            )
        
        # Pressure check
        if sensor_values.get("Pressure", 0) > RecommendationEngine.RECOMMENDATION_RULES["high_pressure"]["threshold"]:
            recommendations.append(
                {
                    "type": "high_pressure",
                    **RecommendationEngine.RECOMMENDATION_RULES["high_pressure"],
                }
            )
        
        # Humidity check
        if sensor_values.get("Humidity", 0) > RecommendationEngine.RECOMMENDATION_RULES["high_humidity"]["threshold"]:
            recommendations.append(
                {
                    "type": "high_humidity",
                    **RecommendationEngine.RECOMMENDATION_RULES["high_humidity"],
                }
            )
        
        # Runtime hours check
        if sensor_values.get("Runtime Hours", 0) > RecommendationEngine.RECOMMENDATION_RULES["high_runtime"]["threshold"]:
            recommendations.append(
                {
                    "type": "high_runtime",
                    **RecommendationEngine.RECOMMENDATION_RULES["high_runtime"],
                }
            )
        
        return recommendations


class HealthScoreCalculator:
    """Calculate equipment health scores based on sensor data."""
    
    @staticmethod
    def calculate_health_score(sensor_values: Dict[str, float], equipment_type: str = "Turbine") -> Tuple[float, str]:
        """
        Calculate health score (0-100).
        Returns: (health_score, status)
        Status: 'Healthy', 'Caution', 'Critical'
        """
        score = 100.0
        
        # Get normal ranges for the equipment
        normal_ranges = SensorSimulator.SENSOR_RANGES.get(equipment_type, SensorSimulator.SENSOR_RANGES["Turbine"])
        
        # Deduct points for out-of-range values
        for sensor_name, value in sensor_values.items():
            if sensor_name in normal_ranges:
                min_val, max_val = normal_ranges[sensor_name]
                
                # Calculate deviation percentage
                if value < min_val:
                    deviation = ((min_val - value) / min_val) * 100
                    score -= min(30, deviation * 0.5)
                elif value > max_val:
                    deviation = ((value - max_val) / max_val) * 100
                    score -= min(50, deviation * 0.8)
        
        # Determine status
        if score >= 80:
            status = "Healthy"
        elif score >= 50:
            status = "Caution"
        else:
            status = "Critical"
        
        return max(0, round(score, 2)), status


class MaintenancePrediction:
    """Predict maintenance schedules based on equipment health."""
    
    @staticmethod
    def predict_next_maintenance_date(
        health_score: float,
        current_runtime_hours: float,
        last_maintenance_date: datetime,
    ) -> Tuple[datetime, str, str]:
        """
        Predict the next maintenance date.
        Returns: (maintenance_date, urgency, description)
        """
        days_until_maintenance = 30  # Default
        urgency = "Normal"
        description = "Routine maintenance scheduled"
        
        # Health-based prediction
        if health_score < 40:
            days_until_maintenance = 1
            urgency = "Critical"
            description = "URGENT: Immediate maintenance required"
        elif health_score < 60:
            days_until_maintenance = 3
            urgency = "High"
            description = "Priority maintenance needed within 3 days"
        elif health_score < 80:
            days_until_maintenance = 7
            urgency = "Medium"
            description = "Schedule maintenance within 1 week"
        else:
            days_until_maintenance = 30
            urgency = "Normal"
            description = "Routine maintenance in 1 month"
        
        # Runtime-based prediction
        if current_runtime_hours > 8000:
            days_until_maintenance = min(days_until_maintenance, 7)
            urgency = "High"
            description = "High runtime hours detected. Maintenance recommended soon."
        
        maintenance_date = datetime.utcnow() + timedelta(days=days_until_maintenance)
        
        return maintenance_date, urgency, description


class RiskLevelCalculator:
    """Calculate risk levels for equipment failure."""
    
    @staticmethod
    def calculate_risk_level(failure_probability: float) -> str:
        """
        Calculate risk level based on failure probability.
        Returns: 'Low', 'Medium', 'Critical'
        """
        probability_percentage = failure_probability * 100
        
        if probability_percentage < 30:
            return "Low"
        elif probability_percentage < 70:
            return "Medium"
        else:
            return "Critical"
    
    @staticmethod
    def get_risk_color(risk_level: str) -> str:
        """Get color code for risk level visualization."""
        color_map = {
            "Low": "#2dd4bf",      # Teal (safe)
            "Medium": "#f59e0b",   # Amber (warning)
            "Critical": "#ef4444", # Red (danger)
        }
        return color_map.get(risk_level, "#6b7280")
