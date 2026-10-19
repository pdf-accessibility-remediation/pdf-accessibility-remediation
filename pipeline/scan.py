"""scan.py: fast read-only checks on a folder of PDFs (local, no OCR, no model, nothing written next to the PDFs).

    python3 scan.py <folder> <out_dir>

For each PDF (searched recursively): tagged or not, producer, page triage (text / image only / blank), and the text-layer
checks intake.py runs on every text page: private-use characters (3.6), text outside the visible page area (CropBox),
and word breaks that are only gaps between letters (3.4), with narrow gaps counted separately. Writes
<out_dir>/books/<name>.json per book and <out_dir>/summary.md. A book that cannot be opened is listed with the reason.
"""
import sys, os, json, time, collections, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pikepdf, pypdfium2 as pdfium
import intake as I
from lib import support

def scan(path):
    r = {'file': os.path.basename(path), 'folder': os.path.dirname(path)}
    t0 = time.time()
    try: pdf = pikepdf.open(path)
    except pikepdf.PasswordError: r['error'] = 'needs a password'; return r
    except Exception as e: r['error'] = f'could not be opened ({str(e)[:100]})'; return r
    with pdf:
        r['pages'] = len(pdf.pages); r['tagged'] = I.tagged(pdf)
        r['pdf_version'] = support.version(pdf); r['unsupported'] = support.unsupported(pdf)     # PDF 2.0: intake stops it
        info = pdf.docinfo if '/Info' in pdf.trailer else {}
        r['producer'] = str(info.get('/Producer', '')).strip() or None
        r['creator'] = str(info.get('/Creator', '')).strip() or None
        inv = [I.page_inventory(pg) for pg in pdf.pages]
    kinds = collections.defaultdict(list)
    for i, x in enumerate(inv, 1): kinds[x['kind']].append(i)
    r['triage'] = {k: len(v) for k, v in kinds.items()}
    r['image_only_pages'] = kinds['image-only'][:50]
    text_pages = kinds['text'] + kinds['ocr-layer']
    doc = pdfium.PdfDocument(path)
    try: L = I.layer_scan(doc, sorted(text_pages))
    finally: doc.close()
    n = max(len(text_pages), 1)
    r['private_use'] = {'count': sum(L['pua'].values()), 'pages': len(L['pua_pages']), 'ranges': I.private_use_ranges(L['pua'])[:6]}
    r['outside_page_area'] = {'chars': sum(L['outside'].values()), 'pages': len(L['outside']), 'first_pages': sorted(L['outside'])[:12]}
    r['word_breaks'] = {'space_characters': L['real'], 'gaps_only': L['gen'], 'pages_relying_on_gaps': len(L['gaps']),
                        'share_of_text_pages': round(len(L['gaps']) / n, 3), 'narrow_gaps': L['narrow_total'],
                        'narrow_per_text_page': round(L['narrow_total'] / n, 2), 'pages_with_narrow_gaps': len(L['narrow']),
                        'check': L['narrow_total'] / n >= I.NARROW_BOOK_RATE}
    r['seconds'] = round(time.time() - t0, 1)
    return r

