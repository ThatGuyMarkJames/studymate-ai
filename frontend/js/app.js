let state = {
  subjects:        [],
  activeSubject:   null,
  currentQuiz:     null,
  currentQuestion: 0,
  quizAnswers:     {},
  quizStartTime:   null,
  timerInterval:   null,
  dsaProgress:     null,
  fcDeck:          null,
  fcIndex:         0,
  fcFlipped:       false,
  notesSubjectId:  null,
  pomodoro: {
    running:    false,
    mode:       'focus',
    remaining:  25 * 60,
    sessions:   0,
    interval:   null,
  },
};

document.addEventListener('DOMContentLoaded', () => {
  const token = getToken();
  const user  = getUser();
  if (token && user) {
    showApp(user);
    loadDashboard();
  } else {
    showAuth();
  }
});

function showAuth() {
  document.getElementById('auth-screen').classList.remove('hidden');
  document.getElementById('app').classList.add('hidden');
}

function showApp(user) {
  document.getElementById('auth-screen').classList.add('hidden');
  document.getElementById('app').classList.remove('hidden');
  updateSidebarUser(user);
}

function updateSidebarUser(user) {
  if (!user) return;
  document.getElementById('sidebar-name').textContent   = user.full_name || user.username;
  document.getElementById('sidebar-avatar').textContent = (user.full_name || user.username)[0].toUpperCase();
}

function switchAuthTab(tab) {
  document.querySelectorAll('.auth-tab').forEach((t, i) => t.classList.toggle('active', (i === 0) === (tab === 'login')));
  document.getElementById('login-form').classList.toggle('hidden',  tab !== 'login');
  document.getElementById('signup-form').classList.toggle('hidden', tab !== 'signup');
}

async function handleLogin(e) {
  e.preventDefault();
  const btn = document.getElementById('login-btn');
  const err = document.getElementById('login-error');
  err.classList.add('hidden');
  btn.innerHTML = '<span class="loading-spinner"></span>';
  btn.disabled  = true;
  try {
    const data = await API.login({
      email:    document.getElementById('login-email').value,
      password: document.getElementById('login-password').value,
    });
    setToken(data.access_token);
    setUser(data.user);
    showApp(data.user);
    loadDashboard();
  } catch(ex) {
    err.textContent = ex.message;
    err.classList.remove('hidden');
  } finally {
    btn.innerHTML = '<span>Sign In</span>';
    btn.disabled  = false;
  }
}

async function handleSignup(e) {
  e.preventDefault();
  const btn = document.getElementById('signup-btn');
  const err = document.getElementById('signup-error');
  err.classList.add('hidden');
  btn.innerHTML = '<span class="loading-spinner"></span>';
  btn.disabled  = true;
  try {
    const data = await API.signup({
      username:  document.getElementById('signup-username').value,
      email:     document.getElementById('signup-email').value,
      full_name: document.getElementById('signup-name').value,
      password:  document.getElementById('signup-password').value,
    });
    setToken(data.access_token);
    setUser(data.user);
    showApp(data.user);
    loadDashboard();
  } catch(ex) {
    err.textContent = ex.message;
    err.classList.remove('hidden');
  } finally {
    btn.innerHTML = '<span>Create Account</span>';
    btn.disabled  = false;
  }
}

function logout() {
  clearToken();
  state = {
    subjects: [], activeSubject: null, currentQuiz: null, currentQuestion: 0,
    quizAnswers: {}, quizStartTime: null, timerInterval: null, dsaProgress: null,
    fcDeck: null, fcIndex: 0, fcFlipped: false, notesSubjectId: null,
    pomodoro: { running: false, mode: 'focus', remaining: 25 * 60, sessions: 0, interval: null },
  };
  showAuth();
}

function navigateTo(page) {
  document.querySelectorAll('.page').forEach(p => { p.classList.remove('active'); p.classList.add('hidden'); });
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.getElementById(`page-${page}`).classList.remove('hidden');
  document.getElementById(`page-${page}`).classList.add('active');
  document.querySelector(`[data-page="${page}"]`).classList.add('active');

  if (page === 'dashboard')  loadDashboard();
  if (page === 'study')      loadStudyPage();
  if (page === 'flashcards') loadFlashcardsPage();
  if (page === 'quiz')       loadQuizPage();
  if (page === 'dsa')        loadDSAPage();
  if (page === 'notes')      loadNotesPage();
}

async function loadDashboard() {
  try {
    const user    = getUser();
    const hour    = new Date().getHours();
    const greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';
    document.getElementById('dash-greeting').textContent = `${greeting}, ${user?.full_name?.split(' ')[0] || user?.username}! 👋`;

    const [subjects, quizStats, dsaProgress] = await Promise.allSettled([
      API.getSubjects(),
      API.getQuizStats(),
      API.getDSAProgress(),
    ]);

    if (subjects.status === 'fulfilled') {
      const subs = subjects.value || [];
      state.subjects = subs;
      document.getElementById('dash-subjects').textContent = subs.length;
      document.getElementById('dash-docs').textContent     = subs.reduce((acc, s) => acc + (s.doc_count || 0), 0);

      const recentEl = document.getElementById('dash-recent-subjects');
      if (subs.length === 0) {
        recentEl.innerHTML = '<p class="empty-state">No subjects yet. Create one in Study Chat!</p>';
      } else {
        recentEl.innerHTML = subs.slice(0, 4).map(s => `
          <div class="subj-pill">
            <div class="subj-dot" style="background:${s.color}"></div>
            <div class="subj-info">
              <div>${s.name}</div>
              <div class="subj-docs">${s.doc_count} doc${s.doc_count !== 1 ? 's' : ''}</div>
            </div>
          </div>`).join('');
      }
    }

    if (quizStats.status === 'fulfilled') {
      const qs  = quizStats.value;
      document.getElementById('dash-quizzes').textContent = qs.total_quizzes;
      document.getElementById('dash-quiz-stats').innerHTML = qs.total_quizzes === 0
        ? '<p class="empty-state">No quizzes taken yet.</p>'
        : `<div class="quiz-stat-row"><span>Avg Score</span><strong>${qs.avg_score}%</strong></div>
           <div class="quiz-stat-row"><span>Best Score</span><strong>${qs.best_score}%</strong></div>
           <div class="quiz-stat-row"><span>Total Quizzes</span><strong>${qs.total_quizzes}</strong></div>
           ${qs.weak_areas.length ? `<div class="weak-areas"><span>Weak areas:</span> ${qs.weak_areas.map(w => `<span class="weak-tag">${w}</span>`).join('')}</div>` : ''}`;
    }

    if (dsaProgress.status === 'fulfilled') {
      updateDSAProgress(dsaProgress.value);
    }
  } catch(ex) {
    console.error('Dashboard load error:', ex);
  }
}

