/* webapp/panel.js: the run page's panel (review.html served by the app), and the bar on an earlier result's dashboard.
   Every button starts one of review_workorder.py's own commands as a job (webapp/runs.py); everything shown comes from
   /api/run/<run>, which reads the run folder. No log lines or commands are shown: a failed job says why in plain words,
   and where its log is saved.

   Accessibility (WCAG 2.1 AA): every action is a real button or link; status is said in words, never by colour alone
   (the spinner beside a running step is decorative: hidden from screen readers, still under reduced motion); progress
   goes to one polite live region, only when a job's step changes and when it ends (never each log line); focus moves only
   after the person's own action (a click, or a page they opened), to the new heading or result. A job that ends in the
   background is announced, and focus stays where it is. */
(() => {
'use strict';
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const sn = id => /^\d+$/.test(String(id)) ? 'session ' + Number(id) : id === 'ai' ? 'the result applied without review' : String(id);
const cap = t => t.charAt(0).toUpperCase() + t.slice(1);
const $ = id => document.getElementById(id);
const encRun = run => run.split('/').map(encodeURIComponent).join('/');
async function api(path, body) {
  const r = await fetch(path, body === undefined ? { cache: 'no-store' } :
    { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  let b = {}; try { b = await r.json(); } catch (e) {}
  return [r.status, b];
}
function confirmDlg(title, text, yes, opener) {
  return new Promise(res => {
    const d = $('pp-dlg');
    d.innerHTML = '<h2 id="pp-dlg-h">' + esc(title) + '</h2><p>' + esc(text) + '</p><div><button type="button" class="pp-primary" value="yes">' + esc(yes) +
                  '</button><button type="button" value="no">Cancel</button></div>';
    const id = opener.id;                                       // a re-render while the dialog is open replaces the element
    const done = v => { d.close(); ($(id) || opener).focus(); res(v); };
    d.querySelectorAll('button').forEach(x => x.addEventListener('click', () => done(x.value === 'yes')));
    d.oncancel = ev => { ev.preventDefault(); done(false); };
    d.showModal(); d.querySelector('button[value=no]').focus();
  });
}
function abandonText(open, from) {
  return cap(sn(open.id)) + ' is open (started ' + (open.started || '').replace('T', ' ') + '). Starting from ' +
         (from === 'ai' ? 'the AI\'s decisions' : sn(from)) + ' marks it abandoned; it is kept in reviews/sessions/' + open.id + '.json.';
}

// ================================================================ an earlier result: the bar
const vbox = $('pdfrem-version');
if (vbox) {
  const RUN = vbox.dataset.run, SID = vbox.dataset.session, API = '/api/run/' + encRun(RUN), BASE = '/run/' + encRun(RUN) + '/';
  const what = SID === 'ai' ? 'the result applied without review' : 'an earlier result (' + sn(SID) + ')';
  vbox.innerHTML = '<nav class="pp pp-bar" aria-label="Earlier result"><p><b>You\'re viewing ' + esc(what) + '.</b> ' +
    '<a href="' + BASE + '">Back to the current result</a> <span id="pp-vact"></span></p>' +
    '<p id="pp-msg" class="pp-msg" tabindex="-1" hidden></p></nav><dialog class="pp-dlg" id="pp-dlg" aria-labelledby="pp-dlg-h"></dialog>';
  const label = SID === 'ai' ? 'Start over from the AI\'s decisions' : 'Review again from this session';
  api(API).then(([s, st]) => {
    if (s !== 200) return;
    const busy = st.live_review || st.lock || (st.jobs || []).some(j => j.status === 'queued' || j.status === 'running');
    $('pp-vact').innerHTML = busy ? '· A job for this run is running or waiting: see the current result.' :
      '<button type="button" id="pp-vreview">' + esc(label) + '</button>';
    const b = $('pp-vreview'); if (!b) return;
    b.addEventListener('click', async () => {
      const m = $('pp-msg'), body = { from: SID };
      if (st.open) {
        if (!await confirmDlg('Start a new session?', abandonText(st.open, SID), 'Mark it abandoned and start', b)) return;
        body.discard_open = true;
      }
      try {
        const [c, r] = await api(API + '/review', body);
        if (c === 202) { location.assign(BASE + '?opening=' + encodeURIComponent(r.job.id)); return; }   // the person's click: to the run page
        m.hidden = false; m.textContent = r.error || 'The app refused this'; m.focus();
      } catch (e) { m.hidden = false; m.textContent = 'The app is not running: start it with python3 app.py, then try again.'; m.focus(); }
    });
  }).catch(() => {});
}

// ================================================================ the run page: the panel
const box = $('pdfrem-panel'); if (!box) return;
const RUN = box.dataset.run, API = '/api/run/' + encRun(RUN);
const q = new URLSearchParams(location.search);

// The page opens the review page by itself only right after the person's own Review again: within 30 s of the click and
// while they have not pressed a key or a pointer since. Otherwise it says the page is ready and shows the link. A new
// result never reloads the page by itself: "New result ready" is announced and a button loads it.
let quiet = true, wantAt = 0;
['keydown', 'pointerdown'].forEach(e => addEventListener(e, () => { quiet = false; }, true));
let want = q.get('after') === 'finish' ? 'result' : q.get('opening') ? 'review' : null;   // what the person's last action is waiting for
if (want === 'review') wantAt = Date.now();                    // Review again from an earlier result's bar
let st = null, setup = null, primed = false, offline = false, failing = false, timer = null, newResult = false;
const SHOWN = box.dataset.current || null;                     // the session whose result this page shows (set when served)
const seen = {};                                                // per job: the last step and status announced

box.innerHTML = '<section class="pp" aria-labelledby="pp-h"><h2 id="pp-h" tabindex="-1">Run actions</h2>' +
  '<div id="pp-body"><p>Loading…</p></div><p id="pp-msg" class="pp-msg" tabindex="-1" hidden></p>' +
  '<div id="pp-live" class="pp-sr" role="status" aria-live="polite" aria-atomic="true"></div></section>' +
  '<dialog class="pp-dlg" id="pp-dlg" aria-labelledby="pp-dlg-h"></dialog>';
const live = t => { const l = $('pp-live'); l.textContent = ''; setTimeout(() => { l.textContent = t; }, 50); };
function msg(text, ok, focus) {
  const m = $('pp-msg'); m.hidden = !text; m.textContent = text || ''; m.classList.toggle('pp-okmsg', !!ok);
  if (text && focus) m.focus();
}

// ---------------------------------------------------------------- the view
const ordinal = n => n + ({ 1: 'st', 2: 'nd', 3: 'rd' }[n % 100 > 10 && n % 100 < 14 ? 0 : n % 10] || 'th');
const lost = j => j.status === 'interrupted' && j.interrupted && j.interrupted.state === 'done';
const ended = j => j.status === 'done' || lost(j);
const stepWords = j => j.step ? j.step.words + ' (' + j.step.n + ' of ' + j.step.total + ')' : '';
function jobWords(j) {
  if (j.status === 'queued') return 'Waiting' + (j.position ? ': ' + ordinal(j.position) + ' in line' : '');
  if (j.status === 'running') {
    if (j.kind === 'review' && !j.past_finish) return j.url ? 'Waiting for you: the review page is open' : 'Opening the review page';
    return 'Running' + (j.step ? ': ' + stepWords(j) : '');
  }
  if (j.status === 'done' && j.kind === 'review' && / stays open$/.test(j.outcome || '')) return 'Stopped (the session stays open)';
  if (j.status === 'failed') return 'Failed';
  if (j.status === 'interrupted') return lost(j) ? 'Done (the app lost track of the job)' : 'Interrupted';
  if (j.status === 'needs-spend') return 'Needs Spend again';
  return 'Done';
}
const spins = j => j.status === 'running' && !(j.kind === 'review' && !j.past_finish && j.url);   // not while a person reviews
function jobCard(j) {
  const cls = j.status === 'failed' || j.status === 'interrupted' ? ' pp-failed' : '';
  let h = '<article class="pp-job" id="job-' + esc(j.id) + '" aria-labelledby="jh-' + esc(j.id) + '">' +
    '<h4 id="jh-' + esc(j.id) + '" tabindex="-1">' + esc(j.title) + '</h4>' +
    '<p>' + (spins(j) ? '<span class="pp-spin" aria-hidden="true"></span>' : '') + '<span class="pp-state' + cls + '">' + esc(jobWords(j)) + '</span>' +
    (j.started ? ' <span class="pp-note">· started ' + esc(j.started.slice(11, 16)) + '</span>' : '') + '</p>';
  const steps = j.steps || [];
  if (steps.length) h += '<ol class="pp-steps">' + steps.map(s => '<li' + (s.state === 'running' && j.status === 'running' ? ' aria-current="step"' : '') + '>' +
    esc(cap(s.words)) + ': ' + (s.state === 'done' ? 'done' + (s.time ? ', ' + esc(s.time) : '') : j.status === 'running' ? 'running' : 'did not finish') + '</li>').join('') + '</ol>';
  if (j.kind === 'review' && j.status === 'running' && !j.past_finish && j.url)
    h += '<div class="pp-row"><a class="pp-btn pp-primary" id="pp-open" href="' + esc(j.url) + '">Open the review page</a>' +
         '<button type="button" id="pp-stop" data-act="stop">Stop reviewing (the session stays open)</button></div>';
  if (j.reason) h += '<p><b>Why:</b> ' + esc(j.reason) + '</p><p class="pp-note">Its log is saved in ' + esc(j.log) + '.</p>';
  return h + '</article>';
}

function jobsBlock(s) {
  // running, waiting, and failed or interrupted ones not followed by a success: cards; the last finished one: one line;
  // every other finished one: folded under "Earlier jobs". Nothing drops off.
  const all = (s.jobs || []).slice().reverse();                 // newest first
  const lastOk = all.findIndex(ended);
  const card = all.filter((j, i) => j.status === 'queued' || j.status === 'running' || j.status === 'needs-spend' ||
                                    ((j.status === 'failed' || (j.status === 'interrupted' && !lost(j))) && (lastOk < 0 || i < lastOk)));
  const last = lastOk >= 0 ? all[lastOk] : null;
  const earlier = all.filter(j => !card.includes(j) && j !== last);
  if (!card.length && !last && !earlier.length) return '';
  let h = '<h3>Jobs for this run</h3>' + card.map(jobCard).join('');
  if (last) h += '<p class="pp-last"><b>Last job:</b> ' + esc(last.title) + '</p>';
  if (earlier.length) h += '<details id="pp-earlier"><summary>Earlier jobs (' + earlier.length + ')</summary><ul>' +
    earlier.map(j => '<li>' + esc(j.title) + (j.reason ? ' <span class="pp-note">' + esc(j.reason) + ' Log: ' + esc(j.log) + '</span>' : '') + '</li>').join('') + '</ul></details>';
  return h;
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
  if (active.length) return '<p>A job for this run is ' + (active[0].status === 'running' ? 'running' : 'waiting') + ': ' + esc(active[0].title) + '. One job at a time per run.</p>';
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
      '</td><td>' + esc(r.changes) + '</td><td>' + esc(r.since_start) + '</td><td>' + (r.current ? 'this page' : r.result ? '<a href="' + esc(r.result) + '">earlier result</a>' : 'none') +
      '</td><td>' + ((r.status === 'finished' || r.status === 'applied') && !s.live_review && !s.lock ? '<button type="button" id="pp-from-' + esc(r.id) + '" data-act="review" data-from="' + esc(r.id) + '">Review again from ' + esc(r.label) + '</button>' : '') +
      '</td></tr>').join('') + '</tbody></table></div>';
  if (s.ai_result) h += '<p><a href="' + esc(s.ai_result) + '">The result applied without review</a> (kept in reviews/versions/ai/).</p>';
  return h + '</details>';
}

function render() {
  const s = st, keepFocus = document.activeElement && document.activeElement.id, opened = [...box.querySelectorAll('details[open]')].map(d => d.id);
  // "Ready to ship?" is not repeated here: the report's own card, right below, says it
  let h = setupBlock() + (s.batch ? '<p>Part of batch ' + esc(s.batch) + ': <a href="/batch/' + encodeURIComponent(s.batch) + '/">every book in the batch</a></p>' : '') +
    '<h3 id="pp-cur" tabindex="-1">Current result: ' + esc(s.current.label) + '</h3>';
  if (s.pending) h += '<p>' + esc(sn(s.pending.session)) + ' is ' + esc(s.pending.status) + ' and not applied yet, so "Ready to ship?" says No until it is.</p>';
  if (newResult) h += '<p><b>New result ready:</b> ' + esc(s.current.label) + ' is now the current result; the report below is the earlier one.</p>' +
    '<div class="pp-row"><button type="button" class="pp-primary" id="pp-show" data-act="reload">Show the new result</button></div>';
  h += actions(s) + jobsBlock(s) + historyBlock(s);
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
        if (!await confirmDlg('Start a new session?', abandonText(st.open, b.dataset.from), 'Mark it abandoned and start', b)) return;
        body.discard_open = true;
      }
      [s, r] = await api(API + '/review', body);
      if (s === 202) { want = 'review'; wantAt = Date.now(); }
    }
    if (s !== 202) return msg(r.error || 'The app refused this', false, true);
    quiet = true;                                                // set after this click's own keydown/pointerdown
    await poll(true);
    const hd = $('jh-' + r.job.id); if (hd) hd.focus();
  } catch (err) { msg('The app is not running: start it with python3 app.py, then try again.', false, true); }
});

