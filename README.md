# PDF Accessibility Remediation Pipeline

Claude reads a compact summary of a tagged PDF and returns a **work order**: a JSON file of decisions (heading levels, alt text, what to artifact, language, reading-order fixes). The code carries those decisions out, checks the result, writes a review for a person, and never changes the original. The only paid step is the model call in `decide.py`.

```
original.pdf ─► audit.py ─► decide.py (model via OpenRouter) ─► apply.py ─► verify.py ─► report.py
                 digest        work order                        original_remediated.pdf review.md + record.json
```

## Setup (once)

1. **Python packages:** First cd to pipeline, then create and activate the virtual environment with `python3 -m venv .venv && source .venv/bin/activate`. Then `pip install -r requirements.txt` (pdfplumber must be 0.11.9: `plumb_fix.py` patches its internals).
2. **Key:** put `OPENROUTER_API_KEY=…` in a `.env` file in `pipeline/` or any folder above it (e.g. the repo root). Keep `.env` in `.gitignore`.
3. **Check the key (free):** `python3 decide.py --check-key`.
4. **Prompt:** `workorder_v4.md` goes in `pipeline/prompts/` or in `prompts/` beside `pipeline/`. Older versions are kept only as a record.
5. **PDFs:** originals go in `samples/<name>/` and are never written to. Outputs go in `runs/<name>/<run-label>/` (single runs) or `runs/batches/<label>/<name>/` (batches) beside `pipeline/` (set `RUNS_DIR` to put them elsewhere). Keep both out of git: the books are in copyright.

## Run

```bash
cd pipeline
bash run_api.sh ../samples/group1/clans.pdf clanstest apirun1
```

The script audits the PDF and shows the cost estimate and your available credit. It **asks before calling the API**, then applies Claude's work order, verifies the result and writes the report. Use a new run label (`api-run2` …) for each run. `KEEP=1 bash run_api.sh …` keeps the working files for debugging.

The short name (`clans`) names the run folder. The result is named after the original with `_remediated` added (`<file>_remediated.pdf`); `OUT=clans.pdf bash run_api.sh …` names it yourself.

## Options

| Before the command | Effect |
|---|---|
| `AUTO=1` | No y/N question: sends straight away. For a Claude model only if the estimate is within the $2 cap and your credit; for any other model the estimate is approximate and not capped (the line printed before sending says which) |
| `ESTIMATE=1` | Audit and cost estimate only; a later run with the same label reuses the audit |
| `REPLY=path/to/reply.txt` | Reuses a saved Claude reply instead of calling the API (no cost) |
| `KEEP=1` | Keeps the working files (digest, figure crops, raw reply, logs) |
| `OUT=name.pdf` | Names the result (default: `<original name>_remediated.pdf`) |
| `MODEL=openai/gpt-5` | Any OpenRouter model id for this run or batch (default: `DEFAULT_MODEL` in `decide.py`, `anthropic/claude-sonnet-5.5`) |
| `MAX_TOKENS=32000` | Output limit for the model's reply, reasoning included (default 16,000). Raise it when a reply is cut off |
| `RUNS_DIR=/path` | Writes runs somewhere other than `PDFREM/runs/` |
| `JOBS=1` | Batches only: books run at the same time (default 3). Use 1 after a rate limit (see "When the model call fails") |

A run label that already holds a finished run is refused, so earlier results are never overwritten.

**If a run stops partway, rerun the same command** (same label). It picks up where it stopped:

- the audit is reused
- a reply that was **cut off** at the output limit is logged with its cost (it ends up in `record.json` under `earlier_attempts`, and in the cost line of `review.md`), then a new call is made. Add `MAX_TOKENS=32000` so it doesn't happen again
- a reply that was complete, where a later step failed, is reused at no cost

The output limit: change the default once in `decide.py` (the line `ap.add_argument('--max-tokens', type=int, default=16000)`), or per run with `MAX_TOKENS=`. Doubling it to 32,000 raises the worst-case estimate by about $0.16 per book with Sonnet; you only pay for what is used.

## Batch runs

