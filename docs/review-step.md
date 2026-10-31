---
title: Reviewing the work order
nav_order: 3.5
---

# Reviewing the work order before it is applied

With `REVIEW=1`, a run stops after the AI's decisions and before `apply.py`. A person then checks the work order, approving, changing or rejecting each decision, and the run goes on with the reviewed version. Without `REVIEW=1`, runs work as before.

This is for decisions where a wrong answer still passes every automated check. For example, the AI tagged godzone's half-title ("Mapping the Godzone", PDF 2) as P under prompt v7 and as H1 under v8. Both versions pass "exactly one H1"; only a person looking at the pages can tell which is right.

## Steps

```bash
cd pipeline
REVIEW=1 bash run_api.sh ../samples/group1/godzone.pdf godzone rv1   # intake, audit, the AI's decisions; then it stops
python3 review_workorder.py ../runs/godzone/rv1 --serve              # the review page, in your browser
bash run_api.sh ../samples/group1/godzone.pdf godzone rv1            # same label, without REVIEW=1: apply, verify, report
```

1. **The run stops.** It keeps the AI's work order as `workorder.ai.json`, lists the decisions for the review page (`review_items.json`), and prints the next two commands. Nothing has been applied yet.
2. **`--serve` opens the review page** at `http://localhost:8765/`. It runs on this computer only. On WSL, open the printed link in a Windows browser. The terminal must stay open while you review. Ctrl+C stops it without finishing; your choices are kept in the browser, and in `review_decisions.json` after each **Save**, so running the command again carries on where you left off.
3. **On the page,** enter your name, then go through the cards. Each decision has **Approve**, **Change** or **Reject**, and a note. Deferrals and the AI's note to the reviewer have **Seen** only, because nothing applies them. **Add a decision** adds what the AI left out (see [Adding a decision](#adding-a-decision)).
   - **Save** checks your choices with the same rules `decide.py` uses on the AI's reply, and shows anything that would be dropped. For example, `english` as a language is not a BCP 47 tag. It also lists any **gaps**: things still missing once the review is applied (see [Gaps](#gaps)).
   - **Finish Review** records the review and stops the server. If some decisions are not reviewed, it asks whether to accept them unchanged; they are then recorded as *accepted without review*. If gaps are open, it asks for a reason for each, or you can go back and add what is missing.
4. **Rerun the same command** (same label, no `REVIEW=1`). `decide.py` is skipped (no API call) and the reviewed `workorder.json` is applied. Intake is not run again: the reviewed order is applied to the intake result saved before the stop (`_intake/intake.pdf`, or the original for a tagged book), the one the decisions were made on. The original given must be the same file (its sha256 is checked against `_intake/intake.json`), and `apply.py` checks the input against the work order's `source.sha256`.

Until the review is finished, rerunning the label is refused, so a half-reviewed work order never reaches `apply.py`. Batches (`batch_api.sh`) refuse `REVIEW=1`, because they run unattended.

The first review is kept as **session 1** in the run's `reviews/` folder (see [Reviewing again](#reviewing-again)).

## From the browser

`python3 app.py <run folder>` opens a finished run's page with buttons for everything below: **Review Again**, **Start Over from the AI's Decisions**, **Review Again from Session N**, **Apply Session N** and **Session History**. Each button runs the command shown here, and **Finish** goes back to the run page, which shows the re-apply; when it ends, the page says "New result ready" and a **Show the New Result** button loads it (the page never reloads by itself). Ctrl+C on the review page while Finish is being recorded waits until the review is recorded. See [The app](app.md). The commands below work as before.

## Reviewing again

A finished run (with or without `REVIEW=1`) can be reviewed again: the page opens with every earlier choice preloaded, you change only what is needed, and Finish applies the reviewed order at once, with no AI call. The result is a new remediated PDF, `review.md` and `review.html`. Nothing earlier is overwritten.

