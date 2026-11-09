#!/usr/bin/env bash
# One OpenRouter run, start to finish: Claude decides, the code applies, checks and reports.
#   bash run_api.sh <original.pdf> <short-name> [run-label]
#   bash run_api.sh ../samples/tagged/teika.pdf teika api-run1   →  PDFREM/runs/teika/api-run1/
# Needs OPENROUTER_API_KEY in a .env file in or above this folder. Asks before spending anything.
# KEEP=1  bash run_api.sh …   keeps the working files (digest, figure crops, raw reply, logs) for debugging
# REPLY=path/to/reply.txt bash run_api.sh …   reuses a saved Claude reply instead of calling the API (no cost)
# REVIEW=1 bash run_api.sh …   stops after the AI's decisions so a person can review them first (review_workorder.py --serve);
#   rerunning the same label afterwards applies the reviewed work order. Not for batches.
# AUTO=1 bash run_api.sh …   no y/N question: sends if the estimate is within the $2 cap and your credit
# ESTIMATE=1 bash run_api.sh …   audit + cost estimate only; a later run with the same label reuses the audit
# OUT=clan.pdf bash run_api.sh …   names the result; by default it is <original file name>_remediated.pdf
# MAX_TOKENS=64000 bash run_api.sh …   output limit for Claude's reply, reasoning included (default 48000, set in decide.py)
# MAX_USD=3 bash run_api.sh …   the cap on one call's worst case, in dollars (default 2, set in decide.py; Claude models only)
# A book with more images than one request takes (100) gets figure requests after the first one, each sending up to 100
# of the figures the first could not take (issue #63; docs/files.md):
# BOOK_MAX_USD=6 bash run_api.sh …   the cap on the worst case of all of a book's requests together (default 5; Claude only)
# FIGURE_PASSES=off bash run_api.sh …   no figure requests: figures past 100 go to a person, as before
# FIGURE_MAX_TOKENS=48000 bash run_api.sh …   output limit for each figure request (default 32000)
# FIGURE_PROBE=20 bash run_api.sh …   test only: also re-send 20 figures the first request answered (recorded, never used)
# MODEL=openai/gpt-5 bash run_api.sh …   any OpenRouter model id for this run (default: DEFAULT_MODEL in decide.py)
# PAGE_READS=1 bash run_api.sh …   also read scanned, mostly Hawaiian pages whole with the AI (read_pages.py; paid, asks first)
# PAGE_READS=all bash run_api.sh …   the same for every scanned page with text (English books with Hawaiian words throughout)
# Untagged PDFs first go through intake.py (local, no cost): OCR where pages have no text, then auto-tagging. Its
# result (_intake/intake.pdf) is what the rest of the run works on; the original is never written to.
# FORCE_OCR=1 bash run_api.sh …   if the text layer fails the OCR comparison, OCR every page anyway (else the book stops)
# OCR_LANG=jpn+eng bash run_api.sh …   Tesseract languages for OCR (default eng; a scan with CJK text stops until this names a CJK pack; vertical Japanese: jpn_vert+jpn+eng)
# OCR=off / INTAKE=off bash run_api.sh …   no OCR (image-only pages are only listed) / no intake step at all
#
# Rerunning a label that did not finish picks up where it stopped: the audit is reused; a reply that was cut off
# is logged with its cost (attempts.json, folded into record.json) and a new call is made; a reply that was fine
# but a later step failed is reused at no cost.
# Outputs go to PDFREM/runs/<short-name>/<run-label>/ (beside pipeline). RUNS_DIR=/some/path overrides it.
# RUN_DIR=/exact/folder sets the run folder itself (batch_api.sh uses it: runs/batches/<label>/<name>/).
# ASK_LANG=1 (the app, #45 D4): with no OCR_LANG and no intake yet, intake.py --languages runs first; when pages need OCR
# and their language matters (not Latin script only, not "no text found") the run stops with exit 4 before any OCR
# (_intake/languages.json has the suggestion), so a person gives the language. Otherwise it goes on as before.
set -euo pipefail
SRC=${1:?path to the original PDF}; NAME=${2:?short name, e.g. teika}; RUN=${3:-api-$(date +%Y%m%d-%H%M)}
[[ -f $SRC ]] || { echo "no such PDF: $SRC"; exit 1; }
SRC=$(cd "$(dirname "$SRC")" && pwd)/$(basename "$SRC")      # absolute, so it works from any folder
BASE=$(basename "$SRC"); USER_OUT=${OUT:-}; OUT=${OUT:-${BASE%.*}_remediated.pdf}; [[ $OUT == *.[pP][dD][fF] ]] || OUT=$OUT.pdf
[[ $OUT != */* ]] || { echo "OUT is a file name, not a path: $OUT"; exit 1; }
cd "$(dirname "$0")"
python3 -c 'import pikepdf, pdfplumber, pypdfium2, PIL, fontTools.ttLib' 2>/dev/null || {   # stop before any audit or paid call
  echo "missing Python libraries in $(command -v python3): from pipeline/, run  python3 -m pip install -r requirements.txt"; exit 1; }
VERA=$(python3 vera.py --check) || {                                                         # also before any paid call
  echo "$VERA"; echo "veraPDF is needed for the WCAG checks: bash verapdf/install.sh (see README), or run with VERAPDF=off to skip them"; exit 1; }
RUNS=${RUNS_DIR:-$(cd .. && pwd)/runs}
R=${RUN_DIR:-$RUNS/$NAME/$RUN}; A=$R/_audit
if [[ -f $R/record.json ]]; then echo "$R already holds a finished run: choose another run label"; exit 1; fi
if [[ -n ${MAX_TOKENS:-} && ! $MAX_TOKENS =~ ^[0-9]+$ ]]; then echo "MAX_TOKENS must be a whole number: $MAX_TOKENS"; exit 1; fi
for v in MAX_USD BOOK_MAX_USD; do
  if [[ -n ${!v:-} && ! ${!v} =~ ^[0-9]+([.][0-9]+)?$ ]]; then echo "$v must be a number of dollars: ${!v}"; exit 1; fi
done
for v in FIGURE_MAX_TOKENS FIGURE_PROBE; do
  if [[ -n ${!v:-} && ! ${!v} =~ ^[0-9]+$ ]]; then echo "$v must be a whole number: ${!v}"; exit 1; fi
done
if [[ -n ${FIGURE_PASSES:-} && $FIGURE_PASSES != on && $FIGURE_PASSES != off ]]; then echo "FIGURE_PASSES must be on or off: $FIGURE_PASSES"; exit 1; fi
MT=(); [[ -z ${MAX_TOKENS:-} ]] || MT=(--max-tokens "$MAX_TOKENS")
[[ -z ${MAX_USD:-} ]] || MT+=(--max-usd "$MAX_USD")
[[ -z ${BOOK_MAX_USD:-} ]] || MT+=(--book-max-usd "$BOOK_MAX_USD")
[[ ${FIGURE_PASSES:-on} == on ]] || MT+=(--figure-requests off)
[[ -z ${FIGURE_MAX_TOKENS:-} ]] || MT+=(--figure-max-tokens "$FIGURE_MAX_TOKENS")
[[ -z ${FIGURE_PROBE:-} ]] || MT+=(--figure-probe "$FIGURE_PROBE")
[[ -z ${MODEL:-} ]] || MT+=(--model "$MODEL")
USE_MODEL=${MODEL:-$(python3 -c "import re; print(re.search(r\"^DEFAULT_MODEL = '([^']+)'\", open('decide.py').read(), re.M).group(1))")}
NEW=; [[ -d $R ]] || NEW=1
mkdir -p "$R"

# an earlier attempt in this folder that did not finish
log_attempt() {                # a paid call whose reply could not be used: keep its cost on record, then a new call is made
  python3 - "$R" <<'PY2'
import sys, os, json, datetime
R = sys.argv[1]; run = json.load(open(os.path.join(R, 'run.json'), encoding='utf-8'))
now = datetime.datetime.now().isoformat(timespec='seconds')
fp = run.get('figure_passes') or {}
if fp.get('state') == 'calling' and not run.get('response_from'):   # stopped while its figure requests were being sent:
    p = os.path.join(R, 'attempts.json'); att = json.load(open(p)) if os.path.exists(p) else []   # every request it paid for,
    for c in run.get('passes') or []:                                # and the one in flight, whose charge is not known
        att.append({'started': run.get('started'), 'pass': c['pass'], 'cost_usd': (c.get('usage') or {}).get('cost_usd') or 0,
                    'finish_reason': c.get('finish_reason') or (c.get('calls') or [{}])[-1].get('finish_reason'), 'usage': c.get('usage'),
                    **({'worst_usd': round(sum(x.get('worst_usd') or 0 for x in c['calls']), 4)} if any(x.get('worst_usd') for x in c.get('calls') or []) else {}),   # timed out: charge not known
                    'stopped': True, 'logged': now})
    if fp.get('in_flight'):
        att.append({'started': run.get('started'), 'pass': fp['in_flight'], 'cost_usd': None, 'worst_usd': fp.get('in_flight_worst_usd'), 'stopped': True,
                    'note': 'in flight when the run stopped; any charge is not known', 'logged': now})
    json.dump(att, open(p, 'w'), indent=1)
    for f in ('run.json', 'passes.json', 'workorder.json'):
        if os.path.exists(os.path.join(R, f)): os.remove(os.path.join(R, f))
    spent = sum((c.get('usage') or {}).get('cost_usd') or 0 for c in run.get('passes') or [])
    print(f'▶ the earlier attempt was stopped while its figure requests were being sent: ${spent:.3f} it spent on '
          f'{len(run.get("passes") or [])} request(s) is logged' + (' (and one request was in flight; its charge is not known)' if fp.get('in_flight') else '')
          + '; the run starts over')
    sys.exit(0)
cost = (run.get('usage') or {}).get('cost_usd')
if cost and not run.get('response_from'):                       # a paid call whose reply could not be used
    p = os.path.join(R, 'attempts.json'); att = json.load(open(p)) if os.path.exists(p) else []
    att.append({'started': run.get('started'), 'cost_usd': cost, 'finish_reason': run.get('finish_reason'),
                'max_tokens': (run.get('estimate') or {}).get('max_tokens'), 'usage': run.get('usage'),
                'logged': now})
    json.dump(att, open(p, 'w'), indent=1)
    os.remove(os.path.join(R, 'run.json'))
    print(f'▶ earlier attempt logged: ${cost:.3f} spent, reply {"cut off" if run.get("finish_reason") == "length" else "unusable"}; making a new call')
PY2
}
fig_state() {                  # the state of an earlier attempt's figure requests (decide.py's run.json), or nothing
  [[ -f $R/run.json ]] && python3 -c "import json,sys; print((json.load(open(sys.argv[1])).get('figure_passes') or {}).get('state') or '')" "$R/run.json" || true
}
SAVED=; REVIEWED=; MERGED=
FIG=$(fig_state)
if [[ -f $R/workorder.ai.json ]]; then         # stopped for a person's review (REVIEW=1): never decide again over it
  if [[ ! -f $R/review.json ]]; then
    echo "the AI's work order in $R is waiting for a review. Finish it first:"
    echo "  python3 $(pwd)/review_workorder.py \"$R\" --serve"; exit 1
  fi
  REVIEWED=1; echo "▶ the work order was reviewed by a person: applying the reviewed version (no API call)"
elif [[ -z ${REPLY:-} && -f $R/workorder.json && $FIG == merged ]]; then
  # every request of the earlier attempt finished, figure requests included, and a later step failed: its work order and
  # run.json are this run's own (its calls stay counted as this run's spending; not a replay)
  MERGED=1; echo "▶ every AI request of the earlier attempt finished (a later step failed): applying its work order, no new API call"
elif [[ $FIG == calling ]]; then               # before the next branch: a stop just after workorder.json is written must not replay the first reply alone
  log_attempt                                  # stopped while its figure requests were being sent: logged, then started over
elif [[ -z ${REPLY:-} && -f $R/workorder.json && -f $R/response.json ]]; then
  REPLY=$R/response.json
  echo "▶ the earlier attempt's reply was complete (a later step failed): reusing it, no new API call"
elif [[ -f $R/run.json ]]; then
  # a complete paid reply that could not be read: try it again with the current reader before paying for a new call
  # (not for a book planned with figure requests: they would need new calls, so its cost is logged and the run starts over)
  if [[ -z ${REPLY:-} && -f $R/response.json ]] && python3 -c "import json,sys; r=json.load(open(sys.argv[1])); sys.exit(0 if (r.get('usage') or {}).get('cost_usd') and r.get('finish_reason') not in (None, 'length') and not r.get('error') and not r.get('response_from') and not (r.get('estimate') or {}).get('passes') else 1)" "$R/run.json"; then
    SAVED=1
  else
    log_attempt
  fi
fi

now() { python3 -c 'import time; print(f"{time.time():.2f}")'; }
fmt() { python3 -c "s=float('$1'); print(f'{s:.1f}s' if s < 60 else f'{int(s//60)}m {s%60:04.1f}s')"; }
TIMES=()
stage() {                      # stage "label" command…  → runs it and prints how long it took
  local label=$1; shift; local s e d
  echo "▶ $label"; s=$(now); "$@"; e=$(now)
  d=$(python3 -c "print(f'{$e-$s:.2f}')"); TIMES+=("$label|$d"); echo "  ✓ $label: $(fmt "$d")"
}
write_timing() {               # timing.json: this call's steps; applying a reviewed order adds them to the first call's,
  python3 -c "import json,os,sys; p=sys.argv[1]; t=json.load(open(p)) if sys.argv[2] and os.path.exists(p) else {}; t.update({l.split('|')[0]: round(float(l.split('|')[1]), 1) for l in sys.argv[3:]}); json.dump(t, open(p, 'w'), indent=1)" \
    "$R/timing.json" "${REVIEWED:-}" "${TIMES[@]}"   # kept at the review stop, so the record has the whole run (report.py removes it)
}
summary() {
  local total=0 line label d
  echo; echo "Timing"
  for line in "${TIMES[@]}"; do
    label=${line%%|*}; d=${line##*|}
    printf "  %-34s %10s\n" "$label" "$(fmt "$d")"; total=$(python3 -c "print($total+$d)")
  done
  printf "  %-34s %10s\n" "total" "$(fmt "$total")"

  return 0
}

# 0. intake (untagged PDFs only): OCR where needed, then auto-tag. Exit 3 = flagged for a person: the book stops here
PSRC=$SRC                                      # the file the pipeline works on: the original, or the intake result
if [[ ${INTAKE:-auto} != off ]]; then
  if [[ -n $REVIEWED && -f $R/_intake/intake.json ]]; then   # applying a reviewed order: the intake it was decided on, never a new one
    python3 -c "import json,hashlib,sys; o=json.load(open(sys.argv[1])).get('original') or {}; sys.exit(0 if o.get('sha256') == hashlib.sha256(open(sys.argv[2],'rb').read()).hexdigest() else 1)" "$R/_intake/intake.json" "$SRC" \
      || { echo "$SRC is not the original this run's intake was made from (sha256 differs): give the same original PDF"; exit 1; }
    echo "▶ 0/5 intake: not re-run; applying to the intake result saved before the review stop"
  else
    if [[ -n ${ASK_LANG:-} && -z ${OCR_LANG:-} && ! -f $R/_intake/intake.json ]]; then   # the app (#45 D4): ask before any OCR
      stage "0/5 OCR language check (local, no model)" python3 intake.py "$SRC" "$R/_intake" --languages
      if python3 -c "import json,sys; d=json.load(open(sys.argv[1])); sys.exit(0 if d.get('needs_ocr') and d.get('ask', True) else 1)" "$R/_intake/languages.json"; then
        echo "stopped: pages need OCR, their language matters and no OCR language was given (see $R/_intake/languages.json)"; summary; exit 4
      fi
    fi
    stage "0/5 intake (local, no model)" python3 intake.py "$SRC" "$R/_intake"
  fi
  [[ -f $R/_intake/intake.pdf ]] && PSRC=$R/_intake/intake.pdf
fi
same_source() { [[ -f $A/digest.json ]] && python3 -c "import json,hashlib,sys; d=json.load(open('$A/digest.json')); sys.exit(0 if d['source']['sha256'] == hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest() else 1)" "$PSRC"; }
if same_source; then
  echo "▶ 1/5 audit: reusing the audit already in $A"
  [[ -f $A/verapdf.json ]] || stage "1/5 veraPDF on the original (audit made before veraPDF was added)" python3 vera.py "$PSRC" "$A/verapdf.json"
else
  stage "1/5 audit (no model)"          python3 audit.py "$PSRC" "$A"
fi
if [[ -n $SAVED ]]; then
  echo "▶ 2/5 the earlier attempt's reply was complete but could not be read: reading it again (no cost)"
  cp "$R/run.json" "$R/run.prev.json"; s=$(now)
  if python3 decide.py "$A" "$R" --response-file "$R/response.json" ${MT[@]+"${MT[@]}"}; then
    rm -f "$R/run.prev.json"; e=$(now); d=$(python3 -c "print(f'{$e-$s:.2f}')")
    TIMES+=("2/5 reuse saved reply (no cost)|$d"); echo "  ✓ 2/5 reuse saved reply (no cost): $(fmt "$d")"
    REPLY=$R/response.json; REUSED=1
  else
    mv "$R/run.prev.json" "$R/run.json"; rm -f "$R/workorder.json"
    echo "▶ the saved reply still cannot be read: its cost is logged and a new call is made"; log_attempt
  fi
fi
if [[ -n ${ESTIMATE:-} && ( -n ${REPLY:-} || -n $REVIEWED || -n $MERGED ) ]]; then echo "estimate only: no cost, a saved reply will be reused"; summary; exit 0; fi
if [[ -n ${REUSED:-} || -n $REVIEWED || -n $MERGED ]]; then
  :
elif [[ -n ${REPLY:-} ]]; then
  stage "2/5 reuse saved reply (no cost)" python3 decide.py "$A" "$R" --response-file "$REPLY" ${MT[@]+"${MT[@]}"}
else
  stage "2/5 cost estimate (no model)"  python3 decide.py "$A" "$R" --dry-run ${MT[@]+"${MT[@]}"}
  if [[ -n ${ESTIMATE:-} ]]; then echo "estimate only: $R/run.json (audit kept for the real run)"; summary; exit 0; fi
  if [[ -n ${AUTO:-} ]]; then
    ok=y
    if [[ $USE_MODEL == anthropic/* ]]; then
      echo "AUTO=1: sending without asking (decide.py still refuses a Claude call over the \$${MAX_USD:-2} cap, a book over the \$${BOOK_MAX_USD:-5} book cap, or more than your credit)"
    else
      echo "AUTO=1: sending without asking. The \$2 cap applies to Claude models only: the $USE_MODEL estimate is approximate and not capped; the OpenRouter bill is the real cost"
    fi
  else
    read -r -p "Send to OpenRouter now? [y/N] " ok
  fi
  if [[ ${ok:-n} != [yY]* ]]; then
    echo "stopped before the API call"; [[ -z ${KEEP:-} && -n $NEW ]] && rm -rf "$R"; summary; exit 0
  fi
  stage "3/5 $USE_MODEL via OpenRouter" python3 decide.py "$A" "$R" ${MT[@]+"${MT[@]}"}
fi
# PAGE_READS=1: scanned pages the audit found mostly Hawaiian are read whole by the AI (read_pages.py, issue #49): its own
# paid step, with its own estimate and cap (PAGE_READS_MAX_USD, default 3). Pages read before are reused at no cost.
if [[ -n ${PAGE_READS:-} && -z $REVIEWED ]] && python3 -c "import json,sys; sys.exit(0 if json.load(open(sys.argv[1])).get('pages') else 1)" "$A/page_reads.json" 2>/dev/null; then
  stage "3b/5 page readings: cost estimate (no model)" python3 read_pages.py "$A" "$R" --dry-run ${MODEL:+--model "$MODEL"}
  if [[ -n ${AUTO:-} ]]; then pr_ok=y; echo "AUTO=1: reading the pages without asking (read_pages.py still refuses over its cap or your credit)"
  else read -r -p "Read these pages with the AI now? [y/N] " pr_ok; fi
  if [[ ${pr_ok:-n} == [yY]* ]]; then stage "3b/5 page readings via OpenRouter" python3 read_pages.py "$A" "$R" ${MODEL:+--model "$MODEL"}
  else echo "page readings skipped: the report lists the pages for a person"; fi
fi
if [[ -n ${REVIEW:-} && -z $REVIEWED ]]; then     # stop here: a person reviews the AI's decisions before anything is applied
  cp "$R/workorder.json" "$R/workorder.ai.json"
  stage "review: page images (no model)" python3 review_workorder.py "$R" --prepare --pdf "$PSRC"
  write_timing                                   # intake, audit, the AI call and the page images: the apply adds its own
  # what the app's "Apply" needs to run this same script's second call (webapp/runs.py start_first_apply); report.py removes it
  python3 -c "import json,sys; json.dump({'src': sys.argv[1], 'name': sys.argv[2], 'env': {k: v for k, v in zip(('OCR_LANG', 'INTAKE_REUSE', 'INTAKE', 'OUT'), sys.argv[3:]) if v}}, open(sys.argv[7], 'w'), indent=1)" \
    "$SRC" "$NAME" "${OCR_LANG:-}" "${INTAKE_REUSE:-}" "${INTAKE:-}" "$USER_OUT" "$R/review_stop.json"
  summary
  echo
  echo "stopped for review: nothing has been applied yet"
  echo "Open the run page to review and apply: python3 $(pwd)/app.py \"$R\""
  echo "Or in the terminal:"
  echo "  1. python3 $(pwd)/review_workorder.py \"$R\" --serve     opens the review page"
  echo "  2. ${INTAKE_REUSE:+INTAKE_REUSE=$INTAKE_REUSE }${OCR_LANG:+OCR_LANG=$OCR_LANG }${INTAKE:+INTAKE=$INTAKE }${USER_OUT:+OUT=$USER_OUT }${RUN_DIR:+RUN_DIR=$R }bash $(pwd)/run_api.sh \"$SRC\" $NAME $(basename "$R")     afterwards (without REVIEW=1): applies the reviewed work order"
  exit 0
fi
stage "4/5 apply (no model)"            python3 apply.py "$PSRC" "$R/workorder.json" "$R/$OUT"
stage "4/5 verify (no model)"           bash -c 'python3 verify.py "$1" "$2" > /dev/null' _ "$PSRC" "$R/$OUT"
write_timing
stage "5/5 report"                      python3 report.py "$R" "$A" "--pdf=$OUT" "--input=$PSRC" ${KEEP:+--keep}
summary
echo
echo "done: $R"
echo "  $OUT   the result: run PAC on this"
echo "  review.md     what a person should check"
echo "  record.json   the full record: decisions, cost, timing, checks"
CREDIT=$(python3 decide.py --credit "$R/record.json" 2>/dev/null || true)
if [[ -n $CREDIT ]]; then echo; echo "credit left: \$$CREDIT"; else echo; echo "credit left: could not check (no key, or OpenRouter unreachable)"; fi
