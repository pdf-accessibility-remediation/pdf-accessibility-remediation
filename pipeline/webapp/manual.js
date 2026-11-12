/* webapp/manual.js: the Manual Checks page (webapp/manualpage.py builds it; issue #38, stage 2). Two sections, each a
   form: its answers are saved by themselves about a second after each change (one save at a time; the browser keeps a
   copy too), and "Record …" sends them to review/manual.py, the one writer. The rules are the server's (lib/release.py
   validate()): a refused Record comes back with each problem tied to its field, shown under it and in a summary that
   takes focus. The page itself only marks a note as required when the choice asks for one.

   Accessibility (WCAG 2.1 AA): real inputs, radio groups in fieldsets with legends, errors tied to their fields
   (aria-describedby, aria-invalid), one polite live region and one alert (a failed save, a refusal); the save status is
   not announced; focus moves only after the person's own action, and to a message or the error summary. */
(() => {
'use strict';
// 15 (Patrick, 2026-11-11: page changes in one step): this script is loaded in the head and only defines. The page's data
// comes before the forms, and the page calls Pdfrem.checks() right after each form, so each one is filled (a draft kept in
// this browser, the notes each choice requires) while the page is read, before its first frame. Each call sets up the
// forms read so far that are not set up yet; the page-wide parts are set up once, at the first call.
const $ = id => document.getElementById(id);
const START = 'To start the app again, open a terminal in the project\'s pipeline folder and type python3 app.py; this page then works again.';
const say = (id, t) => { const l = $(id); l.textContent = ''; setTimeout(() => { l.textContent = t; }, 50); };
const live = t => say('mc-live', t), alarm = t => say('mc-alert', t);
async function post(path, body) {
  const r = await fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  let b = {}; try { b = await r.json(); } catch (e) {}
  return [r.status, b];
}
const store = { get(k) { try { return JSON.parse(localStorage.getItem(k) || 'null'); } catch (e) { return null; } },
                set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} },
                del(k) { try { localStorage.removeItem(k); } catch (e) {} } };
let D = null, API = null, leaving = false, once = false;

