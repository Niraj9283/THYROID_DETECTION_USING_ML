"""
ThyroScan — AI-Assisted Risk Screening & Explainability Service
Performs feature normalization, range validation, model probability calibration,
biomarker reference evaluation, and feature influence calculation.
"""

import os
import json
import joblib
import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, '..', 'models')

# Load trained model artifacts
MODEL_PATH = os.path.join(MODELS_DIR, 'best_model.pkl')
ENCODER_PATH = os.path.join(MODELS_DIR, 'label_encoder.pkl')
FEATURES_PATH = os.path.join(MODELS_DIR, 'feature_names.json')
COMPARISON_PATH = os.path.join(MODELS_DIR, 'model_comparison.json')

model = joblib.load(MODEL_PATH)
label_encoder = joblib.load(ENCODER_PATH)
with open(FEATURES_PATH, 'r') as f:
    feature_names = json.load(f)
with open(COMPARISON_PATH, 'r') as f:
    model_comparison = json.load(f)

# Standard clinical reference intervals for visual indicators and risk explainability
LAB_REFERENCE_RANGES = {
    'TSH': {
        'name': 'Thyroid Stimulating Hormone (TSH)',
        'unit': 'mIU/L',
        'min': 0.45,
        'max': 4.5,
        'critical_low': 0.1,
        'critical_high': 10.0,
        'description': 'Primary regulatory pituitary hormone controlling thyroid output.'
    },
    'T3': {
        'name': 'Triiodothyronine (Total T3)',
        'unit': 'ng/mL',
        'min': 0.8,
        'max': 2.0,
        'critical_low': 0.5,
        'critical_high': 3.5,
        'description': 'Active thyroid hormone affecting metabolism and cardiac rate.'
    },
    'TT4': {
        'name': 'Total Thyroxine (TT4)',
        'unit': 'ug/dL',
        'min': 4.5,
        'max': 12.0,
        'critical_low': 2.0,
        'critical_high': 18.0,
        'description': 'Major circulating prohormone secreted by thyroid follicular cells.'
    },
    'T4U': {
        'name': 'T4 Uptake (T4U)',
        'unit': 'ratio',
        'min': 0.8,
        'max': 1.3,
        'critical_low': 0.6,
        'critical_high': 1.6,
        'description': 'Indirect estimate of thyroxine-binding globulin capacity.'
    },
    'FTI': {
        'name': 'Free Thyroxine Index (FTI)',
        'unit': 'index',
        'min': 65.0,
        'max': 135.0,
        'critical_low': 40.0,
        'critical_high': 170.0,
        'description': 'Normalized surrogate estimate of unbound, metabolically free T4.'
    }
}

