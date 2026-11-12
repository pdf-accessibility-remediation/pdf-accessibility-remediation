---
title: Using the review page
parent: Reviewing the work order
grand_parent: Review and ship
nav_order: 1
---

# Using the review page

This page walks a reviewer through one review on the review page: the steps from the run's stop to the reviewed result, what each part of the page shows, the checks it makes as you go, adding a decision the AI did not make, and the gaps to answer before finishing. Internals are at the end, under [For developers](#for-developers).

## Steps

```bash
cd pipeline
REVIEW=1 bash run_api.sh ../samples/tagged/teika.pdf teika rv1       # intake, audit, the AI's decisions; then it stops
python3 app.py ../runs/teika/rv1                                      # the run page: "Open the Review Page"; "Finish Review" applies
```

Or, all in the terminal:

```bash
python3 review_workorder.py ../runs/teika/rv1 --serve                # the review page, in your browser
bash run_api.sh ../samples/tagged/teika.pdf teika rv1                # same label, without REVIEW=1: apply, verify, report
```

### 1. The run stops

The run keeps the AI's work order and lists its decisions for the review page. Nothing has been applied yet. Its message leads with the app (`Open the run page to review and apply: python3 …/app.py <run>`), then gives the two terminal commands as the fallback.

**From the app:** the run page of a run stopped here says nothing has been applied yet, and offers **Open the Review Page** (the `--serve` command below, with **Back to the Run Page** on the review page). After **Finish Review** it goes back to the run page, which offers **Apply**: the second call of `run_api.sh` itself (step 4).

When the apply ends, **Show the Result** loads the run's first report; from then on it is a finished run's page. Until the first apply, the run page offers nothing else: no evaluation, downloads or shipping, because there is no result yet.

### 2. Open the review page

`--serve` opens the review page at `http://localhost:8765/`. It runs on this computer only. On WSL, open the printed link in a Windows browser. The terminal must stay open while you review.

Ctrl+C stops it without finishing. Your choices are saved to `review_decisions.json` as you make them (and kept in the browser too), so running the command again carries on where you left off.

### 3. Review the decisions

Enter your name, then go through the cards. Each decision has **Approve**, **Change** or **Reject**, and a note. Deferrals and the AI's note to the reviewer have **Seen** only, because nothing applies them. **Add a decision** adds what the AI left out (see [Adding a decision](#adding-a-decision)).

