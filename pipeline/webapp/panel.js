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
         (from === 'ai' ? 'the AI\'s decisions' : sn(from)) + ' marks it abandoned; its choices stay in "Session History".';
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
    '<a class="pp-btn" href="' + BASE + '">Back to the Current Result</a> <span id="pp-vact"></span></p>' +
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
let quiet = true, wantAt = 0, land = null;
['keydown', 'pointerdown'].forEach(e => addEventListener(e, () => { quiet = false; if (land) land.moved = true; }, true));
// what the person's last action is waiting for: after=finish (the review page's Finish), after=ocr (Finish OCR Review: this
// page was loaded after the verdict was written, so its report already has it)
let want = q.get('after') === 'finish' ? 'result' : q.get('after') === 'ocr' ? 'ocr' : q.get('opening') ? 'review' : null;
if (want === 'review') wantAt = Date.now();                    // Review again from a previous result's bar
let st = null, setup = null, primed = false, offline = false, failing = false, timer = null, newResult = false;
const SHOWN = box.dataset.current || null;                     // the session whose result this page shows (set when served)
const WAITING = box.dataset.waiting === '1';                   // served before the first review (REVIEW=1): no result yet
let ocrSeen;                                                    // the OCR verdict's `recorded` when this page's report was read
const seen = {};                                                // per job: the last step and status announced

// D7: the panel keeps the height it had on the last page until its first draw, so the report below does not jump when
// the person moves from PDF to PDF (sessionStorage: this tab only)
const HKEY = 'pp-h:' + (WAITING ? 'w' : 'r');
try { const h = +sessionStorage.getItem(HKEY); if (h > 0) box.style.minHeight = h + 'px'; } catch (e) {}
let sized = false;
function keepHeight() {
  if (!sized) { sized = true; box.style.minHeight = ''; }
  try { sessionStorage.setItem(HKEY, String(box.offsetHeight)); } catch (e) {}
}
addEventListener('pagehide', keepHeight);
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
  if (j.status === 'queued') return j.waiting_for ? 'Waiting: it starts when ' + j.waiting_for + ' ends' + (j.position > 1 ? ' (' + ordinal(j.position) + ' in line)' : '')
                                                    : 'Waiting' + (j.position ? ': ' + ordinal(j.position) + ' in line' : '');
  if (j.status === 'running') {
    if (j.kind === 'ocr') return j.url ? 'Waiting for you: the OCR Text Review page is open' : 'Opening the OCR Text Review page';
    if (j.kind === 'review' && !j.past_finish) return j.url ? 'Waiting for you: the review page is open' : 'Opening the review page';
    return 'Running' + (j.step ? ': ' + stepWords(j) : '');
  }
  if (j.status === 'needs-spend') return 'Waiting for a new estimate (the app restarted before the AI call)';
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
  if (j.reason) h += '<p><b>Why:</b> ' + esc(j.reason) + '</p><p class="pp-note">The job\'s full output, for whoever looks after the app, is saved in ' + esc(j.log) + '.</p>';
  return h + '</article>';
}

