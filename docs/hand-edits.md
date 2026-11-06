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

Step 3 makes `runs/hawaii3/rv1-edit/` (by default the label is `handedit-<date>-<time>`) and stops for review, as `REVIEW=1` does. Then:

1. Open the review page:
   - from the app: `python3 app.py ../runs/hawaii3/rv1-edit`;
   - or from the terminal: `python3 review_workorder.py ../runs/hawaii3/rv1-edit --serve`.
2. Write the alt text the edit needs, then select **Finish Review**.
3. Apply the review: press **Apply** in the app, or run the command `handedit.py` printed. The result, `review.md`, `record.json` and the evaluation work as for any run.

**Never edit the run's own PDF in place.** Its sha256 is what the [accessibility evaluation](release.md#each-check-belongs-to-one-file) counts. An edited result is evaluated and shipped in its own run.

`export` refuses when the run's PDF no longer matches `record.json`, because it was changed in place. So does `import`.

## Back into review, or back into the pipeline

| `--to` | What runs | Cost |
|---|---|---|
| `review` (the default) | Intake (skipped for a tagged file), audit, **no AI call** (`DECIDE=none`: the work order starts empty), the review page, then apply, verify and report | $0 |
| `pipeline` | The whole pipeline on the edited file, with a new AI call (`run_api.sh` asks y/N first; `ESTIMATE=1` and `REPLY=` work as usual) | a normal run |

**Review is the usual choice.** The remediated result already holds the earlier run's fixes, so the review needs only what the edit changed.

The empty work order does take two decisions from the run it came from, when the edit kept the number of pages: which pages are contents, notes and index (`sections`), and the fixes to contents link text (`links`). Both are by page number, so they still fit. `apply.py` redoes every link's description on each run, and without them a contents link would lose its "Chapter title, page 12" description. They are listed in `record.json` `run.carried_from_parent` and in `review.md`'s "Edited by hand" section. No decision by object number is carried, because an edited file's object numbers differ.

Choose `pipeline` when the edit was large, for example new pages, or when the edited file is the **original** (`--base original`, below), which holds none of the earlier fixes.

## Figures whose image changed

`import` compares the edited file with the file it was made from, page by page. Two images count as the same when their image data is byte for byte the same, so a save that renumbers every object changes nothing here.

A figure that now holds a new image keeps the old image's alt text in the edited file. That text describes the old image. So it is removed (with any spoken text, `ActualText`) in a working copy, `_handedit/input.pdf`, which the run works on. The old alt text is never reused for a new image:

- **On the review page**, each such figure is a figure with no alt text. It is listed under the gaps (and Finish asks about it), with an **Add** link to write its alt text. A line under the header says what was edited, by whom, and which pages hold a new image.
- **With `--to pipeline`**, the AI sees those figures with no alt text and writes it.
- **In `review.md`**, the "Edited by hand" section has a table: each figure's page, the alt text removed, and the alt text written on that page in this run. A row with none written says so.

New images that no figure holds are listed too, so you can decide whether each is a figure or decoration. A change in the number of pages is also listed.

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
| `<new run>/_handedit/hand_edit.json`, and `record.json` `hand_edit` | `by`, `when`, `note`, `to`, `base` (`output` or `original`) and `base_sha256`; `parent` (the run, its result and original, with their sha256s); `edited` (file, sha256, where it was given from); `input`; `pages` (before, after); `figures_changed` (page and the alt text removed); `alt_not_removed` (a figure that could not be found again, left as it was); `outside_figures`; `images_new`, `images_removed` |
| `<parent run>/hand_edits.json` | `exports` (who, when, which file, its sha256, where it went) and `children` (each run made from an edit: its folder, who, the note, the edited sha256). The only file `handedit.py` writes in the parent run |
| `review.md` and `review.html` | The "Edited by hand" section. With `--to review`, the run line says "no AI call", the AI cost is $0, and the sections say "in this run" instead of "by the AI" |

A run with no AI call has `run.no_model` and `ai_call.no_model` in `record.json`, and `cost_total_usd` is 0.

## Limits

- **Only images are compared.** An edit to text, tags or reading order is not listed. The new run's audit, veraPDF and the review show its effect, and your `--note` says what it was.
- **Image resolution is not checked.** Nothing flags a low-resolution image. You find one by looking.
- **Not in the app yet.** Export and import are terminal commands. The app opens the new run like any other.
- **PDF 2.0.** An edited file saved as PDF 2.0 is refused (exit 3; see [Not supported yet: PDF 2.0](troubleshooting.md#not-supported-yet-pdf-20)).
