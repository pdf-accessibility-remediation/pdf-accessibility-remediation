---
title: Options
nav_order: 4
---

# Options

| Before the command | Effect |
|---|---|
| `AUTO=1` | No y/N question: sends straight away. For a Claude model only if the estimate is within the $2 cap and your credit; for any other model the estimate is approximate and not capped (the line printed before sending says which) |
| `ESTIMATE=1` | Audit and cost estimate only; a later run with the same label reuses the audit |
| `REPLY=path/to/reply.txt` | Reuses a saved Claude reply instead of calling the API (no cost) |
| `REVIEW=1` | Stops after the AI's decisions so a person can approve, change or reject each one before anything is applied; rerunning the same label (without it) applies the reviewed work order. One book at a time, not in batches (see [Reviewing the work order](review-step.md)) |
| `KEEP=1` | Keeps the working files (digest, figure crops, raw reply, logs) |
| `OUT=name.pdf` | Names the result (default: `<original name>_remediated.pdf`) |
| `MODEL=openai/gpt-5` | Any OpenRouter model id for this run or batch (default: `DEFAULT_MODEL` in `decide.py`, `anthropic/claude-sonnet-5.5`) |
| `MAX_TOKENS=64000` | Output limit for the model's reply, reasoning included (default 48,000; Sonnet 5.5 allows up to 128,000 on OpenRouter). Raise it when a reply is cut off |
| `RUNS_DIR=/path` | Writes runs somewhere other than `PDFREM/runs/` |
| `ALLOW_PDF20=1` | Lets a PDF 2.0 book (or one with namespaced tags) through instead of stopping it. Only for building PDF 2.0 support; never on real work (see [Not supported yet: PDF 2.0](troubleshooting.md#not-supported-yet-pdf-20)) |
| `VERAPDF=off` | Runs without veraPDF; review.md says its rows were not run. `VERAPDF=/path/to/verapdf` uses a launcher not on `PATH`; `VERAPDF_TIMEOUT` (seconds, default 900) limits each veraPDF run |
| `FORCE_OCR=1` | Intake: when the text-layer test says a book's text layer is unusable, OCR every page anyway (page images + new invisible OCR text; the old text is replaced). Without it such a book stops, flagged for a person. **Unverified:** in testing, force OCR stopped at its own after-OCR check on every page (see [Intake](intake.md)) |
| `OCR_LANG=jpn+eng` | Intake: Tesseract languages. By default: `eng`, plus `jpn` when kana are found and `kor` for hangul; Chinese characters with no kana are never guessed as Chinese or Japanese, so set this for them (e.g. `chi_tra+eng`) |
| `OCR=off` | Intake: no OCR; image-only pages are listed as having no text |
| `INTAKE=off` | No intake step at all (an untagged book then goes to the audit as it is) |
| `JOBS=1` | Batches only: books run at the same time (default 3). Use 1 after a rate limit (see [When the model call fails](troubleshooting.md#when-the-model-call-fails)) |

A run label that already holds a finished run is refused, so earlier results are never overwritten.

**If a run stops partway, rerun the same command** (same label). It picks up where it stopped:

- the audit is reused
- a reply that was **cut off** at the output limit is logged with its cost (it ends up in `record.json` under `earlier_attempts`, and in the cost line of `review.md`), then a new call is made. Add `MAX_TOKENS=32000` so it doesn't happen again
- a reply that was complete, where a later step failed, is reused at no cost
- a reply that was complete but could not be read as a work order is read again first, at no cost (useful after a pipeline fix). Only if it still can't be read is its cost logged and a new call made

The output limit: change the default once in `decide.py` (the line `ap.add_argument('--max-tokens', type=int, default=48000)`), or per run with `MAX_TOKENS=`. Doubling it to 32,000 raises the worst-case estimate by about $0.16 per book with Sonnet; you only pay for what is used.