```bash
AUTO=1 bash batch_api.sh batch1                                         # every PDF under samples (all subfolders)
AUTO=1 bash batch_api.sh batch1 ../samples/group1                    # one folder
AUTO=1 bash batch_api.sh batch1 ../samples/group1 ../samples/group3   # several folders
AUTO=1 bash batch_api.sh batch1 ../books.txt                            # a list, to choose names yourself
```

Everything a batch makes goes in one folder:

```
PDFREM/runs/batches/batch1/
├── summary.md
├── cadaverous/
│   ├── Cadaverous_remediated.pdf
│   ├── review.md
│   └── record.json
└── clans/ …
```

Names, when you point at folders:

- **Book folder:** a folder holding one PDF gives its folder name (`samples/cadaverous/x.pdf` → `batches/batch1/cadaverous/`). A folder holding several gives each file's name without `.pdf`.
- **Result:** always the original file name with `_remediated` added (`x.pdf` → `x_remediated.pdf`).

A book list sets the book folder, and optionally the result name after a `|`:

```
# <short-name> <path to pdf> [| <result name>]
clan        samples/group3/3-most-accessible_9798880703333.pdf | Korea Five Clans.pdf
cadaverous  samples/cadaverous/Cadaverous.pdf
```

`batch_api.sh` refuses to start without `AUTO=1`, because it calls the API without asking. It works in three steps:

1. **Estimate (no model).** It audits every book and adds up the worst-case cost. It stops before any API call if the Claude total is over `BATCH_MAX_USD` (default $5) or over your credit. The audits are kept, so a rerun with a higher cap reuses them. Only Claude models count against the cap and the credit check (see "Choosing the model"), so the total line depends on the model:

   ```
   # Claude batch
     total worst case             $0.75   batch cap $5.00   credit $11.46
   # non-Claude batch: one approximate line, nothing capped
     worst case                   about $0.75, approximate, not capped (the OpenRouter bill is the real cost)   credit $11.46
   # mixed (e.g. a RETRY with another model): the Claude line is the capped portion
     worst case, capped (Claude)  $0.50   batch cap $5.00   credit $11.46
     worst case, non-Claude       about $0.25, approximate, not capped (the OpenRouter bill is the real cost)
   ```
2. **Run.** It runs every book through the full pipeline, `JOBS` at a time (default 3; each book needs about 0.5–1.5 GB of memory). A failed book doesn't stop the others.
3. **Summary.** It prints the batch start time, model and prompt file, then a table of book, status, pages, API cost, time, checks flagged and result, then the total cost and the credit you have left, and saves it as `summary.md`. A failed book's status says why: `reply cut off at 16,000 tokens`, `OpenRouter 429, model rate-limited (nothing charged)`, or OpenRouter's error code and message. Its log is kept beside the summary (`<name>.log`) only if that book failed; `KEEP=1` keeps every log and working file.

A label that already holds a batch is refused, unless you add `RETRY=1`: then only the books without a finished result run again, and `summary.md` is rewritten for the whole batch. Give the same folders or list as the first time. When books fail, the summary prints the exact command to use. It repeats the batch's `MODEL=`, `FROM=` and `MAX_TOKENS=`, doubles `MAX_TOKENS` if a reply was cut off, and adds `JOBS=1` (with a note to wait a few minutes) if the model was rate-limited:

```bash
# a reply was cut off
RETRY=1 MAX_TOKENS=32000 AUTO=1 bash batch_api.sh g2-run2 ../samples/group2
# a non-default model was rate-limited (429): wait, then one book at a time, same model
RETRY=1 JOBS=1 MODEL=openai/gpt-6.1-sol AUTO=1 bash batch_api.sh group1SOL ../samples/group1
```

Copy the printed command rather than retyping it: a `RETRY=1` without the original `MODEL=` would finish the books with the default model.

The summary's API cost includes calls whose reply was cut off (they are paid for). Credit left is OpenRouter's balance, or, when OpenRouter hasn't caught up with the batch's calls yet, the credit before the batch minus what the batch spent.

`FROM=<earlier-label>` re-runs a batch from the Claude replies saved in earlier `record.json` files: no API calls and no cost. Use it to apply pipeline fixes to past decisions. It looks for each book in the batch `runs/batches/<label>/<name>/` first, then in the single run `runs/<name>/<label>/`, so the book folder names must match the earlier run.

