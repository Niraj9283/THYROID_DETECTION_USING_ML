import os
import json
import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, AdaBoostClassifier
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, recall_score, roc_auc_score, classification_report
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from imblearn.over_sampling import SMOTE
from sklearn.cluster import KMeans
from kneed import KneeLocator
import xgboost as xgb
import shap
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
MODELS_DIR = BASE_DIR / 'models'
DATASET_PATH = BASE_DIR / 'data/dataset.csv'
MODELS_DIR.mkdir(exist_ok=True)

def main():
    print("🔄 Loading dataset...")
    df = pd.read_csv(DATASET_PATH)
    print(f"Dataset shape: {df.shape}")
    print("\nClass distribution (before SMOTE):")
    print(df['diagnosis'].value_counts())
    
    # Prepare features and target
    X = df.drop(['patient_id', 'diagnosis'], axis=1)
    y = df['diagnosis']
    le = LabelEncoder()
    y_encoded = le.fit_transform(y)
    print(f"Target classes: {le.classes_}")
    
    print(f"\nFeatures: {X.columns.tolist()}")
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(X, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded)
    
# Preprocessing pipeline for numeric and categorical
    numeric_features = ['age', 'TSH', 'T3', 'TT4', 'T4U', 'FTI', 'TBG']
    categorical_features = [col for col in X.columns if col not in numeric_features]
    
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', SimpleImputer(strategy='median'), numeric_features),
            ('cat', Pipeline([
                ('imputer', SimpleImputer(strategy='constant', fill_value='missing')),
                ('onehot', OneHotEncoder(handle_unknown='ignore', sparse_output=False))
            ]), categorical_features)
        ])
    
    X_train_pre = preprocessor.fit_transform(X_train)
    X_test_pre = preprocessor.transform(X_test)
    
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train_pre)
    X_test_scaled = scaler.transform(X_test_pre)
    
    print("\nApplying SMOTE oversampling...")
    smote = SMOTE(random_state=42)
    X_train_smote, y_train_smote = smote.fit_resample(X_train_scaled, y_train)
    print("Class distribution (after SMOTE):")
    print(pd.Series(y_train_smote).value_counts())
    
    # Define 7 models with pipelines
    models = {
        'RandomForest': RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1),
        'GradientBoosting': GradientBoostingClassifier(n_estimators=100, random_state=42),
        'SVM': SVC(probability=True, random_state=42),
        'XGBoost': xgb.XGBClassifier(n_estimators=100, random_state=42, eval_metric='mlogloss'),
        'KNN': KNeighborsClassifier(n_neighbors=5),
        'LogisticRegression': LogisticRegression(max_iter=1000, random_state=42),
        'AdaBoost': AdaBoostClassifier(n_estimators=100, random_state=42)
    }
    
    results = {}
    
    print("\n🚀 Training models...")
    for name, model in models.items():
        print(f"\nTraining {name}...")
        if name in ['SVM', 'KNN', 'LogisticRegression']:
            model.fit(X_train_smote, y_train_smote)
            y_pred = model.predict(X_test_scaled)
            y_proba = model.predict_proba(X_test_scaled)
        else:
            model.fit(X_train_smote, y_train_smote)
            y_pred = model.predict(X_test_scaled)
            y_proba = model.predict_proba(X_test_scaled)
        
        acc = accuracy_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred, average='weighted')
        rec_macro = recall_score(y_test, y_pred, average='macro')
        auc_macro = roc_auc_score(y_test, y_proba, multi_class='ovr', average='macro')
        
        results[name] = {
            'accuracy': float(acc),
            'f1_weighted': float(f1),
            'recall_macro': float(rec_macro),
            'auc_macro': float(auc_macro)
        }
        
        print(f"{name}: Acc={acc:.4f}, F1={f1:.4f}, Recall_macro={rec_macro:.4f}, AUC={auc_macro:.4f}")
        print(classification_report(y_test, y_pred, target_names=le.classes_))
    
    # Select best model by macro recall
    best_model_name = max(results.keys(), key=lambda k: results[k]['recall_macro'])
    best_model = models[best_model_name]
    best_metrics = results[best_model_name]
    print(f"\n🏆 Best model: {best_model_name} (recall_macro: {best_metrics['recall_macro']:.4f})")
    
    # Save best model, encoder, scaler, imputer, feature names
    joblib.dump(best_model, MODELS_DIR / 'best_model.pkl')
    joblib.dump(le, MODELS_DIR / 'label_encoder.pkl')
    joblib.dump(preprocessor, MODELS_DIR / 'preprocessor.pkl')
    joblib.dump(scaler, MODELS_DIR / 'scaler.pkl')
    with open(MODELS_DIR / 'feature_names_original.json', 'w') as f:
        json.dump(X.columns.tolist(), f)
    print(f"Preprocessor output features: {len(preprocessor.get_feature_names_out())}")
    
    # SHAP Explainability (prefer TreeExplainer)
    print("\n🔍 Computing SHAP explanations...")
    try:
        explainer = shap.TreeExplainer(best_model)
        shap_values = explainer.shap_values(X_test_scaled[:100])  # First 100 for speed
        
        # Summary plot
        plt.figure(figsize=(10, 8))
        shap.summary_plot(shap_values, X_test_scaled[:100], feature_names=preprocessor.get_feature_names_out(), show=False)
        plt.tight_layout()
        plt.savefig(MODELS_DIR / 'shap_summary.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        joblib.dump(explainer, MODELS_DIR / 'explainer.pkl')
        joblib.dump(shap_values, MODELS_DIR / 'shap_test_values.pkl')
        print("✅ SHAP explainer and summary plot saved")
    except:
        print("⚠️ TreeExplainer failed, using PermutationExplainer (slower)")
        explainer = shap.PermutationExplainer(best_model.predict_proba, X_train_scaled[:500])
        shap_values = explainer.shap_values(X_test_scaled[:100])
        joblib.dump(explainer, MODELS_DIR / 'explainer.pkl')
        joblib.dump(shap_values, MODELS_DIR / 'shap_test_values.pkl')
    
    # Clustering for personalized predictions
    print("\n🧠 Finding optimal clusters with KneeLocator...")
    k_range = range(2, 11)
    inertias = []
    for k in k_range:
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        kmeans.fit(X_train_scaled)
        inertias.append(kmeans.inertia_)
    
    kl = KneeLocator(k_range, inertias, curve='convex', direction='decreasing')
    optimal_k = kl.elbow
    print(f"Optimal number of clusters: {optimal_k}")
    
    # Train final clusterer
    clusterer = KMeans(n_clusters=optimal_k, random_state=42, n_init=10)
    cluster_labels = clusterer.fit_predict(X_train_scaled)
    joblib.dump(clusterer, MODELS_DIR / 'clusterer.pkl')
    
    # Train per-cluster models (using best model type)
    print("\nTraining per-cluster models...")
    for i in range(optimal_k):
        mask = cluster_labels == i
        if np.sum(mask) > 10:  # Minimum size
            X_cluster = X_train_scaled[mask]
            y_cluster = y_train_smote[mask]
            cluster_model = type(best_model)()
            if hasattr(cluster_model, 'random_state'):
                cluster_model.random_state = 42
            cluster_model.fit(X_cluster, y_cluster)
            joblib.dump(cluster_model, MODELS_DIR / f'cluster_model_{i}.pkl')
            print(f"✅ Cluster {i}: {np.sum(mask)} samples")
        else:
            print(f"⚠️ Cluster {i}: too few samples")
    
    # Update model comparison
    results['best_model'] = {
        'name': best_model_name,
        'recall_macro': best_metrics['recall_macro']
    }
    results['clustering'] = {'n_clusters': int(optimal_k)}
    with open(MODELS_DIR / 'model_comparison.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print("\n🎉 Training complete! All artifacts saved to models/")
    print("New files: explainer.pkl, shap_summary.png, shap_test_values.pkl, clusterer.pkl, cluster_model_*.pkl")

if __name__ == "__main__":
    main()