// ---------------------------------------------------------------- following the jobs
function announce(s) {
  for (const j of s.jobs || []) {
    const key = j.status + '|' + (j.step ? j.step.words : '') + '|' + (j.url || '') + '|' + !!j.past_finish;
    const was = seen[j.id]; seen[j.id] = key;
    if (!primed || was === key) continue;
    const t = j.title + ' (' + RUN + ')';
    if (ended(j) && !newResult && SHOWN && s.current && s.current.id !== SHOWN) {    // one message, not two in a row
      newResult = true; live(t + '. New result ready: ' + s.current.label + '. Show the new result loads it.'); continue;
    }
    if (ended(j) || j.status === 'failed' || j.status === 'interrupted') live(t + ': ' + jobWords(j).toLowerCase() + (j.reason ? '. ' + j.reason : ''));
    else if (j.kind === 'review' && j.url && !j.past_finish && (!was || !was.includes(j.url))) live(t + ': the review page is ready');
    else if (j.step) live(t + ': ' + stepWords(j));
    else if (j.status === 'running' && (!was || was.startsWith('queued'))) live(t + ': started');
  }
  primed = true;
}

async function poll(force) {
  clearTimeout(timer);
  let s, b;
  try { [s, b] = await api(API); }
  catch (e) {                                                    // no answer at all: the app is not running
    banner('pp-offline', 'The app is not running, so this page cannot start or follow jobs. Start it from pipeline/ with python3 app.py; jobs already running carry on.');
    offline = true;
  }
  if (s !== undefined) {
    if (offline) { offline = false; banner('pp-offline', null); live('The app is running again.'); }
    if (s !== 200) { if (!failing) banner('pp-error', 'This run cannot be read by the app (' + (b.error || 'HTTP ' + s) + '): it may have been moved or removed. Reload the page to try again.'); failing = true; }
    else {
      if (failing) { failing = false; banner('pp-error', null); }
      const before = st; st = b;
      announce(b);
      followUp(b);
      if (force || JSON.stringify(before) !== JSON.stringify(b)) render();
    }
  }
  const busy = st && ((st.jobs || []).some(j => j.status === 'queued' || j.status === 'running') || st.live_review);
  timer = setTimeout(poll, busy ? 1000 : 5000);
}
function banner(id, text) {                                     // one banner per kind, announced once when it appears
  const o = $(id);
  if (!text) { if (o) o.remove(); return; }
  if (o) return;
  const p = document.createElement('p'); p.id = id; p.className = 'pp-offline'; p.textContent = text; box.prepend(p); live(text);
}

