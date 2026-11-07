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
    assert REL.download_names(out, '005', 'earlier version')[0] == 'expedition_remediated_session-5_previous-version.pdf'
    assert REL.download_names(out, None, REL.NOT_READY)[0] == 'expedition_remediated_no-review_not-ready.pdf'

def test_a_hostile_output_name_is_made_safe():
    pdf, zname = REL.download_names(' ..‮A"b/c\\d<e>f:g|h?i*j;k\r\nl. .pdf ', '3', REL.READY)
    assert pdf == 'A_b_c_d_e_f_g_h_i_j_kl_session-3_not-shipped.pdf'                  # controls dropped, reserved → _, no leading dot
    d = REL.disposition('Kū ʻĀina_session-3_not-ready.pdf')
    assert d.startswith('attachment; filename="K_ __ina_session-3_not-ready.pdf"; ')            # an ASCII fallback
    assert "filename*=UTF-8''K%C5%AB%20%CA%BB%C4%80ina_session-3_not-ready.pdf" in d and '"' not in d.split('filename="')[1].split('";')[0]
    title = 'ʻ' * 300                                                                  # a 300-character non-ASCII title (K2)
    pdf, _ = REL.download_names(title + '.pdf', '5', 'earlier version')
    base = pdf[:-len('_session-5_previous-version.pdf')]
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
    sha = REL.sha_file(os.path.join(R, 'sample_remediated.pdf'))
    st, body, h = get(port, f'/run/{RUN}/download?what=pdf&v=current')
    assert st == 200 and h['Content-Type'] == 'application/pdf' and body == open(os.path.join(R, 'sample_remediated.pdf'), 'rb').read()
    assert h['Content-Disposition'] == REL.disposition('sample_remediated_no-review_not-ready.pdf') and h['X-Content-Type-Options'] == 'nosniff'
    st, body, h = get(port, f'/run/{RUN}/download?what=record&v=current')          # read to the end of the stream (K5)
    assert st == 200 and h['Content-Type'] == 'application/zip' and 'Content-Length' not in h
    z = zipfile.ZipFile(io.BytesIO(body)); assert z.testzip() is None
    folder = 'sample_remediated_record_no-review_not-ready'
    assert sorted(z.namelist()) == sorted(f'{folder}/{n}' for n in ('sample_remediated.pdf', 'review.html', 'han_review.csv', 'READ-ME.txt'))
    # no review.md, evaluation-results.json or statement .md: the ZIP is for staff (Patrick, 2026-11-01; han_review.csv: review 30 S1)
    pdf = z.getinfo(f'{folder}/sample_remediated.pdf')
    assert pdf.compress_type == zipfile.ZIP_STORED and z.read(pdf) == open(os.path.join(R, 'sample_remediated.pdf'), 'rb').read()
    rd = z.read(f'{folder}/READ-ME.txt').decode()
    assert sha not in rd and 'sha256' not in rd and 'Status: Not Ready · 1 issue noted' in rd             # no hash line (Patrick, 2026-11-01)
    assert rd.split('\n')[1] == 'Source PDF: sample.pdf'
    assert ('- review.html: the report on this version (what was changed, what was checked, and the results of the accessibility '
            'evaluation). Open it in a web browser.') in rd
    assert 'Accessibility evaluation results recorded on this file: 1 (in review.html)' in rd and 'evaluation-results.json' not in rd
    assert ('This folder holds:\n- sample_remediated.pdf: the remediated PDF of this version.\n- review.html: the report on this version' in rd
            and '- READ-ME.txt: this file.' in rd and 'review.md' not in rd)
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
    assert st == 409 and b"so it can&#x27;t be downloaded as this version" in body and b'recorded' not in body   # its own words (L1)

# ------------------------------------------------------------------ an earlier version, and one moment per download
def add_version(R, vid='001', text='an earlier PDF'):
    V = os.path.join(R, 'reviews', 'versions', vid); os.makedirs(V)
    doc = pikepdf.new(); doc.add_blank_page(page_size=(200, 200)); doc.docinfo['/Title'] = text; doc.save(os.path.join(V, 'sample_remediated.pdf'))
    core.save(os.path.join(V, 'record.json'), {'document': {'file': 'sample.pdf', 'output': 'sample_remediated.pdf'}})
    open(os.path.join(V, 'review.md'), 'w').write('# old\n'); open(os.path.join(V, 'review.html'), 'w').write('<p>old</p>')
    return V

