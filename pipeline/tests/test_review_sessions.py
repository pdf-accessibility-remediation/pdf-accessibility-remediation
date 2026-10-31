"""test_review_sessions.py: the review loop's records (review/sessions.py), on a synthetic digest and work order. No PDF
is rendered and no model is called.

    python -m pytest tests/test_review_sessions.py -q

What is tested: choices carried only onto the same decision; a review made before sessions were kept rebuilt per card only
when the rebuilt order gives exactly the recorded changes and counts; the basis refusals; a finished session's record
(who set each choice); promotion of a new result (and completing an interrupted one); the lock; ready to ship while a
finished session waits to be applied; the server's /save and /finish in a reviews/ folder; and that two runs of the
same input get different browser-draft keys.
"""
import os, json, copy, threading, time, urllib.request, socket
import pytest
from review import core, sessions as S

def digest():
    return {'source': {'pages': 5, 'file': 'book.pdf', 'sha256': 'f' * 64},
            'elements': [{'obj': '10 0 R', 'text': 'Introduction', 'page': 1, 'style': 'P'},
                         {'obj': '12 0 R', 'text': 'Chapter one', 'page': 2, 'style': 'P'}],
            'headings': [{'obj': '11 0 R', 'text': 'The Book', 'page': 1, 'style': 'Title', 'level': 'H1'}],
            'heading_candidates': [], 'lists': [], 'tables': [],
            'figures': [{'obj': '20 0 R', 'page': 2, 'alt': None, 'image': None}, {'obj': '21 0 R', 'page': 3, 'alt': None, 'image': None}],
            'styles': [{'style': 'Title', 'count': 1, 'pages': [1, 1], 'maps_to': 'H1'}, {'style': 'P', 'count': 40, 'pages': [1, 5], 'maps_to': 'P'}]}

def ai_order():
    return {'source': {'file': 'book.pdf', 'sha256': 'f' * 64}, 'decided_by': 'model via OpenRouter · prompt workorder_v8.md (abc)',
            'retype': [{'obj': '10 0 R', 'type': 'H2', 'why': 'a section head'}, {'obj': '12 0 R', 'type': 'H2', 'why': 'a chapter'}],
            'alt': [{'obj': '20 0 R', 'alt': 'A map of the island', 'why': 'informative'}],
            'document': {'title': 'The Book'},
            'deferrals': [{'what': 'a table on PDF 4', 'why': 'unclear headers', 'pages': [4]}]}

def review(ai, dg, decisions, additions=(), reviewer='Pat'):
    """What review/core.py's finish records for these choices: the final order, its changes and counts."""
    items = core.build_items(ai, dg)
    wo = core.apply_decisions(ai, items, decisions)
    assert not core.add_entries(wo, list(additions), core.addable(ai, dg), reviewer)
    from lib import workorder_check
    workorder_check.check(wo, dg, set(), set())
    st = [core._status(it, decisions.get(it['id'])) for it in items]
    counts = {s: st.count(s) for s in ('approved', 'changed', 'rejected', 'seen', 'accepted_unreviewed')}
    if additions: counts['added'] = len(additions)
    wo['reviewed_by'] = f'{reviewer} on 2026-10-20'
    return wo, {'reviewer': reviewer, 'date': '2026-10-20', 'method': 'page', 'changes': core.diff(ai, wo), 'counts': counts,
                'dropped_on_check': []}

ALL = {'retype:10 0 R': {'status': 'approved'}, 'retype:12 0 R': {'status': 'approved'}, 'alt:20 0 R': {'status': 'approved'},
       'document.title': {'status': 'approved'}, 'deferrals:0': {'status': 'seen'}}

