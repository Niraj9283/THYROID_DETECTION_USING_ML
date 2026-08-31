"""
ThyroScan AI — Clinical Model Laboratory & Multi-Family ML Pipeline
Trains and benchmarks 8 diverse model families + Unsupervised Autoencoder Anomaly Screener:
1. XGBoost (Extreme Gradient Boosting)
2. LightGBM (Histogram-based Gradient Boosting)
3. CatBoost (Categorical-aware Gradient Boosting)
4. Random Forest (Bagging Decision Trees)
5. Extra Trees (Extremely Randomized Trees)
6. SVM (RBF Kernel Support Vector Machine)
7. Deep Tabular Neural Network (Multi-Layer Perceptron)
8. Stacking Super Learner (Meta-Ensemble trained on 5-Fold OOF probabilities)
9. Autoencoder Anomaly Screener (Unsupervised reconstruction network)

Computes clinical discrimination and calibration metrics:
- Accuracy & Balanced Accuracy
- Macro & Weighted F1
- Multi-class ROC-AUC (One-vs-Rest)
- Expected Calibration Error (ECE)
- Multi-class Brier Score
"""

import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import json
import joblib
import time
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.model_selection import train_test_split, StratifiedKFold
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    accuracy_score, balanced_accuracy_score, f1_score,
    roc_auc_score, classification_report
)
from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier
from sklearn.svm import SVC
from sklearn.neural_network import MLPClassifier, MLPRegressor
from sklearn.linear_model import LogisticRegression

# Import gradient boosting libraries
try:
    from xgboost import XGBClassifier
    HAS_XGB = True
except ImportError:
    HAS_XGB = False

try:
    from lightgbm import LGBMClassifier
    HAS_LGB = True
except ImportError:
    HAS_LGB = False

try:
    from catboost import CatBoostClassifier
    HAS_CAT = True
except ImportError:
    HAS_CAT = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, '..', 'data', 'dataset.csv')
MODELS_DIR = os.path.join(BASE_DIR, '..', 'models')
os.makedirs(MODELS_DIR, exist_ok=True)


def calculate_ece(y_true, y_prob, n_bins=10):
    """
    Computes Expected Calibration Error (ECE).
    Evaluates whether predicted probabilities reflect true empirical frequencies.
    """
    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    confidences = np.max(y_prob, axis=1)
    predictions = np.argmax(y_prob, axis=1)
    accuracies = (predictions == y_true)

    ece = 0.0
    for i in range(n_bins):
        bin_lower = bin_boundaries[i]
        bin_upper = bin_boundaries[i + 1]
        in_bin = (confidences > bin_lower) & (confidences <= bin_upper)
        prop_in_bin = np.mean(in_bin)

        if prop_in_bin > 0:
            accuracy_in_bin = np.mean(accuracies[in_bin])
            avg_confidence_in_bin = np.mean(confidences[in_bin])
            ece += np.abs(avg_confidence_in_bin - accuracy_in_bin) * prop_in_bin

    return round(float(ece), 4)


def calculate_multiclass_brier(y_true, y_prob, n_classes):
    """Computes multi-class Brier score (mean squared error of probabilities)."""
    y_true_onehot = np.eye(n_classes)[y_true]
    brier = np.mean(np.sum((y_prob - y_true_onehot) ** 2, axis=1))
    return round(float(brier), 4)


from backend.model_lab_service import StackingSuperLearner