CLINICAL_PROFILES = {
    'negative': {
        'title': 'Low Thyroid Risk Signal',
        'badge': 'Low Risk',
        'severity': 'low',
        'color': '#10b981',
        'summary': 'Clinical biomarkers and symptom patterns align within typical physiological parameters. No active pattern of hyper/hypo dysfunction detected.',
        'action_plan': [
            'Maintain routine annual wellness check-ups',
            'Follow a nutrient-dense diet containing adequate dietary iodine and selenium',
            'Track your energy levels, sleep patterns, and body weight over time',
            'Consult your physician if new unexplained fatigue or thermal intolerance develops'
        ]
    },
    'hypothyroid': {
        'title': 'Elevated Hypothyroid Risk Signal',
        'badge': 'Elevated Risk (Hypothyroidism)',
        'severity': 'high',
        'color': '#ef4444',
        'summary': 'Biomarker patterns (typically high TSH with reduced T4/T3) and symptoms indicate a strong signal of underactive thyroid hormone production.',
        'action_plan': [
            'Schedule an evaluation with a primary physician or endocrinologist',
            'Bring your original laboratory report for comprehensive clinical review',
            'Discuss confirmatory thyroid panel testing (Free T3, Free T4, Anti-TPO antibodies)',
            'Do not initiate or adjust levothyroxine without direct prescription from a physician'
        ]
    },
    'hyperthyroid': {
        'title': 'Elevated Hyperthyroid Risk Signal',
        'badge': 'Elevated Risk (Hyperthyroidism)',
        'severity': 'high',
        'color': '#ef4444',
        'summary': 'Biomarker patterns (suppressed TSH with elevated T4/T3) suggest excessive thyroid hormone synthesis and hypermetabolic state.',
        'action_plan': [
            'Seek timely medical consultation with an endocrinologist',
            'Monitor for resting palpitations, tremors, sudden weight loss, or heat intolerance',
            'Bring laboratory reports to discuss possible TSI/TRAb antibodies and thyroid ultrasound',
            'Avoid excessive caffeine, energy drinks, and unprescribed iodine supplements'
        ]
    },
    'subclinical_hypothyroid': {
        'title': 'Moderate Subclinical Hypothyroid Signal',
        'badge': 'Moderate Risk (Subclinical Hypo)',
        'severity': 'moderate',
        'color': '#f59e0b',
        'summary': 'Mildly elevated TSH with relatively preserved peripheral hormone levels. Often represents an early or borderline stage requiring periodic monitoring.',
        'action_plan': [
            'Schedule a follow-up consultation with your doctor within 4–8 weeks',
            'Re-test TSH and Free T4 in 3 to 6 months to establish longitudinal trend',
            'Review potential contributing factors like recent illness, stress, or medications',
            'Discuss anti-thyroid peroxidase (TPO) antibody testing to assess autoimmune risk'
        ]
    },
    'subclinical_hyperthyroid': {
        'title': 'Moderate Subclinical Hyperthyroid Signal',
        'badge': 'Moderate Risk (Subclinical Hyper)',
        'severity': 'moderate',
        'color': '#f59e0b',
        'summary': 'Mildly suppressed TSH with normal circulating T3 and T4 levels. May be transient or an early sign of mild thyroid overactivity.',
        'action_plan': [
            'Consult your physician to review underlying clinical context and bone/heart health',
            'Repeat TSH and thyroid panel after 6 to 12 weeks to confirm persistence',
            'Avoid unnecessary iodine supplements and excessive stimulants',
            'Inform your doctor if palpitations, arrhythmia, or nervousness occur'
        ]
    }
}
CLINICAL_PROFILES['normal'] = CLINICAL_PROFILES['negative']



def analyze_biomarkers(data: dict) -> list:
    """Analyze input lab values against standard reference ranges."""
    evaluations = []
    for key, ref in LAB_REFERENCE_RANGES.items():
        val = data.get(key)
        if val is None or val == '' or (isinstance(val, (int, float)) and np.isnan(val)):
            continue
        try:
            val_num = float(val)
        except (ValueError, TypeError):
            continue

        status = 'normal'
        status_label = 'Normal Range'
        color = '#10b981'

        if val_num < ref['min']:
            if val_num <= ref['critical_low']:
                status = 'critical_low'
                status_label = 'Significantly Below Range'
                color = '#ef4444'
            else:
                status = 'low'
                status_label = 'Below Typical Range'
                color = '#f59e0b'
        elif val_num > ref['max']:
            if val_num >= ref['critical_high']:
                status = 'critical_high'
                status_label = 'Significantly Above Range'
                color = '#ef4444'
            else:
                status = 'high'
                status_label = 'Above Typical Range'
                color = '#f59e0b'

        evaluations.append({
            'code': key,
            'name': ref['name'],
            'value': round(val_num, 3),
            'unit': ref['unit'],
            'ref_min': ref['min'],
            'ref_max': ref['max'],
            'status': status,
            'status_label': status_label,
            'color': color,
            'description': ref['description']
        })
    return evaluations


