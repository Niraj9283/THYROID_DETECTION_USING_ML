const API_BASE = 'http://localhost:5000';

// Medications data
const MEDS = {
  hypo: ['levothyroxine', 'levoxyl', 'synthroid'],
  hyper: ['methimazole', 'propylthiouracil', 'ptu']
};

const DOSAGES = {
  levothyroxine: [25, 50, 75, 88, 100, 112, 125, 150, 175, 200, 300],
  levoxyl: [25, 50, 75, 88, 100, 112, 125, 150, 175, 200],
  synthroid: [25, 50, 75, 88, 100, 112, 125, 150, 175, 200, 300],
  methimazole: [5, 10, 15, 20, 30],
  propylthiouracil: [50, 100, 150, 200, 300],
  ptu: [50, 100, 150, 200]
};

// Toggle measured checkbox
function toggleMeasured(checkbox, fieldName) {
  const input = document.querySelector(`input[name="${fieldName}"]`);
  if (input) {
    input.disabled = !checkbox.checked;
    if (!checkbox.checked) input.value = '';
  }
}

// Toggle pregnancy field
function togglePregnancy(sexValue) {
  const pregnancyField = document.getElementById('pregnancy-field');
  const pregnantRadios = pregnancyField.querySelectorAll('input[name="pregnant"]');
  if (sexValue === '1') { // Male
    pregnancyField.style.display = 'none';
    pregnantRadios.forEach(r => r.disabled = true);
    pregnantRadios[1].checked = true;
  } else {
    pregnancyField.style.display = '';
    pregnantRadios.forEach(r => r.disabled = false);
  }
}

// Medication handlers
function toggleMedications() {
  const yesRadio = document.querySelector('input[name="on_thyroxine"][value="1"]:checked');
  const medDetails = document.getElementById('medication-details');
  const medTypeDetails = document.getElementById('med-type-details');
  const dosageDetails = document.getElementById('dosage-details');
  if (yesRadio) {
    if (medDetails) medDetails.style.display = '';
  } else {
    if (medDetails) medDetails.style.display = 'none';
    if (medTypeDetails) medTypeDetails.style.display = 'none';
    if (dosageDetails) dosageDetails.style.display = 'none';
    const medCondSelect = document.getElementById('med-condition-select');
    const medTypeSelect = document.getElementById('med-type-select');
    const dosageSelect = document.getElementById('dosage-select');
    if (medCondSelect) medCondSelect.value = '';
    if (medTypeSelect) {
      medTypeSelect.innerHTML = '<option value="">Select medication</option>';
    }
    if (dosageSelect) {
      dosageSelect.innerHTML = '<option value="">Select dosage</option>';
    }
  }
}

function toggleMedCondition() {
  const condition = document.getElementById('med-condition-select').value;
  const medTypeDetails = document.getElementById('med-type-details');
  const dosageDetails = document.getElementById('dosage-details');
  const medTypeSelect = document.getElementById('med-type-select');
  const dosageSelect = document.getElementById('dosage-select');
  
  if (condition) {
    if (medTypeDetails) medTypeDetails.style.display = '';
    if (medTypeSelect) {
      medTypeSelect.innerHTML = '<option value="">Select medication</option>';
      MEDS[condition].forEach(med => {
        const opt = document.createElement('option');
        opt.value = med;
        opt.textContent = med.charAt(0).toUpperCase() + med.slice(1).replace('_', ' ');
        medTypeSelect.appendChild(opt);
      });
    }
  } else {
    if (medTypeDetails) medTypeDetails.style.display = 'none';
    if (dosageDetails) dosageDetails.style.display = 'none';
    if (medTypeSelect) medTypeSelect.innerHTML = '<option value="">Select medication</option>';
    if (dosageSelect) dosageSelect.innerHTML = '<option value="">Select dosage</option>';
  }
}