# ------------------------------------------------------------------ carrying choices
def test_carry_same_id_same_ai_only():
    items = core.build_items(ai_order(), digest())
    src = {'retype:10 0 R': {'status': 'changed', 'value': 'H3', 'ai': 'H2', 'set_in': '001'},
           'retype:12 0 R': {'status': 'approved', 'ai': 'H1', 'set_in': '001'},           # the AI value differs now
           'alt:99 0 R': {'status': 'approved', 'ai': 'x', 'set_in': '001'}}               # no such decision
    carried, missed = S.carry(items, src)
    assert list(carried) == ['retype:10 0 R']
    assert {m['id'] for m in missed} == {'retype:12 0 R', 'alt:99 0 R'}

# ------------------------------------------------------------------ a review recorded before sessions were kept
def test_summary_with_changes_is_rebuilt_per_card():
    ai, dg = ai_order(), digest()
    dec = dict(ALL, **{'retype:10 0 R': {'status': 'changed', 'value': 'H3'}, 'alt:20 0 R': {'status': 'rejected'}})
    adds = [{'kind': 'alt', 'target': '21 0 R', 'value': 'A photograph of the harbour'}]
    final, rv = review(ai, dg, dec, adds)
    got = S.from_summary(ai, final, rv, dg)
    assert got is not None
    d, a = got
    assert {k: v['status'] for k, v in d.items()} == {k: v['status'] for k, v in dec.items()}
    assert d['retype:10 0 R']['value'] == 'H3'
    assert a == adds

def test_summary_with_unreviewed_items_stays_summary_only():
    ai, dg = ai_order(), digest()
    dec = dict(ALL); dec.pop('retype:12 0 R')
    final, rv = review(ai, dg, dec)
    assert rv['counts']['accepted_unreviewed'] == 1
    assert S.from_summary(ai, final, rv, dg) is None

def test_summary_whose_counts_do_not_match_stays_summary_only():
    ai, dg = ai_order(), digest()
    final, rv = review(ai, dg, ALL)
    rv['counts'] = dict(rv['counts'], approved=rv['counts']['approved'] - 1, rejected=1)   # recorded counts the order cannot give
    assert S.from_summary(ai, final, rv, dg) is None

def test_summary_whose_changes_do_not_match_stays_summary_only():
    ai, dg = ai_order(), digest()
    final, rv = review(ai, dg, ALL)
    rv['changes'] = [{'where': 'retype', 'id': 'obj 10 0 R', 'change': 'changed', 'ai': {'type': 'H2'}, 'person': {'type': 'H4'}}]
    assert S.from_summary(ai, final, rv, dg) is None

def test_summary_text_wording():
    s = {'id': '001', 'review': {'counts': {'approved': 159, 'changed': 0, 'rejected': 0, 'seen': 8, 'accepted_unreviewed': 0}, 'changes': []}}
    t = S.summary_text(s)
    assert t.startswith('Session 1 (summary only): 159 approved, 8 seen, no changes; per-decision choices were not recorded before ')
    assert 'legacy' not in t

# ------------------------------------------------------------------ a run folder
def run_folder(tmp_path, reviewed=False):
    """A finished run with reviews/ kept: record.json, a remediated 'PDF', the input file and the basis."""
    R = tmp_path / 'run'; R.mkdir()
    (R / '_intake').mkdir()
    inp = R / '_intake' / 'intake.pdf'; inp.write_bytes(b'%PDF-1.7 synthetic input')
    dg = digest(); dg['source']['sha256'] = S.sha_file(str(inp))
    ai = ai_order(); ai['source']['sha256'] = dg['source']['sha256']
    os.makedirs(R / 'reviews' / '_audit')
    S.save(str(R / 'reviews' / '_audit' / 'digest.json'), dg)
    rec = {'schema': 'record/0.1', 'written': '2026-10-20T10:00:00', 'document': {'file': 'book.pdf', 'output': 'book_remediated.pdf'},
           'intake': {'result': {'pdf': 'intake.pdf'}}, 'workorder': ai,
           'run': {'digest_sha256': S.sha_file(str(R / 'reviews' / '_audit' / 'digest.json'))[:16], 'model': 'm', 'prompt_file': 'workorder_v8.md',
                   'prompt_sha256': 'abc', 'usage': {'cost_usd': 0.25}}, 'cost_total_usd': 0.25}
    S.save(str(R / 'record.json'), rec)
    (R / 'book_remediated.pdf').write_bytes(b'old result'); (R / 'review.md').write_text('old review'); (R / 'review.html').write_text('<p>old</p>')
    b = S.new_basis(str(R), str(inp), S.sha_file(str(inp)), str(R / 'reviews' / '_audit' / 'digest.json'), ai, 'test')
    S.save(S.P(str(R))['basis'], b)
    return str(R), rec, ai, dg

