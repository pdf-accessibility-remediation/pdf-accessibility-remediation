---
title: Running
nav_order: 3
---

# Running

## Run

```bash
cd pipeline
bash run_api.sh ../samples/group1/clans.pdf clanstest apirun1
```

The script audits the PDF and shows the cost estimate and your available credit. It **asks before calling the API**, then applies Claude's work order, verifies the result and writes the report. Use a new run label (`api-run2` …) for each run. `KEEP=1 bash run_api.sh …` keeps the working files for debugging.

To have a person check the AI's decisions before they are applied, start with `REVIEW=1`: the run stops after the model call, and `review_workorder.py --serve` opens a review page (see [Reviewing the work order](review-step.md)).

The short name (`clans`) names the run folder. The result is named after the original with `_remediated` added (`<file>_remediated.pdf`); `OUT=clans.pdf bash run_api.sh …` names it yourself.

## Step by step (what `run_api.sh` does)

```bash
S=../samples/cadaverous/<file>.pdf
R=../runs/cadaverous/api-run1;  A=$R/_audit
python3 intake.py $S $R/_intake                           # untagged only: OCR + auto-tag; then S=$R/_intake/intake.pdf
python3 audit.py  $S $A                                   # no model, ~30 s; also veraPDF on the original → $A/verapdf.json
python3 decide.py $A $R --dry-run                         # cost estimate + available credit; sends nothing
python3 decide.py $A $R                                   # the API call
# REVIEW=1 stops here: workorder.ai.json + review_workorder.py $R --prepare --pdf $S, then a person runs --serve
O=$R/<file>_remediated.pdf
python3 apply.py  $S $R/workorder.json $O                 # no model, ~80 s
python3 verify.py $S $O                                   # no model, ~3 min; veraPDF on the result runs alongside
python3 report.py $R $A                                   # review.md, record.json, han_review.csv; add --keep to keep working files
```

If `decide.py` fails after the API call, the raw reply is in `$R/reply.txt` and OpenRouter's full response in `$R/response.json`. A reply that was cut off can't be used; rerun `run_api.sh` with the same label and a higher `MAX_TOKENS` (see [Options](options.md)). For errors from OpenRouter itself, see [When the model call fails](troubleshooting.md#when-the-model-call-fails).