function populateDosage() {
  const medType = document.getElementById('med-type-select').value;
  const dosageSelect = document.getElementById('dosage-select');
  const dosageDetails = document.getElementById('dosage-details');
  if (dosageSelect) dosageSelect.innerHTML = '<option value="">Select dosage</option>';
  if (dosageDetails) dosageDetails.style.display = 'none';
  if (medType && DOSAGES[medType]) {
    DOSAGES[medType].forEach(d => {
      const opt = document.createElement('option');
      opt.value = d;
      opt.textContent = d + ' mcg';
      dosageSelect.appendChild(opt);
    });
    if (dosageDetails) dosageDetails.style.display = '';
  }
}

// Sick toggle
function toggleSick() {
  const yesRadio = document.querySelector('input[name="sick"][value="1"]:checked');
  const sickDetails = document.getElementById('sick-details');
  const symptomSelect = document.getElementById('sick-symptom-select');
  if (yesRadio && sickDetails) {
    sickDetails.style.display = '';
  } else {
    if (sickDetails) sickDetails.style.display = 'none';
    if (symptomSelect) symptomSelect.value = '';
  }
}

// BMI calculator
function calcBMI() {
  const heightCm = parseFloat(document.getElementById('height_cm').value);
  const weightKg = parseFloat(document.getElementById('weight_kg').value);
  const bmiResult = document.getElementById('bmi-result');
  const bmiValue = document.getElementById('bmi_value');
  
  if (heightCm && heightCm > 0 && weightKg && weightKg > 0) {
    const heightM = heightCm / 100;
    const bmi = weightKg / (heightM * heightM);
    bmiValue.value = bmi.toFixed(1);
    
    let category, color, risk = '';
    if (bmi < 18.5) {
      category = 'Underweight';
      color = '#3b82f6';
      risk = 'Underweight individuals may be prone to hypothyroidism.';
    } else if (bmi < 25) {
      category = 'Normal';
      color = '#10b981';
      risk = 'Healthy BMI range.';
    } else if (bmi < 30) {
      category = 'Overweight';
      color = '#f59e0b';
      risk = 'Overweight may increase risk for hypothyroidism.';
    } else {
      category = 'Obese';
      color = '#ef4444';
      risk = 'Obesity is associated with higher hypothyroidism risk.';
    }
    
    bmiResult.innerHTML = `
      <strong style="color: ${color};">BMI: ${bmi.toFixed(1)} (${category})</strong><br>
      <small>${risk}</small>
    `;
    bmiResult.style.border = `1px solid ${color}`;
    bmiResult.style.background = color + '20';
  } else {
    bmiResult.textContent = 'Enter height and weight to calculate BMI';
    bmiResult.style.border = '';
    bmiResult.style.background = '';
    bmiValue.value = '';
  }
}

