"""test_review_problems.py: the check's verdict card by card (review/core.py problems) and the server's use of it (#48):
each field marked from each save, and Finish refused while a card's choice would be dropped. A synthetic digest in a
temporary run folder; no PDF is rendered and no model is called.

    python -m pytest tests/test_review_problems.py -q

What is tested: a value the check refuses lands on its own card (an AI card, an added card, the move box that is wrong);
choices that clash are one conflict naming every card; the origin (review, earlier session, the AI's untouched choice);
a drop no card holds is left out and never blocks Finish; every reason the check gives has a fix in plain words; /keep
returns the problems and /finish refuses with needs "invalid" until they are fixed.
"""
import os, re, json, inspect, threading, time, socket, urllib.request
from review import core
from lib import workorder_check
from test_review_sessions import up  # noqa: E402  (waits for the server to answer)

def entry(id_, first, last, parent=None, depth=1, top=True, under=None, firsts=()):
    return {'id': id_, 'parent': parent, 'style': 'Sect', 'first': first, 'last': last, 'depth': depth, 'text': id_, 'skip': False,
            'group': True, 'top': top, 'under': under, 'firsts': list(firsts)}

def order():
    """front 1, body 10-60, tail 80, then 'about' (PDF 3) and 'end' (PDF 70) read after tail: two sections out of place."""
    return [entry('part', 1, 80, firsts=[1, 10, 80, 3, 70]), entry('front', 1, 1, 'part', 2, False, 'part', [1]),
            entry('body', 10, 60, 'part', 2, False, 'part', [10]), entry('tail', 80, 80, 'part', 2, False, 'part', [80]),
            entry('about', 3, 3, 'part', 2, False, 'part', [3]), entry('end', 70, 70, 'part', 2, False, 'part', [70])]

def digest():
    return {'source': {'pages': 80, 'file': 'book.pdf', 'sha256': 'f' * 64},
            'elements': [{'obj': '10 0', 'text': 'Introduction', 'page': 1, 'style': 'P'}],
            'headings': [{'obj': '11 0', 'text': 'The Book', 'page': 1, 'style': 'Title', 'level': 'H1'}],
            'heading_candidates': [], 'lists': [],
            'tables': [{'obj': '30 0', 'page': 5, 'rows': 4, 'cols': 3}, {'obj': '31 0', 'page': 6, 'rows': 4, 'cols': 3}],
            'figures': [{'obj': '20 0', 'page': 2, 'alt': None, 'image': None}],
            'styles': [{'style': 'Title', 'count': 1, 'pages': [1, 1], 'maps_to': 'H1'}, {'style': 'P', 'count': 40, 'pages': [1, 80], 'maps_to': 'P'}]}

def ai_order():
    return {'source': {'file': 'book.pdf', 'sha256': 'f' * 64},
            'retype': [{'obj': '10 0', 'type': 'H2'}], 'alt': [{'obj': '20 0', 'alt': 'A map of the island'}],
            'tables': [{'obj': '30 0', 'header_rows': 1, 'header_cols': 0}], 'document': {'title': 'The Book'},
            'move_section': [{'pages': [3, 3], 'before_page': 10}, {'pages': [70, 70], 'before_page': 80}]}

def run(tmp_path, ai=None):
    R = str(tmp_path); os.makedirs(os.path.join(R, '_audit'), exist_ok=True)
    core.save(os.path.join(R, '_audit', 'digest.json'), digest())
    core.save(os.path.join(R, '_audit', 'fulltext.json'), {'reading_order': order()})
    ai = ai or ai_order(); core.save(os.path.join(R, 'workorder.ai.json'), ai)
    ro = core.reading_order(digest(), {'reading_order': order()}, ai)
    return R, ai, core.build_items(ai, digest(), ro['entries'], ro), core.addable(ai, digest(), ro)

def probs(tmp_path, decisions, additions=(), ai=None, set_in=None):
    R, ai, items, adds = run(tmp_path, ai)
    return core.problems(R, ai, items, decisions, list(additions), adds, 'Kim', set_in)[0]

