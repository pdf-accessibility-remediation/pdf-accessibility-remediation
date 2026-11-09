"""test_prune.py: "Clean Up Space" (review/prune.py; 17 §F, review 18 K7–K9; by selection, Patrick 2026-11-01): what it
offers and never offers, that only the chosen versions go, its refusals, its trail and the note on the version's page, the
app's POST, the panel's dialog and the command line. Synthetic runs.

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
    doc = pikepdf.new(); doc.add_blank_page(page_size=(200, 200)); doc.docinfo['/Title'] = title; doc.save(os.path.join(V, 'sample_remediated.pdf'), deterministic_id=True)
    core.save(os.path.join(V, 'record.json'), {'document': {'file': 'sample.pdf', 'output': 'sample_remediated.pdf'}})
    open(os.path.join(V, 'review.md'), 'w').write('# old\n')
    return V

def chk(sha): return {'id': 1, 'recorded': '2026-11-01T10:00:00', 'by': 'K', 'pdf': {'sha256': sha, 'which': 'current'}, 'items': {}}

def test_the_plan_never_takes_the_ai_version_an_evaluated_or_a_shipped_one(tmp_path):
    R = make_run(str(tmp_path / 'r'), record_sha=True)
    for vid in ('ai', '001', '002', '003', '004'): add_version(R, vid, f'version {vid}')
    sha = lambda v: REL.sha_file(os.path.join(R, 'reviews', 'versions', v, 'sample_remediated.pdf'))
    os.makedirs(os.path.join(R, 'release'))
    core.save(os.path.join(R, 'release', 'checks.json'), {'schema': REL.SCHEMA, 'pac': [chk(sha('002'))], 'screen_reader': []})
    core.save(os.path.join(R, 'release', 'shipped.json'), [{'n': 1, 'shipped': 'x', 'pdf': {'sha256': sha('003')}, 'withdrawn': {'by': 'L'}}])
    plan = prune.plan(R)
    assert [x['id'] for x in plan] == ['001', '004']                                  # not ai (K9), not evaluated, not shipped (even withdrawn)
    assert all(x['bytes'] > 0 and len(x['sha256']) == 64 for x in plan)

def pick(plan, *ids): return [{'id': x['id'], 'sha256': x['sha256']} for x in plan if x['id'] in ids]

def test_an_evaluated_or_a_shipped_version_posted_is_refused(mapp):
    """Review 29 R5: a version never offered (an evaluation result on its PDF; shipped, even withdrawn), posted with its own
    hash, is refused as a changed list, through prune.remove() and the app's POST, and nothing is removed."""
    port, R = mapp['port'], mapp['R']
    for vid in ('001', '002', '003'): add_version(R, vid, f'version {vid}')
    sha = lambda v: REL.sha_file(os.path.join(R, 'reviews', 'versions', v, 'sample_remediated.pdf'))
    os.makedirs(os.path.join(R, 'release'), exist_ok=True)
    core.save(os.path.join(R, 'release', 'checks.json'), {'schema': REL.SCHEMA, 'pac': [chk(sha('001'))], 'screen_reader': []})
    core.save(os.path.join(R, 'release', 'shipped.json'), [{'n': 1, 'shipped': 'x', 'pdf': {'sha256': sha('002')}},
                                                         {'n': 2, 'shipped': 'x', 'pdf': {'sha256': sha('003')}, 'withdrawn': {'by': 'L'}}])
    assert prune.plan(R) == []
    for vid in ('001', '002', '003'):
        bad = [{'id': vid, 'sha256': sha(vid)}]
        with pytest.raises(S.Refused) as e: prune.remove(R, bad, 'Kim', say=lambda *a: None)
        assert str(e.value) == prune.LIST_CHANGED, vid
        st, r = js(port, 'POST', f'/api/run/{RUN}/remove-older-pdfs', {'by': 'Kim', 'chosen': bad})
        assert st == 409 and r['error'] == prune.LIST_CHANGED, vid
    assert all(os.path.exists(os.path.join(R, 'reviews', 'versions', v, 'sample_remediated.pdf')) for v in ('001', '002', '003'))
    assert REL.removed(R) == []

