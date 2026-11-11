"""support.py: is this PDF one the pipeline can remediate? PDF 2.0 (and namespaced tags) are not supported yet.

    reason = support.unsupported(pdf)      # pikepdf.Pdf -> None, or why the book must go to a person
    pdf = support.open_or_stop(path, step) # audit.py / apply.py: open, or exit (3 locked or unsupported, 1 unreadable)

The checks and fixes are written for PDF 1.x tagging (PDF/UA-1): veraPDF runs the PDF 1.x WCAG profile, and audit,
apply and verify read only the plain /RoleMap. On a PDF 2.0 book they would check the wrong standard and could
retype correct PDF 2.0 tags (FENote, Title, Aside …) into PDF 1.7 ones. intake.py stops such a book (exit 3, flagged
at intake); audit.py and apply.py stop it too, for runs that skip intake. See README, "Not supported yet: PDF 2.0".

A PDF locked with a password, or one that can't be opened at all (a damaged file), stops too: intake.py writes it in
intake.json, and audit.py and apply.py (runs with INTAKE=off) print the same words, so the app shows the same card.

ALLOW_PDF20=1 lets it through: only for building PDF 2.0 support, never for real work.
"""
import os, sys

REASON = ('not supported yet. The checks and fixes are for PDF 1.x tagging (PDF/UA-1) and could downgrade correct '
          'PDF 2.0 tags. A person remediates this book; see README, "Not supported yet: PDF 2.0"')

NEEDS_PASSWORD = 'the PDF needs a password to open; a person must supply an unlocked copy'


def cannot_open(e):
    return f'the PDF could not be opened ({str(e)[:120]})'


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
        print(f'{step}: stopped: {why}', file=sys.stderr); sys.exit(3)


def open_or_stop(path, step):
    """For audit.py and apply.py: the PDF opened with pikepdf, or exit before anything is written. Locked with a password:
    exit 3 (flagged for a person, as at intake). Not readable (a damaged file): exit 1 (failed, as at intake). Then the
    PDF 2.0 check. Only the open is guarded, so an error further on is never mistaken for a damaged file."""
    import pikepdf
    try: pdf = pikepdf.open(path)
    except pikepdf.PasswordError: print(f'{step}: stopped: {NEEDS_PASSWORD}', file=sys.stderr); sys.exit(3)
    except Exception as e: print(f'{step}: failed: {cannot_open(e)}', file=sys.stderr); sys.exit(1)
    stop_if_unsupported(pdf, step)
    return pdf
