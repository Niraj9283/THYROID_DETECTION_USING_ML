"""
ThyroScan AI — Flagship Production Flask Application
Features: Multi-Model Ensemble Agreement, AI Lab Report Comparison,
Conversational Voice/Chat Screening, What-If Simulator, Doctor Mode SOAP Summaries,
and AI Safety Gateway.
"""

import os
import json
import sqlite3
from flask import Flask, request, jsonify, send_from_directory, send_file
from backend.database import get_db, init_db
from backend.auth import (
    hash_password, verify_password, generate_token, get_current_user, require_auth
)
from backend.predict_service import execute_screening, model_comparison, feature_names
from backend.ensemble_service import run_ensemble_prediction
from backend.copilot_service import compare_lab_reports
from backend.safety_gateway import evaluate_safety_gate
from backend.conversational_screening import extract_entities_from_utterance
from backend.doctor_service import generate_clinical_soap_note
from backend.report_service import generate_pdf_report
from backend.ocr_service import extract_text_from_pdf, parse_lab_parameters_from_text
from backend.rag_service import generate_bot_response
from backend.model_lab_service import (
    get_laboratory_benchmarks, run_model_laboratory_tournament, screen_anomalies_autoencoder
)
from backend.ultrasound_service import (
    evaluate_tirads_score, generate_ultrasound_slice_with_segmentation,
    perform_multimodal_fusion, PRESET_ULTRASOUND_SCENARIOS
)
from backend.trajectory_service import analyze_longitudinal_trajectory
from backend.clinical_nlp_service import parse_clinical_notes_nlp
from backend.ft_transformer_service import run_ft_transformer_inference
from backend.explainability_service import calculate_feature_attributions, generate_counterfactual_explanation
from backend.fhir_report_service import generate_fhir_r4_bundle



BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, '..', 'frontend'))

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path='')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload limit

init_db()


def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response


@app.after_request
def after_request_handler(response):
    return add_cors_headers(response)


# -------------------------------------------------------------
# Frontend Static Routes
# -------------------------------------------------------------
@app.route('/')
def index():
    return send_from_directory(FRONTEND_DIR, 'index.html')


@app.route('/manifest.json')
def manifest():
    return send_from_directory(FRONTEND_DIR, 'manifest.json')


@app.route('/sw.js')
def service_worker():
    return send_from_directory(FRONTEND_DIR, 'sw.js')



# -------------------------------------------------------------
# Health & Model Metadata
# -------------------------------------------------------------
@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'ok',
        'platform': 'ThyroScan Flagship AI Healthcare Platform',
        'model_loaded': True,
        'model_version': 'v2.0-multi-model-ensemble',
        'ensemble_models': ['Gradient Boosting', 'Random Forest', 'SVM (RBF Kernel)']
    })


@app.route('/api/model-info', methods=['GET'])
def model_info():
    return jsonify({
        'comparison': model_comparison,
        'features': feature_names,
        'model_version': 'v2.0-ensemble',
        'intended_use': 'AI-assisted educational and preliminary risk stratification screening.',
        'non_intended_use': 'Direct medical diagnosis or automated prescription decisions.',
        'metrics_transparency': {
            'dataset_size': 30000,
            'train_test_split': '80/20 Stratified Split',
            'calibration': 'Multi-Model Consensus & Weighted Probability Distribution',
            'limitations': 'Statistical correlation model; requires clinical endocrinology review.'
        }
    })


# -------------------------------------------------------------
# Authentication Endpoints
# -------------------------------------------------------------
@app.route('/api/auth/register', methods=['POST', 'OPTIONS'])
def register():
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    data = request.get_json() or {}
    name = data.get('name', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not name or not email or not password:
        return jsonify({'error': 'Name, email, and password are required.'}), 400
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters.'}), 400

    pwd_hash = hash_password(password)
    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, pwd_hash)
        )
        user_id = cursor.lastrowid

        cursor.execute(
            "INSERT INTO patient_profiles (user_id, age, sex) VALUES (?, ?, ?)",
            (user_id, data.get('age'), data.get('sex'))
        )
        conn.commit()

        token = generate_token(user_id, email, name)
        return jsonify({
            'message': 'Account created successfully.',
            'token': token,
            'user': {'id': user_id, 'name': name, 'email': email}
        }), 201

    except sqlite3.IntegrityError:
        return jsonify({'error': 'An account with this email address already exists.'}), 409
    finally:
        conn.close()


