"""test_run_api_language.py: run_api.sh's language step (#118, step 3c) with a saved reply (REPLY=, as FROM= gives each
book): never a request (review 02, M3). Without saved language decisions the step is not run and says so; with them
(LANG_REPLY=) they are applied by form at no cost, and the record keeps them. A synthetic tagged book, veraPDF off, no
key and no network (a request would fail loudly).

    python -m pytest tests/test_run_api_language.py -q
"""
import os, sys, json, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import langpdf  # noqa: E402
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def run_api(tmp_path, runs=None, **extra):
    src = langpdf.build(str(tmp_path / 'book.pdf'), runs or [{'font': 'F3', 'text': 'The temple of Onjōji and mappō.'}])
    wo = {'document': {'lang': 'en', 'title': 'Synthetic language test'}}
    (tmp_path / 'reply.txt').write_text(json.dumps({'model': 'anthropic/claude-sonnet-5.5', 'choices': [{'message': {'content': json.dumps(wo)}, 'finish_reason': 'stop'}],
                                                    'usage': {'prompt_tokens': 1000, 'completion_tokens': 100, 'cost': 0.3}}))
    env = dict(os.environ, VERAPDF='off', RUN_DIR=str(tmp_path / 'run'), REPLY=str(tmp_path / 'reply.txt'), INTAKE='off', OPENROUTER_API_KEY='test-not-a-key',
               HTTPS_PROXY='http://127.0.0.1:9', HTTP_PROXY='http://127.0.0.1:9', https_proxy='http://127.0.0.1:9', http_proxy='http://127.0.0.1:9',   # no network
               RUNS_DIR=str(tmp_path / 'runs'), PATH=os.path.dirname(sys.executable) + os.pathsep + os.environ.get('PATH', ''), **extra)
    for k in ('AUTO', 'FROM', 'LANG_REPLY', 'LANG_TAGS', 'REVIEW'):
        if k not in extra: env.pop(k, None)
    r = subprocess.run(['bash', 'run_api.sh', src, 'book', 'l1'], cwd=HERE, env=env, capture_output=True, text=True, timeout=600)
    return r, tmp_path / 'run'

def test_a_saved_reply_never_starts_the_language_step(tmp_path):
    r, R = run_api(tmp_path)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-2000:]
    assert 'language tags: not run' in r.stdout and 'language tags via OpenRouter' not in r.stdout
    rec = json.load(open(R / 'record.json'))
    assert 'language_run' not in rec and 'language_parts' not in rec['workorder']           # the step never ran: no forms either

def test_saved_language_decisions_are_applied_at_no_cost(tmp_path):
    saved = {'schema': 'language-run/1', 'model': 'anthropic/claude-sonnet-5.5', 'cost_usd': 0.05,
             'decisions': {'marks|Onjōji': {'lang': 'ja-Latn', 'confidence': 'high', 'why': 'language'},
                           'hawaiian|mappō': {'lang': 'ja-Latn', 'confidence': 'high', 'why': 'language'}}}
    (tmp_path / 'book.language.json').write_text(json.dumps(saved))
    r, R = run_api(tmp_path, LANG_REPLY=str(tmp_path / 'book.language.json'), LANG_TAGS='off')
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-2000:]
    assert 'language tags: saved decisions (no cost)' in r.stdout
    rec = json.load(open(R / 'record.json'))
    assert rec['language_run']['replay']['used'] == 2 and rec['cost_total_usd'] == 0.3      # the saved reply's own; the language replay adds nothing
    sys.path.insert(0, HERE); from lib import langreq
    assert sorted(p['form'] for p in langreq.expand(rec['workorder']['language_parts'])) == ['Onjōji', 'mappō']
    assert rec['apply']['language_parts']['split'] == 2
    md = open(R / 'review.md', encoding='utf-8').read()
    assert '. Language Tags' in md and '| Japanese (Romanized) | 2 | 2 |' in md and '- "Onjōji": Japanese (Romanized)' in md
    assert '| Language tags hold their words | OK | 2 tags checked · 0 not matching their words or language |' in md
    g = rec['glance']; lang_line = next(x for x in g['ship'] if x['what'] == 'Language tags')
    assert lang_line['ok'] is False and lang_line['text'].startswith('Not Reviewed (')          # not reviewed: never Ready

