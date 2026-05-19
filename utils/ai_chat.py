"""AI Chat Assistant - Intelligent chatbot for equipment diagnostics and insights."""

from datetime import datetime
from typing import Dict, List, Any, Tuple
from database.models import Equipment, Prediction, Alert
from utils.prediction_state import build_latest_fleet_snapshot
from utils.ai_intelligence import build_equipment_intelligence


class AIChatAssistant:
    """Conversational AI for equipment monitoring and diagnostics."""

    @staticmethod
    def chat(user_message: str, context: Dict[str, Any] = None) -> str:
        """Process user message and return intelligent response."""
        user_msg_lower = user_message.lower().strip()
        context = context or {}

        # Equipment-specific queries
        if "why" in user_msg_lower and ("critical" in user_msg_lower or "failure" in user_msg_lower):
            return AIChatAssistant._explain_failure(user_message, context)

        if "compare" in user_msg_lower:
            return AIChatAssistant._suggest_comparison(user_message, context)

        if "recommend" in user_msg_lower or "maintain" in user_msg_lower:
            return AIChatAssistant._suggest_maintenance(user_message, context)

        if "health" in user_msg_lower or "status" in user_msg_lower:
            return AIChatAssistant._explain_health(user_message, context)

        if "anomal" in user_msg_lower or "unusual" in user_msg_lower:
            return AIChatAssistant._explain_anomalies(user_message, context)

        if "forecast" in user_msg_lower or "predict" in user_msg_lower:
            return AIChatAssistant._explain_forecast(user_message, context)

        if "alert" in user_msg_lower or "warning" in user_msg_lower:
            return AIChatAssistant._summarize_alerts(user_message, context)

        if "trend" in user_msg_lower or "history" in user_msg_lower:
            return AIChatAssistant._analyze_trends(user_message, context)

        # General queries
        if "help" in user_msg_lower or "what can" in user_msg_lower:
            return AIChatAssistant._provide_help()

        # Fallback
        return AIChatAssistant._general_response(user_message)

    @staticmethod
    def _explain_failure(msg: str, context: Dict) -> str:
        """Explain why equipment became critical."""
        equipment_id = context.get("equipment_id")
        if not equipment_id:
            return "Please select an equipment card to get failure analysis. I can then explain why it became critical."

        try:
            intel = build_equipment_intelligence(equipment_id)
            equipment = intel.get("equipment_name", equipment_id)
            root_cause = intel.get("root_cause", {})
            health = intel.get("health_score", 0)
            risk = intel.get("risk_level", "Unknown")

            response = f"""**Why is {equipment} Critical?**

🔴 **Status:** {risk} Risk | Health Score: {health}%

**Root Cause:**
{root_cause.get('cause', 'Abnormal equipment behavior detected')}

**Affected Subsystem:**
{root_cause.get('subsystem', 'General')}

**Analysis:**
{root_cause.get('summary', 'Multiple sensors indicate equipment stress.')}

**Recommendation:**
Immediate inspection required. {intel.get('maintenance', {}).get('timeline_summary', 'Schedule maintenance within 4 hours.')}
"""
            return response
        except Exception as e:
            return f"Unable to analyze equipment: {str(e)}"

    @staticmethod
    def _explain_health(msg: str, context: Dict) -> str:
        """Explain current health status."""
        try:
            snapshot = build_latest_fleet_snapshot()
            fleet = snapshot.get("rows", [])

            critical_count = sum(1 for eq in fleet if eq["status"] == "critical")
            warning_count = sum(1 for eq in fleet if eq["status"] == "warning")
            online_count = sum(1 for eq in fleet if eq["status"] == "online")

            avg_health = sum(eq["health_score"] for eq in fleet) / len(fleet) if fleet else 0

            return f"""**Fleet Health Status**

📊 **Overall:** {avg_health:.1f}% average health

🟢 Online: {online_count} equipment
🟡 Warning: {warning_count} equipment  
🔴 Critical: {critical_count} equipment

**Key Insight:**
Fleet is {"stable" if avg_health > 70 else "degrading" if avg_health > 40 else "critical"}.

**Action:**
{"✅ Continue routine monitoring" if critical_count == 0 else f"⚠️ Address {critical_count} critical equipment immediately"}
"""
        except Exception as e:
            return f"Unable to retrieve fleet health: {str(e)}"

    @staticmethod
    def _suggest_maintenance(msg: str, context: Dict) -> str:
        """Suggest maintenance actions."""
        equipment_id = context.get("equipment_id")
        if not equipment_id:
            equipment_id = "all"

        try:
            if equipment_id == "all":
                snapshot = build_latest_fleet_snapshot()
                critical_equipment = [eq for eq in snapshot["rows"] if eq["status"] == "critical"][:3]

                if not critical_equipment:
                    return "✅ All equipment is operating normally. Continue scheduled maintenance as planned."

                response = "**Maintenance Recommendations**\n\n"
                for eq in critical_equipment:
                    response += f"**{eq['equipment'].get('equipment_name', eq['equipment_id'])}** (Critical)\n"
                    response += f"- Health: {eq['health_score']}%\n"
                    response += f"- Action: Inspect immediately\n\n"
                return response
            else:
                intel = build_equipment_intelligence(equipment_id)
                maint = intel.get("maintenance", {})
                return f"""**Maintenance Plan for {intel.get('equipment_name', equipment_id)}**

**Urgency:** {maint.get('urgency', 'Medium')}
**Timeline:** {maint.get('timeline_summary', 'Schedule within 24 hours')}
**Action:** {maint.get('recommended_action', 'Perform routine inspection')}

**Recommendations:**
{chr(10).join([f"- {r.get('message', 'Unknown')} (Priority: {r.get('priority', 'Medium')})" for r in maint.get('recommendations', [])[:3]])}
"""
        except Exception as e:
            return f"Cannot generate maintenance recommendations: {str(e)}"

    @staticmethod
    def _suggest_comparison(msg: str, context: Dict) -> str:
        """Suggest equipment comparison."""
        snapshot = build_latest_fleet_snapshot()
        fleet = snapshot.get("rows", [])[:5]

        if len(fleet) < 2:
            return "Need at least 2 equipment to compare. Click 'Compare Mode' when you have multiple machines."

        response = "**Available Equipment for Comparison:**\n\n"
        for eq in fleet:
            response += f"• {eq['equipment'].get('equipment_name', eq['equipment_id'])} (Health: {eq['health_score']}%)\n"

        return response + "\n👉 Select two equipment from the dashboard to activate Comparison Mode."

    @staticmethod
    def _explain_anomalies(msg: str, context: Dict) -> str:
        """Explain detected anomalies."""
        equipment_id = context.get("equipment_id")
        if not equipment_id:
            return "Select an equipment to analyze anomalies in its sensor data."

        try:
            intel = build_equipment_intelligence(equipment_id)
            anomalies = intel.get("anomaly_flags", [])
            contributions = intel.get("sensor_contributions", [])

            if not anomalies:
                return f"✅ **{intel.get('equipment_name', equipment_id)}** - No anomalies detected. Sensor readings are normal."

            response = f"**Anomalies Detected in {intel.get('equipment_name', equipment_id)}**\n\n"
            for sensor in contributions:
                if sensor["direction"] != "stable":
                    response += f"⚠️ **{sensor['sensor']}:** {sensor['value']} ({sensor['direction'].upper()})\n"
                    response += f"   Expected range: {sensor['expected_range']}\n"
                    response += f"   Impact: {sensor['contribution_pct']}% of overall risk\n\n"

            return response
        except Exception as e:
            return f"Cannot analyze anomalies: {str(e)}"

    @staticmethod
    def _explain_forecast(msg: str, context: Dict) -> str:
        """Explain failure forecast."""
        equipment_id = context.get("equipment_id")
        if not equipment_id:
            return "Select an equipment to see its failure forecast."

        try:
            intel = build_equipment_intelligence(equipment_id)
            forecast = intel.get("forecast", {})

            return f"""**Failure Forecast for {intel.get('equipment_name', equipment_id)}**

📊 **24-Hour Forecast:** {forecast.get('failure_24h', 0)}% failure probability
📈 **7-Day Forecast:** {forecast.get('failure_7d', 0)}% failure probability
📉 **Remaining Life:** ~{forecast.get('estimated_remaining_life_days', 0)} days

**Recommendation:**
{"🟢 Equipment stable - continue normal operation" if forecast.get('failure_24h', 0) < 30 else "🟡 Monitor closely - maintain ready status" if forecast.get('failure_24h', 0) < 60 else "🔴 High risk - prepare for immediate maintenance"}

**Note:** These estimates are based on current sensor readings and historical trends.
"""
        except Exception as e:
            return f"Cannot forecast: {str(e)}"

    @staticmethod
    def _summarize_alerts(msg: str, context: Dict) -> str:
        """Summarize current alerts."""
        try:
            alerts = Alert.get_active_alerts()[:5]
            if not alerts:
                return "✅ **No Active Alerts** - All systems operating normally."

            response = f"**Active Alerts ({len(alerts)})**\n\n"
            for alert in alerts:
                response += f"🔴 **{alert.get('severity', 'Medium')}** - {alert.get('equipment_id', 'Unknown')}\n"
                response += f"   {alert.get('message', 'Alert triggered')}\n\n"

            return response
        except Exception as e:
            return f"Cannot retrieve alerts: {str(e)}"

    @staticmethod
    def _analyze_trends(msg: str, context: Dict) -> str:
        """Analyze equipment trends."""
        equipment_id = context.get("equipment_id")
        if not equipment_id:
            return "Select equipment to view its trend analysis."

        try:
            intel = build_equipment_intelligence(equipment_id)
            trend = intel.get("health_trend", {})
            points = trend.get("points", [])

            if not points:
                return "No historical data available yet."

            first_health = points[0]["health_score"] if points else 0
            last_health = points[-1]["health_score"] if points else 0
            direction = trend.get("direction", "stable")

            response = f"**Health Trend for {intel.get('equipment_name', equipment_id)}**\n\n"
            response += f"📉 **Direction:** {direction.upper()}\n"
            response += f"📊 **Starting Health:** {first_health}%\n"
            response += f"📍 **Current Health:** {last_health}%\n"
            response += f"📈 **Change:** {last_health - first_health:+.1f}%\n\n"

            if direction == "degrading":
                response += "⚠️ Equipment is degrading. Consider scheduling maintenance soon."
            elif direction == "improving":
                response += "✅ Equipment health is improving."
            else:
                response += "➡️ Equipment is stable."

            return response
        except Exception as e:
            return f"Cannot analyze trends: {str(e)}"

    @staticmethod
    def _provide_help() -> str:
        """Provide help information."""
        return """**AI Chat Assistant - Available Commands**

Ask me about:
- **Why is [equipment] critical?** - Explain failure reasons
- **What's the health status?** - Fleet health overview
- **Recommend maintenance** - Get maintenance suggestions
- **Show anomalies** - Detect unusual sensor behavior
- **Forecast failure** - See failure predictions
- **Summarize alerts** - View active alerts
- **Compare equipment** - Side-by-side equipment comparison
- **Analyze trends** - View equipment degradation trends

💡 **Tip:** Select an equipment card to get equipment-specific analysis!
"""

    @staticmethod
    def _general_response(msg: str) -> str:
        """Generate general response."""
        return """Hello! I'm your Prediction Assistant. I specialize in monitoring equipment health, predicting failures, and recommending maintenance.

**Try asking me things like:**
- "Why is Turbine A critical?"
- "What is the overall fleet health status?"
- "Recommend maintenance for Pump B"
- "Show anomalies"

How can I help you today?
"""


def format_chat_response(response: str, is_assistant: bool = True) -> Dict[str, Any]:
    """Format chat response for frontend."""
    return {
        "message": response,
        "sender": "assistant" if is_assistant else "user",
        "timestamp": datetime.utcnow().isoformat(),
        "is_html": True,
    }
