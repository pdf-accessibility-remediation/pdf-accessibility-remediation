---
title: Options
nav_order: 4
---

# Options

These settings change what one run or batch does. Put them before the command, for example `KEEP=1 bash run_api.sh …`. The tables below list them by purpose. After the tables come resuming a run that stopped, what a run may cost, and the settings only developers use.

## Running and reviewing

| Before the command | Effect |
|---|---|
| `AUTO=1` | Sends without the y/N question. The dollar limits and your credit still apply (see [Sending without asking](#sending-without-asking)) |
| `ESTIMATE=1` | Audit and cost estimate only. A later run with the same label reuses the audit |
| `REPLY=path/to/reply.txt` | Reuses a saved AI reply instead of making an AI request (no cost) |
| `REVIEW=1` | Stops after the AI's decisions so a reviewer can approve, change or reject each one before anything is applied. One PDF at a time, not in batches (see [Reviewing the work order](review-step.md)) |
| `REVIEW_DRYRUN=off` | With `REVIEW=1`: skips the trial run of the apply step at the review stop (see [The trial run at the review stop](#the-trial-run-at-the-review-stop)) |
| `DECIDE=none` | No AI request at all: the work order starts empty and a reviewer fills it in, $0 (see [No AI request](#no-ai-request)) |
| `KEEP=1` | Keeps the working files (digest, figure crops, raw reply, logs) |
| `OUT=name.pdf` | Names the result (default: `<original name>_remediated.pdf`) |
| `RUNS_DIR=/path` | Writes runs somewhere other than `runs/` beside `pipeline/` |
| `VERAPDF=off` | Runs without veraPDF; review.md says its rows were not run (see [veraPDF settings](#verapdf-settings)) |

To apply a reviewed work order, rerun the same label without `REVIEW=1`.

## Model and cost

| Before the command | Effect |
|---|---|
| `MODEL=openai/gpt-5` | Any OpenRouter model id for this run or batch (default: `DEFAULT_MODEL` in `decide.py`, `anthropic/claude-sonnet-5.5`; see [Models](models.md)) |
| `MAX_USD=3` | The limit on what one AI request could cost, in dollars (default 2). Claude models only |
| `BOOK_MAX_USD=6` | The limit on what all of a PDF's requests could cost together (default 5). Claude models only (see [The limit per PDF](#the-limit-per-pdf)) |
| `BATCH_MAX_USD=20` | Batches only: the limit on what the batch has already spent plus what it could still cost (default 10) |
| `PAGE_READS=off` | No page readings: scanned Hawaiian pages are not read whole by the AI (see [Page readings](#page-readings)) |
| `PAGE_READS=all` | Page readings for every scanned page with text, not only mostly Hawaiian ones |
| `PAGE_READS_MAX_USD=5` | The limit on what the page readings together could cost, in dollars (default 3) |
| `FIGURE_PASSES=off` | No figure requests: figures past the first request's 100 images go to a reviewer (see [Files](files.md)) |

## Untagged PDFs (intake)

| Before the command | Effect |
|---|---|
| `OCR_LANG=jpn+eng` | Tesseract languages for OCR (default `eng`; see [OCR languages](#ocr-languages)) |
| `FORCE_OCR=1` | OCRs every page of a PDF whose text layer is unusable, instead of stopping it. **Unverified** (see [Forcing OCR](#forcing-ocr)) |
| `OCR=off` | No OCR; image-only pages are listed as having no text |
| `INTAKE=off` | No intake step at all: an untagged PDF goes to the audit as it is |

## Batches

| Before the command | Effect |
|---|---|
| `JOBS=1` | PDFs run at the same time (default 3). Use 1 after a rate limit (see [When the AI request fails](troubleshooting.md#when-the-ai-request-fails)) |

`BATCH_MAX_USD` and the other batch settings are explained in [Batch runs](batch-runs.md).

## Details

### Sending without asking

With `AUTO=1` and a Claude model, the request is sent only if each request's Max Estimated Cost is within the $2 limit per AI request, the PDF's total is within the $5 limit per PDF, and both are within your credit.

For any other model the estimate is approximate and is not a limit. The line printed before sending says which case applies.

### The limit per PDF

`BOOK_MAX_USD` counts every request for the PDF: the work order, its figure requests, and what previous attempts in the same run folder spent. The run stops before any request when the total is over the limit, and says the value to set.

### No AI request

`DECIDE=none` makes an empty work order for a reviewer to fill in on the review page (with `REVIEW=1`). It costs nothing and reads no pages. With `ESTIMATE=1` it only says there is nothing to estimate.

`handedit.py import` sets it for a PDF edited by hand and brought back for review (see [Editing the PDF by hand](hand-edits.md)).

### The trial run at the review stop

At the review stop, the pipeline runs `apply.py` once as a trial. It works out which figures the executor moves, and whether it makes the AI's section move. It takes about as long as the apply step: about 2 minutes for a 250-page PDF.

`REVIEW_DRYRUN=off` skips it; the review page then says the figure moves were not worked out. A later review reuses the saved trial run while nothing it depends on has changed. `REVIEW_DRYRUN=fresh` makes it again regardless.

### Page readings

By default (`PAGE_READS=1`), the scanned pages the audit finds mostly Hawaiian are read whole by the AI (`read_pages.py`). They have their own estimate and question; `AUTO=1` skips the question. A PDF with no such pages costs nothing. If the readings are refused (over their limit or your credit), the step is skipped and the PDF goes on without them.

No pages are read:
- with a saved reply (`REPLY=…`)
- with no AI request (`DECIDE=none`)
- in command-line batches, unless you turn it on with `PAGE_READS=1 bash batch_api.sh …`. `BATCH_MAX_USD` then counts it.

`PAGE_READS=all` is for an English PDF with Hawaiian words on most pages. The audit lists the pages to read, so a run already audited without it needs a fresh audit. See [OCR words](ocr-words.md#pages-read-whole).

### OCR languages

A scan with Chinese, Japanese or Korean text on pages to be OCR'd stops until `OCR_LANG` names a CJK pack:
- `kor+eng` for Korean
- `jpn+eng` for Japanese
- `chi_tra+eng` or `chi_sim+eng` for Chinese

Chinese characters with no kana are never guessed as Chinese or Japanese.

For **vertical** Japanese, which the stop message points out, use `jpn_vert+jpn+eng`. With `jpn+eng` alone the OCR text is mostly junk. On one 13-page sample it gave 5% Japanese and left 8 pages without text, against 85% and every page with the `_vert` pack.

Hawaiian has no Tesseract model, so a Hawaiian scan is OCR'd with `eng`. That turns the ʻokina into `‘` and drops or misreads the kahakō (see [OCR words](ocr-words.md#hawaiian)).

### Forcing OCR

When intake's text-layer test says a PDF's text layer is unusable, the PDF stops, flagged for a reviewer. `FORCE_OCR=1` OCRs every page anyway: page images plus new invisible OCR text, replacing the old text.

**Unverified:** in testing, forced OCR stopped at its own after-OCR check on every page (see [Intake](intake.md)).

### veraPDF settings

`VERAPDF=off` runs without veraPDF, and review.md says its rows were not run. `VERAPDF=/path/to/verapdf` uses a launcher that is not on `PATH`. `VERAPDF_TIMEOUT` (seconds, default 900) limits each veraPDF run.

## If a run stops partway

A run label that already holds a finished run is refused, so earlier results are never overwritten.

**If a run stops partway, rerun the same command** (same label). It picks up where it stopped:

- **The audit** is reused.
- **A reply that was cut off** at the output limit is logged with its cost, then a new request is made that **allows twice as much, automatically**, up to the model's maximum. Nothing needs setting; the new estimate shows what it could cost. A reply already cut off at the model's maximum stops the run, because another attempt would be cut off too.
- **A complete reply, where a later step failed,** is reused with no new charge. What it cost stays this run's: it still counts toward the limits and in every cost shown.
- **A complete reply that couldn't be read as a work order** is read again first, with no new charge (useful after a pipeline fix). Only if it still can't be read is its cost logged and a new request made.

The cost of a cut-off reply is listed in `record.json` under `earlier_attempts`, and in the cost line of `review.md`.

## What a run may cost

**The dollar limits are the only limits you set:** $2 per AI request, $5 per PDF and $10 per batch. The app and the terminal use the same defaults. They apply to Claude models only.

Before each AI request, the pipeline shows two figures:

- **Expected Cost:** what the run will probably cost. Read it first; it decides nothing.
- **Max Estimated Cost:** the most it could cost. This is the figure checked against the limits and your credit.

### Expected Cost

Expected Cost is learned from the last 80 finished AI requests of the same model and kind: work order, figure request or page reading. Each PDF weighs the same. The terminal also prints the usual range. The figure can't pass the Max Estimated Cost.

It reads **Not Available Yet**:
- until there are 12 past requests from 6 PDFs for that model and kind (today Opus 5.5 and every non-Claude model)
- after an answer was cut off in that run's folder

**A request larger than any learned from still gets a figure,** and the terminal says so. It rests on few PDFs and tends to read high: in testing, work orders of that size came in at a median of 0.85 of the figure, and figure requests at 0.57.

**Page readings** (see [OCR words](ocr-words.md#pages-read-whole)) have their own history. Until 12 pages from 6 PDFs have been read, a PDF with pages to read shows Not Available Yet, because leaving the pages out would read low. Its Max Estimated Cost includes them either way.

Pages paid for count as the PDF's money at every stage: on the run and batch pages while it waits for review, in its record afterwards, and toward the per-PDF limit on a later attempt. A page read again after a cut-off keeps the first charge in the total; a page reused adds nothing.

### Max Estimated Cost

Max Estimated Cost is the input estimate × 1.25 at the input price, plus the request's room for a reply at the output price:
- 48,000 output tokens for a work order (more for a PDF with many OCR word forms: 16,000 plus 45 per form sent)
- 32,000 for a figure request

It is usually about 2.5 times the bill. If a limit can't afford that room, the run stops before spending: the room is never lowered to fit.

### After a cut-off

- **A work order:** the next attempt allows twice as much (see [If a run stops partway](#if-a-run-stops-partway)).
- **A figure request:** sent once more, automatically, with twice the room (64,000 tokens, trimmed to the model's maximum), within your real limits ($2 and $5, not the estimate shown). If that can't be sent or is cut off again, its figures go to a reviewer and are listed on the review page.

This second send can take the bill past the Max Estimated Cost shown, and the cost line then says so:

```
AI Cost: $3.40 ($2.90 + $0.50 to retry an answer that was cut off) · Max Estimated Cost: $3.13, not including the retry
```

Money spent by previous attempts in the folder is shown the same way.

### Batches

**A batch over its limit is refused before anything is sent.** The limit counts what the batch has already spent plus the Max Estimated Cost of the PDFs still to send. "Already spent" means every PDF's folder, whatever its state, and PDFs moved to the Trash.

**A retry may go past the batch limit.** A figure request's retry isn't checked against the batch limit during the run, because PDFs run side by side with no shared reservation. Getting past the limit would need bills near 100% of their ceilings plus a retry; real bills average about 40% of the ceiling.

## For developers

### Settings for development only

| Before the command | Effect |
|---|---|
| `MAX_TOKENS=` | A work order's output room for one run, terminal only. Can go below the normal value, and beats the doubling after a cut-off. Still held to the dollar limits; the app never passes it |
| `FIGURE_MAX_TOKENS=` | The same for figure requests |
| `FIGURE_RETRY_MAX_USD`, `FIGURE_RETRY_BOOK_MAX_USD` | The real limits for a figure request's doubled retry. The app passes them; in the terminal they default to `MAX_USD` and `BOOK_MAX_USD` |
| `FIGURE_PROBE=20` | Test only, terminal only: also re-sends 20 figures the first request answered, to compare the two answers. Recorded in `record.json` (`run.passes`, `overlap`), never used, counted in the cost |
| `APPLY_DRAFT=1` | Set by the review page's **Build a Draft PDF** for its own run of `apply.py`, not by hand: marks the output as a draft (a RemediationDraft document property). See [Checking a draft PDF while you review](review-step.md#checking-a-draft-pdf-while-you-review) |
| `ALLOW_PDF20=1` | Lets a PDF 2.0 file (or one with namespaced tags) through instead of stopping it. Only for building PDF 2.0 support; never on real work (see [Not supported yet: PDF 2.0](troubleshooting.md#not-supported-yet-pdf-20)) |
| `COST_HISTORY=/path` | Writes the cost history somewhere other than `runs/.cost-history.jsonl` |

### Where the limits live

`lib/costs.py` holds the limit defaults in one place (`DEFAULT_LIMITS`). The app and the terminal read them from there; the app's `webapp/settings.json` no longer lists them (see [The app](app.md)).

### Page readings in the app

The app's estimate prices the page readings. `ESTIMATE=1` writes `page_reads_estimate.json`, which `lib/costs.py` adds to the PDF's Max Estimated Cost, its checks and its fingerprint. Spend then sends the readings with `PAGE_READS_MAX_USD` bound to the estimate shown.

### How Expected Cost is learned

It predicts output tokens from the input estimate, so a price change needs no new history. The usual range is the 5th to 95th percentile of past misses. Its output can't pass the request's room for a reply. `read_pages.py` writes each finished page to the history, kind "page"; a page cut off teaches nothing.

**Where it learns from:**
- `pipeline/lib/cost_seed.json`: committed, numbers only. It holds token counts, two names, a date and a plain label per PDF such as `b07`.
- `runs/.cost-history.jsonl`: local, one line per finished paid request, never committed.

A saved reply (`REPLY=`, `FROM=`), a cut-off call and `decide.py` called on its own add nothing.

To rebuild the seed, run `python3 tools/cost_seed.py`. It keeps every label it gave, and writes the link from each PDF to its label only to `runs/.cost-book-labels.json`. So a call in both the seed and the local file counts once, and a PDF in both counts as one PDF. On a computer without that file, a seed PDF run again there counts as one more PDF.

### How Expected Cost was tested

**Work orders:** each past call predicted only from calls before it, never from its own PDF (`python3 tools/cost_backtest.py`, on the committed seed). The bill fell in the range on 206 of 235 calls (88%), and within 25% of the figure on 87%.

Caveats:
- The rule was picked on these same calls.
- The data for the current prompt is thin; on it the bill has run about 10% under the figure.
- Very large PDFs are overpredicted. The 18 work orders larger than any learned from (from two PDFs, up to 1.45 times the largest at the time) came in at a median of 0.85.

**Figure requests** are thinner: 19 calls from 6 PDFs, tested by holding each PDF out in turn, because no earlier set is large enough to predict forward from.
- The bill fell in the range on 14 of 19, and within 25% on 58%.
- Single requests ran over the figure more often than under it: 13 of 19, about 17% over at the median, seven of the 19 from one PDF.
- PDFs differ widely: 0.4 to 1.4 times the figure.
- The 2 figure requests larger than any learned from (from one PDF) came in at 0.57.

**Whole PDFs**, work order included: the five that could be checked came to $4.39 against $4.60 expected (worked out afterwards, with the minimum lowered for the test). That is about 5% under, ranging from 30% under to 33% over.