def test_the_lock_is_named_in_plain_words(tmp_path, monkeypatch):
    """Review 29 R4: the review lock taken by Clean Up Space is named "clean up space", and the pages say it in plain words."""
    from webapp import jobs as Jb
    R = make_run(str(tmp_path / 'r'), record_sha=True); add_version(R, '001', 'one')
    seen = {}
    real = S.Lock
    def spy(R_, what): seen['what'] = what; return real(R_, what)
    monkeypatch.setattr(S, 'Lock', spy)
    prune.remove(R, pick(prune.plan(R), '001'), 'Kim', say=lambda *a: None)
    assert seen['what'] == 'clean up space'
    assert Jb.lock_words('clean up space', '2026-11-01T14:02:11') == ("PDFs of this run's previous versions are being removed (since 2:02 PM). "
                                                                      "Try again when it's done.")
    assert 'older pdfs' not in open(os.path.join(HERE, 'review', 'prune.py'), encoding='utf-8').read().lower()

def test_remove_takes_only_the_chosen_versions_and_keeps_the_records(tmp_path, monkeypatch):
    R = make_run(str(tmp_path / 'r'), record_sha=True)
    V1 = add_version(R, '001', 'one'); V2 = add_version(R, '002', 'two'); V3 = add_version(R, '003', 'three'); add_version(R, 'ai', 'the AI')
    plan = prune.plan(R); chosen = pick(plan, '001', '003')
    with pytest.raises(S.Refused, match='Select at least one PDF'): prune.remove(R, [], 'Kim', say=lambda *a: None)   # nothing unless chosen
    with pytest.raises(S.Refused, match='Removed By'): prune.remove(R, chosen, ' ', say=lambda *a: None)
    for bad in ([{'id': '001', 'sha256': '0' * 64}], [{'id': 'ai', 'sha256': plan[0]['sha256']}], [{'id': '009', 'sha256': plan[0]['sha256']}],
                chosen + [{'id': '001', 'sha256': '0' * 64}]):                       # a hash not the one shown, the AI's, unknown, named twice
        with pytest.raises(S.Refused, match='changed since they were shown'): prune.remove(R, bad, 'Kim', say=lambda *a: None)
    lk = S.Lock(R, 'reopen')                                                          # a review page open: refused, in plain words
    monkeypatch.setattr(S, 'review_process', lambda pid: True)                        # (its holder is a review process, as in the app)
    with pytest.raises(S.Refused, match='review of this book is open'): prune.remove(R, chosen, 'Kim', say=lambda *a: None)
    lk.release(); monkeypatch.undo()
    os.makedirs(os.path.join(R, 'reviews', 'work'))
    with pytest.raises(S.Refused, match='being made'): prune.remove(R, chosen, 'Kim', say=lambda *a: None)
    os.rmdir(os.path.join(R, 'reviews', 'work'))
    doc = pikepdf.new(); doc.add_blank_page(page_size=(300, 300)); doc.save(os.path.join(V3, 'sample_remediated.pdf'), deterministic_id=True)   # changed after it was shown
    with pytest.raises(S.Refused, match='changed since they were shown'): prune.remove(R, chosen, 'Kim', say=lambda *a: None)
    assert all(os.path.exists(os.path.join(V, 'sample_remediated.pdf')) for V in (V1, V2, V3))   # refused: nothing removed
    chosen = pick(prune.plan(R), '001', '003')
    done = prune.remove(R, chosen, 'Kim', say=lambda *a: None)
    assert [x['id'] for x in done] == ['001', '003'] and not os.path.exists(os.path.join(V1, 'sample_remediated.pdf'))
    assert os.path.exists(os.path.join(V2, 'sample_remediated.pdf'))                  # not chosen: kept
    assert os.path.exists(os.path.join(V1, 'record.json')) and os.path.exists(os.path.join(V1, 'review.md'))
    assert os.path.exists(os.path.join(R, 'reviews', 'versions', 'ai', 'sample_remediated.pdf'))
    log = REL.removed(R)
    assert [x['version'] for x in log] == ['001', '003'] and log[0]['sha256'] == chosen[0]['sha256'] and log[0]['by'] == 'Kim'
    assert [x['id'] for x in prune.plan(R)] == ['002'] and not os.path.exists(S.P(R)['lock'])   # the review lock released

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
        assert 'Its PDF was removed on November 1, 2026 ("Clean Up Space"), to free space.' in h.replace('&quot;', '"')
        assert 'was replaced by session 2' in h

