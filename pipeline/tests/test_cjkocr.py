"""test_cjkocr.py: lib/cjkocr.py (#119): the CJK score, a page reading matched back to the OCR's lines, a line's reading
split over its OCR words, furigana lines and refusals. Strings only (no Tesseract, no network).

    python -m pytest tests/test_cjkocr.py -q
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib import cjkocr as C  # noqa: E402

def test_the_score_counts_cjk_characters_only():
    s = C.score('今日は朝から風が強く (2026)', '今日は朝から強く 2026 xyz')
    assert s == {'ref': 10, 'ocr': 8, 'matched': 8, 'edits': 2}               # 風 and が dropped; Latin and digits ignored
    s = C.score('大韓民國', '大韓民国')
    assert s['matched'] == 3 and s['edits'] == 1 and s['ocr'] == 4             # 國 read as 国: one substitution, one invented

def test_lines_are_paired_in_order_and_junk_stays_unpaired():
    lines = ['今日は朝から風が強く', '山の上には', 'xyz', '祖母は縁側に座って']
    read, unused, share = C.align_page(lines, '今日は朝から風が強く\n山の上には白い雲\n祖母は縁側に座って、庭\n全く別の行')
    assert read == {0: '今日は朝から風が強く', 1: '山の上には白い雲', 3: '祖母は縁側に座って、庭'}
    assert unused == ['全く別の行'] and share == 0.75                        # 3 of 4 text lines paired: 'xyz' keeps the OCR's text
    read, _, share = C.align_page(['abc def', '今日'], 'zzz\n今日')
    assert read == {0: 'zzz', 1: '今日'} and share == 1.0                     # one unpaired line on each side before a pair: the same line

def test_a_junk_line_between_two_pairs_takes_the_reading_between_them():
    """The real case (Korean with Hanja, 2026-11-22 end-to-end run): Tesseract read a whole line as Latin noise, too
    unlike its reading to pair on its own; it sits between two paired lines, as does exactly one AI line."""
    lines = ['大韓民國의 首都 서울에는', '날 MEE 소뻐으로 &08 되며 , HART RE Re)', '譜를 硏究 하는 學者들을']
    read, unused, share = C.align_page(lines, '大韓民國의首都서울에는\n날博物館과公園으로使用되며\n譜를硏究하는學者들을')
    assert read[1] == '날博物館과公園으로使用되며' and unused == [] and share == 1.0

def test_unequal_gaps_and_unanchored_pages_stay_unpaired():
    read, unused, _ = C.align_page(['第一行', 'junk', 'more junk', '第四行'], '第一行\n第二行\n第四行')
    assert sorted(read) == [0, 3] and unused == ['第二行']                     # two OCR lines, one AI line: not guessed
    read, _, share = C.align_page(['abc', 'def'], 'xyz\nuvw')
    assert read == {} and share == 0.0                                       # nothing paired: no anchor, no filling

def test_a_line_the_ocr_read_as_junk_still_gets_its_reading():
    """Korean with Hanja: Tesseract read the Hanja as junk Hangul, but the Hangul around them still pairs the lines
    (ACCEPT 0.2: measured 99.7% read on the Hanja pages, against 92.5% at 0.5)."""
    read, _, _ = C.align_page(['+뿌보뻐의꼽체서울에는오래된줌뻐과', '날 #406과수떼으로뻐되며'],
                              '大韓民國의首都서울에는오래된宮闕과\n날博物館과公園으로使用되며')
    assert read == {0: '大韓民國의首都서울에는오래된宮闕과', 1: '날博物館과公園으로使用되며'}

def test_order_is_kept_so_a_reading_never_jumps_lines():
    read, _, _ = C.align_page(['第一行', '第二行', '第三行'], '第三行\n第一行\n第二行')
    assert list(sorted(read.items())) == [(0, '第一行'), (1, '第二行')]       # the out-of-order line is left, not swapped in

def test_a_page_that_does_not_match_goes_to_a_person():
    _, unused, share = C.align_page(['新北市 桃園市', '宜蘭縣', '新竹縣', '連江縣'], '連江縣 金門縣\n新北市\n全く違う\nまた違う')
    assert share < C.MATCH_MIN and unused                                    # a map's labels: a draft for a person

def test_a_line_reading_is_split_over_its_words():
    assert C.split_line(['大韓民國의', '首都', '서울에는'], '大韓民國의首都서울에는') == ['大韓民國의', '首都', '서울에는']
    assert C.split_line(['+뿌보뻐의꼽체', '서울에는'], '大韓民國의首都서울에는') == ['大韓民國의首都', '서울에는']
    assert C.split_line(['今日は朝から', 'が強く'], '今日は朝から風が強く') == ['今日は朝から風', 'が強く']   # 風, dropped: to the word before
    assert C.split_line(['host', '(主人:', '女主人)'], 'host（主人：女主人）') == ['host', '（主人：', '女主人）']
    assert C.split_line(['朝から'], '今朝から') == ['今朝から'] and C.split_line([], 'x') == []

def test_furigana_lines_are_short_and_kana():
    assert C.is_ruby('きょう かぜ', 30, 85) and C.is_ruby('ぅあきかぜつよ 。くも', 51, 85)
    assert not C.is_ruby('今日は朝から', 80, 85) and not C.is_ruby('きょう', 80, 85) and not C.is_ruby('漢字', 30, 85)

def test_a_refusal_is_never_a_reading():
    ocr = '한미동맹은 지역안보와 국제협력에 기여' * 5
    assert C.refused("I can't transcribe this page. It is a long run of published text, and reproducing it would mean copying copyrighted material.", ocr)
    assert C.refused('', ocr) and C.refused('   ', ocr)
    assert not C.refused('한미동맹은 지역안보와 국제협력에 기여', ocr)
    assert not C.refused('The Copyright Act of 1976 著作権法', '著作権法')        # the word copyright on the page itself

def test_split_line_says_where_the_reading_has_a_space():
    assert C.split_line(['날', '博物', '館과'], '날 博物館과', spaces=True) == [('날', True), ('博物', False), ('館과', False)]
    assert C.split_line(['a', 'b'], 'x y', spaces=True) == [('x', True), ('y', False)]                    # one to one
