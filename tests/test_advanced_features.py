"""
ThyroScan — Flagship Advanced Features Test Suite
Tests Multi-Model Ensemble, Lab Report Comparison, Conversational Extraction,
Safety Gateway, and Doctor Mode SOAP Notes.
"""

import unittest
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.join(BASE_DIR, '..')
sys.path.insert(0, PROJECT_DIR)

from backend.app import app
from backend.ensemble_service import run_ensemble_prediction
from backend.copilot_service import compare_lab_reports
from backend.safety_gateway import evaluate_safety_gate
from backend.conversational_screening import extract_entities_from_utterance
from backend.doctor_service import generate_clinical_soap_note


class AdvancedFeaturesTestSuite(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_multi_model_ensemble_prediction(self):
        sample = {
            'age': 55, 'sex': 0, 'TSH': 24.0, 'T3': 0.6, 'TT4': 38.0,
            'T4U': 1.1, 'FTI': 35.0, 'query_hypothyroid': 1
        }
        res = run_ensemble_prediction(sample)
        self.assertIn('ensemble_prediction', res)
        self.assertIn('calibrated_probability', res)
        self.assertIn('consensus_score', res)
        self.assertIn('individual_models', res)
        self.assertIn('Gradient Boosting', res['individual_models'])
        self.assertIn('Random Forest', res['individual_models'])
        self.assertIn('SVM (RBF Kernel)', res['individual_models'])

    def test_lab_report_comparator_deltas(self):
        report_a = {'date': '2026-01-15', 'TSH': 3.2, 'T3': 1.2, 'TT4': 95.0, 'weight_kg': 68.0}
        report_b = {'date': '2026-06-20', 'TSH': 6.4, 'T3': 0.9, 'TT4': 72.0, 'weight_kg': 71.0}
        res = compare_lab_reports(report_a, report_b)
        self.assertIn('comparisons', res)
        tsh_comp = next((c for c in res['comparisons'] if c['param'] == 'TSH'), None)
        self.assertIsNotNone(tsh_comp)
        self.assertEqual(tsh_comp['pct_change'], 100.0)
        self.assertEqual(tsh_comp['direction'], 'increased')
        self.assertIn('trajectory', res)
        self.assertIn('suggested_doctor_questions', res)

    def test_conversational_entity_extractor(self):
        utterance = "I am a 48 year old female. My TSH is 7.4 and total T3 is 0.85, and I am taking Levothyroxine."
        res = extract_entities_from_utterance(utterance)
        state = res['state']
        self.assertEqual(state.get('age'), 48)
        self.assertEqual(state.get('sex'), 0)
        self.assertEqual(state.get('TSH'), 7.4)
        self.assertEqual(state.get('T3'), 0.85)
        self.assertEqual(state.get('on_thyroxine'), 1)
        self.assertTrue(res['is_ready_for_screening'])

    def test_safety_gateway_medication_query(self):
        query = "Should I double my Levothyroxine dosage from 50mcg to 100mcg?"
        gate_res = evaluate_safety_gate(query)
        self.assertEqual(gate_res['status'], 'intercepted')
        self.assertEqual(gate_res['category'], 'medication_alteration')
        self.assertIn('MEDICATION SAFETY ADVISORY', gate_res['message'])

    def test_safety_gateway_emergency_query(self):
        query = "My chest is hurting badly and I passed out"
        gate_res = evaluate_safety_gate(query)
        self.assertEqual(gate_res['status'], 'intercepted')
        self.assertTrue(gate_res['is_emergency'])

    def test_doctor_mode_soap_note_generation(self):
        assessment = {
            'screening_result': 'hypothyroid',
            'badge': 'Elevated Risk (Hypothyroidism)',
            'model_probability': 94.5,
            'ensemble_consensus': '3/3 Models Agree',
            'inputs': {'age': 45, 'sex': 0, 'TSH': 14.2, 'T3': 0.7, 'TT4': 45, 'query_hypothyroid': 1}
        }
        patient = {'name': 'Jane Doe', 'age': 45, 'sex': 0, 'bmi': 26.4}
        soap = generate_clinical_soap_note(assessment, patient)
        self.assertIn('ehr_soap_text', soap)
        self.assertIn('[S] SUBJECTIVE', soap['ehr_soap_text'])
        self.assertIn('[O] OBJECTIVE', soap['ehr_soap_text'])
        self.assertIn('[A] CLINICAL AI ASSESSMENT', soap['ehr_soap_text'])
        self.assertIn('[P] RECOMMENDATIONS & PLAN', soap['ehr_soap_text'])


if __name__ == '__main__':
    unittest.main()