def load_and_preprocess(path):
    print(f"Reading dataset from {path}...")
    df = pd.read_csv(path)

    # Drop identifiers and columns with >95% missing values
    drop_cols = ['patient_id', 'TBG', 'TBG_measured']
    df.drop(columns=[c for c in drop_cols if c in df.columns], inplace=True)

    # Encode binary clinical indicators
    binary_cols = [
        'on_thyroxine', 'query_on_thyroxine', 'on_antithyroid_medication',
        'sick', 'pregnant', 'thyroid_surgery', 'I131_treatment',
        'query_hypothyroid', 'query_hyperthyroid', 'lithium', 'goitre',
        'tumor', 'hypopituitary', 'psych',
        'TSH_measured', 'T3_measured', 'TT4_measured', 'T4U_measured',
        'FTI_measured'
    ]
    for col in binary_cols:
        if col in df.columns:
            df[col] = df[col].map({'t': 1, 'f': 0, 'y': 1, 'n': 0, 'M': 1, 'F': 0}).fillna(0).astype(int)

    # Encode sex
    if 'sex' in df.columns:
        df['sex'] = df['sex'].map({'M': 1, 'F': 0}).fillna(0.5)

    # Encode referral source
    if 'referral_source' in df.columns:
        le_ref = LabelEncoder()
        df['referral_source'] = le_ref.fit_transform(df['referral_source'].astype(str))

    # Convert numeric biomarkers
    numeric_cols = ['age', 'TSH', 'T3', 'TT4', 'T4U', 'FTI']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # Encode target diagnosis
    le_target = LabelEncoder()
    df['diagnosis_encoded'] = le_target.fit_transform(df['diagnosis'])

    X = df.drop(columns=['diagnosis', 'diagnosis_encoded'])
    y = df['diagnosis_encoded']

    return X, y, le_target


def train_autoencoder_screener(X_train, y_train, le_target, feature_names):
    """
    Trains an unsupervised bottleneck Autoencoder on normal (euthyroid/negative) patients.
    Reconstruction error serves as an anomaly screener for rare/outlier profiles.
    """
    print("\n" + "="*60)
    print("Training Unsupervised Autoencoder Anomaly Screener...")

    # Identify normal class index
    neg_idx = np.where(le_target.classes_ == 'negative')[0]
    if len(neg_idx) > 0:
        normal_mask = (y_train == neg_idx[0])
        X_normal = X_train[normal_mask]
    else:
        X_normal = X_train

    imputer = SimpleImputer(strategy='median')
    scaler = StandardScaler()

    X_normal_imp = imputer.fit_transform(X_normal)
    X_normal_scaled = scaler.fit_transform(X_normal_imp)

    # Bottleneck Autoencoder architecture: D -> 16 -> 8 (Bottleneck) -> 16 -> D
    autoencoder = MLPRegressor(
        hidden_layer_sizes=(16, 8, 16),
        activation='relu',
        solver='adam',
        max_iter=250,
        random_state=42,
        early_stopping=True,
        n_iter_no_change=10
    )
    autoencoder.fit(X_normal_scaled, X_normal_scaled)

    # Evaluate reconstruction error on normal training samples
    reconstructions = autoencoder.predict(X_normal_scaled)
    mse_errors = np.mean((X_normal_scaled - reconstructions) ** 2, axis=1)

    mean_error = float(np.mean(mse_errors))
    std_error = float(np.std(mse_errors))
    threshold = float(mean_error + 2.5 * std_error)

    print(f"Autoencoder Trained on {len(X_normal)} Normal Profiles:")
    print(f"  Mean Reconstruction MSE : {mean_error:.4f}")
    print(f"  Std Reconstruction MSE  : {std_error:.4f}")
    print(f"  Anomaly Cutoff Threshold: {threshold:.4f}")

    autoencoder_pipeline = {
        'imputer': imputer,
        'scaler': scaler,
        'model': autoencoder,
        'feature_names': feature_names
    }

    metadata = {
        'mean_mse': round(mean_error, 4),
        'std_mse': round(std_error, 4),
        'anomaly_threshold': round(threshold, 4),
        'architecture': 'Bottleneck Neural Autoencoder (Input -> 16 -> 8 -> 16 -> Output)',
        'trained_samples': int(len(X_normal)),
        'features': feature_names
    }

    joblib.dump(autoencoder_pipeline, os.path.join(MODELS_DIR, 'autoencoder_model.pkl'))
    with open(os.path.join(MODELS_DIR, 'autoencoder_metadata.json'), 'w') as f:
        json.dump(metadata, f, indent=2)

    return metadata


