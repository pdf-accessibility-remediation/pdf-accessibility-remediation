"""webapp/credit.py: the OpenRouter credit, read the way decide.py reads it (the key's remaining limit and the account's
balance, the smaller), but saying why when it can't be read (U8, #45, Patrick 2026-11-07). A credit read sends no book
content and costs nothing. The key is read from the environment or the nearest .env, never printed or logged.

    check(timeout=30) → (usd or None, why or None); why: 'no_key' | 'refused' (HTTP 401/403: the key was refused)
                         | 'unreachable' (no connection, a timeout) | 'error' (another answer)
"""
import os, json, urllib.request, urllib.error

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # pipeline/ (this file is in webapp/)

def _key():
    k = os.environ.get('OPENROUTER_API_KEY')
    if k: return k
    d = HERE
    while True:
        p = os.path.join(d, '.env')
        if os.path.isfile(p):
            for line in open(p, encoding='utf-8'):
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    a, b = line.split('=', 1)
                    if a.strip().removeprefix('export ').strip() == 'OPENROUTER_API_KEY': return b.strip().strip('"').strip("'") or None
            return None
        if os.path.dirname(d) == d: return None
        d = os.path.dirname(d)

def check(timeout=30):
    key = _key()
    if not key: return None, 'no_key'
    vals, why = [], None
    for url, pick in (('https://openrouter.ai/api/v1/key', lambda d: d.get('limit_remaining')),
                      ('https://openrouter.ai/api/v1/credits', lambda d: (d['total_credits'] - d['total_usage']) if 'total_credits' in d else None)):
        try:
            req = urllib.request.Request(url, headers={'Authorization': f'Bearer {key}', 'User-Agent': 'pdfremproto1'})
            with urllib.request.urlopen(req, timeout=timeout) as r: v = pick(json.load(r).get('data', {}))
            if v is not None: vals.append(float(v))
        except urllib.error.HTTPError as e: why = why or ('refused' if e.code in (401, 403) else 'error')
        except (urllib.error.URLError, TimeoutError, OSError): why = why or 'unreachable'
        except (ValueError, KeyError, TypeError): why = why or 'error'
    return (min(vals), None) if vals else (None, why or 'error')