async function loadStudyPage() {
  try {
    const subjects = await API.getSubjects();
    state.subjects = subjects;
    renderSubjectList(subjects);
  } catch(ex) {
    showToast(ex.message, 'error');
  }
}

function renderSubjectList(subjects) {
  const el = document.getElementById('subject-list');
  if (subjects.length === 0) {
    el.innerHTML = '<p class="empty-state" style="padding:1rem">No subjects yet</p>';
    return;
  }
  el.innerHTML = subjects.map(s => `
    <div class="subj-item ${state.activeSubject?.id === s.id ? 'active' : ''}" onclick="selectSubject(${s.id})">
      <div class="subj-color-bar" style="background:${s.color}"></div>
      <div class="subj-item-info">
        <div class="subj-item-name">${escHtml(s.name)}</div>
        <div class="subj-item-docs">${s.doc_count} doc${s.doc_count !== 1 ? 's' : ''}</div>
      </div>
      <button class="subj-delete-btn" onclick="deleteSubject(event, ${s.id})" title="Delete">✕</button>
    </div>`).join('');
}

async function selectSubject(id) {
  const subj = state.subjects.find(s => s.id === id);
  if (!subj) return;
  state.activeSubject = subj;
  renderSubjectList(state.subjects);

  document.getElementById('study-empty').classList.add('hidden');
  document.getElementById('study-chat').classList.remove('hidden');
  document.getElementById('chat-subject-name').textContent       = subj.name;
  document.getElementById('chat-subject-dot').style.background   = subj.color;

  try {
    const history = await API.getChatHistory(id);
    const el      = document.getElementById('chat-messages');
    el.innerHTML  = '';
    history.forEach(m => appendChatMessage(m.role, m.content, m.sources));
    if (history.length === 0) {
      appendChatMessage('assistant', `Hi! I'm ready to help you study **${subj.name}**. Upload a document and ask me anything! 📚`);
    }
  } catch(ex) {
    console.error('History load error:', ex);
  }
}

function openNewSubjectModal() {
  openModal('New Subject', `
    <div class="field-group">
      <label>Subject Name</label>
      <input type="text" id="new-subj-name" placeholder="e.g. Data Structures" autofocus/>
    </div>
    <div class="field-group">
      <label>Description (optional)</label>
      <input type="text" id="new-subj-desc" placeholder="Brief description…"/>
    </div>
    <div class="field-group">
      <label>Color</label>
      <input type="color" id="new-subj-color" value="#6366f1"/>
    </div>
    <button class="btn-primary btn-full" onclick="createSubject()">Create Subject</button>
  `);
}

async function createSubject() {
  const name  = document.getElementById('new-subj-name').value.trim();
  const desc  = document.getElementById('new-subj-desc').value.trim();
  const color = document.getElementById('new-subj-color').value;
  if (!name) return;
  try {
    await API.createSubject({ name, description: desc, color });
    closeModal();
    await loadStudyPage();
    showToast('Subject created!', 'success');
  } catch(ex) {
    showToast(ex.message, 'error');
  }
}

async function deleteSubject(e, id) {
  e.stopPropagation();
  if (!confirm('Delete this subject and all its documents?')) return;
  try {
    await API.deleteSubject(id);
    if (state.activeSubject?.id === id) {
      state.activeSubject = null;
      document.getElementById('study-chat').classList.add('hidden');
      document.getElementById('study-empty').classList.remove('hidden');
    }
    await loadStudyPage();
    showToast('Subject deleted.', 'info');
  } catch(ex) {
    showToast(ex.message, 'error');
  }
}

function openUploadModal() {
  if (!state.activeSubject) { showToast('Select a subject first', 'error'); return; }
  openModal('Upload Document', `
    <p class="modal-hint">Supported formats: PDF, TXT (max 10MB)</p>
    <div class="upload-zone" id="upload-zone" onclick="document.getElementById('file-input').click()"
      ondrop="handleFileDrop(event)" ondragover="event.preventDefault()">
      <div class="upload-icon">📎</div>
      <p>Click to browse or drag & drop</p>
      <input type="file" id="file-input" accept=".pdf,.txt" class="hidden" onchange="handleFileSelect(this)"/>
    </div>
    <div id="upload-status"></div>
  `);
}

function handleFileDrop(e) {
  e.preventDefault();
  const file = e.dataTransfer.files[0];
  if (file) uploadFile(file);
}

function handleFileSelect(input) {
  const file = input.files[0];
  if (file) uploadFile(file);
}

