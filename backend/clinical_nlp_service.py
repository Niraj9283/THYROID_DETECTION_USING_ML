"""
ThyroScan AI — Clinical Symptoms NLP & Free-Text Medical Narrative Service
Parses clinical notes, physician consultation transcripts, and patient complaints to extract
structured symptom clusters, calculate endocrine burden indices, and correlate with laboratory findings.
"""

import re


SYMPTOM_DICTIONARY = {
    'hypothyroid': [
        {'key': 'fatigue', 'terms': ['fatigue', 'tired', 'lethargy', 'exhaustion', 'sluggish', 'weakness', 'lack of energy']},
        {'key': 'cold_intolerance', 'terms': ['cold intolerance', 'sensitive to cold', 'feeling cold', 'chilly', 'cold extremities']},
        {'key': 'weight_gain', 'terms': ['weight gain', 'unexplained weight gain', 'gaining weight', 'unable to lose weight']},
        {'key': 'constipation', 'terms': ['constipation', 'sluggish bowels', 'hard stool']},
        {'key': 'dry_skin_hair', 'terms': ['dry skin', 'hair loss', 'brittle hair', 'brittle nails', 'hair thinning', 'coarse hair']},
        {'key': 'brain_fog_mood', 'terms': ['brain fog', 'memory loss', 'forgetfulness', 'depression', 'low mood', 'poor concentration']},
        {'key': 'puffy_face_edema', 'terms': ['facial puffiness', 'puffy face', 'periorbital edema', 'swollen ankles', 'myxedema']},
        {'key': 'muscle_aches', 'terms': ['muscle cramps', 'joint pain', 'arthralgia', 'myalgia', 'muscle aches']},
        {'key': 'bradycardia', 'terms': ['slow heart rate', 'bradycardia', 'slow pulse']}
    ],
    'hyperthyroid': [
        {'key': 'palpitations_tachycardia', 'terms': ['palpitations', 'racing heart', 'tachycardia', 'rapid pulse', 'heart pounding', 'irregular heartbeat']},
        {'key': 'heat_intolerance', 'terms': ['heat intolerance', 'sensitive to heat', 'excessive sweating', 'diaphoresis', 'hot flashes']},
        {'key': 'weight_loss', 'terms': ['weight loss', 'unexplained weight loss', 'losing weight', 'increased appetite with weight loss']},
        {'key': 'tremors_jittery', 'terms': ['tremor', 'hand tremor', 'shakiness', 'jittery', 'shaky hands']},
        {'key': 'anxiety_insomnia', 'terms': ['anxiety', 'nervousness', 'insomnia', 'restlessness', 'irritability', 'sleep disturbance']},
        {'key': 'frequent_bowels', 'terms': ['frequent bowel movements', 'diarrhea', 'loose stools', 'hyperdefecation']},
        {'key': 'eye_symptoms', 'terms': ['eye bulging', 'exophthalmos', 'proptosis', 'double vision', 'eye pain', 'grittiness in eyes']}
    ],
    'compressive_nodule': [
        {'key': 'neck_swelling', 'terms': ['neck swelling', 'thyroid enlargement', 'goiter', 'neck lump', 'nodule', 'thyroid mass']},
        {'key': 'dysphagia', 'terms': ['difficulty swallowing', 'dysphagia', 'food getting stuck', 'choking']},
        {'key': 'hoarseness', 'terms': ['hoarseness', 'voice change', 'dysphonia', 'raspy voice']},
        {'key': 'globus_sensation', 'terms': ['tightness in neck', 'lump in throat', 'globus sensation', 'neck pressure']},
        {'key': 'neck_pain', 'terms': ['neck pain', 'anterior neck tenderness', 'pain radiating to ear']}
    ]
}