```bash
cd pipeline
python3 review_workorder.py ../runs/godzone/rv1 --reopen              # the latest session's choices, preloaded
python3 review_workorder.py ../runs/godzone/rv1 --reopen --from 1     # start from an earlier session (--from ai: the AI's decisions)
python3 review_workorder.py ../runs/godzone/rv1 --sessions            # every session: who, when, from where, what changed, which is current
python3 review_workorder.py ../runs/godzone/rv1 --apply               # apply a finished session that was not applied (--no-apply, or a failed apply)
```

`--return-to URL` (with `--serve` or `--reopen`) makes the review page go to that page after Finish, and link back to it. The app passes its run page. Only `http://127.0.0.1:<port>/…` or `http://localhost:<port>/…` is accepted.

- **The page** says which session it is, where it started, how many choices were preloaded, and any that could not be carried. Each preloaded card says which session set its choice. It links the current result's `review.html` (served by the review server, as a browser cannot open a local file from the page), and keeps the gap reasons given last time.
- **Finish** records the session and applies it: apply, verify and report run in the terminal, each with its time. The current result moves to `reviews/versions/<session>/` (or `versions/ai/` for a result applied without review) only after all three succeed; if one fails, the current result is unchanged and the session stays *finished*: run `--apply` again. `--no-apply` stops after Finish. Until the session is applied, "Ready to ship?" says **No** ("the latest review … is finished but not applied"), because the PDF on disk is older than the sign-off.
- **One review at a time per run:** `reviews/.lock` is held from the moment the page opens until the re-apply ends. Ctrl+C leaves the session *open*; `--reopen` carries on with it. `--reopen --from N` while a session is open is refused unless `--discard-open` (the open session is kept, marked *abandoned*). `--discard-open` on its own does only that: the open session is marked abandoned and no new one is opened; the current result does not change.
- **The OCR text verdict** is one per run (the latest wins) and reopening never rolls it back. The page shows the current verdict (who, when) and the one in force at each earlier finish; it is changed with `review_ocr.py`, not on this page (an OCR section is planned).
- **Exactness.** The decisions point at objects, styles and list positions. A session is opened and applied only when the input PDF, the kept digest (`reviews/_audit/digest.json`, its fingerprint the one `decide.py` recorded as `run.digest_sha256`) and the AI's order are exactly the ones the run was made with; anything else is refused, never re-matched. So is a kept digest that this version of the review step cannot read (after a change to the digest's format). A preloaded choice is carried only onto the same decision with the same AI value; one that is not (after a change to how the review page lists decisions) is shown as not reviewed and listed.
- **Runs finished before every run kept its digest** need it pinned once: `python3 review_workorder.py <run> --pin [--pdf <original.pdf>]` re-audits the run's input (free, no model), checks the digest against the record and keeps it, with `fulltext.json` (the whole texts review.md quotes, so a re-apply quotes them as the first run did). A run pinned before `--pin` kept `fulltext.json` gets it added by a second `--pin`, only when today's audit reproduces the kept digest byte for byte; otherwise nothing is added and the run stays reviewable (a re-apply then quotes the digest's shortened excerpts). A book with no intake result needs `--pdf` (its sha256 is checked). `--reopen` pins first by itself (also a `KEEP=1` review run, whose digest was not kept); if today's audit no longer matches (audit code, veraPDF or Python changed), the run cannot be reviewed again.
- **When a run cannot be reviewed again** (the pin is refused, or the kept digest cannot be read), the fallback is a new run of the book from its saved reply, on today's code. It is not a review of the old result: the audit, the checks and the result are today's.
  - `python3 review_workorder.py <run> --replay-to <new run folder>` copies the run's `_intake/` (`intake.json`, `intake.pdf`) into the new folder and writes, beside it, the saved reply (`record.json`'s `raw_reply`) as `<folder>.reply.txt`, with a `.meta.json` holding the original model and the OCR-word list the reply was written for (as `FROM=` batches do). It prints the command to run next.
  - That command is `INTAKE_REUSE=1 REPLY=<folder>.reply.txt REVIEW=1 RUN_DIR=<folder> bash run_api.sh <original.pdf> <name> <label>`: no API call. `INTAKE_REUSE=1` with the copied `_intake/` keeps the intake result the reply was written for; `REPLY=` alone would redo OCR and auto-tagging, and the reply's ids could then name other elements.
  - After the review, apply with the command run_api.sh prints (`RUN_DIR=<folder> bash run_api.sh …`). The apply step does not run intake again (step 4 above), so the copied intake result is the one applied to.
  - The reply is checked against today's audit as any reused reply is: what no longer fits is dropped and listed. OCR-word readings are used only when the OCR-word list is the same; a reply that predates the fingerprint loses them (the OCR-words row is a CHECK).