async function uploadFile(file) {
  const status = document.getElementById('upload-status');
  status.innerHTML = '<div class="upload-progress">Uploading and processing…</div>';
  const form = new FormData();
  form.append('file', file);
  try {
    await API.uploadDoc(state.activeSubject.id, form);
    status.innerHTML = '<div class="upload-success">✅ Document processed successfully!</div>';
    const subs = await API.getSubjects();
    state.subjects = subs;
    state.activeSubject = subs.find(s => s.id === state.activeSubject.id) || state.activeSubject;
    renderSubjectList(subs);
    setTimeout(closeModal, 1200);
  } catch(ex) {
    status.innerHTML = `<div class="upload-error">❌ ${escHtml(ex.message)}</div>`;
  }
}

async function sendChatMessage() {
  const input = document.getElementById('chat-input');
  const msg   = input.value.trim();
  if (!msg || !state.activeSubject) return;
  input.value = '';
  input.style.height = 'auto';
  document.getElementById('chat-send-btn').disabled = true;
  appendChatMessage('user', msg);
  const el     = document.getElementById('chat-messages');
  const typing = document.createElement('div');
  typing.className = 'message assistant typing-bubble';
  typing.id = 'chat-typing';
  typing.innerHTML = `<div class="msg-avatar">⚡</div><div class="msg-body"><div class="msg-bubble"><span class="typing-dots"><span>●</span><span>●</span><span>●</span></span></div></div>`;
  el.appendChild(typing);
  el.scrollTop = el.scrollHeight;
  try {
    const res = await API.chat({ subject_id: state.activeSubject.id, message: msg });
    document.getElementById('chat-typing')?.remove();
    appendChatMessage('assistant', res.answer, res.sources);
  } catch(ex) {
    document.getElementById('chat-typing')?.remove();
    appendChatMessage('assistant', `Error: ${ex.message}`);
  } finally {
    document.getElementById('chat-send-btn').disabled = false;
    input.focus();
  }
}

function appendChatMessage(role, content, sources = []) {
  const el  = document.getElementById('chat-messages');
  const div = document.createElement('div');
  div.className = `message ${role}`;
  const avatar = role === 'user' ? (getUser()?.full_name?.[0] || 'U').toUpperCase() : '⚡';
  const srcHtml = sources?.length
    ? `<div class="msg-sources"><span>📄 Sources:</span>${sources.map(s => `<span class="source-chip">${escHtml(s.substring(0,60))}…</span>`).join('')}</div>`
    : '';
  div.innerHTML = `
    <div class="msg-avatar">${avatar}</div>
    <div class="msg-body">
      <div class="msg-bubble">${formatMd(content)}</div>
      ${srcHtml}
    </div>`;
  el.appendChild(div);
  el.scrollTop = el.scrollHeight;
}

function handleChatKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChatMessage(); }
}

async function clearChatHistory() {
  if (!state.activeSubject) return;
  if (!confirm('Clear all chat history for this subject?')) return;
  try {
    await API.clearChat(state.activeSubject.id);
    document.getElementById('chat-messages').innerHTML = '';
    appendChatMessage('assistant', `Chat cleared! Ask me anything about **${state.activeSubject.name}**.`);
  } catch(ex) {
    showToast(ex.message, 'error');
  }
}

function openNotesPanel() {
  if (!state.activeSubject) { showToast('Select a subject first', 'error'); return; }
  state.notesSubjectId = state.activeSubject.id;
  const panel  = document.getElementById('notes-panel');
  const layout = document.querySelector('#page-study .study-layout');
  panel.classList.remove('hidden');
  if (layout) layout.classList.add('notes-open');
  loadNotes();
}

function closeNotesPanel() {
  const panel  = document.getElementById('notes-panel');
  const layout = document.querySelector('#page-study .study-layout');
  panel.classList.add('hidden');
  if (layout) layout.classList.remove('notes-open');
}

async function loadNotes() {
  try {
    const notes = await API.getNotes(state.notesSubjectId);
    renderNotes(notes);
  } catch(ex) {
    showToast(ex.message, 'error');
  }
}

function renderNotes(notes) {
  const el = document.getElementById('notes-list');
  if (notes.length === 0) {
    el.innerHTML = '<p class="empty-state" style="padding:1rem;font-size:.85rem">No notes yet. Click + to add one.</p>';
    return;
  }
  el.innerHTML = notes.map(n => `
    <div class="note-card" style="background:${n.color}">
      <div class="note-card-header">
        <span class="note-card-title">${escHtml(n.title)}</span>
        <div class="note-card-actions">
          <button class="note-act-btn" onclick="editNote(${n.id}, '${escAttr(n.title)}', '${escAttr(n.content || '')}', '${n.color}')">✏</button>
          <button class="note-act-btn" onclick="deleteNote(${n.id})">✕</button>
        </div>
      </div>
      <div class="note-card-content">${escHtml(n.content || '')}</div>
    </div>`).join('');
}

