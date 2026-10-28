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
   - **Finish review** records the review and stops the server. If some decisions are not reviewed, it asks whether to accept them unchanged; they are then recorded as *accepted without review*. If gaps are open, it asks for a reason for each, or you can go back and add what is missing.
4. **Rerun the same command** (same label, no `REVIEW=1`). `decide.py` is skipped (no API call) and the reviewed `workorder.json` is applied.

Until the review is finished, rerunning the label is refused, so a half-reviewed work order never reaches `apply.py`. Batches (`batch_api.sh`) refuse `REVIEW=1`, because they run unattended.

The first review is kept as **session 1** in the run's `reviews/` folder (see [Reviewing again](#reviewing-again)).

## Reviewing again

A finished run (with or without `REVIEW=1`) can be reviewed again: the page opens with every earlier choice preloaded, you change only what is needed, and Finish applies the reviewed order at once, with no AI call. The result is a new remediated PDF, `review.md` and `review.html`. Nothing earlier is overwritten.

```bash
cd pipeline
python3 review_workorder.py ../runs/godzone/rv1 --reopen              # the latest session's choices, preloaded
python3 review_workorder.py ../runs/godzone/rv1 --reopen --from 1     # start from an earlier session (--from ai: the AI's decisions)
python3 review_workorder.py ../runs/godzone/rv1 --sessions            # every session: who, when, from where, what changed, which is current
python3 review_workorder.py ../runs/godzone/rv1 --apply               # apply a finished session that was not applied (--no-apply, or a failed apply)
```

- **The page** says which session it is, where it started, how many choices were preloaded, and any that could not be carried. Each preloaded card says which session set its choice. It links the current result's `review.html` (served by the review server, as a browser cannot open a local file from the page), and keeps the gap reasons given last time.
- **Finish** records the session and applies it: apply, verify and report run in the terminal, each with its time. The current result moves to `reviews/versions/<session>/` (or `versions/ai/` for a result applied without review) only after all three succeed; if one fails, the current result is unchanged and the session stays *finished*: run `--apply` again. `--no-apply` stops after Finish. Until the session is applied, "Ready to ship?" says **No** ("the latest review … is finished but not applied"), because the PDF on disk is older than the sign-off.
- **One review at a time per run:** `reviews/.lock` is held from the moment the page opens until the re-apply ends. Ctrl+C leaves the session *open*; `--reopen` carries on with it. `--reopen --from N` while a session is open is refused unless `--discard-open` (the open session is kept, marked *abandoned*).
- **The OCR text verdict** is one per run (the latest wins) and reopening never rolls it back. The page shows the current verdict (who, when) and the one in force at each earlier finish; it is changed with `review_ocr.py`, not on this page (an OCR section is planned).
- **Exactness.** The decisions point at objects, styles and list positions. A session is opened and applied only when the input PDF, the kept digest (`reviews/_audit/digest.json`, its fingerprint the one `decide.py` recorded as `run.digest_sha256`) and the AI's order are exactly the ones the run was made with; anything else is refused, never re-matched. So is a kept digest that this version of the review step cannot read (after a change to the digest's format). A preloaded choice is carried only onto the same decision with the same AI value; one that is not (after a change to how the review page lists decisions) is shown as not reviewed and listed.
- **Runs finished before every run kept its digest** need it pinned once: `python3 review_workorder.py <run> --pin [--pdf <original.pdf>]` re-audits the run's input (free, no model), checks the digest against the record and keeps it. A book with no intake result needs `--pdf` (its sha256 is checked). `--reopen` pins first by itself (also a `KEEP=1` review run, whose digest was not kept); if today's audit no longer matches (audit code, veraPDF or Python changed), the run cannot be reviewed again.
- **When a run cannot be reviewed again** (the pin is refused, or the kept digest cannot be read), the fallback is a new run of the book from its saved reply, on today's code. It is not a review of the old result: the audit, the checks and the result are today's.
  - `python3 review_workorder.py <run> --replay-to <new run folder>` copies the run's `_intake/` (`intake.json`, `intake.pdf`) into the new folder and writes, beside it, the saved reply (`record.json`'s `raw_reply`) as `<folder>.reply.txt`, with a `.meta.json` holding the original model and the OCR-word list the reply was written for (as `FROM=` batches do). It prints the command to run next.
  - That command is `INTAKE_REUSE=1 REPLY=<folder>.reply.txt REVIEW=1 RUN_DIR=<folder> bash run_api.sh <original.pdf> <name> <label>`: no API call. `INTAKE_REUSE=1` with the copied `_intake/` keeps the intake result the reply was written for; `REPLY=` alone would redo OCR and auto-tagging, and the reply's ids could then name other elements.
  - After the review, apply with the command run_api.sh prints, which keeps `INTAKE_REUSE=1` (`INTAKE_REUSE=1 RUN_DIR=<folder> bash run_api.sh …`). Without it, the apply step runs intake again, which replaces the copied intake result (and a scanned CJK book stops there for OCR_LANG).
  - The reply is checked against today's audit as any reused reply is: what no longer fits is dropped and listed. OCR-word readings are used only when the OCR-word list is the same; a reply that predates the fingerprint loses them (the OCR-words row is a CHECK).
