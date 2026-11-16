"""webapp/lang.py: "Language of the Scanned Pages" (#45 D4, part 1 of #37, intake: suggest the OCR language; Patrick,
2026-11-06). New Run and New Batch no longer ask for an OCR language: "Get the Estimate" runs run_api.sh with ASK_LANG=1,
which stops (exit 4) before any OCR when pages need it, leaving intake.py --languages's _intake/languages.json. The run
page (or the PDF's row on the batch page) then asks, with intake's suggestion preselected and its evidence in plain words:

    kana → Japanese, Hangul → Korean, Vietnamese letters → Vietnamese, Latin only → English;
    Chinese characters with no kana, or more than one CJK script: nothing preselected (Japanese and Chinese are never
    guessed: a person picks Chinese (Traditional), Chinese (Simplified) or Japanese).

The full intake still checks every page to be OCR'd for Chinese, Japanese or Korean text: when it finds some and the
chosen language has no CJK pack, the PDF stops as before (intake.json, "OCR language needed"), and the same question comes
back with that evidence, offering only the CJK languages.

An answer of English leaves OCR_LANG unset (English is intake's own default), so the run is exactly what it was before
this question existed; any other answer sets OCR_LANG. The catalogue language (part 2 of #37) is not read here.
"""
import os, json
from . import books as BK

CJK = ('chi_tra', 'chi_sim', 'jpn', 'kor')
KEEP = 'keep'                                        # #121: "Keep the Existing OCR Text", the default answer to a re-OCR question
KEEP_FILE = 'reocr_choice.json'                      # _intake/<this>: the person kept the existing OCR text (the question goes)
CJK_KEEP_FILE = 'cjk_keep.json'                      # review 06 H1: _intake/<this>: pages kept at intake's CJK stop, by whom, when
SCRIPT_WORDS = {'kana': 'Japanese', 'hangul': 'Korean', 'han': 'Chinese characters', 'Latin': 'Latin script', 'Japanese': 'Japanese', 'Hiragana': 'Japanese', 'Katakana': 'Japanese', 'Korean': 'Korean',
                'Hangul': 'Korean', 'Han': 'Chinese characters', 'HanS': 'Chinese characters', 'HanT': 'Chinese characters',
                'Cyrillic': 'Cyrillic script', 'Greek': 'Greek script', 'Arabic': 'Arabic script', 'Hebrew': 'Hebrew script',
                'Devanagari': 'Devanagari script', 'Thai': 'Thai script'}

def _load(p):
    try: return json.load(open(p, encoding='utf-8'))
    except (OSError, ValueError): return None

def _n(k, one, many=None): return f'{k:,} {one if k == 1 else (many or one + "s")}'

def evidence(lj):
    """intake.py --languages's counts, in plain words."""
    e = lj.get('evidence') or {}
    out = []
    tl = e.get('text_layer') or {}
    if tl.get('kana'): out.append(f'The PDF\'s text holds {_n(tl["kana"], "Japanese kana character")}.')
    if tl.get('hangul'): out.append(f'The PDF\'s text holds {_n(tl["hangul"], "Korean (Hangul) letter")}.')
    if tl.get('han'): out.append(f'The PDF\'s text holds {_n(tl["han"], "Chinese character")}.')
    if (e.get('vietnamese_letters') or 0) >= 50: out.append(f'The PDF\'s text holds {_n(e["vietnamese_letters"], "Vietnamese letter")}.')
    if tl.get('latin') and not any(tl.get(k) for k in ('kana', 'hangul', 'han')) and lj.get('found') != 'other': out.append('The PDF\'s text is in Latin letters.')
    ss, n = e.get('scan_scripts') or {}, e.get('sampled_scans') or 0
    if n:
        seen = {}
        for k, v in ss.items(): seen[SCRIPT_WORDS.get(k, k)] = seen.get(SCRIPT_WORDS.get(k, k), 0) + v
        none = e.get('scans_with_no_text') or 0
        told = sum(seen.values())
        parts = [f'{v} look{"s" if v == 1 else ""} like {k}' for k, v in sorted(seen.items(), key=lambda x: -x[1])]
        if n - none - told > 0: parts.append(f'{n - none - told} {"has" if n - none - told == 1 else "have"} text whose script couldn\'t be told')
        if none: parts.append(f'{none} {"has" if none == 1 else "have"} no text to read (a picture or a cover)')
        out.append(f'Of the {_n(n, "scanned page")} checked, ' + '; '.join(parts) + '.')
    to = e.get('text_other_scripts') or {}
    if sum(to.values()) >= 50: out.append('The PDF\'s text holds ' + ', '.join(f'{_n(v, k.title() + " letter")}' for k, v in sorted(to.items(), key=lambda x: -x[1])[:3]) + '.')
    if lj.get('found') == 'other': out.append('A script other than Latin was found, so the language is asked rather than taken as English.')
    if lj.get('han_only'): out.append('Chinese characters with no Japanese kana can be Chinese or Japanese, so the language isn\'t chosen for you.')
    return out

