---
title: Options
nav_order: 4
---

# Options

| Before the command | Effect |
|---|---|
| `AUTO=1` | No y/N question: sends straight away. For a Claude model only if each request's Max Estimated Cost is within the $2 limit per AI call, the PDF's within the $5 limit per PDF, and both within your credit; for any other model the estimate is approximate and not a limit (the line printed before sending says which) |
| `ESTIMATE=1` | Audit and cost estimate only; a later run with the same label reuses the audit |
| `REPLY=path/to/reply.txt` | Reuses a saved Claude reply instead of calling the API (no cost) |
| `REVIEW=1` | Stops after the AI's decisions so a person can approve, change or reject each one before anything is applied; rerunning the same label (without it) applies the reviewed work order. One book at a time, not in batches (see [Reviewing the work order](review-step.md)) |
| `REVIEW_DRYRUN=off` | With `REVIEW=1`: skips the trial run of `apply.py` at the review stop that works out which figures the executor moves and whether it makes the AI's section move (as long as the apply step: about 2 minutes for a 250-page book); the review page then says the figure moves were not worked out. A later review reuses the saved trial run while nothing it depends on has changed; `REVIEW_DRYRUN=fresh` makes it again regardless |
| `APPLY_DRAFT=1` | Set by the review page's **Build a Draft PDF** for its own run of `apply.py`, not by hand: marks the output as a draft (a RemediationDraft document property). See [Checking a draft PDF while you review](review-step.md#checking-a-draft-pdf-while-you-review) |
| `KEEP=1` | Keeps the working files (digest, figure crops, raw reply, logs) |
| `OUT=name.pdf` | Names the result (default: `<original name>_remediated.pdf`) |
| `MODEL=openai/gpt-5` | Any OpenRouter model id for this run or batch (default: `DEFAULT_MODEL` in `decide.py`, `anthropic/claude-sonnet-5.5`) |
| `MAX_USD=3` | The limit on what one AI call could cost, in dollars (default 2). Claude models only |
| `BOOK_MAX_USD=6` | The limit on what all of a PDF's requests could cost together, figure requests and previous attempts in the folder included (default 5). The run stops before any call when it is over, and says the value to set. Claude models only |
| `BATCH_MAX_USD=20` | Batches only: the limit on what the batch has already spent plus what it could still cost (default 10) |
| `FIGURE_PASSES=off` | No figure requests: figures past the first request's 100 images go to a person, as before (see [Files](files.md)) |
| `FIGURE_PROBE=20` | Test only, terminal only: also re-sends 20 figures the first request answered, to compare the two answers; recorded in `record.json` (`run.passes`, `overlap`), never used, counted in the cost |
| `RUNS_DIR=/path` | Writes runs somewhere other than `PDFREM/runs/` |
| `ALLOW_PDF20=1` | Lets a PDF 2.0 book (or one with namespaced tags) through instead of stopping it. Only for building PDF 2.0 support; never on real work (see [Not supported yet: PDF 2.0](troubleshooting.md#not-supported-yet-pdf-20)) |
| `VERAPDF=off` | Runs without veraPDF; review.md says its rows were not run. `VERAPDF=/path/to/verapdf` uses a launcher not on `PATH`; `VERAPDF_TIMEOUT` (seconds, default 900) limits each veraPDF run |
| `FORCE_OCR=1` | Intake: when the text-layer test says a book's text layer is unusable, OCR every page anyway (page images + new invisible OCR text; the old text is replaced). Without it such a book stops, flagged for a person. **Unverified:** in testing, force OCR stopped at its own after-OCR check on every page (see [Intake](intake.md)) |
| `OCR_LANG=jpn+eng` | Intake: Tesseract languages for OCR. By default `eng`. A scan with Chinese, Japanese or Korean text on pages to be OCR'd stops until `OCR_LANG` names a CJK pack: `kor+eng` for Korean, `jpn+eng` for Japanese, `chi_tra+eng` or `chi_sim+eng` for Chinese (Chinese characters with no kana are never guessed as Chinese or Japanese). For **vertical** Japanese, which the stop message points out, use `jpn_vert+jpn+eng`: with `jpn+eng` alone the OCR text is mostly junk (one 13-page sample: 5% Japanese and 8 pages left without text, against 85% and every page with the `_vert` pack). Hawaiian has no Tesseract model, so a Hawaiian scan is OCR'd with `eng`, which turns the ʻokina into `‘` and drops or misreads the kahakō (see [OCR words](ocr-words.md#hawaiian)) |
| `OCR=off` | Intake: no OCR; image-only pages are listed as having no text |
| `INTAKE=off` | No intake step at all (an untagged book then goes to the audit as it is) |
| `JOBS=1` | Batches only: books run at the same time (default 3). Use 1 after a rate limit (see [When the model call fails](troubleshooting.md#when-the-model-call-fails)) |

A run label that already holds a finished run is refused, so earlier results are never overwritten.

**If a run stops partway, rerun the same command** (same label). It picks up where it stopped:

- the audit is reused
- a reply that was **cut off** at the output limit is logged with its cost (it ends up in `record.json` under `earlier_attempts`, and in the cost line of `review.md`), then a new call is made that **allows twice as much, automatically**, up to the model's maximum. Nothing needs setting; the new estimate shows what it could cost. A reply already cut off at the model's maximum stops, because another attempt would be cut off too
- a reply that was complete, where a later step failed, is reused at no cost
- a reply that was complete but could not be read as a work order is read again first, at no cost (useful after a pipeline fix). Only if it still can't be read is its cost logged and a new call made

## What a run may cost

**The dollar limits are the only limits a person sets.** `lib/costs.py` holds their defaults in one place (`DEFAULT_LIMITS`): $2 per AI call, $5 per PDF, $10 per batch; the app and the terminal read them from there. The app's `webapp/settings.json` no longer lists them (see [The app](app.md)). They apply to Claude models only.

- **Expected Cost** is what a run will probably cost. It is what to read first, and it decides nothing. It is learned from the last 80 finished calls of the same model and kind (work order, or figure request): predicted output tokens from the input estimate, each PDF weighing the same. Output tokens are what it learns, so a price change needs no new history. The terminal also prints the usual range, the 5th to 95th percentile of past misses. The figure can't pass the maximum, and its output can't pass the request's room for a reply.
  - **Not Available Yet** appears with fewer than 12 calls from 6 PDFs for that model and kind (today every figure request, Opus 5.5 and every non-Claude model), for a PDF larger than any it has learned from, and after an answer was cut off in that run's folder.
  - **How it was tested:** each past work-order call predicted only from calls before it and never from its own PDF (`python3 tools/cost_backtest.py`, on the committed seed). The bill fell in the range on 185 of 211 calls (88%), and within 25% of the figure on 88%. The rule was picked on these same calls, the data for the current prompt is thin (on it the bill has run about 12% under the figure), and very large PDFs are overpredicted.
  - **Where it learns from:** `pipeline/lib/cost_seed.json` (committed, numbers only: token counts, two names, a date and a plain label per PDF such as `b07`) and the local `runs/.cost-history.jsonl`, one line per finished paid call, never committed. A saved reply (`REPLY=`, `FROM=`) adds nothing, a cut-off call adds nothing, and `decide.py` called on its own adds nothing. `COST_HISTORY=/path` writes it somewhere else. To rebuild the seed: `python3 tools/cost_seed.py`; it keeps every label it gave and writes the link from each PDF to its label only to `runs/.cost-book-labels.json`, so a call in both the seed and the local file counts once and a PDF in both counts as one PDF. On a computer without that file, a seed PDF run again there counts as one more PDF.
- **Max Estimated Cost** is the estimated ceiling, the figure checked against the limits and your credit. It is input estimate × 1.25 at the input price, plus the request's room for a reply at the output price: 48,000 output tokens for a work order (more for a book with many OCR word forms: 16,000 plus 45 per form sent), 32,000 for a figure request. It is usually about 2.5 times the bill. If a limit can't afford that room the run stops before spending: it is never lowered to fit.
- **After a cut-off.** A work order: the next attempt allows twice as much (above). A figure request: sent once more, automatically, with twice the room (64,000, trimmed to the model's maximum), within your real limits ($2 and $5, not the estimate shown). If that can't be sent or is cut off again, its figures go to a person and are listed on the review page. This second send can take the bill past the Max Estimated Cost shown, and the cost line then says so: "AI Cost: $3.40 ($2.90 + $0.50 to retry an answer that was cut off) · Max Estimated Cost: $3.13, not including the retry". Money spent by previous attempts in the folder is shown the same way.
- **A retry may go past the batch limit.** The batch limit is checked before anything is sent. A figure request's retry isn't checked against it during the run, because books run side by side with no shared reservation. Getting past the limit would need bills near 100% of their ceilings plus a retry; real bills average about 40% of the ceiling.
- **A batch over its limit is refused before anything is sent.** The limit counts what the batch has already spent (every PDF's folder, whatever its state, and PDFs moved to the Trash) plus the Max Estimated Cost of the PDFs still to send.

**For developers, terminal only:** `MAX_TOKENS=` and `FIGURE_MAX_TOKENS=` set a request's output room for one run, and can go below the normal value. `MAX_TOKENS=` beats the doubling after a cut-off. Both stay held to the dollar limits, and the app never passes them. The app passes `FIGURE_RETRY_MAX_USD` and `FIGURE_RETRY_BOOK_MAX_USD`, the real limits for a figure request's doubled retry; in the terminal these default to `MAX_USD` and `BOOK_MAX_USD`.