- **Reviews made before sessions were kept** (`record.json` has the review's changes and counts, not each card's choice) become session 1, *summary only*: "Session 1 (summary only): 159 approved, 8 seen, no changes; per-decision choices were not recorded before 2026-10-27". When nothing was accepted without review, each card's choice is rebuilt from the recorded changes, and kept only if the rebuilt order gives exactly the recorded changes and counts; those cards show "approved (inferred)" and point to session 1. Otherwise the new session starts from the AI's decisions, with the summary on the page.
- **Batches:** re-applying a book in a batch folder rebuilds the batch's `summary.html`; `summary.md` stays as the batch run wrote it.

## What the page shows

- **Check these first.** Decisions in categories where a mistake is likely or affects much of the book. They are chosen by fixed rules (no model), grouped in this order, and sorted by page within each group:
  1. **H1 and title:** any decision that makes or unmakes an H1, and the document title.
  2. **Style-wide mappings:** each `rolemap` entry, most elements first. One entry changes every element of that style.
  3. **Heading-level changes:** a `retype` that changes a heading level, or turns a heading into body text or the reverse.
  4. **Rules that can hide text:** artifact text rules and untagged rules, with their pattern and page range.
  5. **Pages the AI asked about:** deferrals with a specific page range, and the AI's note when it names pages ("PDF 4").
  6. **General:** deferrals with no pages, or covering more than half the book.
- **All** lists every decision by kind; **Not reviewed** lists what is left.
- Each card has labeled lines: **Page** ("PDF p. 2 (printed i)", or a page range), **Decision type**, the element (for example **Text on the page**), **What this does** (a plain-language description of the effect, written by the page for each kind of decision, not by the AI), **Change** or **Original** and **AI's choice**, and **AI's reason** (the model's own short `why`). Decoration rules are described in words (**Hides**, **Where on the page**, **Marked as**), with the AI's exact entry under a fold. An **AI confidence** below 1 is flagged on any kind of decision. The decision's ID (for example `retype:1154 0`: the kind of decision and the element's object number in the original PDF) is in small print at the bottom. Every card with a page shows that page; heading decisions also show the pages either side; alt text shows the figure crop; an OCR word shows the word cut from the scan, the same image the AI read. Page images are made the first time you scroll to them, so there is no limit on how many a book can have. Click an image to enlarge it.
- The box for a new value appears only when **Change** is selected. Edits are limited to valid values:
  - a heading level from a list (H1–H6, P, Span, Caption, Note, Div), with a warning on a style mapping saying how many elements it changes;
  - alt text, spoken text and OCR readings as text;
  - the language as a tag;
  - table header rows and columns as numbers 0–3.

  Artifact rules and the remaining keys (`sections`, `links` and the like) can only be approved or rejected; to edit a rule's pattern, edit `workorder.json` by hand (below).
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

For example, after changing godzone's half-title (PDF 2, `1154 0`) from H1 to P on its card, add a Heading or tag change for the title page (`1155 0`, PDF 4) as H1.

- **A target the AI already decided is not in the list:** change it on its card.
- **A figure the AI marked as decoration needs that decision rejected first,** before alt text can be added; the form says so.
- **Additions go through the same checks as the AI's decisions,** except for the two rules about images the model never saw. Those exist so the model cannot describe a figure it did not see; you see the page. An addition is written in the AI's shape, with `why` "added by <name> in review", and appears in the record as `added`.
- **Only targets the audit listed can be chosen.** Artifact text rules (a pattern over a page range) and the remaining keys (`sections`, `toc` and the like) cannot be added on the page; edit `workorder.json` by hand (see "Without the page").

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
- `review.html` has a "Review of the AI's decisions" section: the session table (the current one marked), each decision's status (approved, changed, rejected, seen, accepted without review; "(inferred)" for a summary-only session's rebuilt choices) with the session that set it, and the command that reopens the review. A run never reviewed shows its decision count by kind, all applied without review.

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
- The server answers only to itself: the `Host` must be `localhost` or `127.0.0.1` on its port, and a POST must be `application/json` from the page's own origin. Another web page open in the browser cannot submit a review.
