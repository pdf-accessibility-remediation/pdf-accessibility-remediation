---
title: The accessibility evaluation
parent: Accessibility evaluation and release
grand_parent: Review and ship
nav_order: 1
---

# The accessibility evaluation

Before a remediated PDF ships, a person evaluates it with PAC 2026 and a screen reader and records what they found. This page explains that evaluation, the Accessibility Evaluation page in the app, and how "Ready to ship?" is answered. Internals are at the end, under [For developers](#for-developers).

## The accessibility evaluation

A PDF is ready to ship only after a person has evaluated it by hand (#38). It follows the sponsor's rule that a person reviews AI output before it ships. The evaluation has two parts, recorded for each version of the PDF:

- **PAC 2026:** PAC 2026's WCAG check, plus a few checks that need eyes.
- **The Screen-Reader Test:** a person listens to the PDF with a screen reader.

It is a staff check against a checklist, not yet a task test with real screen-reader users.

**The evaluation is a report, not a gate on its results** (decided 2026-10-31). Both parts must be recorded for the version before it is Ready. A Fail never blocks: it needs a note, and it is counted as an issue noted in the status ("Ready · 2 issues noted"). It is kept in the report and, once shipped, in the shipped folder, for a reviewer to fix later. The evaluation is a record of what a person found, not a legal certification.

Both parts are recorded on the app's **Accessibility Evaluation** page (below), or from the terminal with `manual_checks.py`. Any version can be downloaded at any time, ready or not (see [Downloads](shipping.md#downloads)). A Ready version is marked as shipped from the run page (see [Mark as Shipped](shipping.md#mark-as-shipped)), which keeps a copy of it with its report.

## The Accessibility Evaluation page (in the app)

**Opening it.** The run page has a strip right after "Ready to Ship?", headed **Accessibility Evaluation (PAC 2026 & Screen-Reader Test)**. It has a **Complete Evaluation** button, "Mark as Shipped" when it is offered, and "Available Downloads". The card above it says each requirement, so the strip has no line per part, and does not repeat "This version is not ready to ship".

The strip also says, in plain words:
- the status as it is now, when the report's card was written before a change (a session opened after shipping, or a session finished but not applied)
- that a version was already shipped
- when the PDF has changed since its report was made. While the PDF on disk is not the one the report describes (a Ready PDF's or a shipped one's), the app drops the card's green border on the run page. review.html opened as a file keeps it until it is next rebuilt.

When the run has no "Ready to Ship?" card, the strip goes at the end of the panel.

### The page

The page (`/run/<run>/checks`) has the same heading as the strip. It names the PDF as "PDF Title": the remediated PDF's own title, else the original's name without ".pdf". Right after "Back to the Run Page" come, as consecutive lines with no gap:
- the **Overall Status**, with the unsatisfied requirements when it is Not Ready: "Overall Status: Not Ready · Unsatisfied Requirements: Work Order Approval, OCR Text Approval"
- the version the results are for: "the version from Session 6, applied on October 30, 2026, at 2:02 PM"
- two help lines: when to complete the evaluation, and 'Every item needs a result, and a "Fail" needs a note. A "Fail" does not hold the book back; it is kept in the report with its note for future reference and further review.'

### Filling in a part

Each part is a section headed "PAC 2026" or "Screen-Reader Test". It holds a form:
- **Checked By:** empty at first. No name is ever filled in for you, here or in the run page's dialogs, not even from an unfinished draft.
- the part's fields
- one group per item, with **Pass** / **Fail** / **Not Applicable** (PAC's WCAG check: Pass or Fail) and **Notes**
- **Pages Checked**, optional

A note becomes required when the choice asks for one (see [The rules for each item](#the-rules-for-each-item)). When the pipeline found something, the hint says so ("This book has 12 tables"). When it found none, the hint says that too: 'No formulas were found in this book, so this check may be marked "Not Applicable."' The same goes for figures, tables, links and lists, and 'No pages in this book have text from character recognition (OCR), …'. The help lines keep the WCAG numbers, as PAC's report shows them.

**Saving is automatic,** as on the review page: about a second after each change, one save at a time, with the browser keeping a copy. "All changes saved" / "Saving…" sits beside the Record button, and is not announced. A failed save is announced (not when the page is leaving after a Record). A draft older than the one saved is never written over it, for example from a second tab.

**A draft never keeps "Checked By"**, on the server or in the browser: it carries no name to the next person. A draft saved before 2026-11-01 has its name dropped when it loads.

**A draft started on a previous version** is not used as answers. **Start from These Notes** copies its versions, pages and notes, never its results or "Checked By", as it does for previous results.

### Recording

**Record the PAC 2026 Results / Record the Screen-Reader Test Results** sends the answers to the same code `manual_checks.py` uses. Problems come back from that code, each shown under its field and in a summary that takes focus; nothing is recorded while one remains.

Recording clears the section's draft, so the answers never come back as a draft. The page stays, with a message (a green left border) saying what changed and what is still needed. With a Fail, it adds "1 issue noted: it is kept in the report for future reference and further review." There is no **Review Again** here: it stays on the run page.

- **The results tables** never scroll sideways: Notes wrap, and the Item column keeps its words together.
- **Previous results** are under **Previous Results (N)**, folded and read-only.
- **Refused** while a new version is being made, the PDF has changed, the PDF on disk is not the one the last review produced, or another change is being saved (a page waits at most 5 s). The message says why, before anything is filled in, and drafts are still saved.
- **An hour-long screen-reader test never holds the run's job slot:** these writes are made in the app's own process, not as a job.

### From the terminal

```bash
cd pipeline
python3 manual_checks.py ../runs/teika/rv1 --show                        # status, "Ready to ship?", the version, every result
python3 manual_checks.py --template pac > pac.json                       # empty results to fill in
python3 manual_checks.py ../runs/teika/rv1 --record pac pac.json         # record it (screen-reader: --record screen-reader FILE)
python3 manual_checks.py ../runs/teika/rv1 --refresh                     # recompute the Overview and review.html (no PDF touched)
```

`--for-sha SHA` records only when the PDF on disk still has that sha256: the version you checked. `--show` prints it.

## What each part asks

Each item is **Pass**, **Fail** or **Not Applicable**, with notes. The list is defined once, in `lib/release.py` (`CHECKLIST`); review.md's "Accessibility Evaluation" section and the app read it from there.

| PAC 2026 | |
|---|---|
| PAC 2026: WCAG Check | Pass or Fail only |
| Title and Language | |
| Spot-Check of Pages | **Pages Checked** (optional: `5, 9-12`) |
| Color Alone (1.4.1), Contrast (1.4.3), Images of Text (1.4.5) | |
| What Needs a Person | every item the report lists was looked at; a Pass turns the dashboard's "Needs a Person" card green ("Considered during the evaluation") |

| Screen-Reader Test | |
|---|---|
| Screen Reader and Version (required), PDF Reader and Version (optional) | |
| Title Announced; Document Language and Passages in Other Languages; Heading Navigation | |
| Reading Order on Sample Pages | **Pages Checked** (optional) |
| Figure Alt Text; Tables Read with Their Headers; Links Say Where They Go; Lists; OCR Pages Read Sensibly; Formulas | |
| Other Notes (optional) | |

**Retired items (2026-10-31):** PAC 2026's PDF/UA check and the PAC Version field are no longer asked. Older records that hold them still load. They are never counted (not toward completeness, not as an issue), and are shown only in that record's full results, labelled "(no longer asked)" (`RETIRED` in `lib/release.py`).

### The rules for each item

- **A Fail needs a note.**
- **Not Applicable needs a note when the pipeline found the thing:** figures, tables, links, lists or formulas in the tag tree, or OCR text on some pages, read from `record.json`.
- **A Pass needs a note when the same item failed** in the latest results of the same file, so a Fail is never overturned without a reason.
- **Text limits:** names and fields at most 80 characters, item notes 1,000, Other Notes 4,000. Control characters and direction overrides are removed, and `|` and `](` are refused, as on the OCR form.

## Each check belongs to one file

**Every check records the sha256 of the remediated PDF it was made on.** A check counts only for the file with that hash: the hash shown, the hash on disk and the hash in `record.json` (`document.output_sha256`) must be the same. Nothing relies on an apply making new bytes.

**In practice, any new apply makes the checks out of date.** A re-apply gives a new file: pikepdf writes a new `/ID` on each save, and the `/ID` follows the clock. So do the PAC check after the last review is applied. An OCR verdict does not change the PDF, so it does not make checks out of date.

**A check is refused,** and nothing is written, when:
- the PDF on disk is not the one `record.json` describes
- the PDF changed since the version was shown (`--for-sha`)
- a new version is being made (see [When a new version is being made](#when-a-new-version-is-being-made))
- the record is out of step with the review sessions: an applied session is newer than the session record.json names. No apply leaves this behind; the check is refused rather than filed under the wrong version.

**A PDF edited by hand is evaluated in its own run.** Edit an exported copy and bring it back with `handedit.py import`: it becomes a new run with its own `output_sha256` (see [Editing the PDF by hand](hand-edits.md)). The run it came from keeps its checks, which still count for its own file.

**Offline dashboards** (`review.html` opened as a file, `summary.html`) compare the checks with `document.output_sha256` only. They never hash the PDF.

## "Ready to ship?"

The card in review.html (and the run page that shows it) is headed "Ready to Ship?". Its status line carries the answer, and its four requirements follow, each with a check mark when satisfied. The words say it; the mark is hidden from screen readers.

```
Ready to Ship?
Status: Pending Evaluation
  ✓ Work Order Approval: Approved (Kim on October 31, 2026)
  ✓ OCR Text Approval: Not Applicable
  ✓ Safety Checks: Passed
  • Accessibility Evaluation: Not Completed
```

review.md's Overview writes the same lines, under `**Ready to ship?**` and the `**Status:**` line above it. A version is **Ready** when all four are satisfied:

1. **Work Order Approval:** the work order was approved on the review page. Otherwise "Not Approved", with why: applied without a review, decisions not reviewed, reviewed by hand edit, or a later session finished but not applied.
2. **OCR Text Approval:** the OCR text was approved, when it needs approval. It reads "Approved", "Not Approved", "Waiting for a Language Reader", "Not Reviewed", or "Not Applicable". Not Applicable means no OCR text was added and the PDF has no flagged OCR layer; a publisher's OCR layer that the test checked and did not flag is "Not Applicable" too.
3. **Safety Checks:** the five damage checks are OK: pages look the same, text unchanged, all content tagged or decoration, the tag-tree index points into the tree, every font readable. It reads "Passed", or "Failed (…)" naming them. A run made before some of these checks existed records fewer: "Not Checked (only 3 of the 5 checks were recorded for this run)", and the Safety card says "Not checked". Such a run is never Ready.
4. **Accessibility Evaluation:** both parts are completed for this version of the PDF. A part is completed when its latest results on that file have, for every item the checklist asks, one of that item's own choices. It reads "Completed", "Completed (2 issues noted)", "Not Completed" when neither part is recorded, or "Not Completed (…)" saying what is missing: "Not Completed (Screen-Reader Test not recorded)", a part recorded on a previous version, or one that could not be read in full.

### veraPDF is a finding, not a safety check

Since 2026-10-31, a WCAG rule newly failing or failing more often after the run, or veraPDF not run on both files, is listed first among the requirement items in "What Needs a Person". It comes from review.md's row "veraPDF: no rule newly failing or failing more often", counted once, as that CHECK row. The veraPDF card says "N newly failing" in orange, or "newly failing: not checked" when veraPDF did not run on both files.

A newly failing rule is often one that only became checkable after tagging, not damage. One earlier test book went from 9 failing rules to 2, with 7.18.1-1 new. A PDF/UA-only regression stays an ordinary check.

- **"Failing more often" counts failed checks.**
- **A different measure from the regression test's:** regression.py's own invariant compares the *total* number of WCAG rules failing (before and after), while the finding compares rule by rule, so the two can disagree.

## In the report

**review.md** ends with "## Accessibility Evaluation": how to do it, and the checklist. Once a result is recorded, each part's latest results are written in full: a summary line, who and the fields, the Item / Result / Notes table, and Other Notes as a quote. A person's text is escaped, so it reads as typed and no line of it can start a heading or a list.

The section is redrawn on every refresh once anything is recorded, and nothing else in review.md changes. A re-apply's review.md shows the run's previous results ("Completed on a previous version (Session 5) …").

**review.html** shows an "Accessibility Evaluation" section once anything is recorded (nothing before):
- one summary line per part: "PAC 2026: Completed by Kim on October 31, 2026 · 7 items · 1 issue noted"
- the failed items with their notes
- **View Full Results**, which opens the full results in the page's notes box: an accessible pop-up, where Escape and × close it and focus returns to the button. Without the script, and in print, the full results are shown in place.

While nothing is recorded, review.md's own section is drawn as a fold at the end (the instructions). Once something is, it is not, so nothing appears twice.

**The "Needs a Person" card** turns green once this version's PAC 2026 results mark "What Needs a Person" as Pass: "Considered during the evaluation (Kim, November 1, 2026)", with the name and date from that result. A Pass recorded on a previous version does not count. A Fail keeps it orange ("marked Fail in the evaluation …"). review.md's "Needs a person" line uses the same words in sentence case: "considered during the evaluation (…)" or "marked Fail in the evaluation (…)".

## The accessibility statement (dropped)

The pipeline writes no accessibility statement. Writing one is for the institution that adopts the pipeline, which knows its audience, where the statement goes and who answers for it. Who writes it, and where it goes, is still an open question for the sponsor.

Until then, a shipment's copy has the report (review.html, review.md), the evaluation's results and a read-me. The read-me keeps "Automated checks are evidence, not legal sign-off." and "The evaluation is a record of what a person found, not a legal certification." review.md keeps the second too.

Dropped with it: `lib/disclosure.py`, the statement files written at shipping, the ZIP's copy, review.html's "View the Accessibility Statement" link, the app's route that served it, and the dialog's "Where It Was Published (optional)".

A folder shipped before keeps its `accessibility-statement.*` or `disclosure.*` files on disk, untouched: they are no longer linked, served or zipped. An older review.html that still links one, or shows a shipment's "where:", is drawn without them by the app and in the ZIP (`lib/release.py` `no_statement`; the file on disk is unchanged). A shipment recorded with `where` keeps it in `shipped.json`, never shown.

## Older runs

A run made before 2026-11 keeps its review.md: its old headings and its old "Final check with PAC 2026" section, until something is recorded on it. The section is then replaced by "Accessibility Evaluation". Its Overview and review.html change when something is recorded on it, or with `--refresh`.

Its stored glance (schema `glance/0.3`) is never trusted for "Ready to ship?": it is never Ready until it is recomputed, and every dashboard recomputes it.

## For developers

### Names in the records

In the records and the code, the two parts are still "manual checks": `release/checks.json`, with keys `pac` and `screen_reader`. Drafts are saved in `release/drafts.json`. A draft that could not be cleared after a Record is logged in `runs/.app/server.log`; an auto-save handled after the Record is refused. `record.json`'s glance has `ready`, true exactly when the status is Ready.

### When the PDF is hashed

- From 2026-11, `report.py` hashes the PDF it reports on.
- A run made before that has no `output_sha256`. Its first recorded check takes the hash of the file on disk, marked `output_sha256_from: "first check, <date>"`. Where the current session's record (`reviews/sessions/NNN.json` `version.pdf_sha256`) names a hash, the two must be equal, or the check is refused.

### When a new version is being made

A new version is being made when any of these holds:
- a session newer than the current result is finished and not yet applied: what Apply applies. This covers the whole re-apply, and a failed one.
- `reviews/work/` exists: a re-apply under way
- `reviews/promoting.json` exists: a promotion that did not finish

A finished session that a later one replaced (its apply failed, then a new review was applied) never blocks. One rule, `review/sessions.py` `newer()`, decides this, the app's Apply offer and the "Newer version" line.

**A check whose refresh fails is taken back.** If rewriting the record after a check fails (for example an import error), `release/checks.json` is put back as it was and the error is raised. So a check never stands beside a record that lacks its hash.

### Fail closed

The first three requirements can be satisfied only on a stored glance of schema `glance/0.4` or `glance/0.5`, with all three lines and all five damage checks. Both schemas are written under every current rule; `glance/0.3` predates the rules for a flagged OCR layer, a finished but unapplied session, and the sent-to-a-reader verdict. A stored `glance/0.4`'s sixth check (veraPDF) is dropped on read, and its Safety line worked out again from the five.

### The records

```
release/checks.json     {schema: "manual-checks/1", pac: [check …], screen_reader: [check …]}   newest last, nothing deleted
                        check: {id, recorded, by, via, code, pdf: {sha256, file, session, which}, fields,
                                items: {key: {result: pass|fail|na (not_run: an older PDF/UA row), note}}, notes}
release/shipped.json    [{n, shipped, by, pdf: {sha256, …}, where, note, withdrawn?}]   (written from a later stage)
<run>/.record.lock      the record lock (below)
```

- **The latest results of a part on a file are the ones that count.** Earlier ones stay in the record.
- **`result` is what the person saw,** never rewritten. Only the reading changed on 2026-10-31.
- **`code`** is the git commit the writer ran on. An app started before a `git pull` writes with its old code until it is restarted, and this field shows which code that was.
- **Reads fail closed:** a missing item, an unknown result or an unknown item (retired ones are known) makes that part "could not be read in full: record it again", never completed. Its Fails still count as issues noted. An `accepted` key (reserved earlier for a "Fail, Accepted with a Note") is no longer needed, and is read by the result alone.
- **`record.json` keeps copies for the archive,** never read back for a decision: `manual_checks` (each part's latest results with their `state`, which is completed, could not be read, or earlier version, shown as "previous version"; and `issues`) and `release`.
- **The `release/` folder stays through every re-apply:** a promotion moves only the result files. A copied run folder carries it too, so a test copy of a checked (or, later, shipped) PDF says so, and holds what the original holds.

**A shipment** adds to `release/shipped.json` `{n, shipped (local time, to the second), by, note, pdf: {sha256, file, session}, folder, issues, checks}`. It is written under the record lock; the PDF is hashed while copied. If the folder can't be completed, `shipped.json` is restored. The gate is `webapp/manualpage.py` `ship_gate`, checked again under the lock. **Clean Up Space** goes through `review/prune.py`, hashes each PDF again under the locks, and records each removal (version, sha256, size, who, when) in `release/removed.json`.

### The record lock

Every writer of a finished run's `record.json`, `review.md`, `review.html` and `release/` holds `<run>/.record.lock` around its whole read-change-write (`lib/runlock.py`). The writers are: a manual check, an OCR verdict, `mark_pending`, and each stage of a promotion up to and including its re-mirror. The evaluation page takes it in the app's own process, with no job.

- **Waits:** a page's request waits at most 5 s ("Another change to this book is being saved. Try again in a moment."); the command line and jobs wait up to 120 s.
- **Not re-entrant:** no writer calls another, so taking it twice in one thread is a bug and raises.
- **The order:** `reviews/.lock` (never waits) → `_intake/.verdict.lock` → `.record.lock`, never the reverse. `runs/.app/dispatch.lock` is never held together with it.
- **A promotion** re-reads `release/` after it moves the new result in, then rewrites the Overview, review.html and the mirror, so a check recorded during a re-apply is not lost. It releases the lock before it rewrites the replaced version's own page. The locked refresh takes about 0.1 s on a 96 MB PDF (2026-10-31).
- **Readers take no lock;** every file is written whole (a temp file and a rename).
