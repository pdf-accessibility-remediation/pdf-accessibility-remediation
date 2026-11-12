---
title: Testing
parent: For developers
nav_order: 1
---

# Testing

This page explains the project's tests: what each kind checks, how to run it, when to update the regression baseline, and what CI runs. It ends with the rules for writing these docs. It is for developers.

There are five kinds of tests. None of them makes an AI request, and none costs anything.

| Test | What it checks | Run it (from `pipeline/`) | Time |
|---|---|---|---|
| **Unit tests** | That each small rule in `lib/` does its job, using made-up inputs; plus a few small synthetic PDFs through the real pdfplumber, `audit.py`, `apply.py` and `verify.py` | `python -m pytest tests -q` | a few seconds |
| **Regression test** | That whole books still come out the same, using saved AI replies | `python3 tools/regression.py --jobs 3` | about 10 minutes for all nine books (21 one at a time; `--books northkorea` about 2) |
| **Reorder case** | That `move_section` works on a real book's tag tree, from a hand-written reply (one move, or `--moves 2`: two, made in turn) | `python3 tools/reorder_case.py [--moves 2]` | about 3 minutes each |
| **Hand-edit case** | That a real book's result, edited by hand (one figure's image replaced) and brought back for review, is applied again safely: the figure is found, its alt is written again, nothing else changes | `python3 tools/handedit_case.py` | a few minutes |
| **Intake cases** | That intake sorts pages and tag trees correctly, using small synthetic PDFs | `python3 tools/intake_cases.py <out_dir>` | under a minute |

Install the test tools once, in the same virtual environment: `pip install -r requirements-dev.txt` (it includes `requirements.txt` and adds pytest).

## Unit tests

The tests in `pipeline/tests/` call one function at a time with hand-made inputs:

- `test_gaptext.py`: where word breaks go in text that has no space characters. This covers a wide gap, letter-spaced type, a gap filled by another glyph, line ends with and without a hyphen, and vertical text.
- `test_listrule.py`: real list markers (`•`, `1.`, `(a)`, `iv)`), and the false one-item list made from a paragraph's first word.
- `test_langtag.py`: language tags that are tidied (`en_US` → `en-US`), and values that are not tags (`english`).
- `test_workorder_check.py`: one test for each reason the work-order checks drop an item:
  - unknown keys and objects; tag types that are not allowed; bad regexes and page ranges; table header counts; alt text for an image that was not sent; language tags
  - section moves, one or a list. Dropped, each alone: one where the audit finds nothing out of place in its pages or where it lands (kept when it lands before the flagged one of a swapped pair), a fourth, an overlapping one, and one landing inside another. The full reading order is used when given.
  - the [OCR word](ocr-words.md) readings, including the one-third limit and the quarter cost of OCR junk characters
