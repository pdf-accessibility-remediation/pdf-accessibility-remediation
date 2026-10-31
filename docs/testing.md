---
title: Testing
nav_order: 12.5
---

# Testing

There are three kinds of tests. None of them calls the model, and none costs anything.

| Test | What it checks | Run it (from `pipeline/`) | Time |
|---|---|---|---|
| **Unit tests** | That each small rule in `lib/` does its job, using made-up inputs; plus a few small synthetic PDFs through the real pdfplumber, `audit.py`, `apply.py` and `verify.py` | `python -m pytest tests -q` | a few seconds |
| **Regression test** | That whole books still come out the same, using saved model replies | `python3 tools/regression.py --jobs 3` | about 7 minutes for all seven books (18 one at a time; `--books godzone` about 1) |
| **Reorder case** | That `move_section` works on a real book's tag tree, from a hand-written reply | `python3 tools/reorder_case.py` | about 3 minutes |
| **Intake cases** | That intake sorts pages and tag trees correctly, using small synthetic PDFs | `python3 tools/intake_cases.py <out_dir>` | under a minute |

Install the test tools once, in the same virtual environment: `pip install -r requirements-dev.txt` (it includes `requirements.txt` and adds pytest).

## Unit tests

The tests in `pipeline/tests/` call one function at a time with hand-made inputs:

- `test_gaptext.py`: where word breaks go in text that has no space characters. This covers a wide gap, letter-spaced type, a gap filled by another glyph, line ends with and without a hyphen, and vertical text.
- `test_listrule.py`: real list markers (`•`, `1.`, `(a)`, `iv)`), and the false one-item list made from a paragraph's first word.
- `test_langtag.py`: language tags that are tidied (`en_US` → `en-US`), and values that are not tags (`english`).
- `test_workorder_check.py`: one test for each reason the work-order checks drop an item. That includes unknown keys and objects, tag types that are not allowed, bad regexes and page ranges, table header counts, alt text for an image that was not sent, and language tags. It also covers the [OCR word](ocr-words.md) readings, including the one-third limit and the quarter cost of OCR junk characters.
- `test_readorder.py`: which sections are read away from their printed place (a small misplaced story is flagged, not the chapter it sits in; a child is never compared with its parent; Divs around figures are skipped), the digest's line format read back, and the `move_section` match with one, none or several candidates.
- `test_review_core.py`: the review page's reading-order cards (group 5, their pages, the move preview, orphan text for their pages only), rejecting them, and the reading-order list from `fulltext.json` or from the digest's lines.
- `test_sections.py`: `review.md` turned into sections and back gives the same lines, and the WCAG-only view leaves out the PDF/UA-only parts.
- `test_synthetic.py`: small PDFs built by the test, for rules no tagged sample reaches. One page sets its words with no space characters, as TeX does (moves between words, or kerning inside one `TJ`); read through pdfplumber, the words must come out with spaces between them. One page has a tagged one-item list made from a paragraph's first word ("as …") next to a real list ("1.", "2."). `audit.py` must mark only the first for the rule, and `apply.py` with an empty work order must turn it into a paragraph, or keep it when `keep_lists` names it. A four-page book with one section read out of printed order goes through `audit.py`, the review page's preview, `apply.py` with a `move_section` and `verify.py`: the preview must show the order `apply.py` makes, and verify's section check must mark the original's flag as "already in the original" and a bad move's flag as new. These run the real scripts with `VERAPDF=off`.

The expected values come from the module docstrings and from [Work order](work-order.md) and [OCR words](ocr-words.md), not from what the code happens to return. A failing unit test means a rule changed. If the change was intended, update the test's expected value in the same PR.

## Regression test

`tools/regression.py` runs the books in `pipeline/tests/baseline/` (godzone, clans, translation, cadaverous, sands, buddhist and ilokano) through the whole pipeline with `run_api.sh` and `REPLY=`, so the saved model reply is used instead of an API call. Each book's folder holds:

| File | What it is |
|---|---|
| `reply.txt`, `reply.txt.meta.json` | The saved model reply, with the model and temperature that produced it. This is the run's fixed input |
| `review.md` | The report the last accepted run wrote |
| `_intake/` | Untagged books only (ilokano): `intake.json` and `intake.pdf`, the intake result the reply was written for. It is reused (`INTAKE_REUSE=1`, as `FROM=` batches do) instead of rerunning OCR and auto-tagging, whose output varies with the Tesseract and OpenDataLoader versions. A note is printed when `requirements.txt` pins another OpenDataLoader than the one that made it; re-seed then |
| `expect.json` | A fingerprint of that run's `record.json`: veraPDF rules before and after, what `apply.py` did, what the work-order checks dropped, the tag counts, headings and figures `verify.py` found |