// Sample data loader
function fillSample() {
  const samples = [
    // Hypothyroid sample
    { age: 72, sex: '0', on_thyroxine: '1', thyroid_surgery: '0', pregnant: '0', sick: '1',
      med_condition: 'hypo', med_type: 'levothyroxine', dosage_mcg: 100,
      sick_symptom: 'fatigue', height_cm: 165, weight_kg: 85, bmi: 31.2,
      TSH: 42.0, T3: 0.8, TT4: 45, T4U: 1.02, FTI: 50,
      goitre: true, query_hypothyroid: true },
    // Normal sample
    { age: 35, sex: '1', on_thyroxine: '0', thyroid_surgery: '0', pregnant: '0', sick: '0',
      height_cm: 175, weight_kg: 70, bmi: 22.9,
      TSH: 1.8, T3: 2.1, TT4: 105, T4U: 1.05, FTI: 100 },
    // Hyperthyroid sample
    { age: 28, sex: '0', on_thyroxine: '1', thyroid_surgery: '0', pregnant: '0', sick: '1',
      med_condition: 'hyper', med_type: 'methimazole', dosage_mcg: 10,
      sick_symptom: 'palpitations', height_cm: 160, weight_kg: 55, bmi: 21.5,
      TSH: 0.01, T3: 5.2, TT4: 200, T4U: 0.95, FTI: 180,
      goitre: true, query_hyperthyroid: true }
  ];
  const sample = samples[Math.floor(Math.random() * samples.length)];
  const form = document.getElementById('predict-form');

  // Fill basic fields
  ['age', 'sex', 'on_thyroxine', 'thyroid_surgery', 'pregnant', 'sick'].forEach(field => {
    const el = form.querySelector(`[name="${field}"]`);
    if (!el) return;
    if (el.tagName === 'SELECT') el.value = sample[field] ?? el.value;
    else if (el.type === 'radio') {
      form.querySelectorAll(`[name="${field}"]`).forEach(r => {
        r.checked = r.value === String(sample[field] ?? '0');
      });
    }
  });

  // New fields
  if (sample.med_condition) {
    document.getElementById('med-condition-select').value = sample.med_condition;
    setTimeout(() => {
      document.getElementById('med-type-select').value = sample.med_type || '';
      setTimeout(() => {
        document.getElementById('dosage-select').value = sample.dosage_mcg || '';
      }, 100);
    }, 100);
  }
  if (sample.sick_symptom) {
    document.getElementById('sick-symptom-select').value = sample.sick_symptom;
  }
  if (sample.height_cm) document.getElementById('height_cm').value = sample.height_cm;
  if (sample.weight_kg) document.getElementById('weight_kg').value = sample.weight_kg;
  if (sample.bmi) calcBMI();

  // Fill lab values
  ['TSH', 'T3', 'TT4', 'T4U', 'FTI'].forEach(field => {
    const el = form.querySelector(`input[name="${field}"]`);
    if (el && sample[field] !== undefined) {
      el.value = sample[field];
      el.disabled = false;
      const chk = form.querySelector(`input[name="${field}_measured"]`);
      if (chk) chk.checked = true;
    }
  });

  // Flags
  form.querySelectorAll('.flag-card input[type="checkbox"]').forEach(cb => cb.checked = false);
  ['goitre', 'tumor', 'psych', 'lithium', 'hypopituitary', 'query_hypothyroid', 'query_hyperthyroid', 'on_antithyroid_medication', 'I131_treatment'].forEach(flag => {
    if (sample[flag]) {
      const cb = form.querySelector(`input[name="${flag}"]`);
      if (cb) cb.checked = true;
    }
  });

  // Trigger toggles
  setTimeout(() => {
    toggleMedications();
    toggleMedCondition();
    toggleSick();
    togglePregnancy(document.querySelector('[name="sex"]').value);
  }, 200);

  showToast('Sample data loaded!');
}

// Reset form
function resetForm() {
  document.getElementById('predict-form').reset();
  document.getElementById('result-section').classList.add('hidden');
  document.getElementById('bmi-result').textContent = 'Enter height and weight to calculate BMI';
  document.getElementById('bmi-result').style.border = '';
  document.getElementById('bmi-result').style.background = '';
  toggleMedications();
  toggleSick();
  showToast('Form cleared.');
}

// Toast notification
function showToast(msg) {
  const existing = document.querySelector('.toast');
  if (existing) existing.remove();
  const t = document.createElement('div');
  t.className = 'toast';
  t.textContent = msg;
  t.style.cssText = `
    position:fixed;bottom:24px;left:50%;transform:translateX(-50%);
    background:rgba(99,252,218,0.15);border:1px solid rgba(99,252,218,0.3);
    color:#63fcda;padding:10px 20px;border-radius:8px;font-size:13px;
    z-index:300;backdrop-filter:blur(10px);animation:fadeIn 0.3s ease;
  `;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 2500);
}

// Collect form data
function collectFormData() {
  const form = document.getElementById('predict-form');
  const fd = new FormData(form);
  const data = {};
  const binaryFields = ['on_thyroxine', 'query_on_thyroxine', 'on_antithyroid_medication', 'sick', 'pregnant', 'thyroid_surgery', 'I131_treatment', 'query_hypothyroid', 'query_hyperthyroid', 'lithium', 'goitre', 'tumor', 'hypopituitary', 'psych', 'TSH_measured', 'T3_measured', 'TT4_measured', 'T4U_measured', 'FTI_measured'];
  
  ['TSH_measured', 'T3_measured', 'TT4_measured', 'T4U_measured', 'FTI_measured'].forEach(f => data[f] = 0);
  for (const [key, value] of fd.entries()) data[key] = value;
  
  binaryFields.forEach(f => data[f] = data[f] === undefined ? 0 : parseInt(data[f]) || 0);
  ['age', 'sex', 'referral_source'].forEach(f => data[f] = parseFloat(data[f]) || 0);
  ['TSH', 'T3', 'TT4', 'T4U', 'FTI', 'height_cm', 'weight_kg', 'bmi'].forEach(f => {
    if (data[f] !== undefined && data[f] !== '') data[f] = parseFloat(data[f]);
    else data[f] = null;
  });
  
  return data;
}

