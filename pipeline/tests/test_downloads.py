"""test_downloads.py: a run's downloads (issue #38, stage 3; 17 §A–B, review 18 K2–K5): the names, the record ZIP read to its
end, the refusals, version ids from the run's own list only, and one moment per download (a promotion during a download
never mixes two versions). An app on a temporary runs folder (test_webapp_checks' fixtures), synthetic one-page PDFs.

    python -m pytest tests/test_downloads.py -q
"""
import os, io, json, shutil, zipfile, urllib.parse
import pytest
import pikepdf
from lib import release as REL
from review import core, manual as M
from webapp import downloads as DL, manualpage as MP
from test_webapp import setup, wait, free_port  # noqa: F401  (fixtures)
from test_webapp_checks import mapp, make_run, req, RUN, PAC  # noqa: F401

SR = {'by': 'Lee', 'fields': {'screen_reader': 'NVDA'}, 'items': {x['key']: {'result': 'pass'} for x in REL.CHECKLIST['screen_reader']}}

# ------------------------------------------------------------------ names (K2, K4)
def test_names_for_each_state():
    out = 'expedition_remediated.pdf'
    assert REL.download_names(out, '006', REL.NOT_READY) == ('expedition_remediated_session-6_not-ready.pdf', 'expedition_remediated_record_session-6_not-ready.zip')
    assert REL.download_names(out, '006', REL.PENDING)[0] == 'expedition_remediated_session-6_not-ready.pdf'
    assert REL.download_names(out, '006', REL.READY) == ('expedition_remediated_session-6_not-shipped.pdf', 'expedition_remediated_record_session-6_not-shipped.zip')
    assert REL.download_names(out, '006', REL.SHIPPED, 2) == ('expedition_remediated.pdf', 'expedition_remediated_record_shipment-2.zip')
    assert REL.download_names(out, '005', 'earlier version')[0] == 'expedition_remediated_session-5_earlier-version.pdf'
    assert REL.download_names(out, None, REL.NOT_READY)[0] == 'expedition_remediated_no-review_not-ready.pdf'

def test_a_hostile_output_name_is_made_safe():
    pdf, zname = REL.download_names(' ..‮A"b/c\\d<e>f:g|h?i*j;k\r\nl. .pdf ', '3', REL.READY)
    assert pdf == 'A_b_c_d_e_f_g_h_i_j_kl_session-3_not-shipped.pdf'                  # controls dropped, reserved → _, no leading dot
    d = REL.disposition('Kū ʻĀina_session-3_not-ready.pdf')
    assert d.startswith('attachment; filename="K_ __ina_session-3_not-ready.pdf"; ')            # an ASCII fallback
    assert "filename*=UTF-8''K%C5%AB%20%CA%BB%C4%80ina_session-3_not-ready.pdf" in d and '"' not in d.split('filename="')[1].split('";')[0]
    title = 'ʻ' * 300                                                                  # a 300-character non-ASCII title (K2)
    pdf, _ = REL.download_names(title + '.pdf', '5', 'earlier version')
    base = pdf[:-len('_session-5_earlier-version.pdf')]
    assert len(base.encode('utf-8')) <= REL.BASE_BYTES and base == 'ʻ' * 75 and len(pdf.encode('utf-8')) < 255

# ------------------------------------------------------------------ the routes
def get(port, path):
    st, body, h = req(port, 'GET', path); return st, body, h

def test_the_pdf_and_the_record_zip(mapp):
    port, R = mapp['port'], mapp['R']
    open(os.path.join(R, 'han_review.csv'), 'w').write('pdf_page,text\n1,漢\n')
    os.makedirs(os.path.join(R, '_intake')); open(os.path.join(R, '_intake', 'intake.json'), 'w').write('{}')
    open(os.path.join(R, '.hidden'), 'w').write('x')
    M.record(R, 'pac', dict(PAC, items=dict(PAC['items'], contrast={'result': 'fail', 'note': 'grey on grey'})), say=lambda *a: None, batch=False)
    sha = REL.sha_file(os.path.join(R, 'clans_remediated.pdf'))
    st, body, h = get(port, f'/run/{RUN}/download?what=pdf&v=current')
    assert st == 200 and h['Content-Type'] == 'application/pdf' and body == open(os.path.join(R, 'clans_remediated.pdf'), 'rb').read()
    assert h['Content-Disposition'] == REL.disposition('clans_remediated_no-review_not-ready.pdf') and h['X-Content-Type-Options'] == 'nosniff'
    st, body, h = get(port, f'/run/{RUN}/download?what=record&v=current')          # read to the end of the stream (K5)
    assert st == 200 and h['Content-Type'] == 'application/zip' and 'Content-Length' not in h
    z = zipfile.ZipFile(io.BytesIO(body)); assert z.testzip() is None
    folder = 'clans_remediated_record_no-review_not-ready'
    assert sorted(z.namelist()) == sorted(f'{folder}/{n}' for n in ('clans_remediated.pdf', 'review.html', 'review.md', 'han_review.csv',
                                                                       'evaluation-results.json', 'READ-ME.txt'))
    pdf = z.getinfo(f'{folder}/clans_remediated.pdf')
    assert pdf.compress_type == zipfile.ZIP_STORED and z.read(pdf) == open(os.path.join(R, 'clans_remediated.pdf'), 'rb').read()
    ev = json.loads(z.read(f'{folder}/evaluation-results.json'))
    assert ev['pdf_sha256'] == sha and len(ev['pac']) == 1 and ev['screen_reader'] == []
    rd = z.read(f'{folder}/READ-ME.txt').decode()
    assert f'sha256 of clans_remediated.pdf: {sha}' in rd and 'Status: Not Ready · 1 issue noted' in rd
    assert 'not legal sign-off' in rd and 'not a legal certification' in rd and 'The Clan Records' in rd
    for n in z.namelist(): assert not any(x in n for x in ('record.json', '_intake', '.hidden', 'drafts', 'reviews/', 'release/'))

