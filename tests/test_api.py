"""
ThyroScan AI — Automated Test Suite
Tests API authentication, screening validation, probability calculation,
OCR parsing, report generation, ThyroBot RAG, and safety filtering.
"""

import unittest
import json
import os
import sys

# Add project root to sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.join(BASE_DIR, '..')
sys.path.insert(0, PROJECT_DIR)

from backend.app import app
from backend.database import get_db, init_db
from backend.predict_service import execute_screening, analyze_biomarkers
from backend.ocr_service import parse_lab_parameters_from_text
from backend.rag_service import detect_emergency, generate_bot_response


class ThyroScanTestSuite(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        init_db()

    def test_health_check(self):
        res = self.app.get('/api/health')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['status'], 'ok')
        self.assertTrue(data['model_loaded'])

    def test_model_info_transparency(self):
        res = self.app.get('/api/model-info')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('comparison', data)
        self.assertIn('intended_use', data)
        self.assertIn('metrics_transparency', data)

    def test_auth_registration_and_login(self):
        email = f"test_{os.urandom(4).hex()}@example.com"
        # Register
        reg_res = self.app.post('/api/auth/register', json={
            'name': 'Dr Test User',
            'email': email,
            'password': 'password123',
            'age': 32,
            'sex': 0
        })
        self.assertEqual(reg_res.status_code, 201)
        reg_data = reg_res.get_json()
        self.assertIn('token', reg_data)

        # Login
        login_res = self.app.post('/api/auth/login', json={
            'email': email,
            'password': 'password123'
        })
        self.assertEqual(login_res.status_code, 200)
        login_data = login_res.get_json()
        self.assertIn('token', login_data)

        # Auth Me
        me_res = self.app.get('/api/auth/me', headers={'Authorization': f"Bearer {login_data['token']}"})
        self.assertEqual(me_res.status_code, 200)
        me_data = me_res.get_json()
        self.assertEqual(me_data['user']['email'], email)

    def test_screening_execution_normal_case(self):
        input_data = {
            'age': 35,
            'sex': 1,
            'TSH': 1.8,
            'T3': 2.1,
            'TT4': 105,
            'T4U': 1.05,
            'FTI': 100,
            'on_thyroxine': 0,
            'thyroid_surgery': 0
        }
        res = execute_screening(input_data)
        self.assertIn('screening_result', res)
        self.assertIn('model_probability', res)
        self.assertIn('biomarker_analysis', res)
        self.assertIn('feature_influences', res)
        self.assertIn('action_plan', res)
        self.assertIn('disclaimer', res)

    def test_biomarker_reference_range_analysis(self):
        data = {'TSH': 14.5, 'T3': 0.6, 'TT4': 3.2}
        evals = analyze_biomarkers(data)
        tsh_eval = next((e for e in evals if e['code'] == 'TSH'), None)
        self.assertIsNotNone(tsh_eval)
        self.assertEqual(tsh_eval['status'], 'critical_high')

    def test_ocr_parameter_extraction(self):
        sample_lab_text = """
        METROPOLIS CLINICAL LABS
        Patient: Jane Doe | Age: 42 Yrs | Sex: Female
        THYROID PROFILE ULTRASENSITIVE
        TSH (Thyroid Stimulating Hormone): 5.82 uIU/mL (Ref: 0.45 - 4.50)
        Total T3: 1.10 ng/mL (Ref: 0.80 - 2.00)
        Total Thyroxine (TT4): 74.0 nmol/L
        """
        parsed = parse_lab_parameters_from_text(sample_lab_text)
        self.assertEqual(parsed['extracted']['TSH'], 5.82)
        self.assertEqual(parsed['extracted']['T3'], 1.1)
        self.assertEqual(parsed['extracted']['age'], 42)
        self.assertEqual(parsed['extracted']['sex'], 0)

    def test_thyrobot_emergency_safety_detector(self):
        emergency_query = "I am having severe crushing chest pain and heart racing at 180 bpm"
        self.assertTrue(detect_emergency(emergency_query))
        res = generate_bot_response(emergency_query)
        self.assertTrue(res['is_emergency'])
        self.assertIn('URGENT MEDICAL ADVISORY', res['message'])

    def test_thyrobot_rag_and_citations(self):
        normal_query = "What is the normal reference range for TSH according to guidelines?"
        self.assertFalse(detect_emergency(normal_query))
        res = generate_bot_response(normal_query)
        self.assertFalse(res['is_emergency'])
        self.assertTrue(len(res['citations']) > 0)
        self.assertIn('American Thyroid Association', str(res['citations']))


if __name__ == '__main__':
    unittest.main()
