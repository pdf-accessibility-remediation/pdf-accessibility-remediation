"""test_prune.py: "Remove Older PDFs" (review/prune.py; 17 §F, review 18 K7–K9): what it removes and never removes, its
refusals, its trail and the note on the version's page, the app's POST and the command line's dry run. Synthetic runs.

    python -m pytest tests/test_prune.py -q
"""
import os, sys, json, shutil, subprocess
import pytest
import pikepdf
from lib import release as REL
from review import core, prune, sessions as S
from test_webapp import setup, wait, free_port  # noqa: F401  (fixtures)
from test_webapp_checks import mapp, make_run, req, js, RUN, PAC  # noqa: F401

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def add_version(R, vid, title):
    V = os.path.join(R, 'reviews', 'versions', vid); os.makedirs(V)
    doc = pikepdf.new(); doc.add_blank_page(page_size=(200, 200)); doc.docinfo['/Title'] = title; doc.save(os.path.join(V, 'clans_remediated.pdf'))
    core.save(os.path.join(V, 'record.json'), {'document': {'file': 'clans.pdf', 'output': 'clans_remediated.pdf'}})
    open(os.path.join(V, 'review.md'), 'w').write('# old\n')
    return V

def chk(sha): return {'id': 1, 'recorded': '2026-11-01T10:00:00', 'by': 'K', 'pdf': {'sha256': sha, 'which': 'current'}, 'items': {}}

def test_the_plan_never_takes_the_ai_version_an_evaluated_or_a_shipped_one(tmp_path):
    R = make_run(str(tmp_path / 'r'), record_sha=True)
    for vid in ('ai', '001', '002', '003', '004'): add_version(R, vid, f'version {vid}')
    sha = lambda v: REL.sha_file(os.path.join(R, 'reviews', 'versions', v, 'clans_remediated.pdf'))
    os.makedirs(os.path.join(R, 'release'))
    core.save(os.path.join(R, 'release', 'checks.json'), {'schema': REL.SCHEMA, 'pac': [chk(sha('002'))], 'screen_reader': []})
    core.save(os.path.join(R, 'release', 'shipped.json'), [{'n': 1, 'shipped': 'x', 'pdf': {'sha256': sha('003')}, 'withdrawn': {'by': 'L'}}])
    plan = prune.plan(R)
    assert [x['id'] for x in plan] == ['001', '004']                                  # not ai (K9), not evaluated, not shipped (even withdrawn)
    assert all(x['bytes'] > 0 and len(x['sha256']) == 64 for x in plan)

def test_remove_takes_only_what_was_shown_and_keeps_the_records(tmp_path, monkeypatch):
    R = make_run(str(tmp_path / 'r'), record_sha=True)
    V1 = add_version(R, '001', 'one'); add_version(R, 'ai', 'the AI')
    shown = [x['sha256'] for x in prune.plan(R)]
    with pytest.raises(S.Refused, match='Removed By'): prune.remove(R, shown, ' ', say=lambda *a: None)
    with pytest.raises(S.Refused, match='changed since it was shown'): prune.remove(R, ['0' * 64], 'Kim', say=lambda *a: None)
    lk = S.Lock(R, 'reopen')                                                          # a review page open: refused, in plain words
    monkeypatch.setattr(S, 'review_process', lambda pid: True)                        # (its holder is a review process, as in the app)
    with pytest.raises(S.Refused, match='review of this book is open'): prune.remove(R, shown, 'Kim', say=lambda *a: None)
    lk.release(); monkeypatch.undo()
    os.makedirs(os.path.join(R, 'reviews', 'work'))
    with pytest.raises(S.Refused, match='being made'): prune.remove(R, shown, 'Kim', say=lambda *a: None)
    os.rmdir(os.path.join(R, 'reviews', 'work'))
    done = prune.remove(R, shown, 'Kim', say=lambda *a: None)
    assert [x['id'] for x in done] == ['001'] and not os.path.exists(os.path.join(V1, 'clans_remediated.pdf'))
    assert os.path.exists(os.path.join(V1, 'record.json')) and os.path.exists(os.path.join(V1, 'review.md'))
    assert os.path.exists(os.path.join(R, 'reviews', 'versions', 'ai', 'clans_remediated.pdf'))
    log = REL.removed(R)
    assert log[0]['version'] == '001' and log[0]['sha256'] == shown[0] and log[0]['by'] == 'Kim'
    assert prune.plan(R) == [] and not os.path.exists(S.P(R)['lock'])               # nothing left; the review lock released