def test_basis_check_passes_and_refuses(tmp_path):
    R, rec, ai, dg = run_folder(tmp_path)
    b, inp, got = S.check_basis(R, rec)
    assert got == ai and os.path.exists(S.P(R)['ai'])
    # the kept digest edited: refused
    d2 = copy.deepcopy(dg); d2['elements'][0]['text'] = 'Changed'
    S.save(os.path.join(S.P(R)['audit'], 'digest.json'), d2)
    with pytest.raises(S.Refused, match='not the one the AI decided on'): S.check_basis(R, rec)
    S.save(os.path.join(S.P(R)['audit'], 'digest.json'), dg)
    # the AI order changed: refused
    ai2 = copy.deepcopy(ai); ai2['retype'][0]['type'] = 'H3'; S.save(S.P(R)['ai'], ai2)
    with pytest.raises(S.Refused, match='not the one the basis recorded'): S.check_basis(R, rec)
    S.save(S.P(R)['ai'], ai)
    # the input changed: refused
    with open(os.path.join(R, '_intake', 'intake.pdf'), 'ab') as f: f.write(b' edited')
    with pytest.raises(S.Refused, match='not the file this run worked on'): S.check_basis(R, rec)

def test_record_fingerprint_must_match_too(tmp_path):
    R, rec, ai, dg = run_folder(tmp_path)
    rec2 = dict(rec, run=dict(rec['run'], digest_sha256='0' * 16))
    with pytest.raises(S.Refused, match='not the one the AI decided on'): S.check_basis(R, rec2)

def test_two_runs_of_the_same_input_get_different_draft_keys(tmp_path):
    (tmp_path / 'a').mkdir(); (tmp_path / 'b').mkdir()
    R1, rec1, ai, dg = run_folder(tmp_path / 'a'); R2, rec2, _, _ = run_folder(tmp_path / 'b')
    assert S.basis(R1)['digest_sha256'] == S.basis(R2)['digest_sha256']
    assert S.basis(R1)['run_id'] != S.basis(R2)['run_id']

# ------------------------------------------------------------------ finishing a session
def test_finish_session_records_who_set_each_choice(tmp_path):
    R, rec, ai, dg = run_folder(tmp_path)
    S.check_basis(R, rec)
    p = S.P(R); items = core.build_items(ai, dg)
    S.save(p['items'], {'items': items})
    start = {k: dict(v, ai=next(it['ai'] for it in items if it['id'] == k), set_in='001') for k, v in ALL.items()}
    s = {'id': '002', 'from': '001', 'status': 'open', 'start': start, 'start_additions': []}
    now = dict(ALL, **{'retype:12 0 R': {'status': 'changed', 'value': 'H3'}})
    S.save(p['draft'], {'reviewer': 'Kim', 'decisions': now, 'additions': []})
    wo = core.apply_decisions(ai, items, now); S.save(os.path.join(p['dir'], 'workorder.json'), wo)
    S.save(os.path.join(p['dir'], 'review.json'), {'reviewer': 'Kim', 'date': '2026-10-27', 'method': 'page', 'changes': core.diff(ai, wo)})
    os.makedirs(p['sessions'], exist_ok=True)
    s = S.finish_session(R, s, rec)
    assert s['status'] == 'finished' and s['reviewer'] == 'Kim'
    assert s['decisions']['retype:12 0 R']['set_in'] == '002'
    assert s['decisions']['retype:10 0 R']['set_in'] == '001'
    assert s['carried'] == 4
    assert [x['id'] for x in s['since_start']] == ['retype:12 0 R']
    assert os.path.exists(os.path.join(p['sessions'], '002.workorder.json'))
    assert not os.path.exists(p['draft']) and not os.path.exists(p['items'])
    row = S.summary_row(s)
    assert row['carried'] == 4 and row['since_start'] == 1

