---
title: Accessibility evaluation and release
nav_order: 3.7
---

# Accessibility evaluation, status and release

A book is ready to ship only after a person has evaluated it by hand. The **accessibility evaluation** has two parts,
recorded for each version of the book (issue #38; sponsor checklist rule 2, 11.2 and 11.3 in part: 11.3 asks for a task
test with real screen-reader users, and this is a staff check against a checklist):

- **PAC 2026:** PAC 2026's WCAG check, plus a few checks that need eyes;
- **the Screen-Reader Test:** a person listens to the book with a screen reader.

**The evaluation is a report, not a gate on its results** (decided 2026-10-31). Both parts must be recorded for the
version before it is Ready. A Fail never blocks: it needs a note, and it is counted as an issue noted in the status
("Ready · 2 issues noted"), kept in the report and, once shipped, in the shipped folder, for a person to fix later. The
evaluation is a record of what a person found, not a legal certification.

Both parts are recorded on the app's **Accessibility Evaluation** page (below), or from the terminal with
`manual_checks.py`. In the records and the code they are still "manual checks" (`release/checks.json`, `pac`,
`screen_reader`). Any version can be downloaded at any time, ready or not ("Downloads" below). A Ready version is marked
as shipped from the run page ("Mark as Shipped" below), which keeps a copy with its accessibility statement.

## The Accessibility Evaluation page (in the app)

- **Opening it:** the run page has a strip right after "Ready to Ship?", headed **Accessibility Evaluation (PAC 2026 &
  Screen-Reader Test)**, with a **Complete Evaluation** button and one line per part: "completed on this version (Kim,
  November 1, 2026)" with a check mark (and "· 1 issue noted" when it has Fails), "not completed", "completed on an
  earlier version: evaluate this version", or "could not be read in full: record it again". Each part's name links
  straight to its section. The strip also says the status as it is now when the report's card was written before a change
  (a session opened after shipping, for example), and says in plain words when the book's PDF has changed since its report
  was made. While the PDF on disk is not the one the report describes (a Ready book's or a shipped one's), the app drops
  the card's green border on the run page; review.html opened as a file keeps it until it is next rebuilt. When the run
  has no "Ready to Ship?" card, the strip goes at the end of the panel, as an h3.
