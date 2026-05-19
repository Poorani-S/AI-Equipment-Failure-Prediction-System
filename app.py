import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, redirect, url_for, session
from werkzeug.exceptions import HTTPException


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

load_dotenv()

from model import (
    DEFAULT_DATASET_PATH,
    DEFAULT_MODEL_PATH,
    FEATURE_COLUMNS,
    predict_equipment_failure,
    train_model,
)
from database.models import Prediction, db as mongo_db
from utils.prediction_state import sync_equipment_state

DATASET_PATH = os.path.join(BASE_DIR, DEFAULT_DATASET_PATH)
MODEL_PATH = os.path.join(BASE_DIR, DEFAULT_MODEL_PATH)

app = Flask(__name__)
# Ensure a secret key exists for session handling
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key-change-me")

# Clean SMTP credentials (strip accidental spaces)
_mail_username = (os.getenv("MAIL_USERNAME") or "").strip()
_mail_password = (os.getenv("MAIL_PASSWORD") or "").strip().replace(" ", "")
_mail_sender = (os.getenv("MAIL_DEFAULT_SENDER") or "").strip() or _mail_username

app.config.update(
    MAIL_SERVER=os.getenv("MAIL_SERVER"),
    MAIL_PORT=int(os.getenv("MAIL_PORT", "587")),
    MAIL_USE_TLS=os.getenv("MAIL_USE_TLS", "true").lower() == "true",
    MAIL_USE_SSL=os.getenv("MAIL_USE_SSL", "false").lower() == "true",
    MAIL_USERNAME=_mail_username,
    MAIL_PASSWORD=_mail_password,
    MAIL_DEFAULT_SENDER=_mail_sender or "noreply@equipmentmonitoring.com",
)

import logging
import traceback
logging.basicConfig(level=logging.INFO)

from utils.notifications import mail
mail.init_app(app)

# Register blueprints independently so a single failure doesn't block the others
try:
    from routes.auth import auth_bp
    app.register_blueprint(auth_bp)
except Exception as e:
    print(f"Warning: could not register auth blueprint: {e}")

try:
    from routes.dashboard import dashboard_bp
    app.register_blueprint(dashboard_bp)
except Exception as e:
    print(f"Warning: could not register dashboard blueprint: {e}")

try:
    from routes.admin import admin_bp
    app.register_blueprint(admin_bp)
except Exception as e:
    print(f"Warning: could not register admin blueprint: {e}")


# WSGI middleware to log unhandled exceptions during request handling
_original_wsgi = app.wsgi_app
def _logging_middleware(environ, start_response):
    try:
        return _original_wsgi(environ, start_response)
    except Exception:
        tb = traceback.format_exc()
        try:
            os.makedirs("logs", exist_ok=True)
            with open("logs/error.log", "a", encoding="utf-8") as f:
                f.write(tb + "\n\n")
        except Exception:
            pass
        raise

app.wsgi_app = _logging_middleware


def ensure_trained_model() -> None:
    if not os.path.exists(MODEL_PATH):
        train_model(DATASET_PATH, MODEL_PATH)


def get_predictions_collection():
    """Reuse the shared Prediction collection from the database layer."""
    return Prediction.get_collection()


def build_sensor_payload(source_data):
    payload = {}
    for column in FEATURE_COLUMNS:
        # Case-insensitive check for Equipment Type
        if column == "Equipment Type":
            payload[column] = source_data.get("equipment_type") or source_data.get("Equipment Type") or "Turbine"
            continue

        if column not in source_data or source_data[column] in (None, ""):
            raise ValueError(f"Missing required field: {column}")
        
        payload[column] = float(source_data[column])
    return payload


ensure_trained_model()
predictions_collection = get_predictions_collection()

print("\n" + "="*40)
if mongo_db is not None:
    print("✅ MongoDB Status: Connected Successfully")
else:
    print("❌ MongoDB Status: Disconnected (Using local fallback)")
print("="*40 + "\n")


@app.route("/")
def index():
    # Render home directly at the root URL
    return render_template("index.html", feature_columns=FEATURE_COLUMNS)


@app.route("/home")
def home():
    # Redirect legacy /home to root URL
    return redirect(url_for("index"))


