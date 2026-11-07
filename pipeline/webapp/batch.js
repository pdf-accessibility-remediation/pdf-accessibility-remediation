/* webapp/batch.js: the batch page and the side column of every book page in a batch (#45, home interface).

   The side column ("Books in This Batch"): each book with its status in words (never by colour alone), the current book
   marked aria-current="page"; a real button hides and shows the list (aria-expanded), remembered in this browser only (a
   convenience); on a narrow screen (below 48em, 320 px included) the list starts closed under its button, in the page's
   flow, so nothing scrolls sideways. "Skip to the content" skips it. The statuses are kept current from /api/batch/<label>.

   The batch page: the estimate of every book added up, the batch limit and the credit, "Spend" (with the
   worst-case estimate beside it), the running total while it runs, "Open the Batch Dashboard"
   when the batch has one, and "Run the Unfinished Books Again". Focus moves only after the person's own action. */
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
function closed() { try { const v = localStorage.getItem(KEY); return v === null ? narrow.matches : v === '1'; } catch (e) { return narrow.matches; } }
function setOpen(open, remember) {
  const t = $('bn-toggle'), n = nav.querySelectorAll('#bn-list li').length;
  nav.classList.toggle('closed', !open); document.body.classList.toggle('bn-closed', !open);
  t.setAttribute('aria-expanded', String(open)); t.textContent = open ? 'Hide the Book List' : 'Show the Book List (' + n + ')';
  if (remember) { try { localStorage.setItem(KEY, open ? '0' : '1'); } catch (e) {} }
}
document.body.classList.add('bn-on');
setOpen(!closed(), false);
$('bn-toggle').addEventListener('click', () => setOpen(nav.classList.contains('closed'), true));

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
  });
}
const PHASE = { estimating: 'Estimating', ready: 'Ready to Spend', running: 'Running', finished: 'Finished', stopped: 'Stopped', missing: 'Stopped: an Estimate Is Missing', 'needs-spend': 'Spend Again' };
function body(s) {
  const T = s.totals, n = s.books.length;
  let h = '<h3 id="bt-phase" tabindex="-1">' + esc(PHASE[s.phase] || s.phase) + '</h3>';
  if (s.test) h += '<p class="pp pp-bar">Test: saved replies, no AI call.</p>';
  h += '<p>' + T.finished + ' of ' + n + ' books finished' + (s.ocr_name ? ' · OCR Language: ' + esc(s.ocr_name) : '') + '</p>';
  const x = T.expected;
  if (s.phase === 'ready' || s.phase === 'estimating' || s.phase === 'missing')
    h += '<p><b>' + (x ? 'About ' + usd(x.usd) + ' · ' : '') + 'Worst-case estimate ' + usd(T.ceiling_usd) + ' for ' + T.books_to_send + ' book' + (T.books_to_send === 1 ? '' : 's') +
         ' · Batch limit ' + usd(T.limit_usd) + (T.credit_usd != null ? ' · Credit ' + usd(T.credit_usd) : ' · Credit not checked') + '</b></p>';
  if (T.spent_usd || s.phase === 'running' || s.phase === 'finished')
    h += '<p>Spent so far: ' + usd(T.spent_usd) + (T.shown_ceiling_usd != null ? ' (worst-case estimate ' + usd(T.shown_ceiling_usd) + ')' : '') + '</p>';
  if (s.flagged.length) h += '<p>' + s.flagged.length + ' book' + (s.flagged.length === 1 ? '' : 's') + ' stopped and need' + (s.flagged.length === 1 ? 's' : '') +
    ' a person: ' + (s.flagged.length === 1 ? 'it is' : 'they are') + ' not sent. Each book\'s page says why.</p>';
  if (s.phase === 'estimating') h += '<p>Each book is being prepared and estimated (free). This page follows them; you can leave it and come back from the home page.</p>';
  if (s.phase === 'missing') h += '<p class="pp-warn-t">A book\'s estimate is missing, so the batch can\'t be sent.</p><p>Each book\'s page says what happened. ' +
    '"Get New Estimates" tries again for the books without a result.</p><div class="pp-row"><button type="button" id="bt-again" data-act="again">Get New Estimates</button></div>';
  if (s.phase === 'needs-spend') h += '<p>The app restarted before the batch started, so nothing was sent.</p><div class="pp-row"><button type="button" id="bt-again" data-act="again">Get New Estimates</button>' +
    '<button type="button" id="bt-dismiss" data-act="dismiss">Dismiss</button></div>';
  if (s.phase === 'ready') {
    h += '<p>Books in a batch are applied without a review first. Review each one afterwards from its page.</p>';
    if (s.spend && s.spend.ok) h +=
      '<div class="pp-row"><button type="button" class="pp-primary" id="bt-spend" data-act="spend">Spend</button></div>' +
      '<p class="pp-note">' + (s.test ? 'Test: "Spend" uses saved replies; nothing is sent to the AI service.' : '"Spend" sends every book to the AI service. The cost is bound to the worst-case estimate above; the real cost is usually much lower.') + '</p>';
    else h += '<p class="pp-warn-t">' + esc((s.spend && s.spend.why) || 'This batch can\'t be sent yet.') + '</p><p>Whoever looks after the app can raise the limit or add credit; or start a batch with fewer books.</p>';
  }
  if (s.phase === 'running') h += '<p>The books are being sent and applied, ' + 'a few at a time. Each book\'s status is in the list of books.</p>';
  if (s.phase === 'stopped' && s.job && s.job.status !== 'done') h += '<div class="pp-fail"><h4>Stopped: The batch stopped before every book finished</h4><p>The books that finished keep their results.</p>' +
    '<details><summary>Details</summary><ul class="pp-note"><li>Exit code: ' + esc(s.job.exit) + '</li><li>Full log: runs/.app/jobs/' + esc(s.job.id) + '.log</li></ul></details></div>';
  if (s.summary) h += '<p><a class="pp-btn" href="summary.html">Open the Batch Dashboard</a></p>';
  if (s.again) h += '<div class="pp-row"><button type="button" id="bt-again" data-act="again">Run the Unfinished Books Again</button>' +
    '<span class="pp-note">New estimates first (free), then "Spend" for those books.</span></div>';
  return h;
}
async function api(path, b) {
  const r = await fetch(path, b === undefined ? { cache: 'no-store' } : { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(b) });
  let d = {}; try { d = await r.json(); } catch (e) {}
  return [r.status, d];
}
let timer = null;
async function poll() {
  clearTimeout(timer);
  try {
    const [c, s] = await api(API);
    if (c === 200) {
      for (const b of s.books) { const was = seen[b.name]; seen[b.name] = b.status; if (primed && was && was !== b.status) live(b.book + ': ' + b.status); }
      primed = true; st = s; column(s);
      const bb = $('bt-body');
      if (bb) {
        const h = body(s), keep = document.activeElement && document.activeElement.id;
        if (bb.dataset.h !== h) { bb.innerHTML = h; bb.dataset.h = h; if (keep && $(keep)) $(keep).focus(); }
      }
    }
  } catch (e) { if ($('bt-body')) msg('The app is not running, so this page can\'t follow the batch. ' + START); }
  const busy = st && ['estimating', 'running'].includes(st.phase);
  timer = setTimeout(poll, busy ? 2000 : 6000);
}
const panel = $('bt-panel');
if (panel) panel.addEventListener('click', async e => {
  const b = e.target.closest('button[data-act]'); if (!b) return;
  const act = b.dataset.act;
  if (act === 'dismiss' && b.classList.contains('pp-x')) { msg(''); $('bt-h').focus(); return; }
  try {
    let c, r;
    if (act === 'spend') {
      [c, r] = await api(API + '/spend', { fingerprint: st.fingerprint });
    } else [c, r] = await api(API + '/' + act, {});
    if (c !== 202 && c !== 200) return msg(r.error || 'The app refused this.', false, true);
    msg(act === 'spend' ? 'The batch has started.' : act === 'dismiss' ? 'Dismissed: nothing was sent.' : 'New estimates have started (free).', true, false);
    await poll(); $('bt-phase').focus();
  } catch (err) { msg('The app is not running. ' + START, false, true); }
});
poll();
})();
