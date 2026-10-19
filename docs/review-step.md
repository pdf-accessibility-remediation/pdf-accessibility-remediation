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
3. **On the page,** enter your name, then go through the cards. Each decision has **Approve**, **Change** or **Reject**, and a note. Deferrals and the AI's note to the reviewer have **Seen** only, because nothing applies them.
   - **Save** checks your choices with the same rules `decide.py` uses on the AI's reply, and shows anything that would be dropped. For example, `english` as a language is not a BCP 47 tag.
   - **Finish review** records the review and stops the server. If some decisions are not reviewed, it asks whether to accept them unchanged; they are then recorded as *accepted without review*.
4. **Rerun the same command** (same label, no `REVIEW=1`). `decide.py` is skipped (no API call) and the reviewed `workorder.json` is applied.

Until the review is finished, rerunning the label is refused, so a half-reviewed work order never reaches `apply.py`. Batches (`batch_api.sh`) refuse `REVIEW=1`, because they run unattended.

## What the page shows

- **Check these first.** Decisions in categories where a mistake is likely or affects much of the book. They are chosen by fixed rules (no model), grouped in this order, and sorted by page within each group:
  1. **H1 and title:** any decision that makes or unmakes an H1, and the document title.
  2. **Style-wide mappings:** each `rolemap` entry, most elements first. One entry changes every element of that style.
  3. **Heading-level changes:** a `retype` that changes a heading level, or turns a heading into body text or the reverse.
  4. **Rules that can hide text:** artifact text rules and untagged rules, with their pattern and page range.
  5. **Pages the AI asked about:** deferrals with a specific page range, and the AI's note when it names pages ("PDF 4").
  6. **General:** deferrals with no pages, or covering more than half the book.
- **All** lists every decision by kind; **Not reviewed** lists what is left.
- Each card has labeled lines: **Page** ("PDF p. 2 (printed i)", or a page range), **Decision type**, the element (for example **Text on the page**), **What this does** (a plain-language description of the effect, written by the page for each kind of decision, not by the AI), **Change** or **Original** and **AI's choice**, and **AI's reason** (the model's own short `why`). Decoration rules are described in words (**Hides**, **Where on the page**, **Marked as**), with the AI's exact entry under a fold. An **AI confidence** below 1 is flagged on any kind of decision. The decision's ID (for example `retype:1154 0`: the kind of decision and the element's object number in the original PDF) is in small print at the bottom. Heading decisions show the page and the pages either side; alt text shows the figure crop; an OCR word shows the word cut from the scan, the same image the AI read. Page images are made the first time you scroll to them, so there is no limit on how many a book can have. Click an image to enlarge it.
- The box for a new value appears only when **Change** is selected. Edits are limited to valid values:
  - a heading level from a list (H1–H6, P, Span, Caption, Note, Div), with a warning on a style mapping saying how many elements it changes;
  - alt text, spoken text and OCR readings as text;
  - the language as a tag;
  - table header rows and columns as numbers 0–3.

  Artifact rules and the remaining keys (`sections`, `links` and the like) can only be approved or rejected; to edit a rule's pattern, edit `workorder.json` by hand (below).
- A **page index** at the side lists the pages of the "check first" items. On a narrow screen the side list folds away behind a **Sections** button.
- To undo a choice, click the selected option again, or **Clear**: the decision goes back to not reviewed. Its note stays.

## What is recorded

- `review.json` (folded into `record.json` as `review.workorder`): reviewer, date, `method` (`page` or `hand-edit`), every change (`where`, `id`, `changed` / `removed` / `added`, the AI's value and the person's), edits not accepted by the check, counts (approved, changed, rejected, seen, accepted without review), the reviewer's notes, and earlier reviews under `history`.
- `record.json` also keeps the AI's version as `workorder_ai` when the person changed anything. `workorder` is what was applied, and carries `reviewed_by`.
- `review.md` gets a row in the automated checks ("Work order reviewed by a person before it was applied"). The row is a CHECK when decisions were accepted without review or an edit was dropped. It also gets a section listing each change, AI → person.

## Without the page

Edit `workorder.json` by hand (the AI's version stays in `workorder.ai.json`), then:

```bash
python3 review_workorder.py ../runs/godzone/rv1 --reviewer "Your Name" [--note TEXT]
```

The edited order goes through the same checks, and `review.json` gets the same record with `method: hand-edit`. Leave `source` as it is, or the command refuses. Bad JSON is reported with its line number.

## Limits

- **The priority list points at risky kinds of decisions, not at wrong ones.** A confident wrong decision outside those categories is only in **All**.
- **The AI rarely gives a `confidence`** (2 items across the nine v8 books). Where it does, a value below 1 is marked on the card.
- **Lists can be long.** buddhist re-levels 50 headings, so group 3 has 50 cards.
- **The page cannot add a decision.** It approves, changes or rejects the AI's decisions only. For example, after changing a half-title from H1 to P, making the title page the H1 instead needs a hand edit of `workorder.json`, recorded with `--reviewer` (see "Without the page").
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
