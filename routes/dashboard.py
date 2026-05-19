"""
Dashboard routes (Blueprint) - Main dashboard, equipment monitoring, and analytics.
"""

import io
from flask import Blueprint, render_template, jsonify, request, send_file
from utils.auth import login_required
from database.models import Equipment, Prediction, Alert, User
from utils.monitoring import (
    SensorSimulator,
    HealthScoreCalculator,
    RecommendationEngine,
    RiskLevelCalculator,
    MaintenancePrediction,
)
from utils.prediction_state import sync_equipment_state, build_latest_fleet_snapshot, normalize_risk_level, derive_health_status, derive_equipment_status
from utils.ai_intelligence import build_equipment_intelligence, build_platform_intelligence
from utils.ai_chat import AIChatAssistant, format_chat_response
from utils.anomaly_detection import AnomalyDetector
from utils.equipment_comparison import EquipmentComparison
from utils.cost_estimation import DowntimeCostEstimator
from utils.advanced_search import AdvancedSearch
from utils.factory_manager import FactoryManager, FactoryFleetAnalytics
from model import predict_equipment_failure, FEATURE_COLUMNS
from datetime import datetime, timedelta

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


def sanitize_for_json(data):
    from bson.objectid import ObjectId
    if isinstance(data, dict):
        return {k: sanitize_for_json(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_for_json(x) for x in data]
    elif isinstance(data, ObjectId):
        return str(data)
    elif isinstance(data, datetime):
        return data.isoformat()
    return data


@dashboard_bp.route("/")
@login_required
def index():
    """Main dashboard page."""
    try:
        snapshot = sync_equipment_state(debug=False)
        equipment_list = snapshot["equipment_list"]
        active_alerts = Alert.get_active_alerts()
        recent_predictions = Prediction.get_recent_predictions(limit=10)
        stats = {
            "total_equipment": snapshot["total_equipment"],
            "online": snapshot["counts"]["online"],
            "critical": snapshot["counts"]["critical"],
            "warning": snapshot["counts"]["warning"],
            "active_alerts": len(active_alerts),
        }
        
        return render_template(
            "dashboard/index.html",
            equipment_list=equipment_list,
            active_alerts=active_alerts[:5],  # Show top 5 alerts
            recent_predictions=recent_predictions[:10],
            stats=stats,
        )
    except Exception as e:
        print(f"Error loading dashboard: {e}")
        return render_template("dashboard/index.html", error=str(e))


@dashboard_bp.route("/equipment-status")
@login_required
def equipment_status():
    """Detailed equipment status page with charts and slicers."""
    sync_equipment_state(debug=False)
    return render_template("dashboard/equipment_status.html")


@dashboard_bp.route("/equipment/<equipment_id>")
@login_required
def equipment_detail(equipment_id):
    """Equipment detail page with full analytics."""
    try:
        # Get equipment
        equipment = Equipment.find_by_id(equipment_id)
        if not equipment:
            return render_template("error.html", message="Equipment not found"), 404
        
        # Get prediction history
        history = Prediction.get_equipment_history(equipment_id, limit=100)
        
        # Get trends
        trends = SensorSimulator.generate_trends(equipment.get("equipment_type", "Turbine"), hours=24)
        
        # Get alerts for this equipment
        equipment_alerts = Alert.get_active_alerts()
        equipment_alerts = [a for a in equipment_alerts if a.get("equipment_id") == equipment_id]
        
        return render_template(
            "dashboard/equipment_detail.html",
            equipment=equipment,
            history=history,
            trends=trends,
            alerts=equipment_alerts,
        )
    except Exception as e:
        print(f"Error loading equipment detail: {e}")
        return render_template("error.html", message=str(e)), 500


@dashboard_bp.route("/api/sensor-data/<equipment_id>", methods=["POST"])
@login_required
def get_sensor_data(equipment_id):
    """Get simulated sensor data and prediction for equipment."""
    try:
        # Get equipment
        equipment = Equipment.find_by_id(equipment_id)
        if not equipment:
            return jsonify({"error": "Equipment not found"}), 404
        
        # Generate sensor data
        equipment_type = equipment.get("equipment_type", "Turbine")
        is_failure = request.form.get("is_failure", "false").lower() == "true"
        sensors = SensorSimulator.generate_sensors(equipment_type, is_failure)
        
        # Make prediction
        try:
            prediction, probability = predict_equipment_failure(sensors)
        except:
            prediction = 0
            probability = 0.0
        
        # Calculate sensor-based health score
        sensor_health_score, _ = HealthScoreCalculator.calculate_health_score(sensors, equipment_type)

        # Blend sensor health with ML failure probability for consistency.
        # This ensures: if ML says 78% failure → health score reflects that, not 100%.
        ml_health = round((1.0 - probability) * 100.0, 2)
        health_score = round(sensor_health_score * 0.4 + ml_health * 0.6, 2)
        health_score = max(0.0, min(100.0, health_score))

        if health_score >= 80:
            health_status = "Healthy"
        elif health_score >= 50:
            health_status = "Caution"
        else:
            health_status = "Critical"

        # Get risk level
        risk_level = RiskLevelCalculator.calculate_risk_level(probability)
        risk_color = RiskLevelCalculator.get_risk_color(risk_level)

        # Get recommendations
        recommendations = RecommendationEngine.generate_recommendations(sensors)
        intelligence = build_equipment_intelligence(equipment_id)
        
        status_map = {"Low": "online", "Medium": "warning", "Critical": "critical"}
        equipment_status_value = status_map.get(risk_level, "online")

        # Store prediction in database
        try:
            Prediction.store_prediction(
                equipment_id,
                sensors,
                prediction,
                probability,
                risk_level,
                health_score=health_score,
                health_status=health_status,
                equipment_status=equipment_status_value,
            )
            
            # Create alert if critical
            if risk_level == "Critical":
                Alert.create_alert(
                    equipment_id,
                    "failure",
                    "Critical",
                    f"Equipment {equipment_id} detected failure risk: {probability*100:.1f}%",
                    f"Recommendations: {'; '.join([r['action'] for r in recommendations[:3]])}",
                )
            
            # Update equipment status through the centralized sync path.
            Equipment.update_status(equipment_id, equipment_status_value, health_score)
            sync_equipment_state(debug=True)
        except Exception as db_error:
            print(f"Database error: {db_error}")
        
        return jsonify(
            {
                "success": True,
                "equipment_id": equipment_id,
                "sensors": sensors,
                "prediction": "Equipment Failure Predicted" if prediction == 1 else "Equipment Working Normally",
                "prediction_value": prediction,
                "failure_probability": round(probability * 100, 2),
                "health_score": health_score,
                "health_status": health_status,
                "risk_level": risk_level,
                "risk_color": risk_color,
                "recommendations": recommendations,
                "intelligence": intelligence,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@dashboard_bp.route("/api/equipment-list")
@login_required
def get_equipment_list():
    """Get all equipment as JSON."""
    try:
        snapshot = sync_equipment_state(debug=False)
        equipment_list = snapshot["equipment_list"]
        return jsonify({
            "success": True,
            "data": [
                {
                    "id": str(eq.get("_id")),
                    "equipment_id": eq.get("equipment_id"),
                    "name": eq.get("equipment_name"),
                    "type": eq.get("equipment_type"),
                    "location": eq.get("location"),
                    "status": eq.get("status"),
                    "health_score": eq.get("health_score"),
                }
                for eq in equipment_list
            ],
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@dashboard_bp.route("/api/equipment/<equipment_id>", methods=["DELETE"])
@login_required
def delete_equipment(equipment_id):
    """Delete a single equipment and its related alerts/predictions."""
    try:
        deleted_equipment = Equipment.delete_by_equipment_id(equipment_id)
        deleted_predictions = Prediction.delete_by_equipment_id(equipment_id)
        deleted_alerts = Alert.delete_by_equipment_id(equipment_id)

        if not deleted_equipment:
            return jsonify({"success": False, "error": "Equipment not found"}), 404

        return jsonify(
            {
                "success": True,
                "message": f"Equipment {equipment_id} deleted",
                "deleted_predictions": deleted_predictions,
                "deleted_alerts": deleted_alerts,
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@dashboard_bp.route("/api/equipment", methods=["DELETE"])
@login_required
def delete_all_equipment_data():
    """Delete all equipment, predictions, and alerts used by dashboard."""
    try:
        removed_equipment = Equipment.delete_all()
        removed_predictions = Prediction.delete_all()
        removed_alerts = Alert.delete_all()

        return jsonify(
            {
                "success": True,
                "message": "All dashboard data deleted",
                "removed_equipment": removed_equipment,
                "removed_predictions": removed_predictions,
                "removed_alerts": removed_alerts,
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@dashboard_bp.route("/api/alerts")
@login_required
def get_alerts():
    """Get all active alerts."""
    try:
        sync_equipment_state(debug=False)
        alerts = Alert.get_active_alerts()
        return jsonify({
            "success": True,
            "data": [
                {
                    "id": str(alert.get("_id")),
                    "equipment_id": alert.get("equipment_id"),
                    "type": alert.get("alert_type"),
                    "severity": alert.get("severity"),
                    "message": alert.get("message"),
                    "created_at": alert.get("created_at").isoformat() if alert.get("created_at") else None,
                }
                for alert in alerts
            ],
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@dashboard_bp.route("/api/last-prediction-time")
@login_required
def get_last_prediction_time():
    """Return the timestamp of the most recent prediction (ISO format)."""
    try:
        recent = Prediction.get_recent_predictions(limit=1)
        if recent is not None and len(recent) > 0:
            ts = recent[0].get("timestamp")
            # Ensure ISO string
            try:
                if hasattr(ts, "isoformat"):
                    ts = ts.isoformat()
            except Exception:
                ts = str(ts)
            return jsonify({"success": True, "last_prediction": ts})
        return jsonify({"success": True, "last_prediction": None})
    except Exception as e:
        print(f"Error in get_last_prediction_time: {e}")
        return jsonify({"success": True, "last_prediction": None}), 200


@dashboard_bp.route("/api/recent-predictions")
@login_required
def get_recent_predictions():
    """Get normalized recent predictions for dashboard widgets."""
    try:
        predictions = Prediction.get_recent_predictions(limit=10)
        if predictions is None:
            predictions = []

        normalized = []
        for item in predictions:
            try:
                prediction_value = item.get("prediction_value", item.get("prediction"))

                prediction_text = item.get("prediction_text")
                if not prediction_text:
                    if isinstance(prediction_value, (int, float)):
                        prediction_text = (
                            "Equipment Failure Predicted" if int(prediction_value) == 1 else "Equipment Working Normally"
                        )
                    else:
                        prediction_text = str(item.get("prediction", "Unknown"))

                probability = item.get("failure_probability", item.get("probability", 0))
                try:
                    probability = float(probability)
                except (TypeError, ValueError):
                    probability = 0.0

                if probability <= 1:
                    probability = probability * 100

                risk_level = normalize_risk_level(item.get("risk_level"))
                health_status = derive_health_status(item)
                equipment_status = derive_equipment_status(item)

                timestamp = item.get("timestamp")
                if hasattr(timestamp, "isoformat"):
                    timestamp = timestamp.isoformat()
                else:
                    timestamp = str(timestamp)

                normalized.append(
                    {
                        "id": str(item.get("_id", "unknown")),
                        "equipment_id": item.get("equipment_id", "N/A"),
                        "prediction_text": prediction_text,
                        "prediction_value": prediction_value,
                        "failure_probability": round(probability, 2),
                        "risk_level": risk_level,
                        "health_status": health_status,
                        "equipment_status": equipment_status,
                        "timestamp": timestamp,
                    }
                )
            except Exception as item_error:
                print(f"Error processing prediction item: {item_error}")
                continue

        return jsonify({"success": True, "data": normalized})
    except Exception as e:
        print(f"Error in get_recent_predictions: {e}")
        return jsonify({"success": True, "data": []}), 200


@dashboard_bp.route("/api/analytics")
@login_required
def get_analytics():
    """Get dashboard analytics data."""
    try:
        snapshot = sync_equipment_state(debug=False)
        equipment_list = snapshot["equipment_list"]
        predictions = Prediction.get_recent_predictions(limit=100)
        
        total_equipment = snapshot["total_equipment"]
        critical_count = snapshot["counts"]["critical"]
        warning_count = snapshot["counts"]["warning"]
        online_count = snapshot["counts"]["online"]
        
        # Failure rate
        failure_count = sum(1 for p in predictions if p.get("prediction") == 1)
        failure_rate = (failure_count / len(predictions)) * 100 if predictions else 0
        
        # Average health score
        avg_health = sum(eq.get("health_score", 0) for eq in equipment_list) / total_equipment if equipment_list else 0
        
        return jsonify({
            "success": True,
            "total_equipment": total_equipment,
            "online": online_count,
            "warning": warning_count,
            "critical": critical_count,
            "failure_rate": round(failure_rate, 2),
            "average_health_score": round(avg_health, 2),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@dashboard_bp.route("/api/intelligence")
@login_required
def get_platform_intelligence():
    """Return advanced fleet intelligence for the dashboard."""
    try:
        sync_equipment_state(debug=False)
        selected_id = request.args.get("selected_id")
        return jsonify({"success": True, "data": sanitize_for_json(build_platform_intelligence(selected_id=selected_id))})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@dashboard_bp.route("/api/intelligence/<equipment_id>")
@login_required
def get_equipment_intelligence(equipment_id):
    """Return advanced intelligence for a single equipment."""
    try:
        sync_equipment_state(debug=False)
        return jsonify({"success": True, "data": sanitize_for_json(build_equipment_intelligence(equipment_id))})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@dashboard_bp.route("/api/report/equipment/<equipment_id>")
@login_required
def download_equipment_report(equipment_id):
    """Generate and download a PDF report for a specific equipment."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

        equipment = Equipment.find_by_id(equipment_id)
        history = Prediction.get_equipment_history(equipment_id, limit=20)

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle('Title', parent=styles['Title'], textColor=colors.HexColor('#00d4ff'), fontName='Helvetica-Bold', spaceAfter=12)
        body_style = ParagraphStyle('Body', parent=styles['BodyText'], textColor=colors.HexColor('#1a1f3a'), leading=14)

        story = []
        eq_name = equipment.get('equipment_name', equipment_id) if equipment else equipment_id
        story.append(Paragraph(f"Equipment Report: {eq_name}", title_style))
        story.append(Paragraph(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", body_style))
        story.append(Spacer(1, 12))

        if equipment:
            info_rows = [
                ['Equipment ID', str(equipment.get('equipment_id', 'N/A'))],
                ['Name', str(equipment.get('equipment_name', 'N/A'))],
                ['Type', str(equipment.get('equipment_type', 'N/A'))],
                ['Location', str(equipment.get('location', 'N/A'))],
                ['Status', str(equipment.get('status', 'N/A'))],
                ['Health Score', f"{equipment.get('health_score', 0)}%"],
            ]
            info_table = Table(info_rows, colWidths=[2 * inch, 4 * inch])
            info_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e6f7ff')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#102138')),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#c7d5e6')),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('PADDING', (0, 0), (-1, -1), 8),
            ]))
            story.append(info_table)
            story.append(Spacer(1, 14))

        if history:
            story.append(Paragraph("Prediction History (Last 20 Records)", styles['Heading2']))
            story.append(Spacer(1, 8))
            pred_rows = [['Timestamp', 'Prediction', 'Risk Level', 'Probability']]
            for pred in history[:20]:
                ts = pred.get('timestamp', '')
                ts_str = ts.strftime('%Y-%m-%d %H:%M') if hasattr(ts, 'strftime') else str(ts)[:16]
                pred_val = pred.get('prediction_value', pred.get('prediction', 0))
                try:
                    pred_val = int(pred_val)
                except (TypeError, ValueError):
                    pred_val = 0
                pred_text = 'Failure Predicted' if pred_val == 1 else 'Normal'
                prob = pred.get('failure_probability', pred.get('probability', 0))
                try:
                    prob = float(prob)
                except (TypeError, ValueError):
                    prob = 0.0
                prob_display = f"{prob * 100:.1f}%" if prob <= 1 else f"{prob:.1f}%"
                pred_rows.append([ts_str, pred_text, str(pred.get('risk_level', 'Low')), prob_display])

            pred_table = Table(pred_rows, colWidths=[1.8 * inch, 2.0 * inch, 1.2 * inch, 1.1 * inch])
            pred_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#00d4ff')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#102138')),
                ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#c7d5e6')),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('PADDING', (0, 0), (-1, -1), 6),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f4f8fc')]),
            ]))
            story.append(pred_table)
        else:
            story.append(Paragraph("No prediction history available.", body_style))

        doc.build(story)
        buffer.seek(0)
        filename = f"equipment-report-{equipment_id}-{datetime.utcnow().strftime('%Y%m%d')}.pdf"
        return send_file(buffer, as_attachment=True, download_name=filename, mimetype='application/pdf')
    except Exception as e:
        print(f"Error generating equipment report: {e}")
        return jsonify({"error": str(e)}), 500


@dashboard_bp.route("/api/chat", methods=["POST"])
@login_required
def chat_assistant():
    """AI chat assistant endpoint."""
    try:
        data = request.get_json() or {}
        message = data.get("message", "").strip()
        context = data.get("context", {})

        if not message:
            return jsonify({"success": False, "error": "No message provided"}), 400

        response = AIChatAssistant.chat(message, context)
        return jsonify({"success": True, "response": response})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@dashboard_bp.route("/api/anomalies/<equipment_id>")
@login_required
def get_anomalies(equipment_id):
    """Get anomalies for specific equipment."""
    try:
        anomalies = AnomalyDetector.detect_equipment_anomalies(equipment_id)
        return jsonify({"success": True, "data": anomalies})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@dashboard_bp.route("/api/anomalies/fleet")
@login_required
def get_fleet_anomalies():
    """Get fleet-wide anomalies."""
    try:
        anomalies = AnomalyDetector.detect_fleet_anomalies()
        return jsonify({"success": True, "data": anomalies})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@dashboard_bp.route("/api/comparison", methods=["POST"])
@login_required
def compare_equipment():
    """Compare multiple equipment."""
    try:
        data = request.get_json() or {}
        equipment_ids = data.get("equipment_ids", [])

        if not equipment_ids or len(equipment_ids) < 2:
            return jsonify({"success": False, "error": "Need at least 2 equipment IDs"}), 400

        comparison = EquipmentComparison.compare_equipment(equipment_ids)
        recommendations = EquipmentComparison.get_comparison_recommendations(comparison.get("data", []))
        comparison["recommendations"] = recommendations

        return jsonify({"success": True, "data": comparison})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@dashboard_bp.route("/api/cost/<equipment_id>")
@login_required
def get_downtime_cost(equipment_id):
    """Get downtime cost estimation."""
    try:
        cost = DowntimeCostEstimator.estimate_equipment_cost(equipment_id)
        return jsonify({"success": True, "data": cost})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@dashboard_bp.route("/api/cost/fleet")
@login_required
def get_fleet_cost():
    """Get fleet-wide cost estimation."""
    try:
        cost = DowntimeCostEstimator.estimate_fleet_cost()
        return jsonify({"success": True, "data": cost})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@dashboard_bp.route("/api/search", methods=["GET", "POST"])
@login_required
def search_equipment():
    """Advanced search and filtering."""
    try:
        if request.method == "POST":
            data = request.get_json() or {}
        else:
            data = request.args.to_dict()

        query = data.get("q", "")
        filters = {
            "status": data.getlist("status") if hasattr(data, "getlist") else data.get("status"),
            "risk_levels": data.getlist("risk_levels") if hasattr(data, "getlist") else data.get("risk_levels"),
            "equipment_types": data.getlist("equipment_types") if hasattr(data, "getlist") else data.get("equipment_types"),
            "locations": data.getlist("locations") if hasattr(data, "getlist") else data.get("locations"),
            "health_score_min": float(data.get("health_score_min", 0)) if data.get("health_score_min") else None,
            "health_score_max": float(data.get("health_score_max", 100)) if data.get("health_score_max") else None,
            "sort_by": data.get("sort_by", "health_score"),
            "sort_order": data.get("sort_order", "desc"),
        }
        filters = {k: v for k, v in filters.items() if v is not None}

        results = AdvancedSearch.search_equipment(query, filters)
        return jsonify({"success": True, "data": results})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@dashboard_bp.route("/api/search/filters")
@login_required
def get_search_filters():
    """Get available search filters."""
    try:
        filters = AdvancedSearch.get_available_filters()
        return jsonify({"success": True, "data": filters})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