def main():
    if len(sys.argv) != 3: sys.exit(__doc__.split('\n\n')[1])
    src, out = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
    os.makedirs(os.path.join(out, 'books'), exist_ok=True)
    files = sorted(os.path.join(d, f) for d, _, fs in os.walk(src) for f in fs if f.lower().endswith('.pdf'))
    rows, t0 = [], time.time()
    for k, f in enumerate(files, 1):
        r = scan(f); rows.append(r)
        name = os.path.splitext(os.path.relpath(f, src))[0].replace(os.sep, '__')
        json.dump(r, open(os.path.join(out, 'books', name + '.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
        print(f'{k}/{len(files)} {r["file"]}: ' + (r.get('error') or f'{r["pages"]} pages, {r["seconds"]}s'), flush=True)
    ok = [r for r in rows if 'error' not in r]
    def esc(s): return (s or 'not recorded').replace('|', '/')[:40]
    def pct(x): return f'{x:.0%}'
    L = [f'# Fast checks: {len(files)} PDFs in `{src}`', '',
         f'Written {datetime.datetime.now().isoformat(timespec="seconds")} by `scan.py` (read-only: no OCR, no model, nothing written next to the PDFs). '
         f'Thresholds as in `intake.py`: private-use CHECK above {I.PUA_CHECK}; text outside the visible page area counted from '
         f'{I.OUTSIDE_MIN_CHARS} characters a page; a page relies on gaps when at least {I.GAP_MIN_BREAKS} word breaks, more than '
         f'{pct(I.GAP_SHARE)} of them gaps only; a narrow gap is under {pct(I.NARROW_GAP)} of the type size (advance widths), a CHECK when '
         f'they average {I.NARROW_BOOK_RATE} or more per text page. Total time {time.time() - t0:.0f} s.', '',
         '## Totals', '',
         f'- Opened: {len(ok)} of {len(files)}' + (f' (not opened: {", ".join(r["file"] + ": " + r["error"] for r in rows if "error" in r)})' if len(ok) < len(files) else ''),
         f'- Already tagged: {sum(1 for r in ok if r["tagged"])}; untagged: {sum(1 for r in ok if not r["tagged"])}',
         f'- Not supported yet (PDF 2.0 or namespaced tags; the pipeline stops them at intake for a person): {sum(1 for r in ok if r.get("unsupported"))}',
         f'- With image-only pages (scans or picture pages): {sum(1 for r in ok if r["triage"].get("image-only"))}',
         f'- Private-use characters over {I.PUA_CHECK}: {sum(1 for r in ok if r["private_use"]["count"] > I.PUA_CHECK)} books',
         f'- Text outside the visible page area: {sum(1 for r in ok if r["outside_page_area"]["chars"])} books',
         f'- Relying on gaps for most word breaks (over half their text pages): {sum(1 for r in ok if r["word_breaks"]["share_of_text_pages"] > 0.5)} books',
         f'- Narrow word gaps at {I.NARROW_BOOK_RATE} or more per text page (CHECK): {sum(1 for r in ok if r["word_breaks"]["check"])} books', '']
    prod = collections.defaultdict(list)
    for r in ok: prod[(r['producer'] or 'not recorded').split('(')[0].strip()[:40]].append(r)
    L += ['## By producer', '', '| Producer | Books | Tagged | Private-use > 100 | Text outside page | Relies on gaps | Narrow gaps CHECK |',
          '|---|---:|---:|---:|---:|---:|---:|']
    for p, rs in sorted(prod.items(), key=lambda kv: -len(kv[1])):
        L.append(f'| {esc(p)} | {len(rs)} | {sum(1 for r in rs if r["tagged"])} | {sum(1 for r in rs if r["private_use"]["count"] > I.PUA_CHECK)} | '
                 f'{sum(1 for r in rs if r["outside_page_area"]["chars"])} | {sum(1 for r in rs if r["word_breaks"]["share_of_text_pages"] > 0.5)} | '
                 f'{sum(1 for r in rs if r["word_breaks"]["check"])} |')
    L += ['', '## Books', '', '| File | Pages | Supported | Tagged | Producer | Text / image-only / blank | Private-use (most common range) | Outside page area | Pages relying on gaps | Narrow gaps per text page |',
          '|---|---:|---|---|---|---|---|---|---:|---|']
    for r in rows:
        if 'error' in r: L.append(f'| {r["file"]} | — | — | — | — | not opened: {r["error"]} | — | — | — | — |'); continue
        t, pu, op, wb = r['triage'], r['private_use'], r['outside_page_area'], r['word_breaks']
        top = f' ({pu["ranges"][0]["range"]}, {pu["ranges"][0]["what"]})' if pu['ranges'] else ''
        sup = 'yes' if not r.get('unsupported') else '**no: ' + ('PDF ' + r['pdf_version'] if r['unsupported'].startswith('PDF') else 'namespaced tags') + '**'
        L.append(f'| {r["file"]} | {r["pages"]} | {sup} | {"yes" if r["tagged"] else "no"} | {esc(r["producer"])} | '
                 f'{t.get("text", 0) + t.get("ocr-layer", 0)} / {t.get("image-only", 0)} / {t.get("blank", 0)} | '
                 f'{pu["count"]}{top}' + (' **CHECK**' if pu['count'] > I.PUA_CHECK else '') + ' | '
                 + (f'{op["chars"]} characters on {op["pages"]} pages' if op['chars'] else 'none') + ' | '
                 f'{pct(wb["share_of_text_pages"])} | {wb["narrow_per_text_page"]} ({wb["narrow_gaps"]} in all)' + (' **CHECK**' if wb['check'] else '') + ' |')
    L += ['', 'Automated counts are evidence for planning, not a verdict on any book. Per-book details: `books/<file>.json`.']
    open(os.path.join(out, 'summary.md'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    print(f'saved: {os.path.join(out, "summary.md")}')

if __name__ == '__main__':
    main()
