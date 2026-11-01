---
title: Verification with veraPDF
nav_order: 10
---

# Verification with veraPDF

The goal is WCAG 2.2 AA. [veraPDF](https://github.com/veraPDF) checks the original (in `audit.py`) and the result (in `verify.py`) with its **WCAG 2.2 machine** profile, pinned in `pipeline/verapdf/WCAG-2-2-Machine.xml` (from veraPDF-validation-profiles branch `rel/1.30`). That profile holds every machine-checkable PDF/UA-1 rule and a few WCAG-only ones (contrast, small text, link descriptions, redundant tags). veraPDF's CLI has no flavour for it, so it is passed with `-p`.

Not every PDF/UA rule matters for WCAG. `pipeline/verapdf/rules.json` sorts every rule in the profile:

- **wcag**: a failure fails a success criterion (listed per rule). Counted in review.md.
- **ua_only**: a PDF/UA requirement with no success criterion behind it (XMP metadata and dc:title, Note IDs, font program embedding, widths and encodings, optional content, embedded files, XFA, print-production annotations). Listed apart and not counted.

A rule veraPDF reports that is not in `rules.json` counts as WCAG and is named as unclassified in review.md, so someone adds it. After updating the profile, re-check that every rule is listed.

`vera.py` keeps one entry per failed rule, not one per failure (a scanned book can fail 70,000 checks): the rule, what it checks, how many checks failed, its pages, five examples with their object and PDF page, and who can fix it:

| Who fixes | Rules | How it is used |
|---|---|---|
| the pipeline | flags, `DisplayDocTitle`, links tied and described, tab order, note IDs, the OCR layer's undefined glyphs, role-map loops (7.1-6), standard tags remapped (7.1-7), malformed `/Lang` spelling (7.2-29) | not sent to the model: the executor fixes these whatever the work order says, and review.md says how many it changed |
| the AI | figure alt text, heading levels, natural language, untagged content, role mapping (including styles with no mapping), document title, table headers (7.5-x), broken table, list and contents structure | sent to the model in the digest (`pdfua_check`) as rule, count, example objects, the work-order `key` that fixes it and `objs` (up to 20 tags it failed on) |
| a person | fonts, Formula alt, Figure bounding boxes, the PDF/UA claim | not sent; listed in `review.md` as known gaps |

Which rules belong to whom, and which work-order key fixes each AI rule, is set in `pipeline/vera.py` (`EXECUTOR`, `KEY`, `PERSON`). The AI must address every rule it is sent with its key, or defer it naming the rule (prompt v8, step 9).

**Targeting from the original's results.** The audit uses veraPDF's findings to make the flagged tags reachable: a Figure with no alt and no image of its own (a vector logo or drawing) gets a crop of its whole page (`image_is_whole_page`), so the model can see it; a table whose cells veraPDF flags is marked with `pdfua_rules` (and kept even past the 100-table cap).

**Executor fixes for veraPDF rules** run on every book (after the work order, before the index rebuild) and change no page's look or text. Each records what it changed under `rule_fixes` in the apply log, shown in review.md's "Who fixes" column:

| Rule | Fix |
|---|---|
| 7.1-6 | A RoleMap chain that loops is cut where it closes (that style → P) and listed for a person |
| 7.1-7 | A standard tag remapped in the RoleMap (sands: `Caption → P`): its elements are retyped to what the RoleMap made them, and the entry removed |
| 7.2-29 | `/Lang` spelling tidied (`en_US` → `en-US`, case, spaces; `lib/langtag.py`); an empty `/Lang` on a tag removed; anything else listed, never guessed |
| 7.5-1/2 | A header cell (TH) with no direction gets one where the table makes it plain: a row of only TH → Column, a row whose only TH is its first cell → Row; others are listed |

The work order's `tables` key (`op_tables`) marks the header rows and columns the AI names in a real table as TH with their Scope; spans that cross the header edge are rejected for a person. `rolemap` may add a mapping for a style the source never mapped (7.1-5).

veraPDF runs once per step, in the background while the step's own checks run. The audit's run is the "before" (`verapdf.json`, plus its `pdfua_check` view in the digest); it is printed with the audit, so a file that already passes (or fails thousands of checks) shows up before anything is spent. Verify's run is the "after". review.md gets two rows (no WCAG failures after; no rule newly failing or failing more often) and a "veraPDF" section with each failed rule's before and after counts, who fixes it, its status (newly failing, failing more often, still failing, fixed) and pages. `record.json` keeps both summaries under `verapdf`; `summary.md` shows each book's failing rules before → after.

**WCAG checks veraPDF does not make** are in `verify.py` (`wcag` in `record.json`), each a row in review.md and listed under "WCAG checks veraPDF does not make". They find things to look at, not proven failures:

| SC | Check |
|---|---|
| 1.1.1 | Alt text that looks like a file name, has no letters or digits, or is the same on 3+ figures |
| 1.3.1 | A table with content and no header cell (TH) |
| 1.3.2 | Pages where the tagged text, in tag-tree order, jumps back up the same column 2+ times (notes, figures and captions skipped) |
| 1.3.2 | Sections (and Divs) read away from their printed place among their sibling sections: those outside the longest run that reads in page order, by pages covered. A Div around a figure or note is skipped. The same check runs on the original, and each flag is marked **new** (this run caused it), **moved again** (out of place in the original too, but now read somewhere else: its section or its nearest earlier sibling that still holds content changed) or **already in the original**; the row is CHECK for new and moved-again ones. Small sections (one or two pages) read more than 5 pages after their page, after a longer sibling that covers them, are listed below it without failing it (in sands: 57 figure sections read after their part). A tag tree with no sections has nothing to compare. The rule is in `lib/readorder.py`, shared with the review page |
| 2.4.2 | A title that looks like a file name or placeholder |
| 2.4.4 | Link text like "click here" or "more" |
| 2.4.6 | Headings with no text, over 200 characters, or the same twice in a row |

The executor sets `/Tabs /S` on every page with annotations (2.4.3), so tab order follows the tag tree.

When an audit is reused and has no `verapdf.json` yet, `run_api.sh` runs veraPDF on the file the audit was made from (the intake result, if intake ran), and `decide.py` builds `pdfua_check` from it.

**PAC 2026** ([pac.pdf-accessibility.org](https://pac.pdf-accessibility.org/en), Windows, no command line) is the final manual check. review.md ends with what to run and the criteria no automated check covers (alt-text accuracy, meaningful order, colour, contrast over images, images of text, descriptive headings, language of parts). A PAC failure not listed in review.md is a gap in the automated checks: open an issue.