def parse_clinical_notes_nlp(clinical_text: str) -> dict:
    """
    Extracts structured thyroid symptoms, calculates category symptom burdens,
    and returns highlighted text with clinical diagnostic correlation.
    """
    if not clinical_text or len(clinical_text.strip()) < 5:
        return {
            'status': 'empty_text',
            'message': 'Please provide clinical notes or patient complaints to extract structured thyroid symptoms.'
        }

    text_lower = clinical_text.lower()
    matched_symptoms = []
    category_counts = {'hypothyroid': 0, 'hyperthyroid': 0, 'compressive_nodule': 0}

    # Match symptoms across dictionaries
    for category, symptom_list in SYMPTOM_DICTIONARY.items():
        for item in symptom_list:
            matched_terms = []
            for term in item['terms']:
                # Exact or word boundary match
                pattern = r'\b' + re.escape(term) + r'\b'
                if re.search(pattern, text_lower):
                    matched_terms.append(term)

            if matched_terms:
                category_counts[category] += 1
                matched_symptoms.append({
                    'symptom_key': item['key'],
                    'display_name': item['key'].replace('_', ' ').title(),
                    'category': category,
                    'category_label': 'Hypothyroid Spectrum' if category == 'hypothyroid' else ('Hyperthyroid Spectrum' if category == 'hyperthyroid' else 'Compressive / Nodule Signs'),
                    'matched_term': matched_terms[0]
                })

    total_hypo_possible = len(SYMPTOM_DICTIONARY['hypothyroid'])
    total_hyper_possible = len(SYMPTOM_DICTIONARY['hyperthyroid'])
    total_comp_possible = len(SYMPTOM_DICTIONARY['compressive_nodule'])

    hypo_burden_pct = round((category_counts['hypothyroid'] / total_hypo_possible) * 100, 1)
    hyper_burden_pct = round((category_counts['hyperthyroid'] / total_hyper_possible) * 100, 1)
    comp_burden_pct = round((category_counts['compressive_nodule'] / total_comp_possible) * 100, 1)

    # Dominant Clinical Phenotype
    if hypo_burden_pct > hyper_burden_pct and hypo_burden_pct >= 20.0:
        dominant_phenotype = "Hypothyroid Symptom Dominance"
        phenotype_badge = "badge-info"
        clinical_interpretation = (
            f"Clinical narrative exhibits strong hypothyroid symptom presentation ({category_counts['hypothyroid']} positive indicators). "
            "Correlate with serum TSH, Free T4, and Anti-TPO titers to confirm Primary or Subclinical Hypothyroidism."
        )
    elif hyper_burden_pct > hypo_burden_pct and hyper_burden_pct >= 20.0:
        dominant_phenotype = "Hyperthyroid / Thyrotoxic Symptom Dominance"
        phenotype_badge = "badge-warning"
        clinical_interpretation = (
            f"Clinical narrative demonstrates hyperadrenergic / thyrotoxic symptom profile ({category_counts['hyperthyroid']} positive indicators). "
            "Evaluate TSH, Free T3, Free T4, and TSH receptor antibodies (TRAb) for Graves' disease or toxic adenoma."
        )
    elif comp_burden_pct >= 30.0:
        dominant_phenotype = "Local Compressive / Structural Goiter Phenotype"
        phenotype_badge = "badge-danger"
        clinical_interpretation = (
            f"Prominent local anatomical compressive symptoms noted ({category_counts['compressive_nodule']} structural signs). "
            "Urgent high-resolution thyroid ultrasound and surgical airway/esophageal evaluation recommended."
        )
    elif len(matched_symptoms) == 0:
        dominant_phenotype = "Non-Specific / Asymptomatic Narrative"
        phenotype_badge = "badge-secondary"
        clinical_interpretation = "No classical thyroid symptomatology detected in narrative. Patient may be asymptomatic or presenting with non-specific complaints."
    else:
        dominant_phenotype = "Mixed / Non-Differentiated Endocrine Features"
        phenotype_badge = "badge-warning"
        clinical_interpretation = "Overlapping hypothyroid and hyperthyroid clinical features identified. Biochemical laboratory confirmation required."

    return {
        'status': 'success',
        'matched_symptoms_count': len(matched_symptoms),
        'dominant_phenotype': dominant_phenotype,
        'phenotype_badge': phenotype_badge,
        'clinical_interpretation': clinical_interpretation,
        'burden_scores': {
            'hypothyroid_pct': hypo_burden_pct,
            'hyperthyroid_pct': hyper_burden_pct,
            'compressive_nodule_pct': comp_burden_pct
        },
        'symptoms_list': matched_symptoms
    }