@app.route('/api/auth/login', methods=['POST', 'OPTIONS'])
def login():
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({'error': 'Email and password are required.'}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()

    if not user or not verify_password(password, user['password_hash']):
        conn.close()
        return jsonify({'error': 'Invalid email or password.'}), 401

    cursor.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?", (user['id'],))
    conn.commit()
    conn.close()

    token = generate_token(user['id'], user['email'], user['name'])
    return jsonify({
        'message': 'Signed in successfully.',
        'token': token,
        'user': {'id': user['id'], 'name': user['name'], 'email': user['email']}
    })


@app.route('/api/auth/me', methods=['GET'])
def get_me():
    user = get_current_user()
    if not user:
        return jsonify({'user': None})

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, email, created_at FROM users WHERE id = ?", (user['user_id'],))
    u = cursor.fetchone()

    cursor.execute("SELECT * FROM patient_profiles WHERE user_id = ?", (user['user_id'],))
    prof = cursor.fetchone()
    conn.close()

    if not u:
        return jsonify({'user': None})

    profile_data = dict(prof) if prof else {}
    return jsonify({
        'user': {
            'id': u['id'],
            'name': u['name'],
            'email': u['email'],
            'created_at': u['created_at'],
            'profile': profile_data
        }
    })


# -------------------------------------------------------------
# Screening & Multi-Model Ensemble Prediction
# -------------------------------------------------------------
@app.route('/api/predict', methods=['POST', 'OPTIONS'])
def predict():
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No screening parameters provided.'}), 400

    try:
        assessment_type = data.get('assessment_type', 'comprehensive')
        base_result = execute_screening(data, assessment_type=assessment_type)

        # Run Multi-Model Ensemble Agreement
        ensemble_res = run_ensemble_prediction(data)
        base_result['ensemble'] = ensemble_res
        base_result['model_probability'] = ensemble_res['calibrated_probability']
        base_result['class_probabilities'] = ensemble_res['calibrated_class_probabilities']

        user = get_current_user()
        saved_id = None

        if user:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO assessments (
                user_id, assessment_type, screening_result, risk_level,
                model_probability, class_probabilities, biomarker_analysis,
                inputs_json, model_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user['user_id'],
                assessment_type,
                base_result['screening_result'],
                base_result['risk_level'],
                base_result['model_probability'],
                json.dumps(base_result['class_probabilities']),
                json.dumps(base_result['biomarker_analysis']),
                json.dumps(data),
                'v2.0-ensemble'
            ))
            conn.commit()
            saved_id = cursor.lastrowid

            if data.get('height_cm') and data.get('weight_kg'):
                try:
                    h_m = float(data['height_cm']) / 100.0
                    w_kg = float(data['weight_kg'])
                    bmi_calc = round(w_kg / (h_m * h_m), 1)
                    cursor.execute("""
                    UPDATE patient_profiles SET height_cm=?, weight_kg=?, bmi=?, updated_at=CURRENT_TIMESTAMP
                    WHERE user_id=?
                    """, (data['height_cm'], data['weight_kg'], bmi_calc, user['user_id']))
                    conn.commit()
                except Exception:
                    pass

            conn.close()

        base_result['saved_assessment_id'] = saved_id
        return jsonify(base_result)

    except Exception as e:
        return jsonify({'error': f"Screening evaluation failed: {str(e)}"}), 500


# -------------------------------------------------------------
# What-If Biomarker Simulator
# -------------------------------------------------------------
@app.route('/api/simulator/simulate', methods=['POST', 'OPTIONS'])
def simulate_biomarkers():
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    data = request.get_json() or {}
    try:
        res = execute_screening(data, assessment_type='simulation')
        ens = run_ensemble_prediction(data)
        res['ensemble'] = ens
        res['model_probability'] = ens['calibrated_probability']
        res['class_probabilities'] = ens['calibrated_class_probabilities']
        return jsonify(res)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# -------------------------------------------------------------
# Model Laboratory — Multi-Family Benchmark & Tournament API
# -------------------------------------------------------------
@app.route('/api/model-lab/benchmarks', methods=['GET'])
def model_lab_benchmarks():
    data = get_laboratory_benchmarks()
    return jsonify(data)


