"""test_review_group_approval.py: the review page's group approval (#124) and its record, with the rows the reading rule
decided (#123). Synthetic work orders and one synthetic book; no network.

    python -m pytest tests/test_review_group_approval.py -q

#124's checks: rows are grouped only when the reading beside the characters and the AI name the same language, never on
none, mixed or disagreeing evidence (nor low confidence, a publisher's tag or a mixed answer); "Approve All Shown"
approves only the rows its rules allow; a group approval on a row that doesn't qualify decides nothing; each group
approval is recorded with its evidence and language and listed in review.md; single decisions are unchanged.
"""
import os, sys, json, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import langpdf  # noqa: E402
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from review import core  # noqa: E402
from lib import langreq  # noqa: E402

DIGEST = {'source': {'pages': 3, 'file': 'b.pdf'}}

def rd(lang, text, langs=None, with_=1, places=1):
    return {'lang': lang, 'langs': langs if langs is not None else ([lang] if lang else []), 'text': text, 'with': with_, 'places': places, 'back': 0}

def form(f, group, cls, lang=None, conf=None, why='language', current=None, reading=None, rule=None, person=None):
    return {'key': f'{group}|{f}', 'form': f, 'group': group, 'class': cls, 'lang': lang, 'confidence': conf, 'why': why,
            'tag': bool(lang and conf in ('high', 'medium') and group != 'existing'), **({'current': current} if current else {}),
            **({'reading': reading} if reading else {}), **({'rule': rule} if rule else {}), **({'person': True} if person else {}), 'places': 1}

HAN = ['cjk:han_only']
FORMS = [form('極楽', 'cjk', HAN, 'ja', 'high', reading=rd('ja', 'gokuraku')),                       # 0 matches: the AI's
         form('中文', 'cjk', HAN, 'zh', 'high', reading=rd('zh', 'zhongwen'), rule='reading'),          # 1 matches: the rule's (#123)
         form('地獄', 'cjk', HAN, 'zh', 'high', reading=rd('ja', 'jigoku')),                            # 2 disagrees
         form('浄土', 'cjk', HAN, 'ja', 'high', reading=rd(None, 'jōdo', ['ja', 'zh'])),                # 3 mixed evidence
         form('仏教', 'cjk', HAN, 'ja', 'high'),                                                         # 4 no evidence
         form('念仏', 'cjk', HAN, 'ja', 'low', reading=rd('ja', 'nenbutsu'), person=True),              # 5 low: not tagged
         form('禅宗', 'cjk', HAN, 'ja', 'medium', reading=rd('ja', 'zenshū')),                          # 6 medium, matches
         form('天台', 'cjk', HAN, 'ja', 'high', why='varies', reading=rd('ja', 'tendai')),              # 7 a mixed answer
         form('漢字', 'existing', ['existing'], 'ja', 'high', current='ja', reading=rd('ja', 'kanji'), person=True),   # 8 a publisher's tag
         form('mappō', 'marks', ['marks'], 'ja-Latn', 'high'),                                          # 9 Approve All Shown's
         form('漢文', 'cjk', HAN, 'zh-Hant', 'high', reading=rd('zh', 'hanwen'))]                       # 10 zh-Hant matches zh

def wo():
    return {'language_parts': {'version': 2, 'forms': [dict(f) for f in FORMS], 'parts': [[1, i, 0, 1, i] for i in range(len(FORMS))]}}

def items_by(w=None):
    items = core.build_items(w or wo(), DIGEST)
    return items, {it['label']: it for it in items if it['kind'] == core.LANG_KIND}

def test_rows_qualify_only_where_the_reading_and_the_tag_agree():
    _, by = items_by()
    q = {k for k, it in by.items() if it['context'].get('reading_bulk')}
    assert q == {'極楽', '禅宗', '漢文'}                               # never disagreeing, mixed, none, low, a mixed answer or a publisher's tag
    assert {k for k, it in by.items() if it['context'].get('rule_bulk')} == {'中文'}      # #132: the rule's row has its own button only
    assert {k for k, it in by.items() if it['context'].get('bulk')} == {'mappō'}          # Approve All Shown: its rules, unchanged
    assert by['中文']['context']['rule'] == 'reading' and by['極楽']['context'].get('rule') is None

