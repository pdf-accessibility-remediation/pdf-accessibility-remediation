"""test_support.py: the files the pipeline must refuse (#69): PDF 2.0, namespaced tags, a PDF locked with a password, a damaged file.

    python -m pytest tests/test_support.py -q

- lib/support.py's rule on its own: PDF 2.0 (in the header, or in the catalog's /Version over a 1.7 header) and a tag tree
  with /Namespaces are refused, a plain PDF 1.7 is not, and ALLOW_PDF20=1 lets both through.
- The scripts on hand-made one-page PDFs: intake.py stops a locked file (exit 3, intake.json "stopped") and a damaged one
  (exit 1, "failed"); audit.py and apply.py, run with no intake before them, stop the same files with the same words and
  write nothing; run_api.sh stops a locked file before the cost estimate, with or without intake.
No book content; nothing is sent anywhere; veraPDF is off.
"""
import os, sys, io, json, subprocess
import pikepdf
from lib import support

PIPE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def pdf_file(path, version=None, catalog_version=None, namespaces=False, password=None):
    """A one-page PDF with a small tag tree (one empty Document element), so only the check under test can stop it."""
    pdf = pikepdf.new(); pdf.add_blank_page(page_size=(432, 576))
    root = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructTreeRoot))
    root.K = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructElem, S=pikepdf.Name.Document, P=root, K=pikepdf.Array()))
    if namespaces:
        root.Namespaces = pikepdf.Array([pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.Namespace,
                                                                              NS=pikepdf.String('http://iso.org/pdf2/ssn')))])
    pdf.Root.StructTreeRoot = root; pdf.Root.MarkInfo = pikepdf.Dictionary(Marked=True)
    if catalog_version: pdf.Root.Version = pikepdf.Name('/' + catalog_version)
    kw = {'encryption': pikepdf.Encryption(owner='o', user=password)} if password else {'deterministic_id': True}
    pdf.save(str(path), min_version=version or '1.7', **kw)
    return str(path)

def damaged_file(path):
    """The first 20 bytes of a good PDF: qpdf can't rebuild it (a file cut in half it can, and opens)."""
    b = io.BytesIO(); p = pikepdf.new(); p.add_blank_page(); p.save(b)
    open(path, 'wb').write(b.getvalue()[:20]); return str(path)

def reason(path):
    with pikepdf.open(path) as pdf: return support.unsupported(pdf)

def run(script, *args, **env):
    e = dict(os.environ, VERAPDF='off', **env); e.pop('ALLOW_PDF20', None)
    return subprocess.run([sys.executable, os.path.join(PIPE, script), *map(str, args)], env=e, capture_output=True, text=True, timeout=300)

# ---- lib/support.py
def test_pdf_17_is_supported(tmp_path, monkeypatch):
    monkeypatch.delenv('ALLOW_PDF20', raising=False)
    p = pdf_file(tmp_path / 'a.pdf')
    assert reason(p) is None
    with pikepdf.open(p) as pdf: assert support.version(pdf) == '1.7'

def test_pdf_20_is_refused(tmp_path, monkeypatch):
    monkeypatch.delenv('ALLOW_PDF20', raising=False)
    assert reason(pdf_file(tmp_path / 'a.pdf', version='2.0')).startswith('PDF 2.0: not supported yet')

def test_a_catalog_version_later_than_the_header_counts(tmp_path, monkeypatch):
    monkeypatch.delenv('ALLOW_PDF20', raising=False)
    p = pdf_file(tmp_path / 'a.pdf', catalog_version='2.0')
    with pikepdf.open(p) as pdf: assert str(pdf.pdf_version) == '1.7' and support.version(pdf) == '2.0'
    assert reason(p).startswith('PDF 2.0: ')

def test_namespaced_tags_in_a_17_file_are_refused(tmp_path, monkeypatch):
    monkeypatch.delenv('ALLOW_PDF20', raising=False)
    assert reason(pdf_file(tmp_path / 'a.pdf', namespaces=True)).startswith('namespaced tags (PDF 2.0 tagging in a PDF 1.7 file): ')

def test_allow_pdf20_lets_both_through(tmp_path, monkeypatch):
    monkeypatch.setenv('ALLOW_PDF20', '1')
    assert reason(pdf_file(tmp_path / 'a.pdf', version='2.0')) is None
    assert reason(pdf_file(tmp_path / 'b.pdf', namespaces=True)) is None

# ---- intake.py
def intake_json(d): return json.load(open(os.path.join(d, 'intake.json'), encoding='utf-8'))

def test_intake_stops_a_locked_pdf(tmp_path):
    r = run('intake.py', pdf_file(tmp_path / 'a.pdf', password='u'), tmp_path / 'in')
    assert r.returncode == 3, r.stdout + r.stderr
    j = intake_json(tmp_path / 'in')
    assert j['status'] == 'stopped' and j['summary'] == support.LOCKED
    assert not os.path.exists(tmp_path / 'in' / 'intake.pdf')

