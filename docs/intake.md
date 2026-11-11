---
title: Intake
nav_order: 8
---

# Intake: untagged PDFs

This page explains how the pipeline prepares a PDF that has no tags, before the audit: OCR for pages without text, then automatic tagging, with a check after each step. It is for anyone who runs untagged PDFs or changes intake. Calibration figures, thresholds and record fields are at the end, under [For developers](#for-developers).

`intake.py` runs first in every run (`INTAKE=off` turns it off). A tagged PDF is left alone ("none (already tagged)"). For an untagged one, everything is local: no AI writes or changes any text, and the original is never written to.

## What intake does

1. **Triage:** each page is classed as text, image only, an existing OCR layer, or blank, and checked for problems a screen reader would meet.
2. **Text-layer test:** sample pages are read by OCR and compared with the PDF's own text, to see whether that text can be trusted.
3. **Language:** pages to be OCR'd are checked for Chinese, Japanese or Korean text, which needs its own OCR language.
4. **OCR:** pages with no text get invisible OCR text. Pages with text are left as they are.
5. **Auto-tag:** OpenDataLoader adds a tag tree.
6. **Checks:** after each step, intake confirms the pages look the same and the text is unchanged. A failed check stops the PDF.

The result, `_intake/intake.pdf`, is what the rest of the run works on. Intake's own checks compare it with the original, and `verify.py` compares the remediated PDF with it.

**When intake stops a PDF,** it goes to a reviewer, with the reason in intake's record. That happens when:
- the text layer is unusable (unless `FORCE_OCR=1`; see [Step 4](#4-ocr))
- pages to be OCR'd hold Chinese, Japanese or Korean text, and `OCR_LANG` names no CJK language
- a safety check fails
- the PDF is locked with a password, or is PDF 2.0

A rerun with the same settings reuses an earlier intake. `FROM=` reruns copy the earlier PDF's intake, so a saved reply still fits the same file.

## Which PDFs count as tagged

A tag tree counts only when it has at least one element that carries text structure: P, H1–H6, lists, tables, Span, Note, Link, Caption and the like, after the RoleMap. A tree with only grouping elements (Document, Part, Sect, Div, Art), or only Figure tags, is a **placeholder**. In the sponsors' 148 books, 25 of the 59 "tagged" ones had one: Acrobat Distiller/APL 8.0 books with one Part per page, and Prince books with Figure tags only.

Intake removes a placeholder tree from its working copy only, and handles the PDF as untagged. The original is unchanged, and a check confirms pages and text did not change.

Publisher alt text found in a placeholder tree is recorded, but not yet carried into `intake.pdf` or passed to the AI; a CHECK says so.

MarkInfo does not decide it: 12 of the 148 have full trees with MarkInfo missing or Marked false, as do some regression books (moralfoods, teika), and they stay "already tagged". An earlier "skipped" intake is reused only if the tree still counts as real (`FROM=` reruns always reuse).

## 1. Triage

Every page is classed:
- **visible text**
- **image only:** no text, and images covering at least 25% of the visible page area together. That is a scan, or a picture page such as a Part opener.
- **an existing invisible OCR layer**
- **blank**

**Empty text objects.** A page whose text operators draw no character (an empty text object over a scan, as in two ScholarSpace downloads) is classed by its images alone, so a scan is OCR'd. Before OCR, intake removes those empty text objects from its working copy, because OCRmyPDF passes over any page with a text object, even an empty one. A check confirms nothing visible or in the text changed. The pages are listed as a note.

During triage, every text page is also checked for:
- **Private-use characters:** legacy fonts use private-use codes for, for example, U+F730–F739 old-style digits and U+F761–F77A small capitals. A screen reader may read them as nothing or nonsense. Their count, pages and code ranges are recorded; more than 100 is a CHECK.
- **Text outside the visible page area:** characters that lie outside the CropBox (a printer's slug in the margin, for example) are invisible on screen and in print, but read by a screen reader unless marked as artifacts. Their count and pages are recorded and flagged.
- **Word breaks** (below)
- **Two printed pages on one PDF page** (below)

### Word breaks

For every text page, PDFium tells real space characters from spaces it makes up from gaps between letters. A PDF where most word breaks are gaps only gets a note with the share of pages. Prince and TeX books are typically over 90%, Distiller books near 0%.

A gap is **narrow** when it is under 19% of the type size: a text extractor may then run the words together. The PDF is judged as a whole. When narrow breaks average **10 or more per text page**, it is a **CHECK** listing the 20 worst pages; below that, a note with the rate. Detection only: nothing is changed.

### Two printed pages on one PDF page

A page that, as displayed, is landscape, with a gutter in the middle and ink on both sides, is a **spread**. A landscape page of the same size next to one counts too, because a chapter end leaves a half blank. Pages are never split. A CHECK lists them.

When the top or bottom band of each half shows a pair of page numbers that differ by one, and a neighbouring spread's pair is 2 higher or lower, both are kept. The page is then cited as "PDF 3 (printed 210–211)" in intake.md and review.md, and a range reads "printed 208–209 to 218–219". Years in the running heads, which do not rise, are not taken this way, and numbers are never guessed.

## 2. Is the text layer usable?

Up to 20 pages with text, spread through the PDF, plus up to 4 that look suspicious (private-use characters, very long run-together words), are drawn at 300 dpi and read by Tesseract. The OCR text is compared with the page's own text layer.

- **Page score:** how much of the text differs, as a character error rate. A page whose text is right but read in a different order is not counted as wrong; it shows as "usable (reading order differs)".
- **PDF score:** the median of the page scores. 5% or less: **usable**. Over 15%: **unusable**. In between: **doubtful**: the PDF goes on, with a CHECK. Fewer than 5 pages scored: "not enough pages scored", a CHECK.

**Pages that are not scored** are listed as "not scored" with the reason, and left out of the median. Each is replaced by the nearest scorable page, so up to 20 pages are scored. A page is not scored when:
- images cover 25% or more of it together
- it has fewer than 300 characters in the text layer
- it has 20+ CJK characters (or 10%+ of its letters) when the OCR language has no CJK pack
- **math:** OCR reads ∨ ∧ ≥ ∈ as v a > e
- **diacritics OCR did not read:** the text layer has many more marked letters than OCR read, and without the marks the page scores usable (pinyin tone marks with `eng`, for example)

The last two are listed, never passed: as a note on born-digital text (the OCR missed the marks), and as a CHECK on an existing OCR layer (the layer itself may lack them). A text layer that lacks marks the print has still scores badly.

**Unusable, but born-digital or math.** When the producer writes text (pdfTeX, XeTeX, LuaTeX, Prince, Microsoft Word, Adobe PDF Library, InDesign), or the PDF has math, an unusable verdict stops the PDF for a reviewer without suggesting `FORCE_OCR=1`: OCR may simply not read the text. The doubtful message says the same.

**Flags:**
- sample pages that are unusable although the PDF is not
- doubtful sample pages, as one CHECK listing them
- pages with clearly fewer word breaks than the printed page ("words run together")

### An existing OCR layer on scanned pages

The test above can't score an existing OCR layer, because its pages are images. Instead, up to 10 such pages (spread through the PDF, past the front matter) are read again by a *different* Tesseract model for the layer's script: a script model, since the PDF's own language pack tends to share the layer's errors (see [Script models](setup.md#script-models)).

- **Median error over 15%:** a CHECK "OCR layer". 5–15%: the worse pages are listed.
- **No page scored at all** (for example, no script model installed): a CHECK "OCR layer not checked".
- **Diacritics:** on pages whose letters agree, when the script model reads many marked vowels and the layer has almost none, it is a CHECK "OCR layer: diacritics". Such a page is judged on its letters.
- Latin pages with 10 or more math symbols are not scored.

This is never a stop, and the layer is never replaced: it may be the library's record.

A flagged layer (doubtful, unusable or missing diacritics), or one the test could not check ("OCR layer not checked"), makes OCR text approval part of "Ready to ship". An unknown layer is not "not needed". The same goes for OCR text intake added. The row "OCR text reviewed by a person" stays CHECK until the review page's OCR Text section (or `review_ocr.py`) records "approved".

## 3. Language

OCR uses `eng` unless `OCR_LANG` says otherwise. The scripts found in the text layer, and by Tesseract on image-only pages, are recorded. They choose language packs only for the text-layer test's sample pages, never the OCR language.

### Chinese, Japanese or Korean on pages to be OCR'd

Before OCR, every planned page is read once with the Chinese, Japanese and Korean packs. When pages hold CJK text, the PDF **stops** unless `OCR_LANG` names a CJK language, for Chinese, Japanese and Korean alike. The language is never guessed: Chinese characters with no kana are never guessed as Chinese or Japanese.

With a CJK language set, the pages carry a CHECK "CJK OCR: needs a person", because CJK OCR is often wrong, and multi-column CJK lists may be read across the columns.

When no CJK is found, every page is still read, so a CJK glossary in an English scan is not missed. With more than 12 pages to OCR, the check is shortened:
- **without a CJK pack in `OCR_LANG`,** it stops at the first CJK page, since the PDF stops either way. The message says how many pages were checked.
- **with one,** 8 pages spread through the PDF are read, and a full run lists the CJK pages from the OCR text itself.

### Vertical text

Vertical CJK reads poorly with the horizontal packs. So on pages where they find only a few confident CJK characters, up to 3 of those pages are read again with the installed `_vert` packs. When one of them finds enough, all such pages count as CJK.

When the `_vert` packs read clearly more CJK on most trial pages, the stop message suggests adding the `_vert` pack (for example `OCR_LANG=jpn_vert+jpn+eng`). With an `OCR_LANG` that has none, a CHECK says so.

**With `FORCE_OCR=1`** there is no CJK check. CJK text found in the PDF, with no CJK pack in `OCR_LANG`, flags the pages that get OCR text: a CHECK only when OCR is planned or kept; the scripts found are always recorded. A language with no installed pack is flagged.

## 4. OCR

OCRmyPDF 17 OCRs only pages with no text. Pages with text are copied untouched; images are not recompressed, and the file is not converted to PDF/A.

- **Low-resolution scans:** scans under 300 dpi are read enlarged (the page image itself is unchanged), and flagged. In `--plan-only` this is a note, since the run itself flags only the pages that keep OCR text.
- **Pictures, not text:** an image-only page whose OCR text is not text-like gets no OCR text. It is a picture (a cover, a Part opener), and goes to the figure step for alt text.
- **Unmapped characters:** characters the OCR font could not map are counted.
- **Junk check:** on each page that keeps OCR text, tokens with symbols (# @ ® & …), capital clusters with no vowel ("MBH"), or letters mixed with digits are counted. 5% or more of 30+ tokens is a CHECK "OCR text looks like junk".

### An unusable text layer

When the text layer is unusable, the PDF **stops**, flagged, unless `FORCE_OCR=1` is set. Then every page is OCR'd anew: each page becomes an image, with new invisible OCR text, and the publisher's text layer is replaced, which review.md marks as a CHECK.

**`FORCE_OCR=1` is unverified.** In testing, the after-OCR check stopped every PDF it was tried on (see [Forced OCR in testing](#forced-ocr-in-testing)). Until this is resolved, a PDF with an unusable text layer goes to a reviewer.

## 5. Auto-tag

OpenDataLoader (local mode) adds a tag tree: headings, paragraphs, lists, tables, figures, captions and links. Running heads and page numbers become artifacts. When there is OCR text, the invisible OCR text is tagged too. On OCR'd pages, a Figure that is only the whole-page scan image is then marked as decoration: it is the page itself, not a figure.

**Spreads.** The tagger's own reading order mixes the two halves of a spread. On spread pages only, intake reorders the tagger's elements by half:
- the right half first when the text is vertical CJK, with its columns from right to left
- otherwise the left half first, keeping the tagger's order within a half

Only the tree order changes: no page's appearance or text. The CHECK says what was done, not what was planned. In vertical text the body columns run right to left by position, and running heads, page numbers, ruby and stray OCR fragments go where their position falls.

**Placeholder alt text.** OpenDataLoader writes alt text on every Figure ("image 12") and every Link ("Annotation"). A screen reader would say those words instead of describing the figure or reading the link's own text, and veraPDF's alt-text rule passes on them.

Intake removes alt text that is exactly one of those two forms; any other alt, such as a link's web address, is kept. The count is a note in `intake.md`. The figures then count as having no alt text: the AI writes it for those it is sent, and the rest are listed for a reviewer (in an earlier test book, 443 of 543). verify's "Figures: none with empty or placeholder alt" row also counts alt such as "image 12" as a placeholder.

## 6. Checks

A failed check stops the PDF, with the reason in intake's record:
- **After OCR:** every page looks exactly as before, and only the planned pages gained text. With forced OCR, pages may differ only by anti-aliasing.
- **After auto-tagging:** every page looks the same, and its text is unchanged. A page whose text holds exactly the same characters in a different order passes as "reordered": the tagger re-sequenced text runs. The moved fragments are listed, and the tag tree sets the reading order.
- A tag tree exists.
- Bookmarks, links and page labels are all still there.

How much text the tag tree reaches is recorded.

**Checks on every PDF** (verify.py, tagged or not): characters a screen reader reaches that have no Unicode value (`(cid:N)`, U+FFFD, control codes), and characters with private-use codes, with their code ranges. Each is a CHECK when above 0.

## In review.md

- An "Intake:" line under the header.
- Check rows for:
  - the text-layer test
  - an existing OCR layer ("Existing OCR layer agrees with a fresh OCR reading": CHECK when doubtful, unusable or diacritics are missing)
  - spreads ("One printed page per PDF page": CHECK, with how many pages were reordered)
  - word breaks
  - the OCR, with any low-resolution, language, unmapped-character or left empty-text issue
  - **"OCR text reviewed by a person"**, which stays CHECK until someone records "approved", on the review page's OCR Text section or with `review_ocr.py`. A verdict can also be "sent to a language reader": see [Sign-off](review-step.md#sign-off-when-a-pdf-is-ready-to-ship).
- An "Intake: OCR and auto-tagging" section with the per-page text-layer scores (a page that was not scored shows why, and which page replaced it), the OCR'd pages, and every flag.

## Asking for the OCR language

The app asks for the language of scanned pages only when it matters ([The home page](home.md#language-of-the-scanned-pages); #45, part 1 of #37). `python3 intake.py <pdf> <out_dir> --languages` runs only the page triage and the script detection of step 3, and writes `<out_dir>/languages.json`. It does no text-layer test, no CJK check and no OCR, so it takes seconds.

**The language matters (asked):**
- Japanese kana (suggests `jpn+eng`)
- Korean Hangul (`kor+eng`)
- Vietnamese letters (`vie+eng`)
- Chinese characters with no kana, or more than one CJK script: nothing suggested, never guessed
- another script, such as Cyrillic or Greek. A math book's Greek doesn't count, and IPA and other Latin extensions count as Latin.
- a scanned page with text whose script couldn't be told

With a Latin text layer, English is preselected for the last two.

**It doesn't (no question; the run goes on as before, OCR'd as English):**
- the Latin script only
- no text to read on the sampled scanned pages, such as a cover or a picture. This is kept apart from "Latin".

A weak "Japanese" reading counts as Chinese characters: asked, with nothing preselected, because Japanese and Chinese are never guessed from a weak reading. Kana in the text layer still suggests Japanese.

**Latin-script scans are OCR'd as English.** On a scan the app sees only the script, not the language, so a Hawaiian, Ilokano or Bikol scan is read with `eng`, as before this question existed. Lost ʻokina or kahakō are then caught at "OCR Text Approval" (a person reads the OCR text). The catalogue language (part 2 of #37, intake: suggest the OCR language) is the later fix.

`run_api.sh` runs it when `ASK_LANG=1` and no `OCR_LANG` is set. It stops with exit 4 only when pages need OCR and their language matters, so the app can ask it. The full intake's CJK check still runs afterwards, as above, and still stops a PDF whose pages to OCR hold CJK text.

## Not done yet

- OpenDataLoader's hybrid mode: a second, Docling-based server, which may handle complex tables better: cells that span rows or columns, and tables inside tables.
- Deskewing and despeckling degraded scans.
- Re-reading OCR lines the engine is unsure of, at a higher resolution.
- Flagging PDFs that hold personal information.
- PDF 2.0 files. They are stopped for a reviewer: see [Not supported yet: PDF 2.0](troubleshooting.md#not-supported-yet-pdf-20).
- Measuring the accuracy of the OCR itself (character and word error rates). This needs hand-corrected reference text; the first candidate is `9780824882402.pdf`, PDF pages 381–386.

veraPDF checking is done: see [Verification with veraPDF](verapdf.md).

## For developers

Calibration figures below come from the team's local test books (`samples/candidates/`, not in the repository) and books used for testing before the current samples. They are not named here.

To see what intake would do to a folder of PDFs without changing anything:

```bash
for f in ../samples/untagged/*.pdf; do python3 intake.py "$f" "/tmp/intake-plan/$(basename "$f" .pdf)" --plan-only; done
```

**Thresholds** (5% / 15%, 15 words / 60%, the 25% image and 300-character rules, 5 pages, 100 private-use characters) are named constants at the top of `intake.py`, and recorded in every `intake.json` (`settings.thresholds`). They are starting points to tune on real scores.

### Placeholder trees

`intake.json` `tag_tree` records the elements, MarkInfo, and every Figure's alt text with its page, MCIDs and image box. Alt text is recorded as:
- `placeholder`: alt whose whole text, trimmed and in any case, says nothing: "Decorative element" as Prince writes it, "image", "image N", "figure", "figure N", "graphic", "picture", "photo", "untitled"
- `publisher`: anything else, such as "Photo of …"

### Triage details

- A page counts as empty only when pdfplumber also finds no character on it: PDFium misses most of Acrobat's hidden vertical OCR text. Empty-text pages are listed in `triage.empty_text_pages`; their removal is checked as `checks.empty_text_removed`.
- Private-use characters are recorded as `private_use`; text outside the page area as `outside_page_area`; word breaks as `word_breaks`; spreads as `spreads`, with printed page numbers in `spreads.printed`.
- **Word-break gap:** under 19% of the type size (font size × text matrix), measured between advance widths, which is what a text extractor uses. The cut was calibrated on two Acrobat copies: on an earlier test book's PDF 86, Acrobat ran words together at 14.9–18.3% ("concernedwithChinese", "theWestern", "theWest"), and on 9798880703272 PDF 9 it spaced 19.8% correctly.
- **Spread test:** landscape as displayed (after its /Rotate) means width at least 1.15 × height. The gutter must fall in the middle 40–60% of the width, with 25% or more of the ink on each side. Calibrated on two test books: 17 of 19 pages and 10 of 10, with no false alarm in 178 other books.

### Text-layer test details

- **Sampling:** in a PDF with 40 or more text pages, samples are not taken from the first 5% of them (at least 6 pages), because front matter such as the copyright page is set in small type that OCR reads poorly.
- **Normalising:** quotes, dashes, case, spacing and line-end hyphens. CJK characters and underscores (which OCR never reads as fill-in rules) are left out. Only text inside the visible page area (CropBox) is compared.
- **Sample languages:** `eng`, plus the packs the text layer calls for: kana `jpn`, hangul `kor`, 50 or more Vietnamese letters `vie` (`language.score_lang`).
- **Page score:** the lower of the in-order character error rate and the any-order one (the same characters in any order). Both raw rates are recorded per page (`cer_in_order`, `cer_any_order`); `cer` is the page score. The PDF score is `median_cer`.
- **Not-scored rules:** fewer than 300 characters is counted after normalising. Math means a math font (CMMI, CMSY, CMEX, MSAM, MSBM, Symbol, MT Extra, "Math" …) and 10 or more math symbols or Greek letters in the text layer (20 or more without a math font). Diacritics not read means 20 or more marked letters in the text layer, 1.5 times as many as OCR read. How many pages in the whole PDF fall under each reason is recorded (`unscorable_in_book`).

### OCR-layer test details

- Script models used: `script/Latin`, `script/Japanese_vert+script/Japanese`, `script/Hangul…`, `script/HanS…+script/HanT…`.
- The layer is read with pdfplumber when PDFium sees under half its characters (Acrobat's hidden vertical OCR text).
- **Diacritics rule:** on pages whose error without the marks is 15% or less, the script model reads 5 or more marked vowels a page on average and the layer has under 10% as many. One test book lost ŏ/ŭ as o/u: 82 marked vowels read on 10 pages, 0 in the layer.
- Recorded as `ocr_layer_test`. Calibrated on five test books: a starting point. Math scans score badly (21% and 27% on two of them), because their OCR'd math is junk letters, not math symbols.

### Language details

- Tesseract's script names "Korean" and "Hangul", "Japanese", "Han" are read alike.
- **CJK threshold:** 10 or more CJK characters at 60% confidence or more mean the page holds CJK text. Calibrated on an earlier test book: its Chinese glossary pages scored 47–229, every cover and Part opener 0–1.
- **Speed:** with more than 12 pages to OCR, this takes 18–60 s a page on a newspaper scan, hence the shortened check. On an earlier 54-page test PDF, plan-only: about 20 minutes before, now 38 s without `OCR_LANG` and 5 minutes with `kor+eng`. The full run's CJK list also shows in intake.md's "CJK on pages to be OCR'd" row.
- **History:** before 2026-10-24, a Japanese scan went on with `eng+jpn` chosen by intake, which on vertical text gave junk.
- **Vertical trial:** pages where the horizontal packs find only 5–9 confident CJK characters are retried, up to 3 spread through the PDF; 10 or more with a `_vert` pack makes them all count. The `_vert` packs read at most 3 pages in all: those, then the CJK pages with most CJK as a trial. The suggestion needs 1.5 times the confident CJK characters on most trial pages. Recorded as `cjk_probe.vertical_trial`.

### OCR details

- The command: OCRmyPDF 17 with `--mode skip --pages <image-only pages> --output-type pdf --optimize 0 --oversample 300`. Forced OCR uses `--mode force`.
- **Not text-like:** fewer than 15 word-like tokens, or under 60% of its tokens.
- **Junk calibration:** clean OCR 0%; an earlier test book's Chinese glossary pages 3.8–10.9% with `chi_tra+eng`.

#### Forced OCR in testing

On synthetic test files, OCRmyPDF redrew each page at 400 dpi: as a 1-bit black-and-white image when the page held only black text, and as an 8-bit RGB image when it held a grey or color picture. Either way, 0.31–0.39% of each softened page differed, and the after-OCR check (limit 0.3%) stopped the PDF.

### Auto-tag details

- OpenDataLoader runs with `--format tagged-pdf`, in local mode, with no hybrid server. Its hidden-text filter is turned off when there is OCR text.
- **Spreads:** the tagger's own order is xycut, its default; it has no per-half option. On one test book it switched between halves 7–90 times a page before reordering, and once after. Vertical CJK is recognised from an Identity-V font such as Acrobat's HiddenVertOCR, the vertical-text trial, or a `_vert` pack in `OCR_LANG`.
- **Spreads, recorded:** per page, the switches between halves before and after, and whether the order changed, are recorded (`checks.spreads_reordered`), with the pages left in the tagger's order and why: a tag tree that is not one flat list under Document, or fewer than 2 elements on the page.
- On that test book's PDF 3, the running head of printed page 210 is the 14th element of its half.
- **Placeholder alt removed:** `checks.placeholder_alt_removed` in `intake.json`.

### Check details

After auto-tagging, "looks the same" allows a tolerance of 0.05% of a softened 72-dpi page, for sub-pixel glyph shifts where the tagger splits a text run. A page over it gets a second look at 300 dpi, and passes when no quarter-inch tile has more than 50 changed pixels, which a missing character exceeds. The moved fragments of a "reordered" page are listed in `intake.json` and review.md.

The OCR verdict is recorded in `record.json` → `intake.review.ocr_text_approved`: verdict, reviewer, date, reason, pages. The review page's OCR Text section writes the same record, through the same code.

### The language question

`--languages` uses one function, `scripts_seen()`, also used by the full intake. It reads the text layer's scripts, and Tesseract's on up to 5 image-only pages. `languages.json` records whether pages need OCR, how many, whether their language matters (`ask`), what was found (`found`: `latin`, `none`, …), a suggested OCR language, and the evidence: the text layer's letters by script, and each sampled scanned page's reading. `intake.json` is not touched, and its reuse check is unchanged.

- **Another script** counts at 50 letters or more and 5% of the text layer's letters.
- **A scanned page has text** when Tesseract's orientation confidence is 4.0 or more (`OSD_TEXT_CONF`). Calibrated on 14 sampled pages of 7 test books: text pages 4.7–20; covers, pictures and Part openers 0.08–3.4, some of them read as "Cyrillic" or "Devanagari".
- **A CJK script reading** (Korean, Japanese, Han) counts from 1.5 (`OSD_CJK_CONF`). A low-resolution Korean newspaper scan read "Korean" at 1.9; with the old threshold it wasn't asked, and its estimate ran 3.5 minutes to intake's CJK stop before the question came. None of the calibration pages under 4.0 read as a CJK script.
- **A weak "Japanese" reading** is one under 4.0. Tesseract's script confidence is not used: it doesn't tell text from pictures.
- When no sampled scan gives any orientation reading (blank pages, or Tesseract's `osd.traineddata` missing), the log says so in one line ("Tesseract gave no orientation reading on any of the N sampled scans"), since every page then counts as "no text".