def test_the_summary_lists_every_qualifying_row_of_a_fold():
    items, by = items_by()
    s = {g['group']: g for g in core.language_summary(items)['groups']}
    assert sorted(s['Japanese']['reading_ids']) == sorted(by[k]['id'] for k in ('極楽', '禅宗'))
    assert s['Chinese']['reading_ids'] == [] and s['Chinese']['count'] == 2      # 地獄 shows, never qualifies; 中文 is the rule's (#132)
    assert s['Chinese']['rule_ids'] == [by['中文']['id']] and s['Japanese']['rule_ids'] == []
    assert s['Chinese (Traditional)']['reading_ids'] == [by['漢文']['id']]
    rows = {r['form']: r for g in s for r in core.language_rows(items, g)['rows']}
    assert rows['中文']['rule'] == 'reading' and rows['中文']['reading'] == {'text': 'zhongwen', 'lang': 'zh', 'langs': ['zh'], 'names': ['Chinese'], 'with': 1, 'places': 1}
    assert rows['浄土']['reading']['names'] == ['Japanese', 'Chinese'] and not rows['浄土']['reading_bulk']

def test_each_group_approval_is_recorded_with_its_evidence_and_language():
    w = wo(); items, by = items_by(w)
    dec = {by['極楽']['id']: {'status': 'approved', 'bulk': 'readings'}, by['中文']['id']: {'status': 'approved', 'bulk': 'printed_reading'},
           by['mappō']['id']: {'status': 'approved', 'bulk': 'all_shown'}, by['禅宗']['id']: {'status': 'approved'}}
    out = core.apply_decisions(w, items, dec)['language_parts']['forms']
    f = {x['form']: x for x in out}
    assert f['極楽']['group_approval'] == {'button': 'readings', 'lang': 'ja', 'evidence': 'the reading printed beside it: gokuraku'}
    assert f['中文']['group_approval'] == {'button': 'printed_reading', 'lang': 'zh', 'evidence': 'the reading printed beside it: zhongwen'}
    assert f['中文']['decided'] == 'tagged'
    assert f['mappō']['group_approval'] == {'button': 'all_shown', 'lang': 'ja-Latn', 'evidence': 'the AI at high confidence'}
    assert 'group_approval' not in f['禅宗'] and f['禅宗']['decided'] == 'tagged'                  # a single decision: unchanged
    lr = core.language_review(items, dec)
    assert lr['bulk'] == 3 and lr['bulk_by'] == {'all_shown': 1, 'readings': 1, 'printed_reading': 1} and lr['local'] == 1 and lr['approved'] == 4

def test_review_again_keeps_each_group_approval_mark():
    """Review 33 F3: "Review Again" carries a group approval's button with its choice (session record, the next session's
    draft, the record's count), and a person's own later change still drops it."""
    from review import sessions as S
    w = wo(); items, by = items_by(w)
    first = {by['極楽']['id']: {'status': 'approved', 'bulk': 'readings'}, by['mappō']['id']: {'status': 'approved', 'bulk': 'all_shown'},
             by['禅宗']['id']: {'status': 'approved'}}
    rec1 = {k: dict(d, ai=next(it['ai'] for it in items if it['id'] == k), set_in='001') for k, d in first.items()}   # session 001's record
    start, missed = S.carry(items, rec1)
    assert not missed and start[by['mappō']['id']]['bulk'] == 'all_shown'
    draft = S.page_decisions(start)                                     # what "Review Again" opens with
    assert draft == first
    lr = core.language_review(items, draft)
    assert lr['bulk'] == 2 and lr['bulk_by'] == {'all_shown': 1, 'readings': 1, 'printed_reading': 0} and lr['approved'] == 3
    draft[by['極楽']['id']] = {'status': 'approved'}                     # the page's single "Approve" drops the mark (langSet)
    assert core.language_review(items, draft)['bulk_by']['readings'] == 0


