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
  } else if (tabId === 'modellab') {
    loadModelLabBenchmarks();
  } else if (tabId === 'ultrasound') {
    initUltrasoundStudio();
  } else if (tabId === 'trajectory') {
    initTrajectoryTracker();
  } else if (tabId === 'explainability') {
    initExplainabilityStudio();
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
  loadModelLabBenchmarks();
}

// -------------------------------------------------------------
// 14. Model Laboratory & Diagnostic Tournament Engine
// -------------------------------------------------------------
async function loadModelLabBenchmarks() {
  const tbody = document.getElementById('lab-benchmarks-tbody');
  if (!tbody) return;

  try {
    const res = await fetch(`${API_BASE}/api/model-lab/benchmarks`);
    const data = await res.json();

    if (!data || !data.leaderboard || Object.keys(data.leaderboard).length === 0) {
      tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; padding:20px; color:var(--text-muted);">Model benchmarks are initializing. Click Run Tournament above.</td></tr>';
      return;
    }

    tbody.innerHTML = '';
    const champion = data.champion_model || '';

    for (const [modelName, meta] of Object.entries(data.leaderboard)) {
      const isChamp = (modelName === champion);
      const tr = document.createElement('tr');
      if (isChamp) tr.style.background = 'rgba(56, 189, 248, 0.08)';

      const champBadge = isChamp ? ' <span class="status-pill normal" style="font-size:10.5px; padding:2px 6px;">Champion 🏆</span>' : '';

      tr.innerHTML = `
        <td><strong>${modelName}</strong>${champBadge}</td>
        <td><span style="font-size:12px; color:var(--text-secondary);">${meta.model_type || 'Classifier'}</span></td>
        <td><strong>${meta.accuracy ? meta.accuracy.toFixed(2) + '%' : 'N/A'}</strong></td>
        <td>${meta.balanced_accuracy ? meta.balanced_accuracy.toFixed(2) + '%' : 'N/A'}</td>
        <td>${meta.macro_f1 ? meta.macro_f1.toFixed(2) + '%' : 'N/A'}</td>
        <td><span style="color:#38bdf8; font-weight:700;">${meta.roc_auc ? meta.roc_auc.toFixed(2) + '%' : 'N/A'}</span></td>
        <td>${meta.ece !== undefined ? meta.ece.toFixed(4) : 'N/A'}</td>
        <td>${meta.brier_score !== undefined ? meta.brier_score.toFixed(4) : 'N/A'}</td>
      `;
      tbody.appendChild(tr);
    }
  } catch (err) {
    console.error('Error loading Model Lab benchmarks:', err);
    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; padding:20px; color:var(--risk-high);">Could not load model benchmarks.</td></tr>';
  }
}

function loadLabPreset(preset) {
  const presets = {
    normal: { tsh: 2.1, t3: 2.3, tt4: 105.0, t4u: 1.01, fti: 104.0, age: 42, sex: 'F', thyroxine: 'f' },
    sub_hypo: { tsh: 7.8, t3: 2.0, tt4: 98.0, t4u: 1.05, fti: 93.3, age: 54, sex: 'F', thyroxine: 'f' },
    overt_hypo: { tsh: 28.5, t3: 0.8, tt4: 38.0, t4u: 1.25, fti: 30.4, age: 62, sex: 'F', thyroxine: 'f' },
    sub_hyper: { tsh: 0.08, t3: 3.4, tt4: 135.0, t4u: 0.92, fti: 146.7, age: 38, sex: 'M', thyroxine: 'f' },
    outlier: { tsh: 65.0, t3: 8.5, tt4: 260.0, t4u: 0.40, fti: 650.0, age: 88, sex: 'M', thyroxine: 't' }
  };

  const p = presets[preset];
  if (!p) return;

  document.getElementById('lab-input-tsh').value = p.tsh;
  document.getElementById('lab-input-t3').value = p.t3;
  document.getElementById('lab-input-tt4').value = p.tt4;
  document.getElementById('lab-input-t4u').value = p.t4u;
  document.getElementById('lab-input-fti').value = p.fti;
  document.getElementById('lab-input-age').value = p.age;
  document.getElementById('lab-input-sex').value = p.sex;
  document.getElementById('lab-input-thyroxine').value = p.thyroxine;

  showToast(`Loaded Preset: ${preset.replace('_', ' ').toUpperCase()}`);
}

