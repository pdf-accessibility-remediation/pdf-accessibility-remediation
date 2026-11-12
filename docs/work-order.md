---
title: Work order
parent: How it works
nav_order: 3
---

# Work order

The work order is the JSON list of decisions the AI returns for one PDF. This page explains what the AI decides, what the executor (`apply.py`) does by itself on every PDF, how it carries out the AI's decisions, and the rules every work order follows. It is a reference for anyone who reads `review.md` closely or changes the executor.

## What the AI decides

- **Title and language.**
- **Headings:** heading levels (by style, or element by element when the tagger's headings are generic), merges, and spoken heading text.
- **Figures:** alt text, and which figures are decorative (including full-page scan images).
- **Alt text for whole pages** the executor wraps as Figures (`page_figures`), from an image of the page in the digest: for a map, its name and main regions.
- **Decoration:** running heads and page numbers to hide, including ones marked but outside the tag tree. Untagged blank-page notices, and untagged labels inside a Figure whose alt text covers them, are marked as decoration (`artifacts.untagged`, all or nothing per page).
- **Structure by style:** lists, contents, notes and captions. Contents entries by a list of styles and the contents pages. The AI decides which paragraph styles become Notes; IDs are always handled by the executor.
- **False lists and tables** to flatten into paragraphs.
- **Orphan runs** that are real content (notes, bibliography), added to the tag tree in page order (`adopt_orphans`).
- **Reading-order moves.**

Real tables, untagged real content, and OCR errors go to a reviewer.

## What the executor always does by itself

These steps are mechanical, so they never wait for the AI.

### Structure

- Makes sure there is exactly one Document root. Auto-Tag output often has none; some exports have two.
- Sets the "tagged" flag, and shows the title in the window.
- Rebuilds the tag-tree index (ParentTree) from the tree, where entries are missing or wrong.
- Gives every Note tag a unique ID, and lists it in the ID tree. A Note tag is removed only when it is proven empty: nothing under it holds content or an annotation, it carries no alt, ActualText or ID, and nothing in the file but its parent refers to it. Turning note paragraphs into Notes stays the AI's decision.
- Reports any PDF/UA claim the source already makes. It never adds one.

### Links and tab order

- Ties every link annotation to its text and gives it a description, creating Link tags where the tagger left none.
- Removes references to annotations that sit on no page.
- Defers links on text missing from the tag tree to a reviewer.
- Sets `/Tabs /S` on every page with links or other annotations, so the keyboard and a screen reader move through them in tag order (WCAG 2.4.3, PDF/UA 7.18.3). verify.py counts pages still without it.

**Links whose description is only a URL** get the PDF's own sentence around the link, with the URL (and any other URL in it) removed: no words added, and the visible URL unchanged. In a caption, the whole caption is used. When no words are left, the link is listed for a reviewer. A link address that looks broken (an unmatched closing bracket) is listed, not changed.

### Language of Chinese, Japanese and Korean runs

The executor tags CJK runs with their language where it differs from the document's (WCAG 3.1.2; `lib/scripts.py`):
- hangul runs: `ko`
- kana runs: the work order's `kana_runs` (`ja` when it gives none)

A run in the document's own language needs no tag: Chinese characters in a Chinese, Japanese or Korean document (Japanese kanji, Korean hanja), hangul in a Korean one, kana in a Japanese one.

Elsewhere, Han-only runs (Japanese or Chinese, never guessed) and runs mixing CJK with Latin letters go to a reviewer (`han_review.csv`).

### Text outside the visible page

The executor marks text lying entirely outside the visible page area (CropBox) as an artifact: a printer's slug in the margin, or the back cover and spine of a cover spread cropped to the front.

- A line counts only as a whole, so a line that starts on the page and runs past its edge is real content, and is left (and listed).
- Off-page text inside a shared form XObject is left too.
- Before a page is changed, its text operators are matched one for one with the characters the reader found. Any mismatch leaves the page as it was.

review.md lists what was marked. For a page with much hidden text (a cropped cover, even when the auto-tagger already marked it), it lists every hidden line for whoever writes that page's alt text.

### Font maps

The executor corrects font maps:
- Characters a font maps to private-use codes that are really digits become 0–9: Adobe old-style U+F730–F739, and Minion lining U+F639–F641/U+F6DC.
- A glyph named `threeemdash` with no map entry becomes three em dashes.

**Each glyph is confirmed by rendering it.** A digit must read as that digit in context ("2?2", "3?3", two exact readings), and agree with the digit its glyph name states. The dash must be one bar at least 2.5 em wide. There is one decision per font across all its copies: corrected when at least one copy confirms it, and contradictions are at most a quarter of the confirmations.

Only the font's ToUnicode map changes, so pages look the same; verify.py compares text after the same corrections. Glyphs not confirmed are listed in review.md for a reviewer. This needs Tesseract; without it, the step is skipped with a note (tagged-only users need nothing new).

### The invisible OCR layer's font

The executor gives the invisible OCR layer of scanned pages defined glyphs, when:
- its font is HiddenHorzOCR, HiddenVertOCR or GlyphLessFont
- every use of it is invisible (render mode 3)
- its embedded program holds only `.notdef`

The font program is swapped for a blank TrueType one: each character a defined, empty glyph of the same width. The character codes, ToUnicode map, widths and render mode stay the same. The swap is kept only if a replay of those pages shows none looking different and no text changed. It does not correct OCR errors, and it never touches a visible font.

### Spoken text

The executor checks every spoken text (ActualText) against the printed characters, because the AI may describe or restructure the PDF but never write its text. It may differ only in spacing, letter case and line-end hyphens (kept or dropped). Added or changed words or punctuation are rejected. review.md lists every accepted spoken text that differs from the print, and every rejected one.

### Text rules

- **Matching ignores spacing:** a pattern fits the text as stored, with spaces normalised, or with spaces from gaps (`lib/gaptext.py`). Every space in a pattern is optional, so patterns written against spaceless or spaced text both match.
- **A top- or bottom-band rule** (running heads, page numbers) hides a run only when everything else on that line is matched by a band rule too, or is already decoration. A superscript note number in the first line of body text can match a page-number pattern, but the body text beside it does not, so it stays visible. review.md lists such runs.

### Lists

A one-item list whose label is not a list marker becomes one paragraph: auto-taggers sometimes take a paragraph's first word ("as", "at", a year) for a list label. A marker is a bullet on its own, or a number, letter or roman numeral followed by "." or ")", or in parentheses (`lib/listrule.py`).

The digest marks such lists `flattened_by_rule`. The AI can keep one as a list with `keep_lists`, and a `flatten` of the same list from the AI is logged as already done. review.md lists every list changed.

### Bookmarks

When the file has headings and no bookmarks at all, the executor builds bookmarks from the heading tags: nested by level, with the title from the heading's ActualText or its text, and the heading's page as the target. An existing bookmark tree is never touched.

### Decorative paths

Untagged vector paths (rules, borders, lines) are marked as decoration when nothing ties them to content:
- the path is not inside marked content that carries properties (ActualText, optional content)
- it is not painted with a pattern
- it does not overlap a link or other annotation
- it does not touch untagged text or untagged images on its page

A path that touches them is part of an untagged drawing (a map, a chart), and is left for a reviewer to tag as a Figure. A path inside a shared form XObject is changed only if it qualifies everywhere the form is drawn, and the form is edited once. Strokes sitting directly under text are listed in the review, because an underline can carry meaning.

### Whole-page figures

A page is wrapped whole in one Figure when:
- nothing on it is tagged or marked as decoration
- it has no links or other annotations
- it has no hidden text layer (text in render mode 3, such as OCR)
- it draws at least one image or path: a full-page map, plate or cover

Text in render mode 7 (a clipping shape, such as textured map labels) counts as drawn. Nothing on the page is changed or removed.

The Figure gets a bounding box, and goes in reading order after the block holding the last tagged content before the page (a paragraph that runs across the page comes first), or first in the Document when nothing comes before it (a cover).

Its alt text comes only from the work order (`page_figures`). Without one, the Figure has none, and `review.md` says "Page N is a figure wrap. Write the alt text." A page that fails the guard is left as it is, and listed with the reason.

### Captions and figure order

- **A caption is grouped with the element just before it** when that element holds nothing but figures, on the caption's page and above it. The element becomes a Div, whether or not the work order names a wrapper style. A paragraph left behind when a figure moves out to join its caption is removed only when proven empty (the same proof as Note shells).
- **Every figure group goes back on its own page in reading order** (`fix_figure_order`), unless the work order turns it off for the PDF with `"fix_figure_order": false` (for a plates section the text refers to by number, say). Each move is listed in `review.md`, and so is a PDF where the step was turned off, by the AI or by the reviewer rejecting the Figures Moved card.

## How it carries out the AI's decisions

- **A RoleMap entry for a standard tag** (for example the publisher style literally named `H1` → `H3`) cannot be written into the RoleMap, so it is carried out as a retype of every element with that tag. The review lists it as "retype (standard tag)" with the element count.
- **Text rules** (running heads, page numbers) match the run's text with spacing normalized (double spaces, leading and trailing spaces). A running head split into several runs is hidden as a whole when all its runs sit in the rule's band. A rule that matches nothing is reported, not silently dropped.
- **Decoration drawn by a shared Form XObject** (for example a junk text grid repeated on many pages) is hidden inside the form when a text rule matches every run in it, and its tags leave the tree.
- **Captions** on a page with several figures are tied to the figure right next to them: above or below, at most 40 pt, overlapping horizontally. Two equally close figures, or a caption inside a figure's area (a panel letter such as "a"), stay with a person. Position-paired captions are listed in the review.
- **Tables** (below).

### Tables

The work order (`tables`, worked out in `lib/tablegrid.py`) reads a table's rows as title, header, group, repeated header or note rows, and its left columns as headers.

**Title and note rows:**
- Title rows become the table's one Caption: two title lines, such as "Table 3" and a subtitle, make one Caption, not two. A table that already has a Caption keeps it, and its title rows are not taken out (the reading is rejected for a reviewer).
- Note rows become a paragraph right after the table. A note cell's paragraphs move out as they are, and any loose text beside them becomes a paragraph of its own, so no paragraph ends up inside another.
- A title or note cell's spoken text (ActualText), alt text or language stays with its own text, on a Span; on a Div when the cell holds paragraphs, since a Span can't.

**Header cells:**
- Header cells become TH with a Scope. A TH the reading doesn't name goes back to TD, and an empty cell never heads anything.
- A cell that names a header which leaves the table, or which the reading turns into a data cell, stops naming it.
- Where a Scope can't say it (section rows, two levels of column header, a row header spanning rows), each data cell lists its headers by ID.

**A reading that doesn't fit the table** is rejected for a reviewer, and the table stays as it was. That includes:
- a cell that spans down into a title or note row ("a cell in row 12 spans into the note row")
- a group or repeated row number that is not in the table
- a title or note row whose text has no page in the tag tree

One rejected table never stops the others. Spans are counted when placing cells.

The digest shows the AI up to 14 rows of each table: always the top 4 and the bottom 2 (where a source note sits), then the rows holding one thing (a title, a group label) in order. Tables split across pages into separate Table tags are not joined: no sample has one, so it could not be tested.

## Checks and cleanup

### Fonts

Fonts are checked; the only font change is the invisible OCR layer's (above). `verify.py` lists:
- fonts that are not embedded
- fonts with no ToUnicode map
- fonts whose embedded program holds only the `.notdef` glyph: every character drawn with them is undefined (PDF/UA 7.21.8)

`review.md` explains each one and what a person must do, and has a row for undefined glyphs in invisible OCR text. A font program that cannot be read is a CHECK ("every embedded font program could be read"), never a pass: unread means unchecked.

A missing ToUnicode map is not flagged for a simple, non-symbolic font whose encoding is WinAnsi, MacRoman or MacExpert with no `/Differences`, because its characters are fixed by that encoding. It is flagged when the encoding is missing, custom, or has `/Differences`. This needs `fonttools` (in `requirements.txt`).

### Untagged content

`verify.py` counts every text, path and image that is neither tagged nor an artifact (a form XObject once, as checkers do; an image drawn inline in the content stream counts as an image, as an image XObject does: before #93 Part 3, inline images were never counted). `review.md` lists the pages with the most, with a separate row for untagged paths.

- Untagged text is marked as decoration only in the two `artifacts.untagged` cases.
- Untagged paths only by the path rule above.
- Untagged images never.

A page with no tags at all that holds a drawing is wrapped as a Figure (above), never hidden.

### Empty tags

Empty tags are removed when proven empty, whether the source or the run emptied them: nothing under the tag holds content, it carries no Alt, ActualText, E or ID, and nothing in the file refers to it except its parent.

- The pass repeats until nothing changes: removing a child can empty its parent (a flattened grid unwinds paragraph → row → table).
- Table cells and rows are never removed one by one; a table goes only when every part of it is empty.
- A tag kept only because something refers to it (a ParentTree entry, stale or not; an IDTree entry; a /Ref; a bookmark), or because it carries an attribute, is a CHECK naming the reference.
- Each removed empty heading is tested: if no other heading on its page has text, `review.md` says the title may be lost.
- Empty captions, figures, links and list items are listed.

The pass runs before bookmarks are built.

### Tag-tree index cleanup

This runs last. A ParentTree entry that points at a tag no longer in the tree is cleared: the entry becomes null, and its key stays. An IDTree entry that points at such a tag, or at nothing, is removed.

These come from the source file, or from tags the run removed (for example running heads that carried IDs). Nothing on a page, no text and no reachable tag changes. `review.md` lists every entry cleared.

### Structure checks

`verify.py` and `review.md` check for:
- empty tags (an empty table cell is not counted)
- a paragraph holding nothing but figures
- a caption not grouped with a figure
- a link whose description is only a URL
- a table whose every cell is empty
- a tag-tree index entry (ParentTree or IDTree) that points at a tag no longer in the tree (dangling). Stale entries (marked content no longer drawn) are counted beside it.

### What the executor never does

The executor never recolors text, rewrites words (apart from the OCR-word readings, see [OCR words](ocr-words.md)), invents MathML, creates form fields, replaces figures, or rewrites the alt text the work order supplies. Contrast, OCR quality, forms, math, reflow and color-only meaning stay with a person.

## How the report writes pages and missing values

### Page references

Page references in `review.md` use the PDF page as the key, because the checker, Acrobat and the executor all count the file: `PDF 16 (printed 3)`.

- The printed label comes from the remediated PDF's own page-label table, and appears only when there is one and it differs. A non-numeric label counts too: `PDF 1 (printed Cover)`. A PDF with no labels shows the PDF page alone.
- Ranges: `PDF 7–234 (printed 1–221)`.
- **A tag with no page of its own:** if it holds a figure or other content, it takes the page of the figure inside it, else of the first content inside it. If it is empty (a kept empty tag, for example), it takes its parent tag's page: one step up, never a Sect that only stores the page it starts on. If that is missing too, the review says `page: not on this tag`.

The executor's own sentences, rejections and deferral reasons use the same form; `record.json` and the logs keep plain PDF page integers. The AI's sentences are quoted as written, never rewritten. The prompt asks it to cite pages the same way, and a deferral's optional `pages` field is shown in the standard form beside its sentence.

### No bare "unknown"

`review.md` and `summary.md` never print "unknown", "?" or "None"; a missing value says why:

| Missing | Shown as |
|---|---|
| a header cost or token count | "AI request did not finish" |
| the cost, for a reused saved reply (`REPLY=`, `FROM=`, a review's re-apply) | the original AI request's cost: "AI cost $0.256 ($0.0006 per page), from the original AI request on October 26, 2026 · this run: no new AI request", or "AI cost not recorded" when no original cost is kept anywhere; tokens: "saved reply reused, not counted" |
| a run start time, model or prompt | "not recorded" |
| a count the verify file or the log left empty | "not counted" |
| heading text or style | "(no text)" / "(no style)" |
| an artifact label the AI did not give | "(no label given)" |
| a rejection's reason | "(no reason recorded)" |
| title or language | "not set" |

`record.json` and the logs keep a missing value as `null`. Quoted text (the PDF's own words, the AI's sentences) is printed as written, question marks included.

## Work order rules

- **Elements are referenced by object number in the original file** (`"18592 0"`). That works because `apply.py` changes everything in memory and saves once.
- **`source.sha256` must match the input file,** or `apply.py` refuses to run.
- **Each operation checks its target first.** One that doesn't fit is **rejected and logged**, never half-applied.
- **Targets are whitelisted.** Work-order text is only ever data: never executed, never written into page content.

### Figure requests

A figure request's answer (a PDF with more than 100 images, see [Files](files.md)) may hold only `alt`, `page_figures`, `artifacts.elements` and `deferrals`, each for the figures that request was sent. Anything else is dropped: "a figure request may only decide alt text, decoration and deferrals for its figures", or "not one of the figures sent in figure request K".

The first request's `alt`, `artifacts.elements`, `retype` and `actual_text` for a figure a figure request was sent are dropped ("decided in figure request K, which saw the image"). Its structural decisions (`captions`, `move_to_document_start`, `fix_figure_order`, `artifacts.untagged`) stay. The answers are merged into one work order before the other checks.

### A work order a reviewer changed

A work order a person reviewed (`REVIEW=1`) goes through the same checks as the AI's (`lib/workorder_check.py`) before it is applied, and carries `reviewed_by` ("Name on YYYY-MM-DD"). The AI's version is kept in `record.json` as `workorder_ai`.

The reviewer can also add entries the AI left out: a retype, alt text, table headers, a style mapping, the title or language, an OCR reading. They are written in the AI's shape, with `why` "added by <name> in review". The two rules about images the AI never saw (alt text past `--max-images`, readings of OCR words whose sheet was not sent) do not apply to a reviewer's entries. See [Reviewing the work order](review-step.md), which also describes the review's item and decision formats for a later front end.

### Section moves

`move_section` is one move `{"pages": [a, b], "before_page": c}` (prompt v8), or a list of up to 3 (v9). They are made in the order listed, each matched on the tag tree the earlier ones left, so a later move sees an earlier one's result. Each one the executor refuses is logged on its own (`move 2 (PDF a–b): …`). `review.md` gives one line per move made (`Move 1: Section on …`).

The check drops, each with its reason:
- **a move where the audit finds no section read out of place** inside its pages or at the page it lands before. Of two swapped sections, either may be the one flagged. The reason reads "the audit finds no section read out of place in these pages or where it lands". Under v9 the AI asked for such moves in two earlier samples, and they only re-nested a section or left it where it was.
- a move past the third
- a move whose pages overlap another's
- a move that lands inside another's pages

It judges by the audit's full reading order (`fulltext.json`), or by the digest's lines for an audit made before that was kept. With neither, moves are not judged this way.

### One work order per reply

An AI model sometimes writes a work order, then a correction ("This is the intended entry set:") and a second, complete one. Then the **last** block is used, exactly as written: it is the AI's final answer, nothing is merged, and an earlier block is never used in its place. If the last block can't be read, the run stops, even when an earlier one could be.

`review.md` marks it as a CHECK ("Model reply held one work order"), and quotes what the AI wrote before the last block. `record.json` keeps the full reply (`raw_reply`) and `run.reply_blocks`.

## Background

Before any API spending, a replay test confirmed that `apply.py` reproduces, exactly, a result made earlier by hand in a Claude Cowork session, from a written-down version of that session's decisions.