function escAttr(s) {
  return String(s).replace(/'/g, "\\'").replace(/\n/g, '\\n');
}

function addNote() {
  document.getElementById('note-modal-title').textContent  = 'New Note';
  document.getElementById('note-title-input').value        = '';
  document.getElementById('note-content-input').value      = '';
  document.getElementById('note-color-value').value        = '#fef3c7';
  document.getElementById('note-edit-id').value            = '';
  document.querySelectorAll('.note-color-btn').forEach(b => b.classList.remove('selected'));
  document.querySelector('.note-color-btn[data-color="#fef3c7"]')?.classList.add('selected');
  document.getElementById('note-modal-overlay').classList.remove('hidden');
}

function editNote(id, title, content, color) {
  document.getElementById('note-modal-title').textContent  = 'Edit Note';
  document.getElementById('note-title-input').value        = title;
  document.getElementById('note-content-input').value      = content.replace(/\\n/g, '\n');
  document.getElementById('note-color-value').value        = color;
  document.getElementById('note-edit-id').value            = id;
  document.querySelectorAll('.note-color-btn').forEach(b => b.classList.toggle('selected', b.dataset.color === color));
  document.getElementById('note-modal-overlay').classList.remove('hidden');
}

function selectNoteColor(color, btn) {
  document.getElementById('note-color-value').value = color;
  document.querySelectorAll('.note-color-btn').forEach(b => b.classList.remove('selected'));
  btn.classList.add('selected');
}

async function saveNote() {
  const title   = document.getElementById('note-title-input').value.trim();
  const content = document.getElementById('note-content-input').value.trim();
  const color   = document.getElementById('note-color-value').value;
  const editId  = document.getElementById('note-edit-id').value;
  if (!title) return;
  try {
    if (editId) {
      await API.updateNote(editId, { title, content, color });
    } else {
      await API.createNote({ subject_id: state.notesSubjectId, title, content, color });
    }
    closeNoteModal();
    if (state._notePageMode) {
      await filterNotesBySubject();
      state._notePageMode = false;
    } else {
      loadNotes();
    }
    showToast('Note saved!', 'success');
  } catch(ex) {
    showToast(ex.message, 'error');
  }
}

async function deleteNote(id) {
  if (!confirm('Delete this note?')) return;
  try {
    await API.deleteNote(id);
    loadNotes();
  } catch(ex) {
    showToast(ex.message, 'error');
  }
}

function closeNoteModal() {
  document.getElementById('note-modal-overlay').classList.add('hidden');
}

function handleNoteModalClick(e) {
  if (e.target === document.getElementById('note-modal-overlay')) closeNoteModal();
}

async function loadFlashcardsPage() {
  try {
    const subjects = await API.getSubjects();
    state.subjects  = subjects;
    const sel = document.getElementById('fc-subject-select');
    sel.innerHTML = '<option value="">Select a subject…</option>' +
      subjects.map(s => `<option value="${s.id}">${escHtml(s.name)}</option>`).join('');
  } catch(ex) {
    showToast(ex.message, 'error');
  }
}

async function loadDecksForSubject() {
  const sid = document.getElementById('fc-subject-select').value;
  if (!sid) { document.getElementById('fc-deck-list').innerHTML = ''; return; }
  try {
    const decks = await API.getDecks(sid);
    renderDeckList(decks);
  } catch(ex) {
    showToast(ex.message, 'error');
  }
}

function renderDeckList(decks) {
  const el = document.getElementById('fc-deck-list');
  if (decks.length === 0) { el.innerHTML = '<p class="empty-state" style="font-size:.8rem;padding:.5rem 0">No decks yet</p>'; return; }
  el.innerHTML = decks.map(d => `
    <div class="fc-deck-item" onclick="openDeck(${d.id})">
      <span class="fc-deck-name">${escHtml(d.title)}</span>
      <span class="fc-deck-count">${d.card_count} cards</span>
    </div>`).join('');
}

async function generateDeck() {
  const sid      = document.getElementById('fc-subject-select').value;
  const numCards = parseInt(document.getElementById('fc-num-cards').value) || 10;
  if (!sid) { showToast('Select a subject first', 'error'); return; }
  const btn = document.getElementById('fc-gen-btn');
  btn.innerHTML = '<span class="loading-spinner"></span>';
  btn.disabled  = true;
  try {
    const deck = await API.generateDeck({ subject_id: parseInt(sid), num_cards: numCards });
    showToast(`Generated ${deck.card_count} flashcards!`, 'success');
    loadDecksForSubject();
    openDeckData(deck);
  } catch(ex) {
    showToast(ex.message, 'error');
  } finally {
    btn.innerHTML = '<span>✨ Generate</span>';
    btn.disabled  = false;
  }
}

async function openDeck(deckId) {
  try {
    const deck = await API.getDeck(deckId);
    openDeckData(deck);
  } catch(ex) {
    showToast(ex.message, 'error');
  }
}

function openDeckData(deck) {
  state.fcDeck   = deck;
  state.fcIndex  = 0;
  state.fcFlipped = false;
  document.getElementById('fc-empty').classList.add('hidden');
  document.getElementById('fc-review').classList.remove('hidden');
  renderFCCard();
}

function renderFCCard() {
  const deck  = state.fcDeck;
  const card  = deck.cards[state.fcIndex];
  const total = deck.cards.length;
  const mastered = deck.cards.filter(c => c.mastered).length;

  document.getElementById('fc-deck-title').textContent   = deck.title;
  document.getElementById('fc-card-counter').textContent = `${state.fcIndex + 1} / ${total}`;
  document.getElementById('fc-mastered-count').textContent = `${mastered} mastered`;
  document.getElementById('fc-front-text').textContent   = card.front;
  document.getElementById('fc-back-text').textContent    = card.back;
  document.getElementById('fc-tag').textContent          = card.topic_tag || '';

  const masterBtn = document.getElementById('fc-master-btn');
  masterBtn.textContent  = card.mastered ? '★ Unmark' : '★ Mark Mastered';
  masterBtn.className    = `fc-action-btn ${card.mastered ? 'fc-action-unmaster' : 'fc-action-master'}`;

  state.fcFlipped = false;
  const inner = document.getElementById('fc-card-inner');
  inner.classList.remove('flipped');
}

function flipCard() {
  state.fcFlipped = !state.fcFlipped;
  document.getElementById('fc-card-inner').classList.toggle('flipped', state.fcFlipped);
}

function fcNext() {
  if (!state.fcDeck) return;
  state.fcIndex = (state.fcIndex + 1) % state.fcDeck.cards.length;
  renderFCCard();
}

function fcPrev() {
  if (!state.fcDeck) return;
  state.fcIndex = (state.fcIndex - 1 + state.fcDeck.cards.length) % state.fcDeck.cards.length;
  renderFCCard();
}

function fcSkip() {
  fcNext();
}

async function toggleMastered() {
  if (!state.fcDeck) return;
  const card    = state.fcDeck.cards[state.fcIndex];
  const newVal  = !card.mastered;
  try {
    await API.updateCard(card.id, { mastered: newVal });
    card.mastered = newVal;
    renderFCCard();
    showToast(newVal ? 'Marked as mastered! 🌟' : 'Unmarked', 'success');
  } catch(ex) {
    showToast(ex.message, 'error');
  }
}

async function deleteDeck() {
  if (!state.fcDeck) return;
  if (!confirm('Delete this deck and all its cards?')) return;
  try {
    await API.deleteDeck(state.fcDeck.id);
    state.fcDeck = null;
    document.getElementById('fc-review').classList.add('hidden');
    document.getElementById('fc-empty').classList.remove('hidden');
    loadDecksForSubject();
    showToast('Deck deleted.', 'info');
  } catch(ex) {
    showToast(ex.message, 'error');
  }
}

async function loadQuizPage() {
  try {
    const [subjects, stats] = await Promise.allSettled([API.getSubjects(), API.getQuizStats()]);
    if (subjects.status === 'fulfilled') {
      const subs = subjects.value || [];
      const sel  = document.getElementById('quiz-subject-select');
      sel.innerHTML = '<option value="">Select a subject…</option>' +
        subs.map(s => `<option value="${s.id}">${escHtml(s.name)}</option>`).join('');
    }
    if (stats.status === 'fulfilled') {
      const qs = stats.value;
      document.getElementById('quiz-stats-content').innerHTML = qs.total_quizzes === 0
        ? '<p class="empty-state">No quizzes taken yet.</p>'
        : `<div class="quiz-stat-row"><span>Total Quizzes</span><strong>${qs.total_quizzes}</strong></div>
           <div class="quiz-stat-row"><span>Average Score</span><strong>${qs.avg_score}%</strong></div>
           <div class="quiz-stat-row"><span>Best Score</span><strong>${qs.best_score}%</strong></div>
           ${qs.weak_areas.length ? `<div class="weak-areas"><span>Needs work:</span>${qs.weak_areas.map(w => `<span class="weak-tag">${escHtml(w)}</span>`).join('')}</div>` : ''}`;
    }
  } catch(ex) {
    console.error('Quiz page load error:', ex);
  }
}

async function generateQuiz() {
  const sid    = document.getElementById('quiz-subject-select').value;
  const num    = parseInt(document.getElementById('quiz-num').value);
  const diff   = document.getElementById('quiz-difficulty').value;
  const types  = [];
  if (document.getElementById('qt-mcq').checked)   types.push('mcq');
  if (document.getElementById('qt-short').checked) types.push('short');
  const errEl  = document.getElementById('quiz-gen-error');
  errEl.classList.add('hidden');

  if (!sid)          { errEl.textContent = 'Select a subject.';   errEl.classList.remove('hidden'); return; }
  if (!types.length) { errEl.textContent = 'Select question type.'; errEl.classList.remove('hidden'); return; }

  const btn = document.getElementById('quiz-gen-btn');
  btn.innerHTML = '<span class="loading-spinner"></span>';
  btn.disabled  = true;

  try {
    const quiz = await API.generateQuiz({ subject_id: parseInt(sid), num_questions: num, difficulty: diff, question_types: types, time_limit: 0 });
    state.currentQuiz     = quiz;
    state.currentQuestion = 0;
    state.quizAnswers     = {};
    state.quizStartTime   = Date.now();
    renderQuiz();
  } catch(ex) {
    errEl.textContent = ex.message;
    errEl.classList.remove('hidden');
  } finally {
    btn.innerHTML = '<span>🎯 Generate Quiz</span>';
    btn.disabled  = false;
  }
}

function renderQuiz() {
  document.getElementById('quiz-setup').classList.add('hidden');
  document.getElementById('quiz-active').classList.remove('hidden');
  renderQuestion();
}

function renderQuestion() {
  const quiz  = state.currentQuiz;
  const qi    = state.currentQuestion;
  const q     = quiz.questions[qi];
  const total = quiz.questions.length;

  document.getElementById('qpb-fill').style.width  = `${(qi / total) * 100}%`;
  document.getElementById('q-counter').textContent = `Question ${qi + 1} / ${total}`;
  document.getElementById('prev-btn').disabled     = qi === 0;
  document.getElementById('next-btn').textContent  = qi === total - 1 ? 'Submit Quiz' : 'Next →';

  const card  = document.getElementById('question-card');
  const saved = state.quizAnswers[q.id];

  if (q.question_type === 'mcq' && q.options?.length) {
    card.innerHTML = `
      <div class="q-text">${qi + 1}. ${escHtml(q.question_text)}</div>
      <div class="q-options">
        ${q.options.map((opt, i) => {
          const letter  = ['A','B','C','D'][i];
          const checked = saved === letter || saved === opt;
          return `<label class="q-option${checked ? ' selected' : ''}">
            <input type="radio" name="q${q.id}" value="${letter}" ${checked ? 'checked' : ''}
              onchange="saveAnswer(${q.id}, '${letter}', this.closest('.q-options'))">
            ${escHtml(opt)}
          </label>`;
        }).join('')}
      </div>`;
  } else {
    card.innerHTML = `
      <div class="q-text">${qi + 1}. ${escHtml(q.question_text)}</div>
      <div class="q-short">
        <textarea placeholder="Type your answer here…" oninput="saveAnswer(${q.id}, this.value)">${saved || ''}</textarea>
      </div>`;
  }
}

function saveAnswer(qid, val, optionsEl) {
  state.quizAnswers[qid] = val;
  if (optionsEl) {
    optionsEl.querySelectorAll('.q-option').forEach(o => o.classList.remove('selected'));
    optionsEl.querySelector('input:checked')?.closest('.q-option')?.classList.add('selected');
  }
}

function prevQuestion() {
  if (state.currentQuestion > 0) { state.currentQuestion--; renderQuestion(); }
}

async function nextQuestion() {
  const total = state.currentQuiz.questions.length;
  if (state.currentQuestion < total - 1) {
    state.currentQuestion++;
    renderQuestion();
  } else {
    await submitQuiz();
  }
}

async function submitQuiz() {
  const timeTaken = Math.round((Date.now() - state.quizStartTime) / 1000);
  const answers   = {};
  state.currentQuiz.questions.forEach(q => { answers[q.id] = state.quizAnswers[q.id] || ''; });
  document.getElementById('next-btn').innerHTML = '<span class="loading-spinner"></span>';
  document.getElementById('next-btn').disabled  = true;
  try {
    const result = await API.submitQuiz({ quiz_id: state.currentQuiz.id, answers, time_taken_sec: timeTaken });
    renderResults(result);
  } catch(ex) {
    showToast(ex.message, 'error');
    document.getElementById('next-btn').innerHTML = 'Submit Quiz';
    document.getElementById('next-btn').disabled  = false;
  }
}

function renderResults(result) {
  document.getElementById('quiz-active').classList.add('hidden');
  document.getElementById('quiz-results').classList.remove('hidden');
  document.getElementById('result-score').textContent    = `${result.percentage}%`;
  document.getElementById('result-feedback').textContent = result.feedback;
  document.getElementById('qpb-fill').style.width        = '100%';
  const det = document.getElementById('result-details');
  det.innerHTML = result.detailed.map(d => `
    <div class="result-item ${d.is_correct ? 'correct' : 'wrong'}">
      <div class="result-q">${escHtml(d.question)}</div>
      <div class="result-ans">
        Your answer: <span class="${d.is_correct ? 'correct-ans' : 'wrong-ans'}">${escHtml(d.user_answer || 'No answer')}</span>
        ${!d.is_correct ? ` → Correct: <span class="correct-ans">${escHtml(d.correct_answer)}</span>` : ''}
      </div>
      ${d.explanation ? `<div class="result-expl">💡 ${escHtml(d.explanation)}</div>` : ''}
    </div>`).join('');
  loadQuizPage();
}

function resetQuiz() {
  state.currentQuiz = null;
  document.getElementById('quiz-active').classList.add('hidden');
  document.getElementById('quiz-results').classList.add('hidden');
  document.getElementById('quiz-setup').classList.remove('hidden');
}

async function loadDSAPage() {
  try {
    const [progress, history, challenge] = await Promise.allSettled([
      API.getDSAProgress(),
      API.getDSAHistory(),
      API.getChallenge(),
    ]);
    if (progress.status  === 'fulfilled') updateDSAProgress(progress.value);
    if (history.status   === 'fulfilled') renderDSAHistory(history.value);
    if (challenge.status === 'fulfilled') renderChallenge(challenge.value);
    if (history.status === 'fulfilled' && !history.value?.length) {
      appendDSAMessage('assistant', `👋 Welcome to DSA Practice! I'm your DSA Mentor.\n\n**I can help you with:**\n- Explaining concepts (Arrays, Trees, Graphs, DP...)\n- Generating practice problems\n- Reviewing your solutions\n- Step-by-step walkthroughs\n\nPick a topic from the left, or just ask me anything! 🚀`);
    }
  } catch(ex) {
    console.error('DSA page load error:', ex);
  }
}

function updateDSAProgress(dp) {
  state.dsaProgress = dp;
  const pct = Math.max(2, Math.min(98, ((200 - dp.next_level_xp) / 200) * 100));
  document.getElementById('dsa-level-num').textContent  = dp.level;
  document.getElementById('dsa-xp-bar').style.width     = pct + '%';
  document.getElementById('dsa-xp-text').textContent    = `${dp.xp_points} / ${dp.level * 200} XP`;
  document.getElementById('dsa-streak').textContent     = dp.streak_days;
  document.getElementById('dsa-solved').textContent     = dp.problems_solved;
  const levels = ['Novice','Apprentice','Practitioner','Advanced','Expert','Master','Grandmaster'];
  document.getElementById('dsa-level-name').textContent = (levels[Math.min(dp.level - 1, levels.length - 1)] || 'Legend') + ' Coder';
  document.getElementById('sidebar-level').textContent  = `Level ${dp.level}`;
  document.getElementById('dash-streak').textContent    = dp.streak_days;
}

function renderDSAHistory(history) {
  const el = document.getElementById('dsa-messages');
  el.innerHTML = '';
  history.forEach(msg => appendDSAMessage(msg.role, msg.content));
  el.scrollTop = el.scrollHeight;
}

function appendDSAMessage(role, content, meta = {}) {
  const el  = document.getElementById('dsa-messages');
  const div = document.createElement('div');
  div.className = `message ${role}`;
  const avatar = role === 'user' ? (getUser()?.full_name?.[0] || 'U').toUpperCase() : '💻';
  let extra = '';
  if (meta.xp_gained) extra = `<span class="xp-toast">+${meta.xp_gained} XP</span>`;
  div.innerHTML = `
    <div class="msg-avatar">${avatar}</div>
    <div class="msg-body">
      <div class="msg-bubble">${formatMd(content)}</div>
      ${extra}
    </div>`;
  el.appendChild(div);
  el.scrollTop = el.scrollHeight;
}

async function sendDSAMessage() {
  const input = document.getElementById('dsa-input');
  const msg   = input.value.trim();
  if (!msg) return;
  input.value = '';
  input.style.height = 'auto';
  document.getElementById('dsa-send-btn').disabled = true;
  appendDSAMessage('user', msg);
  const el     = document.getElementById('dsa-messages');
  const typing = document.createElement('div');
  typing.className = 'message assistant typing-bubble';
  typing.id = 'dsa-typing';
  typing.innerHTML = `<div class="msg-avatar">💻</div><div class="msg-body"><div class="msg-bubble"><span class="typing-dots"><span>●</span><span>●</span><span>●</span></span></div></div>`;
  el.appendChild(typing);
  el.scrollTop = el.scrollHeight;
  try {
    const res = await API.dsaChat({ message: msg });
    document.getElementById('dsa-typing')?.remove();
    appendDSAMessage('assistant', res.answer, { xp_gained: res.xp_gained });
    updateDSAProgress({ ...state.dsaProgress, xp_points: res.total_xp, level: res.level, next_level_xp: res.level * 200 - res.total_xp });
    if (res.challenge_done) { showToast('🎉 Daily Challenge Completed! Bonus XP awarded!', 'success'); await refreshChallenge(); }
  } catch(ex) {
    document.getElementById('dsa-typing')?.remove();
    appendDSAMessage('assistant', `Error: ${ex.message}`);
  } finally {
    document.getElementById('dsa-send-btn').disabled = false;
  }
}

function handleDSAKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendDSAMessage(); }
}

