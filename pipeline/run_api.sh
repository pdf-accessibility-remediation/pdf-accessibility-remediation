#!/usr/bin/env bash
# One OpenRouter run, start to finish: Claude decides, the code applies, checks and reports.
#   bash run_api.sh <original.pdf> <short-name> [run-label]
#   bash run_api.sh ../samples/tagged/teika.pdf teika api-run1   →  runs/teika/api-run1/ (beside pipeline/)
# Needs OPENROUTER_API_KEY in a .env file in or above this folder. Asks before spending anything.
# KEEP=1  bash run_api.sh …   keeps the working files (digest, figure crops, raw reply, logs) for debugging
# REPLY=path/to/reply.txt bash run_api.sh …   reuses a saved Claude reply instead of calling the API (no cost)
# REVIEW=1 bash run_api.sh …   stops after the AI's decisions so a person can review them first (review_workorder.py --serve);
#   rerunning the same label afterwards applies the reviewed work order. Not for batches.
# AUTO=1 bash run_api.sh …   no y/N question: sends if the estimate is within the dollar limits and your credit
# ESTIMATE=1 bash run_api.sh …   audit + cost estimate only; a later run with the same label reuses the audit
# OUT=clan.pdf bash run_api.sh …   names the result; by default it is <original file name>_remediated.pdf
# MAX_USD=3 bash run_api.sh …   the limit on what one AI request could cost, in dollars (default 2, lib/costs.py; Claude models only)
# A book with more images than one request takes (100) gets figure requests after the first one, each sending up to 100
# of the figures the first could not take (issue #63; docs/files.md):
# BOOK_MAX_USD=6 bash run_api.sh …   the limit on what all of a PDF's requests could cost together, previous attempts included (default 8, lib/costs.py; Claude only)
# FIGURE_PASSES=off bash run_api.sh …   no figure requests: figures past 100 go to a person, as before
# FIGURE_PROBE=20 bash run_api.sh …   test only: also re-send 20 figures the first request answered (recorded, never used)
# MODEL=openai/gpt-5 bash run_api.sh …   any OpenRouter model id for this run (default: DEFAULT_MODEL in decide.py)
# Scanned, mostly Hawaiian pages are read whole with the AI by default (read_pages.py; paid, its own estimate, asks first
# unless AUTO=1; a PDF with no such pages costs nothing). PAGE_READS=off bash run_api.sh …   no page readings
# PAGE_READS=all bash run_api.sh …   every scanned page with text, not only mostly Hawaiian ones (English PDFs with Hawaiian words throughout)
# Untagged PDFs first go through intake.py (local, no cost): OCR where pages have no text, then auto-tagging. Its
# result (_intake/intake.pdf) is what the rest of the run works on; the original is never written to.
# FORCE_OCR=1 bash run_api.sh …   if the text layer fails the OCR comparison, OCR every page anyway (else the book stops)
# OCR_LANG=jpn+eng bash run_api.sh …   Tesseract languages for OCR (default eng; a scan with CJK text stops until this names a CJK pack; vertical Japanese: jpn_vert+jpn+eng)
# KEEP_CJK_PAGES=35,41 bash run_api.sh …   intake's CJK stop answered "keep": the existing OCR text is kept on those pages
#                                          (their images hold no Chinese, Japanese or Korean text: a map, a chart)
# OCR=off / INTAKE=off bash run_api.sh …   no OCR (image-only pages are only listed) / no intake step at all
# DECIDE=none bash run_api.sh …   no AI call: an empty work order for a person to fill (with REVIEW=1). handedit.py import
#   uses it for a PDF edited by hand and brought back for review; such a run works on _handedit/input.pdf when there is one
#
# Rerunning a label that did not finish picks up where it stopped: the audit is reused; a reply that was cut off
# is logged with its cost (attempts.json, folded into record.json) and a new request is made with twice the room; a reply that
# was fine but a later step failed is reused at no cost.
# Outputs go to runs/<short-name>/<run-label>/ (beside pipeline/). RUNS_DIR=/some/path overrides it.
# RUN_DIR=/exact/folder sets the run folder itself (batch_api.sh uses it: runs/batches/<label>/<name>/).
# A relative RUNS_DIR, RUN_DIR, REPLY, LANG_REPLY or COST_HISTORY is taken from the folder the command is run in, as the
# PDF's path is (#144).
# ASK_LANG=1 (the app, #45 D4): with no OCR_LANG and no intake yet, intake.py --languages runs first; when pages need OCR
# and their language matters (not Latin script only, not "no text found") the run stops with exit 4 before any OCR
# (_intake/languages.json has the suggestion), so a person gives the language. Otherwise it goes on as before.
set -euo pipefail
unset CDPATH                                                 # a cd below never prints, nor goes elsewhere
SRC=${1:?path to the original PDF}; NAME=${2:?short name, e.g. teika}; RUN=${3:-api-$(date +%Y%m%d-%H%M)}
[[ -f $SRC ]] || { echo "no such PDF: $SRC"; exit 1; }
SRC=$(cd "$(dirname "$SRC")" && pwd)/$(basename "$SRC")      # absolute, so it works from any folder
BASE=$(basename "$SRC"); USER_OUT=${OUT:-}; OUT=${OUT:-${BASE%.*}_remediated.pdf}; [[ $OUT == *.[pP][dD][fF] ]] || OUT=$OUT.pdf
[[ $OUT != */* ]] || { echo "OUT is a file name, not a path: $OUT"; exit 1; }
PAGE_READS=${PAGE_READS:-1}; [[ $PAGE_READS == 0 || $PAGE_READS == no ]] && PAGE_READS=off
[[ $PAGE_READS == 1 || $PAGE_READS == all || $PAGE_READS == off ]] || { echo "PAGE_READS is 1 (the default), all or off: $PAGE_READS"; exit 1; }
LANG_TAGS=${LANG_TAGS:-on}; [[ $LANG_TAGS == 0 || $LANG_TAGS == no ]] && LANG_TAGS=off      # the language step (#118): on unless LANG_TAGS=off
[[ $LANG_TAGS == on || $LANG_TAGS == 1 || $LANG_TAGS == off ]] || { echo "LANG_TAGS is on (the default) or off: $LANG_TAGS"; exit 1; }
# LANG_GROW=on: a title's whole extent is tagged; LANG_GROUP=on: adjacent single Chinese characters are one form (review 08,
# M6). Both off by default, read by name_languages.py; title growth stays off until the Windows check of a title in pieces.
for v in LANG_GROW LANG_GROUP; do
  case ${!v:-off} in on|off|1|0) ;; *) echo "$v is on or off (the default): ${!v}"; exit 1;; esac
done
abs_path() { python3 -c 'import os,sys; print(os.path.abspath(sys.argv[1]))' "$1"; }   # no folder needed; ".." and a final "/" go
for v in RUNS_DIR RUN_DIR REPLY LANG_REPLY COST_HISTORY; do   # absolute, before the cd below: R is compared with other paths (#144)
  [[ -z ${!v:-} ]] || printf -v "$v" '%s' "$(abs_path "${!v}")"
done
cd "$(dirname "$0")"
python3 -c 'import pikepdf, pdfplumber, pypdfium2, PIL, fontTools.ttLib' 2>/dev/null || {   # stop before any audit or paid call
  echo "missing Python libraries in $(command -v python3): from pipeline/, run  python3 -m pip install -r requirements.txt"; exit 1; }
VERA=$(python3 vera.py --check) || {                                                         # also before any paid call
  echo "$VERA"; echo "veraPDF is needed for the WCAG checks: bash verapdf/install.sh (see README), or run with VERAPDF=off to skip them"; exit 1; }
RUNS=${RUNS_DIR:-$(cd .. && pwd)/runs}
export COST_HISTORY=${COST_HISTORY:-$RUNS/.cost-history.jsonl}   # the local history behind "Expected Cost" (lib/costhistory.py)
R=${RUN_DIR:-$RUNS/$NAME/$RUN}; A=$R/_audit
if [[ -f $R/record.json ]]; then echo "$R already holds a finished run: choose another run label"; exit 1; fi
if [[ -n ${MAX_TOKENS:-} && ! $MAX_TOKENS =~ ^[0-9]+$ ]]; then echo "MAX_TOKENS must be a whole number: $MAX_TOKENS"; exit 1; fi
if [[ -n ${DECIDE:-} && $DECIDE != none ]]; then echo "DECIDE is none (no AI call) or unset: $DECIDE"; exit 1; fi
for v in MAX_USD BOOK_MAX_USD FIGURE_RETRY_MAX_USD FIGURE_RETRY_BOOK_MAX_USD; do
  if [[ -n ${!v:-} && ! ${!v} =~ ^[0-9]+([.][0-9]+)?$ ]]; then echo "$v must be a number of dollars: ${!v}"; exit 1; fi
done
for v in FIGURE_MAX_TOKENS FIGURE_PROBE; do
  if [[ -n ${!v:-} && ! ${!v} =~ ^[0-9]+$ ]]; then echo "$v must be a whole number: ${!v}"; exit 1; fi
done
if [[ -n ${FIGURE_PASSES:-} && $FIGURE_PASSES != on && $FIGURE_PASSES != off ]]; then echo "FIGURE_PASSES must be on or off: $FIGURE_PASSES"; exit 1; fi
MT=(); [[ -z ${MAX_TOKENS:-} ]] || MT=(--max-tokens "$MAX_TOKENS")
[[ -z ${MAX_USD:-} ]] || MT+=(--max-usd "$MAX_USD")
[[ -z ${BOOK_MAX_USD:-} ]] || MT+=(--book-max-usd "$BOOK_MAX_USD")
[[ -z ${FIGURE_RETRY_MAX_USD:-} ]] || MT+=(--figure-retry-max-usd "$FIGURE_RETRY_MAX_USD")                  # the app: the real limits, for a doubled figure retry only
[[ -z ${FIGURE_RETRY_BOOK_MAX_USD:-} ]] || MT+=(--figure-retry-book-max-usd "$FIGURE_RETRY_BOOK_MAX_USD")
[[ ${FIGURE_PASSES:-on} == on ]] || MT+=(--figure-requests off)
[[ -z ${FIGURE_MAX_TOKENS:-} ]] || MT+=(--figure-max-tokens "$FIGURE_MAX_TOKENS")
[[ -z ${FIGURE_PROBE:-} ]] || MT+=(--figure-probe "$FIGURE_PROBE")
[[ -z ${MODEL:-} ]] || MT+=(--model "$MODEL")
USE_MODEL=${MODEL:-$(python3 -c "import re; print(re.search(r\"^DEFAULT_MODEL = '([^']+)'\", open('decide.py').read(), re.M).group(1))")}
NEW=; [[ -d $R ]] || NEW=1
mkdir -p "$R"

# a previous attempt in this folder that did not finish
log_attempt() {                # a paid call whose reply could not be used: keep its cost on record, then a new call is made
  python3 - "$R" <<'PY2'
import sys, os, json, datetime
R = sys.argv[1]; run = json.load(open(os.path.join(R, 'run.json'), encoding='utf-8'))
now = datetime.datetime.now().isoformat(timespec='seconds')
fp = run.get('figure_passes') or {}
if fp.get('state') == 'calling' and not run.get('response_from'):   # stopped while its figure requests were being sent:
    p = os.path.join(R, 'attempts.json'); att = json.load(open(p)) if os.path.exists(p) else []   # every request it paid for,
    for c in run.get('passes') or []:                                # and those in flight, whose charges are not known
        att.append({'started': run.get('started'), 'pass': c['pass'], 'cost_usd': (c.get('usage') or {}).get('cost_usd') or 0,
                    'finish_reason': 'length' if any(x.get('finish_reason') == 'length' for x in c.get('calls') or []) else c.get('finish_reason') or (c.get('calls') or [{}])[-1].get('finish_reason'), 'usage': c.get('usage'),
                    **({'worst_usd': round(sum(x.get('worst_usd') or 0 for x in c['calls']), 4)} if any(x.get('worst_usd') for x in c.get('calls') or []) else {}),   # timed out: charge not known
                    'stopped': True, 'logged': now})
    fly = fp.get('in_flight')                                        # #135 (parallel requests): a list of the requests being sent,
    fly = (list(fly) if isinstance(fly, list) else [{'pass': fly, 'worst_usd': fp.get('in_flight_worst_usd'),   # or the older single
           'paid_usd': fp.get('in_flight_paid_usd'), 'cut_off': fp.get('in_flight_cut_off')}] if fly else [])      # request's fields
    fly += list(fp.get('stopped_in_flight') or [])                   # recorded by decide.py when it was interrupted
    for e in fly:
        if e.get('paid_usd'):                                        # paid for already (a cut-off or an unreadable reply), with its retry in flight
            att.append({'started': run.get('started'), 'pass': e['pass'], 'cost_usd': e['paid_usd'], 'finish_reason': 'length' if e.get('cut_off') else 'stop', 'stopped': True, 'logged': now})
        att.append({'started': run.get('started'), 'pass': e['pass'], 'cost_usd': None, 'worst_usd': e.get('worst_usd'), 'stopped': True,
                    'note': 'in flight when the run stopped; any charge is not known', 'logged': now})
    json.dump(att, open(p, 'w'), indent=1)
    for f in ('run.json', 'passes.json', 'workorder.json'):
        if os.path.exists(os.path.join(R, f)): os.remove(os.path.join(R, f))
    spent = sum((c.get('usage') or {}).get('cost_usd') or 0 for c in run.get('passes') or []) + sum(e.get('paid_usd') or 0 for e in fly)
    n = len(fly)
    print(f'▶ the previous attempt was stopped while its figure requests were being sent: ${spent:.3f} it spent on '
          f'{len(run.get("passes") or [])} request(s) is logged'
          + (f' (and {n} request{"s were" if n != 1 else " was"} in flight; {"their charges are" if n != 1 else "its charge is"} not known)' if n else '')
          + '; the run starts over')
    sys.exit(0)
cost = (run.get('usage') or {}).get('cost_usd')
if cost and (not run.get('response_from') or run.get('own_reply')):   # a paid call whose reply could not be used (a reply from elsewhere was not paid for here)
    p = os.path.join(R, 'attempts.json'); att = json.load(open(p)) if os.path.exists(p) else []
    att.append({'started': run.get('started'), 'cost_usd': cost, 'finish_reason': run.get('finish_reason'),
                'max_tokens': (run.get('estimate') or {}).get('max_tokens'), 'usage': run.get('usage'),
                'logged': now})
    json.dump(att, open(p, 'w'), indent=1)
    os.remove(os.path.join(R, 'run.json'))
    print(f'▶ previous attempt logged: ${cost:.3f} spent, reply {"cut off" if run.get("finish_reason") == "length" else "unusable"}; making a new request')
PY2
}
fig_state() {                  # the state of an earlier attempt's figure requests (decide.py's run.json), or nothing
  [[ -f $R/run.json ]] && python3 -c "import json,sys; print((json.load(open(sys.argv[1])).get('figure_passes') or {}).get('state') or '')" "$R/run.json" || true
}
SAVED=; REVIEWED=; MERGED=
FIG=$(fig_state)
outcome() { python3 -m lib.aistatus record "$R" "$@" 2>/dev/null || true; }   # #151: how a step ended (ai_outcome.json)
refused_est() { python3 -c 'import json,sys; e=json.load(open(sys.argv[1])); sys.exit(0 if (e.get("refused") or {}).get("why") in ("cap", "book") else 1)' "$1" 2>/dev/null; }
# #151 (App: hold the review when AI requests did not finish): AI_RETRY=1 asks the AI again for what a run held at its
# review stop did not finish ("Ask the AI Again"), in two parts (review 25 §2.4): the unfinished page readings first, else
# the unfinished language step. Intake, audit and the work order are not run again; the call stops for review again.
RETRY=; RETRY_PART=
if [[ -n ${AI_RETRY:-} ]]; then
  RETRY_PART=$(python3 -c 'import json,os,sys
from lib import aistatus
R = sys.argv[1]
if not os.path.exists(os.path.join(R, "workorder.ai.json")): sys.exit("refusing: this run is not waiting for a review, so there is nothing to ask the AI again")
for f, why in (("record.json", "the run has been applied"), ("review.json", "the review was finished"), ("review_decisions.json", "a review was started"),
               (aistatus.OVERRIDE, "the review was opened without the missing suggestions")):
    if os.path.exists(os.path.join(R, f)): sys.exit(f"refusing to ask the AI again: {why}")
part = aistatus.retry_parts(aistatus.status(R))
if not part: sys.exit("refusing: nothing that the AI can be asked again is unfinished in this run")
print(part)' "$R" 2>&1) || { echo "${RETRY_PART:-refusing}"; exit 1; }
  RETRY=1; REVIEW=1
  # review 29 M1: the run's own settings, from its review stop, for each one this call didn't set (a terminal retry gives
  # none). The step and per-PDF limits are not taken from it: those figures are the first call's bounds, not limits
  # (review 29 M2); the current limits apply, and the app's Spend binds its job to the amount it showed.
  while IFS='=' read -r k v; do
    if [[ $k == OUT ]]; then                     # OUT has its default already (line 48): USER_OUT says whether the caller gave one
      [[ -z $USER_OUT ]] && USER_OUT=$v && OUT=$v && { [[ $OUT == *.[pP][dD][fF] ]] || OUT=$OUT.pdf; } && echo "  OUT=$v (from this run's review stop)"
    elif [[ -n $k && -z ${!k:-} ]]; then export "$k=$v"; echo "  $k=$v (from this run's review stop)"; fi
  done < <(python3 -c 'import json,sys
e = (json.load(open(sys.argv[1])).get("env") or {}) if __import__("os").path.exists(sys.argv[1]) else {}
for k in ("OCR_LANG", "INTAKE_REUSE", "INTAKE", "OUT", "MODEL", "LANGUAGE_MODEL"):
    if e.get(k): print(f"{k}={e[k]}")' "$R/review_stop.json")
  echo "▶ asking the AI again for the unfinished $( [[ $RETRY_PART == pages ]] && echo 'page readings' || echo 'language suggestions' ) (the work order is not decided again)"
fi
if [[ -n $RETRY ]]; then
  :
elif [[ -f $R/workorder.ai.json ]]; then         # stopped for a person's review (REVIEW=1): never decide again over it
  if [[ ! -f $R/review.json ]]; then
    echo "the AI's work order in $R is waiting for a review. Finish it first:"
    echo "  python3 $(pwd)/review_workorder.py \"$R\" --serve"; exit 1
  fi
  REVIEWED=1; echo "▶ the work order was reviewed by a person: applying the reviewed version (no AI request)"
elif [[ -z ${REPLY:-} && -f $R/workorder.json && $FIG == merged ]]; then
  # every request of the earlier attempt finished, figure requests included, and a later step failed: its work order and
  # run.json are this run's own (its calls stay counted as this run's spending; not a replay)
  MERGED=1; echo "▶ every AI request of the previous attempt finished (a later step failed): applying its work order, no new AI request"
elif [[ $FIG == calling ]]; then               # before the next branch: a stop just after workorder.json is written must not replay the first reply alone
  log_attempt                                  # stopped while its figure requests were being sent: logged, then started over
elif [[ -z ${REPLY:-} && -f $R/workorder.json && -f $R/response.json ]]; then
  REPLY=$R/response.json
  echo "▶ the previous attempt's reply was complete (a later step failed): reusing it, no new AI request"
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
    "$R/timing.json" "${REVIEWED:-}${RETRY:-}" "${TIMES[@]}"   # kept at the review stop, so the record has the whole run (report.py removes it)
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
  if [[ ( -n $REVIEWED || -n $RETRY ) && -f $R/_intake/intake.json ]]; then   # applying a reviewed order (or asking the AI again, #151): the intake it was decided on, never a new one
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
# a PDF edited by hand (handedit.py import): the copy with stale alt text removed, unless intake had to tag it
# (the same folder however it is written: both sides absolute and with links resolved, #144)
if [[ $PSRC == "$SRC" && -f $R/_handedit/input.pdf && $(cd "$(dirname "$SRC")" && pwd -P) == "$(cd "$R/_handedit" && pwd -P)" ]]; then PSRC=$R/_handedit/input.pdf; fi
same_source() { [[ -f $A/digest.json ]] && python3 -c "import json,hashlib,sys; d=json.load(open('$A/digest.json')); sys.exit(0 if d['source']['sha256'] == hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest() else 1)" "$PSRC"; }
if same_source; then
  echo "▶ 1/5 audit: reusing the audit already in $A"
  [[ -f $A/verapdf.json ]] || stage "1/5 veraPDF on the original (audit made before veraPDF was added)" python3 vera.py "$PSRC" "$A/verapdf.json"
else
  stage "1/5 audit (no model)"          python3 audit.py "$PSRC" "$A"
fi
pages_listed() { python3 -c "import json,sys; sys.exit(0 if json.load(open(sys.argv[1])).get('pages') else 1)" "$A/page_reads.json" 2>/dev/null; }   # the audit found pages to read (#49)
if [[ -n $SAVED ]]; then
  echo "▶ 2/5 the previous attempt's reply was complete but could not be read: reading it again (no cost)"
  cp "$R/run.json" "$R/run.prev.json"; s=$(now)
  if python3 decide.py "$A" "$R" --response-file "$R/response.json" ${MT[@]+"${MT[@]}"}; then
    rm -f "$R/run.prev.json"; e=$(now); d=$(python3 -c "print(f'{$e-$s:.2f}')")
    TIMES+=("2/5 reuse saved reply (no cost)|$d"); echo "  ✓ 2/5 reuse saved reply (no cost): $(fmt "$d")"
    REPLY=$R/response.json; REUSED=1
  else
    mv "$R/run.prev.json" "$R/run.json"; rm -f "$R/workorder.json"
    echo "▶ the saved reply still cannot be read: its cost is logged and a new request is made"; log_attempt
  fi
fi
if [[ -n ${ESTIMATE:-} && ( -n ${REPLY:-} || -n $REVIEWED || -n $MERGED || ${DECIDE:-} == none ) ]]; then echo "estimate only: no cost, no new AI request will be made"; summary; exit 0; fi
# the folder's own reply, reused after a later step failed (156) or read again (REUSED): computed here, before the branch
# below, so it keeps this folder's ai_outcome.json (#151, review 26 M1)
OWN_REPLY=; [[ -n ${REPLY:-} && -f $R/response.json && $(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$REPLY") == $(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$R/response.json") ]] && OWN_REPLY=1
if [[ -n ${REUSED:-} || -n $REVIEWED || -n $MERGED || -n $RETRY ]]; then
  :                                              # #151: these keep ai_outcome.json and add to it
elif [[ ${DECIDE:-} == none ]]; then
  python3 -m lib.aistatus create "$R"            # #151: a call that decides the work order anew starts a fresh outcome file
  stage "2/5 no AI call (a person decides)" python3 decide.py "$A" "$R" --no-model
elif [[ -n ${REPLY:-} ]]; then
  [[ -n $OWN_REPLY ]] || python3 -m lib.aistatus create "$R"   # this folder's own reply keeps its outcomes (26 M1)
  stage "2/5 reuse saved reply (no cost)" python3 decide.py "$A" "$R" --response-file "$REPLY" ${MT[@]+"${MT[@]}"}
else
  [[ -n ${ESTIMATE:-} ]] || python3 -m lib.aistatus create "$R"   # an estimate is not a run: it records no outcome
  # the page readings' own estimate first (page_reads_estimate.json): the cost lines below and the app's estimate include it
  if [[ $PAGE_READS != off ]] && pages_listed; then
    python3 read_pages.py "$A" "$R" --dry-run ${MODEL:+--model "$MODEL"} || echo "page readings: no estimate (see the line above)"
  else
    # #151 (review 24 M2/M3): an estimate in this folder that left the step out for its cost is recorded before it goes.
    # An estimate-only call (a batch's estimate step) keeps such a file for the run that follows it
    if [[ -n ${ESTIMATE:-} ]] && refused_est "$R/page_reads_estimate.json"; then :
    else
      if left=$(python3 -m lib.aistatus refused "$R" pages "$R/page_reads_estimate.json" 2>/dev/null); then
        echo "page readings: left out for their cost by an earlier estimate in this folder (${left}): the review will hold until they are included or \"Review Without the Missing Suggestions\" is chosen"
      fi
      rm -f "$R/page_reads_estimate.json"
    fi
  fi
  # the language step's own estimate too (language_estimate.json, #118): the cost lines and the app's estimate include it.
  # #159 (review 29 M4): the work order is priced first, so the language step fills to the room left in the PDF's limit
  if [[ $LANG_TAGS != off ]]; then
    python3 decide.py "$A" "$R" --dry-run ${MT[@]+"${MT[@]}"} > /dev/null 2>&1 || true
    python3 name_languages.py "$A" "$R" --pdf "$PSRC" --dry-run ${LANGUAGE_MODEL:+--model "$LANGUAGE_MODEL"} || echo "language tags: no estimate (see the line above)"
  else
    if [[ -n ${ESTIMATE:-} ]] && refused_est "$R/language_estimate.json"; then :
    else
      if left=$(python3 -m lib.aistatus refused "$R" language "$R/language_estimate.json" 2>/dev/null); then
        echo "language tags: left out for their cost by an earlier estimate in this folder (${left}): the review will hold until they are included or \"Review Without the Missing Suggestions\" is chosen"
      fi
      rm -f "$R/language_estimate.json"
    fi
  fi
  stage "2/5 cost estimate (no model)"  python3 decide.py "$A" "$R" --dry-run ${MT[@]+"${MT[@]}"}
  if [[ -n ${ESTIMATE:-} ]]; then
    echo "estimate only: $R/run.json (audit kept for the real run)"; summary; exit 0
  fi
  if [[ -n ${AUTO:-} ]]; then
    ok=y
    if [[ $USE_MODEL == anthropic/* ]]; then
      read -r L_CALL L_BOOK < <(python3 -c "from lib import costs as c; L = c.DEFAULT_LIMITS; print(f'{L[\"per_call_usd\"]:.2f} {L[\"per_book_usd\"]:.2f}')")
      echo "AUTO=1: sending without asking (still refused over the \$${MAX_USD:-$L_CALL} limit per AI request, the \$${BOOK_MAX_USD:-$L_BOOK} limit per PDF, or your credit)"
    else
      echo "AUTO=1: sending without asking. The dollar limits apply to Claude models only: the $USE_MODEL estimate is approximate and not a limit; the OpenRouter bill is the real cost"
    fi
  else
    read -r -p "Send to OpenRouter now? [y/N] " ok
  fi
  if [[ ${ok:-n} != [yY]* ]]; then
    echo "stopped before the AI request"; [[ -z ${KEEP:-} && -n $NEW ]] && rm -rf "$R"; summary; exit 0
  fi
  stage "3/5 $USE_MODEL via OpenRouter" python3 decide.py "$A" "$R" ${MT[@]+"${MT[@]}"}
fi
# Page readings (on unless PAGE_READS=off): scanned pages the audit found mostly Hawaiian are read whole by the AI
# (read_pages.py, issue #49): its own paid step, with its own estimate and limit (PAGE_READS_MAX_USD, default 3). A PDF
# with no such pages costs nothing. Pages read before are reused at no cost. A saved reply from elsewhere (FROM=, or
# REPLY= of another folder) makes no new AI request, so it reads no pages, and neither does a run with no AI request
# (DECIDE=none: a PDF edited by hand). A retry on this folder's own reply (a later step failed: the same command again,
# or the app's "Try Again", #95) gets the pages already read back from page_reads_run.json (decide.py, no cost, no
# network); pages the interrupted step never read are read now, under the step's own estimate, limit and credit, as on a
# first run (the app's "Try Again" runs with PAGE_READS=off: they are listed for a person). A refusal (over the limit,
# the credit, OpenRouter unreachable) or a "no" skips the step: the PDF goes on without readings and the report lists the
# pages for a person.
page_reads_step() {             # each of its failures is reported and skipped, never the end of the run
  python3 read_pages.py "$A" "$R" "$@" ${MODEL:+--model "$MODEL"} ${BOOK_MAX_USD:+--book-max-usd "$BOOK_MAX_USD"} || { echo "page readings not done (above): the PDF goes on without them"; return 0; }
}
pages_left() {                  # pages the audit lists that page_reads_run.json holds no complete reading for (#95)
  python3 -c 'import json,os,sys
listed = {p["page"] for p in json.load(open(sys.argv[1])).get("pages") or []}
run = json.load(open(sys.argv[2])) if os.path.exists(sys.argv[2]) else {}
done = {x.get("page") for x in run.get("pages") or [] if x.get("finish") == "stop" and (x.get("text") or "").strip()}
print(len(listed - done))' "$A/page_reads.json" "$R/page_reads_run.json" 2>/dev/null || echo 1
}
if [[ -n $MERGED && -f $R/page_reads_run.json ]]; then   # #95: the merged path keeps workorder.json as it was; an interruption
  # before read_pages.py wrote into it would lose pages already paid for, so they are put back from their own file, as
  # decide.py does on a retry of its own reply (no cost, no network)
  python3 -c 'import json,sys
run = json.load(open(sys.argv[1])); wo = json.load(open(sys.argv[2]))
pages = [{"page": x["page"], "text": x["text"]} for x in run.get("pages") or [] if x.get("finish") == "stop" and (x.get("text") or "").strip()]
if pages: wo["page_readings"] = pages; json.dump(wo, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False, indent=1)' "$R/page_reads_run.json" "$R/workorder.json" \
    || echo "page readings: the pages read before could not be put back (see above)"
fi
# #151: was the language step finished before a retry's page part? (review 26 M2: only then can new readings be the reason)
LANG_DONE_BEFORE=
[[ -n $RETRY && $RETRY_PART == pages && -f $R/language_run.json ]] && python3 -c 'import sys
from lib import aistatus
sys.exit(1 if "language" in aistatus.status(sys.argv[1])["steps"] else 0)' "$R" && LANG_DONE_BEFORE=1
if [[ -n $RETRY ]]; then
  # #151: "Ask the AI Again", one part per call (review 25 §2.4)
  part_ok=n
  if [[ $RETRY_PART == pages ]]; then
    # the retry's own dry run records nothing: refused under the bound limit (prices moved), the part keeps its earlier outcome
    if python3 read_pages.py "$A" "$R" --dry-run ${MODEL:+--model "$MODEL"}; then part_ok=y; fi
    if [[ $part_ok == y && -z ${AUTO:-} ]]; then read -r -p "Read the unfinished pages with the AI now? [y/N] " part_ok || part_ok=n; fi
    if [[ ${part_ok:-n} == [yY]* ]]; then stage "retry: page readings via OpenRouter" page_reads_step --outcome
    else [[ -z ${AUTO:-} ]] && outcome pages declined; echo "page readings not asked again (above)"; fi
    # the readings change words the language step answered: the language step is estimated again, never sent in this call
    if [[ -n $LANG_DONE_BEFORE ]] && env -u LANGUAGE_MAX_USD python3 name_languages.py "$A" "$R" --pdf "$PSRC" --dry-run --outcome --estimate-to "$R/language_retry_estimate.json" ${LANGUAGE_MODEL:+--model "$LANGUAGE_MODEL"}; then
      if python3 -c 'import json,sys; sys.exit(0 if (json.load(open(sys.argv[1])).get("to_send") or 0) > 0 else 1)' "$R/language_retry_estimate.json" 2>/dev/null; then
        outcome language pages_changed "New page readings changed some words."
        echo "language tags: the new page readings changed some words: their language suggestions are estimated again (ask the AI again to send them)"
      fi
    fi
  else
    if python3 name_languages.py "$A" "$R" --pdf "$PSRC" --dry-run ${LANGUAGE_MODEL:+--model "$LANGUAGE_MODEL"}; then part_ok=y; fi
    if [[ $part_ok == y && -z ${AUTO:-} ]]; then read -r -p "Ask the AI again for the unfinished language suggestions now? [y/N] " part_ok || part_ok=n; fi
    if [[ ${part_ok:-n} == [yY]* ]]; then
      stage "retry: language tags via OpenRouter" bash -c 'python3 name_languages.py "$@" || echo "language tags not done (above): the review stays held"' _ "$A" "$R" --pdf "$PSRC" --outcome ${LANGUAGE_MODEL:+--model "$LANGUAGE_MODEL"} ${BOOK_MAX_USD:+--book-max-usd "$BOOK_MAX_USD"}
    else [[ -z ${AUTO:-} ]] && outcome language declined; echo "language suggestions not asked again (above)"; fi
  fi
elif [[ ( -n $OWN_REPLY || -n $MERGED ) && -f $R/page_reads_run.json && $(pages_left) == 0 ]] && pages_listed; then
  echo "page readings: every page was read before: their readings are kept (no cost, no AI request)"
  outcome pages saved
elif [[ ${PAGE_READS} != off && ( -z ${REPLY:-} || -n $OWN_REPLY ) && -z $REVIEWED && ${DECIDE:-} != none ]] && pages_listed; then
  pr_ok=n
  if python3 read_pages.py "$A" "$R" --dry-run --outcome ${MODEL:+--model "$MODEL"}; then
    if [[ -n ${AUTO:-} ]]; then pr_ok=y; echo "AUTO=1: reading the pages without asking (still refused over the page readings' limit or your credit)"
    else read -r -p "Read these pages with the AI now? [y/N] " pr_ok || pr_ok=n; fi      # no terminal: no
  else echo "page readings not done (above): the PDF goes on without them"; fi
  if [[ ${pr_ok:-n} == [yY]* ]]; then stage "3b/5 page readings via OpenRouter" page_reads_step --outcome
  elif [[ -z ${AUTO:-} ]]; then echo "page readings skipped: the report lists the pages for a person"; outcome pages declined; fi
elif [[ -z $REVIEWED ]] && pages_listed; then
  outcome pages not_run                          # #151: a saved reply from elsewhere, DECIDE=none or PAGE_READS=off (a refusal stays)
fi
# Language tags (#118; on unless LANG_TAGS=off): name_languages.py names the language of the candidate words and
# passages the audit found, and writes language_parts into the work order. Its own paid step, with its own model
# (LANGUAGE_MODEL, default Sonnet 5.5), estimate and limit (LANGUAGE_MAX_USD, default 6). A saved reply (REPLY=, FROM=)
# never starts a request (review 02, M3): its saved language decisions are used (LANG_REPLY=, or this folder's own
# language_run.json when the reply is this folder's own), else the step is not run and the record says so.
lang_step() {                   # each failure is reported and skipped, never the end of the run
  python3 name_languages.py "$A" "$R" --pdf "$PSRC" "$@" ${LANGUAGE_MODEL:+--model "$LANGUAGE_MODEL"} ${BOOK_MAX_USD:+--book-max-usd "$BOOK_MAX_USD"} || { echo "language tags not done (above): the PDF goes on without them"; return 0; }
}
if [[ -n $RETRY ]]; then
  :                                              # #151: the retry's part ran above
elif [[ ( $LANG_TAGS != off || -n ${LANG_REPLY:-} ) && -z $REVIEWED && ${DECIDE:-} != none && -f $R/workorder.json ]]; then   # saved decisions apply even with the step off: no cost
  if [[ -n ${REPLY:-} || -n $MERGED ]]; then
    if [[ -n ${LANG_REPLY:-} && -f ${LANG_REPLY:-} ]]; then stage "3c/5 language tags: saved decisions (no cost)" lang_step --response-file "$LANG_REPLY"; outcome language saved
    elif [[ -f $R/language_run.json && ( $REPLY == "$R/response.json" || -n $MERGED ) ]]; then stage "3c/5 language tags: this run's own decisions (no cost)" lang_step --reuse; outcome language saved
    else echo "language tags: not run (a saved reply makes no new AI request, and none of its language decisions was saved)"; outcome language not_run; fi
  else
    lt_ok=n
    if python3 name_languages.py "$A" "$R" --pdf "$PSRC" --dry-run --outcome ${LANGUAGE_MODEL:+--model "$LANGUAGE_MODEL"}; then
      # #159 (Patrick's decision): word forms the limits hold back are said before anything is sent: a warning, not a refusal
      python3 -c 'import json,sys
from lib import aistatus
w = aistatus.held_back_words(json.load(open(sys.argv[1])), terminal=True)
if w: print("language tags: " + w)' "$R/language_estimate.json" 2>/dev/null || true
      if python3 -c 'import json,sys; e=json.load(open(sys.argv[1])); sys.exit(0 if not e.get("to_send") and e.get("local") else 1)' "$R/language_estimate.json" 2>/dev/null; then
        lt_ok=y; echo "language tags: every word form is decided by the reading printed beside it (#123): no AI request, nothing to ask"
      elif [[ -n ${AUTO:-} ]]; then lt_ok=y; echo "AUTO=1: naming languages without asking (still refused over the language step's limit or your credit)"
      else read -r -p "Name the languages of these words and passages with the AI now? [y/N] " lt_ok || lt_ok=n; fi
    else echo "language tags not done (above): the PDF goes on without them"; fi
    if [[ ${lt_ok:-n} == [yY]* ]]; then stage "3c/5 language tags via OpenRouter" lang_step --outcome
    elif [[ -z ${AUTO:-} ]]; then echo "language tags skipped: the PDF goes on without them"; outcome language declined; fi
  fi
elif [[ -z $REVIEWED ]]; then
  outcome language not_run                       # #151: the step off, DECIDE=none, or no work order (a refusal recorded at 248 stays)
fi
if [[ -n ${REVIEW:-} && -z $REVIEWED ]]; then     # stop here: a person reviews the AI's decisions before anything is applied
  cp "$R/workorder.json" "$R/workorder.ai.json"
  stage "${RETRY:+retry: }review: page images (no model)" python3 review_workorder.py "$R" --prepare --pdf "$PSRC"   # a retry's stages keep their own labels (#151)
  write_timing                                   # intake, audit, the AI call and the page images: the apply adds its own
  python3 -c 'from lib import costs; import sys; print(costs.after_line(sys.argv[1]))' "$R" || true
  # #151: what did not finish holds the review; "Ask the AI Again" shows the amount of its next part, estimated here (free)
  if python3 -m lib.aistatus held "$R" "$A" > "$R/.held.txt" 2>/dev/null; then
    echo; echo "the review will hold: some AI suggestions are missing"; sed 's/^/  /' "$R/.held.txt"
    case $(python3 -m lib.aistatus retry "$R" "$A") in
      # review 29 M2: estimated under the current limits, never under a job's bound (the amount a Spend showed)
      pages) env -u PAGE_READS_MAX_USD -u LANGUAGE_MAX_USD python3 read_pages.py "$A" "$R" --dry-run --estimate-to "$R/page_reads_retry_estimate.json" ${MODEL:+--model "$MODEL"} > /dev/null 2>&1 || echo "  (the page readings' estimate could not be made now)" ;;
      language) [[ -f $R/language_retry_estimate.json && $R/language_retry_estimate.json -nt $R/language_run.json ]] \
                  || env -u PAGE_READS_MAX_USD -u LANGUAGE_MAX_USD python3 name_languages.py "$A" "$R" --pdf "$PSRC" --dry-run --estimate-to "$R/language_retry_estimate.json" ${LANGUAGE_MODEL:+--model "$LANGUAGE_MODEL"} > /dev/null 2>&1 \
                  || echo "  (the language suggestions' estimate could not be made now)" ;;
    esac
    echo "  to ask the AI again: AI_RETRY=1 bash $(pwd)/run_api.sh \"$SRC\" $NAME $(basename "$R")"
  fi
  rm -f "$R/.held.txt"
  # what the app's "Apply" needs to run this same script's second call (webapp/runs.py start_first_apply); report.py removes it
  # (#151: and what "Ask the AI Again" runs with: the models and the limits this run had)
  [[ -n $RETRY ]] || python3 -c "import json,sys; ks=('OCR_LANG', 'INTAKE_REUSE', 'INTAKE', 'OUT', 'MODEL', 'LANGUAGE_MODEL', 'BOOK_MAX_USD', 'LANGUAGE_MAX_USD', 'PAGE_READS_MAX_USD'); json.dump({'src': sys.argv[1], 'name': sys.argv[2], 'env': {k: v for k, v in zip(ks, sys.argv[3:12]) if v}}, open(sys.argv[12], 'w'), indent=1)" \
    "$SRC" "$NAME" "${OCR_LANG:-}" "${INTAKE_REUSE:-}" "${INTAKE:-}" "$USER_OUT" "${MODEL:-}" "${LANGUAGE_MODEL:-}" "${BOOK_MAX_USD:-}" "${LANGUAGE_MAX_USD:-}" "${PAGE_READS_MAX_USD:-}" "$R/review_stop.json"
  summary
  echo
  echo "stopped for review: nothing has been applied yet"
  echo "Open the run page to review and apply: python3 $(pwd)/app.py \"$R\""
  echo "Or in the terminal:"
  echo "  1. python3 $(pwd)/review_workorder.py \"$R\" --serve     opens the review page"
  echo "  2. ${INTAKE_REUSE:+INTAKE_REUSE=$INTAKE_REUSE }${OCR_LANG:+OCR_LANG=$OCR_LANG }${INTAKE:+INTAKE=$INTAKE }${USER_OUT:+OUT=$USER_OUT }${RUN_DIR:+RUN_DIR=$R }bash $(pwd)/run_api.sh \"$SRC\" $NAME $(basename "$R")     afterwards (without REVIEW=1): applies the reviewed work order"
  exit 0
fi
rm -f "$A/dryrun.key.json"                      # #93: the key of the order applied, for report.py to keep this apply's moves for
if [[ -z $REVIEWED ]]; then                     # the first "Review Again" (review/core.py keep_trial); not a stage: no timing entry
  python3 -c 'import sys
try:
    from review import core
    core.save_key(*sys.argv[1:4])
except Exception as e: print(f"note: the figure moves of this apply will not be kept for a later review ({type(e).__name__})")' \
    "$PSRC" "$R/workorder.json" "$A/dryrun.key.json" || echo "note: the figure moves of this apply will not be kept for a later review"
fi
stage "4/5 apply (no model)"            python3 apply.py "$PSRC" "$R/workorder.json" "$R/$OUT"
stage "4/5 verify (no model)"           bash -c 'python3 verify.py "$1" "$2" > /dev/null' _ "$PSRC" "$R/$OUT"
write_timing
stage "5/5 report"                      python3 report.py "$R" "$A" "--pdf=$OUT" "--input=$PSRC" "--lang-tags=$LANG_TAGS" ${KEEP:+--keep}
summary
echo
echo "done: $R"
echo "  $OUT   the result: run PAC on this"
echo "  review.md     what a person should check"
echo "  record.json   the full record: decisions, cost, timing, checks"
echo; python3 -c 'from lib import costs; import sys; print(costs.after_line(sys.argv[1]))' "$R" || true
if python3 -c "import json,sys; sys.exit(0 if (json.load(open(sys.argv[1])).get('run') or {}).get('no_model') else 1)" "$R/record.json" 2>/dev/null; then
  exit 0                                                  # DECIDE=none: no AI request, so no credit used and nothing to look up at OpenRouter
fi
CREDIT=$(python3 decide.py --credit "$R/record.json" 2>/dev/null || true)
if [[ -n $CREDIT ]]; then echo; echo "credit left: \$$CREDIT"; else echo; echo "credit left: could not check (no key, or OpenRouter unreachable)"; fi
