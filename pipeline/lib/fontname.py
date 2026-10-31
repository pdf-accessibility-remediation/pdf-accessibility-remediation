"""fontname.py: a font's /BaseFont as text, whatever bytes the name holds.

    fontname.base(f)      -> 'B5+SimSun', or 'B5+#bf#ac#cc#e5' for a name that is not UTF-8

PDF names are bytes. Most are ASCII, but Chinese tools write legacy encodings (CNKI's GBK names, e.g. 楷体 as
#bf#ac#cc#e5), and str() on such a pikepdf.Name raises UnicodeDecodeError, which stopped apply.py's font steps and all
of verify.py. A name that is not UTF-8 is kept in the PDF's own #xx spelling: lossless, and no encoding is guessed.
"""

def base(f, default=''):
    """The font's /BaseFont without the leading slash ('' when it has none)."""
    n = f.get('/BaseFont') if hasattr(f, 'get') else None
    if n is None: return default
    try: return str(n).lstrip('/')
    except UnicodeDecodeError: return n.unparse().decode('latin-1').lstrip('/')

def short(f, default=''):
    """base() without a subset prefix: 'SimSun' for 'B3+SimSun'."""
    return base(f, default).split('+')[-1]
