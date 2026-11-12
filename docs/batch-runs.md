---
title: Batch runs
parent: Get started
nav_order: 3
---

# Batch runs

A batch runs a folder (or a list) of PDFs with one command and writes one summary. Batches can also be started from the app's home page, with a cost estimate before any paid request and a page that follows every PDF: see [The home page](home-batches.md#batches). The commands below are what the app runs.

```bash
AUTO=1 bash batch_api.sh batch1                                         # every PDF under samples (all subfolders)
AUTO=1 bash batch_api.sh batch1 ../samples/tagged                    # one folder
AUTO=1 bash batch_api.sh batch1 ../samples/tagged ../samples/untagged # several folders
AUTO=1 bash batch_api.sh batch1 ../books.txt                            # a list, to choose names yourself
```

`batch_api.sh` refuses to start without `AUTO=1`, because it makes AI requests without asking.

## Where the results go

Everything a batch makes goes in one folder:

```
runs/batches/batch1/
├── summary.md
├── teika/
│   ├── Teika_remediated.pdf
│   ├── review.md
│   └── record.json
└── fishers/ …
```

When you point at folders, the names are:

- **Each PDF's folder:** a folder holding one PDF gives its folder name (`books/teika/x.pdf` → `batches/batch1/teika/`). A folder holding several gives each file's name without `.pdf`.
- **The result:** always the original file name with `_remediated` added (`x.pdf` → `x_remediated.pdf`).

## A list of PDFs

A list sets each PDF's folder name, and optionally the result's name after a `|`:

```
# <short-name> <path to pdf> [| <result name>]
hawaii3     samples/tagged/hawaii3.pdf | The Value of Hawaii 3.pdf
teika       samples/tagged/teika.pdf
```

Relative paths count from the list file's folder. Short names must be unique across the batch.

## What a batch does

A batch works in three steps: estimate, run, summary.

### 1. Estimate (no AI request)

The batch runs intake for untagged PDFs (OCR and auto-tagging; free), audits every PDF and adds up what it could cost. A PDF with more than 100 images counts every one of its requests; its row says "in N requests" (see [Files](files.md)). Each PDF is also held to its own limit (`BOOK_MAX_USD`, $5) when it runs.

It stops before any AI request if:
- what the batch has already spent plus the Claude total is over `BATCH_MAX_USD` (default $10, from `lib/costs.py`), or
- the Claude total is over your credit.

The audits are kept, so a rerun with a higher limit reuses them.

