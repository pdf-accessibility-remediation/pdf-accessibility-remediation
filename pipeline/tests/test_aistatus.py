"""test_aistatus.py: #151 (App: hold the review when AI requests did not finish), lib/aistatus.py.

    python -m pytest tests/test_aistatus.py -q

One "finished" rule read by both name_languages.reusable() (what a retry reuses) and aistatus (what holds the review),
the outcome ranking, and the marker rule for runs made before #151. Synthetic records only: no PDF, no network.
"""
import os, sys, json
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from lib import aistatus  # noqa: E402
import name_languages  # noqa: E402

GOOD = json.dumps({'decisions': [{'id': '1', 'form': 'mappō', 'lang': 'ja-Latn', 'confidence': 'high', 'why': 'language'}]})

def entry(n, sha, finish='stop', text=GOOD, **kw):
    return {'n': n, 'sha256': sha, 'ids': ['1'], 'finish': finish, 'text': text, **kw}

def fixture():
    """Every kind of entry, numbered 1-9, as language_run.json keeps them."""
    return {'estimate': {'requests': 9}, 'requests': [
        entry(1, 'a'),                                                               # finished
        {'n': 2, 'sha256': 'b', 'ids': ['1'], 'error': {'code': 500, 'message': 'x'}},   # failed
        entry(3, 'c', finish='length'), entry(3, 'c2', resend_of=3, resend_of_sha256='c'),          # cut off, its resend finished
        entry(4, 'd', finish='length'), {'n': 4, 'sha256': 'd2', 'resend_of': 4, 'resend_of_sha256': 'd', 'error': {'code': 429}},  # cut off, resend failed
        entry(5, 'e', text='not json at all'),                                       # unreadable (finish 'stop')
        entry(6, 'f', resend='2 undecided forms sent once more'), entry(6, 'f2', resend_of=6, resend_of_sha256='f'),   # partial, resend finished
        entry(7, 'g', resend='2 undecided forms sent once more'), {'n': 7, 'sha256': 'g2', 'resend_of': 7, 'resend_of_sha256': 'g', 'error': {'code': 502}},  # partial, resend failed (24 M1)
        entry(8, 'h', resend='2 undecided forms not sent again: the language step limit has no room for them'),            # partial, resend not sent (24 M1)
        # 9: never came back (in flight when the step stopped): no entry
    ]}

def test_reusable_and_unfinished_agree_on_every_entry():
    run = fixture()
    reused = {e[0]['n'] for e in name_languages.reusable(run).values()}
    left = set(aistatus.language_unfinished(run))
    assert reused == {1, 3, 6} and left == {2, 4, 5, 7, 8, 9}
    assert reused | left == set(range(1, 10)) and not reused & left            # one rule: never both, never neither

def test_a_resend_is_reused_with_its_original():
    pair = name_languages.reusable(fixture())['f']
    assert [x['sha256'] for x in pair] == ['f', 'f2']

def test_a_reply_from_elsewhere_holds_nothing_and_an_own_replay_is_judged_by_its_entries():
    run = fixture()
    assert aistatus.language_unfinished({**run, 'response_from': '/other/run/language_run.json'}) == []
    assert set(aistatus.language_unfinished({**run, 'response_from': '/this/language_run.json', 'own_reply': True})) == {2, 4, 5, 7, 8, 9}

def test_record_keeps_a_refusal_and_saved_never_hides_a_failure(tmp_path):
    R = str(tmp_path); aistatus.create(R)
    aistatus.record(R, 'language', 'book', 'left out')
    assert aistatus.record(R, 'language', 'not_run') == 'book' and aistatus.record(R, 'language', 'saved') == 'book'
    for old in ('done', 'error', 'lookup', 'started'):
        aistatus.record(R, 'pages', old)
        assert aistatus.record(R, 'pages', 'saved') == old and aistatus.outcome(R, 'pages')['why'] == old
    aistatus.record(R, 'language', 'started')                                   # the step itself may run again (a retry)
    assert aistatus.outcome(R, 'language')['why'] == 'started'

def test_run_api_writes_nothing_into_a_folder_made_before_151(tmp_path):
    R = str(tmp_path)
    assert aistatus.record(R, 'language', 'not_run') is None and not os.path.exists(tmp_path / aistatus.NAME)

def write(R, name, d): (R / name).write_text(json.dumps(d))

