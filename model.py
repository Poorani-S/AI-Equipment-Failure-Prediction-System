import os
from typing import Dict, Tuple

import joblib
import numpy as np
import pandas as pd

# Try to import scikit-learn; if unavailable (missing heavy DLLs), provide
# a lightweight fallback so the app can run for UI/testing without sklearn.
SKLEARN_AVAILABLE = True
try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import accuracy_score, classification_report
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import LabelEncoder
except Exception:
    SKLEARN_AVAILABLE = False
    RandomForestClassifier = None
    accuracy_score = None
    classification_report = None
    train_test_split = None
    LabelEncoder = None


FEATURE_COLUMNS = [
    "Temperature",
    "Vibration",
    "Pressure",
    "Humidity",
    "Runtime Hours",
    "Equipment Type",
]
TARGET_COLUMN = "Failure Status"
DEFAULT_DATASET_PATH = "equipment_data.csv"
DEFAULT_MODEL_PATH = "equipment_failure_model.pkl"


def normalize_target(value) -> int:
    """Convert the failure label into a binary value for supervised learning."""
    if pd.isna(value):
        raise ValueError("Failure Status cannot be empty.")

    if isinstance(value, (int, float, np.integer, np.floating)):
        return int(float(value) >= 1.0)

    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "fail", "failure", "fault", "faulty", "broken"}:
        return 1
    if text in {"0", "false", "no", "n", "normal", "working", "ok", "healthy"}:
        return 0

    try:
        return int(float(text) >= 1.0)
    except ValueError as exc:
        raise ValueError(f"Unsupported Failure Status value: {value}") from exc


def load_dataset(data_file: str) -> pd.DataFrame:
    if not os.path.exists(data_file):
        raise FileNotFoundError(
            f"Dataset not found at {data_file}. Create equipment_data.csv and run again."
        )

    df = pd.read_csv(data_file)
    required_columns = FEATURE_COLUMNS + [TARGET_COLUMN]
    missing_columns = [column for column in required_columns if column not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns in dataset: {missing_columns}")

    clean_df = df[required_columns].dropna().copy()
    clean_df[TARGET_COLUMN] = clean_df[TARGET_COLUMN].apply(normalize_target)
    return clean_df


def train_model(data_file: str = DEFAULT_DATASET_PATH, output_file: str = DEFAULT_MODEL_PATH) -> Dict[str, object]:
    """Train a Random Forest classifier and persist the full model artifact."""
    if not SKLEARN_AVAILABLE:
        raise RuntimeError("scikit-learn is not available in this environment. Install scikit-learn to train the model.")

    df = load_dataset(data_file)

    if df[TARGET_COLUMN].nunique() < 2:
        raise ValueError("Dataset must contain both working and failure examples.")

    # Encode categorical "Equipment Type"
    le = LabelEncoder()
    df["Equipment Type"] = le.fit_transform(df["Equipment Type"])

    x_values = df[FEATURE_COLUMNS]
    y_values = df[TARGET_COLUMN]

    x_train, x_test, y_train, y_test = train_test_split(
        x_values,
        y_values,
        test_size=0.2,
        random_state=42,
        stratify=y_values,
    )

    model = RandomForestClassifier(
        n_estimators=500,
        max_depth=15,
        min_samples_split=2,
        min_samples_leaf=1,
        class_weight="balanced",
        random_state=42,
    )
    model.fit(x_train, y_train)

    predictions = model.predict(x_test)
    accuracy = accuracy_score(y_test, predictions)

    print("Model training completed successfully.")
    print(f"Accuracy: {accuracy:.2%}")
    print("Classification Report:")
    print(classification_report(y_test, predictions, digits=4))

    artifact = {
        "model": model,
        "feature_columns": FEATURE_COLUMNS,
        "label_encoder": le,
    }
    joblib.dump(artifact, output_file)
    print(f"Saved trained model to: {output_file}")
    return artifact


def load_model_artifact(model_path: str = DEFAULT_MODEL_PATH) -> Tuple[RandomForestClassifier, list[str], LabelEncoder]:
    """Load the saved model artifact and return the model plus its feature order and encoder."""
    # If sklearn isn't available, return None and default feature order.
    if not SKLEARN_AVAILABLE:
        return None, FEATURE_COLUMNS, None

    artifact = joblib.load(model_path)
    if isinstance(artifact, dict):
        model = artifact["model"]
        feature_columns = artifact.get("feature_columns", FEATURE_COLUMNS)
        le = artifact.get("label_encoder")
        return model, feature_columns, le

    return artifact, FEATURE_COLUMNS, None


def predict_equipment_failure(sensor_values: Dict[str, object], model_path: str = DEFAULT_MODEL_PATH) -> Tuple[int, float]:
    """Predict the failure class and return the probability for the failure class."""
    model, feature_columns, le = load_model_artifact(model_path)

    # Prepare input data
    processed_values = sensor_values.copy()
    
    # Encode Equipment Type if encoder exists
    if le and "Equipment Type" in processed_values:
        try:
            # Handle unknown labels by mapping to a default if necessary, 
            # but for this app the inputs are controlled.
            processed_values["Equipment Type"] = le.transform([processed_values["Equipment Type"]])[0]
        except Exception:
            # Fallback to a default if the type is unknown
            processed_values["Equipment Type"] = 0

    # Build input vector in expected column order
    input_data = []
    for col in feature_columns:
        val = processed_values.get(col, 0)
        try:
            input_data.append(float(val))
        except:
            input_data.append(0.0)

    input_frame = pd.DataFrame([input_data], columns=feature_columns)

    # If model is not available (no sklearn), use a simple heuristic fallback
    if model is None or not SKLEARN_AVAILABLE:
        # Simple heuristic rules (tunable)
        temp = float(sensor_values.get("Temperature", 0.0))
        vib = float(sensor_values.get("Vibration", 0.0))
        pres = float(sensor_values.get("Pressure", 0.0))
        hum = float(sensor_values.get("Humidity", 0.0))
        run = float(sensor_values.get("Runtime Hours", 0.0))

        score = 0.0
        score += max(0, (temp - 75.0)) * 0.04
        score += max(0, (vib - 2.0)) * 0.2
        score += max(0, (pres - 100.0)) * 0.02
        score += max(0, (hum - 80.0)) * 0.02
        score += min(run / 10000.0, 1.0) * 0.1

        failure_probability = min(max(score, 0.0), 1.0)
        prediction = 1 if failure_probability > 0.5 else 0
        return prediction, float(failure_probability)

    # Use the trained model for prediction
    prediction = int(model.predict(input_frame)[0])
    failure_probability = 0.0
    if hasattr(model, "predict_proba"):
        probabilities = model.predict_proba(input_frame)[0]
        class_list = list(model.classes_)
        if 1 in class_list:
            failure_probability = float(probabilities[class_list.index(1)])
        else:
            failure_probability = float(max(probabilities))

    return prediction, failure_probability


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    dataset_path = os.path.join(base_dir, DEFAULT_DATASET_PATH)
    model_path = os.path.join(base_dir, DEFAULT_MODEL_PATH)

    try:
        train_model(dataset_path, model_path)
    except Exception as exc:
        print(f"Error while training model: {exc}")