Each run is compared with the baseline in three ways:

1. **`expect.json`**, field by field.
2. **`review.md`**, line by line. Three lines are left out: `Time:` and the run-start line, which change on every run, and `Libraries:`, which changes with the Python version.
3. **Checks that must always hold, whatever the baseline says:**
   - veraPDF ran
   - no more WCAG rules fail after the run than before it
   - nothing failed in `apply.py`
   - no page looks different
   - no page's text changed
   - the original PDF is unchanged

The test prints one line per book (identical, or the fields and lines that differ) and exits with 1 when any book differs. It needs veraPDF (see [Verification with veraPDF](verapdf.md)). Run folders go to a temporary folder, which is kept when something differs; `--out DIR` puts them in `DIR` instead.

**Running books in parallel.** `--jobs N` runs N books at once (default: the `JOBS` environment variable, as for `batch_api.sh`, else 1). The biggest books start first, and the report still lists the books in their usual order. A book whose run fails is reported with the end of its log while the others carry on. Each book needs about 0.5–1.5 GB of memory: with 8 GB, `--jobs 3` peaked at about 5 GB used and took 7 minutes for all seven books, against 18 one at a time. No run can be shorter than the slowest book (buddhist, about 4 minutes). On WSL, check `free -h`; if memory is short, raise `memory=` in `C:\Users\<you>\.wslconfig` and run `wsl --shutdown`. CI does not use `--jobs`: each book is its own job there.

`meta.json` records the books, the prompt and the Python version the baseline was made with (Python 3.14). Another Python version prints a note, because a difference may come from the version and not from the code. CI runs godzone, clans, translation and buddhist on both Python 3.13 and 3.14, the two versions [Setup](setup.md) allows. buddhist is the one where the version could matter: its OCR word readings are checked with Python's Unicode tables (Unicode 15.1 in 3.13, 16.0 in 3.14). The other books run on 3.14 only. Run one book with `--books translation`; `--update --books X` adds X to the baseline and keeps the others.

**What it covers, and what it does not.**

| Book | Adds |
|---|---|
| godzone, clans | alt text, artifacts, document settings, flattened lists and tables, retyped headings, the role map, sections |
| translation | tables, notes, captions, the table of contents, whole-page figures, merged headings, ActualText, empty containers, untagged lines and borders |
| cadaverous | `language`, `lists`, `fix_figure_order` |
| sands | `adopt_orphans` |
| buddhist | `ocr_words` (its OCR text layer) |
| ilokano | an untagged book: an OpenDataLoader tag tree, so the one-item list rule (15 lists) and word breaks that rely on gaps |

Not covered by the regression test: `move_section` (no saved reply uses it; the synthetic test above and `tools/reorder_case.py` cover it), intake itself (frozen here; `tools/intake_cases.py` tests it on synthetic PDFs), OCR on a real book, and CJK text. To check all nine tagged samples, rerun them from saved replies before and after your change, then compare the two batches with [compare_runs.py](batch-runs.md):

```bash
FROM=all9-v8 AUTO=1 bash batch_api.sh before ../samples/group1 ../samples/group2 ../samples/group3most   # on main
FROM=all9-v8 AUTO=1 bash batch_api.sh after ../samples/group1 ../samples/group2 ../samples/group3most    # on your branch
python3 tools/compare_runs.py before after
```

### When to update the baseline

The baseline is never updated automatically. A person updates it on purpose:

```bash
python3 tools/regression.py --update --reason "why the output changed"
```

This reruns the books, writes their `review.md` and `expect.json` as the new baseline, and adds the reason to `tests/baseline/UPDATES.md`. Commit the baseline changes together with the code change, so the reviewer sees both diffs side by side.

**Update** when the regression test fails, every difference is one the PR meant to make, and the always-true checks still pass. For example, a fix in `apply.py` removes clans' last PDF/UA failure. The diff then shows that veraPDF rule gone, one new entry in `apply.applied`, and the matching `review.md` lines, and nothing else.

**Do not update:**
- to make CI pass when you don't understand a difference
- in a PR that was not meant to change any output, such as a refactor
- when an always-true check fails; `--update` refuses then

In the example above, if the diff also showed two headings gone (`verify.tree_types.H2: 7 → 5`), that would be a bug, not a new baseline.

Make one update per PR, with its own reason. Don't fold several unrelated changes into one update.