- `test_readorder.py`: which sections are read away from their printed place (a small misplaced story is flagged, not the chapter it sits in; a child is never compared with its parent; Divs around figures are skipped), the digest's line format read back, and the `move_section` match with one, none or several candidates.
- `test_review_dryrun.py`: the review stop's trial run of `apply.py` is reused while nothing it depends on has changed (#52). On a three-page figure PDF, with the real `apply.py`:
  - the same inputs a second time reuse the saved result, and give the same review items
  - a changed work order, PDF, code file or setting `apply.py` reads makes it again, while the AI turning the figure step off alone does not
  - a failed trial run, an older result without a key, a cut-short one and `REVIEW_DRYRUN=fresh` are never reused
  - the copy kept in `reviews/_audit` is reused by Review Again
  - every variable `apply.py` or `lib/` reads is part of the key
  - for a run applied from the AI's own decisions (#93): its apply's moves are kept with the key `run_api.sh` worked out before the apply, and the first Review Again reuses them and shows the same cards as a fresh trial run. Nothing is kept when the AI turned the figure step off, after a review or a re-apply, when anything in the key changed during the run, with no key or no apply log, when the record's order differs, or into any folder but the run's own `_audit/`. One builder makes the result (its source and `trial_order`'s are in the key), and a whole `run_api.sh` run on a saved reply keeps it, after which a re-apply leaves it byte for byte as it was.
- `test_handedit_trial.py`: the kept trial run on PDFs edited by hand (#93 with #62), through the whole loop at no cost (`run_api.sh` with `DECIDE=none`, `handedit.py import`, veraPDF off):
  - an edited copy applied with no review stop (`--to pipeline`'s shape) keeps its apply under its own input (`_handedit/input.pdf`); the first Review Again reuses it and shows what a fresh trial run shows; the kept result is never reused for the edited file as saved or for the parent's result
  - a hand edit brought back for review (`--to review`) keeps nothing and says why ("the order applied was reviewed"), and its first Review Again shows what a fresh trial run shows
- `test_webapp_first.py`: each panel's first answer comes with its page (#93):
  - the run page (with and without `review.html`), the batch page and the home page carry exactly what the panel's first request returns, as a JSON data block that is never a script (the page's policy is unchanged) and that no text can end
  - the home page names what was moved to the Trash, and the batch page the PDFs a partial move took (three, then "and N more", escaped)
  - every kind of run page (finished, no dashboard, a PDF in a batch, waiting or pending) loads `panel.js` once, in its head, render-blocking
- `test_webapp_onestep.py`: page changes in one step (#93, Patrick 2026-11-11; [Page changes in one step](app-run-page.md#page-changes-in-one-step)):
  - no fade and nothing kept for it; html and body with the app's background, and a color scheme in every page's head; the gap above "Ready to Ship?" exactly as before the panel's call was added
  - the app's own files named with their version, and kept by the browser only when asked for by it
  - each script that draws a first view is a plain script in the head (never deferred), called right after the elements it fills (Run Actions, the evaluation strip after the "Ready to Ship?" card, a previous result's bar with its first answer, the side list, "This Batch", "Runs in Progress", the line after an upload); every call is defined, and the page's policy allows exactly its calls
  - `test_review_draft.py` checks the review page the same way: its script read in the head and called at the end, the check line it starts from exactly what `/keep` answers for the same choices, a Session Note holding `<!--` and `<script>` that can't end or hide the page's script, and image sizes read page by page (one page pdfium can't read leaves the others theirs). The frame-by-frame check is done in the browser, outside the suite.
- `test_webapp_speed.py`: the app's pages as the jobs and runs add up (#93):
  - a job's place in line, and what it waits for, are the same when the jobs check builds them once for the whole answer as when each job is looked at alone; a newer queued job counts the older ones the answer doesn't show
  - each page (the home page, a batch page and its poll, the jobs check, a batch PDF's page and its side list, a run page with its panel's first answer, and the panel's own `/api/run/<run>`) opens each names file and each job file exactly once; a Title the PDF list writes into the cache reaches the rows drawn after it
  - the home page's lighter check announces exactly what the full list announces (queued → done, running → failed, a dismissed paid job, an interrupted job that finishes, or runs again and finishes, a new waiting paid job), and checks its `seen` ids, leaving out interrupted jobs that can't change any more
  - a batch page or poll asks Tesseract for its languages once at most, and not at all when no PDF asks its language; the batch dashboard never opens a PDF for page labels it doesn't use; a PDF's page in a batch and its side list's check (`?nav=1`) never build the dashboard, while the batch page and its own check do, with the same side list
- `test_report_html_text.py`: `review.html`'s text is data, never script (#93): the page strip's data block escapes `<`, `>` and `&`, so a section title holding `<!--<script>` or `</script>` stays inside it; a link in review.md's text is live only for "#…", http:, https: and relative paths; and no link `inline()` writes is read by a browser with another scheme (`java&#115;cript:`, `javascript&colon;`, a leading space).
- `test_apply_tree_writes.py`: `apply.py` keeps its tag-tree index between steps and walks the tree again only after a write to it (#93 Part 3, C2; see [apply.py's kept tag-tree index](#applypys-kept-tag-tree-index-and-its-check-mode) below):
  - read from the code of `apply.py` and of every `lib/*.py`: no write of `/K`, `/P`, `/Pg`, `/Type`, `/MCID` or `/Stm` except through `tree_set()` (no attribute or literal-key assignment or `del`, no `.update(` naming one, no `__setattr__`/`__setitem__` called by name, no `setattr`), and `/K` read only through `kids()`; the rule is first shown to refuse each of those forms
  - on a real `apply.py` run (its globals kept): an `/MCID` written through `tree_set()` after a kept walk is seen by the next `reindex()`; one written around it is caught by the check mode, which prints its marker and stops with `TreeIndexStale`; `all_elems()` hands out a copy; and `review/core.py`'s `run_apply()` raises on the marker instead of returning a soft result
- `test_contentops.py`: `verify.py`'s untagged-content loop asks pikepdf only for the operators it acts on (`lib/contentops.py`):
  - the operator names the loop compares against, read from `verify.py`'s own code, must be exactly the filter's list; any other read of the operator in the loop (written the other way round, or through a call) fails the test
  - the filter keeps an inline image as `BI ID EI`, all three (with `BI` alone pikepdf drops everything after the first inline image; without them inline images vanish), and refuses anything else
  - the filtered parse gives the same operators, operands and order as the unfiltered one, on a page with inline images, text and paths and on three broken streams (pikepdf stops silently on those, in both modes)
- `test_verify_inline.py`: `verify.py` counts an untagged inline image as untagged content, exactly as an image XObject: built with each in turn, untagged on the page, tagged, decoration, in a form drawn on two pages (counted once), in a form drawn inside tagged content, in a form inside a form, in the second stream of a `/Contents` array, after which text and a path still count; inside a Type 3 glyph, a tiling pattern or an annotation's appearance it isn't counted (the text or fill that paints it is). End to end with no AI request, review.md's safety-check row and "Untagged Content" section name it, one object in the singular.
- `test_review_core.py`: the review page's reading-order cards:
  - group 5, their pages, the move preview, and orphan text for their pages only; rejecting them; the reading-order list from `fulltext.json` or from the digest's lines
  - the findings no decision answers: one seen-only card per section out of place that no text rule removes and per page jump, one card for the sections read late (none when rules remove them all), and every rule that removes a section named by its card id and listed on that rule's card. Marking them seen or rejected changes nothing in the work order.
  - a section move added for a section out of place (only when the AI made none, with the suggested page and its preview; a second move refused), the captions decision in group 5, and the Figures Moved card from a trial run's result
  - the move preview leaves out what the text rules remove: a move onto or of a removed block is refused and names the rule, and the preview on Save follows the reviewed rules, so rejecting the rule brings the block back. The move card carries the trial run's outcome.
  - several moves: one card each (`move_section`, `move_section:1`), each previewed on the order the earlier ones leave. Changing or rejecting one touches only it; an added move goes after the AI's, up to 3.
  - the Figures Moved card is the `fix_figure_order` decision: Reject turns it off, or on when the AI turned it off
- `test_support.py`: the files the pipeline must refuse (#69), on one-page PDFs the test makes:
  - The support rule on its own: a PDF 2.0 file is refused, including a 1.7 header whose catalog says 2.0. So is a 1.7 file whose tag tree declares namespaces. A plain 1.7 file is accepted, and `ALLOW_PDF20=1` lets both refused files through.
  - The real scripts: `intake.py` stops a PDF locked with a password (exit 3, `stopped`), a damaged one (exit 1, `failed`) and a PDF 2.0 one (exit 3, with its flag). `audit.py` and `apply.py`, run with no intake before them, stop the same files with the same words and write nothing.
  - `run_api.sh` stops a locked PDF before the cost estimate, with and without intake.
  - The damaged file is the first 20 bytes of a PDF. A file cut in half is not enough, because qpdf rebuilds it and it opens.
- `test_sections.py`: `review.md` turned into sections and back gives the same lines, and the WCAG-only view leaves out the PDF/UA-only parts.
- `test_tablegrid.py`: where cells sit with spans counted, who heads what (plain grids, title, note, group and repeated rows, two-level headers, row headers spanning rows, empty cells, false header cells), and each reading that is refused.
- `test_pagereads.py`: whole-page readings of Hawaiian pages (#49):
  - which pages are read (the share of longer words with Hawaiian shape)
  - which readings replace an OCR word at its place (marks, a misreading; not a garbled or split word), and each place getting its own reading (na and nā)
  - the work-order check's refusals
  - `apply.py` on a tiny tagged page, with its words on the page or in a form XObject drawn once (OCRmyPDF 17's layer), never in a shared one
- `test_page_costs.py`: what page readings cost: paid money counted at every stage and once, the per-PDF limit on a later attempt, a page reused at no cost, the "page" history and "Not Available Yet" until it exists (against a fake OpenRouter).
- `test_synthetic.py`: small PDFs built by the test, for rules no tagged sample reaches. These run the real scripts with `VERAPDF=off`.
  - **Word breaks:** one page sets its words with no space characters, as TeX does (moves between words, or kerning inside one `TJ`). Read through pdfplumber, the words must come out with spaces between them.
  - **The list rule:** one page has a tagged one-item list made from a paragraph's first word ("as …") next to a real list ("1.", "2."). `audit.py` must mark only the first for the rule, and `apply.py` with an empty work order must turn it into a paragraph, or keep it when `keep_lists` names it.
  - **One section move:** a four-page PDF with one section read out of printed order goes through `audit.py`, the review page's preview, `apply.py` with a `move_section`, and `verify.py`. The preview must show the order `apply.py` makes, and verify's section check must mark the original's flag as "already in the original" and a bad move's flag as new.
  - **A reviewer's move and the trial run:** the same move added by a reviewer (no AI move) is made the same way. The review stop's trial run of `apply.py` returns the executor's figure moves and what it did with the section move (made, or refused and why), and says why when it cannot run.
  - **Two moves and figure order:** a six-page PDF with two sections out of place gets a list of two moves, made in turn as the chained previews show. A figure read after the last page is moved back unless `fix_figure_order` is false, and the trial run lists it even then.
  - **A table:** a small table goes through the work order with a title, a group row, a source note and a false header cell. It must come out with a Caption, a paragraph after it, data cells tied to headers the IDTree can find, tags the ParentTree still owns, and the same page text.

The expected values come from the module docstrings and from [Work order](work-order.md) and [OCR words](ocr-words.md), not from what the code happens to return. A failing unit test means a rule changed. If the change was intended, update the test's expected value in the same PR.

### apply.py's kept tag-tree index and its check mode

For whoever changes `apply.py` (#93 Part 3, C2). `reindex()` (page, parent and owner of every tag) and `all_elems()` (every tag in order) keep their result and walk the tag tree again only after `TREE_V` has gone up, which `tree_set()` does before every write. So:

- **Write `/K`, `/P`, `/Pg`, `/Type`, `/MCID` and `/Stm` only through `tree_set(n, key, value)`** (or `set_kids()`, which uses it), and read `/K` only through `kids()`. `test_apply_tree_writes.py` fails on any other write of those keys it can read in the code of `apply.py` and every `lib/*.py`. It can't read a write with a computed key (`n[key] = …`) or an `.update(` on an object built elsewhere: those are the check mode's job.
- **The check mode, `APPLY_TREE_CHECK=1`:** wherever a kept result is about to be used, `apply.py` walks the tree again anyway and compares (by object number). On any difference, or a tag stored as a direct object, it prints one line starting with **`TREE INDEX STALE:`** (what differed, and which step used it), and stops with `TreeIndexStale` (a `BaseException`, so no `except Exception` in `apply.py` can swallow it). It returns the kept result, so what runs is the production path.
- **Where it is on:** always in pytest (`tests/conftest.py` sets it for every test and its child processes, with `APPLY_TREE_STALE_LOG`: any stop fails the test that ran it, and a stop still in the log at the end of the session fails the session) and in `tools/regression.py`'s runs (a stop in a run's log fails the PDF). `review/core.py`'s `run_apply()` raises `TreeIndexStale` when it sees the marker, so a stop inside a trial run is never turned into "the trial run stopped". The review page's draft build reports one as a failed draft; the log is the backstop there. Production runs never set it: there, a kept index is used as it is.
- If you see the marker: a write reached one of the keys above without `tree_set()`. Route it through `tree_set()`.

## Regression test

`tools/regression.py` runs the books in `pipeline/tests/baseline/` (hawaii3, globalasias, northkorea, fishers, moralfoods, teika, migrant, ilokano and romanization-ocr; sources and licenses in `samples/README.md` in the repository) through the whole pipeline with `run_api.sh` and `REPLY=`, so the saved AI reply is used instead of an AI request. Each book's folder holds:

| File | What it is |
|---|---|
| `reply.txt`, `reply.txt.meta.json` | The saved AI reply, with the model and temperature that produced it, and for a scanned book the OCR-word list the reply was written for (`ocr_words_fingerprint`, `ocr_words_sent`, `ocr_words_list`). This is the run's fixed input (see [Saved replies and OCR words](#saved-replies-and-ocr-words)) |
| `review.md` | The report the last accepted run wrote |
| `_intake/` | Untagged books only (ilokano): `intake.json` and `intake.pdf`, the intake result the reply was written for. It is reused (`INTAKE_REUSE=1`, as `FROM=` batches do) instead of rerunning OCR and auto-tagging, whose output varies with the Tesseract and OpenDataLoader versions. A note is printed when `requirements.txt` pins another OpenDataLoader than the one that made it; re-seed then |
| `expect.json` | A fingerprint of that run's `record.json`: veraPDF rules before and after, what `apply.py` did, what the work-order checks dropped, the tag counts, headings and figures `verify.py` found |

Every run's `apply.py` runs in its check mode (`APPLY_TREE_CHECK=1`, [above](#applypys-kept-tag-tree-index-and-its-check-mode)): a `TREE INDEX STALE:` line in a run's log fails the PDF.

### Saved replies and OCR words

A reply whose OCR-word list does not match today's audit, or has no fingerprint, has its OCR-word readings dropped on replay ([OCR words](ocr-words.md)). Re-seed such a book with a new reply.

### How it compares

Each run is compared with the baseline in three ways:

1. **`expect.json`**, field by field.
2. **`review.md`**, line by line. Three lines are left out: `Time:` and the run-start line, which change on every run, and `Libraries:`, which changes with the Python version. In the veraPDF line, only the version number is left out: it is whatever veraPDF is installed (Homebrew's 1.30.3 calls itself 1.30.0), while the profile hash on the same line is still compared.
3. **Checks that must always hold, whatever the baseline says:**
   - veraPDF ran
   - no more WCAG rules fail after the run than before it
   - nothing failed in `apply.py`
   - no page looks different
   - no page's text changed
   - the original PDF is unchanged

The test prints one line per book (identical, or the fields and lines that differ) and exits with 1 when any book differs. It needs veraPDF (see [Verification with veraPDF](verapdf.md)). Run folders go to a temporary folder, which is kept when something differs; `--out DIR` puts them in `DIR` instead.

### Running books in parallel

`--jobs N` runs N books at once (default: the `JOBS` environment variable, as for `batch_api.sh`, else 1). The biggest books start first, and the report still lists the books in their usual order. A book whose run fails is reported with the end of its log while the others carry on.

Each book needs about 0.5–1.5 GB of memory: with 8 GB, `--jobs 3` peaked at about 5 GB used and took about 10 minutes for all nine books, against 21 one at a time. No run can be shorter than the slowest book (migrant, about 4 minutes).

On WSL, check `free -h`; if memory is short, raise `memory=` in `C:\Users\<you>\.wslconfig` and run `wsl --shutdown`. CI does not use `--jobs`: each book is its own job there.

### Python versions

`meta.json` records the books, the prompt and the Python version the baseline was made with (Python 3.14). Another Python version prints a note, because a difference may come from the version and not from the code.

CI runs the regression test on 3.14 only, and the unit tests on both versions [Setup](setup.md) allows (3.13 and 3.14). If a local run on 3.13 shows a difference, run it again on 3.14 before updating the baseline. Run one book with `--books teika`; `--update --books X` adds X to the baseline and keeps the others.

### What it covers, and what it does not

| Book | Adds |
|---|---|
| hawaii3 | alt text, retyped headings (H1–H5), the role map, sections; ʻokina and kahakō; language tags that are not BCP 47 ("Hawaii"), deferred to a reviewer, so veraPDF 7.2-29 still fails |
| globalasias | `language` (Chinese, Japanese and Korean words in an English book), merged headings, ActualText the executor refuses, a cover move refused (no host) |
| northkorea | `tables`, flattened tables, `move_to_document_start`, captions retyped; a file not made by Adobe (Aspose) |
| fishers | `adopt_orphans`, notes, the role map, a wrong document language (fr-FR on an English book), Vietnamese diacritics |
| moralfoods | `language` (CJK runs), `artifacts`, `toc`, `captions`, `links`, `notes`, `fix_figure_order`, page figures, tab order; MarkInfo false |
| teika | `tables` with no header cells, artifacts the executor refuses, `toc`, notes, three section moves the check drops (the audit flags nothing there); no document language |
| migrant | `lists`, a table running over two pages (one Table tag), notes, a cover move refused (no host) |
| romanization-ocr | a scanned book whose OCR layer drops every tone mark (made from an open-access book for this test): the OCR-layer check (doubtful, diacritics missing), `ocr_words` (10 misread forms in 15 places), OCR fonts, OCR text approval |
| ilokano | an untagged book: an OpenDataLoader tag tree, so the one-item list rule (15 lists) and word breaks that rely on gaps |

**Covered only in part:** `move_section`. teika's moves are dropped by the work-order check, and the cover moves of globalasias and migrant are refused by the executor, so none is made. The synthetic test above and `tools/reorder_case.py` cover moves that are made.

**Not covered by the regression test:**
- intake itself: frozen here; `tools/intake_cases.py` tests it on synthetic PDFs
- OCR made by intake on a real book: romanization-ocr's layer comes with the file
- a book written mainly in Chinese, Japanese or Korean
- vertical text, math, forms and PDF 2.0

To check all the tagged samples, rerun them from saved replies before and after your change, then compare the two batches with [compare_runs.py](batch-runs.md):

```bash
FROM=v10-open AUTO=1 bash batch_api.sh before ../samples/tagged   # on main
FROM=v10-open AUTO=1 bash batch_api.sh after ../samples/tagged    # on your branch
python3 tools/compare_runs.py before after
```

### When to update the baseline

The baseline is never updated automatically. A person updates it on purpose:

```bash
python3 tools/regression.py --update --reason "why the output changed"
```

This reruns the books, writes their `review.md` and `expect.json` as the new baseline, and adds the reason to `tests/baseline/UPDATES.md`. Commit the baseline changes together with the code change, so the reviewer sees both diffs side by side.

**Update** when the regression test fails, every difference is one the PR meant to make, and the always-true checks still pass. For example, a fix in `apply.py` removes a book's last PDF/UA failure. The diff then shows that veraPDF rule gone, one new entry in `apply.applied`, and the matching `review.md` lines, and nothing else.

**Do not update:**
- to make CI pass when you don't understand a difference
- in a PR that was not meant to change any output, such as a refactor
- when an always-true check fails; `--update` refuses then

In the example above, if the diff also showed two headings gone (`verify.tree_types.H2: 7 → 5`), that would be a bug, not a new baseline.

Make one update per PR, with its own reason. Don't fold several unrelated changes into one update.

**After a failed CI run:** each failed regression job uploads its run folder as the `regression-runs-<book>-py<version>` artifact. To adopt it without rerunning, download the artifact and run `python3 tools/regression.py --update --books <book> --from-dir <downloaded folder> --reason "…"` (CI runs it on Python 3.14, the baseline's version).

**After a prompt change:** the saved replies were written for one prompt version (`meta.json` → `prompt`). When `decide.py` uses a new prompt, the test stops and asks for a re-seed instead of showing a diff. To re-seed:

1. Run the baseline books with the new prompt. This is a paid request, about $1.90 for the nine (v10, 2026-11-03: $1.49 for the seven tagged books, $0.30 for romanization-ocr; ilokano about $0.10); ask first. ilokano and romanization-ocr are single runs (`bash run_api.sh ../samples/untagged/ilokano.pdf ilokano <label>`), the others a batch.
2. Run `python3 tools/regression.py --update --seed ../runs/batches/<label> --reason "prompt vN"` for the tagged books, and `--update --books ilokano --seed ../runs/ilokano/<label>` for ilokano (a single run folder; its `_intake/` is copied too), and the same for romanization-ocr.

`--seed` copies each book's `raw_reply` from its `record.json`.

## Reorder case

`tools/reorder_case.py` covers `move_section` on a real tag tree without an AI reply. It swaps one section with the next under a section host, in a copy of a tagged sample (hawaii3 by default: a chapter on PDF 236–239 among its sibling sections). Then it runs the pipeline with a reply that holds only the `move_section` putting it back.

It checks that:
- the audit flags the pair
- the review page's preview finds one section and its host
- `apply.py` makes the move, and logs the same section and host
- the host's sections read in the book's order again
- the preview's order is the one `apply.py` made
- verify's section check no longer flags the swapped pair, and finds nothing new

The swap is in the file the run starts from. So if the move were not made, verify would count the pair's flag as already in the original, not as new: the first check is what catches that.

`--moves 2` swaps two separate pairs (on hawaii3, PDF 236–239 and PDF 250–253), and puts both back with a reply holding a list of two moves. `apply.py` makes them in turn, and each is checked the same way against the review page's preview, chained as the page works it out.

CI runs it (one move and `--moves 2`) whenever `pipeline/` changes. Run it yourself after a change to `lib/readorder.py`, `op_move_section` or the review page's preview, for a quicker answer.

## Hand-edit case

`tools/handedit_case.py` covers a PDF edited by hand and brought back (`handedit.py`, see [Editing the PDF by hand](hand-edits.md)) on a real book. It runs the book from its saved baseline reply, exports the result, replaces one figure's image in the copy (a solid image of the same size), and brings it back for review with no AI call. Then it writes that figure's alt text by hand (`review_workorder.py --reviewer`) and applies it.

It checks that:
- the import lists only that figure, and removes its alt
- the review's gap names it
- the parent's result and the edited file are unchanged, and `hand_edit` records both sha256s
- `apply.py` fails nothing, and the safety checks pass
- the new alt is in the result, while no other figure lost its alt

It also prints what `apply.py` changed again on a file that already held the earlier fixes. Run it after a change to `handedit.py`, `lib/handedit.py`, or an automatic step in `apply.py`. The unit tests (`tests/test_handedit.py`) do the same on a one-page PDF.

## Intake cases

`tools/intake_cases.py` builds synthetic PDFs with no book content and checks what `intake.py --plan-only` decides for each:

- an empty text object over a scan, an OCR layer, a text page
- placeholder and real tag trees
- existing OCR layers scored against their scan: one that matches, one missing the breves the scan shows (ŏ, ŭ), and one too short to score
- two printed pages side by side (two-up spreads, a vertical-OCR spread, spreads with years in the running heads) and a landscape page with one wide column, which is not a spread
- Japanese, vertical Japanese and Korean scans, and 14-page scans for the sampled CJK check

It also checks that a spread's reading order is reordered and saved. It prints PASS, FAIL or SKIP per case, a summary line, and exits with 1 on any FAIL.

`--full` also runs the whole intake on the empty-text scan (the empty text object is removed and OCR text added; needs OCRmyPDF 17), on the two placeholder-tree cases (the old tree is set aside and OpenDataLoader makes a real one) and on the two-up spreads (read half by half); auto-tagging needs Java 11 or later. This is what tests intake itself, since the regression test reuses ilokano's frozen intake result.

### Fonts and skipped cases

Several scans are drawn with a font: the Japanese and Korean text, the breves, and the page the full empty-text case OCRs. On macOS that is Arial Unicode, on Linux Noto Sans CJK (`sudo apt install fonts-noto-cjk`); `INTAKE_CASES_FONT=/path/to/font` overrides both. Without such a font, PIL's default font draws no CJK and no breves, and its text is too small to OCR, so those cases are SKIPped.

The summary line counts skips separately, so a skip is never mistaken for a pass. With `--strict` (as in CI) any skip counts as a failure and the script exits with 1. The CJK cases also need Tesseract's `osd`, `jpn`, `kor`, `chi_sim` and `chi_tra` packs, each with its `_vert` pack. Two OCR-layer cases need the `script/Latin` model (`tesseract-ocr-script-latn`; see [Setup](setup.md)); without it they are SKIPped.

When an OCR-layer case fails, the script prints intake's OCR-layer test under it: the verdict, and each sample page's score or why it was not scored.

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
  - compile check, shell syntax and `pip-audit` (`pip-audit` on Python 3.14 only)
  - the unit tests, on Python 3.13 and 3.14 (one job each)
  - a second job that installs Tesseract with its CJK packs, the `script/Latin` model and `fonts-noto-cjk`, then runs the intake cases, then `--full` with Java 17 and OCRmyPDF 17 (installed with pipx). Both steps are blocking and run with `--strict`, so a missing tool fails the job instead of skipping cases
- **`pdf-validation.yml`, when `pipeline/`, `prompts/` or `samples/` change:**
  - the existing veraPDF audit of one sample
  - a `regression` job per book on Python 3.14 (9 jobs in parallel, with Java 17 and veraPDF 1.30.3) that runs `tools/regression.py --books <book>`, and uploads the run folders when it fails (`regression-runs-<book>-py<version>`)
  - a `reorder-case` job on Python 3.14 (no Java, no veraPDF) that runs `tools/reorder_case.py` on hawaii3, once with one move and once with `--moves 2` (about 3 minutes each), and uploads both folders when either fails (`reorder-case`)

## Writing the docs

A pull request that changes `pipeline/` or `prompts/` must also change `docs/`, unless it has the `no-docs-needed` label. The links in `README.md`, `docs/` and `notes/` are checked in CI. The README is a short overview; `docs/` is the full reference, so a fact the two share must say the same thing in both. When they differ, check the code.

When you write or change a page:

- Open it with one to three sentences on what the page is for and who it is for, before the first heading, table or code block.
- Keep paragraphs to about 80 words. Split a long one, or turn a run of facts into a list.
- Keep table cells to about 60 words. Put the rest in a section below the table and link to it from the cell.
- Lead with what a user sees and does. Put internals (`record.json` keys, modules, internal flags, calibration figures) in a `## For developers` section at the end of the page.
- Don't cite internal decision codes (such as R17 or D3) or name people. Link the issue (`#88`) when the history matters.
- Say "the AI" for what writes the work order. Say "model" only when choosing or naming one (`MODEL=`, [Models](models.md)), and "Claude" only for what applies to Claude alone, such as the dollar limits.
- Say "PDF" for what the pipeline works on, and "the original" only to contrast it with the result. Say "book" only in a quoted app label or for the printed publication itself. Say "reviewer" for the person who checks the AI's decisions, and "library staff" when the app's users are meant.
- Quote words the app shows exactly as it shows them (Title Case labels).
- Don't cite the sponsor checklist's step numbers: say what the step does. Record coverage in `notes/checklist-coverage.md` instead.
- Name the open-access sample books in `samples/README.md` freely. Don't name the old non-open-source samples: for a measurement made on one, say "an earlier test book". Published works used as test material may be named under "For developers" when a result needs them (as in [OCR words](ocr-words.md#results-on-test-books)).
- Add a term the pages use without explaining it to the [Glossary](glossary.md).
- Give a new page a `parent:` in its front matter: one of `Get started`, `Review and ship`, `How it works` or `For developers` (#112). Its `nav_order` is a whole number within that group. Add it to the group page's list and to "Where to go next" in [Overview](index.md#where-to-go-next) too. A page without a parent shows at the top level of the sidebar, beside Troubleshooting and Glossary.
- A page can also sit one level lower, under a page in a group, as the parts of [Reviewing the work order](review-step.md) do (#115). Its `parent:` is that page's title and its `grand_parent:` the group, and its `nav_order` is a whole number among its siblings. List it on its parent page only, not on the group page or in "Where to go next". The parent page has `has_children: true` and `has_toc: false`, and opens with its own list of its parts.
- Moving a section to another page breaks every `page.md#section` link to it, because the site cannot redirect an anchor. Update the links in the same pull request; the link check follows anchors. A link to the docs site from the code (such as the review page's "How to fix it by hand") is pinned by `test_links_to_the_docs_site_land_on_a_section`.
- The pipeline diagram is a short text diagram in a code block: each step with a few words beside it, and lines of 46 characters or less so it fits a phone screen. The full explanations belong on the docs pages, not in the diagram. It is in both `README.md` and [Overview](index.md#how-it-works): change the two together so they stay identical.