def test_a_group_approval_a_row_does_not_qualify_for_decides_nothing():
    """An edited page, or a draft saved under other rules: the server never counts a group approval the row's rules leave
    out. The row stays to decide; one a person decides on its own is unchanged."""
    w = wo(); items, by = items_by(w)
    bad = {k: {'status': 'approved', 'bulk': 'readings'} for k in (by['地獄']['id'], by['浄土']['id'], by['仏教']['id'], by['念仏']['id'], by['天台']['id'], by['漢字']['id'])}
    bad[by['極楽']['id']] = {'status': 'approved', 'bulk': 'all_shown'}                          # never Chinese characters alone
    bad[by['mappō']['id']] = {'status': 'approved', 'bulk': True}                               # a draft from before #124: Approve All Shown
    bad[by['中文']['id']] = {'status': 'approved', 'bulk': 'readings'}                          # #132: a rule row under "Matching Readings"
    bad[by['禅宗']['id']] = {'status': 'approved', 'bulk': 'printed_reading'}                   # the AI's row under the rule's button
    bad[by['漢文']['id']] = {'status': 'approved', 'bulk': 'everything'}                        # review 02, L4: no other button
    out = core.apply_decisions(w, items, bad)['language_parts']['forms']
    assert [x['form'] for x in out if x.get('decided') or x.get('group_approval')] == ['mappō']
    lr = core.language_review(items, bad)
    assert lr['approved'] == 1 and lr['bulk_by'] == {'all_shown': 1, 'readings': 0, 'printed_reading': 0}
    assert sorted(core.unreviewed(items, bad)) == sorted(it['id'] for it in items if it['kind'] == core.LANG_KIND and it['label'] != 'mappō')
    single = {by['地獄']['id']: {'status': 'approved'}, by['浄土']['id']: {'status': 'changed', 'value': 'zh'}}
    out = {x['form']: x for x in core.apply_decisions(w, items, single)['language_parts']['forms']}
    assert out['地獄']['decided'] == 'tagged' and (out['浄土']['lang'], out['浄土']['decided']) == ('zh', 'changed')

def test_a_rule_row_always_shows_the_reading_that_decided_it():
    """#123: the review page marks a row the reading rule decided, and shows the reading that decided it: in the reading
    line, or, when its readings are all in a bibliography (no reading line, #124), in its evidence."""
    page = open(os.path.join(HERE, 'review', 'page.html'), encoding='utf-8').read()
    assert "r.ai && r.rule ? 'The reading printed beside it tags it as <b>'" in page and '(a fixed rule, not the AI: every place has the reading)' in page
    assert "(r.evidence && !(r.rule && reading) ? ' · Evidence: '" in page
    assert "'Reading printed beside it: \"'" in page

# ---------------------------------------------------------------- the record and review.md, through run_api.sh
def run_api(tmp_path, R, **extra):
    env = dict(os.environ, VERAPDF='off', RUN_DIR=str(R), REPLY=str(tmp_path / 'reply.txt'), INTAKE='off', OPENROUTER_API_KEY='test-not-a-key',
               HTTPS_PROXY='http://127.0.0.1:9', HTTP_PROXY='http://127.0.0.1:9', https_proxy='http://127.0.0.1:9', http_proxy='http://127.0.0.1:9',   # no network
               RUNS_DIR=str(tmp_path / 'runs'), PATH=os.path.dirname(sys.executable) + os.pathsep + os.environ.get('PATH', ''), **extra)
    for k in ('AUTO', 'FROM', 'LANG_TAGS', 'REVIEW', 'LANG_READING_RULE'):
        if k not in extra: env.pop(k, None)
    r = subprocess.run(['bash', 'run_api.sh', str(tmp_path / 'book.pdf'), 'book', 'g1'], cwd=HERE, env=env, capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-2000:]
    return r

