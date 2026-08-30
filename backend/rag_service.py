"""
ThyroScan — Context-Aware ThyroBot with Medical Knowledge Base & Safety Filter
Provides RAG-based answers with clinical citations, user context injection,
and immediate detection for emergency/acute symptoms.
"""

import re

# Curated medical reference knowledge base
THYROID_KNOWLEDGE_BASE = [
    {
        'id': 'tsh_guidelines',
        'title': 'TSH Clinical Interpretation',
        'source': 'American Thyroid Association (ATA) Guidelines',
        'keywords': ['tsh', 'thyroid stimulating hormone', 'reference range', 'high tsh', 'low tsh', 'normal'],
        'content': 'Thyroid Stimulating Hormone (TSH), produced by the pituitary gland, is the standard first-line biomarker for assessing thyroid function. A standard normal range is approximately 0.45 to 4.5 mIU/L. High TSH indicates that the pituitary is working harder to stimulate an underactive gland (hypothyroidism), while low or undetectable TSH indicates pituitary suppression due to hormone excess (hyperthyroidism).'
    },
    {
        'id': 'hypothyroidism_overview',
        'title': 'Hypothyroidism Signs & Clinical Management',
        'source': 'NHS Clinical Guidance on Underactive Thyroid',
        'keywords': ['hypothyroid', 'hypothyroidism', 'underactive', 'weight gain', 'fatigue', 'tired', 'levothyroxine', 'cold'],
        'content': 'Hypothyroidism occurs when the thyroid gland produces insufficient thyroxine (T4) and triiodothyronine (T3). Common clinical symptoms include progressive fatigue, unexplained weight gain, sensitivity to cold environments, constipation, dry skin, and muscle weakness. Standard primary medical therapy is daily oral Levothyroxine (synthetic T4), titrated based on 6-8 week TSH evaluations.'
    },
    {
        'id': 'hyperthyroidism_overview',
        'title': 'Hyperthyroidism Signs & Therapy',
        'source': 'American Association of Clinical Endocrinology (AACE)',
        'keywords': ['hyperthyroid', 'hyperthyroidism', 'overactive', 'palpitations', 'tremor', 'weight loss', 'sweating', 'heat'],
        'content': 'Hyperthyroidism is characterized by hormone overproduction accelerating basal metabolic rate. Manifestations include tachycardia, tremors, heat intolerance, diaphoresis, unprovoked weight loss, and anxiety. Clinical etiology frequently includes Graves\' disease or toxic multinodular goitre. Management options include antithyroid medications (Methimazole/Carbimazole), beta-blockers for symptom relief, radioiodine therapy, or surgery.'
    },
    {
        'id': 'subclinical_thyroid',
        'title': 'Subclinical Thyroid Dysfunction',
        'source': 'European Thyroid Association (ETA) Guidelines',
        'keywords': ['subclinical', 'borderline', 'mild', 'subclinical hypo', 'subclinical hyper'],
        'content': 'Subclinical hypothyroidism is defined as serum TSH above the upper reference limit with normal free T4 levels. Subclinical hyperthyroidism is serum TSH below reference range with normal circulating free hormones. Routine intervention depends on patient age, cardiovascular risk, symptom severity, and whether TSH persistently exceeds 10 mIU/L or is suppressed <0.1 mIU/L.'
    },
    {
        'id': 'diet_and_iodine',
        'title': 'Iodine, Selenium, and Thyroid Nutrition',
        'source': 'World Health Organization (WHO) Micronutrient Guidelines',
        'keywords': ['iodine', 'diet', 'food', 'nutrition', 'selenium', 'supplement', 'salt', 'kelp'],
        'content': 'Iodine is an essential building block for thyroid hormones. Recommended daily dietary intake is 150 mcg for adults (250 mcg during pregnancy/lactation). While mild iodine deficiency can cause goitre, excessive supplementation (such as high-dose kelp supplements) can trigger or worsen both autoimmune thyroiditis and hyperthyroidism (Jod-Basedow effect).'
    },
    {
        'id': 'medications_and_interactions',
        'title': 'Thyroid Medications & Absorption Best Practices',
        'source': 'British National Formulary (BNF) Guidance',
        'keywords': ['medication', 'levothyroxine', 'empty stomach', 'calcium', 'iron', 'coffee', 'absorption'],
        'content': 'Levothyroxine should be taken on an empty stomach with a full glass of plain water, ideally 30 to 60 minutes before breakfast or at bedtime 3–4 hours after the last meal. Supplements containing calcium, iron, or soy, as well as espresso coffee, can significantly impair intestinal absorption and should be spaced at least 4 hours apart.'
    }
]

# Emergency symptom detector patterns
EMERGENCY_PATTERNS = [
    r'\b(?:chest pain|crushing pain|heart attack|angina)\b',
    r'\b(?:fainting|passed out|blackout|syncope)\b',
    r'\b(?:cannot breathe|severe shortness of breath|gasping)\b',
    r'\b(?:heart racing extremely fast|rapid palpitations with dizziness|heart beat.*(?:160|180|200))\b',
    r'\b(?:thyroid storm|high fever with confusion|delirium.*tremor)\b'
]


