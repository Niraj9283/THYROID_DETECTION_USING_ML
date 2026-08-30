/* ==========================================================================
   ThyroScan AI — Flagship Client Logic
   Multi-Model Ensemble, Conversational AI, Lab Comparison, What-If Simulator,
   Doctor Mode SOAP Notes, and Health Copilot
   ========================================================================== */

const API_BASE = window.location.origin;

let currentUser = null;
let currentResultData = null;
let currentAssessmentId = null;
let appMode = 'patient'; // 'patient' or 'doctor'
let conversationalState = {};
let recognition = null;
let convRecognition = null;

// Initialize on load
document.addEventListener('DOMContentLoaded', () => {
  initAuth();
  loadModelCardInfo();
  initServiceWorker();
  runLiveSimulator(); // Initial simulator state
});

function initServiceWorker() {
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js')
      .then(() => console.log('ServiceWorker registered.'))
      .catch(err => console.warn('SW registration failed:', err));
  }
}

// -------------------------------------------------------------
// 1. Navigation & App Modes
// -------------------------------------------------------------
function switchTab(tabId) {
  document.querySelectorAll('.nav-tab-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.tab === tabId);
  });
  document.querySelectorAll('.tab-view').forEach(view => {
    view.classList.toggle('active', view.id === `tab-${tabId}`);
  });

  if (tabId === 'dashboard') {
    loadDashboardStats();
    loadAssessmentsList();
  } else if (tabId === 'trends') {
    loadTrends();
  }
}

function setAppMode(mode) {
  appMode = mode;
  const isDoc = mode === 'doctor';
  document.body.classList.toggle('doctor-mode', isDoc);
  document.getElementById('btn-mode-patient').classList.toggle('active', !isDoc);
  document.getElementById('btn-mode-doctor').classList.toggle('active', isDoc);

  const sub = document.getElementById('nav-mode-subtitle');
  if (sub) {
    sub.textContent = isDoc ? 'Clinical Diagnostic Decision Support' : 'Clinical Risk Stratification';
  }
  showToast(`Switched to ${isDoc ? 'Clinician / Doctor Mode' : 'Patient View'}`);
}

// -------------------------------------------------------------
// 2. Authentication Management (JWT)
// -------------------------------------------------------------
function getToken() {
  return localStorage.getItem('thyroscan_jwt_token');
}

function setToken(token) {
  if (token) localStorage.setItem('thyroscan_jwt_token', token);
  else localStorage.removeItem('thyroscan_jwt_token');
}

async function initAuth() {
  const token = getToken();
  if (!token) {
    updateAuthUI(null);
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/api/auth/me`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const data = await res.json();
    if (data.user) {
      currentUser = data.user;
      updateAuthUI(currentUser);
      loadDashboardStats();
      loadAssessmentsList();
    } else {
      setToken(null);
      updateAuthUI(null);
    }
  } catch (err) {
    console.error('Auth verification error:', err);
    updateAuthUI(null);
  }
}

function updateAuthUI(user) {
  const btnText = document.getElementById('user-name-display');
  const avatar = document.getElementById('user-avatar-text');
  const welcomeText = document.getElementById('welcome-user-text');

  if (user) {
    btnText.textContent = user.name;
    avatar.textContent = user.name.charAt(0).toUpperCase();
    if (welcomeText) welcomeText.textContent = `Welcome back, ${user.name} 👋`;
  } else {
    btnText.textContent = 'Sign In';
    avatar.textContent = '?';
    if (welcomeText) welcomeText.textContent = 'Welcome to ThyroScan 👋';
  }
}

function openAuthModal() {
  if (currentUser) {
    if (confirm(`Signed in as ${currentUser.name} (${currentUser.email}). Sign out?`)) {
      setToken(null);
      currentUser = null;
      updateAuthUI(null);
      showToast('Signed out successfully.');
      loadDashboardStats();
      loadAssessmentsList();
    }
    return;
  }
  document.getElementById('auth-modal').classList.add('active');
}

function closeAuthModal() {
  document.getElementById('auth-modal').classList.remove('active');
}

function toggleAuthTab(tab) {
  const isLogin = tab === 'login';
  document.getElementById('auth-tab-login').classList.toggle('active', isLogin);
  document.getElementById('auth-tab-register').classList.toggle('active', !isLogin);
  document.getElementById('auth-login-form').style.display = isLogin ? 'block' : 'none';
  document.getElementById('auth-register-form').style.display = !isLogin ? 'block' : 'none';
}

async function handleLogin() {
  const email = document.getElementById('login-email').value;
  const password = document.getElementById('login-pwd').value;

  try {
    const res = await fetch(`${API_BASE}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    const data = await res.json();
    if (data.error) throw new Error(data.error);

    setToken(data.token);
    currentUser = data.user;
    updateAuthUI(currentUser);
    closeAuthModal();
    showToast(`Welcome back, ${data.user.name}!`);
    loadDashboardStats();
    loadAssessmentsList();
  } catch (err) {
    showToast(`Sign in error: ${err.message}`);
  }
}