def test_version_ids_come_from_the_runs_own_list(mapp):
    port, R = mapp['port'], mapp['R']
    for v in ('../x', '001/../..', 'nope', '%2e%2e', 'current/..'):
        st, body, _ = get(port, f'/run/{RUN}/download?what=pdf&v={urllib.parse.quote(v, safe="")}')
        assert st == 404 and b'not available to download' in body, v
    assert get(port, f'/run/{RUN}/download?what=other')[0] == 404

def test_refusals_for_downloads(mapp):
    port, R = mapp['port'], mapp['R']
    os.makedirs(os.path.join(R, 'reviews', 'work'))                                   # a re-apply under way: still given
    assert get(port, f'/run/{RUN}/download?what=pdf')[0] == 200
    open(os.path.join(R, 'reviews', 'promoting.json'), 'w').write('{}')               # a promotion that did not finish: refused
    st, body, _ = get(port, f'/run/{RUN}/download?what=record')
    assert st == 409 and M.PROMOTING.encode() in body.replace(b'&#x27;', b"'")
    os.remove(os.path.join(R, 'reviews', 'promoting.json'))
    rec = core.load(os.path.join(R, 'record.json')); rec['document']['output_sha256'] = 'c' * 64; core.save(os.path.join(R, 'record.json'), rec)
    st, body, _ = get(port, f'/run/{RUN}/download?what=pdf')                          # the file on disk is not the one described
    assert st == 409 and b'has changed since this report was made' in body

# ------------------------------------------------------------------ an earlier version, and one moment per download
def add_version(R, vid='001', text='an earlier PDF'):
    V = os.path.join(R, 'reviews', 'versions', vid); os.makedirs(V)
    doc = pikepdf.new(); doc.add_blank_page(page_size=(200, 200)); doc.docinfo['/Title'] = text; doc.save(os.path.join(V, 'clans_remediated.pdf'))
    core.save(os.path.join(V, 'record.json'), {'document': {'file': 'clans.pdf', 'output': 'clans_remediated.pdf'}})
    open(os.path.join(V, 'review.md'), 'w').write('# old\n'); open(os.path.join(V, 'review.html'), 'w').write('<p>old</p>')
    return V

def test_an_earlier_version_is_listed_named_and_described_as_earlier(tmp_path):
    R = make_run(str(tmp_path / 'r'), record_sha=True); V = add_version(R)
    rec = core.load(os.path.join(R, 'record.json'))
    vs = DL.versions(R, rec)
    assert [x['id'] for x in vs] == ['current', '001'] and vs[1]['label'] == 'Session 1 (earlier version)'
    assert DL.marked_line(vs[1]['state']) == 'The downloaded files are marked "earlier version".'
    d = DL.prepare(R, 'r', '001', 'record')
    assert d['name'] == 'clans_remediated_record_session-1_earlier-version.zip'
    buf = io.BytesIO(); DL.stream_zip(buf, d)
    rd = zipfile.ZipFile(buf).read('clans_remediated_record_session-1_earlier-version/READ-ME.txt').decode()
    assert 'Status: earlier version (not the current one; the current version is the version applied without a review)' in rd   # K3
    os.remove(os.path.join(V, 'clans_remediated.pdf'))                                # its PDF gone: not offered
    assert [x['id'] for x in DL.versions(R, rec)] == ['current']
    with pytest.raises(DL.Refused): DL.prepare(R, 'r', '001', 'pdf')

