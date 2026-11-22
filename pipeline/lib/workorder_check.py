"""workorder_check.py: the checks every work order goes through before apply.py sees it.

decide.py runs them on the model's reply; review_workorder.py runs the same checks on a work order a person has
reviewed, so an edit is held to the same rules as the AI's decision.

    dropped = check(wo, digest, not_sent, words_sent, order=None)
    dropped = check_language_parts(wo, pages, places=None)     (also run by check(); #118, language tagging)

wo is changed in place: items that fail are removed and listed in `dropped` as {where, item, why}.
not_sent: figure objs (and "page N" for page figures) whose image was not sent to the model.
words_sent: ids of the OCR word forms whose word sheet was sent.
order: the audit's full reading order (fulltext.json's reading_order), for the section-move rule; without it the
digest's reading_order lines are used. A move is kept only when the audit finds a section read out of place
(lib/readorder.py) inside its pages, or at the page it lands before (of two swapped sections, either may be the one
flagged): a move the audit gives no reason for only re-nests a section or leaves it where it is.
"""
import re, unicodedata
from lib import readorder, langtag, langreq

ALLOWED = {'H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'P', 'Span', 'Caption', 'Note', 'Div', 'Figure'}
KNOWN = {'schema', 'sections', 'artifacts', 'document', 'rolemap', 'merges', 'actual_text', 'retype', 'flatten', 'alt',
         'move_to_document_start', 'captions', 'lists', 'toc', 'notes', 'language', 'links', 'move_section',
         'fix_figure_order', 'remove_empty_containers', 'deferrals', 'notes_for_reviewer', 'adopt_orphans', 'page_figures',
         'keep_lists', 'ocr_words', 'tables', 'page_readings', 'language_parts'}
META = {'source', 'decided_by', 'reviewed_by'}       # written by the pipeline, not by the model: never checked or dropped

JUNK = set("il1jtfrz;:'./|_~()¢£")           # what OCR turns unknown letters into: ñ → "ii", ṇ → "l;l" / "lJ" / "t:J."
def skeleton(t): return ''.join(c for c in unicodedata.normalize('NFKD', t.lower()) if not unicodedata.combining(c))
def distance(ocr, reading):
    """Edits from the OCR text to the reading, without diacritics. Changing or dropping an OCR junk character costs
    a quarter, any other edit 1: a letter garbled into several junk characters is cheap, a different word is not."""
    a, b = skeleton(ocr), skeleton(reading); row = [float(j) for j in range(len(b) + 1)]
    for ca in a:
        c = 0.25 if ca in JUNK else 1; new = [row[0] + c]
        for j, cb in enumerate(b, 1): new.append(min(row[j] + c, new[j - 1] + 1, row[j - 1] + (0 if ca == cb else c)))
        row = new
    return row[-1]

def check(wo, digest, not_sent, words_sent, order=None):
    N = digest['source']['pages']
    objs = ({e['obj'] for e in digest['elements']} | {f['obj'] for f in digest['figures']} | {h['obj'] for h in digest.get('headings', [])}
            | {c['obj'] for c in digest.get('heading_candidates', [])})
    flat_objs = {x['obj'] for x in digest.get('lists', [])} | {x['obj'] for x in digest.get('tables', [])}
    single = {f['obj'] for f in digest['figures'] if f.get('single_run')}
    styles = {s['style'] for s in digest['styles']}
    words = {w['id']: w for w in digest.get('ocr_words') or []}
    dropped = []
    def drop(where, item, why): dropped.append({'where': where, 'item': item, 'why': why})
    def page_ok(p): return isinstance(p, int) and 1 <= p <= N
    for k in list(wo):
        if k not in KNOWN and k not in META: drop(k, wo.pop(k), 'unknown key')
    def keep(key, items, test):
        out = []
        for it in items or []:
            why = test(it)
            if why: drop(key, it, why)
            else: out.append(it)
        return out
    if 'artifacts' in wo:
        a = wo['artifacts']
        a['elements'] = keep('artifacts.elements', a.get('elements'), lambda it: None if it.get('obj') in single else
                             ('not a single-run figure listed in the digest' if it.get('obj') in objs else 'unknown obj'))
        def rule_ok(r):
            try: re.compile(r.get('regex', '.*'))
            except Exception: return 'bad regex'
            if r.get('band', 'any') not in ('top', 'bottom', 'any'): return 'band must be top, bottom or any'
            return None if all(page_ok(p) for p in r.get('pages', [])) and len(r.get('pages', [])) == 2 else 'bad page range'
        a['text_rules'] = keep('artifacts.text_rules', a.get('text_rules'), rule_ok)
        def untagged_ok(r):
            if not (len(r.get('pages', [])) == 2 and all(page_ok(p) for p in r['pages'])): return 'bad page range'
            if r.get('regex'):
                try: re.compile(r['regex'])
                except Exception: return 'bad regex'
                return None
            return None if r.get('where') == 'in_figure' else 'needs regex or where: in_figure'
        if 'untagged' in a: a['untagged'] = keep('artifacts.untagged', a.get('untagged'), untagged_ok)
    if 'rolemap' in wo:
        for s_, t in list(wo['rolemap'].items()):
            if s_ not in styles: drop('rolemap', {s_: t}, 'unknown style'); del wo['rolemap'][s_]
            elif t not in ALLOWED - {'Figure'}: drop('rolemap', {s_: t}, 'target not allowed'); del wo['rolemap'][s_]
    for key in ('actual_text', 'retype', 'alt'):
        if key in wo:
            wo[key] = keep(key, wo[key], lambda it: None if it.get('obj') in objs else 'unknown obj')
    if 'retype' in wo: wo['retype'] = keep('retype', wo['retype'], lambda it: None if it.get('type') in ALLOWED else 'type not allowed')
    if 'alt' in wo:
        figs = {f['obj'] for f in digest['figures']}
        wo['alt'] = keep('alt', wo['alt'], lambda it: None if it.get('obj') in figs and str(it.get('alt', '')).strip() else 'not a figure or empty alt')
        wo['alt'] = keep('alt', wo['alt'], lambda it: 'its image was not sent (over --max-images), so the alt was written unseen' if it.get('obj') in not_sent else None)
    if 'deferrals' in wo:                       # optional "pages": PDF page integers; anything else is dropped, the deferral kept
        for d_ in wo['deferrals'] if isinstance(wo['deferrals'], list) else []:
            if isinstance(d_, dict) and 'pages' in d_:
                ps_ = d_['pages'] if isinstance(d_['pages'], list) else [d_['pages']]
                good = [p for p in ps_ if page_ok(p)]
                if len(good) != len(ps_): drop('deferrals.pages', {'what': d_.get('what'), 'pages': ps_}, 'not PDF page numbers in range')
                if good: d_['pages'] = good
                else: del d_['pages']
    if 'page_figures' in wo:
        pfs = {pf['page']: pf for pf in digest.get('page_figures') or []}
        wo['page_figures'] = keep('page_figures', wo['page_figures'], lambda it: 'not a page listed in page_figures' if not isinstance(it, dict) or it.get('page') not in pfs
                                  else 'empty alt' if not str(it.get('alt', '')).strip()
                                  else 'its page image was not sent (over --max-images), so the alt was written unseen' if f'page {it["page"]}' in not_sent else None)
    if 'ocr_words' in wo:                       # {"id": "reading"} → [{id, text, reads, count}] for the executor
        raw_ow = wo.pop('ocr_words')
        items = ([{'id': k, 'reads': v} for k, v in raw_ow.items()] if isinstance(raw_ow, dict) else raw_ow if isinstance(raw_ow, list) else [])
        out = []
        for it in items:
            try: i = int(it.get('id')) if isinstance(it, dict) else None
            except (TypeError, ValueError): i = None
            reads = unicodedata.normalize('NFC', str(it.get('reads', '')).strip()) if isinstance(it, dict) else ''
            why = ('unknown id' if i not in words else 'its word sheet was not sent' if i not in words_sent
                   else 'empty' if not reads else 'not one word' if re.search(r'\s', reads) or len(reads) > 80
                   else 'same as the OCR text' if reads == words[i]['text']
                   else 'too different from the OCR text to be a misreading of it'
                   if distance(words[i]['text'], reads) > max(2, 0.34 * len(skeleton(reads))) else None)
            if why: drop('ocr_words', it, why); continue
            out.append({'id': i, 'text': words[i]['text'], 'reads': reads, 'count': words[i]['count']})
        if out: wo['ocr_words'] = out
    if 'page_readings' in wo:                   # whole-page readings of scanned Hawaiian pages (read_pages.py): [{page, text}]
        seen_p = set()
        def page_reading(it):
            if not isinstance(it, dict) or not isinstance(it.get('page'), int) or isinstance(it.get('page'), bool) or not 1 <= it['page'] <= N: return 'bad page'
            if not isinstance(it.get('text'), str) or not it['text'].strip(): return 'empty'
            if it['page'] in seen_p: return 'the same page twice'
            seen_p.add(it['page']); it['text'] = unicodedata.normalize('NFC', it['text'])
        wo['page_readings'] = keep('page_readings', wo['page_readings'] if isinstance(wo['page_readings'], list) else [], page_reading)
        if not wo['page_readings']: del wo['page_readings']
    if 'flatten' in wo:
        wo['flatten'] = keep('flatten', wo['flatten'], lambda it: None if isinstance(it, dict) and it.get('obj') in flat_objs else 'not a list or table listed in the digest')
    if 'tables' in wo:                          # header rows / columns of a real table: [{obj, header_rows, header_cols}]
        flattened = {it.get('obj') for it in wo.get('flatten') or [] if isinstance(it, dict)}
        table_objs = {x['obj'] for x in digest.get('tables', [])}
        table_rows = {x['obj']: x.get('rows') for x in digest.get('tables', [])}
        def count_ok(v): return isinstance(v, int) and not isinstance(v, bool) and 0 <= v <= 3
        def rows_ok(it, key):
            v = it.get(key, [])
            n = table_rows.get(it['obj'])
            return isinstance(v, list) and all(isinstance(r, int) and not isinstance(r, bool) and r >= 0 and (n is None or r < n) for r in v)
        wo['tables'] = keep('tables', wo['tables'], lambda it: 'not a table listed in the digest' if not isinstance(it, dict) or it.get('obj') not in table_objs
                            else 'also flattened' if it['obj'] in flattened
                            else 'header_rows and header_cols must be whole numbers 0-3' if not (count_ok(it.get('header_rows', 0)) and count_ok(it.get('header_cols', 0)))
                            else 'title_rows and note_rows must be whole numbers 0-3' if not (count_ok(it.get('title_rows', 0)) and count_ok(it.get('note_rows', 0)))
                            else 'group_rows and repeat_rows must list row numbers in the table' if not (rows_ok(it, 'group_rows') and rows_ok(it, 'repeat_rows'))
                            else 'no header rows or columns' if not (it.get('header_rows', 0) or it.get('header_cols', 0)) else None)
        seen_t = set()
        wo['tables'] = keep('tables', wo['tables'], lambda it: 'the same table twice' if it['obj'] in seen_t else seen_t.add(it['obj']))
    if isinstance(wo.get('document'), dict) and 'lang' in wo['document']:     # a BCP 47 tag; spelling tidied (en_US -> en-US), never guessed
        from . import langtag
        tag = langtag.norm(wo['document']['lang'])
        if tag: wo['document']['lang'] = tag
        else: drop('document.lang', wo['document'].pop('lang'), 'not a BCP 47 language tag')
    if 'keep_lists' in wo:
        rule_objs = {l['obj'] for l in digest.get('lists') or [] if l.get('flattened_by_rule')}
        wo['keep_lists'] = keep('keep_lists', wo['keep_lists'], lambda it: None if isinstance(it, dict) and it.get('obj') in rule_objs
                                else 'not a list the one-item rule would flatten')
    if 'merges' in wo:
        wo['merges'] = keep('merges', wo['merges'], lambda r: None if r.get('style') in styles and r.get('direction') in ('next', 'prev')
                            and all(w in styles for w in r.get('with', [])) else 'unknown style or direction')
    if 'move_to_document_start' in wo:
        wo['move_to_document_start'] = keep('move_to_document_start', wo['move_to_document_start'], lambda o: None if o in objs else 'unknown obj')
    if 'captions' in wo and not any(s_.startswith(wo['captions'].get('style', '\0')) for s_ in styles): drop('captions', wo.pop('captions'), 'no such style')
    if 'toc' in wo:
        t_ = wo['toc']; bad_ = [x for x in t_.get('item_styles') or [] if x not in styles]
        if bad_: drop('toc', bad_, 'unknown styles'); t_['item_styles'] = [x for x in t_['item_styles'] if x in styles]
        if t_.get('pages') and not (len(t_['pages']) == 2 and all(page_ok(p) for p in t_['pages'])): drop('toc', {'pages': t_.pop('pages')}, 'bad page range')
        if not t_.get('item_styles') and not (t_.get('item_prefix') and any(s_.startswith(t_['item_prefix']) for s_ in styles)):
            drop('toc', wo.pop('toc'), 'no such style')
    if 'adopt_orphans' in wo:
        wo['adopt_orphans'] = keep('adopt_orphans', wo['adopt_orphans'], lambda r: None if len(r.get('pages', [])) == 2 and all(page_ok(p) for p in r['pages']) else 'bad page range')
    if 'lists' in wo: wo['lists'] = keep('lists', wo['lists'], lambda r: None if r.get('first_style') in styles else 'unknown style')
    if 'notes' in wo:
        bad = [s_ for s_ in wo['notes'].get('styles', []) if s_ not in styles]
        if bad: drop('notes', bad, 'unknown styles'); wo['notes']['styles'] = [s_ for s_ in wo['notes']['styles'] if s_ in styles]
    if 'sections' in wo:
        sec = wo['sections']
        for k in ('notes_pages',):
            if k in sec and not (len(sec[k]) == 2 and all(page_ok(p) for p in sec[k])): drop('sections', {k: sec.pop(k)}, 'bad page range')
        if 'toc_pages' in sec: sec['toc_pages'] = [p for p in sec['toc_pages'] if page_ok(p)]
        if 'index_from' in sec and not page_ok(sec['index_from']): drop('sections', {'index_from': sec.pop('index_from')}, 'bad page')
    if 'move_section' in wo:                         # one move (v8) or a list (v9): each checked, the shape kept
        ms, kept = wo['move_section'], []
        es = order if order else readorder.parse_lines(digest.get('reading_order'))
        away = [(es[x['i']]['first'], es[x['i']]['last']) for x in readorder.out_of_order(es)] if es else None   # None: no order to judge by
        for m in [ms] if isinstance(ms, dict) else ms if isinstance(ms, list) else [ms]:
            if not (isinstance(m, dict) and len(m.get('pages') or []) == 2 and all(page_ok(p) for p in m['pages']) and page_ok(m.get('before_page'))):
                drop('move_section', m, 'bad pages')
            elif away is not None and not any(m['pages'][0] <= f <= m['pages'][1] or f == m['before_page'] for f, _ in away):
                drop('move_section', m, 'the audit finds no section read out of place in these pages or where it lands')
            elif len(kept) == readorder.MAX_MOVES: drop('move_section', m, f'more than {readorder.MAX_MOVES} section moves')
            elif any(m['pages'][0] <= k['pages'][1] and k['pages'][0] <= m['pages'][1] for k in kept):
                drop('move_section', m, 'its pages overlap another section move')
            elif any(k['pages'][0] <= m['before_page'] <= k['pages'][1] or m['pages'][0] <= k['before_page'] <= m['pages'][1] for k in kept):
                drop('move_section', m, 'it lands inside the pages of another section move')
            else: kept.append(m)
        if not kept: wo.pop('move_section')
        else: wo['move_section'] = kept[0] if isinstance(ms, dict) else kept
    if 'links' in wo:
        for f_, r_ in wo['links'].get('toc_text_fixes', []):
            try: re.compile(f_)
            except Exception: drop('links', [f_, r_], 'bad regex'); wo['links']['toc_text_fixes'].remove([f_, r_])
    dropped += check_language_parts(wo, N)
    return dropped


LANG_PART_KEYS = {'page', 'mcid', 'first', 'last', 'lang', 'text', 'form', 'class', 'confidence', 'whole', 'source', 'why', 'note'}

def check_language_parts(wo, pages, places=None):
    """wo['language_parts'] = {'parts': [{page, mcid, first, last, lang, text?, form?, …}]}: language tags on words and
    passages, each a place in one marked-content run (first and last: character indexes within it, lib/langcands.py).
    A part is dropped when its page, run or indexes are not whole numbers in range, its language is not one the step may
    write (langtag.valid_part: shortest form, a named language, never 'jp', 'cn', 'eng' or a deprecated code), it
    overlaps another part in the same run, or (places given: the audit's candidate places, as (page, mcid, first, last))
    it is not one of them. Changes wo in place; returns the dropped parts as {where, item, why}."""
    dropped = []
    lp = wo.get('language_parts')
    if lp is None: return dropped
    if langreq.has_forms(lp): return _check_rows(lp, pages, dropped)
    if not isinstance(lp, dict) or not isinstance(lp.get('parts'), list):
        dropped.append({'where': 'language_parts', 'item': lp, 'why': 'not a {"parts": [...]} object'}); wo.pop('language_parts'); return dropped
    def whole(v): return isinstance(v, int) and not isinstance(v, bool)
    keep, seen = [], {}
    for it in lp['parts']:
        why = None
        if not isinstance(it, dict): why = 'not an object'
        elif set(it) - LANG_PART_KEYS: why = f'unknown keys: {sorted(set(it) - LANG_PART_KEYS)}'
        elif not (whole(it.get('page')) and 1 <= it['page'] <= pages): why = 'page not in the book'
        elif not (whole(it.get('mcid')) and it['mcid'] >= 0): why = 'run (MCID) not a whole number'
        elif not (whole(it.get('first')) and whole(it.get('last')) and 0 <= it['first'] <= it['last']): why = 'character indexes not in order'
        elif not langtag.valid_part(it.get('lang')):
            why = f'language tag not allowed: {it.get("lang")!r}' + (f' (shortest form: {langtag.shortest(it.get("lang"))})'
                                                                        if langtag.shortest(it.get('lang')) not in (None, it.get('lang')) else '')
        elif places is not None and (it['page'], it['mcid'], it['first'], it['last']) not in places: why = 'not a candidate place found by the audit'
        else:
            key = (it['page'], it['mcid'])
            if any(not (it['last'] < a or it['first'] > b) for a, b in seen.get(key, [])): why = 'overlaps another part in the same run'
            else: seen.setdefault(key, []).append((it['first'], it['last']))
        if why: dropped.append({'where': 'language_parts', 'item': it, 'why': why})
        else: keep.append(it)
    lp['parts'] = keep
    return dropped

FORM_KEYS = {'key', 'form', 'group', 'class', 'lang', 'confidence', 'why', 'evidence', 'current', 'tag', 'person', 'places', 'context',
             'decided', 'note', 'rule', 'reading', 'group_approval', 'no_answer',
             'carried',                         # where a publisher's tag sits (review 12, C of #118): to_rows writes it (review 17 §4)
             'latin_list', 'latin_phrase'}      # proposal 14: the review page's dictionary marks (review 15, M1)
RULES = {'reading'}                                    # lib/hanreading.RULE: the one local rule (#123)
from lib.langreq import NO_ANSWER   # why a form has no AI answer (#137); one list, so a new reason is never dropped here (#151, review 22 M3)
READING_KEYS = {'lang', 'langs', 'text', 'with', 'places', 'back'}
GROUP_APPROVALS = {'all_shown', 'readings', 'printed_reading'}   # the review page's group-approval buttons (#124; #132 the third)

def _check_rows(lp, pages, dropped):
    """language_parts versions 2 and 3 (lib/langreq.to_rows): forms, and rows [page, mcid, first, last, form index] or
    [page, [[mcid, first, last], …], form index] (one place across several runs: #150, #161). The structure (one parent,
    next to each other, no spoken text) is the finder's and the executor's to check: this check has no PDF (review 02, M3). A form whose
    language is not one the step may write is not tagged (its `tag` set false, its places kept for a person); a row that is
    not five whole numbers in range, or that overlaps a row of a tagged form in the same run, is dropped."""
    forms = lp.get('forms') if isinstance(lp.get('forms'), list) else []
    lp['forms'] = forms
    for i, f in enumerate(forms):
        if not isinstance(f, dict): forms[i] = f = {'tag': False}; dropped.append({'where': 'language_parts.forms', 'item': i, 'why': 'not an object'})
        extra = set(f) - FORM_KEYS - {'_card'}            # _card: the review page's marker for its own check (review/core.problems; review 08, M1)
        if extra: dropped.append({'where': 'language_parts.forms', 'item': f.get('form'), 'why': f'unknown keys: {sorted(extra)}'})
        if f.get('lang') is not None and not langtag.valid_part(f.get('lang')):
            dropped.append({'where': 'language_parts.forms', 'item': f.get('form'), 'why': f'language tag not allowed: {f.get("lang")!r}'
                            + (f' (shortest form: {langtag.shortest(f.get("lang"))})' if langtag.shortest(f.get('lang')) not in (None, f.get('lang')) else '')})
            f['tag'] = False; f['lang'] = None
        if f.get('tag') and not f.get('lang'): f['tag'] = False
        if 'rule' in f and f['rule'] not in RULES:     # #123: only the reading rule decides locally
            dropped.append({'where': 'language_parts.forms', 'item': f.get('form'), 'why': f'not a local rule: {f["rule"]!r}'}); f.pop('rule')
        if 'no_answer' in f and f['no_answer'] not in NO_ANSWER:   # #137 (review 02, L2): only the reasons the page can word
            dropped.append({'where': 'language_parts.forms', 'item': f.get('form'), 'why': f'not a no-answer reason: {f["no_answer"]!r}'}); f.pop('no_answer')
        r = f.get('reading')
        if r is not None and not (isinstance(r, dict) and set(r) <= READING_KEYS and (r.get('lang') is None or langtag.valid_part(r.get('lang')))
                                  and isinstance(r.get('langs', []), list) and all(langtag.valid_part(x) for x in r.get('langs', []))):
            dropped.append({'where': 'language_parts.forms', 'item': f.get('form'), 'why': 'reading not a reading record'}); f.pop('reading')
        g = f.get('group_approval')
        if g is not None and not (isinstance(g, dict) and g.get('button') in GROUP_APPROVALS):
            dropped.append({'where': 'language_parts.forms', 'item': f.get('form'), 'why': 'group_approval not one of the group-approval buttons'}); f.pop('group_approval')
    keep, seen = [], {}
    for r in lp.get('parts') if isinstance(lp.get('parts'), list) else []:
        why = None
        page, segs, *fi = langreq.parse_row(r)                  # one shape check for every reader (review 02, H2)
        if page is None: why = segs
        elif not 1 <= page <= pages: why = 'page not in the book'
        elif langreq.segments_problem(segs): why = langreq.segments_problem(segs)
        elif not 0 <= fi[0] < len(forms): why = 'no such form'
        elif forms[fi[0]].get('tag'):                       # each segment against every tagged row in its run, of either shape
            if any(not (b_ < a or a_ > b) for m, a_, b_ in segs for a, b in seen.get((page, m), [])): why = 'overlaps another part in the same run'
            else:
                for m, a_, b_ in segs: seen.setdefault((page, m), []).append((a_, b_))
        if why: dropped.append({'where': 'language_parts', 'item': r, 'why': why})
        else: keep.append(r)
    lp['parts'] = keep
    return dropped
