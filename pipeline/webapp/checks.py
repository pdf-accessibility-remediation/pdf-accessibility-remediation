"""webapp/checks.py: the setup status the app checks at start (docs/setup.md), each item ready or missing with its fix.

Required (the app does not start without them): the Python libraries, veraPDF (a real version line: vera.py --check's
exit 0 for VERAPDF=off does not count) and Java. Needed only for untagged books (a warning; New run refuses an untagged
book until they are installed): OCRmyPDF, Tesseract and its language packs. The API key is not checked here: the
estimate checks it. Every check runs in the environment the children get (config.child_env).
"""
import os, re, sys, subprocess
from . import config

MAC = sys.platform == 'darwin'
SCRIPTS = ('Latin', 'Japanese', 'Japanese_vert', 'Hangul', 'Hangul_vert', 'HanS', 'HanS_vert', 'HanT', 'HanT_vert')
VERSION = re.compile(r'^veraPDF \S+$')

def _run(argv, env, timeout=120):
    try:
        r = subprocess.run(argv, cwd=config.PIPELINE, env=env, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout or '') + (r.stderr or '')
    except (OSError, subprocess.TimeoutExpired) as e: return None, str(e)

def _first(text): return next((l.strip() for l in text.splitlines() if l.strip()), '')

def check(s):
    """[{id, name, required, ok, detail, fix}] for the page header; the app refuses to start when a required one is not ok."""
    env = config.child_env(s)
    out = []
    def item(id, name, required, ok, detail, fix): out.append({'id': id, 'name': name, 'required': required, 'ok': bool(ok), 'detail': detail, 'fix': None if ok else fix})
    rc, t = _run([sys.executable, '-c', 'import pikepdf, pdfplumber, pypdfium2, PIL, fontTools.ttLib'], env)
    item('python', 'Python libraries', True, rc == 0, f'Python {sys.version.split()[0]}' if rc == 0 else _first(t.splitlines()[-1] if t.strip() else 'not importable'),
         'from pipeline/: python3 -m pip install -r requirements.txt')
    rc, t = _run([sys.executable, 'vera.py', '--check'], env)
    line = _first(t)
    item('verapdf', 'veraPDF', True, rc == 0 and VERSION.match(line), line or 'no answer',
         'from pipeline/: bash verapdf/install.sh, then put the launcher path in webapp/settings.local.json as "tools": {"VERAPDF": "…"} (or export VERAPDF)')
    rc, t = _run(['java', '-version'], env)
    item('java', 'Java', True, rc == 0, _first(t) if rc == 0 else 'not found on the PATH the app gives its children',
         ('brew install openjdk@21, then add /opt/homebrew/opt/openjdk@21/bin to "tools": {"path_prepend": […]} in webapp/settings.local.json'
          if MAC else 'sudo apt install openjdk-17-jre-headless'))
    ocr_fix = 'brew install ocrmypdf tesseract-lang' if MAC else 'sudo apt install ocrmypdf tesseract-ocr (and the language packs, docs/setup.md)'
    rc, t = _run(['ocrmypdf', '--version'], env)
    item('ocrmypdf', 'OCRmyPDF (untagged books only)', False, rc == 0, f'OCRmyPDF {_first(t)}' if rc == 0 else 'not found', ocr_fix)
    rc, t = _run(['tesseract', '--version'], env)
    item('tesseract', 'Tesseract (untagged books only)', False, rc == 0, _first(t) if rc == 0 else 'not found', ocr_fix)
    langs = []
    if rc == 0:
        rc2, t2 = _run(['tesseract', '--list-langs'], env)
        langs = [l.strip() for l in t2.splitlines()[1:] if l.strip()] if rc2 == 0 else []
    have = {l.split('/')[-1] for l in langs}
    missing = [x for x in SCRIPTS if x not in have]
    ok = 'eng' in have and not missing
    item('tesseract_langs', 'Tesseract language packs (untagged books only)', False, ok,
         (f'{len(langs)} installed' + (f'; missing: {", ".join((["eng"] if "eng" not in have else []) + missing)}' if not ok else '')) if langs else 'none found',
         'brew install tesseract-lang' if MAC else 'docs/setup.md, step 2 (the tesseract-ocr-script-* packages)')
    return out

def required_missing(items): return [x for x in items if x['required'] and not x['ok']]
def untagged_ready(items): return all(x['ok'] for x in items if x['id'] in ('ocrmypdf', 'tesseract', 'tesseract_langs'))
