"""review_ocr.py: record a person's verdict on a book's OCR text (sponsor checklist rule 2). No model, nothing sent.

    python3 review_ocr.py <book_run_dir> --verdict approved|"not approved" --reviewer NAME --reason TEXT [--date YYYY-MM-DD] [--pages 381-386]

<book_run_dir> is a finished run (the folder with review.md, record.json and _intake/). The verdict is written to
_intake/intake.json (and shown in _intake/intake.md) and record.json (intake → review → ocr_text_approved: verdict, reviewer, date, reason, pages) and
shown in review.md: the row "OCR text reviewed by a person" turns OK only on "approved", and "At a glance" (review.md,
record.json `glance`, review.html) is refreshed, since "Ready to ship?" depends on it. A later verdict replaces the
earlier one; the earlier one is kept under review.history. FROM= reruns carry the verdict with the intake they reuse;
a fresh intake (new OCR text) starts unreviewed.
"""
import sys, os, re, json, argparse, datetime

ROW = 'OCR text reviewed by a person'

def row_text(v):
    """The review.md row for a verdict (or None: not reviewed)."""
    if not v: return None
    who = f'{v["reviewer"]} on {v["date"]}' + (f' (pages {v["pages"]})' if v.get('pages') else '')
    if v['verdict'] == 'approved': return f'| {ROW} | OK | approved by {who}: {v["reason"]} |'
    return f'| {ROW} | **CHECK** | not approved by {who}: {v["reason"]} |'

def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('run_dir'); ap.add_argument('--verdict', required=True, choices=['approved', 'not approved'])
    ap.add_argument('--reviewer', required=True); ap.add_argument('--reason', required=True)
    ap.add_argument('--date', default=datetime.date.today().isoformat()); ap.add_argument('--pages')
    a = ap.parse_args()
    R = os.path.abspath(a.run_dir); ij = os.path.join(R, '_intake', 'intake.json'); rj = os.path.join(R, 'record.json')
    if not os.path.exists(ij): sys.exit(f'no _intake/intake.json in {R}: this book had no intake (already tagged?)')
    intake = json.load(open(ij, encoding='utf-8'))
    if not (intake.get('ocr') or {}).get('pages_with_ocr_text'): sys.exit('this book has no OCR text to review')
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', a.date): sys.exit('--date must be YYYY-MM-DD')
    v = {'verdict': a.verdict, 'reviewer': a.reviewer, 'date': a.date, 'reason': a.reason, **({'pages': a.pages} if a.pages else {}),
         'recorded': datetime.datetime.now().isoformat(timespec='seconds')}
    def put(rec):
        rv = rec.setdefault('review', {})
        old = rv.get('ocr_text_approved')
        if isinstance(old, dict): rv.setdefault('history', []).append(old)
        rv['ocr_text_approved'] = v; rv.pop('approved_by', None)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    put(intake)
    try:                                               # intake.md beside it shows the verdict too
        import intake as I
        intake['glance'] = I.intake_glance(intake)
        I.write_md(intake, os.path.join(R, '_intake', 'intake.md'))
    except Exception as e: print(f'note: intake.md not rewritten ({e})')
    json.dump(intake, open(ij, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    rec = json.load(open(rj, encoding='utf-8')) if os.path.exists(rj) else None
    if rec is not None and isinstance(rec.get('intake'), dict): put(rec['intake']); rec['intake']['glance'] = intake.get('glance')
    md = os.path.join(R, 'review.md'); text = None
    if os.path.exists(md):
        lines = open(md, encoding='utf-8').read().split('\n'); hit = False
        for i, l in enumerate(lines):
            if l.startswith(f'| {ROW} |'): lines[i] = row_text(v); hit = True
        if not hit: print('note: review.md has no OCR review row; record.json and intake.json were updated')
        text = '\n'.join(lines)
    if rec is not None and text is not None:           # "Ready to ship?" depends on this verdict: refresh the glance everywhere
        try:
            from lib import glance as G
            import report_html as H
            labels = H.labels_of(R, rec)
            rec['glance'] = G.glance(rec, text, labels, H.han_pages(R))
            text = G.replace_block(text, G.glance_md(rec['glance']))
            H.review_html(R, rec, text, labels)
        except Exception as e: print(f'note: "At a glance" and review.html not refreshed ({type(e).__name__}: {e})')
    if rec is not None: json.dump(rec, open(rj, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    if text is not None: open(md, 'w', encoding='utf-8').write(text)
    print(f'recorded: {a.verdict} by {a.reviewer} on {a.date}' + (f' (pages {a.pages})' if a.pages else '') + f' in {R}')

if __name__ == '__main__':
    main()