- **The page** (`/run/<run>/checks`) names the book as "PDF Title" (the remediated PDF's own title, else the original's
  name without ".pdf"), the version the results are for ("the version from Session 6, applied on October 30, 2026 at
  2:02 PM"), and the **Overall Status**, with the unsatisfied requirements when it is Not Ready ("Overall Status: Not
  Ready · Unsatisfied Requirements: Work Order Approval, OCR Text Approval").
- **Each part** is a section headed "PAC 2026" or "Screen-Reader Test". It holds a form: **Checked By**, its fields, and
  one group per item with **Pass** / **Fail** / **Not Applicable** (PAC's WCAG check: Pass or Fail) and **Notes**. A note
  becomes required when the choice asks for one (a Fail; Not Applicable on something the pipeline found, with a hint such
  as "This book has 12 tables"; a Pass where the last results recorded for this version failed the item). **Pages Checked**
  is optional. The help lines keep the WCAG numbers, as PAC's report shows them.
- **Saving is automatic,** as on the review page: about a second after each change (`release/drafts.json`), one save at a
  time, the browser keeping a copy; "All changes saved" / "Saving…" beside the Record button, not announced; a failed
  save is announced (not when the page is leaving after a Record). A draft older than the one saved is never written over
  it (two tabs). A draft started on an earlier version is not used as answers: **Start from These Notes** copies its
  names, versions, pages and notes, never its results, as it does for earlier results.
- **Record the PAC 2026 Results / Record the Screen-Reader Test Results** sends the answers to the same code
  `manual_checks.py` uses. Problems come back from that code, each shown under its field and in a summary that takes
  focus; nothing is recorded while one remains. Recording clears the section's draft (an auto-save handled after it is
  refused, so the answers never come back as a draft). The page stays, with a message saying what changed and what is
  still needed; results with a Fail offer **Review Again**. A draft that could not be cleared is logged in
  `runs/.app/server.log`.
- **The results tables** never scroll sideways: Notes wrap, and the Item column keeps its words together.
- **Earlier results** are under **Earlier Results (N)**, folded and read-only.
- **Refused** while a new version is being made, the PDF has changed, the PDF on disk is not the one the book's last
  review produced, or another change is being saved (a page waits at most 5 s): the message says why, before anything is
  filled in, and drafts are still saved.
- **The record lock** is taken in the app's own process for these writes (no job): an hour-long screen-reader test never
  holds the run's job slot.

```bash
cd pipeline
python3 manual_checks.py ../runs/godzone/rv1 --show                      # status, "Ready to ship?", the version, every result
python3 manual_checks.py --template pac > pac.json                       # empty results to fill in
python3 manual_checks.py ../runs/godzone/rv1 --record pac pac.json       # record it (screen-reader: --record screen-reader FILE)
python3 manual_checks.py ../runs/godzone/rv1 --refresh                   # recompute the Overview and review.html (no PDF touched)
```

`--for-sha SHA` records only when the PDF on disk still has that sha256 (the version you checked; `--show` prints it).

## What each part asks

Each item is **Pass**, **Fail** or **Not Applicable**, with notes. The list is defined once, in `lib/release.py`
(`CHECKLIST`). review.md's "Accessibility Evaluation" section and the app read it from there.

| PAC 2026 | |
|---|---|
| PAC 2026: WCAG Check | Pass or Fail only |
| Title and Language | |
| Spot-Check of Pages | **Pages Checked** (optional: `5, 9-12`) |
| Colour Alone (1.4.1), Contrast (1.4.3), Images of Text (1.4.5) | |
| What Needs a Person | every item the report lists was looked at; a Pass turns the dashboard's "Needs a Person" card neutral ("looked at in the evaluation") |

| Screen-Reader Test | |
|---|---|
| Screen Reader and Version (required), PDF Reader and Version (optional) | |
| Title Announced; Document Language and Passages in Other Languages; Heading Navigation | |
| Reading Order on Sample Pages | **Pages Checked** (optional) |
| Figure Alt Text; Tables Read with Their Headers; Links Say Where They Go; Lists; OCR Pages Read Sensibly; Formulas | |
| Other Notes (optional) | |

**Retired items (2026-10-31):** PAC 2026's PDF/UA check and the PAC Version field are no longer asked. Older records that
hold them still load: they are never counted (not toward completeness, not as an issue) and are shown only in that
record's full results, labelled "(no longer asked)" (`RETIRED` in `lib/release.py`).

**The rules for each item:**
- **A Fail needs a note.**
- **Not Applicable needs a note when the pipeline found the thing** (figures, tables, links, lists or formulas in the tag
  tree, or OCR text on some pages, read from `record.json`).
- **A Pass needs a note when the same item failed** in the latest results of the same file, so a Fail is never
  overturned without a reason.
- **Text limits:** names and fields at most 80 characters, item notes 1,000, Other Notes 4,000. Control characters and
  direction overrides are removed, and `|` and `](` are refused, as on the OCR form.

## Each check belongs to one file

**Every check records the sha256 of the remediated PDF it was made on.** A check counts only for the file with that hash.
The rule is simply that the hash shown, the hash on disk and the hash in `record.json` (`document.output_sha256`) must
be the same. Nothing relies on an apply making new bytes.

- **In practice, any new apply makes the checks out of date.** A re-apply gives a new file: pikepdf writes a new `/ID`
  on each save, and the `/ID` follows the clock. So do the PAC check after the last review is applied. An OCR verdict
  does not change the PDF, so it does not.
- **When the PDF is hashed:**
  - from 2026-11, `report.py` hashes the PDF it reports on;
  - a run made before that has no `output_sha256`. Its first recorded check takes the hash of the file on disk, marked
    `output_sha256_from: "first check, <date>"`. Where the current session's record (`reviews/sessions/NNN.json`
    `version.pdf_sha256`) names a hash, the two must be equal, or the check is refused.
