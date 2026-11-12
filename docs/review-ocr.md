---
title: The OCR text
parent: Reviewing the work order
grand_parent: Review and ship
nav_order: 5
---

# The OCR text on the review page

When a PDF's text came from OCR, a reviewer approves that text, or not, on the review page. This page explains what the OCR Text section shows and how its verdict is recorded. Internals are at the end, under [For developers](#for-developers).

## The OCR text

A PDF whose OCR text needs a reviewer's approval has an **OCR Text** section on the review page, after **Session Notes**. That happens when intake added OCR text, or flagged the PDF's existing OCR layer (doubtful, unusable, missing diacritics, or not checked).

Approving it is part of "Ready to ship?", because a person must approve AI and OCR output before it ships. The text is shown as OCR read it, and is never edited on the page: the verdict approves or rejects the text as it is.

### What the section shows

**In plain words.** The section is for library staff, so it names no files, codes or tools. The opening lines say what intake did ("During intake, OCR added text to 6 pages, read as Chinese (Traditional) and English. PDF 1 is a picture with no text."), with the languages named from OCR_LANG as on the **I can read …** box. Or they say what the check of the PDF's own OCR text found. Examples in a finding follow "ex.".

**Each page listed** shows the page image next to its text, as it is in the PDF the run worked on. Pages listed are every page intake added OCR text to, or, for a flagged layer, the pages the layer test scored. Under each are intake's findings for that page:
- words read by OCR
- words and symbols that look like junk ("33 of 374 words and symbols look like junk (9%), ex. TC# ® * MR & #1")
- Chinese, Japanese or Korean characters, text set vertically, two printed pages on one PDF page
- for a flagged layer: how much of its text differs from a new OCR reading, letters with accent marks in each, and words a new OCR reading was sure of that are missing

For a flagged layer, **Show Another Page** shows any other page with the PDF's own OCR text.

**OCR words** on a page are listed with their reading, linked to their card: they are work-order decisions, approved there, not here. The audit keeps only the first 3 pages of each word form, so a page's list can be incomplete.

**The text's language** is marked for screen readers only when OCR_LANG names one language; otherwise the page says why it is not. It is never guessed.

### The verdict

**Current Verdict** heads the section, with **Previous Verdicts** folded right under it. A verdict keeps its choice's name: "Current Verdict: Approved by Kim on 2026-10-31 …", "Not Approved by …". The header's status line says "OCR Text: Approved".

The OCR verdict is not one of the decisions: it is not counted in "N of M reviewed", or in Finish's count of decisions not reviewed.

The choices:
- **Approved** passes this part of "Ready to ship?". For pages in a non-Latin script (CJK, kana or Hangul, or OCR_LANG naming such a language), it needs **I can read …** ticked. That is an ability, not "I have read"; the record keeps "reads …". The language comes from OCR_LANG, or from kana or Hangul, else "the language of these pages".
- **Not Approved** keeps it closed.
- **Sent to a Language Reader** keeps it closed, with an optional **Sent to** (a person or a team). "Ready to ship?" says "no (waiting for a language reader: …)", and What Needs a Person says "OCR text waiting for a language reader". The reader then records Approved or Not Approved.

**Reason** (needed for Approved and Not Approved) and **Pages** (optional, `381-386` or `5, 9-12`) are one line each. A `|` or `](` is refused, because they would break review.md's table or become a link in review.html. The page says each refusal in plain words ("The reason can't contain the character "|". Use another one, such as a comma or a slash.").

**Record Verdict** writes it at once, on its own, and the page stays open. The verdict goes to intake's record, and for a finished run to the report: review.md's "OCR text reviewed by a person" row and Overview, and review.html. Its date is the day it is recorded, not the day the page was opened. "Recorded: …" then says the verdict and the report's "OCR text approved" line.

During a first review (`REVIEW=1`, before the run is applied), only intake's record gets it; the report shows it after the apply. Discarding the session does not undo it.

In the section's grey helper lines, the names of buttons, choices and sections are in semi-bold, without quotes (elsewhere on the pages such names are in quotes). Each radio button is centred on its choice's name.

### Without a review session

`python3 review_ocr.py <run> --serve` opens the same section alone: the OCR-only page. Use it for runs that cannot be reviewed again, or to record a verdict without opening a session. The app's run page has **Review OCR Text** for it.

On this page, **Finish OCR Review** takes the place of Record Verdict. It records the verdict, closes the page and goes back to the run page, whose report already shows the verdict. From a terminal, the page says so and the terminal prints "closed". **Close Without a Verdict** closes it with none.

`review_ocr.py <run> --verdict … --reviewer …` (with `--reads`, `--to`) records a verdict from the terminal, through the same checks. `review_ocr.py` keeps its own wording for refusals, which names its options (`--reads`). `--date` is refused with `--serve`: a verdict on the page is dated the day it is recorded.

**Stopping:** Ctrl+C (or the app's Stop) while a verdict, an automatic save or a Finish is being written waits until it is written whole. A request that comes after that is refused ("The review page is closing"). A request that stalls (it sends no body) gives up after 30 seconds, so a stop never waits longer than that.

## For developers

### The OCR verdict record

OCR text verdicts are kept in one record, `intake.review.ocr_text_approved`, in `_intake/intake.json` and `record.json`. It holds:
- the verdict (`approved`, `not approved` or `sent to a language reader`), reviewer, date, reason and pages
- when given, `reads` (the languages the reviewer reads) and `to` (who it was sent to)
- `via` (`page` or `review_ocr.py`), `session` (the session open when it was recorded on the page) and `recorded`

The review page's **OCR Text** section writes it, and `review_ocr.py` writes the same record through the same code (see [Intake](intake.md)), via `review/ocr.py`. The latest verdict wins; earlier ones are kept under `history`.

Record Verdict writes `_intake/intake.json` (and intake.md), and for a finished run `record.json`. The OCR section's page images are read with pdfplumber. The OCR-only page's images go to a temporary folder, not the run, and a `reviews/` folder it had to make for its lock is removed when it closes.

**Only one writer at a time:** the page and `review_ocr.py` take the same lock on `_intake/`, so their writes never interleave. For a finished run, `review_ocr.py` is also refused while a review page of the run is open or an apply runs (`reviews/.lock`). During a first review (`REVIEW=1`, no `record.json` yet) only the `_intake/` lock applies.