@app.route('/api/model-lab/predict-all', methods=['POST', 'OPTIONS'])
def model_lab_predict_all():
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    data = request.get_json() or {}
    try:
        results = run_model_laboratory_tournament(data)
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': f"Model laboratory tournament failed: {str(e)}"}), 500


@app.route('/api/model-lab/anomaly-screen', methods=['POST', 'OPTIONS'])
def model_lab_anomaly_screen():
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    data = request.get_json() or {}
    try:
        results = screen_anomalies_autoencoder(data)
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': f"Anomaly screening failed: {str(e)}"}), 500




# -------------------------------------------------------------
# Phase 2: Multimodal Ultrasound AI & ACR TI-RADS Analysis
# -------------------------------------------------------------
@app.route('/api/ultrasound/presets', methods=['GET'])
def ultrasound_presets():
    return jsonify(PRESET_ULTRASOUND_SCENARIOS)


@app.route('/api/ultrasound/analyze', methods=['POST', 'OPTIONS'])
def ultrasound_analyze():
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    data = request.get_json() or {}
    try:
        composition = data.get('composition', 'solid')
        echogenicity = data.get('echogenicity', 'hypoechoic')
        shape = data.get('shape', 'wider_than_tall')
        margin = data.get('margin', 'smooth')
        echogenic_foci = data.get('echogenic_foci', 'none')
        nodule_size_cm = float(data.get('nodule_size_cm', 1.8))
        preset_key = data.get('preset_key', 'tr5_papillary_carcinoma')
        custom_params = data.get('custom_params', None)

        tirads_results = evaluate_tirads_score(
            composition=composition,
            echogenicity=echogenicity,
            shape=shape,
            margin=margin,
            echogenic_foci=echogenic_foci,
            nodule_size_cm=nodule_size_cm
        )

        visual_results = generate_ultrasound_slice_with_segmentation(
            scenario_key=preset_key,
            custom_params=custom_params
        )

        response_payload = {**tirads_results, **visual_results}
        return jsonify(response_payload)
    except Exception as e:
        return jsonify({'error': f"Ultrasound analysis failed: {str(e)}"}), 500


@app.route('/api/multimodal/fuse', methods=['POST', 'OPTIONS'])
def multimodal_fuse():
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    data = request.get_json() or {}
    try:
        tabular_data = data.get('tabular_data', {})
        ultrasound_data = data.get('ultrasound_data', {})

        fusion_result = perform_multimodal_fusion(tabular_data, ultrasound_data)
        return jsonify(fusion_result)
    except Exception as e:
        return jsonify({'error': f"Multimodal fusion failed: {str(e)}"}), 500


# -------------------------------------------------------------
# Phase 2: Longitudinal Patient Trajectory Tracking
# -------------------------------------------------------------
@app.route('/api/trajectory/analyze', methods=['POST', 'OPTIONS'])
def trajectory_analyze():
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    data = request.get_json() or {}
    try:
        visits = data.get('visits', [])
        results = analyze_longitudinal_trajectory(visits)
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': f"Trajectory analysis failed: {str(e)}"}), 500


# -------------------------------------------------------------
# Phase 2: Clinical Symptoms NLP Parser
# -------------------------------------------------------------
@app.route('/api/clinical-nlp/extract', methods=['POST', 'OPTIONS'])
def clinical_nlp_extract():
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    data = request.get_json() or {}
    try:
        text = data.get('clinical_text', '')
        results = parse_clinical_notes_nlp(text)
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': f"Clinical NLP extraction failed: {str(e)}"}), 500



# -------------------------------------------------------------
# Phase 3 & 4: FT-Transformer & Clinical Explainability (XAI)
# -------------------------------------------------------------
@app.route('/api/explainability/ft-transformer', methods=['POST', 'OPTIONS'])
def explainability_ft_transformer():
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    data = request.get_json() or {}
    try:
        results = run_ft_transformer_inference(data)
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': f"FT-Transformer inference failed: {str(e)}"}), 500


@app.route('/api/explainability/attributions', methods=['POST', 'OPTIONS'])
def explainability_attributions():
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    data = request.get_json() or {}
    try:
        results = calculate_feature_attributions(data)
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': f"Feature attribution calculation failed: {str(e)}"}), 500


@app.route('/api/explainability/counterfactual', methods=['POST', 'OPTIONS'])
def explainability_counterfactual():
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    data = request.get_json() or {}
    try:
        results = generate_counterfactual_explanation(data)
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': f"Counterfactual generation failed: {str(e)}"}), 500


