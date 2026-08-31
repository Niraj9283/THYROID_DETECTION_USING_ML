"""
ThyroScan AI — Longitudinal Patient Trajectory & Treatment Response Service
Tracks multi-visit clinical time-series biomarker evolutions, calculates hormonal shift velocities,
projects future endocrine trajectories, and evaluates Levothyroxine/Antithyroid dosage adequacy.
"""

import math
from datetime import datetime
import numpy as np


def analyze_longitudinal_trajectory(visits: list) -> dict:
    """
    Analyzes a multi-visit time series of patient thyroid biomarkers.
    Visits list format:
    [
        {"date": "2025-01-10", "tsh": 7.8, "ft4": 12.2, "t3": 2.1, "medication": "Levothyroxine", "dose_mcg": 50},
        {"date": "2025-04-12", "tsh": 5.4, "ft4": 14.1, "t3": 2.4, "medication": "Levothyroxine", "dose_mcg": 50},
        {"date": "2025-08-20", "tsh": 2.3, "ft4": 16.5, "t3": 2.6, "medication": "Levothyroxine", "dose_mcg": 75}
    ]
    """
    if not visits or len(visits) < 2:
        return {
            'status': 'insufficient_data',
            'message': 'At least 2 longitudinal visits are required to compute rate-of-change velocities and disease trajectories.'
        }

    # Sort visits chronologically
    sorted_visits = []
    for v in visits:
        try:
            dt = datetime.strptime(v.get('date', '2025-01-01'), '%Y-%m-%d')
        except ValueError:
            dt = datetime.now()
        
        tsh = float(v.get('tsh', 2.0))
        ft4 = float(v.get('ft4', 15.0)) if v.get('ft4') is not None else 15.0
        t3 = float(v.get('t3', 2.3)) if v.get('t3') is not None else 2.3
        med = v.get('medication', 'None')
        dose = float(v.get('dose_mcg', 0)) if v.get('dose_mcg') is not None else 0

        sorted_visits.append({
            'date_str': v.get('date', dt.strftime('%Y-%m-%d')),
            'datetime': dt,
            'tsh': tsh,
            'ft4': ft4,
            't3': t3,
            'medication': med,
            'dose_mcg': dose
        })

    sorted_visits.sort(key=lambda x: x['datetime'])

    # 1. Extract Time Deltas (in months) and Biomarker Values
    t0 = sorted_visits[0]['datetime']
    months_elapsed = []
    tsh_values = []
    ft4_values = []

    for v in sorted_visits:
        delta_days = (v['datetime'] - t0).days
        m = round(delta_days / 30.4375, 1)
        months_elapsed.append(m)
        tsh_values.append(v['tsh'])
        ft4_values.append(v['ft4'])

    total_duration_months = months_elapsed[-1]
    n_visits = len(sorted_visits)

    # 2. Compute Rates of Change (Velocity)
    initial_tsh = tsh_values[0]
    current_tsh = tsh_values[-1]
    delta_tsh = current_tsh - initial_tsh

    initial_ft4 = ft4_values[0]
    current_ft4 = ft4_values[-1]
    delta_ft4 = current_ft4 - initial_ft4

    if total_duration_months > 0:
        tsh_velocity = delta_tsh / total_duration_months  # mIU/L per month
        ft4_velocity = delta_ft4 / total_duration_months  # pmol/L per month
    else:
        tsh_velocity = 0.0
        ft4_velocity = 0.0

    # 3. Volatility Index (Coefficient of Variation)
    mean_tsh = np.mean(tsh_values)
    std_tsh = np.std(tsh_values)
    volatility_cv = (std_tsh / mean_tsh * 100) if mean_tsh > 0 else 0.0

    # 4. Trajectory Classification & Forecasting
    latest_visit = sorted_visits[-1]
    latest_med = latest_visit['medication']
    latest_dose = latest_visit['dose_mcg']

    if current_tsh > 10.0:
        trajectory_pattern = "Progression to Overt Primary Hypothyroidism"
        clinical_severity = "High"
        severity_badge = "badge-danger"
        projected_tsh_6m = current_tsh + (tsh_velocity * 6 if tsh_velocity > 0 else 1.5)
        treatment_response = "Sub-therapeutic / Unmanaged"
        titration_recommendation = (
            "Substantial TSH elevation (> 10.0 mIU/L). If on Levothyroxine, verify adherence, absorption, "
            "and consider escalating dosage by +25 to +50 mcg/day. Repeat TSH and Free T4 in 6-8 weeks."
        )
    elif 4.5 <= current_tsh <= 10.0:
        if initial_tsh < 4.5 and tsh_velocity > 0:
            trajectory_pattern = "Active Subclinical Hypothyroid Progression"
            clinical_severity = "Moderate"
            severity_badge = "badge-warning"
            projected_tsh_6m = current_tsh + (tsh_velocity * 6)
            treatment_response = "Borderline / Pending Titration"
            titration_recommendation = (
                f"TSH demonstrates an upward velocity of +{tsh_velocity:.2f} mIU/L/month toward subclinical threshold. "
                "Check Anti-TPO antibodies. If symptomatic or high cardiovascular risk, consider initiating trial of Levothyroxine (25-50 mcg)."
            )
        elif initial_tsh > current_tsh:
            trajectory_pattern = "Therapeutic Response / Subclinical Improvement"
            clinical_severity = "Improving"
            severity_badge = "badge-info"
            projected_tsh_6m = max(2.0, current_tsh + (tsh_velocity * 6))
            treatment_response = "Positive Response to Treatment"
            titration_recommendation = (
                "TSH is trending down favorably toward target euthyroid range (0.4 - 4.0 mIU/L). "
                "Maintain current Levothyroxine dose and recheck lab panel in 8-12 weeks."
            )
        else:
            trajectory_pattern = "Stable Subclinical Hypothyroid Plateau"
            clinical_severity = "Low - Moderate"
            severity_badge = "badge-warning"
            projected_tsh_6m = current_tsh
            treatment_response = "Stable Observation"
            titration_recommendation = "Maintain routine 6-month surveillance unless patient develops overt hypothyroid symptomatology."
    elif 0.4 <= current_tsh < 4.5:
        trajectory_pattern = "Optimal Euthyroid Homeostasis"
        clinical_severity = "Normal / Controlled"
        severity_badge = "badge-success"
        projected_tsh_6m = current_tsh + (tsh_velocity * 3)
        treatment_response = "Target Reached (Well-Controlled)"
        titration_recommendation = (
            "Thyroid axis is well-equilibrated within normal physiological target bounds. "
            "Continue current regimen with annual routine surveillance."
        )
    elif 0.1 <= current_tsh < 0.4:
        trajectory_pattern = "Borderline Subclinical Hyperthyroidism / Mild Over-replacement"
        clinical_severity = "Moderate"
        severity_badge = "badge-warning"
        projected_tsh_6m = current_tsh + (tsh_velocity * 6)
        treatment_response = "Mild Over-replacement"
        titration_recommendation = (
            "TSH is mildly suppressed. If patient is on Levothyroxine, reduce daily dose slightly (e.g. -12.5 mcg or skip one dose weekly) "
            "to prevent atrial fibrillation and accelerated bone turnover."
        )
    else:  # < 0.1
        trajectory_pattern = "Marked Thyrotoxicosis / Severe Exogenous Suppression"
        clinical_severity = "High"
        severity_badge = "badge-danger"
        projected_tsh_6m = current_tsh
        treatment_response = "Excessive Replacement / Thyrotoxic"
        titration_recommendation = (
            "Critical TSH suppression (< 0.1 mIU/L). Urgently reduce or hold thyroid hormone therapy. "
            "Evaluate ECG for tachyarrhythmias and assess bone mineral density risk."
        )

    # 5. Timeline Chart Data Points
    chart_timeline = []
    for i, v in enumerate(sorted_visits):
        chart_timeline.append({
            'date': v['date_str'],
            'month': months_elapsed[i],
            'tsh': v['tsh'],
            'ft4': v['ft4'],
            'medication': v['medication'],
            'dose_mcg': v['dose_mcg']
        })

    # Add Projected 6-Month Point
    chart_timeline.append({
        'date': 'Projected (6m)',
        'month': round(total_duration_months + 6.0, 1),
        'tsh': round(float(projected_tsh_6m), 2),
        'ft4': round(float(current_ft4 + ft4_velocity * 6.0), 2),
        'is_projected': True,
        'medication': latest_med,
        'dose_mcg': latest_dose
    })

    return {
        'status': 'success',
        'visits_count': n_visits,
        'total_duration_months': total_duration_months,
        'trajectory_pattern': trajectory_pattern,
        'clinical_severity': clinical_severity,
        'severity_badge': severity_badge,
        'treatment_response': treatment_response,
        'titration_recommendation': titration_recommendation,
        'metrics': {
            'initial_tsh': initial_tsh,
            'current_tsh': current_tsh,
            'delta_tsh': round(delta_tsh, 2),
            'tsh_velocity_monthly': round(tsh_velocity, 3),
            'initial_ft4': initial_ft4,
            'current_ft4': current_ft4,
            'delta_ft4': round(delta_ft4, 2),
            'ft4_velocity_monthly': round(ft4_velocity, 3),
            'volatility_cv_pct': round(volatility_cv, 1),
            'projected_tsh_6m': round(float(projected_tsh_6m), 2)
        },
        'timeline': chart_timeline
    }