def build_candidate_models():
    """Builds pipeline dictionary of diverse model families."""
    models = {}

    # 1. XGBoost
    if HAS_XGB:
        models['XGBoost'] = {
            'pipeline': Pipeline([
                ('imputer', SimpleImputer(strategy='median')),
                ('clf', XGBClassifier(
                    n_estimators=160,
                    max_depth=6,
                    learning_rate=0.08,
                    subsample=0.85,
                    colsample_bytree=0.85,
                    random_state=42,
                    eval_metric='mlogloss',
                    n_jobs=-1
                ))
            ]),
            'type': 'Extreme Gradient Boosting Tree',
            'strengths': 'Robust non-linear feature splits, regularization, high tabular accuracy.'
        }

    # 2. LightGBM
    if HAS_LGB:
        models['LightGBM'] = {
            'pipeline': Pipeline([
                ('imputer', SimpleImputer(strategy='median')),
                ('clf', LGBMClassifier(
                    n_estimators=160,
                    max_depth=6,
                    learning_rate=0.08,
                    num_leaves=31,
                    subsample=0.85,
                    random_state=42,
                    verbose=-1,
                    n_jobs=-1
                ))
            ]),
            'type': 'Histogram Gradient Booster',
            'strengths': 'Ultra-fast training, memory efficiency, optimal continuous feature binning.'
        }

    # 3. CatBoost
    if HAS_CAT:
        models['CatBoost'] = {
            'pipeline': Pipeline([
                ('imputer', SimpleImputer(strategy='median')),
                ('clf', CatBoostClassifier(
                    iterations=180,
                    depth=6,
                    learning_rate=0.08,
                    random_seed=42,
                    verbose=False,
                    thread_count=-1
                ))
            ]),
            'type': 'Categorical Gradient Booster',
            'strengths': 'Symmetric trees, ordered boosting, resists target leakage and overfitting.'
        }

    # 4. Random Forest
    models['Random Forest'] = {
        'pipeline': Pipeline([
            ('imputer', SimpleImputer(strategy='median')),
            ('clf', RandomForestClassifier(
                n_estimators=160,
                max_depth=15,
                class_weight='balanced',
                random_state=42,
                n_jobs=-1
            ))
        ]),
        'type': 'Bagging Decision Forest',
        'strengths': 'Parallel ensemble voting, resilience to feature noise and class imbalance.'
    }

    # 5. Extra Trees
    models['Extra Trees'] = {
        'pipeline': Pipeline([
            ('imputer', SimpleImputer(strategy='median')),
            ('clf', ExtraTreesClassifier(
                n_estimators=160,
                max_depth=15,
                class_weight='balanced',
                random_state=42,
                n_jobs=-1
            ))
        ]),
        'type': 'Extremely Randomized Trees',
        'strengths': 'Aggressive variance reduction through randomized split cutoffs.'
    }

    # 6. SVM (RBF Kernel)
    models['SVM (RBF)'] = {
        'pipeline': Pipeline([
            ('imputer', SimpleImputer(strategy='median')),
            ('scaler', StandardScaler()),
            ('clf', SVC(
                kernel='rbf',
                C=10,
                probability=True,
                class_weight='balanced',
                max_iter=3000,
                random_state=42
            ))
        ]),
        'type': 'Support Vector Machine (RBF)',
        'strengths': 'Max-margin hyperplane optimization, non-linear kernel projection.'
    }

    # 7. Deep Tabular Neural Network (MLP)
    models['Deep MLP'] = {
        'pipeline': Pipeline([
            ('imputer', SimpleImputer(strategy='median')),
            ('scaler', StandardScaler()),
            ('clf', MLPClassifier(
                hidden_layer_sizes=(128, 64),
                activation='relu',
                alpha=0.0001,
                learning_rate_init=0.001,
                max_iter=200,
                early_stopping=True,
                n_iter_no_change=10,
                random_state=42
            ))
        ]),
        'type': 'Deep Tabular Neural Network',
        'strengths': 'Deep representation learning, multi-scale hidden bottleneck features.'
    }

    return models


