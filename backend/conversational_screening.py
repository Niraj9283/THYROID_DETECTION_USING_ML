"""
ThyroScan — Conversational Assessment & Entity Extraction Engine
Transforms natural language speech and chat responses into structured clinical screening payloads.
"""

import re


def extract_entities_from_utterance(text: str, current_state: dict = None) -> dict:
    """
    Extracts clinical parameters from user conversational speech/text.
    Updates the accumulated patient screening state.
    """
    state = dict(current_state or {})
    text_lower = text.lower()

    # 1. Age extraction
    age_match = re.search(r'\b(?:i am|i\'m|age|age is)?\s*([0-9]{1,3})\s*(?:years|yrs|year old|yo)?\b', text_lower)
    if age_match:
        try:
            val = int(age_match.group(1))
            if 1 <= val <= 120:
                state['age'] = val
        except ValueError:
            pass

    # 2. Sex extraction
    if re.search(r'\b(?:female|woman|girl)\b', text_lower):
        state['sex'] = 0
    elif re.search(r'\b(?:male|man|boy)\b', text_lower):
        state['sex'] = 1

    # 3. Biomarkers extraction
    # TSH
    tsh_match = re.search(r'\b(?:tsh|thyroid stimulating hormone)\s*(?:is|of|level|value)?\s*([0-9]+\.?[0-9]*)\b', text_lower)
    if tsh_match:
        try:
            state['TSH'] = float(tsh_match.group(1))
            state['TSH_measured'] = 1
        except ValueError:
            pass

    # T3
    t3_match = re.search(r'\b(?:t3|total t3)\s*(?:is|of|level|value)?\s*([0-9]+\.?[0-9]*)\b', text_lower)
    if t3_match:
        try:
            state['T3'] = float(t3_match.group(1))
            state['T3_measured'] = 1
        except ValueError:
            pass

    # Total T4 / TT4
    t4_match = re.search(r'\b(?:t4|total t4|tt4|thyroxine)\s*(?:is|of|level|value)?\s*([0-9]+\.?[0-9]*)\b', text_lower)
    if t4_match:
        try:
            state['TT4'] = float(t4_match.group(1))
            state['TT4_measured'] = 1
        except ValueError:
            pass

    # 4. Clinical Flags & Symptoms
    if re.search(r'\b(?:taking levo|levothyroxine|synthroid|on thyroxine|thyroid medicine)\b', text_lower):
        state['on_thyroxine'] = 1
    if re.search(r'\b(?:thyroid surgery|removed my thyroid|thyroidectomy)\b', text_lower):
        state['thyroid_surgery'] = 1
    if re.search(r'\b(?:goitre|goiter|swollen neck|enlarged gland)\b', text_lower):
        state['goitre'] = 1
    if re.search(r'\b(?:tired|fatigue|weight gain|feeling cold|constipation)\b', text_lower):
        state['query_hypothyroid'] = 1
    if re.search(r'\b(?:palpitations|weight loss|sweating|tremor|heat intolerance|anxious)\b', text_lower):
        state['query_hyperthyroid'] = 1
    if re.search(r'\b(?:pregnant|expecting)\b', text_lower):
        state['pregnant'] = 1

    # 5. Determine next conversational prompt
    missing_fields = []
    if 'age' not in state:
        missing_fields.append('age')
    if 'sex' not in state:
        missing_fields.append('biological sex')
    if 'TSH' not in state:
        missing_fields.append('TSH lab value')

    next_prompt = ""
    is_complete = len(missing_fields) == 0

    if is_complete:
        next_prompt = "Great! I have recorded your age, sex, and TSH lab value. Click 'Run Analysis' or tell me about any symptoms or medications."
    else:
        next_prompt = f"Got it. Could you also provide your {missing_fields[0]}?"

    return {
        'state': state,
        'extracted_fields': list(state.keys()),
        'is_ready_for_screening': is_complete,
        'assistant_reply': next_prompt
    }