In a book list, relative paths count from the list file's folder. Short names must be unique across the batch.

## What a run leaves in `PDFREM/runs/<name>/<run-label>/`

| File | For | What it is |
|---|---|---|
| `<original>_remediated.pdf` | everyone | The result. Run PAC on this (named by `OUT` or the book list if you set one) |
| `review.md` | the human reviewer | Automated checks; every alt text the AI wrote (before and after) and the ones it left alone; heading levels and spoken heading text; what was hidden as decoration; reading-order moves; what the AI and the executor deferred; anything not applied |
| `record.json` | the archive | Everything vital in one file: source fingerprint, model, prompt version, tokens, cost, the full work order, what was applied, rejected and deferred, the verification results, and Claude's raw reply. `apply.py` accepts it in place of a work order, to re-apply a run |
| `han_review.csv` | a Japanese / Chinese reader | Only when the book has Han-only CJK runs: one row per run, with a blank decision column |

Nothing else is kept. The working files (digest, figure crops, raw request and response, logs) are deleted once the report is written, because they are rebuilt from the original in under a minute and the crops are copies of book pages. A run that fails partway keeps its working files, so the failure can be diagnosed.

## Step by step (what `run_api.sh` does)

```bash
S=../samples/cadaverous/<file>.pdf
R=../runs/cadaverous/api-run1;  A=$R/_audit
python3 audit.py  $S $A                                   # no model, ~30 s
python3 decide.py $A $R --dry-run                         # cost estimate + available credit; sends nothing
python3 decide.py $A $R                                   # the API call
O=$R/<file>_remediated.pdf
python3 apply.py  $S $R/workorder.json $O                 # no model, ~80 s
python3 verify.py $S $O                                   # no model, ~3 min
python3 report.py $R $A                                   # review.md, record.json, han_review.csv; add --keep to keep working files
```

If `decide.py` fails after the API call, the raw reply is in `$R/reply.txt` and OpenRouter's full response in `$R/response.json`. A reply that was cut off can't be used; rerun `run_api.sh` with the same label and a higher `MAX_TOKENS` (see above). For errors from OpenRouter itself, see "When the model call fails".

## When the model call fails

`decide.py` prints OpenRouter's own message and code, and says whether anything was charged. The error is also saved in `run.json` (and the full reply in `response.json` or `error.txt`), so a batch summary shows the reason in the book's row. OpenRouter sometimes sends an error inside a normal-looking reply (for example a 429); it is caught the same way.

| What you see | What it means | What to do |
|---|---|---|
| `OpenRouter error 429 … rate-limited … Nothing was charged` | The model's maker is throttling requests, often when a batch sends several at once | Wait a few minutes. Single run: the same command again. Batch: `RETRY=1 JOBS=1 MODEL=<same model> AUTO=1 bash batch_api.sh <label> <same folders>` (the summary prints it) |
| `reply was cut off at 16000 output tokens` | The reply ran out of output tokens; it was paid for | The same command with `MAX_TOKENS=32000` (batches: add `RETRY=1`). The earlier cost stays in the record |
| `rejected the temperature setting … Add "<model>" … to OMIT_TEMPERATURE` | The model refuses a temperature value; nothing was charged or retried | Add the model id (or its prefix) to `OMIT_TEMPERATURE` in `decide.py`, then run again |
| `no provider of <model> accepts our "don't keep or train on the data" setting` | No provider will serve the model under `data_collection: deny`; nothing was sent | Choose another model |
| `OpenRouter error 402` | Not enough credit for the request | Add credit, or lower `MAX_TOKENS` |
| `OpenRouter error 413` | The request was too large | Report it: the figure images are already shrunk to fit |
| `refusing: …` (before sending) | The model check failed: unknown id, no image input, output limit under `MAX_TOKENS`, or the request too large for its context window | Choose another model or adjust `MAX_TOKENS`; nothing was sent |
| `OpenRouter error <other code>: <message>` | Any other error from OpenRouter or the provider | Read the message; usually run again later |

