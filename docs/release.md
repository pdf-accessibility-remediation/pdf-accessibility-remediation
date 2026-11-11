---
title: Accessibility evaluation and release
nav_order: 3.7
---

# Accessibility evaluation, status and release

This page explains what has to happen before a remediated PDF ships: the accessibility evaluation a person records by hand, the PDF's status, and how a version is downloaded, marked as shipped, withdrawn or cleared. Internals are at the end, under [For developers](#for-developers).

## The accessibility evaluation

A PDF is ready to ship only after a person has evaluated it by hand (#38). It follows the sponsor's rule that a person reviews AI output before it ships. The evaluation has two parts, recorded for each version of the PDF:

- **PAC 2026:** PAC 2026's WCAG check, plus a few checks that need eyes.
- **The Screen-Reader Test:** a person listens to the PDF with a screen reader.

It is a staff check against a checklist, not yet a task test with real screen-reader users.

**The evaluation is a report, not a gate on its results** (decided 2026-10-31). Both parts must be recorded for the version before it is Ready. A Fail never blocks: it needs a note, and it is counted as an issue noted in the status ("Ready · 2 issues noted"). It is kept in the report and, once shipped, in the shipped folder, for a reviewer to fix later. The evaluation is a record of what a person found, not a legal certification.

Both parts are recorded on the app's **Accessibility Evaluation** page (below), or from the terminal with `manual_checks.py`. Any version can be downloaded at any time, ready or not (see [Downloads](#downloads)). A Ready version is marked as shipped from the run page (see [Mark as Shipped](#mark-as-shipped)), which keeps a copy of it with its report.

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

## The status

| Status | When |
|---|---|
| **Not Ready** | a requirement among the first three is unsatisfied |
| **Pending Evaluation** | those three are satisfied; the evaluation is not completed for this version |
| **Ready** | all four are satisfied |
| **Shipped** | a shipment exists that is not withdrawn; the status is about the shipped copy |

- **"· N issues noted"** follows any status whose version has Fails in its evaluation: "Pending Evaluation · 1 issue noted", "Ready · 2 issues noted", "Shipped · 2 issues noted". After a shipment they are the shipped file's.
- **A Shipped PDF** has Ready's green border on the card. summary.html counts the two apart: "Ready: N · Shipped: M · Pending Evaluation: P".
- **Withdrawal:** the status falls back to the latest shipment not withdrawn; with none, the statuses before shipping apply.
- **Where the status is shown:** review.md's Overview (`**Status:** …` above "**Ready to ship?**"), review.html's card, summary.html's Status column, and the evaluation page ("Overall Status") and the strip.

**After a shipment, a second line** says what comes next:
- "Newer version: Session 7 finished, not applied" (being applied, or its apply failed)
- else "Newer version: Session 7 being reviewed" (an open session, also while the shipped file is still the current one)
- else, when the current file is not the shipped one, that version's own status: "Newer version (Session 7): Pending Evaluation"

## In the report

**review.md** ends with "## Accessibility Evaluation": how to do it, and the checklist. Once a result is recorded, each part's latest results are written in full: a summary line, who and the fields, the Item / Result / Notes table, and Other Notes as a quote. A person's text is escaped, so it reads as typed and no line of it can start a heading or a list.

The section is redrawn on every refresh once anything is recorded, and nothing else in review.md changes. A re-apply's review.md shows the run's previous results ("Completed on a previous version (Session 5) …").

**review.html** shows an "Accessibility Evaluation" section once anything is recorded (nothing before):
- one summary line per part: "PAC 2026: Completed by Kim on October 31, 2026 · 7 items · 1 issue noted"
- the failed items with their notes
- **View Full Results**, which opens the full results in the page's notes box: an accessible pop-up, where Escape and × close it and focus returns to the button. Without the script, and in print, the full results are shown in place.

While nothing is recorded, review.md's own section is drawn as a fold at the end (the instructions). Once something is, it is not, so nothing appears twice.

**The "Needs a Person" card** turns green once this version's PAC 2026 results mark "What Needs a Person" as Pass: "Considered during the evaluation (Kim, November 1, 2026)", with the name and date from that result. A Pass recorded on a previous version does not count. A Fail keeps it orange ("marked Fail in the evaluation …"). review.md's "Needs a person" line uses the same words in sentence case: "considered during the evaluation (…)" or "marked Fail in the evaluation (…)".

## Downloads

Any version of the PDF can be downloaded at any time, ready or not, from **Available Downloads**. It is on the run page's strip (under "Complete Evaluation") and on the evaluation page, laid out the same on both:
- the heading, which is the list's label
- the list of versions
- the line saying how the chosen version's files are marked (the list's description)
- **Download the Remediated PDF** and **Download the Record (ZIP)**, in a row