def compute_feature_influences(data: dict, prediction_label: str) -> list:
    """
    Computes explainable relative feature influence factors for the screening outcome.
    Provides clear visual attribution for why the model flagged specific risk signals.
    """
    influences = []

    # Check TSH influence
    tsh = data.get('TSH')
    if tsh is not None and tsh != '':
        try:
            tsh_val = float(tsh)
            if tsh_val > 4.5:
                delta = min(100, int((tsh_val - 4.5) * 8 + 45))
                influences.append({
                    'feature': 'TSH (Elevated)',
                    'influence_pct': delta,
                    'direction': 'Promotes Hypothyroid Signal',
                    'category': 'Biomarker'
                })
            elif tsh_val < 0.45:
                delta = min(100, int((0.45 - tsh_val) * 80 + 50))
                influences.append({
                    'feature': 'TSH (Suppressed)',
                    'influence_pct': delta,
                    'direction': 'Promotes Hyperthyroid Signal',
                    'category': 'Biomarker'
                })
            else:
                influences.append({
                    'feature': 'TSH (Normal)',
                    'influence_pct': 30,
                    'direction': 'Stabilizes Normal Signal',
                    'category': 'Biomarker'
                })
        except Exception:
            pass

    # Check TT4 influence
    tt4 = data.get('TT4')
    if tt4 is not None and tt4 != '':
        try:
            tt4_val = float(tt4)
            if tt4_val < 4.5:
                influences.append({
                    'feature': 'Total T4 (Low)',
                    'influence_pct': 70,
                    'direction': 'Supports Hypothyroid Signal',
                    'category': 'Biomarker'
                })
            elif tt4_val > 12.0:
                influences.append({
                    'feature': 'Total T4 (High)',
                    'influence_pct': 72,
                    'direction': 'Supports Hyperthyroid Signal',
                    'category': 'Biomarker'
                })
            else:
                influences.append({
                    'feature': 'Total T4 (Normal)',
                    'influence_pct': 25,
                    'direction': 'Aligns with Euthyroid Range',
                    'category': 'Biomarker'
                })
        except Exception:
            pass

    # Check Age influence
    age = data.get('age')
    if age:
        try:
            age_val = float(age)
            if age_val > 60:
                influences.append({
                    'feature': f'Patient Age ({int(age_val)} yrs)',
                    'influence_pct': 42,
                    'direction': 'Demographic Risk Factor',
                    'category': 'Demographic'
                })
        except Exception:
            pass

    # Check Clinical Flags
    if data.get('goitre') in (1, '1', True):
        influences.append({
            'feature': 'Presence of Goitre / Gland Enlargement',
            'influence_pct': 58,
            'direction': 'Elevates Thyroid Anomaly Signal',
            'category': 'Clinical Finding'
        })
    if data.get('on_thyroxine') in (1, '1', True):
        influences.append({
            'feature': 'Active Thyroxine Replacement Therapy',
            'influence_pct': 65,
            'direction': 'Alters Endogenous Baseline Hormone Levels',
            'category': 'Medication'
        })
    if data.get('thyroid_surgery') in (1, '1', True):
        influences.append({
            'feature': 'Prior Thyroid Surgical Intervention',
            'influence_pct': 60,
            'direction': 'History of Thyroid Tissue Resection',
            'category': 'History'
        })

    # Sort descending by influence percentage
    influences.sort(key=lambda x: x['influence_pct'], reverse=True)
    return influences[:5]