- **Reviews made before sessions were kept** (`record.json` has the review's changes and counts, not each card's choice) become session 1, *summary only*: "Session 1 (summary only): 159 approved, 8 seen, no changes; per-decision choices were not recorded before 2026-10-27". When nothing was accepted without review, each card's choice is rebuilt from the recorded changes, and kept only if the rebuilt order gives exactly the recorded changes and counts; those cards show "approved (inferred)" and point to session 1. Otherwise the new session starts from the AI's decisions, with the summary on the page.
- **Batches:** re-applying a book in a batch folder rebuilds the batch's `summary.html`; `summary.md` stays as the batch run wrote it.

## What the page shows

- **Check these first.** Decisions in categories where a mistake is likely or affects much of the book. They are chosen by fixed rules (no model), grouped in this order, and sorted by page within each group:
  1. **H1 and title:** any decision that makes or unmakes an H1, and the document title.
  2. **Style-wide mappings:** each `rolemap` entry, most elements first. One entry changes every element of that style.
  3. **Heading-level changes:** a `retype` that changes a heading level, or turns a heading into body text or the reverse.
  4. **Rules that can hide text:** artifact text rules and untagged rules, with their pattern and page range.
  5. **Reading order:** a section move (`move_section`), elements moved to the start (`move_to_document_start`), orphan text added to the tags (`adopt_orphans`), each with the pages it touches, and the captions decision (`captions`), which ties each caption to its figure and so moves it in the reading order. Also the **reading-order checks**: findings in the original's reading order that no decision answers (below). They can only be marked **Seen**, with a note; nothing is applied. The group opens with the reading-order panel (below) and is always listed, so a book with nothing in it says so ("5. Reading Order (0)").
  6. **Pages the AI asked about:** deferrals with a specific page range, and the AI's note when it names pages ("PDF 4").
  7. **General:** deferrals with no pages, or covering more than half the book.
