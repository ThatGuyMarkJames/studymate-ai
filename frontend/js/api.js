const BASE = '/api';

function getToken() { return localStorage.getItem('sm_token'); }
function setToken(t) { localStorage.setItem('sm_token', t); }
function getUser()  { try { return JSON.parse(localStorage.getItem('sm_user')); } catch { return null; } }
function setUser(u) { localStorage.setItem('sm_user', JSON.stringify(u)); }
function clearToken() { localStorage.removeItem('sm_token'); localStorage.removeItem('sm_user'); }

async function apiFetch(path, options = {}) {
  const token = getToken();
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const res = await fetch(BASE + path, { ...options, headers });
  if (!res.ok) {
    let msg = `Request failed (${res.status})`;
    try { const d = await res.json(); msg = d.detail || JSON.stringify(d); } catch {}
    throw new Error(msg);
  }
  if (res.status === 204) return null;
  return res.json();
}

const API = {
  login:         (d) => apiFetch('/auth/login',  { method: 'POST', body: JSON.stringify(d) }),
  signup:        (d) => apiFetch('/auth/signup', { method: 'POST', body: JSON.stringify(d) }),
  me:            ()  => apiFetch('/auth/me'),

  getSubjects:   ()  => apiFetch('/study/subjects'),
  createSubject: (d) => apiFetch('/study/subjects', { method: 'POST', body: JSON.stringify(d) }),
  deleteSubject: (id) => apiFetch(`/study/subjects/${id}`, { method: 'DELETE' }),

  uploadDoc:     (subjectId, form) => {
    const token = getToken();
    return fetch(`${BASE}/study/subjects/${subjectId}/documents`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      body: form,
    }).then(async r => {
      if (!r.ok) { const d = await r.json(); throw new Error(d.detail || 'Upload failed'); }
      return r.json();
    });
  },
  getDocs:       (sid) => apiFetch(`/study/subjects/${sid}/documents`),
  deleteDoc:     (sid, did) => apiFetch(`/study/subjects/${sid}/documents/${did}`, { method: 'DELETE' }),

  chat:          (d)   => apiFetch('/study/chat', { method: 'POST', body: JSON.stringify(d) }),
  getChatHistory:(sid) => apiFetch(`/study/chat/${sid}/history`),
  clearChat:     (sid) => apiFetch(`/study/chat/${sid}/history`, { method: 'DELETE' }),

  generateQuiz:  (d)   => apiFetch('/quiz/generate',  { method: 'POST', body: JSON.stringify(d) }),
  submitQuiz:    (d)   => apiFetch('/quiz/submit',     { method: 'POST', body: JSON.stringify(d) }),
  getQuizHistory:()    => apiFetch('/quiz/history'),
  getQuizStats:  ()    => apiFetch('/quiz/stats'),

  getDSAProgress:()    => apiFetch('/dsa/progress'),
  getDSAHistory: ()    => apiFetch('/dsa/chat/history'),
  dsaChat:       (d)   => apiFetch('/dsa/chat',           { method: 'POST', body: JSON.stringify(d) }),
  clearDSAChat:  ()    => apiFetch('/dsa/chat/history',   { method: 'DELETE' }),
  getChallenge:  ()    => apiFetch('/dsa/challenge/active'),
  newChallenge:  ()    => apiFetch('/dsa/challenge/new',  { method: 'POST' }),

  generateDeck:  (d)   => apiFetch('/flashcards/generate',         { method: 'POST', body: JSON.stringify(d) }),
  getDecks:      (sid) => apiFetch(`/flashcards/subject/${sid}`),
  getDeck:       (did) => apiFetch(`/flashcards/deck/${did}`),
  updateCard:    (cid, d) => apiFetch(`/flashcards/card/${cid}`, { method: 'PATCH', body: JSON.stringify(d) }),
  deleteDeck:    (did) => apiFetch(`/flashcards/deck/${did}`,    { method: 'DELETE' }),

  getNotes:      (sid) => apiFetch(`/notes/subject/${sid}`),
  createNote:    (d)   => apiFetch('/notes/',              { method: 'POST',   body: JSON.stringify(d) }),
  updateNote:    (id, d) => apiFetch(`/notes/${id}`,       { method: 'PUT',    body: JSON.stringify(d) }),
  deleteNote:    (id)  => apiFetch(`/notes/${id}`,         { method: 'DELETE' }),
};
