"""test_fontname.py: a font's name as text, including names that are not UTF-8 (lib/fontname.py).

    python -m pytest tests/test_fontname.py -q
"""
import pikepdf
from lib import fontname

def test_ascii_name():
    f = pikepdf.Dictionary(BaseFont=pikepdf.Name('/B3+SimSun'))
    assert fontname.base(f) == 'B3+SimSun' and fontname.short(f) == 'SimSun'

def test_gbk_name_is_kept_in_pdf_spelling():
    """CNKI writes 楷体 in GBK: /B5+#bf#ac#cc#e5. str() on it raised UnicodeDecodeError and stopped verify.py."""
    f = pikepdf.Object.parse(b'<< /BaseFont /B5+#bf#ac#cc#e5 >>')
    assert fontname.base(f) == 'B5+#bf#ac#cc#e5' and fontname.short(f) == '#bf#ac#cc#e5'

def test_no_name():
    assert fontname.base(pikepdf.Dictionary()) == '' and fontname.short(pikepdf.Dictionary(), 'x') == 'x'