# ------------------------------------------------------------------ promotion
def test_promote_moves_the_old_result_and_keeps_a_record_at_the_top(tmp_path):
    R, rec, ai, dg = run_folder(tmp_path)
    W = S.P(R)['work']; os.makedirs(W)
    new = dict(rec, review={'workorder': {'reviewer': 'Kim'}, 'session': '002'})
    S.save(os.path.join(W, 'record.json'), new)
    for n, t in (('book_remediated.pdf', 'new result'), ('review.md', 'new review'), ('review.html', '<p>new</p>')):
        open(os.path.join(W, n), 'w').write(t)
    S.promote(R, '002', 'book_remediated.pdf', say=lambda *a: None)
    V = os.path.join(S.P(R)['versions'], 'ai')
    assert open(os.path.join(V, 'book_remediated.pdf')).read() == 'old result'
    assert open(os.path.join(V, 'review.md')).read() == 'old review'
    assert S.load(os.path.join(V, 'record.json')) == rec                  # the replaced record, as it was
    assert open(os.path.join(R, 'book_remediated.pdf')).read() == 'new result'
    assert S.load(os.path.join(R, 'record.json'))['review']['session'] == '002'
    assert not os.path.exists(S.P(R)['promoting']) and not os.path.exists(W)

def test_an_interrupted_promotion_is_completed(tmp_path):
    R, rec, ai, dg = run_folder(tmp_path)
    W = S.P(R)['work']; os.makedirs(W)
    S.save(os.path.join(W, 'record.json'), dict(rec, written='new'))
    open(os.path.join(W, 'book_remediated.pdf'), 'w').write('new result')
    V = os.path.join(S.P(R)['versions'], 'ai'); os.makedirs(V)          # crashed after saving the old record
    S.save(os.path.join(V, 'record.json'), rec)
    S.save(S.P(R)['promoting'], {'to': '002', 'from': 'ai', 'out': 'book_remediated.pdf', 'stage': 'save old'})
    assert os.path.exists(os.path.join(R, 'record.json'))
    S.promote(R, None, None, say=lambda *a: None)
    assert S.load(os.path.join(R, 'record.json'))['written'] == 'new'
    assert open(os.path.join(V, 'book_remediated.pdf')).read() == 'old result'

# ------------------------------------------------------------------ the lock
def test_lock_refuses_a_second_review_and_takes_over_a_dead_one(tmp_path):
    R, rec, ai, dg = run_folder(tmp_path)
    with S.Lock(R, 'reopen'):
        with pytest.raises(S.Refused, match='another review'): S.Lock(R, 'apply')
    S.save(S.P(R)['lock'], {'pid': 999999, 'since': 'then', 'what': 'reopen'})   # a process that has ended
    S.Lock(R, 'apply').release()
    assert not os.path.exists(S.P(R)['lock'])

# ------------------------------------------------------------------ ready to ship
def test_finished_but_not_applied_is_not_ready():
    from lib import glance as G
    rec = {'workorder': ai_order(), 'review': {'workorder': {'reviewer': 'Pat', 'date': '2026-10-20', 'method': 'page', 'counts': {'approved': 5}},
                                               'pending': {'session': '003', 'status': 'finished', 'reviewer': 'Kim'}},
           'sections': [], 'apply': {}, 'verify': {}}
    g = G.glance(rec, None, {}, [], sections=[])
    assert g['ship'][0]['ok'] is False and 'session 3' in g['ship'][0]['text'] and 'not applied' in g['ship'][0]['text']
    rec['review']['pending']['status'] = 'open'                              # an open draft changes nothing
    assert G.glance(rec, None, {}, [], sections=[])['ship'][0]['ok'] is True