def train_stacking_ensemble(candidate_models, X_train, y_train, X_test, y_test, le_target):
    """
    Builds and trains an Out-of-Fold (OOF) Stacking Super Learner.
    Meta-learner combines probability predictions from top tree and neural models.
    """
    print("\n" + "="*60)
    print("Training Stacking Super Learner Ensemble (5-Fold CV Meta-Learner)...")

    # Base estimators for stacking: LightGBM, XGBoost, CatBoost, RandomForest, ExtraTrees
    stack_keys = ['LightGBM', 'XGBoost', 'CatBoost', 'Random Forest', 'Extra Trees']
    stack_estimators = []
    for key in stack_keys:
        if key in candidate_models:
            stack_estimators.append((key, candidate_models[key]['pipeline']))

    super_learner = StackingSuperLearner(base_models=stack_estimators)

    t0 = time.time()
    super_learner.fit(X_train, y_train, cv=5)
    train_time = round(time.time() - t0, 2)

    y_pred = super_learner.predict(X_test)
    y_prob = super_learner.predict_proba(X_test)
    n_classes = len(le_target.classes_)

    acc = round(accuracy_score(y_test, y_pred) * 100, 2)
    bal_acc = round(balanced_accuracy_score(y_test, y_pred) * 100, 2)
    macro_f1 = round(f1_score(y_test, y_pred, average='macro') * 100, 2)
    weighted_f1 = round(f1_score(y_test, y_pred, average='weighted') * 100, 2)
    roc_auc = round(roc_auc_score(y_test, y_prob, multi_class='ovr') * 100, 2)
    ece = calculate_ece(y_test.values if hasattr(y_test, 'values') else y_test, y_prob)
    brier = calculate_multiclass_brier(y_test.values if hasattr(y_test, 'values') else y_test, y_prob, n_classes)

    print(f"Stacking Super Learner Performance:")
    print(f"  Accuracy       : {acc:.2f}%")
    print(f"  Balanced Acc   : {bal_acc:.2f}%")
    print(f"  Macro F1       : {macro_f1:.2f}%")
    print(f"  ROC-AUC (OvR)  : {roc_auc:.2f}%")
    print(f"  ECE Calibration: {ece:.4f}")
    print(f"  Brier Score    : {brier:.4f}")
    print(f"  Training Time  : {train_time}s")

    joblib.dump(super_learner, os.path.join(MODELS_DIR, 'stacking_model.pkl'))

    return {
        'model': super_learner,
        'metrics': {
            'accuracy': acc,
            'balanced_accuracy': bal_acc,
            'macro_f1': macro_f1,
            'weighted_f1': weighted_f1,
            'roc_auc': roc_auc,
            'ece': ece,
            'brier_score': brier,
            'train_time_sec': train_time,
            'model_type': 'Stacking Super Learner (Meta-Ensemble)',
            'strengths': 'Optimal meta-weighting over out-of-fold probability vectors.'
        }
    }