A failed call that OpenRouter did charge for is logged with its cost and counted in the record and the summary; a rerun with the same label makes a new call.

## Files

| File | Role |
|---|---|
| `audit.py` | Original → digest (styles, listed elements, figures with crops, page map, reading order, front matter). No model |
| `prompts/workorder_v4.md` | The system prompt: rules and the work-order format. Its hash is recorded in every run |
| `decide.py` | The API call. Estimates cost, checks available credit, sends the digest and crops, parses and validates the reply. `--dry-run`, `--response-file`, `--check-key`, `--credit` (credit left), `--max-images` (default 100), `--max-tokens` (default 16,000, set on the `ap.add_argument('--max-tokens' …)` line; the model's reasoning counts against it) |
| `apply.py` | The executor. Original + work order → `<original>_remediated.pdf`. pikepdf only; checks each target first and rejects what doesn't fit |
| `verify.py` | Checks the result against the original |
| `report.py` | Writes `review.md`, `record.json` and `han_review.csv`, then removes the working files |
| `plumb_fix.py` | Fix for pdfplumber's nested marked-content bug (required) |
| `run_api.sh` | All of the above in one command |
| `batch_api.sh` | Several books in parallel, with a batch cost gate and a summary (needs `AUTO=1`) |

**Figure images** are sent as JPEG (long side 800 px). If a book's images together pass 20 MB they are made smaller step by step, because OpenRouter refuses requests with more than 30 MB of images (HTTP 413). At most 100 images go in one request (Anthropic's limit); in a book with more figures, the alt text for the rest goes to a person, listed in the review under the AI's deferrals. What was sent is recorded in `record.json` under `run.images`.

## Choosing the model

The default is one line near the top of `decide.py`: `DEFAULT_MODEL = 'anthropic/claude-sonnet-5.5'`. Change it to any id from https://openrouter.ai/models. For one run or one batch, put `MODEL=` in front instead:

```bash
# default model (DEFAULT_MODEL in decide.py), with the y/N question
bash run_api.sh ../samples/group1/clans.pdf clans api-run3
# another model for one book, no question
MODEL=openai/gpt-5 AUTO=1 bash run_api.sh ../samples/group1/clans.pdf clans gpt-run1
# the cost estimate only, to see what a model would cost (free)
MODEL=google/gemini-3.8-flash ESTIMATE=1 bash run_api.sh ../samples/group1/clans.pdf clans gem-run1
# the same group with two models, to compare
AUTO=1 bash batch_api.sh g1-sonnet ../samples/group1
MODEL=anthropic/claude-opus-5.5 AUTO=1 bash batch_api.sh g1-opus ../samples/group1
# a bigger output limit as well
MODEL=openai/gpt-5 MAX_TOKENS=32000 AUTO=1 bash batch_api.sh g3-gpt ../samples/group3
# finish the books a batch couldn't (keep the same MODEL as the first try; the summary prints this command)
RETRY=1 MODEL=openai/gpt-5 AUTO=1 bash batch_api.sh g3-gpt ../samples/group3
# the model was rate-limited (429): wait a few minutes, then one book at a time
RETRY=1 JOBS=1 MODEL=openai/gpt-6.1-sol AUTO=1 bash batch_api.sh group1SOL ../samples/group1
# re-apply saved replies for free; each keeps the model that wrote it, so no MODEL= needed
FROM=g1-opus AUTO=1 bash batch_api.sh g1-opus-rerun ../samples/group1
```

Ids that exist on OpenRouter and take images: `anthropic/claude-sonnet-5.5`, `anthropic/claude-opus-5.5`, `google/gemini-3.8-flash`, `openai/gpt-5`.

Before anything is sent, `decide.py` looks the model up on OpenRouter and refuses it if:

- the id is not on OpenRouter
- it cannot take images (the figure crops are part of every request)
- its output limit is under `MAX_TOKENS`
- the request (input estimate + `MAX_TOKENS`) does not fit its context window