# ------------------------------------------------------------------ the server in a reviews/ folder
def free_port():
    with socket.socket() as s: s.bind(('127.0.0.1', 0)); return s.getsockname()[1]

def test_server_save_and_finish_in_a_reviews_folder(tmp_path):
    R, rec, ai, dg = run_folder(tmp_path)
    S.check_basis(R, rec)
    p = S.P(R); items = core.build_items(ai, dg)
    S.save(p['items'], {'book': 'book.pdf', 'run': 'run', 'pages': 5, 'pdf': '', 'groups': core.GROUPS, 'levels': core.LEVELS,
                        'add_kinds': core.ADD_KINDS, 'items': items, 'addable': core.addable(ai, dg),
                        'session': {'key': 'abc:002', 'id': '002', 'reopened': True}})
    S.save(p['draft'], {'reviewer': '', 'decisions': ALL, 'additions': []})
    port = free_port(); out = {}
    t = threading.Thread(target=lambda: out.update(v=__import__('review.server', fromlist=['serve']).serve(
        p['dir'], '2026-10-27', port, open_browser=False, files={'/result/review.html': os.path.join(R, 'review.html')})), daemon=True)
    t.start(); time.sleep(0.8)
    def call(path, body=None):
        req = urllib.request.Request(f'http://127.0.0.1:{port}{path}', data=None if body is None else json.dumps(body).encode(),
                                     headers={'Content-Type': 'application/json', 'Host': f'127.0.0.1:{port}'})
        with urllib.request.urlopen(req) as r: return r.read()
    assert b'old' in call('/result/review.html')
    assert b'abc:002' in call('/')
    dec = dict(ALL, **{'alt:20 0 R': {'status': 'changed', 'value': 'A map of Oʻahu'}})
    assert json.loads(call('/save', {'reviewer': 'Kim', 'decisions': dec, 'additions': []}))['changes'] == 1
    r = json.loads(call('/finish', {'reviewer': 'Kim', 'decisions': dec, 'additions': [], 'gaps_ack': {'figures_without_alt': 'drawn later'}}))
    assert r['finished'] and r['changes'] == 1
    t.join(5)
    assert out['v']['reviewer'] == 'Kim'
    assert S.load(os.path.join(p['dir'], 'workorder.json'))['alt'][0]['alt'] == 'A map of Oʻahu'

# ------------------------------------------------------------------ digests this version cannot read, and KEEP=1 review runs
def test_a_digest_the_review_step_cannot_read_is_refused(tmp_path):
    R, rec, ai, dg = run_folder(tmp_path)
    bad = copy.deepcopy(dg); del bad['source']                              # e.g. a digest schema change
    S.save(os.path.join(S.P(R)['audit'], 'digest.json'), bad)
    b = S.basis(R); b['digest_sha256'] = S.sha_file(os.path.join(S.P(R)['audit'], 'digest.json'))[:16]; S.save(S.P(R)['basis'], b)
    rec = dict(rec, run=dict(rec['run'], digest_sha256=b['digest_sha256']))
    with S.Lock(R, 'reopen'):
        with pytest.raises(S.Refused, match='cannot be read by this version'): S.open_session(R, rec, say=lambda *a: None)
    assert not os.path.exists(S.P(R)['lock'])
    assert sorted(os.listdir(S.P(R)['dir'])) == ['_audit', 'basis.json', 'workorder.ai.json']   # no session, no review files

def test_pin_keeps_the_run_id_of_a_basis_without_a_digest(tmp_path, monkeypatch):
    R, rec, ai, dg = run_folder(tmp_path)
    run_id = S.basis(R)['run_id']
    os.remove(os.path.join(S.P(R)['audit'], 'digest.json'))               # a KEEP=1 review run: basis written, digest not kept
    def fake_audit(inp, out):
        os.makedirs(out, exist_ok=True); S.save(os.path.join(out, 'digest.json'), dg)
        S.save(os.path.join(out, 'fulltext.json'), {'elements': {'10 0 R': 'Introduction, in full'}})
    monkeypatch.setattr(S, 'reaudit', fake_audit)
    assert S.pin(R, say=lambda *a: None) == 'pinned'
    assert S.basis(R)['run_id'] == run_id and os.path.exists(os.path.join(S.P(R)['audit'], 'digest.json'))
    assert os.path.exists(os.path.join(S.P(R)['audit'], 'fulltext.json'))           # --pin keeps fulltext.json too
    assert S.pin(R, say=lambda *a: None) == 'already pinned'

