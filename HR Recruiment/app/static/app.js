const api = {
  get: (path) => fetch(path, { credentials: 'same-origin' }).then(async r => { if (!r.ok) throw new Error((await r.json()).detail || 'Request failed'); return r.json(); }),
  post: (path, body) => fetch(path, { method:'POST', credentials:'same-origin', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body) }).then(async r => { if (!r.ok) throw new Error((await r.json()).detail || 'Request failed'); return r.json(); })
};

let jobs = [];
let candidates = [];
const skills = value => value.split(',').map(item => item.trim()).filter(Boolean);
const escapeHtml = value => String(value || '').replace(/[&<>'"]/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
function showMessage(message) { window.alert(message); }

function renderJobs() {
  document.querySelector('#jobs').innerHTML = jobs.length ? jobs.map(job => `<div class="record"><strong>${escapeHtml(job.title)}</strong><span>${escapeHtml(job.department)} · ${escapeHtml(job.level)} · ${escapeHtml(job.work_arrangement)}</span><span>${job.required_skills.map(s => `<i class="tag">${escapeHtml(s)}</i>`).join('')}</span></div>`).join('') : '<p class="muted">No roles yet.</p>';
  document.querySelector('#screening-job').innerHTML = jobs.length ? jobs.map(job => `<option value="${job.id}">${escapeHtml(job.title)}</option>`).join('') : '<option value="">Create a role first</option>';
}

function renderCandidates() {
  document.querySelector('#candidates').innerHTML = candidates.length ? candidates.map(candidate => `<div class="record"><strong>${escapeHtml(candidate.full_name)}</strong><span>${candidate.skills.map(s => `<i class="tag">${escapeHtml(s)}</i>`).join('')}</span></div>`).join('') : '<p class="muted">No candidates yet.</p>';
  document.querySelector('#screening-candidate').innerHTML = candidates.length ? candidates.map(candidate => `<option value="${candidate.id}">${escapeHtml(candidate.full_name)}</option>`).join('') : '<option value="">Add a candidate first</option>';
}

function renderScreening(screening) {
  const evidence = screening.evidence.matched_required_skills || [];
  document.querySelector('#screening-result').classList.remove('empty');
  document.querySelector('#screening-result').innerHTML = `<div class="score">${screening.score}%</div><div class="badge">${escapeHtml(screening.recommendation)}</div><p><b>Method:</b> ${escapeHtml(screening.model_name)}</p><p><b>Matched requirements:</b> ${evidence.length ? evidence.map(escapeHtml).join(', ') : 'None evidenced'}</p><p><b>Gaps to validate:</b> ${screening.gaps.length ? screening.gaps.map(escapeHtml).join(', ') : 'None identified'}</p><p><b>Suggested questions:</b></p><ul>${screening.suggested_questions.map(q => `<li>${escapeHtml(q)}</li>`).join('')}</ul>`;
}

async function refresh() {
  try {
    [jobs, candidates] = await Promise.all([api.get('/jobs'), api.get('/candidates')]);
    const [screenings, status] = await Promise.all([api.get('/screenings'), api.get('/ml/status')]);
    document.querySelector('#job-count').textContent = jobs.length;
    document.querySelector('#candidate-count').textContent = candidates.length;
    document.querySelector('#screening-count').textContent = screenings.length;
    document.querySelector('#ml-status').textContent = status.trained ? 'ML model' : 'Baseline';
    renderJobs(); renderCandidates();
  } catch (error) {
    if (error.message === 'Authentication required.' || error.message.includes('session')) showLogin();
    else showMessage(error.message);
  }
}

function showApp() { document.querySelector('#login-view').hidden = true; document.querySelector('#app-view').hidden = false; refresh(); }
function showLogin() { document.querySelector('#login-view').hidden = false; document.querySelector('#app-view').hidden = true; }

document.querySelector('#login-form').addEventListener('submit', async event => {
  event.preventDefault();
  const payload = Object.fromEntries(new FormData(event.currentTarget).entries());
  try {
    await api.post('/auth/login', payload);
    event.currentTarget.reset();
    document.querySelector('#login-error').textContent = '';
    showApp();
  } catch (error) { document.querySelector('#login-error').textContent = error.message; }
});

document.querySelector('#logout-button').addEventListener('click', async () => { await api.post('/auth/logout', {}); showLogin(); });

document.querySelector('#job-form').addEventListener('submit', async event => {
  event.preventDefault(); const form = new FormData(event.currentTarget); const payload = Object.fromEntries(form.entries());
  payload.required_skills = skills(payload.required_skills); payload.preferred_skills = skills(payload.preferred_skills);
  try { await api.post('/jobs', payload); event.currentTarget.reset(); await refresh(); } catch (error) { showMessage(error.message); }
});

document.querySelector('#candidate-form').addEventListener('submit', async event => {
  event.preventDefault(); const form = new FormData(event.currentTarget); const payload = Object.fromEntries(form.entries()); payload.skills = skills(payload.skills);
  if (!payload.email) delete payload.email; if (!payload.source) delete payload.source;
  try { await api.post('/candidates', payload); event.currentTarget.reset(); await refresh(); } catch (error) { showMessage(error.message); }
});

document.querySelector('#screening-form').addEventListener('submit', async event => {
  event.preventDefault(); const form = new FormData(event.currentTarget);
  if (!form.get('job_id') || !form.get('candidate_id')) return showMessage('Create a role and candidate first.');
  try { renderScreening(await api.post('/screenings', Object.fromEntries(form.entries()))); await refresh(); } catch (error) { showMessage(error.message); }
});

fetch('/auth/me', { credentials: 'same-origin' }).then(r => r.ok ? showApp() : showLogin()).catch(() => showLogin());