def stopped_to_ask(j):
    """An estimate job that stopped to ask the language (run_api.sh ASK_LANG=1, exit 4)."""
    return bool(j) and j.get('kind') in ('estimate', 'batch-estimate') and j.get('status') == 'failed' and j.get('exit') == 4

def asks(R):
    """'cjk' (intake's CJK stop), 'first' (languages.json: pages need OCR, before intake), or None, from the folder alone
    (the home page's cached rows). A 'first' is a question only while the run's latest estimate stopped to ask
    (stopped_to_ask): the home page checks that against the jobs, question() too, so a later failure is never hidden."""
    ij = _load(os.path.join(R, '_intake', 'intake.json'))
    if ij: return 'cjk' if ij.get('status') == 'stopped' and any(f.get('what') == 'OCR language needed' for f in ij.get('flags') or []) \
        else 'reocr' if reocr_stopped(R, ij) or reocr_pending(R, ij) else None
    if os.path.isfile(os.path.join(R, 'record.json')): return None
    lj = _load(os.path.join(R, '_intake', 'languages.json')) or {}
    return 'first' if lj.get('needs_ocr') and lj.get('ask', True) else None       # ask: the language matters (intake.py)

def question(s, R, js=None, nm=None):
    """The question for a run folder, or None: {kind: first | cjk | reocr, pages, choices: [[value, name]], suggested, evidence}
    (a reocr question from intake's stop also carries stopped: True, and offers only the CJK languages).
    js: the run's jobs (oldest first); a 'first' question needs its latest estimate to have stopped to ask (exit 4).
    nm: the request's names snapshot, which asks Tesseract for its languages once per request (#93, review 04 M-A); the
    languages are asked only for a question there is (most runs have none), never before the checks that return None."""
    def choices_(): return [list(c) for c in BK.ocr_choices(nm.langs() if nm else BK.installed_langs(s))]
    if js is None:
        from . import jobs
        Ra = os.path.abspath(R)
        js = [j for j in jobs.all_jobs(s['jobs']) if j.get('dir') == Ra]
    ij = _load(os.path.join(R, '_intake', 'intake.json'))
    if ij:
        if reocr_stopped(R, ij):                       # review 04 H2: CJK under an OCR layer that lacks it stops the run
            choices = choices_(); n = ((ij.get('triage') or {}).get('counts') or {}).get('ocr-layer')
            return {'kind': 'reocr', 'stopped': True, 'pages': n,
                    'choices': [[KEEP, 'Keep the Existing OCR Text']] + ([c for c in choices if any(x in c[0] for x in CJK)] or choices),   # review 06 H1
                    'suggested': None, 'found': cjk_found(R, ij), 'needs_name': KEEP,
                    'evidence': ['The check read Chinese, Japanese or Korean characters on the page images below that the existing OCR text lacks. It can misread a map or a chart.',
                                 'Without that text, those pages would be sent to the AI as pictures of text, so the run stopped before any AI request.',
                                 'Chinese and Japanese are never guessed: choose the one the PDF is in.']}
        f = next((f for f in ij.get('flags') or [] if f.get('what') == 'OCR language needed'), None)
        if ij.get('status') != 'stopped' or not f:
            if not reocr_pending(R, ij): return None
            rs = ij['reocr_suggested']; n = ((ij.get('triage') or {}).get('counts') or {}).get('ocr-layer')
            ev = (['The page images show accents or other marks that the existing OCR text lacks.'] if 'diacritics' in rs.get('why', []) else []) \
                + (['The page images show Chinese, Japanese or Korean text that the existing OCR text lacks.'] if 'cjk' in rs.get('why', []) else [])
            return {'kind': 'reocr', 'pages': n, 'choices': [[KEEP, 'Keep the Existing OCR Text']] + choices_(), 'suggested': KEEP, 'evidence': ev}
        choices = choices_()
        cj = [c for c in choices if any(x in c[0] for x in CJK)]
        pages = f.get('pages') or []
        return {'kind': 'cjk', 'pages': len((ij.get('plan') or {}).get('ocr_pages') or []) or None, 'choices': cj or choices, 'suggested': None,
                'evidence': [f'Chinese, Japanese or Korean text was found on {"page" if len(pages) == 1 else "pages"} {", ".join(map(str, pages[:12]))}'
                             + (' and others' if len(pages) > 12 else '') + ' of the pages to be read by OCR, so a language with those characters is needed.',
                             'Chinese and Japanese are never guessed: choose the one the PDF is in.']}
    lj = _load(os.path.join(R, '_intake', 'languages.json'))
    if not lj or not lj.get('needs_ocr') or not lj.get('ask', True): return None
    est = [j for j in js if j.get('kind') in ('estimate', 'batch-estimate')]
    if not est or not stopped_to_ask(est[-1]): return None            # answered since, and that estimate failed otherwise
    sug = lj.get('suggestion'); choices = choices_()
    return {'kind': 'first', 'pages': lj.get('pages_to_ocr'), 'choices': choices,
            'suggested': sug if sug in [c[0] for c in choices] else None, 'evidence': evidence(lj)}