def files_of(R):
    """Every file under R with its sha256: what a top-up may and may not change."""
    out = {}
    for d, _, fs in os.walk(R):
        for f in fs: out[os.path.relpath(os.path.join(d, f), R)] = S.sha_file(os.path.join(d, f))
    return out

def test_top_up_adds_only_fulltext_and_a_second_run_changes_nothing(tmp_path, monkeypatch):
    R, rec, ai, dg = run_folder(tmp_path)                                           # pinned before --pin kept fulltext.json
    kept = open(os.path.join(S.P(R)['audit'], 'digest.json'), 'rb').read()
    def fake_audit(inp, out):                                                        # today's audit: the same digest, byte for byte
        os.makedirs(out, exist_ok=True); open(os.path.join(out, 'digest.json'), 'wb').write(kept)
        S.save(os.path.join(out, 'fulltext.json'), {'elements': {'10 0 R': 'Introduction, in full'}})
    monkeypatch.setattr(S, 'reaudit', fake_audit)
    before = files_of(R)
    assert S.pin(R, say=lambda *a: None) == 'already pinned; fulltext.json added'
    after = files_of(R)
    assert set(after) - set(before) == {os.path.join('reviews', '_audit', 'fulltext.json')}
    assert all(after[k] == v for k, v in before.items())                             # nothing else changed
    assert S.pin(R, say=lambda *a: None) == 'already pinned'
    assert files_of(R) == after                                                      # a second run changes nothing

def test_top_up_keeps_nothing_when_the_audit_does_not_reproduce(tmp_path, monkeypatch):
    R, rec, ai, dg = run_folder(tmp_path)
    def fake_audit(inp, out):                                                        # today's audit differs from the kept digest
        os.makedirs(out, exist_ok=True); S.save(os.path.join(out, 'digest.json'), dict(dg, changed=True))
        S.save(os.path.join(out, 'fulltext.json'), {'elements': {}})
    monkeypatch.setattr(S, 'reaudit', fake_audit)
    before = files_of(R)
    assert 'does not reproduce' in S.pin(R, say=lambda *a: None)
    assert files_of(R) == before

# ------------------------------------------------------------------ the fallback for a run that can no longer be reviewed
def test_replay_to_copies_intake_and_reply_with_its_meta(tmp_path):
    R, rec, ai, dg = run_folder(tmp_path)
    rec = dict(rec, raw_reply='{"retype": []}', intake={'result': {'pdf': 'intake.pdf'}})
    rec['run'] = dict(rec['run'], temperature=0, ocr_words={'fingerprint': 'abc123', 'sent': 2, 'list': {'1': 'Maiiana', '2': 'Kaimuki'}})
    S.save(os.path.join(R, 'record.json'), rec)
    S.save(os.path.join(R, '_intake', 'intake.json'), {'status': 'done'})
    D = str(tmp_path / 'new')
    reply, cmd = S.replay_to(R, D)
    assert open(reply, encoding='utf-8').read() == '{"retype": []}' and reply == D + '.reply.txt'
    assert sorted(os.listdir(os.path.join(D, '_intake'))) == ['intake.json', 'intake.pdf']
    meta = S.load(reply + '.meta.json')
    assert meta['model'] == 'm' and meta['temperature'] == 0
    assert meta['ocr_words_fingerprint'] == 'abc123' and meta['ocr_words_sent'] == 2        # the list the reply was written for
    assert 'INTAKE_REUSE=1' in cmd and f'RUN_DIR={D}' in cmd and 'REVIEW=1' in cmd
    with pytest.raises(S.Refused, match='not empty'): S.replay_to(R, D)                     # never into a used folder

