"""lib/replies.py: the figure requests' saved answers beside a saved reply (issue #63; handoff/alt-text-passes 03 §5).

A reply saved for reuse (batch_api.sh FROM=, tools/regression.py --seed, review_workorder.py --replay-to) is reply.txt
(the first request's text, as always) with reply.txt.meta.json. A run that made figure requests also needs its
figure requests' answers and the split they were written for: reply.txt.passes.json (format figure-passes/1), and the
meta's `figure_passes` ({requests, fingerprint}), so a replay that finds the meta but not the file refuses instead of
reading the reply as an older single one. Each caller keeps writing its own meta in its own format; this only adds.

    meta_keys(rec)              {'figure_passes': {...}} for the meta, or {} (a single-request run: nothing changes)
    write(rec, reply_path)      writes <reply_path>.passes.json when the run made figure requests; returns meta_keys(rec)
"""
import os, json

def meta_keys(rec):
    fp = (rec.get('run') or {}).get('figure_passes') or {}
    if not rec.get('raw_reply_passes') or not fp.get('fingerprint'): return {}
    return {'figure_passes': {'requests': fp.get('requests'), 'fingerprint': fp['fingerprint']}}

def write(rec, reply_path):
    keys = meta_keys(rec)
    if keys:
        with open(reply_path + '.passes.json', 'w', encoding='utf-8') as f:
            json.dump(rec['raw_reply_passes'], f, ensure_ascii=False, indent=1)
    return keys