async function handleRegister() {
  const name = document.getElementById('reg-name').value;
  const email = document.getElementById('reg-email').value;
  const password = document.getElementById('reg-pwd').value;

  try {
    const res = await fetch(`${API_BASE}/api/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, email, password })
    });
    const data = await res.json();
    if (data.error) throw new Error(data.error);

    setToken(data.token);
    currentUser = data.user;
    updateAuthUI(currentUser);
    closeAuthModal();
    showToast('Account created successfully!');
    loadDashboardStats();
  } catch (err) {
    showToast(`Registration error: ${err.message}`);
  }
}

// -------------------------------------------------------------
// 3. Conversational Screening Assistant
// -------------------------------------------------------------
function toggleScreeningMethod(method) {
  const isConv = method === 'conversational';
  document.getElementById('btn-view-form-wizard').className = isConv ? 'btn-secondary' : 'btn-primary';
  document.getElementById('btn-view-conv-wizard').className = isConv ? 'btn-primary' : 'btn-secondary';
  document.getElementById('conversational-screening-container').style.display = isConv ? 'block' : 'none';
  document.getElementById('standard-wizard-container').style.display = isConv ? 'none' : 'block';
}

async function sendConversationalUtterance() {
  const input = document.getElementById('conv-user-utterance');
  const text = input.value.trim();
  if (!text) return;
  input.value = '';

  appendConvBubble('user', text);

  try {
    const res = await fetch(`${API_BASE}/api/conversational/extract`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, current_state: conversationalState })
    });
    const data = await res.json();
    conversationalState = data.state;

    // Update slots
    if (conversationalState.age) document.getElementById('slot-age').textContent = `${conversationalState.age} yrs`;
    if (conversationalState.sex !== undefined) document.getElementById('slot-sex').textContent = conversationalState.sex === 0 ? 'Female' : 'Male';
    if (conversationalState.TSH !== undefined) document.getElementById('slot-tsh').textContent = `${conversationalState.TSH} mIU/L`;
    if (conversationalState.T3 !== undefined) document.getElementById('slot-t3').textContent = `${conversationalState.T3} ng/mL`;
    if (conversationalState.TT4 !== undefined) document.getElementById('slot-tt4').textContent = `${conversationalState.TT4} ug/dL`;

    let flags = [];
    if (conversationalState.on_thyroxine) flags.push('On Levothyroxine');
    if (conversationalState.query_hypothyroid) flags.push('Hypothyroid symptoms');
    if (conversationalState.query_hyperthyroid) flags.push('Hyperthyroid symptoms');
    if (conversationalState.goitre) flags.push('Goitre');
    document.getElementById('slot-flags').textContent = flags.join(', ') || 'None';

    appendConvBubble('bot', data.assistant_reply);
    document.getElementById('btn-conv-execute').disabled = !data.is_ready_for_screening;
  } catch (err) {
    appendConvBubble('bot', 'Could not process message. Please try again.');
  }
}

function appendConvBubble(sender, text) {
  const box = document.getElementById('conv-chat-history');
  const bubble = document.createElement('div');
  bubble.className = `chat-msg ${sender}`;
  bubble.innerHTML = `<strong>${sender === 'user' ? 'You' : 'Assistant'}:</strong> ${text}`;
  box.appendChild(bubble);
  box.scrollTop = box.scrollHeight;
}

function toggleConversationalVoice() {
  if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
    showToast('Voice speech recognition not supported in browser.');
    return;
  }
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!convRecognition) {
    convRecognition = new SpeechRecognition();
    convRecognition.onstart = () => showToast('Listening... Speak your age, sex, and lab values.');
    convRecognition.onresult = (event) => {
      const text = event.results[0][0].transcript;
      document.getElementById('conv-user-utterance').value = text;
      sendConversationalUtterance();
    };
  }
  convRecognition.start();
}

function executeConversationalScreening() {
  // Transfer to wizard inputs and run
  if (conversationalState.age) document.getElementById('inp-age').value = conversationalState.age;
  if (conversationalState.sex !== undefined) document.getElementById('inp-sex').value = conversationalState.sex;
  if (conversationalState.TSH !== undefined) document.getElementById('inp-TSH').value = conversationalState.TSH;
  if (conversationalState.T3 !== undefined) document.getElementById('inp-T3').value = conversationalState.T3;
  if (conversationalState.TT4 !== undefined) document.getElementById('inp-TT4').value = conversationalState.TT4;

  toggleScreeningMethod('wizard');
  goToStep(4);
  submitScreening();
}

// -------------------------------------------------------------
// 4. Assessment Wizard Navigation & BMI Calculation
// -------------------------------------------------------------
function goToStep(stepNumber) {
  if (stepNumber > 1) {
    const age = document.getElementById('inp-age').value;
    const sex = document.getElementById('inp-sex').value;
    if (!age || !sex) {
      showToast('Please enter Patient Age and Sex before proceeding.');
      return;
    }
  }

  for (let i = 1; i <= 4; i++) {
    const node = document.getElementById(`step-node-${i}`);
    const content = document.getElementById(`form-step-${i}`);
    if (node) {
      node.classList.toggle('active', i === stepNumber);
      node.classList.toggle('completed', i < stepNumber);
    }
    if (content) content.classList.toggle('active', i === stepNumber);
  }
}

function calculateLiveBMI() {
  const h = parseFloat(document.getElementById('inp-height').value);
  const w = parseFloat(document.getElementById('inp-weight').value);
  const disp = document.getElementById('inp-bmi-disp');

  if (h > 0 && w > 0) {
    const h_m = h / 100.0;
    const bmi = (w / (h_m * h_m)).toFixed(1);
    let category = 'Normal';
    if (bmi < 18.5) category = 'Underweight';
    else if (bmi >= 25 && bmi < 30) category = 'Overweight';
    else if (bmi >= 30) category = 'Obese';
    disp.value = `${bmi} (${category})`;
  } else {
    disp.value = '';
  }
}

function loadSampleCase() {
  const samples = [
    { age: 62, sex: '0', height_cm: 162, weight_kg: 74, TSH: 18.4, T3: 0.7, TT4: 48, T4U: 1.15, FTI: 42, query_hypothyroid: true, goitre: true },
    { age: 34, sex: '1', height_cm: 176, weight_kg: 72, TSH: 1.85, T3: 1.4, TT4: 98, T4U: 1.02, FTI: 96 },
    { age: 29, sex: '0', height_cm: 165, weight_kg: 52, TSH: 0.02, T3: 4.8, TT4: 185, T4U: 0.88, FTI: 210, query_hyperthyroid: true }
  ];
  const s = samples[Math.floor(Math.random() * samples.length)];

  document.getElementById('inp-age').value = s.age;
  document.getElementById('inp-sex').value = s.sex;
  document.getElementById('inp-height').value = s.height_cm;
  document.getElementById('inp-weight').value = s.weight_kg;
  calculateLiveBMI();

  document.getElementById('inp-TSH').value = s.TSH;
  document.getElementById('inp-T3').value = s.T3;
  document.getElementById('inp-TT4').value = s.TT4;
  document.getElementById('inp-T4U').value = s.T4U;
  document.getElementById('inp-FTI').value = s.FTI;

  document.querySelectorAll('.flag-toggle-card input').forEach(cb => cb.checked = false);
  if (s.query_hypothyroid) document.querySelector('[name="query_hypothyroid"]').checked = true;
  if (s.query_hyperthyroid) document.querySelector('[name="query_hyperthyroid"]').checked = true;
  if (s.goitre) document.querySelector('[name="goitre"]').checked = true;

  showToast('Sample patient data loaded.');
}

function collectWizardInputs() {
  const age = parseFloat(document.getElementById('inp-age').value);
  const sex = parseInt(document.getElementById('inp-sex').value);
  const height_cm = parseFloat(document.getElementById('inp-height').value) || null;
  const weight_kg = parseFloat(document.getElementById('inp-weight').value) || null;

  let bmi = null;
  if (height_cm && weight_kg) {
    const h_m = height_cm / 100.0;
    bmi = parseFloat((weight_kg / (h_m * h_m)).toFixed(1));
  }

  const tsh = document.getElementById('inp-TSH').value;
  const t3 = document.getElementById('inp-T3').value;
  const tt4 = document.getElementById('inp-TT4').value;
  const t4u = document.getElementById('inp-T4U').value;
  const fti = document.getElementById('inp-FTI').value;

  const data = {
    age, sex, height_cm, weight_kg, bmi,
    TSH: tsh !== '' ? parseFloat(tsh) : null,
    T3: t3 !== '' ? parseFloat(t3) : null,
    TT4: tt4 !== '' ? parseFloat(tt4) : null,
    T4U: t4u !== '' ? parseFloat(t4u) : null,
    FTI: fti !== '' ? parseFloat(fti) : null,
    TSH_measured: tsh !== '' ? 1 : 0,
    T3_measured: t3 !== '' ? 1 : 0,
    TT4_measured: tt4 !== '' ? 1 : 0,
    T4U_measured: t4u !== '' ? 1 : 0,
    FTI_measured: fti !== '' ? 1 : 0,
  };

  const binaryFlags = [
    'on_thyroxine', 'on_antithyroid_medication', 'thyroid_surgery',
    'goitre', 'query_hypothyroid', 'query_hyperthyroid', 'I131_treatment',
    'pregnant', 'sick', 'lithium', 'tumor', 'psych'
  ];
  binaryFlags.forEach(f => {
    const el = document.querySelector(`[name="${f}"]`);
    data[f] = el && el.checked ? 1 : 0;
  });

  return data;
}

// -------------------------------------------------------------
// 5. Screening Submission & Ensemble Rendering
// -------------------------------------------------------------
async function submitScreening() {
  const btn = document.getElementById('btn-run-screening');
  btn.disabled = true;
  btn.textContent = 'Executing Multi-Model Ensemble...';

  try {
    const inputPayload = collectWizardInputs();
    const token = getToken();
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const res = await fetch(`${API_BASE}/api/predict`, {
      method: 'POST',
      headers,
      body: JSON.stringify(inputPayload)
    });

    const result = await res.json();
    if (result.error) throw new Error(result.error);

    currentResultData = result;
    currentResultData.inputs = inputPayload;
    currentAssessmentId = result.saved_assessment_id;

    renderScreeningResult(result);
    showToast('Ensemble screening completed.');
    loadDashboardStats();
  } catch (err) {
    showToast(`Screening error: ${err.message}`);
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<span>🔬</span> Execute AI Risk Analysis';
  }
}

function renderScreeningResult(res) {
  document.getElementById('screening-pre-submit').style.display = 'none';
  const resultDisplay = document.getElementById('screening-result-display');
  resultDisplay.style.display = 'block';

  // Result card header
  const cardBox = document.getElementById('res-card-box');
  cardBox.className = `result-header-card risk-${res.risk_level}`;
  document.getElementById('res-badge-title').textContent = res.badge;
  document.getElementById('res-prob-val').textContent = `${res.model_probability}%`;
  document.getElementById('res-summary-text').textContent = res.summary;

  // Ensemble Agreement Matrix
  const ens = res.ensemble || {};
  document.getElementById('res-consensus-score').textContent = ens.consensus_score ? `${ens.consensus_score} Models Agree` : '3/3 Unanimous';
  const ensRows = document.getElementById('res-ensemble-rows');
  ensRows.innerHTML = '';
  Object.entries(ens.individual_models || {}).forEach(([mName, mInfo]) => {
    const r = document.createElement('div');
    r.className = 'ensemble-row';
    r.innerHTML = `
      <div>
        <strong>${mName}</strong> <span style="font-size:11px; color:var(--text-muted);">(${mInfo.model_type})</span>
      </div>
      <div style="display:flex; align-items:center; gap:8px;">
        <span class="status-pill ${mInfo.prediction === 'negative' ? 'normal' : 'high'}">${mInfo.prediction_badge}</span>
        <strong>${mInfo.confidence}%</strong>
      </div>
    `;
    ensRows.appendChild(r);
  });

  const disAlert = document.getElementById('res-disagreement-alert');
  if (ens.has_disagreement && ens.disagreement_warning) {
    disAlert.style.display = 'block';
    disAlert.textContent = ens.disagreement_warning;
  } else {
    disAlert.style.display = 'none';
  }

  // Biomarkers table
  const bioTbody = document.getElementById('res-biomarkers-tbody');
  bioTbody.innerHTML = '';
  if (res.biomarker_analysis && res.biomarker_analysis.length > 0) {
    res.biomarker_analysis.forEach(bio => {
      const pillClass = bio.status === 'normal' ? 'normal' : ('low' in bio.status ? 'low' : 'high');
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><strong>${bio.name}</strong> (${bio.code})</td>
        <td><strong>${bio.value}</strong> ${bio.unit}</td>
        <td>${bio.ref_min} – ${bio.ref_max} ${bio.unit}</td>
        <td><span class="status-pill ${pillClass}">${bio.status_label}</span></td>
      `;
      bioTbody.appendChild(tr);
    });
  } else {
    bioTbody.innerHTML = '<tr><td colspan="4" style="text-align:center; color:var(--text-muted);">No blood test biomarkers provided. Analysis based on symptoms and demographics.</td></tr>';
  }

  // Feature attributions
  const inflBox = document.getElementById('res-influences-box');
  inflBox.innerHTML = '';
  (res.feature_influences || []).forEach(item => {
    const div = document.createElement('div');
    div.innerHTML = `
      <div style="display:flex; justify-content:space-between; font-size:13px;">
        <span><strong>${item.feature}</strong></span>
        <span style="color:var(--accent-cyan); font-weight:600;">${item.direction}</span>
      </div>
      <div class="influence-bar-wrap">
        <div class="influence-bar-fill" style="width:${item.influence_pct}%"></div>
      </div>
    `;
    inflBox.appendChild(div);
  });

  // Probability distribution
  const probBox = document.getElementById('res-prob-distribution-box');
  probBox.innerHTML = '';
  const labelMap = {
    negative: 'Low Risk (Normal)',
    hypothyroid: 'Hypothyroidism',
    hyperthyroid: 'Hyperthyroidism',
    subclinical_hypothyroid: 'Subclinical Hypo',
    subclinical_hyperthyroid: 'Subclinical Hyper'
  };
  Object.entries(res.class_probabilities || {}).forEach(([cls, pct]) => {
    const div = document.createElement('div');
    div.innerHTML = `
      <div style="display:flex; justify-content:space-between; font-size:12.5px; margin-bottom:2px;">
        <span>${labelMap[cls] || cls}</span>
        <strong>${pct}%</strong>
      </div>
      <div class="influence-bar-wrap" style="height:6px;">
        <div class="influence-bar-fill" style="width:${pct}%; background:${pct > 40 ? 'var(--accent-cyan)' : 'rgba(255,255,255,0.2)'};"></div>
      </div>
    `;
    probBox.appendChild(div);
  });

  // Action plan
  const planList = document.getElementById('res-action-plan-list');
  planList.innerHTML = '';
  (res.action_plan || []).forEach(item => {
    const li = document.createElement('li');
    li.textContent = item;
    planList.appendChild(li);
  });

  resultDisplay.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function resetScreeningWizard() {
  document.getElementById('screening-wizard-form').reset();
  document.getElementById('screening-pre-submit').style.display = 'block';
  document.getElementById('screening-result-display').style.display = 'none';
  goToStep(1);
}

