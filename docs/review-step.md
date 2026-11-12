---
title: Reviewing the work order
parent: Review and ship
nav_order: 3
---

# Reviewing the work order before it is applied

With `REVIEW=1`, a run stops after the AI's decisions and before `apply.py`. A reviewer then checks the work order, approving, changing or rejecting each decision, and the run goes on with the reviewed version. Without `REVIEW=1`, runs work as before.

The review is for decisions where a wrong answer still passes every automated check. For example, one of the earlier sample books had its half-title (PDF 2) tagged as P under prompt v7 and as H1 under v8. Both versions pass "exactly one H1"; only a person looking at the pages can tell which is right.

This page covers the review page from start to finish: the steps, reviewing a run again, each part of the page, and its limits. Internals are at the end, under [For developers](#for-developers).

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
- **Every run the app starts sets `REVIEW=1`** ([The app](app.md)). From a terminal it stays optional.
- **The first review is kept as session 1** in the run's `reviews/` folder (see [Reviewing again](#reviewing-again)).

## From the browser

`python3 app.py <run folder>` opens a finished run's page with buttons for everything below: **Review Again**, **Start Over from the AI's Decisions**, **Review Again from Session N**, **Apply Session N** and **Session History**. Each button runs the command shown here. See [The app](app.md); the commands below work as before.

**Finish** goes back to the run page, which shows the re-apply. When it ends, the page says "New result ready" and a **Show the New Result** button loads it; the page never reloads by itself. Ctrl+C on the review page while Finish is being recorded waits until the review is recorded.

## Reviewing again

A finished run, with or without `REVIEW=1`, can be reviewed again. The page opens with every earlier choice preloaded, you change only what is needed, and Finish applies the reviewed order at once, with no AI request. The result is a new remediated PDF, `review.md` and `review.html`. Nothing earlier is overwritten.

```bash
cd pipeline
python3 review_workorder.py ../runs/teika/rv1 --reopen                # the latest session's choices, preloaded
python3 review_workorder.py ../runs/teika/rv1 --reopen --from 1       # start from an earlier session (--from ai: the AI's decisions)
python3 review_workorder.py ../runs/teika/rv1 --sessions              # every session: who, when, from where, what changed, which is current
python3 review_workorder.py ../runs/teika/rv1 --apply                 # apply a finished session that was not applied (--no-apply, or a failed apply)
```

`--return-to URL` (with `--serve` or `--reopen`) makes the review page go to that page after Finish, and link back to it. The app passes its run page. Only `http://127.0.0.1:<port>/…` or `http://localhost:<port>/…` is accepted.

### What the page shows

The page says which session it is, where it started, how many choices were preloaded, and any that could not be carried. Each preloaded card says which session set its choice.

The page links the current result's `review.html`, served by the review server, because a browser cannot open a local file from the page. It keeps the gap reasons given last time.

### Finishing a review again

**Finish** records the session and applies it: apply, verify and report run in the terminal, each with its time. `--no-apply` stops after Finish.

The current result moves to `reviews/versions/<session>/` (or `versions/ai/` for a result applied without review) only after all three succeed. If one fails, the current result is unchanged and the session stays *finished*: run `--apply` again.

Until the session is applied, "Ready to ship?" says **No** ("the latest review … is finished but not applied"), because the PDF on disk is older than the sign-off.

### One review at a time

Only one review of a run can be open at a time. Ctrl+C leaves the session *open*, and `--reopen` carries on with it.

`--reopen --from N` while a session is open is refused, unless you add `--discard-open`: the open session is kept, marked *abandoned*. `--discard-open` on its own does only that: the open session is marked abandoned and no new one is opened, and the current result does not change.

### The OCR text verdict

There is one OCR text verdict per run (the latest wins), and reopening never rolls it back. It is recorded on its own under **OCR Text** (see [The OCR text](#the-ocr-text)), not with Finish. Finish keeps a copy of the verdict in force in the session record.

### Older runs and runs that can't be reviewed again

A session is opened and applied only when the input PDF, the kept digest and the AI's order are exactly the ones the run was made with. Anything else is refused, never re-matched (see [Exactness](#exactness)).

**Runs finished before every run kept its digest** need it pinned once:

```bash
python3 review_workorder.py <run> --pin [--pdf <original.pdf>]
```

This re-audits the run's input (free, no AI request), checks the digest against the record, and keeps it. A PDF with no intake result needs `--pdf` (its sha256 is checked). `--reopen` pins first by itself. If today's audit no longer matches (because the audit code, veraPDF or Python changed), the run cannot be reviewed again. More in [Pinning](#pinning).

**When a run cannot be reviewed again** (the pin is refused, or the kept digest cannot be read), the fallback is a new run of the PDF from its saved reply, on today's code. It is not a review of the old result: the audit, the checks and the result are today's.

The app's run page says this in plain words ("This run can't be reviewed again: the pipeline has changed since it was made. A new run of the book from its saved AI reply is needed …"). The commands are in the job's log, and in [Replaying a saved reply](#replaying-a-saved-reply).

**Reviews made before sessions were kept** become session 1, *summary only*: "Session 1 (summary only): 159 approved, 8 seen, no changes; per-decision choices were not recorded before 2026-10-27". When nothing was accepted without review, each card's choice is rebuilt from the recorded changes. Those cards show "approved (inferred)" and point to session 1. Otherwise the new session starts from the AI's decisions, with the summary on the page.

**Batches:** re-applying a PDF in a batch folder rebuilds the batch's `summary.html`; `summary.md` stays as the batch run wrote it.

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
5. **Reading order** (see [The reading-order group](#the-reading-order-group)).
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

**An orphan-text card** shows the text no tag owns on its pages: up to six runs per page, from the audit.

### Changing a value

The box for a new value appears only when **Change** is selected. Edits are limited to valid values:

- a heading level from a list (H1–H6, P, Span, Caption, Note, Div), with a warning on a style mapping saying how many elements it changes
- alt text, spoken text and OCR readings as text
- the language from a list of named languages (English, English (US), Hawaiian, Japanese, …), or **Other**, which shows a box for a language tag such as `en-AU`. A tag that is not in the list opens under **Other**, kept exactly as it was.
- table header rows and columns from two lists, 0–3
- a section move's pages as page numbers (the boxes take digits only)

Artifact rules, reading-order decisions other than a section move, and the remaining keys (`sections`, `links` and the like) can only be approved or rejected. To edit a rule's pattern, edit `workorder.json` by hand (see [Without the page](#without-the-page)).

**To undo a choice,** click the selected option again, or **Clear**: the decision goes back to not reviewed. Its note stays.

**When two decisions would each make an H1** (for example the AI's H1 and one you added), both cards are flagged.

### Saving

Every change (a decision, a note, the name, the notes) is saved to the run about half a second after it is made, and at once when you leave its card. The browser keeps a copy as a backup. When you open the page, whichever copy is newer is used; a newer browser copy is saved to the run at once.

The header says **All changes saved** or **Saving…**, right of **Finish Review**, in a fixed-width space so nothing moves when it changes. It is not announced. A failed save is announced, as an alert that says what to do.

**No edit is lost.** One save runs at a time; an edit made while a save is under way is carried by the next save, which sends the whole draft. A draft older than the one already on disk is never written over it. Stop or Ctrl+C while a save is being written waits for it: it is written whole.

**Leaving the page.** While a change hasn't reached the run yet, closing the tab or leaving the page first shows the browser's leave-page prompt. If you leave anyway, the last edits are sent as the page goes. A browser sends at most 64 KiB that way, so a very large draft (a big PDF fully decided, with long notes) may not be sent then. The browser's own copy still has it, and the review picks it up when opened again in the same browser at the same address.

## The reading-order group

Group 5 of **Check these first** holds:
- the section move (`move_section`), with the pages it touches
- elements moved to the start (`move_to_document_start`)
- orphan text added to the tags (`adopt_orphans`)
- the captions decision (`captions`), which ties each caption to its figure and so moves it in the reading order
- the **reading-order checks:** findings in the original's reading order that no decision answers (below). They can only be marked **Seen**, with a note; nothing is applied.

The group opens with the reading-order panel and is always listed, so a PDF with nothing in it says so ("5. Reading Order (0)").

### Reading Order in the Original (Before Changes)

This panel is a fold at the top of group 5 in **Check first**, and at the top of the reading-order decisions in **All** (the first of "Reading order" and "Reading order check"). **Not reviewed** does not show it, because every finding left there is a card.

Its heading says how many findings there are to check ("3 findings to check"). Inside are a short explanation, then the findings in sentences, each with a link to its card. The kinds of finding follow.

#### A section read out of its printed place

…that no decoration rule removes. A section is out of place when it does not fit the longest run of its sibling sections that reads in page order (the run covering the most pages). So a one-page running-head story read before the chapter it sits in is flagged, not the chapter.

A child section is never compared with the section around it, and a Div around a figure or a note is not compared ("placed where the text refers to it"). Each such section gets a card, for example a cover that is a top-level Article read last.

#### Sections the AI's decisions take care of

Three kinds of out-of-place section are not findings, while the decisions that take care of them are not rejected:

- **A one-page section every text run of which is matched by one of the AI's text rules.** One rule can match it all, or several together. In one earlier sample, a notes running head's page number ("186") is matched by one rule and its title ("Notes to Pages 7–11") by another. Once the rules are applied, a screen reader skips it.
- **A section made only of captions in the AI's captions style (and figures).** `apply.py` ties each caption to its figure, so it is read with the figure and never compared.
- **A section out of place only because of siblings the rules remove.** Once they are gone, it is read in its place. In one earlier sample, an About the Author section (PDF 254) was read after a block of stray letters on PDF 255. The letter rules remove that block, and the rule cards say they put About the Author back in its printed place. review.md, after the changes, finds it in place.

These get no card of their own. Each rule's card says which sections it removes ("This rule, alone or with the AI's other rules, removes 2 sections …"), and the captions decision's card says which it ties to their figures. In one earlier sample, all 24 flags were such sections.

**If you reject a rule or the captions decision, the page lists the sections it no longer takes care of as findings again at once.** A section that two rules each remove whole (stray letter blocks, for example) stays removed until both are rejected. A section uncovered this way has no card; note it on the decision's card.

#### Pages where the text jumps back up the same column

…two or more times in reading order: the same page check review.md makes after the changes. Each page gets a card with its image. The pipeline cannot change the order within a page, so the card asks for a note, for example a fix by hand in Acrobat.

#### Figures the executor moves back to their page

`apply.py` runs a step that moves figures back to their page (`fix_figure_order`), unless the work order turns it off for the PDF. The figures it would move are worked out at the review stop by a trial run of `apply.py` on a copy (see [The trial run](#the-trial-run)).

One card, **Figures Moved**, lists them as review.md does ("Figure on PDF p. 81 (printed 72): read after PDF 139 now; after PDF 82 after the changes"). Two earlier samples had 15 each.

This card is the decision for the step:
- **Approve** has the figures moved back.
- **Reject** leaves every figure where it is read now (`fix_figure_order: false`), for example in a plates section the text refers to by number.

When the AI turned the step off, the card says so: Approve keeps it off, Reject turns it on. A run with no trial run lists `fix_figure_order` under Other decisions instead; rejecting it there turns the step off too. Runs prepared before this card existed have no card.

A change you make on the page (for example rejecting the captions decision) can change which figures move; review.md lists the moves actually made.

#### Small sections read late

These are one or two pages, read more than 5 pages after their printed page because an earlier sibling already reached that far: a figure caption read after the chapter it sits in, for example. Overlapping stories are normal in InDesign books, so this is not a failure.

One card, **Small Sections Read Late**, lists the first 12 and the count of those the AI's decisions do not take care of. It says how many more they do take care of (text the rules remove, captions tied to their figures); those are no longer read late after the changes. In one earlier sample: 2 listed (the series editors on PDF 3, Table 1 on PDF 27, the same 2 review.md lists after the changes), 27 removed by rules, 15 captions tied.

#### The list of sections

Below the findings is the list of sections in the order a screen reader meets them, indented by nesting, with their pages and first words. By default it shows only the sections named in the findings, the section the AI moves and the place it lands.

**Show Every Section in the Book** shows all of them, each finding written out ("Read out of place: it is read between PDF 3 and PDF 22."), with a link to the rule that removes it where one does. Select a row to see its first page.

This is the order before any change. Figure moves and added orphan text happen in `apply.py`, after the review, and the final order is checked in `review.md` (WCAG 1.3.2). When the AI moves a section, its row and the place it lands are marked, and the marks follow the section move card (approved, rejected, changed, not reviewed).

A PDF whose tags have no sections says so. Its page-jump findings still get cards, and review.md's page-by-page 1.3.2 check still covers it.

### Reading-order check cards

These cards say what was found and what you can do. Mark each **Seen**. The note you write (for example "move it before PDF 255 by hand in Acrobat" or "fine as it is") is recorded with your review, in `review.md`'s "Reviewer notes".

"Reviewer notes" names each note by its card ("Text on PDF 10 jumps back up the page (`reading_order:jump:10`): …"), on any card, not only these. A note on something you added is named "Your addition: …".

Finish counts these cards as unreviewed until they are marked. A choice on one carries to a later session like any other. The out-of-place and page-jump cards link to [Fixing the reading order by hand](#fixing-the-reading-order-by-hand).

### Section moves

The AI can ask for up to 3 section moves. There is one card per move, made by the executor in order: `move_section`, then `move_section:1`, `move_section:2`. Each card's preview is worked out on the order the earlier moves leave, as its **Worked Out** row says.

**The preview** shows the sections around the move now and after it, worked out with the executor's own match on the original's tags. It also shows how many sections in the PDF are read away from their place before and after.

The preview leaves out the blocks the text rules remove: `apply.py` removes them before it moves sections, so a move onto a removed block, or of one, is refused. `apply.py` matches again on the file it edits, so this is a preview: review.md says where the executor actually put the section, and says so if that differs from the preview.

**When the executor would refuse the move,** the card says so, and names the text rules when they are the reason. The executor refuses when no section, or more than one, lies inside the pages, or when no section holds pages both before the range and from the target page on. Rejecting such a rule keeps its blocks, so the move can work again: the preview follows your rule decisions within a second (with the auto-save).

**Change** gives three numbers: the pages, and the page to read before. The preview for them is worked out the same way within a second. A card you are typing in is redrawn once you leave it.

**Trial Run** on the AI's move card says what the review stop's trial run of `apply.py` did with the move: where it put the section, or why it refused it. It is the most exact answer, so when it differs from the preview, the card says the trial run is what will happen. It used the AI's decisions as written, so it is hidden once you change the move or reject a text rule.

#### Adding a section move

While the work order holds fewer than 3 section moves, an out-of-place card that no move of the AI's covers has **Add a Section Move**. It opens **Add a decision** with that section, a suggested page to read it before, and the same preview the AI's move card has. The suggestion is the first page of the next sibling that reads in page order, leaving out blocks the rules remove.

It is offered only when that preview shows the executor can make the move. The executor moves a section within the section around it, before a page another section of it starts on. So a section at the top of the tree (a cover, for example), or one that belongs before everything else in its section, cannot be moved this way, and its card says so.

Change the numbers on the added card: its preview follows within a second (with the auto-save). An added move is made after the AI's, so its preview is worked out on the order they leave. When the AI's move covers the section, the card links to that move instead. With 3 moves already, it says to reject or change one first.

### The trial run

At the review stop, the pipeline runs `apply.py` once on a copy, with the AI's decisions as written and the figure step on even when the AI turned it off. It records the figures the step moves, and what became of each of the AI's section moves (the move cards' **Trial Run** row). It uses no AI, and takes as long as the apply step: about 2 minutes for a 250-page PDF. `REVIEW_DRYRUN=off` skips it.

A later review of the same PDF (**Review Again**) reuses that trial run's result while nothing it depends on has changed, so the page opens without the wait and shows exactly the same. It depends on the PDF, the AI's decisions, the pipeline's code, the Python packages and Tesseract it runs with, and the settings `apply.py` reads.

After any of these changes, for example after updating the pipeline, the trial run is made again; one that failed or was skipped is always made again. `REVIEW_DRYRUN=fresh` makes it again regardless.

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

## Checking a draft PDF while you review

**Build a Draft PDF**, in the page's header next to **Finish Review**, makes a PDF from the choices you have made so far. You can check them in Adobe Acrobat or with a screen reader (NVDA, VoiceOver, PAC's screen reader preview), then carry on with the same review. The session stays open; nothing is recorded.

**What it builds:** the choices so far, through the same check as Finish, then the same executor. A choice the check doesn't accept is left out of the draft, so you can check everything else while a card still needs fixing; **Finish Review** waits until it is fixed or rejected (see [Checks as you go](#checks-as-you-go)). Decisions not reviewed yet are built as the AI wrote them.

It takes about as long as the apply step: seconds for a short PDF, up to about 2 minutes for a long one. The page shows the time while it builds, and your changes are still saved as you make them. One draft is built at a time.

**After it is built:** a **Download the Draft PDF** link (the file is named after the PDF, with `_draft.pdf`), and a list of anything left out. Choices the check left out (additions too) have the same message as under their cards, with a link to each. Section moves or other steps the executor could not make say so in plain words; **Details** shows the executor's own reason, and the report after Finish explains it.

**Out of date:** a change to a decision or an addition after the build marks the draft "out of date". Build it again to check the change.

### Limits of the draft

- **It is for checking only.** It is not checked by veraPDF or the pixel and text checks, and it has no review record. It must not be shipped or handed out. Inside, it looks like a finished result to a screen reader: its title and tags are the ones Finish would make. A document property, **RemediationDraft** (Acrobat: File > Properties > Custom), says it is a draft.
- **Changes made to the draft in Acrobat are lost.** Finish builds the real result again from your choices. Fix the reading order by hand only on the remediated result (see [Fixing the reading order by hand](#fixing-the-reading-order-by-hand)).
- **The final result can still differ** from a draft you checked: a change made after the build, or a section move the executor refuses at Finish. Section moves are made in turn, each on the order the earlier ones leave, so changing one move can change what the next one finds.
- **Nothing is kept.** The draft is held in a temporary folder that is removed when the review page closes (Finish, Ctrl+C or **Stop Reviewing**). A folder left by a review page that was killed is removed the next time a review page starts. The run's report, its record and its earlier results are not touched. The copies you download stay in your Downloads folder: delete them when you are done, especially for PDFs that are not open source.
- **Where:** a first review (`REVIEW=1`), or a review opened again (`--reopen`, or **Review Again** in the app). Not on the OCR text review page.

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
- **Only targets the audit listed can be chosen.** Artifact text rules (a pattern over a page range) and the remaining keys (`sections`, `toc` and the like) cannot be added on the page; edit `workorder.json` by hand (see [Without the page](#without-the-page)).

## Fixing the reading order by hand

Some reading-order problems are left to a reviewer: a page whose text jumps back up a column, a second section out of place, or a move the executor refuses. Fix them in Adobe Acrobat Pro, on an exported copy of the **remediated** PDF, and say what you did in the card's note. Never fix the original, or a draft PDF from the review page: Finish builds a new file and those fixes would be lost.

- **A screen reader follows the tag order.** Change the order in the **Tags** panel: drag a section's tag to where it belongs. The **Order** panel (and Acrobat's "reflow" order) does not change what a screen reader reads; changing it alone is a common mistake.
- **A section read out of place:** in the Tags panel, find the section's tag (its first words are on the card) and drag it to just before the section it should be read before (the card's "read before PDF …").
- **A page whose text jumps back up a column:** on that page, reorder its paragraph tags in the Tags panel so they follow the printed columns, or select the page with the **Reading Order** tool and retag it in order.
- **Check it:** listen to the page with a screen reader (NVDA on Windows, VoiceOver on a Mac) or PAC's screen reader preview, then rerun veraPDF (see [Verification with veraPDF](verapdf.md)).
- **Bring it back:** make the fix on an exported copy (`handedit.py export`), then bring the edited file back as a new run (`handedit.py import`), so it is audited, verified and reported again and can be evaluated and shipped. A fix made on the run's own PDF changes its sha256, so the accessibility evaluation refuses it. See [Editing the PDF by hand](hand-edits.md).

## Gaps

In the Finish dialog and at **Finish**, the work order as it would be applied is checked for things that are still missing. Gaps don't block the review: you can add what is missing, or finish and give a reason.

- **H1:** no element would be an H1, or more than one would. The count combines style mappings and single-element retypes. It is approximate, because the audit lists element counts per style; `review.md` has the exact count after the run.
- **Figures without alt text** that are not marked as decoration. A figure past the first request's 100 images gets its alt text from a figure request (see [Files](files.md)). What is left are figures whose figure request did not finish, or every figure past 100 with `FIGURE_PASSES=off` (in an earlier test book that was 443 of 543 figures). The alt texts the figure requests wrote are decisions on the page like any other.
- **Whole-page figures without alt text.**

The line beside **Finish Review** counts the open gaps ("1 gap open"). The Finish dialog lists each gap with an **Add** link that closes the dialog and opens the form at the right kind.

At **Finish**, each open gap needs a reason. The reasons are recorded and listed in `review.md`. An explained gap counts as handled, so the review's row stays OK. A hand edit recorded without `--note` gives no reason, so its gaps make the row a CHECK.

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

The command that reopens the review is not on the page: it is the one in [Reviewing again](#reviewing-again) (`--reopen`). Reports written before 2026-10-29 keep the earlier layout until their next apply.

## Without the page

Edit `workorder.json` by hand (the AI's version stays in `workorder.ai.json`), then:

```bash
python3 review_workorder.py ../runs/teika/rv1 --reviewer "Your Name" [--note TEXT]
```

The edited order goes through the same checks, and `review.json` gets the same record with `method: hand-edit`. Leave `source` as it is, or the command refuses. Bad JSON is reported with its line number. Gaps are printed as warnings and recorded with `--note` as their reason; without a note, the reason recorded is "hand edit: no reason asked for".

## Limits

- **The priority list points at risky kinds of decisions, not at wrong ones.** A confident wrong decision outside those categories is only in **All**.
- **The AI rarely gives a `confidence`:** 2 items across nine books under prompt v8. Where it does, a value below 1 is marked on the card.
- **Lists can be long.** A PDF whose AI re-levels 50 headings has 50 cards in group 3.
- **Additions are limited to what the audit listed.** An element the digest does not list cannot be retyped on the page. Artifact rules and the remaining keys need a hand edit (see [Without the page](#without-the-page)).
- **The gap check looks for what is missing, not for what is wrong.** An H1 on the wrong element, or poor alt text, is not a gap.
- **Page references in the AI's note are found by a pattern** ("PDF 4", "PDF 254–282"). A note that names pages some other way is listed under General.
- **The reading-order list compares where sections start.** A section that starts inside a longer one and is read after it is not flagged as out of place, because overlapping stories are normal in InDesign books; a small one read more than 5 pages late is marked quietly instead. Content outside any section is not listed: the page-jump list covers the order within each page.
- **Rule matches are judged on the original's runs.** A flagged story counts as removed only when it has at most 100 runs and every one matches a rule on its page. Rules and the captions decision are approved or rejected on the page, never edited there, so the page follows a rejection at once. A pattern edited by hand in `workorder.json` is not reflected in the panel.
- **A caption tie is a prediction:** `apply.py` can still refuse one (for example with several figures on the page), and review.md lists any section still read late after the changes.
- **At most 3 section moves per PDF.** A fourth section out of place gets a note on its card (and see [Fixing the reading order by hand](#fixing-the-reading-order-by-hand)). A run whose AI wrote one move (prompt v8) still gets up to 3 on the page. The order within a page cannot be changed by the pipeline at all.
- **The figure moves are worked out with the AI's decisions as written.** The trial run adds time at the first review stop (a later review reuses it while nothing has changed), and does not follow the changes you make on the page.
- **An edit the check refuses is not applied at all.** The AI's value is not used as a fallback. The Finish dialog says so, and lists what would be dropped with a link to each card, so the reviewer can fix the value or approve the AI's.

**Some decisions depend on others, and the Finish dialog's check does not know.** It runs the same checks as `decide.py`, but not the executor's own checks. Two cases were found in testing:
- Rejecting a heading **merge** makes the spoken text (ActualText) the AI wrote for those headings ("Chapter Two …") stop matching the print, so the executor refuses it too. In one earlier sample, rejecting its one merge removed 8 spoken-text entries.
- **Table header columns** are refused when any row has that many cells or fewer, such as a one-cell title row across the table.

Both show up after the run in `review.md` under "Decisions not applied"; nothing is half-applied. The cards for merges, spoken text and tables warn about this.

## For developers

### Files kept at the review stop

When the run stops, it keeps:
- `workorder.ai.json`: the AI's work order
- `review_items.json`: the decisions listed for the review page
- `timing.json`: the time of each step so far. The second call adds its own, so the record has the whole run's.
- `review_stop.json`: what the app's **Apply** needs to run the same second call. That is the original's path, the name and the settings it was run with (`OCR_LANG`, `INTAKE_REUSE`, `INTAKE` and `OUT`). The report removes it.

The app's Apply runs the second call in the run's own folder (`RUN_DIR`). It finds the original from `review_stop.json`, or, if that file has moved, by its sha256 in the folder of original PDFs or of uploads.

Saving uses `POST /keep`, under the server's write lock. One review at a time is enforced by `reviews/.lock`, held from the moment the page opens until the re-apply ends.

### Exactness

The decisions point at objects, styles and list positions. A session is opened and applied only when these are exactly the ones the run was made with; anything else is refused, never re-matched:
- the input PDF
- the kept digest (`reviews/_audit/digest.json`), whose fingerprint must be the one `decide.py` recorded as `run.digest_sha256`
- the AI's order

So is a kept digest that this version of the review step cannot read (after a change to the digest's format). A preloaded choice is carried only onto the same decision with the same AI value. One that is not (after a change to how the review page lists decisions) is shown as not reviewed and listed.

### Pinning

`--pin` keeps the digest with `fulltext.json`: the whole texts review.md quotes, so a re-apply quotes them as the first run did.

A run pinned before `--pin` kept `fulltext.json` gets it added by a second `--pin`, but only when today's audit reproduces the kept digest byte for byte. Otherwise nothing is added and the run stays reviewable; a re-apply then quotes the digest's shortened excerpts.

`--reopen` also pins a `KEEP=1` review run, whose digest was not kept.

### Replaying a saved reply

When a run can't be reviewed again:

1. `python3 review_workorder.py <run> --replay-to <new run folder>` copies the run's `_intake/` (`intake.json`, `intake.pdf`) into the new folder. Beside it, it writes the saved reply (`record.json`'s `raw_reply`) as `<folder>.reply.txt`, with a `.meta.json` holding the original model and the OCR-word list the reply was written for (as `FROM=` batches do). It prints the command to run next.
2. That command is `INTAKE_REUSE=1 REPLY=<folder>.reply.txt REVIEW=1 RUN_DIR=<folder> bash run_api.sh <original.pdf> <name> <label>`: no AI request. `INTAKE_REUSE=1` with the copied `_intake/` keeps the intake result the reply was written for. `REPLY=` alone would redo OCR and auto-tagging, and the reply's ids could then name other elements.
3. After the review, apply with the command run_api.sh prints (`RUN_DIR=<folder> bash run_api.sh …`). The apply step does not run intake again (step 4 above), so the copied intake result is the one applied to.

The reply is checked against today's audit as any reused reply is: what no longer fits is dropped and listed. OCR-word readings are used only when the OCR-word list is the same. A reply that predates the fingerprint loses them, and the OCR-words row is a CHECK.

**Summary-only sessions.** When an old review's choices are rebuilt from its recorded changes, each is kept only if the rebuilt order gives exactly the recorded changes and counts.

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

### The OCR verdict record

OCR text verdicts are kept in one record, `intake.review.ocr_text_approved`, in `_intake/intake.json` and `record.json`. It holds:
- the verdict (`approved`, `not approved` or `sent to a language reader`), reviewer, date, reason and pages
- when given, `reads` (the languages the reviewer reads) and `to` (who it was sent to)
- `via` (`page` or `review_ocr.py`), `session` (the session open when it was recorded on the page) and `recorded`

The review page's **OCR Text** section writes it, and `review_ocr.py` writes the same record through the same code (see [Intake](intake.md)), via `review/ocr.py`. The latest verdict wins; earlier ones are kept under `history`.

Record Verdict writes `_intake/intake.json` (and intake.md), and for a finished run `record.json`. The OCR section's page images are read with pdfplumber. The OCR-only page's images go to a temporary folder, not the run, and a `reviews/` folder it had to make for its lock is removed when it closes.

**Only one writer at a time:** the page and `review_ocr.py` take the same lock on `_intake/`, so their writes never interleave. For a finished run, `review_ocr.py` is also refused while a review page of the run is open or an apply runs (`reviews/.lock`). During a first review (`REVIEW=1`, no `record.json` yet) only the `_intake/` lock applies.

### The section-membership data

Counting a captions-only section as taken care of needs the section's child styles, which the audit records in `fulltext.json`. Runs audited earlier count no captions this way. The full reading order comes from `_audit/fulltext.json`; a run audited before this was added shows the digest's section lines only, with no move preview and no page-jump findings.

Text-rule matching on the page is done as `apply.py` matches: the whole run, the pattern as written or with its spaces optional.

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