**The list** holds the current version and each previous result whose PDF still exists. It decides which version the two buttons give. It never changes what the evaluation records: the evaluation is always for the current version.

The line under it says how the files are marked ('The downloaded files are marked "not ready."'), never their names. A shipped version has no line, because the line above the downloads and its own label already say it was shipped. On the evaluation page, a version that is not the current one adds "Results on this page are recorded for the current version only." to that line.

### File names

The PDF's bytes are never changed, only the name it is saved under:

| That version | PDF | ZIP |
|---|---|---|
| Not Ready or Pending Evaluation | `<book>_session-6_not-ready.pdf` | `<book>_record_session-6_not-ready.zip` |
| Ready | `<book>_session-6_not-shipped.pdf` | `<book>_record_session-6_not-shipped.zip` |
| Shipped (the shipped file) | `<book>.pdf` | `<book>_record_shipment-2.zip` |
| A withdrawn shipped copy | `<book>_shipment-1_withdrawn.pdf` | `<book>_record_shipment-1_withdrawn.zip` |
| A previous version | `<book>_session-5_previous-version.pdf` | `<book>_record_session-5_previous-version.zip` |
| No review | `<book>_no-review_not-ready.pdf` | `<book>_record_no-review_not-ready.zip` |

`<book>` is the remediated PDF's name without ".pdf", made safe for any computer (see [Download names](#download-names)). The session's number is used, never its name.

### The record ZIP

The record ZIP is for library staff. It holds one folder named as the ZIP, with only:
- the PDF, under its own name
- review.html: the report, with the evaluation's results in it
- han_review.csv, when the PDF has one (review.html sends staff to it). The read-me calls it "passages in Chinese or Japanese a person needs to check, as a spreadsheet".
- `READ-ME.txt`, in plain words (below)

It never holds review.md or `evaluation-results.json`: they stay in the run folder and in `release/shipped/NNN/`, which keep their full set. It never holds record.json either, because that holds the AI's raw reply.

The ZIP's review.html keeps only the links that work inside the ZIP. Its header's link to review.md is dropped, and any other link that would lead outside the ZIP (a previous result, a file of the run folder) is left as plain text. Links within the page and to the web stay. review.html on disk is unchanged.

**READ-ME.txt** gives:
- the title and "Source PDF: …" (the original PDF's name)
- the version, and its status. For a previous version it says "previous version", naming the current one.
- each shipment of that file ("Shipment 1, shipped on November 1, 2026 by Kim"; "Withdrawn on … by …: …" for a withdrawn one)
- the number of evaluation results recorded on it
- the run details of that version's own record (below)
- what each file is
- "automated checks are evidence, not legal sign-off" and "the evaluation is a record of what a person found, not a legal certification"

It gives no hash: a file's sha256 is in its record (`document.output_sha256`) and its shipped folder's READ-ME.txt. The run details read, for example:

```
Pages: 437
Remediated: October 26, 2026, at 6:48 AM
AI model: anthropic/claude-sonnet-5.5 · Instructions: workorder_v8
AI cost: $0.256, from the original AI request on October 26, 2026 · Cost per page: $0.0006
OCR and Auto-Tagging: 6 pages are pictures with no text, so no text was added for them; the PDF had no tags and was tagged automatically.
Total runtime: 3 min 52 s (intake 4 s, audit 37 s, AI request (a previous answer reused) 2 s, preparing the review 8 s, applying and checks 3 min 2 s); the review time is not counted.
Software: Python 3.13.9, pikepdf 10.5.1, pdfplumber 0.11.9, pypdfium2 5.7.1, Pillow 13.0.0, fontTools 4.62.1
```

- **The AI cost** is always the request's real cost: for a reused reply, the original request's. It reads "not recorded" only when none is kept anywhere. Any missing value reads "not recorded".
- **OCR and Auto-Tagging** says plainly what intake did, from OCR's own lists of pages: "1 page is a picture with no text, so no text was added for it", "…, so OCR added its text", "7 pages are pictures with no text: OCR added text to 6 of them, and no text was added for the other one", or "every page has text, so no OCR was needed".
- **Then the tags:** "the PDF had no tags and was tagged automatically", or "the PDF's tags held no text structure, so it was tagged again automatically". A tagged PDF, which intake skips, reads "not needed: the PDF was already tagged."; a record with no intake, "not recorded".
- **Total runtime** is the computer's time across the whole run, with its parts in parentheses: intake, audit, the AI call (named "a previous answer reused" for a reused reply: the time of reading it, not the original call's), preparing the review (a run stopped with `REVIEW=1`), and applying and checks. It ends "the review time is not counted". A part with no time kept reads "not recorded", and the total then says "at least".