def test_an_earlier_version_is_listed_named_and_described_as_earlier(tmp_path):
    R = make_run(str(tmp_path / 'r'), record_sha=True); V = add_version(R)
    rec = core.load(os.path.join(R, 'record.json'))
    vs = DL.versions(R, rec)
    assert [x['id'] for x in vs] == ['current', '001'] and vs[1]['label'] == 'Session 1 (previous version)'
    assert DL.marked_line(vs[1]['state']) == 'The downloaded files are marked "previous version."'   # the period inside the quotes
    d = DL.prepare(R, 'r', '001', 'record')
    assert d['name'] == 'sample_remediated_record_session-1_previous-version.zip'
    buf = io.BytesIO(); DL.stream_zip(buf, d)
    rd = zipfile.ZipFile(buf).read('sample_remediated_record_session-1_previous-version/READ-ME.txt').decode()
    assert 'Status: previous version (not the current one; the current version is the version applied without a review)' in rd   # K3
    os.remove(os.path.join(V, 'sample_remediated.pdf'))                                # its PDF gone: not offered
    assert [x['id'] for x in DL.versions(R, rec)] == ['current']
    with pytest.raises(DL.Refused): DL.prepare(R, 'r', '001', 'pdf')

def test_a_failure_after_opening_closes_every_handle(tmp_path, monkeypatch):
    """prepare() opened the PDF and han_review.csv, then a later step failed: both are closed before the error goes on (35)."""
    import builtins
    R = make_run(str(tmp_path / 'r'), record_sha=True)
    open(os.path.join(R, 'han_review.csv'), 'w').write('pdf_page,text\n1,漢\n')
    opened = []
    def tracking(*a, **k):
        f = builtins.open(*a, **k)
        if 'b' in (a[1] if len(a) > 1 else k.get('mode', 'r')): opened.append(f)
        return f
    monkeypatch.setattr(DL, 'open', tracking, raising=False)                     # the module's open(): its own lookups only
    def boom(rec): raise RuntimeError('a later step failed')
    monkeypatch.setattr(MP, 'book', boom)                                         # after both files are open
    with pytest.raises(RuntimeError, match='a later step failed'): DL.prepare(R, 'r', 'current', 'record')
    assert {os.path.basename(f.name) for f in opened} == {'sample_remediated.pdf', 'han_review.csv'}
    assert all(f.closed for f in opened)

@pytest.mark.parametrize('name', ['../outside.pdf', 'a/b.pdf', 'a\\b.pdf', '..pdf', '.hidden.pdf', 'bad\nname.pdf', ''])
def test_a_pdf_name_that_is_not_a_plain_file_name_is_refused(tmp_path, name):
    """A hand-edited record.json never makes a ZIP entry or a path outside its folder (35): the current version is refused
    in plain words, before its file is looked at; a previous version or a shipped copy with such a name is not offered."""
    R = make_run(str(tmp_path / 'r'), record_sha=True)
    open(os.path.join(str(tmp_path), 'outside.pdf'), 'wb').write(open(os.path.join(R, 'sample_remediated.pdf'), 'rb').read())
    assert not DL.plain_name(name) and DL.plain_name('sample_remediated.pdf') and DL.plain_name('Kū ʻĀina_remediated.pdf')
    rec = core.load(os.path.join(R, 'record.json')); rec['document']['output'] = name; core.save(os.path.join(R, 'record.json'), rec)
    for what in ('pdf', 'record'):
        with pytest.raises(DL.Refused) as e: DL.prepare(R, 'r', 'current', what)
        assert e.value.args[0] == DL.BAD_NAME and 'record.json' not in DL.BAD_NAME
    rec['document']['output'] = 'sample_remediated.pdf'; core.save(os.path.join(R, 'record.json'), rec)
    V = add_version(R)
    vrec = core.load(os.path.join(V, 'record.json')); vrec['document']['output'] = name; core.save(os.path.join(V, 'record.json'), vrec)
    assert [x['id'] for x in DL.versions(R, rec)] == ['current']                 # not offered
    with pytest.raises(DL.Refused): DL.prepare(R, 'r', '001', 'record')

