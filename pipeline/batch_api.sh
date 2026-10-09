#!/usr/bin/env bash
# Several books at once. Spends money without asking, so it only starts with AUTO=1.
#
#   AUTO=1 bash batch_api.sh <run-label> [folder | books.txt | file.pdf] …
#
#   nothing        every PDF under ../samples (all subfolders)
#   a folder       every PDF in that folder and its subfolders, e.g. ../samples/group1
#                  (several folders, lists and PDFs can be given together)
#   books.txt      one book per line: <short-name> <path/to/file.pdf> [| <result name>.pdf]
#                  (paths may contain spaces; # starts a comment; relative paths count from the folder books.txt is in)
#   short names    the run folder: a folder holding a single PDF gives its folder name (samples/cadaverous/x.pdf →
#                  cadaverous); a folder holding several gives each file's name without .pdf
#   result name    <original file name>_remediated.pdf, unless a book list line names it after a |
#
#   JOBS=3           books processed at the same time (each needs about 0.5–1.5 GB of memory)
#   BATCH_MAX_USD=5  refuse to start if the summed worst-case estimate is higher
#   KEEP=1           keep each run's working files and every log
#   MODEL=<id>       any OpenRouter model id for every book in this batch (default: DEFAULT_MODEL in decide.py).
#                    The batch cap only counts Claude models: for others the estimate is approximate and not capped
#   MAX_TOKENS=32000 output limit for each Claude reply, reasoning included (default 16000, set in decide.py)
#   RETRY=1          reuse a label that already ran: only the books without a finished result run again (give the
#                    same folders/lists as the first time), then summary.md is rewritten for the whole batch. A reply
#                    that was cut off stays on record with its cost; a complete reply whose later step failed is reused free
#   FROM=<label>     no API calls: reuse each book's Claude reply saved in an earlier record.json, from the batch
#                    runs/batches/<label>/<name>/ or the single run runs/<name>/<label>/ (free re-run after
#                    pipeline changes); skips the cost step
#
# Everything goes in ../runs/batches/<run-label>/: summary.md and one folder per book.
# 1. audits every book and adds up the worst-case cost (no model); stops if it exceeds BATCH_MAX_USD or your credit
# 2. runs every book (AUTO=1 run_api.sh, reusing the audits), JOBS at a time
# 3. prints the summary and saves it as summary.md. A book's log is kept only if that book failed
# summary.md is also written when the batch stops early or is interrupted, and RETRY=1 on a batch whose books have
# all finished just rewrites it (no cost). A missing library stops the batch before any paid call.
set -euo pipefail
[[ -n ${AUTO:-} ]] || { echo "batch runs call the API without asking: start with  AUTO=1 bash batch_api.sh <run-label> [folder | books.txt] …"; exit 1; }
LABEL=${1:?run label used for every book, e.g. batch1}; shift
SOURCES=("$@")
START_DIR=$(pwd)
cd "$(dirname "$0")"; HERE=$(pwd)
python3 -c 'import pikepdf, pdfplumber, pypdfium2, PIL, fontTools.ttLib' 2>/dev/null || {   # stop before any audit or paid call
  echo "missing Python libraries in $(command -v python3): from pipeline/, run  python3 -m pip install -r requirements.txt"; exit 1; }
export RUNS_DIR=${RUNS_DIR:-$(cd .. && pwd)/runs}
JOBS=${JOBS:-3}; MAX=${BATCH_MAX_USD:-5}
B=$RUNS_DIR/batches/$LABEL
if [[ -z ${RETRY:-} ]] && { [[ -f $B/summary.md ]] || compgen -G "$B/*/record.json" > /dev/null; }; then
  echo "$B already holds a batch: choose another run label, or add RETRY=1 to rerun only the books that did not finish"; exit 1
fi
mkdir -p "$B"
now() { python3 -c 'import time; print(f"{time.time():.2f}")'; }
T0=$(now); STARTED=$(date '+%Y-%m-%d %H:%M')
DEFAULT_MODEL=$(python3 -c "import re; print(re.search(r\"^DEFAULT_MODEL = '([^']+)'\", open('decide.py').read(), re.M).group(1))")
export MODEL=${MODEL:-}

