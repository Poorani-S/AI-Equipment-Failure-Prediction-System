"""
Main Flask Application - AI-Powered Industrial Equipment Failure Prediction System
Enterprise-level production-ready application with modular architecture.
"""

import os
from datetime import timedelta
from flask import Flask, render_template, redirect, url_for, jsonify, request
from flask_login import LoginManager
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Ensure the enterprise app uses the Atlas database by default.
os.environ.setdefault(
    "MONGODB_URI",
    "mongodb+srv://241cd030_db_user:poorani123@equipmentpredictionsyst.8ptxg06.mongodb.net/?appName=equipmentpredictionsystem",
)

# Import blueprints
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.admin import admin_bp
from database.models import User, Equipment, Prediction, init_db
from utils.notifications import mail
from utils.auth import AuthenticationManager
from utils.prediction_state import sync_equipment_state
from utils.monitoring import HealthScoreCalculator, RiskLevelCalculator
from model import FEATURE_COLUMNS, predict_equipment_failure
from datetime import datetime, timezone

# Initialize Flask app
app = Flask(__name__)

# Configuration
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production-12345!")
app.config["AUTH_SESSION_VERSION"] = os.urandom(16).hex()
app.config["SESSION_COOKIE_SECURE"] = False  # Set to True in production with HTTPS
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)
app.config.update(
    MAIL_SERVER=os.getenv("MAIL_SERVER", "smtp.gmail.com"),
    MAIL_PORT=int(os.getenv("MAIL_PORT", "587")),
    MAIL_USE_TLS=os.getenv("MAIL_USE_TLS", "true").lower() == "true",
    MAIL_USE_SSL=os.getenv("MAIL_USE_SSL", "false").lower() == "true",
    MAIL_USERNAME=os.getenv("MAIL_USERNAME", "poorani0307@gmail.com"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD", "Poor@ni0307@."),
    MAIL_DEFAULT_SENDER=os.getenv("MAIL_DEFAULT_SENDER", "poorani0307@gmail.com"),
)

# Initialize database
init_db()
mail.init_app(app)

# Register safe_url_for function for templates
def safe_url_for(endpoint, **kwargs):
    """Safely generate URLs, returning '#' if endpoint doesn't exist."""
    try:
        from flask import url_for as flask_url_for
        return flask_url_for(endpoint, **kwargs)
    except:
        return '#'

app.jinja_env.globals.update(safe_url_for=safe_url_for)

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(admin_bp)


# Redirect helpers for common paths (handle missing trailing slashes)
@app.route("/dashboard")
def dashboard_redirect():
    """Redirect /dashboard to /dashboard/"""
    return redirect(url_for("dashboard.index"))


# Fallback routes: if blueprints failed to register (e.g., import error), provide
# safe read-only routes so the UI pages still load for testing.
def _add_fallback_routes(app):
    from flask import render_template

    if "dashboard.index" not in app.view_functions:
        @app.route("/dashboard/")
        def _fallback_dashboard():
            return render_template("dashboard/index.html")

    if "auth.login" not in app.view_functions:
        @app.route("/auth/login")
        def _fallback_login():
            return render_template("auth/login.html")

        @app.route("/auth/login/")
        def _fallback_login_slash():
            return render_template("auth/login.html")

    if "admin.dashboard" not in app.view_functions:
        @app.route("/admin/")
        def _fallback_admin():
            return render_template("admin/dashboard.html")

        @app.route("/admin")
        def _fallback_admin_no_slash():
            return render_template("admin/dashboard.html")


_add_fallback_routes(app)


@app.route('/__routes')
def _list_routes():
    """Return registered URL rules for diagnostics."""
    rules = [str(r) for r in app.url_map.iter_rules()]
    return jsonify({"routes": rules}), 200


# Routes
@app.route("/")
def index():
    """Always send visitors to the login page first."""
    return redirect(url_for("auth.login"))


@app.route("/login")
def login_page():
    return redirect(url_for("auth.login", **request.args))


@app.route("/home")
def home():
    """Authenticated home page alias used by navigation links."""
    if not AuthenticationManager.is_user_logged_in():
        return redirect(url_for("auth.login"))
    return render_template("index.html")


@app.route("/predict", methods=["POST"])
def predict():
    """Run a prediction from the home page and store it for the dashboard."""
    if not AuthenticationManager.is_user_logged_in():
        return jsonify({"success": False, "error": "Please log in to make a prediction."}), 401

    try:
        incoming_data = request.get_json(silent=True) or request.form.to_dict()
        sensor_values = {}
        for column in FEATURE_COLUMNS:
            if column == "Equipment Type":
                sensor_values[column] = incoming_data.get("equipment_type") or incoming_data.get("Equipment Type") or "Turbine"
                continue
            if column not in incoming_data or incoming_data[column] in (None, ""):
                raise ValueError(f"Missing required field: {column}")
            sensor_values[column] = float(incoming_data[column])

        prediction_value, failure_probability = predict_equipment_failure(sensor_values)
        prediction_text = (
            "Equipment Failure Predicted" if prediction_value == 1 else "Equipment Working Normally"
        )

        equipment_id = (incoming_data.get("equipment_id") or "HOME-ENTRY").strip() or "HOME-ENTRY"
        timestamp = datetime.now(timezone.utc).isoformat()

        sensor_health_score, _ = HealthScoreCalculator.calculate_health_score(sensor_values, incoming_data.get("equipment_type", "Turbine"))
        ml_health = round((1.0 - failure_probability) * 100.0, 2)
        health_score = round(sensor_health_score * 0.4 + ml_health * 0.6, 2)
        health_score = max(0.0, min(100.0, health_score))
        health_status = "Healthy" if health_score >= 80 else "Caution" if health_score >= 50 else "Critical"
        risk_level = RiskLevelCalculator.calculate_risk_level(failure_probability)
        status_map = {"Low": "online", "Medium": "warning", "Critical": "critical"}
        equipment_status = status_map.get(risk_level, "online")

        stored = False
        record_id = None
        try:
            record_id = Prediction.store_prediction(
                equipment_id,
                sensor_values,
                prediction_value,
                failure_probability,
                risk_level,
                health_score=health_score,
                health_status=health_status,
                equipment_status=equipment_status,
            )
            if not Equipment.find_by_id(equipment_id):
                Equipment.create_equipment(equipment_id, equipment_id, "Home Input", incoming_data.get("equipment_type", "Turbine"))
            Equipment.update_status(equipment_id, equipment_status, health_score)
            stored = True
            sync_equipment_state(debug=True)
        except Exception as db_error:
            print(f"Unable to store prediction from home page: {db_error}")

        return jsonify(
            {
                "success": True,
                "prediction": prediction_text,
                "prediction_value": prediction_value,
                "failure_probability": round(failure_probability * 100, 2),
                "timestamp": timestamp,
                "stored": stored,
                "record_id": record_id,
            }
        )
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 400


@app.route("/health")
def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy", "version": "1.0.0"}, 200


@app.route("/auth/login/")
def auth_login_slash():
    return redirect(url_for("auth.login"))


@app.route("/admin/")
def admin_slash():
    return redirect(url_for("admin.dashboard"))


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return render_template("error.html", message="Page not found", error_code=404), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return render_template("error.html", message="Internal server error", error_code=500), 500


@app.before_request
def init_sample_data():
    """Initialize sample data on first run."""
    try:
        # Only initialize sample data when database is connected
        # Equipment.get_collection() returns None when MongoDB is unavailable
        if Equipment.get_collection() is None:
            return

        equipment_list = Equipment.find_all()
        if len(equipment_list) == 0:
            # Create sample equipment
            Equipment.create_equipment("TURB-001", "Turbine A", "Factory 1", "Turbine")
            Equipment.create_equipment("PUMP-001", "Pump B", "Factory 1", "Pump")
            Equipment.create_equipment("COMP-001", "Compressor C", "Factory 2", "Compressor")
            print("Sample equipment created")
    except Exception as e:
        print("Error initializing sample data:", e)


if __name__ == "__main__":
    # Create necessary directories
    os.makedirs("templates", exist_ok=True)
    os.makedirs("static", exist_ok=True)
    os.makedirs("reports", exist_ok=True)
    
    # Run the application
    print("=" * 70)
    print("🚀 Starting AI Equipment Failure Prediction System")
    print("=" * 70)
    print(f"🌐 Server: http://127.0.0.1:5000")
    print(f"📊 Dashboard: http://127.0.0.1:5000/dashboard")
    print(f"👤 Login: http://127.0.0.1:5000/auth/login")
    print(f"⚙️  Admin: http://127.0.0.1:5000/admin")
    print("=" * 70)
    
    # Disable the auto-reloader to avoid intermittent socket errors on Windows
    app.run(debug=True, host="127.0.0.1", port=5000, use_reloader=False)
