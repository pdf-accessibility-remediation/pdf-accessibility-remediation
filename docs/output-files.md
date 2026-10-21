---
title: Output files
nav_order: 7
---

# What a run leaves in `PDFREM/runs/<name>/<run-label>/`

| File | For | What it is |
|---|---|---|
| `<original>_remediated.pdf` | everyone | The result. Run PAC 2026 on this (named by `OUT` or the book list if you set one) |
| `review.md` | the human reviewer | Automated checks (including exactly one H1, bookmarks present, every decision applied, nothing deferred: a green row is evidence, not proof); every alt text the AI wrote (before and after) and the ones it left alone; heading levels and spoken heading text; what was hidden as decoration; reading-order moves; what the AI and the executor deferred; anything not applied |
| `review.html` | the human reviewer | The main view for people, beside `review.md` (the record, which links to it). "Ready to ship?"; four status cards (safety, with its five checks in a fold that opens, failed check first, when one fails; needs a person; AI decisions; veraPDF before → after); a folded "Run details" (result file, intake, libraries, time); what needs a person, every description in full, with its source and pages and a "Details" link that opens the folded section at that very item (without JavaScript it lands on the section); counts as bars with a table of the same numbers under each (a chart with only one bar is left out, its table stays); a strip of the book's pages (one cell per page, shaded by its most serious issue; one Tab stop, arrow keys move, the page's issues are read out) and the same as a plain list; and every section of review.md, collapsible. It reports WCAG only: veraPDF's PDF/UA-only rules, which review.md keeps as the record, are left out. One offline file: no internet, no external scripts; it reads in full without JavaScript. It quotes book text, like review.md, so it stays under `runs/` |
| `record.json` | the archive | Everything vital in one file: source fingerprint, model, prompt version, tokens, cost, the full work order, what was applied, rejected and deferred, the verification results, and Claude's raw reply. `apply.py` accepts it in place of a work order, to re-apply a run |
| (review) | the archive | Runs with `REVIEW=1` only: `record.json` adds `review.workorder` (who reviewed the work order, when, and every change from the AI's version) and `workorder_ai` (the AI's version, when it was changed); `review.md` adds a checks row and a "Work order reviewed by a person" section. See [Reviewing the work order](review-step.md) |
| `han_review.csv` | a Japanese / Chinese reader | Only when the book has Han-only CJK runs: one row per run, with a blank decision column |
| `_intake/intake.json` | the archive | Untagged originals only: what intake measured and did (page triage, text-layer test scores, OCR language, OCR pages, tool versions, every check). Also in `record.json` under `intake` |
| `_intake/intake.md` | a person | Untagged originals only: the intake record in plain words (status, pages OCR'd, picture pages, CHECKs and notes with their pages, the OCR review verdict). Written for every outcome, also by `intake.py <pdf> <dir>` on its own and by `--plan-only` |
| `_intake/intake.pdf` | the pipeline | Untagged originals only, when intake changed anything: the OCR'd and auto-tagged copy the rest of the run worked on. Kept so `FROM=` reruns apply saved replies to the very same file |

A batch folder also holds `summary.md` and `summary.html`: one row per book (ready to ship, needs a person, AI decisions, safety, veraPDF WCAG rules before → after, cost, pages), sorted with the most work first and sortable by any column; each book's name opens its `review.html`. To rebuild the dashboards of a finished run or batch: `python3 report_html.py <run>` or `python3 report_html.py --summary <batch>`.

## "At a glance"

`review.md` opens with an "At a glance" block, and `_intake/intake.md` with its own. Their numbers are computed once (`lib/glance.py`; for intake, `intake.py`) and kept in `record.json` as `glance` (intake's in `intake.json`, and so in `record.json` under `intake`), so review.md, review.html and summary.html always agree.

- **Ready to ship?** Yes only when the work order was approved on the review page (`REVIEW=1`; see [Sign-off](review-step.md#sign-off-when-a-book-is-ready-to-ship)), the OCR text was approved when intake added OCR text, and the safety checks are OK. "Manual check (PAC)" is listed for information: PAC 2026 is the final manual check after it. A book whose text layer is the publisher's own OCR shows "not needed", with a pointer to the review.md section about it.
- **Safety checks:** pages look the same, text unchanged, all content tagged or decoration, the tag-tree index points into the tree, every font readable. "OK ✔" or "FAILED ✘", never colour alone.
- **Needs a person** = the AI's deferrals + the executor's deferrals (counted by kind and page: 13 captions on 4 pages count 4; all Han-only runs count 1) + CHECK rows, leaving out "Nothing deferred by the executor", which only points at that list. One item can be counted twice when a CHECK row and a deferral describe the same failure (e.g. veraPDF 7.1-3 and the AI's deferral about it).
- **AI decisions:** every entry in the work order (deferrals and the note to the reviewer are not decisions); "approved by NAME on DATE" once the review page has approved it.
- **Fixed automatically (no AI):** the executor's own fixes, by kind (links tied and described, note IDs, tag-tree index entries, standard tags un-remapped, empty tags, decorative lines, tab order, font maps, …), with no total: several touch the same link.
- **Top issues:** safety failures first, then the ship conditions (OCR text, the review), CHECK rows, the executor's deferrals and the AI's; review.md shows five and "… and N more", the dashboard all of them. Each points to its review.md section.
- **intake.md:** the result, what needs a person, the OCR verdict, and "Is the existing text trustworthy?": how many sample pages were read by OCR and compared with the PDF's own text, the typical (median) match, the best and worst pages, and the pages over 5% and 15%, with how to read the numbers.

`review_ocr.py` refreshes all of it (review.md's block, `record.json` and review.html) when it records a verdict, since "Ready to ship?" depends on it.

Nothing else is kept. The working files (digest, figure crops, raw request and response, logs, and with `REVIEW=1` the review's page images, OCR word crops and files) are deleted once the report is written, because they are rebuilt from the original in under a minute and the crops are copies of book pages. A run that fails partway keeps its working files, so the failure can be diagnosed.