// -------------------------------------------------------------
// 6. Doctor Mode & SOAP Notes
// -------------------------------------------------------------
async function generateAndShowDoctorSOAP() {
  if (!currentAssessmentId && !currentResultData) {
    showToast('No active screening result available.');
    return;
  }

  const modal = document.getElementById('doctor-soap-modal');
  const soapDisplay = document.getElementById('doctor-soap-text');
  modal.classList.add('active');
  soapDisplay.textContent = 'Generating structured clinical SOAP summary...';

  try {
    if (currentAssessmentId) {
      const res = await fetch(`${API_BASE}/api/doctor/summary/${currentAssessmentId}`);
      const data = await res.json();
      soapDisplay.textContent = data.ehr_soap_text;
    } else {
      // Local synthesis
      const inp = currentResultData.inputs || {};
      const note = `CLINICAL SCREENING CONSULT NOTE (Preview)
Date: ${new Date().toISOString().slice(0, 10)}
Patient: Anonymous | Age: ${inp.age || 38} | Sex: ${inp.sex === 0 ? 'Female' : 'Male'}
------------------------------------------------------------------------
[S] SUBJECTIVE:
- Patient completed self-guided AI clinical screening.

[O] OBJECTIVE BIOMARKERS:
- TSH: ${inp.TSH || 'N/A'} mIU/L | T3: ${inp.T3 || 'N/A'} | TT4: ${inp.TT4 || 'N/A'}

[A] ASSESSMENT:
- AI Risk Signal: ${currentResultData.badge} (${currentResultData.model_probability}% Calibrated Probability).

[P] PLAN:
- Verify with confirmatory laboratory assay (Free T4 / Total T3).
- Review medication status and repeat panel in 6-12 weeks.
`;
      soapDisplay.textContent = note;
    }
  } catch (err) {
    soapDisplay.textContent = `Error generating clinical note: ${err.message}`;
  }
}

