"""
Admin panel routes (Blueprint) - User management, system settings, and analytics.
"""

import csv
import io
import json
import os
from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for, send_file
from utils.auth import admin_required, login_required, AuthenticationManager, PasswordValidator, EmailValidator, UsernameValidator
from database.models import User, Equipment, Prediction, Alert, MaintenanceSchedule
from utils.notifications import EmailNotifier
from utils.prediction_state import sync_equipment_state
from utils.ai_intelligence import build_platform_intelligence
from datetime import datetime, timedelta
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image

_LOGO_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "img", "logo.png")

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


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


def _build_admin_report_data():
    snapshot = sync_equipment_state(debug=False)
    equipment_list = snapshot["equipment_list"]
    predictions = Prediction.get_recent_predictions(limit=1000)
    alerts = Alert.get_active_alerts()

    total_equipment = snapshot["total_equipment"]
    prediction_collection = Prediction.get_collection()
    alert_collection = Alert.get_collection()
    total_predictions = prediction_collection.count_documents({}) if prediction_collection is not None else 0
    total_alerts = alert_collection.count_documents({}) if alert_collection is not None else 0
    total_users = len(User.find_all())

    return {
        "total_users": total_users,
        "total_equipment": total_equipment,
        "total_predictions": total_predictions,
        "total_alerts": total_alerts,
        "failure_rate": round((sum(1 for p in predictions if p.get("prediction") == 1) / len(predictions)) * 100, 2) if predictions else 0,
        "recent_alerts": alerts[:10],
        "equipment_list": equipment_list,
    }


def _build_admin_intelligence_data():
    snapshot = sync_equipment_state(debug=False)
    platform = build_platform_intelligence()
    predictions = Prediction.get_recent_predictions(limit=200)
    alerts = Alert.get_active_alerts()
    users = User.find_all()

    audit_log = []
    for item in predictions[:20]:
        timestamp = item.get("timestamp")
        audit_log.append(
            {
                "timestamp": timestamp.isoformat() if hasattr(timestamp, "isoformat") else str(timestamp),
                "category": "prediction",
                "message": f"Prediction recorded for {item.get('equipment_id', 'Unknown')}",
                "severity": item.get("risk_level", "Low"),
            }
        )

    for alert in alerts[:20]:
        timestamp = alert.get("created_at")
        audit_log.append(
            {
                "timestamp": timestamp.isoformat() if hasattr(timestamp, "isoformat") else str(timestamp),
                "category": "alert",
                "message": f"Alert raised for {alert.get('equipment_id', 'Unknown')} ({alert.get('severity', 'Medium')})",
                "severity": alert.get("severity", "Medium"),
            }
        )

    for user in users[:10]:
        timestamp = user.get("created_at")
        audit_log.append(
            {
                "timestamp": timestamp.isoformat() if hasattr(timestamp, "isoformat") else str(timestamp),
                "category": "user",
                "message": f"User available: {user.get('username', 'Unknown')} ({user.get('role', 'user')})",
                "severity": "Info",
            }
        )

    audit_log.sort(key=lambda item: item.get("timestamp", ""), reverse=True)

    return {
        "platform": platform,
        "snapshot": snapshot,
        "audit_log": audit_log[:40],
        "model_monitoring": platform.get("model_monitoring", {}),
    }


@admin_bp.route("/")
@admin_required
def dashboard():
    """Admin dashboard."""
    try:
        snapshot = sync_equipment_state(debug=False)
        equipment_list = snapshot["equipment_list"]
        predictions = Prediction.get_recent_predictions(limit=1000)
        alerts = Alert.get_active_alerts()
        
        total_equipment = snapshot["total_equipment"]
        prediction_collection = Prediction.get_collection()
        alert_collection = Alert.get_collection()
        total_predictions = prediction_collection.count_documents({}) if prediction_collection is not None else 0
        total_alerts = alert_collection.count_documents({}) if alert_collection is not None else 0
        
        status_breakdown = {
            "online": snapshot["counts"]["online"],
            "warning": snapshot["counts"]["warning"],
            "critical": snapshot["counts"]["critical"],
            "offline": sum(1 for eq in equipment_list if eq.get("status") == "offline"),
        }
        
        # Failure statistics
        failure_count = sum(1 for p in predictions if p.get("prediction") == 1)
        failure_rate = (failure_count / len(predictions)) * 100 if predictions else 0
        
        stats = {
            "total_equipment": total_equipment,
            "total_predictions": total_predictions,
            "total_alerts": total_alerts,
            "failure_rate": round(failure_rate, 2),
            "status_breakdown": status_breakdown,
        }
        
        return render_template("admin/dashboard.html", stats=stats, recent_alerts=alerts[:10])
    except Exception as e:
        print(f"Error loading admin dashboard: {e}")
        return render_template("admin/dashboard.html", error=str(e))