def test_group_approvals_and_reading_rule_tags_are_listed_in_review_md(tmp_path):
    langpdf.build(str(tmp_path / 'book.pdf'), [{'tag': 'H1', 'text': 'Chapter One'},
                                               {'font': 'F2', 'text': 'The Pure Land (と) 極楽 and the hells (Zhongwen) 地獄 and 中文 here, 地獄 again.'}])
    wo_ = {'document': {'lang': 'en', 'title': 'Synthetic language test'}}
    (tmp_path / 'reply.txt').write_text(json.dumps({'model': 'anthropic/claude-sonnet-5.5', 'choices': [{'message': {'content': json.dumps(wo_)}, 'finish_reason': 'stop'}],
                                                    'usage': {'prompt_tokens': 1000, 'completion_tokens': 100, 'cost': 0.3}}))
    saved = {'schema': 'language-run/1', 'decisions': {'cjk|地獄': {'lang': 'zh', 'confidence': 'high', 'why': 'language'},
                                                        'cjk|中文': {'lang': 'zh', 'confidence': 'high', 'why': 'language'}}}
    (tmp_path / 'book.language.json').write_text(json.dumps(saved))
    R = tmp_path / 'run'
    r = run_api(tmp_path, R, REVIEW='1', LANG_REPLY=str(tmp_path / 'book.language.json'))
    assert '1 decided by the reading rule' in r.stdout
    ai = json.load(open(R / 'workorder.ai.json')); data = json.load(open(R / 'review_items.json'))
    items = data['items']; by = {it['label']: it for it in items if it['kind'] == core.LANG_KIND}
    assert by['極楽']['context']['rule'] == 'reading' and by['極楽']['context']['rule_bulk']           # the rule's row: its own button (#132)
    assert not by['極楽']['context'].get('reading_bulk')
    assert by['地獄']['context']['reading']['lang'] == 'zh' and by['地獄']['context']['reading_bulk']  # the AI's zh, the reading zh
    assert by['中文']['context'].get('reading') is None                                                # no reading: one by one
    dec = {by['極楽']['id']: {'status': 'approved', 'bulk': 'printed_reading'}, by['地獄']['id']: {'status': 'approved', 'bulk': 'readings'},
           by['中文']['id']: {'status': 'approved'}}
    wo = core.apply_decisions(ai, items, dec)
    core.finish(str(R), ai, wo, 'Kim', '2026-11-15', 'page', decisions=dec, items=items, gap_default='synthetic test book')
    run_api(tmp_path, R)
    rec = json.load(open(R / 'record.json'))
    assert rec['language_review']['bulk_by'] == {'all_shown': 0, 'readings': 1, 'printed_reading': 1} and rec['language_review']['local'] == 1
    assert rec['language_review']['not_reviewed'] == 0
    f = {x['form']: x for x in rec['workorder']['language_parts']['forms']}
    assert f['極楽']['group_approval'] == {'button': 'printed_reading', 'lang': 'ja', 'evidence': 'the reading printed beside it: と'}
    assert sorted((p['form'], p['lang']) for p in langreq.expand(rec['workorder']['language_parts'])) == [('中文', 'zh'), ('地獄', 'zh'), ('地獄', 'zh'), ('極楽', 'ja')]
    md = open(R / 'review.md', encoding='utf-8').read()
    assert 'Decided by the reading printed beside the characters at every place, not by the AI (#123): 1 word form in Chinese characters (Japanese 1)' in md
    assert ('**Approved in a group approval (2 word forms):** Approve Characters with Matching Readings: 1 · '
            'Approve Forms Decided by Their Printed Reading: 1') in md or ('**Approved in a group approval (2 word forms):** '
            'Approve Forms Decided by Their Printed Reading: 1 · Approve Characters with Matching Readings: 1') in md
    assert '- "極楽": Japanese · Printed Reading · the reading printed beside it: と' in md
    assert '- "地獄": Chinese · Matching Readings · the reading printed beside it: Zhongwen' in md
    assert '- "極楽": Japanese (by the reading printed beside it) (group approval) · 1 place' in md
    assert '- "地獄": Chinese (group approval) · 2 places' in md
    assert '- "中文": Chinese · 1 place' in md                                                        # a single decision: as before
    g = next(x for x in rec['glance']['ship'] if x['what'] == 'Language tags')
    assert g['ok'] is True and g['text'].startswith('Approved (Kim')

def test_the_page_offers_the_printed_reading_button():
    """#132: the third button, behind the same switch, with its count of the fold's rule rows; its status line."""
    page = open(os.path.join(HERE, 'review', 'page.html'), encoding='utf-8').read()
    assert ">Approve Forms Decided by Their Printed Reading (' + fmtN(rul) + ')</button>" in page
    assert "langSet(id, 'approved', undefined, 'printed_reading')" in page and "' (in a group approval: printed reading)'" in page
