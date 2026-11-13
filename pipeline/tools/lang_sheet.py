"""lang_sheet.py: a short spot-check sheet for a reader of Japanese or Chinese (#118, language tagging; review 02, M1.5).
Free, local. The sheet stays in runs/ (book text and page crops: never committed).

    python3 tools/lang_sheet.py TEST_DIR BOOK=PDF …  -> TEST_DIR/spotcheck/{sheet.html, sheet.csv, crops/}

The items are the test's Han-only forms with no reading nearby (tools/lang_test.py, source "nokey"), up to 25: the ones
nothing else measures. Each row shows the form, its sentence and a crop of the printed line, and asks: Japanese, Chinese,
another language, or can't tell.
"""
import sys, os, json, csv, html, collections
PER_LANG = 14
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib import plumb_fix, plpages  # noqa: F401
import pypdfium2 as pdfium

def main(test_dir, books):
    nk = [it for it in json.load(open(os.path.join(test_dir, 'items.json'), encoding='utf-8'))['items'] if it['source'] == 'nokey']
    # the sheet's first 25 items stay as they were (earlier builds); then Chinese and Korean books until each of the three
    # languages has about as many as Japanese allows: up to PER_LANG items of each
    first = nk[:25]
    lang_of = {'cadaverous': 'ja', 'teika': 'ja', 'globalasias': 'zh', 'taiwan-matters': 'zh', 'tclt7': 'zh', 'korea-matters': 'ko', 'memorial-ko': 'ko'}
    have = collections.Counter(lang_of.get(it['book']) for it in first); items = list(first)
    for it in nk[25:]:
        lg = lang_of.get(it['book'])
        if lg in ('zh', 'ko') and have[lg] < PER_LANG: items.append(it); have[lg] += 1
    # Korean: Hanja beside Hangul is tagged locally, so no Korean item lacks evidence; a Korean reader checks the
    # romanized-Korean key instead (silver:yale_italic: the key, not the AI, is what is checked)
    allit = json.load(open(os.path.join(test_dir, 'items.json'), encoding='utf-8'))['items']
    for it in [x for x in allit if x['source'] == 'silver:yale_italic'][:PER_LANG - have['ko']]: items.append({**it, 'checks_key': it['key']})
    cands = {n: json.load(open(os.path.join(test_dir, 'cand', f'{n}.json'), encoding='utf-8')) for n in {it['book'] for it in items}}
    out = os.path.join(test_dir, 'spotcheck'); os.makedirs(os.path.join(out, 'crops'), exist_ok=True)
    PLs, docs = {}, {}
    rows = []
    for n, it in enumerate(items, 1):
        b = it['book']
        if b not in PLs: PLs[b] = plpages.Pages(books[b]); docs[b] = pdfium.PdfDocument(books[b])
        pg = PLs[b].pages[it['page'] - 1]
        cs = [c for c in pg.chars if c.get('mcid') == it['mcid']][it['first']:it['last'] + 1]
        crop = ''
        if cs:
            x0, x1 = min(c['x0'] for c in cs), max(c['x1'] for c in cs); top, bot = min(c['top'] for c in cs), max(c['bottom'] for c in cs)
            sc = 3.0; im = docs[b][it['page'] - 1].render(scale=sc).to_pil()
            box = (max(0, int((x0 - 120) * sc)), max(0, int((top - 14) * sc)), min(im.width, int((x1 + 120) * sc)), min(im.height, int((bot + 14) * sc)))
            crop = f'crops/{n:02d}.png'; im.crop(box).save(os.path.join(out, crop)); im.close()
        words = cands[b]['words'].get(str(it['page'])) or []
        ctx = ' '.join(words[max(0, it['w0'] - 15):it['w0']] + [f'[{it["text"]}]'] + words[it['w1'] + 1:it['w1'] + 16]) if it.get('w0') is not None else ''
        rows.append({'n': n, 'id': it['id'], 'book': b, 'page': it['page'], 'form': it['form'], 'context': ctx, 'crop': crop,
                     'asks': 'Is this romanized Korean?' if it.get('checks_key') else 'Japanese, Chinese, another language, or can\'t tell?',
                     'language (Japanese / Chinese / other / can\'t tell)': '', 'note': ''})
    with open(os.path.join(out, 'sheet.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    h = ['<!doctype html><meta charset="utf-8"><title>Language spot check</title>',
         '<style>body{font:15px/1.5 system-ui,sans-serif;max-width:900px;margin:24px auto;padding:0 16px}td,th{border-top:1px solid #ccc;padding:8px;vertical-align:top}img{max-width:100%}</style>',
         '<h1>Language Spot Check</h1>',
         '<p>For each item, answer the question shown (for most: is the text in brackets Japanese, Chinese, another language, or can\'t you tell?). Write the answer in the '
         'sheet (sheet.csv, the column "language"). The crop shows the printed line.</p><table><tr><th>#</th><th>Form and Sentence</th><th>Printed Line</th></tr>']
    for r in rows:
        img = f'<img src="{r["crop"]}" alt="">' if r['crop'] else ''
        h.append(f'<tr><td>{r["n"]}</td><td><i>{html.escape(r["asks"])}</i><br><b>{html.escape(r["form"])}</b><br>{html.escape(r["context"])}<br><small>{html.escape(r["book"])}, PDF page {r["page"]}</small></td>'
                 f'<td>{img}</td></tr>')
    h.append('</table>')
    open(os.path.join(out, 'sheet.html'), 'w', encoding='utf-8').write('\n'.join(h))
    print(len(rows), 'items →', out)

if __name__ == '__main__':
    main(sys.argv[1], dict(b.split('=', 1) for b in sys.argv[2:]))
