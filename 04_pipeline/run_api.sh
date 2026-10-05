#!/usr/bin/env bash
# One OpenRouter run, start to finish: Claude decides, the code applies, checks and reports.
#   bash run_api.sh <original.pdf> <short-name> [run-label]
#   bash run_api.sh ../02_samples/cadaverous/<file>.pdf cadaverous api-run1   →  PDFREM/runs/cadaverous/api-run1/
# Needs OPENROUTER_API_KEY in a .env file in or above this folder. Asks before spending anything.
# KEEP=1  bash run_api.sh …   keeps the working files (digest, figure crops, raw reply, logs) for debugging
# REPLY=path/to/reply.txt bash run_api.sh …   reuses a saved Claude reply instead of calling the API (no cost)
# AUTO=1 bash run_api.sh …   no y/N question: sends if the estimate is within the $2 cap and your credit
# ESTIMATE=1 bash run_api.sh …   audit + cost estimate only; a later run with the same label reuses the audit
# OUT=clan.pdf bash run_api.sh …   names the result; by default it is <original file name>_remediated.pdf
# MAX_TOKENS=32000 bash run_api.sh …   output limit for Claude's reply, reasoning included (default 16000, set in decide.py)
#
# Rerunning a label that did not finish picks up where it stopped: the audit is reused; a reply that was cut off
# is logged with its cost (attempts.json, folded into record.json) and a new call is made; a reply that was fine
# but a later step failed is reused at no cost.
# Outputs go to PDFREM/runs/<short-name>/<run-label>/ (beside 04_pipeline). RUNS_DIR=/some/path overrides it.
# RUN_DIR=/exact/folder sets the run folder itself (batch_api.sh uses it: runs/batches/<label>/<name>/).
set -euo pipefail
SRC=${1:?path to the original PDF}; NAME=${2:?short name, e.g. cadaverous}; RUN=${3:-api-$(date +%Y%m%d-%H%M)}
[[ -f $SRC ]] || { echo "no such PDF: $SRC"; exit 1; }
SRC=$(cd "$(dirname "$SRC")" && pwd)/$(basename "$SRC")      # absolute, so it works from any folder
BASE=$(basename "$SRC"); OUT=${OUT:-${BASE%.*}_remediated.pdf}; [[ $OUT == *.[pP][dD][fF] ]] || OUT=$OUT.pdf
[[ $OUT != */* ]] || { echo "OUT is a file name, not a path: $OUT"; exit 1; }
cd "$(dirname "$0")"
RUNS=${RUNS_DIR:-$(cd .. && pwd)/runs}
R=${RUN_DIR:-$RUNS/$NAME/$RUN}; A=$R/_audit
if [[ -f $R/record.json ]]; then echo "$R already holds a finished run: choose another run label"; exit 1; fi
if [[ -n ${MAX_TOKENS:-} && ! $MAX_TOKENS =~ ^[0-9]+$ ]]; then echo "MAX_TOKENS must be a whole number: $MAX_TOKENS"; exit 1; fi
MT=(); [[ -z ${MAX_TOKENS:-} ]] || MT=(--max-tokens "$MAX_TOKENS")
NEW=; [[ -d $R ]] || NEW=1
mkdir -p "$R"

# an earlier attempt in this folder that did not finish
if [[ -z ${REPLY:-} && -f $R/workorder.json && -f $R/response.json ]]; then
  REPLY=$R/response.json
  echo "▶ the earlier attempt's reply was complete (a later step failed): reusing it, no new API call"
elif [[ -f $R/run.json ]]; then
  python3 - "$R" <<'PY2'
import sys, os, json, datetime
R = sys.argv[1]; run = json.load(open(os.path.join(R, 'run.json'), encoding='utf-8'))
cost = (run.get('usage') or {}).get('cost_usd')
if cost and not run.get('response_from'):                       # a paid call whose reply could not be used
    p = os.path.join(R, 'attempts.json'); att = json.load(open(p)) if os.path.exists(p) else []
    att.append({'started': run.get('started'), 'cost_usd': cost, 'finish_reason': run.get('finish_reason'),
                'max_tokens': (run.get('estimate') or {}).get('max_tokens'), 'usage': run.get('usage'),
                'logged': datetime.datetime.now().isoformat(timespec='seconds')})
    json.dump(att, open(p, 'w'), indent=1)
    os.remove(os.path.join(R, 'run.json'))
    print(f'▶ earlier attempt logged: ${cost:.3f} spent, reply {"cut off" if run.get("finish_reason") == "length" else "unusable"}; making a new call')
PY2
fi

now() { python3 -c 'import time; print(f"{time.time():.2f}")'; }
fmt() { python3 -c "s=float('$1'); print(f'{s:.1f}s' if s < 60 else f'{int(s//60)}m {s%60:04.1f}s')"; }
TIMES=()
stage() {                      # stage "label" command…  → runs it and prints how long it took
  local label=$1; shift; local s e d
  echo "▶ $label"; s=$(now); "$@"; e=$(now)
  d=$(python3 -c "print(f'{$e-$s:.2f}')"); TIMES+=("$label|$d"); echo "  ✓ $label: $(fmt "$d")"
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

same_source() { [[ -f $A/digest.json ]] && python3 -c "import json,hashlib,sys; d=json.load(open('$A/digest.json')); sys.exit(0 if d['source']['sha256'] == hashlib.sha256(open('$SRC','rb').read()).hexdigest() else 1)"; }
if same_source; then
  echo "▶ 1/5 audit: reusing the audit already in $A"
else
  stage "1/5 audit (no model)"          python3 audit.py "$SRC" "$A"
fi
if [[ -n ${ESTIMATE:-} && -n ${REPLY:-} ]]; then echo "estimate only: no cost, a saved reply will be reused"; summary; exit 0; fi
if [[ -n ${REPLY:-} ]]; then
  stage "2/5 reuse saved reply (no cost)" python3 decide.py "$A" "$R" --response-file "$REPLY"
else
  stage "2/5 cost estimate (no model)"  python3 decide.py "$A" "$R" --dry-run ${MT[@]+"${MT[@]}"}
  if [[ -n ${ESTIMATE:-} ]]; then echo "estimate only: $R/run.json (audit kept for the real run)"; summary; exit 0; fi
  if [[ -n ${AUTO:-} ]]; then
    ok=y; echo "AUTO=1: sending without asking (decide.py still refuses anything over the cap or your credit)"
  else
    read -r -p "Send to OpenRouter now? [y/N] " ok
  fi
  if [[ ${ok:-n} != [yY]* ]]; then
    echo "stopped before the API call"; [[ -z ${KEEP:-} && -n $NEW ]] && rm -rf "$R"; summary; exit 0
  fi
  stage "3/5 Claude via OpenRouter"     python3 decide.py "$A" "$R" ${MT[@]+"${MT[@]}"}
fi
stage "4/5 apply (no model)"            python3 apply.py "$SRC" "$R/workorder.json" "$R/$OUT"
stage "4/5 verify (no model)"           bash -c 'python3 verify.py "$1" "$2" > /dev/null' _ "$SRC" "$R/$OUT"
python3 -c "import json,sys; json.dump({l.split('|')[0]: round(float(l.split('|')[1]), 1) for l in sys.argv[1:]}, open('$R/timing.json', 'w'), indent=1)" "${TIMES[@]}"
stage "5/5 report"                      python3 report.py "$R" "$A" "--pdf=$OUT" ${KEEP:+--keep}
summary
echo
echo "done: $R"
echo "  $OUT   the result: run PAC on this"
echo "  review.md     what a person should check"
echo "  record.json   the full record: decisions, cost, timing, checks"
CREDIT=$(python3 decide.py --credit "$R/record.json" 2>/dev/null || true)
if [[ -n $CREDIT ]]; then echo; echo "credit left: \$$CREDIT"; else echo; echo "credit left: could not check (no key, or OpenRouter unreachable)"; fi