# -------------------------------------------------------------
# Phase 4: Standardized HL7 FHIR R4 Diagnostic Dossier Export
# -------------------------------------------------------------
@app.route('/api/fhir/export', methods=['POST', 'OPTIONS'])
def fhir_export():
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    data = request.get_json() or {}
    try:
        patient_data = data.get('patient_data', {})
        model_results = data.get('model_results', {})
        ultrasound_data = data.get('ultrasound_data', {})
        trajectory_data = data.get('trajectory_data', {})

        bundle = generate_fhir_r4_bundle(
            patient_data=patient_data,
            model_results=model_results,
            ultrasound_data=ultrasound_data,
            trajectory_data=trajectory_data
        )
        return jsonify(bundle)
    except Exception as e:
        return jsonify({'error': f"FHIR bundle export failed: {str(e)}"}), 500


# -------------------------------------------------------------
# Conversational Voice & Chat Entity Extraction
# -------------------------------------------------------------
@app.route('/api/conversational/extract', methods=['POST', 'OPTIONS'])
def conversational_extract():
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    data = request.get_json() or {}
    utterance = data.get('text', '')
    current_state = data.get('current_state', {})

    result = extract_entities_from_utterance(utterance, current_state)
    return jsonify(result)


# -------------------------------------------------------------
# AI Lab Report Comparison (Report A vs Report B)
# -------------------------------------------------------------
@app.route('/api/lab-report/compare', methods=['POST', 'OPTIONS'])
def compare_reports_endpoint():
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    data = request.get_json() or {}
    report_a = data.get('report_a', {})
    report_b = data.get('report_b', {})

    if not report_a or not report_b:
        return jsonify({'error': 'Both Report A and Report B payloads are required for comparison.'}), 400

    diff_result = compare_lab_reports(report_a, report_b)
    return jsonify(diff_result)