async function runLaboratoryTournament() {
  const btn = document.getElementById('btn-run-tournament');
  const resultsWrap = document.getElementById('lab-tournament-results');

  const inputPayload = {
    TSH: parseFloat(document.getElementById('lab-input-tsh').value) || null,
    T3: parseFloat(document.getElementById('lab-input-t3').value) || null,
    TT4: parseFloat(document.getElementById('lab-input-tt4').value) || null,
    T4U: parseFloat(document.getElementById('lab-input-t4u').value) || null,
    FTI: parseFloat(document.getElementById('lab-input-fti').value) || null,
    age: parseInt(document.getElementById('lab-input-age').value) || 45,
    sex: document.getElementById('lab-input-sex').value || 'F',
    on_thyroxine: document.getElementById('lab-input-thyroxine').value || 'f'
  };

  // Set default measurement flags
  inputPayload.TSH_measured = inputPayload.TSH !== null ? 1 : 0;
  inputPayload.T3_measured = inputPayload.T3 !== null ? 1 : 0;
  inputPayload.TT4_measured = inputPayload.TT4 !== null ? 1 : 0;
  inputPayload.T4U_measured = inputPayload.T4U !== null ? 1 : 0;
  inputPayload.FTI_measured = inputPayload.FTI !== null ? 1 : 0;

  btn.disabled = true;
  btn.textContent = '⏳ Executing 8 Model Families in Parallel...';

  try {
    const res = await fetch(`${API_BASE}/api/model-lab/predict-all`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(inputPayload)
    });

    const data = await res.json();
    if (data.error) {
      showToast(`Error: ${data.error}`);
      return;
    }

    resultsWrap.style.display = 'block';

    // 1. Champion Consensus Card
    const champDiag = document.getElementById('lab-champion-diagnosis');
    const champConf = document.getElementById('lab-champion-conf');
    const consensusScore = document.getElementById('lab-consensus-score');
    const disagBox = document.getElementById('lab-disagreement-box');

    champDiag.textContent = data.champion_prediction_badge || 'Negative';
    champConf.textContent = `Calibrated Probability: ${data.champion_confidence}% (Consensus: ${data.consensus_pct}%)`;
    consensusScore.textContent = `${data.consensus_score} Models Agree`;

    if (data.has_split_opinion && data.split_opinion_warning) {
      disagBox.style.display = 'block';
      disagBox.textContent = data.split_opinion_warning;
    } else {
      disagBox.style.display = 'none';
    }

    // 2. Autoencoder Anomaly Card
    const ae = data.anomaly_screening || {};
    const aeCard = document.getElementById('lab-autoencoder-card');
    const aeBadge = document.getElementById('lab-ae-badge');
    const aeScoreTxt = document.getElementById('lab-ae-score-txt');
    const aeStatusTitle = document.getElementById('lab-ae-status-title');
    const aeGuidanceTxt = document.getElementById('lab-ae-guidance-txt');
    const aeDeviations = document.getElementById('lab-ae-deviations');

    if (ae.available) {
      aeScoreTxt.textContent = `Recon MSE: ${ae.anomaly_score} (Cutoff: ${ae.anomaly_threshold})`;
      aeStatusTitle.textContent = ae.clinical_status;
      aeGuidanceTxt.textContent = ae.clinical_guidance;

      if (ae.is_anomaly) {
        aeCard.style.borderColor = '#ef4444';
        aeBadge.style.background = 'rgba(239, 68, 68, 0.2)';
        aeBadge.style.color = '#ef4444';
        aeBadge.textContent = '🚨 Physiological Anomaly Flagged';
      } else {
        aeCard.style.borderColor = '#10b981';
        aeBadge.style.background = 'rgba(16, 185, 129, 0.15)';
        aeBadge.style.color = '#10b981';
        aeBadge.textContent = '✔ Standard Physiological Distribution';
      }

      if (ae.top_deviating_biomarkers && ae.top_deviating_biomarkers.length > 0) {
        let devHtml = '<div style="margin-top:8px; border-top:1px solid rgba(255,255,255,0.08); padding-top:6px;"><strong>Biomarker Reconstruction Attribution:</strong><br>';
        ae.top_deviating_biomarkers.forEach(b => {
          devHtml += `<span style="display:inline-block; margin-right:12px; margin-top:3px;">• <code>${b.biomarker}</code> = ${b.input_value} (Dev: ${b.reconstruction_error})</span>`;
        });
        devHtml += '</div>';
        aeDeviations.innerHTML = devHtml;
      } else {
        aeDeviations.innerHTML = '';
      }
    }

    // 3. 8-Model Battle Cards Grid
    const cardsGrid = document.getElementById('lab-model-cards-grid');
    cardsGrid.innerHTML = '';

    const modelsObj = data.individual_models || {};
    for (const [mName, mData] of Object.entries(modelsObj)) {
      const card = document.createElement('div');
      card.className = 'glass-card';
      card.style.padding = '14px';
      card.style.background = 'rgba(30, 41, 59, 0.7)';

      const isAgree = (mData.prediction === data.champion_prediction);
      const borderClr = isAgree ? 'rgba(56, 189, 248, 0.4)' : 'rgba(245, 158, 11, 0.4)';
      card.style.border = `1px solid ${borderClr}`;

      card.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
          <strong style="font-size:14px; color:#ffffff;">${mName}</strong>
          <span class="status-pill normal" style="font-size:10px; padding:2px 6px;">${mData.model_badge || 'Classifier'}</span>
        </div>
        <div style="margin-bottom:10px;">
          <div style="font-size:16px; font-weight:800; color:${isAgree ? '#38bdf8' : '#f59e0b'};">
            ${mData.prediction_badge || 'N/A'}
          </div>
          <div style="font-size:12px; color:var(--text-muted); margin-top:2px;">
            Confidence: <strong>${mData.confidence}%</strong> (Hist. Acc: ${mData.historical_accuracy || 'N/A'})
          </div>
        </div>
        <div style="background:rgba(255,255,255,0.08); height:6px; border-radius:3px; overflow:hidden;">
          <div style="width:${mData.confidence}%; height:100%; background:${isAgree ? '#38bdf8' : '#f59e0b'};"></div>
        </div>
      `;
      cardsGrid.appendChild(card);
    }

    // Refresh benchmarks table
    loadModelLabBenchmarks();
    showToast('Model Tournament Completed!');
    resultsWrap.scrollIntoView({ behavior: 'smooth', block: 'start' });

  } catch (err) {
    console.error('Tournament execution error:', err);
    showToast('Failed to run tournament inference.');
  } finally {
    btn.disabled = false;
    btn.textContent = '🚀 Run Model Tournament & Anomaly Screening';
  }
}



// -------------------------------------------------------------
// 14. Phase 2: Multimodal Ultrasound AI & ACR TI-RADS Studio
// -------------------------------------------------------------
let currentUltrasoundData = null;
let currentUltrasoundRawB64 = null;
let currentUltrasoundOverlayB64 = null;
let showingOverlay = true;

const ULTRASOUND_PRESETS = {
  'tr1_benign_cyst': {
    composition: 'cystic', echogenicity: 'anechoic', shape: 'wider_than_tall',
    margin: 'smooth', foci: 'none', size: 1.6
  },
  'tr3_follicular_adenoma': {
    composition: 'solid', echogenicity: 'isoechoic', shape: 'wider_than_tall',
    margin: 'smooth', foci: 'none', size: 2.1
  },
  'tr4_suspicious_nodule': {
    composition: 'solid', echogenicity: 'hypoechoic', shape: 'wider_than_tall',
    margin: 'lobulated_irregular', foci: 'macrocalcifications', size: 1.7
  },
  'tr5_papillary_carcinoma': {
    composition: 'solid', echogenicity: 'very_hypoechoic', shape: 'taller_than_wide',
    margin: 'lobulated_irregular', foci: 'punctate_microcalcifications', size: 1.4
  }
};

let ultrasoundStudioInitialized = false;
function initUltrasoundStudio() {
  if (ultrasoundStudioInitialized) return;
  ultrasoundStudioInitialized = true;
  loadUltrasoundPreset('tr5_papillary_carcinoma');
}

function loadUltrasoundPreset(key) {
  const p = ULTRASOUND_PRESETS[key];
  if (!p) return;

  document.getElementById('tirads-composition').value = p.composition;
  document.getElementById('tirads-echogenicity').value = p.echogenicity;
  document.getElementById('tirads-shape').value = p.shape;
  document.getElementById('tirads-margin').value = p.margin;
  document.getElementById('tirads-foci').value = p.foci;
  document.getElementById('tirads-size').value = p.size;

  runUltrasoundAnalysis(key);
}

async function runUltrasoundAnalysis(presetKey = 'tr5_papillary_carcinoma') {
  const comp = document.getElementById('tirads-composition').value;
  const echo = document.getElementById('tirads-echogenicity').value;
  const shape = document.getElementById('tirads-shape').value;
  const margin = document.getElementById('tirads-margin').value;
  const foci = document.getElementById('tirads-foci').value;
  const size = parseFloat(document.getElementById('tirads-size').value) || 1.5;

  const payload = {
    composition: comp,
    echogenicity: echo,
    shape: shape,
    margin: margin,
    echogenic_foci: foci,
    nodule_size_cm: size,
    preset_key: presetKey
  };

  try {
    const res = await fetch('/api/ultrasound/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();

    if (data.error) {
      showToast(`Ultrasound error: ${data.error}`);
      return;
    }

    currentUltrasoundData = data;
    currentUltrasoundRawB64 = data.raw_image_b64;
    currentUltrasoundOverlayB64 = data.segmentation_overlay_b64;
    showingOverlay = true;

    // Display image
    const imgEl = document.getElementById('us-display-img');
    const placeholder = document.getElementById('us-placeholder-text');
    imgEl.src = data.segmentation_overlay_b64;
    imgEl.style.display = 'inline-block';
    if (placeholder) placeholder.style.display = 'none';

    // Update morphology metrics
    const morph = data.morphology_metrics || {};
    document.getElementById('us-major-axis').textContent = `${morph.major_axis_mm || '--'} mm`;
    document.getElementById('us-minor-axis').textContent = `${morph.minor_axis_mm || '--'} mm`;
    document.getElementById('us-aspect-ratio').textContent = morph.aspect_ratio || '--';
    document.getElementById('us-shape-class').textContent = morph.shape_classification || '--';
    document.getElementById('us-shape-class').style.color = (morph.aspect_ratio > 1.0) ? '#ef4444' : '#10b981';
    document.getElementById('us-volume').textContent = `${morph.estimated_volume_ml || '--'} mL`;

    // Update TI-RADS Diagnostic Output
    const badge = document.getElementById('tirads-category-badge');
    badge.textContent = `${data.category} — ${data.classification}`;
    badge.className = `badge ${data.badge_class || 'badge-danger'}`;

    document.getElementById('tirads-points-text').textContent = `Total Points: ${data.total_points}`;
    document.getElementById('tirads-risk-pct').textContent = `Malignancy Risk: ~${data.malignancy_probability}% (${data.malignancy_risk_range})`;
    document.getElementById('tirads-progress-bar').style.width = `${Math.min(100, data.malignancy_probability)}%`;
    document.getElementById('tirads-fna-text').textContent = data.fna_recommendation;
    document.getElementById('tirads-followup-text').textContent = data.follow_up_recommendation;

    // Auto update multimodal fusion
    runMultimodalFusion();

  } catch (err) {
    console.error('Ultrasound analysis error:', err);
    showToast('Failed to execute ultrasound analysis.');
  }
}

function toggleUltrasoundOverlay() {
  if (!currentUltrasoundData) return;
  const imgEl = document.getElementById('us-display-img');
  showingOverlay = !showingOverlay;
  imgEl.src = showingOverlay ? currentUltrasoundOverlayB64 : currentUltrasoundRawB64;
  showToast(showingOverlay ? 'Displaying U-Net Segmentation Overlay' : 'Displaying Raw B-Mode Ultrasound');
}

async function runMultimodalFusion() {
  if (!currentUltrasoundData) {
    showToast('Please run ultrasound analysis first.');
    return;
  }

  // Get current tabular prediction status if available
  const tabData = {
    champion_prediction_badge: 'Negative (Normal Euthyroid)',
    champion_confidence: 80.1,
    anomaly_screening: { is_anomaly: false }
  };

  try {
    const res = await fetch('/api/multimodal/fuse', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        tabular_data: tabData,
        ultrasound_data: currentUltrasoundData
      })
    });
    const data = await res.json();

    if (data.error) return;

    document.getElementById('mm-functional-status').textContent = data.functional_component.diagnosis;
    document.getElementById('mm-functional-conf').textContent = `Confidence: ${data.functional_component.confidence}% | Autoencoder: ${data.functional_component.autoencoder_anomaly ? 'Outlier' : 'Normal'}`;

    document.getElementById('mm-anatomical-status').textContent = `${data.anatomical_component.tirads_category} — ${data.anatomical_component.classification}`;
    document.getElementById('mm-anatomical-risk').textContent = `Malignancy: ~${data.anatomical_component.malignancy_probability}% | Size: ${data.anatomical_component.nodule_size_cm} cm`;

    document.getElementById('mm-composite-urgency').textContent = data.composite_urgency;
    document.getElementById('mm-composite-summary').textContent = data.overall_status;

    document.getElementById('mm-management-plan').textContent = data.multidisciplinary_management_plan;

  } catch (err) {
    console.error('Multimodal fusion error:', err);
  }
}


// -------------------------------------------------------------
// 15. Phase 2: Clinical Symptoms NLP Module
// -------------------------------------------------------------
const NLP_PRESETS = {
  'hypo': 'Patient is a 52-year-old female presenting with profound chronic fatigue, cold intolerance, 4.5kg unexplained weight gain over 4 months, constipation, brain fog, facial puffiness, and brittle hair thinning.',
  'hyper': 'Patient reports 3-week history of resting palpitations, racing heart rate (tachycardia 112 bpm), severe heat intolerance, diaphoresis, hand tremor, anxiety with insomnia, and 5kg unintentional weight loss despite hyperphagia.',
  'goiter': 'Patient complains of visible anterior neck swelling, progressive difficulty swallowing (dysphagia with solid foods), persistent hoarseness in voice, and globus sensation of throat tightness when lying supine.'
};

function loadNLPPreset(type) {
  const text = NLP_PRESETS[type] || '';
  document.getElementById('nlp-clinical-text').value = text;
  runClinicalNLPExtraction();
}

async function runClinicalNLPExtraction() {
  const text = document.getElementById('nlp-clinical-text').value;
  if (!text || text.trim().length < 5) {
    showToast('Please enter clinical notes to parse symptoms.');
    return;
  }

  try {
    const res = await fetch('/api/clinical-nlp/extract', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ clinical_text: text })
    });
    const data = await res.json();

    if (data.error || data.status === 'empty_text') {
      showToast(data.message || 'No symptoms detected.');
      return;
    }

    const container = document.getElementById('nlp-output-container');
    container.style.display = 'block';

    const badge = document.getElementById('nlp-phenotype-badge');
    badge.textContent = data.dominant_phenotype;
    badge.className = `badge ${data.phenotype_badge || 'badge-info'}`;

    document.getElementById('nlp-matched-count').textContent = `${data.matched_symptoms_count} Symptoms Extracted`;
    document.getElementById('nlp-hypo-burden').textContent = `${data.burden_scores.hypothyroid_pct}%`;
    document.getElementById('nlp-hyper-burden').textContent = `${data.burden_scores.hyperthyroid_pct}%`;
    document.getElementById('nlp-comp-burden').textContent = `${data.burden_scores.compressive_nodule_pct}%`;

    const tagsContainer = document.getElementById('nlp-symptoms-tags');
    tagsContainer.innerHTML = (data.symptoms_list || []).map(s => {
      const color = s.category === 'hypothyroid' ? '#38bdf8' : (s.category === 'hyperthyroid' ? '#f59e0b' : '#ef4444');
      return `<span style="background:rgba(255,255,255,0.06); border:1px solid ${color}; color:#f8fafc; font-size:11px; padding:3px 8px; border-radius:12px;">
        ${s.display_name} (<em style="color:${color};">${s.matched_term}</em>)
      </span>`;
    }).join('');

    document.getElementById('nlp-clinical-summary').textContent = data.clinical_interpretation;
    showToast(`Extracted ${data.matched_symptoms_count} structured symptoms.`);

  } catch (err) {
    console.error('NLP extraction error:', err);
    showToast('Failed to parse clinical notes.');
  }
}


// -------------------------------------------------------------
// 16. Phase 2: Longitudinal Trajectory Tracking Module
// -------------------------------------------------------------
let trajectoryVisits = [
  { date: '2025-01-10', tsh: 8.4, ft4: 11.2, t3: 2.0, medication: 'None', dose_mcg: 0 },
  { date: '2025-04-15', tsh: 6.1, ft4: 13.5, t3: 2.3, medication: 'Levothyroxine', dose_mcg: 50 },
  { date: '2025-08-20', tsh: 3.2, ft4: 15.8, t3: 2.5, medication: 'Levothyroxine', dose_mcg: 75 }
];

const TRAJECTORY_PRESETS = {
  'hypo_progression': [
    { date: '2024-09-01', tsh: 4.8, ft4: 14.5, t3: 2.4, medication: 'None', dose_mcg: 0 },
    { date: '2025-01-15', tsh: 7.2, ft4: 12.8, t3: 2.2, medication: 'None', dose_mcg: 0 },
    { date: '2025-06-20', tsh: 11.5, ft4: 9.8, t3: 1.8, medication: 'None', dose_mcg: 0 }
  ],
  'euthyroid_control': [
    { date: '2024-10-01', tsh: 9.2, ft4: 10.5, t3: 2.0, medication: 'None', dose_mcg: 0 },
    { date: '2025-02-15', tsh: 4.5, ft4: 13.8, t3: 2.3, medication: 'Levothyroxine', dose_mcg: 50 },
    { date: '2025-07-10', tsh: 1.8, ft4: 16.2, t3: 2.6, medication: 'Levothyroxine', dose_mcg: 75 }
  ],
  'over_replacement': [
    { date: '2025-01-05', tsh: 5.8, ft4: 12.0, t3: 2.1, medication: 'Levothyroxine', dose_mcg: 50 },
    { date: '2025-04-10', tsh: 1.2, ft4: 16.5, t3: 2.6, medication: 'Levothyroxine', dose_mcg: 100 },
    { date: '2025-08-15', tsh: 0.08, ft4: 24.1, t3: 3.4, medication: 'Levothyroxine', dose_mcg: 150 }
  ]
};

let trajectoryTrackerInitialized = false;
function initTrajectoryTracker() {
  if (trajectoryTrackerInitialized) return;
  trajectoryTrackerInitialized = true;
  renderTrajectoryTable();
  runTrajectoryAnalysis();
}

function loadTrajectoryPreset(key) {
  const p = TRAJECTORY_PRESETS[key];
  if (!p) return;
  trajectoryVisits = JSON.parse(JSON.stringify(p));
  renderTrajectoryTable();
  runTrajectoryAnalysis();
}

function renderTrajectoryTable() {
  const tbody = document.getElementById('trajectory-tbody');
  if (!tbody) return;

  tbody.innerHTML = trajectoryVisits.map((v, i) => `
    <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
      <td style="padding:6px;"><input type="date" value="${v.date}" onchange="updateTrajectoryVisit(${i}, 'date', this.value)" style="font-size:12px; padding:4px 8px; background:rgba(0,0,0,0.3); border:1px solid rgba(255,255,255,0.1); border-radius:6px; color:#f8fafc;" /></td>
      <td style="padding:6px;"><input type="number" step="0.01" value="${v.tsh}" onchange="updateTrajectoryVisit(${i}, 'tsh', this.value)" style="width:75px; font-size:12px; padding:4px 8px; background:rgba(0,0,0,0.3); border:1px solid rgba(255,255,255,0.1); border-radius:6px; color:#f8fafc;" /></td>
      <td style="padding:6px;"><input type="number" step="0.1" value="${v.ft4}" onchange="updateTrajectoryVisit(${i}, 'ft4', this.value)" style="width:75px; font-size:12px; padding:4px 8px; background:rgba(0,0,0,0.3); border:1px solid rgba(255,255,255,0.1); border-radius:6px; color:#f8fafc;" /></td>
      <td style="padding:6px;"><input type="number" step="0.1" value="${v.t3}" onchange="updateTrajectoryVisit(${i}, 't3', this.value)" style="width:75px; font-size:12px; padding:4px 8px; background:rgba(0,0,0,0.3); border:1px solid rgba(255,255,255,0.1); border-radius:6px; color:#f8fafc;" /></td>
      <td style="padding:6px;">
        <select onchange="updateTrajectoryVisit(${i}, 'medication', this.value)" style="font-size:12px; padding:4px 8px; background:rgba(0,0,0,0.3); border:1px solid rgba(255,255,255,0.1); border-radius:6px; color:#f8fafc;">
          <option value="None" ${v.medication === 'None' ? 'selected' : ''}>None</option>
          <option value="Levothyroxine" ${v.medication === 'Levothyroxine' ? 'selected' : ''}>Levothyroxine (T4)</option>
          <option value="Liothyronine" ${v.medication === 'Liothyronine' ? 'selected' : ''}>Liothyronine (T3)</option>
          <option value="Methimazole" ${v.medication === 'Methimazole' ? 'selected' : ''}>Methimazole</option>
          <option value="PTU" ${v.medication === 'PTU' ? 'selected' : ''}>Propylthiouracil</option>
        </select>
      </td>
      <td style="padding:6px;"><input type="number" step="12.5" value="${v.dose_mcg}" onchange="updateTrajectoryVisit(${i}, 'dose_mcg', this.value)" style="width:70px; font-size:12px; padding:4px 8px; background:rgba(0,0,0,0.3); border:1px solid rgba(255,255,255,0.1); border-radius:6px; color:#f8fafc;" /></td>
      <td style="padding:6px; text-align:center;">
        <button class="btn-secondary" style="font-size:11px; padding:3px 8px; color:#ef4444;" onclick="deleteTrajectoryRow(${i})">✕</button>
      </td>
    </tr>
  `).join('');
}

function updateTrajectoryVisit(index, field, val) {
  if (!trajectoryVisits[index]) return;
  if (field === 'tsh' || field === 'ft4' || field === 't3' || field === 'dose_mcg') {
    trajectoryVisits[index][field] = parseFloat(val) || 0;
  } else {
    trajectoryVisits[index][field] = val;
  }
}

function addTrajectoryRow() {
  const lastDate = trajectoryVisits.length > 0 ? trajectoryVisits[trajectoryVisits.length - 1].date : '2025-01-01';
  const d = new Date(lastDate);
  d.setMonth(d.getMonth() + 3);
  const nextDateStr = d.toISOString().split('T')[0];

  trajectoryVisits.push({
    date: nextDateStr,
    tsh: 4.0,
    ft4: 14.0,
    t3: 2.2,
    medication: 'Levothyroxine',
    dose_mcg: 50
  });
  renderTrajectoryTable();
}

function deleteTrajectoryRow(idx) {
  if (trajectoryVisits.length <= 2) {
    showToast('At least 2 visits are required for trajectory velocity calculation.');
    return;
  }
  trajectoryVisits.splice(idx, 1);
  renderTrajectoryTable();
}

async function runTrajectoryAnalysis() {
  if (trajectoryVisits.length < 2) {
    showToast('Please record at least 2 longitudinal lab visits.');
    return;
  }

  try {
    const res = await fetch('/api/trajectory/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ visits: trajectoryVisits })
    });
    const data = await res.json();

    if (data.error || data.status === 'insufficient_data') {
      showToast(data.message || 'Trajectory analysis failed.');
      return;
    }

    const resCard = document.getElementById('trajectory-results-card');
    resCard.style.display = 'block';

    const badge = document.getElementById('traj-pattern-badge');
    badge.textContent = data.trajectory_pattern;
    badge.className = `badge ${data.severity_badge || 'badge-info'}`;

    document.getElementById('traj-response-text').textContent = data.treatment_response;
    document.getElementById('traj-titration-text').textContent = data.titration_recommendation;

    const m = data.metrics || {};
    document.getElementById('traj-tsh-velocity').textContent = `${m.tsh_velocity_monthly > 0 ? '+' : ''}${m.tsh_velocity_monthly} /mo`;
    document.getElementById('traj-ft4-velocity').textContent = `${m.ft4_velocity_monthly > 0 ? '+' : ''}${m.ft4_velocity_monthly} /mo`;
    document.getElementById('traj-volatility').textContent = `${m.volatility_cv_pct}%`;
    document.getElementById('traj-projected-tsh').textContent = `${m.projected_tsh_6m} mIU/L`;

    // Render Timeline Flow
    const flowContainer = document.getElementById('traj-timeline-flow');
    flowContainer.innerHTML = (data.timeline || []).map((t, idx) => {
      const isProj = t.is_projected;
      const borderCol = isProj ? '#ef4444' : '#38bdf8';
      return `
        <div style="background:rgba(255,255,255,0.02); border-left:3px solid ${borderCol}; padding:8px 12px; border-radius:6px;">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <strong style="font-size:12.5px; color:${isProj ? '#ef4444' : '#f8fafc'};">${t.date} ${isProj ? '(Prognostic Forecast)' : ''}</strong>
            <span style="font-size:11.5px; color:var(--text-muted);">${t.medication !== 'None' ? t.medication + ' ' + t.dose_mcg + 'mcg' : 'Unmedicated'}</span>
          </div>
          <div style="font-size:12px; color:var(--text-secondary); margin-top:2px;">
            TSH: <strong>${t.tsh} mIU/L</strong> | Free T4: <strong>${t.ft4} pmol/L</strong>
          </div>
        </div>
      `;
    }).join('');

    showToast('Trajectory Analysis Complete!');

  } catch (err) {
    console.error('Trajectory analysis error:', err);
    showToast('Failed to compute trajectory.');
  }
}


// -------------------------------------------------------------
// 17. Phase 3 & 4: FT-Transformer & Explainability Studio (XAI)
// -------------------------------------------------------------
let currentXAIPatient = {
  TSH: 8.5, FTI: 105.0, TT4: 100.0, T3: 2.2, T4U: 1.0, age: 45, on_thyroxine: 'f', sex: 'F'
};

const XAI_PRESETS = {
  'subclinical_hypo': { TSH: 8.5, FTI: 105.0, TT4: 100.0, T3: 2.2, T4U: 1.0, age: 45, on_thyroxine: 'f', sex: 'F' },
  'overt_hypo': { TSH: 28.0, FTI: 48.0, TT4: 42.0, T3: 1.1, T4U: 1.1, age: 52, on_thyroxine: 'f', sex: 'F' },
  'hyperthyroid': { TSH: 0.04, FTI: 185.0, TT4: 195.0, T3: 4.2, T4U: 0.85, age: 36, on_thyroxine: 'f', sex: 'F' },
  'euthyroid': { TSH: 1.85, FTI: 108.0, TT4: 105.0, T3: 2.3, T4U: 1.0, age: 32, on_thyroxine: 'f', sex: 'F' }
};

let explainabilityStudioInitialized = false;
function initExplainabilityStudio() {
  if (explainabilityStudioInitialized) return;
  explainabilityStudioInitialized = true;
  loadXAIPreset('subclinical_hypo');
}

function loadXAIPreset(key) {
  const p = XAI_PRESETS[key];
  if (!p) return;
  currentXAIPatient = JSON.parse(JSON.stringify(p));

  const sliderTsh = document.getElementById('cf-tsh-slider');
  const sliderFti = document.getElementById('cf-fti-slider');
  if (sliderTsh) sliderTsh.value = currentXAIPatient.TSH;
  if (sliderFti) sliderFti.value = currentXAIPatient.FTI;

  document.getElementById('cf-tsh-val-display').textContent = `${currentXAIPatient.TSH} mIU/L`;
  document.getElementById('cf-fti-val-display').textContent = `${currentXAIPatient.FTI} pmol/L`;

  runXAIAnalysis();
}

async function runXAIAnalysis() {
  try {
    // 1. Run FT-Transformer Inference
    const fttRes = await fetch('/api/explainability/ft-transformer', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(currentXAIPatient)
    });
    const fttData = await fttRes.json();

    if (fttData.prediction_badge) {
      document.getElementById('ftt-pred-badge').textContent = fttData.prediction_badge;
      document.getElementById('ftt-confidence-text').innerHTML = `Model Confidence: <strong>${fttData.confidence}%</strong>`;

      // Probability bars
      const probBars = document.getElementById('ftt-prob-bars');
      probBars.innerHTML = Object.entries(fttData.class_probabilities || {}).map(([cls, pct]) => `
        <div>
          <div style="display:flex; justify-content:space-between; font-size:11px; margin-bottom:2px;">
            <span>${cls.replace('_', ' ').title ? cls.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase()) : cls}</span>
            <strong>${pct}%</strong>
          </div>
          <div style="background:rgba(255,255,255,0.06); height:6px; border-radius:4px; overflow:hidden;">
            <div style="width:${pct}%; height:100%; background:${cls.includes('subclinical') ? '#f59e0b' : (cls.includes('hypo') || cls.includes('hyper') ? '#ef4444' : '#10b981')};"></div>
          </div>
        </div>
      `).join('');

      // Render Attention Heatmap Table
      renderAttentionMatrix(fttData.features, fttData.attention_matrix);
    }

    // 2. Fetch SHAP Feature Attributions
    const shapRes = await fetch('/api/explainability/attributions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(currentXAIPatient)
    });
    const shapData = await shapRes.json();
    if (shapData.attributions) {
      renderSHAPWaterfall(shapData.attributions, shapData.base_value);
    }

    // 3. Fetch Counterfactual Optimization
    const cfRes = await fetch('/api/explainability/counterfactual', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(currentXAIPatient)
    });
    const cfData = await cfRes.json();
    renderCounterfactualTarget(cfData);

  } catch (err) {
    console.error('XAI execution error:', err);
    showToast('Failed to execute XAI suite.');
  }
}

function renderAttentionMatrix(features, matrix) {
  const table = document.getElementById('ftt-attention-table');
  if (!table || !features || !matrix) return;

  let html = `<thead><tr style="color:var(--text-muted); border-bottom:1px solid rgba(255,255,255,0.1);"><th style="padding:6px; text-align:left;">Token (From \\ To)</th>`;
  features.forEach(f => {
    html += `<th style="padding:6px;">${f}</th>`;
  });
  html += `</tr></thead><tbody>`;

  matrix.forEach(row => {
    html += `<tr style="border-bottom:1px solid rgba(255,255,255,0.03);"><td style="padding:6px; font-weight:600; text-align:left; color:#f8fafc;">${row.feature}</td>`;
    features.forEach(fTo => {
      const val = row.attentions[fTo] || 0;
      const alpha = Math.min(0.9, Math.max(0.08, val * 2.2));
      html += `<td style="padding:6px; background:rgba(56, 189, 248, ${alpha}); color:${alpha > 0.4 ? '#020617' : '#f8fafc'}; font-weight:${val > 0.15 ? '700' : '400'}; border-radius:4px;">
        ${val.toFixed(2)}
      </td>`;
    });
    html += `</tr>`;
  });

  html += `</tbody>`;
  table.innerHTML = html;
}

function renderSHAPWaterfall(attributions, baseVal) {
  const container = document.getElementById('shap-waterfall-container');
  if (!container) return;

  container.innerHTML = attributions.map(attr => {
    const isPos = attr.attribution_shap > 0;
    const barWidth = Math.min(100, Math.abs(attr.attribution_shap) * 120);
    const color = isPos ? '#ef4444' : '#10b981';

    return `
      <div style="background:rgba(255,255,255,0.02); border:1px solid rgba(255,255,255,0.06); padding:10px 14px; border-radius:8px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
          <div>
            <strong style="font-size:13px; color:#f8fafc;">${attr.feature}</strong>
            <span style="font-size:12px; color:var(--text-muted); margin-left:6px;">= ${attr.value}</span>
          </div>
          <div style="font-size:13px; font-weight:700; color:${color};">
            ${isPos ? '+' : ''}${attr.attribution_shap} SHAP
          </div>
        </div>

        <!-- Waterfall Bar -->
        <div style="background:rgba(255,255,255,0.06); height:6px; border-radius:4px; overflow:hidden; margin-bottom:6px;">
          <div style="width:${barWidth}%; height:100%; background:${color}; border-radius:4px;"></div>
        </div>

        <div style="font-size:11.5px; color:var(--text-secondary); line-height:1.4;">
          ${attr.impact_description}
        </div>
      </div>
    `;
  }).join('');
}

function renderCounterfactualTarget(cfData) {
  const summaryEl = document.getElementById('cf-summary-text');
  const listEl = document.getElementById('cf-perturbations-list');
  if (!summaryEl || !listEl) return;

  if (!cfData.is_counterfactual_needed) {
    summaryEl.textContent = 'Patient is already in physiological homeostasis (Euthyroid baseline).';
    listEl.innerHTML = '';
    return;
  }

  summaryEl.textContent = cfData.summary;
  listEl.innerHTML = (cfData.perturbations || []).map(p => `
    <div style="background:rgba(255,255,255,0.02); border-left:3px solid #10b981; padding:6px 10px; border-radius:4px;">
      <div style="display:flex; justify-content:space-between; font-size:11.5px;">
        <strong>${p.biomarker}:</strong>
        <span style="color:#10b981;">Shift to ${p.target_value} (Δ ${p.required_change})</span>
      </div>
      <div style="font-size:11px; color:var(--text-muted); margin-top:2px;">
        ${p.clinical_action}
      </div>
    </div>
  `).join('');
}

let cfSliderDebounce = null;
function handleCounterfactualSliderChange() {
  const tsh = parseFloat(document.getElementById('cf-tsh-slider').value) || 2.0;
  const fti = parseFloat(document.getElementById('cf-fti-slider').value) || 105.0;

  document.getElementById('cf-tsh-val-display').textContent = `${tsh.toFixed(2)} mIU/L`;
  document.getElementById('cf-fti-val-display').textContent = `${fti.toFixed(1)} pmol/L`;

  currentXAIPatient.TSH = tsh;
  currentXAIPatient.FTI = fti;

  clearTimeout(cfSliderDebounce);
  cfSliderDebounce = setTimeout(() => {
    runXAIAnalysis();
  }, 250);
}

// -------------------------------------------------------------
// 18. HL7 FHIR R4 Bundle Modal & Export
// -------------------------------------------------------------
let latestFHIRBundle = null;

async function exportFHIRBundleModal() {
  try {
    const payload = {
      patient_data: currentXAIPatient,
      model_results: { champion_prediction_badge: document.getElementById('ftt-pred-badge') ? document.getElementById('ftt-pred-badge').textContent : 'Negative' },
      ultrasound_data: currentUltrasoundData || { category: 'TR1', classification: 'Benign', malignancy_probability: 1.2 }
    };

    const res = await fetch('/api/fhir/export', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();

    latestFHIRBundle = data;
    document.getElementById('fhir-json-display').textContent = JSON.stringify(data, null, 2);
    document.getElementById('fhir-modal').classList.add('active');

  } catch (err) {
    console.error('FHIR export error:', err);
    showToast('Failed to generate FHIR R4 bundle.');
  }
}

function closeFHIRModal() {
  document.getElementById('fhir-modal').classList.remove('active');
}

function copyFHIRJSON() {
  if (!latestFHIRBundle) return;
  navigator.clipboard.writeText(JSON.stringify(latestFHIRBundle, null, 2));
  showToast('HL7 FHIR R4 JSON copied to clipboard!');
}

function downloadFHIRJSON() {
  if (!latestFHIRBundle) return;
  const str = JSON.stringify(latestFHIRBundle, null, 2);
  const blob = new Blob([str], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `ThyroScan_FHIR_Bundle_${Date.now()}.json`;
  a.click();
  URL.revokeObjectURL(url);
  showToast('FHIR Bundle JSON downloaded!');
}


function showToast(msg) {
  const existing = document.querySelector('.app-toast');
  if (existing) existing.remove();

  const toast = document.createElement('div');
  toast.className = 'app-toast';
  toast.textContent = msg;
  document.body.appendChild(toast);

  setTimeout(() => toast.remove(), 3500);
}
