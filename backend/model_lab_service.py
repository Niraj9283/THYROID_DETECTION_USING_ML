"""
ThyroScan AI — Model Laboratory & Multi-Family Tournament Service
Provides live parallel inference across 8 model families, unsupervised autoencoder anomaly screening,
consensus dispersion analysis, and clinical leaderboard benchmarks.
"""

import os
import json
import joblib
import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, '..', 'models')

from sklearn.base import clone
from sklearn.model_selection import StratifiedKFold
from sklearn.linear_model import LogisticRegression

class StackingSuperLearner:
    """
    Super Learner Meta-Ensemble representation for unpickling and inference.
    """
    def __init__(self, base_models, meta_learner=None):
        self.base_models = base_models
        self.meta_learner = meta_learner or LogisticRegression(max_iter=1000, C=1.0, random_state=42)

    def fit(self, X, y, cv=5):
        skf = StratifiedKFold(n_splits=cv, shuffle=True, random_state=42)
        n_classes = len(np.unique(y))
        n_models = len(self.base_models)
        oof_preds = np.zeros((len(X), n_models * n_classes))

        X_df = X.reset_index(drop=True) if hasattr(X, 'reset_index') else pd.DataFrame(X)
        y_ser = y.reset_index(drop=True) if hasattr(y, 'reset_index') else pd.Series(y)

        print(f"  Generating Out-Of-Fold probabilities across {cv} folds for {n_models} base models...")
        for m_idx, (name, pipe) in enumerate(self.base_models):
            for fold_idx, (train_idx, val_idx) in enumerate(skf.split(X_df, y_ser)):
                X_tr, y_tr = X_df.iloc[train_idx], y_ser.iloc[train_idx]
                X_val = X_df.iloc[val_idx]

                pipe_clone = clone(pipe)
                pipe_clone.fit(X_tr, y_tr)
                oof_preds[val_idx, m_idx * n_classes:(m_idx + 1) * n_classes] = pipe_clone.predict_proba(X_val)

        print("  Fitting meta-learner on out-of-fold probability matrix...")
        self.meta_learner.fit(oof_preds, y_ser)

        print("  Fitting final base models on full dataset...")
        for name, pipe in self.base_models:
            pipe.fit(X_df, y_ser)

        return self

    def predict_proba(self, X):
        X_df = X.reset_index(drop=True) if hasattr(X, 'reset_index') else pd.DataFrame(X)
        meta_features = []
        for name, pipe in self.base_models:
            probs = pipe.predict_proba(X_df)
            meta_features.append(probs)
        meta_features = np.hstack(meta_features)
        return self.meta_learner.predict_proba(meta_features)

    def predict(self, X):
        probs = self.predict_proba(X)
        return np.argmax(probs, axis=1)


def load_lab_resources():
    global LABEL_ENCODER, FEATURE_NAMES, BENCHMARKS_DATA, AUTOENCODER_PIPELINE, AUTOENCODER_METADATA, LOADED_LAB_MODELS

    # 1. Feature Names
    feat_path = os.path.join(MODELS_DIR, 'feature_names.json')
    if os.path.exists(feat_path):
        with open(feat_path, 'r') as f:
            FEATURE_NAMES = json.load(f)

    # 2. Label Encoder
    le_path = os.path.join(MODELS_DIR, 'label_encoder.pkl')
    if os.path.exists(le_path):
        LABEL_ENCODER = joblib.load(le_path)

    # 3. Benchmarks Data
    bench_path = os.path.join(MODELS_DIR, 'laboratory_benchmarks.json')
    if os.path.exists(bench_path):
        with open(bench_path, 'r') as f:
            BENCHMARKS_DATA = json.load(f)

    # 4. Autoencoder Anomaly Model
    ae_path = os.path.join(MODELS_DIR, 'autoencoder_model.pkl')
    ae_meta_path = os.path.join(MODELS_DIR, 'autoencoder_metadata.json')
    if os.path.exists(ae_path):
        AUTOENCODER_PIPELINE = joblib.load(ae_path)
    if os.path.exists(ae_meta_path):
        with open(ae_meta_path, 'r') as f:
            AUTOENCODER_METADATA = json.load(f)

    # 5. Model Registry
    model_files = {
        'Stacking Super Learner': {'file': 'stacking_model.pkl', 'weight': 0.25, 'badge': 'Super Learner'},
        'XGBoost': {'file': 'xgb_model.pkl', 'weight': 0.18, 'badge': 'Extreme Gradient Boost'},
        'LightGBM': {'file': 'lgbm_model.pkl', 'weight': 0.15, 'badge': 'Histogram Gradient Boost'},
        'CatBoost': {'file': 'catboost_model.pkl', 'weight': 0.15, 'badge': 'Categorical Boost'},
        'Random Forest': {'file': 'rf_model.pkl', 'weight': 0.10, 'badge': 'Bagging Forest'},
        'Extra Trees': {'file': 'extra_trees_model.pkl', 'weight': 0.08, 'badge': 'Randomized Trees'},
        'Deep MLP': {'file': 'mlp_model.pkl', 'weight': 0.05, 'badge': 'Deep Tabular Net'},
        'SVM (RBF)': {'file': 'svm_model.pkl', 'weight': 0.04, 'badge': 'Support Vector Machine'}
    }

    LOADED_LAB_MODELS = {}
    for name, meta in model_files.items():
        path = os.path.join(MODELS_DIR, meta['file'])
        if os.path.exists(path):
            try:
                clf = joblib.load(path)
                hist_acc = "N/A"
                bal_acc = "N/A"
                f1_score_val = "N/A"
                if BENCHMARKS_DATA and 'leaderboard' in BENCHMARKS_DATA:
                    for lb_name, lb_meta in BENCHMARKS_DATA['leaderboard'].items():
                        if name.lower() in lb_name.lower() or lb_name.lower() in name.lower():
                            hist_acc = f"{lb_meta.get('accuracy', 0):.2f}%"
                            bal_acc = f"{lb_meta.get('balanced_accuracy', 0):.2f}%"
                            f1_score_val = f"{lb_meta.get('macro_f1', 0):.2f}%"
                            break

                LOADED_LAB_MODELS[name] = {
                    'model': clf,
                    'weight': meta['weight'],
                    'badge': meta['badge'],
                    'historical_accuracy': hist_acc,
                    'balanced_accuracy': bal_acc,
                    'macro_f1': f1_score_val
                }
            except Exception as e:
                print(f"[ModelLab] Could not load {name}: {e}")

