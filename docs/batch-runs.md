---
title: Batch runs
nav_order: 5
---

# Batch runs

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

1. **Estimate (no model).** It runs the intake step for untagged books (OCR and auto-tagging; free) and audits every book and adds up the worst-case cost. It stops before any API call if the Claude total is over `BATCH_MAX_USD` (default $5) or over your credit. The audits are kept, so a rerun with a higher cap reuses them. Only Claude models count against the cap and the credit check (see [Choosing the model](models.md#choosing-the-model)), so the total line depends on the model:

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
