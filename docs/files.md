---
title: Files
nav_order: 13
---

# Files

This page lists what each script, module and data file in the repository does. It is for developers. The pipeline lives in `pipeline/`; paths below are relative to it, apart from `prompts/`. Run the scripts from `pipeline/`. Modules in `lib/` are only imported by them.

## Pipeline steps

| File | Role |
|---|---|
| `run_api.sh` | Runs the steps below for one PDF, in one command |
| `batch_api.sh` | Several PDFs in parallel, with a batch cost gate and a summary (needs `AUTO=1`) |
| `intake.py` | Untagged originals only: page triage, text-layer test, OCR and auto-tagging, with checks after each step. Local, no AI (see [intake.py](#intakepy)) |
| `audit.py` | Original → digest, the summary the AI reads. No AI (see [audit.py](#auditpy)) |
| `decide.py` | The AI request: estimates cost, checks credit, sends the digest and crops, parses and validates the reply (see [decide.py](#decidepy)) |
| `read_pages.py` | Scanned PDFs with mostly Hawaiian pages only: sends each such page image to the AI to transcribe as printed. Paid (see [read_pages.py](#read_pagespy)) |
| `apply.py` | The executor. Original + work order → `<original>_remediated.pdf`. pikepdf only; checks each target first and rejects what doesn't fit |
| `verify.py` | Checks the result against the original, adds the WCAG checks veraPDF does not make, and runs veraPDF on the result |
| `report.py` | Writes `review.md`, `record.json`, `han_review.csv` and `review.html`, then removes the working files (see [report.py](#reportpy)) |
| `report_html.py` | The offline dashboards: `review.html` for a run (`report.py` runs it) and, with `--summary <batch>`, `summary.html` for a batch (`batch_api.sh` runs it). Also rebuilds them for any finished run. See [Output files](output-files.md) |
| `vera.py` | Runs veraPDF with the pinned WCAG 2.2 machine profile (which includes the PDF/UA-1 rules), and condenses its report to one entry per failed rule: WCAG or PDF/UA-only, and who can fix it (for the AI, the work-order key). `--check`; or `vera.py FILE.pdf OUT.json` on its own |

### intake.py

A placeholder tag tree with no text structure counts as untagged. OCR is by OCRmyPDF and Tesseract, auto-tagging by OpenDataLoader. `--plan-only` shows what it would do without changing anything. See [Intake](intake.md).

### audit.py

The digest holds styles, listed elements, figures with crops, a page map, the reading order and front matter. In scanned PDFs it adds suspect OCR words on word sheets, and it holds veraPDF's PDF/UA failures.

Positions are measured in the visible page area (CropBox): running-head bands (top 70 pt, bottom 60 pt), figure sizes and crops. A figure drawn only outside it gets no crop, and is marked `outside_visible_area`.

The whole texts the digest shortens (elements, first list items, first table rows), and the full reading order of the containers for the review page (with each container's child styles), go to `fulltext.json` beside it. That file is for review.md, review.html and the review page only: never sent to the AI. It is kept in the run's `reviews/_audit/` with the digest (not the crops), for a later review.

### decide.py

Options: `--dry-run`, `--response-file`, `--no-model` (no AI request: an empty work order for a reviewer, `DECIDE=none`), `--check-key`, `--credit` (credit left), `--max-images` (default 100).

Each request's output room comes from `lib/costs.py`: 48,000 for a work order, or 16,000 plus 45 per OCR word form sent when that is more; 32,000 for a figure request. The AI's reasoning counts against it.

### read_pages.py

It runs after its own estimate and limit, and adds the readings to the work order as `page_readings`. A page read before is reused at no cost. See [OCR words](ocr-words.md#pages-read-whole).

It is on by default in `run_api.sh` and in the app's runs and batches, where the estimate prices it. `PAGE_READS=off` turns it off. It is off in command-line batches, and in a run with no AI request (`DECIDE=none`).

### report.py

`review.md` comes with its "Overview", and `record.json` with `glance`. It keeps the digest, `fulltext.json` and OCR word sheets in `reviews/`, and records a review as session 1. `--input` (from `run_api.sh`) records the input's path; `--from-record` and `--intake` are for a re-apply.

## Review and the app

| File | Role |
|---|---|
| `review_workorder.py` | The review step (`REVIEW=1`) and reviewing again (see [review_workorder.py](#review_workorderpy)) |
| `review_ocr.py` | Records a reviewer's verdict on a PDF's OCR text, or opens the OCR-only review page (see [review_ocr.py](#review_ocrpy)) |
| `manual_checks.py` | The accessibility evaluation from the terminal: `--show`, `--record pac\|screen-reader FILE.json [--for-sha SHA]`, `--refresh`, `--template pac\|screen-reader`; through `review/manual.py` |
| `handedit.py` | A PDF edited by hand in Acrobat: exports a copy, and brings an edited one back as a new run (see [handedit.py](#handeditpy)) |
| `app.py` | The app: one start command, then a run's page in the browser with buttons that run `review_workorder.py`'s own commands as queued jobs. See [The app](app.md) |
| `review/` | The review step's code: `core.py` (items, priority groups, decisions, diff, record; no web code), `server.py` (standard-library web server on 127.0.0.1), `page.html` (the page; no external libraries), `palette.css` (see [review/](#review)) |
| `review/sessions.py` | The review loop's records, with no server and no HTML (see [review/sessions.py](#reviewsessionspy)) |
| `review/ocr.py` | The OCR text verdict: the one writer for the review page and `review_ocr.py` (see [review/ocr.py](#reviewocrpy)) |
| `review/manual.py` | The one writer of the accessibility evaluation's results (see [review/manual.py](#reviewmanualpy)) |
| `review/clear.py` | "Clear This Book's Files" for a shipped PDF: the gate, the PDFs and images it deletes, `release/cleared.json` ([Accessibility evaluation and release](release.md#clearing-a-shipped-book)) |
| `review/prune.py` | "Clean Up Space": which previous versions' PDFs can go (never the current version, the AI's own, an evaluated or a shipped one), and their removal under `reviews/.lock` and the record lock, recorded in `release/removed.json`. `review_workorder.py --remove-older-pdfs` is its command line |
| `webapp/` | The app's core parts (see [webapp/](#webapp)) |
| `webapp/home.py`, `webapp/home.js` | The home page ([The home page](home.md)): the PDFs, runs in progress, My Workspace (cached in `runs/.app/home-index.json`), the "Upload a PDF" drop zone, the "⋯" menus and Edit Name in place, and the app bar on every page but the home page |
| `webapp/shared.js` | What the home and batch pages share: the "⋯" menus, Edit Name in place, and the New Run and New Batch pop-ups (contents from `GET /api/form`) |
| `webapp/books.py` | The PDF list (the uploads only; samples/ is searched by sha256 for originals, never listed), display names (`runs/.app/books-cache.json`), Upload a PDF (into `uploads/`, never replacing a file), the OCR language choices |
| `webapp/names.py` | The names people see, the app's only: PDF names (`runs/.app/book-names.json`), plain run and batch names (`runs/.app/run-names.json`), the automatic cleanup of a PDF's Title, and the folder label a plain name becomes |
| `webapp/newrun.py`, `webapp/spend.py` | A single run from the home page (see [webapp/newrun.py and spend.py](#webappnewrunpy-and-spendpy)) |
| `webapp/batches.py`, `webapp/batch.js` | Batches from the home page: the list of PDFs (`runs/.app/batches/<label>.books.txt`) and record, per-PDF estimates, totals, the batch's "Start Remediation" (batch_api.sh), the batch page and the side column |
| `webapp/lang.py` | "Language of the Scanned Pages" (#45): the question from `_intake/languages.json` (or intake's CJK stop), its evidence in plain words, and the answer's environment |
| `webapp/trash.py`, `webapp/trash.js` | "Move to Trash" (#45): a run, a batch whole or in part, an added PDF; the plans the confirmations show, the refusals, the moves, `runs/.app/trash-log.json` ([The app](app.md#move-to-trash)) |
| `webapp/manualpage.py`, `webapp/manual.js` | The app's Accessibility Evaluation page (see [webapp/manualpage.py](#webappmanualpagepy)) |
| `webapp/downloads.py` | A run's versions and their downloads (see [webapp/downloads.py](#webappdownloadspy)) |
| `webapp/failures.py` | Why a run stopped, in plain words, as a table by step, with the tool's own words only under "Details" |

### review_workorder.py

- **The review step:** `--prepare --pdf FILE` (run by `run_api.sh`: review items and page images), `--serve` (the review page on localhost), or `--reviewer NAME` after editing `workorder.json` by hand. It writes `review.json` and the reviewed `workorder.json`.
- **On a finished run:** `--reopen [--from N\|ai] [--no-apply] [--discard-open]`, `--discard-open` on its own (the open session marked abandoned), `--sessions`, `--apply`, `--pin [--pdf FILE]`, and `--replay-to DIR` (a run that can no longer be reviewed: its intake and saved reply copied for a new run on today's code).
- `--return-to URL` (with `--serve` or `--reopen`): the page to go to after Finish (the app's run page).

See [Reviewing the work order](review-step.md).

### review_ocr.py

```bash
python3 review_ocr.py <run>/<book> --verdict approved|"not approved"|"sent to a language reader" --reviewer NAME [--reason TEXT] [--pages 381-386] [--reads LANGUAGE] [--to WHO] [--date YYYY-MM-DD]
```

It goes through `review/ocr.py`, the same code as the review page's OCR Text section. It writes `_intake/intake.json`, `record.json` and the review.md row, and refreshes "Overview" and `review.html`. The row is OK only on "approved". FROM= reruns carry the verdict.

For a finished run, it is refused while a review page of the run is open or an apply runs. `--serve` opens the OCR-only review page.

### handedit.py

- `export RUN [--original --pdf FILE] [--to PATH] [--by NAME]` copies the result (or the original) for editing.
- `import RUN EDITED.pdf --by NAME --note TEXT [--label L] [--to review\|pipeline] [--base output\|original] [--base-pdf FILE] [--no-run]` makes a new run of it, linked to RUN: no AI call and a review stop by default, or the whole pipeline.

See [Editing the PDF by hand](hand-edits.md).

### review/

`palette.css` holds the dashboards' colors, light and dark, copied from `page.html`. `report_html.py` inlines it. Keep the two in step.

### review/sessions.py

The basis and its checks, pinning, sessions, carrying choices, a summary-only session for reviews made before sessions were kept, the lock, and the re-apply and promotion of a new result. See [Reviewing again](review-step.md#reviewing-again).

### review/ocr.py

- the gate's condition
- the checks on a verdict: one line, limits, no `\|` or `](`, pages within the PDF, `reads` for non-Latin pages
- the one writer for the review page and `review_ocr.py`: its locks, and every file written whole
- the review page's OCR Text section: pages, intake's findings, page text

See [The OCR text](review-step.md#the-ocr-text).

### review/manual.py

It records PAC 2026 or screen-reader test results under the record lock. It refuses while a new version is being made, or when the PDF on disk is not the one shown and described. It takes a first hash for older runs. See [Accessibility evaluation and release](release.md).

`write_run` is the refresh every writer of a finished run's record shares: release/ mirrored, the glance, review.md's Overview and its Accessibility Evaluation section, and review.html, each file written whole.

### webapp/

- `settings.json`: committed defaults. `settings.local.json` beside it is this machine's, git-ignored.
- `config.py`: the settings, and the clean environment of each job
- `checks.py`: the setup status
- `jobs.py` and `jobrun.py`: the queue on disk, and the process that runs one job
- `server.py`: 127.0.0.1 only; serves the run's own files from a fixed list
- `runs.py`: a run's state, and the commands its buttons start
- `logs.py`: the lines read from the tools' output
- `panel.js` and `panel.css`: the run page's panel

### webapp/newrun.py and spend.py

`newrun.py` has New Run's form, the free estimate job, Try Again decided from disk, New Run from the Saved Reply, and the "Language of the Scanned Pages" answer.

`spend.py` is the one gate every "Start Remediation" goes through: the fingerprint, the model and prompt, the limits, and MAX_USD. Every app run sets REVIEW=1.

### webapp/manualpage.py

Its data and HTML, escaped, with its data in a JSON block with `<`, `>` and `&` escaped. It also holds the display-only hash of the remediated PDF, and the run page's strip after "Ready to Ship?". The script (`manual.js`) saves drafts and records through `review/manual.py`. See [Accessibility evaluation and release](release.md).

### webapp/downloads.py

- the version list: only versions whose PDF exists; after clearing, the shipped copies
- the download names
- the files, opened in one moment under the record lock
- the streamed record ZIP and its read-me
- `release/downloads.json`: a complete record ZIP of a live shipment

## Tools and tests

| File | Role |
|---|---|
| `scan.py` | Fast read-only checks on a folder of PDFs, with no OCR and no AI (see [scan.py](#scanpy)) |
| `tools/compare_runs.py` | Are two runs' `review.md` files the same, PDF by PDF? (see [tools/compare_runs.py](#toolscompare_runspy)) |
| `tools/intake_cases.py` | Synthetic test PDFs for intake's classification (see [tools/intake_cases.py](#toolsintake_casespy)) |
| `tools/reorder_case.py` | `move_section` on a real book's tag tree (see [tools/reorder_case.py](#toolsreorder_casepy)) |
| `tools/handedit_case.py` | `handedit.py` on a real book (see [tools/handedit_case.py](#toolshandedit_casepy)) |
| `tools/regression.py` | The regression test: reruns the baseline books (`tests/baseline/`) from their saved replies (no AI request), and compares `record.json` fields and `review.md` with the baseline, plus checks that must always hold. `--update --reason "…"` writes a new baseline; `--seed RUNS_BATCH_DIR` copies the replies after a prompt change. See [Testing](testing.md) |
| `tests/` | The unit tests (`python -m pytest tests -q`) and `tests/baseline/`: the regression baseline (per book a saved reply, `review.md` and `expect.json`; `meta.json`; `UPDATES.md`, why each update was made). See [Testing](testing.md) |
| `requirements-dev.txt` | `requirements.txt` plus pytest, pinned: `pip install -r requirements-dev.txt` to run the tests |

### scan.py

`python3 scan.py <folder> <out_dir>` checks, per PDF:
- tagged, placeholder tag tree or untagged; MarkInfo; producer
- page triage (pages whose text draws no character are counted by their images)
- private-use characters, text outside the visible page area, and word breaks

Results go to `books/*.json` and `summary.md`.

### tools/compare_runs.py

`python3 tools/compare_runs.py <label-a> <label-b>` compares two batch folders under `runs/batches/`, or a prefix naming several (`s1` → `s1-g1`, `s1-g2`, …). It compares byte for byte, leaving out only the two lines that change on every run ("Time:" and the run-start line). It prints one line per PDF and a total, and exits with 1 when any PDF differs.

It is the acceptance test when `review.md`'s writing code changes: rerun the same PDFs with `FROM=` before and after, then compare. See [Batch runs](batch-runs.md).

### tools/intake_cases.py

Synthetic test PDFs, with no book content:
- an empty text object over a scan, an OCR layer, a text page
- placeholder and real tag trees (MarkInfo missing/false/true, Figure-only with alt)
- Japanese, vertical Japanese and Korean scans, with and without `OCR_LANG`

`python3 tools/intake_cases.py <out_dir> [--full] [--strict]` runs `intake.py --plan-only` on each, and prints PASS/FAIL per case and a summary line. The CJK cases SKIP when no CJK font is installed; `INTAKE_CASES_FONT` names one. `--full` also runs the whole intake on the two placeholder-tree cases. `--strict` (used in CI) counts a SKIP as a failure. Local, no AI.

### tools/reorder_case.py

It swaps one section with the next in a copy of a tagged sample (default hawaii3; pages unchanged). It runs `run_api.sh` on it with a hand-written reply holding only a `move_section` that undoes the swap. It checks:
- the audit's flag
- the review page's preview
- apply's move and log
- the restored order
- verify's section check: the swapped pair no longer flagged, nothing new

`python3 tools/reorder_case.py [--book hawaii3] [--moves 2] [--out DIR]`. With `--moves 2`, two pairs are swapped and put back by a list of two moves. It prints PASS/FAIL per check, and exits with 1 on any FAIL. No AI, veraPDF off; about 3 minutes. It also runs in CI (`pdf-validation.yml`, `reorder-case`).

### tools/handedit_case.py

It takes the result of a run from its saved reply, replaces one figure's image in an exported copy, brings it back for review (no AI call), writes its alt by hand, and applies it. It checks the figure found, the hashes, the safety checks and the alt texts, and prints what `apply.py` changed again.

`python3 tools/handedit_case.py [--book hawaii3] [--out DIR]`. PASS/FAIL per check, exit 1 on any FAIL. Local, no AI, veraPDF off.

## Shared helpers (`lib/`)

| File | Role |
|---|---|
| `lib/tablegrid.py` | Who heads what in a table, from its cells' spans and the work order's reading of its rows; refuses a reading that doesn't fit. Used by `apply.py`. No PDF here |
| `lib/workorder_check.py` | The checks every work order goes through before `apply.py`: used by `decide.py` on the AI's reply, and by `review_workorder.py` on a reviewed order |
| `lib/support.py` | Says whether the pipeline supports a PDF: PDF 2.0 and namespaced tags are not supported yet. `intake.py` stops such a PDF for a reviewer; `audit.py` and `apply.py` check again; `scan.py` reports it |
| `lib/gaptext.py` | Text as a reader hears it: a space where the PDF has a gap but no space character (over 0.10 em and 2.5 × the line's typical gap; not where another tag's glyph fills the gap). Used for the digest and review.md, and for matching text rules; never changes the PDF |
| `lib/listrule.py` | The one-item list rule, shared by `audit.py` (marks the lists in the digest) and `apply.py` (applies it) |
| `lib/readorder.py` | The reading-order rules: which tags count as sections, which are read away from their printed place (`verify.py` and the review page), and the one `move_section` match `apply.py` uses and the review page previews. Also the digest's one-line form of a section |
| `lib/scripts.py` | Which CJK script a run is in (hangul, kana, Han-only, mixed with Latin), and what language tag it needs against the document's language. Shared by `audit.py` (the digest's `cjk_runs`) and `apply.py` (the language step) |
| `lib/ocrwords.py` | Which OCR words in a scanned PDF look misread, and where words break (spaces, and gaps by `gaptext.py`'s rule). Used by `audit.py` for the word sheets. See [OCR words](ocr-words.md) |
| `lib/pagereads.py` | Which scanned pages are mostly Hawaiian (`audit.py`), and how a whole-page reading is paired with the OCR words, place by place (`apply.py`). See [OCR words](ocr-words.md#pages-read-whole) |
| `lib/langtag.py` | Checks and tidies a BCP 47 language tag. Used by `apply.py` (`/Lang` spelling) and `decide.py` (the work order's `document.lang`) |
| `lib/sections.py` | `review.md`'s content as data (see [lib/sections.py](#libsectionspy)) |
| `lib/origin.py` | The AI request behind a run's work order, for the cost per page (see [lib/origin.py](#liboriginpy)) |
| `lib/release.py` | The accessibility evaluation's rules, with no writing (see [lib/release.py](#libreleasepy)) |
| `lib/costs.py` | The money rules in one place (see [lib/costs.py](#libcostspy)) |
| `lib/costhistory.py` | The Expected Cost, learned from past AI requests (see [lib/costhistory.py](#libcosthistorypy)) |
| `lib/cost_seed.json` | The Expected Cost's committed starting history, numbers only. Built by `tools/cost_seed.py`; `tools/cost_backtest.py` tests the method on it |
| `lib/dates.py` | Dates and times as a person reads them ("October 31, 2026", "4:32 PM"), wherever the app, the dashboards and review.md show one. The same rule is in `webapp/panel.js` and `review/page.html` |
| `lib/runlock.py` | The record lock: one writer at a time of a finished run's record.json, review.md, review.html and release/ (`<run>/.record.lock`, flock, not re-entrant, a bounded wait) |
| `lib/glance.py` | The "Overview" numbers for a finished run, from `record.json` and `review.md`; shared by `report.py`, `report_html.py` and `review_ocr.py` (see [lib/glance.py](#libglancepy)) |
| `lib/plpages.py` | Reads each page once with pdfplumber, and keeps only what `audit.py` and `apply.py` use: characters, image boxes, size and the visible area (CropBox) |
| `lib/handedit.py` | What changed in a PDF edited by hand, for `handedit.py import`: the images on each page by their data's sha256, each Figure and the images it holds, the figures whose image is new, and a copy with their old alt text removed |
| `lib/plumb_fix.py` | Fix for pdfplumber's nested marked-content bug. Required; imported before pdfplumber reads a page |

### lib/sections.py

`report.py` writes `review.md`'s lines as before. A line can carry a key, its pages, and the parts only PDF/UA requires. `to_sections()` turns them into `record.json`'s `sections`, and `render_md()` gives back `review.md` line for line. `review.html` leaves out the PDF/UA-only lines and parts by this field, not by matching phrases.

### lib/origin.py

A reused reply (FROM=, REPLY=, a review's re-apply) carries the original call's cost, model, prompt and date. They come from `run.original_call`, a reply's `.meta.json`, or a record beside the reply with the same reply text. It writes `record.json` `ai_call` with the cost per page, and "not recorded" only when none is kept anywhere.

### lib/release.py

- the checklist, once, for the page, the command line and review.md, with its retired items
- checking results, and which results count for which file (by sha256)
- completeness and issues noted, and the evaluation line
- the status: Not Ready, Pending Evaluation, Ready, Shipped
- review.md's evaluation section

### lib/costs.py

The default dollar limits, each kind's output room, a step's Max Estimated Cost, limits and credit, the fingerprint, and the bounds a "Start Remediation" passes on (MAX_USD, BOOK_MAX_USD, BATCH_MAX_USD). Also the actual cost after a run and its one wording, and a batch's totals and what it has spent.

### lib/costhistory.py

It learns output tokens from past AI requests: the last 80 per model and kind (work order, figure request, page reading). It adds a PDF's page readings to its figure (`with_pages`). It reads the seed plus the local ledger, with each call and each PDF counted once, and it is the only code that writes the ledger. See [What a run may cost](options.md#what-a-run-may-cost).

### lib/glance.py

The numbers: status, ready to ship, the five safety checks, the veraPDF finding, needs a person, AI decisions, fixed automatically, veraPDF, and top issues.

## Prompts and veraPDF data

| File | Role |
|---|---|
| `prompts/workorder_v10.md` | The system prompt: rules and the work-order format. Its hash is recorded in every run (see [Prompt versions](#prompt-versions)) |
| `prompts/figures_v1.md` | The figure requests' system prompt (PDFs with more than 100 images, below): the figure rules of `workorder_v10.md`, copied word for word, and what a figure request may return. Its hash is recorded in `run.figure_passes` |
| `prompts/page_reading_v1.md` | The page readings' prompt (`read_pages.py`): transcribe the page exactly as printed, with ʻokina and kahakō only where the page prints them. Its hash is recorded in `record.json` under `page_reads` |
| `verapdf/` | `WCAG-2-2-Machine.xml` (the pinned profile), `rules.json` (each rule's WCAG success criteria, or why it is PDF/UA-only), `install.sh` |

### Prompt versions

Older prompt versions are kept as a record; v8 and older are no longer used.

- **v10** reads a table's rows from the digest's `row_shapes` (`title_rows`, `note_rows`, `group_rows`, `repeat_rows`), and stops counting a title row as a header. Work orders from v9 are still read.
- **v9** (schema `workorder/0.2`) makes `move_section` a list of up to 3 moves, made in order. It lets the AI turn the figure-order step off for a PDF (`fix_figure_order: false`, for figures meant to be read apart from their page). Work orders from v8 (one move) are still read.
- **v8** adds `tables` (header rows and columns of a real table), and lets `rolemap` map a style the source never mapped. It tells the AI the work-order key and tags for each `pdfua_check` rule, and requires every such rule to be fixed or deferred by name (step 9).
- **v7** changes the ActualText wording: spoken text only where printed glyphs read wrongly, equal to the print apart from spacing, case and line-end hyphens, and merges join a label and its title. It adds `ocr_words` (the printed spelling of misread OCR words in scanned PDFs, read from word sheets) and `pdfua_check` (the veraPDF failures the AI can act on).

## Figure images and figure requests

**Figure images** are sent as JPEG (long side 800 px). If a PDF's images together pass 20 MB, they are made smaller step by step, because OpenRouter refuses requests with more than 30 MB of images (HTTP 413). At most 100 images go in one request (Anthropic's limit). What was sent is recorded in `record.json` under `run.images`. Among the earlier test books, one had 543 figures and another 113.

**Figure requests** (#63) are for a PDF with more images than one request takes. The first request is the work order, as always. The figures it cannot take go to **figure requests** after it, up to 100 each. The 543-figure book had 100 with the work order, then 100, 100, 100, 100 and 43.

Each figure request sees:
- its figures: the same images and the same entries as the first request would have shown
- their captions, and the lines of their pages and the pages on either side
- the PDF's title, language and scan quality, so a whole-page scan in a scanned PDF is still marked as decoration
- the heading each figure's page falls under
- the untagged text on those pages
- the veraPDF failures that name those figures
- ten alt texts the first request wrote, as style examples, picked evenly through the PDF from the ones that passed the checks

Its instructions are `prompts/figures_v1.md`: the figure rules of `workorder_v10.md`, copied word for word (a test keeps the two in step). A figure request may decide only alt text, decoration and deferrals, and only for its own figures; anything else is dropped.

The first request is told, in a note after the digest, which figures another request will answer. Any decision it still makes about them is dropped: each figure has one decision, from the request that saw it. Then the answers are merged into one work order, which goes through the same checks as always.

### When the first request is unchanged

Exactly when it can take every figure and every OCR word sheet, by count and within 20 MB. Then nothing above happens: the same request, the same records.

When it can't, the OCR word sheets are reserved first, the figures fill the rest, and the remaining figures go to figure requests. So a PDF with 90 figures and 21 word sheets (111 images) sends the 21 sheets and 79 figures first, and 11 figures after.

A PDF whose images fit by count but not within 20 MB keeps one request: the figures are made one step smaller so that every sheet goes, and there is no note.

### Retries

**One retry:** a figure request that fails without being charged (OpenRouter 429 or 5xx, no connection) is sent once more after a pause: 60 s after a 429, 20 s otherwise. So is one whose reply could not be read, or that got no reply in time, when the PDF's limit still has room for it. A request that still fails leaves its figures to a reviewer, as one deferral ("Alt text for N figures"), and the run goes on; its cost is recorded.

**After a cut-off:** a reply cut off at its output limit (32,000) is sent once more, automatically and with no pause, with twice the room (64,000, trimmed to the model's maximum). So every image gets its alt text whenever it can. Only that request's `max_tokens` changes; a request not cut off is sent byte for byte as before.
- It must fit the real limits ($2 per AI request, and $5 per PDF with what is spent and what the other requests still planned), not the estimate shown, and the model's maximum and context.
- A request is never charged more than twice, and the doubled call isn't retried.
- If it can't be sent or is cut off again, its figures go to a reviewer as above, and the reason says why.
- A replay uses the final answer, free. The cost line says when a retry was paid for (see [What a run may cost](options.md#what-a-run-may-cost)).

### Cost

Every request is built, and its worst case worked out, before the first one is sent. The run stops before spending anything when:
- one request's worst case is over the per-call limit (`MAX_USD`, $2), or
- all of them together, plus what previous attempts in the same run folder spent, are over the limit per PDF (`BOOK_MAX_USD`, $5), or over your credit. Previous attempts are in `attempts.json`; a request whose charge isn't known (in flight when a run stopped or timed out) counts at its worst case.

It says the estimate, and how to raise the limit for that run. Both limits apply to Claude models only. There is no limit on the number of figure requests: the per-PDF limit is the limit.

Expected cost: about $0.002–0.003 per figure, plus about $0.05 per request. The 543-figure book cost about $0.9–1.8 for its five figure requests. The worst case allows the input 25% over the estimate (the largest undercount measured is 14.4%), and the full output limit.

### Records, replays and settings

- **Records:** `run.usage` and `cost_total_usd` are the sum of every request. `run.passes` lists each request with its figures, usage, time and outcome; `run.figure_passes` sums them up; `raw_reply_passes` holds each figure request's answer and the figures it was written for (see [Output files](output-files.md)). review.md lists the requests under the run line, with a check row "Figure requests: every figure seen by the AI".
- **Replays** (`FROM=`, `REPLY=`, "Review Again") use the recorded split, never a new one, and make no call. A saved reply made with figure requests needs its answers file (`reply.txt.passes.json`) beside it; without it, the replay stops. Older single replies replay exactly as before.
- **`FIGURE_PASSES=off`** sends one request as before: figures past 100 go to a reviewer, listed in the review under the AI's deferrals.
- **With `REVIEW=1`,** every alt text is a decision on the review page, whichever request wrote it, and every figure left without alt text is a gap at Finish (see [Reviewing the work order](review-step.md)).

## Where records live

**A record is never an image or a PDF.** `_audit/` and `reviews/_audit/` hold what the pipeline extracts from the PDF:
- records: the digest, its full text, dryrun.json, the OCR-word list, all `.json` or `.csv`
- figure crops and page images

Clearing a shipped PDF removes the PDFs and images there, and keeps every `.json`, `.md`, `.html` and `.csv` file ([Accessibility evaluation and release](release.md#clearing-a-shipped-book)). A new record goes beside record.json, in `reviews/` or in `release/`.

**The app's own files** are in `runs/.app/` (the `jobs` setting):
- `jobs/<id>.json` and `.log`: each job, its environment, its log
- `dispatch.lock`, `server.log`
- `sha256-cache.json`: PDFs' hashes
- `books-cache.json`: titles and page counts
- `home-index.json`: the earlier-runs list
- `book-names.json` and `run-names.json`: names, with `names.lock`
- `batches/<label>.books.txt` and `.json`: a batch made in the app

**`uploads/`** (repository root, git-ignored) holds the PDFs added with **Upload a PDF** and not used yet, each with a `<name>.json` note.

**A run started from the app** keeps its own original in `source/` (`<file name>.pdf` and its note). It is never written to, and kept by report.py's clean-up and by "Clear This Book's Files".

A run's `_intake/languages.json` is intake's `--languages` result. A batch folder may hold `ocr_langs.tsv` (each PDF's OCR language) and `trashed.json` (its PDFs moved to the Trash, with their cost).
