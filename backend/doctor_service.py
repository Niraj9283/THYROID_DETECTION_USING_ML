"""
ThyroScan — Doctor Mode & Clinical SOAP Summary Generator
Generates clinical summaries and copyable SOAP notes for medical records.
"""

from datetime import datetime


def generate_clinical_soap_note(assessment_data: dict, patient_profile: dict = None) -> dict:
    """
    Generates structured SOAP (Subjective, Objective, Assessment, Plan) note
    and copyable EHR clinical text for physicians.
    """
    pat = patient_profile or {}
    inputs = assessment_data.get('inputs', {})
    res_label = assessment_data.get('badge', assessment_data.get('screening_result', 'Negative')).upper()
    prob = assessment_data.get('model_probability', 0)
    ensemble = assessment_data.get('ensemble_consensus', '3/3 Models Agree')

    age = pat.get('age') or inputs.get('age', 'Unspecified')
    sex = 'Female' if str(pat.get('sex') or inputs.get('sex')) == '0' else 'Male'
    bmi = pat.get('bmi') or inputs.get('bmi', 'N/A')

    # 1. Subjective (Symptoms & Meds)
    subjective_items = []
    if inputs.get('query_hypothyroid'):
        subjective_items.append("Fatigue, cold sensitivity, suspected hypothyroid symptoms")
    if inputs.get('query_hyperthyroid'):
        subjective_items.append("Palpitations, heat intolerance, suspected hyperthyroid symptoms")
    if inputs.get('on_thyroxine'):
        subjective_items.append("Active Levothyroxine therapy")
    if inputs.get('thyroid_surgery'):
        subjective_items.append("Prior thyroid surgery / partial resection")
    if inputs.get('goitre'):
        subjective_items.append("Noted neck swelling / goitre")
    if not subjective_items:
        subjective_items.append("Routine thyroid screening; no acute symptoms reported.")

    # 2. Objective (Biomarkers)
    tsh = inputs.get('TSH', 'Not tested')
    t3 = inputs.get('T3', 'Not tested')
    tt4 = inputs.get('TT4', 'Not tested')
    t4u = inputs.get('T4U', 'Not tested')
    fti = inputs.get('FTI', 'Not tested')

    # 3. Assessment
    assessment_text = f"AI Risk Stratification Signal: {res_label} (Model Probability: {prob}%, Ensemble Consensus: {ensemble})."

    # 4. Plan
    plan_items = assessment_data.get('action_plan', [
        "Recommend complete thyroid panel (TSH, Free T4, Total T3)",
        "Assess thyroid antibodies (Anti-TPO / TRAb) if clinically indicated",
        "Follow up evaluation in 6-12 weeks"
    ])

    soap_text = f"""CLINICAL SCREENING CONSULT NOTE
Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}
Patient: {pat.get('name', 'Anonymous')} | Age: {age} | Sex: {sex} | BMI: {bmi}
------------------------------------------------------------------------
[S] SUBJECTIVE:
- Clinical History & Flags: {', '.join(subjective_items)}

[O] OBJECTIVE LAB BIOMARKERS:
- TSH: {tsh} mIU/L (Ref: 0.45 - 4.5)
- Total T3: {t3} ng/mL (Ref: 0.8 - 2.0)
- Total T4: {tt4} ug/dL (Ref: 4.5 - 12.0)
- T4U: {t4u} | FTI: {fti}

[A] CLINICAL AI ASSESSMENT:
- {assessment_text}
- Model Limitations: Statistical ML estimation; does not constitute definitive laboratory diagnosis.

[P] RECOMMENDATIONS & PLAN:
{chr(10).join([f"- {p}" for p in plan_items])}
------------------------------------------------------------------------
Note: Generated via ThyroScan AI Clinical Assistant for clinician decision support.
"""

    return {
        'subjective': subjective_items,
        'objective': {
            'TSH': tsh,
            'T3': t3,
            'TT4': tt4,
            'T4U': t4u,
            'FTI': fti,
            'BMI': bmi
        },
        'assessment': assessment_text,
        'plan': plan_items,
        'ehr_soap_text': soap_text
    }
