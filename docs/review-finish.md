---
title: Draft PDF and sign-off
parent: Reviewing the work order
grand_parent: Review and ship
nav_order: 2
---

# Draft PDF, sign-off and limits

This page is for the end of a review: checking a draft of the PDF before finishing, when a PDF is ready to ship, what the report says about the review, and what the review page cannot do.

## Checking a draft PDF while you review

**Build a Draft PDF**, in the page's header next to **Finish Review**, makes a PDF from the choices you have made so far. You can check them in Adobe Acrobat or with a screen reader (NVDA, VoiceOver, PAC's screen reader preview), then carry on with the same review. The session stays open; nothing is recorded.

**What it builds:** the choices so far, through the same check as Finish, then the same executor. A choice the check doesn't accept is left out of the draft, so you can check everything else while a card still needs fixing; **Finish Review** waits until it is fixed or rejected (see [Checks as you go](review-page.md#checks-as-you-go)). Decisions not reviewed yet are built as the AI wrote them.

It takes about as long as the apply step: seconds for a short PDF, up to about 2 minutes for a long one. The page shows the time while it builds, and your changes are still saved as you make them. One draft is built at a time.

**After it is built:** a **Download the Draft PDF** link (the file is named after the PDF, with `_draft.pdf`), and a list of anything left out. Choices the check left out (additions too) have the same message as under their cards, with a link to each. Section moves or other steps the executor could not make say so in plain words; **Details** shows the executor's own reason, and the report after Finish explains it.

**Out of date:** a change to a decision or an addition after the build marks the draft "out of date". Build it again to check the change.

### Limits of the draft