A version applied from a later review carries the run's steps before the review from the record it replaces, and adds its own applying and checks. A `REVIEW=1` run applied before 2026-11-01 kept only the apply's steps.

### When a download is refused

A download is refused while a new version is being put in place and did not finish, or when the PDF on disk is not the one the report describes. A re-apply under way, or a finished session not yet applied, does not stop a download.

"Which Version Is This File?" (a PDF hashed in the browser and named as a version) was removed from the evaluation page.

## Mark as Shipped

"Mark as Shipped" records that a person published this version elsewhere, for example in ScholarSpace. The app publishes nothing.

**It is offered only when:**
- the current version is Ready
- the PDF on disk is the one the report describes
- no refusal stands: a session finished and not applied, a new version being made, a record out of step
- **this file has not already shipped**, in a shipment that is not withdrawn. The same file never ships twice; after a withdrawal it may ship again.

Beside the button: "Records that this version was reviewed and shipped." Otherwise the strip says why, once:
- "This version was shipped on November 2, 2026 (Shipment 1)."
- or, while a refusal stands, the strip's one refusal line, worded for both recording and shipping: "…so no results can be recorded for it and it can't be marked as shipped."

A version that is not Ready gets no line: the card above says what is unsatisfied. After a shipment, a newer version that becomes Ready is offered again as the next shipment.

**The dialog** says "Records that this version was reviewed and shipped.", with the number of issues noted that ship with the copy, **Shipped By** (required, empty at first) and **Note (optional)**. It doesn't ask where the PDF was published. After it: "Marked as shipped: Shipment 1."

From the terminal: `manual_checks.py <run> --ship --by NAME [--note …]`.

### What shipping keeps

Shipping writes `release/shipped/NNN/`, whole or not at all. The folder holds:
- the PDF (a copy)
- review.md and review.html as they read once shipped; the copy's page says "Shipped copy (Shipment 1, …)"
- han_review.csv
- `evaluation-results.json`: the results on that file, with their issues
- `READ-ME.txt`, in plain words: the shipment's line ("Shipment 1, shipped on November 1, 2026 by Kim"), its status, what each file is, and the PDF's fingerprint. It is written once: a later withdrawal is said in a downloaded ZIP's read-me, not in this one.
- record.json, for the local archive only, never served and never in a ZIP

If anything fails before the folder is complete, the folder is removed and the pages redrawn, so nothing says Shipped.

Shipment numbers are never reused. A shipment is "Shipment N" in Title Case wherever a person reads it (the message, the strip, review.html, review.md, the read-me, "Available Downloads"); file names keep `_shipment-N`.

### After shipping

- The status reads "Shipped" (with "· N issues noted"), with Ready's green border.
- review.md's evaluation section names each shipment.
- review.html's Shipments list names each shipment, by whom and when.
- The shipped file downloads under its plain names.
- A shipped copy that a newer version replaced is listed in "Available Downloads" as "Shipment 1, shipped on …".
- A previous result's own page reads "Previous version (the current version is Session N)", naming its shipment when it was itself shipped.