# Initial load
load_lab_resources()


def prepare_input_dataframe(input_data: dict) -> pd.DataFrame:
    """Formats raw user input into an aligned, numerically encoded feature DataFrame."""
    global FEATURE_NAMES
    if not FEATURE_NAMES:
        load_lab_resources()

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

    df = pd.DataFrame([row])
    return df


def screen_anomalies_autoencoder(input_data: dict) -> dict:
    """
    Evaluates patient biomarkers through the unsupervised bottleneck Autoencoder.
    Calculates reconstruction error ||X - X_hat||^2 against physiological normal threshold.
    """
    global AUTOENCODER_PIPELINE, AUTOENCODER_METADATA
    if AUTOENCODER_PIPELINE is None:
        load_lab_resources()

    if AUTOENCODER_PIPELINE is None:
        return {
            'available': False,
            'message': 'Autoencoder screener model is initializing.'
        }

    try:
        imputer = AUTOENCODER_PIPELINE['imputer']
        scaler = AUTOENCODER_PIPELINE['scaler']
        model = AUTOENCODER_PIPELINE['model']
        feature_names = AUTOENCODER_PIPELINE['feature_names']

        df_raw = prepare_input_dataframe(input_data)

        # Impute and standardize
        X_imp = imputer.transform(df_raw)
        X_scaled = scaler.transform(X_imp)

        # Reconstruct
        X_recon = model.predict(X_scaled)
        feature_squared_errors = (X_scaled[0] - X_recon[0]) ** 2
        total_mse = float(np.mean(feature_squared_errors))

        threshold = AUTOENCODER_METADATA.get('anomaly_threshold', 1.5)
        mean_mse = AUTOENCODER_METADATA.get('mean_mse', 0.5)
        std_mse = AUTOENCODER_METADATA.get('std_mse', 0.4)

        is_anomaly = bool(total_mse > threshold)
        z_score = float((total_mse - mean_mse) / (std_mse if std_mse > 0 else 1.0))

        # Identify top 3 anomalous biomarkers with largest reconstruction deviation
        ranked_feature_indices = np.argsort(feature_squared_errors)[::-1]
        top_anomalous_biomarkers = []
        for idx in ranked_feature_indices[:3]:
            feat_name = feature_names[idx]
            err_val = float(feature_squared_errors[idx])
            raw_val = input_data.get(feat_name, 'N/A')
            top_anomalous_biomarkers.append({
                'biomarker': feat_name,
                'input_value': raw_val,
                'reconstruction_error': round(err_val, 3)
            })

        if is_anomaly:
            clinical_status = "Atypical / Outlier Physiological Profile"
            clinical_guidance = (
                "The patient's combination of hormone levels and clinical flags diverges significantly "
                "from standard baseline endocrine patterns. Endocrinology review and repeat lab verification advised."
            )
        else:
            clinical_status = "Standard Physiological Distribution"
            clinical_guidance = "Lab biomarkers fit within expected historical endocrine distribution bounds."

        return {
            'available': True,
            'is_anomaly': is_anomaly,
            'anomaly_score': round(total_mse, 4),
            'anomaly_threshold': round(threshold, 4),
            'deviation_z_score': round(z_score, 2),
            'clinical_status': clinical_status,
            'clinical_guidance': clinical_guidance,
            'top_deviating_biomarkers': top_anomalous_biomarkers
        }
    except Exception as e:
        return {
            'available': False,
            'error': str(e)
        }