- **A check is refused** (and nothing is written) when:
  - the PDF on disk is not the one `record.json` describes;
  - the PDF changed since the version was shown (`--for-sha`);
  - a new version is being made: a session newer than the current result is finished and not yet applied (what Apply
    applies; this covers the whole re-apply and a failed one), `reviews/work/` exists (a re-apply under way), or
    `reviews/promoting.json` exists (a promotion that did not finish). A finished session that a later one replaced (its
    apply failed, then a new review was applied) never blocks: one rule, `review/sessions.py` `newer()`, decides this,
    the app's Apply offer and the "Newer version" line.
  - the record is out of step with the review sessions: an applied session is newer than the session record.json names
    (no apply leaves this behind; refused rather than filing a check under the wrong version).
- **A check whose refresh fails is taken back.** If rewriting the record after a check fails (for example an import
  error), `release/checks.json` is put back as it was and the error is raised, so a check never stands beside a record
  that lacks its hash.
- **Offline dashboards** (`review.html` opened as a file, `summary.html`) compare the checks with `document.output_sha256`
  only. They never hash the PDF.

## "Ready to ship?"

The card (review.html, and the run page that shows it) is headed "Ready to Ship?". Its status line carries the answer, and
its four requirements follow, each with a check mark when satisfied (the words say it; the mark is hidden from screen
readers):

```
Ready to Ship?
Status: Pending Evaluation
  ✓ Work Order Approval: Approved (Patrick on October 31, 2026)
  ✓ OCR Text Approval: Not Required (no OCR text was added during intake)
  ✓ Safety Checks: Passed
  • Accessibility Evaluation: Not Completed (neither part recorded for this version)
```

review.md's Overview writes the same lines, under `**Ready to ship?**` and the `**Status:**` line above it. A version is
**Ready** when all four are satisfied:

1. **Work Order Approval:** the work order was approved on the review page. Otherwise "Not Approved", with why: applied
   without a review, decisions not reviewed, reviewed by hand edit, or a later session finished but not applied.
2. **OCR Text Approval:** the OCR text was approved, when it needs approval (as before): "Approved", "Not Approved",
   "Waiting for a Language Reader", "Not Reviewed", or "Not Required".
3. **Safety Checks:** the five damage checks are OK: pages look the same, text unchanged, all content tagged or
   decoration, the tag-tree index points into the tree, every font readable. "Passed", or "Failed (…)" naming them. A run
   made before some of these checks existed records fewer: "Not Checked (only 3 of the 5 checks were recorded for this
   run)", and the Safety card says "Not checked". Such a run is never Ready.
4. **Accessibility Evaluation:** both parts are completed for this version of the PDF. A part is completed when its
   latest results on that file have, for every item the checklist asks, one of that item's own choices. "Completed",
   "Completed (2 issues noted)", or "Not Completed (…)" saying what is missing: a part not recorded, recorded on an
   earlier version, or that could not be read in full.

**veraPDF is a finding, not a safety check** (2026-10-31). A WCAG rule newly failing or failing more often after the run,
or veraPDF not run on both files, is listed first among the requirement items in "What Needs a Person" (from review.md's
row "veraPDF: no rule newly failing or failing more often", counted once, as that CHECK row). The veraPDF card says
"N newly failing" in orange, or "newly failing: not checked" when veraPDF did not run on both files. A newly failing rule
is often one that only became checkable after tagging (bringing went from 9 failing rules to 2, with 7.18.1-1 new), not
damage. A PDF/UA-only regression stays an ordinary check.
- **"Failing more often" counts failed checks.**
- **A different measure from the regression test's:** regression.py's own invariant compares the *total* number of WCAG
  rules failing (before and after); the finding compares rule by rule, so the two can disagree.

