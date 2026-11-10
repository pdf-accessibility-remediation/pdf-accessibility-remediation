/* webapp/home.js: the home page's own script (#45, home interface): "Upload a PDF" (the drop zone: each chosen or dropped PDF
   is sent to the app as it is; the files on the person's computer are only read), the "⋯" menus and Edit Name in place,
   Create a New Batch's selection, and the live "Runs in Progress" list (shown only while something runs or waits to start).

   Accessibility: every action is a real button or link ("Choose PDFs" is the keyboard path to the drop zone); a "⋯" is a
   menu button (arrow keys, Home, End, Esc returns focus to it, Tab closes it); messages go to a message box that takes
   focus after the person's own action, except after an upload where the first new name box takes it; the list of runs in
   progress is redrawn quietly and only a job that ends is announced (one polite live region). */
(() => {
'use strict';
const $ = id => document.getElementById(id);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const enc = run => run.split('/').map(encodeURIComponent).join('/');
const START = 'To start the app again, open a terminal in the project\'s pipeline folder and type python3 app.py.';
function msg(text, ok, focus = true) {
  const m = $('hm-msg'); m.hidden = !text; m.classList.toggle('pp-okmsg', !!ok);
  m.innerHTML = text ? '<span class="pp-msg-t">' + esc(text) + '</span><button type="button" class="pp-x" aria-label="Dismiss message"><span aria-hidden="true">×</span></button>' : '';
  if (text && focus) m.focus();
}
const live = t => { const l = $('hm-live'); if (!l) return; l.textContent = ''; setTimeout(() => { l.textContent = t; }, 50); };
$('hm-msg').addEventListener('click', e => { if (e.target.closest('button.pp-x')) { msg(''); ($('hm-choose') || document.querySelector('form [name]')).focus(); } });

const edit = (...a) => window.Pdfrem.edit(...a), closeMenu = (...a) => window.Pdfrem.closeMenu(...a);   // webapp/shared.js
if (!$('hm-active')) return;                                      // the New Run and New Batch pages stop here

// ---------------------------------------------------------------- Upload a PDF: the drop zone (Q1, Patrick's test 2026-11-07)
// Several PDFs at once, chosen ("Choose PDFs", the keyboard path) or dropped. Each is sent on its own, one after the other,
// with the server's checks (a PDF, the size limit, the same content already listed, the space left); a file that fails gets
// its own plain sentence. Then the page is drawn again with the new PDFs first, highlighted, their name boxes open.
const drop = $('hm-drop'), pick = $('hm-file');
function isPdf(f) { return /\.pdf$/i.test(f.name) || f.type === 'application/pdf'; }
async function upload(files) {
  files = [...files]; if (!files.length) return;
  const ok = [], bad = [], notes = [];
  $('hm-choose').disabled = true;
  for (let i = 0; i < files.length; i++) {
    const f = files[i];
    if (!isPdf(f)) { bad.push('"' + f.name + '": this file isn\'t a PDF.'); continue; }
    msg('Adding ' + (files.length > 1 ? (i + 1) + ' of ' + files.length + ': ' : '') + '"' + f.name + '"…', true, false);
    try {
      const r = await fetch('/api/upload', { method: 'POST', body: f,
        headers: { 'Content-Type': 'application/pdf', 'X-Pdfrem-Upload': '1', 'X-Pdfrem-Filename': encodeURIComponent(f.name) } });
      let d = {}; try { d = await r.json(); } catch (err) {}
      if (r.status === 201) {
        ok.push(d.book.key);
        if (d.book.locked) notes.push('"' + f.name + '" was added, but it is locked with a password: add an unlocked copy.');
        else if (d.book.unreadable) notes.push('"' + f.name + '" was added, but it couldn\'t be read.');
      } else bad.push('"' + f.name + '": ' + (d.error || 'it was not added.'));
    } catch (err) { bad.push('"' + f.name + '": the app is not running. ' + START); break; }
  }
  $('hm-choose').disabled = false; pick.value = '';
  const lines = bad.concat(notes);
  if (!ok.length) { msg(lines.join(' ') || 'Nothing was added.', false, true); return; }
  const to = '/?added=' + ok.join(',');
  if (lines.length) {
    try { sessionStorage.setItem('hm-upload-notes', JSON.stringify(lines)); }
    catch (err) {                                                  // no storage here: say it now, and offer the list
      msg((ok.length === 1 ? '1 PDF was added. ' : ok.length + ' PDFs were added. ') + lines.join(' '), false, true);
      $('hm-msg').insertAdjacentHTML('beforeend', ' <a class="pp-btn" href="' + esc(to) + '">Show the Added PDFs</a>'); return;
    }
  }
  location.assign(to);
}
if (drop) {
  $('hm-choose').addEventListener('click', () => pick.click());
  pick.addEventListener('change', () => upload(pick.files));
  // a PDF dropped anywhere on the page never opens in this tab (the page would be lost); only the zone takes it
  ['dragover', 'drop'].forEach(k => addEventListener(k, e => { if (e.dataTransfer && [...e.dataTransfer.types].includes('Files')) e.preventDefault(); }));
  drop.addEventListener('dragenter', e => { e.preventDefault(); drop.classList.add('hm-over'); });
  drop.addEventListener('dragover', e => { e.preventDefault(); drop.classList.add('hm-over'); });
  drop.addEventListener('dragleave', e => { if (!drop.contains(e.relatedTarget)) drop.classList.remove('hm-over'); });
  drop.addEventListener('drop', e => { e.preventDefault(); drop.classList.remove('hm-over'); upload(e.dataTransfer.files); });
}
const qp = new URLSearchParams(location.search);
if (qp.get('open')) {                                             // T4: a saved batch's page opens its pop-up here
  const lab = qp.get('open'); qp.delete('open'); history.replaceState(null, '', '/' + (qp.toString() ? '?' + qp : ''));
  window.Pdfrem.openDialog('/api/form?what=batch&saved=' + encodeURIComponent(lab), null);
}
const added = qp.get('added') || qp.get('renamed') || qp.get('trashed');
if (added && $('hm-added')) {
  ['added', 'renamed', 'trashed'].forEach(k => qp.delete(k)); history.replaceState(null, '', '/' + (qp.toString() ? '?' + qp : ''));
  let notes = []; try { notes = JSON.parse(sessionStorage.getItem('hm-upload-notes') || '[]'); sessionStorage.removeItem('hm-upload-notes'); } catch (err) {}
  const fresh = [...document.querySelectorAll('tr[data-new]')];
  msg($('hm-added').textContent + (notes.length ? ' ' + notes.join(' ') : ''), !notes.length, !fresh.length || !!notes.length);
  fresh.forEach((tr, i) => edit(tr.querySelector('[data-edit]'), !notes.length && i === 0));   // the name boxes open; the first takes focus
}


// ---------------------------------------------------------------- New Batch: two or more PDFs
const form = $('hm-batch');
if (form && $('hm-batch-n')) {
function picked() { return [...form.querySelectorAll('input[name=book]:checked')].length; }
form.addEventListener('change', () => {
  const n = picked();
  $('hm-batch-n').textContent = n < 2 ? 'Select two or more PDFs first.' + (n ? ' 1 selected.' : '') : n + ' PDFs selected.';
});
form.addEventListener('submit', e => {                            // T4: New Batch is a pop-up on this page
  e.preventDefault();
  if (picked() < 2) { msg('Select two or more PDFs for a batch: one PDF is a "New Run".'); return; }
  const p = new URLSearchParams([['what', 'batch'], ...[...form.querySelectorAll('input[name=book]:checked')].map(x => ['book', x.value])]);
  window.Pdfrem.openDialog('/api/form?' + p, $('hm-batch-b'));
});
}

// ---------------------------------------------------------------- My Workspace in place (R15, Patrick's test 2026-11-07)
// The switch, the filter, the search and "Show More" fetch the same page from the app and swap only My Workspace's
// contents: no reload, no jump to the top. The address keeps them (history.replaceState), so refreshing keeps them too.
// Focus stays on the control the person used (found again in the new contents); the new count is announced.
const ws = document.querySelector('.hm-c-ws');
async function swap(url, focusSel) {
  try {
    const r = await fetch(url, { cache: 'no-store' }); if (!r.ok) throw new Error(String(r.status));
    const doc = new DOMParser().parseFromString(await r.text(), 'text/html'), nw = doc.querySelector('.hm-c-ws');
    if (!nw) throw new Error('no workspace');
    closeMenu(false);
    ws.innerHTML = nw.innerHTML; history.replaceState(null, '', url);
    const f = focusSel && ws.querySelector(focusSel); if (f) f.focus();
    const note = ws.querySelector(':scope > p.pp-note'); live(note ? note.textContent : '');
  } catch (err) { location.assign(url); }                      // the app answers otherwise: the plain page
}
if (ws) {
  ws.addEventListener('submit', e => {
    const f = e.target; if (!f.matches('form.hm-ws')) return;
    e.preventDefault();
    // Enter in the search box submits with the form's first button ("Single Runs"): only a switch button the person
    // pressed changes the view; the search keeps the one shown
    const sw = e.submitter && e.submitter.closest('.hm-switch') && document.activeElement !== $('hm-q');
    const cur = (f.querySelector('.hm-switch button[aria-pressed="true"]') || {}).value || 'runs';
    const fd = new FormData(f), p = new URLSearchParams();
    const view = sw ? e.submitter.value : cur, q = (fd.get('q') || '').trim(), group = fd.get('group') || '';
    if (view !== 'runs') p.set('view', view);
    if (q) p.set('q', q);
    if (group) p.set('group', group);
    swap('/' + (p.toString() ? '?' + p : ''), sw ? '.hm-switch button[value="' + view + '"]' : '#hm-q');
  });
  ws.addEventListener('click', e => {
    const a = e.target.closest('.hm-filter a, a#hm-more'); if (!a || e.ctrlKey || e.metaKey || e.shiftKey || e.button) return;
    e.preventDefault();
    const href = a.getAttribute('href');
    swap(href, a.id === 'hm-more' ? '#hm-more, .hm-c-ws .pp-tw' : '.hm-filter a[href="' + CSS.escape(href) + '"]');
  });
}

// ---------------------------------------------------------------- Runs in Progress
const seen = {}; let primed = false;
// #93: the app is asked only about jobs whose status can still change, and about the ones last seen in one of these
// statuses (review 02 H1: a dismissed paid job, an interrupted job that finishes), so an end is announced as before
const CAN_CHANGE = ['queued', 'running', 'needs-spend', 'interrupted'];
function words(j) {
  if (j.status === 'queued') return 'Waiting to Start' + (j.waiting_for ? ': it starts when ' + j.waiting_for + ' ends' : j.position ? ' (' + j.position + ' in line)' : '');
  if (j.status === 'needs-spend') return 'The app restarted before the AI request started: open it to get a new estimate';
  if (j.kind === 'review' && !j.past_finish) return j.url ? 'Waiting for you: the review page is open' : 'Opening the review page';
  return 'Running' + (j.step ? ': ' + j.step.words.charAt(0).toUpperCase() + j.step.words.slice(1) + ' (' + j.step.n + ' of ' + j.step.total + ')' : '');
}
function href(j) { return j.kind === 'batch' || j.kind === 'batch-estimate' ? '/batch/' + encodeURIComponent(j.run.split('/')[1]) + '/' : '/run/' + enc(j.run) + '/'; }
async function poll() {
  try {
    const ids = Object.keys(seen).filter(i => CAN_CHANGE.includes(seen[i])).slice(-500);
    const r = await fetch('/api/jobs?active=1&seen=' + ids.map(encodeURIComponent).join(','), { cache: 'no-store' }); const js = await r.json();
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
