from flask import Flask, render_template, request, jsonify
import pickle
import numpy as np
from sklearn.preprocessing import StandardScaler
import os

app = Flask(__name__)

# Load the trained diabetes prediction model
MODEL_PATH = 'diabetes_model.pkl'

def load_model():
    """Load the trained ML model"""
    if os.path.exists(MODEL_PATH):
        with open(MODEL_PATH, 'rb') as file:
            model = pickle.load(file)
        return model
    return None

# Load model at startup
model = load_model()

# Feature scaling (you may need to adjust based on your model's training scaler)
scaler = StandardScaler()

@app.route('/')
def home():
    """Home page with patient input form"""
    return render_template('index.html')

@app.route('/predict', methods=['POST'])
def predict():
    """Handle diabetes prediction"""
    try:
        # Get form data from request
        data = request.get_json()
        
        # Extract patient information
        pregnancies = float(data.get('pregnancies', 0))
        glucose = float(data.get('glucose', 0))
        blood_pressure = float(data.get('blood_pressure', 0))
        skin_thickness = float(data.get('skin_thickness', 0))
        insulin = float(data.get('insulin', 0))
        bmi = float(data.get('bmi', 0))
        diabetes_pedigree = float(data.get('diabetes_pedigree', 0))
        age = float(data.get('age', 0))
        
        # Validate inputs
        if glucose < 0 or bmi < 0 or age < 0:
            return jsonify({
                'success': False,
                'message': 'Invalid input values. Please ensure all values are non-negative.',
                'risk': None
            }), 400
        
        # Create feature array in the correct order
        features = np.array([[
            pregnancies,
            glucose,
            blood_pressure,
            skin_thickness,
            insulin,
            bmi,
            diabetes_pedigree,
            age
        ]])
        
        # Check if model is loaded
        if model is None:
            return jsonify({
                'success': False,
                'message': 'Model not loaded. Please ensure diabetes_model.pkl exists.',
                'risk': None
            }), 500
        
        # Make prediction
        prediction = model.predict(features)[0]
        probability = model.predict_proba(features)[0]
        
        # Generate healthcare message based on prediction
        if prediction == 1:
            risk_level = 'HIGH RISK'
            message = 'Based on the patient information, there is a HIGH RISK of diabetes. Immediate consultation with an endocrinologist is recommended.'
            message_type = 'danger'
            probability_score = float(probability[1]) * 100
        else:
            risk_level = 'LOW RISK'
            message = 'Based on the patient information, there is a LOW RISK of diabetes. Regular health checkups are recommended.'
            message_type = 'success'
            probability_score = float(probability[0]) * 100
        
        return jsonify({
            'success': True,
            'prediction': int(prediction),
            'risk_level': risk_level,
            'message': message,
            'message_type': message_type,
            'probability': round(probability_score, 2),
            'confidence': round(max(probability) * 100, 2)
        }), 200
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'message': f'Invalid input format: {str(e)}',
            'risk': None
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error during prediction: {str(e)}',
            'risk': None
        }), 500

@app.route('/about')
def about():
    """About page with application information"""
    return render_template('about.html')

@app.route('/health-info')
def health_info():
    """Health information page with tips"""
    return render_template('health_info.html')

@app.route('/api/test-model', methods=['GET'])
def test_model():
    """API endpoint to test if model is loaded correctly"""
    if model is None:
        return jsonify({'status': 'error', 'message': 'Model not loaded'}), 500
    
    return jsonify({
        'status': 'success',
        'message': 'Model loaded successfully',
        'model_type': str(type(model).__name__)
    }), 200

if __name__ == '__main__':
    # Check if model exists
    if model is None:
        print("⚠️  WARNING: diabetes_model.pkl not found. Please ensure the model file exists.")
    else:
        print("✓ Model loaded successfully")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