def test_the_removal_note_is_drawn_from_the_record_on_every_build(tmp_path):
    """K8: the note comes from release/removed.json whenever the version's page is built, so a rebuild keeps it."""
    import report_html as H
    from test_evaluation import make_run as eval_run
    R = eval_run(tmp_path / 'run', True)                                             # a run with a whole record and review.md
    V = os.path.join(R, 'reviews', 'versions', '001'); shutil.copytree(R, V, ignore=shutil.ignore_patterns('reviews'))
    core.save(os.path.join(R, 'release', 'removed.json') if os.path.isdir(os.path.join(R, 'release')) else
              (os.makedirs(os.path.join(R, 'release')) or os.path.join(R, 'release', 'removed.json')),
              [{'version': '001', 'sha256': 'a' * 64, 'bytes': 1, 'by': 'K', 'removed': '2026-11-01T10:00:00'}])
    for _ in range(2):
        H.review_html(V, None, None, None, banner='This result (session 1) was replaced by session 2.')
        h = open(os.path.join(V, 'review.html'), encoding='utf-8').read()
        assert 'Its PDF was removed on November 1, 2026 ("Remove Older PDFs"), to free space.' in h.replace('&quot;', '"')
        assert 'was replaced by session 2' in h

def test_the_apps_post_and_the_panel(mapp):
    port, R = mapp['port'], mapp['R']; add_version(R, '001', 'one')
    st, s = js(port, 'GET', f'/api/run/{RUN}')
    assert s['prune']['versions'][0]['label'].startswith('Session 1') and s['prune']['total'].endswith('MB')
    st, r = js(port, 'POST', f'/api/run/{RUN}/remove-older-pdfs', {'by': 'Kim', 'shas': ['0' * 64]})
    assert st == 409 and 'changed since it was shown' in r['error']
    st, r = js(port, 'POST', f'/api/run/{RUN}/remove-older-pdfs', {'by': 'Kim', 'shas': s['prune']['shas']})
    assert st == 200 and r['removed'] == 1 and r['bytes'] > 0
    assert js(port, 'GET', f'/api/run/{RUN}')[1]['prune'] is None
    pj = open(os.path.join(HERE, 'webapp', 'panel.js'), encoding='utf-8').read()
    assert "This can\\'t be undone." in pj and "'Its record and decisions are'" in pj           # L2
    assert '>Remove Older PDFs</button>' in pj and "Their records and decisions are kept. The AI\\'s own version is always kept." in pj
    assert "'</button><button type=\"button\" value=\"no\">Cancel</button>" in pj and 'Removed By' in pj and 'drafts' not in pj.split('function pruneBlock')[1][:3000]

def test_the_command_line_is_a_dry_run_unless_yes(tmp_path):
    R = make_run(str(tmp_path / 'r'), record_sha=True); V = add_version(R, '001', 'one')
    out = subprocess.run([sys.executable, 'review_workorder.py', R, '--remove-older-pdfs'], cwd=HERE, capture_output=True, text=True)
    assert 'Session 1:' in out.stdout and 'a dry run' in out.stdout and os.path.exists(os.path.join(V, 'clans_remediated.pdf'))
    out = subprocess.run([sys.executable, 'review_workorder.py', R, '--remove-older-pdfs', '--yes', '--by', 'Kim'], cwd=HERE, capture_output=True, text=True)
    assert 'removed 1 older PDF(s)' in out.stdout and not os.path.exists(os.path.join(V, 'clans_remediated.pdf'))