function closeDoctorSoapModal() {
  document.getElementById('doctor-soap-modal').classList.remove('active');
}

function copyDoctorSOAPNote() {
  const txt = document.getElementById('doctor-soap-text').textContent;
  navigator.clipboard.writeText(txt).then(() => showToast('SOAP note copied to clipboard!'));
}

// -------------------------------------------------------------
// 7. Interactive "What-If" Biomarker Simulator
// -------------------------------------------------------------
let simDebounceTimer = null;
function runLiveSimulator() {
  const tsh = parseFloat(document.getElementById('sim-tsh').value);
  const t3 = parseFloat(document.getElementById('sim-t3').value);
  const tt4 = parseFloat(document.getElementById('sim-tt4').value);
  const age = parseInt(document.getElementById('sim-age').value);
  const onThyr = document.getElementById('sim-thyroxine').checked ? 1 : 0;

  document.getElementById('sim-disp-tsh').textContent = tsh.toFixed(2);
  document.getElementById('sim-disp-t3').textContent = t3.toFixed(2);
  document.getElementById('sim-disp-tt4').textContent = tt4.toFixed(1);
  document.getElementById('sim-disp-age').textContent = age;

  clearTimeout(simDebounceTimer);
  simDebounceTimer = setTimeout(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/simulator/simulate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          TSH: tsh, T3: t3, TT4: tt4, age,
          on_thyroxine: onThyr,
          TSH_measured: 1, T3_measured: 1, TT4_measured: 1
        })
      });
      const data = await res.json();
      renderSimResult(data);
    } catch (err) {
      console.warn('Simulation error:', err);
    }
  }, 100);
}