def test_a_run_made_before_151_is_judged_by_its_entries_alone(tmp_path):
    """review 24 M4 (runs/dakine/mmmm's shape): waiting for review, an estimate with requests to send, every request
    finished, no ai_outcome.json: not held. One entry changed to an error: held."""
    R = tmp_path; (R / '_audit').mkdir()
    write(R, 'language_estimate.json', {'to_send': 7, 'requests': 7})
    run = {'estimate': {'requests': 7}, 'requests': [entry(i, f's{i}') for i in range(1, 8)]}
    write(R, 'language_run.json', run)
    s = aistatus.status(str(R))
    assert not s['marker'] and not s['held']
    run['requests'][3] = {'n': 4, 'sha256': 's4', 'ids': ['1'], 'error': {'code': 500}}
    write(R, 'language_run.json', run)
    s = aistatus.status(str(R))
    assert s['held'] and s['steps']['language']['count'] == 1 and aistatus.retry_parts(s) == 'language'

def test_a_step_expected_but_never_recorded_holds_only_with_the_marker(tmp_path):
    R = tmp_path; (R / '_audit').mkdir()
    write(R, 'language_estimate.json', {'to_send': 3, 'requests': 3})
    assert not aistatus.status(str(R))['held']                                  # no marker: nothing to go on
    aistatus.create(str(R))
    s = aistatus.status(str(R))
    assert s['held'] and s['steps']['language']['state'] == 'unfinished'

def test_left_out_holds_with_no_retry_and_credit_offers_one(tmp_path):
    R = tmp_path; (R / '_audit').mkdir(); aistatus.create(str(R))
    aistatus.record(str(R), 'language', 'cap', aistatus.WORDS['cap']['language'])
    s = aistatus.status(str(R))
    assert s['held'] and s['steps']['language']['state'] == 'left_out' and aistatus.retry_parts(s) is None
    assert aistatus.lines(s)[0].startswith('Language Suggestions Not Made: The language suggestions were left out')
    aistatus.record(str(R), 'language', 'credit')
    write(R, 'language_estimate.json', {'to_send': 2})
    s = aistatus.status(str(R))
    assert s['steps']['language']['retry'] and aistatus.retry_parts(s) == 'language'

def test_pages_come_first_and_an_override_clears_the_hold(tmp_path):
    R = tmp_path; A = R / '_audit'; A.mkdir(); aistatus.create(str(R))
    write(A, 'page_reads.json', {'pages': [{'page': 3}, {'page': 5}]})
    write(R, 'page_reads_run.json', {'pages': [{'page': 3, 'text': 'Ua hele', 'finish': 'stop'}, {'page': 5, 'error': {'code': 500}}]})
    aistatus.record(str(R), 'pages', 'done')
    aistatus.record(str(R), 'language', 'error', aistatus.WORDS['error'])
    s = aistatus.status(str(R))
    assert s['steps']['pages']['count'] == 1 and aistatus.retry_parts(s) == 'pages'       # two parts: the pages first (25 §2.4)
    d = aistatus.set_override(str(R), 'Kim', '2026-11-18')
    assert d['by'] == 'Kim' and len(d['missing']) == 2 and not aistatus.status(str(R))['held']

def test_the_command_line(tmp_path):
    import subprocess
    R = tmp_path; (R / '_audit').mkdir()
    def cli(*a): return subprocess.run([sys.executable, '-m', 'lib.aistatus', *a], cwd=HERE, capture_output=True, text=True)
    assert cli('create', str(R)).returncode == 0
    write(R, 'language_estimate.json', {'to_send': 4, 'refused': {'why': 'book', 'words': 'Left out of this PDF.'}})
    r = cli('refused', str(R), 'language', str(R / 'language_estimate.json'))
    assert r.returncode == 0 and r.stdout.strip() == 'Left out of this PDF.' and aistatus.outcome(str(R), 'language')['why'] == 'book'
    assert cli('held', str(R)).returncode == 0
    write(R, 'page_reads_estimate.json', {'to_read': 2})
    assert cli('refused', str(R), 'pages', str(R / 'page_reads_estimate.json')).returncode == 1          # no refusal: nothing recorded

def test_an_unreadable_reply_gives_its_own_no_answer_code():
    """review 22 M3: a reply that can't be read at all is `unreadable` for each of its forms; one read only in pieces stays
    `invalid`; workorder_check keeps the code (one list: langreq.NO_ANSWER)."""
    from lib import langreq, workorder_check
    assert langreq.no_answer(['1', '2'], [{'id': None, 'code': 'unreadable'}]) == {'1': 'unreadable', '2': 'unreadable'}
    assert langreq.no_answer(['1'], [{'id': None, 'code': 'unreadable'}, {'id': None, 'code': 'partial'}]) == {'1': 'invalid'}
    assert workorder_check.NO_ANSWER is langreq.NO_ANSWER and 'unreadable' in workorder_check.NO_ANSWER