def test_refusals_name_the_fallback(tmp_path):
    R, rec, ai, dg = run_folder(tmp_path)
    rec2 = dict(rec, run=dict(rec['run'], digest_sha256='0' * 16))
    with pytest.raises(S.Refused, match='--replay-to'): S.check_basis(R, rec2)
    with pytest.raises(S.Refused, match='--replay-to'): S.readable(lambda: {}['x'])

# ------------------------------------------------------------------ session names and notes (#47)
def test_name_and_notes_are_cleaned_and_limited():
    bidi = ''.join(chr(c) for c in (0x202a, 0x202e, 0x2066, 0x2069))
    assert core.clean_text(f'a{bidi}b\r\nc\x07‍d‌  ') == 'ab\nc‍d‌'          # ZWJ and ZWNJ stay
    assert core.clean_text(' two\n lines\t', one_line=True) == 'two lines'
    for n in ('Session 5', ' session  5 ', 'SESSION 5', ''):                                     # up to case and spacing: no name
        assert core.session_fields({'session_name': n}, '005') == (None, None)
    assert core.session_fields({'session_name': 'Session 4'}, '005')[0] == 'Session 4'         # another number is a name
    astral = '𠀀' * 80                                                                           # 80 code points, 160 UTF-16 units
    assert core.session_fields({'session_name': astral}, '001')[0] == astral
    with pytest.raises(ValueError, match='at most 80'): core.session_fields({'session_name': astral + 'x'}, '001')
    assert core.session_fields({'session_notes': 'n' * 4000}, '001')[1] == 'n' * 4000
    with pytest.raises(ValueError, match='at most 4,000'): core.session_fields({'session_notes': 'n' * 4001}, '001')
    assert S.name_notes({'session_name': 'x' * 81}, '001') == {}                                # a hand-written draft over the limit: nothing kept

def test_finish_and_abandon_keep_the_name_and_notes(tmp_path):
    R, rec, ai, dg = run_folder(tmp_path)
    S.check_basis(R, rec)
    p = S.P(R); items = core.build_items(ai, dg); os.makedirs(p['sessions'], exist_ok=True)
    S.save(p['items'], {'items': items})
    S.save(p['draft'], {'reviewer': 'Kim', 'decisions': ALL, 'additions': [], 'session_name': 'Chapters 1–4', 'session_notes': 'Stopped at PDF 40.\nCheck the maps.'})
    wo = core.apply_decisions(ai, items, ALL); S.save(os.path.join(p['dir'], 'workorder.json'), wo)
    S.save(os.path.join(p['dir'], 'review.json'), {'reviewer': 'Kim', 'date': '2026-10-31', 'method': 'page', 'changes': []})
    s = S.finish_session(R, {'id': '002', 'from': 'ai', 'status': 'open', 'start': {}, 'start_additions': []}, rec)
    assert (s['name'], s['notes']) == ('Chapters 1–4', 'Stopped at PDF 40.\nCheck the maps.')
    assert 'session_name' not in json.dumps(S.load(os.path.join(p['sessions'], '002.workorder.json')))   # never in the order
    assert 'Chapters' not in json.dumps(s['review'])                                                   # nor in review.json
    row = S.summary_row(s); assert (row['name'], row['notes']) == ('Chapters 1–4', 'Stopped at PDF 40.\nCheck the maps.')
    # an open session discarded: its name and notes stay with it
    S.save(p['draft'], {'reviewer': 'Lee', 'decisions': {}, 'additions': [], 'session_name': 'Session 3', 'session_notes': 'half done'})
    s3 = {'id': '003', 'from': '002', 'status': 'open'}; S.save_session(R, s3)
    S.abandon(R, s3, say=lambda *a: None)
    kept = S.session(R, '003')
    assert kept['status'] == 'abandoned' and kept['notes'] == 'half done' and 'name' not in kept    # "Session 3" is no name