**A shipped PDF that later changes on disk** keeps "Shipped", with "The current PDF has changed since this report was made." beside it, and never Ready's green. Mark as Shipped stays refused until it is resolved. The shipped copy in `release/shipped/` is untouched and still downloads.

## Withdrawal

Withdrawal is from the terminal only:

```bash
manual_checks.py <run> --withdraw-shipment N --by NAME --reason "…"
```

- It writes `withdrawn: {by, date, reason}` (local time, to the second) on that shipment; nothing is deleted.
- It is refused for an unknown shipment, one already withdrawn, or without a name and a reason.
- **The status** falls back to the latest shipment not withdrawn, and with none left to the statuses before shipping.
- **"Available Downloads"** still lists a withdrawn copy, marked "(withdrawn)", named `_shipment-N_withdrawn`.

## Clean Up Space

Every version is kept as a real PDF; there is no rebuilding from work orders. Repeated reviews keep one full PDF per version (13 MB and 96 MB for two earlier test books). So the run page offers a **Clean Up Space** button under Session History when there is something to remove, with no line under it.

Its dialog explains: "Deletes the PDF files of the previous versions you select to free up space. Their records and decisions stay in "Session History." The original AI-generated version is always kept."

**Never removed:**
- the current version
- the AI's own version (`reviews/versions/ai`: the result before any review, the evidence of what the AI did)
- any version with an evaluation result on its PDF
- any shipped version, withdrawn or not

**What goes:** only the PDF. The version's record.json, review.md and review.html, and the session's work order, stay. The version's page says the PDF was removed, whenever it is built.

**The dialog** has a checkbox per removable version, with its session, date and size. Any number can be selected; nothing is selected at first. It shows the selection's count and size, "Removed By" (empty at first), and "This can't be undone."
- The remove button names the count ("Remove 2 PDFs"), and is disabled while none is selected.
- Only the selected versions go, and only if each is still offered with the PDF it showed. If one changed meanwhile, nothing is removed.
- It is refused while a review is open or a new version is being made.
- The deletion is permanent. Escape or Cancel closes it, and focus returns to the button.

**Session History** keeps every row; a version whose PDF was removed is marked "PDF removed". **"Available Downloads"** lists only versions whose PDF exists.

**From the terminal:** `python3 review_workorder.py <run> --remove-older-pdfs` lists them, with their session numbers. `--remove-older-pdfs 3 5` names the sessions to remove (a dry run); add `--yes --by NAME` to remove those PDFs only. `--yes` without sessions is refused: nothing is removed unless chosen.

## Clearing a shipped book

**Clearing is optional.** A shipped PDF that is never cleared stays a full run, reachable from the home page at any time: **Review Again**, a newer version shipping as Shipment N+1, withdrawal, the downloads and the evaluation all keep working.

**Clear This Book's Files** is offered only on the run page, and only once its gate is open. The home page never prompts for it, counts it, highlights it or lists it as a to-do, and no status or message suggests that a shipped PDF should be cleared.

**The gate** is open when:
- the PDF is **Shipped**: its current PDF, hashed now, has a live (not withdrawn) shipment's hash
- the **record ZIP of that version was downloaded** in full. That the person kept it is not known.
- the **shipped copy** in `release/shipped/NNN/` still has the shipment's hash
- **nothing is in progress:** no job of the run, no review lock, no promotion or re-apply, no open session, no finished session waiting to be applied
- it is not cleared already

**The dialog** lists what goes, with sizes, and what stays, then asks for "Your Name" (never prefilled) and "Type CLEAR to Confirm". Afterwards the browser goes to the home page, where the row reads "Cleared on November 5, 2026 · shipped as Shipment 1".

### What is deleted