- **Reading Order in the Original (Before Changes)**, a fold at the top of group 5 in **Check first**, and at the top of the reading-order decisions in **All** (the first of "Reading order" and "Reading order check"). **Not reviewed** does not show it: every finding left there is a card. Its heading says how many findings there are to check ("3 findings to check"). Inside, a short explanation, then the findings in sentences, each with a link to its card:
  - **A section read out of its printed place that no decoration rule removes.** A section is out of place when it does not fit the longest run of its sibling sections that reads in page order (the run covering the most pages). So a one-page running-head story read before the chapter it sits in is flagged, not the chapter. A child section is never compared with the section around it, and a Div around a figure or a note is not compared ("placed where the text refers to it"). Each such section gets a card. In sands: its cover, a top-level Article read last.
  - **Sections read out of place that the AI's decisions take care of.** Two kinds are not findings while the decisions that take care of them are not rejected:
    - a one-page section every text run of which is matched by one of the AI's text rules (matched as `apply.py` matches: the whole run, the pattern as written or with its spaces optional). One rule can match it all, or several together: in translation, a notes running head's page number ("186") is matched by one rule and its title ("Notes to Pages 7–11") by another. Once the rules are applied, a screen reader skips it.
    - a section made only of captions in the AI's captions style (and figures): `apply.py` ties each caption to its figure, so it is read with the figure and never compared. This needs the section's child styles, which the audit records in `fulltext.json` (runs audited earlier: no captions are counted this way).
    - a section out of place only because of siblings the rules remove: once they are gone, it is read in its place. In translation, About the Author (PDF 254) is read after a block of stray letters on PDF 255; the letter rules remove that block, and the rule cards say they put About the Author back in its printed place. review.md, after the changes, finds it in place.

    These get no card of their own; each rule's card says which sections it removes ("This rule, alone or with the AI's other rules, removes 2 sections …"), and the captions decision's card which it ties to their figures. In translation, all 24 flags are such sections. **If you reject a rule or the captions decision, the page lists the sections it no longer takes care of as findings again at once.** A section that two rules each remove whole (translation's stray letter blocks) stays removed until both are rejected. A section uncovered this way has no card; note it on the decision's card.
  - **Pages where the text jumps back up the same column** two or more times in reading order (the same page check review.md makes after the changes). Each page gets a card with its image. The pipeline cannot change the order within a page, so the card asks for a note, for example a fix by hand in Acrobat.
  - **Figures the executor moves back to their page** (`fix_figure_order`, a step `apply.py` runs unless the work order turns it off for the book). They are worked out at the review stop by a trial run of `apply.py` on a copy (which also records what became of each of the AI's section moves: see their cards' Trial Run row), with the AI's decisions as written and this step on even when the AI turned it off (no model; it takes as long as the apply step, about 2 minutes for translation; `REVIEW_DRYRUN=off` skips it). One card, **Figures Moved**, lists them as review.md does ("Figure on PDF p. 81 (printed 72): read after PDF 139 now; after PDF 82 after the changes"). In sands and translation, 15 each. This card is the decision for the step: **Approve** has the figures moved back, **Reject** leaves every figure where it is read now (`fix_figure_order: false`), for example in a plates section the text refers to by number. When the AI turned the step off, the card says so: Approve keeps it off, Reject turns it on. (A run with no trial run lists `fix_figure_order` under Other decisions instead; rejecting it there turns the step off too.) A change you make on the page (for example rejecting the captions decision) can change them; review.md lists the moves actually made. Runs prepared before this have no card.
  - **Small sections read late:** one or two pages, read more than 5 pages after their printed page because an earlier sibling already reached that far (a figure caption read after the chapter it sits in). Overlapping stories are normal in InDesign books, so this is not a failure. One card, **Small Sections Read Late**, lists the first 12 and the count of those the AI's decisions do not take care of, and says how many more they do (text the rules remove, captions tied to their figures): those are no longer read late after the changes. In translation: 2 listed (the series editors on PDF 3, Table 1 on PDF 27, the same 2 review.md lists after the changes), 27 removed by rules, 15 captions tied.
  - Below the findings, the list of sections in the order a screen reader meets them, indented by nesting, with their pages and first words. By default it shows only the sections named in the findings, the section the AI moves and the place it lands; **Show Every Section in the Book** shows all of them, each finding written out ("Read out of place: it is read between PDF 3 and PDF 22."), with a link to the rule that removes it where one does. Select a row to see its first page.
  - This is the order before any change: figure moves and added orphan text happen in `apply.py`, after the review, and the final order is checked in `review.md` (1.3.2, below). When the AI moves a section, its row and the place it lands are marked, and the marks follow the section move card (approved, rejected, changed, not reviewed).
  - A book whose tags have no sections says so; its page-jump findings still get cards, and review.md's page-by-page 1.3.2 check still covers it.
  - The full order comes from `_audit/fulltext.json`. A run audited before this was added shows the digest's section lines only, with no move preview and no page-jump findings.