**Fail closed:** the first three requirements can be satisfied only on a stored glance of schema `glance/0.4` or
`glance/0.5` (both written under every current rule; `glance/0.3` predates the rules for a flagged OCR layer, a finished
but unapplied session and the sent-to-a-reader verdict) that has all three lines and all five damage checks. A stored
`glance/0.4`'s sixth check (veraPDF) is dropped on read and its Safety line worked out again from the five.

## The status

| Status | When |
|---|---|
| **Not Ready** | a requirement among the first three is unsatisfied |
| **Pending Evaluation** | those three are satisfied; the evaluation is not completed for this version |
| **Ready** | all four are satisfied |
| **Shipped** | a shipment exists that is not withdrawn; the status is about the shipped copy |

- **"· N issues noted"** follows any status whose version has Fails in its evaluation: "Pending Evaluation · 1 issue
  noted", "Ready · 2 issues noted", "Shipped · 2 issues noted". After a shipment they are the shipped file's.
- **`ready`** (in record.json's glance) is true exactly when the status is Ready. A Shipped book has Ready's green border on
  the card, and summary.html counts the two apart ("Ready: N · Shipped: M · Pending Evaluation: P").
- **After a shipment, a second line** says what comes next, from the session files (`newer()`): "Newer version: Session 7
  finished, not applied" (being applied, or its apply failed), else "Newer version: Session 7 being reviewed" (an open
  session, also while the shipped file is still the current one), else, when the current file is not the shipped one,
  that version's own status: "Newer version (Session 7): Pending Evaluation".
- **Withdrawal:** the status falls back to the latest shipment not withdrawn; with none, the statuses before shipping apply.
- **Where the status is shown:** review.md's Overview (`**Status:** …` above "**Ready to ship?**"); review.html's card;
  summary.html's Status column; the evaluation page ("Overall Status") and the strip.

## The records

```
release/checks.json     {schema: "manual-checks/1", pac: [check …], screen_reader: [check …]}   newest last, nothing deleted
                        check: {id, recorded, by, via, code, pdf: {sha256, file, session, which}, fields,
                                items: {key: {result: pass|fail|na (not_run: an older PDF/UA row), note}}, notes}
release/shipped.json    [{n, shipped, by, pdf: {sha256, …}, where, note, withdrawn?}]   (written from a later stage)
<run>/.record.lock      the record lock (below)
```

- **The latest results of a part on a file are the ones that count.** Earlier ones stay in the record.
- **`result` is what the person saw,** never rewritten. Only the reading changed on 2026-10-31.
- **`code`** is the git commit the writer ran on. An app started before a `git pull` writes with its old code until it is
  restarted, and this field shows which code that was.
- **Reads fail closed:** a missing item, an unknown result or an unknown item (retired ones are known) makes that part
  "could not be read in full: record it again", never completed. Its Fails still count as issues noted. An `accepted`
  key (reserved earlier for a "Fail, Accepted with a Note") is no longer needed and is read by the result alone.
- **`record.json` keeps copies for the archive,** never read back for a decision: `manual_checks` (each part's latest
  results with their `state`: completed, could not be read, earlier version; and `issues`) and `release`.
- **The `release/` folder stays through every re-apply:** a promotion moves only the result files. A copied run folder
  carries it too, so a test copy of a checked (or, later, shipped) book says so, and holds what the original holds.

## The record lock

Every writer of a finished run's `record.json`, `review.md`, `review.html` and `release/` holds `<run>/.record.lock`
around its whole read-change-write: a manual check, an OCR verdict, `mark_pending`, and each stage of a promotion up to
and including its re-mirror (`lib/runlock.py`).

- **Waits:** a page's request waits at most 5 s ("Another change to this book is being saved. Try again in a moment.");
  the command line and jobs wait up to 120 s.