function jobsBlock(s, noLast) {
  // running, waiting, and failed or interrupted ones not followed by a success: cards; the last finished one: one line;
  // every other finished one: folded under "Previous Jobs". Nothing drops off. One-line places are sentence case.
  const all = (s.jobs || []).slice().reverse();                 // newest first
  const lastOk = all.findIndex(ended);
  const card = all.filter((j, i) => j.status === 'queued' || j.status === 'running' || j.status === 'needs-spend' ||
                                    ((j.status === 'failed' || (j.status === 'interrupted' && !lost(j))) && (lastOk < 0 || i < lastOk)));
  const last = lastOk >= 0 ? all[lastOk] : null;
  const previous = all.filter(j => !card.includes(j) && j !== last);   // noLast (the estimate card, P12): the last job is not shown at all
  if (!card.length && !last && !previous.length) return '';
  let h = card.map(jobCard).join('');
  if (last && !noLast) h += '<p class="pp-last"><b>Last Job:</b> ' + esc(cap(last.title)) + '</p>';
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
  const from = s.open ? null : s.latest ? cap(sn(s.latest.id)) : s.legacy_review ? 'the review recorded before sessions were kept' : 'the AI\'s decisions';
  h += s.open ? '<button type="button" class="pp-primary" id="pp-review" data-act="review">' + esc(tc('Continue review (' + cap(s.open.label) + ', open)')) + '</button>'
              : '<button type="button" class="pp-primary" id="pp-review" data-act="review">' + esc(tc('Review again (from ' + from + ')')) + '</button>';
  if (s.open) h += '<button type="button" id="pp-discard" data-act="discard">' + esc(tc('Discard ' + s.open.label)) + '</button>';
  if (s.latest || s.open) h +='<button type="button" id="pp-ai" data-act="review" data-from="ai">Start Over from the AI\'s Decisions</button>';
  if (s.unapplied && !s.open) h += '<button type="button" id="pp-apply" data-act="apply" aria-describedby="pp-unapplied">Try Again</button>' +
    '<span class="pp-note" id="pp-unapplied">' + esc(cap(s.unapplied.label)) + ' was finished and not applied.</span>';
  h += '</div>';
  if (s.ocr && s.ocr.needed)                                     // the OCR text verdict, on its own (no work-order session)
    h += '<div class="pp-row"><button type="button" id="pp-ocr" data-act="ocr">Review OCR Text</button>' +
         '<span class="pp-note">OCR Text: ' + esc(tc(s.ocr.verdict || 'not yet reviewed')) + '</span></div>';
  if (!s.pinned) h += '<p class="pp-note">Review again first re-audits this run to pin it (free, a minute or more).</p>';
  return h;
}