def test_a_promotion_during_a_download_never_mixes_two_versions(tmp_path):
    R = make_run(str(tmp_path / 'r'), record_sha=True)
    old_pdf = open(os.path.join(R, 'clans_remediated.pdf'), 'rb').read(); old_md = open(os.path.join(R, 'review.md'), 'rb').read()
    d = DL.prepare(R, 'r', 'current', 'record')                                       # every member opened under the lock
    V = os.path.join(R, 'reviews', 'versions', 'ai'); os.makedirs(V)                  # a promotion: the files moved by rename,
    for n in ('clans_remediated.pdf', 'review.md', 'review.html'): shutil.move(os.path.join(R, n), os.path.join(V, n))
    doc = pikepdf.new(); doc.add_blank_page(page_size=(400, 400)); doc.save(os.path.join(R, 'clans_remediated.pdf'))   # and new ones put in place
    open(os.path.join(R, 'review.md'), 'w').write('# the new version\n')
    buf = io.BytesIO(); DL.stream_zip(buf, d)
    z = zipfile.ZipFile(buf); f = d['folder']
    assert z.read(f'{f}/clans_remediated.pdf') == old_pdf and z.read(f'{f}/review.md') == old_md
    import hashlib
    assert hashlib.sha256(old_pdf).hexdigest() in z.read(f'{f}/READ-ME.txt').decode()

def test_the_file_check_knows_every_version_and_removed_ones(tmp_path):
    R = make_run(str(tmp_path / 'r'), record_sha=True); add_version(R)
    os.makedirs(os.path.join(R, 'release'), exist_ok=True)
    core.save(os.path.join(R, 'release', 'removed.json'), [{'version': '002', 'sha256': 'd' * 64, 'bytes': 10, 'by': 'K', 'removed': '2026-11-01T10:00:00'}])
    rec = core.load(os.path.join(R, 'record.json'))
    k = {x['sha']: x['words'] for x in DL.known(R, rec)}
    assert k[rec['document']['output_sha256']].startswith('This is the current version (applied without a review): Not Ready')
    assert 'This is an earlier version (Session 1), not the current one.' in k.values()
    assert k['d' * 64] == 'This is an earlier version (Session 2), not the current one. Its PDF was removed from this computer to free space.'

# ------------------------------------------------------------------ the picker and the file check on the pages (K6, C)
def test_the_evaluation_page_offers_the_downloads_and_the_file_check(tmp_path):
    import re
    from test_webapp_checks import visible
    R = make_run(str(tmp_path / 'r'), record_sha=True); add_version(R)
    page = MP.page(R, 'r')
    assert '<label for="mc-dlv">Version to Download</label><select id="mc-dlv" name="v" aria-describedby="mc-dl-marked">' in page
    assert '<option value="001" data-marked="The downloaded files are marked &quot;earlier version&quot;.">Session 1 (earlier version)</option>' in page
    assert 'action="/run/r/download"' in page and 'name="what" value="pdf">Download the Remediated PDF' in page and 'value="record">Download the Record (ZIP)' in page
    assert '<input type="file" id="fc-file" accept=".pdf,application/pdf"' in page and 'role="status" aria-live="polite"' in page
    text = re.sub(r'\s+', ' ', visible(page))
    assert 'Which Version Is This File?' in text and 'never uploaded' in text and 'sha256' not in text and '.pdf' not in text
    data = json.loads(re.search(r'id="mc-data">(.*?)</script>', page, re.S).group(1))
    assert len(data['known']) == 2 and all(len(k['sha']) == 64 for k in data['known'])
    s = MP.strip(R, core.load(os.path.join(R, 'record.json')))
    assert [v['id'] for v in s['downloads']['versions']] == ['current', '001'] and s['downloads']['versions'][0]['marked'] == 'The downloaded files are marked "not ready".'
    js = open(os.path.join(os.path.dirname(MP.__file__), 'panel.js'), encoding='utf-8').read()
    assert '<label for="pp-dlv">Version to Download</label>' in js and 'aria-describedby="pp-dl-marked"' in js

def test_the_file_checks_matching_in_javascript():
    from test_dates import js_runner
    import subprocess
    run = js_runner()
    if run is None: pytest.skip('no JavaScript engine runs here')
    src = open(os.path.join(os.path.dirname(MP.__file__), 'manual.js'), encoding='utf-8').read()
    fn = src[src.index('function matchVersion'):src.index('const fc = ')]
    code = fn + ('\nconst K = [{sha: "aa", words: "This is the current version (Session 6): Ready."}];\n'
                 '(typeof print === "function" ? print : console.log)(JSON.stringify([matchVersion("aa", K), matchVersion("bb", K), matchVersion("aa", null)]));')
    out = subprocess.run(run + [code], capture_output=True, text=True, timeout=30)
    assert json.loads(out.stdout) == ['This is the current version (Session 6): Ready.', 'This file matches no version of this book.',
                                      'This file matches no version of this book.']