@app.route("/predict", methods=["POST"])
def predict():
    if not session.get("user_id"):
        return jsonify({"success": False, "error": "Authentication required. Please Login or Sign Up to run predictions."}), 401
        
    try:
        from database.models import Equipment, Prediction
        from utils.monitoring import RiskLevelCalculator

        incoming_data = request.get_json(silent=True) or request.form.to_dict()
        sensor_values = build_sensor_payload(incoming_data)

        # Equipment identity from the form
        equipment_name = (incoming_data.get("equipment_name") or "Manual Entry").strip()
        equipment_type = (incoming_data.get("equipment_type") or "General").strip()
        
        # Derive a stable equipment_id from the name
        equipment_id = "HOME-" + equipment_name.upper().replace(" ", "-")[:20]

        prediction_value, failure_probability = predict_equipment_failure(sensor_values, MODEL_PATH)
        prediction_text = (
            "Equipment Failure Predicted" if prediction_value == 1 else "Equipment Working Normally"
        )

        risk_level = RiskLevelCalculator.calculate_risk_level(failure_probability)
        status_map = {"Low": "online", "Medium": "warning", "Critical": "critical"}
        status = status_map.get(risk_level, "online")

        timestamp = datetime.now(timezone.utc).isoformat()

        # Upsert equipment so it appears in the dashboard
        stored = False
        inserted_id = None
        try:
            existing = Equipment.find_by_id(equipment_id)
            from utils.monitoring import HealthScoreCalculator
            sensor_health, _ = HealthScoreCalculator.calculate_health_score(
                sensor_values, equipment_type
            )
            ml_health = round((1.0 - failure_probability) * 100.0, 2)
            health_score = round(sensor_health * 0.4 + ml_health * 0.6, 2)
            health_score = max(0.0, min(100.0, health_score))

            if not existing:
                Equipment.create_equipment(
                    equipment_id, equipment_name, "Home Input", equipment_type
                )
            Equipment.update_status(equipment_id, status, health_score)

            # Store prediction via the shared model so dashboard can read it
            pred_id = Prediction.store_prediction(
                equipment_id,
                sensor_values,
                prediction_value,
                failure_probability,
                risk_level,
                health_score=health_score,
                health_status="Healthy" if health_score >= 80 else "Caution" if health_score >= 50 else "Critical",
                equipment_status=status,
            )
            inserted_id = str(pred_id)
            stored = inserted_id is not None
            sync_equipment_state(debug=True)
        except Exception as db_exc:
            print(f"DB error in /predict: {db_exc}")
            # If we reached here, the primary DB insert failed, but Prediction.store_prediction 
            # might have already returned a fallback ID.
            stored = (inserted_id is not None)
            # Fallback: store raw record
            if predictions_collection is not None:
                try:
                    result = predictions_collection.insert_one({
                        **sensor_values,
                        "equipment_id": equipment_id,
                        "prediction": prediction_text,
                        "prediction_value": prediction_value,
                        "failure_probability": round(failure_probability, 4),
                        "risk_level": risk_level,
                        "health_score": health_score,
                        "health_status": "Healthy" if health_score >= 80 else "Caution" if health_score >= 50 else "Critical",
                        "equipment_status": status,
                        "timestamp": timestamp,
                    })
                    inserted_id = str(result.inserted_id)
                    stored = True
                except Exception:
                    pass

        return jsonify(
            {
                "success": True,
                "prediction": prediction_text,
                "prediction_value": prediction_value,
                "failure_probability": round(failure_probability * 100, 2),
                "equipment_id": equipment_id,
                "equipment_name": equipment_name,
                "risk_level": risk_level,
                "timestamp": timestamp,
                "stored": stored,
                "record_id": inserted_id,
            }
        )
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 400


@app.errorhandler(Exception)
def _log_unhandled_exception(error):
    if isinstance(error, HTTPException):
        return render_template(
            "error.html",
            message=error.description,
            error_code=error.code,
        ), error.code

    tb = traceback.format_exc()
    app.logger.error("Unhandled exception:\n%s", tb)
    try:
        os.makedirs("logs", exist_ok=True)
        with open("logs/error.log", "a", encoding="utf-8") as f:
            f.write(tb + "\n\n")
    except Exception:
        pass
    return render_template("error.html", message="Internal server error", error_code=500), 500


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000, use_reloader=False)