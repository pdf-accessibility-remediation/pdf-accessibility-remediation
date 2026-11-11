/* webapp/trash.js: "Move to Trash" on the home page (a run, a batch, a PDF) and the batch page (the batch, or the PDFs
   selected in its dashboard) (#45 D8). Every move asks first, in a dialog that names what goes in plain words (from the
   app's own plan: /api/trash/plan); a move the app refuses says why and moves nothing. Focus returns to the button that
   opened the dialog; after a move the page is drawn again (the home page) or goes to the home page (a whole batch). */
(() => {
'use strict';
const $ = id => document.getElementById(id);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
let dlg = $('tr-dlg');
if (!dlg) { dlg = document.createElement('dialog'); dlg.id = 'tr-dlg'; dlg.className = 'pp-dlg'; dlg.setAttribute('aria-labelledby', 'tr-dlg-h'); document.body.appendChild(dlg); }
async function post(path, body) {
  const r = await fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  let d = {}; try { d = await r.json(); } catch (e) {}
  return [r.status, d];
}
function show(html, opener, onYes) {
  dlg.innerHTML = html;
  const close = () => { dlg.close(); if (opener && document.body.contains(opener)) opener.focus({ preventScroll: true }); };   // U6
  dlg.querySelectorAll('button').forEach(b => b.addEventListener('click', async () => {
    if (b.value !== 'yes') return close();
    b.disabled = true;
    const ok = await onYes();
    if (!ok) b.disabled = false;
  }));
  dlg.oncancel = e => { e.preventDefault(); close(); };
  dlg.showModal(); (dlg.querySelector('button[value=no]') || dlg.querySelector('button')).focus();
}
function body(p) {
  let h = '';
  if (p.what === 'run') h += '<p><b>' + esc(p.name) + '</b><br>' + esc(p.pdf) + (p.file ? '<br><span class="hm-file">Source PDF: ' + esc(p.file) + '</span>' : '') + '</p>';
  if (p.what === 'batch') h += '<p>' + (p.saved ? 'The batch <b>' + esc(p.name) + '</b>, saved with nothing started. Its PDFs:' :   // S7
    p.whole ? 'The whole batch <b>' + esc(p.name) + '</b> and every PDF in it:' : 'From the batch <b>' + esc(p.name) + '</b>:') + '</p><ul>' +
    p.pdfs.map(x => '<li>' + esc(x.pdf) + ' <span class="hm-file">Source PDF: ' + esc(x.file) + '</span></li>').join('') + '</ul>';
  if (p.what === 'pdf') {
    h += '<p><b>' + esc(p.pdf) + '</b><br><span class="hm-file">Source PDF: ' + esc(p.file) + '</span></p>';
    if (p.runs.length) h += '<p>These runs were made from:</p><ul>' + p.runs.map(r => '<li>' + esc(r.name) + ' · ' + esc(r.date) + ' · ' + esc(r.status) +
      (r.effect ? '<br><span' + (/still works|doesn't change that/.test(r.effect) ? ' class="pp-note"' : ' class="pp-warn-t"') + '>' + esc(r.effect) + '</span>' : '') + '</li>').join('') + '</ul>';
  }
  (p.words || []).forEach(w => { h += '<p' + (/shipped/.test(w) ? ' class="pp-warn-t"' : '') + '>' + esc(w) + '</p>'; });   // the warnings stand out
  return h + '<p class="pp-note tr-note">' + esc(goes(p)) + '</p>';
}
// What happens, in one sentence (#93, Patrick's test of the app): a PDF, or the folder of a run or a batch (several PDFs
// selected in a batch: their folders)
function goes(p) {
  const n = p.what === 'batch' && !p.whole && (p.pdfs || []).length > 1;
  return (p.what === 'pdf' ? 'This PDF will be' : n ? 'These folders will be' : 'This folder will be') +
         ' moved to the Trash on this computer and cannot be restored through the app.';
}
// The name the home page's message gives after the move ("Moved to the Trash: <name>.")
function named(p) { return p.what === 'pdf' ? p.pdf : p.name; }
async function ask(req, opener, after) {
  let c, p;
  try { [c, p] = await post('/api/trash/plan', req); }
  catch (e) { return show('<h2 id="tr-dlg-h">Move to the Trash</h2><p class="pp-warn-t">The app is not running, so nothing can be moved.</p><div><button type="button" value="no">Close</button></div>', opener); }
  const title = req.what === 'pdf' ? 'Move This PDF to the Trash?' : req.what === 'run' ? 'Move This Run to the Trash?' :
                p.whole ? 'Move This Batch to the Trash?' : 'Move the Selected PDFs to the Trash?';
  if (c !== 200) return show('<h2 id="tr-dlg-h">' + title + '</h2><p class="pp-warn-t">' + esc(p.error || 'The app refused this.') + '</p><div><button type="button" value="no">Close</button></div>', opener);
  if (p.refused) return show('<h2 id="tr-dlg-h">' + title + '</h2>' + body(Object.assign({}, p, { words: [] })).replace(/<p class="pp-note tr-note">.*$/, '') +
    '<p class="pp-warn-t">This can\'t be moved now. ' + esc(p.refused) + '</p><div><button type="button" value="no">Close</button></div>', opener);
  show('<h2 id="tr-dlg-h">' + title + '</h2>' + body(p) + '<div id="tr-msg" class="pp-msg" hidden></div><div><button type="button" class="pp-primary" value="yes">Move to Trash</button>' +
       '<button type="button" value="no">Cancel</button></div>', opener, async () => {
    const [c2, r] = await post('/api/trash/move', req);
    if (c2 !== 200) { const m = $('tr-msg'); m.hidden = false; m.textContent = r.error || 'The app refused this: nothing was moved.'; return false; }
    dlg.close(); after(p, r); return true;
  });
}
document.addEventListener('click', e => {
  let b = e.target.closest('button[data-trash]'); if (!b) return;
  const m = b.closest('.hm-menu'), item = b; if (m) b = m.querySelector('.hm-more');   // from a "⋯" menu: focus returns to "⋯" (Q4)
  const what = item.dataset.trash, d = item.dataset;
  if (what === 'selected') {                                       // the batch page: the PDFs ticked in its dashboard
    const names = [...document.querySelectorAll('input[name=trash-pdf]:checked')].map(x => x.value);
    if (!names.length) { show('<h2 id="tr-dlg-h">Move the Selected PDFs to the Trash?</h2><p>Select one or more PDFs in the dashboard first.</p><div><button type="button" value="no">Close</button></div>', b); return; }
    return ask({ what: 'batch', label: d.label, names }, b, (p, r) => { if (r.whole) location.assign('/?view=batches&trashed=1'); else location.reload(); });
  }
  const req = what === 'run' ? { what, run: d.run } : what === 'batch' ? { what, label: d.label } : { what, key: d.key };
  ask(req, b, p => {
    const t = 'trashed=' + encodeURIComponent(named(p) || '1');     // the home page names what was moved
    if (what === 'batch' && !document.body.dataset.home) location.assign('/?view=batches&' + t);
    else location.assign(location.pathname + location.search.replace(/([?&])trashed=[^&]*&?/, '$1') + (location.search ? '&' : '?') + t);
  });
});
})();
