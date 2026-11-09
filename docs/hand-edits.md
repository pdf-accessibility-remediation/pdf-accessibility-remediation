---
title: Editing the PDF by hand
nav_order: 3.8
---

# Editing the PDF by hand and bringing it back

Sometimes the PDF itself has to change in ways the work order can't express. Examples: a low-resolution photo that needs a better scan, or a reading-order fix only Acrobat can make (see [Fixing the reading order by hand](review-step.md#fixing-the-reading-order-by-hand)).

Make the change in Acrobat or another tool, on an **exported copy**. Then bring the edited file back with `handedit.py`. It becomes a **new run** of the same book, linked to the run it came from. That run is audited, reviewed or decided, applied, verified and reported again, so the edit is checked like any other result.

The original PDF and the run's own result are never changed.

## Steps

From `pipeline/`:

```bash
# 1. Export the run's result for editing (a copy; logged in the run's hand_edits.json)
python3 handedit.py export ../runs/hawaii3/rv1 --by "Your Name"
#    → ../runs/hawaii3/rv1/exports/hawaii3_remediated_for-editing.pdf   (--to PATH puts it elsewhere)

# 2. Edit that copy in Acrobat and save it.

# 3. Bring it back for review: no AI call, $0
python3 handedit.py import ../runs/hawaii3/rv1 path/to/edited.pdf --by "Your Name" \
    --note "replaced the low-resolution photo on PDF 12" --label rv1-edit
```