**After a failed CI run:** each failed regression job uploads its run folder as the `regression-runs-<book>-py<version>` artifact. To adopt it without rerunning, download the artifact and run `python3 tools/regression.py --update --books <book> --from-dir <downloaded folder> --reason "…"` (take the Python 3.14 artifact: the baseline's version).

**After a prompt change:** the saved replies were written for one prompt version (`meta.json` → `prompt`). When `decide.py` uses a new prompt, the test stops and asks for a re-seed instead of showing a diff. To re-seed:

1. Run the baseline books with the new prompt. This is a paid call, about $1.70 for the seven; ask first. ilokano is a single run (`bash run_api.sh ../samples/untagged/ilokano.pdf ilokano <label>`), the others a batch.
2. Run `python3 tools/regression.py --update --seed ../runs/batches/<label> --reason "prompt vN"` for the tagged books, and `--update --books ilokano --seed ../runs/ilokano/<label>` for ilokano (a single run folder; its `_intake/` is copied too).

`--seed` copies each book's `raw_reply` from its `record.json`.

## Reorder case

`tools/reorder_case.py` covers `move_section` on a real tag tree without a model reply. It swaps one section with the next under a section host in a copy of a tagged sample (godzone by default: a chapter on PDF 10–18 under the Part), then runs the pipeline with a reply that holds only the `move_section` putting it back. It checks that the audit flags the pair, that the review page's preview finds one section and its host, that `apply.py` makes the move and logs the same section and host, that the host's sections read in the book's order again, that the preview's order is the one `apply.py` made, and that verify's section check finds nothing new. Run it after a change to `lib/readorder.py`, `op_move_section` or the review page's preview.

## Intake cases

`tools/intake_cases.py` builds synthetic PDFs with no book content and checks what `intake.py --plan-only` decides for each:

- an empty text object over a scan, an OCR layer, a text page
- placeholder and real tag trees
- existing OCR layers scored against their scan: one that matches, one missing the breves the scan shows (ŏ, ŭ), and one too short to score
- two printed pages side by side (two-up spreads, a vertical-OCR spread, spreads with years in the running heads) and a landscape page with one wide column, which is not a spread
- Japanese, vertical Japanese and Korean scans, and 14-page scans for the sampled CJK check

It also checks that a spread's reading order is reordered and saved. It prints PASS, FAIL or SKIP per case, a summary line, and exits with 1 on any FAIL. `--full` also runs the whole intake on the empty-text scan (the empty text object is removed and OCR text added; needs OCRmyPDF 17), on the two placeholder-tree cases (the old tree is set aside and OpenDataLoader makes a real one) and on the two-up spreads (read half by half); auto-tagging needs Java 11 or later. This is what tests intake itself, since the regression test reuses ilokano's frozen intake result.

Several scans are drawn with a font: the Japanese and Korean text, the breves, and the page the full empty-text case OCRs. On macOS that is Arial Unicode, on Linux Noto Sans CJK (`sudo apt install fonts-noto-cjk`); `INTAKE_CASES_FONT=/path/to/font` overrides both. Without such a font, PIL's default font draws no CJK and no breves, and its text is too small to OCR, so those cases are SKIPped. The summary line counts skips separately, so a skip is never mistaken for a pass. The CJK cases also need Tesseract's `osd`, `jpn`, `kor`, `chi_sim` and `chi_tra` packs, each with its `_vert` pack. Two OCR-layer cases need the `script/Latin` model (`tesseract-ocr-script-latn`; see [Setup](setup.md)); without it they are SKIPped. When an OCR-layer case fails, the script prints intake's OCR-layer test under it: the verdict, and each sample page's score or why it was not scored.

## Updating the tests

| Change | Unit tests | Regression | Intake cases |
|---|---|---|---|
| New rule or check in `lib/` | Add tests | Maybe update the baseline | — |
| Changes the output for a baseline book | — | Update the baseline (free) | — |
| New prompt version | — | Re-seed (a small paid run) | — |
| Intake change, or a new OpenDataLoader version | — | Re-seed ilokano (a small paid run), since its frozen intake no longer matches | Update or add cases |
| Refactor with no change in behaviour | Must pass unchanged | Must pass unchanged | Must pass unchanged |

## In CI

- **`ci.yml`, on every push and PR:**
  - compile check, shell syntax and `pip-audit`, as before
  - the unit tests
  - a second job that installs Tesseract with its CJK packs, the `script/Latin` model and `fonts-noto-cjk`, then runs the intake cases, then `--full` with Java 17 and OCRmyPDF 17 (installed with pipx; not yet blocking: `continue-on-error` until it has passed a few times on Linux CI)
- **`pdf-validation.yml`, when `pipeline/`, `prompts/` or `samples/` change:**
  - the existing veraPDF audit of one sample
  - a `regression` job per book and Python version (all seven books on 3.14; godzone, clans, translation and buddhist also on 3.13: 11 jobs in parallel, with Java 17 and veraPDF 1.30.3) that runs `tools/regression.py --books <book>`, and uploads the run folders when it fails (`regression-runs-<book>-py<version>`)
