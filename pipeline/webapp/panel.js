/* webapp/panel.js: the run page's panel (review.html served by the app), and the bar on a previous result's dashboard.
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
// names are never prefilled (Patrick, 2026-11-01): a name remembered by an earlier version of the app is cleared once
try { localStorage.removeItem('checks:by'); } catch (e) {}
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const sn = id => /^\d+$/.test(String(id)) ? 'session ' + Number(id) : id === 'ai' ? 'the result applied without review' : String(id);
const cap = t => t.charAt(0).toUpperCase() + t.slice(1);
// Title Case for labels (headings, toggles, column headers, buttons); explanatory text stays in sentence case. The rule of
// lib/titles.py: a, an, the, and, or, of, to, in, on, for, by, from, with stay lowercase unless first, last, or first after a
// colon or question mark; a word with a capital inside, a dot, slash, underscore or digit is left as written, and so is
// everything in parentheses (a qualifier stays lowercase: "Sent to (optional)").
// ---- dates (lib/dates.py): "October 31, 2026" and "4:32 PM", parsed by hand, never with Date ('2026-10-31' is UTC midnight)
const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
const DATE_RE = /^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2})(?::(\d{2})(?:\.\d+)?)?)?(?:Z|[+-]\d{2}:?\d{2})?$/;
function fmtParse(v) {
  const m = DATE_RE.exec(String(v == null ? '' : v).trim()); if (!m) return null;
  const mo = +m[2], d = +m[3], h = m[4] === undefined ? null : +m[4], mi = m[4] === undefined ? null : +m[5];
  if (mo < 1 || mo > 12 || d < 1 || d > 31 || (h !== null && (h > 23 || mi > 59))) return null;
  return [+m[1], mo, d, h, mi];
}
function fmtBlank(v) { return v == null || !String(v).trim(); }
function fmtDay(v) { if (fmtBlank(v)) return 'date not recorded'; const p = fmtParse(v); return p ? MONTHS[p[1] - 1] + ' ' + p[2] + ', ' + p[0] : String(v).trim(); }
function fmtClock(v) {
  const p = fmtParse(v);
  if (!p || p[3] === null) return fmtBlank(v) || p ? 'time not recorded' : String(v).trim();
  return ((p[3] % 12) || 12) + ':' + String(p[4]).padStart(2, '0') + ' ' + (p[3] < 12 ? 'AM' : 'PM');
}
function fmtWhen(v) { const p = fmtParse(v); return p && p[3] !== null ? fmtDay(v) + ', at ' + fmtClock(v) : fmtDay(v); }
// ---- end of dates
const SMALL = new Set(['a', 'an', 'the', 'and', 'or', 'of', 'to', 'in', 'on', 'for', 'by', 'from', 'with', 'as']);
function tc(s) {
  const w = String(s).split(' '); let edge = true, depth = 0;
  return w.map((x, n) => {
    const i = x.search(/[^("'*[`]/), core = i < 0 ? '' : x.slice(i), first = edge || n === w.length - 1;
    const inside = depth > 0 || /^["'*[`]*\(/.test(x);
    depth = Math.max(0, depth + (x.match(/\(/g) || []).length - (x.match(/\)/g) || []).length);
    edge = /[:?—]$/.test(x);
    if (inside) return x;
    if (!core || !/^\p{L}/u.test(core) || /[./_@\d]/.test(core) || /\p{Lu}/u.test(core.slice(1))) return x;
    if (!first && SMALL.has(core.replace(/[:?!.,;)"'*`\]]+$/, ''))) return x;
    return x.slice(0, i) + core[0].toUpperCase() + core.slice(1);
  }).join(' ');
}
const $ = id => document.getElementById(id);
// the one command a person needs here, with what it does and where to type it
const START = 'To start the app again, open a terminal in the project\'s pipeline folder and type python3 app.py; this page then works again.';
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
    d.innerHTML = '<h2 id="pp-dlg-h">' + esc(tc(title)) + '</h2><p>' + esc(text) + '</p><div><button type="button" class="pp-primary" value="yes">' + esc(tc(yes)) +
                  '</button><button type="button" value="no">Cancel</button></div>';
    const id = opener.id;                                       // a re-render while the dialog is open replaces the element
    const done = v => { d.close(); ($(id) || opener).focus(); res(v); };
    d.querySelectorAll('button').forEach(x => x.addEventListener('click', () => done(x.value === 'yes')));
    d.oncancel = ev => { ev.preventDefault(); done(false); };
    d.showModal(); d.querySelector('button[value=no]').focus();
  });
}
// A session's notes in a pop-up box, read-only (review.html's own script has the same box for the report's Notes). One
// box per session, several open at once; opening one already open brings it to the front. Not modal: the page stays
// usable beside them. A box moves by its title bar, resizes from its corner, and closes with × or Escape (Escape closes
// the box that has focus). Focus goes into its text on open and back to its own Notes button on close (found by id: the
// panel may have redrawn it meanwhile). Moving it is never needed to read the notes, which scroll inside it.
let notesTop = 50;                                              // the z-index of the box in front
function notesBox(title, text, opener, key) {
  const id = 'pp-notes-box-' + key;
  let d = $(id);
  if (!d) {
    d = document.createElement('dialog'); d.id = id; d.className = 'pp-ndlg'; d.setAttribute('aria-labelledby', id + '-h');
    d.innerHTML = '<div class="pp-nbar"><h2 id="' + id + '-h"></h2>' +
      '<button type="button" class="pp-nx" aria-label="Close the notes"><span aria-hidden="true">×</span></button></div>' +
      '<div class="pp-nbody" tabindex="0" role="region" aria-labelledby="' + id + '-h"></div>';
    document.body.appendChild(d);
    const close = () => { d.close(); d.remove(); const o = $(d.dataset.opener); if (o) o.focus(); };
    d.addEventListener('pointerdown', () => { d.style.zIndex = ++notesTop; });   // a click brings it to the front
    d.querySelector('.pp-nx').addEventListener('click', close);
    d.addEventListener('keydown', e => { if (e.key === 'Escape') { e.preventDefault(); close(); } });
    const put = (x, y) => {                                      // kept inside the window
      d.style.left = Math.max(0, Math.min(innerWidth - 80, x)) + 'px'; d.style.top = Math.max(0, Math.min(innerHeight - 40, y)) + 'px';
    };
    d.querySelector('.pp-nbar').addEventListener('pointerdown', e => {   // drag by the title bar (not its close button)
      if (e.button || e.target.closest('.pp-nx')) return;
      const dx = e.clientX - d.offsetLeft, dy = e.clientY - d.offsetTop, bar = e.currentTarget;
      bar.setPointerCapture(e.pointerId); e.preventDefault();
      const move = ev => put(ev.clientX - dx, ev.clientY - dy);
      const up = () => { bar.removeEventListener('pointermove', move); bar.removeEventListener('pointerup', up); bar.removeEventListener('pointercancel', up); };
      bar.addEventListener('pointermove', move); bar.addEventListener('pointerup', up); bar.addEventListener('pointercancel', up);
    });
  }
  d.dataset.opener = opener.id; d.style.zIndex = ++notesTop;
  if (!d.open) {
    d.querySelector('h2').textContent = title; d.querySelector('.pp-nbody').textContent = text;
    const n = document.querySelectorAll('dialog.pp-ndlg[open]').length;   // each new box a little lower and to the right
    d.show();
    d.style.left = Math.max(0, (innerWidth - d.offsetWidth) / 2 + 24 * n) + 'px'; d.style.top = Math.max(0, (innerHeight - d.offsetHeight) / 3 + 24 * n) + 'px';
    d.querySelector('.pp-nbody').scrollTop = 0;
  }
  d.querySelector('.pp-nbody').focus();
}
// a message in the panel or the bar: its text and a "×" button (accessible name "Dismiss message"); an error keeps its red
// style. An empty text hides it.
function showMsg(m, text, ok, focus) {
  m.hidden = !text; m.classList.toggle('pp-okmsg', !!ok);
  m.innerHTML = text ? '<span class="pp-msg-t">' + esc(text) + '</span><button type="button" class="pp-x" data-act="dismiss" aria-label="Dismiss message">' +
                       '<span aria-hidden="true">×</span></button>' : '';    // the glyph hidden: VoiceOver read it as "times"
  if (text && focus) m.focus();
}
function abandonText(open, from) {
  return cap(sn(open.id)) + ' is open (started ' + fmtWhen(open.started) + '). Starting from ' +
         (from === 'ai' ? (st.no_model ? 'the beginning' : 'the AI\'s decisions') : sn(from)) + ' marks it abandoned; its choices stay in "Session History."';
}

// ================================================================ in-page links
// A link to "#…" moves focus to its target (tabindex="-1", no outline), so a screen reader's cursor follows, as the page map
// does. review.html's own script already does this for its links and stops the event (defaultPrevented); this covers the
// app's own pages (the review.md page, the no-dashboard page) and any link it leaves.
document.addEventListener('click', e => {
  if (e.defaultPrevented || e.button) return;
  const a = e.target.closest && e.target.closest('a[href^="#"]'); if (!a || a.getAttribute('href').length < 2) return;
  let id; try { id = decodeURIComponent(a.getAttribute('href').slice(1)); } catch (err) { return; }   // a malformed #%E0: leave it
  const t = document.getElementById(id); if (!t) return;
  e.preventDefault();
  if (!t.hasAttribute('tabindex')) t.setAttribute('tabindex', '-1');
  t.scrollIntoView(); t.focus({ preventScroll: true }); history.replaceState(null, '', '#' + t.id);
});

// ================================================================ a previous result: the bar
const vbox = $('pdfrem-version');
if (vbox) {
  const RUN = vbox.dataset.run, SID = vbox.dataset.session, API = '/api/run/' + encRun(RUN), BASE = '/run/' + encRun(RUN) + '/';
  const what = SID === 'ai' ? 'the result applied without review' : 'a previous result (' + sn(SID) + ')';
  vbox.innerHTML = '<nav class="pp pp-bar" aria-label="Previous result"><p><b>You\'re viewing ' + esc(what) + '.</b> ' +
    '<a href="' + BASE + '">Back to the Current Result</a> <span id="pp-vact"></span></p>' +
    '<div id="pp-msg" class="pp-msg" tabindex="-1" hidden></div></nav><dialog class="pp-dlg" id="pp-dlg" aria-labelledby="pp-dlg-h"></dialog>';
  vbox.addEventListener('click', e => {                          // dismiss: the message goes, focus to the bar's first link
    if (!e.target.closest('button[data-act="dismiss"]')) return;
    showMsg($('pp-msg'), ''); vbox.querySelector('a').focus();
  });
  const label = SID === 'ai' ? 'Start Over from the AI\'s Decisions' : 'Review Again from This Session';
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
        showMsg(m, r.error || 'The app refused this', false, true);
      } catch (e) { showMsg(m, 'The app is not running. ' + START + ' Then try again.', false, true); }
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
// what the person's last action is waiting for: after=finish (the review page's Finish), after=ocr (Finish OCR Review: this
// page was loaded after the verdict was written, so its report already has it)
let want = q.get('after') === 'finish' ? 'result' : q.get('after') === 'ocr' ? 'ocr' : q.get('opening') ? 'review' : null;
if (want === 'review') wantAt = Date.now();                    // Review again from a previous result's bar
let st = null, setup = null, primed = false, offline = false, failing = false, timer = null, newResult = false;
const SHOWN = box.dataset.current || null;                     // the session whose result this page shows (set when served)
const WAITING = box.dataset.waiting === '1';                   // served before the first review (REVIEW=1): no result yet
let ocrSeen;                                                    // the OCR verdict's `recorded` when this page's report was read
const seen = {};                                                // per job: the last step and status announced

box.innerHTML = '<section class="pp" aria-labelledby="pp-h"><h2 id="pp-h" tabindex="-1">Run Actions</h2>' +
  '<div id="pp-body"><p>Loading…</p></div><div id="pp-msg" class="pp-msg" tabindex="-1" hidden></div>' +
  '<div id="pp-live" class="pp-sr" role="status" aria-live="polite" aria-atomic="true"></div></section>' +
  '<dialog class="pp-dlg" id="pp-dlg" aria-labelledby="pp-dlg-h"></dialog>';
const live = t => { const l = $('pp-live'); l.textContent = ''; setTimeout(() => { l.textContent = t; }, 50); };
function msg(text, ok, focus) { showMsg($('pp-msg'), text, ok, focus); }

// ---------------------------------------------------------------- the view
const ordinal = n => n + ({ 1: 'st', 2: 'nd', 3: 'rd' }[n % 100 > 10 && n % 100 < 14 ? 0 : n % 10] || 'th');
const lost = j => j.status === 'interrupted' && j.interrupted && j.interrupted.state === 'done';
const ended = j => j.status === 'done' || lost(j);
const stepWords = j => j.step ? j.step.words + ' (' + j.step.n + ' of ' + j.step.total + ')' : '';
// a job's status line, in sentence case: what it is doing, or what came of it ("Done: session 5 applied (Kim, 21:04)")
function jobWords(j) {
  if (j.status === 'queued') return 'Waiting' + (j.position ? ': ' + ordinal(j.position) + ' in line' : '');
  if (j.status === 'running') {
    if (j.kind === 'ocr') return j.url ? 'Waiting for you: the OCR Text Review page is open' : 'Opening the OCR Text Review page';
    if (j.kind === 'review' && !j.past_finish) return j.url ? 'Waiting for you: the review page is open' : 'Opening the review page';
    return 'Running' + (j.step ? ': ' + stepWords(j) : '');
  }
  if (j.status === 'needs-spend') return 'Needs Spend again';
  const r = j.result || '';
  if (j.status === 'done' && j.kind === 'review' && / left open /.test(r)) return 'Stopped: ' + r;
  if (j.status === 'failed' || (j.status === 'interrupted' && !lost(j))) return cap(r || j.status);
  if (lost(j)) return 'Done (the app lost track of the job): ' + r;
  return /^(done|pinned|discarded)\b/.test(r) ? cap(r) : 'Done: ' + r;
}
const person = j => j.kind === 'review' || j.kind === 'ocr';    // a page open for a person: the work-order review, the OCR-only page
const spins = j => j.status === 'running' && !(person(j) && !j.past_finish && j.url);   // not while a person reviews
function jobCard(j) {                                           // heading: the action (Title Case); outcome on the status line
  const cls = j.status === 'failed' || j.status === 'interrupted' ? ' pp-failed' : '';
  let h = '<article class="pp-job" id="job-' + esc(j.id) + '" aria-labelledby="jh-' + esc(j.id) + '">' +
    '<h4 id="jh-' + esc(j.id) + '" tabindex="-1">' + esc(tc(j.action || j.title)) + '</h4>' +
    '<p>' + (spins(j) ? '<span class="pp-spin" aria-hidden="true"></span>' : '') + '<span class="pp-state' + cls + '">' + esc(jobWords(j)) + '</span>' +
    (j.started ? ' <span class="pp-note">· started ' + esc(fmtClock(j.started)) + '</span>' : '') + '</p>';
  const steps = j.steps || [];                                  // the step running now is in the status line: no ": running" here
  if (steps.length) h += '<ol class="pp-steps">' + steps.map(s => '<li' + (s.state === 'running' && j.status === 'running' ? ' aria-current="step"' : '') + '>' +
    esc(cap(s.words)) + (s.state === 'done' ? ': done' + (s.time ? ', ' + esc(s.time) : '') : j.status === 'running' ? '' : ': did not finish') + '</li>').join('') + '</ol>';
  if (j.kind === 'review' && j.status === 'running' && !j.past_finish && j.url)
    h += '<div class="pp-row"><a class="pp-btn pp-primary" id="pp-open" href="' + esc(j.url) + '">Open the Review Page</a>' +
         '<button type="button" id="pp-stop" data-act="stop">' + (j.first ? 'Stop Reviewing (Your Choices Are Saved)' : 'Stop Reviewing (the Session Stays Open)') + '</button></div>';
  if (j.kind === 'ocr' && j.status === 'running' && j.url)
    h += '<div class="pp-row"><a class="pp-btn pp-primary" id="pp-open" href="' + esc(j.url) + '">Open the OCR Text Review Page</a>' +
         '<button type="button" id="pp-stop" data-act="stop">Close Without a Verdict</button></div>';
  if (j.child_url) h += '<div class="pp-row"><a class="pp-btn pp-primary" href="' + esc(j.child_url) + '">Open the Edited Run</a></div>';
  if (j.reason) h += '<p><b>Why:</b> ' + esc(j.reason) + '</p><p class="pp-note">The job\'s full output, for whoever looks after the app, is saved in ' + esc(j.log) + '.</p>';
  return h + '</article>';
}

function jobsBlock(s) {
  // running, waiting, and failed or interrupted ones not followed by a success: cards; the last finished one: one line;
  // every other finished one: folded under "Previous Jobs". Nothing drops off. One-line places are sentence case.
  const all = (s.jobs || []).slice().reverse();                 // newest first
  const lastOk = all.findIndex(ended);
  const card = all.filter((j, i) => j.status === 'queued' || j.status === 'running' || j.status === 'needs-spend' ||
                                    ((j.status === 'failed' || (j.status === 'interrupted' && !lost(j))) && (lastOk < 0 || i < lastOk)));
  const last = lastOk >= 0 ? all[lastOk] : null;
  const previous = all.filter(j => !card.includes(j) && j !== last);
  if (!card.length && !last && !previous.length) return '';
  let h = card.map(jobCard).join('');
  if (last) h += '<p class="pp-last"><b>Last Job:</b> ' + esc(cap(last.title)) + '</p>';
  if (previous.length) h += '<details id="pp-previous"><summary>Previous Jobs (' + previous.length + ')</summary><ul>' +
    previous.map(j => '<li>' + esc(cap(j.title)) + (j.reason ? ' <span class="pp-note">' + esc(j.reason) + ' Log: ' + esc(j.log) + '</span>' : '') + '</li>').join('') + '</ul></details>';
  return h;
}

function setupBlock() {                                         // shown only when a tool is missing, as a warning
  if (!setup) return '';
  const miss = setup.filter(x => !x.ok), req = miss.filter(x => x.required);
  if (!miss.length) return '';
  const sum = req.length ? 'Setup: ' + req.length + ' required tool' + (req.length > 1 ? 's' : '') + ' missing' :
              miss.length ? 'Setup: ready (tools for untagged books missing: ' + miss.length + ')' : 'Setup: every tool ready';
  return '<details id="pp-setup" class="pp-warn"><summary>' + esc(tc(sum)) + '</summary><ul>' + setup.map(x => '<li>' + (x.ok ? 'Ready' : x.required ? 'Missing (required)' : 'Missing') +
    ': ' + esc(x.name) + ' · ' + esc(x.detail) + (x.fix ? '<br>Fix: <code>' + esc(x.fix) + '</code>' : '') + '</li>').join('') + '</ul></details>';
}

function actions(s) {
  const lr = s.live_review, active = (s.jobs || []).filter(j => j.status === 'queued' || j.status === 'running');
  if (lr) return '';                                             // its own card has Open / Stop
  if (s.lock) return '<p>' + esc(s.lock.words) + ' The buttons come back then.</p>' +   // who or what, since when (webapp/jobs.py lock_words)
    (['reopen', 'ocr review'].includes(s.lock.what) ? '<div class="pp-row"><button type="button" id="pp-stop-other" data-act="stop-other">Stop the Other Review</button></div>' : '');
  if (active.length) return '<p>A job for this run is ' + (active[0].status === 'running' ? 'running' : 'waiting') + ': ' + esc(active[0].title) + '. One job at a time per run.</p>';
  let h = '<div class="pp-row">';
  // in parentheses tc() leaves words as written: a session is named "Session N" there
  const from = s.open ? null : s.latest ? cap(sn(s.latest.id)) : s.legacy_review ? 'the review recorded before sessions were kept' : s.no_model ? 'the beginning' : 'the AI\'s decisions';
  h += s.open ? '<button type="button" class="pp-primary" id="pp-review" data-act="review">' + esc(tc('Continue review (' + cap(s.open.label) + ', open)')) + '</button>'
              : '<button type="button" class="pp-primary" id="pp-review" data-act="review">' + esc(tc('Review again (from ' + from + ')')) + '</button>';
  if (s.open) h += '<button type="button" id="pp-discard" data-act="discard">' + esc(tc('Discard ' + s.open.label)) + '</button>';
  if (s.latest || s.open) h +='<button type="button" id="pp-ai" data-act="review" data-from="ai">' + (s.no_model ? 'Start Over from the Beginning' : 'Start Over from the AI\'s Decisions') + '</button>';
  if (s.unapplied && !s.open) h += '<button type="button" id="pp-apply" data-act="apply">' + esc(tc('Apply ' + s.unapplied.label)) + '</button>';
  h += '</div>';
  if (s.ocr && s.ocr.needed)                                     // the OCR text verdict, on its own (no work-order session)
    h += '<div class="pp-row"><button type="button" id="pp-ocr" data-act="ocr">Review OCR Text</button>' +
         '<span class="pp-note">OCR Text: ' + esc(tc(s.ocr.verdict || 'not yet reviewed')) + '</span></div>';
  if (!s.pinned) h += '<p class="pp-note">Review again first re-audits this run to pin it (free, a minute or more).</p>';
  h += '<div class="pp-row"><button type="button" id="pp-bring" data-act="bring-back">Bring Back an Edited PDF</button>' +
       '<span class="pp-note">A copy you changed in Acrobat comes back as a new run for review (no AI call).</span></div>';
  return h;
}

// a PDF edited by hand (handedit.py, docs/hand-edits.md): the run it was made from, and the runs made from edited copies of it
function handEditBlock(s) {
  const he = s.hand_edits; if (!he) return '';
  let h = '';
  if (he.parent) h += '<p>Made from an edited copy of run ' + esc(he.parent.label) + (he.parent.url ? ': <a href="' + esc(he.parent.url) + '">open it</a>' : ' (its folder is gone)') + '.</p>';
  if ((he.children || []).length)
    h += '<h3>' + esc(tc('Edited copies')) + '</h3><ul>' + he.children.map(c => '<li><b>' + esc(c.label) + '</b> · ' + esc(c.state) +
      (c.by ? ' · ' + esc(c.by) : '') + (c.when ? ', ' + esc(fmtDay(c.when)) : '') + (c.note ? ' · “' + esc(c.note) + '”' : '') +
      (c.url ? ' · <a href="' + esc(c.url) + '">Open</a>' : '') +
      (c.state === 'not started' ? (c.startable ? ' · brought back but not run yet <button type="button" id="pp-start-' + esc(c.label) + '" data-act="bring-start" data-label="' + esc(c.label) + '">Start</button>'
                                                : ' · brought back for the full pipeline (a paid AI call): start it in a terminal') : '') + '</li>').join('') + '</ul>';
  return h;
}
// Bring Back an Edited PDF: the edited file (chosen here and uploaded), a name (never prefilled) and what was changed. The
// upload and the request are sent from the dialog, so a refusal is shown in it, in the app's words; Escape or Cancel closes it
// (and stops an upload under way).
function bringDlg(s, opener) {
  return new Promise(res => {
    const d = $('pp-dlg');
    d.innerHTML = '<h2 id="pp-dlg-h">Bring Back an Edited PDF</h2>' +
      '<ol><li>Download this version with "Download the Remediated PDF."</li>' +
      '<li>Edit it in Acrobat. First turn off text recognition: Edit, then Edit settings, and uncheck "Recognize scanned text."</li>' +
      '<li>Choose the edited PDF here.</li></ol>' +
      '<p>It comes back as a new run that stops for review: no AI call, no cost. This run is not changed.</p>' +
      '<p><label for="pp-bring-file">Edited PDF</label><br><input type="file" id="pp-bring-file" accept="application/pdf,.pdf"></p>' +
      '<p><label for="pp-bring-by">Edited By</label><br><input type="text" id="pp-bring-by" autocomplete="name"></p>' +
      '<p><label for="pp-bring-note">What You Changed</label><br><textarea id="pp-bring-note" rows="2" maxlength="200"></textarea></p>' +
      '<p id="pp-bring-err" class="pp-warn-t" role="alert"></p><div><button type="button" class="pp-primary" value="yes">Bring Back</button>' +
      '<button type="button" value="no">Cancel</button></div>';
    let xhr = null;
    const id = opener.id, err = t => { $('pp-bring-err').textContent = t; };
    const done = v => { if (xhr) xhr.abort(); d.close(); ($(id) || opener).focus(); res(v); };
    const send = file => new Promise(ok => {                    // the PDF's own bytes; its name in a header (percent-encoded)
      xhr = new XMLHttpRequest();
      xhr.open('POST', API + '/upload');
      xhr.setRequestHeader('Content-Type', 'application/pdf');
      xhr.setRequestHeader('X-File-Name', encodeURIComponent(file.name));
      xhr.upload.onprogress = ev => { if (ev.lengthComputable) err('Uploading… ' + Math.round(100 * ev.loaded / ev.total) + '%'); };
      xhr.onload = () => { let r = {}; try { r = JSON.parse(xhr.responseText || '{}'); } catch (e) {} ok([xhr.status, r]); };
      xhr.onerror = () => ok([0, { error: 'The app is not running. ' + START }]);
      xhr.onabort = () => ok([-1, {}]);
      xhr.send(file);
    });
    d.querySelector('button[value=no]').addEventListener('click', () => done(null));
    d.querySelector('button[value=yes]').addEventListener('click', async ev => {
      const file = $('pp-bring-file').files[0], by = $('pp-bring-by').value.trim(), note = $('pp-bring-note').value.trim();
      if (!file) { err('Choose the edited PDF.'); $('pp-bring-file').focus(); return; }
      if (!by) { err('Enter your name in "Edited By."'); $('pp-bring-by').focus(); return; }
      if (!note) { err('Say what you changed in "What You Changed."'); $('pp-bring-note').focus(); return; }
      ev.target.disabled = true; err('Uploading…');
      const [c, u] = await send(file); xhr = null;
      if (c === -1) return;                                        // cancelled
      if (c !== 200) { err(u.error || 'The PDF was not uploaded.'); ev.target.disabled = false; return; }
      err('Uploaded. Starting…');
      try {
        const [c2, r] = await api(API + '/bring-back', { file: u.file, by, note });
        if (c2 === 202) return done(r.job);
        err(r.error || 'The app refused this.'); ev.target.disabled = false;
      } catch (e) { err('The app is not running. ' + START); ev.target.disabled = false; }
    });
    d.oncancel = ev => { ev.preventDefault(); done(null); };
    d.showModal(); $('pp-bring-file').focus();
  });
}

// "Clean Up Space" (stage 3, review/prune.py): the button alone, shown only when a previous version's PDF can be removed;
// the explanation is in its dialog (Patrick, 2026-11-01)
const PRUNE_LINE = 'Deletes the PDF files of the previous versions you select to free up space. Their records and decisions stay in "Session History." The original AI-generated version is always kept.';
function pruneBlock(s) {
  if (!s.prune) return '';
  return '<div class="pp-row"><button type="button" id="pp-prune" data-act="prune">Clean Up Space</button></div>';
}
function removeLabel(n) { return n ? 'Remove ' + n + ' PDF' + (n === 1 ? '' : 's') : 'Remove PDFs'; }
function pruneDlg(p, opener) {                                    // a checkbox per version and a name (never prefilled); Escape or Cancel closes it
  return new Promise(res => {
    const d = $('pp-dlg');
    d.innerHTML = '<h2 id="pp-dlg-h">Clean Up Space</h2><p>' + esc(PRUNE_LINE) + '</p>' +
      '<fieldset class="pp-prune"><legend>Previous Versions</legend>' +
      p.versions.map((v, i) => '<label><input type="checkbox" id="pp-prune-' + i + '" value="' + i + '"> ' + esc(v.label) + ' · ' + esc(v.size) + '</label>').join('') +
      '</fieldset><p id="pp-prune-sel" class="pp-note" aria-live="polite">None selected.</p>' +
      '<p><label for="pp-prune-by">Removed By</label> <input type="text" id="pp-prune-by" autocomplete="name"></p>' +
      '<p>This can\'t be undone.</p><p id="pp-prune-err" class="pp-warn-t" role="alert"></p><div><button type="button" class="pp-primary" value="yes" disabled>' + removeLabel(0) +
      '</button><button type="button" value="no">Cancel</button></div>';
    const id = opener.id, done = v => { d.close(); ($(id) || opener).focus(); res(v); };
    const picked = () => [...d.querySelectorAll('.pp-prune input:checked')].map(x => p.versions[Number(x.value)]);
    const yes = d.querySelector('button[value=yes]');
    d.querySelector('.pp-prune').addEventListener('change', () => {   // the count on the button; nothing goes unless selected
      const vs = picked(), mb = vs.reduce((a, v) => a + v.bytes, 0) / 1e6;
      yes.textContent = removeLabel(vs.length); yes.disabled = !vs.length;
      $('pp-prune-sel').textContent = vs.length ? vs.length + ' selected · ' + mb.toFixed(1) + ' MB' : 'None selected.';
    });
    d.querySelector('button[value=no]').addEventListener('click', () => done(null));
    yes.addEventListener('click', () => {
      const vs = picked(); if (!vs.length) return;
      const name = $('pp-prune-by').value.trim();
      if (!name) { $('pp-prune-err').textContent = 'Enter your name in "Removed By."'; $('pp-prune-by').focus(); return; }
      done({ by: name, chosen: vs.map(v => ({ id: v.id, sha256: v.sha256 })) });
    });
    d.oncancel = ev => { ev.preventDefault(); done(null); };
    d.showModal(); $('pp-prune-0').focus();
  });
}
function historyBlock(s) {
  const rows = (s.sessions || []).slice().sort((a, b) => Number(b.id) - Number(a.id));   // newest first
  let h = '<details id="pp-hist"><summary>Session History (' + rows.length + ')</summary>';
  if (!rows.length) h += '<p>' + (s.legacy_review ? 'Reviewed before sessions were kept: "Review Again" records that review as Session 1.' : 'Never reviewed: the result was applied without review.') + '</p>';
  else h += '<div class="pp-tw" tabindex="0" role="region" aria-label="Session History Table"><table><caption>Review Sessions of This Run</caption><thead><tr>' +
    '<th scope="col">Session</th><th scope="col">Status</th><th scope="col">Reviewer</th><th scope="col">Date</th><th scope="col">Started From</th>' +
    '<th scope="col">Changes from the AI</th><th scope="col">Set in This Session</th><th scope="col">Notes</th><th scope="col">Result</th><th scope="col">Action</th></tr></thead><tbody>' +
    // a session's name and notes are a person's own text: escaped, never Title Cased
    rows.map(r => '<tr><th scope="row"><span class="pp-nw">' + esc(cap(r.label)) + (r.current ? ' (current)' : '') + '</span>' + (r.name ? '<span class="pp-name' + ([...r.name].length > 40 ? ' pp-long' : '') + '">' + esc(r.name) + '</span>' : '') + '</th><td>' + esc(r.status) + (r.summary_only ? ' (summary only)' : r.inferred ? ' (inferred)' : '') +
      '</td><td>' + esc(r.reviewer || 'not recorded') + '</td><td class="pp-nw">' + esc(r.date || r.started ? fmtDay(r.date || r.started) : 'not recorded') + '</td><td class="pp-nw">' + esc(/^session \d/.test(r.from_label) ? cap(r.from_label) : r.from_label) +
      '</td><td>' + esc(r.changes) + '</td><td>' + esc(r.since_start) + '</td><td>' +
      (r.notes ? '<button type="button" class="pp-link" id="pp-notes-' + esc(r.id) + '" data-act="notes" data-id="' + esc(r.id) + '">Notes</button>' : 'none') + '</td><td>' + (r.current ? 'this page' : r.result ? '<a href="' + esc(r.result) + '">previous result</a>' : 'none') + (r.pdf_removed ? '<span class="pp-note"> · PDF removed</span>' : '') +
      '</td><td>' + ((r.status === 'finished' || r.status === 'applied') && !s.live_review && !s.lock ? '<button type="button" id="pp-from-' + esc(r.id) + '" data-act="review" data-from="' + esc(r.id) + '">' + esc(tc('Review again from ' + r.label)) + '</button>' : '') +
      '</td></tr>').join('') + '</tbody></table></div>';
  if (s.ai_result) h += '<p><a href="' + esc(s.ai_result) + '">The result applied without review</a> (kept with the run).</p>';
  return h + '</details>';
}

// ---------------------------------------------------------------- the evaluation strip, right after "Ready to Ship?"
// (webapp/server.py with_strip() places its box; a page with no card gets it at the end of this panel). The card above it
// says each requirement, so the strip has no line per part (Patrick, 2026-11-01); it says the live status when it differs
// from the report's card on disk, so the page never shows two answers without saying which is current.
function stripBlock(s, inPanel) {
  const m = s.manual; if (!m) return '';
  const hx = inPanel ? 'h3' : 'h2';                  // inside the panel's own h2 section: one level down (review 12 G2)
  let h = '<section class="pp pp-checks" aria-labelledby="pp-mc-h"><' + hx + ' id="pp-mc-h">Accessibility Evaluation (PAC 2026 &amp; Screen-Reader Test)</' + hx + '>';
  const now = (m.status || '') + (m.newer ? ' · ' + m.newer : ''), card = (m.card_status || '') + (m.card_newer ? ' · ' + m.card_newer : '');
  if (m.status && now !== card) h += '<p><b>Status now:</b> ' + esc(now) + ' <span class="pp-note">(the report on this page was written before this)</span></p>';
  if (m.refusal) h += '<p class="pp-warn-t">' + esc(m.refusal) + '</p>';
  h += '<div class="pp-row"><a class="pp-btn pp-primary" id="pp-mc-open" href="checks">Complete Evaluation</a></div>' +
    shipBlock(m.ship) + dlForm(m.downloads, inPanel ? 'h4' : 'h3') + '</section>';
  return h;
}
// "Mark as Shipped" (stage 4): offered only when the gate is open (webapp/manualpage.py ship_gate: current Ready, the file
// unchanged, this file not already shipped); otherwise the one line that says why
function shipBlock(sp) {
  if (!sp) return '';
  if (sp.ok) return '<div class="pp-row"><button type="button" id="pp-ship" data-ship="1">Mark as Shipped</button>' +
    '<span class="pp-note">Records that this version was reviewed and shipped.</span></div>';
  return sp.why ? '<p class="pp-note">' + esc(sp.why) + '</p>' : '';
}
function shipDlg(sp, opener) {                                    // a name (never prefilled) and a note; Escape or Cancel closes it
  return new Promise(res => {
    const d = $('pp-dlg'), n = sp.issues || 0;
    d.innerHTML = '<h2 id="pp-dlg-h">Mark as Shipped</h2><p>Records that this version was reviewed and shipped.' +
      (n ? ' ' + n + ' issue' + (n === 1 ? ' was' : 's were') + ' noted in the evaluation; ' + (n === 1 ? 'it is' : 'they are') + ' kept with the shipped copy.' : '') + '</p>' +
      '<p><label for="pp-ship-by">Shipped By</label><br><input type="text" id="pp-ship-by" autocomplete="name"></p>' +
      '<p><label for="pp-ship-note">Note <span class="pp-note">(optional)</span></label><br><textarea id="pp-ship-note" rows="2"></textarea></p>' +
      '<p id="pp-ship-err" class="pp-warn-t" role="alert"></p><div><button type="button" class="pp-primary" value="yes">Mark as Shipped</button>' +
      '<button type="button" value="no">Cancel</button></div>';
    const id = opener.id, done = v => { d.close(); ($(id) || opener).focus(); res(v); };
    d.querySelector('button[value=no]').addEventListener('click', () => done(null));
    d.querySelector('button[value=yes]').addEventListener('click', () => {
      const name = $('pp-ship-by').value.trim();
      if (!name) { $('pp-ship-err').textContent = 'Enter your name in "Shipped By."'; $('pp-ship-by').focus(); return; }
      done({ by: name, note: $('pp-ship-note').value.trim() });
    });
    d.oncancel = ev => { ev.preventDefault(); done(null); };
    d.showModal(); d.querySelector('button[value=no]').focus();
  });
}
async function shipNow(b) {
  const sp = st.manual && st.manual.ship; if (!sp || !sp.ok) return;
  const v = await shipDlg(sp, b); if (!v) return;
  try {
    const [c, r] = await api(API + '/ship', { by: v.by, note: v.note, shown_sha256: sp.sha });
    if (c !== 200) return msg(r.error || 'It was not marked as shipped.', false, true);
    msg('Marked as shipped: Shipment ' + r.shipped.n + '.', true, true);
    return poll(true);
  } catch (e) { return msg('The app is not running. ' + START, false, true); }
}
// "Available Downloads" (stage 3), as on the evaluation page (webapp/manualpage.py downloads_form): the heading holding the
// select's label, the select, the line saying how the chosen version's files are marked (never a file name), then the two
// buttons in a row. A GET form to download?v=…&what=pdf|record: any version, ready or not. A shipped version has no line:
// it is hidden and the select is not described by it (the line above the downloads and the label already say it was shipped)
function dlForm(dd, hx) {
  const vs = (dd && dd.versions) || []; if (!vs.length) return '';
  const m = vs[0].marked;
  return '<form class="pp-dl" method="get" action="download"><' + hx + ' id="pp-dl-h">' + '<label for="pp-dlv">Available Downloads</label></' + hx + '>' +
    '<select id="pp-dlv" name="v"' + (m ? ' aria-describedby="pp-dl-marked"' : '') + '>' +
    vs.map(x => '<option value="' + esc(x.id) + '" data-marked="' + esc(x.marked) + '">' + esc(x.label) + '</option>').join('') + '</select>' +
    '<p id="pp-dl-marked" class="pp-note"' + (m ? '' : ' hidden') + '>' + esc(m) + '</p>' +
    '<div class="pp-row"><button type="submit" name="what" value="pdf">Download the Remediated PDF</button>' +
    '<button type="submit" name="what" value="record">Download the Record (ZIP)</button></div></form>';
}
function renderStrip(s) {
  let sb = $('pdfrem-checks');
  if (!sb) { sb = document.createElement('div'); sb.id = 'pdfrem-checks'; sb.dataset.inPanel = '1'; box.querySelector('section.pp').appendChild(sb); }   // no card: in the panel
  const sel = $('pp-dlv'), chosen = sel ? sel.value : null;      // the picker keeps its choice when the strip is redrawn
  const h = stripBlock(s, sb.dataset.inPanel === '1'), keep = document.activeElement && sb.contains(document.activeElement) ? document.activeElement.id : null;
  if (sb.dataset.h !== h) {
    sb.innerHTML = h; sb.dataset.h = h;
    const ns = $('pp-dlv');
    if (ns && chosen && [...ns.options].some(o => o.value === chosen)) { ns.value = chosen; dlMarked(ns); }
    if (keep && $(keep)) $(keep).focus();
  }
  if (!sb.dataset.shipWired) { sb.dataset.shipWired = '1'; sb.addEventListener('click', e => { const b = e.target.closest('button[data-ship]'); if (b) shipNow(b); }); }
  const dl = $('pp-dlv');
  if (dl && !dl.dataset.wired) { dl.dataset.wired = '1'; dl.addEventListener('change', () => dlMarked(dl)); }
}
function dlMarked(sel) {                                          // the line under the picker for the chosen version, or none
  const p = $('pp-dl-marked'), m = sel.selectedOptions[0].dataset.marked;
  p.textContent = m; p.hidden = !m;
  if (m) sel.setAttribute('aria-describedby', p.id); else sel.removeAttribute('aria-describedby');
}

// A run stopped for its first review (REVIEW=1): "Open the Review Page," then, after "Finish Review," "Apply" (run_api.sh's
// second call); once applied, the page offers its first result (it never reloads by itself)
function waitingBlock(s) {
  const w = s.waiting, active = (s.jobs || []).filter(j => j.status === 'queued' || j.status === 'running');
  if (!w) return '<p><b>Result Ready:</b> Session 1 is applied. The report and the remediated PDF are ready.</p>' +
    '<div class="pp-row"><button type="button" class="pp-primary" id="pp-show" data-act="reload">Show the Result</button></div>';
  if (s.live_review) return '';                                  // its own card has Open / Stop
  if (active.length) return '<p>A job for this run is ' + (active[0].status === 'running' ? 'running' : 'waiting') + ': ' + esc(active[0].title) + '.</p>';
  if (!w.reviewed) return '<p>The AI\'s decisions are waiting for your review. Nothing has been applied yet.</p>' +
    '<div class="pp-row"><button type="button" class="pp-primary" id="pp-review" data-act="review">Open the Review Page</button></div>';
  return '<p>Review finished (' + esc(w.reviewer || 'reviewer not recorded') + ', ' + esc(fmtDay(w.date)) + '). Nothing has been applied yet: ' +
    '"Apply" makes the remediated PDF and its report.</p>' +
    '<div class="pp-row"><button type="button" class="pp-primary" id="pp-apply" data-act="apply">Apply</button></div>';
}

function render() {
  if (WAITING) {                                                 // no result, no strip: the review, then the first apply
    const h = setupBlock() + '<h3 id="pp-cur" tabindex="-1">' + esc(tc(!st.waiting ? 'First result' : st.waiting.reviewed ? 'Waiting to be applied' : 'Waiting for review')) + '</h3>' +
      waitingBlock(st) + jobsBlock(st), body = $('pp-body'), keepFocus = document.activeElement && document.activeElement.id;
    if (body.dataset.h === h) return;
    body.innerHTML = h; body.dataset.h = h;
    if (keepFocus && $(keepFocus) && box.contains($(keepFocus))) $(keepFocus).focus();
    return;
  }
  renderStrip(st);
  const s = st, keepFocus = document.activeElement && document.activeElement.id, opened = [...box.querySelectorAll('details[open]')].map(d => d.id);
  // "Ready to ship?" is not repeated here: the report's own card, right below, says it
  let h = setupBlock() + (s.batch ? '<p>Part of batch ' + esc(s.batch) + ': <a href="/batch/' + encodeURIComponent(s.batch) + '/">every book in the batch</a></p>' : '') +
    '<h3 id="pp-cur" tabindex="-1">' + esc(tc('Current result: ' + s.current.label)) + '</h3>';
  if (s.pending) h += '<p>' + esc(sn(s.pending.session)) + ' is ' + esc(s.pending.status) + ' and not applied yet, so the book stays "Not Ready" until it is.</p>';
  if (newResult) h += '<p><b>New Result Ready:</b> ' + esc(cap(s.current.label)) + ' is now the current result; the report below is the previous one.</p>' +
    '<div class="pp-row"><button type="button" class="pp-primary" id="pp-show" data-act="reload">Show the New Result</button></div>';
  else if (s.ocr && ocrSeen !== undefined && s.ocr.recorded !== ocrSeen)   // a verdict recorded since this page loaded: never reloads by itself
    h += '<p><b>OCR Verdict Recorded:</b> ' + esc(s.ocr.verdict || 'a new verdict') + '. The report below was made before it.</p>' +
      '<div class="pp-row"><button type="button" class="pp-primary" id="pp-show" data-act="reload">Show the Updated Report</button></div>';
  h += actions(s) + jobsBlock(s) + handEditBlock(s) + historyBlock(s) + pruneBlock(s);
  // replaced only when it changed, as the strip is: a poll whose data changed but not what the panel shows (the review
  // page saving a session's draft while a review is open) never swaps the buttons under the mouse or a selection
  const body = $('pp-body');
  if (body.dataset.h === h) return;
  body.innerHTML = h; body.dataset.h = h;
  opened.forEach(id => { const d = $(id); if (d) d.open = true; });
  if (keepFocus && $(keepFocus) && box.contains($(keepFocus))) $(keepFocus).focus();
}

// ---------------------------------------------------------------- what the person does
box.addEventListener('click', async e => {
  const b = e.target.closest('button[data-act]'); if (!b) return;
  const act = b.dataset.act;
  if (act === 'dismiss') { msg(''); $('pp-h').focus(); return; }   // the message goes; focus to the Run Actions heading
  if (act === 'notes') {                                         // a session's notes, read-only, in the pop-up box
    const r = (st.sessions || []).find(x => String(x.id) === b.dataset.id); if (!r) return;
    return notesBox(tc('Notes: ' + r.label) + (r.name ? ' · ' + r.name : ''), r.notes || '', b, String(r.id));
  }
  if (act === 'prune') {                                         // "Clean Up Space": select in the dialog, then remove exactly those
    const p = st.prune; if (!p) return;
    const v = await pruneDlg(p, b); if (!v) return;
    try {
      const [c, r] = await api(API + '/remove-older-pdfs', { by: v.by, chosen: v.chosen });
      if (c !== 200) return msg(r.error || 'The PDFs were not removed.', false, true);
      msg('Removed ' + r.removed + ' PDF' + (r.removed === 1 ? '' : 's') + ' (' + (r.bytes / 1e6).toFixed(1) + ' MB freed). ' + (r.removed === 1 ? 'Its record and decisions are' : 'Their records and decisions are') + ' kept in "Session History."', true, true);
      return poll(true);
    } catch (e) { return msg('The app is not running. ' + START, false, true); }
  }
  if (act === 'bring-start') {                                   // an edited copy brought back but never run: run its review stop
    try {
      const [c, r] = await api(API + '/bring-back', { resume: b.dataset.label });
      if (c !== 202) return msg(r.error || 'The app refused this.', false, true);
      await poll(true); const hd = $('jh-' + r.job.id); if (hd) hd.focus(); return;
    } catch (e) { return msg('The app is not running. ' + START, false, true); }
  }
  if (act === 'bring-back') {                                    // the dialog sends it; on 202 the job's card takes focus
    const j = await bringDlg(st, b); if (!j) return;
    msg('The edited PDF is coming back as a new run. When it is ready, open it from the job below.', true, true);
    await poll(true); const hd = $('jh-' + j.id); if (hd) hd.focus(); return;
  }
  msg('');                                                       // any other panel button clears the message too
  if (act === 'reload') { location.replace(location.pathname + '?landed=1'); return; }
  try {
    let s, r;
    if (act === 'stop') {
      const open = st.open ? cap(sn(st.open.id)) : 'The session', ocr = st.live_review && st.live_review.kind === 'ocr';
      [s, r] = await api(API + '/stop', {}); if (s !== 200) return msg(r.error || 'Stop failed', false, true);
      msg(ocr ? 'The OCR Text Review page is closed without a verdict.'
              : st.waiting ? 'The review page is closed. Your choices so far are saved: select "Open the Review Page" to pick up where you left off.'
              : 'The review page is closed. ' + open + ' stays open. Select "Continue Review" to pick up where you left off.', true, true); return poll();
    }
    if (act === 'stop-other') {                                  // a review page the app did not start (a terminal's): asks first
      if (!await confirmDlg('Stop the other review?', 'The other review\'s session stays open; nothing is lost.', 'Stop the other review', b)) return;
      [s, r] = await api(API + '/stop-other', {}); if (s !== 200) return msg(r.error || 'Stop failed', false, true);
      msg('The other review is stopping. Its session stays open: "Continue Review" carries it on here.', true, true); return poll(true);
    }
    if (act === 'discard') {                                     // asks first; nothing is deleted, the current result stays
      const n = sn(st.open.id);
      if (!await confirmDlg('Discard ' + n + '?', 'Its choices are kept in "Session History" as abandoned; the current result (' +
                            sn(st.current.id) + ') doesn\'t change.', 'Discard ' + n, b)) return;
      [s, r] = await api(API + '/discard', {}); if (s !== 202) return msg(r.error || 'Discard failed', false, true);
      for (let i = 0; i < 30; i++) {                             // a moment: it only marks the session
        await poll(true); const j = (st.jobs || []).find(x => x.id === r.job.id);
        if (j && j.status !== 'queued' && j.status !== 'running') {
          return j.status === 'done' ? msg(cap(n) + ' is discarded: its choices are kept in "Session History" as abandoned.', true, true)
                                     : msg(cap(n) + ' could not be discarded: ' + (j.reason || j.status), false, true);
        }
        await new Promise(res => setTimeout(res, 500));
      }
      return;
    }
    if (act === 'apply') { [s, r] = await api(API + '/apply', {}); }
    else if (act === 'ocr') {
      [s, r] = await api(API + '/ocr', {});
      if (s === 202) { want = 'review'; wantAt = Date.now(); }  // goes to the OCR page when it is up, as Review again does
    }
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
  } catch (err) { msg('The app is not running. ' + START + ' Then try again.', false, true); }
});

// ---------------------------------------------------------------- following the jobs
function announce(s) {
  for (const j of s.jobs || []) {
    const key = j.status + '|' + (j.step ? j.step.words : '') + '|' + (j.url || '') + '|' + !!j.past_finish;
    const was = seen[j.id]; seen[j.id] = key;
    if (!primed || was === key) continue;
    const t = cap(j.action || j.title) + ' (' + RUN + ')';      // the action; the outcome follows from jobWords
    const low = x => x.charAt(0).toLowerCase() + x.slice(1);
    if (ended(j) && !newResult && SHOWN && s.current && s.current.id !== SHOWN) {    // one message, not two in a row
      newResult = true; live(t + ': ' + low(jobWords(j)) + '. New result ready: ' + s.current.label + '. "Show the New Result" loads it.'); continue;
    }
    if (ended(j) || j.status === 'failed' || j.status === 'interrupted') live(t + ': ' + low(jobWords(j)) + (j.reason ? '. ' + j.reason : ''));
    else if (person(j) && j.url && !j.past_finish && (!was || !was.includes(j.url))) live(t + ': the ' + (j.kind === 'ocr' ? 'OCR Text Review page' : 'review page') + ' is ready');
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
    banner('pp-offline', 'The app is not running, so this page cannot start or follow jobs; jobs already running carry on. ' + START);
    offline = true;
  }
  if (s !== undefined) {
    if (offline) { offline = false; banner('pp-offline', null); live('The app is running again.'); }
    if (s !== 200) { if (!failing) banner('pp-error', 'This run cannot be read by the app (' + (b.error || 'HTTP ' + s) + '): it may have been moved or removed. Reload the page to try again.'); failing = true; }
    else {
      if (failing) { failing = false; banner('pp-error', null); }
      const before = st; st = b;
      if (ocrSeen === undefined) ocrSeen = b.ocr ? b.ocr.recorded : null;
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
    live('The review page is ready: "Open the Review Page."');
  }
  if (want === 'result') {                                     // the page the person's Finish opened: focus its job's heading
    const j = (s.jobs || []).slice().reverse().find(x => x.kind === 'review' || x.kind === 'apply');
    want = null; history.replaceState(null, '', location.pathname);
    if (j) setTimeout(() => { const hd = $('jh-' + j.id); if (hd) hd.focus(); }, 0);
  }
  if (want === 'ocr') {                                        // Finish OCR Review: the job's heading once its page has closed
    const j = (s.jobs || []).slice().reverse().find(x => x.kind === 'ocr');
    if (!j || j.status !== 'running') {
      want = null; history.replaceState(null, '', location.pathname);
      if (s.ocr && s.ocr.verdict) live('OCR verdict recorded: ' + s.ocr.verdict + '. The report on this page includes it.');
      setTimeout(() => { const hd = j && $('jh-' + j.id); (hd || $('pp-cur')).focus(); }, 0);   // a finished job is one line: the result's heading
    }
  }
  if (!newResult && SHOWN && s.current && s.current.id !== SHOWN) {   // a new result with no job end seen here (a terminal apply)
    newResult = true; live('New result ready: ' + s.current.label + '. "Show the New Result" loads it.');
  }
}

if (q.get('landed') === '1' || q.get('opening')) history.replaceState(null, '', location.pathname);
api('/api/setup').then(([s, b]) => { if (s === 200) { setup = b; if (st) render(); } }).catch(() => {});
poll(true).then(() => {
  if (q.get('landed') === '1') { const h = $('pp-cur'); if (h) h.focus(); }
  if (q.get('opening')) { const h = $('jh-' + q.get('opening')); if (h) h.focus(); }      // from a previous result's bar
});
})();