function renderSimResult(data) {
  const box = document.getElementById('sim-card-box');
  box.className = `result-header-card risk-${data.risk_level}`;
  document.getElementById('sim-badge-title').textContent = data.badge;
  document.getElementById('sim-prob-val').textContent = `${data.model_probability}%`;
  document.getElementById('sim-summary-text').textContent = data.summary;

  const probsDiv = document.getElementById('sim-probs-distribution');
  probsDiv.innerHTML = '';
  const labelMap = {
    negative: 'Normal Euthyroid',
    hypothyroid: 'Hypothyroidism',
    hyperthyroid: 'Hyperthyroidism',
    subclinical_hypothyroid: 'Subclinical Hypo',
    subclinical_hyperthyroid: 'Subclinical Hyper'
  };
  Object.entries(data.class_probabilities || {}).forEach(([cls, pct]) => {
    const d = document.createElement('div');
    d.innerHTML = `
      <div style="display:flex; justify-content:space-between; font-size:12px; margin-bottom:2px;">
        <span>${labelMap[cls] || cls}</span>
        <strong>${pct}%</strong>
      </div>
      <div class="influence-bar-wrap" style="height:5px;">
        <div class="influence-bar-fill" style="width:${pct}%; background:${pct > 40 ? 'var(--accent-cyan)' : 'rgba(255,255,255,0.2)'};"></div>
      </div>
    `;
    probsDiv.appendChild(d);
  });
}

