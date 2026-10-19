"""workorder_check.py: the checks every work order goes through before apply.py sees it.

decide.py runs them on the model's reply; review_workorder.py runs the same checks on a work order a person has
reviewed, so an edit is held to the same rules as the AI's decision.

    dropped = check(wo, digest, not_sent, words_sent)

wo is changed in place: items that fail are removed and listed in `dropped` as {where, item, why}.
not_sent: figure objs (and "page N" for page figures) whose image was not sent to the model.
words_sent: ids of the OCR word forms whose word sheet was sent.
"""
import re, unicodedata

ALLOWED = {'H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'P', 'Span', 'Caption', 'Note', 'Div', 'Figure'}
KNOWN = {'schema', 'sections', 'artifacts', 'document', 'rolemap', 'merges', 'actual_text', 'retype', 'flatten', 'alt',
         'move_to_document_start', 'captions', 'lists', 'toc', 'notes', 'language', 'links', 'move_section',
         'fix_figure_order', 'remove_empty_containers', 'deferrals', 'notes_for_reviewer', 'adopt_orphans', 'page_figures',
         'keep_lists', 'ocr_words', 'tables'}
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

def check(wo, digest, not_sent, words_sent):
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
    if 'flatten' in wo:
        wo['flatten'] = keep('flatten', wo['flatten'], lambda it: None if isinstance(it, dict) and it.get('obj') in flat_objs else 'not a list or table listed in the digest')
    if 'tables' in wo:                          # header rows / columns of a real table: [{obj, header_rows, header_cols}]
        flattened = {it.get('obj') for it in wo.get('flatten') or [] if isinstance(it, dict)}
        table_objs = {x['obj'] for x in digest.get('tables', [])}
        def count_ok(v): return isinstance(v, int) and not isinstance(v, bool) and 0 <= v <= 3
        wo['tables'] = keep('tables', wo['tables'], lambda it: 'not a table listed in the digest' if not isinstance(it, dict) or it.get('obj') not in table_objs
                            else 'also flattened' if it['obj'] in flattened
                            else 'header_rows and header_cols must be whole numbers 0-3' if not (count_ok(it.get('header_rows', 0)) and count_ok(it.get('header_cols', 0)))
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
    if 'move_section' in wo:
        ms = wo['move_section']
        if not (len(ms.get('pages', [])) == 2 and all(page_ok(p) for p in ms['pages']) and page_ok(ms.get('before_page'))):
            drop('move_section', wo.pop('move_section'), 'bad pages')
    if 'links' in wo:
        for f_, r_ in wo['links'].get('toc_text_fixes', []):
            try: re.compile(f_)
            except Exception: drop('links', [f_, r_], 'bad regex'); wo['links']['toc_text_fixes'].remove([f_, r_])
    return dropped
