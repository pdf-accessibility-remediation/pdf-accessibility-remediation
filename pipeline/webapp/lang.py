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
SCRIPT_WORDS = {'Latin': 'Latin script', 'Japanese': 'Japanese', 'Hiragana': 'Japanese', 'Katakana': 'Japanese', 'Korean': 'Korean',
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
    if tl.get('latin') and not any(tl.get(k) for k in ('kana', 'hangul', 'han')): out.append('The PDF\'s text is in Latin letters only.')
    ss, n = e.get('scan_scripts') or {}, e.get('sampled_scans') or 0
    if n:
        seen = {}
        for k, v in ss.items(): seen[SCRIPT_WORDS.get(k, k)] = seen.get(SCRIPT_WORDS.get(k, k), 0) + v
        if seen: out.append(f'Of the {_n(n, "scanned page")} checked, ' + '; '.join(f'{v} look{"s" if v == 1 else ""} like {k}' for k, v in
                                                                           sorted(seen.items(), key=lambda x: -x[1])) + '.')
        else: out.append(f'The script of the {_n(n, "scanned page")} checked couldn\'t be told.')
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
    if ij: return 'cjk' if ij.get('status') == 'stopped' and any(f.get('what') == 'OCR language needed' for f in ij.get('flags') or []) else None
    if os.path.isfile(os.path.join(R, 'record.json')): return None
    return 'first' if (_load(os.path.join(R, '_intake', 'languages.json')) or {}).get('needs_ocr') else None

def question(s, R, js=None):
    """The question for a run folder, or None: {kind: first | cjk, pages, choices: [[value, name]], suggested, evidence}.
    js: the run's jobs (oldest first); a 'first' question needs its latest estimate to have stopped to ask (exit 4)."""
    if js is None:
        from . import jobs
        Ra = os.path.abspath(R)
        js = [j for j in jobs.all_jobs(s['jobs']) if j.get('dir') == Ra]
    ij = _load(os.path.join(R, '_intake', 'intake.json'))
    choices = [list(c) for c in BK.ocr_choices(BK.installed_langs(s))]
    if ij:
        f = next((f for f in ij.get('flags') or [] if f.get('what') == 'OCR language needed'), None)
        if ij.get('status') != 'stopped' or not f: return None
        cj = [c for c in choices if any(x in c[0] for x in CJK)]
        pages = f.get('pages') or []
        return {'kind': 'cjk', 'pages': len((ij.get('plan') or {}).get('ocr_pages') or []) or None, 'choices': cj or choices, 'suggested': None,
                'evidence': [f'Chinese, Japanese or Korean text was found on {"page" if len(pages) == 1 else "pages"} {", ".join(map(str, pages[:12]))}'
                             + (' and others' if len(pages) > 12 else '') + ' of the pages to be read by OCR, so a language with those characters is needed.',
                             'Chinese and Japanese are never guessed: choose the one the PDF is in.']}
    lj = _load(os.path.join(R, '_intake', 'languages.json'))
    if not lj or not lj.get('needs_ocr'): return None
    est = [j for j in js if j.get('kind') in ('estimate', 'batch-estimate')]
    if not est or not stopped_to_ask(est[-1]): return None            # answered since, and that estimate failed otherwise
    sug = lj.get('suggestion')
    return {'kind': 'first', 'pages': lj.get('pages_to_ocr'), 'choices': choices,
            'suggested': sug if sug in [c[0] for c in choices] else None, 'evidence': evidence(lj)}

def env_for(lang):
    """The estimate's environment for an answer: English leaves OCR_LANG unset (intake's own default: the run is as before)."""
    return {'ESTIMATE': '1', **({} if lang == 'eng' else {'OCR_LANG': lang})}

def check(s, R, lang):
    """The answer, checked against the question this run asks now; raises ValueError in plain words."""
    q = question(s, R)
    if not q: raise ValueError('This PDF isn\'t waiting for a language.')
    names = dict((c[0], c[1]) for c in q['choices'])
    if lang not in names: raise ValueError('Choose a language from the list.')
    return names[lang]
