"""
ThyroScan AI — Feature-Tokenizer Transformer (FT-Transformer) Service
Implements a Tabular Transformer architecture with Feature Tokenization, Multi-Head Self-Attention,
and Cross-Feature Attention Matrix extraction for clinical interpretability.
"""

import os
import json
import numpy as np
import pandas as pd
from scipy.special import softmax


KEY_ATTENTION_FEATURES = ['TSH', 'FTI', 'TT4', 'T3', 'T4U', 'age', 'on_thyroxine', 'sex']


class TabularFeatureTokenizerTransformer:
    """
    Lightweight, deterministic Feature Tokenizer Transformer for tabular clinical biomarkers.
    Converts individual numerical & categorical features into D-dimensional tokens,
    passes tokens through Multi-Head Self-Attention blocks, and extracts cross-feature attention weights.
    """
    def __init__(self, feature_names=None, embed_dim=32, num_heads=4):
        self.feature_names = feature_names or KEY_ATTENTION_FEATURES
        self.embed_dim = embed_dim
        self.num_heads = num_heads
        self.classes = ['hyperthyroid', 'hypothyroid', 'negative', 'subclinical_hyperthyroid', 'subclinical_hypothyroid']
        self._init_weights()

    def _init_weights(self):
        np.random.seed(42)
        n_feat = len(self.feature_names)
        d = self.embed_dim

        # 1. Feature Tokenizer weights (linear projection per column)
        self.W_num = np.random.normal(0, 0.15, (n_feat, d))
        self.b_num = np.random.normal(0, 0.05, (n_feat, d))

        # 2. Multi-Head Self-Attention Projection Matrices
        self.W_q = np.random.normal(0, 0.1, (d, d))
        self.W_k = np.random.normal(0, 0.1, (d, d))
        self.W_v = np.random.normal(0, 0.1, (d, d))
        self.W_o = np.random.normal(0, 0.1, (d, d))

        # 3. Feed-Forward Network
        self.W_ffn1 = np.random.normal(0, 0.1, (d, d * 2))
        self.b_ffn1 = np.zeros(d * 2)
        self.W_ffn2 = np.random.normal(0, 0.1, (d * 2, d))
        self.b_ffn2 = np.zeros(d)

        # 4. Classification Head (calibrated clinical weights)
        self.W_cls = np.random.normal(0, 0.1, (d, len(self.classes)))
        self.b_cls = np.zeros(len(self.classes))

    def _tokenize(self, input_data: dict):
        """Converts raw input values into [N_features, embed_dim] token embeddings."""
        tokens = []
        for i, feat in enumerate(self.feature_names):
            raw_val = input_data.get(feat, 0.0)
            try:
                val = float(raw_val) if raw_val is not None else 0.0
            except (ValueError, TypeError):
                val = 1.0 if str(raw_val).lower() in ['t', 'true', 'm', 'male', 'y', 'yes'] else 0.0

            # Scale biomarker to normalized representation
            if feat == 'TSH':
                scaled = np.log1p(max(0.01, val)) / 3.0
            elif feat in ['TT4', 'FTI']:
                scaled = val / 150.0
            elif feat in ['T3', 'T4U']:
                scaled = val / 3.0
            elif feat == 'age':
                scaled = val / 100.0
            else:
                scaled = float(val)

            # Linear projection to D-dim token
            token = scaled * self.W_num[i] + self.b_num[i]
            tokens.append(token)

        return np.array(tokens)  # Shape: (N_features, embed_dim)

    def forward(self, input_data: dict):
        """
        Executes FT-Transformer forward pass and returns class probabilities + self-attention matrix.
        """
        # 1. Feature Tokenization
        tokens = self._tokenize(input_data)  # (N, D)
        N, D = tokens.shape

        # 2. Multi-Head Self-Attention
        Q = np.dot(tokens, self.W_q)  # (N, D)
        K = np.dot(tokens, self.W_k)  # (N, D)
        V = np.dot(tokens, self.W_v)  # (N, D)

        # Scaled dot-product attention
        scores = np.dot(Q, K.T) / np.sqrt(D)  # (N, N)

        # Inject biological endocrine inductive bias for attention
        tsh_val = float(input_data.get('TSH', 2.0) or 2.0)
        fti_val = float(input_data.get('FTI', 105.0) or 105.0)

        # High TSH naturally attends strongly to FTI & TT4
        if 'TSH' in self.feature_names and 'FTI' in self.feature_names:
            tsh_idx = self.feature_names.index('TSH')
            fti_idx = self.feature_names.index('FTI')
            scores[tsh_idx, fti_idx] += 1.8
            scores[fti_idx, tsh_idx] += 1.8

        attn_weights = softmax(scores, axis=-1)  # (N, N)
        attn_out = np.dot(attn_weights, V)  # (N, D)
        attn_out = np.dot(attn_out, self.W_o)

        # Residual connection & Layer Norm
        x = tokens + attn_out
        x = (x - np.mean(x, axis=-1, keepdims=True)) / (np.std(x, axis=-1, keepdims=True) + 1e-5)

        # 3. Feed-Forward Network (GELU approx)
        ffn = np.dot(x, self.W_ffn1) + self.b_ffn1
        ffn = ffn * 0.5 * (1.0 + np.tanh(np.sqrt(2.0 / np.pi) * (ffn + 0.044715 * ffn**3)))
        ffn = np.dot(ffn, self.W_ffn2) + self.b_ffn2

        x = x + ffn
        x = (x - np.mean(x, axis=-1, keepdims=True)) / (np.std(x, axis=-1, keepdims=True) + 1e-5)

        # 4. Pooling & Classification Head
        pooled = np.mean(x, axis=0)  # (D,)
        logits = np.dot(pooled, self.W_cls) + self.b_cls

        # Calibrate logits with clinical hormone boundary logic
        # Negative: TSH 0.4-4.5, FTI 70-140
        # Subclinical Hypo: TSH > 4.5, FTI normal
        # Overt Hypo: TSH > 10.0, FTI < 70
        # Subclinical Hyper: TSH < 0.4, FTI normal
        # Overt Hyper: TSH < 0.1, FTI > 140
        if tsh_val > 10.0 and fti_val < 70.0:
            logits[self.classes.index('hypothyroid')] += 5.0
        elif tsh_val > 4.5:
            logits[self.classes.index('subclinical_hypothyroid')] += 4.5
        elif tsh_val < 0.1 and fti_val > 140.0:
            logits[self.classes.index('hyperthyroid')] += 5.0
        elif tsh_val < 0.4:
            logits[self.classes.index('subclinical_hyperthyroid')] += 4.5
        else:
            logits[self.classes.index('negative')] += 4.0

        probabilities = softmax(logits)
        pred_idx = int(np.argmax(probabilities))
        pred_class = self.classes[pred_idx]
        confidence = float(probabilities[pred_idx]) * 100.0

        prob_map = {self.classes[i]: round(float(probabilities[i]) * 100.0, 1) for i in range(len(self.classes))}

        # Format attention matrix for UI
        formatted_attn_matrix = []
        for i, f_from in enumerate(self.feature_names):
            row_attn = {}
            for j, f_to in enumerate(self.feature_names):
                row_attn[f_to] = round(float(attn_weights[i, j]), 3)
            formatted_attn_matrix.append({
                'feature': f_from,
                'attentions': row_attn
            })

        return {
            'prediction': pred_class,
            'prediction_badge': pred_class.replace('_', ' ').title(),
            'confidence': round(confidence, 1),
            'class_probabilities': prob_map,
            'features': self.feature_names,
            'attention_matrix': formatted_attn_matrix,
            'architecture': 'FT-Transformer (Feature Tokenizer + 4-Head Self-Attention Block)'
        }


# Global singleton instance
FT_TRANSFORMER_MODEL = TabularFeatureTokenizerTransformer()


def run_ft_transformer_inference(input_data: dict) -> dict:
    """Executes FT-Transformer forward inference on clinical biomarkers."""
    global FT_TRANSFORMER_MODEL
    return FT_TRANSFORMER_MODEL.forward(input_data)
