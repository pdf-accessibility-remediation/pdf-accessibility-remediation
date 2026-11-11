/* webapp/batch.js: the batch page and the side column of every book page in a batch (#45, home interface).

   The side column ("PDFs in This Batch"): each PDF with its status in words and its state in its left border (P15: never by
   colour alone), the current one marked aria-current="page" (darker background, bold); a real button beside "Home Page"
   hides and shows the list (aria-expanded), remembered in this browser only (a convenience); on a narrow screen (below
   48em, 320 px included) the list starts closed, in the page's flow, so nothing scrolls sideways. "Skip to the content"
   skips it. The statuses are kept current from /api/batch/<label>.

   The batch page: the estimate of every book added up, the batch limit and the credit, "Start Remediation" (with the
   expected and the max estimated cost beside it), the total cost, the batch dashboard drawn in the page (P8: report_html's own rows), and
   "Run the Unfinished PDFs Again". Focus moves only after the person's own action. */
(() => {
'use strict';
const $ = id => document.getElementById(id);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const usd = x => '$' + Number(x || 0).toFixed(2);
const START = 'To start the app again, open a terminal in the project\'s pipeline folder and type python3 app.py.';
const nav = $('pp-bnav'); if (!nav) return;
const LABEL = nav.dataset.label, API = '/api/batch/' + encodeURIComponent(LABEL);
const narrow = matchMedia('(max-width: 48em)');
const KEY = 'batchnav:closed';
function closed() {                                             // the server laid it out from the cookie (D7); else the narrow default
  if (document.body.classList.contains('bn-closed')) return true;
  if (document.body.classList.contains('bn-open')) return false;
  try { const v = localStorage.getItem(KEY); return v === null ? narrow.matches : v === '1'; } catch (e) { return narrow.matches; }
}
function setOpen(open, remember) {
  const t = $('bn-toggle'), n = nav.querySelectorAll('#bn-list li').length; if (!t) return;
  nav.classList.toggle('closed', !open); document.body.classList.toggle('bn-closed', !open);
  t.setAttribute('aria-expanded', String(open)); t.textContent = open ? 'Hide the PDF List' : 'Show the PDF List (' + n + ')';
  if (remember) {
    try { localStorage.setItem(KEY, open ? '0' : '1'); } catch (e) {}
    document.cookie = 'pdfrem_bn=' + (open ? 'open' : 'closed') + '; path=/; max-age=31536000; SameSite=Strict';   // the server lays out the next page (D7)
  }
  document.body.classList.remove('bn-auto'); document.body.classList.toggle('bn-open', open);
}
const SCROLL = 'batchnav:scroll';                                // the side list keeps its place from page to page (D7)
try { const y = sessionStorage.getItem(SCROLL); if (y !== null) nav.scrollTop = +y; } catch (e) {}
addEventListener('pagehide', () => { try { sessionStorage.setItem(SCROLL, String(nav.scrollTop)); } catch (e) {} });
document.body.classList.add('bn-on');
setOpen(!closed(), false);
if ($('bn-toggle')) $('bn-toggle').addEventListener('click', () => setOpen(nav.classList.contains('closed'), true));

let st = null, primed = false; const seen = {};
const live = t => { const l = $('pp-live'); if (!l) return; l.textContent = ''; setTimeout(() => { l.textContent = t; }, 50); };
function msg(text, ok, focus) {
  const m = $('pp-msg'); if (!m) return; m.hidden = !text; m.classList.toggle('pp-okmsg', !!ok);
  m.innerHTML = text ? '<span class="pp-msg-t">' + esc(text) + '</span><button type="button" class="pp-x" data-act="dismiss" aria-label="Dismiss message"><span aria-hidden="true">×</span></button>' : '';
  if (text && focus) m.focus();
}
function column(s) {                                             // the statuses in the side column
  s.books.forEach(b => {
    const a = nav.querySelector('a[data-book="' + CSS.escape(b.name) + '"]'); if (!a) return;
    const x = a.querySelector('.bn-st'); if (x.textContent !== b.status) x.textContent = b.status;
    const nm = a.querySelector('.bn-name'); if (nm && b.book && nm.textContent !== b.book) nm.textContent = b.book;   // T2: a PDF renamed
    const c = 'bn-t-' + (b.tone || 'new');
    if (!a.classList.contains(c)) { a.className = c; }
    const sp = a.querySelector('.bn-spin');
    if (b.tone === 'processing' && !sp) a.insertAdjacentHTML('beforeend', '<span class="bn-spin" role="img" aria-label="Processing"></span>');
    else if (b.tone !== 'processing' && sp) sp.remove();
  });
}
const PHASE = { language: 'Waiting for a Language', estimating: 'Estimating', ready: 'Ready to Start', running: 'Running', finished: 'Finished', stopped: 'Stopped', review: 'Waiting for Review', missing: 'Stopped: an Estimate Is Missing', 'needs-spend': 'Waiting for a New Estimate' };
function body(s) {
  const T = s.totals, n = s.books.length;
  let h = '<h3 id="bt-phase" tabindex="-1">' + esc(PHASE[s.phase] || s.phase) + '</h3>';
  if (s.test) h += '<p class="pp pp-bar">Test: saved replies, no AI request.</p>';
  h += '<p>' + T.finished + ' of ' + n + ' PDFs finished' + (s.ocr_name ? ' · OCR Language: ' + esc(s.ocr_name) : '') + '</p>';
  const plural = k => k === 1 ? '' : 's';
  const x = T.expected;                                          // no key on any estimate (made before #65): no line
  const exp = !x ? '' : x.usd == null ? 'Expected Cost: Not Available Yet' :
    'Expected Cost: ' + usd(x.usd) + ' for ' + (x.books === x.of ? '' : x.books + ' of ') + x.of + ' PDF' + plural(x.of) + (x.books === x.of ? '' : ' (Not Available Yet for ' + (x.of - x.books) + ' PDF' + plural(x.of - x.books) + ')');
  const before = s.phase === 'ready' || s.phase === 'missing';
  if (s.phase === 'estimating' || s.phase === 'language') {      // R14: never "$0.00" while the estimates come in
    if (T.estimated) h += '<p id="bt-cost"><b>Max Estimated Cost So Far: ' + usd(T.ceiling_usd) + ' for ' + T.estimated + ' of ' + T.to_estimate +
      ' PDF' + plural(T.to_estimate) + ' (estimating) · Batch Limit: ' + usd(T.limit_usd) + '</b></p>';
  } else if (before)
    h += '<p id="bt-cost">' + (exp ? exp + '<br>' : '') + 'Max Estimated Cost: ' + usd(T.ceiling_usd) + ' for ' + T.books_to_send + ' PDF' + plural(T.books_to_send) +
         (T.requests > T.books_to_send ? ' (' + T.requests + ' AI requests)' : '') + ' · Batch Limit: ' + usd(T.limit_usd) +
         (T.spent_usd ? ' · Already Spent in This Batch: ' + usd(T.spent_usd) : '') + (T.credit_usd != null ? ' · Credit: ' + usd(T.credit_usd) : ' · Credit: Not Checked') + '</p>';
  const total = !before && (T.spent_usd || s.phase === 'running' || s.phase === 'finished' || (s.trashed && s.trashed.n));
  if (total) h += '<p><b>Total Cost:</b> ' + esc(T.cost_words) + '</p>';   // one wording with the run page and the terminal (lib/costs.py)
  if (s.trashed && s.trashed.n) h += '<p>' + s.trashed.n + ' PDF' + plural(s.trashed.n) + ' moved to the Trash (AI cost ' + usd(s.trashed.cost_usd) + (T.spent_usd ? ', counted in the cost above' : '') + ')</p>';   // D8: the spend stays shown
  if (s.flagged.length) h += '<p>' + s.flagged.length + ' PDF' + (s.flagged.length === 1 ? '' : 's') + ' stopped and need' + (s.flagged.length === 1 ? 's' : '') +
    ' a person: ' + (s.flagged.length === 1 ? 'it is' : 'they are') + ' not sent. Each PDF\'s page says why.</p>';
  if (s.phase === 'estimating') h += '<p>Each PDF is being prepared and estimated (free). This page follows them; you can leave it and come back from the home page.</p>';
  if (s.phase === 'missing') h += '<p class="pp-warn-t">A PDF\'s estimate is missing, so the batch can\'t be sent.</p><p>Each PDF\'s page says what happened. ' +
    '"Get New Estimates" tries again for the PDFs without a result.</p><div class="pp-row"><button type="button" id="bt-again" data-act="again">Get New Estimates</button></div>';
  if (s.phase === 'needs-spend') h += '<p>The app restarted before the batch started, so nothing was sent.</p><div class="pp-row"><button type="button" id="bt-again" data-act="again">Get New Estimates</button>' +
    '<button type="button" id="bt-dismiss" data-act="dismiss">Dismiss</button></div>';
  if (s.phase === 'ready') {
    if (s.spend && s.spend.ok) h +=
      '<div class="pp-row"><button type="button" class="pp-primary" id="bt-spend" data-act="spend" aria-describedby="bt-cost">Start Remediation</button></div>' +
      '<p class="pp-note">' + (s.test ? 'Test: "Start Remediation" uses saved replies; nothing is sent to the AI service.' : '"Start Remediation" sends every PDF to the AI service. "Expected Cost" is based on the PDFs\' content and may vary. "Max Estimated Cost" is the estimated cost ceiling; it must fit within your spending limits and available credit. The actual cost is usually much lower.') + '</p>';
    else if (s.spend && s.spend.code === 'no_credit') h += '<p class="pp-warn-t" id="bt-why">' + esc(s.spend.why) + '</p>' +   // U8: stays while it is the reason
      '<div class="pp-row"><button type="button" class="pp-primary" id="bt-credit" data-act="credit">Check Credit Again</button></div>';
    else h += '<p class="pp-warn-t" id="bt-why">' + esc((s.spend && s.spend.why) || 'This batch can\'t be sent yet.') + '</p><p>' +
      (s.spend && s.spend.code === 'credit' ? 'The app administrator can add credit.' :
       s.spend && s.spend.code === 'limit' ? esc(s.spend.advice) :
       'Each PDF\'s page says more.') + '</p>';
  }
  if (s.phase === 'review' || (s.reviewing && s.reviewing.length && s.phase !== 'running')) h += '<p>' + s.reviewing.length + ' PDF' + (s.reviewing.length === 1 ? ' is' : 's are') +
    ' waiting for review. Open each one from the list; its "Finish Review" applies it, and this page and the dashboard follow.</p>';
  const asking = s.books.filter(b => b.language);                // D4: each PDF that waits for its language, on its own row
  if (asking.length) {
    h += '<h3 id="bt-lang-h">Language of the Scanned Pages</h3><p>' + asking.length + ' PDF' + (asking.length === 1 ? ' has' : 's have') +
      ' scanned pages read by OCR. Choose each one\'s language; its estimate follows. The batch can start once every one is answered.</p>';
    asking.forEach(b => {
      const q = b.language, id = 'bt-lang-' + b.name;                // by the PDF's short name: a redraw keeps its focus and choice
      const opts = (q.suggested ? '' : '<option value="" selected disabled>Choose a language</option>') +
        q.choices.map(c => '<option value="' + esc(c[0]) + '"' + (c[0] === q.suggested ? ' selected' : '') + '>' + esc(c[1]) + '</option>').join('');
      h += '<div class="pp-job"><p><b>' + esc(b.book) + '</b><br><span class="hm-file">Source PDF: ' + esc(b.file) + '</span></p>' +
        (q.evidence && q.evidence.length ? '<ul class="pp-note">' + q.evidence.map(x => '<li>' + esc(x) + '</li>').join('') + '</ul>' : '') +
        '<div class="pp-row"><label for="' + esc(id) + '">Language of the Scanned Pages</label><select id="' + esc(id) + '" data-book="' + esc(b.name) + '">' + opts + '</select>' +
        '<button type="button" class="pp-primary" data-act="language" data-book="' + esc(b.name) + '" data-sel="' + esc(id) + '">Continue</button>' +
        (asking.length > 1 ? '<button type="button" data-act="language-all" data-book="' + esc(b.name) + '" data-sel="' + esc(id) + '">Use for All Waiting PDFs</button>' : '') +
        '</div></div>';
    });
  }
  if (s.phase === 'running') h += '<p>The PDFs are being sent to the AI, a few at a time. Each PDF\'s status is shown below.</p>';   // V1
  if (s.phase === 'stopped' && s.job && s.job.status !== 'done') h += '<div class="pp-fail"><h4>Stopped: The batch stopped before every PDF finished</h4><p>The PDFs that finished keep their results.</p>' +
    '<details><summary>Details</summary><ul class="pp-note"><li>Exit code: ' + esc(s.job.exit) + '</li><li>Full log: runs/.app/jobs/' + esc(s.job.id) + '.log</li></ul></details></div>';
  if (s.again) h += '<div class="pp-row"><button type="button" id="bt-again" data-act="again">Run the Unfinished PDFs Again</button>' +
    '<span class="pp-note">New estimates first (free), then "Start Remediation" for those PDFs.</span></div>';
  h += dash(s);
  return h;
}
const money = x => x == null ? 'not recorded' : x < 0.01 && x > 0 ? '< $0.01' : usd(x);
function dash(s) {                                               // the batch dashboard (P8): blank result columns until a PDF is applied
  const rs = s.dashboard || []; if (!rs.length) return '';
  const SAFE = { ok: 'OK', failed: 'Failed', 'not checked': 'Not Checked' };
  const keep = new Set([...document.querySelectorAll('input[name=trash-pdf]:checked')].map(x => x.value));   // a redraw keeps the ticks
  let h = '<h3 id="bt-dash-h">Batch Dashboard</h3><div class="pp-tw" tabindex="0" role="region" aria-labelledby="bt-dash-h"><table class="hm-t bt-dash"><thead><tr>' +
    ['Select', 'PDF', 'Status', 'Needs a Person', 'AI Decisions', 'Safety', 'veraPDF (WCAG Rules)', 'AI Cost', 'Pages'].map(x => '<th scope="col">' + x + '</th>').join('') + '</tr></thead><tbody>';
  rs.forEach((r, i) => {
    const x = r.result;
    h += '<tr><td><input type="checkbox" name="trash-pdf" value="' + esc(r.name) + '" id="bt-sel-' + i + '" aria-labelledby="bt-n' + i + '"' + (keep.has(r.name) ? ' checked' : '') + '></td>' +
      '<th scope="row" id="bt-n' + i + '"><span class="hm-book">' + esc(r.book) + '</span><span class="hm-file">Source PDF: ' + esc(r.file) + '</span>' +
      '<span class="hm-acts bt-acts"><a class="pp-btn bt-open" href="' + esc(r.href) + '" id="bt-o' + i + '">Open</a> ' + rowMenu(r, i) + '</span></th><td>' + esc(r.status) + (x && !x.reviewed ? ' <span class="pp-note">(not reviewed)</span>' : '') + '</td>';
    if (!x) { h += '<td></td><td></td><td></td><td></td><td></td><td></td></tr>'; return; }
    h += '<td>' + x.needs + '</td><td>' + x.ai + '</td><td>' + esc(SAFE[x.safety] || x.safety) + '</td>' +
      '<td>' + (x.va == null ? 'not run' : (x.vb == null ? '–' : x.vb) + ' → ' + x.va + (x.new ? ' <b>(' + x.new + ' new)</b>' : '')) + '</td>' +
      '<td>' + money(x.cost) + '</td><td>' + (x.pages || 'not counted') + '</td></tr>';
  });
  return h + '</tbody></table></div><p class="pp-note">Sorted by "Needs a Person", most work first. Automated checks are evidence, not sign-off.</p>' +
    '<div class="pp-row"><button type="button" id="bt-trash-sel" data-trash="selected" data-label="' + esc(LABEL) + '">Move Selected to Trash</button>' +
    '<button type="button" id="bt-trash-all" data-trash="batch" data-label="' + esc(LABEL) + '">Move This Batch to Trash</button></div>';
}
// T2 (Patrick, 2026-11-07): a "⋯" menu per PDF, the same menu button as My Workspace's (webapp/shared.js): "Edit Name"
// (its display name, kept by sha256: never a file, folder or run name) and "New Run of This PDF" (a pop-up)
function rowMenu(r, i) {
  const mid = 'bt-m' + i, lab = 'More Actions for ' + esc(r.book);
  return '<span class="hm-menu"><button type="button" class="hm-more" id="bt-more-' + esc(r.name) + '" aria-haspopup="menu" aria-expanded="false" aria-controls="' + mid + '" aria-label="' + lab + '">' +
    '<span aria-hidden="true">⋯</span></button><span class="hm-mlist" role="menu" id="' + mid + '" aria-label="' + lab + '" hidden>' +
    '<button type="button" role="menuitem" tabindex="-1" data-edit="batchpdf" data-label="' + esc(LABEL) + '" data-book="' + esc(r.name) + '">Edit Name</button>' +
    '<button type="button" role="menuitem" tabindex="-1" data-dialog="/api/form?what=run&amp;run=' + esc(encodeURIComponent('batches/' + LABEL + '/' + r.name)) + '">New Run of This PDF</button>' +
    '</span></span>';
}
async function api(path, b) {
  const r = await fetch(path, b === undefined ? { cache: 'no-store' } : { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(b) });
  let d = {}; try { d = await r.json(); } catch (e) {}
  return [r.status, d];
}
let timer = null;
// #93 (Patrick's test of the app): on the batch page, the first answer comes with the page (batches.py page()), so "This
// Batch" is drawn at once, with no "Loading…"; every later one is asked for. Read once, then removed.
let first = (() => { const el = $('bt-first'); if (!el) return null; try { return JSON.parse(el.textContent); } catch (e) { return null; } finally { el.remove(); } })();
async function poll() {
  clearTimeout(timer);
  try {
    let c, s;
    if (first !== null) { [c, s] = [200, first]; first = null; }   // drawn in this same step: nothing waits for the network
    else [c, s] = await api(API);
    if (c === 200) {
      for (const b of s.books) { const was = seen[b.name]; seen[b.name] = b.status; if (primed && was && was !== b.status) live(b.book + ': ' + b.status); }
      primed = true; st = s; column(s);
      const bb = $('bt-body');
      // R9 (Patrick's test, 2026-11-07): a redraw never undoes a language chosen but not yet sent, and never happens while
      // a language list has focus (an open list would close under the person); the next poll draws it.
      const ae = document.activeElement;
      const busy_ = bb && (bb.querySelector('.hm-rename') || bb.querySelector('.hm-more[aria-expanded="true"]'));   // T2: never under an open menu or name box
      if (bb && !busy_ && !(ae && ae.tagName === 'SELECT' && bb.contains(ae))) {
        const h = body(s), keep = ae && ae.id;
        if (bb.dataset.h !== h) {
          const chosen = {}; bb.querySelectorAll('select[data-book][data-chosen]').forEach(x => { chosen[x.dataset.book] = x.value; });
          bb.innerHTML = h; bb.dataset.h = h;
          bb.querySelectorAll('select[data-book]').forEach(x => {
            const v = chosen[x.dataset.book];
            if (v && [...x.options].some(o => o.value === v)) { x.value = v; x.dataset.chosen = '1'; }
          });
          if (keep && $(keep)) $(keep).focus();
        }
      }
    }
  } catch (e) { if ($('bt-body')) msg('The app is not running, so this page can\'t follow the batch. ' + START); }
  const busy = st && (['estimating', 'running'].includes(st.phase) || st.books.some(b => b.tone === 'processing'));
  timer = setTimeout(poll, busy ? 2000 : 6000);
}
const panel = $('bt-panel');
if (panel) panel.addEventListener('change', e => { if (e.target.matches('select[data-book]')) e.target.dataset.chosen = '1'; });   // the person's choice
if (panel) panel.addEventListener('click', async e => {
  const b = e.target.closest('button[data-act]'); if (!b) return;
  const act = b.dataset.act;
  if (act === 'dismiss' && b.classList.contains('pp-x')) { msg(''); $('bt-h').focus(); return; }
  try {
    let c, r;
    if (act === 'spend') {
      [c, r] = await api(API + '/spend', { fingerprint: st.fingerprint });
    } else if (act === 'credit') {                                 // U8: "Check Credit Again" (free)
      b.disabled = true;
      const [c2, d] = await api('/api/credit', {});
      await poll();
      live(d.usd != null ? 'Credit checked: ' + usd(d.usd) + '.' : 'The credit still couldn\'t be checked.');
      const f = $('bt-spend') || $('bt-credit'); if (f) f.focus();
      return;
    } else if (act === 'language' || act === 'language-all') {
      const v = $(b.dataset.sel).value;
      if (!v) { msg('Choose a language first.', false, true); return; }
      [c, r] = await api(API + '/language', act === 'language' ? { book: b.dataset.book, lang: v } : { all: true, lang: v });   // R10
    } else [c, r] = await api(API + '/' + act, {});
    if (c !== 202 && c !== 200) return msg(r.error || 'The app refused this.', false, true);
    // R11: no notice that only repeats the status (the heading that takes focus says it); one that adds something stays
    if (act === 'dismiss') msg('Dismissed: nothing was sent.', true, false);
    else if (act === 'language-all' && r.left && r.left.length) msg(r.left.length + ' PDF' + (r.left.length === 1 ? ' still needs its' : 's still need their') +
      ' own answer: the language chosen isn\'t one of ' + (r.left.length === 1 ? 'its' : 'their') + ' choices (' + r.left.join(', ') + ').', false, false);
    else msg('');
    await poll(); $('bt-phase').focus();
  } catch (err) { msg('The app is not running. ' + START, false, true); }
});
poll();
})();
