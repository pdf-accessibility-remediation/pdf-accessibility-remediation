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