- **Reading-order check cards** (group 5) say what was found and what you can do. Mark each **Seen**; the note you write (for example "move it before PDF 255 by hand in Acrobat" or "fine as it is") is recorded with your review: in `review.md`'s "Reviewer notes" and in `record.json` `review.decisions`. "Reviewer notes" names each note by its card ("Text on PDF 10 jumps back up the page (`reading_order:jump:10`): …"), on any card, not only these; a note on something you added is named "Your addition: …". Finish counts them as unreviewed until they are marked. Their IDs are `reading_order:away:<section>`, `reading_order:jump:<page>`, `reading_order:figures` (approved or rejected, not marked seen: see above) and `reading_order:late`; a choice carries to a later session like any other. The out-of-place and page-jump cards link to "Fixing the reading order by hand" (below).
- **Adding a section move.** While the work order holds fewer than 3 section moves, an out-of-place card that no move of the AI's covers has **Add a Section Move**. It opens **Add a decision** with that section and a suggested page to read it before (the first page of the next sibling that reads in page order, leaving out blocks the rules remove), and the same preview the AI's move card has. It is offered only when that preview shows the executor can make the move: the executor moves a section within the section around it, before a page another section of it starts on, so a section at the top of the tree (sands' cover) or one that belongs before everything else in its section cannot be moved this way, and its card says so. Change the numbers on the added card and **Save** to see the preview for them. An added move is made after the AI's, so its preview is worked out on the order they leave. When the AI's move covers the section, the card links to that move instead; with 3 moves already, it says to reject or change one first.
- **A section move's card** (one per move: `move_section`, then `move_section:1`, `move_section:2`; the executor makes them in that order, and each card's preview is worked out on the order the earlier moves leave, as its **Worked Out** row says) shows the sections around it now and after the move, worked out with the executor's own match on the original's tags, and how many sections in the book are read away from their place before and after. The preview leaves out the blocks the text rules remove: `apply.py` removes them before it moves sections, so a move onto a removed block, or of one, is refused. When the executor would refuse the move (no section, or more than one, lies inside the pages; or no section holds pages both before the range and from the target page on), the card says so, and names the text rules when they are the reason. Rejecting such a rule keeps its blocks, so the move can work again: **Save** to see the preview with your rule decisions. `apply.py` matches again on the file it edits, so this is a preview: review.md says where the executor actually put the section, and says so if that differs from the preview.
- **Trial Run** on the AI's move card: what the review stop's trial run of `apply.py` did with the move (where it put the section, or why it refused it). It is the most exact answer, so when it differs from the preview the card says the trial run is what will happen. It used the AI's decisions as written, so it is hidden once you change the move or reject a text rule. **Change** gives three numbers (the pages and the page to read before); **Save** works out the preview for them the same way. An **orphan-text card** shows the text no tag owns on its pages (up to six runs per page, from the audit).
- **All** lists every decision by kind; **Not reviewed** lists what is left.
- Each card has labeled lines: **Page** ("PDF p. 2 (printed i)", or a page range), **Decision type**, the element (for example **Text on the page**), **What this does** (a plain-language description of the effect, written by the page for each kind of decision, not by the AI), **Change** or **Original** and **AI's choice**, and **AI's reason** (the model's own short `why`). Decoration rules are described in words (**Hides**, **Where on the page**, **Marked as**), with the AI's exact entry under a fold. An **AI confidence** below 1 is flagged on any kind of decision. The decision's ID (for example `retype:1154 0`: the kind of decision and the element's object number in the original PDF) is in small print at the bottom. Every card with a page shows that page; heading decisions also show the pages either side; alt text shows the figure crop; an OCR word shows the word cut from the scan, the same image the AI read. Page images are made the first time you scroll to them, so there is no limit on how many a book can have. Click an image to enlarge it.
- The box for a new value appears only when **Change** is selected. Edits are limited to valid values:
  - a heading level from a list (H1–H6, P, Span, Caption, Note, Div), with a warning on a style mapping saying how many elements it changes;
  - alt text, spoken text and OCR readings as text;
  - the language as a tag;
  - table header rows and columns as numbers 0–3.

  Artifact rules, reading-order decisions other than a section move, and the remaining keys (`sections`, `links` and the like) can only be approved or rejected; to edit a rule's pattern, edit `workorder.json` by hand (below).
