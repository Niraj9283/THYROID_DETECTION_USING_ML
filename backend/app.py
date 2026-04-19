
import os
import json
import joblib
import numpy as np
import pandas as pd
from flask import Flask, request, jsonify, send_from_directory, render_template
from backend.models import db, PredictionHistory
from flask import Flask, request, jsonify
from dotenv import load_dotenv
load_dotenv()
import google.generativeai as genai

# Add this right below the genai import!
CHATBOT_SYSTEM = """You are ThyroBot, a helpful AI assistant for a Thyroid Disease Detection System. 
You help users understand their thyroid lab values (TSH, T3, TT4), common symptoms, and healthy diets. 
Keep your answers brief, friendly, and formatted nicely. 
IMPORTANT: Always remind users that you are an AI and they should consult a doctor for real medical advice."""


app = Flask(__name__, static_folder='../frontend', static_url_path='', template_folder='../templates')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///predictions.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Create DB tables
with app.app_context():
    db.create_all()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, '..', 'models')
DATA_PATH = os.path.join(BASE_DIR, '..', 'data', 'dataset.csv')

# Load model artifacts
model = joblib.load(os.path.join(MODELS_DIR, 'best_model.pkl'))
label_encoder = joblib.load(os.path.join(MODELS_DIR, 'label_encoder.pkl'))
with open(os.path.join(MODELS_DIR, 'feature_names.json')) as f:
    feature_names = json.load(f)
with open(os.path.join(MODELS_DIR, 'model_comparison.json')) as f:
    model_comparison = json.load(f)

DIAGNOSIS_INFO = {
    'negative': {'label': 'Negative', 'description': 'No thyroid disorder detected.', 'severity': 'normal', 'color': '#10b981', 'recommendations': ['Regular check-ups']},
    'hypothyroid': {'label': 'Hypothyroid', 'description': 'Underactive thyroid.', 'severity': 'high', 'color': '#ef4444', 'recommendations': ['See endocrinologist']},
    'hyperthyroid': {'label': 'Hyperthyroid', 'description': 'Overactive thyroid.', 'severity': 'high', 'color': '#ef4444', 'recommendations': ['Medical attention']},
    'subclinical_hypothyroid': {'label': 'Subclinical Hypothyroid', 'description': 'Early stage hypothyroidism.', 'severity': 'moderate', 'color': '#f59e0b', 'recommendations': ['Follow-up']},
    'subclinical_hyperthyroid': {'label': 'Subclinical Hyperthyroid', 'description': 'Early stage hyperthyroidism.', 'severity': 'moderate', 'color': '#f59e0b', 'recommendations': ['Follow-up']},
}

# Validation Class
class InputValidator:
    REQUIRED_COLS = feature_names
    NUMERIC_RANGES = {
        'age': (0, 120),
        'TSH': (0, 100),
        'T3': (0, 10),
        'TT4': (0, 300),
        'T4U': (0, 2),
        'FTI': (0, 200)
    }

    @staticmethod
    def validate(data):
        errors = []
        
        # Check required columns
        for col in InputValidator.REQUIRED_COLS:
            if col not in data:
                errors.append(f"Missing required field: {col}")
        
        # Check numeric ranges
        for field, (min_val, max_val) in InputValidator.NUMERIC_RANGES.items():
            val = data.get(field)
            if val is not None and (pd.isna(val) or not min_val <= float(val) <= max_val):
                errors.append(f"{field} must be between {min_val} and {max_val}")
        
        # Check no empty row (at least age/sex)
        if data.get('age') is None or data.get('sex') is None:
            errors.append("Age and sex are required")
        
        return errors

def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

# ── Chat endpoint ─────────────────────────────────────────────────────────────
@app.route('/api/chat', methods=['POST', 'OPTIONS'])
def chat():
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    data = request.get_json()
    if not data or 'messages' not in data:
        return jsonify({'error': 'No messages provided'}), 400

    # Get API key from environment variable
    api_key = os.environ.get('GEMINI_API_KEY', '')
    if not api_key:
        return jsonify({'reply': (
            "⚠️ ThyroBot is not configured yet. "
            "Please set the GEMINI_API_KEY environment variable on the server "
            "and restart the app."
        )}), 200

    try:
        # 1. Configure the API key
        genai.configure(api_key=api_key)

        # 2. Initialize the model and pass your custom system prompt
        model = genai.GenerativeModel(
            'gemini-2.5-flash',
            system_instruction=CHATBOT_SYSTEM
        )

        messages = data['messages'][-20:]  # keep last 20 turns

        # 3. Format history for Gemini 
        # (Assuming your frontend sends standard [{"role": "user", "content": "..."}] format)
        gemini_history = []
        for msg in messages[:-1]: # Grab all messages EXCEPT the very last one for history
            role = 'model' if msg.get('role') == 'assistant' else 'user'
            text = msg.get('content', '')
            gemini_history.append({'role': role, 'parts': [text]})

        # 4. Start the chat with the history
        chat_session = model.start_chat(history=gemini_history)

        # 5. Send the newest user message to the model
        latest_message = messages[-1].get('content', '')
        response = chat_session.send_message(latest_message)

        return jsonify({'reply': response.text})

    except Exception as e:
        return jsonify({'reply': f'⚠️ Something went wrong: {str(e)}'}), 200

@app.after_request
def after_request(response):
    return add_cors_headers(response)

@app.route('/')
def index():
    return send_from_directory('../frontend', 'index.html')

@app.route('/history')
def history_page():
    return render_template('history.html')

@app.route('/dashboard')
def dashboard_page():
    return render_template('dashboard.html')

@app.route('/api/predict', methods=['POST', 'OPTIONS'])
def predict():
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    # Validation
    errors = InputValidator.validate(data)
    if errors:
        return jsonify({'error': '; '.join(errors)}), 400

    try:
        # Build input df
        row = {feat: data.get(feat, np.nan) for feat in feature_names}
        df_input = pd.DataFrame([row])
        
        # Numeric conversion
        numeric_fields = ['age', 'TSH', 'T3', 'TT4', 'T4U', 'FTI']
        for field in numeric_fields:
            if field in df_input:
                df_input[field] = pd.to_numeric(df_input[field], errors='coerce')

        # Predict
        prediction_encoded = model.predict(df_input)[0]
        prediction_label = label_encoder.inverse_transform([prediction_encoded])[0]
        probabilities = model.predict_proba(df_input)[0]
        confidence = float(probabilities.max()) * 100

        class_probs = {label_encoder.inverse_transform([i])[0]: round(float(p)*100, 2) 
                      for i, p in enumerate(probabilities)}

        diagnosis_info = DIAGNOSIS_INFO.get(prediction_label, {'label': prediction_label})

        # Save to history
        history = PredictionHistory(
            input_features=json.dumps(data),
            prediction=prediction_label,
            confidence=confidence/100
        )
        db.session.add(history)
        db.session.commit()

        return jsonify({
            'prediction': prediction_label,
            'confidence': round(confidence, 2),
            'class_probabilities': class_probs,
            'diagnosis_info': diagnosis_info
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/history', methods=['GET'])
def get_history():
    histories = PredictionHistory.query.order_by(PredictionHistory.timestamp.desc()).limit(100).all()
    return jsonify([h.to_dict() for h in histories])

@app.route('/api/history', methods=['DELETE'])
def clear_history():
    PredictionHistory.query.delete()
    db.session.commit()
    return jsonify({'message': 'History cleared'})

@app.route('/api/model-info')
def model_info():
    return jsonify(model_comparison)

@app.route('/api/health')
def health():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    print("🚀 Thyroid Detection API at http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
    