# -------------------------------------------------------------
# Doctor Mode & SOAP Note Summaries
# -------------------------------------------------------------
@app.route('/api/doctor/summary/<int:assessment_id>', methods=['GET'])
def get_doctor_soap_summary(assessment_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM assessments WHERE id = ?", (assessment_id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return jsonify({'error': 'Assessment record not found.'}), 404

    patient_profile = {}
    if row['user_id']:
        cursor.execute("SELECT u.name, p.* FROM users u LEFT JOIN patient_profiles p ON u.id = p.user_id WHERE u.id = ?", (row['user_id'],))
        p_row = cursor.fetchone()
        if p_row:
            patient_profile = dict(p_row)
    conn.close()

    assessment_data = {
        'id': row['id'],
        'screening_result': row['screening_result'],
        'risk_level': row['risk_level'],
        'model_probability': row['model_probability'],
        'inputs': json.loads(row['inputs_json']) if row['inputs_json'] else {},
        'badge': row['screening_result'].replace('_', ' ').title()
    }

    soap_data = generate_clinical_soap_note(assessment_data, patient_profile)
    return jsonify(soap_data)


# -------------------------------------------------------------
# Assessment History & PDF Generation
# -------------------------------------------------------------
@app.route('/api/assessments', methods=['GET'])
def get_assessments():
    user = get_current_user()
    if not user:
        return jsonify({'assessments': []})

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT id, assessment_type, screening_result, risk_level, model_probability,
           class_probabilities, biomarker_analysis, inputs_json, created_at
    FROM assessments WHERE user_id = ?
    ORDER BY created_at DESC LIMIT 50
    """, (user['user_id'],))
    rows = cursor.fetchall()
    conn.close()

    records = []
    for r in rows:
        records.append({
            'id': r['id'],
            'assessment_type': r['assessment_type'],
            'screening_result': r['screening_result'],
            'risk_level': r['risk_level'],
            'model_probability': r['model_probability'],
            'class_probabilities': json.loads(r['class_probabilities']) if r['class_probabilities'] else {},
            'biomarker_analysis': json.loads(r['biomarker_analysis']) if r['biomarker_analysis'] else [],
            'inputs': json.loads(r['inputs_json']) if r['inputs_json'] else {},
            'created_at': r['created_at']
        })

    return jsonify({'assessments': records})


@app.route('/api/assessments/<int:assessment_id>', methods=['DELETE', 'OPTIONS'])
def delete_assessment(assessment_id):
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    user = get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM assessments WHERE id = ? AND user_id = ?", (assessment_id, user['user_id']))
    conn.commit()
    conn.close()

    return jsonify({'message': 'Assessment deleted successfully.'})


@app.route('/api/reports/<int:assessment_id>/pdf', methods=['GET'])
def download_assessment_pdf(assessment_id):
    user = get_current_user()

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM assessments WHERE id = ?", (assessment_id,))
    row = cursor.fetchone()

    patient_info = {'name': 'Guest Patient'}
    if user:
        cursor.execute("SELECT u.name, p.age, p.sex, p.height_cm, p.weight_kg, p.bmi FROM users u LEFT JOIN patient_profiles p ON u.id = p.user_id WHERE u.id = ?", (user['user_id'],))
        p_row = cursor.fetchone()
        if p_row:
            patient_info = dict(p_row)
    conn.close()

    if not row:
        return jsonify({'error': 'Assessment record not found.'}), 404

    assessment_data = {
        'id': row['id'],
        'screening_result': row['screening_result'],
        'risk_level': row['risk_level'],
        'model_probability': row['model_probability'],
        'class_probabilities': json.loads(row['class_probabilities']) if row['class_probabilities'] else {},
        'biomarker_analysis': json.loads(row['biomarker_analysis']) if row['biomarker_analysis'] else [],
        'inputs': json.loads(row['inputs_json']) if row['inputs_json'] else {},
        'badge': row['screening_result'].replace('_', ' ').title()
    }

    pdf_buffer = generate_pdf_report(assessment_data, patient_info)
    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=f"ThyroScan_Report_{assessment_id}.pdf",
        mimetype='application/pdf'
    )


@app.route('/api/reports/preview/pdf', methods=['POST', 'OPTIONS'])
def preview_pdf():
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    data = request.get_json() or {}
    user = get_current_user()

    patient_info = {
        'name': user.get('name') if user else (data.get('name') or 'Patient Screening Preview'),
        'age': data.get('inputs', {}).get('age') or data.get('age'),
        'sex': data.get('inputs', {}).get('sex') or data.get('sex'),
        'bmi': data.get('inputs', {}).get('bmi') or data.get('bmi')
    }

    pdf_buffer = generate_pdf_report(data, patient_info)
    return send_file(
        pdf_buffer,
        as_attachment=False,
        download_name="ThyroScan_Preview_Report.pdf",
        mimetype='application/pdf'
    )


# -------------------------------------------------------------
# Lab Report OCR & Extraction
# -------------------------------------------------------------
@app.route('/api/lab-report/extract', methods=['POST', 'OPTIONS'])
def extract_lab_report():
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded.'}), 400

    uploaded_file = request.files['file']
    if uploaded_file.filename == '':
        return jsonify({'error': 'Empty filename.'}), 400

    content = uploaded_file.read()
    filename_lower = uploaded_file.filename.lower()

    extracted_text = ""
    if filename_lower.endswith('.pdf'):
        extracted_text = extract_text_from_pdf(content)
    else:
        try:
            extracted_text = content.decode('utf-8', errors='ignore')
        except Exception:
            extracted_text = ""

    parsed = parse_lab_parameters_from_text(extracted_text)
    return jsonify({
        'filename': uploaded_file.filename,
        'extracted': parsed['extracted'],
        'confidence': parsed['confidence'],
        'found_count': parsed['found_count'],
        'snippets': parsed['snippets'],
        'preview_snippet': parsed['raw_text_snippet'],
        'message': 'Biomarkers parsed successfully. Please verify values before running analysis.'
    })


# -------------------------------------------------------------
# Context-Aware ThyroBot Chat with AI Safety Gateway
# -------------------------------------------------------------
@app.route('/api/chat', methods=['POST', 'OPTIONS'])
def chat():
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    data = request.get_json() or {}
    message = data.get('message', '').strip()
    if not message:
        return jsonify({'error': 'Message cannot be empty.'}), 400

    # 1. Evaluate AI Safety Gateway
    safety_check = evaluate_safety_gate(message)
    if safety_check['status'] == 'intercepted':
        return jsonify(safety_check)

    # 2. Add Longitudinal Context if user is logged in
    user = get_current_user()
    user_context = {}

    if user:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
        SELECT screening_result, inputs_json, model_probability FROM assessments
        WHERE user_id = ? ORDER BY created_at DESC LIMIT 1
        """, (user['user_id'],))
        latest = cursor.fetchone()
        if latest:
            user_context['latest_assessment'] = {
                'screening_result': latest['screening_result'],
                'inputs': json.loads(latest['inputs_json']) if latest['inputs_json'] else {},
                'probability': latest['model_probability']
            }
        conn.close()

    bot_reply = generate_bot_response(message, user_context)

    if user:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO chat_messages (user_id, role, message, citations_json, is_emergency)
        VALUES (?, 'user', ?, NULL, 0)
        """, (user['user_id'], message))
        cursor.execute("""
        INSERT INTO chat_messages (user_id, role, message, citations_json, is_emergency)
        VALUES (?, 'assistant', ?, ?, ?)
        """, (user['user_id'], bot_reply['message'], json.dumps(bot_reply.get('citations', [])), 1 if bot_reply.get('is_emergency') else 0))
        conn.commit()
        conn.close()

    return jsonify(bot_reply)


@app.route('/api/chat/history', methods=['GET', 'DELETE', 'OPTIONS'])
def chat_history():
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    user = get_current_user()
    if not user:
        return jsonify({'messages': []})

    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'DELETE':
        cursor.execute("DELETE FROM chat_messages WHERE user_id = ?", (user['user_id'],))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Chat conversation cleared.'})

    cursor.execute("""
    SELECT role, message, citations_json, is_emergency, created_at
    FROM chat_messages WHERE user_id = ? ORDER BY created_at ASC LIMIT 100
    """, (user['user_id'],))
    rows = cursor.fetchall()
    conn.close()

    messages = []
    for r in rows:
        messages.append({
            'role': r['role'],
            'message': r['message'],
            'citations': json.loads(r['citations_json']) if r['citations_json'] else [],
            'is_emergency': bool(r['is_emergency']),
            'created_at': r['created_at']
        })

    return jsonify({'messages': messages})


# -------------------------------------------------------------
# Longitudinal Health Trends
# -------------------------------------------------------------
@app.route('/api/trends', methods=['GET'])
def get_trends():
    user = get_current_user()
    if not user:
        return jsonify({'trends': [], 'message': 'Sign in to view longitudinal health trends.'})

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT id, screening_result, model_probability, inputs_json, created_at
    FROM assessments WHERE user_id = ? ORDER BY created_at ASC LIMIT 30
    """, (user['user_id'],))
    rows = cursor.fetchall()
    conn.close()

    points = []
    for r in rows:
        inputs = json.loads(r['inputs_json']) if r['inputs_json'] else {}
        points.append({
            'id': r['id'],
            'date': r['created_at'][:10] if r['created_at'] else '',
            'screening_result': r['screening_result'],
            'probability': r['model_probability'],
            'TSH': inputs.get('TSH'),
            'T3': inputs.get('T3'),
            'TT4': inputs.get('TT4'),
            'bmi': inputs.get('bmi') or inputs.get('weight_kg')
        })

    return jsonify({'trends': points})


