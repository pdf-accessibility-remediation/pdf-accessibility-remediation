"""review.html's text is data, never script (#93 (improve performance: home and batch pages, first-time "Review Again",
and PDF pipeline step timing), Patrick 2026-11-11; review 16 M2's gap in report_html.py and CLAUDE.md's inline() follow-up):
the page strip's `mentions` JSON block escapes <, > and &, and a link in review.md's text is made live only for "#…",
http:, https: and relative paths.

    python -m pytest tests/test_report_html_text.py -q
"""
import os, re, sys, json
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import report_html as H  # noqa: E402

TITLE = 'Notes <!--<script> and </script> & more'
MD = ('# Review\n\n## Automated Checks\n\n## ' + TITLE + '\n\n- See PDF 2 for the figure. [x](javascript:alert(1)) '
      '[y](data:text/html,hi) [z](JavaScript:alert(2)) [w](foo:bar) [ok](#pg-2) [web](https://example.org/a) [rel](review.md)\n')

def build(tmp_path):
    (tmp_path / 'review.md').write_text(MD, encoding='utf-8')
    return open(H.review_html(str(tmp_path), {'document': {'pages': 3}}, MD, {}), encoding='utf-8').read()

def test_a_mention_holding_markup_stays_inside_its_block(tmp_path):
    """A section title naming a page goes into the mentions block; "<!--", "<script>", "</script>" and "&" in it are
    \\u escapes, so the block can't end early or hide the report's own script after it, and it reads back unchanged."""
    page = build(tmp_path)
    blocks = re.findall(r'<script type="application/json" id="mentions">(.*?)</script>', page, re.S)
    assert len(blocks) == 1 and not set('<>&') & set(blocks[0])
    assert json.loads(blocks[0]) == {'2': [[json.loads(blocks[0])['2'][0][0], TITLE]]}
    assert page.count('<script>') == 1 and page.index('id="mentions"') < page.index('<script>\n')   # the report's script, still whole after it
    assert H.json_block({'a': '</script><!--'}) == '{"a": "\\u003c/script\\u003e\\u003c!--"}'

def test_only_safe_links_in_review_md_become_live(tmp_path):
    """[text](url) in review.md's text: "#…", http(s) and relative paths are links; javascript:, data: or any other
    scheme (in any case) stays as the text it was."""
    page = build(tmp_path)
    li = re.search(r'<li id="[^"]*">See .*?</li>', page).group(0)
    for t in ('[x](javascript:alert(1))', '[y](data:text/html,hi)', '[z](JavaScript:alert(2))', '[w](foo:bar)'): assert t in li, t
    assert '<a href="#pg-2">ok</a>' in li and '<a href="https://example.org/a">web</a>' in li and '<a href="review.md">rel</a>' in li
    assert not re.search(r'href="\s*(?:javascript|data|foo):', page, re.I)
    for u in ('#x', 'http://a', 'HTTPS://a', 'review.md', 'a/b:c', './x:y', 'r%C3%A9vision.md'): assert H.safe_href(u), u
    for u in ('javascript:x', 'JavaScript:x', 'data:x', 'vbscript:x', 'foo:bar', 'mailto:a@b'): assert not H.safe_href(u), u
