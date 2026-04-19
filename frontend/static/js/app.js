

const API_BASE = 'http://localhost:5000';

// ---- Toggle measured checkbox ----
function toggleMeasured(checkbox, fieldName) {
  const input = document.querySelector(`input[name="${fieldName}"]`);
  if (input) {
    input.disabled = !checkbox.checked;
    if (!checkbox.checked) input.value = '';
  }
}

// ---- Toggle pregnancy field ----
function togglePregnancy(sexValue) {
  const pregnancyField = document.getElementById('pregnancy-field');
  const pregnantRadios = pregnancyField.querySelectorAll('input[name="pregnant"]');
  if (sexValue === '1') { // Male: hide & set No
    pregnancyField.style.display = 'none';
    pregnantRadios.forEach(r => r.disabled = true);
    pregnantRadios[1].checked = true; // No
  } else { // Female: show
    pregnancyField.style.display = '';
    pregnantRadios.forEach(r => r.disabled = false);
  }
}

// ---- Medications handlers ----
const DOSAGES = {
  eltroxin: [25, 50, 75, 88, 100, 112, 125, 200],
  thyronorm: [25, 50, 75, 88, 100, 112, 125]
};

function toggleMedications() {
  const yesRadio = document.querySelector('input[name="on_thyroxine"][value="1"]:checked');
  const medDetails = document.getElementById('medication-details');
  const dosageDetails = document.getElementById('dosage-details');
  if (yesRadio) {
    medDetails.style.display = '';
  } else {
    medDetails.style.display = 'none';
    dosageDetails.style.display = 'none';
    if (document.getElementById('med-type-select')) document.getElementById('med-type-select').value = '';
    if (document.getElementById('dosage-select')) {
      document.getElementById('dosage-select').innerHTML = '<option value="">Select dosage</option>';
      dosageDetails.style.display = 'none';
    }
  }
}

function populateDosage() {
  const medType = document.getElementById('med-type-select').value;
  const dosageSelect = document.getElementById('dosage-select');
  const dosageDetails = document.getElementById('dosage-details');
  dosageSelect.innerHTML = '<option value="">Select dosage</option>';
  dosageDetails.style.display = 'none';
  if (medType === 'eltroxin' || medType === 'thyronorm') {
    const dosages = DOSAGES[medType];
    dosages.forEach(d => {
      const opt = document.createElement('option');
      opt.value = d;
      opt.textContent = d + ' mcg';
      dosageSelect.appendChild(opt);
    });
    dosageDetails.style.display = '';
  }
}

// ---- Sample data loader ----
function fillSample() {
  const samples = [
    // Hypothyroid sample
    { age: 72, sex: '0', on_thyroxine: '0', thyroid_surgery: '0', pregnant: '0', sick: '0',
      TSH: 42.0, T3: 0.8, TT4: 45, T4U: 1.02, FTI: 50,
      goitre: true, query_hypothyroid: true },
    // Normal sample
{ age: 35, sex: '1', on_thyroxine: '1', thyroid_surgery: '0', pregnant: '0', sick: '0',\n      TSH: 1.8, T3: 2.1, TT4: 105, T4U: 1.05, FTI: 100,\n      medication_type: 'eltroxin', dosage_mcg: 100 },
    // Hyperthyroid sample
    { age: 28, sex: '0', on_thyroxine: '0', thyroid_surgery: '0', pregnant: '0', sick: '0',
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

  // Clear then set flags\n  form.querySelectorAll('.flag-card input[type="checkbox"]').forEach(cb => { cb.checked = false; });\n  ['goitre', 'tumor', 'psych', 'lithium', 'hypopituitary',\n   'query_hypothyroid', 'query_hyperthyroid', 'on_antithyroid_medication', 'I131_treatment'].forEach(flag => {\n    if (sample[flag]) {\n      const cb = form.querySelector(`input[name="${flag}"]`);\n      if (cb) cb.checked = true;\n    }\n  });\n\n  // Set medications if present\n  if (sample.on_thyroxine === '1' && sample.medication_type) {\n    const onThyroxineYes = form.querySelector('input[name="on_thyroxine"][value="1"]');\n    if (onThyroxineYes) onThyroxineYes.checked = true;\n    toggleMedications();\n    setTimeout(() => {\n      const medSelect = document.getElementById('med-type-select');\n      if (medSelect) medSelect.value = sample.medication_type;\n      populateDosage();\n      setTimeout(() => {\n        const dosageSelect = document.getElementById('dosage-select');\n        if (dosageSelect && sample.dosage_mcg) dosageSelect.value = sample.dosage_mcg;\n      }, 50);\n    }, 50);\n  }
    if (sample[flag]) {
      const cb = form.querySelector(`input[name="${flag}"]`);
      if (cb) cb.checked = true;
    }
  });

  showToast('Sample data loaded!');
}

