"""
ThyroScan — AI Health Copilot & Longitudinal Lab Report Comparator
Compares multiple diagnostic reports (Report A vs Report B), calculates biomarker deltas,
and generates clinical questions for physician appointments.
"""


def compare_lab_reports(report_a: dict, report_b: dict) -> dict:
    """
    Compares Baseline Lab Report (A) with Follow-up Lab Report (B).
    Calculates absolute and percentage shifts, trends, and clinical summary.
    """
    parameters = ['TSH', 'T3', 'TT4', 'T4U', 'FTI', 'weight_kg', 'bmi']
    comparisons = []
    significant_changes = []

    units = {
        'TSH': 'mIU/L',
        'T3': 'ng/mL',
        'TT4': 'ug/dL',
        'T4U': 'ratio',
        'FTI': 'index',
        'weight_kg': 'kg',
        'bmi': 'kg/m²'
    }

    labels = {
        'TSH': 'Thyroid Stimulating Hormone (TSH)',
        'T3': 'Total Triiodothyronine (T3)',
        'TT4': 'Total Thyroxine (TT4)',
        'T4U': 'T4 Uptake (T4U)',
        'FTI': 'Free Thyroxine Index (FTI)',
        'weight_kg': 'Body Weight',
        'bmi': 'Body Mass Index (BMI)'
    }

    for param in parameters:
        val_a = report_a.get(param)
        val_b = report_b.get(param)

        if val_a is not None and val_b is not None:
            try:
                num_a = float(val_a)
                num_b = float(val_b)
                diff = round(num_b - num_a, 2)
                pct_change = round(((num_b - num_a) / num_a) * 100, 1) if num_a != 0 else 0

                direction = 'stable'
                if pct_change > 10:
                    direction = 'increased'
                elif pct_change < -10:
                    direction = 'decreased'

                comp_entry = {
                    'param': param,
                    'name': labels.get(param, param),
                    'unit': units.get(param, ''),
                    'baseline_val': num_a,
                    'followup_val': num_b,
                    'diff': diff,
                    'pct_change': pct_change,
                    'direction': direction
                }
                comparisons.append(comp_entry)

                if abs(pct_change) >= 20:
                    change_desc = f"{labels.get(param, param)} {'increased' if pct_change > 0 else 'decreased'} by {abs(pct_change)}% ({num_a} → {num_b} {units.get(param, '')})"
                    significant_changes.append(change_desc)

            except (ValueError, TypeError):
                continue

    # Generate synthesis & trajectory
    tsh_entry = next((c for c in comparisons if c['param'] == 'TSH'), None)
    t4_entry = next((c for c in comparisons if c['param'] == 'TT4'), None)

    trajectory = "Stable"
    synthesis = "Hormone biomarker concentrations remained largely stable between assessments."

    if tsh_entry:
        if tsh_entry['pct_change'] >= 25 and (t4_entry and t4_entry['pct_change'] < -10):
            trajectory = "Progressive Hypothyroid Pattern"
            synthesis = "TSH increased noticeably while Total T4 decreased compared to baseline. This may indicate reduced thyroid hormone production or increased replacement requirement."
        elif tsh_entry['pct_change'] <= -25 and (t4_entry and t4_entry['pct_change'] > 10):
            trajectory = "Progressive Hyperthyroid Pattern"
            synthesis = "TSH suppressed significantly while Total T4 increased compared to baseline. Suggests elevated hormone concentration or potential exogenous over-replacement."
        elif abs(tsh_entry['pct_change']) < 15:
            trajectory = "Optimal Euthyroid Stability"
            synthesis = "Thyroid hormone levels demonstrate consistency with baseline reference tracking."

    # Questions to ask physician
    suggested_doctor_questions = [
        "What clinical factors could account for the shifts observed between my two lab tests?",
        "Is my current medication dosage (or dietary intake) adequate for maintaining stable TSH levels?",
        "Should we schedule antibody testing (Anti-TPO or TRAb) or a follow-up ultrasound?",
        "When is the most appropriate timeframe for my next follow-up thyroid panel?"
    ]

    return {
        'date_baseline': report_a.get('date', 'Report A (Baseline)'),
        'date_followup': report_b.get('date', 'Report B (Follow-up)'),
        'comparisons': comparisons,
        'significant_changes': significant_changes,
        'trajectory': trajectory,
        'synthesis': synthesis,
        'suggested_doctor_questions': suggested_doctor_questions
    }