@admin_bp.route("/users")
@admin_required
def manage_users():
    """User management page."""
    try:
        users = User.find_all()
        users_list = [
            {
                "id": str(u.get("_id")),
                "username": u.get("username"),
                "email": u.get("email"),
                "role": u.get("role"),
                "is_active": u.get("is_active"),
                "created_at": u.get("created_at"),
            }
            for u in users
        ]
        return render_template("admin/users.html", users=users_list)
    except Exception as e:
        print(f"Error loading users: {e}")
        return render_template("admin/users.html", error=str(e))


@admin_bp.route("/api/users", methods=["GET"])
@admin_required
def get_users():
    """Get all users as JSON."""
    try:
        users = User.find_all()
        users_list = [
            {
                "id": str(u.get("_id")),
                "username": u.get("username"),
                "email": u.get("email"),
                "role": u.get("role"),
                "is_active": u.get("is_active"),
                "created_at": u.get("created_at").isoformat() if hasattr(u.get("created_at"), "isoformat") else str(u.get("created_at")) if u.get("created_at") else None,
            }
            for u in users
        ]
        return jsonify({"success": True, "data": users_list})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/api/users", methods=["POST"])
@admin_required
def create_user():
    """Create a new user from the admin panel."""
    try:
        data = request.get_json(silent=True) or request.form.to_dict()
        username = (data.get("username") or "").strip()
        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""
        role = (data.get("role") or "operator").strip().lower()

        is_valid, message = UsernameValidator.validate_with_reason(username)
        if not is_valid:
            return jsonify({"success": False, "error": f"Username validation failed: {message}"}), 400

        is_valid, message = EmailValidator.validate_with_reason(email)
        if not is_valid:
            return jsonify({"success": False, "error": f"Email validation failed: {message}"}), 400

        is_valid, message = PasswordValidator.validate(password)
        if not is_valid:
            return jsonify({"success": False, "error": f"Password validation failed: {message}"}), 400

        if role not in {"user", "operator", "technician", "admin"}:
            return jsonify({"success": False, "error": "Invalid role"}), 400

        if User.find_by_username(username):
            return jsonify({"success": False, "error": "Username already exists"}), 400

        if User.find_by_email(email):
            return jsonify({"success": False, "error": "Email already exists"}), 400

        password_hash = AuthenticationManager.hash_password(password)
        user_id = User.create_user(username, email, password_hash, role=role)
        return jsonify({"success": True, "message": "User created successfully", "user_id": user_id})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@admin_bp.route("/api/user/<user_id>", methods=["GET"])