# ---- summary.md: written at the end, when a RETRY finds nothing left to run, and when a batch stops early
SUMMARY_DONE=; RUNNING=; FAILED_AT=
AGAIN="${FROM:+FROM=$FROM }${MODEL:+MODEL=$MODEL }AUTO=1 bash batch_api.sh $LABEL"
if [[ ${#SOURCES[@]} -gt 0 ]]; then AGAIN="$AGAIN$(printf ' %q' "${SOURCES[@]}")"; fi
write_summary() {
  local WALL CREDIT
  WALL=$(python3 -c "print($(now)-$T0)"); CREDIT=$(python3 decide.py --credit 2>/dev/null || true)
python3 - "$B/books.tsv" "$B/todo.tsv" "$B" "$LABEL" "$WALL" "$CREDIT" "$AGAIN" "$STARTED" "${MAX_TOKENS:-}" <<'PY'
import sys, json, os, collections
books, todo, B, label, wall, credit, again, started, cur_mt = sys.argv[1:10]; wall = float(wall)
rate_limited = False
def fmt(s): return f'{s:.0f}s' if s < 60 else f'{int(s // 60)}m {s % 60:02.0f}s'
def load(p): return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else None
ran = {l.split('\t')[0] for l in open(todo)}             # books run by this command (the others finished earlier)
L = [f'# Batch {label}', '', '| Book | Status | Pages | API cost | Time | Checks flagged | Result |', '|---|---|---:|---:|---:|---:|---|']
total = wasted = new_spend = 0.0; done = n = 0; starts = []; failed = []; cut_at = []
models, prompts, runs_at = collections.Counter(), collections.Counter(), []
for line in open(books):
    name = line.split('\t')[0]; R = os.path.join(B, name); n += 1
    rec = load(os.path.join(R, 'record.json'))
    if rec:                                               # finished: this call + any earlier cut-off calls
        run = rec['run']; this = (run.get('usage') or {}).get('cost_usd') or 0
        earlier = sum(a.get('cost_usd') or 0 for a in rec.get('earlier_attempts') or [])
    else:                                                 # not finished: a paid call may still have happened
        run = load(os.path.join(R, 'run.json')) or {}
        this = 0 if run.get('response_from') else ((run.get('usage') or {}).get('cost_usd') or 0)
        earlier = sum(a.get('cost_usd') or 0 for a in load(os.path.join(R, 'attempts.json')) or [])
        if run.get('finish_reason') == 'length': wasted += this
    wasted += earlier; total += this + earlier
    if run.get('model'): models[run['model']] += 1
    if run.get('prompt_file'): prompts[f'`{run["prompt_file"]}` ({run.get("prompt_sha256") or "hash not recorded"})'] += 1
    if run.get('started'): runs_at.append(run['started'])
    if name in ran:                                       # money spent by this command, for the credit line
        if not run.get('response_from'): new_spend += this
        c0 = (run.get('estimate') or {}).get('credit_available_usd')
        if c0 is not None: starts.append(c0)
    cost = f'${this + earlier:.3f}'
    if not rec:
        failed.append(name)
        if run.get('finish_reason') == 'length':
            mt = (run.get('estimate') or {}).get('max_tokens') or 16000; cut_at.append(mt)
            why = f'**failed**: reply cut off at {mt:,} tokens'
        elif run.get('error'):                            # OpenRouter refused or failed the call
            er = run['error']; code = str(er.get('code'))
            if code == '429': rate_limited = True; why = '**failed**: OpenRouter 429, model rate-limited' + ('' if this else ' (nothing charged)')
            else: why = f'**failed**: OpenRouter {code}: {(er.get("message") or "")[:70].replace("|", "/")} (see `{name}.log`)'
        elif not run and not os.path.exists(os.path.join(B, f'{name}.log')): why = '**not finished**: the batch stopped before this book ran'
        else: why = f'**failed**: see `{name}.log`'
        L.append(f'| {name} | {why} | | {cost if this + earlier else ""} | | | |'); continue
    done += 1
    t = sum((rec.get('timing_seconds') or {}).values())
    rv = open(os.path.join(R, 'review.md'), encoding='utf-8').read()
    checks = sum(1 for l in rv.splitlines() if l.startswith('|') and '**CHECK**' in l)
    L.append(f'| {name} | done | {rec["document"]["pages"]} | {cost} | {fmt(t)} | {checks} | `{name}/{rec["document"].get("output") or ""}` |')
def each_(c): return ', '.join(f'{k}' + (f' ×{v}' if len(c) > 1 else '') for k, v in c.items()) or 'not recorded'
span = sorted({r[:16].replace('T', ' ') for r in runs_at})
L[1:1] = ['', f'Batch started {started}' + (f' (books run from {span[0]} to {span[-1]})' if len(span) > 1 else '')
          + f' · model {", ".join(f"`{k}`" + (f" ×{v}" if len(models) > 1 else "") for k, v in models.items()) or "not recorded"}'
          + f' · prompt {each_(prompts)}']
L += ['', f'{done} of {n} books done · API cost ${total:.3f}' + (f' (includes ${wasted:.3f} for replies that were cut off)' if wasted else '')
      + f' · wall time {fmt(wall)}', '']
# OpenRouter's balance can lag behind new calls, so also work it out: credit seen before the calls minus what they cost
live = float(credit.split()[0]) if credit.strip() else None
worked = max(starts) - new_spend if starts else None
if worked is not None and (live is None or worked < live - 0.005):
    L.append(f'Credit left: ${worked:.2f}' + ('' if live is None else f' (OpenRouter still shows ${live:.2f}; it catches up within a minute or so)'))
elif live is not None: L.append(f'Credit left: ${live:.2f}')
else: L.append('Credit left: could not check (no key, or OpenRouter unreachable)')
L.append('')
if failed:
    mt = f'MAX_TOKENS={max(cut_at) * 2} ' if cut_at else (f'MAX_TOKENS={cur_mt} ' if cur_mt else '')
    jobs = 'JOBS=1 ' if rate_limited else ''
    L += [f'To run only the {len(failed)} unfinished book(s) again, from pipeline'
          + (' (wait a few minutes first: the model was rate-limited)' if rate_limited else '') + ':', '', f'    RETRY=1 {jobs}{mt}{again}', '']
L += [f'Results are relative to {B}/', '',
      'Checks flagged = rows marked CHECK in each review.md. Open the review.md of any book with flags before running PAC.']
out = os.path.join(B, 'summary.md'); open(out, 'w', encoding='utf-8').write('\n'.join(L) + '\n')
print('\n'.join(L[2:]))
print(f'\nsaved: {out}')
PY
  SUMMARY_DONE=1
}
tidy() {   # the book lists and copied replies were only working files
  [[ -n ${KEEP:-} ]] || rm -f "$B/books.tsv" "$B/todo.tsv" "$B"/*.reply.txt "$B"/*.reply.txt.meta.json
}
finish() {
  local rc=$?; trap - EXIT
  if [[ $rc != 0 ]]; then echo; echo "batch stopped (exit $rc)${FAILED_AT:+ at $FAILED_AT}" >&2; fi
  if [[ -n $RUNNING && -z $SUMMARY_DONE ]]; then echo "writing summary.md for what did finish"; write_summary || true; fi
  [[ -z $RUNNING ]] || tidy
  exit $rc
}
trap finish EXIT
trap 'FAILED_AT="line $LINENO: $BASH_COMMAND"' ERR
trap 'exit 130' INT TERM

# ---- the book list → books.tsv (name <TAB> absolute path <TAB> result name, or - for the default)
python3 - "$START_DIR" "$HERE/../samples" ${SOURCES[@]+"${SOURCES[@]}"} > "$B/books.tsv" <<'PY'
import sys, os, re
start, samples, sources = sys.argv[1], sys.argv[2], sys.argv[3:] or [sys.argv[2]]
def stem(p): return re.sub(r'[^A-Za-z0-9_-]+', '_', os.path.splitext(os.path.basename(p))[0])
books = []
def from_folder(root):
    for d, subs, files in sorted(os.walk(root)):
        subs.sort()
        pdfs = sorted(f for f in files if f.lower().endswith('.pdf'))
        for f in pdfs:
            name = re.sub(r'[^A-Za-z0-9_-]+', '_', os.path.basename(os.path.normpath(d))) if len(pdfs) == 1 and os.path.normpath(d) != os.path.normpath(root) else stem(f)
            books.append((name, os.path.join(d, f), '-'))
def from_list(lst):
    for line in open(lst, encoding='utf-8'):
        line = line.split('#', 1)[0].strip()
        if not line: continue
        name, rest = line.split(None, 1); path, _, out = rest.partition('|')
        path = path.strip().strip('"'); out = out.strip().strip('"') or '-'
        if '/' in out: sys.exit(f'{lst}: the result name is a file name, not a path: {out}')
        books.append((name, path if os.path.isabs(path) else os.path.normpath(os.path.join(os.path.dirname(lst), path)), out))
for src in sources:
    p = src if os.path.isabs(src) else os.path.normpath(os.path.join(start, src))
    if os.path.isdir(p): from_folder(p)
    elif p.lower().endswith('.pdf'): books.append((stem(p), p, '-'))
    elif os.path.isfile(p): from_list(p)
    else: sys.exit(f'not a folder, PDF or book list: {src}')
books = [(n, os.path.abspath(p), o) for n, p, o in books]
names = [n for n, _, _ in books]
dups = {n for n in names if names.count(n) > 1}
missing = [p for _, p, _ in books if not os.path.isfile(p)]
if dups: sys.exit(f'duplicate short names: {", ".join(sorted(dups))} (use a book list to name them)')
if missing: sys.exit('no such PDF: ' + '; '.join(missing))
if not books: sys.exit('no PDFs found in: ' + ', '.join(sources))
for n, p, o in books: print(f'{n}\t{p}\t{o}')
PY
N=$(wc -l < "$B/books.tsv" | tr -d ' ')
: > "$B/todo.tsv"                               # the books still to run (all of them, unless RETRY=1 finds finished ones)
while IFS=$'\t' read -r name rest; do
  if [[ -f $B/$name/record.json ]]; then echo "  · $name: already finished, skipped"; else printf '%s\t%s\n' "$name" "$rest" >> "$B/todo.tsv"; fi
done < "$B/books.tsv"
TODO=$(wc -l < "$B/todo.tsv" | tr -d ' ')
if [[ $TODO == 0 ]]; then
  echo "every book in batch $LABEL has already finished: nothing to run; summary.md is rewritten"
  RUNNING=1; echo; echo "summary"; write_summary; exit 0
fi
echo "Batch $LABEL: $TODO of $N books to run, $JOBS at a time, model $( [[ -n ${FROM:-} ]] && echo "as recorded under $FROM" || echo "${MODEL:-$DEFAULT_MODEL}")${MAX_TOKENS:+, MAX_TOKENS=$MAX_TOKENS} → $B/"
cut -f1 "$B/todo.tsv" | sed 's/^/  · /'

# run one step for every book, JOBS at a time; each book's output goes to its own log
each() {   # each <step: estimate|run>
  tr '\t' '\0' < "$B/todo.tsv" | tr '\n' '\0' | xargs -0 -n 3 -P "$JOBS" bash -c '
    name=$1; pdf=$2; s=$(date +%s)
    if [[ $3 == - ]]; then unset OUT; else export OUT=$3; fi
    if [[ $STEP == estimate ]]; then
      log=$B/$name.estimate.log
      RUN_DIR=$B/$name ESTIMATE=1 bash run_api.sh "$pdf" "$name" "$LABEL" > "$log" 2>&1 && rc=0 || rc=$?
      st="FAILED (see $name.estimate.log)"
    else
      if [[ -n ${FROM:-} ]]; then export REPLY="$B/$name.reply.txt"; fi
      log=$B/$name.log
      RUN_DIR=$B/$name AUTO=1 bash run_api.sh "$pdf" "$name" "$LABEL" > "$log" 2>&1 && rc=0 || rc=$?
      st="FAILED (see $name.log)"
    fi
    if [[ $rc == 0 ]]; then st=ok
    elif (( rc > 128 )); then echo "  ✗ $name: interrupted"; exit 255     # Ctrl-C: stop the whole batch, not only this book
    fi
    [[ $st == ok && -z ${KEEP:-} ]] && rm -f "$log"
    echo "  $( [[ $st == ok ]] && echo ✓ || echo ✗ ) $name: $st, $(( $(date +%s) - s ))s"' _
}
FROM=${FROM:-}; KEEP=${KEEP:-}; export B LABEL STEP FROM KEEP

if [[ -n ${FROM:-} ]]; then
  echo; echo "1/3 reusing the replies saved under run label $FROM (no API calls, no cost; each record keeps its original model)"
  python3 - "$B/todo.tsv" "$RUNS_DIR" "$FROM" "$B" <<'PY' || exit 1
import sys, json, os, math
books, runs, src, B = sys.argv[1:5]; bad = []
for line in open(books):
    name = line.split('\t')[0]
    p = next((q for q in (os.path.join(runs, 'batches', src, name, 'record.json'), os.path.join(runs, name, src, 'record.json'))
              if os.path.exists(q) and json.load(open(q)).get('raw_reply')), None)
    if not p: bad.append(name); continue
    r = json.load(open(p))
    open(os.path.join(B, f'{name}.reply.txt'), 'w', encoding='utf-8').write(r['raw_reply'])
    json.dump({k: r['run'][k] for k in ('model', 'temperature') if k in r['run']},      # the new record keeps the original's
              open(os.path.join(B, f'{name}.reply.txt.meta.json'), 'w'))
if bad: sys.exit(f'stopped: no saved reply under {src} for {", ".join(bad)}')
print('  saved replies found for every book')
PY
else
echo; echo "1/3 audit + cost estimate for every book (no model)"
STEP=estimate each
python3 - "$B/todo.tsv" "$RUNS_DIR" "$LABEL" "$MAX" <<'PY' || exit 1
import sys, json, os, math
books, runs, label, cap = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4])
total, credit, rows, bad, approx, capped_n = 0.0, None, [], [], 0.0, 0
for line in open(books):
    name = line.split('\t')[0]; R = os.path.join(runs, 'batches', label, name)
    if os.path.exists(os.path.join(R, 'workorder.json')) and os.path.exists(os.path.join(R, 'response.json')):
        rows.append(f'  {name:28} $0.00: reuses its earlier complete reply'); continue
    p = os.path.join(R, 'run.json')
    if not os.path.exists(p): bad.append(name); continue
    e = json.load(open(p))['estimate']
    if e.get('approximate'): approx += e['worst_case_total_usd']        # not a Claude model: not counted against the cap
    else: total += e['worst_case_total_usd']; capped_n += 1
    if e.get('credit_available_usd') is not None: credit = e['credit_available_usd'] if credit is None else min(credit, e['credit_available_usd'])
    rows.append(f'  {name:28} worst case ${e["worst_case_total_usd"]:.2f}{" (approximate)" if e.get("approximate") else ""}  ({e["input_tokens"]:,} input tokens, {e["images"]} images)')
print('\n'.join(rows))
cr = '' if credit is None else f'   credit ${credit:.2f}'
if capped_n:                                     # at least one Claude book counts toward the cap
    print(f'  {"worst case, capped (Claude)" if approx else "total worst case":28} ${total:.2f}   batch cap ${cap:.2f}{cr}')
    if approx: print(f'  {"worst case, non-Claude":28} about ${approx:.2f}, approximate, not capped (the OpenRouter bill is the real cost)')
elif approx:                                     # every book is non-Claude: no cap bucket to show
    print(f'  {"worst case":28} about ${approx:.2f}, approximate, not capped (the OpenRouter bill is the real cost){cr}')
else: print(f'  {"total worst case":28} $0.00 (nothing new to send){cr}')
if bad: sys.exit(f'stopped: no estimate for {", ".join(bad)} (see their .estimate.log)')
if total > cap: sys.exit(f'stopped: worst case ${total:.2f} is over BATCH_MAX_USD ${cap:.2f}. Raise it (BATCH_MAX_USD={math.ceil(total)}) or run fewer books; the audits are kept and will be reused')
if credit is not None and total > credit: sys.exit(f'stopped: worst case ${total:.2f} is more than your ${credit:.2f} credit. Add credit or run fewer books')
PY

fi
echo; echo "2/3 $( [[ -n ${FROM:-} ]] && echo 'saved replies' || echo "${MODEL:-$DEFAULT_MODEL} via OpenRouter"), apply, verify, report: $JOBS books at a time"
RUNNING=1
STEP=run each

echo; echo "3/3 summary"
write_summary