def test_report_shows_names_and_notes_as_text(tmp_path):
    import report_html as H
    ss = [{'id': '001', 'from': 'ai', 'status': 'applied', 'reviewer': 'Kim', 'date': '2026-10-28', 'counts': {'approved': 5},
           'name': '<script>alert(1)</script>', 'notes': '[x](javascript:alert(1))\nline two'},
          {'id': '002', 'from': '001', 'status': 'applied', 'reviewer': 'Lee', 'date': '2026-10-29', 'counts': {'approved': 5}}]
    out = ''.join(H.review_card(str(tmp_path), {'review': {'session': '001', 'sessions': ss}}))
    assert '<script>' not in out and 'href="javascript' not in out
    assert '<strong>Session 1: &lt;script&gt;alert(1)&lt;/script&gt;</strong>' in out
    assert '<summary>Session Notes</summary><div class="pre">[x](javascript:alert(1))\nline two</div>' in out
    assert 'Session 2</strong>' not in out and '<td><span class="nowrap">2</span></td>' in out    # no name: the number alone

def test_keep_and_save_together_never_cut_the_draft(tmp_path):
    R, rec, ai, dg = run_folder(tmp_path)
    S.check_basis(R, rec)
    p = S.P(R); items = core.build_items(ai, dg)
    S.save(p['items'], {'book': 'book.pdf', 'run': 'run', 'pages': 5, 'pdf': '', 'groups': core.GROUPS, 'levels': core.LEVELS,
                        'add_kinds': core.ADD_KINDS, 'items': items, 'addable': core.addable(ai, dg),
                        'session': {'key': 'abc:002', 'id': '002', 'reopened': True, 'name_default': 'Session 2'}})
    port = free_port(); out = {}
    t = threading.Thread(target=lambda: out.update(v=__import__('review.server', fromlist=['serve']).serve(
        p['dir'], '2026-10-31', port, open_browser=False)), daemon=True)
    t.start(); time.sleep(0.8)
    def call(path, body):
        req = urllib.request.Request(f'http://127.0.0.1:{port}{path}', data=json.dumps(body).encode(),
                                     headers={'Content-Type': 'application/json', 'Host': f'127.0.0.1:{port}'})
        try:
            with urllib.request.urlopen(req) as r: return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e: return e.code, json.loads(e.read())
        except OSError: return None, None                                  # the server stopped after Finish
    base = {'reviewer': 'Kim', 'decisions': ALL, 'additions': []}
    assert call('/save', dict(base, session_notes='n' * 4001))[0] == 400
    errs = []
    def hammer(path, i):
        st, b = call(path, dict(base, session_name=f'pass {i}', session_notes='x' * 3000))
        if st not in (200, 409): errs.append((path, st, b))
        S.load(p['draft'])                                                 # parses at every moment: never cut short
    for wave in range(6):                                                  # 4 at a time: the server's listen queue is 5
        th = [threading.Thread(target=hammer, args=(('/keep', '/save')[i % 2], wave * 4 + i)) for i in range(4)]
        for x in th: x.start()
        for x in th: x.join()
    assert not errs and S.load(p['draft'])['session_notes'] == 'x' * 3000
    assert not [n for n in os.listdir(p['dir']) if n.endswith('.tmp')]
    # Finish with Keeps racing it: every Keep is kept before Finish or refused after, so the draft is Finish's
    fin = dict(base, session_name='final', session_notes='done', gaps_ack={'figures_without_alt': 'drawn later'})
    th = [threading.Thread(target=hammer, args=('/keep', i)) for i in range(6)]
    for x in th[:3]: x.start()
    st, b = call('/finish', fin)
    for x in th[3:]: x.start()                                             # after Finish: refused, or the server has stopped
    for x in th: x.join()
    t.join(5)
    assert st == 200 and b['finished'] and not [e for e in errs if e[1] is not None]
    assert S.load(p['draft'])['session_name'] == 'final' and S.load(p['draft'])['session_notes'] == 'done'
