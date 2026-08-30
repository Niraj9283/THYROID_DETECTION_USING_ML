"""
ThyroScan — AI Clinical Safety Gateway
Intercepts and triages medication alterations, dosage questions,
dangerous self-treatment, and acute symptoms before generative response.
"""

import re

SAFETY_PATTERNS = {
    'medication_change': [
        r'\b(?:should i|can i)?\s*(?:stop|double|increase|decrease|change|skip|adjust|modify|raise|lower)\s*(?:my\s*)?(?:levo|levothyroxine|synthroid|thyroxine|antithyroid|medication|medicine|pill|dose|dosage)?\s*(?:dose|dosage|medication|pill)?',
        r'\b(?:from\s*[0-9]+\s*(?:mcg|mg)\s*to\s*[0-9]+\s*(?:mcg|mg))\b',
        r'\b(?:can i stop taking (?:levo|thyroxine|medication))\b',
        r'\b(?:how many (?:mg|mcg|tablets|pills) should i take)\b'
    ],
    'dangerous_self_treatment': [
        r'\b(?:cure (?:my )?thyroid with (?:kelp|iodine|salt|herbs|fasting|crystals))\b',
        r'\b(?:natural cure for hypothyroid without doctor)\b'
    ],
    'acute_emergency': [
        r'\b(?:chest pain|chest is hurting|fainting|passed out|blackout|cannot breathe|severe palpitations.*(?:180|190|200))\b'
    ]
}


def evaluate_safety_gate(user_message: str) -> dict:
    """
    Evaluates message against clinical safety rules.
    Returns status 'safe' or 'intercepted' with safety guidance.
    """
    msg_lower = user_message.lower()

    # 1. Acute Emergency Check
    for reg in SAFETY_PATTERNS['acute_emergency']:
        if re.search(reg, msg_lower, re.IGNORECASE):
            return {
                'status': 'intercepted',
                'category': 'acute_emergency',
                'is_emergency': True,
                'message': (
                    "🚨 **URGENT MEDICAL SAFETY ALERT:** The symptoms you mentioned (such as severe chest pain, "
                    "fainting, or extreme palpitations) require **immediate emergency medical evaluation**. "
                    "Please call local emergency services (e.g., 911, 112, or 999) or visit the nearest emergency department right away."
                ),
                'citations': [{'source': 'Clinical Triage Protocol', 'topic': 'Emergency Care'}],
                'suggested_actions': ['Contact Emergency Services', 'Seek Immediate In-Person Care']
            }

    # 2. Medication Alteration Check
    for reg in SAFETY_PATTERNS['medication_change']:
        if re.search(reg, msg_lower, re.IGNORECASE):
            return {
                'status': 'intercepted',
                'category': 'medication_alteration',
                'is_emergency': False,
                'message': (
                    "🛡️ **MEDICATION SAFETY ADVISORY:** Thyroid hormone medications (such as Levothyroxine, Synthroid, or Carbimazole) "
                    "require precise therapeutic titration based on blood tests (TSH/Free T4). "
                    "**Never alter your dosage, start, or discontinue thyroid medication without direct instructions from your prescribing physician.** "
                    "Improper dosage changes can induce cardiac arrhythmias, osteoporosis, or severe metabolic imbalances."
                ),
                'citations': [{'source': 'American Association of Clinical Endocrinology', 'topic': 'Hormone Replacement Protocols'}],
                'suggested_actions': ['Consult Your Prescribing Doctor', 'Request a Routine TSH Follow-up Test']
            }

    # 3. Dangerous Self-Treatment Check
    for reg in SAFETY_PATTERNS['dangerous_self_treatment']:
        if re.search(reg, msg_lower, re.IGNORECASE):
            return {
                'status': 'intercepted',
                'category': 'self_treatment',
                'is_emergency': False,
                'message': (
                    "🛡️ **CLINICAL NUTRITION ADVISORY:** While adequate dietary iodine is essential, unmonitored high-dose iodine "
                    "(e.g. concentrated kelp or seaweed extracts) can paradoxically worsen autoimmune thyroid disease (Hashimoto's) "
                    "or trigger severe hyperthyroidism. Always discuss dietary supplements with your endocrinologist."
                ),
                'citations': [{'source': 'World Health Organization (WHO)', 'topic': 'Iodine and Thyroid Nutrition'}],
                'suggested_actions': ['Review Diet with a Registered Dietitian', 'Discuss Supplements with Physician']
            }

    return {'status': 'safe'}
