---
title: Testing
nav_order: 12.5
---

# Testing

There are three kinds of tests. None of them calls the model, and none costs anything.

| Test | What it checks | Run it (from `pipeline/`) | Time |
|---|---|---|---|
| **Unit tests** | That each small rule in `lib/` does its job, using made-up inputs (no PDF) | `python -m pytest tests -q` | about 1 second |
| **Regression test** | That whole books still come out the same, using saved model replies | `python3 tools/regression.py` | about 6 minutes (`--books godzone` about 1) |
| **Intake cases** | That intake sorts pages and tag trees correctly, using small synthetic PDFs | `python3 tools/intake_cases.py <out_dir>` | under a minute |

Install the test tools once, in the same virtual environment: `pip install -r requirements-dev.txt` (it includes `requirements.txt` and adds pytest).

## Unit tests

The tests in `pipeline/tests/` call one function at a time with hand-made inputs:

- `test_gaptext.py`: where word breaks go in text that has no space characters. This covers a wide gap, letter-spaced type, a gap filled by another glyph, line ends with and without a hyphen, and vertical text.
- `test_listrule.py`: real list markers (`•`, `1.`, `(a)`, `iv)`), and the false one-item list made from a paragraph's first word.
- `test_langtag.py`: language tags that are tidied (`en_US` → `en-US`), and values that are not tags (`english`).
- `test_workorder_check.py`: one test for each reason the work-order checks drop an item. That includes unknown keys and objects, tag types that are not allowed, bad regexes and page ranges, table header counts, alt text for an image that was not sent, and language tags. It also covers the [OCR word](ocr-words.md) readings, including the one-third limit and the quarter cost of OCR junk characters.
- `test_sections.py`: `review.md` turned into sections and back gives the same lines, and the WCAG-only view leaves out the PDF/UA-only parts.

The expected values come from the module docstrings and from [Work order](work-order.md) and [OCR words](ocr-words.md), not from what the code happens to return. A failing unit test means a rule changed. If the change was intended, update the test's expected value in the same PR.

## Regression test

`tools/regression.py` runs the books in `pipeline/tests/baseline/` (godzone, clans and translation) through the whole pipeline with `run_api.sh` and `REPLY=`, so the saved model reply is used instead of an API call. Each book's folder holds:

| File | What it is |
|---|---|
| `reply.txt`, `reply.txt.meta.json` | The saved model reply, with the model and temperature that produced it. This is the run's fixed input |
| `review.md` | The report the last accepted run wrote |
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

`meta.json` records the books, the prompt and the Python version the baseline was made with (Python 3.14). Another Python version prints a note, because a difference may come from the version and not from the code. CI runs every book on both Python 3.13 and 3.14, the two versions [Setup](setup.md) allows, so a difference between them shows up there. Run one book with `--books translation`; `--update --books X` adds X to the baseline and keeps the others.

**What it covers, and what it does not.** godzone and clans cover alt text, artifacts, document settings, flattened lists and tables, retyped headings, the role map and sections. translation adds tables, notes, captions, the table of contents, whole-page figures, merged headings, ActualText, empty containers and untagged lines and borders. Not covered: `language`, `lists`, `fix_figure_order`, `adopt_orphans` and `ocr_words` (the saved replies of these books don't use them); the one-item list rule, which only fires on books OpenDataLoader tagged (untagged input), and the word-gap rule (these books' text has real spaces), both covered only by the unit tests; and the whole untagged path (OCR, auto-tagging) and CJK text. To check all nine tagged samples, rerun them from saved replies before and after your change, then compare the two batches with [compare_runs.py](batch-runs.md):

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

1. Run the baseline books with the new prompt. This is a paid call, about $0.60 for the three; ask first.
2. Run `python3 tools/regression.py --update --seed ../runs/<batch folder> --reason "prompt vN"`, where the batch folder is the one holding `<book>/record.json`.

`--seed` copies each book's `raw_reply` from its `record.json`.

## Intake cases

`tools/intake_cases.py` builds synthetic PDFs with no book content and checks what `intake.py --plan-only` decides for each:

- an empty text object over a scan
- an OCR layer
- a text page
- placeholder and real tag trees
- Japanese, vertical Japanese and Korean scans

It prints PASS, FAIL or SKIP per case, a summary line, and exits with 1 on any FAIL.

The Japanese and Korean pages need a CJK font to draw their text: Arial Unicode on macOS, or Noto Sans CJK on Linux (`sudo apt install fonts-noto-cjk`). `INTAKE_CASES_FONT=/path/to/font` overrides both. Without such a font, the CJK cases are SKIPped, and the summary line counts them separately, so a skip is never mistaken for a pass. These cases also need Tesseract's `osd`, `jpn`, `kor`, `chi_sim` and `chi_tra` packs, each with its `_vert` pack.

## Updating the tests

| Change | Unit tests | Regression | Intake cases |
|---|---|---|---|
| New rule or check in `lib/` | Add tests | Maybe update the baseline | — |
| Changes the output for a baseline book | — | Update the baseline (free) | — |
| New prompt version | — | Re-seed (a small paid run) | — |
| Intake change | — | — | Update or add cases |
| Refactor with no change in behaviour | Must pass unchanged | Must pass unchanged | Must pass unchanged |

## In CI

- **`ci.yml`, on every push and PR:**
  - compile check, shell syntax and `pip-audit`, as before
  - the unit tests
  - a second job that installs Tesseract with its CJK packs and `fonts-noto-cjk`, then runs the intake cases
- **`pdf-validation.yml`, when `pipeline/`, `prompts/` or `samples/` change:**
  - the existing veraPDF audit of one sample
  - a `regression` job per book and Python version (godzone, clans, translation × 3.13, 3.14; in parallel, with Java 17 and veraPDF 1.30.3) that runs `tools/regression.py --books <book>`, and uploads the run folders when it fails (`regression-runs-<book>-py<version>`)
