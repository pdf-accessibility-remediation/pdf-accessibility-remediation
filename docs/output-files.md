---
title: Output files
parent: How it works
nav_order: 5
---

# What a run leaves in `runs/<name>/<run-label>/`

Each run writes its results to its own folder, beside `pipeline/`. This page lists every file there, who it is for, and what it holds. The remediated PDF, `review.md` and `review.html` are the three most people need; the [For developers](#for-developers) section describes the rest of the record in detail.

## The files

| File | For | What it is |
|---|---|---|
| `<original>_remediated.pdf` | everyone | The result. Run PAC 2026 on this. Named by `OUT` or the list of PDFs if you set one |
| `review.md` | the reviewer | The report: every check and every decision, as text (see [review.md](#reviewmd)) |
| `review.html` | the reviewer | The same report as an offline page: the main view for people (see [review.html](#reviewhtml)) |
| `record.json` | the archive | Everything vital about the run in one file (see [record.json](#recordjson)) |
| `reviews/` | a later review | What is needed to review the run again after code changes (see [The reviews folder](#the-reviews-folder)) |
| `release/` | the archive | The accessibility evaluation's results and each shipment (see [The release folder](#the-release-folder)) |
| `han_review.csv` | a Japanese / Chinese reader | Only when the PDF has Han-only CJK runs: one row per run, with a blank decision column |
| `_intake/intake.md` | a reviewer | Untagged originals only: the intake record in plain words (see [Intake files](#intake-files)) |
| `_intake/intake.json` | the archive | Untagged originals only: what intake measured and did (see [Intake files](#intake-files)) |
| `_intake/intake.pdf` | the pipeline | Untagged originals only, when intake changed anything: the OCR'd and auto-tagged copy the rest of the run worked on |
| `_handedit/` | the archive | A run made from a PDF edited by hand only (see [Hand-edit files](#hand-edit-files)) |
| `hand_edits.json` | the archive | A run whose PDF was exported or edited by hand: each export and each run made from an edit (see [Editing the PDF by hand](hand-edits.md)) |
| `exports/` | a reviewer | `handedit.py export`'s copies, by default: edit these, never the result itself |

**Nothing else is kept.** The working files are deleted once the report is written: the digest, figure crops, raw request and response, logs, and with `REVIEW=1` the review's page images, OCR word crops and files. They are rebuilt from the original in under a minute, and the crops are copies of the PDF's pages. A run that fails partway keeps its working files, so the failure can be diagnosed.

## review.md

`review.md` is the report as text. It holds:

- the automated checks, including exactly one H1, bookmarks present, every decision applied, and nothing deferred. A green row is evidence, not proof.
- every alt text the AI wrote (before and after), and the ones it left alone
- heading levels and spoken heading text
- what was hidden as decoration
- reading-order moves
- what the AI and the executor deferred
- anything not applied

It opens with an Overview (see [The Overview](#the-overview)).

## review.html

`review.html` is the main view for people. It sits beside `review.md`, which is the record and links to it. It is one offline file: no internet, no external scripts, and it reads in full without JavaScript. It quotes the PDF's text, like review.md, so it stays under `runs/`.

### What it shows, from the top

1. **"Ready to Ship?"**, with the PDF's status and its four requirements (see ["Ready to ship?"](evaluation.md#ready-to-ship)).
2. **An Accessibility Evaluation section**, once a result is recorded: a summary line per part, its failed items and notes, and "View Full Results" in a pop-up (in place, in print).
3. **Four status cards** (see [The status cards](#the-status-cards)).
4. **A folded "Run details":** result file, intake, libraries, time.
5. **What needs a person:** every description in full, with its source and pages, and a "Details" link that opens the folded section at that very item. Without JavaScript it lands on the section.
6. **A filter by source**, whose options show how many issues come from each ("All sources (13)", "Ship condition (1)"). It isn't shown when all come from one source.
7. **The page strip** (see [The page strip](#the-page-strip)), and the same as a plain list.
8. **Every section of review.md**, collapsible.

summary.html keeps its bars.

### The status cards

- **Safety**, with its five checks in a fold. When one fails, the fold opens with the failed check first, and "The 5 Safety Checks" stays a link. When all five pass, that toggle is plain grey.
- **Needs a person**: green once this version's evaluation marks it Pass ("Considered during the evaluation").
- **AI decisions.**
- **veraPDF before → after**, with "N newly failing" in orange, or "newly failing: not checked".

### The page strip

The strip has one cell per page of the PDF, shaded by its most serious issue. It is one Tab stop; the arrow keys move along it, and each page's issues are read out.

- **Preview:** hover or use the arrow keys. A preview has a dotted outline.
- **Pin:** click or press Enter. A pinned page has a solid outline, with a matching swatch before its details. While one is pinned, a preview shows on its own line below it.
- **Unpin:** click the pinned cell, click outside the strip, or press Escape.

"Pinned" and "Preview" are read out to screen readers, and pinning is announced.

Every page reference in the report ("PDF 152 (printed 143)") links to that page in the strip and pins it there. It shows what needs a person on that page and every section that mentions it, each linked to the exact item. A page reference counts only as a whole word: not "veraPDF 1.30.3" or "PDF 2.0".

### Sections and their counts

A "§N Details" link opens the folded section at the very item, and outlines it in blue until the next click elsewhere (one at a time).

Section badges count real entries only (table rows and list items), not notes such as "Not changed: …". A section title that ends in a count equal to its badge is shown without it in review.html; review.md keeps it.

**Items that need a person** are marked:
- an amber pill on the section with their number, read out as "N need(s) a person"
- an amber dot on each item, read out as "Needs a person". In a list it takes the bullet's place; in a table it comes before the first cell's text.
- a key above the sections: "● needs a person"

These follow the Overview's definition exactly, so the numbers add up to the Overview's count: automated checks marked CHECK (other than "Nothing deferred by the executor"), every deferral by the AI, and the executor's deferrals by kind and page.

The veraPDF section says, in one sentence, how many WCAG rules failed before, by who can act on them (the AI, the pipeline, only a person), and how many after. review.md has it too.

### Colors and layout

- **Amber**, the page strip's "needs a person" color, is used only for that: at least 4.5:1 as text and 3:1 as a dot, in light and dark mode.
- **Source tags** (Ship condition, Automated check, Deferred by the AI, Deferred by the executor) are soft grey pills like the item badges, and so is summary.html's "No".
- **The "Safety" tag** is in the page strip's red, because a failed safety check means the PDF may have been damaged. It is at least 4.5:1 in light and dark mode.
- **Tables:** status, number, rule-ID, page and header cells don't wrap; other text wraps between words only. On a narrow screen a table scrolls sideways in its box, which is then a Tab stop.
- **Search:** a section with 20 items or more has a search box. It hides the rows and list items without the words typed, and says how many are shown.

### Lists and quoted text

Lists are shown in full in both review.md and review.html. The pages with text a screen reader could not reach are written as collapsed ranges, each end linked in review.html. Only when even the ranges would be very long does it show the first 25 pages and "… and N more".

Quoted text from the PDF is an excerpt of about 100 characters, ending at a word boundary with "…". review.html has a "show full text" button at the end of each: it opens the whole paragraph in a block below the line and becomes "hide full text". Without JavaScript the whole text is simply shown. A section search that matches only the hidden full text opens it. Alt text, the AI's sentences and veraPDF's rule descriptions are never cut.

### WCAG only

review.html reports WCAG only. It leaves out:
- veraPDF's PDF/UA-only rules
- PDF/UA-only notes, such as a file's own claim of PDF/UA conformance, which is then not counted under "Needs a person"
- PDF/UA wording: a WCAG rule whose veraPDF description speaks of PDF/UA is shown by a WCAG name

review.md keeps them all as the record.

## The Overview

`review.md` opens with an "Overview" block (called "At a glance" in runs made before 2026-10-21), and `_intake/intake.md` with its own.

- **Status:** Not Ready, Pending Evaluation, Ready or Shipped. Each is followed by "· N issues noted" when its version's evaluation has Fails. See [The status](release.md#the-status).
- **Ready to ship?** Four requirements: **Work Order Approval**, **OCR Text Approval**, **Safety Checks** and **Accessibility Evaluation** (see [The four requirements](#the-four-requirements)).
- **Safety checks:** pages look the same, text unchanged, all content tagged or decoration, the tag-tree index points into the tree, every font readable. Each reads "OK ✔" or "FAILED ✘", never color alone.
- **Needs a person:** the AI's deferrals, plus the executor's deferrals, plus CHECK rows (see [What "needs a person" counts](#what-needs-a-person-counts)).
- **AI decisions:** every entry in the work order. Deferrals and the note to the reviewer are not decisions. It reads "approved by NAME on DATE" once the review page has approved it.
- **Fixed automatically (no AI):** the executor's own fixes, by kind: links tied and described, note IDs, tag-tree index entries, standard tags un-remapped, empty tags, decorative lines, tab order, font maps, and others. There is no total, because several touch the same link.
- **Top issues:** safety failures first, then the ship conditions (OCR text, the review), CHECK rows, the executor's deferrals and the AI's. review.md shows five and "… and N more"; the dashboard shows all of them. Each points to its review.md section.

**intake.md's Overview** gives the result, what needs a person, the OCR verdict, and "Is the existing text trustworthy?". That last part says how many sample pages were read by OCR and compared with the PDF's own text, the typical (median) match, the best and worst pages, and the pages over 5% and 15%, with how to read the numbers.

### The four requirements

Each line reads "- ✓ Name: Value (details)" when satisfied, else "- Name: Value (details)". A PDF is ready only when:

1. **Work Order Approval:** the work order was approved on the review page (`REVIEW=1`; see [Sign-off](review-finish.md#sign-off-when-a-pdf-is-ready-to-ship)).
2. **OCR Text Approval:** the OCR text was approved, when intake added OCR text, found the PDF's existing OCR layer doubtful, unusable or missing diacritics, or could not check it because no sample page could be scored. An unknown layer is not "not needed" (decided 2026-10-25). A PDF with no OCR text added and no flagged OCR layer shows "Not Applicable"; that includes a publisher's own OCR layer that the test checked and did not flag.
3. **Safety Checks:** the five safety checks are OK.
4. **Accessibility Evaluation:** both parts (PAC 2026 and the screen-reader test) are recorded for this version of the PDF (from 2026-11). A Fail never blocks: it is an issue noted. It reads "Not Completed" when neither part is recorded, and names the part that is missing when one is: "Not Completed (Screen-Reader Test not recorded)".

### What "needs a person" counts

- the AI's deferrals
- the executor's deferrals, counted by kind and page: 13 captions on 4 pages count 4, and all Han-only runs count 1
- CHECK rows, leaving out "Nothing deferred by the executor", which only points at that list

One item can be counted twice when a CHECK row and a deferral describe the same failure, for example veraPDF 7.1-3 and the AI's deferral about it.

### When the Overview changes

An OCR text verdict or an evaluation result refreshes all of it, since "Ready to ship?" depends on them. The verdict is recorded on the review page or with `review_ocr.py`; evaluation results on the app's page or with `manual_checks.py`.

### Older runs

- From 2026-11, review.md's headings are in Title Case ("## Automated Checks", "## For a Person to Check", "### 1. Intake: OCR and Auto-tagging"). Runs made before keep theirs, and every reader accepts both. Section anchors are lower case, so links do not change.
- The work-order row says "accepted without review" (the stored count is still `accepted_unreviewed`), and the OCR row names the review page's OCR Text section as well as `review_ocr.py`.
- From 2026-11, "**Ready to ship?**" stands alone, because the status carries the answer. It comes as `**Status:** …` above "**Ready to ship?**", never between it and its lines. Older runs keep "**Ready to ship?** Yes/No".
- Runs made on 2026-10-31 by the branch's first stage also listed "no WCAG rule newly failing (veraPDF)" as a safety check. From 2026-11 that is a finding at the top of the top issues, not a safety check.

## Batch and app files

A batch folder also holds `summary.md` and `summary.html`: one row per PDF (ready to ship, needs a person, AI decisions, safety, veraPDF WCAG rules before → after, cost, pages). Rows are sorted with the most work first, and can be sorted by any column; each PDF's name opens its `review.html`.

To rebuild the dashboards of a finished run or batch:

```bash
python3 report_html.py <run>
python3 report_html.py --summary <batch>
```

The app ([The app](app.md)) keeps its own files in `runs/.app/`, never in a run folder:
- `jobs/<id>.json` and `<id>.log`: each job's command, the environment it was given, its status and times, and its output
- `dispatch.lock`: the queue's lock
- `sha256-cache.json`: sha256s of the PDFs in `samples/`, by path, size and time, for finding a run's original
- `server.log`: errors in the app itself

## For developers

### record.json

`record.json` holds everything vital in one file:

- the source fingerprint, model, prompt version and tokens
- the cost: `cost_total_usd` is what this run spent, $0 for a `FROM=` or test-mode reply. A reply this folder paid for and read again keeps its cost.
- the AI request behind the work order (`ai_call`, see below)
- the full work order; what was applied, rejected and deferred; the verification results; and the AI's raw reply
- `review.md`'s content as data (`sections`, with `sections_version: 1`)

**`ai_call`** holds `cost_usd`, `cost_per_page_usd`, `model`, `prompt_file`, `prompt_sha256`, `date` and `reused`. For a reused reply it is the original call's, also kept as `run.original_call` so a later re-apply still has it. The cost is `null` when none is kept anywhere; see `lib/origin.py`.

**`sections`** holds every line of every section as an item: its id, its kind (paragraph, list item, table row), its pages where known, and the parts that only PDF/UA requires. `review.md` and `review.html` are both drawn from it. The whole texts that review.html's "show full text" opens are kept in `sections`, `full`.

`apply.py` accepts `record.json` in place of a work order, to re-apply a run.

**The Overview's numbers** are computed once (`lib/glance.py`; for intake, `intake.py`) and kept in `record.json` as `glance`. Intake's are in `intake.json`, and so in `record.json` under `intake`. That way review.md, review.html and summary.html always agree.

**Refreshing after a verdict.** The OCR verdict goes through `review/ocr.py`, and evaluation results through `review/manual.py`. Each changes the OCR row in `record.json`'s `sections`, recomputes the glance, and draws `review.md` and `review.html` again. For a run made before `sections` existed (no `sections_version`), it edits `review.md`'s text instead, and `report_html.py` reads `review.md` to build the dashboard.

### Reviewed runs in record.json

Reviewed runs only. `review.md` adds a checks row and a "Work order reviewed by a person" section, and `record.json` adds:

- `review.workorder`: who reviewed the work order, when, and every change from the AI's version
- `review.session`: the session this result comes from
- `review.sessions` and `review.decisions`: the sessions, and each decision's review status, including the review page's reading-order checks (`reading_order:*`), marked seen with the reviewer's note
- `review.run_id`: the run's id from `reviews/basis.json`, also the review page's browser-draft key
- `review.run`: the run folder relative to `pipeline/`, for the reopen command
- `workorder_ai`: the AI's version, kept on every reviewed run whether or not the reviewer changed anything (before 2026-10-27, only when something changed)
- `review.pending`: set while a later session is finished but not applied (`session`, `status`, `since`, `reviewer`). Its "Work Order Approval" is then "Not Approved (Session N is finished but not applied)", so the PDF is Not Ready. It goes when that session is applied.

See [Reviewing the work order](review-step.md).

### The reviews folder

Every run keeps `reviews/`, so the run can be reviewed again after code changes:

- `basis.json`: the run id, the input PDF's path and sha256, the digest's fingerprint, and the AI order's sha256
- `_audit/`, which holds:
  - `digest.json` (46–355 KB in the 19 test books). Its `low_resolution` list (figures under 150 ppi) is for the report and the review page only; the AI never sees it (see [Editing the PDF by hand](hand-edits.md#for-developers))
  - `fulltext.json`: the whole texts review.md quotes, local only, 4–186 KB
  - the OCR word sheets of a scanned PDF
  - for a reviewed run, `dryrun.json` (below)
  - never the figure crops

**`dryrun.json`** records the figure moves a trial run of `apply.py` found at the review stop, and what it did with the AI's section move (`section_move`: made, with where, or refused, with why). It carries the fingerprint of what it depended on (`key`: the input PDF's sha256, the order's, the code's, the package versions and the settings), so a later review reuses it while that still matches.

Reviewed runs also keep:
- `workorder.ai.json`
- `sessions/NNN.json` and `NNN.workorder.json`: each review session and the order it applied
- `versions/<id>/`: each previous result (PDF, record.json, review.md, review.html), never edited except a "replaced by" note on review.html

The top level always holds the current result. See [Reviewing again](review-again.md#reviewing-again).

### The release folder

`release/` is never moved by a re-apply. It holds:

- `checks.json`: the accessibility evaluation's results
- `drafts.json`: the evaluation page's unfinished answers, never counted and never mirrored into record.json
- `removed.json`: the previous versions whose PDF "Clean Up Space" took (version, sha256, size, who, when)
- `shipped.json` and `shipped/NNN/`: each shipment. That is the PDF copy, review.md and review.html as shipped, the evaluation results, a read-me, and record.json for the archive only (never served or zipped).

See [Accessibility evaluation and release](release.md).

### Intake files

Untagged originals only.

**`_intake/intake.json`** records what intake measured and did: page triage, text-layer test scores, OCR language, OCR pages, tool versions and every check. It also holds:
- `tag_tree` for a placeholder tag tree, with the publisher's alt text it held
- `ocr_layer_test` for an existing OCR layer on scanned pages
- `spreads` for pages holding two printed pages

It is also in `record.json` under `intake`.

**`_intake/intake.md`** is the intake record in plain words: status, pages OCR'd, picture pages, CHECKs and notes with their pages, and the OCR review verdict. It is written for every outcome, also by `intake.py <pdf> <dir>` on its own and by `--plan-only`.

**`_intake/intake.pdf`** is kept so `FROM=` reruns apply saved replies to the very same file.

### Hand-edit files

A run made from a PDF edited by hand (`handedit.py import`) keeps in `_handedit/`:
- a copy of the edited file: the run's source
- `input.pdf`: the same with the old alt text removed from each figure whose image changed. This is what the run worked on.
- `hand_edit.json`: the link to the run it came from, who, when, the note, and both sha256s. It is also in `record.json` as `hand_edit`.

`hand_edits.json` lists each export (who, when, sha256, where to) and each run made from an edit. See [Editing the PDF by hand](hand-edits.md).

### `record.json` figure requests (PDFs with more than 100 images)

Only when the run made figure requests ("Figure requests" in [Files](files.md)). A single-request run has none of these keys, and its records are as before.

| Field | What it is |
|---|---|
| `run.usage`, `cost_total_usd` | The sum of every request: the first, the figure requests and their retries |
| `run.passes` | One entry per request (see [run.passes](#runpasses)) |
| `run.figure_passes` | The figure requests as a whole (see [run.figure_passes](#runfigure_passes)) |
| `run.estimate.passes` | Each request's images, input tokens and worst case. `worst_case_total_usd` is their sum: the "Max Estimated Cost" shown, which a retry after a cut-off doesn't change. `book_cap_usd` is the limit per PDF |
| `run.estimate.expected` | A paid run only (never `FROM=` or `REPLY=`): the "Expected Cost" shown before sending (`usd`, `low`, `high`, `basis` with `calls` and `books`), or `none` with the reason. Left out of the estimate's fingerprint, like the credit |
| `raw_reply_passes` | The saved form of the figure requests (see [raw_reply_passes](#raw_reply_passes)) |
| `ai_call.calls`, `ai_call.figure_prompt_file` | How many requests the cost covers, and the figure requests' prompt (`lib/origin.py`) |
| `earlier_attempts` entries with `pass` and `stopped` | The requests of a run that was stopped while its figure requests were being sent (see [earlier_attempts](#earlier_attempts)) |
| `run.own_reply` | `true` when the saved reply was this folder's own paid `response.json`, read again (see [run.own_reply](#runown_reply)) |

#### run.passes

One entry per request:
- `pass`: `"1"`, `"2"`, …, or `"probe"`
- its images, `usage` and `seconds`
- for a figure request: its figures (`objs`: `[obj, page, width, height]`), each call (`calls`: retries included, with its `max_tokens`, the error when there was one, and `doubled` on a retry with twice the room), and `outcome` (`done` or `failed`, with `reason`)

The first request's entry carries the note it was given (`note`: version and hash). The probe's carries `overlap`: each figure's alt text from the first request and from the probe.

#### run.figure_passes

- `requests`, and `figures`: how many went to figure requests
- `prompt_file` and `prompt_sha256` (`figures_v1.md`), and `note`
- `state`: `calling` while they are sent, `merged` when done
- `fingerprint`: of the saved split
- `cut_off_retries`: each request sent again with twice the room after a cut-off (`pass`, `max_tokens`, `cost_usd`, `outcome`)
- `failed` (`{request: reason}`), or on a replay `stale`: requests whose saved answers were written for a different figure list

#### raw_reply_passes

The saved form (format `figure-passes/1`): the first request's figures and sheets, the note, and each figure request's figures, fingerprint, answer and call. A replay uses it as recorded. `FROM=`, `regression.py --seed` and `--replay-to` write it beside the reply as `reply.txt.passes.json`, with `figure_passes` in the reply's meta.

#### earlier_attempts

For a run stopped while its figure requests were being sent: each request's cost, and the one in flight with `cost_usd: null`, because its charge is not known.

`worst_usd`, on that entry and on a request with a timed-out call, is the worst case of the charge not known. It counts toward the PDF's limit on the next attempt, never in the cost shown.

When the in-flight call was a retry, what its request had already been charged is a row of its own, with `cost_usd` known and, after a cut-off, `finish_reason: length`. A request with a cut-off among its calls is logged with `finish_reason: length`.

#### run.own_reply

`true` when the saved reply was this folder's own paid `response.json`, read again after a later step failed or after it couldn't be read. It is decided when the reply is read, and stored, so moving or copying the folder doesn't change it. The money counts as this run's everywhere the cost is shown, and the estimate shown before it is kept.

It is absent on `FROM=` reruns, test-mode replies and a reply from another folder, which cost nothing here. review.md stays as for any reused reply.

### `record.json` `run.ocr_words` (scanned PDFs with OCR words)

Only when the audit lists OCR-word forms ([OCR words](ocr-words.md)); other PDFs have just the counts.

| Field | What it is |
|---|---|
| `forms`, `sent`, `sheets`, `not_sent`, `not_found_by_audit` | Today's audit: forms listed, forms whose word sheet was sent, sheets, forms over the image limit, forms past the audit's cap |
| `fingerprint` | A hash of today's list of sent forms (id and form) |
| `list` | That list itself, `{id: form}` (from 2026-10-27), so a later change could re-match a reply's readings by form |
| `reply_fingerprint`, `reply_read`, `reply_list` | A reused reply only (`REPLY=`, `FROM=`, the regression test): the fingerprint, size and list of the word list the reply was written for, as far as they were recorded with it. None for replies made before the fingerprint; `reply_read` comes from the earlier record's `sent` |
| `reply_check` | A reused reply only: `same list` (its readings are used), or `list changed` / `no fingerprint` followed by `: readings dropped` or `: the reply gave no readings` |
| `reply_check_why` | The reason in words, e.g. "the word list changed since (4 forms then, 8 now)"; review.md quotes it |
| `reply_readings_dropped` | How many readings were not used |
