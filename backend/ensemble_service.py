"""
ThyroScan — Multi-Model Ensemble Agreement & Calibration Engine
Runs Gradient Boosting, Random Forest, and SVM in parallel.
Computes classifier consensus, dispersion, agreement matrix, and calibrated probabilities.
"""

import os
import json
import joblib
import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, '..', 'models')

# Load individual models
GB_MODEL = joblib.load(os.path.join(MODELS_DIR, 'gb_model.pkl'))
RF_MODEL = joblib.load(os.path.join(MODELS_DIR, 'rf_model.pkl'))
SVM_MODEL = joblib.load(os.path.join(MODELS_DIR, 'svm_model.pkl'))
LABEL_ENCODER = joblib.load(os.path.join(MODELS_DIR, 'label_encoder.pkl'))

with open(os.path.join(MODELS_DIR, 'feature_names.json'), 'r') as f:
    FEATURE_NAMES = json.load(f)

MODEL_REGISTRY = {
    'Gradient Boosting': {
        'model': GB_MODEL,
        'weight': 0.45,
        'accuracy': '97.00%',
        'type': 'Boosting Tree Ensemble'
    },
    'Random Forest': {
        'model': RF_MODEL,
        'weight': 0.40,
        'accuracy': '96.38%',
        'type': 'Bagging Forest Ensemble'
    },
    'SVM (RBF Kernel)': {
        'model': SVM_MODEL,
        'weight': 0.15,
        'accuracy': '87.08%',
        'type': 'Support Vector Machine'
    }
}


def run_ensemble_prediction(input_data: dict) -> dict:
    """
    Executes parallel inference across all ensemble models.
    Returns consensus score, individual model predictions, and calibrated weighted probabilities.
    """
    binary_cols = [
        'on_thyroxine', 'query_on_thyroxine', 'on_antithyroid_medication',
        'sick', 'pregnant', 'thyroid_surgery', 'I131_treatment',
        'query_hypothyroid', 'query_hyperthyroid', 'lithium', 'goitre',
        'tumor', 'hypopituitary', 'psych',
        'TSH_measured', 'T3_measured', 'TT4_measured', 'T4U_measured',
        'FTI_measured'
    ]

    row = {}
    for feat in FEATURE_NAMES:
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

    individual_results = {}
    weighted_probs = np.zeros(len(LABEL_ENCODER.classes_))
    predictions_list = []

    for name, meta in MODEL_REGISTRY.items():
        clf = meta['model']
        pred_encoded = clf.predict(df_input)[0]
        pred_label = LABEL_ENCODER.inverse_transform([pred_encoded])[0]
        probs = clf.predict_proba(df_input)[0]
        conf = float(probs.max()) * 100

        predictions_list.append(pred_label)
        weighted_probs += probs * meta['weight']

        individual_results[name] = {
            'prediction': pred_label,
            'prediction_badge': pred_label.replace('_', ' ').title(),
            'confidence': round(conf, 1),
            'model_type': meta['type'],
            'historical_accuracy': meta['accuracy']
        }

    # Normalize weighted probabilities
    weighted_probs = weighted_probs / sum(meta['weight'] for meta in MODEL_REGISTRY.values())
    ensemble_encoded = np.argmax(weighted_probs)
    ensemble_label = LABEL_ENCODER.inverse_transform([ensemble_encoded])[0]
    calibrated_probability = round(float(weighted_probs.max()) * 100, 1)

    # Calculate model agreement
    agree_count = sum(1 for p in predictions_list if p == ensemble_label)
    total_models = len(predictions_list)
    consensus_ratio = agree_count / total_models

    has_disagreement = agree_count < total_models
    disagreement_warning = None
    if has_disagreement:
        disagreement_warning = (
            f"Note: {agree_count} of {total_models} models favor {ensemble_label.replace('_', ' ').title()}, "
            f"while other classifiers indicated borderline signals. Clinical laboratory confirmation is strongly recommended."
        )

    # Class probability distribution map
    calibrated_class_probs = {
        LABEL_ENCODER.inverse_transform([i])[0]: round(float(p) * 100, 1)
        for i, p in enumerate(weighted_probs)
    }

    return {
        'ensemble_prediction': ensemble_label,
        'calibrated_probability': calibrated_probability,
        'consensus_score': f"{agree_count}/{total_models}",
        'consensus_pct': round(consensus_ratio * 100),
        'has_disagreement': has_disagreement,
        'disagreement_warning': disagreement_warning,
        'individual_models': individual_results,
        'calibrated_class_probabilities': calibrated_class_probs
    }