// "Clean Up Space" (stage 3, review/prune.py): the button alone, shown only when a previous version's PDF can be removed;
// the explanation is in its dialog (Patrick, 2026-11-01)
const PRUNE_LINE = 'Deletes the PDF files of the previous versions you select to free up space. Their records and decisions stay in "Session History". The original AI-generated version is always kept.';
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
      if (!name) { $('pp-prune-err').textContent = 'Enter your name in "Removed By".'; $('pp-prune-by').focus(); return; }
      done({ by: name, chosen: vs.map(v => ({ id: v.id, sha256: v.sha256 })) });
    });
    d.oncancel = ev => { ev.preventDefault(); done(null); };
    d.showModal(); $('pp-prune-0').focus();
  });
}
// "Clear This Book's Files" (#45): only here, only once its gate is open (a shipped book whose record ZIP was downloaded);
// never prompted or suggested anywhere else. The dialog says what goes and what stays, and asks for a name and CLEAR.
function clearBlock(s) {
  if (!s.clear) return '';
  return '<div class="pp-row"><button type="button" id="pp-clear" data-act="clear">Clear This Book\'s Files</button></div>';
}
function clearDlg(c, opener) {
  return new Promise(res => {
    const d = $('pp-dlg');
    d.innerHTML = '<h2 id="pp-dlg-h">Clear This Book\'s Files</h2>' + (c.resume ? '<p>Clearing stopped partway; this finishes it.</p>' : '') +
      '<p>Deletes the working files this book no longer needs now that it has shipped' + (c.shipment ? ' (Shipment ' + esc(c.shipment) + ')' : '') + ', to free up space:</p><ul>' +
      c.goes.map(g => '<li>' + esc(g.what) + ' · ' + esc(g.size) + '</li>').join('') + '</ul><p>Kept: every record (the decisions, the reviews, the evaluation, ' +
      'the reports), the shipped copy with its report, and the original PDF. Afterwards this book can\'t be reviewed or changed here; a new run of it can.</p>' +
      '<p><label for="pp-clear-by">Your Name</label><br><input type="text" id="pp-clear-by" autocomplete="name"></p>' +
      '<p><label for="pp-clear-ok">Type ' + esc(c.confirm) + ' to Confirm</label><br><input type="text" id="pp-clear-ok" autocomplete="off" spellcheck="false"></p>' +
      '<p>This can\'t be undone.</p><p id="pp-clear-err" class="pp-warn-t" role="alert"></p><div><button type="button" class="pp-primary" value="yes">Clear This Book\'s Files</button>' +
      '<button type="button" value="no">Cancel</button></div>';
    const id = opener.id, done = v => { d.close(); ($(id) || opener).focus(); res(v); };
    d.querySelector('button[value=no]').addEventListener('click', () => done(null));
    d.querySelector('button[value=yes]').addEventListener('click', () => {
      const by = $('pp-clear-by').value.trim(), ok = $('pp-clear-ok').value.trim();
      if (!by) { $('pp-clear-err').textContent = 'Enter your name in "Your Name".'; $('pp-clear-by').focus(); return; }
      if (ok !== c.confirm) { $('pp-clear-err').textContent = 'Type ' + c.confirm + ' to confirm.'; $('pp-clear-ok').focus(); return; }
      done({ by, confirm: ok });
    });
    d.oncancel = ev => { ev.preventDefault(); done(null); };
    d.showModal(); d.querySelector('button[value=no]').focus();
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
      (r.notes ? '<button type="button" class="pp-link" id="pp-notes-' + esc(r.id) + '" data-act="notes" data-id="' + esc(r.id) + '">Notes</button>' : 'none') + '</td><td>' + (r.current ? 'this page' : r.result ? '<a class="pp-btn" href="' + esc(r.result) + '">Open the Previous Result</a>' : 'none') + (r.pdf_removed ? '<span class="pp-note"> · PDF removed</span>' : '') +
      '</td><td>' + ((r.status === 'finished' || r.status === 'applied') && !s.live_review && !s.lock && !s.cleared ? '<button type="button" id="pp-from-' + esc(r.id) + '" data-act="review" data-from="' + esc(r.id) + '">' + esc(tc('Review again from ' + r.label)) + '</button>' : '') +
      '</td></tr>').join('') + '</tbody></table></div>';
  if (s.ai_result) h += '<p class="pp-row"><a class="pp-btn" href="' + esc(s.ai_result) + '">Open the Result Applied Without Review</a> <span class="pp-note">(kept with the run)</span></p>';
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
  if (!(st && st.cleared)) h += '<div class="pp-row"><a class="pp-btn pp-primary" id="pp-mc-open" href="checks">Complete Evaluation</a></div>';
  h += shipBlock(m.ship) + dlForm(m.downloads, inPanel ? 'h4' : 'h3') + '</section>';
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
      if (!name) { $('pp-ship-err').textContent = 'Enter your name in "Shipped By".'; $('pp-ship-by').focus(); return; }
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

// A run stopped for its first review (REVIEW=1): "Open the Review Page"; "Finish Review" then applies at once (D3: run_api.sh's
// second call); once applied, the page offers its first result (it never reloads by itself)
function waitingBlock(s) {
  const w = s.waiting, active = (s.jobs || []).filter(j => j.status === 'queued' || j.status === 'running');
  if (!w) return '<p><b>Result Ready:</b> ' + (s.current && s.current.id === 'ai' ? 'The AI\'s decisions are applied (without a review).' : 'Session 1 is applied.') +
    ' The report and the remediated PDF are ready.</p>' +
    '<div class="pp-row"><button type="button" class="pp-primary" id="pp-show" data-act="reload">Show the Result</button></div>';
  if (s.live_review) return '';                                  // its own card has Open / Stop
  if (active.length) return active[0].kind === 'apply' ?
    '<p>' + (active[0].status === 'running' ? '<span class="pp-spin" aria-hidden="true"></span>Applying the reviewed decisions. This page follows each step.' :
             'Waiting to Start: the reviewed decisions are applied when ' + esc(active[0].waiting_for || 'the runs before it') + ' end' + (active[0].waiting_for ? 's' : '') + '.') + '</p>' :
    '<p>A job for this run is ' + (active[0].status === 'running' ? 'running' : 'waiting') + ': ' + esc(active[0].title) + '.</p>';
  if (!w.reviewed) return '<p>The AI\'s decisions are waiting for your review. Nothing has been applied yet.</p>' +
    '<div class="pp-row"><button type="button" class="pp-primary" id="pp-review" data-act="review">Open the Review Page</button></div>';
  const who = 'Review finished (' + esc(w.reviewer || 'reviewer not recorded') + ', ' + esc(fmtDay(w.date)) + '). ';
  if (w.auto && w.auto.state === 'starting')                     // D3: "Finish Review" starts the apply; the dispatcher makes it within a second
    return '<p><span class="pp-spin" aria-hidden="true"></span>' + who + 'Applying the reviewed decisions.</p>';
  if (w.auto && (w.auto.state === 'refused' || w.auto.state === 'failed'))   // never the spinner after a failed apply (review 10 M1)
    return '<div class="pp-fail"><h4>' + (w.auto.state === 'failed' ? 'Stopped: The Apply Didn\'t Finish' : 'Stopped: The Apply Couldn\'t Start') + '</h4><p>' +
      who + esc(w.auto.why || '') + '</p>' +
      '<div class="pp-row"><button type="button" class="pp-primary" id="pp-apply" data-act="apply">Try Again</button></div></div>';
  return '<p>' + who + 'Nothing has been applied yet: this review was finished before "Finish Review" applied it by itself.</p>' +   // an older review
    '<div class="pp-row"><button type="button" class="pp-primary" id="pp-apply" data-act="apply">Apply the Reviewed Decisions</button></div>';
}

// ---------------------------------------------------------------- a run started from the home page, before its result (#45)
// The estimate (lib/costs.py, one renderer for every page), the button that starts the paid call, the progress of the
// jobs, and why it stopped with what the person can do (webapp/failures.py: plain words; the tool's own words only under
// "Details"). The paid call is bound to the worst case shown (MAX_USD); the button is "Start Remediation" (Patrick, 2026-11-06),
// described by the worst-case line (aria-describedby).
const usd = x => '$' + Number(x || 0).toFixed(2);
function costLine(e) {
  const x = e.expected;                                          // #65 (dollar-only cost limits) fills it; shown only when present
  return (x ? 'About ' + usd(x.usd) + (x.low != null && x.high != null ? ' (usually ' + usd(x.low) + '–' + usd(x.high) + ')' : '') + ' · ' : '') +
    'Worst-case estimate ' + usd(e.ceiling_usd) + ' · Limit ' + usd(e.limits.per_call_usd) + ' per AI call' +
    (e.limits.per_book_usd ? ' · Limit ' + usd(e.limits.per_book_usd) + ' per book' : '') +
    (e.spent_before_usd ? ' · Already spent on this book ' + usd(e.spent_before_usd) : '') +
    (e.credit_usd != null ? ' · Credit ' + usd(e.credit_usd) : ' · Credit not checked');
}
const NEXT = { estimate: ['estimate', 'Get a New Estimate'], retry: ['retry', 'Try Again'], dismiss: ['dismiss', 'Dismiss'], home: null };
function failureCard(f) {
  if (!f) return '';
  const d = f.details || {};
  const btns = (f.next || []).map(n => NEXT[n] ? '<button type="button" id="pp-next-' + n + '" data-act="' + NEXT[n][0] + '">' + esc(NEXT[n][1]) + '</button>' : '').join('');
  return '<div class="pp-fail" role="group" aria-labelledby="pp-fail-h"><h4 id="pp-fail-h">' + esc('Stopped: ' + f.headline) + '</h4>' +
    (f.meaning ? '<p>' + esc(f.meaning) + '</p>' : '') +
    '<h4>What You Can Do</h4>' + (f.todo ? '<p>' + esc(f.todo) + '</p>' : '') + (btns ? '<div class="pp-row">' + btns + '</div>' : '') +
    '<details id="pp-fail-d"><summary>Details</summary><ul class="pp-note">' +
    (d.step ? '<li>Step: ' + esc(d.step) + '</li>' : '') + (d.exit != null ? '<li>Exit code: ' + esc(d.exit) + '</li>' : '') +
    (d.line ? '<li>Message: <code>' + esc(d.line) + '</code></li>' : '') + (d.record ? '<li>Recorded in: ' + esc(d.record) + '</li>' : '') +
    (d.command ? '<li>From the terminal: <code>' + esc(d.command) + '</code></li>' : '') +
    (d.log ? '<li>Full log: ' + esc(d.log) + '</li>' : '') + '</ul></details></div>';
}
function pendingBlock(s) {
  const e = s.estimate;
  let h = s.test ? '<p class="pp-bar pp">Test: saved replies, no AI call.</p>' : '';
  if (s.phase === 'outside') return h + (s.failure ? failureCard(Object.assign({}, s.failure, { next: [] })) : '') +
    '<p>This run was started outside the app, so it can\'t be sent or started again from here. To send this book, start a new run of it from the home page.</p>';
  if (s.phase === 'batch') return h + (s.failure ? failureCard(Object.assign({}, s.failure, { next: [] })) : '') +
    '<p>This book is part of the batch "' + esc(s.batch_name || s.batch) + '". Its estimate, "Start Remediation" and what to do next are on the batch page.</p>' +
    '<div class="pp-row"><a class="pp-btn pp-primary" href="/batch/' + encodeURIComponent(s.batch) + '/">Open the Batch Page</a></div>';
  if (s.phase === 'active') return h + '<p>Working on this book. This page follows each step; you can leave it and come back from the home page.</p>';
  if (s.phase === 'needs-spend') return h + '<p>The app restarted before the AI call started, so nothing was sent. Get a new estimate, then select "Start Remediation" again.</p>' +
    '<div class="pp-row"><button type="button" class="pp-primary" id="pp-reest" data-act="estimate">Get a New Estimate</button>' +
    '<button type="button" id="pp-dismiss" data-act="dismiss">Dismiss</button></div>';
  if (s.phase === 'language') return h + langCard(s.language, 'pp-lang');
  if (s.phase === 'stopped') return h + failureCard(s.failure);
  if (s.phase === 'saved-reply') return h + '<p>No AI call is needed: the AI\'s reply from an earlier attempt is saved and will be used again, at no cost.</p>' +
    '<div class="pp-row"><button type="button" class="pp-primary" id="pp-retry" data-act="retry">Continue</button></div>';
  if (!e) return h + '<p>This run has no estimate yet.</p><div class="pp-row"><button type="button" class="pp-primary" id="pp-reest" data-act="estimate">Get a New Estimate</button></div>';
  h += '<p id="pp-cost"><b>' + esc(costLine(e)) + '</b></p>';                // P12: no "Review First" or "Sent to the AI" lines
  if (!s.spend || !s.spend.ok) return h + '<p class="pp-warn-t">' + esc((s.spend && s.spend.why) || 'This run can\'t be sent yet.') + '</p>' +
    '<p>' + esc(s.spend && ['per_call', 'per_book', 'credit', 'no_credit', 'model'].includes(s.spend.code) ? 'Whoever looks after the app can raise the limit or add credit; then select "Get a New Estimate".' : 'Select "Get a New Estimate" to try again.') + '</p>' +
    '<div class="pp-row"><button type="button" id="pp-reest" data-act="estimate">Get a New Estimate</button></div>';
  return h +
    '<div class="pp-row"><button type="button" class="pp-primary" id="pp-spend" data-act="spend" aria-describedby="pp-cost">Start Remediation</button></div>' +
    (s.test ? '<p class="pp-note">Test: "Start Remediation" uses the saved reply; nothing is sent to the AI service.</p>' :
    '<p class="pp-note">"Start Remediation" sends the book to the AI service. The cost is bound to the worst-case estimate above; the real cost is usually much lower.</p>');
}
// "Language of the Scanned Pages" (D4): intake's suggestion preselected, its evidence in plain words; nothing preselected
// when the characters can't tell (Chinese or Japanese is never guessed), and then "Continue" needs a choice
function langCard(q, id) {
  if (!q) return '';
  const opts = (q.suggested ? '' : '<option value="" selected disabled>Choose a language</option>') +
    q.choices.map(c => '<option value="' + esc(c[0]) + '"' + (c[0] === q.suggested ? ' selected' : '') + '>' + esc(c[1]) + '</option>').join('');
  return '<p>' + (q.kind === 'cjk' ? 'The scanned pages need a language with Chinese, Japanese or Korean characters before they can be read (OCR).' :
      (q.pages === 1 ? '1 page of this PDF is a scan with no text, so it is read by OCR. Choose the language it is in.' :
       (q.pages ? q.pages + ' pages of this PDF are scans' : 'Some pages are scans') + ' with no text, so they are read by OCR. Choose the language they are in.')) + '</p>' +
    (q.evidence && q.evidence.length ? '<ul class="pp-note">' + q.evidence.map(x => '<li>' + esc(x) + '</li>').join('') + '</ul>' : '') +
    (q.suggested ? '<p class="pp-note">The suggestion below comes from these findings; check it before you continue.</p>' : '') +
    '<div class="pp-row pp-lang"><label for="' + id + '">Language of the Scanned Pages</label><select id="' + id + '">' + opts + '</select>' +
    '<button type="button" class="pp-primary" data-act="language" data-sel="' + id + '">Continue</button></div>';
}
const PHASE = { language: 'Language of the Scanned Pages', outside: 'Started Outside the App', batch: 'Part of a Batch', active: 'In Progress', estimate: 'Cost Estimate', 'needs-spend': 'Waiting for a New Estimate', stopped: 'Stopped', 'saved-reply': 'No AI Call Is Needed', new: 'Not Started' };

// After a redraw: focus back on the element that had it (by id). When that element is gone (a finished job's card becomes
// one line), focus goes to the panel's heading rather than being lost; for the Spend's landing (03 §14) that is still
// where the panel put it, not a move by the person.
function refocus(keepFocus) {
  if (!keepFocus) return;
  if ($(keepFocus) && box.contains($(keepFocus))) { $(keepFocus).focus(); return; }
  if (/^jh-/.test(keepFocus) && $('pp-cur')) { $('pp-cur').focus(); if (land && land.id === keepFocus) land.id = 'pp-cur'; }
}

function render() {
  if (WAITING && st.mode === 'pending') {                        // before the result: the estimate, Spend, the progress
    const h = setupBlock() + '<h3 id="pp-cur" tabindex="-1">' + esc(PHASE[st.phase] || 'This Run') + '</h3>' + pendingBlock(st) + jobsBlock(st, true),
          body = $('pp-body'), keepFocus = document.activeElement && document.activeElement.id;
    if (body.dataset.h === h) return;
    body.innerHTML = h; body.dataset.h = h;
    refocus(keepFocus);
    return;
  }
  if (WAITING) {                                                 // no result, no strip: the review, then the first apply
    const h = setupBlock() + '<h3 id="pp-cur" tabindex="-1">' + esc(tc(!st.waiting ? 'First result' : !st.waiting.reviewed ? 'Waiting for review' :
      st.waiting.auto && st.waiting.auto.state !== 'starting' ? 'Stopped' : 'Applying the reviewed decisions')) + '</h3>' +
      waitingBlock(st) + jobsBlock(st), body = $('pp-body'), keepFocus = document.activeElement && document.activeElement.id;
    if (body.dataset.h === h) return;
    body.innerHTML = h; body.dataset.h = h;
    refocus(keepFocus);
    return;
  }
  renderStrip(st);
  const s = st, keepFocus = document.activeElement && document.activeElement.id, opened = [...box.querySelectorAll('details[open]')].map(d => d.id);
  // "Ready to ship?" is not repeated here: the report's own card, right below, says it
  const c = s.cost;
  let h = setupBlock() + (s.pdf_moved ? '<p class="pp-warn">' + esc(s.pdf_moved.text) + '</p>' : '') + (s.batch ? '<p class="pp-row">Part of the batch "' + esc(s.batch_name || s.batch) + '". <a class="pp-btn" href="/batch/' + encodeURIComponent(s.batch) + '/">Open the Batch Page</a></p>' : '') +
    (c ? '<p class="pp-note">AI Cost: ' + (c.reused ? 'none (a saved reply was used)' : usd(c.usd) +
      (c.estimate_usd ? ' (worst-case estimate ' + usd(c.estimate_usd) + ')' : '')) + '</p>' : '') +
    '<h3 id="pp-cur" tabindex="-1">' + esc(tc('Current result: ' + s.current.label)) + '</h3>';
  if (s.pending) h += '<p>' + esc(sn(s.pending.session)) + ' is ' + esc(s.pending.status) + ' and not applied yet, so the book stays "Not Ready" until it is.</p>';
  if (newResult) h += '<p><b>New Result Ready:</b> ' + esc(cap(s.current.label)) + ' is now the current result; the report below is the previous one.</p>' +
    '<div class="pp-row"><button type="button" class="pp-primary" id="pp-show" data-act="reload">Show the New Result</button></div>';
  else if (s.ocr && ocrSeen !== undefined && s.ocr.recorded !== ocrSeen)   // a verdict recorded since this page loaded: never reloads by itself
    h += '<p><b>OCR Verdict Recorded:</b> ' + esc(s.ocr.verdict || 'a new verdict') + '. The report below was made before it.</p>' +
      '<div class="pp-row"><button type="button" class="pp-primary" id="pp-show" data-act="reload">Show the Updated Report</button></div>';
  if (s.cleared) h += '<div class="pp-msg pp-okmsg pp-cleared"><span class="pp-msg-t">' + (s.cleared.state === 'done' ?
      'This book\'s working files were cleared on ' + esc(s.cleared.day) + (s.cleared.shipment ? ' after it shipped as Shipment ' + esc(s.cleared.shipment) : '') +
      ' (' + esc(s.cleared.mb) + ' MB freed). Its records and the shipped copy are kept; to work on it again, start a new run of the book from the home page.'
      : 'Clearing this book\'s files stopped partway. "Clear This Book\'s Files" finishes it.') + '</span></div>';
  if (s.replay) h += '<p>A new run of this book from its saved AI reply can be made instead (free, no AI call; it runs on today\'s pipeline, so it is not a review of this result).</p>' +
    '<div class="pp-row"><button type="button" id="pp-replay" data-act="replay">New Run from the Saved Reply</button></div>';
  h += (s.cleared && s.cleared.state === 'done' ? '' : actions(s)) + jobsBlock(s) + historyBlock(s) + (s.cleared ? '' : pruneBlock(s)) + clearBlock(s);
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
  if (act === 'clear') {                                         // "Clear This Book's Files": then the home page
    const c = st.clear; if (!c) return;
    const v = await clearDlg(c, b); if (!v) return;
    try {
      const [code, r] = await api(API + '/clear', v);
      if (code !== 200) return msg(r.error || 'The files were not cleared.', false, true);
      location.assign(r.location || '/'); return;
    } catch (e) { return msg('The app is not running. ' + START, false, true); }
  }
  if (act === 'prune') {                                         // "Clean Up Space": select in the dialog, then remove exactly those
    const p = st.prune; if (!p) return;
    const v = await pruneDlg(p, b); if (!v) return;
    try {
      const [c, r] = await api(API + '/remove-older-pdfs', { by: v.by, chosen: v.chosen });
      if (c !== 200) return msg(r.error || 'The PDFs were not removed.', false, true);
      msg('Removed ' + r.removed + ' PDF' + (r.removed === 1 ? '' : 's') + ' (' + (r.bytes / 1e6).toFixed(1) + ' MB freed). ' + (r.removed === 1 ? 'Its record and decisions are' : 'Their records and decisions are') + ' kept in "Session History".', true, true);
      return poll(true);
    } catch (e) { return msg('The app is not running. ' + START, false, true); }
  }
  msg('');                                                       // any other panel button clears the message too
  if (act === 'reload') { location.replace(location.pathname + '?landed=1'); return; }
  if (['spend', 'estimate', 'dismiss', 'retry', 'replay', 'language'].includes(act)) {
    try {
      let s, r;
      if (act === 'language') {                                 // D4: the answer, then the estimate again
        const v = $(b.dataset.sel).value;
        if (!v) { msg('Choose a language first.', false, true); $(b.dataset.sel).focus(); return; }
        [s, r] = await api(API + '/language', { lang: v });
      } else if (act === 'spend') {
        [s, r] = await api(API + '/spend', { kind: 'workorder', fingerprint: st.estimate.fingerprint });
      } else if (act === 'replay') {
        if (!await confirmDlg('New run from the saved reply?', 'A new run of this book is made from its saved AI reply, free, and stops for your review. This run stays as it is.', 'Make the new run', b)) return;
        [s, r] = await api(API + '/replay', { label: st.replay.label });
        if (s === 202 && r.location) { location.assign(r.location); return; }
      } else [s, r] = await api(API + '/' + act, {});
      if (act === 'dismiss') { if (s !== 200) return msg(r.error || 'The app refused this', false, true); msg('Dismissed: nothing was sent.', true, true); return poll(true); }
      if (s !== 202) return msg(r.error || 'The app refused this', false, true);
      quiet = true;
      await poll(true);
      const hd = $('jh-' + r.job.id); if (hd) hd.focus();
      if (act === 'spend') land = { id: 'jh-' + r.job.id, moved: false, done: false };   // where the Spend left focus (03 §14)
    } catch (err) { msg('The app is not running. ' + START + ' Then try again.', false, true); }
    return;
  }
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
    const t = cap(j.action || j.title) + (j.run_name ? ' (' + j.run_name + ')' : '');   // the action and the run's plain name (never its folder label)
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
      const focusWas = document.activeElement && document.activeElement.id;   // before a redraw replaces the job card
      if (ocrSeen === undefined) ocrSeen = b.ocr ? b.ocr.recorded : null;
      announce(b);
      followUp(b);
      if (force || JSON.stringify(before) !== JSON.stringify(b)) render();
      if (!sized) keepHeight();
      landed(b, land && focusWas && !$(focusWas) && land.id === 'pp-cur' ? 'pp-cur' : focusWas);
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

// When a Spend's run stops for review (03 §14, Patrick 2026-11-05): focus moves to "Open the Review Page" only when focus is
// still where the panel put it after the Spend click (by its id: the card is redrawn while polling) and no key or pointer
// has been pressed since; otherwise the page announces it and shows the button (docs/app.md: focus stays where it is).
function landed(s, focusWas) {
  if (!land || land.done) return;
  if (s.mode === 'waiting' && s.waiting && !s.waiting.reviewed) {
    if (!$('pp-review')) return;                                  // its job is still finishing: the button comes with the next poll
    land.done = true;
    if (!land.moved && focusWas === land.id && $('pp-review')) { $('pp-review').focus(); live('The AI\'s decisions are ready for your review: "Open the Review Page".'); }
    else live('The AI\'s decisions are ready for your review: "Open the Review Page".');
  } else if (s.mode === 'finished') { land.done = true; live('The run has finished: "Show the Result" loads it.'); }
}

function followUp(s) {
  const lr = s.live_review;
  if (want === 'review' && lr && lr.url && !lr.past_finish) {
    want = null;
    if (quiet && Date.now() - wantAt < 30000) { location.assign(lr.url); return; }   // right after the person's Review again
    live('The review page is ready: "Open the Review Page".');
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