def test_a_promotion_during_a_download_never_mixes_two_versions(tmp_path):
    R = make_run(str(tmp_path / 'r'), record_sha=True)
    old_pdf = open(os.path.join(R, 'sample_remediated.pdf'), 'rb').read()
    with open(os.path.join(R, 'review.html'), 'a') as f: f.write('<p>the old page</p>')
    d = DL.prepare(R, 'r', 'current', 'record')                                       # every member opened under the lock
    V = os.path.join(R, 'reviews', 'versions', 'ai'); os.makedirs(V)                  # a promotion: the files moved by rename,
    for n in ('sample_remediated.pdf', 'review.md', 'review.html'): shutil.move(os.path.join(R, n), os.path.join(V, n))
    doc = pikepdf.new(); doc.add_blank_page(page_size=(400, 400)); doc.save(os.path.join(R, 'sample_remediated.pdf'))   # and new ones put in place
    open(os.path.join(R, 'review.html'), 'w').write('<p>the new page</p>')
    buf = io.BytesIO(); DL.stream_zip(buf, d)
    z = zipfile.ZipFile(buf); f = d['folder']
    page = z.read(f'{f}/review.html').decode()
    assert z.read(f'{f}/sample_remediated.pdf') == old_pdf and 'the old page' in page and 'the new page' not in page
    assert 'Version: the current version' in z.read(f'{f}/READ-ME.txt').decode()        # the read-me of the version opened

# ------------------------------------------------------------------ "Available Downloads" on both pages (K6; Patrick, 2026-11-01)
def test_the_evaluation_page_offers_the_downloads_and_no_file_check(tmp_path):
    import re
    from test_webapp_checks import visible
    R = make_run(str(tmp_path / 'r'), record_sha=True); add_version(R)
    page = MP.page(R, 'r')
    assert ('<section id="downloads" class="mc-sec" aria-labelledby="mc-dl-h"><form class="pp-dl" method="get" action="/run/r/download">'
            '<h2 id="mc-dl-h"><label for="mc-dlv">Available Downloads</label></h2>'
            '<select id="mc-dlv" name="v" aria-describedby="mc-dl-marked">') in page
    assert ('<option value="001" data-marked="The downloaded files are marked &quot;previous version.&quot; Results on this page are recorded for '
            'the current version only.">Session 1 (previous version)</option>') in page   # R1: the evaluation page only, the line tied to the select
    assert ('<p id="mc-dl-marked" class="pp-note">The downloaded files are marked &quot;not ready.&quot;</p><div class="pp-row">'
            '<button type="submit" name="what" value="pdf">Download the Remediated PDF</button>'
            '<button type="submit" name="what" value="record">Download the Record (ZIP)</button></div></form></section>') in page
    text = re.sub(r'\s+', ' ', visible(page))
    assert 'Which Version Is This File?' not in text and 'Version to Download' not in text and 'fc-file' not in page
    data = json.loads(re.search(r'id="mc-data">(.*?)</script>', page, re.S).group(1))
    assert 'known' not in data
    assert page.index('Back to the Run Page') < page.index('Overall Status:') < page.index('These results are recorded for')   # right after the button
    s = MP.strip(R, core.load(os.path.join(R, 'record.json')))
    assert [v['id'] for v in s['downloads']['versions']] == ['current', '001'] and s['downloads']['versions'][0]['marked'] == 'The downloaded files are marked "not ready."'
    assert s['downloads']['versions'][1]['marked'] == 'The downloaded files are marked "previous version."'   # the strip records nothing: no R1 line
    assert 'recorded for the current version only' not in s['downloads']['versions'][0]['marked']
    assert 'sections' not in s                                                                  # no line per part on the strip
    js = open(os.path.join(os.path.dirname(MP.__file__), 'panel.js'), encoding='utf-8').read()
    assert "'<label for=\"pp-dlv\">Available Downloads</label></' + hx + '>'" in js and 'aria-describedby="pp-dl-marked"' in js
    assert 'Version to Download' not in js and 'matchVersion' not in open(os.path.join(os.path.dirname(MP.__file__), 'manual.js'), encoding='utf-8').read()


