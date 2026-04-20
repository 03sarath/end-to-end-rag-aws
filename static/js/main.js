'use strict';

let sessionId = '';
let cardCounter = 0;

const chatWrapper = document.getElementById('chatWrapper');
const userInput  = document.getElementById('userInput');
const sendBtn    = document.getElementById('sendBtn');

// ── Auto-resize textarea ────────────────────────────────────
userInput.addEventListener('input', () => {
  userInput.style.height = 'auto';
  userInput.style.height = Math.min(userInput.scrollHeight, 120) + 'px';
});

// ── Enter to send, Shift+Enter for newline ──────────────────
userInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

// ── Suggestion chips ────────────────────────────────────────
function sendSuggestion(btn) {
  userInput.value = btn.textContent.trim();
  hideSuggestions();
  sendMessage();
}

function hideSuggestions() {
  const s = document.getElementById('suggestions');
  if (s) s.style.display = 'none';
}

// ── Send message ────────────────────────────────────────────
async function sendMessage() {
  const query = userInput.value.trim();
  if (!query) return;

  hideSuggestions();
  appendUserMessage(query);
  userInput.value = '';
  userInput.style.height = 'auto';
  setBusy(true);

  const loadingRow = appendLoading();

  try {
    const payload = { query };
    if (sessionId) payload.session_id = sessionId;

    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    loadingRow.remove();

    if (!res.ok) {
      appendError(data.error || 'Something went wrong. Please try again.');
      return;
    }

    if (data.session_id) sessionId = data.session_id;
    appendAiResponse(data.message, data.packages || []);

  } catch (err) {
    loadingRow.remove();
    appendError('Network error. Please check your connection and try again.');
  } finally {
    setBusy(false);
    scrollToBottom();
  }
}

// ── DOM helpers ─────────────────────────────────────────────
function appendUserMessage(text) {
  const row = document.createElement('div');
  row.className = 'msg-row msg-user';
  row.innerHTML = `<div class="msg-bubble">${escapeHtml(text)}</div>`;
  chatWrapper.appendChild(row);
  scrollToBottom();
}

function appendLoading() {
  const row = document.createElement('div');
  row.className = 'msg-row msg-ai msg-loading';
  row.innerHTML = `
    <div class="msg-avatar"><i class="bi bi-robot"></i></div>
    <div class="msg-bubble">
      <div class="dots-anim"><span></span><span></span><span></span></div>
      Searching packages…
    </div>`;
  chatWrapper.appendChild(row);
  scrollToBottom();
  return row;
}

function appendError(msg) {
  const row = document.createElement('div');
  row.className = 'msg-row msg-ai msg-error';
  row.innerHTML = `
    <div class="msg-avatar"><i class="bi bi-robot"></i></div>
    <div class="msg-bubble"><i class="bi bi-exclamation-circle me-2"></i>${escapeHtml(msg)}</div>`;
  chatWrapper.appendChild(row);
}

function appendAiResponse(message, packages) {
  const row = document.createElement('div');
  row.className = 'msg-row msg-ai';

  const cardsHtml = packages.length ? buildPackagesHtml(packages) : '';

  row.innerHTML = `
    <div class="msg-avatar"><i class="bi bi-robot"></i></div>
    <div class="msg-bubble">
      <p>${escapeHtml(message)}</p>
      ${cardsHtml}
    </div>`;

  chatWrapper.appendChild(row);
}

// ── Package card builder ────────────────────────────────────
function buildPackagesHtml(packages) {
  const sorted = [...packages].sort((a, b) => (a.price || 0) - (b.price || 0));
  const cards  = sorted.map((pkg) => buildCard(pkg, cardCounter++)).join('');
  return `<div class="packages-grid">${cards}</div>`;
}

function buildCard(pkg, idx) {
  const targetBadge = buildTargetBadge(pkg.target);
  const testsHtml   = buildTestsSection(pkg.tests, idx);
  const consultHtml = buildConsultSection(pkg.consultations);
  const addonsHtml  = buildAddonsSection(pkg.optional_addons);

  return `
    <div class="pkg-card">
      <div class="pkg-card-header">
        <div>
          <div class="pkg-hospital">
            <i class="bi bi-hospital"></i>
            ${escapeHtml(pkg.hospital)}
          </div>
          <div class="pkg-name">${escapeHtml(pkg.package_name)}</div>
        </div>
        <div class="pkg-meta">
          <div class="pkg-price">${escapeHtml(pkg.price_display || '₹' + pkg.price)}</div>
          ${targetBadge}
        </div>
      </div>
      <div class="pkg-card-body">
        ${consultHtml}
        ${testsHtml}
        ${addonsHtml}
      </div>
    </div>`;
}

function buildTargetBadge(target) {
  if (!target) return '';
  const t = target.toLowerCase();
  let cls = 'badge-all';
  let icon = 'bi-people';
  if (t.includes('women') || t.includes('woman') || t.includes('female')) { cls = 'badge-women'; icon = 'bi-gender-female'; }
  else if (t.includes('men') || t.includes('male'))  { cls = 'badge-men';   icon = 'bi-gender-male'; }
  else if (t.includes('child') || t.includes('kid')) { cls = 'badge-children'; icon = 'bi-emoji-smile'; }
  return `<span class="pkg-target-badge ${cls}"><i class="bi ${icon}"></i>${escapeHtml(target)}</span>`;
}

function buildTestsSection(tests, idx) {
  if (!tests || !tests.length) return '';
  const id = `tests-${idx}`;
  const items = tests.map(t => `<div class="test-item">${escapeHtml(t)}</div>`).join('');
  return `
    <button class="tests-toggle" onclick="toggleSection(this, '${id}')">
      <span><i class="bi bi-clipboard2-pulse me-2"></i>Tests Included <span class="tests-count">(${tests.length})</span></span>
      <i class="bi bi-chevron-down toggle-icon"></i>
    </button>
    <div class="tests-list" id="${id}">${items}</div>`;
}

function buildConsultSection(consults) {
  if (!consults || !consults.length) return '';
  const chips = consults.map(c =>
    `<span class="consult-chip"><i class="bi bi-person-badge"></i>${escapeHtml(c)}</span>`
  ).join('');
  return `
    <div style="padding:8px 0 4px;">
      <div style="font-size:.78rem;font-weight:700;color:#065f46;text-transform:uppercase;letter-spacing:.05em;margin-bottom:6px;">
        <i class="bi bi-person-check me-1"></i>Consultations
      </div>
      <div class="consult-list">${chips}</div>
    </div>`;
}

function buildAddonsSection(addons) {
  if (!addons || !addons.length) return '';
  const rows = addons.map(a =>
    `<div class="addon-item">
       <span>${escapeHtml(a.name)}</span>
       <span class="addon-price">+₹${Number(a.price).toLocaleString('en-IN')}</span>
     </div>`
  ).join('');
  return `
    <div class="addons-section">
      <div class="addons-title"><i class="bi bi-plus-circle me-1"></i>Optional Add-ons</div>
      ${rows}
    </div>`;
}

// ── Toggle collapsible sections ─────────────────────────────
function toggleSection(btn, targetId) {
  const panel = document.getElementById(targetId);
  const isOpen = panel.classList.toggle('open');
  btn.classList.toggle('open', isOpen);
}

// ── Utility ─────────────────────────────────────────────────
function setBusy(busy) {
  sendBtn.disabled    = busy;
  userInput.disabled  = busy;
}

function scrollToBottom() {
  const main = document.querySelector('.chat-main');
  main.scrollTop = main.scrollHeight;
}

function escapeHtml(str) {
  if (typeof str !== 'string') return String(str || '');
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}