const secs = [];
function start() {
if (!D) {
  D = JSON.parse($('mc-data').textContent);
  API = '/api/run/' + D.run.split('/').map(encodeURIComponent).join('/');
  store.del('checks:by');                                       // names are never prefilled (Patrick, 2026-11-01): an old remembered one goes
}
for (const [key, cfg] of Object.entries(D.sections)) {
  const form = document.querySelector('form[data-section="' + key + '"]'); if (!form || form.dataset.mcOn) continue;
  form.dataset.mcOn = '1';                                      // set up once, at the first call after it
  const sec = { key, cfg, form, p: cfg.p, ls: 'checks:' + D.run + ':' + key, saved_at: cfg.draft_saved_at || null,
                dirty: false, inflight: false, again: false, timer: null, unsaved: false };   // unsaved: the last save failed
  secs.push(sec);
  const found = new Set(cfg.items.filter(i => i.found).map(i => i.key)), failedLast = new Set(cfg.failed_last || []);

  sec.collect = () => {
    const d = { by: '', fields: {}, items: {}, notes: '' };
    form.querySelectorAll('[data-field]').forEach(el => {
      const f = el.dataset.field;
      if (f.startsWith('fields.')) d.fields[f.slice(7)] = el.value; else d[f] = el.value;
    });
    form.querySelectorAll('fieldset[data-item]').forEach(fs => {
      const k = fs.dataset.item, r = fs.querySelector('input[type=radio]:checked'), n = fs.querySelector('textarea[data-note]');
      d.items[k] = { result: r ? r.value : '', note: n ? n.value : '' };
    });
    return d;
  };
  sec.fill = (d, results) => {                                  // results false: versions, pages and notes only, never "Checked By"
    form.querySelectorAll('[data-field]').forEach(el => {
      const f = el.dataset.field, v = f.startsWith('fields.') ? (d.fields || {})[f.slice(7)] : d[f];
      if (results || f !== 'by') el.value = v || '';
    });
    form.querySelectorAll('fieldset[data-item]').forEach(fs => {
      const it = (d.items || {})[fs.dataset.item] || {};
      fs.querySelectorAll('input[type=radio]').forEach(r => { r.checked = results && r.value === it.result; });
      const n = fs.querySelector('textarea[data-note]'); if (n) n.value = it.note || '';
      need(fs);
    });
  };
  // a note required by the choice: Fail; Not Applicable on a thing the pipeline found; Pass after a Fail on this version
  function need(fs) {
    const k = fs.dataset.item, r = fs.querySelector('input[type=radio]:checked'), v = r ? r.value : '';
    const why = v === 'fail' ? '(required)' : v === 'na' && found.has(k) ? '(required: say why it does not apply)' :
                v === 'pass' && failedLast.has(k) ? '(required: say what changed)' : '(optional)';
    const m = fs.querySelector('[data-req-for]'), n = fs.querySelector('textarea[data-note]');
    if (m) m.textContent = why;
    if (n) n.setAttribute('aria-required', why === '(optional)' ? 'false' : 'true');
  }
  form.querySelectorAll('fieldset[data-item]').forEach(need);

  const status = t => { $(sec.p + '-save').textContent = t; };
  sec.save = async () => {
    if (sec.inflight) { sec.again = true; return; }
    sec.inflight = true; sec.dirty = false; status('Saving…');
    let ok = false;
    try {
      const [c, b] = await post(API + '/checks/draft', { section: key, data: sec.collect(), saved_at: sec.saved_at, for_sha256: D.sha });
      ok = c === 200; sec.unsaved = !ok;
      // a save refused because Record went through first (409) is no news: the page is about to reload (G5)
      if (!ok) { status('Not saved'); if (!leaving && !sec.recording) alarm(b.error ? b.error : (b.errors || []).map(x => x.message).join(' ') || 'Your answers were not saved. Try again.'); }
    } catch (e) { sec.unsaved = true; status('Not saved'); if (!leaving && !sec.recording) alarm('Your answers could not be saved: the app is not running. ' + START); }
    sec.inflight = false;
    if (sec.again || sec.dirty) { sec.again = false; return sec.save(); }
    if (ok) status('All changes saved');
  };
  sec.changed = () => {
    sec.saved_at = new Date().toISOString(); sec.dirty = true;
    const kept = sec.collect(); delete kept.by;                  // the browser's copy carries no name either
    store.set(sec.ls, { data: kept, saved_at: sec.saved_at, for: D.sha });
    status('Saving…'); clearTimeout(sec.timer); sec.timer = setTimeout(sec.save, 1000);
  };
  form.addEventListener('input', sec.changed);
  form.addEventListener('change', e => { if (e.target.type === 'radio') need(e.target.closest('fieldset')); sec.changed(); });

  // the browser's copy, when it is newer than the run's (same version, not older than a recorded check's tombstone)
  const mine = store.get(sec.ls);
  if (mine && mine.for === D.sha && (!sec.saved_at || mine.saved_at > sec.saved_at) && (!cfg.tombstone || mine.saved_at > cfg.tombstone)) {
    delete mine.data.by; sec.fill(mine.data, true); sec.saved_at = mine.saved_at; sec.save();   // an old copy's name is dropped
  } else status(cfg.has_draft ? 'All changes saved' : '');

  // ---------------------------------------------------------------- Record
  const errs = $(sec.p + '-errs');
  const target = f => $(sec.p + '-' + f.replace(/\./g, '-'));
  function clearErrors() {
    errs.hidden = true; errs.innerHTML = '';
    form.querySelectorAll('.mc-err').forEach(p => { p.hidden = true; p.textContent = ''; });
    form.querySelectorAll('[aria-invalid]').forEach(x => x.removeAttribute('aria-invalid'));
  }
  function showErrors(list, text) {
    errs.innerHTML = '<h4 id="' + sec.p + '-errs-h">' + (text ? 'Not Recorded' : 'Fix These Before Recording') + '</h4>' +
      (text ? '<p></p>' : '<ul></ul>');
    if (text) errs.querySelector('p').textContent = text;
    for (const x of list || []) {
      const t = target(x.field), li = document.createElement('li');
      if (t) {
        const a = document.createElement('a'); a.href = '#' + t.id; a.textContent = x.message; li.appendChild(a);
        const p = $(t.id + '-err'); if (p) { p.textContent = x.message; p.hidden = false; }
        (t.tagName === 'FIELDSET' ? t.querySelectorAll('input[type=radio]') : [t]).forEach(el => el.setAttribute('aria-invalid', 'true'));
      } else li.textContent = x.message;
      errs.querySelector('ul').appendChild(li);
    }
    errs.hidden = false; errs.focus();
  }
  errs.addEventListener('click', e => {                          // a summary link: focus the field (a group: its first choice)
    const a = e.target.closest('a[href^="#"]'); if (!a) return;
    const t = $(a.getAttribute('href').slice(1)); if (!t) return;
    e.preventDefault(); t.scrollIntoView({ block: 'center' });
    (t.tagName === 'FIELDSET' ? (t.querySelector('input:checked') || t.querySelector('input')) : t).focus();
  });
  form.addEventListener('submit', async e => {
    e.preventDefault();
    clearTimeout(sec.timer);                                     // no auto-save after this: Record carries the last draft time
    const b = form.querySelector('button[type=submit]'); if (b.disabled) return;
    b.disabled = true; clearErrors(); sec.recording = true;
    try {
      const [c, r] = await post(API + '/checks/record', { section: key, data: sec.collect(), shown_sha256: D.sha, draft_saved_at: sec.saved_at });
      if (c === 200) {
        store.del(sec.ls); sec.dirty = false; sec.unsaved = false; leaving = true;
        location.replace('checks?recorded=' + encodeURIComponent(key) + '#mc-msg'); return;   // this page's own address (35)
      }
      if (c === 400 && r.errors) showErrors(r.errors);
      else { showErrors([], r.error || 'The app refused this.'); alarm(r.error || 'The app refused this.'); }
    } catch (err) { showErrors([], 'The app is not running. ' + START + ' Your answers are kept in this browser.'); }
    b.disabled = false; sec.recording = false;
    if (sec.dirty) sec.save();                                   // not recorded: the auto-save cancelled above carries on
  });
}

if (once) return;                                              // the page-wide parts: once
once = true;

// ---------------------------------------------------------------- Start from These Notes (never the results)
document.addEventListener('click', e => {
  const b = e.target.closest('button[data-start]'); if (!b) return;
  const [key, which] = b.dataset.start.split(':'), sec = secs.find(x => x.key === key); if (!sec) return;
  const d = which === 'draft' ? sec.cfg.start_draft : sec.cfg.starts[Number(which)]; if (!d) return;
  sec.fill(d, false); sec.changed();
  live('Versions, pages and notes copied. Enter your name in "Checked By" and choose each result again for this version.');
  const f = sec.form.querySelector('[data-field="by"]'); if (f) f.focus();
});

// a change not saved yet, or whose save failed: the browser's leave-page prompt (the browser's copy keeps it anyway)
addEventListener('beforeunload', e => { if (!leaving && secs.some(s => s.dirty || s.inflight || s.unsaved)) { e.preventDefault(); e.returnValue = ''; } });

// ---------------------------------------------------------------- "Available Downloads" (stage 3)
// the line under the picker says how the chosen version's files are marked; a shipped version has none: the line is hidden
// and the select no longer described by it (as panel.js dlMarked())
const dlv = $('mc-dlv');
function dlMarked() {
  const p = $('mc-dl-marked'), m = dlv.selectedOptions[0].dataset.marked;
  p.textContent = m; p.hidden = !m;
  if (m) dlv.setAttribute('aria-describedby', p.id); else dlv.removeAttribute('aria-describedby');
}
if (dlv) dlv.addEventListener('change', dlMarked);

if (new URLSearchParams(location.search).get('recorded')) {      // after Record: the message, then the plain address
  history.replaceState(null, '', location.pathname);
  const m = $('mc-msg'); if (m) m.focus();
}
}
const P = window.Pdfrem = window.Pdfrem || {}; P.checks = start;
})();