def test_an_answer_the_reply_check_drops_is_kept_and_counted(tmp_path):
    """#137 (dropped language answers): a saved reply whose answer for Onjōji gives a tag the pipeline cannot write. The
    replay keeps the dropped answer with its code and form in the record, the form carries its reason, and review.md
    counts it in plain words (review 02, L1: no codes)."""
    reply = {'decisions': [{'id': '1', 'form': 'Onjōji', 'lang': 'xx-Zzzz', 'confidence': 'high', 'why': 'language'},
                           {'id': '2', 'form': 'mappō', 'lang': 'ja-Latn', 'confidence': 'high', 'why': 'language'}]}
    saved = {'schema': 'language-run/1', 'model': 'anthropic/claude-sonnet-5.5', 'cost_usd': 0.05, 'decisions': {},
             'requests': [{'n': 1, 'sha256': 'x', 'ids': ['1', '2'], 'id_keys': {'1': 'marks|Onjōji', '2': 'hawaiian|mappō'},
                           'text': json.dumps(reply), 'finish': 'stop'}]}
    (tmp_path / 'book.language.json').write_text(json.dumps(saved))
    r, R = run_api(tmp_path, LANG_REPLY=str(tmp_path / 'book.language.json'), LANG_TAGS='off')
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-2000:]
    rec = json.load(open(R / 'record.json'))
    d = [x for x in rec['language_run']['dropped'] if x.get('code') == 'tag']
    assert d and d[0]['key'] == 'marks|Onjōji' and d[0]['form'] == 'Onjōji' and d[0]['lang'] == 'xx-Zzzz' and d[0]['echo'] == 'Onjōji'
    forms = {f['form']: f for f in rec['workorder']['language_parts']['forms']}
    assert forms['Onjōji'].get('no_answer') == 'tag' and 'no_answer' not in forms['mappō']
    md = open(R / 'review.md', encoding='utf-8').read()
    assert '**No AI answer (1 word form):** the AI gave a language that cannot be written into the PDF 1.' in md and 'xx-Zzzz' not in md

def test_hawaiian_lines_are_listed_for_the_hawaiian_reader(tmp_path):
    """review 08, H2: a line tagged Hawaiian by the fixed rule on a page read by the AI is listed in review.md's Language
    Tags section, and counted by the check row. The page reading comes with the saved reply's work order here."""
    src = langpdf.build(str(tmp_path / 'book.pdf'), [{'text': 'Ua hele mai ka wahine i ka hale'}, {'text': 'The house stood on the hill above the bay'}])
    wo = {'document': {'lang': 'en', 'title': 'Synthetic Hawaiian test'},
          'page_readings': [{'page': 1, 'text': 'Ua hele mai ka wahine i ka hale The house stood on the hill above the bay'}]}
    (tmp_path / 'reply.txt').write_text(json.dumps({'model': 'anthropic/claude-sonnet-5.5', 'choices': [{'message': {'content': json.dumps(wo)}, 'finish_reason': 'stop'}],
                                                    'usage': {'prompt_tokens': 1000, 'completion_tokens': 100, 'cost': 0.3}}))
    env = dict(os.environ, VERAPDF='off', RUN_DIR=str(tmp_path / 'run'), REPLY=str(tmp_path / 'reply.txt'), INTAKE='off', OPENROUTER_API_KEY='test-not-a-key',
               HTTPS_PROXY='http://127.0.0.1:9', HTTP_PROXY='http://127.0.0.1:9', https_proxy='http://127.0.0.1:9', http_proxy='http://127.0.0.1:9',
               RUNS_DIR=str(tmp_path / 'runs'), PATH=os.path.dirname(sys.executable) + os.pathsep + os.environ.get('PATH', ''))
    for k in ('AUTO', 'FROM', 'LANG_REPLY', 'LANG_TAGS', 'REVIEW'): env.pop(k, None)
    r = subprocess.run(['bash', 'run_api.sh', src, 'book', 'l1'], cwd=HERE, env=env, capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-2000:]
    md = open(tmp_path / 'run' / 'review.md', encoding='utf-8').read()
    assert '**Tagged Hawaiian by a fixed rule on pages read by the AI (1):**' in md and '- "Ua hele mai ka wahine ka hale" · PDF 1' in md
    assert '1 tags checked (1 Hawaiian lines on pages read by the AI) · 0 not matching their words or language' in md