def run_model_laboratory_tournament(input_data: dict) -> dict:
    """
    Executes parallel inference across all model families in the laboratory.
    Calculates consensus scores, pairwise agreement, and calibrated probability matrices.
    """
    global LOADED_LAB_MODELS, LABEL_ENCODER
    if not LOADED_LAB_MODELS or LABEL_ENCODER is None:
        load_lab_resources()

    if not LOADED_LAB_MODELS:
        return {'error': 'Model Laboratory models are not yet loaded.'}

    df_input = prepare_input_dataframe(input_data)
    classes = list(LABEL_ENCODER.classes_)
    n_classes = len(classes)

    individual_predictions = {}
    predictions_tally = {}
    weighted_probability_vector = np.zeros(n_classes)
    total_weights = 0.0

    for model_name, meta in LOADED_LAB_MODELS.items():
        clf = meta['model']
        weight = meta['weight']

        try:
            pred_encoded = clf.predict(df_input)[0]
            pred_label = LABEL_ENCODER.inverse_transform([pred_encoded])[0]

            if hasattr(clf, 'predict_proba'):
                probs = clf.predict_proba(df_input)[0]
                conf = float(probs.max()) * 100
                prob_map = {classes[i]: round(float(probs[i]) * 100, 1) for i in range(n_classes)}
            else:
                probs = np.zeros(n_classes)
                probs[pred_encoded] = 1.0
                conf = 100.0
                prob_map = {classes[i]: (100.0 if i == pred_encoded else 0.0) for i in range(n_classes)}

            weighted_probability_vector += probs * weight
            total_weights += weight

            predictions_tally[pred_label] = predictions_tally.get(pred_label, 0) + 1

            individual_predictions[model_name] = {
                'prediction': pred_label,
                'prediction_badge': pred_label.replace('_', ' ').title(),
                'confidence': round(conf, 1),
                'model_badge': meta['badge'],
                'historical_accuracy': meta['historical_accuracy'],
                'balanced_accuracy': meta['balanced_accuracy'],
                'macro_f1': meta['macro_f1'],
                'class_probabilities': prob_map
            }
        except Exception as e:
            individual_predictions[model_name] = {
                'error': str(e)
            }

    if total_weights > 0:
        weighted_probability_vector /= total_weights

    ensemble_encoded = int(np.argmax(weighted_probability_vector))
    ensemble_label = classes[ensemble_encoded]
    ensemble_confidence = round(float(weighted_probability_vector.max()) * 100, 1)

    total_valid_models = sum(1 for res in individual_predictions.values() if 'prediction' in res)
    consensus_count = predictions_tally.get(ensemble_label, 0)
    consensus_pct = round((consensus_count / total_valid_models) * 100) if total_valid_models > 0 else 0

    has_split_opinion = consensus_count < total_valid_models
    split_opinion_warning = None
    if has_split_opinion:
        other_opinions = [f"{lbl.replace('_', ' ').title()} ({cnt} models)" for lbl, cnt in predictions_tally.items() if lbl != ensemble_label]
        split_opinion_warning = (
            f"Consensus: {consensus_count} of {total_valid_models} models favor {ensemble_label.replace('_', ' ').title()}. "
            f"Alternative votes: {', '.join(other_opinions)}. Multi-classifier divergence suggests borderline biomarker values."
        )

    # Anomaly screener
    anomaly_assessment = screen_anomalies_autoencoder(input_data)

    calibrated_distribution = {
        classes[i]: round(float(weighted_probability_vector[i]) * 100, 1)
        for i in range(n_classes)
    }

    return {
        'champion_prediction': ensemble_label,
        'champion_prediction_badge': ensemble_label.replace('_', ' ').title(),
        'champion_confidence': ensemble_confidence,
        'consensus_score': f"{consensus_count}/{total_valid_models}",
        'consensus_pct': consensus_pct,
        'has_split_opinion': has_split_opinion,
        'split_opinion_warning': split_opinion_warning,
        'predictions_tally': predictions_tally,
        'calibrated_distribution': calibrated_distribution,
        'individual_models': individual_predictions,
        'anomaly_screening': anomaly_assessment
    }


def get_laboratory_benchmarks() -> dict:
    """Returns the comprehensive benchmark leaderboard and metrics metadata."""
    global BENCHMARKS_DATA
    if not BENCHMARKS_DATA:
        load_lab_resources()
    return BENCHMARKS_DATA