def detect_emergency(user_query: str) -> bool:
    """Checks if the user's message contains acute emergency red flags."""
    query_lower = user_query.lower()
    for pattern in EMERGENCY_PATTERNS:
        if re.search(pattern, query_lower, re.IGNORECASE):
            return True
    return False


def query_rag_knowledge_base(query: str) -> tuple[str, list]:
    """
    Searches the medical knowledge base for passages matching user query.
    Returns matched synthesis content and structured citations list.
    """
    query_lower = query.lower()
    matched_entries = []

    for entry in THYROID_KNOWLEDGE_BASE:
        score = sum(1 for kw in entry['keywords'] if kw in query_lower)
        if score > 0:
            matched_entries.append((score, entry))

    matched_entries.sort(key=lambda x: x[0], reverse=True)

    if not matched_entries:
        # Fallback to general guidance
        top_entries = [THYROID_KNOWLEDGE_BASE[0], THYROID_KNOWLEDGE_BASE[1]]
    else:
        top_entries = [item[1] for item in matched_entries[:2]]

    passages = "\n\n".join([f"• {e['title']}: {e['content']}" for e in top_entries])
    citations = [{'source': e['source'], 'topic': e['title']} for e in top_entries]

    return passages, citations


def generate_bot_response(user_query: str, user_context: dict = None) -> dict:
    """
    Generates a context-aware, safety-filtered response for ThyroBot with clinical citations.
    """
    # 1. Emergency Safety Filter
    if detect_emergency(user_query):
        return {
            'is_emergency': True,
            'message': (
                "⚠️ **URGENT MEDICAL ADVISORY:** The symptoms you described (such as severe palpitations, chest pain, "
                "shortness of breath, fainting, or acute disorientation) require **immediate medical attention**. "
                "Please call your local emergency services (e.g. 911, 112, or 999) or visit the nearest emergency room immediately. "
                "Do not wait for online screening tools or advice."
            ),
            'citations': [{'source': 'Emergency Clinical Care Protocol', 'topic': 'Acute Triage Safety'}],
            'suggested_actions': ['Call Emergency Services Immediately', 'Seek Urgent In-Person Medical Attention']
        }

    # 2. Extract relevant medical passages and citations
    knowledge_passages, citations = query_rag_knowledge_base(user_query)

    # 3. Incorporate user assessment context if available
    context_prefix = ""
    if user_context and user_context.get('latest_assessment'):
        last_rec = user_context['latest_assessment']
        res = last_rec.get('screening_result', 'negative')
        tsh = last_rec.get('inputs', {}).get('TSH', 'Not recorded')
        t3 = last_rec.get('inputs', {}).get('T3', 'Not recorded')
        tt4 = last_rec.get('inputs', {}).get('TT4', 'Not recorded')
        context_prefix = (
            f"*Context from your latest screening:* Your latest record showed a **{res.replace('_', ' ').title()}** signal "
            f"(TSH: {tsh}, T3: {t3}, TT4: {tt4}).\n\n"
        )

    # 4. Generate structured answer
    q_lower = user_query.lower()
    custom_explanation = ""

    if 'why' in q_lower or 'higher' in q_lower or 'result' in q_lower or 'my risk' in q_lower:
        custom_explanation = (
            "Screening outcomes are determined by the statistical combination of your hormone levels (primarily TSH, T3, and Total T4) "
            "and reported symptoms. When TSH shifts outside standard baseline limits (0.45 – 4.5 mIU/L), the model flags higher probability for gland dysfunction.\n\n"
        )
    elif 'diet' in q_lower or 'food' in q_lower or 'eat' in q_lower:
        custom_explanation = (
            "Nutrition plays an important supporting role in endocrine balance. Adequate dietary iodine and selenium are essential, "
            "while excessive supplementation or crash diets can place temporary stress on hormone synthesis.\n\n"
        )
    elif 'medicine' in q_lower or 'levo' in q_lower or 'pill' in q_lower:
        custom_explanation = (
            "Consistency is key with thyroid medications. They are typically taken first thing in the morning with water, separated from breakfast and other supplements.\n\n"
        )
    else:
        custom_explanation = (
            "Here is the medical guidance regarding your question based on established clinical guidelines:\n\n"
        )

    full_message = f"{context_prefix}{custom_explanation}{knowledge_passages}\n\n*Note: This information is for educational screening support and is not a substitute for clinical diagnosis by your physician.*"

    return {
        'is_emergency': False,
        'message': full_message,
        'citations': citations,
        'suggested_actions': [
            'How should I prepare for my thyroid lab test?',
            'What is the difference between T3, T4, and TSH?',
            'What lifestyle habits support healthy thyroid function?'
        ]
    }