// -------------------------------------------------------------
// 8. AI Lab Report Comparison (Report A vs Report B)
// -------------------------------------------------------------
async function executeLabReportComparison() {
  const reportA = {
    date: document.getElementById('comp-date-a').value,
    TSH: parseFloat(document.getElementById('comp-tsh-a').value),
    T3: parseFloat(document.getElementById('comp-t3-a').value),
    TT4: parseFloat(document.getElementById('comp-tt4-a').value)
  };
  const reportB = {
    date: document.getElementById('comp-date-b').value,
    TSH: parseFloat(document.getElementById('comp-tsh-b').value),
    T3: parseFloat(document.getElementById('comp-t3-b').value),
    TT4: parseFloat(document.getElementById('comp-tt4-b').value)
  };

  try {
    const res = await fetch(`${API_BASE}/api/lab-report/compare`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ report_a: reportA, report_b: reportB })
    });
    const data = await res.json();
    if (data.error) throw new Error(data.error);

    renderComparisonResults(data);
    showToast('Lab report comparison calculated.');
  } catch (err) {
    showToast(`Comparison error: ${err.message}`);
  }
}

function renderComparisonResults(data) {
  const card = document.getElementById('comp-results-card');
  card.style.display = 'block';

  document.getElementById('comp-trajectory-badge').textContent = data.trajectory;
  document.getElementById('comp-synthesis-text').textContent = data.synthesis;

  const tbody = document.getElementById('comp-table-tbody');
  tbody.innerHTML = '';
  data.comparisons.forEach(c => {
    const tr = document.createElement('tr');
    const badgeClass = c.direction;
    const sign = c.pct_change > 0 ? '+' : '';
    tr.innerHTML = `
      <td><strong>${c.name}</strong></td>
      <td>${c.baseline_val} ${c.unit}</td>
      <td>${c.followup_val} ${c.unit}</td>
      <td>${c.diff > 0 ? '+' : ''}${c.diff} ${c.unit}</td>
      <td><span class="delta-badge ${badgeClass}">${sign}${c.pct_change}%</span></td>
    `;
    tbody.appendChild(tr);
  });

  const qList = document.getElementById('comp-questions-list');
  qList.innerHTML = '';
  (data.suggested_doctor_questions || []).forEach(q => {
    const li = document.createElement('li');
    li.textContent = q;
    qList.appendChild(li);
  });

  card.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// -------------------------------------------------------------
// 9. PDF Medical Report Download
// -------------------------------------------------------------
async function downloadCurrentResultPDF() {
  if (currentAssessmentId) {
    window.open(`${API_BASE}/api/reports/${currentAssessmentId}/pdf`, '_blank');
    return;
  }

  if (currentResultData) {
    try {
      showToast('Generating PDF Report...');
      const res = await fetch(`${API_BASE}/api/reports/preview/pdf`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(currentResultData)
      });
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `ThyroScan_Screening_Report_${Date.now()}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (err) {
      showToast(`Failed to generate PDF: ${err.message}`);
    }
  }
}

// -------------------------------------------------------------
// 10. Lab Report OCR & Verification
// -------------------------------------------------------------
async function handleOCRFileUpload(file) {
  if (!file) return;

  const loading = document.getElementById('ocr-loading');
  loading.style.display = 'block';

  const formData = new FormData();
  formData.append('file', file);

  try {
    const res = await fetch(`${API_BASE}/api/lab-report/extract`, {
      method: 'POST',
      body: formData
    });
    const data = await res.json();
    if (data.error) throw new Error(data.error);

    const ext = data.extracted;
    if (ext.TSH !== null) document.getElementById('ocr-val-tsh').value = ext.TSH;
    if (ext.T3 !== null) document.getElementById('ocr-val-t3').value = ext.T3;
    if (ext.TT4 !== null) document.getElementById('ocr-val-tt4').value = ext.TT4;
    if (ext.age !== null) document.getElementById('ocr-val-age').value = ext.age;

    document.getElementById('ocr-text-snippet').innerHTML = `
      <strong>Extracted from: ${data.filename} (${data.found_count} parameters found)</strong><br/>
      <pre style="margin-top:6px; white-space:pre-wrap; font-family:monospace; font-size:11px;">${data.preview_snippet}</pre>
    `;

    document.getElementById('btn-apply-ocr-values').disabled = false;
    showToast('Lab values extracted. Please verify before continuing.');
  } catch (err) {
    showToast(`OCR error: ${err.message}`);
  } finally {
    loading.style.display = 'none';
  }
}

function applyOCRToWizard() {
  const tsh = document.getElementById('ocr-val-tsh').value;
  const t3 = document.getElementById('ocr-val-t3').value;
  const tt4 = document.getElementById('ocr-val-tt4').value;
  const age = document.getElementById('ocr-val-age').value;

  if (age) document.getElementById('inp-age').value = age;
  if (tsh) document.getElementById('inp-TSH').value = tsh;
  if (t3) document.getElementById('inp-T3').value = t3;
  if (tt4) document.getElementById('inp-TT4').value = tt4;

  switchTab('assess');
  goToStep(2);
  showToast('Verified biomarkers transferred to screening wizard!');
}

// -------------------------------------------------------------
// 11. Context-Aware ThyroBot AI Copilot
// -------------------------------------------------------------
async function sendChatMessage(customMsg) {
  const input = document.getElementById('chat-user-input');
  const msg = customMsg || input.value.trim();
  if (!msg) return;

  if (!customMsg) input.value = '';
  appendChatBubble('user', msg);

  try {
    const token = getToken();
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const res = await fetch(`${API_BASE}/api/chat`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ message: msg })
    });
    const data = await res.json();
    if (data.error) throw new Error(data.error);

    appendChatBubble('bot', data.message, data.citations, data.is_emergency);
  } catch (err) {
    appendChatBubble('bot', `Assistant connection error: ${err.message}`);
  }
}

function appendChatBubble(sender, text, citations = [], isEmergency = false) {
  const chatList = document.getElementById('chat-msg-list');
  const bubble = document.createElement('div');
  bubble.className = `chat-msg ${sender} ${isEmergency ? 'emergency' : ''}`;

  let contentHtml = text.replace(/\n/g, '<br/>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  bubble.innerHTML = `<strong>${sender === 'user' ? 'You' : 'ThyroBot AI'}:</strong><br/>${contentHtml}`;

  if (citations && citations.length > 0) {
    const citeBox = document.createElement('div');
    citeBox.className = 'citation-chip-box';
    citations.forEach(c => {
      const span = document.createElement('span');
      span.className = 'citation-chip';
      span.textContent = `${c.source}: ${c.topic}`;
      citeBox.appendChild(span);
    });
    bubble.appendChild(citeBox);
  }

  chatList.appendChild(bubble);
  chatList.scrollTop = chatList.scrollHeight;
}

function askSampleQuestion(q) {
  sendChatMessage(q);
}

function askThyroBotAboutResult() {
  switchTab('thyrobot');
  if (currentResultData) {
    const prompt = `Can you explain what my ${currentResultData.badge} screening result and biomarker values mean for my daily health?`;
    sendChatMessage(prompt);
  }
}

function toggleVoiceRecognition() {
  if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
    showToast('Speech recognition not supported in this browser.');
    return;
  }

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!recognition) {
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.lang = 'en-US';

    recognition.onstart = () => {
      document.getElementById('btn-voice-input').style.background = '#ef4444';
      showToast('Listening... Speak now.');
    };

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      document.getElementById('chat-user-input').value = transcript;
      sendChatMessage(transcript);
    };

    recognition.onend = () => {
      document.getElementById('btn-voice-input').style.background = '';
    };
  }

  recognition.start();
}

// -------------------------------------------------------------
// 12. Health Trends & History
// -------------------------------------------------------------
async function loadTrends() {
  const token = getToken();
  if (!token) {
    document.getElementById('trends-chart-container').innerHTML = `
      <div style="text-align:center; padding:30px;">
        <p style="margin-bottom:12px; color:var(--text-secondary);">Please sign in to view your longitudinal health biomarker trends.</p>
        <button class="btn-primary" onclick="openAuthModal()">Sign In / Register</button>
      </div>
    `;
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/api/trends`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const data = await res.json();
    renderTrendsChart(data.trends || []);
    loadAssessmentsList();
  } catch (err) {
    console.error('Trends error:', err);
  }
}

function renderTrendsChart(points) {
  const container = document.getElementById('trends-chart-container');
  if (!points || points.length === 0) {
    container.innerHTML = '<span style="color:var(--text-muted);">No assessments recorded yet. Run a screening to start tracking trends.</span>';
    return;
  }

  const validPoints = points.filter(p => p.TSH !== null && p.TSH !== undefined);
  if (validPoints.length === 0) {
    container.innerHTML = '<span>No numeric TSH values recorded in past screenings.</span>';
    return;
  }

  let html = `<div style="width:100%;"><h4 style="font-size:13.5px; margin-bottom:8px; color:var(--accent-cyan);">TSH Progression (mIU/L) — Ref: 0.45 – 4.5</h4><div style="display:flex; align-items:flex-end; gap:24px; height:150px; padding:10px 0; border-bottom:1px solid var(--border-color);">`;
  validPoints.forEach(pt => {
    const heightPct = Math.min(100, Math.max(15, (pt.TSH / 10.0) * 100));
    const isNormal = pt.TSH >= 0.45 && pt.TSH <= 4.5;
    const barColor = isNormal ? 'var(--risk-low)' : 'var(--risk-high)';
    html += `
      <div style="display:flex; flex-direction:column; align-items:center; gap:6px;">
        <span style="font-size:11px; font-weight:700;">${pt.TSH}</span>
        <div style="width:28px; height:${heightPct}px; background:${barColor}; border-radius:4px;"></div>
        <span style="font-size:10px; color:var(--text-muted);">${pt.date}</span>
      </div>
    `;
  });
  html += `</div></div>`;
  container.innerHTML = html;
}

async function loadAssessmentsList() {
  const token = getToken();
  if (!token) return;

  try {
    const res = await fetch(`${API_BASE}/api/assessments`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const data = await res.json();
    const list = data.assessments || [];

    const dashTbody = document.getElementById('dashboard-recent-tbody');
    if (dashTbody) {
      if (list.length === 0) {
        dashTbody.innerHTML = '<tr><td colspan="5" style="text-align:center; color:var(--text-muted); padding:20px;">No assessment history. Run your first screening.</td></tr>';
      } else {
        dashTbody.innerHTML = '';
        list.slice(0, 5).forEach(item => {
          const pillClass = item.risk_level === 'low' ? 'normal' : (item.risk_level === 'moderate' ? 'low' : 'high');
          const tr = document.createElement('tr');
          tr.innerHTML = `
            <td>${item.created_at.slice(0, 10)}</td>
            <td><span class="status-pill ${pillClass}">${item.screening_result.replace('_', ' ').toUpperCase()}</span></td>
            <td><strong>${item.model_probability}%</strong></td>
            <td>${item.assessment_type}</td>
            <td>
              <a href="${API_BASE}/api/reports/${item.id}/pdf" target="_blank" class="btn-secondary" style="padding:4px 8px; font-size:11px;">PDF Report</a>
            </td>
          `;
          dashTbody.appendChild(tr);
        });
      }
    }

    const trendsTbody = document.getElementById('trends-history-tbody');
    if (trendsTbody) {
      if (list.length === 0) {
        trendsTbody.innerHTML = '<tr><td colspan="8" style="text-align:center; color:var(--text-muted); padding:20px;">No historical records available.</td></tr>';
      } else {
        trendsTbody.innerHTML = '';
        list.forEach(item => {
          const inputs = item.inputs || {};
          const pillClass = item.risk_level === 'low' ? 'normal' : (item.risk_level === 'moderate' ? 'low' : 'high');
          const tr = document.createElement('tr');
          tr.innerHTML = `
            <td>${item.created_at.slice(0, 10)}</td>
            <td><span class="status-pill ${pillClass}">${item.screening_result.replace('_', ' ').toUpperCase()}</span></td>
            <td>${item.model_probability}%</td>
            <td>${inputs.TSH !== undefined && inputs.TSH !== null ? inputs.TSH : '--'}</td>
            <td>${inputs.T3 !== undefined && inputs.T3 !== null ? inputs.T3 : '--'}</td>
            <td>${inputs.TT4 !== undefined && inputs.TT4 !== null ? inputs.TT4 : '--'}</td>
            <td>
              <a href="${API_BASE}/api/reports/${item.id}/pdf" target="_blank" class="btn-secondary" style="padding:4px 8px; font-size:11px;">PDF</a>
            </td>
            <td>
              <button onclick="deleteAssessmentRecord(${item.id})" class="btn-danger-outline" style="padding:3px 6px; font-size:11px;">Delete</button>
            </td>
          `;
          trendsTbody.appendChild(tr);
        });
      }
    }
  } catch (err) {
    console.error('Assessments loading error:', err);
  }
}

async function deleteAssessmentRecord(id) {
  if (!confirm('Delete this screening record?')) return;
  const token = getToken();
  try {
    await fetch(`${API_BASE}/api/assessments/${id}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token}` }
    });
    showToast('Record deleted.');
    loadAssessmentsList();
    loadDashboardStats();
  } catch (err) {
    showToast('Failed to delete record.');
  }
}