**All from the app:** download the current version, edit it, then use **Bring Back an Edited PDF** on the run page and choose the edited file. It uploads the file and replaces steps 1 and 3 (see [The app](app.md#the-run-page)). It offers only the review path (no AI call).

**From the app instead of step 1:** **Download the Remediated PDF** (under **Available Downloads**) gives the same file for the **current** version. The app logs it under `exports` with `via: "app download"` and no name, because the app has no logins. Never edit a download of an earlier version: `import` compares the edited file with the run's current result, so the changes it reports would be wrong.

**Finish the work order first, and do the hand edit last.** The edited run starts from a file that already holds every earlier decision (see "What a review of an edited PDF shows" below).

Step 3 makes `runs/hawaii3/rv1-edit/` (by default the label is `handedit-<date>-<time>`) and stops for review, as `REVIEW=1` does. Then:

1. Open the review page:
   - from the app: `python3 app.py ../runs/hawaii3/rv1-edit`;
   - or from the terminal: `python3 review_workorder.py ../runs/hawaii3/rv1-edit --serve`.
2. Write the alt text the edit needs, then select **Finish Review**. The first section, **Edited by Hand**, has a card for each figure the edit touched: its page, what happened, the alt text it had, and an **Add Alt Text** button that opens the form for that figure. For a figure that lost its tag, the form starts with the alt text it had, as a suggestion to check. Once the alt text is added, the card says so.
3. Apply the review: press **Apply** in the app, or run the command `handedit.py` printed. The result, `review.md`, `record.json` and the evaluation work as for any run.

**Never edit the run's own PDF in place.** Its sha256 is what the [accessibility evaluation](release.md#each-check-belongs-to-one-file) counts. An edited result is evaluated and shipped in its own run.

`export` refuses when the run's PDF no longer matches `record.json`, because it was changed in place. So does `import`.

## Before you edit in Acrobat

Acrobat can change pages you never touched:

- **Edit PDF can run text recognition (OCR) by itself** on a page that is one image, such as a cover. It rewrites that page: the image is saved again (in one test, as two images) and the page loses its tags, including the figure's alt text. Turn it off before you start: in Edit PDF, choose **Edit** → **Edit settings** and uncheck **Recognize scanned text**. With it off, a test that replaced one logo changed nothing else.
- **It can drop the space characters between words** on pages it rewrites. The words usually stay apart on the page, so a reader still hears the spaces.

`import` reports both, so nothing goes back unseen (below).

## Back into review, or back into the pipeline

| `--to` | What runs | Cost |
|---|---|---|
| `review` (the default) | Intake (skipped for a tagged file), audit, **no AI call** (`DECIDE=none`: the work order starts empty, and no pages are read with the AI either, `PAGE_READS=off`), the review page, then apply, verify and report | $0 |
| `pipeline` | The whole pipeline on the edited file, with a new AI call (`run_api.sh` asks y/N first; `ESTIMATE=1` and `REPLY=` work as usual) | a normal run |

**Review is the usual choice.** The remediated result already holds the earlier run's fixes, so the review needs only what the edit changed.

The empty work order does take two decisions from the run it came from, when the edit kept the number of pages: which pages are contents, notes and index (`sections`), and the fixes to contents link text (`links`). Both are by page number, so they still fit. `apply.py` redoes every link's description on each run, and without them a contents link would lose its "Chapter title, page 12" description. They are listed in `record.json` `run.carried_from_parent` and in `review.md`'s "Edited by hand" section. No decision by object number is carried, because an edited file's object numbers differ.

Choose `pipeline` when the edit was large, for example new pages, or when the edited file is the **original** (`--base original`, below), which holds none of the earlier fixes.

## Figures whose image changed

`import` compares the edited file with the file it was made from, page by page. Two images count as the same when their image data is byte for byte the same, so a save that renumbers every object changes nothing here.

A figure that now holds a new image keeps the old image's alt text in the edited file. That text describes the old image. So it is removed (with any spoken text, `ActualText`) in a working copy, `_handedit/input.pdf`, which the run works on. The old alt text is never reused for a new image:

- **On the review page**, each such figure is a figure with no alt text. It has a card under **Edited by Hand** and is listed under the gaps (Finish asks about it). The summary at the top of that section says who edited the file, when, their note, and what the edit changed.
- **With `--to pipeline`**, the AI sees those figures with no alt text and writes it.
- **In `review.md`**, the "Edited by hand" section has a table: each figure's page, the alt text removed, and the alt text written on that page in this run. A row with none written says so.

New images that no figure holds are listed too, so you can decide whether each is a figure or decoration. A change in the number of pages is also listed.

## Figures that lost their tag, and text that changed

`import` also compares what it can of the rest of the file:

- **A figure that lost its tag.** If a figure held an image in the exported file and no figure holds it in the edited one, it is listed with the alt text it had. The image is still drawn, but nothing tags it, so a screen reader skips it.
  - A page left with no tags at all becomes a whole-page figure, and the review page asks for its alt text. Its card's **Add Alt Text** button opens the form with the old alt text already filled in, marked as a suggestion. It is usually right, because the image is the same picture.
  - On a page that still has other tags, re-tag the image in Acrobat, or check that it is meant to be decoration.
- **Text that changed.** Each page whose characters differ is listed:
  - **Read the same:** only space characters went. The page still reads the same with spaces taken from the gaps between words, as the pipeline reads it. `review.md` says so in one line.
  - **Reads differently:** `review.md` marks the pages as a CHECK, and the summary at the top of the review page's Edited by Hand section names them. Compare them with the earlier run and with the print.

## What a review of an edited PDF shows

The edited PDF already holds every decision of the run it came from: alt text, heading levels, decoration and the rest. The AI isn't asked again, and those decisions aren't shown as cards again. Approving them a second time would apply them twice, for example moving a section that is already in place, or hiding text a rule already hid. So the review page shows:

- **Edited by Hand:** the figures the edit touched (above).
- **A "Still to Review" list** at the top of Edited by Hand, kept up to date as you work. It shows the figures still without alt text, the cards under Check First not yet reviewed (by group), and any other decision not yet reviewed, each with a link. When nothing is left, it says to select **Finish Review**.
- **The decisions carried from the earlier run** (which pages are contents, notes and index, and fixes to contents link text) get no card: there is nothing to decide. They keep the contents links' descriptions, which `apply.py` writes again on every run. The summary names them ("Carried from the earlier run, no action needed: contents pages (PDF 6–11)"), and they are applied as written.
- **What today's audit finds anywhere in the book.** These are not things the first run missed. Anything it fixed is in the file and doesn't come back. What comes back:
  - findings the pipeline can't fix, such as text that jumps back up a column on one page;
  - book-wide gaps, such as no H1 or a figure with no alt text.

  When such a check card was marked seen with a note in the earlier review, the card shows that note ("Earlier Note") if the number of pages is unchanged. You still mark it seen yourself.
- **Earlier Review (for reference)**, at the end of the page, read-only: the earlier run's decisions by kind, each with its page, value, status (approved, changed, applied as the AI wrote it, …) and the reviewer's note. It is there for reference; nothing in it is applied again.

**To change an earlier decision after the edit**, add it in the edited run with **Add a Decision**: none of the earlier decisions is decided again there, so each one can be added.

Don't use `--reopen` on the earlier run for this: it rebuilds that run's PDF from the original and its work order, so the hand edit isn't in that result.

## Starting from the original

To edit the original instead of the remediated result:

- export it with `export RUN --original --pdf ORIGINAL.pdf`;
- bring it back with `import RUN EDITED.pdf --base original --base-pdf ORIGINAL.pdf …`.

The original is checked against `record.json` (`document.sha256`). The run's earlier work order is not carried over, because the edited file's object numbers differ. Use `--to pipeline`, unless you will make every decision yourself on the review page.

## What is recorded

| Where | What |
|---|---|
| `<new run>/_handedit/<edited file>` | A copy of the file you edited: the new run's source (`record.json` `document.sha256`). Your own file is never written to |
| `<new run>/_handedit/input.pdf` | Only when a figure's alt text was removed: what the run worked on (`document.pipeline_input`) |
| `<new run>/_handedit/hand_edit.json`, and `record.json` `hand_edit` | `by`, `when`, `note`, `to`, `base` (`output` or `original`) and `base_sha256`; `parent` (the run, its result and original, with their sha256s); `edited` (file, sha256, where it was given from); `input`; `pages` (before, after); `figures_changed` (page and the alt text removed); `alt_not_removed` (a figure that could not be found again, left as it was); `outside_figures`; `images_new`, `images_removed`; `figures_lost` (page and the alt text the figure had); `text_pages` (page, characters before and after, `heard_same`) |
| `<parent run>/hand_edits.json` | `exports` (who, when, which file, its sha256, where it went) and `children` (each run made from an edit: its folder, who, the note, the edited sha256). The only file `handedit.py` writes in the parent run |
| `review.md` and `review.html` | The "Edited by hand" section. With `--to review`, the run line says "no AI call", the AI cost is $0, the sections say "in this run" instead of "by the AI", the Overview says "Decisions (no AI call)", and a review "started from an empty work order (no AI call)". On the run page and the review page, "the AI's decisions" becomes "the beginning" (**Start Over from the Beginning**) |

A run with no AI call has `run.no_model` and `ai_call.no_model` in `record.json`, and `cost_total_usd` is 0.

## Limits

- **Only images, figure tags and text are compared.** Other changes to tags or reading order are not listed. The new run's audit, veraPDF and the review show their effect, and your `--note` says what you changed.
- **Image resolution is not checked.** Nothing flags a low-resolution image. You find one by looking.
- **The app brings an edited PDF back for review only.** A new AI call (`--to pipeline`), `--base original` and `--label` are terminal options.
- **PDF 2.0.** An edited file saved as PDF 2.0 is refused (exit 3; see [Not supported yet: PDF 2.0](troubleshooting.md#not-supported-yet-pdf-20)).
