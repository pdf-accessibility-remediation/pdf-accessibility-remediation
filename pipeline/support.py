"""support.py: is this PDF one the pipeline can remediate? PDF 2.0 (and namespaced tags) are not supported yet.

    reason = support.unsupported(pdf)      # pikepdf.Pdf -> None, or why the book must go to a person

The checks and fixes are written for PDF 1.x tagging (PDF/UA-1): veraPDF runs the PDF 1.x WCAG profile, and audit,
apply and verify read only the plain /RoleMap. On a PDF 2.0 book they would check the wrong standard and could
retype correct PDF 2.0 tags (FENote, Title, Aside …) into PDF 1.7 ones. intake.py stops such a book (exit 3, flagged
at intake); audit.py and apply.py stop it too, for runs that skip intake. See README, "Not supported yet: PDF 2.0".

ALLOW_PDF20=1 lets it through: only for building PDF 2.0 support, never for real work.
"""
import os

REASON = ('not supported yet. The checks and fixes are for PDF 1.x tagging (PDF/UA-1) and could downgrade correct '
          'PDF 2.0 tags. A person remediates this book; see README, "Not supported yet: PDF 2.0"')


def version(pdf):
    """The PDF version that applies: the catalog's /Version when it is later than the header, else the header's."""
    head = str(pdf.pdf_version)
    cat = str(pdf.Root.get('/Version', '')).lstrip('/')
    def num(v):
        try: return tuple(int(x) for x in v.split('.'))
        except ValueError: return (0,)
    return cat if cat and num(cat) > num(head) else head


def unsupported(pdf):
    if os.environ.get('ALLOW_PDF20') == '1': return None
    v = version(pdf)
    if v.split('.')[0].isdigit() and int(v.split('.')[0]) >= 2: return f'PDF {v}: {REASON}'
    st = pdf.Root.get('/StructTreeRoot')
    if st is not None and '/Namespaces' in st: return f'namespaced tags (PDF 2.0 tagging in a PDF {v} file): {REASON}'
    return None


def stop_if_unsupported(pdf, step):
    """For audit.py and apply.py: print why and exit 3 (flagged for a person) before anything is written."""
    why = unsupported(pdf)
    if why:
        import sys
        print(f'{step}: stopped: {why}', file=sys.stderr); sys.exit(3)