# ------------------------------------------------------------------ core.problems
def test_nothing_changed_nothing_to_fix(tmp_path):
    assert probs(tmp_path, {}) == {'fields': [], 'conflicts': [], 'unplaced': []}

def test_an_empty_alt_lands_on_its_card(tmp_path):
    p = probs(tmp_path, {'alt:20 0': {'status': 'changed', 'value': '  '}})
    assert [(x['card'], x['why'], x['origin']) for x in p['fields']] == [('alt:20 0', 'not a figure or empty alt', 'review')]
    assert p['fields'][0]['fix'].startswith('Write alt text') and not p['conflicts']

def test_a_bad_language_lands_on_the_added_card(tmp_path):
    add = [{'kind': 'document', 'target': 'lang', 'value': 'english'}]
    p = probs(tmp_path, {}, add)
    assert [(x['card'], x['why']) for x in p['fields']] == [('add:document:lang', 'not a BCP 47 language tag')]
    assert 'Other' in p['fields'][0]['fix']
    assert probs(tmp_path, {}, [dict(add[0], value='EN_us')])['fields'] == []      # tidied by the check, not refused

def test_table_headers_both_zero_and_the_same_table_twice(tmp_path):
    p = probs(tmp_path, {'tables:30 0': {'status': 'changed', 'value': {'header_rows': 0, 'header_cols': 0}}})
    assert [(x['card'], x['why']) for x in p['fields']] == [('tables:30 0', 'no header rows or columns')]
    p = probs(tmp_path, {}, [{'kind': 'tables', 'target': '31 0', 'value': {'header_rows': 1, 'header_cols': 0}}] * 2)
    assert [(x['cards'], x['why']) for x in p['conflicts']] == [(['add:tables:31 0'], 'added twice')]

def test_overlapping_moves_are_one_conflict_naming_both_cards(tmp_path):
    p = probs(tmp_path, {'move_section:1': {'status': 'changed', 'value': {'pages': [3, 3], 'before_page': 80}}})
    assert [(x['cards'], x['why']) for x in p['conflicts']] == [(['move_section', 'move_section:1'], 'its pages overlap another section move')]
    assert not p['fields']

def test_a_bad_page_marks_only_its_box(tmp_path):
    p = probs(tmp_path, {'move_section': {'status': 'changed', 'value': {'pages': ['x', 3], 'before_page': 10}}})
    assert [(x['card'], x['why'], x['parts']) for x in p['fields']] == [('move_section', 'bad pages', ['a'])]
    p = probs(tmp_path, {'move_section': {'status': 'changed', 'value': {'pages': [3, 3], 'before_page': 999}}})
    assert p['fields'][0]['parts'] == ['before_page'] and '1 to 80' in p['fields'][0]['fix']

def test_an_untouched_ai_choice_and_an_earlier_one_say_so(tmp_path):
    ai = dict(ai_order(), move_section=[{'pages': [20, 20], 'before_page': 30}])   # nothing out of place there
    p = probs(tmp_path, {}, ai=ai)
    assert [(x['card'], x['origin']) for x in p['fields']] == [('move_section', 'ai')]
    dec = {'alt:20 0': {'status': 'changed', 'value': ''}}
    assert probs(tmp_path, dec, set_in={'alt:20 0': '001'})['fields'][0]['origin'] == 'earlier'

def test_a_drop_no_card_holds_is_left_out(tmp_path):
    ai = dict(ai_order(), deferrals=[{'what': 'a table', 'why': 'unclear', 'pages': [999]}])
    p = probs(tmp_path, {}, ai=ai)
    assert not p['fields'] and not p['conflicts']
    assert [(x['where'], x['why']) for x in p['unplaced']] == [('deferrals.pages', 'not PDF page numbers in range')]

