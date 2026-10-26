---
title: Files
nav_order: 13
---

# Files

The pipeline lives in `pipeline/`; paths below are relative to it, apart from `prompts/`. Run the scripts from `pipeline/`. Modules in `lib/` are only imported by them.

## Pipeline steps

| File | Role |
|---|---|
| `run_api.sh` | Runs the steps below for one book, in one command |
| `batch_api.sh` | Several books in parallel, with a batch cost gate and a summary (needs `AUTO=1`) |
| `intake.py` | Untagged originals only (a placeholder tag tree with no text structure counts as untagged): page triage, text-layer test, OCR (OCRmyPDF + Tesseract) and auto-tagging (OpenDataLoader), with checks after each step. Local, no model. `--plan-only` shows what it would do without changing anything |
| `audit.py` | Original → digest (styles, listed elements, figures with crops, page map, reading order, front matter; in scanned books, suspect OCR words on word sheets; veraPDF's PDF/UA failures). No model. Positions are measured in the visible page area (CropBox): running-head bands (top 70 pt, bottom 60 pt), figure sizes and crops; a figure drawn only outside it gets no crop and is marked `outside_visible_area`. The whole texts the digest shortens (elements, first list items, first table rows), and the full reading order of the containers for the review page, go to `fulltext.json` beside it, for review.md and review.html only: never sent to the model, deleted with the other working files once `record.json` holds them |
| `decide.py` | The API call. Estimates cost, checks available credit, sends the digest and crops, parses and validates the reply. `--dry-run`, `--response-file`, `--check-key`, `--credit` (credit left), `--max-images` (default 100), `--max-tokens` (default 48,000, or 16,000 plus 45 per OCR word form sent when that is more; the model's reasoning counts against it) |
| `apply.py` | The executor. Original + work order → `<original>_remediated.pdf`. pikepdf only; checks each target first and rejects what doesn't fit |
| `verify.py` | Checks the result against the original, adds the WCAG checks veraPDF does not make, and runs veraPDF on the result |
| `report.py` | Writes `review.md` (with its "Overview"), `record.json` (with `glance`), `han_review.csv` and `review.html`, then removes the working files |
| `report_html.py` | The offline dashboards: `review.html` for a run (`report.py` runs it) and, with `--summary <batch>`, `summary.html` for a batch (`batch_api.sh` runs it). Also rebuilds them for any finished run. See [Output files](output-files.md) |
| `vera.py` | Runs veraPDF with the pinned WCAG 2.2 machine profile (which includes the PDF/UA-1 rules) and condenses its report to one entry per failed rule: WCAG or PDF/UA-only, and who can fix it (and, for the AI, the work-order key). `--check`; or `vera.py FILE.pdf OUT.json` on its own |

## Review and tools

| File | Role |
|---|---|
| `review_workorder.py` | The review step (`REVIEW=1`): `--prepare --pdf FILE` (run by `run_api.sh`: review items and page images), `--serve` (the review page on localhost), or `--reviewer NAME` after editing `workorder.json` by hand. Writes `review.json` and the reviewed `workorder.json`. See [Reviewing the work order](review-step.md) |
| `review/` | The review step's code: `core.py` (items, priority groups, decisions, diff, record; no web code), `server.py` (standard-library web server on 127.0.0.1), `page.html` (the page; no external libraries), `palette.css` (the dashboards' colours, light and dark, copied from `page.html`; `report_html.py` inlines it; keep the two in step) |
| `review_ocr.py` | Records a person's verdict on a book's OCR text (checklist rule 2): `python3 review_ocr.py <run>/<book> --verdict approved\|"not approved" --reviewer NAME --reason TEXT [--pages 381-386] [--date YYYY-MM-DD]`. Writes `_intake/intake.json`, `record.json` and the review.md row, and refreshes "Overview" and `review.html`; the row is OK only on "approved"; FROM= reruns carry the verdict. The review page's planned OCR section will write the same record |
| `scan.py` | Fast read-only checks on a folder of PDFs (no OCR, no model): tagged, placeholder tag tree or untagged, MarkInfo, producer, page triage (pages whose text draws no character counted by their images), private-use characters, text outside the visible page area and word breaks, per book (`books/*.json`) and in `summary.md`: `python3 scan.py <folder> <out_dir>` |
| `tools/compare_runs.py` | Are two runs' `review.md` files the same, book by book? `python3 tools/compare_runs.py <label-a> <label-b>` (a batch folder under `runs/batches/`, or a prefix naming several: `s1` → `s1-g1`, `s1-g2`, …). Byte for byte, leaving out only the two lines that change on every run ("Time:" and the run-start line); one line per book and a total; exit code 1 when any book differs. The acceptance test when `review.md`'s writing code changes: rerun the same books with `FROM=` before and after, then compare. See [Batch runs](batch-runs.md) |
| `tools/intake_cases.py` | Synthetic test PDFs (no book content) for intake's classification: an empty text object over a scan, an OCR layer, a text page, placeholder and real tag trees (MarkInfo missing/false/true, Figure-only with alt), Japanese, vertical Japanese and Korean scans with and without `OCR_LANG`. `python3 tools/intake_cases.py <out_dir> [--full]` runs `intake.py --plan-only` on each and prints PASS/FAIL per case (SKIP for the CJK cases when no CJK font is installed; `INTAKE_CASES_FONT` names one) and a summary line; `--full` also runs the whole intake on the two placeholder-tree cases. Local, no model |
| `tools/regression.py` | The regression test: reruns the baseline books (`tests/baseline/`) from their saved replies (no API call) and compares `record.json` fields and `review.md` with the baseline, plus checks that must always hold. `--update --reason "…"` writes a new baseline; `--seed RUNS_BATCH_DIR` copies the replies after a prompt change. See [Testing](testing.md) |
| `tests/` | The unit tests (`python -m pytest tests -q`) and `tests/baseline/` (the regression baseline: per book a saved reply, `review.md` and `expect.json`; `meta.json`; `UPDATES.md`, why each update was made). See [Testing](testing.md) |
| `requirements-dev.txt` | `requirements.txt` plus pytest, pinned: `pip install -r requirements-dev.txt` to run the tests |

## Shared helpers (`lib/`)

| File | Role |
|---|---|
| `lib/workorder_check.py` | The checks every work order goes through before `apply.py`: used by `decide.py` on the model's reply and by `review_workorder.py` on a reviewed order |
| `lib/support.py` | Says whether the pipeline supports a PDF: PDF 2.0 and namespaced tags are not supported yet. `intake.py` stops such a book for a person; `audit.py` and `apply.py` check again; `scan.py` reports it |
| `lib/gaptext.py` | Text as a reader hears it: a space where the PDF has a gap but no space character (over 0.10 em and 2.5 × the line's typical gap; not where another tag's glyph fills the gap). Used for the digest and review.md, and for matching text rules; never changes the PDF |
| `lib/listrule.py` | The one-item list rule, shared by `audit.py` (marks the lists in the digest) and `apply.py` (applies it) |
| `lib/readorder.py` | The reading-order rules: which tags count as sections, which sections are read away from their printed place (`verify.py` and the review page), and the one `move_section` match `apply.py` uses and the review page previews. Also the digest's one-line form of a section |
| `lib/langtag.py` | Checks and tidies a BCP 47 language tag; used by `apply.py` (`/Lang` spelling) and `decide.py` (the work order's `document.lang`) |
| `lib/sections.py` | `review.md`'s content as data: `report.py` writes its lines as before, a line can carry a key, its pages and the parts only PDF/UA requires; `to_sections()` turns them into `record.json`'s `sections` and `render_md()` gives back `review.md` line for line. `review.html` leaves out the PDF/UA-only lines and parts by this field, not by matching phrases |
| `lib/glance.py` | The "Overview" numbers for a finished run (ready to ship, safety, needs a person, AI decisions, fixed automatically, veraPDF, top issues), from `record.json` and `review.md`; shared by `report.py`, `report_html.py` and `review_ocr.py` |
| `lib/plpages.py` | Reads each page once with pdfplumber and keeps only what `audit.py` and `apply.py` use: characters, image boxes, size and the visible area (CropBox) |
| `lib/plumb_fix.py` | Fix for pdfplumber's nested marked-content bug (required; imported before pdfplumber reads a page) |

## Prompt and veraPDF data

| File | Role |
|---|---|
| `prompts/workorder_v8.md` | The system prompt: rules and the work-order format. Its hash is recorded in every run. v8 adds `tables` (header rows and columns of a real table), lets `rolemap` map a style the source never mapped, tells the model the work-order key and tags for each `pdfua_check` rule, and requires every such rule to be fixed or deferred by name (step 9). v7 changes the ActualText wording (spoken text only where printed glyphs read wrongly; equal to the print apart from spacing, case and line-end hyphens; merges join a label and its title) and adds `ocr_words` (the printed spelling of misread OCR words in scanned books, read from word sheets) and `pdfua_check` (the veraPDF failures the model can act on). v7 and older are kept as a record |
| `verapdf/` | `WCAG-2-2-Machine.xml` (the pinned profile), `rules.json` (each rule's WCAG success criteria, or why it is PDF/UA-only), `install.sh` |

**Figure images** are sent as JPEG (long side 800 px). If a book's images together pass 20 MB they are made smaller step by step, because OpenRouter refuses requests with more than 30 MB of images (HTTP 413). At most 100 images go in one request (Anthropic's limit). In a book with more figures, the alt text for the rest goes to a person, listed in the review under the AI's deferrals. What was sent is recorded in `record.json` under `run.images`. In the sample books, *dwellings* sent 100 of 543 figures and *dakine* 100 of 113.
- **The cut follows book order, not importance.** Figures go in the order the digest lists them, with whole-page figures (maps, plates) after all of them, so in a long book the cut falls on late figures and page figures first.
- **The model still sees a figure that was cut, but only as text**: its page, size and the text near it. Any alt text it writes for one is dropped as written unseen. It can still mark one as decoration, which hides the figure from screen readers on the strength of that text alone, so check those decisions in the review.
- **OCR word sheets share the 100 slots,** after the figures (see [OCR words](ocr-words.md)).
- **With `REVIEW=1`,** every figure left without alt text is listed as a gap at Finish, and the reviewer can write the alt text on the review page (see [Reviewing the work order](review-step.md)).