def line_of(R):
    return next(l for l in open(R / 'review.md', encoding='utf-8').read().splitlines() if 'Language Tags:' in l)

def test_the_publishers_own_tags_count_as_candidates(tmp_path):
    """review 19, L3: a PDF whose only other-language text is the publisher's own tag (fr-FR on English words: no other
    candidate), run with the step off, reads Not Done, never Not Applicable."""
    r, R = run_api(tmp_path, runs=[{'lang': 'en-US', 'span_lang': 'fr-FR', 'text': 'Copyright notice for this book'},
                                   {'lang': 'en-US', 'text': 'Plain English text stays as it is.'}], LANG_TAGS='off')
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-2000:]
    rec = json.load(open(R / 'record.json'))
    assert rec['language_status'] == {'candidates': 1, 'state': 'off'}
    assert line_of(R) == '- Language Tags: Not Done (the language step was turned off)'

def test_not_applicable_only_when_counted_and_none_and_not_checked_otherwise(tmp_path):
    """Patrick, 2026-11-14 (fail closed): counted and 0 reads Not Applicable; when the count can't be made (the audit's
    lang_candidates.json missing) the line reads Not Done (not checked)."""
    r, R = run_api(tmp_path, runs=[{'lang': 'en-US', 'text': 'Plain English text stays as it is.'}], LANG_TAGS='off', KEEP='1')
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-2000:]
    assert json.load(open(R / 'record.json'))['language_status'] == {'candidates': 0, 'state': 'off'}
    assert line_of(R) == '- ✓ Language Tags: Not Applicable'
    A = R / '_audit'; os.remove(A / 'lang_candidates.json')
    pdf = next(p for p in R.glob('*_remediated.pdf'))
    r2 = subprocess.run([sys.executable, 'report.py', str(R), str(A), f'--pdf={pdf}', f'--input={tmp_path / "book.pdf"}', '--lang-tags=off', '--keep'],
                        cwd=HERE, env=dict(os.environ, VERAPDF='off'), capture_output=True, text=True, timeout=300)
    assert r2.returncode == 0, r2.stdout[-2000:] + r2.stderr[-2000:]
    assert json.load(open(R / 'record.json'))['language_status'] == {'candidates': None, 'state': 'off'}
    assert line_of(R) == '- Language Tags: Not Done (not checked)'

def test_review_md_names_a_charge_not_known_apart_from_the_cost(tmp_path):
    """#135 (parallel requests), review 02 M2: a language request an interruption left in flight counts at its worst case
    toward the limit; review.md's run line names it apart, never as money spent."""
    r, R = run_api(tmp_path, runs=[{'lang': 'en-US', 'text': 'Plain English text stays as it is.'}], LANG_TAGS='off', KEEP='1')
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-2000:]
    (R / 'language_run.json').write_text(json.dumps({'schema': 'language-run/1', 'requests': [], 'decisions': {}, 'cost_usd': 0.25,
                                                     'stopped_in_flight': [{'n': 2, 'worst_usd': 0.5, 'stopped': True}]}))
    pdf = next(p for p in R.glob('*_remediated.pdf'))
    r2 = subprocess.run([sys.executable, 'report.py', str(R), str(R / '_audit'), f'--pdf={pdf}', f'--input={tmp_path / "book.pdf"}', '--lang-tags=off', '--keep'],
                        cwd=HERE, env=dict(os.environ, VERAPDF='off'), capture_output=True, text=True, timeout=300)
    assert r2.returncode == 0, r2.stdout[-2000:] + r2.stderr[-2000:]
    md = open(R / 'review.md', encoding='utf-8').read(); rec = json.load(open(R / 'record.json'))
    assert ' · up to $0.500 more for 1 AI request(s) of the language step or the page readings whose charge is not known' in md
    assert rec['language_run']['stopped_in_flight'][0]['worst_usd'] == 0.5
    assert round(rec['cost_total_usd'] - ((rec['run'].get('usage') or {}).get('cost_usd') or 0), 6) == 0.25        # the known cost only
