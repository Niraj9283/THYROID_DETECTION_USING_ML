"""
Thyroid Detection - Model Training Script
Trains 3 models: Random Forest, Gradient Boosting, SVM
Saves the best performing model.
"""

import pandas as pd
import numpy as np
import joblib
import os
import json
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.svm import SVC
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import (accuracy_score, classification_report,
                              confusion_matrix, f1_score)
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, '..', 'data', 'dataset.csv')
MODELS_DIR = os.path.join(BASE_DIR, '..', 'models')
os.makedirs(MODELS_DIR, exist_ok=True)


def load_and_preprocess(path):
    df = pd.read_csv(path)

    # Drop TBG (97%+ missing), patient_id (identifier), and TBG_measured
    drop_cols = ['patient_id', 'TBG', 'TBG_measured', 'class', 'source']
    df.drop(columns=[c for c in drop_cols if c in df.columns], inplace=True)

    # Encode binary yes/no columns
    binary_cols = ['on_thyroxine', 'query_on_thyroxine', 'on_antithyroid_medication',
                   'sick', 'pregnant', 'thyroid_surgery', 'I131_treatment',
                   'query_hypothyroid', 'query_hyperthyroid', 'lithium', 'goitre',
                   'tumor', 'hypopituitary', 'psych',
                   'TSH_measured', 'T3_measured', 'TT4_measured', 'T4U_measured',
                   'FTI_measured']
    for col in binary_cols:
        if col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].map({'t': 1, 'f': 0, 'y': 1, 'n': 0, 'M': 1, 'F': 0, 'true': 1, 'false': 0}).fillna(0).astype(int)
            else:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

    # Encode sex
    if 'sex' in df.columns:
        if df['sex'].dtype == object:
            df['sex'] = df['sex'].map({'M': 1, 'F': 0, 'm': 1, 'f': 0, 'male': 1, 'female': 0}).fillna(0.5)
        else:
            df['sex'] = pd.to_numeric(df['sex'], errors='coerce').fillna(0.5)

    # Encode referral_source
    if 'referral_source' in df.columns:
        le_ref = LabelEncoder()
        df['referral_source'] = le_ref.fit_transform(df['referral_source'].astype(str))

    # Convert numeric biomarkers
    numeric_cols = ['age', 'TSH', 'T3', 'TT4', 'T4U', 'FTI']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # Encode target
    le_target = LabelEncoder()
    df['diagnosis_encoded'] = le_target.fit_transform(df['diagnosis'])

    X = df.drop(columns=['diagnosis', 'diagnosis_encoded'])
    y = df['diagnosis_encoded']

    return X, y, le_target


def build_models():
    return {
        'Random Forest': Pipeline([
            ('imputer', SimpleImputer(strategy='median')),
            ('clf', RandomForestClassifier(n_estimators=200, max_depth=15,
                                           random_state=42, n_jobs=-1,
                                           class_weight='balanced'))
        ]),
        'Gradient Boosting': Pipeline([
            ('imputer', SimpleImputer(strategy='median')),
            ('clf', GradientBoostingClassifier(n_estimators=150, learning_rate=0.1,
                                                max_depth=5, random_state=42))
        ]),
        'SVM': Pipeline([
            ('imputer', SimpleImputer(strategy='median')),
            ('scaler', StandardScaler()),
            ('clf', SVC(kernel='rbf', C=10, probability=True,
                        class_weight='balanced', random_state=42))
        ])
    }


def evaluate_model(model, X_train, X_test, y_train, y_test, name):
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred, average='weighted')
    print(f"\n{'='*50}")
    print(f"Model: {name}")
    print(f"  Accuracy : {acc:.4f}")
    print(f"  F1 Score : {f1:.4f}")
    print(f"\n  Classification Report:")
    print(classification_report(y_test, y_pred))
    return acc, f1


def main():
    print("Loading and preprocessing data...")
    X, y, le_target = load_and_preprocess(DATA_PATH)
    print(f"Dataset shape: {X.shape}")
    print(f"Classes: {list(le_target.classes_)}")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    models = build_models()
    results = {}

    for name, model in models.items():
        print(f"\nTraining {name}...")
        acc, f1 = evaluate_model(model, X_train, X_test, y_train, y_test, name)
        results[name] = {'accuracy': acc, 'f1': f1, 'model': model}

    # Select best by accuracy
    best_name = max(results, key=lambda k: results[k]['accuracy'])
    best_model = results[best_name]['model']
    best_acc = results[best_name]['accuracy']
    best_f1 = results[best_name]['f1']

    print(f"\n{'='*50}")
    print(f"Best Model: {best_name}")
    print(f"   Accuracy: {best_acc:.4f} | F1: {best_f1:.4f}")

    # Save individual models + best model + label encoder
    file_map = {
        'Random Forest': 'rf_model.pkl',
        'Gradient Boosting': 'gb_model.pkl',
        'SVM': 'svm_model.pkl'
    }
    for m_name, f_name in file_map.items():
        if m_name in results:
            joblib.dump(results[m_name]['model'], os.path.join(MODELS_DIR, f_name))

    joblib.dump(best_model, os.path.join(MODELS_DIR, 'best_model.pkl'))
    joblib.dump(le_target, os.path.join(MODELS_DIR, 'label_encoder.pkl'))

    # Save feature names
    feature_names = list(X.columns)
    with open(os.path.join(MODELS_DIR, 'feature_names.json'), 'w') as f:
        json.dump(feature_names, f)

    # Save comparison results
    comparison = {
        name: {'accuracy': round(results[name]['accuracy'], 4),
               'f1_score': round(results[name]['f1'], 4)}
        for name in results
    }
    comparison['best_model'] = best_name
    with open(os.path.join(MODELS_DIR, 'model_comparison.json'), 'w') as f:
        json.dump(comparison, f, indent=2)

    print(f"\nModel saved to: {MODELS_DIR}/best_model.pkl")
    print("Training complete!")


if __name__ == '__main__':
    main()