- A **page index** at the side lists the pages of the "check first" items. On a narrow screen the side list folds away behind a **Sections** button.
- To undo a choice, click the selected option again, or **Clear**: the decision goes back to not reviewed. Its note stays.
- When two decisions would each make an H1 (for example the AI's H1 and one you added), both cards are flagged.
- Your choices are kept in the browser, and in `review_decisions.json` after each **Save**. When you open the page, whichever copy is newer is used.

## Adding a decision

The cards cover only what the AI decided. **Add a decision** (at the top) is for what it left out. Pick a kind, find the target by text, page or object number, and give a value and an optional note. The addition appears as a card under **Added by you**, where you can change its value or **Remove** it.

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

For example, after changing godzone's half-title (PDF 2, `1154 0`) from H1 to P on its card, add a Heading or tag change for the title page (`1155 0`, PDF 4) as H1.

- **A target the AI already decided is not in the list:** change it on its card.
- **A figure the AI marked as decoration needs that decision rejected first,** before alt text can be added; the form says so.
- **Additions go through the same checks as the AI's decisions,** except for the two rules about images the model never saw. Those exist so the model cannot describe a figure it did not see; you see the page. An addition is written in the AI's shape, with `why` "added by <name> in review", and appears in the record as `added`.
- **Only targets the audit listed can be chosen.** Artifact text rules (a pattern over a page range) and the remaining keys (`sections`, `toc` and the like) cannot be added on the page; edit `workorder.json` by hand (see "Without the page").

## Fixing the reading order by hand

Some reading-order problems are left to a person: a page whose text jumps back up a column, a second section out of place, or a move the executor refuses. Fix them in Adobe Acrobat Pro, on the **remediated** PDF (never the original), and say what you did in the card's note.

- **A screen reader follows the tag order.** Change the order in the **Tags** panel: drag a section's tag to where it belongs. The **Order** panel (and Acrobat's "reflow" order) does not change what a screen reader reads; changing it alone is a common mistake.
- **A section read out of place:** in the Tags panel, find the section's tag (its first words are on the card) and drag it to just before the section it should be read before (the card's "read before PDF …").
- **A page whose text jumps back up a column:** on that page, reorder its paragraph tags in the Tags panel so they follow the printed columns, or select the page with the **Reading Order** tool and retag it in order.
- **Check it:** listen to the page with a screen reader (NVDA on Windows, VoiceOver on a Mac) or PAC's screen reader preview, then rerun veraPDF (see [Verification with veraPDF](verapdf.md)).

## Gaps

On every **Save** and at **Finish**, the work order as it would be applied is checked for things that are still missing. Gaps don't block the review: you can add what is missing, or finish and give a reason.

- **H1:** no element would be an H1, or more than one would. The count combines style mappings and single-element retypes. It is approximate, because the audit lists element counts per style; `review.md` has the exact count after the run.
- **Figures without alt text** that are not marked as decoration. This covers figures whose images were not sent to the model (more than `--max-images`, 100 by default): in *dwellings* that was 443 of 543 figures, all left for a person.
- **Whole-page figures without alt text.**

Each gap in the Save message has an **Add** link that opens the form at the right kind. At **Finish**, each open gap needs a reason. The reasons are recorded and listed in `review.md`. An explained gap counts as handled, so the review's row stays OK. A hand edit recorded without `--note` gives no reason, so its gaps make the row a CHECK.

## What is recorded