function askDSATopic(topic) {
  document.getElementById('dsa-input').value = `Explain ${topic} with examples and common interview problems`;
  sendDSAMessage();
}

function renderChallenge(ch) {
  const el = document.getElementById('challenge-content');
  if (!ch) { el.innerHTML = '<p class="challenge-desc">No active challenge. Click "New" to start!</p>'; return; }
  const pct = Math.round((ch.current_count / ch.target_count) * 100);
  el.innerHTML = `
    <p class="challenge-desc">${escHtml(ch.description)}</p>
    <div class="challenge-prog">
      <div class="challenge-bar-wrap"><div class="challenge-bar" style="width:${pct}%"></div></div>
      <span class="challenge-count">${ch.current_count}/${ch.target_count}</span>
    </div>
    <span class="challenge-xp">🏆 +${ch.xp_reward} XP on completion</span>`;
}

async function refreshChallenge() {
  try {
    const ch = await API.newChallenge();
    renderChallenge(ch);
    showToast('New challenge generated!', 'info');
  } catch(ex) {
    showToast(ex.message, 'error');
  }
}

async function clearDSAHistory() {
  if (!confirm('Clear all DSA chat history?')) return;
  try {
    await API.clearDSAChat();
    document.getElementById('dsa-messages').innerHTML = '';
    appendDSAMessage('assistant', 'Chat cleared! What would you like to practice today?');
  } catch(ex) {
    showToast(ex.message, 'error');
  }
}