Only PDFs and images at named places, never a whole folder:
- the run folder's finished PDF, only when its hash is the shipment's (the shipped copy keeps the same file)
- `_intake/intake.pdf`
- every `reviews/versions/*/` PDF, including the AI's own version (`ai`) and versions with evaluation results. After shipping, the AI's decisions (`workorder.ai.json`, the sessions' work orders) and the records are the evidence; the PDF is a by-product. Before shipping, **Clean Up Space** still keeps the AI's version.
- figure crops and page images (`.png`, `.jpg`, `.jpeg`) under `_audit/` and `reviews/_audit/`

**What is kept:**
- every `.json`, `.md`, `.html` and `.csv` file: record.json, review.md, review.html, han_review.csv, the sessions, the digest, intake's record and the OCR verdict, `release/*.json`
- all of `release/shipped/NNN/`
- the original in `samples/` or `uploads/`, which is never touched, and the run's own original PDF (`source/`)

A clear that stopped partway shows on the run page, and **Clear This Book's Files** finishes it: each file still there is deleted only when it is the one planned; one that changed is kept and named.

### After clearing, the run is read only

From the app and the terminal alike, these are refused ("This book's working files were cleared after it shipped …"): Review Again, Apply, an OCR verdict, the evaluation's Record, Mark as Shipped, Clean Up Space, and New Run from the Saved Reply.

- Withdrawing a shipment still works.
- **Available Downloads** lists the shipped copies (built from `release/shipped/NNN/`) and no current version.
- `batch_api.sh` with `FROM=` refuses a cleared run as its source too ("cleared after shipping: its saved reply can't be reused"), since its intake result is gone.

A rebuild from `workorder.ai.json` after clearing would run on today's code, and would not be the original file. To work on the PDF again, start a new run from the home page.

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

### Downloads

- **One moment per download:** every file is opened under the record lock (a page waits at most 5 s), then the lock is released and the bytes are sent. A new version put in place meanwhile never mixes into a download.
- **A download that fails** after opening its files closes them before the error goes on.
- **The PDF's own name**, as its record gives it, must be a plain file name: no "/", "\", "..", leading dot or control character. Otherwise the current version is refused ("This version's file name in its record is not a plain file name …"), and a previous version or a shipped copy is not listed. So a hand-edited record.json never makes a ZIP entry or a path outside its folder.
- **The record ZIP** stores the PDF without compressing it again. It never holds digests, crops, `reviews/`, `_intake/`, `release/drafts.json` or dot-files. It is built as it is sent, and never kept on disk.
- **The ZIP's review.html:** when the app draws the ZIP's review.html, it also drops an older page's statement links and "where:".
- **The read-me's run details:** the AI cost comes from `lib/origin.py`. A shipped copy's run details come from its folder's record.json, which is never zipped. The stop at the review keeps its step times in `timing.json` for the second call to add to, and an AI request made by the run counts with the seconds `decide.py` kept.
- A refused download while a new version is being put in place means `reviews/promoting.json` exists.

#### Download names

`<book>` is made safe for any computer: NFC; control characters dropped; `< > : " / \ | ? *` and `;` replaced by `_`; no leading or trailing dot or space; at most 150 UTF-8 bytes. It is sent with `Content-Disposition` (RFC 6266/5987: an ASCII fallback and the UTF-8 name).

The list's arrow is drawn by the app's stylesheet, centered on the list's height in the page's text color (the browser's own sat high). With forced colors (Windows High Contrast), the browser's own list comes back.

### Clearing

The gate is `review/clear.py`, read when the page is drawn and again under the locks. The app adds a line to `release/downloads.json` after the ZIP's last byte is written. Locks are taken in Clean Up Space's order: `reviews/.lock`, which refuses, then the record lock. Read-only after clearing is `review/sessions.py` `not_cleared`, read in either state of cleared.json.

**The record:** `release/cleared.json` lists every deleted file with its path, size and sha256 (`versions/ai`'s included). It is written as `planned` before anything is deleted, and marked `done` after, with the space freed and the code's commit. To finish a partial clear, each planned file still there is hashed and deleted only when it matches the plan.

**A record is never an image or a PDF.** Under `_audit/` and `reviews/_audit/`, the records (the digest, the full text, dryrun.json, the OCR-word list) are `.json` or `.csv`. Clearing removes only the PDFs and images there ([Files](files.md)), so a later feature cannot lose a record by its choice of folder or file type, as long as it keeps that rule.
