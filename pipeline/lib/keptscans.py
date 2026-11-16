"""lib/keptscans.py: page scans that intake's picture test kept as figures (#128, review 04 decision 4), and the guard on
their alt text (review 06 H2).

A whole-page scan under OCR text is decoration on a page of text; intake keeps it as a Figure when the image holds more than
text (a plate, a map, a photo page: SCAN_TEXT_INK). The audit marks those figures in the digest (kept_by_picture_test), so
the AI describes the picture instead of artifacting it as the page scan (prompts workorder_v12, figures_v2). Text pages land
there too (no line separates the pages), so the executor refuses alt text that copies the page's text:

  - a run of ALT_SHARED_RUN or more characters (white space removed, letter case ignored) that is also in the page's OCR
    text: the alt would repeat text a screen reader already reads (and text the AI must never write: sponsor rule 1);
  - a run of ALT_CJK_RUN or more Chinese, Japanese or Korean characters that the page's OCR text lacks: on a page whose CJK a
    person kept out of the layer (KEEP_CJK_PAGES), the alt would be the only copy of that text, transcribed by the AI.

Refused alt text is not replaced (apply.py never invents alt text): the figure is left without alt and listed for a person.
"""
import os, re, json, hashlib

ALT_SHARED_RUN = 20
ALT_CJK_RUN = 6
PAGE_SCAN_AREA = 0.8              # a Figure covering this share of the visible page or more is the page scan (audit.py marks it)


def covers_page(box, vis):
    """box (x0, top, x1, bottom: the Figure's images on its page) covers PAGE_SCAN_AREA or more of the visible area vis,
    measured as audit.py measures area_pct (clipped to vis, rounded to 0.1%), so apply.py's guard and the audit's marker
    agree on which Figure is the page scan (review 11 L1)."""
    vx0, vt, vx1, vb = vis
    part = max(min(box[2], vx1) - max(box[0], vx0), 0) * max(min(box[3], vb) - max(box[1], vt), 0)
    return round(100 * part / max(max(vx1 - vx0, 0) * max(vb - vt, 0), 1), 1) >= 100 * PAGE_SCAN_AREA


_CJK = re.compile(r'[぀-ヿ㐀-䶿一-鿿가-힯豈-﫿\U00020000-\U0002fa1f]')


def from_intake(src):
    """{page: {ink_outside_text, reason?}} of the page scans intake kept as figures, read from the intake.json beside src
    (run_api.sh's _intake/intake.pdf) only when that record's result is this file (its sha256); {} otherwise (a tagged
    book, INTAKE=off, a file edited since). ink_outside_text is None for a page kept without being measured; reason is
    "kept by a person" for a page in KEEP_CJK_PAGES (review 08, decision 5: kept whatever its ink). The PDF is hashed only
    when the record names kept page scans (review 08 L8)."""
    if os.path.basename(src) != 'intake.pdf': return {}
    try: j = json.load(open(os.path.join(os.path.dirname(os.path.abspath(src)), 'intake.json'), encoding='utf-8'))
    except (OSError, ValueError): return {}
    out = {}
    for d in ((j.get('page_scans') or {}).get('kept_as_figure') or {}, (j.get('ocr') or {}).get('scan_images_kept_as_figure') or {}):
        for k, v in d.items():
            if str(k).isdigit(): out[int(k)] = {'ink_outside_text': v}
    want = (j.get('result') or {}).get('sha256')
    if not out or not want: return {}
    h = hashlib.sha256()
    with open(src, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    if h.hexdigest() != want: return {}
    for p in ((j.get('ocr_layer_test') or {}).get('cjk_kept') or {}).get('pages') or []:
        if isinstance(p, int) and p in out: out[p]['reason'] = 'kept by a person'
    return out


def _squash(t, fold=True):
    t = re.sub(r'\s+', '', t or '')
    return t.casefold() if fold else t


def copied_text(alt, page_text, fold=True):
    """Why alt copies the page's text, or None. fold: letter case ignored in the shared-run test (the AI may change the
    case of a heading it copies)."""
    a, p = _squash(alt, fold), _squash(page_text, fold)
    n = ALT_SHARED_RUN
    if len(a) >= n and p:
        grams = {p[i:i + n] for i in range(len(p) - n + 1)}
        for i in range(len(a) - n + 1):
            if a[i:i + n] in grams:
                j = i + n
                while j < len(a) and a[i:j + 1] in p: j += 1
                return f'it repeats {j - i} characters of the page\'s OCR text ("{a[i:j][:60]}")'
    for m in re.finditer(_CJK.pattern + '{%d,}' % ALT_CJK_RUN, re.sub(r'\s+', '', alt or '')):
        run = m.group(0)
        if not any(run[i:i + ALT_CJK_RUN] in (page_text or '') for i in range(len(run) - ALT_CJK_RUN + 1)):
            return f'it holds {len(run)} Chinese, Japanese or Korean characters that the page\'s OCR text lacks ("{run[:30]}")'
    return None