def env_for(lang, reocr=False):
    """The estimate's environment for an answer: English leaves OCR_LANG unset (intake's own default: the run is as before).
    reocr (#121): the existing OCR text is read again (REOCR=1), in that language."""
    return {'ESTIMATE': '1', **({} if lang == 'eng' else {'OCR_LANG': lang}), **({'REOCR': '1'} if reocr else {})}

def reocr_pending(R, ij):
    """#121: intake suggested reading the existing OCR text again, and nobody has answered: a run started from the home page
    (not a batch's PDF: the batch page doesn't ask this yet), its intake done without REOCR, nothing decided by the AI yet,
    and "Keep the Existing OCR Text" not chosen."""
    if not ij.get('reocr_suggested') or ij.get('status') != 'done' or (ij.get('settings') or {}).get('REOCR'): return False
    if '/batches/' in os.path.abspath(R).replace(os.sep, '/') + '/': return False
    if any(os.path.isfile(os.path.join(R, f)) for f in ('record.json', 'workorder.ai.json')): return False
    return not os.path.isfile(os.path.join(R, '_intake', KEEP_FILE))

def reocr_stopped(R, ij):
    """Review 04 H2 (interim, until #119): intake stopped because the page images show CJK text the existing OCR layer lacks
    ("OCR layer: CJK missing"), on a run started from the home page (a batch's PDF stops with a CHECK: the batch page doesn't
    ask this yet), not read again yet. The answer is a CJK language, read again with REOCR=1, or "Keep the Existing OCR Text"
    with a person's name (review 06 H1: keep_cjk, then the estimate again with KEEP_CJK_PAGES)."""
    if ij.get('status') != 'stopped' or (ij.get('settings') or {}).get('REOCR'): return False
    if not any(f.get('what') == 'OCR layer: CJK missing' for f in ij.get('flags') or []): return False
    return '/batches/' not in os.path.abspath(R).replace(os.sep, '/') + '/'

def cjk_found(R, ij):
    """The pages intake's CJK check stopped on, for the stopped question: [{page, characters, different, picture, image}]
    (image: the page image intake wrote, served at cjk-page-<page>.png on the run page)."""
    c = (ij.get('ocr_layer_test') or {}).get('cjk_on_images') or {}
    return [{'page': p, 'characters': (c.get('cjk_characters') or {}).get(str(p)), 'different': (c.get('cjk_distinct') or {}).get(str(p)),
             'picture': (c.get('found_by') or {}).get(str(p)) == 'picture-like page',
             'image': os.path.isfile(cjk_image(R, p))} for p in c.get('pages') or [] if isinstance(p, int)]

def cjk_image(R, page):
    """The file of a stop page's image (intake.py CJK_STOP_IMAGES): built from an integer page, never from a request's text."""
    return os.path.join(R, '_intake', f'cjk_page_{int(page)}.png')

def keep_cjk(R, by):
    """Review 06 H1: "Keep the Existing OCR Text" at intake's CJK stop: the stopped pages (with any kept before) are recorded
    with the person's name, the date and the check's counts in _intake/cjk_keep.json; the estimate runs again with
    KEEP_CJK_PAGES naming them, so the CJK check skips those pages. Returns the pages."""
    import datetime
    ij = _load(os.path.join(R, '_intake', 'intake.json')) or {}
    by = ' '.join(str(by or '').split())[:80]
    if not by: raise ValueError('Enter your name in "Your Name" to keep the existing OCR text.')
    old = _load(os.path.join(R, '_intake', CJK_KEEP_FILE)) or {}
    pages = sorted({int(p) for p in (ij.get('settings') or {}).get('KEEP_CJK_PAGES') or []} | {f['page'] for f in cjk_found(R, ij)})
    counts = {**(old.get('counts') or {}), **{str(f['page']): {'cjk_characters': f['characters'], 'cjk_distinct': f['different']} for f in cjk_found(R, ij)}}
    p = os.path.join(R, '_intake', CJK_KEEP_FILE); tmp = p + '.tmp'
    json.dump({'pages': pages, 'by': by, 'at': datetime.datetime.now().isoformat(timespec='seconds'), 'counts': {k: v for k, v in counts.items() if int(k) in pages}},
              open(tmp, 'w', encoding='utf-8'), indent=1, ensure_ascii=False); os.replace(tmp, p)
    return pages

def keep_layer(R):
    """#121: "Keep the Existing OCR Text": recorded beside intake's record, so the question is not asked again."""
    import datetime
    p = os.path.join(R, '_intake', KEEP_FILE); tmp = p + '.tmp'
    json.dump({'choice': KEEP, 'written': datetime.datetime.now().isoformat(timespec='seconds')}, open(tmp, 'w', encoding='utf-8')); os.replace(tmp, p)

def check(s, R, lang):
    """The answer, checked against the question this run asks now; raises ValueError in plain words."""
    q = question(s, R)
    if not q: raise ValueError('This PDF isn\'t waiting for a language.')
    names = dict((c[0], c[1]) for c in q['choices'])
    if lang not in names: raise ValueError('Choose a language from the list.')
    return names[lang]