- **Not re-entrant:** no writer calls another, so taking it twice in one thread is a bug and raises.
- **The order:** `reviews/.lock` (never waits) → `_intake/.verdict.lock` → `.record.lock`, never the reverse.
  `runs/.app/dispatch.lock` is never held together with it.
- **A promotion** re-reads `release/` after it moves the new result in, then rewrites the Overview, review.html and the
  mirror, so a check recorded during a re-apply is not lost. It releases the lock before it rewrites the replaced
  version's own page. The locked refresh takes about 0.1 s on dwellings (96 MB, 2026-10-31).
- **Readers take no lock;** every file is written whole (a temp file and a rename).

## In the report

- **review.md** ends with "## Accessibility Evaluation": how to do it, and the checklist. Once a result is recorded, each
  part's latest results are written in full (a summary line, who and the fields, the Item / Result / Notes table, Other
  Notes as a quote). A person's text is escaped, so it reads as typed and no line of it can start a heading or a list. The
  section is redrawn on every refresh once anything is recorded, and nothing else in review.md changes. A re-apply's
  review.md shows the run's earlier results ("Completed on an earlier version (Session 5) …"), since `release/` is the run's.
- **review.html** shows an "Accessibility Evaluation" section once anything is recorded (nothing before): one summary line
  per part ("PAC 2026: Completed by Patrick on October 31, 2026 · 7 items · 1 issue noted"), the failed items with their
  notes, and **View Full Results**, which opens the full results in the page's notes box (an accessible pop-up: Escape and
  × close it, focus returns to the button). Without the script, and in print, the full results are shown in place. While
  nothing is recorded, review.md's own section is drawn as a fold at the end (the instructions); once something is, it is
  not, so nothing appears twice.
- **The "Needs a Person" card** turns neutral once this version's PAC 2026 results mark "What Needs a Person" as Pass:
  "looked at in the evaluation (Patrick, October 31, 2026)". A Fail keeps it orange ("marked Fail in the evaluation …").
  review.md's "Needs a person" line says the same.

## Downloads

Any version of the book can be downloaded at any time, ready or not: from the run page's strip (under "Complete
Evaluation") and from the evaluation page's "Download and Check the PDF".

- **"Version to Download"** is a list of the current version and each earlier result whose PDF still exists. It decides
  which version the two buttons give: **Download the Remediated PDF** and **Download the Record (ZIP)**. It never
  changes what the evaluation records: the evaluation is always for the current version. The line under it says how the
  files are marked, never their names.
- **Names:** the PDF's bytes are never changed, only the name it is saved under.

  | That version | PDF | ZIP |
  |---|---|---|
  | Not Ready or Pending Evaluation | `<book>_session-6_not-ready.pdf` | `<book>_record_session-6_not-ready.zip` |
  | Ready | `<book>_session-6_not-shipped.pdf` | `<book>_record_session-6_not-shipped.zip` |
  | Shipped (the shipped file) | `<book>.pdf` | `<book>_record_shipment-2.zip` |
  | A withdrawn shipped copy | `<book>_shipment-1_withdrawn.pdf` | `<book>_record_shipment-1_withdrawn.zip` |
  | An earlier version | `<book>_session-5_earlier-version.pdf` | `<book>_record_session-5_earlier-version.zip` |
  | No review | `<book>_no-review_not-ready.pdf` | `<book>_record_no-review_not-ready.zip` |

  - `<book>` is the remediated PDF's name without ".pdf", made safe for any computer: NFC; control characters dropped;
    `< > : " / \ | ? *` and `;` replaced by `_`; no leading or trailing dot or space; at most 150 UTF-8 bytes.
  - The session's number is used, never its name.
  - Sent with `Content-Disposition` (RFC 6266/5987: an ASCII fallback and the UTF-8 name).