- **Saving is automatic;** there is no Save button (see [Saving](#saving)).
- **Each choice is checked as it is saved,** with the same rules `decide.py` uses on the AI's reply (see [Checks as you go](#checks-as-you-go)). A choice the check doesn't accept is marked on its card, with a message under the field saying what to change. An example is `english` as a language, which is not a language tag. **Finish Review** refuses while any choice needs fixing.
- **Session Name** (in the header, prefilled "Session N") and **Session Notes (optional)** (the first section of the column) are for a review that takes several sittings or passes to another person: where you stopped, what to check next. See [Session names and notes](#session-names-and-notes).

**Finish Review** opens a dialog first:
- the session's name and notes, for a last edit
- how many decisions are not reviewed. Finishing records those as *accepted without review*; **Show "Not Reviewed"** lists them instead, with a message that stays until its × dismisses it.
- the check once more, before anything is applied: each choice that needs fixing, with a link to its card (the link closes the dialog and goes there); choices left out because no card holds them; and any **gaps**, things still missing once the review is applied (see [Gaps](#gaps)). If gaps are open, the dialog asks for a reason for each, or you can go back and add what is missing.

While a choice needs fixing, the dialog's **Finish Review** button is turned off. The dialog's text puts the names of buttons, views and sections in quotes, as they appear on screen. **Finish Review** in the dialog records the review and stops the server.

**The header:**
- **Back to the Run Page** (from the app) looks like a button and is a link.
- **Hide Header** (bottom right) folds the header away for more room; **Show Header** (top right) brings it back. Each says to screen readers whether the header is shown, and this browser remembers the choice.
- The status line of a review again says where the session started, and "OCR Text: Approved" (the verdict by its choice's name).

### 4. Apply the reviewed work order

Rerun the same command: same label, no `REVIEW=1`. From the app, "Finish Review" applies at once: the app starts this same command by itself (#45), and the run page follows it. After the review page's Finish from the terminal, its `next:` line names both the app's run page and this command.

`decide.py` is skipped (no AI request) and the reviewed `workorder.json` is applied. Intake is not run again: the reviewed order is applied to the intake result saved before the stop (`_intake/intake.pdf`, or the original for a tagged PDF), the one the decisions were made on. The original given must be the same file (its sha256 is checked against `_intake/intake.json`), and `apply.py` checks the input against the work order's `source.sha256`.

### Good to know

- **Until the review is finished, rerunning the label is refused,** so a half-reviewed work order never reaches `apply.py`.
- **Batches** (`batch_api.sh`) pass `REVIEW=1` to every PDF (#45). Each stops for review, summary.md lists it as waiting for review, and `RETRY=1` never runs it again.
- **Every run the app starts sets `REVIEW=1`** ([Review is always on in the app](app-run-page.md#review-is-always-on-in-the-app)). From a terminal it stays optional.
- **The first review is kept as session 1** in the run's `reviews/` folder (see [Reviewing again](review-again.md#reviewing-again)).

## Session names and notes

**The name** is in the header, prefilled "Session N". A name that is only "Session N" (in any case or spacing), or empty, is recorded as no name, so the session is shown as "Session N". Otherwise it is shown after the number: "Session 5: Chapters 1–4".

**The notes** (optional, no example text in the box) are the first section of the column, headed **Session Notes (optional)**; the heading is the box's label.

**Session Notes** in the header opens the same note in a notepad beside the page:
- It is not modal. Move it by its title bar; resize it from its corner.
- Typing in either box updates both, and it is saved as before.
- **–** shrinks it to a small **Session Notes** button at the bottom right, which brings it back.
- × or Escape closes it, and focus goes back to the header's button.

Text boxes on the page grow taller when dragged, never wider than their place.

### Where the name and notes are kept

- In the browser on every key, and in the run by the automatic save, about half a second after each change or at once when you leave its card. The browser's copy is per page address, and the review page's port can change.
- With Finish.

**Continue Review** (the same open session) brings them back, editable.

**Reviewing again** from a session (**Review Again**, or **Review Again from Session N**) shows that session's name and notes read-only, folded under **Notes from Session N**. The new session starts as "Session M" with empty notes. **Start Over from the AI's Decisions** shows none. **Discarded sessions** keep their name and notes.

### Where they are shown

- Session History on the run page: the name under the session's number, and a **Notes** button
- `review.html`: the current session's line with a **Session Notes** button right under it, and a **Notes** button in the session table
- `--sessions` in the terminal

They are not in `review.md`.

**Order:** Session History and the report's **Previous Sessions** list the newest session first. Where a session started reads "Session 1".

**Long names** in those tables stay on one line up to about 40 characters. A longer one wraps at spaces in a column at most about 26em wide; only a single word too long for it breaks. A name is never cut short with "…".

### The notes boxes

**Notes** opens a session's notes, read-only, in a pop-up box beside the page. It is not modal: the page stays usable.
- There is one box per session, and several can be open at once. Opening one that is already open brings it to the front.
- Drag its title bar to move it, and its corner to resize it. The notes scroll inside it, so reading them never needs either.
- × or Escape closes it; Escape closes the box that has focus.
- Focus goes into the notes when it opens, and back to its own button when it closes.

**Plain text only:** at most 80 characters for the name (one line) and 4,000 for the notes. Control characters and direction overrides are removed. They are shown as typed, never as links or formatting.

## What the page shows

A run made from a PDF edited by hand ([Editing the PDF by hand](hand-edits.md)) starts with two more sections: **Edited by Hand** (a card for each figure the edit touched, with an **Add Alt Text** button) and a read-only **Earlier Review** (the decisions of the run it came from, already in the file).

There are three views of the decisions:
- **Check these first:** the decisions most worth checking (below).
- **All** lists every decision by kind.
- **Not reviewed** lists what is left.

A **page index** at the side lists the pages of the "check first" items. On a narrow screen the side list folds away behind a **Sections** button.

### Check these first

These are decisions in categories where a mistake is likely or affects much of the PDF. They are chosen by fixed rules (no AI), grouped in this order, and sorted by page within each group:

1. **H1 and title:** any decision that makes or unmakes an H1, and the document title.
2. **Style-wide mappings:** each `rolemap` entry, most elements first. One entry changes every element of that style.
3. **Heading-level changes:** a `retype` that changes a heading level, or turns a heading into body text or the reverse.
4. **Rules that can hide text:** artifact text rules and untagged rules, with their pattern and page range.
5. **Reading order** (see [The reading-order group](review-reading-order.md#the-reading-order-group)).
6. **Pages the AI asked about:** deferrals with a specific page range, and the AI's note when it names pages ("PDF 4").
7. **General:** deferrals with no pages, or covering more than half the PDF.

### The cards

Each card has labeled lines:
- **Page:** "PDF p. 2 (printed i)", or a page range
- **Decision type**
- the element, for example **Text on the page**
- **What this does:** a plain-language description of the effect, written by the page for each kind of decision, not by the AI
- **Change**, or **Original** and **AI's choice**
- **AI's reason:** the AI's own short `why`

Decoration rules are described in words (**Hides**, **Where on the page**, **Marked as**), with the AI's exact entry under a fold. An **AI confidence** below 1 is flagged on any kind of decision. The decision's ID (for example `retype:1154 0`: the kind of decision and the element's object number in the original PDF) is in small print at the bottom.

**Images:** every card with a page shows that page; heading decisions also show the pages either side. Alt text shows the figure crop. An OCR word shows the word cut from the scan, the same image the AI read. Page images are made the first time you scroll to them, so there is no limit on how many a PDF can have. Click an image to enlarge it.

**A figure drawn at a low resolution** (under 150 ppi) has an **Image Resolution** line on its alt text card, or on the card for adding its alt text. Write the alt text as usual: replacing the image is a hand edit, done after the review (see [Finding images that need a better copy](hand-edits.md#finding-images-that-need-a-better-copy)).

**An orphan-text card** shows the text no tag owns on its pages: up to six runs per page, from the audit.

### Changing a value

The box for a new value appears only when **Change** is selected. Edits are limited to valid values:

- a heading level from a list (H1–H6, P, Span, Caption, Note, Div), with a warning on a style mapping saying how many elements it changes
- alt text, spoken text and OCR readings as text
- the language from a list of named languages (English, English (US), Hawaiian, Japanese, …), or **Other**, which shows a box for a language tag such as `en-AU`. A tag that is not in the list opens under **Other**, kept exactly as it was.
- table header rows and columns from two lists, 0–3
- a section move's pages as page numbers (the boxes take digits only)

Artifact rules, reading-order decisions other than a section move, and the remaining keys (`sections`, `links` and the like) can only be approved or rejected. To edit a rule's pattern, edit `workorder.json` by hand (see [Without the page](review-again.md#without-the-page)).

**To undo a choice,** click the selected option again, or **Clear**: the decision goes back to not reviewed. Its note stays.

**When two decisions would each make an H1** (for example the AI's H1 and one you added), both cards are flagged.

### Saving

Every change (a decision, a note, the name, the notes) is saved to the run about half a second after it is made, and at once when you leave its card. The browser keeps a copy as a backup. When you open the page, whichever copy is newer is used; a newer browser copy is saved to the run at once.

The header says **All changes saved** or **Saving…**, right of **Finish Review**, in a fixed-width space so nothing moves when it changes. It is not announced. A failed save is announced, as an alert that says what to do.

**No edit is lost.** One save runs at a time; an edit made while a save is under way is carried by the next save, which sends the whole draft. A draft older than the one already on disk is never written over it. Stop or Ctrl+C while a save is being written waits for it: it is written whole.

**Leaving the page.** While a change hasn't reached the run yet, closing the tab or leaving the page first shows the browser's leave-page prompt. If you leave anyway, the last edits are sent as the page goes. A browser sends at most 64 KiB that way, so a very large draft (a big PDF fully decided, with long notes) may not be sent then. The browser's own copy still has it, and the review picks it up when opened again in the same browser at the same address.

## Checks as you go

Every save also runs the check: the same rules `decide.py` uses on the AI's reply (`lib/workorder_check.py`), on the order your choices make so far. Anything it would drop is shown on the card it belongs to.

- **Under the field.** A message says what is wrong and what to do, for example "Choose a language from the list, or choose Other and type a language tag such as en-US or haw."
- **For screen readers,** the field is marked invalid and the message is tied to it, so it is read when the field has focus. When the card's value is not shown (the choice is **Approve**), the message is tied to the card's choices instead. For a section move, only the page box that is wrong is marked.
- **Not while you type.** A new message waits until you leave the card, or stop typing for about a second, so a half-typed page number is not flagged. Leaving the card (Tab, or a click elsewhere) saves your change at once, so its message shows almost immediately. A problem you fix clears at once.
- **Choices that clash** are a conflict: each card involved shows the message, with links to the others. Examples: two section moves whose pages overlap, a table that is both given headers and flattened, an addition the AI already decided.
- **Choices you didn't make.** The check can flag one of the AI's choices that you never touched (it judges section moves against the full reading order), or a choice carried over from an earlier session that is no longer accepted. Its message adds "reject it to continue, or change it". **Reject** is on the card.
- **Choices left out.** A choice the check doesn't accept but that no card holds (for example a page number in one of the AI's deferrals) is listed as left out. It is not applied, as before, and it never stops **Finish Review**.

**The line beside Finish Review** counts what the cards show and the gaps, for example "2 choices need fixing · 1 conflict · 1 gap open", or "All choices can be applied". Screen readers announce it only when its words change. **Show Details** beside it lists everything, each with a link to its card (or the **Add** form, for a gap).

**Finish Review refuses** while any choice needs fixing or conflicts: the dialog's button is off. If a choice changed after the dialog opened, Finish says so and leaves the page as it was. Fix the value, or reject the choice.

## Adding a decision

The cards cover only what the AI decided. **Add a decision** (at the top) is for what it left out. Pick a kind, find the target by text, page or object number, and give a value and an optional note. The addition appears as a card under **Added by you**, where you can change its value or **Remove** it.

In a run made from a PDF edited by hand ([Editing the PDF by hand](hand-edits.md)), the **Edited by Hand** section opens with a summary of the edit, and has a card for each figure it touched. Its **Add Alt Text** button opens this form.

| Kind | What you can add it for | Value |
|---|---|---|
| Heading or tag change (`retype`) | an element the audit listed (headings, heading candidates, other elements) that the AI did not retype | a level from the list |
| Alt text (`alt`) | a figure with no alt text from the AI, including figures whose images were not sent | text |
| Alt text, whole page (`page_figures`) | a whole-page figure with no alt text from the AI | text |
| Table headers (`tables`) | a table the AI neither gave headers nor flattened | header rows and columns, 0–3 |
| Style mapping (`rolemap`) | a text style (mapped to a heading, P, Span and the like) the AI did not map | a level from the list |
| Document (`document`) | the title or language, when the AI did not set it | text, or a language tag |
| OCR words (`ocr_words`) | a word form the audit flagged that the AI gave no reading, including words whose sheet was not sent | the word as printed |
| Section move (`move_section`) | a section read out of its printed place that none of the AI's decisions takes care of and none of its moves covers, while the work order holds fewer than 3 moves | the pages to move and the page to read them before, with a preview |

For example, after changing a half-title (PDF 2) from H1 to P on its card, add a Heading or tag change for the title page (PDF 4) as H1.

- **A target the AI already decided is not in the list:** change it on its card.
- **A figure the AI marked as decoration needs that decision rejected first,** before alt text can be added; the form says so.
- **Additions go through the same checks as the AI's decisions,** except for the two rules about images the AI never saw. Those exist so the AI cannot describe a figure it did not see; you see the page. An addition is written in the AI's shape, with `why` "added by <name> in review", and appears in the record as `added`.
- **Only targets the audit listed can be chosen.** Artifact text rules (a pattern over a page range) and the remaining keys (`sections`, `toc` and the like) cannot be added on the page; edit `workorder.json` by hand (see [Without the page](review-again.md#without-the-page)).

## Gaps

In the Finish dialog and at **Finish**, the work order as it would be applied is checked for things that are still missing. Gaps don't block the review: you can add what is missing, or finish and give a reason.

- **H1:** no element would be an H1, or more than one would. The count combines style mappings and single-element retypes. It is approximate, because the audit lists element counts per style; `review.md` has the exact count after the run.
- **Figures without alt text** that are not marked as decoration. A figure past the first request's 100 images gets its alt text from a figure request (see [Files](files.md)). What is left are figures whose figure request did not finish, or every figure past 100 with `FIGURE_PASSES=off` (in an earlier test book that was 443 of 543 figures). The alt texts the figure requests wrote are decisions on the page like any other.
- **Whole-page figures without alt text.**

The line beside **Finish Review** counts the open gaps ("1 gap open"). The Finish dialog lists each gap with an **Add** link that closes the dialog and opens the form at the right kind.

At **Finish**, each open gap needs a reason. The reasons are recorded and listed in `review.md`. An explained gap counts as handled, so the review's row stays OK. A hand edit recorded without `--note` gives no reason, so its gaps make the row a CHECK.

## For developers

### Files kept at the review stop

When the run stops, it keeps:
- `workorder.ai.json`: the AI's work order
- `review_items.json`: the decisions listed for the review page
- `timing.json`: the time of each step so far. The second call adds its own, so the record has the whole run's.
- `review_stop.json`: what the app's **Apply** needs to run the same second call. That is the original's path, the name and the settings it was run with (`OCR_LANG`, `INTAKE_REUSE`, `INTAKE` and `OUT`). The report removes it.

The app's Apply runs the second call in the run's own folder (`RUN_DIR`). It finds the original from `review_stop.json`, or, if that file has moved, by its sha256 in the folder of original PDFs or of uploads.

Saving uses `POST /keep`, under the server's write lock. One review at a time is enforced by `reviews/.lock`, held from the moment the page opens until the re-apply ends.

### Where the review is recorded

- **`review.json`**, folded into `record.json` as `review.workorder`, holds:
  - the reviewer, the date, and `method` (`page` or `hand-edit`)
  - every change: `where`, `id`, `changed` / `removed` / `added`, the AI's value and the reviewer's
  - edits not accepted by the check
  - counts: approved, changed, rejected, seen, accepted without review, added
  - gaps left open with the reviewer's reason (`gaps`)
  - the reviewer's notes (an addition's note is keyed `add:<kind>:<target>`)
  - earlier reviews under `history`

  A decision marked **Change** but left at the AI's value counts as approved.
- **`record.json`** also keeps:
  - the AI's version as `workorder_ai`. `workorder` is what was applied, and carries `reviewed_by`.
  - `review.session`: the session this result comes from
  - `review.sessions`: one line per session (who, when, from where, status, counts, how many choices were carried and from where, how many changed in the session)
  - `review.decisions`: one line per decision (its review status, the session that set it, `inferred`, its note), which `review.html` shows. Reading-order check notes are recorded here too.
- **`reviews/sessions/NNN.json`** holds each session in full: every choice with the AI value it was judged against and the session that set it, additions, what changed since the session's start, the review as `review.json` had it, and the OCR verdict at Finish. `NNN.workorder.json` is the order it applied.
- **`reviews/basis.json`** holds the run id (the page's browser-draft key), the input PDF's path and sha256, the digest's fingerprint and the AI order's sha256.
- **Session names and notes** are recorded in `reviews/sessions/NNN.json` (`name`, `notes`, only when set) and `record.json` `review.sessions`. They are not in `review.json` or the work order. They are kept in `review_decisions.json` by the automatic save.

Reading-order check IDs are `reading_order:away:<section>`, `reading_order:jump:<page>`, `reading_order:figures` (approved or rejected, not marked seen) and `reading_order:late`.

### For a front end later

The logic is in `pipeline/review/core.py`, apart from the web layer (`server.py`, `page.html`). A front end can call `core.py` and replace those two files. The contract is two JSON formats:

- **Items** (`review_items.json`, from `core.build_items`): `{id, key, kind, label, page, page_label, pages, before, ai, edit, options, context, priority, images, loc, field}`.
  - `id` is stable for a given AI work order (`retype:1154 0`, `rolemap:H4`, `alt:4081 0`, `document.title`, `artifacts.text_rules:0`, `deferrals:2`, `key:sections`).
  - `edit` is `level`, `text`, `lang`, `table` or null (approve or reject only).
- **Decisions** (`review_decisions.json`, taken by `core.apply_decisions`): `{id: {status: approved | changed | rejected | seen, value?, note?}}`. `value` has the item's `ai` shape.
- **Addable targets** (`review_items.json` → `addable`, from `core.addable`): `{kind: [{id, kind, target, label, page, page_label, before, default, edit, options, context, images}]}`. `id` is `add:<kind>:<target>`, for example `add:retype:1155 0`.
- **Additions** (`review_decisions.json` → `additions`, taken by `core.add_entries`): `[{kind, target, value, note?}]`. `value` has the target's `default` shape. `add_entries` returns what it refused, `[{id, why}]`.
- **Problems** (`core.problems(R, ai_wo, items, decisions, additions, adds, reviewer, set_in)`, returned by `/keep`, `/save` and a refused `/finish` as `problems`): `{fields: [{card, why, fix, origin, parts?}], conflicts: [{cards, why, fix, origin}], unplaced: [{where, why, fix}]}`.
  - `why` is the check's reason as recorded, and `fix` what to do in plain words (`core.FIX`).
  - `origin` is `review`, `earlier` or `ai`.
  - `parts` names a move's wrong page boxes (`a`, `b`, `before_page`).
  - `/finish` answers `needs: "invalid"` while `fields` or `conflicts` is non-empty; `unplaced` never blocks it.
  - `core.problems` also returns the gaps, so the check runs once per save.
- **Gaps** (`core.gaps` on the checked order, or `core.preview` for the check and the gaps together): `[{id: h1 | figures_without_alt | page_figures_without_alt, what, add?: {kind, target?}}]`. `core.finish` takes the reasons as `gaps_ack: {id: reason}`.
- `review_decisions.json` also holds `saved_at` (the browser's time of the last change, used to pick the newer copy), and `session_name` and `session_notes` when set (`core.session_fields` cleans them and checks the limits).
- `POST /keep` takes the same body as `/save` and only writes `review_decisions.json`; the page sends it when the name or notes lose focus. The server writes one request at a time, and refuses `/keep` and `/save` once Finish has started.
- The server answers only to itself: the `Host` must be `localhost` or `127.0.0.1` on its port, and a POST must be `application/json` from the page's own origin. Another web page open in the browser cannot submit a review, and cannot show the review page inside a frame of its own: every response says `X-Frame-Options: DENY` and `frame-ancestors 'none'`.