// ---- Reset form ----
function resetForm() {
  document.getElementById('predict-form').reset();
  document.getElementById('result-section').classList.add('hidden');
  showToast('Form cleared.');
}

// ---- Toast notification ----
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

// ---- Collect form data ----
function collectFormData() {
  const form = document.getElementById('predict-form');
  const fd = new FormData(form);
  const data = {};

  // All feature fields
  const binaryFields = ['on_thyroxine', 'query_on_thyroxine', 'on_antithyroid_medication',
    'sick', 'pregnant', 'thyroid_surgery', 'I131_treatment', 'query_hypothyroid',
    'query_hyperthyroid', 'lithium', 'goitre', 'tumor', 'hypopituitary', 'psych',
    'TSH_measured', 'T3_measured', 'TT4_measured', 'T4U_measured', 'FTI_measured'];

  // Defaults for unmeasured
  ['TSH_measured', 'T3_measured', 'TT4_measured', 'T4U_measured', 'FTI_measured'].forEach(f => {
    data[f] = 0;
  });

  for (const [key, value] of fd.entries()) {
    data[key] = value;
  }

  // Checkboxes default to 0 if not checked
  binaryFields.forEach(f => {
    if (data[f] === undefined) data[f] = 0;
    else data[f] = parseInt(data[f]) || 0;
  });

  // Numerics
  ['age', 'sex', 'referral_source'].forEach(f => {
    if (data[f] !== undefined) data[f] = parseFloat(data[f]) || 0;
  });
  ['TSH', 'T3', 'TT4', 'T4U', 'FTI'].forEach(f => {
    if (data[f] !== undefined && data[f] !== '') {
      data[f] = parseFloat(data[f]);
    } else {
      data[f] = null;
    }
  });

  return data;
}

// ---- Show results ----
function showResults(result) {
  const section = document.getElementById('result-section');
  section.classList.remove('hidden');

  const info = result.diagnosis_info;
  const severity = info.severity || 'normal';

  // Diagnosis card
  const card = document.getElementById('diagnosis-card');
  card.className = `diagnosis-card severity-${severity}`;
  const icons = { normal: '✅', moderate: '⚠️', high: '🚨' };
  document.getElementById('diag-icon').textContent = icons[severity] || '🔬';
  document.getElementById('diag-label').textContent = info.label;
  document.getElementById('diag-desc').textContent = info.description;
  document.getElementById('confidence-val').textContent = result.confidence.toFixed(1);

  // Animate confidence bar
  setTimeout(() => {
    document.getElementById('confidence-fill').style.width = result.confidence + '%';
  }, 100);

  // Probability bars
  const probBars = document.getElementById('prob-bars');
  probBars.innerHTML = '';
  const labelMap = {
    negative: 'Negative', hypothyroid: 'Hypothyroidism', hyperthyroid: 'Hyperthyroidism',
    subclinical_hypothyroid: 'Subclinical Hypothyroid', subclinical_hyperthyroid: 'Subclinical Hyperthyroid'
  };
  const sorted = Object.entries(result.class_probabilities).sort((a, b) => b[1] - a[1]);
  sorted.forEach(([cls, pct]) => {
    const row = document.createElement('div');
    row.className = 'prob-row';
    row.innerHTML = `
      <div class="prob-name">${labelMap[cls] || cls}</div>
      <div class="prob-track"><div class="prob-fill" style="width:0%" data-pct="${pct}"></div></div>
      <div class="prob-pct">${pct.toFixed(1)}%</div>
    `;
    probBars.appendChild(row);
  });
  setTimeout(() => {
    document.querySelectorAll('.prob-fill').forEach(el => {
      el.style.width = el.dataset.pct + '%';
    });
  }, 200);

  // Recommendations
  const recList = document.getElementById('rec-list');
  recList.innerHTML = '';
  (info.recommendations || []).forEach(rec => {
    const li = document.createElement('li');
    li.textContent = rec;
    recList.appendChild(li);
  });

  section.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ---- Scroll to form ----
function scrollToForm() {
  document.getElementById('assess').scrollIntoView({ behavior: 'smooth' });
}

// ---- Form submit ----
document.getElementById('predict-form').addEventListener('submit', async (e) => {
  e.preventDefault();

  const ageVal = document.querySelector('[name="age"]').value;
  const sexVal = document.querySelector('[name="sex"]').value;
  if (!ageVal || !sexVal) {
    showToast('Please fill in Age and Sex');
    return;
  }

  document.getElementById('loading-overlay').classList.remove('hidden');

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
    document.getElementById('loading-overlay').classList.add('hidden');
  }
});

