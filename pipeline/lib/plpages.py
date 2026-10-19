"""plpages.py: what audit.py and apply.py need from each page, read once with pdfplumber.

    PL = plpages.Pages(path)     PL.pages[pno - 1].chars / .images / .vis / .width / .height

Keeps the characters (only KEEP_KEYS), image boxes, size and visible area (CropBox) of each page; every pdfplumber
page is released after reading, so a long book does not hold its full layout in memory. Import plumb_fix first, so
each character carries the nearest enclosing MCID.
"""
import pdfplumber

KEEP_KEYS = ('text', 'x0', 'x1', 'top', 'bottom', 'size', 'fontname', 'mcid', 'tag', 'upright')
class Page:
    def __init__(self, p):
        self.width, self.height = float(p.width), float(p.height)
        mb, cb = p.mediabox, p.cropbox                 # the visible area (CropBox), in the reader's top-left coordinates
        self.vis = (max(cb[0], mb[0]) - mb[0], mb[3] - min(cb[3], mb[3]), min(cb[2], mb[2]) - mb[0], mb[3] - max(cb[1], mb[1]))
        self.chars = [{k: c.get(k) for k in KEEP_KEYS} for c in p.chars]
        self.images = [{k: i.get(k) for k in ('x0', 'x1', 'top', 'bottom', 'mcid', 'tag')} for i in p.images]
class Pages:
    def __init__(self, path):
        self.pages = []
        with pdfplumber.open(path) as pl:
            for n, p in enumerate(pl.pages, 1):
                self.pages.append(Page(p)); p.close()
                for c in self.pages[-1].chars: c['pg'] = n          # gaptext: a gap filled by another glyph is no space