- **It is for checking only.** It is not checked by veraPDF or the pixel and text checks, and it has no review record. It must not be shipped or handed out. Inside, it looks like a finished result to a screen reader: its title and tags are the ones Finish would make. A document property, **RemediationDraft** (Acrobat: File > Properties > Custom), says it is a draft.
- **Changes made to the draft in Acrobat are lost.** Finish builds the real result again from your choices. Fix the reading order by hand only on the remediated result (see [Fixing the reading order by hand](review-reading-order.md#fixing-the-reading-order-by-hand)).
- **The final result can still differ** from a draft you checked: a change made after the build, or a section move the executor refuses at Finish. Section moves are made in turn, each on the order the earlier ones leave, so changing one move can change what the next one finds.
- **Nothing is kept.** The draft is held in a temporary folder that is removed when the review page closes (Finish, Ctrl+C or **Stop Reviewing**). A folder left by a review page that was killed is removed the next time a review page starts. The run's report, its record and its earlier results are not touched. The copies you download stay in your Downloads folder: delete them when you are done, especially for PDFs that are not open source.
- **Where:** a first review (`REVIEW=1`), or a review opened again (`--reopen`, or **Review Again** in the app). Not on the OCR text review page.

## Sign-off: when a PDF is ready to ship

The review page is the sign-off on the AI's decisions: a person approves AI output before it ships. A PDF counts as ready to ship only when:

1. a reviewer has approved its work order on the review page
2. its OCR text is approved as well, if intake added OCR text, found the PDF's existing OCR layer doubtful, unusable or missing diacritics, or could not check it
3. the five safety checks are OK
4. both parts of the accessibility evaluation (PAC 2026 and the screen-reader test) are recorded for this version of the PDF (from 2026-11). A Fail in the evaluation never blocks: it is an issue noted.

See [Accessibility evaluation and release](release.md) for the evaluation and the PDF's status.

- **"Ready to ship?" always reflects the latest session:** a session finished but not applied makes it No until `--apply`.
- **The card** in review.html is headed "Ready to Ship?". Its first line is the PDF's status ("Status: Pending Evaluation"), which carries the answer. Its four requirements are "Work Order Approval", "OCR Text Approval", "Safety Checks" and "Accessibility Evaluation", each with its value, in the same words as review.md. Values include "Approved", "Not Approved (applied without a review)", "Not Approved (205 decisions not reviewed; reviewed by Kim on October 30, 2026)", "Not Applicable", "Passed", "Completed (2 issues noted)", "Not Completed" and "Not Completed (PAC 2026 not recorded)".
- A satisfied requirement shows a check mark in place of its bullet, both centred in one column, hidden from screen readers (the words say it). The decision tables' column is "Type".
- **The page's heading** names the PDF's own file ("Work Order Review · ilokano.pdf · 49 pages"), not `intake.pdf`, the intake copy the decisions were made on.
- **`REVIEW=1` is optional for now.** A PDF run without it is still processed and reported, but it is never shown as ready to ship. Once the pipeline is in official use, the review step becomes the standard workflow; the default has not changed yet.

## What the report says about the review

- **`review.md`** gets a row in the automated checks: "Work order reviewed by a person before it was applied". The row is a CHECK when decisions were accepted without review, an edit was dropped, or a gap was left open without a reason (a hand edit with no `--note`). It also gets a section listing each change (AI → reviewer), each open gap with its reason, and which session the result comes from.
- **`review.html`** has a "Review of the AI's Decisions" section. A run never reviewed shows its decision count by kind, all applied without review. A reviewed run shows:
  - one line for the current session: who, when, and how many decisions were approved, changed, rejected and accepted without review
  - its row of the session table, with the other sessions folded under **Previous Sessions (N)**
  - each decision's status (approved, changed, rejected, seen, accepted without review; "(inferred)" for a summary-only session's rebuilt choices), with the session that set it

The command that reopens the review is not on the page: it is the one in [Reviewing again](review-again.md#reviewing-again) (`--reopen`). Reports written before 2026-10-29 keep the earlier layout until their next apply.

## Limits

- **The priority list points at risky kinds of decisions, not at wrong ones.** A confident wrong decision outside those categories is only in **All**.
- **The AI rarely gives a `confidence`:** 2 items across nine books under prompt v8. Where it does, a value below 1 is marked on the card.
- **Lists can be long.** A PDF whose AI re-levels 50 headings has 50 cards in group 3.
- **Additions are limited to what the audit listed.** An element the digest does not list cannot be retyped on the page. Artifact rules and the remaining keys need a hand edit (see [Without the page](review-again.md#without-the-page)).
- **The gap check looks for what is missing, not for what is wrong.** An H1 on the wrong element, or poor alt text, is not a gap.
- **Page references in the AI's note are found by a pattern** ("PDF 4", "PDF 254–282"). A note that names pages some other way is listed under General.
- **The reading-order list compares where sections start.** A section that starts inside a longer one and is read after it is not flagged as out of place, because overlapping stories are normal in InDesign books; a small one read more than 5 pages late is marked quietly instead. Content outside any section is not listed: the page-jump list covers the order within each page.
- **Rule matches are judged on the original's runs.** A flagged story counts as removed only when it has at most 100 runs and every one matches a rule on its page. Rules and the captions decision are approved or rejected on the page, never edited there, so the page follows a rejection at once. A pattern edited by hand in `workorder.json` is not reflected in the panel.
- **A caption tie is a prediction:** `apply.py` can still refuse one (for example with several figures on the page), and review.md lists any section still read late after the changes.
- **At most 3 section moves per PDF.** A fourth section out of place gets a note on its card (and see [Fixing the reading order by hand](review-reading-order.md#fixing-the-reading-order-by-hand)). A run whose AI wrote one move (prompt v8) still gets up to 3 on the page. The order within a page cannot be changed by the pipeline at all.
- **The figure moves are worked out with the AI's decisions as written.** The trial run adds time at the first review stop (a later review reuses it while nothing has changed), and does not follow the changes you make on the page.
- **An edit the check refuses is not applied at all.** The AI's value is not used as a fallback. The Finish dialog says so, and lists what would be dropped with a link to each card, so the reviewer can fix the value or approve the AI's.

**Some decisions depend on others, and the Finish dialog's check does not know.** It runs the same checks as `decide.py`, but not the executor's own checks. Two cases were found in testing:
- Rejecting a heading **merge** makes the spoken text (ActualText) the AI wrote for those headings ("Chapter Two …") stop matching the print, so the executor refuses it too. In one earlier sample, rejecting its one merge removed 8 spoken-text entries.
- **Table header columns** are refused when any row has that many cells or fewer, such as a one-cell title row across the table.

Both show up after the run in `review.md` under "Decisions not applied"; nothing is half-applied. The cards for merges, spoken text and tables warn about this.