def main():
    print("="*60)
    print("THYROSCAN AI — COMPREHENSIVE MODEL LABORATORY BENCHMARK")
    print("="*60)

    X, y, le_target = load_and_preprocess(DATA_PATH)
    n_classes = len(le_target.classes_)
    feature_names = list(X.columns)

    print(f"Dataset Loaded: {X.shape[0]} patient records, {X.shape[1]} clinical biomarkers.")
    print(f"Target Classes ({n_classes}): {list(le_target.classes_)}")

    # 80/20 Stratified Train-Test Split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    # 1. Train Autoencoder Anomaly Screener
    autoencoder_meta = train_autoencoder_screener(X_train, y_train, le_target, feature_names)

    # 2. Build and Train Candidate Base Models
    candidate_models = build_candidate_models()
    benchmark_results = {}

    file_mapping = {
        'XGBoost': 'xgb_model.pkl',
        'LightGBM': 'lgbm_model.pkl',
        'CatBoost': 'catboost_model.pkl',
        'Random Forest': 'rf_model.pkl',
        'Extra Trees': 'extra_trees_model.pkl',
        'SVM (RBF)': 'svm_model.pkl',
        'Deep MLP': 'mlp_model.pkl'
    }

    print("\n" + "="*60)
    print(f"Training {len(candidate_models)} Individual Model Families...")
    print("="*60)

    for name, config in candidate_models.items():
        print(f"\nTraining [{name}] ({config['type']})...")
        pipeline = config['pipeline']

        t0 = time.time()
        pipeline.fit(X_train, y_train)
        train_time = round(time.time() - t0, 2)

        y_pred = pipeline.predict(X_test)
        y_prob = pipeline.predict_proba(X_test)

        acc = round(accuracy_score(y_test, y_pred) * 100, 2)
        bal_acc = round(balanced_accuracy_score(y_test, y_pred) * 100, 2)
        macro_f1 = round(f1_score(y_test, y_pred, average='macro') * 100, 2)
        weighted_f1 = round(f1_score(y_test, y_pred, average='weighted') * 100, 2)
        roc_auc = round(roc_auc_score(y_test, y_prob, multi_class='ovr') * 100, 2)
        ece = calculate_ece(y_test.values, y_prob)
        brier = calculate_multiclass_brier(y_test.values, y_prob, n_classes)

        print(f"  Accuracy: {acc:.2f}% | Bal. Acc: {bal_acc:.2f}% | Macro F1: {macro_f1:.2f}% | ROC-AUC: {roc_auc:.2f}% | ECE: {ece:.4f} | Brier: {brier:.4f} | Time: {train_time}s")

        benchmark_results[name] = {
            'accuracy': acc,
            'balanced_accuracy': bal_acc,
            'macro_f1': macro_f1,
            'weighted_f1': weighted_f1,
            'roc_auc': roc_auc,
            'ece': ece,
            'brier_score': brier,
            'train_time_sec': train_time,
            'model_type': config['type'],
            'strengths': config['strengths']
        }

        # Save individual model
        if name in file_mapping:
            joblib.dump(pipeline, os.path.join(MODELS_DIR, file_mapping[name]))

    # 3. Train Stacking Super Learner Ensemble
    stacking_res = train_stacking_ensemble(candidate_models, X_train, y_train, X_test, y_test, le_target)
    benchmark_results['Stacking Super Learner'] = stacking_res['metrics']

    # 4. Save Common Artifacts
    joblib.dump(le_target, os.path.join(MODELS_DIR, 'label_encoder.pkl'))

    with open(os.path.join(MODELS_DIR, 'feature_names.json'), 'w') as f:
        json.dump(feature_names, f, indent=2)

    # Champion model selection
    champion_name = max(benchmark_results.keys(), key=lambda k: (benchmark_results[k]['balanced_accuracy'], benchmark_results[k]['roc_auc']))

    if champion_name == 'Stacking Super Learner':
        best_model_obj = stacking_res['model']
    else:
        best_model_obj = candidate_models[champion_name]['pipeline']

    joblib.dump(best_model_obj, os.path.join(MODELS_DIR, 'best_model.pkl'))
    if 'LightGBM' in candidate_models:
        joblib.dump(candidate_models['LightGBM']['pipeline'], os.path.join(MODELS_DIR, 'gb_model.pkl'))

    full_laboratory_manifest = {
        'champion_model': champion_name,
        'dataset_records': int(X.shape[0]),
        'feature_count': int(X.shape[1]),
        'classes': list(le_target.classes_),
        'metrics_timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'leaderboard': benchmark_results,
        'autoencoder': autoencoder_meta
    }

    with open(os.path.join(MODELS_DIR, 'laboratory_benchmarks.json'), 'w') as f:
        json.dump(full_laboratory_manifest, f, indent=2)

    # Legacy model comparison compatibility
    legacy_comparison = {
        name: {
            'accuracy': round(meta['accuracy'] / 100, 4),
            'f1_score': round(meta['macro_f1'] / 100, 4)
        }
        for name, meta in benchmark_results.items()
    }
    legacy_comparison['best_model'] = champion_name
    with open(os.path.join(MODELS_DIR, 'model_comparison.json'), 'w') as f:
        json.dump(legacy_comparison, f, indent=2)

    print("\n" + "="*60)
    print("LABORATORY BENCHMARKING COMPLETE!")
    print(f"Champion Model: {champion_name}")
    print(f"Artifacts exported to: {MODELS_DIR}")
    print("="*60)


if __name__ == '__main__':
    main()