**Costs with other models.** The cost estimate uses Claude's token math (calibrated on Sonnet bills), so for any non-Claude model it is marked approximate. The $2 per-book cap, the batch cap and the credit check are not applied to it; the estimate is printed and the request is sent. If your credit is too low, OpenRouter refuses the request (HTTP 402) and nothing is charged. The OpenRouter bill, shown in the review and the summary, is the real cost. With `AUTO=1`, the line printed before sending says which case applies:

```
AUTO=1: sending without asking (decide.py still refuses a Claude estimate over the $2 cap or your credit)
AUTO=1: sending without asking. The $2 cap applies to Claude models only: the openai/gpt-5 estimate is approximate and not capped; the OpenRouter bill is the real cost
```

**Where the model shows:** `review.md` (top line), `record.json` (`run.model`), the batch header and the top of `summary.md`, with the batch start time and the prompt file. `FROM=` and `REPLY=` re-runs keep the model that wrote the saved reply.

If no provider of a model accepts the "don't keep or train on the data" setting, OpenRouter refuses the request before anything is charged, and `decide.py` says so.

## Temperature

One line near the top of `decide.py` sets it for every run: `TEMPERATURE = 0`. There is no command-line override; changing the number changes every run that sends a temperature.

No temperature is sent when the model's maker says to leave it at the default, or the model rejects other values. That is the case when:

- the model id starts with an entry in `OMIT_TEMPERATURE` (in `decide.py`): Opus 4.7 and later, OpenAI reasoning models (`openai/o1`, `o3`, `o4`, `gpt-5`), and `google/gemini-3` (every Gemini 3 model). Add a line there for any other model
- or OpenRouter lists the model as not accepting a temperature setting

Sonnet matches neither, so it gets `0`.

Every new run writes `run.temperature` in `record.json`: the number sent, or `"omitted: …"` with the reason. `FROM=` and `REPLY=` re-runs send nothing, so they keep the original run's value, and add none where the original had none. Records written before this setting existed are not changed (those runs were sent with temperature 0).

If a model that is not on the list, and not flagged by OpenRouter, still rejects the setting, the run stops: OpenRouter charges nothing for the refused request, nothing is retried, and the message says to add the model to `OMIT_TEMPERATURE`.

**Settings recorded in each run:** temperature (`TEMPERATURE`, or omitted as above), `data_collection: deny` (OpenRouter routes only to providers that don't keep or train on the data), at most 16,000 output tokens unless `MAX_TOKENS` says otherwise, $2 spending cap per book (Claude models).

## What the executor always does by itself

These are mechanical, so they never wait for the model:

- makes sure there is exactly one Document root (Auto-Tag output often has none; some exports have two)
- sets the "tagged" flag and shows the title in the window
- ties every link annotation to its text and gives it a description, creating Link tags where the tagger left none
- removes references to annotations that sit on no page
- rebuilds the tag-tree index (ParentTree) from the tree where entries are missing or wrong
- gives every Note tag a unique ID (and lists it in the ID tree). A Note tag is removed only when it is proven empty: nothing under it holds content or an annotation, it carries no alt, ActualText or ID, and nothing in the file but its parent refers to it. Turning note paragraphs into Notes stays the model's decision
- defers Han-only CJK runs and links on text missing from the tag tree to a person
- reports any PDF/UA claim the source already makes; it never adds one

## What the model decides

Title and language; heading levels (by style, or element by element when the tagger's headings are generic); merges and spoken heading text; alt text and decorative figures (including full-page scan images); running heads and page numbers to hide, including ones marked but outside the tag tree; false lists and tables to flatten into paragraphs; lists, contents, notes and captions by style; one reading-order move. Real tables, text missing from the tag tree, and OCR errors go to a person. (Notes: the model decides which paragraph styles become Notes; IDs are always handled by the executor.)

## Work order rules

- Elements are referenced by object number in the **original** file (`"18592 0"`). That works because `apply.py` changes everything in memory and saves once.
- `source.sha256` must match the input file, or `apply.py` refuses to run.
- Each operation checks its target first. One that doesn't fit is **rejected and logged**, never half-applied.
- Targets are whitelisted. Work-order text is only ever data: never executed, never written into page content.

Background: before any API spending, a replay test confirmed that `apply.py` reproduces the Cowork session's *Cadaverous* result exactly from a written-down work order.