function followUp(s) {
  const lr = s.live_review;
  if (want === 'review' && lr && lr.url && !lr.past_finish) {
    want = null;
    if (quiet && Date.now() - wantAt < 30000) { location.assign(lr.url); return; }   // right after the person's Review again
    live('The review page is ready: Open the review page.');
  }
  if (want === 'result') {                                     // the page the person's Finish opened: focus its job's heading
    const j = (s.jobs || []).slice().reverse().find(x => x.kind === 'review' || x.kind === 'apply');
    want = null; history.replaceState(null, '', location.pathname);
    if (j) setTimeout(() => { const hd = $('jh-' + j.id); if (hd) hd.focus(); }, 0);
  }
  if (!newResult && SHOWN && s.current && s.current.id !== SHOWN) {   // a new result with no job end seen here (a terminal apply)
    newResult = true; live('New result ready: ' + s.current.label + '. Show the new result loads it.');
  }
}

if (q.get('landed') === '1' || q.get('opening')) history.replaceState(null, '', location.pathname);
api('/api/setup').then(([s, b]) => { if (s === 200) { setup = b; if (st) render(); } }).catch(() => {});
poll(true).then(() => {
  if (q.get('landed') === '1') { const h = $('pp-cur'); if (h) h.focus(); }
  if (q.get('opening')) { const h = $('jh-' + q.get('opening')); if (h) h.focus(); }      // from an earlier result's bar
});
})();