- `review.json` (folded into `record.json` as `review.workorder`): reviewer, date, `method` (`page` or `hand-edit`), every change (`where`, `id`, `changed` / `removed` / `added`, the AI's value and the person's), edits not accepted by the check, counts (approved, changed, rejected, seen, accepted without review, added), gaps left open with the reviewer's reason (`gaps`), the reviewer's notes (an addition's note is keyed `add:<kind>:<target>`), and earlier reviews under `history`. A decision marked **Change** but left at the AI's value counts as approved.
- `record.json` also keeps the AI's version as `workorder_ai`. `workorder` is what was applied, and carries `reviewed_by`. `review.session` is the session this result comes from, `review.sessions` one line per session (who, when, from where, status, counts, how many choices were carried and from where, how many changed in the session), and `review.decisions` one line per decision (its review status, the session that set it, `inferred`, its note), which `review.html` shows.
- `reviews/sessions/NNN.json`: each session in full: every choice with the AI value it was judged against and the session that set it, additions, what changed since the session's start, the review as `review.json` had it, and the OCR verdict at Finish; `NNN.workorder.json` is the order it applied. `reviews/basis.json` holds the run id (the page's browser-draft key), the input PDF's path and sha256, the digest's fingerprint and the AI order's sha256.
- `review.md` gets a row in the automated checks ("Work order reviewed by a person before it was applied"). The row is a CHECK when decisions were accepted without review, an edit was dropped, or a gap was left open without a reason (a hand edit with no `--note`). It also gets a section listing each change (AI → person), each open gap with its reason, and which session the result comes from.
- `review.html` has a "Review of the AI's Decisions" section. A run never reviewed shows its decision count by kind, all applied without review. A reviewed run shows:
  - one line for the current session: who, when, and how many decisions were approved, changed, rejected and accepted without review;
  - its row of the session table, with the other sessions folded under **Previous Sessions (N)**;
  - each decision's status (approved, changed, rejected, seen, accepted without review; "(inferred)" for a summary-only session's rebuilt choices), with the session that set it.
  The command that reopens the review is not on the page: it is the one above (`--reopen`). Reports written before 2026-10-29 keep the earlier layout until their next apply.

## Sign-off: when a book is ready to ship

The review page is the final sign-off (checklist rule 2: a person approves AI output before it ships). A book counts as ready to ship only when a person has approved its work order on the review page and, if intake added OCR text or found the book's existing OCR layer doubtful, unusable or missing diacritics, or could not check it, its OCR text as well.

- **OCR text verdicts** are kept in one record, `intake.review.ocr_text_approved` (in `_intake/intake.json` and `record.json`): verdict, reviewer, date, reason, pages. The planned OCR section of the review page will write that record. `review_ocr.py` writes the same record and stays as a fallback for runs without the review page (see [Intake](intake.md)). The latest verdict wins; earlier ones are kept under `history`.
- **"Ready to ship?" always reflects the latest session:** a session finished but not applied makes it No until `--apply`.
- **`REVIEW=1` is optional for now.** A book run without it is still processed and reported, but it is never shown as ready to ship. Once the pipeline is in official use, the review step becomes the standard workflow; the default has not changed yet.

## Without the page