function togglePomodoro() {
  const p = state.pomodoro;
  if (p.running) {
    clearInterval(p.interval);
    p.running = false;
    document.getElementById('pomo-start-btn').textContent = '▶';
  } else {
    p.running  = true;
    document.getElementById('pomo-start-btn').textContent = '⏸';
    p.interval = setInterval(tickPomodoro, 1000);
  }
}

function tickPomodoro() {
  const p = state.pomodoro;
  if (p.remaining <= 0) {
    clearInterval(p.interval);
    p.running = false;
    document.getElementById('pomo-start-btn').textContent = '▶';
    if (p.mode === 'focus') {
      p.sessions++;
      p.mode      = 'break';
      p.remaining = 5 * 60;
      document.getElementById('pomo-mode-label').textContent = 'Break Time';
      showToast('🍅 Focus session done! Take a 5-min break.', 'success');
    } else {
      p.mode      = 'focus';
      p.remaining = 25 * 60;
      document.getElementById('pomo-mode-label').textContent = 'Focus Session';
      showToast('Break over! Ready for the next session?', 'info');
    }
    document.getElementById('pomo-session-count').textContent = `${p.sessions} session${p.sessions !== 1 ? 's' : ''}`;
    updatePomodoroDisplay();
    return;
  }
  p.remaining--;
  updatePomodoroDisplay();
}

