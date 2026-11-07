/* webapp/home.js: the home page's own script (#45, home interface): "Add a PDF" (the chosen PDF is sent to the app as it is;
   the file on the person's computer is only read), New Batch's selection, and the live "Runs in Progress" list (shown only
   while something runs or waits to start).

   Accessibility: every action is a real button or link; messages go to a message box that takes focus after the person's
   own action; the list of runs in progress is redrawn quietly and only a job that ends is announced (one polite live
   region). Focus never moves by itself. */
(() => {
'use strict';
const $ = id => document.getElementById(id);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const enc = run => run.split('/').map(encodeURIComponent).join('/');
const START = 'To start the app again, open a terminal in the project\'s pipeline folder and type python3 app.py.';
function msg(text, ok) {
  const m = $('hm-msg'); m.hidden = !text; m.classList.toggle('pp-okmsg', !!ok);
  m.innerHTML = text ? '<span class="pp-msg-t">' + esc(text) + '</span><button type="button" class="pp-x" aria-label="Dismiss message"><span aria-hidden="true">×</span></button>' : '';
  if (text) m.focus();
}
$('hm-msg').addEventListener('click', e => { if (e.target.closest('button')) { msg(''); ($('hm-file') || document.querySelector('form [name]')).focus(); } });

// ---------------------------------------------------------------- the New Run and New Batch forms: JSON to the app, then its page
document.querySelectorAll('form[data-api]').forEach(f => f.addEventListener('submit', async e => {
  e.preventDefault();
  const body = {};
  f.querySelectorAll('[name]').forEach(x => {
    if (x.name === 'books') { if (x.type !== 'checkbox' || x.checked) (body.books = body.books || []).push(x.value); }   // a list
    else if (x.type === 'checkbox') body[x.name] = x.checked;
    else body[x.name] = x.value;
  });
  const b = f.querySelector('button[type=submit]'); b.disabled = true;
  try {
    const r = await fetch(f.dataset.api, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    let d = {}; try { d = await r.json(); } catch (err) {}
    if (r.status === 202 && d.location) { location.assign(d.location); return; }
    msg(d.error || 'The app refused this.');
  } catch (err) { msg('The app is not running. ' + START); }
  finally { b.disabled = false; }
}));
if (!$('hm-active')) return;                                      // the New Run and New Batch pages stop here

// ---------------------------------------------------------------- Add a PDF
if ($('hm-add')) $('hm-add').addEventListener('submit', async e => {
  e.preventDefault();
  const f = $('hm-file').files[0];
  if (!f) { msg('Choose a PDF first: "Add a PDF" opens your files.'); return; }
  const b = $('hm-add-b'); b.disabled = true; msg('Adding "' + f.name + '"…', true);
  try {
    const r = await fetch('/api/upload', { method: 'POST', body: f,
      headers: { 'Content-Type': 'application/pdf', 'X-Pdfrem-Upload': '1', 'X-Pdfrem-Filename': encodeURIComponent(f.name) } });
    let d = {}; try { d = await r.json(); } catch (err) {}
    if (r.status === 201) { location.assign('/book?added=1&key=' + encodeURIComponent(d.book.key)); return; }   // check its name
    msg(d.error || 'The PDF was not added.');
  } catch (err) { msg('The app is not running. ' + START); }
  finally { b.disabled = false; }
});
const qp = new URLSearchParams(location.search);
const added = qp.get('added') || qp.get('renamed') || qp.get('trashed');
if (added && $('hm-added')) { ['added', 'renamed', 'trashed'].forEach(k => qp.delete(k)); history.replaceState(null, '', '/' + (qp.toString() ? '?' + qp : '')); msg($('hm-added').textContent, true); }

// ---------------------------------------------------------------- New Batch: two or more PDFs
const form = $('hm-batch');
if (form && $('hm-batch-n')) {
function picked() { return [...form.querySelectorAll('input[name=book]:checked')].length; }
form.addEventListener('change', () => {
  const n = picked();
  $('hm-batch-n').textContent = n < 2 ? 'Select two or more PDFs first.' + (n ? ' 1 selected.' : '') : n + ' PDFs selected.';
});
form.addEventListener('submit', e => {
  if (picked() < 2) { e.preventDefault(); msg('Select two or more PDFs for a batch: one PDF is a "New Run".'); }
});
}

// ---------------------------------------------------------------- Runs in Progress
const seen = {}; let primed = false;
const live = t => { const l = $('hm-live'); l.textContent = ''; setTimeout(() => { l.textContent = t; }, 50); };
function words(j) {
  if (j.status === 'queued') return 'Waiting to Start' + (j.waiting_for ? ': it starts when ' + j.waiting_for + ' ends' : j.position ? ' (' + j.position + ' in line)' : '');
  if (j.status === 'needs-spend') return 'The app restarted before the AI call started: open it to get a new estimate';
  if (j.kind === 'review' && !j.past_finish) return j.url ? 'Waiting for you: the review page is open' : 'Opening the review page';
  return 'Running' + (j.step ? ': ' + j.step.words + ' (' + j.step.n + ' of ' + j.step.total + ')' : '');
}
function href(j) { return j.kind === 'batch' || j.kind === 'batch-estimate' ? '/batch/' + encodeURIComponent(j.run.split('/')[1]) + '/' : '/run/' + enc(j.run) + '/'; }
async function poll() {
  try {
    const r = await fetch('/api/jobs?limit=200', { cache: 'no-store' }); const js = await r.json();
    const act = js.filter(j => j.status === 'queued' || j.status === 'running');
    js.forEach(j => {
      const k = j.status, was = seen[j.id]; seen[j.id] = k;
      if (primed && was && was !== k && !['queued', 'running'].includes(k))
        live((j.book_name || j.run) + ': ' + (j.action || j.kind) + ' ' + (k === 'done' ? 'finished' : k === 'failed' ? 'stopped with a problem' : 'stopped') + '.');
    });
    primed = true;
    const h = act.length ? '<ul class="hm-active">' + act.map((j, i) => '<li><span class="hm-run" id="hm-a' + i + '">' + esc(j.book_name || j.run) +
      (j.run_name && j.kind !== 'batch' ? ' <span class="pp-note">(' + esc(j.run_name) + ')</span>' : '') + '</span> ' + esc(j.action || j.kind) + ': ' + esc(words(j)) +
      ' <a class="pp-btn" href="' + esc(href(j)) + '" aria-describedby="hm-a' + i + '">Open</a></li>').join('') + '</ul>'
      : '';
    const box = $('hm-active'); if (box.dataset.h !== h) { box.innerHTML = h; box.dataset.h = h; }
    $('hm-act-sec').hidden = !act.length;
    setTimeout(poll, act.length ? 2000 : 5000);
  } catch (err) {
    $('hm-active').innerHTML = '<p class="pp-warn-t">The app is not running. ' + esc(START) + '</p>'; $('hm-act-sec').hidden = false;
    setTimeout(poll, 5000);
  }
}
poll();
})();
