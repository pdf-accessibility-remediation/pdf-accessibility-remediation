"""review_ocr.py: record a person's verdict on a book's OCR text (sponsor checklist rule 2). No model, nothing sent.

    python3 review_ocr.py <book_run_dir> --verdict approved|"not approved"|"sent to a language reader" --reviewer NAME
                          [--reason TEXT] [--pages 381-386] [--reads LANGUAGE] [--to WHO] [--date YYYY-MM-DD]
    python3 review_ocr.py <book_run_dir> --serve [--port 8765] [--no-browser] [--return-to URL] [--pdf ORIGINAL]

<book_run_dir> is a run with _intake/ (a finished run: the folder with review.md, record.json and _intake/). The verdict
is written to _intake/intake.json (and shown in _intake/intake.md) and record.json (intake → review → ocr_text_approved:
verdict, reviewer, date, reason, pages, and when given reads, to; via; recorded) and shown in review.md: the row "OCR
text reviewed by a person" turns OK only on "approved", and "Overview" (review.md, record.json `glance`, review.html) is
refreshed, since "Ready to ship?" depends on it. A later verdict replaces the earlier one; the earlier one is kept under
review.history. FROM= reruns carry the verdict with the intake they reuse; a fresh intake (new OCR text) starts unreviewed.

- --reason is needed for approved and not approved; for "sent to a language reader" it is optional, and --to names who.
- Pages in a non-Latin script (CJK, kana, Hangul, or OCR_LANG naming such a language): "approved" needs --reads, the
  language the reviewer reads (the review page's "I read" box). Refused without it.
- One line each, within limits, no "|" and no "](" (they would break review.md's table or become a link in review.html);
  --pages as 381-386 or 5, 9-12, within the book.
- A finished run: refused while its review page is open or an apply runs (reviews/.lock).

--serve opens the OCR-only review page: the same OCR Text section as the work-order review page (each page's image, its
text and intake's findings, and the verdict form), with no work-order session. For runs that cannot be reviewed again
(their pin was refused) and for recording a verdict without opening a session. Finish OCR Review records the verdict
and closes the page; Close Without a Verdict closes it with none. It holds reviews/.lock while open (and removes a
reviews/ folder it had to make for that).
"""
import sys, os, json, argparse, datetime, tempfile, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from review import core, ocr as O, sessions as S, server  # noqa: E402
from lib.glance import ocr_verdict_row, OCR_ROW  # noqa: E402

ROW = OCR_ROW

def row_text(v):
    """The review.md row for a verdict (or None: not reviewed)."""
    if not v: return None
    good, words = ocr_verdict_row(v)
    return f'| {ROW} | {"OK" if good else "**CHECK**"} | {words} |'

def serve(R, a):
    """The OCR-only page: the run's input PDF for the page images and text, images in a temporary folder (not the run's)."""
    intake = core.load(os.path.join(R, '_intake', 'intake.json'))
    rec = core.load(os.path.join(R, 'record.json'))
    if rec is None: sys.exit(f'{R} is not a finished run (no record.json): during a first review the review page has the OCR section')
    if not O.needed(intake):
        sys.exit('this book has no OCR text to review (intake added none, and its existing OCR layer was checked and not flagged)')
    pdf = os.path.join(R, '_intake', 'intake.pdf')
    if not os.path.isfile(pdf):
        if not a.pdf: sys.exit('this run has no _intake/intake.pdf: give --pdf <the original PDF> (its sha256 is checked)')
        pdf = os.path.abspath(a.pdf)
        want = {(rec.get('document') or {}).get('sha256'), ((rec.get('workorder') or {}).get('source') or {}).get('sha256')} - {None}
        if not os.path.isfile(pdf) or S.sha_file(pdf) not in want: sys.exit(f'{pdf} is not the file this run worked on')
    try:
        import pypdfium2 as pdfium
        doc = pdfium.PdfDocument(pdf); n = len(doc); doc.close()
    except Exception as e: sys.exit(f'{pdf} cannot be read ({type(e).__name__}: {e})')
    made = not os.path.isdir(S.P(R)['dir'])            # a run with no reviews/ yet (never pinned): leave none behind, as record() does
    try:
        with S.Lock(R, 'ocr review'):
            tmp = tempfile.mkdtemp(prefix='ocr-review-')
            try:
                data = {'mode': 'ocr', 'book': (rec.get('document') or {}).get('file') or os.path.basename(R),
                        'run': os.path.relpath(R, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'pages': n, 'pdf': pdf,
                        'items': [], 'groups': {}, 'levels': [], 'add_kinds': {}, 'addable': {},
                        'session': {'key': f'{(S.basis(R) or {}).get("run_id") or "run"}:ocr', 'id': None}}
                server.serve(tmp, a.date, a.port, open_browser=not a.no_browser, return_to=a.return_to, run_dir=R, lock_held=True,
                             data=data, wo=rec.get('workorder'))
            finally: shutil.rmtree(tmp, ignore_errors=True)
    except S.Refused as e: sys.exit(f'refused: {e}')
    finally:
        if made:
            try: os.rmdir(S.P(R)['dir'])
            except OSError: pass                       # something else was put there meanwhile (or it was never made): keep it
    print('closed: the OCR review page is closed')

def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('run_dir')
    ap.add_argument('--verdict', choices=list(O.VERDICTS)); ap.add_argument('--reviewer'); ap.add_argument('--reason')
    ap.add_argument('--date', default=datetime.date.today().isoformat()); ap.add_argument('--pages')
    ap.add_argument('--reads', action='append', metavar='LANGUAGE', help='the language the reviewer reads (needed to approve non-Latin pages)')
    ap.add_argument('--to', metavar='WHO', help='with "sent to a language reader": who or which team')
    ap.add_argument('--serve', action='store_true', help='the OCR-only review page (no work-order session)')
    ap.add_argument('--port', type=int, default=8765); ap.add_argument('--no-browser', action='store_true')
    ap.add_argument('--return-to', metavar='URL'); ap.add_argument('--pdf', help='with --serve: the original, when the run has no intake.pdf')
    a = ap.parse_args()
    R = os.path.abspath(a.run_dir)
    if not os.path.exists(os.path.join(R, '_intake', 'intake.json')): sys.exit(f'no _intake/intake.json in {R}: this book had no intake (already tagged?)')
    if a.serve:
        if a.verdict: sys.exit('--serve opens the page, where the verdict is given: leave out --verdict')
        if a.return_to:
            try: server.check_return_to(a.return_to)
            except ValueError as e: sys.exit(f'--return-to: {e}')
        return serve(R, a)
    if not a.verdict or not a.reviewer: sys.exit('give --verdict and --reviewer (or --serve for the page)')
    fields = {'verdict': a.verdict, 'reviewer': a.reviewer, 'reason': a.reason, 'pages': a.pages, 'reads': a.reads or [], 'to': a.to}
    try: v, _ = O.record(R, fields, via='review_ocr.py', date=a.date)
    except ValueError as e: sys.exit(str(e))
    except S.Refused as e: sys.exit(f'refused: {e}')
    print(f'recorded: {v["verdict"]} by {v["reviewer"]} on {v["date"]}' + (f' (pages {v["pages"]})' if v.get('pages') else '') + f' in {R}')

if __name__ == '__main__':
    main()