Only Claude models count against the limit and the credit check (see [Choosing the model](models.md#choosing-the-model)), so the total lines depend on the model:

```
# Claude batch
  book1                        Expected Cost: $0.31 (usually $0.22–$0.43) · Max Estimated Cost: $0.67  (75,927 input tokens, 25 images)
  book2                        Expected Cost: $1.54 (usually $1.04–$2.22) · Max Estimated Cost: $3.13  (418,351 input tokens, 543 images in 6 requests)
  Expected Cost: $1.85 for 2 PDFs
  Max Estimated Cost: $3.80 for 2 PDFs (7 AI requests) · Batch Limit: $10.00 · Credit: $11.46
# non-Claude batch: one approximate line, no limit
  Max Estimated Cost: about $0.75, approximate, not counted against the limit (the OpenRouter bill is the real cost) · Credit: $11.46
# mixed (e.g. a RETRY with another model): the Claude lines are the part counted
  Max Estimated Cost: $0.50 for 1 PDF · Batch Limit: $10.00 · Credit: $11.46
  Non-Claude Models: about $0.25, approximate, not counted against the limit (the OpenRouter bill is the real cost)
```

A PDF with no figure yet reads "Expected Cost: Not Available Yet" on its row. The total then says how many PDFs it covers: "$0.31 for 1 of 2 PDFs (Not Available Yet for 1 PDF)".

There is no range on the batch's total: the rule tried for one held on about 95% of the earlier PDFs and 80% of the later ones. Each PDF's row keeps its own range.

### 2. Run

The batch runs every PDF through the full pipeline, `JOBS` at a time (default 3; each PDF needs about 0.5–1.5 GB of memory). Each line also gives that PDF's cost and the running total:

```
· AI Cost: $0.31 · Total Cost: $1.20 so far (expected $4.10, max estimated $8.80)
```

A failed PDF doesn't stop the others.

A PDF **flagged at intake** is not sent to the AI. That happens, for example, when its text layer failed the OCR comparison and `FORCE_OCR=1` was not set, or when it needs a password. summary.md shows "flagged at intake" with the reason, and `<book>/_intake/intake.json` has the measurements.

### 3. Summary

The batch prints the batch start time, model and prompt file, then a table with one row per PDF:

- book and status
- intake: what intake did, for example "OCR 6 pages · auto-tagged" or "none (already tagged)"
- pages
- API cost: what this batch spent
- the AI request's cost per page: the original call's for a reused reply, "not recorded" when none is kept
- time
- checks flagged
- veraPDF's failing WCAG rules before → after ("new" marks rules the result fails and the original passed)
- result, with a link to the PDF's `review.html`

Then come the total cost, the AI requests' cost per page over the PDFs whose cost is known, and the credit you have left. All of it is saved as `summary.md`.

A failed PDF's status says why: `reply cut off at 48,000 tokens`, `OpenRouter 429, model rate-limited (nothing charged)`, or OpenRouter's error code and message. Its log is kept beside the summary (`<name>.log`) only if that PDF failed; `KEEP=1` keeps every log and working file.

`summary.md` is written however the batch is started: no folder, one folder, several folders or a list. It is also written when a batch stops early or is interrupted; PDFs that did not run show as "not finished", and the terminal says where it stopped.

The summary's API cost includes calls whose reply was cut off, because they are paid for. Credit left is OpenRouter's balance. When OpenRouter hasn't caught up with the batch's calls yet, it is the credit before the batch minus what the batch spent.

## Finishing a batch that failed partway

A label that already holds a batch is refused, unless you add `RETRY=1`. Then only the PDFs without a finished result run again, and `summary.md` is rewritten for the whole batch. If every PDF has already finished, nothing runs and `summary.md` is simply rewritten: a free way to make a missing summary again. Give the same folders or list as the first time.

When PDFs fail, the summary prints the exact command to use. It repeats the batch's `MODEL=` and `FROM=`, and adds `JOBS=1` (with a note to wait a few minutes) if the model was rate-limited. A PDF whose reply was cut off needs nothing extra: its next attempt allows twice as much by itself. The limit also counts what the batch spent before the `RETRY`.

```bash
# a reply was cut off
RETRY=1 AUTO=1 bash batch_api.sh t-run2 ../samples/tagged
# a non-default model was rate-limited (429): wait, then one PDF at a time, same model
RETRY=1 JOBS=1 MODEL=openai/gpt-6.1-sol AUTO=1 bash batch_api.sh t-sol ../samples/tagged
```

Copy the printed command rather than retyping it: a `RETRY=1` without the original `MODEL=` would finish the PDFs with the default model.

## Rerunning from saved replies (no cost)

`FROM=<earlier-label>` reruns a batch from the AI replies saved in earlier `record.json` files: no AI requests and no cost. Use it to apply pipeline fixes to past decisions.

It looks for each PDF in the batch `runs/batches/<label>/<name>/` first, then in the single run `runs/<name>/<label>/`, so the folder names must match the earlier run.

## Settings the app uses

These are set by the app's batches (#45). With none of them set, `batch_api.sh` behaves as described above.

- **`REVIEW=1`:** every PDF stops after the AI's decisions for review. summary.md lists it as **waiting for review** (never failed), and `RETRY=1` never runs it again ("waiting for review, skipped"). The app's "Finish Review" applies that PDF (`run_api.sh`'s second call in its folder) and then writes the summary again.
- **`ocr_langs.tsv`** in the batch folder gives each PDF its own OCR language, one line each: `<short name> <TAB> <OCR_LANG>`. The app writes it from "Language of the Scanned Pages". A PDF not listed uses `OCR_LANG`.
- **`ASK_LANG=1`** is passed to `run_api.sh`. A PDF with pages to OCR and no OCR language stops before intake (exit 4), is listed as **needs a language**, and is not sent.
- **`SUMMARY_ONLY=1 bash batch_api.sh <label>`** writes summary.md and summary.html again from the batch's PDF folders, with no run and no cost ("Credit left: not checked"). The app runs it after a PDF is applied or moved to the Trash. When the batch folder has `trashed.json` (PDFs moved to the Trash from the app), summary.md adds "N PDFs moved to the Trash (AI cost $X), not counted above".

## For developers: checking a code change

To check that a code change left every `review.md` as it was, rerun the same PDFs with `FROM=` before and after the change, then compare the two labels:

```bash
python3 tools/compare_runs.py <label-before> <label-after>
```

It prints one line per PDF (identical, or how many lines were removed and added, and the first difference), and exits with 1 when any PDF differs. Only the "Time:" line and the run-start line are left out of the comparison.
