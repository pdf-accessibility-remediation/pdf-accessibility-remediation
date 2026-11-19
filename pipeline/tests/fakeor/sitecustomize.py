"""A fake OpenRouter for run_api.sh's subprocesses (#151 tests): on PYTHONPATH with FAKE_OR=<config.json>, every Python
process replaces urllib.request.urlopen (and time.sleep). Config: {"log": path (one line per chat call), "fail_language":
[1, 2] (which language calls answer HTTP 500, counted across processes), "language": "ja-Latn"}. The work order request
gets a minimal work order; a language request gets every item answered. No network, no key."""
import os
if os.environ.get('FAKE_OR'):
    import json, io, time, urllib.request, urllib.error
    _cfg = json.load(open(os.environ['FAKE_OR'], encoding='utf-8'))
    MODEL = 'anthropic/claude-sonnet-5.5'
    class _Resp(io.BytesIO):
        def __init__(self, d): super().__init__(json.dumps(d).encode()); self.status = 200
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def getcode(self): return 200
        @property
        def headers(self): return {}
    def _urlopen(req, timeout=None, *a, **k):
        url = req.full_url if hasattr(req, 'full_url') else req
        if url.endswith('/models'):
            return _Resp({'data': [{'id': MODEL, 'pricing': {'prompt': '0.000002', 'completion': '0.00001'}, 'architecture': {'input_modalities': ['text', 'image']},
                                    'context_length': 1000000, 'top_provider': {'max_completion_tokens': 128000}, 'supported_parameters': ['max_tokens']}]})
        if url.endswith('/key'): return _Resp({'data': {'limit_remaining': 100}})
        if url.endswith('/credits'): return _Resp({'data': {'total_credits': 100, 'total_usage': 0}})
        body = json.loads(req.data)
        try: items = json.loads(body['messages'][-1]['content']).get('items') if isinstance(body['messages'][-1]['content'], str) else None
        except (ValueError, AttributeError): items = None
        kind = 'language' if items else 'workorder'
        with open(_cfg['log'], 'a', encoding='utf-8') as f: f.write(json.dumps({'kind': kind, 'ids': [it['id'] for it in items or []]}) + '\n')
        n = sum(1 for l in open(_cfg['log'], encoding='utf-8') if '"language"' in l) if kind == 'language' else 0
        if kind == 'language' and n in (_cfg.get('fail_language') or []):
            raise urllib.error.HTTPError(url, 500, 'server error', {}, io.BytesIO(b'{"error": {"message": "fake 500"}}'))
        if kind == 'language':
            dec = [{'id': it['id'], 'lang': _cfg.get('language', 'ja-Latn'), 'confidence': 'high', 'why': 'language', 'evidence': 'x'} for it in items]
            text = json.dumps({'decisions': dec})
        else: text = json.dumps({'document': {'lang': 'en', 'title': 'Synthetic retry test'}})
        return _Resp({'model': MODEL, 'choices': [{'message': {'content': text}, 'finish_reason': 'stop'}],
                      'usage': {'prompt_tokens': 900, 'completion_tokens': 100, 'cost': 0.004}})
    urllib.request.urlopen = _urlopen
    time.sleep = lambda s: None