# ------------------------------------------------------------------ review 20: L4, the read-me's date, the refusal page
def test_an_earlier_version_whose_pdf_changed_is_refused(tmp_path):
    R = make_run(str(tmp_path / 'r'), record_sha=True); V = add_version(R)
    vrec = core.load(os.path.join(V, 'record.json'))
    vrec['document']['output_sha256'] = REL.sha_file(os.path.join(V, 'sample_remediated.pdf'))
    core.save(os.path.join(V, 'record.json'), vrec)
    assert DL.prepare(R, 'r', '001', 'pdf')['name'].endswith('_previous-version.pdf')        # its own hash: given
    vrec['document']['output_sha256'] = 'e' * 64; core.save(os.path.join(V, 'record.json'), vrec)
    with pytest.raises(DL.Refused) as e: DL.prepare(R, 'r', '001', 'record')                # another hash: refused (L4)
    assert e.value.args[0] == DL.EARLIER_CHANGED and 'recorded' not in DL.EARLIER_CHANGED

def test_an_earlier_versions_readme_gives_its_applied_date(tmp_path):
    R = make_run(str(tmp_path / 'r'), record_sha=True); add_version(R)
    os.makedirs(os.path.join(R, 'reviews', 'sessions'))
    core.save(os.path.join(R, 'reviews', 'sessions', '001.json'), {'id': '001', 'status': 'applied', 'applied': '2026-10-27T23:45:00'})
    d = DL.prepare(R, 'r', '001', 'record'); buf = io.BytesIO(); DL.stream_zip(buf, d)
    rd = zipfile.ZipFile(buf).read(f'{d["folder"]}/READ-ME.txt').decode()
    assert 'Version: Session 1, a previous version, applied on October 27, 2026, at 11:45 PM' in rd

def test_the_download_not_available_page_has_a_working_skip_link():
    from webapp import server as W
    page = W.refused_page(DL.MISSING, '/run/r/')
    i, j = page.index(W.SKIP), page.index('<main id="main" tabindex="-1">')
    assert 'href="#main"' in W.SKIP and i < j and '<h1>Download Not Available</h1>' in page and 'Back to the Run Page' in page
    assert "can&#x27;t be downloaded" in page and '.pdf' not in page.split('<main')[1]


def test_the_readme_gives_the_run_details_in_plain_words():
    """Patrick, 2026-11-01: the read-me's run details for staff, from the version's own record; a reused reply gives the
    original call's cost (lib/origin.py); nothing missing prints as None."""
    rec = {'document': {'file': 'expedition.pdf', 'pages': 437},
           'run': {'started': '2026-10-26T06:48:36', 'model': 'anthropic/claude-sonnet-5.5', 'prompt_file': 'workorder_v9.md', 'response_from': 'x',
                   'original_call': {'cost_usd': 0.255874, 'model': 'anthropic/claude-sonnet-5.5', 'prompt_file': 'workorder_v8.md', 'date': '2026-10-26T00:30:47'}},
           'cost_total_usd': 0,
           'intake': {'status': 'done', 'triage': {'counts': {'image-only': 6, 'text': 430}}, 'tag_tree': {'status': 'untagged'}, 'result': {'pdf': '_intake/intake.pdf'},
                      'ocr': {'pages_with_ocr_text': [], 'image_pages_without_text': [1, 2, 3, 4, 5, 6]}, 'steps': [{'step': 'autotag', 'error': None}]},
           'timing_seconds': {'0/5 intake (local, no model)': 4.2, '1/5 audit (no model)': 36.8, '2/5 reuse saved reply (no cost)': 1.6,
                              'review: page images (no model)': 8.0, '4/5 apply (no model)': 57.3, '4/5 verify (no model)': 124.6},
           'environment': {'python': '3.13.9', 'executable': '/x/python3', 'pikepdf': '10.5.1', 'pdfplumber': '0.11.9', 'pypdfium2': '5.7.1', 'pillow': '13.0.0', 'fontTools': '4.62.1'}}
    rec['environment']['fonttools'] = rec['environment'].pop('fontTools')
    L = DL.about_lines(rec)
    assert L[0] == 'Pages: 437' and L[1].startswith('Remediated: October 26, 2026')
    assert L[2] == 'AI model: anthropic/claude-sonnet-5.5 · Instructions: workorder_v8'      # the original call's, not today's prompt
    assert L[3] == 'AI cost: $0.256, from the original call on October 26, 2026 · Cost per page: $0.0006'
    assert L[4] == 'OCR and Auto-Tagging: 6 pages are pictures with no text, so no text was added for them; the PDF had no tags and was tagged automatically.'
    assert L[5] == ('Total runtime: 3 min 52 s (intake 4 s, audit 37 s, AI call (a previous answer reused) 2 s, preparing the review 8 s, '
                    'applying and checks 3 min 2 s); the review time is not counted.')
    assert L[6] == 'Software: Python 3.13.9, pikepdf 10.5.1, pdfplumber 0.11.9, pypdfium2 5.7.1, Pillow 13.0.0, fontTools 4.62.1'
    bare = DL.about_lines({'run': {'response_from': 'hand-written.txt'}, 'raw_reply': '{}'})   # nothing recorded
    assert bare == ['Pages: not counted', 'Remediated: not recorded', 'AI model: not recorded · Instructions: not recorded',
                    'AI cost: not recorded · Cost per page: not recorded', 'OCR and Auto-Tagging: not recorded',
                    'Total runtime: not recorded', 'Software: not recorded']