function updatePomodoroDisplay() {
  const p       = state.pomodoro;
  const total   = p.mode === 'focus' ? 25 * 60 : 5 * 60;
  const mins    = String(Math.floor(p.remaining / 60)).padStart(2, '0');
  const secs    = String(p.remaining % 60).padStart(2, '0');
  const pct     = 1 - (p.remaining / total);
  const circumference = 163.4;
  const offset  = circumference * (1 - pct);

  document.getElementById('pomo-time').textContent = `${mins}:${secs}`;
  document.getElementById('pomo-progress').style.strokeDashoffset = circumference - (circumference * pct);
}

function resetPomodoro() {
  const p = state.pomodoro;
  clearInterval(p.interval);
  p.running   = false;
  p.mode      = 'focus';
  p.remaining = 25 * 60;
  document.getElementById('pomo-start-btn').textContent   = '▶';
  document.getElementById('pomo-mode-label').textContent  = 'Focus Session';
  updatePomodoroDisplay();
}

function openModal(title, bodyHtml) {
  document.getElementById('modal-title').textContent = title;
  document.getElementById('modal-body').innerHTML    = bodyHtml;
  document.getElementById('modal-overlay').classList.remove('hidden');
}

function closeModal() {
  document.getElementById('modal-overlay').classList.add('hidden');
}