def test_the_order_finish_writes_has_no_card_marks(tmp_path):
    R, ai, items, adds = run(tmp_path)
    add = [{'kind': 'tables', 'target': '31 0', 'value': {'header_rows': 1, 'header_cols': 0}}]
    core.problems(R, ai, items, {}, add, adds, 'Kim')
    wo = core.apply_decisions(ai, items, {}); core.add_entries(wo, add, adds, 'Kim')
    assert '_card' not in json.dumps(wo) and '_card' not in json.dumps(ai)

def test_every_reason_the_check_gives_has_a_fix():
    def whys(src):                                       # the string literals with a space: the reasons ({…} as N)
        out = set()
        for m in re.finditer(r"""f?'((?:[^'\\\n]|\\.)*)'""", src):
            t = m.group(1).replace("\\'", "'")
            if ' ' in t and not t.startswith('page {'): out.add(re.sub(r'\{[^}]*\}', 'N', t))
        return out
    adds = re.search(r'def add_entries.*?return refused', inspect.getsource(core), re.S).group(0)
    found = whys(inspect.getsource(workorder_check.check)) | {w for w in whys(adds) if not w.startswith('added ') or w == 'added twice'}
    assert len(found) > 40 and not [w for w in found if w not in core.FIX]
    assert core.fix('more than 3 section moves', 80) == 'At most 3 sections can be moved. Reject one of the moves.'
    assert core.fix('something new', 80) == 'Something new.'                       # never blank: the reason itself

def test_the_language_list_names_every_tag():
    L = core.languages()
    assert ['en-US', 'English (US)'] in L and ['haw', 'Hawaiian'] in L and [x[1] for x in L] == sorted(x[1] for x in L)

# ------------------------------------------------------------------ the server
def free_port():
    with socket.socket() as s: s.bind(('127.0.0.1', 0)); return s.getsockname()[1]

def test_keep_marks_and_finish_refuses_until_fixed(tmp_path):
    R, ai, items, adds = run(tmp_path)
    core.save(os.path.join(R, 'review_items.json'), {'book': 'book.pdf', 'run': 'run', 'pages': 80, 'pdf': '', 'groups': core.GROUPS,
                                                   'levels': core.LEVELS, 'add_kinds': core.ADD_KINDS, 'items': items, 'addable': adds})
    port = free_port(); out = {}
    t = threading.Thread(target=lambda: out.update(v=__import__('review.server', fromlist=['serve']).serve(R, '2026-11-02', port, open_browser=False)), daemon=True)
    t.start(); up(port)
    def call(path, body=None):
        req = urllib.request.Request(f'http://127.0.0.1:{port}{path}', data=None if body is None else json.dumps(body).encode(),
                                     headers={'Content-Type': 'application/json', 'Host': f'127.0.0.1:{port}'})
        with urllib.request.urlopen(req, timeout=20) as r: return r.read() if body is None else json.loads(r.read())
    assert b'"languages"' in call('/')
    bad = {it['id']: {'status': 'approved'} for it in items}
    bad['alt:20 0'] = {'status': 'changed', 'value': ''}
    b = call('/keep', {'reviewer': 'Kim', 'decisions': bad, 'additions': []})
    assert [x['card'] for x in b['problems']['fields']] == ['alt:20 0'] and 'gaps' in b
    b = call('/save', {'reviewer': 'Kim', 'decisions': bad, 'additions': []})
    assert b['problems']['fields'] and 'dropped' not in b and 'refused' not in b
    b = call('/finish', {'reviewer': 'Kim', 'decisions': bad, 'additions': [], 'accept_unreviewed': True})
    assert b['finished'] is False and b['needs'] == 'invalid' and b['problems']['fields'][0]['card'] == 'alt:20 0'
    assert not os.path.exists(os.path.join(R, 'review.json'))                       # nothing recorded
    good = dict(bad, **{'alt:20 0': {'status': 'changed', 'value': 'A map of Oʻahu'}})
    b = call('/finish', {'reviewer': 'Kim', 'decisions': good, 'additions': [], 'accept_unreviewed': True})
    assert b['finished'] and b['dropped'] == []
    t.join(5)
    assert core.load(os.path.join(R, 'workorder.json'))['alt'][0]['alt'] == 'A map of Oʻahu'