Edit `workorder.json` by hand (the AI's version stays in `workorder.ai.json`), then:

```bash
python3 review_workorder.py ../runs/godzone/rv1 --reviewer "Your Name" [--note TEXT]
```

The edited order goes through the same checks, and `review.json` gets the same record with `method: hand-edit`. Leave `source` as it is, or the command refuses. Bad JSON is reported with its line number. Gaps are printed as warnings and recorded with `--note` as their reason; without a note, the reason recorded is "hand edit: no reason asked for".

## Limits

- **The priority list points at risky kinds of decisions, not at wrong ones.** A confident wrong decision outside those categories is only in **All**.
- **The AI rarely gives a `confidence`** (2 items across the nine v8 books). Where it does, a value below 1 is marked on the card.
- **Lists can be long.** buddhist re-levels 50 headings, so group 3 has 50 cards.
- **Additions are limited to what the audit listed.** An element the digest does not list cannot be retyped on the page. Artifact rules and the remaining keys need a hand edit (see "Without the page").
- **The gap check looks for what is missing, not for what is wrong.** An H1 on the wrong element, or poor alt text, is not a gap.
- **Page references in the AI's note are found by a pattern** ("PDF 4", "PDF 254–282"). A note that names pages some other way is listed under General.
- **The reading-order list compares where sections start.** A section that starts inside a longer one and is read after it is not flagged as out of place, because overlapping stories are normal in InDesign books; a small one read more than 5 pages late is marked quietly instead. Content outside any section is not listed: the page-jump list covers the order within each page.
- **Rule matches are judged on the original's runs.** A flagged story counts as removed only when it has at most 100 runs and every one matches a rule on its page. Rules and the captions decision are approved or rejected on the page, never edited there, so the page follows a rejection at once; a pattern edited by hand in `workorder.json` is not reflected in the panel. A caption tie is a prediction: `apply.py` can still refuse one (for example with several figures on the page), and review.md lists any section still read late after the changes.
- **At most 3 section moves per book.** A fourth section out of place gets a note on its card (and see "Fixing the reading order by hand"). A run whose AI wrote one move (prompt v8) still gets up to 3 on the page. The order within a page cannot be changed by the pipeline at all.
- **The figure moves are worked out with the AI's decisions as written.** The trial run adds time at the review stop and does not follow the changes you make on the page.
- **Some decisions depend on others, and Save does not know.** Save runs the same checks as `decide.py`, but not the executor's own checks. Two cases found in testing:
  - Rejecting a heading **merge** makes the spoken text (ActualText) the AI wrote for those headings ("Chapter Two …") stop matching the print, so the executor refuses it too. In pearl, rejecting the one merge removed 8 spoken-text entries.
  - **Table header columns** are refused when any row has that many cells or fewer, such as a one-cell title row across the table.

  Both show up after the run in `review.md` under "Decisions not applied"; nothing is half-applied. The cards for merges, spoken text and tables warn about this.
- **An edit the check refuses is not applied at all.** The AI's value is not used as a fallback. Save says so, and lists what was refused, so the reviewer can fix the value or approve the AI's.

## For a front end later

The logic is in `pipeline/review/core.py`, apart from the web layer (`server.py`, `page.html`). A front end can call `core.py` and replace those two files. The contract is two JSON formats:

- **Items** (`review_items.json`, from `core.build_items`): `{id, key, kind, label, page, page_label, pages, before, ai, edit, options, context, priority, images, loc, field}`.
  - `id` is stable for a given AI work order (`retype:1154 0`, `rolemap:H4`, `alt:4081 0`, `document.title`, `artifacts.text_rules:0`, `deferrals:2`, `key:sections`).
  - `edit` is `level`, `text`, `lang`, `table` or null (approve or reject only).
- **Decisions** (`review_decisions.json`, taken by `core.apply_decisions`): `{id: {status: approved | changed | rejected | seen, value?, note?}}`. `value` has the item's `ai` shape.
- **Addable targets** (`review_items.json` → `addable`, from `core.addable`): `{kind: [{id, kind, target, label, page, page_label, before, default, edit, options, context, images}]}`. `id` is `add:<kind>:<target>`, for example `add:retype:1155 0`.
- **Additions** (`review_decisions.json` → `additions`, taken by `core.add_entries`): `[{kind, target, value, note?}]`. `value` has the target's `default` shape. `add_entries` returns what it refused, `[{id, why}]`.
- **Gaps** (`core.gaps` on the checked order, or `core.preview` for the check and the gaps together): `[{id: h1 | figures_without_alt | page_figures_without_alt, what, add?: {kind, target?}}]`. `core.finish` takes the reasons as `gaps_ack: {id: reason}`.
- `review_decisions.json` also holds `saved_at`, the browser's time of the last change, used to pick the newer copy.
- The server answers only to itself: the `Host` must be `localhost` or `127.0.0.1` on its port, and a POST must be `application/json` from the page's own origin. Another web page open in the browser cannot submit a review, and cannot show the review page inside a frame of its own (every response says `X-Frame-Options: DENY` and `frame-ancestors 'none'`).