# -------------------------------------------------------------
# Privacy & GDPR Controls
# -------------------------------------------------------------
@app.route('/api/privacy/export-data', methods=['GET'])
def export_user_data():
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, email, created_at FROM users WHERE id = ?", (user['user_id'],))
    u = cursor.fetchone()

    cursor.execute("SELECT * FROM patient_profiles WHERE user_id = ?", (user['user_id'],))
    prof = cursor.fetchone()

    cursor.execute("SELECT * FROM assessments WHERE user_id = ?", (user['user_id'],))
    assessments = [dict(row) for row in cursor.fetchall()]

    cursor.execute("SELECT role, message, created_at FROM chat_messages WHERE user_id = ?", (user['user_id'],))
    chats = [dict(row) for row in cursor.fetchall()]
    conn.close()

    export_obj = {
        'user': dict(u) if u else {},
        'profile': dict(prof) if prof else {},
        'assessments': assessments,
        'chat_history': chats,
        'exported_at': '2026-08-30'
    }

    return jsonify(export_obj)


@app.route('/api/privacy/delete-account', methods=['DELETE', 'OPTIONS'])
def delete_user_account():
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    user = get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = ?", (user['user_id'],))
    conn.commit()
    conn.close()

    return jsonify({'message': 'Account and all associated medical screening records have been permanently deleted.'})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"Thyroid Detection API running at http://0.0.0.0:{port}")
    app.run(debug=False, host='0.0.0.0', port=port)
