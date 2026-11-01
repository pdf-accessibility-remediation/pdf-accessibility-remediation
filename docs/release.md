---
title: Manual checks and release
nav_order: 3.7
---

# Manual checks, status and release

A book is ready to ship only after a person has checked it by hand. Two checks are recorded for each book (issue #38;
sponsor checklist rule 2, 11.2 and 11.3):

- **PAC 2026 and sanity checks:** PAC 2026's WCAG check, plus a few checks that need eyes. They are part of "Ready to ship?".
- **The screen-reader check:** a person listens to the book with a screen reader. It decides "Verified" or "Needs Rework"
  once the book has shipped (sponsor decision, 2026-10-26).

Stage 1 (this version) records the checks from the terminal and works out the gate and the status. The app's Manual
Checks page, the downloads and the release itself (Mark as Shipped, the disclosure) come in later stages (branch
manual-checks).

```bash
cd pipeline
python3 manual_checks.py ../runs/godzone/rv1 --show                      # status, "Ready to ship?", the version, every check
python3 manual_checks.py --template pac > pac.json                       # an empty check to fill in
python3 manual_checks.py ../runs/godzone/rv1 --record pac pac.json       # record it (screen-reader: --record screen-reader FILE)
python3 manual_checks.py ../runs/godzone/rv1 --refresh                   # recompute the Overview and review.html (no PDF touched)
```

`--for-sha SHA` records only when the PDF on disk still has that sha256 (the version you checked; `--show` prints it).

## What each check asks

Each item is **Pass**, **Fail** or **Not Applicable**, with notes. The list is defined once, in `lib/release.py`
(`CHECKLIST`). review.md's "Final Check with PAC 2026" section and the app read it from there.

| PAC 2026 and sanity checks | |
|---|---|
| PAC 2026: WCAG Check | Pass or Fail only |
| PAC 2026: PDF/UA Check | Pass, Fail or Not Run; optional, and never decides "Ready to ship?" (it is recorded for the record) |
| Title and Language | |
| Spot-Check of Pages | with **Pages Checked** (`5, 9-12`) |
| Colour Alone (1.4.1), Contrast (1.4.3), Images of Text (1.4.5) | |
| What Needs a Person | every item the report lists was looked at |

| Screen-reader check | |
|---|---|
| Screen Reader and Version (required), PDF Reader and Version (optional) | |
| Title Announced; Document Language and Passages in Other Languages; Heading Navigation | |
| Reading Order on Sample Pages | with **Pages Checked** |
| Figure Alt Text; Tables Read with Their Headers; Links Say Where They Go; Lists; OCR Pages Read Sensibly; Formulas | |
| Other Notes (optional) | |

**The rules for each item:**
- **A Fail needs a note.**
- **Not Applicable needs a note when the pipeline found the thing** (figures, tables, links, lists or formulas in the tag
  tree, or OCR text on some pages, read from `record.json`).
- **A Pass needs a note when the same item failed** in the last check of the same file, so a Fail is never overturned
  without a reason.
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
- **A check whose refresh fails is taken back.** If rewriting the record after a check fails (for example an import
  error), `release/checks.json` is put back as it was and the error is raised, so a check never stands beside a record
  that lacks its hash.
- **Offline dashboards** (`review.html` opened as a file, `summary.html`) compare the checks with `document.output_sha256`
  only. They never hash the PDF.

## "Ready to ship?"

Yes only when all of these hold:
1. **The work order** was approved on the review page.
2. **The OCR text** was approved, when it needs approval (as before).
3. **The six safety checks are OK:** pages look the same, text unchanged, all content tagged or decoration, the tag-tree
   index points into the tree, every font readable, and **no WCAG rule newly failing (veraPDF)**.
   - **The sixth check counts WCAG rules only:** a rule that fails after the run and not before, or fails more checks after
     than before. A PDF/UA-only rule that regresses keeps review.md's "veraPDF: no rule newly failing or failing more
     often" row a CHECK, but it is not a safety issue.
   - **"Failing more often" counts failed checks.** On an auto-tagged book, new structure can raise a count
     legitimately (none does on the 19 reference books), so a Failed here means "look", not necessarily "broken".
   - **veraPDF not run on both files** makes the sixth check *not checked*. Such a book is never ready to ship. It is
     shown as "Not checked", never as "Failed".
   - **A different measure from the regression test's:** regression.py's own invariant compares the *total* number of
     WCAG rules failing (before and after). The sixth check compares rule by rule, so the two can disagree.
4. **The manual check (PAC)** was done on this version of the PDF, with no item failed.
5. **No screen-reader check of this version failed an item.** This line appears only then. A version nobody has listened to
   yet is not held back.

**Fail closed:** "Ready to ship?" is Yes only on a glance of the current schema (`glance/0.4`) with the work-order, OCR
and safety lines all present and met. A stored older glance (five safety checks) never reads Yes, even beside a
counting PAC check.

**Version 1 is strict:** any failed item keeps the line closed. A later "Fail, Accepted with a Note" (a person accepting a
failed item with a written reason) has room in the records but is not built, and it waits for the sponsors.

## The status

| Status | When |
|---|---|
| **Not Ready** / **Ready** | nothing shipped (or every shipment withdrawn), and "Ready to ship?" is No / Yes |
| **Shipped** | the latest shipment's file has no screen-reader check yet |
| **Verified** | that file's latest screen-reader check has no Fail; **Verified (checked before shipping, DATE)** when the check is older than the shipment (worked out from the two dates each time, never stored, so the rule can change if the sponsors decide otherwise) |
| **Needs Rework** | that file's latest screen-reader check has a Fail |

- **After a shipment, the status is about the shipped copy,** because that is what readers have. A second line says what
  comes next, from the session files (`newer()`): "Newer version: Session 7 finished, not applied" (being applied, or
  its apply failed), else "Newer version: Session 7 being reviewed" (an open session, also while the shipped file is
  still the current one), else, when the current file is not the shipped one, "Newer version (Session 7): Ready to Ship?
  No". So Needs Rework stays until a fixed version ships.
- **Where the status is shown:**
  - review.md's Overview, as `**Status:** …` above "**Ready to ship?**";
  - review.html's "Ready to Ship?" card;
  - summary.html's Status column.

## The records

```
release/checks.json     {schema: "manual-checks/1", pac: [check …], screen_reader: [check …]}   newest last, nothing deleted
                        check: {id, recorded, by, via, code, pdf: {sha256, file, session, which}, fields,
                                items: {key: {result: pass|fail|na (not_run: PDF/UA only), note}}, notes}
release/shipped.json    [{n, shipped, by, pdf: {sha256, …}, where, note, withdrawn?}]   (written from a later stage)
<run>/.record.lock      the record lock (below)
```

- **The latest check of a section on a file is the one that counts.** Earlier ones stay in the record.
- **`code`** is the git commit the writer ran on. An app started before a `git pull` writes with its old code until it is
  restarted, and this field shows which code that was.
- **v1 reads fail closed:** a blocking item is OK only when its result is `pass` or `na` and it carries no `accepted`.
- **`record.json` keeps copies for the archive,** never read back for a decision: `manual_checks` (each section's
  latest check with its `state`: counts, failed, earlier version) and `release`.
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

## Older runs

A run made before 2026-11 keeps its review.md: its old headings and its old "Final check with PAC 2026" section. Its
Overview and review.html change when something is recorded on it, or with `--refresh`. Its stored glance (schema
`glance/0.3`) is never trusted for "Ready to ship?": every reader works the PAC line, `ready` and the status out again.
