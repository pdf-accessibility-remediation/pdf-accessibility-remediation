/* webapp/panel.js: the run page's panel (review.html served by the app). Every button starts one of review_workorder.py's
   own commands as a job (webapp/runs.py); everything shown comes from /api/run/<run>, which reads the run folder.

   Accessibility (WCAG 2.1 AA): every action is a real button or link; status is said in words, never by colour alone;
   progress goes to one polite live region, only when a job's step changes and when it ends (never each log line);
   focus moves only after the person's own action (a click, or a page they opened), to the new heading or result. A job
   that ends in the background is announced, and focus stays where it is. */
(() => {
'use strict';
const box = document.getElementById('pdfrem-panel'); if (!box) return;
const RUN = box.dataset.run, ENC = RUN.split('/').map(encodeURIComponent).join('/'), API = '/api/run/' + ENC;
const q = new URLSearchParams(location.search);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const sn = id => /^\d+$/.test(String(id)) ? 'session ' + Number(id) : id === 'ai' ? 'the result applied without review' : String(id);
const cap = t => t.charAt(0).toUpperCase() + t.slice(1);

// "quiet": the person has not pressed a key or a pointer since their last action here. Only then may the page go on by
// itself to what that action asked for (the review page once it is up; the new result after Finish).
let quiet = true;
['keydown', 'pointerdown'].forEach(e => addEventListener(e, () => { quiet = false; }, true));
let want = q.get('after') === 'finish' ? 'result' : null;      // what the person's last action is waiting for
let st = null, setup = null, primed = false, offline = false, timer = null;
const seen = {};                                                // per job: the last step and status announced

box.innerHTML = '<section class="pp" aria-labelledby="pp-h"><h2 id="pp-h" tabindex="-1">Run actions</h2>' +
  '<div id="pp-body"><p>Loading…</p></div><p id="pp-msg" class="pp-msg" tabindex="-1" hidden></p>' +
  '<div id="pp-live" class="pp-sr" role="status" aria-live="polite" aria-atomic="true"></div></section>' +
  '<dialog class="pp-dlg" id="pp-dlg" aria-labelledby="pp-dlg-h"></dialog>';
const $ = id => document.getElementById(id);
const live = t => { const l = $('pp-live'); l.textContent = ''; setTimeout(() => { l.textContent = t; }, 50); };
function msg(text, ok, focus) {
  const m = $('pp-msg'); m.hidden = !text; m.textContent = text || ''; m.classList.toggle('pp-okmsg', !!ok);
  if (text && focus) m.focus();
}

async function api(path, body) {
  const r = await fetch(path, body === undefined ? { cache: 'no-store' } :
    { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  let b = {}; try { b = await r.json(); } catch (e) {}
  return [r.status, b];
}

// ---------------------------------------------------------------- the view
const STATUS = { queued: 'Waiting', running: 'Running', done: 'Done', failed: 'Failed', interrupted: 'Interrupted', 'needs-spend': 'Needs Spend again' };
function jobWords(j) {
  if (j.status === 'queued') return 'Waiting' + (j.position ? ': ' + ordinal(j.position) + ' in line' : '');
  if (j.status === 'running') {
    if (j.kind === 'review' && !j.past_finish) return j.url ? 'The review page is open' : 'Opening the review page';
    const cur = (j.steps || []).filter(s => s.state === 'running').pop();
    return 'Running' + (cur ? ': ' + cur.label : '');
  }
  if (j.status === 'done' && j.kind === 'review' && / stays open$/.test(j.outcome || '')) return 'Closed: the session stays open';
  if (j.status === 'failed') return 'Failed' + (j.exit != null ? ' (exit ' + j.exit + ')' : '');
  if (j.status === 'interrupted') return j.interrupted && j.interrupted.state === 'done' ? 'Done (the app lost track of the job)' : 'Interrupted: the job stopped without finishing';
  return STATUS[j.status] || j.status;
}
const ordinal = n => n + ({ 1: 'st', 2: 'nd', 3: 'rd' }[n % 100 > 10 && n % 100 < 14 ? 0 : n % 10] || 'th');
const jobTitle = j => j.what || ({ apply: 'Apply', review: 'Review', pin: 'Pin' }[j.kind] || j.kind);

function jobCard(j) {
  const lost = j.status === 'interrupted' && j.interrupted && j.interrupted.state === 'done';
  const cls = lost || j.status === 'done' ? ' pp-done' : j.status === 'failed' || j.status === 'interrupted' ? ' pp-failed' : '';
  let h = '<article class="pp-job" id="job-' + esc(j.id) + '" aria-labelledby="jh-' + esc(j.id) + '">' +
    '<h3 id="jh-' + esc(j.id) + '" tabindex="-1">' + esc(jobTitle(j)) + '</h3>' +
    '<p><span class="pp-state' + cls + '">' + esc(jobWords(j)) + '</span>' + (j.started ? ' <span class="pp-note">· started ' + esc(j.started.replace('T', ' ')) + '</span>' : '') + '</p>';
  const steps = j.steps || [];
  if (steps.length) h += '<ol class="pp-steps">' + steps.map(s => '<li' + (s.state === 'running' && j.status === 'running' ? ' aria-current="step"' : '') + '>' +
    esc(s.label) + ': ' + (s.state === 'done' ? 'done' + (s.time ? ', ' + esc(s.time) : '') : j.status === 'running' ? 'running' : 'did not finish') + '</li>').join('') + '</ol>';
  if (j.kind === 'review' && j.status === 'running' && !j.past_finish && j.url)
    h += '<div class="pp-row"><a class="pp-btn pp-primary" id="pp-open" href="' + esc(j.url) + '">Open the review page</a>' +
         '<button type="button" id="pp-stop" data-act="stop">Stop reviewing (the session stays open)</button></div>';
  if (j.outcome && j.status !== 'running') h += '<p><b>' + (j.status === 'done' ? 'Result' : 'Message') + ':</b> ' + esc(j.outcome) + '</p>';
  else if ((j.status === 'failed' || j.status === 'interrupted') && (j.tail || []).length) h += '<p><b>Last lines:</b></p><pre>' + esc(j.tail.slice(-6).join('\n')) + '</pre>';
  if (j.status === 'interrupted') h += '<p class="pp-note">' + esc(interruptedNote(j)) + '</p>';
  h += '<details id="log-' + esc(j.id) + '"><summary>Log and command</summary><p><code>' + esc(j.command) + '</code></p><pre id="logt-' + esc(j.id) + '">' + esc((j.tail || []).join('\n')) + '</pre></details>';
  return h + '</article>';
}
function interruptedNote(j) {                                   // what is left comes from the run's state on disk (runs.after_interrupt)
  if (j.interrupted) return j.interrupted.text;
  if (j.kind === 'pin') return 'Nothing was kept: Review again pins the run again.';
  return 'Start it again.';
}

function setupBlock() {
  if (!setup) return '';
  const miss = setup.filter(x => !x.ok), req = miss.filter(x => x.required);
  const sum = req.length ? 'Setup: ' + req.length + ' required tool' + (req.length > 1 ? 's' : '') + ' missing' :
              miss.length ? 'Setup: ready (tools for untagged books missing: ' + miss.length + ')' : 'Setup: every tool ready';
  return '<details id="pp-setup"><summary>' + esc(sum) + '</summary><ul>' + setup.map(x => '<li>' + (x.ok ? 'Ready' : x.required ? 'Missing (required)' : 'Missing') +
    ': ' + esc(x.name) + ' · ' + esc(x.detail) + (x.fix ? '<br>Fix: <code>' + esc(x.fix) + '</code>' : '') + '</li>').join('') + '</ul></details>';
}

function actions(s) {
  const lr = s.live_review, active = (s.jobs || []).filter(j => j.status === 'queued' || j.status === 'running');
  if (lr) return '';                                             // its own card has Open / Stop
  if (s.lock) return '<p>Another review of this run is running (process ' + esc(s.lock.pid) + ', ' + esc(s.lock.what) + ', since ' + esc(s.lock.since) +
                     '), probably from a terminal. The buttons come back when it ends.</p>';
  if (active.length) return '<p>A job for this run is ' + (active[0].status === 'running' ? 'running' : 'waiting') + ': ' + esc(jobTitle(active[0])) + '. One job at a time per run.</p>';
  let h = '<div class="pp-row">';
  const from = s.open ? null : s.latest ? sn(s.latest.id) : s.legacy_review ? 'the review recorded before sessions were kept' : 'the AI\'s decisions';
  h += s.open ? '<button type="button" class="pp-primary" id="pp-review" data-act="review">Continue review (' + esc(s.open.label) + ', open)</button>'
              : '<button type="button" class="pp-primary" id="pp-review" data-act="review">Review again (from ' + esc(from) + ')</button>';
  if (s.latest || s.open) h += '<button type="button" id="pp-ai" data-act="review" data-from="ai">Start over from the AI\'s decisions</button>';
  if (s.unapplied && !s.open) h += '<button type="button" id="pp-apply" data-act="apply">Apply ' + esc(s.unapplied.label) + '</button>';
  h += '</div>';
  if (!s.pinned) h += '<p class="pp-note">Review again first re-audits this run to pin it (free, a minute or more).</p>';
  return h;
}

function historyBlock(s) {
  const rows = s.sessions || [];
  let h = '<details id="pp-hist"><summary>Session history (' + rows.length + ')</summary>';
  if (!rows.length) h += '<p>' + (s.legacy_review ? 'Reviewed before sessions were kept: Review again records that review as session 1.' : 'Never reviewed: the result was applied without review.') + '</p>';
  else h += '<div class="pp-tw" tabindex="0" role="region" aria-label="Session history table"><table><caption>Review sessions of this run</caption><thead><tr>' +
    '<th scope="col">Session</th><th scope="col">Status</th><th scope="col">Reviewer</th><th scope="col">Date</th><th scope="col">Started from</th>' +
    '<th scope="col">Changes from the AI</th><th scope="col">Set in this session</th><th scope="col">Result</th><th scope="col">Action</th></tr></thead><tbody>' +
    rows.map(r => '<tr><th scope="row">' + esc(r.label) + (r.current ? ' (current)' : '') + '</th><td>' + esc(r.status) + (r.summary_only ? ' (summary only)' : r.inferred ? ' (inferred)' : '') +
      '</td><td>' + esc(r.reviewer || 'not recorded') + '</td><td>' + esc(r.date || (r.started || '').slice(0, 10) || 'not recorded') + '</td><td>' + esc(r.from_label) +
      '</td><td>' + esc(r.changes) + '</td><td>' + esc(r.since_start) + '</td><td>' + (r.current ? 'this page' :r.result ? '<a href="' + esc(r.result) + '">earlier result</a>' : 'none') +
      '</td><td>' + ((r.status === 'finished' || r.status === 'applied') && !s.live_review && !s.lock ? '<button type="button" id="pp-from-' + esc(r.id) + '" data-act="review" data-from="' + esc(r.id) + '">Review again from ' + esc(r.label) + '</button>' : '') +
      '</td></tr>').join('') + '</tbody></table></div>';
  if (s.ai_result) h += '<p><a href="' + esc(s.ai_result) + '">The result applied without review</a> (kept in reviews/versions/ai/).</p>';
  return h + '</details>';
}

function render() {
  const s = st, keepFocus = document.activeElement && document.activeElement.id, opened = [...box.querySelectorAll('details[open]')].map(d => d.id);
  const r = s.ready, ready = r.answer ? r.answer : r.text;
  let h = setupBlock() + '<h3 id="pp-cur" tabindex="-1">Current result: ' + esc(s.current.label) + '</h3>' +
    '<p><b>Ready to ship?</b> ' + esc(ready) + '</p>' + (r.lines.length ? '<ul>' + r.lines.map(l => '<li>' + esc(l) + '</li>').join('') + '</ul>' : '');
  if (s.pending) h += '<p>' + esc(sn(s.pending.session)) + ' is ' + esc(s.pending.status) + ' and not applied yet, so "Ready to ship?" says No until it is.</p>';
  h += actions(s);
  const shown = (s.jobs || []).slice().reverse().filter((j, i) => i < 3 || j.status === 'queued' || j.status === 'running');
  if (shown.length) h += '<h3>Jobs for this run</h3>' + shown.map(jobCard).join('');
  if (want === 'shown') h += '<div class="pp-row"><button type="button" class="pp-primary" id="pp-show" data-act="reload">Show the new result</button></div>';
  h += historyBlock(s) +'<details id="pp-cmd"><summary>The same from a terminal</summary><p>From pipeline/: <code>' + esc(s.commands.reopen) +
       '</code> · <code>' + esc(s.commands.sessions) + '</code></p></details>';
  $('pp-body').innerHTML = h;
  opened.forEach(id => { const d = $(id); if (d) d.open = true; });
  if (keepFocus && $(keepFocus) && box.contains($(keepFocus))) $(keepFocus).focus();
}

// ---------------------------------------------------------------- what the person does
box.addEventListener('click', async e => {
  const b = e.target.closest('button[data-act]'); if (!b) return;
  const act = b.dataset.act;
  if (act === 'reload') { location.replace(location.pathname + '?landed=1'); return; }
  msg('');
  try {
    let s, r;
    if (act === 'stop') { [s, r] = await api(API + '/stop', {}); if (s !== 200) return msg(r.error || 'Stop failed', false, true);
                          msg('Review page closed. Its session stays open: Continue review carries on with it.', true, true); return poll(); }
    if (act === 'apply') { [s, r] = await api(API + '/apply', {}); }
    else {
      const body = { from: b.dataset.from || null };
      if (st.open && b.dataset.from) {
        const ok = await confirmDlg('Start a new session?', cap(sn(st.open.id)) + ' is open (started ' + (st.open.started || '').replace('T', ' ') +
          '). Starting from ' + (b.dataset.from === 'ai' ? 'the AI\'s decisions' : sn(b.dataset.from)) + ' marks it abandoned; it is kept in reviews/sessions/' + st.open.id + '.json.',
          'Mark it abandoned and start', b);
        if (!ok) return;
        body.discard_open = true;
      }
      [s, r] = await api(API + '/review', body);
      if (s === 202) want = 'review';
    }
    if (s !== 202) return msg(r.error || 'The app refused this', false, true);
    quiet = true;                                                // set after this click's own keydown/pointerdown
    await poll(true);
    const hd = $('jh-' + r.job.id); if (hd) hd.focus();
  } catch (err) { msg('The app is not running: start it with python3 app.py, then try again.', false, true); }
});

function confirmDlg(title, text, yes, opener) {
  return new Promise(res => {
    const d = $('pp-dlg');
    d.innerHTML = '<h2 id="pp-dlg-h">' + esc(title) + '</h2><p>' + esc(text) + '</p><div><button type="button" class="pp-primary" value="yes">' + esc(yes) +
                  '</button><button type="button" value="no">Cancel</button></div>';
    const done = v => { d.close(); opener.focus(); res(v); };
    d.querySelectorAll('button').forEach(x => x.addEventListener('click', () => done(x.value === 'yes')));
    d.oncancel = ev => { ev.preventDefault(); done(false); };
    d.showModal(); d.querySelector('button[value=no]').focus();
  });
}

// ---------------------------------------------------------------- following the jobs
function announce(s) {
  for (const j of s.jobs || []) {
    const cur = (j.steps || []).filter(x => x.state === 'running').pop(), key = j.status + '|' + (cur ? cur.label : '') + '|' + (j.url || '') + '|' + !!j.past_finish;
    const was = seen[j.id]; seen[j.id] = key;
    if (!primed || was === key) continue;
    const t = jobTitle(j) + ' (' + RUN + ')';
    if (j.status === 'done') live(t + ': ' + (jobWords(j) === 'Done' ? 'done' + (j.outcome ? '. ' + j.outcome : '') : jobWords(j).toLowerCase()));
    else if (j.status === 'failed') live(t + ': failed' + (j.outcome ? '. ' + j.outcome : ''));
    else if (j.status === 'interrupted') live(t + ': ' + (j.interrupted ? jobWords(j).toLowerCase() + '. ' + j.interrupted.text : 'interrupted'));
    else if (j.kind === 'review' && j.url && !j.past_finish && (!was || !was.includes(j.url))) live(t + ': the review page is ready');
    else if (cur) live(t + ': ' + cur.label);
    else if (j.status === 'running' && (!was || was.startsWith('queued'))) live(t + ': started');
  }
  primed = true;
}

async function poll(force) {
  clearTimeout(timer);
  try {
    const [s, b] = await api(API);
    if (s !== 200) throw new Error(b.error || String(s));
    if (offline) { offline = false; const o = $('pp-offline'); if (o) o.remove(); live('The app is running again.'); }
    const before = st; st = b;
    announce(b);
    followUp(before, b);
    if (force || JSON.stringify(strip(before)) !== JSON.stringify(strip(b))) render();
    else refreshLogs(b);
  } catch (e) {
    if (!offline) {
      offline = true;
      const o = document.createElement('p'); o.id = 'pp-offline'; o.className = 'pp-offline';
      o.textContent = 'The app is not running, so this page cannot start or follow jobs. Start it from pipeline/ with python3 app.py; jobs already running carry on.';
      box.prepend(o); live(o.textContent);
    }
  }
  const busy = st && ((st.jobs || []).some(j => j.status === 'queued' || j.status === 'running') || st.live_review);
  timer = setTimeout(poll, busy ? 1000 : 5000);
}
const strip = s => s && Object.assign({}, s, { jobs: (s.jobs || []).map(j => Object.assign({}, j, { tail: null })), live_review: s.live_review && Object.assign({}, s.live_review, { tail: null }) });
function refreshLogs(s) {
  for (const j of s.jobs || []) { const p = $('logt-' + j.id); if (p && p.closest('details').open) p.textContent = (j.tail || []).join('\n'); }
}

function followUp(before, s) {
  const lr = s.live_review;
  if (want === 'review' && lr && lr.url && !lr.past_finish) {
    want = null;
    if (quiet) { location.assign(lr.url); return; }          // the person's Review again opens the review page
    live('The review page is ready: Open the review page.');
  }
  if (want === 'result' || want === 'result-wait') {
    const j = (s.jobs || []).slice().reverse().find(x => x.kind === 'review' || x.kind === 'apply');
    if (!j) return;
    if (want === 'result') {                                   // the page the person's Finish opened: focus its job's heading
      want = 'result-wait'; history.replaceState(null, '', location.pathname);
      setTimeout(() => { const hd = $('jh-' + j.id); if (hd) hd.focus(); }, 0);
    }
    if (j.status === 'done' || (j.interrupted && j.interrupted.state === 'done')) {
      if (quiet) { location.replace(location.pathname + '?landed=1'); return; }
      want = 'shown';                                           // background end: announced, focus stays; a button to load it
    } else if (j.status === 'failed' || j.status === 'interrupted') want = null;
  }
}

if (q.get('landed') === '1') history.replaceState(null, '', location.pathname);
api('/api/setup').then(([s, b]) => { if (s === 200) { setup = b; if (st) render(); } }).catch(() => {});
poll(true).then(() => {
  if (q.get('landed') === '1') { const h = $('pp-cur'); if (h) h.focus(); }
});
})();
