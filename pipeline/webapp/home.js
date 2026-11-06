/* webapp/home.js: the home page's own script (#45, home interface): "Add a Book" (the chosen PDF is sent to the app as it is;
   the file on the person's computer is only read), New Batch's selection, and the live "Runs in Progress" list.

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

// ---------------------------------------------------------------- Add a Book
if ($('hm-add')) $('hm-add').addEventListener('submit', async e => {
  e.preventDefault();
  const f = $('hm-file').files[0];
  if (!f) { msg('Choose a PDF first: "Add a Book" opens your files.'); return; }
  const b = $('hm-add-b'); b.disabled = true; msg('Adding "' + f.name + '"…', true);
  try {
    const r = await fetch('/api/upload', { method: 'POST', body: f,
      headers: { 'Content-Type': 'application/pdf', 'X-Pdfrem-Upload': '1', 'X-Pdfrem-Filename': encodeURIComponent(f.name) } });
    let d = {}; try { d = await r.json(); } catch (err) {}
    if (r.status === 201) { location.assign('/?added=' + encodeURIComponent(d.book.key) + '#hm-msg'); return; }
    msg(d.error || 'The book was not added.');
  } catch (err) { msg('The app is not running. ' + START); }
  finally { b.disabled = false; }
});
const added = new URLSearchParams(location.search).get('added');
if (added && $('hm-added')) { history.replaceState(null, '', '/'); msg($('hm-added').textContent, true); }

// ---------------------------------------------------------------- New Batch: two or more books
const form = $('hm-batch');
function picked() { return [...form.querySelectorAll('input[name=book]:checked')].length; }
form.addEventListener('change', () => {
  const n = picked();
  $('hm-batch-n').textContent = n < 2 ? 'Select two or more books first.' + (n ? ' 1 selected.' : '') : n + ' books selected.';
});
form.addEventListener('submit', e => {
  if (picked() < 2) { e.preventDefault(); msg('Select two or more books for a batch: one book is a "New Run".'); }
});

// ---------------------------------------------------------------- Runs in Progress
const seen = {}; let primed = false;
const live = t => { const l = $('hm-live'); l.textContent = ''; setTimeout(() => { l.textContent = t; }, 50); };
function words(j) {
  if (j.status === 'queued') return 'Waiting to start' + (j.position ? ' (' + j.position + ' in line)' : '');
  if (j.status === 'needs-spend') return 'The app restarted before the AI call started: open it to get a new estimate';
  if (j.kind === 'review' && !j.past_finish) return j.url ? 'Waiting for you: the review page is open' : 'Opening the review page';
  return 'Running' + (j.step ? ': ' + j.step.words + ' (' + j.step.n + ' of ' + j.step.total + ')' : '');
}
function href(j) { return j.kind === 'batch' || j.kind === 'batch-estimate' ? '/batch/' + encodeURIComponent(j.run.split('/')[1]) + '/' : '/run/' + enc(j.run) + '/'; }
async function poll() {
  try {
    const r = await fetch('/api/jobs?limit=200', { cache: 'no-store' }); const js = await r.json();
    const act = js.filter(j => j.status === 'queued' || j.status === 'running' || j.status === 'needs-spend');
    js.forEach(j => {
      const k = j.status, was = seen[j.id]; seen[j.id] = k;
      if (primed && was && was !== k && !['queued', 'running'].includes(k))
        live((j.book_name || j.run) + ': ' + (j.action || j.kind) + ' ' + (k === 'done' ? 'finished' : k === 'failed' ? 'stopped with a problem' : 'stopped') + '.');
    });
    primed = true;
    const h = act.length ? '<ul class="hm-active">' + act.map(j => '<li><a href="' + esc(href(j)) + '">' + esc(j.book_name || j.run) + '</a>' +
      (j.run_name ? ' <span class="pp-note">(' + esc(j.run_name) + ')</span>' : '') + ' · ' + esc(j.action || j.kind) + ': ' + esc(words(j)) + '</li>').join('') + '</ul>'
      : '<p>Nothing is running.</p>';
    const box = $('hm-active'); if (box.dataset.h !== h) { box.innerHTML = h; box.dataset.h = h; }
    setTimeout(poll, act.length ? 2000 : 5000);
  } catch (err) {
    $('hm-active').innerHTML = '<p class="pp-warn-t">The app is not running. ' + esc(START) + '</p>';
    setTimeout(poll, 5000);
  }
}
poll();
})();
