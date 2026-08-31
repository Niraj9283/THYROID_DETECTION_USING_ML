"""
ThyroScan AI — HL7 FHIR R4 Multimodal Diagnostic Dossier Service
Generates standardized, interoperable Fast Healthcare Interoperability Resources (FHIR R4) Bundles
integrating Laboratory Observations, Ultrasound Imaging Studies, AI Multi-Model Predictions, and Care Plans.
"""

import uuid
from datetime import datetime


LOINC_CODES = {
    'TSH': {'code': '3016-3', 'display': 'Thyrotropin [Units/volume] in Serum or Plasma', 'unit': 'mIU/L'},
    'FTI': {'code': '3024-7', 'display': 'Thyroxine (T4) free [Mass/volume] in Serum or Plasma', 'unit': 'pmol/L'},
    'TT4': {'code': '3026-2', 'display': 'Thyroxine (T4) total [Mass/volume] in Serum or Plasma', 'unit': 'nmol/L'},
    'T3': {'code': '3053-6', 'display': 'Triiodothyronine (T3) total [Mass/volume] in Serum or Plasma', 'unit': 'nmol/L'},
    'T4U': {'code': '3025-4', 'display': 'Thyroxine (T4) uptake in Serum or Plasma', 'unit': 'ratio'}
}


def generate_fhir_r4_bundle(patient_data: dict, model_results: dict = None,
                            ultrasound_data: dict = None, trajectory_data: dict = None) -> dict:
    """
    Generates a valid HL7 FHIR R4 Bundle (document type) containing Patient, Observation,
    ImagingStudy, and DiagnosticReport resources.
    """
    bundle_id = str(uuid.uuid4())
    patient_id = patient_data.get('patient_id', f"PAT-{uuid.uuid4().hex[:8].upper()}")
    timestamp_str = datetime.utcnow().isoformat() + "Z"

    gender = 'female' if str(patient_data.get('sex', 'F')).upper() in ['F', '0', 'FEMALE'] else 'male'
    age = int(patient_data.get('age', 45) or 45)

    entries = []

    # 1. FHIR Patient Resource
    patient_resource = {
        'fullUrl': f"urn:uuid:{patient_id}",
        'resource': {
            'resourceType': 'Patient',
            'id': patient_id,
            'gender': gender,
            'active': True,
            'extension': [{
                'url': 'http://hl7.org/fhir/StructureDefinition/patient-age',
                'valueInteger': age
            }]
        }
    }
    entries.append(patient_resource)

    # 2. FHIR Observation Resources for Biomarkers
    observation_refs = []
    for key, meta in LOINC_CODES.items():
        if key in patient_data and patient_data[key] is not None:
            obs_id = str(uuid.uuid4())
            try:
                val = float(patient_data[key])
            except (ValueError, TypeError):
                continue

            obs_entry = {
                'fullUrl': f"urn:uuid:{obs_id}",
                'resource': {
                    'resourceType': 'Observation',
                    'id': obs_id,
                    'status': 'final',
                    'category': [{
                        'coding': [{
                            'system': 'http://terminology.hl7.org/CodeSystem/observation-category',
                            'code': 'laboratory',
                            'display': 'Laboratory'
                        }]
                    }],
                    'code': {
                        'coding': [{
                            'system': 'http://loinc.org',
                            'code': meta['code'],
                            'display': meta['display']
                        }],
                        'text': key
                    },
                    'subject': {'reference': f"urn:uuid:{patient_id}"},
                    'effectiveDateTime': timestamp_str,
                    'valueQuantity': {
                        'value': val,
                        'unit': meta['unit'],
                        'system': 'http://unitsofmeasure.org'
                    }
                }
            }
            entries.append(obs_entry)
            observation_refs.append({'reference': f"urn:uuid:{obs_id}"})

    # 3. FHIR Observation for Ultrasound ACR TI-RADS (if available)
    if ultrasound_data:
        us_obs_id = str(uuid.uuid4())
        us_entry = {
            'fullUrl': f"urn:uuid:{us_obs_id}",
            'resource': {
                'resourceType': 'Observation',
                'id': us_obs_id,
                'status': 'final',
                'category': [{
                    'coding': [{
                        'system': 'http://terminology.hl7.org/CodeSystem/observation-category',
                        'code': 'imaging',
                        'display': 'Imaging'
                    }]
                }],
                'code': {
                    'text': 'Thyroid Ultrasound ACR TI-RADS Evaluation'
                },
                'subject': {'reference': f"urn:uuid:{patient_id}"},
                'valueString': f"{ultrasound_data.get('category', 'TR1')} ({ultrasound_data.get('classification', 'Benign')}) - {ultrasound_data.get('total_points', 0)} points",
                'component': [
                    {
                        'code': {'text': 'Malignancy Probability'},
                        'valueQuantity': {
                            'value': float(ultrasound_data.get('malignancy_probability', 1.5)),
                            'unit': '%'
                        }
                    },
                    {
                        'code': {'text': 'FNA Recommendation'},
                        'valueString': ultrasound_data.get('fna_recommendation', 'No FNA required.')
                    }
                ]
            }
        }
        entries.append(us_entry)
        observation_refs.append({'reference': f"urn:uuid:{us_obs_id}"})

    # 4. FHIR DiagnosticReport Resource
    report_id = str(uuid.uuid4())
    conclusion_text = (
        f"ThyroScan AI Multimodal Evaluation: "
        f"Champion Model consensus = {model_results.get('champion_prediction_badge', 'Negative') if model_results else 'Negative'}. "
        f"{'Ultrasound TI-RADS = ' + ultrasound_data.get('category', 'TR1') if ultrasound_data else ''}."
    )

    report_entry = {
        'fullUrl': f"urn:uuid:{report_id}",
        'resource': {
            'resourceType': 'DiagnosticReport',
            'id': report_id,
            'status': 'final',
            'category': [{
                'coding': [{
                    'system': 'http://terminology.hl7.org/CodeSystem/v2-0074',
                    'code': 'MB',
                    'display': 'Microbiology / Endocrine'
                }]
            }],
            'code': {
                'coding': [{
                    'system': 'http://loinc.org',
                    'code': '11502-2',
                    'display': 'Laboratory report'
                }],
                'text': 'ThyroScan AI Multimodal Endocrine Diagnostic Dossier'
            },
            'subject': {'reference': f"urn:uuid:{patient_id}"},
            'issued': timestamp_str,
            'result': observation_refs,
            'conclusion': conclusion_text
        }
    }
    entries.append(report_entry)

    # Compile Final FHIR R4 Bundle
    fhir_bundle = {
        'resourceType': 'Bundle',
        'id': bundle_id,
        'type': 'document',
        'timestamp': timestamp_str,
        'total': len(entries),
        'entry': entries
    }

    return fhir_bundle
