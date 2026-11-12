"""lowres.py: figures whose images are drawn at a low resolution (issue #97, docs/hand-edits.md).

    lowres.ppi(img)                          -> an image's effective resolution in pixels per inch, or None
    lowres.figure_ppi(images)                -> the lowest of a figure's images that count, or None
    lowres.flag(figures, images_by_obj)      -> [{obj, page, ppi}] of the figures below LOW_PPI, by page

An image's effective resolution is its stored pixel size (pdfplumber's srcsize) over the size it is drawn at on the
page, in inches. A 100-pixel-wide photo drawn 3 inches wide is about 33 ppi: it looks blurry when printed or zoomed.
The audit lists such figures in the digest (low_resolution); the report and the review page show them, so a person
knows which images to replace by hand. Never sent to the AI: decide.py removes it from what it sends.

Only the stored size is measured: an image enlarged before it was put in the PDF passes, and JPEG quality is not
judged. Scanned PDFs and whole-page figures are left out by the audit (intake flags scans under 300 dpi).
"""

LOW_PPI = 150              # below this a photo looks soft in print (the issue's suggestion, chosen by the team)
MIN_SIDE_PT = 72           # an image counts when its long side is drawn at least 1 inch: icons, rules and dots don't

def ppi(img):
    """img: a pdfplumber image (x0, x1, top, bottom, srcsize). None when it is too small to count or has no size.
    The sides are paired short with short, so an image turned 90 degrees measures the same."""
    src = img.get('srcsize')
    try:
        px = sorted(float(v) for v in src)
        pt = sorted((float(img['x1']) - float(img['x0']), float(img['bottom']) - float(img['top'])))
    except (TypeError, ValueError, KeyError): return None
    if len(px) != 2 or min(px) <= 0 or min(pt) <= 0 or max(pt) < MIN_SIDE_PT: return None
    return min(p / (s / 72) for p, s in zip(px, pt))

def figure_ppi(images):
    """The lowest effective resolution among a figure's images that count; None when none does (a drawing)."""
    vals = [v for v in (ppi(i) for i in images or []) if v is not None]
    return min(vals) if vals else None

def flag(figures, images_by_obj, threshold=LOW_PPI):
    """figures: the digest's figures; images_by_obj: {obj: [its pdfplumber images]}. The figures below threshold,
    leaving out whole-page crops (image_is_whole_page) and figures drawn outside the visible page."""
    out = []
    for f in figures:
        if f.get('image_is_whole_page') or f.get('outside_visible_area') or not f.get('page'): continue
        v = figure_ppi(images_by_obj.get(f['obj']))
        if v is None: continue
        v = round(v)                       # whole ppi: an image made at 150 ppi measures 149.9 when its box is a fraction of a point wide
        if v < threshold: out.append({'obj': f['obj'], 'page': f['page'], 'ppi': v})
    return sorted(out, key=lambda x: (x['page'], x['obj']))
