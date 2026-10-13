# PDF Accessibility Remediation Pipeline

[![CI](https://github.com/pdf-accessibility-remediation/pdf-accessibility-remediation/actions/workflows/ci.yml/badge.svg)](https://github.com/pdf-accessibility-remediation/pdf-accessibility-remediation/actions/workflows/ci.yml)

Claude reads a compact summary of a tagged PDF and returns a **work order**: a JSON file of decisions (heading levels, alt text, what to artifact, language, reading-order fixes). The code carries those decisions out, checks the result, writes a review for a person, and never changes the original. The only paid step is the model call in `decide.py`.

```
original.pdf ─► intake.py ─► audit.py ─► decide.py (model via OpenRouter) ─► apply.py ─► verify.py ─► report.py
                untagged only:  digest     work order                        original_remediated.pdf review.md + record.json
                OCR + auto-tag  + veraPDF (before)                                       + veraPDF (after)
```

An **untagged** PDF first goes through `intake.py` (local tools, no model, no cost): OCR where pages have no text, then auto-tagging, with checks after each step (see "Intake: untagged PDFs"). A tagged PDF skips it.

The same validator, veraPDF's WCAG 2.2 machine profile (which includes the PDF/UA-1 rules), runs on the original during the audit and on the result during verify. `review.md` sorts every failed rule into fixed, still failing, or **newly failing** (something the run broke, flagged as a CHECK). See [Verification with veraPDF](#verification-with-verapdf).

## Automated checks

GitHub Actions runs the following checks:

- **CI** — Compiles Python sources, validates shell-script syntax, installs dependencies, and runs `pip-audit`.
- **PDF validation** — Installs Java 17 and veraPDF, then runs `audit.py` (with veraPDF on the original) against a sample PDF when pipeline or sample files change.
- **Dependency review** — Reviews dependency changes in pull requests and fails on high-severity vulnerabilities.
- **CodeQL** — Performs static security analysis of the Python code on pushes, pull requests, and weekly.

These workflows do not run `run_api.sh` or make OpenRouter API calls automatically.

## Setup (once)

1. **Python packages:** First cd to pipeline, then create and activate the virtual environment with `python3 -m venv .venv && source .venv/bin/activate`. Then `pip install -r requirements.txt` (pdfplumber must be 0.11.9: `plumb_fix.py` patches its internals). Every run first checks that the required libraries import in the Python that runs the pipeline: if one is missing, it stops before any audit or paid call and prints the install command. Each `record.json` (`environment`) and the top of each `review.md` record the Python and library versions used.
2. **For untagged PDFs (intake), once:** `brew install ocrmypdf tesseract-lang` (OCRmyPDF 17 brings Tesseract and Ghostscript; `tesseract-lang` adds the language packs, including `chi_sim`, `chi_tra`, `jpn`, `kor`) and Java 11 or later for auto-tagging (for example `brew install --cask temurin`; any Java 11+ install works, e.g. Homebrew's `openjdk@21`). OCRmyPDF is installed by Homebrew, not pip, because its pip package needs newer pikepdf and pdfminer versions than this pipeline pins. `opendataloader-pdf` (the auto-tagger) comes with `requirements.txt`. These are checked only when a book needs them: tagged books, teammates who only run tagged books and the GitHub checks need none of them.
3. **Key:** put `OPENROUTER_API_KEY=…` in a `.env` file in `pipeline/` or any folder above it (e.g. the repo root). Keep `.env` in `.gitignore`.
4. **Check the key (free):** `python3 decide.py --check-key`.
5. **veraPDF** (WCAG and PDF/UA checks, see "Verification with veraPDF"): needs Java 17 (`sudo apt install openjdk-17-jre-headless`, or any Java 17 runtime on `PATH`; the auto-tagger's Java works too if it is 17 or later). Then, from `pipeline/`, `bash verapdf/install.sh` installs veraPDF 1.30.3 in `~/.local/opt/verapdf` and prints the line to add to your shell profile: `export VERAPDF=~/.local/opt/verapdf/verapdf`. pip can't install it: it is a Java program, not a Python package. `python3 vera.py --check` prints the version. Every run checks it before any paid call and stops if it is missing; `VERAPDF=off` runs without it, and `review.md` then says its rows were not run.
6. **Prompt:** `workorder_v8.md` goes in `pipeline/prompts/` or in `prompts/` beside `pipeline/`. Older versions are kept only as a record.
7. **PDFs:** originals go in `samples/<name>/` and are never written to. Outputs go in `runs/<name>/<run-label>/` (single runs) or `runs/batches/<label>/<name>/` (batches) beside `pipeline/` (set `RUNS_DIR` to put them elsewhere). Keep both out of git: the books are in copyright.

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
| `MAX_TOKENS=64000` | Output limit for the model's reply, reasoning included (default 48,000; Sonnet 5.5 allows up to 128,000 on OpenRouter). Raise it when a reply is cut off |
| `RUNS_DIR=/path` | Writes runs somewhere other than `PDFREM/runs/` |
| `VERAPDF=off` | Runs without veraPDF; review.md says its rows were not run. `VERAPDF=/path/to/verapdf` uses a launcher not on `PATH`; `VERAPDF_TIMEOUT` (seconds, default 900) limits each veraPDF run |
| `FORCE_OCR=1` | Intake: when the text-layer test says a book's text layer is unusable, OCR every page anyway (page images + new invisible OCR text; the old text is replaced). Without it such a book stops, flagged for a person. **Unverified:** in testing, force OCR stopped at its own after-OCR check on every page (see "Intake") |
| `OCR_LANG=jpn+eng` | Intake: Tesseract languages. By default: `eng`, plus `jpn` when kana are found and `kor` for hangul; Chinese characters with no kana are never guessed as Chinese or Japanese, so set this for them (e.g. `chi_tra+eng`) |
| `OCR=off` | Intake: no OCR; image-only pages are listed as having no text |
| `INTAKE=off` | No intake step at all (an untagged book then goes to the audit as it is) |
| `JOBS=1` | Batches only: books run at the same time (default 3). Use 1 after a rate limit (see "When the model call fails") |

A run label that already holds a finished run is refused, so earlier results are never overwritten.

**If a run stops partway, rerun the same command** (same label). It picks up where it stopped:

- the audit is reused
- a reply that was **cut off** at the output limit is logged with its cost (it ends up in `record.json` under `earlier_attempts`, and in the cost line of `review.md`), then a new call is made. Add `MAX_TOKENS=32000` so it doesn't happen again
- a reply that was complete, where a later step failed, is reused at no cost
- a reply that was complete but could not be read as a work order is read again first, at no cost (useful after a pipeline fix). Only if it still can't be read is its cost logged and a new call made

The output limit: change the default once in `decide.py` (the line `ap.add_argument('--max-tokens', type=int, default=48000)`), or per run with `MAX_TOKENS=`. Doubling it to 32,000 raises the worst-case estimate by about $0.16 per book with Sonnet; you only pay for what is used.

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

1. **Estimate (no model).** It runs the intake step for untagged books (OCR and auto-tagging; free) and audits every book and adds up the worst-case cost. It stops before any API call if the Claude total is over `BATCH_MAX_USD` (default $5) or over your credit. The audits are kept, so a rerun with a higher cap reuses them. Only Claude models count against the cap and the credit check (see "Choosing the model"), so the total line depends on the model:

   ```
   # Claude batch
     total worst case             $0.75   batch cap $5.00   credit $11.46
   # non-Claude batch: one approximate line, nothing capped
     worst case                   about $0.75, approximate, not capped (the OpenRouter bill is the real cost)   credit $11.46
   # mixed (e.g. a RETRY with another model): the Claude line is the capped portion
     worst case, capped (Claude)  $0.50   batch cap $5.00   credit $11.46
     worst case, non-Claude       about $0.25, approximate, not capped (the OpenRouter bill is the real cost)
   ```
2. **Run.** It runs every book through the full pipeline, `JOBS` at a time (default 3; each book needs about 0.5–1.5 GB of memory). A failed book doesn't stop the others. A book **flagged at intake** (e.g. its text layer failed the OCR comparison and `FORCE_OCR=1` was not set, or it needs a password) is not sent to the model: summary.md shows "flagged at intake" with the reason, and `<book>/_intake/intake.json` has the measurements.
3. **Summary.** It prints the batch start time, model and prompt file, then a table of book, status, intake (what intake did: e.g. "OCR 6 pages · auto-tagged", or "none (already tagged)"), pages, API cost, cost per page, time, checks flagged, veraPDF's failing PDF/UA rules before → after ("new" marks rules the result fails and the original passed) and result, then the total cost, the cost per page (checklist 11.5) and the credit you have left, and saves it as `summary.md`. A failed book's status says why: `reply cut off at 48,000 tokens`, `OpenRouter 429, model rate-limited (nothing charged)`, or OpenRouter's error code and message. Its log is kept beside the summary (`<name>.log`) only if that book failed; `KEEP=1` keeps every log and working file. `summary.md` is written whichever way the batch is started (no folder, one folder, several folders or a book list), and also when a batch stops early or is interrupted (books that did not run show as "not finished"); the terminal then says where it stopped.

A label that already holds a batch is refused, unless you add `RETRY=1`: then only the books without a finished result run again, and `summary.md` is rewritten for the whole batch. If every book has already finished, nothing runs and `summary.md` is simply rewritten (a free way to regenerate a missing summary). Give the same folders or list as the first time. When books fail, the summary prints the exact command to use. It repeats the batch's `MODEL=`, `FROM=` and `MAX_TOKENS=`, doubles `MAX_TOKENS` if a reply was cut off, and adds `JOBS=1` (with a note to wait a few minutes) if the model was rate-limited:

```bash
# a reply was cut off
RETRY=1 MAX_TOKENS=96000 AUTO=1 bash batch_api.sh g2-run2 ../samples/group2
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
| `<original>_remediated.pdf` | everyone | The result. Run PAC 2026 on this (named by `OUT` or the book list if you set one) |
| `review.md` | the human reviewer | Automated checks (including exactly one H1, bookmarks present, every decision applied, nothing deferred: a green row is evidence, not proof); every alt text the AI wrote (before and after) and the ones it left alone; heading levels and spoken heading text; what was hidden as decoration; reading-order moves; what the AI and the executor deferred; anything not applied |
| `record.json` | the archive | Everything vital in one file: source fingerprint, model, prompt version, tokens, cost, the full work order, what was applied, rejected and deferred, the verification results, and Claude's raw reply. `apply.py` accepts it in place of a work order, to re-apply a run |
| `han_review.csv` | a Japanese / Chinese reader | Only when the book has Han-only CJK runs: one row per run, with a blank decision column |
| `_intake/intake.json` | the archive | Untagged originals only: what intake measured and did (page triage, text-layer test scores, OCR language, OCR pages, tool versions, every check). Also in `record.json` under `intake` |
| `_intake/intake.md` | a person | Untagged originals only: the intake record in plain words (status, pages OCR'd, picture pages, CHECKs and notes with their pages, the OCR review verdict). Written for every outcome, also by `intake.py <pdf> <dir>` on its own and by `--plan-only` |
| `_intake/intake.pdf` | the pipeline | Untagged originals only, when intake changed anything: the OCR'd and auto-tagged copy the rest of the run worked on. Kept so `FROM=` reruns apply saved replies to the very same file |

Nothing else is kept. The working files (digest, figure crops, raw request and response, logs) are deleted once the report is written, because they are rebuilt from the original in under a minute and the crops are copies of book pages. A run that fails partway keeps its working files, so the failure can be diagnosed.

## Step by step (what `run_api.sh` does)

```bash
S=../samples/cadaverous/<file>.pdf
R=../runs/cadaverous/api-run1;  A=$R/_audit
python3 intake.py $S $R/_intake                           # untagged only: OCR + auto-tag; then S=$R/_intake/intake.pdf
python3 audit.py  $S $A                                   # no model, ~30 s; also veraPDF on the original → $A/verapdf.json
python3 decide.py $A $R --dry-run                         # cost estimate + available credit; sends nothing
python3 decide.py $A $R                                   # the API call
O=$R/<file>_remediated.pdf
python3 apply.py  $S $R/workorder.json $O                 # no model, ~80 s
python3 verify.py $S $O                                   # no model, ~3 min; veraPDF on the result runs alongside
python3 report.py $R $A                                   # review.md, record.json, han_review.csv; add --keep to keep working files
```

If `decide.py` fails after the API call, the raw reply is in `$R/reply.txt` and OpenRouter's full response in `$R/response.json`. A reply that was cut off can't be used; rerun `run_api.sh` with the same label and a higher `MAX_TOKENS` (see above). For errors from OpenRouter itself, see "When the model call fails".

## Verification with veraPDF

The goal is WCAG 2.2 AA. [veraPDF](https://github.com/veraPDF) checks the original (in `audit.py`) and the result (in `verify.py`) with its **WCAG 2.2 machine** profile, pinned in `pipeline/verapdf/WCAG-2-2-Machine.xml` (from veraPDF-validation-profiles branch `rel/1.30`). That profile holds every machine-checkable PDF/UA-1 rule and a few WCAG-only ones (contrast, small text, link descriptions, redundant tags). veraPDF's CLI has no flavour for it, so it is passed with `-p`.

Not every PDF/UA rule matters for WCAG. `pipeline/verapdf/rules.json` sorts every rule in the profile:

- **wcag**: a failure fails a success criterion (listed per rule). Counted in review.md.
- **ua_only**: a PDF/UA requirement with no success criterion behind it (XMP metadata and dc:title, Note IDs, font program embedding, widths and encodings, optional content, embedded files, XFA, print-production annotations). Listed apart and not counted.

A rule veraPDF reports that is not in `rules.json` counts as WCAG and is named as unclassified in review.md, so someone adds it. After updating the profile, re-check that every rule is listed.

`vera.py` keeps one entry per failed rule, not one per failure (a scanned book can fail 70,000 checks): the rule, what it checks, how many checks failed, its pages, five examples with their object and PDF page, and who can fix it:

| Who fixes | Rules | How it is used |
|---|---|---|
| the pipeline | flags, `DisplayDocTitle`, links tied and described, tab order, note IDs, the OCR layer's undefined glyphs, role-map loops (7.1-6), standard tags remapped (7.1-7), malformed `/Lang` spelling (7.2-29) | not sent to the model: the executor fixes these whatever the work order says, and review.md says how many it changed |
| the AI | figure alt text, heading levels, natural language, untagged content, role mapping (including styles with no mapping), document title, table headers (7.5-x), broken table, list and contents structure | sent to the model in the digest (`pdfua_check`) as rule, count, example objects, the work-order `key` that fixes it and `objs` (up to 20 tags it failed on) |
| a person | fonts, Formula alt, Figure bounding boxes, the PDF/UA claim | not sent; listed in `review.md` as known gaps |

Which rules belong to whom, and which work-order key fixes each AI rule, is set in `pipeline/vera.py` (`EXECUTOR`, `KEY`, `PERSON`). The AI must address every rule it is sent with its key, or defer it naming the rule (prompt v8, step 9).

**Targeting from the original's results.** The audit uses veraPDF's findings to make the flagged tags reachable: a Figure with no alt and no image of its own (a vector logo or drawing) gets a crop of its whole page (`image_is_whole_page`), so the model can see it; a table whose cells veraPDF flags is marked with `pdfua_rules` (and kept even past the 100-table cap).

**Executor fixes for veraPDF rules** run on every book (after the work order, before the index rebuild) and change no page's look or text. Each records what it changed under `rule_fixes` in the apply log, shown in review.md's "Who fixes" column:

| Rule | Fix |
|---|---|
| 7.1-6 | A RoleMap chain that loops is cut where it closes (that style → P) and listed for a person |
| 7.1-7 | A standard tag remapped in the RoleMap (sands: `Caption → P`): its elements are retyped to what the RoleMap made them, and the entry removed |
| 7.2-29 | `/Lang` spelling tidied (`en_US` → `en-US`, case, spaces; `langtag.py`); an empty `/Lang` on a tag removed; anything else listed, never guessed |
| 7.5-1/2 | A header cell (TH) with no direction gets one where the table makes it plain: a row of only TH → Column, a row whose only TH is its first cell → Row; others are listed |

The work order's `tables` key (`op_tables`) marks the header rows and columns the AI names in a real table as TH with their Scope; spans that cross the header edge are rejected for a person. `rolemap` may add a mapping for a style the source never mapped (7.1-5).

veraPDF runs once per step, in the background while the step's own checks run. The audit's run is the "before" (`verapdf.json`, plus its `pdfua_check` view in the digest); it is printed with the audit, so a file that already passes (or fails thousands of checks) shows up before anything is spent. Verify's run is the "after". review.md gets two rows (no WCAG failures after; no rule newly failing or failing more often) and a "veraPDF" section with each failed rule's before and after counts, who fixes it, its status (newly failing, failing more often, still failing, fixed) and pages. `record.json` keeps both summaries under `verapdf`; `summary.md` shows each book's failing rules before → after.

**WCAG checks veraPDF does not make** are in `verify.py` (`wcag` in `record.json`), each a row in review.md and listed under "WCAG checks veraPDF does not make". They find things to look at, not proven failures:

| SC | Check |
|---|---|
| 1.1.1 | Alt text that looks like a file name, has no letters or digits, or is the same on 3+ figures |
| 1.3.1 | A table with content and no header cell (TH) |
| 1.3.2 | Pages where the tagged text, in tag-tree order, jumps back up the same column 2+ times (notes, figures and captions skipped) |
| 2.4.2 | A title that looks like a file name or placeholder |
| 2.4.4 | Link text like "click here" or "more" |
| 2.4.6 | Headings with no text, over 200 characters, or the same twice in a row |

The executor sets `/Tabs /S` on every page with annotations (2.4.3), so tab order follows the tag tree.

When an audit is reused and has no `verapdf.json` yet, `run_api.sh` runs veraPDF on the file the audit was made from (the intake result, if intake ran), and `decide.py` builds `pdfua_check` from it.

**PAC 2026** ([pac.pdf-accessibility.org](https://pac.pdf-accessibility.org/en), Windows, no command line) is the final manual check. review.md ends with what to run and the criteria no automated check covers (alt-text accuracy, meaningful order, colour, contrast over images, images of text, descriptive headings, language of parts). A PAC failure not listed in review.md is a gap in the automated checks: open an issue.

## When the model call fails

`decide.py` prints OpenRouter's own message and code, and says whether anything was charged. The error is also saved in `run.json` (and the full reply in `response.json` or `error.txt`), so a batch summary shows the reason in the book's row. OpenRouter sometimes sends an error inside a normal-looking reply (for example a 429); it is caught the same way.

| What you see | What it means | What to do |
|---|---|---|
| `OpenRouter error 429 … rate-limited … Nothing was charged` | The model's maker is throttling requests, often when a batch sends several at once | Wait a few minutes. Single run: the same command again. Batch: `RETRY=1 JOBS=1 MODEL=<same model> AUTO=1 bash batch_api.sh <label> <same folders>` (the summary prints it) |
| `reply was cut off at 48000 output tokens` | The reply ran out of output tokens; it was paid for | The same command with `MAX_TOKENS=96000` (batches: add `RETRY=1`). The earlier cost stays in the record |
| `rejected the temperature setting … Add "<model>" … to OMIT_TEMPERATURE` | The model refuses a temperature value; nothing was charged or retried | Add the model id (or its prefix) to `OMIT_TEMPERATURE` in `decide.py`, then run again |
| `no provider of <model> accepts our "don't keep or train on the data" setting` | No provider will serve the model under `data_collection: deny`; nothing was sent | Choose another model |
| `OpenRouter error 402` | Not enough credit for the request | Add credit, or lower `MAX_TOKENS` |
| `OpenRouter error 413` | The request was too large | Report it: the figure images are already shrunk to fit |
| `the reply held 2 JSON work orders and the last one … could not be read` / `could not parse a JSON work order` | The reply was paid for but holds no usable work order | Rerun the same command (batches: `RETRY=1`): the saved reply is read again first, then a new call is made if it still can't be used |
| `refusing: …` (before sending) | The model check failed: unknown id, no image input, output limit under `MAX_TOKENS`, or the request too large for its context window | Choose another model or adjust `MAX_TOKENS`; nothing was sent |
| `OpenRouter error <other code>: <message>` | Any other error from OpenRouter or the provider | Read the message; usually run again later |

A failed call that OpenRouter did charge for is logged with its cost and counted in the record and the summary; a rerun with the same label makes a new call.

## Files

| File | Role |
|---|---|
| `intake.py` | Untagged originals only: page triage, text-layer test, OCR (OCRmyPDF + Tesseract) and auto-tagging (OpenDataLoader), with checks after each step. Local, no model. `--plan-only` shows what it would do without changing anything |
| `gaptext.py` | Text as a reader hears it: a space where the PDF has a gap but no space character (over 0.10 em and 2.5 × the line's typical gap; not where another tag's glyph fills the gap). Used for the digest and review.md, and for matching text rules; never changes the PDF |
| `listrule.py` | The one-item list rule, shared by `audit.py` (marks the lists in the digest) and `apply.py` (applies it) |
| `review_ocr.py` | Records a person's verdict on a book's OCR text (checklist rule 2): `python3 review_ocr.py <run>/<book> --verdict approved\|"not approved" --reviewer NAME --reason TEXT [--pages 381-386] [--date YYYY-MM-DD]`. Writes `_intake/intake.json`, `record.json` and the review.md row; the row is OK only on "approved"; FROM= reruns carry the verdict |
| `scan.py` | Fast read-only checks on a folder of PDFs (no OCR, no model): tagged or not, producer, page triage, private-use characters, text outside the visible page area and word breaks, per book (`books/*.json`) and in `summary.md`: `python3 scan.py <folder> <out_dir>` |
| `audit.py` | Original → digest (styles, listed elements, figures with crops, page map, reading order, front matter; in scanned books, suspect OCR words on word sheets; veraPDF's PDF/UA failures). No model. Positions are measured in the visible page area (CropBox): running-head bands (top 70 pt, bottom 60 pt), figure sizes and crops; a figure drawn only outside it gets no crop and is marked `outside_visible_area` |
| `prompts/workorder_v8.md` | The system prompt: rules and the work-order format. Its hash is recorded in every run. v8 adds `tables` (header rows and columns of a real table), lets `rolemap` map a style the source never mapped, tells the model the work-order key and tags for each `pdfua_check` rule, and requires every such rule to be fixed or deferred by name (step 9). v7 changes the ActualText wording (spoken text only where printed glyphs read wrongly; equal to the print apart from spacing, case and line-end hyphens; merges join a label and its title) and adds `ocr_words` (the printed spelling of misread OCR words in scanned books, read from word sheets) and `pdfua_check` (the veraPDF failures the model can act on). v7 and older are kept as a record |
| `decide.py` | The API call. Estimates cost, checks available credit, sends the digest and crops, parses and validates the reply. `--dry-run`, `--response-file`, `--check-key`, `--credit` (credit left), `--max-images` (default 100), `--max-tokens` (default 48,000, or 16,000 plus 45 per OCR word form sent when that is more; the model's reasoning counts against it) |
| `apply.py` | The executor. Original + work order → `<original>_remediated.pdf`. pikepdf only; checks each target first and rejects what doesn't fit |
| `verify.py` | Checks the result against the original, adds the WCAG checks veraPDF does not make, and runs veraPDF on the result |
| `vera.py` | Runs veraPDF with the pinned WCAG 2.2 machine profile (which includes the PDF/UA-1 rules) and condenses its report to one entry per failed rule: WCAG or PDF/UA-only, and who can fix it (and, for the AI, the work-order key). `--check`; or `vera.py FILE.pdf OUT.json` on its own |
| `langtag.py` | Checks and tidies a BCP 47 language tag; used by `apply.py` (`/Lang` spelling) and `decide.py` (the work order's `document.lang`) |
| `verapdf/` | `WCAG-2-2-Machine.xml` (the pinned profile), `rules.json` (each rule's WCAG success criteria, or why it is PDF/UA-only), `install.sh` |
| `report.py` | Writes `review.md`, `record.json` and `han_review.csv`, then removes the working files |
| `plumb_fix.py` | Fix for pdfplumber's nested marked-content bug (required) |
| `run_api.sh` | All of the above in one command |
| `batch_api.sh` | Several books in parallel, with a batch cost gate and a summary (needs `AUTO=1`) |

**Figure images** are sent as JPEG (long side 800 px). If a book's images together pass 20 MB they are made smaller step by step, because OpenRouter refuses requests with more than 30 MB of images (HTTP 413). At most 100 images go in one request (Anthropic's limit); in a book with more figures, the alt text for the rest goes to a person, listed in the review under the AI's deferrals. What was sent is recorded in `record.json` under `run.images`.

## OCR words in scanned books

OCR engines read letters they don't know as look-alikes. In romanized Pali, Sanskrit and Japanese this is constant: ā and ū become "ii" (*nibbāna* → `nibbiina`, *rūpa* → `riipa`), ṇḍ becomes `t;l¢`, ü becomes "ii" (`Miiller`). A screen reader then says the wrong word, and copying gives it.

In a scanned book (the producer says OCR, or most pages are full-page images), `audit.py` lists every distinct word form that looks misread (`ii` inside a word, or `;` `¢` `£` between letters), most frequent first, up to 700. Each form is cropped once from the page image and placed on numbered **word sheets** (PNG, sent at full size: a macron is a few pixels). The model reads each crop and returns `ocr_words`: the id and the word exactly as printed, for the forms whose letters differ. Forms the OCR read correctly (`Hawaii`) are left out.

`decide.py` drops a reading that isn't one word, is the same as the OCR text, or is too different from it to be a misreading: after removing diacritics, the edits from the OCR text to the reading may not pass a third of the reading's length, where changing or dropping a character OCR produces from unknown letters (`i l 1 J ; : t f z` …) counts a quarter. On *Buddhist* this kept all 593 readings and let through 12 of 570 deliberately mismatched pairs, so the review's table is still checked by a person. `apply.py` then wraps every text operator that shows the form in `/Span <</ActualText (…)>> BDC … EMC`. Screen readers speak the printed spelling and copying gives it; the OCR text, its fonts and the page are unchanged, so `verify.py`'s pixel and text checks still hold (a text search still finds the OCR spelling). `review.md` lists every respelled form with its first pages for a person to check against the scan.

It costs about 1,400 input tokens per sheet (31 words) and about 37 output tokens per word, reasoning included (about 11 of them are the reading itself; the output limit allows 45). *Buddhist* (648 forms, 21 sheets) cost $0.51 in all, against $0.19–0.24 for books with no OCR words.

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

**Settings recorded in each run:** temperature (`TEMPERATURE`, or omitted as above), `data_collection: deny` (OpenRouter routes only to providers that don't keep or train on the data), at most 48,000 output tokens unless `MAX_TOKENS` says otherwise (a 30-minute wait for the reply); the output tokens are recorded as reasoning and visible (`run.usage.reasoning_tokens`, `visible_tokens`) when OpenRouter reports the split, $2 spending cap per book (Claude models).

## Intake: untagged PDFs

`intake.py` runs first in every run (`INTAKE=off` turns it off). A tagged PDF is left alone ("none (already tagged)"). For an untagged one, everything is local, no model writes or changes any text, and the original is never written to. The sponsor-checklist step each part serves is in brackets.

1. **Triage.** Every page is classed: visible text, image only (no text, and images covering at least 25% of the visible page area together: a scan or a picture page such as a Part opener), an existing invisible OCR layer, or blank. **Private-use characters (3.6):** every text page is checked for characters with private-use codes (legacy fonts use them for e.g. U+F730–F739 old-style digits, U+F761–F77A small capitals), which a screen reader may read as nothing or nonsense. Their count, pages and code ranges are recorded in `intake.json` (`private_use`); more than 100 is a CHECK. **Text outside the visible page area:** characters that lie outside the CropBox (e.g. a printer's slug in the margin) are invisible on screen and in print but read by a screen reader unless marked as artifacts; their count and pages are recorded (`outside_page_area`) and flagged. **Word breaks (3.4):** for every text page, PDFium tells real space characters from spaces it makes up from gaps between letters. A book where most word breaks are gaps only gets a note with the share of pages (`word_breaks`; Prince and TeX books are typically over 90%, Distiller books near 0%). A gap is **narrow** when it is under 19% of the type size (font size × text matrix), measured between advance widths, which is what a text extractor uses. The cut was calibrated on two Acrobat copies: on bringing PDF 86 Acrobat ran words together at 14.9–18.3% ("concernedwithChinese", "theWestern", "theWest"), and on 9798880703272 PDF 9 it spaced 19.8% correctly. The book is judged as a whole: when narrow breaks average **10 or more per text page** it is a **CHECK** listing the 20 worst pages; below that, a note with the rate. Detection only: nothing is changed.
2. **Is the text layer usable? (1.2)** Up to 20 pages with text, spread through the book (in a book with 40 or more text pages, not from the first 5% of them, at least 6: front matter such as the copyright page is set in small type that OCR reads poorly), plus up to 4 that look suspicious (private-use characters, very long run-together words) are drawn at 300 dpi and read by Tesseract, and the OCR text is compared with the page's own text layer, after normalising quotes, dashes, case, spacing and line-end hyphens (CJK characters are left out). Only text inside the visible page area (CropBox) is compared.
   - **Page score:** the lower of the in-order character error rate and the any-order one (the same characters in any order), so a page whose text is right but read in a different order is not counted as wrong; it shows as "usable (reading order differs)". Both raw rates are recorded per page (`cer_in_order`, `cer_any_order`; `cer` is the page score).
   - **Book score:** the median of the page scores (`median_cer`). ≤ 5%: usable. Over 15%: unusable. In between: doubtful (the book goes on with a CHECK). Fewer than 5 pages scored: "not enough pages scored" (a CHECK).
   - **Pages that are not scored** (listed as "not scored" with the reason, left out of the median): images cover 25% or more of the page together; fewer than 300 characters in the text layer after normalising; or 20+ CJK characters (or 10%+ of its letters) when the OCR language has no CJK pack. Each is replaced by the nearest scorable page, so up to 20 pages are scored. How many pages in the whole book fall under each reason is recorded (`unscorable_in_book`).
   - **Flags:** sample pages that are unusable although the book is not; doubtful sample pages, as one CHECK listing them; pages with clearly fewer word breaks than the printed page ("words run together", 3.4).
3. **Language (3.7).** From the scripts in the text layer, and Tesseract's script detection on image-only pages: Latin → `eng`, kana → `jpn`, hangul → `kor`. **CJK on pages to be OCR'd:** before OCR, every planned page is read once with the Chinese, Japanese and Korean packs; 10 or more CJK characters at 60% confidence or more mean the page holds CJK text (calibrated: sojourners' glossary 47–229, every cover and Part opener 0–1). Then the book **stops** unless `OCR_LANG` names a CJK language (it is never guessed); with one, the pages carry a CHECK "CJK OCR: needs a person" (CJK OCR is often wrong, and multi-column CJK lists may be read across the columns). Chinese characters with no kana are not guessed: OCR uses English only, and unless `OCR_LANG` says, the pages that get OCR text are flagged (a CHECK only when OCR is planned or kept; the scripts found are always recorded). A language with no installed pack is flagged.
4. **OCR (2.1, 3.1, 10.3, 10.4).** OCRmyPDF 17 with `--mode skip --pages <image-only pages> --output-type pdf --optimize 0 --oversample 300`: only pages with no text are OCR'd; pages with text are copied untouched; images are not recompressed and the file is not converted to PDF/A; scans under 300 dpi are read enlarged (the page image itself is unchanged) and flagged (in `--plan-only` as a note, since the run itself flags only the pages that keep OCR text). An image-only page whose OCR text is not text-like (fewer than 15 word-like tokens, or under 60% of its tokens) gets no OCR text: it is a picture (a cover, a Part opener) and goes to the figure step for alt text. Characters the OCR font could not map are counted (3.6). **Junk check:** on each page that keeps OCR text, tokens with symbols (# @ ® & …), capital clusters with no vowel ("MBH") or letters mixed with digits are counted; 5% or more of 30+ tokens is a CHECK "OCR text looks like junk" (calibrated: clean OCR 0%, sojourners' glossary 3.8–10.9% with `chi_tra+eng`).
   - **Unusable text layer:** the book **stops**, flagged, unless `FORCE_OCR=1` is set; then every page is OCR'd with `--mode force` (each page becomes an image, 400 dpi in our tests, with new invisible OCR text; the publisher's text layer is replaced, which review.md marks as a CHECK). **`FORCE_OCR=1` is unverified:** on synthetic test files OCRmyPDF redrew each page at 400 dpi, as a 1-bit black-and-white image when the page held only black text and as an 8-bit RGB image when it held a grey or colour picture. Either way 0.31–0.39% of each softened page differed and the after-OCR check (limit 0.3%) stopped the book. Until this is resolved, a book with an unusable text layer goes to a person.
5. **Auto-tag (4–7, 10.5).** OpenDataLoader (`--format tagged-pdf`, local mode, no hybrid server) adds a tag tree: headings, paragraphs, lists, tables, figures, captions, links; running heads and page numbers become artifacts. When there is OCR text, its hidden-text filter is turned off so the invisible OCR text is tagged too. On OCR'd pages, a Figure that is only the whole-page scan image is then marked as decoration: it is the page itself, not a figure (5.1).
6. **Checks (a failed check stops the book, with the reason in `intake.json`):** after OCR, every page looks exactly as before and only the planned pages gained text (force OCR: pages may differ only by anti-aliasing); after auto-tagging, every page looks the same (a tolerance of 0.05% of a softened 72-dpi page allows sub-pixel glyph shifts where the tagger splits a text run; a page over it gets a second look at 300 dpi and passes when no quarter-inch tile has more than 50 changed pixels, which a missing character exceeds) and its text is unchanged (a page whose text holds exactly the same characters in a different order passes as "reordered": the tagger re-sequenced text runs; the moved fragments are listed in `intake.json` and review.md, and the tag tree sets the reading order); a tag tree exists; bookmarks, links and page labels are all still there. How much text the tag tree reaches is recorded.

The result, `_intake/intake.pdf`, is what audit, decide, apply and verify then work on; `verify.py` compares the remediated PDF with it, and intake's own checks compare it with the original. A rerun with the same settings reuses an earlier intake; `FROM=` reruns copy the earlier book's intake so a saved reply still fits the same file.

**Checks on every book (verify.py, checklist 3.6):** characters a screen reader reaches that have no Unicode value (`(cid:N)`, U+FFFD, control codes), and characters with private-use codes, with their code ranges; each is a CHECK when above 0.

**In review.md:** an "Intake:" line under the header; check rows for the text-layer test, word breaks, the OCR (with any low-resolution, language or unmapped-character issue) and **"OCR text reviewed by a person"**, which stays CHECK until someone records "approved" with `review_ocr.py` (`record.json` → `intake.review.ocr_text_approved`: verdict, reviewer, date, reason, pages; checklist rule 2); and an "Intake: OCR and auto-tagging" section with the per-page text-layer scores (a page that was not scored shows why, and which page replaced it), the OCR'd pages and every flag.

**Not done (yet):** OpenDataLoader's hybrid mode (a second, Docling-based server, which may handle complex tables better: 5.6–5.8), deskew/despeckle of degraded scans (2.2), re-reading low-confidence OCR lines (3.2), and personal-information flagging (1.1); veraPDF (11.2) is done (see "Verification with veraPDF"). Accuracy of the OCR itself (CER/WER) needs a hand-corrected reference (11.1); the first candidate is `9780824882402.pdf`, PDF 381–386. Thresholds (5% / 15%, 15 words / 60%, the 25% image and 300-character rules, 5 pages, 100 private-use characters) are named constants at the top of `intake.py` and recorded in every `intake.json` (`settings.thresholds`); they are starting points to tune on real scores.

To see what intake would do to a folder of books without changing anything:

```bash
for f in ../samples/untagged/*.pdf; do python3 intake.py "$f" "/tmp/intake-plan/$(basename "$f" .pdf)" --plan-only; done
```

## What the executor always does by itself

These are mechanical, so they never wait for the model:

- makes sure there is exactly one Document root (Auto-Tag output often has none; some exports have two)
- sets the "tagged" flag and shows the title in the window
- sets the tab order of every page with annotations to the structure order (`/Tabs /S`; WCAG 2.4.3, PDF/UA 7.18.3)
- ties every link annotation to its text and gives it a description, creating Link tags where the tagger left none
- removes references to annotations that sit on no page
- rebuilds the tag-tree index (ParentTree) from the tree where entries are missing or wrong
- gives every Note tag a unique ID (and lists it in the ID tree). A Note tag is removed only when it is proven empty: nothing under it holds content or an annotation, it carries no alt, ActualText or ID, and nothing in the file but its parent refers to it. Turning note paragraphs into Notes stays the model's decision
- defers Han-only CJK runs and links on text missing from the tag tree to a person
- reports any PDF/UA claim the source already makes; it never adds one
- marks text lying entirely outside the visible page area (CropBox) as an artifact: a printer's slug in the margin, or the back cover and spine of a cover spread cropped to the front. A line counts only as a whole, so a line that starts on the page and runs past its edge is real content and is left (and listed); off-page text inside a shared form XObject is left too. Before a page is changed, its text operators are matched one for one with the characters the reader found, and any mismatch leaves the page as it was. review.md lists what was marked, and for a page with much hidden text (a cropped cover, even when the auto-tagger already marked it) lists every hidden line for whoever writes that page's alt text
- sets `/Tabs /S` on every page with links or other annotations, so the keyboard and a screen reader move through them in tag order (WCAG 2.4.3); verify.py counts pages still without it
- corrects font maps (3.6): characters a font maps to private-use codes that are really digits (Adobe old-style U+F730–F739, Minion lining U+F639–F641/U+F6DC) become 0–9, and a glyph named `threeemdash` with no map entry becomes three em dashes. Each glyph is confirmed by rendering it: a digit must read as that digit in context ("2?2", "3?3", two exact readings) and agree with the digit its glyph name states; the dash must be one bar at least 2.5 em wide. One decision per font across all its copies (corrected when at least one copy confirms it and contradictions are at most a quarter of the confirmations). Only the font's ToUnicode map changes, so pages look the same; verify.py compares text after the same corrections. Glyphs not confirmed are listed in review.md for a person. Needs Tesseract; without it the step is skipped with a note (tagged-only users need nothing new)
- checks every spoken text (ActualText) against the printed characters (sponsor rule 1): it may differ only in spacing, letter case and line-end hyphens (kept or dropped); added or changed words or punctuation are rejected. review.md lists every accepted spoken text that differs from the print, and every rejected one
- hides a run with a top- or bottom-band text rule (running heads, page numbers) only when everything else on that line is matched by a band rule too (or is already decoration): a superscript note number in the first line of body text can match a page-number pattern, but the body text beside it does not, so it stays visible; review.md lists such runs
- matches text rules whitespace-insensitively: a pattern fits the text as stored, with spaces normalised, or with spaces from gaps (`gaptext.py`), and every space in a pattern is optional, so patterns written against spaceless or spaced text both match
- turns a one-item list whose label is not a list marker into one paragraph: auto-taggers sometimes take a paragraph's first word ("as", "at", a year) for a list label. A marker is a bullet on its own or a number, letter or roman numeral followed by "." or ")" or in parentheses (`listrule.py`). The digest marks such lists `flattened_by_rule`; the model can keep one as a list with `keep_lists`, and a model `flatten` of the same list is logged as already done. review.md lists every list changed
- builds bookmarks from the heading tags when the file has headings and no bookmarks at all (nested by level; title from the heading's ActualText or its text; target its page). An existing bookmark tree is never touched
- marks untagged vector paths (rules, borders, lines) as decoration when nothing ties them to content: the path is not inside marked content that carries properties (ActualText, optional content), is not painted with a pattern, does not overlap a link or other annotation, and does not touch untagged text or untagged images on its page. A path that touches them is part of an untagged drawing (a map, a chart) and is left for a person to tag as a Figure. A path inside a shared form XObject is changed only if it qualifies everywhere the form is drawn, and the form is edited once. Strokes sitting directly under text are listed in the review, because an underline can carry meaning
- wraps a page whole in one Figure when nothing on it is tagged or marked as decoration, it has no links or other annotations, it has no hidden text layer (text in render mode 3, such as OCR), and it draws at least one image or path (a full-page map, plate or cover). Nothing on the page is changed or removed; the Figure gets a bounding box and goes in reading order after the block holding the last tagged content before the page (a paragraph that runs across the page comes first), or first in the Document when nothing comes before it (a cover). Its alt text comes only from the work order (`page_figures`); without one the Figure has none and `review.md` says "Page N is a figure wrap. Write the alt text." A page that fails the guard is left as it is and listed with the reason. Text in render mode 7 (a clipping shape, e.g. textured map labels) counts as drawn
- groups a caption with the element just before it when that element holds nothing but figures, on the caption's page and above it (the element becomes a Div), whether or not the work order names a wrapper style. A paragraph left behind when a figure moves out to join its caption is removed only when proven empty (the same proof as Note shells)
- puts every figure group back on its own page in reading order (`fix_figure_order` always runs); each move is listed in `review.md`
- gives a link whose description is only a URL the book's own sentence around it with the URL (and any other URL in it) removed: no words added, the visible URL unchanged. In a caption the whole caption is used. When no words are left the link is listed for a person; a link address that looks broken (an unmatched closing bracket) is listed, not changed
- gives the invisible OCR layer of scanned pages defined glyphs, when its font is HiddenHorzOCR, HiddenVertOCR or GlyphLessFont, every use of it is invisible (render mode 3), and its embedded program holds only `.notdef`. The font program is swapped for a blank TrueType one (each character a defined, empty glyph of the same width); the character codes, ToUnicode map, widths and render mode stay the same. The swap is kept only if a replay of those pages shows none looking different and no text changed. It does not correct OCR errors, and it never touches a visible font

How it carries out the model's decisions, mechanically:

- **A RoleMap entry for a standard tag** (e.g. the publisher style literally named `H1` → `H3`) cannot be written into the RoleMap, so it is carried out as a retype of every element with that tag. The review lists it as "retype (standard tag)" with the element count
- **Text rules** (running heads, page numbers) match the run's text with spacing normalized (double spaces, leading and trailing spaces). A running head split into several runs is hidden as a whole when all its runs sit in the rule's band. A rule that matches nothing is reported, not silently dropped
- **Decoration drawn by a shared Form XObject** (e.g. a junk text grid repeated on many pages) is hidden inside the form when a text rule matches every run in it, and its tags leave the tree
- **Captions** on a page with several figures are tied to the figure right next to them (above or below, at most 40 pt, overlapping horizontally). Two equally close figures, or a caption inside a figure's area (a panel letter such as "a"), stay with a person. Position-paired captions are listed in the review

**Fonts** are checked; the only font change is the invisible OCR layer above. `verify.py` lists fonts that are not embedded, fonts with no ToUnicode map, and fonts whose embedded program holds only the `.notdef` glyph (every character drawn with them is undefined, PDF/UA 7.21.8); `review.md` explains each one and what a person must do, and has a row for undefined glyphs in invisible OCR text. A font program that cannot be read is a CHECK ("every embedded font program could be read"), never a pass: unread means unchecked. A missing ToUnicode map is not flagged for a simple, non-symbolic font whose encoding is WinAnsi, MacRoman or MacExpert with no `/Differences` (its characters are fixed by that encoding); it is flagged when the encoding is missing, custom, or has `/Differences`. Needs `fonttools` (in `requirements.txt`).

**Untagged content** is counted: `verify.py` counts every text, path and image that is neither tagged nor an artifact (a form XObject once, as checkers do), and `review.md` lists the pages with the most, with a separate row for untagged paths. Untagged text is marked as decoration only in the two `artifacts.untagged` cases; untagged paths only by the path rule above; untagged images never. A page with no tags at all that holds a drawing is wrapped as a Figure (above), never hidden.

**Page references** in `review.md` use the PDF page as the key, because the checker, Acrobat and the executor all count the file: `PDF 16 (printed 3)`. The printed label comes from the remediated PDF's own page-label table and appears only when there is one and it differs (a non-numeric label too: `PDF 1 (printed Cover)`); a book with no labels shows the PDF page alone. Ranges: `PDF 7–234 (printed 1–221)`. A tag with no page of its own: if it holds a figure or other content, it takes the page of the figure inside it, else of the first content inside it; if it is empty (e.g. a kept empty tag), it takes its parent tag's page (one step up, never a Sect that only stores the page it starts on). If that is missing too, the review says `page: not on this tag`. The executor's own sentences use the same wording for a missing page. The executor's own messages (rejections, deferral reasons) use the same form; `record.json` and the logs keep plain PDF page integers. The model's sentences are quoted as written, never rewritten; the prompt asks it to cite pages the same way, and a deferral's optional `pages` field is shown in the standard form beside its sentence.

**No bare "unknown".** `review.md` and `summary.md` never print "unknown", "?" or "None"; a missing value says why: a header cost or token count missing → "call did not finish"; a run start time, model or prompt missing → "not recorded"; a count the verify file or the log left empty → "not counted"; heading text or style absent → "(no text)" / "(no style)"; an artifact label the model did not give → "(no label given)"; a rejection with no reason → "(no reason recorded)"; title or language missing → "not set". `record.json` and the logs keep a missing value as `null`. Quoted text (the book's own words, the model's sentences) is printed as written, question marks included.

**Empty tags** are removed when proven empty, whether the source or the run emptied them: nothing under the tag holds content, it carries no Alt, ActualText, E or ID, and nothing in the file refers to it except its parent. The pass repeats until nothing changes (removing a child can empty its parent, e.g. a flattened grid unwinds paragraph → row → table). Table cells and rows are never removed one by one; a table goes only when every part of it is empty. A tag kept only because something refers to it (a ParentTree entry, stale or not; an IDTree entry; a /Ref; a bookmark) or because it carries an attribute is a CHECK naming the reference. Each removed empty heading is tested: if no other heading on its page has text, `review.md` says the title may be lost. Empty captions, figures, links and list items are listed. The pass runs before bookmarks are built.

**Tag-tree index cleanup** runs last: a ParentTree entry that points at a tag no longer in the tree is cleared (the entry becomes null; its key stays), and an IDTree entry that points at such a tag, or at nothing, is removed. These come from the source file or from tags the run removed (e.g. running heads that carried IDs). Nothing on a page, no text and no reachable tag changes; `review.md` lists every entry cleared.

**Structure checks** in `verify.py` and `review.md`: empty tags (an empty table cell is not counted), a paragraph holding nothing but figures, a caption not grouped with a figure, a link whose description is only a URL, a table whose every cell is empty, and a tag-tree index entry (ParentTree or IDTree) that points at a tag no longer in the tree (dangling); stale entries (marked content no longer drawn) are counted beside it.

The executor never recolours text, rewrites words (including OCR text), invents MathML, creates form fields, replaces figures, or rewrites the alt text the work order supplies. Contrast, OCR quality, forms, math, reflow and colour-only meaning stay with a person.

## What the model decides

Title and language; heading levels (by style, or element by element when the tagger's headings are generic); merges and spoken heading text; alt text and decorative figures (including full-page scan images); running heads and page numbers to hide, including ones marked but outside the tag tree; false lists and tables to flatten into paragraphs; lists, contents, notes and captions by style; one reading-order move. Contents entries by a list of styles and the contents pages. Orphan runs that are real content (notes, bibliography) added to the tag tree in page order (`adopt_orphans`). Untagged blank-page notices, and untagged labels inside a Figure whose alt text covers them, marked as decoration (`artifacts.untagged`, all-or-nothing per page). Alt text for pages the executor wraps whole as Figures (`page_figures`, from an image of the page in the digest: for a map, its name and main regions). Real tables, untagged real content, and OCR errors go to a person. (Notes: the model decides which paragraph styles become Notes; IDs are always handled by the executor.)

## Work order rules

- Elements are referenced by object number in the **original** file (`"18592 0"`). That works because `apply.py` changes everything in memory and saves once.
- `source.sha256` must match the input file, or `apply.py` refuses to run.
- Each operation checks its target first. One that doesn't fit is **rejected and logged**, never half-applied.
- Targets are whitelisted. Work-order text is only ever data: never executed, never written into page content.
- **One work order per reply.** A model sometimes writes a work order, then a correction ("This is the intended entry set:") and a second, complete one. Then the **last** block is used, exactly as written: it is the model's final answer, nothing is merged, and an earlier block is never used in its place. If the last block can't be read, the run stops even when an earlier one could be. `review.md` marks it as a CHECK ("Model reply held one work order") and quotes what the model wrote before the last block; `record.json` keeps the full reply (`raw_reply`) and `run.reply_blocks`.

Background: before any API spending, a replay test confirmed that `apply.py` reproduces the Cowork session's *Cadaverous* result exactly from a written-down work order.