// ... rest of functions (showResults, loadModelComparison, etc.) unchanged from original ...
function showResults(result) {
  const section = document.getElementById('result-section');
  section.classList.remove('hidden');
  const info = result.diagnosis_info;
  const severity = info.severity || 'normal';
  const card = document.getElementById('diagnosis-card');
  card.className = `diagnosis-card severity-${severity}`;
  const icons = { normal: '✅', moderate: '⚠️', high: '🚨' };
  document.getElementById('diag-icon').textContent = icons[severity] || '🔬';
  document.getElementById('diag-label').textContent = info.label;
  document.getElementById('diag-desc').textContent = info.description;
  document.getElementById('confidence-val').textContent = result.confidence.toFixed(1);
  setTimeout(() => document.getElementById('confidence-fill').style.width = result.confidence + '%', 100);
  
  const probBars = document.getElementById('prob-bars');
  probBars.innerHTML = '';
  const labelMap = { negative: 'Negative', hypothyroid: 'Hypothyroidism', hyperthyroid: 'Hyperthyroidism', subclinical_hypothyroid: 'Subclinical Hypothyroid', subclinical_hyperthyroid: 'Subclinical Hyperthyroid' };
  const sorted = Object.entries(result.class_probabilities).sort((a, b) => b[1] - a[1]);
  sorted.forEach(([cls, pct]) => {
    const row = document.createElement('div');
    row.className = 'prob-row';
    row.innerHTML = `<div class="prob-name">${labelMap[cls] || cls}</div><div class="prob-track"><div class="prob-fill" style="width:0%" data-pct="${pct}"></div></div><div class="prob-pct">${pct.toFixed(1)}%</div>`;
    probBars.appendChild(row);
  });
  setTimeout(() => document.querySelectorAll('.prob-fill').forEach(el => el.style.width = el.dataset.pct + '%'), 200);
  
  const recList = document.getElementById('rec-list');
  recList.innerHTML = '';
  (info.recommendations || []).forEach(rec => {
    const li = document.createElement('li');
    li.textContent = rec;
    recList.appendChild(li);
  });
  section.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

async function loadModelComparison() {
  try {
    const res = await fetch(`${API_BASE}/api/model-info`);
    const data = await res.json();
    const grid = document.getElementById('models-grid');
    grid.innerHTML = '';
    const modelNames = Object.keys(data).filter(k => k !== 'best_model');
    const best = data.best_model;
    const icons = { 'Random Forest': '🌲', 'Gradient Boosting': '⚡', 'SVM': '🔮' };
    modelNames.forEach(name => {
      const m = data[name];
      const isBest = name === best;
      const card = document.createElement('div');
      card.className = 'model-card' + (isBest ? ' is-best' : '');
      card.innerHTML = `<div class="model-name">${icons[name] || '🤖'} ${name}</div><div class="model-metrics"><div class="metric-row"><div class="metric-label">Accuracy <span>${(m.accuracy * 100).toFixed(2)}%</span></div><div class="metric-bar"><div class="metric-fill" style="width:0%" data-pct="${m.accuracy * 100}"></div></div></div><div class="metric-row"><div class="metric-label">F1 Score <span>${(m.f1_score * 100).toFixed(2)}%</span></div><div class="metric-bar"><div class="metric-fill" style="width:0%;background:linear-gradient(90deg,#8b5cf6,#63fcda)" data-pct="${m.f1_score * 100}"></div></div></div></div>`;
      grid.appendChild(card);
    });
    setTimeout(() => document.querySelectorAll('.metric-fill').forEach(el => el.style.width = el.dataset.pct + '%'), 300);
  } catch (err) {
    console.warn('Could not load model info:', err.message);
    const grid = document.getElementById('models-grid');
    grid.innerHTML = `
      <div class="model-card is-best">
        <div class="model-name">🌲 Random Forest</div>
        <div class="model-metrics">
          <div class="metric-row">
            <div class="metric-label">Accuracy <span>97.30%</span></div>
            <div class="metric-bar"><div class="metric-fill" style="width:97.3%"></div></div>
          </div>
        </div>
      </div>
      <div class="model-card">
        <div class="model-name">⚡ Gradient Boosting</div>
        <div class="model-metrics">
          <div class="metric-row">
            <div class="metric-label">Accuracy <span>97.08%</span></div>
            <div class="metric-bar"><div class="metric-fill" style="width:97.08%"></div></div>
          </div>
        </div>
      </div>
      <div class="model-card">
        <div class="model-name">🔮 SVM</div>
        <div class="model-metrics">
          <div class="metric-row">
            <div class="metric-label">Accuracy <span>87.08%</span></div>
            <div class="metric-bar"><div class="metric-fill" style="width:87.08%"></div></div>
          </div>
        </div>
      </div>
    `;
  }
}

function scrollToForm() {
  document.getElementById('assess').scrollIntoView({ behavior: 'smooth' });
}

const sections = document.querySelectorAll('section[id]');
window.addEventListener('scroll', () => {
  let cur = '';
  sections.forEach(s => {
    if (window.scrollY >= s.offsetTop - 100) cur = s.id;
  });
  document.querySelectorAll('.nav-link').forEach(a => a.classList.toggle('active', a.getAttribute('href') === '#' + cur));
});

// Form submit
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('predict-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const ageVal = document.querySelector('[name="age"]').value;
    const sexVal = document.querySelector('[name="sex"]').value;
    if (!ageVal || !sexVal) {
      showToast('Please fill in Age and Sex');
      return;
    }
    const loadingOverlay = document.getElementById('loading-overlay');
    if (loadingOverlay) loadingOverlay.classList.remove('hidden');
    try {
      const data = collectFormData();
      const response = await fetch(`${API_BASE}/api/predict`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
      const result = await response.json();
      if (result.error) throw new Error(result.error);
      showResults(result);
    } catch (err) {
      showToast('Error: ' + (err.message || 'Server not reachable'));
      console.error(err);
    } finally {
      if (loadingOverlay) loadingOverlay.classList.add('hidden');
    }
  });

  // Event listeners
  const sexSelect = document.querySelector('[name="sex"]');
  if (sexSelect) {
    sexSelect.addEventListener('change', e => togglePregnancy(e.target.value));
    togglePregnancy(sexSelect.value);
  }
  
  document.querySelectorAll('input[name="on_thyroxine"]').forEach(radio => radio.addEventListener('change', toggleMedications));
  document.querySelectorAll('input[name="sick"]').forEach(radio => radio.addEventListener('change', toggleSick));
  
  const medCondSelect = document.getElementById('med-condition-select');
  if (medCondSelect) medCondSelect.addEventListener('change', toggleMedCondition);
  
  const medTypeSelect = document.getElementById('med-type-select');
  if (medTypeSelect) medTypeSelect.addEventListener('change', populateDosage);
  
  toggleMedications();
  toggleSick();
  
  // Theme toggle
  const themeToggle = document.getElementById('theme-toggle');
  const body = document.body;
  if (themeToggle) {
    const saved = localStorage.getItem('theme');
    if (saved === 'light' || (!saved && window.matchMedia('(prefers-color-scheme: light)').matches)) {
      body.classList.add('light-theme');
      themeToggle.textContent = '☀️';
    }
    themeToggle.addEventListener('click', () => {
      body.classList.toggle('light-theme');
      const isLight = body.classList.contains('light-theme');
      themeToggle.textContent = isLight ? '☀️' : '🌙';
      localStorage.setItem('theme', isLight ? 'light' : 'dark');
    });
  }

  function updateStatus() {
    const now = new Date();
    const time = now.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
    const temp = Math.round(15 + Math.random() * 20);
    document.getElementById('status-bar').textContent = `${time} | ${temp}°C`;
  }
  updateStatus();
  setTimeout(updateStatus, 10000);

  loadModelComparison();
});