def test_the_readme_says_what_ocr_and_auto_tagging_did():
    """Patrick, 2026-11-01: "OCR and Auto-Tagging" (was "Before remediation") in plain words, from OCR's own lists."""
    def line(**i): return DL._ocr_tagging({'intake': {'status': 'done', **i}})
    auto = {'steps': [{'step': 'autotag', 'error': None}]}
    assert line(triage={'counts': {'image-only': 1}}, ocr={'pages_with_ocr_text': [], 'image_pages_without_text': [1]}, tag_tree={'status': 'untagged'}, **auto) == \
        '1 page is a picture with no text, so no text was added for it; the PDF had no tags and was tagged automatically.'   # demo1, as Patrick wrote it
    assert line(triage={'counts': {'image-only': 1}}, ocr={'pages_with_ocr_text': [1]}, tag_tree={'status': 'placeholder'}, result={'pdf': 'x'}, plan={'autotag': True}) == \
        "1 page is a picture with no text, so OCR added its text; the PDF's tags held no text structure, so it was tagged again automatically."
    assert line(triage={'counts': {'image-only': 7}}, ocr={'pages_with_ocr_text': [1, 2, 3, 4, 5, 6], 'image_pages_without_text': [7]}, **auto) == \
        ('7 pages are pictures with no text: OCR added text to 6 of them, and no text was added for the other one; '
         'the PDF had no tags and was tagged automatically.')                                 # sojourners
    assert line(triage={'counts': {'image-only': 2}}, ocr={'pages_with_ocr_text': list(range(1, 11))}, **auto).startswith('OCR added text to 10 pages; ')   # FORCE_OCR: every page
    assert line(**auto) == 'every page has text, so no OCR was needed; the PDF had no tags and was tagged automatically.'
    assert line() == 'every page has text, so no OCR was needed; the PDF had no tags and was not tagged automatically.'
    assert DL._ocr_tagging({'intake': {'status': 'skipped', 'result': {'pdf': None}}}) == 'not needed: the PDF was already tagged.'
    assert DL._ocr_tagging({}) == 'not recorded'

def test_the_total_runtime_names_what_was_not_recorded():
    """A REVIEW=1 run applied before the stop kept its timings (demo1): only the apply's steps, and the AI call's own seconds."""
    rec = {'intake': {'status': 'done'}, 'run': {'seconds': 29.1, 'response_from': None},
           'timing_seconds': {'4/5 apply (no model)': 4.3, '4/5 verify (no model)': 8.9}}
    assert DL._runtime(rec) == ('Total runtime: at least 42 s (intake not recorded, audit not recorded, AI call 29 s, '
                                'applying and checks 13 s); the review time is not counted.')
    rec['timing_seconds'].update({'0/5 intake (local, no model)': 6.2, '1/5 audit (no model)': 18.0, '3/5 anthropic/claude-sonnet-5.5 via OpenRouter': 30.4,
                                  '2/5 cost estimate (no model)': 0.4, 'review: page images (no model)': 0.3})
    assert DL._runtime(rec) == ('Total runtime: 1 min 8 s (intake 6 s, audit 18 s, AI call 31 s, preparing the review less than 1 s, '
                                'applying and checks 13 s); the review time is not counted.')
    assert DL._runtime({'run': {}, 'timing_seconds': {'4/5 apply (no model)': 61}}) == \
        'Total runtime: at least 1 min 1 s (audit not recorded, AI call not recorded, applying and checks 1 min 1 s); the review time is not counted.'   # no intake: not a part
