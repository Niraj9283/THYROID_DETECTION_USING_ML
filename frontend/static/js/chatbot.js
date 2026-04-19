/* ================================================================
   ThyroScan AI — Chatbot  (chatbot.js)
   Place in: frontend/static/js/chatbot.js
   Calls backend /api/chat — no API key exposed in browser
   ================================================================ */

(function () {

  const API_BASE = 'http://localhost:5000';

  async function askBot(messages) {
    const res = await fetch(`${API_BASE}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages })
    });
    if (!res.ok) throw new Error(`Server error: ${res.status}`);
    const data = await res.json();
    return data.reply || 'Sorry, I could not get a response.';
  }

  const css = `
    #thyrobot-bubble {
      position: fixed; bottom: 28px; right: 28px; z-index: 9999;
      width: 58px; height: 58px; border-radius: 50%;
      background: linear-gradient(135deg, #63fcda, #8b5cf6);
      border: none; cursor: pointer;
      box-shadow: 0 4px 24px rgba(99,252,218,0.45);
      display: flex; align-items: center; justify-content: center;
      font-size: 26px; transition: transform 0.2s, box-shadow 0.2s;
    }
    #thyrobot-bubble:hover { transform: scale(1.1); box-shadow: 0 8px 32px rgba(99,252,218,0.6); }
    #thyrobot-bubble .bot-badge {
      position: absolute; top: -3px; right: -3px;
      width: 15px; height: 15px; border-radius: 50%;
      background: #ef4444; border: 2px solid #070b14;
      animation: badgePulse 2s ease-in-out infinite;
    }
    body.light-theme #thyrobot-bubble .bot-badge { border-color: #fff; }
    @keyframes badgePulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:0.5;transform:scale(1.2)} }

    #thyrobot-window {
      position: fixed; bottom: 100px; right: 28px; z-index: 9998;
      width: 375px; height: 580px;
      background: #0d1424; border: 1px solid rgba(99,252,218,0.18);
      border-radius: 22px; display: flex; flex-direction: column;
      box-shadow: 0 24px 64px rgba(0,0,0,0.55);
      transform: scale(0.88) translateY(24px); opacity: 0; pointer-events: none;
      transition: all 0.28s cubic-bezier(0.34,1.56,0.64,1); overflow: hidden;
    }
    #thyrobot-window.open { transform: scale(1) translateY(0); opacity: 1; pointer-events: all; }
    body.light-theme #thyrobot-window { background: #f8fafc; border-color: rgba(37,99,235,0.18); box-shadow: 0 24px 64px rgba(0,0,0,0.14); }

    .bot-header { padding: 14px 16px; display: flex; align-items: center; gap: 11px; background: linear-gradient(135deg, rgba(99,252,218,0.07), rgba(139,92,246,0.07)); border-bottom: 1px solid rgba(255,255,255,0.07); flex-shrink: 0; }
    body.light-theme .bot-header { border-bottom-color: rgba(0,0,0,0.07); }
    .bot-avatar { width: 40px; height: 40px; border-radius: 50%; background: linear-gradient(135deg, #63fcda, #8b5cf6); display: flex; align-items: center; justify-content: center; font-size: 20px; flex-shrink: 0; }
    .bot-info { flex: 1; min-width: 0; }
    .bot-name { font-family: 'Syne', sans-serif; font-size: 15px; font-weight: 700; color: #e2e8f0; line-height: 1.2; }
    body.light-theme .bot-name { color: #1a3557; }
    .bot-status { font-size: 11px; color: #63fcda; display: flex; align-items: center; gap: 5px; margin-top: 2px; }
    body.light-theme .bot-status { color: #059669; }
    .status-dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; animation: badgePulse 2s infinite; }
    .bot-close { background: none; border: none; cursor: pointer; font-size: 17px; color: #64748b; padding: 4px 6px; line-height: 1; border-radius: 8px; transition: color 0.15s, background 0.15s; }
    .bot-close:hover { color: #e2e8f0; background: rgba(255,255,255,0.07); }
    body.light-theme .bot-close:hover { color: #1a3557; background: rgba(0,0,0,0.06); }

    .bot-quick-btns { display: flex; gap: 6px; padding: 9px 12px; flex-wrap: wrap; border-bottom: 1px solid rgba(255,255,255,0.06); flex-shrink: 0; }
    body.light-theme .bot-quick-btns { border-bottom-color: rgba(0,0,0,0.06); }
    .quick-btn { padding: 5px 11px; border-radius: 20px; border: 1px solid rgba(99,252,218,0.22); background: rgba(99,252,218,0.07); color: #63fcda; font-size: 11.5px; cursor: pointer; transition: all 0.18s; white-space: nowrap; font-family: 'DM Sans', sans-serif; }
    .quick-btn:hover { background: rgba(99,252,218,0.17); border-color: rgba(99,252,218,0.45); }
    body.light-theme .quick-btn { border-color: rgba(37,99,235,0.22); background: rgba(37,99,235,0.06); color: #2563eb; }
    body.light-theme .quick-btn:hover { background: rgba(37,99,235,0.14); }

    .bot-messages { flex: 1; overflow-y: auto; padding: 14px 13px 6px; display: flex; flex-direction: column; gap: 10px; scroll-behavior: smooth; }
    .bot-messages::-webkit-scrollbar { width: 3px; }
    .bot-messages::-webkit-scrollbar-thumb { background: rgba(99,252,218,0.18); border-radius: 2px; }

    .msg { display: flex; gap: 8px; animation: msgIn 0.22s ease; }
    .msg.user { flex-direction: row-reverse; }
    @keyframes msgIn { from{opacity:0;transform:translateY(10px)} to{opacity:1;transform:translateY(0)} }

    .msg-avatar { width: 28px; height: 28px; border-radius: 50%; flex-shrink: 0; margin-top: 2px; display: flex; align-items: center; justify-content: center; font-size: 14px; }
    .msg.bot  .msg-avatar { background: rgba(99,252,218,0.1);  border: 1px solid rgba(99,252,218,0.2); }
    .msg.user .msg-avatar { background: rgba(139,92,246,0.15); border: 1px solid rgba(139,92,246,0.25); }

    .msg-bubble { padding: 9px 13px; border-radius: 15px; font-size: 13.5px; line-height: 1.58; max-width: 83%; word-break: break-word; font-family: 'DM Sans', sans-serif; }
    .msg.bot  .msg-bubble { background: rgba(255,255,255,0.05); color: #cbd5e1; border: 1px solid rgba(255,255,255,0.08); border-bottom-left-radius: 4px; }
    .msg.user .msg-bubble { background: linear-gradient(135deg, rgba(99,252,218,0.14), rgba(139,92,246,0.14)); color: #e2e8f0; border: 1px solid rgba(99,252,218,0.22); border-bottom-right-radius: 4px; }
    body.light-theme .msg.bot  .msg-bubble { background: #fff; color: #374151; border-color: #e2e8f0; box-shadow: 0 1px 4px rgba(0,0,0,0.06); }
    body.light-theme .msg.user .msg-bubble { background: linear-gradient(135deg, rgba(37,99,235,0.1), rgba(139,92,246,0.1)); color: #1a3557; border-color: rgba(37,99,235,0.22); }
    .msg-bubble ul { margin: 5px 0 0 14px; padding: 0; }
    .msg-bubble li { margin-bottom: 3px; }
    .msg-bubble strong { color: #63fcda; }
    body.light-theme .msg-bubble strong { color: #1d4ed8; }

    .typing-indicator { display: flex; align-items: center; gap: 4px; padding: 10px 14px; background: rgba(255,255,255,0.05); border-radius: 15px; border-bottom-left-radius: 4px; border: 1px solid rgba(255,255,255,0.08); width: fit-content; }
    body.light-theme .typing-indicator { background: #fff; border-color: #e2e8f0; }
    .typing-dot { width: 6px; height: 6px; border-radius: 50%; background: #63fcda; animation: typingBounce 1.2s ease infinite; }
    body.light-theme .typing-dot { background: #2563eb; }
    .typing-dot:nth-child(2){animation-delay:0.2s}
    .typing-dot:nth-child(3){animation-delay:0.4s}
    @keyframes typingBounce { 0%,60%,100%{transform:translateY(0)} 30%{transform:translateY(-7px)} }

    .bot-input-row { display: flex; gap: 8px; padding: 10px 12px 14px; border-top: 1px solid rgba(255,255,255,0.06); flex-shrink: 0; align-items: flex-end; }
    body.light-theme .bot-input-row { border-top-color: rgba(0,0,0,0.07); }
    .bot-input { flex: 1; background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.1); border-radius: 22px; padding: 9px 16px; color: #e2e8f0; font-family: 'DM Sans', sans-serif; font-size: 13.5px; outline: none; transition: border-color 0.2s; resize: none; }
    .bot-input:focus { border-color: rgba(99,252,218,0.45); }
    .bot-input::placeholder { color: #475569; }
    body.light-theme .bot-input { background: #fff; border-color: #e2e8f0; color: #374151; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
    body.light-theme .bot-input::placeholder { color: #94a3b8; }
    body.light-theme .bot-input:focus { border-color: rgba(37,99,235,0.4); }
    .bot-send { width: 40px; height: 40px; border-radius: 50%; border: none; background: linear-gradient(135deg, #63fcda, #8b5cf6); cursor: pointer; display: flex; align-items: center; justify-content: center; font-size: 16px; flex-shrink: 0; transition: transform 0.18s, opacity 0.18s; }
    .bot-send:hover:not(:disabled) { transform: scale(1.1); }
    .bot-send:disabled { opacity: 0.38; cursor: not-allowed; }

    @media (max-width: 430px) {
      #thyrobot-window { width: calc(100vw - 16px); right: 8px; bottom: 88px; border-radius: 18px; height: 70vh; }
      #thyrobot-bubble { right: 14px; bottom: 14px; }
    }
  `;

  const styleEl = document.createElement('style');
  styleEl.textContent = css;
  document.head.appendChild(styleEl);

  const wrap = document.createElement('div');
  wrap.innerHTML = `
    <button id="thyrobot-bubble" title="Chat with ThyroBot" aria-label="Open ThyroBot chat">
      🤖<span class="bot-badge"></span>
    </button>
    <div id="thyrobot-window" role="dialog" aria-label="ThyroBot medical assistant">
      <div class="bot-header">
        <div class="bot-avatar">🤖</div>
        <div class="bot-info">
          <div class="bot-name">ThyroBot</div>
          <div class="bot-status"><span class="status-dot"></span> Online — here to help</div>
        </div>
        <button class="bot-close" id="thyrobot-close" aria-label="Close chat">✕</button>
      </div>
      <div class="bot-quick-btns">
        <button class="quick-btn" data-msg="How do I use this website?">📖 How to use</button>
        <button class="quick-btn" data-msg="What are common symptoms of thyroid disease?">🩺 Symptoms</button>
        <button class="quick-btn" data-msg="What diet should I follow for thyroid?">🥗 Diet tips</button>
        <button class="quick-btn" data-msg="What exercises are good for thyroid patients?">🏃 Exercise</button>
        <button class="quick-btn" data-msg="Explain TSH, T3 and TT4 lab values and their normal ranges">🧪 Lab values</button>
      </div>
      <div class="bot-messages" id="thyrobot-messages"></div>
      <div class="bot-input-row">
        <input type="text" class="bot-input" id="thyrobot-input" placeholder="Ask me anything about thyroid…" maxlength="500" autocomplete="off"/>
        <button class="bot-send" id="thyrobot-send" aria-label="Send message">➤</button>
      </div>
    </div>
  `;
  document.body.appendChild(wrap);

  const chatHistory = [];
  let isOpen = false, isBusy = false, greeted = false;

  const bubble   = document.getElementById('thyrobot-bubble');
  const win      = document.getElementById('thyrobot-window');
  const closeBtn = document.getElementById('thyrobot-close');
  const msgArea  = document.getElementById('thyrobot-messages');
  const input    = document.getElementById('thyrobot-input');
  const sendBtn  = document.getElementById('thyrobot-send');

  function toggle() {
    isOpen = !isOpen;
    win.classList.toggle('open', isOpen);
    bubble.querySelector('.bot-badge').style.display = isOpen ? 'none' : '';
    if (isOpen) { if (!greeted) { greeted = true; greet(); } setTimeout(() => input.focus(), 320); }
  }

  function fmt(text) {
    return text
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/^[\-•]\s(.+)/gm, '<li>$1</li>')
      .replace(/(<li>[\s\S]*?<\/li>)/g, '<ul>$1</ul>')
      .replace(/\n/g, '<br>');
  }

  function addMsg(role, text) {
    const div = document.createElement('div');
    div.className = `msg ${role}`;
    div.innerHTML = `<div class="msg-avatar">${role==='bot'?'🤖':'👤'}</div><div class="msg-bubble">${fmt(text)}</div>`;
    msgArea.appendChild(div);
    msgArea.scrollTop = msgArea.scrollHeight;
  }

  function showTyping() {
    const div = document.createElement('div');
    div.className = 'msg bot'; div.id = 'bot-typing';
    div.innerHTML = `<div class="msg-avatar">🤖</div><div class="typing-indicator"><div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div></div>`;
    msgArea.appendChild(div);
    msgArea.scrollTop = msgArea.scrollHeight;
  }
  function hideTyping() { document.getElementById('bot-typing')?.remove(); }

  async function greet() {
    showTyping();
    await new Promise(r => setTimeout(r, 800));
    hideTyping();
    const msg = `👋 Hi! I'm **ThyroBot**, your thyroid health assistant!\n\nI can help you with:\n- 📋 Navigating and using this website\n- 🩺 Understanding thyroid symptoms\n- 🥗 Diet & nutrition advice\n- 🏃 Exercise recommendations\n- 🧪 Explaining lab values (TSH, T3, TT4)\n\nWhat would you like to know? Use the quick buttons above or just type!`;
    addMsg('bot', msg);
    chatHistory.push({ role: 'assistant', content: msg });
  }

  async function send(text) {
    text = text.trim();
    if (!text || isBusy) return;
    isBusy = true; sendBtn.disabled = true; input.value = '';
    addMsg('user', text);
    chatHistory.push({ role: 'user', content: text });
    showTyping();
    try {
      const reply = await askBot(chatHistory.slice(-20));
      hideTyping();
      addMsg('bot', reply);
      chatHistory.push({ role: 'assistant', content: reply });
    } catch (err) {
      hideTyping();
      addMsg('bot', '⚠️ Could not reach the server. Make sure Flask is running at localhost:5000 and try again.');
      console.error('ThyroBot:', err);
    } finally {
      isBusy = false; sendBtn.disabled = false; input.focus();
    }
  }

  bubble.addEventListener('click', toggle);
  closeBtn.addEventListener('click', toggle);
  sendBtn.addEventListener('click', () => send(input.value));
  input.addEventListener('keydown', e => { if (e.key==='Enter' && !e.shiftKey) { e.preventDefault(); send(input.value); } });
  document.querySelectorAll('.quick-btn').forEach(btn => {
    btn.addEventListener('click', () => { if (!isOpen) toggle(); setTimeout(() => send(btn.dataset.msg), isOpen ? 0 : 420); });
  });
  document.addEventListener('click', e => { if (isOpen && !win.contains(e.target) && !bubble.contains(e.target)) toggle(); });
  document.addEventListener('keydown', e => { if (e.key==='Escape' && isOpen) toggle(); });

})();