// -------------------------------------------------------------
// 13. Dashboard Stats Refresh & Model Metadata
// -------------------------------------------------------------
async function loadDashboardStats() {
  const token = getToken();
  if (!token) {
    document.getElementById('stat-latest-result').textContent = 'No Data';
    document.getElementById('stat-latest-prob').textContent = '-- %';
    document.getElementById('stat-user-bmi').textContent = '--';
    document.getElementById('stat-total-screenings').textContent = '0';
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/api/assessments`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const data = await res.json();
    const list = data.assessments || [];

    document.getElementById('stat-total-screenings').textContent = list.length;
    if (list.length > 0) {
      const latest = list[0];
      document.getElementById('stat-latest-result').textContent = latest.screening_result.replace('_', ' ').toUpperCase();
      document.getElementById('stat-latest-prob').textContent = `${latest.model_probability}%`;
      
      const bannerTitle = document.getElementById('dash-banner-title');
      const bannerDesc = document.getElementById('dash-banner-desc');
      if (bannerTitle) bannerTitle.textContent = `Latest Record: ${latest.screening_result.replace('_', ' ').toUpperCase()} Signal (${latest.model_probability}% Probability)`;
      if (bannerDesc) bannerDesc.textContent = `Assessed on ${latest.created_at.slice(0, 10)}. Run a new assessment or compare lab tests.`;
    }

    if (currentUser && currentUser.profile && currentUser.profile.bmi) {
      document.getElementById('stat-user-bmi').textContent = currentUser.profile.bmi;
    }
  } catch (err) {
    console.error('Stats loading error:', err);
  }
}

async function loadModelCardInfo() {
  try {
    const res = await fetch(`${API_BASE}/api/model-info`);
    const data = await res.json();
    console.log('Model Registry Loaded:', data);
  } catch (err) {
    console.warn('Model card loading error:', err);
  }
}

// -------------------------------------------------------------
// 14. Toast Notification
// -------------------------------------------------------------
function showToast(msg) {
  const existing = document.querySelector('.app-toast');
  if (existing) existing.remove();

  const toast = document.createElement('div');
  toast.className = 'app-toast';
  toast.textContent = msg;
  document.body.appendChild(toast);

  setTimeout(() => toast.remove(), 3500);
}