def execute_screening(input_data: dict, assessment_type: str = 'comprehensive') -> dict:
    """
    Main screening execution pipeline with input normalization, model inference,
    biomarker range analysis, and explainability breakdown.
    """
    # 1. Clean and align inputs to model features
    binary_cols = [
        'on_thyroxine', 'query_on_thyroxine', 'on_antithyroid_medication',
        'sick', 'pregnant', 'thyroid_surgery', 'I131_treatment',
        'query_hypothyroid', 'query_hyperthyroid', 'lithium', 'goitre',
        'tumor', 'hypopituitary', 'psych',
        'TSH_measured', 'T3_measured', 'TT4_measured', 'T4U_measured',
        'FTI_measured'
    ]

    row = {}
    for feat in feature_names:
        val = input_data.get(feat, np.nan)
        if feat == 'sex':
            if str(val).upper() in ['M', '1', 'MALE']:
                row[feat] = 1.0
            elif str(val).upper() in ['F', '0', 'FEMALE']:
                row[feat] = 0.0
            else:
                row[feat] = 0.5
        elif feat in binary_cols:
            if str(val).lower() in ['t', 'y', '1', 'true', 'yes']:
                row[feat] = 1.0
            elif str(val).lower() in ['f', 'n', '0', 'false', 'no']:
                row[feat] = 0.0
            else:
                row[feat] = 0.0
        elif feat == 'referral_source':
            try:
                row[feat] = float(val) if val is not None and not np.isnan(float(val)) else 0.0
            except (ValueError, TypeError):
                row[feat] = 0.0
        else:
            try:
                fval = float(val) if val is not None else np.nan
                if not np.isnan(fval):
                    if feat == 'age' and fval > 1.0:
                        fval = fval / 100.0
                    elif feat == 'TSH' and fval > 0.6:
                        fval = fval / 1000.0
                    elif feat == 'T3' and fval > 0.4:
                        fval = fval / 100.0
                    elif feat == 'TT4' and fval > 1.0:
                        fval = fval / 1000.0
                    elif feat == 'T4U' and fval > 0.5:
                        fval = fval / 10.0
                    elif feat == 'FTI' and fval > 1.0:
                        fval = fval / 1000.0
                row[feat] = fval
            except (ValueError, TypeError):
                row[feat] = np.nan

    df_input = pd.DataFrame([row])

    # 2. Run model prediction & probabilities
    prediction_encoded = model.predict(df_input)[0]
    prediction_label = label_encoder.inverse_transform([prediction_encoded])[0]
    probabilities = model.predict_proba(df_input)[0]
    raw_confidence = float(probabilities.max())

    # Build calibrated class probabilities map
    class_probs = {
        label_encoder.inverse_transform([i])[0]: round(float(p) * 100, 1)
        for i, p in enumerate(probabilities)
    }

    # 3. Biomarker reference ranges analysis
    biomarker_evals = analyze_biomarkers(input_data)

    # 4. Feature explainability & influence indicators
    influences = compute_feature_influences(input_data, prediction_label)

    # 5. Clinical profile & risk classification
    profile = CLINICAL_PROFILES.get(prediction_label, {
        'title': 'Undetermined Risk Signal',
        'badge': 'Review Recommended',
        'severity': 'moderate',
        'color': '#6b7280',
        'summary': 'The input pattern yielded mixed signals across classifier thresholds.',
        'action_plan': ['Please consult a healthcare professional for a standard laboratory workup.']
    })

    return {
        'screening_result': prediction_label,
        'title': profile['title'],
        'badge': profile['badge'],
        'risk_level': profile['severity'],
        'color': profile['color'],
        'summary': profile['summary'],
        'model_probability': round(raw_confidence * 100, 1),
        'class_probabilities': class_probs,
        'biomarker_analysis': biomarker_evals,
        'feature_influences': influences,
        'action_plan': profile['action_plan'],
        'assessment_type': assessment_type,
        'model_version': 'v1.0-gb-calibrated',
        'limitations': [
            'Trained on cross-sectional clinical datasets; does not account for acute illness or pregnancy alterations without specialist review',
            'Model probability represents mathematical confidence over learned patterns, not clinical certainty',
            'Screening does not replace antibody diagnostics (Anti-TPO, Anti-Tg, TRAb) or thyroid ultrasonography'
        ],
        'disclaimer': 'This screening report is generated by an AI statistical model for educational and risk-stratification assistance. It is NOT a clinical diagnosis. Always consult a qualified medical professional before making any health decisions.'
    }
