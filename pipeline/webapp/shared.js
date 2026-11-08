/* webapp/shared.js: what the home page and the batch page share (#45, home interface): the "⋯" menus, Edit Name in place,
   and the pop-ups for New Run and New Batch (T4, Patrick 2026-11-07). Loaded before home.js and batch.js; they reach it
   through window.Pdfrem.

   The pop-ups: a native <dialog> opened with showModal() (the page behind is inert, so Tab stays inside), named by its
   heading, focus on its first field; Esc and "Cancel" close it, change nothing and give focus back to the button that
   opened it (for a "⋯" menu's item, that "⋯"). Its contents come from the app (GET /api/form), so the fields are the
   app's own; a refusal is shown inside it, under the name field when it is about the name. "Get the Estimate(s)" starts
   only the free estimate, as before: the paid step stays "Start Remediation" on the run or batch page. */
(() => {
'use strict';
const $ = id => document.getElementById(id);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const START = 'To start the app again, open a terminal in the project\'s pipeline folder and type python3 app.py.';
const live = t => { const l = $('hm-live') || $('pp-live'); if (!l) return; l.textContent = ''; setTimeout(() => { l.textContent = t; }, 50); };

// ---------------------------------------------------------------- the "⋯" menus (Q4): a real menu button
let openMenu = null;
function closeMenu(focusBack) {
  if (!openMenu) return;
  const b = openMenu.previousElementSibling, m = openMenu; openMenu = null;
  m.hidden = true; b.setAttribute('aria-expanded', 'false');
  if (focusBack) b.focus();
}
function showMenu(b, first) {
  closeMenu(false);
  const m = b.nextElementSibling; m.hidden = false; b.setAttribute('aria-expanded', 'true'); openMenu = m;
  place(b, m);
  const items = [...m.querySelectorAll('[role=menuitem]')];
  (first ? items[0] : items[items.length - 1]).focus();
}
function place(b, m) {                                              // against the window: the table's scroll box never clips it
  const r = b.getBoundingClientRect(), h = m.offsetHeight;
  m.style.right = Math.max(4, innerWidth - r.right) + 'px';
  m.style.top = (r.bottom + 4 + h > innerHeight && r.top - 4 - h > 0 ? r.top - 4 - h : r.bottom + 4) + 'px';
}
addEventListener('resize', () => closeMenu(false));
addEventListener('scroll', () => { if (openMenu) place(openMenu.previousElementSibling, openMenu); }, true);
document.addEventListener('click', e => {
  const b = e.target.closest('.hm-more');
  if (b) { if (b.getAttribute('aria-expanded') === 'true') closeMenu(true); else showMenu(b, true); return; }
  const it = e.target.closest('[role=menuitem]');
  if (it && openMenu && openMenu.contains(it)) {                    // the menu closes first: the dialog or the name box returns focus to "⋯"
    const more = openMenu.previousElementSibling; closeMenu(false);
    if (it.dataset.edit) edit(it, true, more);
    else if (it.dataset.dialog) openDialog(it.dataset.dialog, more);   // "New Run of This PDF" (R17): a pop-up (T4)
    return;                                                         // Move to Trash: trash.js, with "⋯" as the opener
  }
  if (openMenu && !openMenu.contains(e.target)) closeMenu(false);
}, true);
document.addEventListener('keydown', e => {
  const b = e.target.closest && e.target.closest('.hm-more');
  if (b && (e.key === 'ArrowDown' || e.key === 'ArrowUp')) { e.preventDefault(); showMenu(b, e.key === 'ArrowDown'); return; }
  if (!openMenu || !openMenu.contains(e.target)) return;
  const items = [...openMenu.querySelectorAll('[role=menuitem]')], i = items.indexOf(e.target);
  if (e.key === 'ArrowDown') { e.preventDefault(); items[(i + 1) % items.length].focus(); }
  else if (e.key === 'ArrowUp') { e.preventDefault(); items[(i - 1 + items.length) % items.length].focus(); }
  else if (e.key === 'Home') { e.preventDefault(); items[0].focus(); }
  else if (e.key === 'End') { e.preventDefault(); items[items.length - 1].focus(); }
  else if (e.key === 'Escape') { e.preventDefault(); closeMenu(true); }
  else if (e.key === 'Tab') closeMenu(false);
});

// ---------------------------------------------------------------- Edit Name, in place (Q3, Q4)
// The row's name becomes a text box: Enter or "Save Name" saves it, Esc or "Cancel" puts the name back. Only the name the
// pages show changes: never a file or a folder. Focus goes back to the row's "⋯" button.
const SAY = { pdf: ['PDF Name', '/api/book/name', d => ({ key: d.key })], run: ['Run Name', '/api/rename/run', d => ({ run: d.run })],
              batch: ['Batch Name', '/api/rename/batch', d => ({ label: d.label })],
              batchpdf: ['PDF Name', '/api/rename/batch-pdf', d => ({ label: d.label, book: d.book })] };   // T2: by sha256
let nEdit = 0;
function edit(item, focus, more) {
  if (!item) return;
  const tr = item.closest('tr'), kind = item.dataset.edit, el = tr.querySelector(kind === 'pdf' || kind === 'batchpdf' ? '.hm-book' : '.hm-run');
  more = more || tr.querySelector('.hm-more');
  if (!el || tr.querySelector('.hm-rename')) { const x = tr.querySelector('.hm-rename input'); if (x && focus) x.focus(); return; }
  const id = 'hm-ed' + (++nEdit), old = el.textContent;
  const box = document.createElement('div'); box.className = 'hm-rename';
  box.innerHTML = '<label class="pp-sr" for="' + id + '">' + SAY[kind][0] + '</label><input type="text" id="' + id + '" maxlength="120" required value="' + esc(old) +
    '" aria-describedby="' + id + '-e"> <button type="button" class="pp-primary" data-save>Save Name</button> <button type="button" data-cancel>Cancel</button>' +
    '<span class="pp-warn-t" id="' + id + '-e" hidden></span>';
  el.hidden = true; el.after(box);
  const input = box.querySelector('input'), err = box.querySelector('.pp-warn-t');
  const done = (name) => {
    if (name) el.textContent = name;
    box.remove(); el.hidden = false; tr.classList.remove('hm-new'); delete tr.dataset.new;
    if (more) { more.setAttribute('aria-label', 'More Actions for ' + el.textContent); more.nextElementSibling.setAttribute('aria-label', 'More Actions for ' + el.textContent); more.focus(); }
    if (name) live('Saved: the name is now ' + name + '.');
  };
  async function save() {
    const v = input.value.trim();
    if (!v) { err.hidden = false; err.textContent = 'Type a name first.'; input.setAttribute('aria-invalid', 'true'); input.focus(); return; }
    if (v === old) return done(null);
    box.querySelector('[data-save]').disabled = true;
    try {
      const r = await fetch(SAY[kind][1], { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(Object.assign({ name: v }, SAY[kind][2](item.dataset))) });
      let d = {}; try { d = await r.json(); } catch (x) {}
      if (r.ok) return done(d.name || v);
      err.hidden = false; err.textContent = d.error || 'The name was not saved.';
    } catch (x) { err.hidden = false; err.textContent = 'The app is not running. ' + START; }
    box.querySelector('[data-save]').disabled = false; input.setAttribute('aria-invalid', 'true'); input.focus();
  }
  box.addEventListener('keydown', e => {
    if (e.key === 'Enter' && e.target === input) { e.preventDefault(); save(); }     // never the batch form around the list
    else if (e.key === 'Escape') { e.preventDefault(); done(null); }
  });
  box.querySelector('[data-save]').addEventListener('click', save);
  box.querySelector('[data-cancel]').addEventListener('click', () => done(null));
  if (focus) { input.focus(); input.select(); }
}

// ---------------------------------------------------------------- the pop-ups: New Run and New Batch (T4)
let dlg = null, opener = null, dlgUrl = null;
function closeDialog() {
  if (!dlg || !dlg.open) return;
  dlg.close();
  let o = opener; opener = null;
  if (o && !document.body.contains(o) && o.id) o = $(o.id);       // the page drew that button again meanwhile: the new one
  if (o && document.body.contains(o) && !o.closest('[hidden]')) o.focus();
}
function fieldError(f, text) {                                   // a refusal under its field, else in the pop-up's message box
  const nameIn = f.querySelector('[data-field=name]'), ne = nameIn && $(nameIn.getAttribute('aria-describedby'));
  const box = f.querySelector('.dlg-msg');
  f.querySelectorAll('.pp-field-e').forEach(x => { x.hidden = true; x.textContent = ''; });
  if (nameIn) nameIn.removeAttribute('aria-invalid');
  if (box) { box.hidden = true; box.textContent = ''; }
  if (!text) return;
  if (nameIn && ne && /name/i.test(text)) { ne.hidden = false; ne.textContent = text; nameIn.setAttribute('aria-invalid', 'true'); nameIn.focus(); return; }
  if (box) { box.hidden = false; box.textContent = text; box.focus(); }
}
async function fill(url) {
  const r = await fetch(url, { cache: 'no-store' });
  let d = {}; try { d = await r.json(); } catch (e) {}
  if (!r.ok || !d.html) throw new Error(d.error || 'The app refused this.');
  dlg.innerHTML = d.html;
  const f = dlg.querySelector('[data-field=name]') || dlg.querySelector('button, input');
  if (f) { f.focus(); if (f.select) f.select(); }
}
async function openDialog(url, from) {
  if (!dlg) {
    dlg = document.createElement('dialog'); dlg.className = 'pp-dlg pp-form-dlg'; dlg.id = 'pp-form-dlg'; dlg.setAttribute('aria-labelledby', 'dlg-h');
    document.body.appendChild(dlg);
    dlg.addEventListener('cancel', e => { e.preventDefault(); closeDialog(); });   // Esc: closed, nothing changed
    dlg.addEventListener('click', e => { if (e.target.closest('[data-cancel]')) closeDialog(); });
    dlg.addEventListener('submit', submit);
    dlg.addEventListener('click', remove);
  }
  opener = from || document.activeElement; dlgUrl = url;
  dlg.innerHTML = '<h2 id="dlg-h">Loading…</h2>';
  if (!dlg.open) dlg.showModal();
  try { await fill(url); }
  catch (err) {
    dlg.innerHTML = '<h2 id="dlg-h">Not Available</h2><p class="pp-warn-t">' + esc(err.message === 'Failed to fetch' ? 'The app is not running. ' + START : err.message) +
      '</p><div class="pp-row"><button type="button" data-cancel>Close</button></div>';
    dlg.querySelector('[data-cancel]').focus();
  }
}
async function submit(e) {
  const f = e.target; if (!f.matches('form[data-api]')) return;
  e.preventDefault();
  const body = {};
  f.querySelectorAll('[name]').forEach(x => {
    if (x.name === 'books') (body.books = body.books || []).push(x.value);   // a list
    else body[x.name] = x.value;
  });
  const nameIn = f.querySelector('[data-field=name]');
  if (nameIn && !nameIn.value.trim()) return fieldError(f, nameIn.id === 'nb-name' ? 'Enter a name for the batch.' : 'Enter a name for the run.');
  const b = e.submitter || f.querySelector('button[type=submit]'); b.disabled = true;
  try {
    const api = (e.submitter && e.submitter.dataset.api) || f.dataset.api;   // "Save Batch for Later" posts elsewhere (S7)
    const r = await fetch(api, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    let d = {}; try { d = await r.json(); } catch (err) {}
    if (r.status === 202 && d.location) { fieldError(f, ''); location.assign(d.location); return; }
    fieldError(f, d.error || 'The app refused this.');
  } catch (err) { fieldError(f, 'The app is not running. ' + START); }
  finally { b.disabled = false; }
}
async function remove(e) {                                        // S7: "Remove from Batch" in a saved batch's pop-up
  const b = e.target.closest('button[data-remove]'); if (!b) return;
  b.disabled = true;
  try {
    const r = await fetch('/api/batch/' + encodeURIComponent(b.dataset.label) + '/remove', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ book: b.dataset.remove }) });
    let d = {}; try { d = await r.json(); } catch (err) {}
    if (r.ok) { const keep = dlg.querySelector('[data-field=name]'), v = keep && keep.value; await fill(dlgUrl);
                const n = dlg.querySelector('[data-field=name]'); if (n && v) n.value = v; live('Removed from the batch: it is back in the upload list.'); return; }
    fieldError(dlg.querySelector('form'), d.error || 'The app refused this.');
  } catch (err) { fieldError(dlg.querySelector('form'), 'The app is not running. ' + START); }
  b.disabled = false;
}
document.addEventListener('click', e => {                         // a button that opens a pop-up ("New Run", a saved batch's "Open")
  const b = e.target.closest('button[data-dialog]'); if (!b || b.getAttribute('role') === 'menuitem') return;
  openDialog(b.dataset.dialog, b);
});

window.Pdfrem = { edit, closeMenu, openDialog, live };
})();