- **The record ZIP** holds one folder named as the ZIP. Every file keeps its own name:
  - the PDF (stored, not compressed again);
  - review.html, review.md, han_review.csv when there is one;
  - `evaluation-results.json`: the results recorded on that file's hash;
  - `READ-ME.txt`: the version, its status (for an earlier version: "earlier version", naming the current one), the
    PDF's sha256, "automated checks are evidence, not legal sign-off" and "the evaluation is a record of what a person
    found, not a legal certification".

  Never record.json (it holds the AI's raw reply), digests, crops, `reviews/`, `_intake/`, `release/drafts.json` or
  dot-files. The ZIP is built as it is sent and never kept on disk.
- **One moment per download:** every file is opened under the record lock (a page waits at most 5 s), then the lock is
  released and the bytes are sent. A new version put in place meanwhile never mixes into a download.
- **Refused:** while a new version is being put in place and did not finish (`reviews/promoting.json`), or when the PDF
  on disk is not the one the report describes. A re-apply under way, or a finished session not yet applied, does not
  stop a download.

## Which Version Is This File?

On the evaluation page, a person can choose a PDF (one downloaded earlier, or the one checked in PAC). The page hashes it
in the browser (`crypto.subtle`) and says which version it is:
- the current one, with its status;
- an earlier one;
- an earlier one whose PDF was removed from this computer;
- or that it matches no version of this book.

Nothing is uploaded. Both `http://localhost` and `http://127.0.0.1` are secure contexts, which `crypto.subtle` needs.

## Remove Older PDFs

Every version is kept as a real PDF; there is no rebuilding from work orders. Repeated reviews keep one full PDF per
version (13 MB for expedition, 96 MB for dwellings), so the run page offers **Remove Older PDFs** under Session History
when there is something to remove: "Frees space by deleting the PDFs of earlier versions that were never evaluated or
shipped. Their records and decisions are kept. The AI's own version is always kept."

- **Never removed:**
  - the current version;
  - the AI's own version (`reviews/versions/ai`, the result before any review: the evidence of what the AI did);
  - any version with an evaluation result on its PDF;
  - any shipped version, withdrawn or not.
- **What goes:** only the PDF. The version's record.json, review.md and review.html, and the session's work order, stay.
  `release/removed.json` records each removal (version, sha256, size, who, when), and the version's page says so
  whenever it is built.
- **The dialog** lists each version with its size and the total, and asks for "Removed By". It removes exactly the list
  it showed: if anything changed meanwhile, nothing is removed. It is refused while a review is open or a new version
  is being made. The deletion is permanent.
- **From the terminal:** `python3 review_workorder.py <run> --remove-older-pdfs` lists them (a dry run). Add `--yes --by
  NAME` to remove them (`review/prune.py`).
- **"Version to Download"** lists only versions whose PDF exists. "Which Version Is This File?" still recognises a
  removed one.

## Mark as Shipped

"Mark as Shipped" records that a person published this version elsewhere (for example in ScholarSpace). The app publishes
nothing.

- **Offered only when** (webapp/manualpage.py `ship_gate`, and again under the lock):
  - the current version is Ready;
  - the PDF on disk is the one the report describes;
  - no refusal stands (a session finished and not applied, a new version being made, a record out of step);
  - **this file has not already shipped**, in a shipment that is not withdrawn (03 §3.3): the same file never ships
    twice, and after a withdrawal it may ship again.

  Otherwise the strip says why, in one line: "This version was shipped on November 2, 2026 (shipment 1)", or "This
  version is not ready to ship: … still unsatisfied". After a shipment, a newer version that becomes Ready is offered
  again as the next shipment.
- **The dialog:** **Shipped By** (required), **Where It Was Published (optional)**, **Note (optional)**, and the number of
  issues noted that ship with the copy. Or from the terminal: `manual_checks.py <run> --ship --by NAME [--where …]
  [--note …]`.
- **What it writes,** under the record lock, whole or not at all: `release/shipped/NNN/`.
  - The folder holds:
    - the PDF (a copy, hashed while copied);
    - review.md and review.html as they read once shipped (the copy's page says "Shipped copy (shipment 1, …)");
    - han_review.csv;
    - `evaluation-results.json`: the results on that file, with their issues;
    - the accessibility statement (`disclosure.html`, `disclosure.md`);
    - `READ-ME.txt`;
    - record.json, for the local archive only, never served and never in a ZIP.
  - `release/shipped.json` gains `{n, shipped (local time, to the second), by, where, note, pdf: {sha256, file, session},
    folder, issues, checks}`.
  - If anything fails before the folder is complete, the folder is removed, `shipped.json` restored, and the pages
    redrawn, so nothing says Shipped.
  - Shipment numbers are never reused.
- **Afterwards:**
  - the status reads "Shipped" (with "· N issues noted"), with Ready's green border;
  - review.md's evaluation section names each shipment;
  - review.html's Shipments list links "View the Accessibility Statement";
  - the shipped file downloads under its plain names, and its record ZIP holds the statement;
  - a shipped copy that a newer version replaced is listed in "Version to Download" as "Shipment 1, shipped on …".
- **A shipped book whose PDF later changes on disk** keeps "Shipped", with "The current PDF has changed since this report
  was made." beside it, and never Ready's green. Mark as Shipped stays refused until it is resolved. The shipped copy in
  `release/shipped/` is untouched and still downloads.
- **A previous result's own page** reads "Earlier version (the current version is Session N)", naming its shipment when
  it was itself shipped.

## Withdrawal

From the terminal only: `manual_checks.py <run> --withdraw-shipment N --by NAME --reason "…"`.
- It writes `withdrawn: {by, date, reason}` (local time, to the second) on that shipment; nothing is deleted.
- It is refused for an unknown shipment, one already withdrawn, or without a name and a reason.
- **The status** falls back to the latest shipment not withdrawn, and with none left to the statuses before shipping.
- **"Version to Download"** still lists a withdrawn copy, marked "(withdrawn)", named `_shipment-N_withdrawn`.

## The accessibility statement

Written once when a version ships, into its folder, as `disclosure.html` and `disclosure.md`, by `lib/disclosure.py`;
never rewritten afterwards. It is marked "Draft wording: to be agreed with the sponsors".

- **This file:** the file, its version, who shipped it, when, where, and its sha256.
- **The text:** "No AI wrote or changed the book's printed text", then, only when they apply:
  - the AI's readings of misread OCR words, given as spoken text only;
  - the local OCR pages and who approved them;
  - the publisher's OCR layer, checked and kept.
- **What the AI decided and what people did, per kind:** approved as proposed, changed by a person, rejected by a
  person, added by a person. An older reviewed run gives the totals; a run with neither says the split was not recorded.
  The model, the instructions and the date of the call are named only for a real call: a replayed reply says "those of
  an earlier call, not recorded for this run".
- **What people reviewed and approved:** the work order's reviewer (the applied session's), the OCR text, and each part
  of the evaluation with its evaluator.
- **Every issue noted,** with its note.
- **The automated checks:** the five safety checks, and veraPDF before and after, or "not checked".
- **The two sentences:** "Automated checks are evidence, not legal sign-off." and "The accessibility evaluation is a
  record of what a person found, not a legal certification."
- **Names and notes are shown as typed,** escaped in both files.
- **Waiting on the sponsors:** the audience, placement (beside the PDF in ScholarSpace or on the item page; never inside
  the PDF), whether names stay public, and a contact.

## Older runs

A run made before 2026-11 keeps its review.md: its old headings and its old "Final check with PAC 2026" section, until
something is recorded on it (the section is then replaced by "Accessibility Evaluation"). Its Overview and review.html
change when something is recorded on it, or with `--refresh`. Its stored glance (schema `glance/0.3`) is never trusted for
"Ready to ship?": it is never Ready until it is recomputed (every dashboard recomputes it).