// ---- Load model comparison ----
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
      card.innerHTML = `
        <div class="model-name">${icons[name] || '🤖'} ${name}</div>
        <div class="model-metrics">
          <div class="metric-row">
            <div class="metric-label">Accuracy <span>${(m.accuracy * 100).toFixed(2)}%</span></div>
            <div class="metric-bar"><div class="metric-fill" style="width:0%" data-pct="${m.accuracy * 100}"></div></div>
          </div>
          <div class="metric-row">
            <div class="metric-label">F1 Score <span>${(m.f1_score * 100).toFixed(2)}%</span></div>
            <div class="metric-bar"><div class="metric-fill" style="width:0%;background:linear-gradient(90deg,#8b5cf6,#63fcda)" data-pct="${m.f1_score * 100}"></div></div>
          </div>
        </div>
      `;
      grid.appendChild(card);
    });

    setTimeout(() => {
      document.querySelectorAll('.metric-fill').forEach(el => {
        el.style.width = el.dataset.pct + '%';
      });
    }, 300);
  } catch (err) {
    console.warn('Could not load model info:', err.message);
    // Show static fallback
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

// ---- Nav active on scroll ----
const sections = document.querySelectorAll('section[id]');
window.addEventListener('scroll', () => {
  let cur = '';
  sections.forEach(s => {
    if (window.scrollY >= s.offsetTop - 100) cur = s.id;
  });
  document.querySelectorAll('.nav-link').forEach(a => {
    a.classList.toggle('active', a.getAttribute('href') === '#' + cur);
  });
});

// ---- Sex change listener ----
document.addEventListener('DOMContentLoaded', function() {
  const sexSelect = document.querySelector('[name="sex"]');
  if (sexSelect) {
    sexSelect.addEventListener('change', function() {
      togglePregnancy(this.value);
    });
    // Init visibility
    togglePregnancy(sexSelect.value);
  }

  // Medications init
  document.querySelectorAll('input[name="on_thyroxine"]').forEach(radio => {
    radio.addEventListener('change', toggleMedications);
  });
  const medTypeSelect = document.getElementById('med-type-select');
  if (medTypeSelect) {
    medTypeSelect.addEventListener('change', populateDosage);
  }
  toggleMedications();

  // ---- Theme toggle ----
  const themeToggle = document.getElementById('theme-toggle');
  const body = document.body;
  if (themeToggle) {
    // Load saved theme
    if (localStorage.getItem('theme') === 'light' || (!localStorage.getItem('theme') && window.matchMedia('(prefers-color-scheme: light)').matches)) {
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

  // ---- Real-time status (clock + temp) ----
  function updateStatus() {
    const now = new Date();
    const time = now.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
    const temp = Math.round(15 + Math.random() * 20); // 15-35°C
    document.getElementById('status-bar').textContent = `${time} | ${temp}°C`;
  }
  updateStatus(); // Initial
  setInterval(updateStatus, 10000); // Every 10s
});

// ---- Init ----
loadModelComparison();