def test_the_apps_post_the_panel_and_session_history(mapp):
    port, R = mapp['port'], mapp['R']; add_version(R, '001', 'one'); add_version(R, '002', 'two')
    st, s = js(port, 'GET', f'/api/run/{RUN}')
    v = s['prune']['versions']
    assert [x['id'] for x in v] == ['001', '002'] and v[0]['label'].startswith('Session 1') and v[0]['size'].endswith('MB') and len(v[0]['sha256']) == 64
    st, r = js(port, 'POST', f'/api/run/{RUN}/remove-older-pdfs', {'by': 'Kim', 'chosen': [{'id': '001', 'sha256': '0' * 64}]})
    assert st == 409 and 'changed since they were shown' in r['error']
    st, r = js(port, 'POST', f'/api/run/{RUN}/remove-older-pdfs', {'by': 'Kim', 'chosen': []})
    assert st == 409 and 'Select at least one PDF' in r['error']
    st, r = js(port, 'POST', f'/api/run/{RUN}/remove-older-pdfs', {'by': 'Kim', 'chosen': [{'id': '002', 'sha256': v[1]['sha256']}]})
    assert st == 200 and r['removed'] == 1 and r['bytes'] > 0
    assert [x['id'] for x in js(port, 'GET', f'/api/run/{RUN}')[1]['prune']['versions']] == ['001']
    pj = open(os.path.join(HERE, 'webapp', 'panel.js'), encoding='utf-8').read()
    blk = pj.split('function pruneBlock')[1][:4000]
    assert '>Clean Up Space</button></div>\';' in pj and 'Remove Older PDFs' not in pj and 'pp-note' not in blk.split('function removeLabel')[0]   # the button alone
    assert ("Deletes the PDF files of the previous versions you select to free up space. Their records and decisions stay in \"Session History\". "
            "The original AI-generated version is always kept.") in pj
    assert "This can\\'t be undone." in pj and 'type="checkbox"' in blk and 'value="yes" disabled>' in blk and 'yes.disabled = !vs.length' in blk
    assert "'Remove ' + n + ' PDF' + (n === 1 ? '' : 's')" in pj and 'Removed By' in blk and 'drafts' not in blk
    assert "(r.pdf_removed ? '<span class=\"pp-note\"> · PDF removed</span>' : '')" in pj

def test_session_history_marks_a_removed_pdf(tmp_path):
    from webapp import runs
    R = make_run(str(tmp_path / 'r'), record_sha=True); add_version(R, '001', 'one')
    core.save(os.path.join(R, 'reviews', 'sessions', '001.json') if os.path.isdir(os.path.join(R, 'reviews', 'sessions')) else
              (os.makedirs(os.path.join(R, 'reviews', 'sessions')) or os.path.join(R, 'reviews', 'sessions', '001.json')),
              {'id': '001', 'status': 'applied', 'reviewer': 'Kim', 'started': '2026-10-30T10:00:00'})
    prune.remove(R, pick(prune.plan(R), '001'), 'Kim', say=lambda *a: None)
    row = next(x for x in runs.state({'jobs': str(tmp_path / 'jobs')}, 'r', R)['sessions'] if x['id'] == '001')
    assert row['pdf_removed'] is True

def test_the_command_line_lists_and_removes_only_the_named_sessions(tmp_path):
    R = make_run(str(tmp_path / 'r'), record_sha=True); V1 = add_version(R, '001', 'one'); V2 = add_version(R, '002', 'two')
    cmd = [sys.executable, 'review_workorder.py', R, '--remove-older-pdfs']
    out = subprocess.run(cmd, cwd=HERE, capture_output=True, text=True)
    assert 'Session 1:' in out.stdout and 'Session 2:' in out.stdout and '--remove-older-pdfs 1 --yes --by NAME' in out.stdout
    out = subprocess.run(cmd + ['--yes', '--by', 'Kim'], cwd=HERE, capture_output=True, text=True)
    assert out.returncode != 0 and 'nothing is removed unless chosen' in out.stderr and os.path.exists(os.path.join(V1, 'sample_remediated.pdf'))
    out = subprocess.run(cmd + ['2'], cwd=HERE, capture_output=True, text=True)
    assert 'a dry run' in out.stdout and os.path.exists(os.path.join(V2, 'sample_remediated.pdf'))
    out = subprocess.run(cmd + ['7'], cwd=HERE, capture_output=True, text=True)
    assert out.returncode != 0 and 'not offered' in out.stderr
    out = subprocess.run(cmd + ['002', '--yes', '--by', 'Kim'], cwd=HERE, capture_output=True, text=True)
    assert 'removed 1 PDF(s)' in out.stdout and not os.path.exists(os.path.join(V2, 'sample_remediated.pdf')) and os.path.exists(os.path.join(V1, 'sample_remediated.pdf'))