def test_intake_fails_on_a_damaged_pdf(tmp_path):
    r = run('intake.py', damaged_file(tmp_path / 'a.pdf'), tmp_path / 'in')
    assert r.returncode == 1 and 'Traceback' not in r.stderr, r.stdout + r.stderr
    j = intake_json(tmp_path / 'in')
    assert j['status'] == 'failed' and j['summary'].startswith('the PDF could not be opened (')

def test_intake_stops_a_pdf_20(tmp_path):
    r = run('intake.py', pdf_file(tmp_path / 'a.pdf', version='2.0'), tmp_path / 'in')
    assert r.returncode == 3, r.stdout + r.stderr
    j = intake_json(tmp_path / 'in')
    assert j['status'] == 'stopped' and j['summary'].startswith('PDF 2.0: ')
    assert [f['what'] for f in j['flags']] == ['Not supported yet: PDF 2.0']

# ---- audit.py and apply.py (a run with INTAKE=off, or a reused audit or reply)
def audit_stops(tmp_path, src, code, words):
    out = tmp_path / 'audit'
    r = run('audit.py', src, out)
    assert r.returncode == code and words in r.stderr and 'Traceback' not in r.stderr, r.stdout + r.stderr
    assert not os.path.exists(out)                    # nothing written: not even the figures folder

def test_audit_stops_a_pdf_20(tmp_path):
    audit_stops(tmp_path, pdf_file(tmp_path / 'a.pdf', version='2.0'), 3, 'audit: stopped: PDF 2.0: ')

def test_audit_stops_namespaced_tags(tmp_path):
    audit_stops(tmp_path, pdf_file(tmp_path / 'a.pdf', namespaces=True), 3, 'audit: stopped: namespaced tags')

def test_audit_stops_a_locked_pdf(tmp_path):
    audit_stops(tmp_path, pdf_file(tmp_path / 'a.pdf', password='u'), 3, 'audit: stopped: ' + support.LOCKED)

def test_audit_fails_on_a_damaged_pdf(tmp_path):
    audit_stops(tmp_path, damaged_file(tmp_path / 'a.pdf'), 1, 'audit: failed: the PDF could not be opened (')

def apply_stops(tmp_path, src, code, words):
    wo = tmp_path / 'workorder.json'; wo.write_text(json.dumps({'schema': 'workorder/0.1'}))
    out = tmp_path / 'out.pdf'
    r = run('apply.py', src, wo, out)
    assert r.returncode == code and words in r.stderr and 'Traceback' not in r.stderr, r.stdout + r.stderr
    assert not os.path.exists(out) and not os.path.exists(str(out) + '.log.json')

def test_apply_stops_a_locked_pdf(tmp_path):
    apply_stops(tmp_path, pdf_file(tmp_path / 'a.pdf', password='u'), 3, 'apply: stopped: ' + support.LOCKED)

def test_apply_fails_on_a_damaged_pdf(tmp_path):
    apply_stops(tmp_path, damaged_file(tmp_path / 'a.pdf'), 1, 'apply: failed: the PDF could not be opened (')

def test_apply_stops_a_pdf_20(tmp_path):
    apply_stops(tmp_path, pdf_file(tmp_path / 'a.pdf', version='2.0'), 3, 'apply: stopped: PDF 2.0: ')

# ---- run_api.sh: a locked PDF stops before the cost estimate, with or without intake
def run_api(src, R, **env):
    e = dict(os.environ, VERAPDF='off', RUN_DIR=str(R), PATH=os.path.dirname(sys.executable) + os.pathsep + os.environ.get('PATH', ''), **env)
    for k in ('INTAKE_REUSE', 'ALLOW_PDF20', 'REPLY', 'FROM', 'REVIEW', 'ESTIMATE', 'AUTO', 'DECIDE'):
        if k not in env: e.pop(k, None)
    return subprocess.run(['bash', 'run_api.sh', str(src), 'book', 'l1'], cwd=PIPE, env=e, capture_output=True, text=True, timeout=300)

def test_run_api_stops_a_locked_pdf_at_intake(tmp_path):
    R = tmp_path / 'run'
    r = run_api(pdf_file(tmp_path / 'a.pdf', password='u'), R)
    assert r.returncode == 3, r.stdout + r.stderr
    assert 'intake: stopped: ' + support.LOCKED in r.stdout and 'cost estimate' not in r.stdout
    assert not any(os.path.exists(R / f) for f in ('request.json', 'run.json', '_audit'))

def test_run_api_stops_a_locked_pdf_at_audit_without_intake(tmp_path):
    R = tmp_path / 'run'
    r = run_api(pdf_file(tmp_path / 'a.pdf', password='u'), R, INTAKE='off')
    assert r.returncode == 3, r.stdout + r.stderr
    assert 'audit: stopped: ' + support.LOCKED in r.stderr and 'cost estimate' not in r.stdout
    assert not any(os.path.exists(R / f) for f in ('request.json', 'run.json', '_intake'))
