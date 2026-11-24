"""Stack-based marked-content tracking for pdfplumber.

pdfplumber's device keeps only the current tag: a nested BDC without an MCID (e.g. InDesign's
/Span <</ActualText ( )>>) sets cur_mcid=None, and its EMC clears everything, so all text after
it in the enclosing /P <</MCID n>> is reported as untagged. This keeps a stack: each char gets
the nearest enclosing MCID, and tag 'Artifact' if any enclosing sequence is an Artifact."""
import pdfplumber.page as _pp
_dec = _pp.decode_text
_cls = next(c for c in vars(_pp).values() if isinstance(c, type) and 'begin_tag' in c.__dict__)
def _begin(self, tag, props=None):
    st = self.__dict__.setdefault('_mc_stack', [])
    name = _dec(tag.name)
    mcid = props['MCID'] if isinstance(props, dict) and 'MCID' in props else None
    st.append((name, mcid))
    self._sync()
def _end(self):
    st = self.__dict__.setdefault('_mc_stack', [])
    if st: st.pop()
    self._sync()
def _sync(self):
    st = self.__dict__.get('_mc_stack', [])
    art = any(n == 'Artifact' for n, _ in st)
    self.cur_mcid = None if art else next((m for _, m in reversed(st) if m is not None), None)
    self.cur_tag = 'Artifact' if art else (st[-1][0] if st else None)
_cls.begin_tag, _cls.end_tag, _cls._sync = _begin, _end, _sync

# #166 (steps that skip text drawn inside a form XObject), stage A: each character, image and path also gets `mcs`, the
# stream of the marked content that gave it its MCID: None for the page's own content, else the form XObject's object
# number (pikepdf's objgen[0]); DIRECT for a form stored as a direct object (no number: no reader matches it). A run is
# then (page, stream, MCID), so a form's run and a page run with the same number are told apart (review 02 §3, stage A).
# The interpreter keeps a stack of the forms being drawn (do_Do, with try/finally, so a form that raises inside pdfminer
# can't leave the stack wrong); a BDC records the stream on top when it runs. A BDC that names its properties (/P /MC0 BDC)
# is resolved through the stream's /Properties before the device sees it, so its MCID is read (hawaii3's three runs).
import pdfminer.pdfinterp as _pi
from pdfminer.psparser import PSLiteral as _Lit, literal_name as _lname
from pdfminer.pdftypes import resolve1 as _res1
DIRECT = 'direct'
_pp.ALL_ATTRS.add('mcs')
_tag_item = _cls.tag_cur_item
def _begin2(self, tag, props=None):
    st = self.__dict__.setdefault('_mc_stack', [])
    streams = self.__dict__.get('_mc_streams') or [None]
    st.append((_dec(tag.name), props['MCID'] if isinstance(props, dict) and 'MCID' in props else None, streams[-1]))
    self._sync()
def _sync2(self):
    st = self.__dict__.get('_mc_stack', [])
    art = any(e[0] == 'Artifact' for e in st)
    near = None if art else next((e for e in reversed(st) if e[1] is not None), None)
    self.cur_mcid = near[1] if near else None
    self.cur_mcs = near[2] if near else None
    self.cur_tag = 'Artifact' if art else (st[-1][0] if st else None)
def _tag_cur_item2(self):
    _tag_item(self)
    if self.cur_item._objs: self.cur_item._objs[-1].mcs = getattr(self, 'cur_mcs', None)
_cls.begin_tag, _cls._sync, _cls.tag_cur_item = _begin2, _sync2, _tag_cur_item2
_do_Do = _pi.PDFPageInterpreter.do_Do
def _do_Do2(self, xobjid_arg):
    ref = (self.xobjmap or {}).get(_lname(xobjid_arg))
    key = getattr(ref, 'objid', None)
    if key is None and ref is not None: key = DIRECT
    st = self.device.__dict__.setdefault('_mc_streams', [None])
    st.append(key)
    try: return _do_Do(self, xobjid_arg)
    finally: st.pop()
_do_BDC = _pi.PDFPageInterpreter.do_BDC
def _do_BDC2(self, tag, props):
    if isinstance(props, _Lit):
        try:
            d = _res1((_res1((self.resources or {}).get('Properties')) or {}).get(_lname(props)))
            if isinstance(d, dict): props = {k: _res1(v) for k, v in d.items()}
        except Exception: pass
    return _do_BDC(self, tag, props)
_pi.PDFPageInterpreter.do_Do, _pi.PDFPageInterpreter.do_BDC = _do_Do2, _do_BDC2