function handleModalClick(e) {
  if (e.target === document.getElementById('modal-overlay')) closeModal();
}

let toastTimer;
function showToast(msg, type = 'info') {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className   = `toast ${type}`;
  el.classList.remove('hidden');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.add('hidden'), 3500);
}

function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function formatMd(text) {
  // Extract fenced code blocks first so \n inside them aren't converted to <br>
  const blocks = [];
  let out = text.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) => {
    const i = blocks.length;
    blocks.push(`<pre data-lang="${escHtml(lang)}"><code>${escHtml(code.trim())}</code></pre>`);
    return `\x00BLOCK${i}\x00`;
  });

  // Escape HTML on the remaining text, then apply inline markdown
  out = escHtml(out)
    .replace(/`([^`\n]+)`/g,         '<code>$1</code>')
    .replace(/\*\*([^*\n]+)\*\*/g,   '<strong>$1</strong>')
    .replace(/\*([^*\n]+)\*/g,       '<em>$1</em>')
    .replace(/^#{1,3}\s+(.+)$/gm,    '<strong>$1</strong>')
    .replace(/^[\-\*]\s+(.+)$/gm,    '&bull; $1')
    .replace(/\n/g, '<br>');

  // Reinsert code blocks
  out = out.replace(/\x00BLOCK(\d+)\x00/g, (_, i) => blocks[parseInt(i)]);
  return out;
}

function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 120) + 'px';
}

document.addEventListener('keydown', e => {
  if (e.key === 'Escape') { closeModal(); closeNoteModal(); }
  if (e.key === 'ArrowRight' && state.fcDeck && document.getElementById('page-flashcards').classList.contains('active')) fcNext();
  if (e.key === 'ArrowLeft'  && state.fcDeck && document.getElementById('page-flashcards').classList.contains('active')) fcPrev();
  if (e.key === ' ' && state.fcDeck && document.getElementById('page-flashcards').classList.contains('active')) { e.preventDefault(); flipCard(); }
});

/* ── NOTES STANDALONE PAGE ─────────────────────────────────── */
async function loadNotesPage() {
  try {
    const subjects = await API.getSubjects();
    state.subjects  = subjects;
    const filter    = document.getElementById('notes-subject-filter');
    const currVal   = filter.value;
    filter.innerHTML = '<option value="">All Subjects</option>' +
      subjects.map(s => `<option value="${s.id}"${s.id == currVal ? ' selected' : ''}>${escHtml(s.name)}</option>`).join('');
    await filterNotesBySubject();
  } catch(ex) {
    showToast(ex.message, 'error');
  }
}

async function filterNotesBySubject() {
  const sid  = document.getElementById('notes-subject-filter').value;
  const grid = document.getElementById('notes-page-grid');
  grid.innerHTML = '<p class="empty-state">Loading…</p>';
  try {
    let allNotes = [];
    if (sid) {
      allNotes = await API.getNotes(parseInt(sid));
    } else {
      const results = await Promise.allSettled(state.subjects.map(s => API.getNotes(s.id)));
      results.forEach(r => { if (r.status === 'fulfilled') allNotes.push(...r.value); });
    }
    if (allNotes.length === 0) {
      grid.innerHTML = '<p class="empty-state" style="padding:2rem">No notes yet. Click “New Note” to get started!</p>';
      return;
    }
    grid.innerHTML = allNotes.map(n => {
      const subj = state.subjects.find(s => s.id === n.subject_id);
      return `
        <div class="note-page-card" style="background:${n.color}">
          <div class="note-page-card-subj">${subj ? escHtml(subj.name) : 'Unknown'}</div>
          <div class="note-page-card-title">${escHtml(n.title)}</div>
          <div class="note-page-card-content">${escHtml(n.content || '')}</div>
          <div class="note-page-card-actions">
            <button onclick="editGlobalNote(${n.id},'${escAttr(n.title)}','${escAttr(n.content||'')}','${n.color}',${n.subject_id})" title="Edit">✏</button>
            <button onclick="deleteGlobalNote(${n.id})" title="Delete">✕</button>
          </div>
        </div>`;
    }).join('');
  } catch(ex) {
    showToast(ex.message, 'error');
  }
}

function openGlobalNoteModal() {
  if (!state.subjects.length) { showToast('Create a subject first in Study Chat', 'error'); return; }
  const sid = document.getElementById('notes-subject-filter')?.value;
  state.notesSubjectId  = sid ? parseInt(sid) : state.subjects[0].id;
  state._notePageMode   = true;
  document.getElementById('note-modal-title').textContent = 'New Note';
  document.getElementById('note-title-input').value       = '';
  document.getElementById('note-content-input').value     = '';
  document.getElementById('note-color-value').value       = '#fef3c7';
  document.getElementById('note-edit-id').value           = '';
  document.querySelectorAll('.note-color-btn').forEach(b => b.classList.remove('selected'));
  document.querySelector('.note-color-btn[data-color="#fef3c7"]')?.classList.add('selected');
  document.getElementById('note-modal-overlay').classList.remove('hidden');
}

function editGlobalNote(id, title, content, color, subjectId) {
  state.notesSubjectId = subjectId;
  state._notePageMode  = true;
  editNote(id, title, content, color);
}

async function deleteGlobalNote(id) {
  if (!confirm('Delete this note?')) return;
  try {
    await API.deleteNote(id);
    await filterNotesBySubject();
    showToast('Note deleted.', 'info');
  } catch(ex) {
    showToast(ex.message, 'error');
  }
}

