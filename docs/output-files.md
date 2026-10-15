---
title: Output files
nav_order: 7
---

# What a run leaves in `PDFREM/runs/<name>/<run-label>/`

| File | For | What it is |
|---|---|---|
| `<original>_remediated.pdf` | everyone | The result. Run PAC 2026 on this (named by `OUT` or the book list if you set one) |
| `review.md` | the human reviewer | Automated checks (including exactly one H1, bookmarks present, every decision applied, nothing deferred: a green row is evidence, not proof); every alt text the AI wrote (before and after) and the ones it left alone; heading levels and spoken heading text; what was hidden as decoration; reading-order moves; what the AI and the executor deferred; anything not applied |
| `record.json` | the archive | Everything vital in one file: source fingerprint, model, prompt version, tokens, cost, the full work order, what was applied, rejected and deferred, the verification results, and Claude's raw reply. `apply.py` accepts it in place of a work order, to re-apply a run |
| (review) | the archive | Runs with `REVIEW=1` only: `record.json` adds `review.workorder` (who reviewed the work order, when, and every change from the AI's version) and `workorder_ai` (the AI's version, when it was changed); `review.md` adds a checks row and a "Work order reviewed by a person" section. See [Reviewing the work order](review-step.md) |
| `han_review.csv` | a Japanese / Chinese reader | Only when the book has Han-only CJK runs: one row per run, with a blank decision column |
| `_intake/intake.json` | the archive | Untagged originals only: what intake measured and did (page triage, text-layer test scores, OCR language, OCR pages, tool versions, every check). Also in `record.json` under `intake` |
| `_intake/intake.md` | a person | Untagged originals only: the intake record in plain words (status, pages OCR'd, picture pages, CHECKs and notes with their pages, the OCR review verdict). Written for every outcome, also by `intake.py <pdf> <dir>` on its own and by `--plan-only` |
| `_intake/intake.pdf` | the pipeline | Untagged originals only, when intake changed anything: the OCR'd and auto-tagged copy the rest of the run worked on. Kept so `FROM=` reruns apply saved replies to the very same file |

Nothing else is kept. The working files (digest, figure crops, raw request and response, logs, and with `REVIEW=1` the review's page images and files) are deleted once the report is written, because they are rebuilt from the original in under a minute and the crops are copies of book pages. A run that fails partway keeps its working files, so the failure can be diagnosed.