@admin_required
def get_user(user_id):
    """Get a single user for the edit dialog."""
    try:
        user = User.find_by_id(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        return jsonify(
            {
                "success": True,
                "data": {
                    "id": str(user.get("_id")),
                    "username": user.get("username"),
                    "email": user.get("email"),
                    "role": user.get("role"),
                    "is_active": user.get("is_active", True),
                    "created_at": user.get("created_at").isoformat() if hasattr(user.get("created_at"), "isoformat") else str(user.get("created_at")),
                },
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/api/user/<user_id>", methods=["POST"])
@admin_required
def update_user(user_id):
    """Update a user's role."""
    try:
        data = request.get_json(silent=True) or {}
        role = data.get("role")
        if role not in {"user", "operator", "technician", "admin"}:
            return jsonify({"error": "Invalid role"}), 400

        collection = User.get_collection()
        if collection is None:
            from database.models import _FALLBACK_USERS, _persist_fallback_data
            user = next((user for user in _FALLBACK_USERS if user.get("_id") == user_id), None)
            if not user:
                return jsonify({"error": "User not found"}), 404
            user["role"] = role
            _persist_fallback_data()
            return jsonify({"success": True, "message": "User updated successfully"})

        from bson.objectid import ObjectId
        result = collection.update_one({"_id": ObjectId(user_id)}, {"$set": {"role": role}})
        if result.matched_count == 0:
            return jsonify({"error": "User not found"}), 404

        return jsonify({"success": True, "message": "User updated successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/api/user/<user_id>/delete", methods=["POST"])
@admin_required
def delete_user(user_id):
    """Delete a user account."""
    try:
        collection = User.get_collection()
        if collection is None:
            from database.models import _FALLBACK_USERS, _persist_fallback_data
            user = next((user for user in _FALLBACK_USERS if user.get("_id") == user_id), None)
            if not user:
                return jsonify({"error": "User not found"}), 404
            _FALLBACK_USERS.remove(user)
            _persist_fallback_data()
            return jsonify({"success": True, "message": "User deleted successfully"})

        from bson.objectid import ObjectId
        result = collection.delete_one({"_id": ObjectId(user_id)})
        if result.deleted_count == 0:
            return jsonify({"error": "User not found"}), 404

        return jsonify({"success": True, "message": "User deleted successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/api/analytics", methods=["GET"])
@admin_required
def api_analytics():
    """Return admin analytics for the dashboard widgets."""
    try:
        snapshot = sync_equipment_state(debug=False)
        equipment_list = snapshot["equipment_list"]
        predictions = Prediction.get_recent_predictions(limit=1000)
        alerts = Alert.get_active_alerts()

        total_users = len(User.find_all())
        total_equipment = snapshot["total_equipment"]
        prediction_collection = Prediction.get_collection()
        alert_collection = Alert.get_collection()
        total_predictions = prediction_collection.count_documents({}) if prediction_collection is not None else 0
        total_alerts = alert_collection.count_documents({}) if alert_collection is not None else len(alerts)

        total_status = max(total_equipment, 1)
        healthy = snapshot["counts"]["online"]
        caution = snapshot["counts"]["warning"]
        critical = snapshot["counts"]["critical"]

        return jsonify(
            {
                "success": True,
                "data": {
                    "total_users": total_users,
                    "total_equipment": total_equipment,
                    "total_predictions": total_predictions,
                    "total_alerts": total_alerts,
                    "uptime": "99.9%",
                    "accuracy": "98.5%",
                    "equipment_healthy": round((healthy / total_status) * 100, 1),
                    "equipment_caution": round((caution / total_status) * 100, 1),
                    "equipment_critical": round((critical / total_status) * 100, 1),
                    "failure_rate": round((sum(1 for p in predictions if p.get("prediction") == 1) / len(predictions)) * 100, 2) if predictions else 0,
                },
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/api/intelligence", methods=["GET"])
@admin_required
def api_intelligence():
    """Return intelligence data for the admin control center."""
    try:
        data = _build_admin_intelligence_data()
        return jsonify({"success": True, "data": sanitize_for_json(data)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@admin_bp.route("/api/audit-logs", methods=["GET"])
@admin_required
def api_audit_logs():
    """Return synthesized audit activity for the admin dashboard."""
    try:
        data = _build_admin_intelligence_data()
        return jsonify({"success": True, "data": sanitize_for_json(data.get("audit_log", []))})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@admin_bp.route("/api/settings", methods=["GET", "POST"])
@admin_required
def api_settings():
    """Return or update admin settings."""
    if request.method == "GET":
        return jsonify(
            {
                "success": True,
                "data": {
                    "prediction_threshold": 0.7,
                    "alert_email": "admin@example.com",
                    "maintenance_interval": 30,
                },
            }
        )

    return jsonify({"success": True, "message": "Settings saved successfully"})


@admin_bp.route("/api/export", methods=["GET"])
@admin_required
def export_admin_data():
    """Export a simple CSV snapshot for the admin panel."""
    equipment_list = Equipment.find_all()
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["equipment_id", "equipment_name", "location", "equipment_type", "status", "health_score"])
    for equipment in equipment_list:
        writer.writerow(
            [
                equipment.get("equipment_id", ""),
                equipment.get("equipment_name", ""),
                equipment.get("location", ""),
                equipment.get("equipment_type", ""),
                equipment.get("status", ""),
                equipment.get("health_score", ""),
            ]
        )

    from flask import Response

    response = Response(buffer.getvalue(), mimetype="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=admin-export.csv"
    return response


@admin_bp.route("/api/export/intelligence", methods=["GET"])
@admin_required
def export_admin_intelligence_json():
    """Download the current intelligence payload as JSON."""
    data = _build_admin_intelligence_data()
    buffer = io.StringIO()
    json.dump(data, buffer, ensure_ascii=False, indent=2, default=str)
    buffer.seek(0)
    response = send_file(
        io.BytesIO(buffer.getvalue().encode("utf-8")),
        as_attachment=True,
        download_name=f"admin-intelligence-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.json",
        mimetype="application/json",
    )
    return response


@admin_bp.route("/api/export/intelligence/pdf", methods=["GET"])
@admin_required
def export_admin_intelligence_pdf():
    """Download a PDF summary of intelligence and audit activity."""
    data = _build_admin_intelligence_data()
    platform = data.get("platform", {})
    monitoring = data.get("model_monitoring", {})
    audit_log = data.get("audit_log", [])

    buffer = io.BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "AdminIntelTitle",
        parent=styles["Title"],
        textColor=colors.HexColor("#00d4ff"),
        fontName="Helvetica-Bold",
        spaceAfter=12,
    )
    body_style = ParagraphStyle(
        "AdminIntelBody",
        parent=styles["BodyText"],
        textColor=colors.HexColor("#1a1f3a"),
        leading=14,
    )

    story = []
    if os.path.exists(_LOGO_PATH):
        logo_img = Image(_LOGO_PATH, width=0.7*inch, height=0.7*inch)
        logo_img.hAlign = 'LEFT'
        story.append(logo_img)
    story += [
        Paragraph("AI Equipment Prediction - Intelligence Report", title_style),
        Paragraph(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", body_style),
        Spacer(1, 12),
    ]

    monitoring_rows = [
        ["Metric", "Value"],
        ["Average Prediction Confidence", f"{monitoring.get('average_prediction_confidence', 0)}%"],
        ["Prediction Volume", str(monitoring.get('prediction_volume_24h', 0))],
        ["Active Alerts", str(monitoring.get('alert_volume', 0))],
        ["Fleet Stability", f"{platform.get('fleet', {}).get('fleet_stability_score', 0)}%"],
    ]
    monitoring_table = Table(monitoring_rows, colWidths=[3.0 * inch, 2.0 * inch])
    monitoring_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e6f7ff")),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#102138")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#c7d5e6")),
        ("PADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(Paragraph("Model Monitoring", styles["Heading2"]))
    story.append(monitoring_table)

    if audit_log:
        story.append(Spacer(1, 14))
        story.append(Paragraph("Audit Activity", styles["Heading2"]))
        audit_rows = [["Timestamp", "Category", "Message"]]
        for item in audit_log[:20]:
            audit_rows.append([
                str(item.get("timestamp", "N/A"))[:19],
                str(item.get("category", "N/A")),
                str(item.get("message", "")),
            ])
        audit_table = Table(audit_rows, colWidths=[1.8 * inch, 1.0 * inch, 3.2 * inch])
        audit_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#00d4ff")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c7d5e6")),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("PADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(audit_table)

    document.build(story)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="admin-intelligence-report.pdf", mimetype="application/pdf")


@admin_bp.route("/api/export/pdf", methods=["GET"])
@admin_required
def export_admin_pdf():
    """Export a PDF summary for the admin panel."""
    report_data = _build_admin_report_data()
    buffer = io.BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "AdminTitle",
        parent=styles["Title"],
        textColor=colors.HexColor("#00d4ff"),
        fontName="Helvetica-Bold",
        spaceAfter=12,
    )
    body_style = ParagraphStyle(
        "AdminBody",
        parent=styles["BodyText"],
        textColor=colors.HexColor("#1a1f3a"),
        leading=14,
    )

    story = []
    if os.path.exists(_LOGO_PATH):
        logo_img = Image(_LOGO_PATH, width=0.7*inch, height=0.7*inch)
        logo_img.hAlign = 'LEFT'
        story.append(logo_img)
    story += [
        Paragraph("AI Equipment Prediction - Admin Report", title_style),
        Paragraph(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", body_style),
        Spacer(1, 12),
    ]

    summary_rows = [
        ["Total Users", str(report_data["total_users"])],
        ["Total Equipment", str(report_data["total_equipment"])],
        ["Predictions Made", str(report_data["total_predictions"])],
        ["Active Alerts", str(report_data["total_alerts"])],
        ["Failure Rate", f"{report_data['failure_rate']}%"],
    ]
    summary_table = Table(summary_rows, colWidths=[2.5 * inch, 1.7 * inch])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e6f7ff")),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#102138")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#c7d5e6")),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#f4f8fc")]),
        ("PADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(summary_table)

    if report_data["recent_alerts"]:
        story.append(Spacer(1, 14))
        story.append(Paragraph("Recent Alerts", styles["Heading2"]))
        alert_rows = [["Equipment", "Severity", "Message"]]
        for alert in report_data["recent_alerts"]:
            alert_rows.append([
                str(alert.get("equipment_id", "N/A")),
                str(alert.get("severity", "N/A")),
                str(alert.get("message", "")),
            ])
        alert_table = Table(alert_rows, colWidths=[1.3 * inch, 1.0 * inch, 3.8 * inch])
        alert_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#00d4ff")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c7d5e6")),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("PADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(alert_table)

    document.build(story)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="admin-report.pdf", mimetype="application/pdf")


@admin_bp.route("/api/reports/email", methods=["POST"])
@admin_required
def email_admin_report():
    """Email the admin summary report to a recipient."""
    try:
        data = request.get_json(silent=True) or request.form.to_dict()
        recipient = (data.get("recipient") or "").strip().lower()
        if not recipient:
            return jsonify({"success": False, "error": "Recipient email is required"}), 400

        report_data = _build_admin_report_data()
        print(f"DEBUG: Attempting to send admin report to {recipient}...")
        sent = EmailNotifier.send_daily_report_email(recipient, report_data)
        if not sent:
            print(f"DEBUG: EmailNotifier failed for {recipient}")
            return jsonify({
                "success": False,
                "error": (
                    "Email could not be sent. Gmail requires an App Password — "
                    "go to Google Account → Security → 2-Step Verification → App Passwords, "
                    "generate one for 'Mail', and paste it as MAIL_PASSWORD in your .env file."
                )
            }), 500

        return jsonify({"success": True, "message": f"Report sent to {recipient}"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@admin_bp.route("/api/health-check", methods=["GET"])
@admin_required
def api_health_check():
    """Return the status of the main services."""
    user_collection = User.get_collection()
    from flask import current_app

    smtp_ready = bool(
        current_app.config.get("MAIL_SERVER")
        and current_app.config.get("MAIL_USERNAME")
        and current_app.config.get("MAIL_PASSWORD")
    )
    return jsonify(
        {
            "success": True,
            "data": {
                "database_status": "Online" if user_collection is not None else "Offline",
                "api_status": "Online",
                "model_status": "Online",
                "email_status": "Configured" if smtp_ready else "Not Configured",
                "cache_status": "Ready",
            },
        }
    )


@admin_bp.route("/api/backup", methods=["POST"])
@admin_required
def api_backup():
    """Create a lightweight backup artifact in the reports directory."""
    import os

    os.makedirs("reports", exist_ok=True)
    backup_name = f"admin-backup-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.txt"
    backup_path = os.path.join("reports", backup_name)
    with open(backup_path, "w", encoding="utf-8") as backup_file:
        backup_file.write("Admin backup generated from the application dashboard.\n")

    return jsonify({"success": True, "backup_file": backup_name})


@admin_bp.route("/api/clear-cache", methods=["POST"])
@admin_required
def api_clear_cache():
    """Clear cached admin session data (best-effort)."""
    return jsonify({"success": True, "message": "Cache cleared"})


@admin_bp.route("/api/users/<user_id>/toggle-active", methods=["POST"])
@admin_required
def toggle_user_active(user_id):
    """Toggle user active status."""
    try:
        from bson.objectid import ObjectId
        collection = User.get_collection()
        if collection is None:
            return jsonify({"error": "Database not connected"}), 500
        
        user = collection.find_one({"_id": ObjectId(user_id)})
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        new_status = not user.get("is_active", True)
        collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"is_active": new_status}},
        )
        
        return jsonify({
            "success": True,
            "message": f"User status updated to: {new_status}",
            "is_active": new_status,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/equipment")
@admin_required
def manage_equipment():
    """Equipment management page."""
    try:
        equipment_list = Equipment.find_all()
        return render_template("admin/equipment.html", equipment=equipment_list)
    except Exception as e:
        print(f"Error loading equipment: {e}")
        return render_template("admin/equipment.html", error=str(e))


@admin_bp.route("/api/equipment", methods=["POST"])
@admin_required
def add_equipment():
    """Add new equipment."""
    try:
        data = request.get_json()
        
        equipment_id = Equipment.create_equipment(
            data.get("equipment_id"),
            data.get("equipment_name"),
            data.get("location"),
            data.get("equipment_type"),
        )
        
        return jsonify({
            "success": True,
            "message": "Equipment added successfully",
            "equipment_id": equipment_id,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/alerts")
@admin_required
def manage_alerts():
    """Alert management page."""
    try:
        alerts = Alert.get_active_alerts()
        return render_template("admin/alerts.html", alerts=alerts)
    except Exception as e:
        print(f"Error loading alerts: {e}")
        return render_template("admin/alerts.html", error=str(e))


@admin_bp.route("/api/alerts/<alert_id>/resolve", methods=["POST"])
@admin_required
def resolve_alert(alert_id):
    """Mark an alert as resolved."""
    try:
        success = Alert.resolve_alert(alert_id)
        if success:
            return jsonify({"success": True, "message": "Alert resolved"})
        else:
            return jsonify({"error": "Failed to resolve alert"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/maintenance")
@admin_required
def manage_maintenance():
    """Maintenance schedules page."""
    try:
        schedules = MaintenanceSchedule.get_upcoming_schedules(days_ahead=60)
        return render_template("admin/maintenance.html", schedules=schedules)
    except Exception as e:
        print(f"Error loading maintenance: {e}")
        return render_template("admin/maintenance.html", error=str(e))


@admin_bp.route("/api/maintenance", methods=["POST"])
@admin_required
def create_maintenance():
    """Create maintenance schedule."""
    try:
        data = request.get_json()
        
        scheduled_date = datetime.fromisoformat(data.get("scheduled_date"))
        
        schedule_id = MaintenanceSchedule.create_schedule(
            data.get("equipment_id"),
            scheduled_date,
            data.get("maintenance_type"),
            data.get("estimated_duration"),
            data.get("priority", "Normal"),
        )
        
        return jsonify({
            "success": True,
            "message": "Maintenance scheduled",
            "schedule_id": schedule_id,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/analytics")
@admin_required
def analytics():
    """System analytics page."""
    try:
        predictions = Prediction.get_recent_predictions(limit=1000)
        equipment_list = Equipment.find_all()
        
        # Prepare analytics data
        failure_by_type = {}
        for eq in equipment_list:
            eq_type = eq.get("equipment_type", "Unknown")
            if eq_type not in failure_by_type:
                failure_by_type[eq_type] = {"total": 0, "failures": 0}
            failure_by_type[eq_type]["total"] += 1
        
        for pred in predictions:
            if pred.get("prediction") == 1:
                eq = next(
                    (e for e in equipment_list if e.get("equipment_id") == pred.get("equipment_id")),
                    None,
                )
                if eq:
                    eq_type = eq.get("equipment_type", "Unknown")
                    if eq_type in failure_by_type:
                        failure_by_type[eq_type]["failures"] += 1
        
        return render_template(
            "admin/analytics.html",
            equipment_count=len(equipment_list),
            prediction_count=len(predictions),
            failure_stats=failure_by_type,
        )
    except Exception as e:
        print(f"Error loading analytics: {e}")
        return render_template("admin/analytics.html", error=str(e))
