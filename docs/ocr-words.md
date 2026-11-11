---
title: OCR words
nav_order: 9
---

# OCR words in scanned PDFs

OCR engines read letters they don't know as look-alikes. In romanized Pali, Sanskrit and Japanese this is constant: ā and ū become "ii" (*nibbāna* → `nibbiina`, *rūpa* → `riipa`), ṇḍ becomes `t;l¢`, ü becomes "ii" (`Miiller`). A screen reader then says the wrong word, and copying gives it.

This page explains how the pipeline finds such misread words in a scanned PDF, has the AI read them from the page image, and corrects the hidden OCR text, and what a reviewer checks. It also covers Hawaiian, where pages can be read whole. Internals and test results are at the end, under [For developers](#for-developers).

## How misread words are fixed

1. **The audit lists suspect words.** In a scanned PDF (the producer says OCR, or most pages are full-page images), `audit.py` lists every distinct word form that looks misread, most frequent first, up to 700. A form looks misread when it has `ii` inside a word, `;` `¢` `£` between letters, or a quote mark standing for an ʻokina (see [Hawaiian](#hawaiian)).
2. **The AI reads them from the scan.** Each form is cropped once from the page image, and placed on numbered **word sheets** sent with the work-order request. The AI returns the word exactly as printed, for the forms whose letters differ. Forms the OCR read correctly (`Hawaii`) are left out.
3. **Unlikely readings are dropped.** A reading that isn't one word, is the same as the OCR text, or is too different from it to be a misreading is not used.
4. **Every place the form appears gets the printed spelling.** The hidden OCR text is rewritten where it can be (see [Rewriting the OCR text](#rewriting-the-ocr-text)), so search, copying and every screen reader get the printed spelling. The page image is unchanged.
5. **A reviewer checks.** `review.md` lists every respelled form with its first pages, to check against the scan. With `REVIEW=1`, the reviewer can also add readings on the review page.

**Cost:** about 1,400 input tokens per sheet (31 words), and about 37 output tokens per word, reasoning included. One earlier test book (648 forms, 21 sheets) cost $0.51 in all, against $0.19–0.24 for PDFs with no OCR words.

**When sheets don't fit.** Word sheets share the first request's 100 images and 20 MB with the figure images (see [Files](files.md)). When the figures and sheets together don't fit, the sheets are reserved first and the figures that don't fit go to figure requests, so every sheet is read (at most 700 forms, about 23 sheets and 1.5 MB).

Only with `FIGURE_PASSES=off`, or when the sheets alone leave no room, do sheets go unsent. The words on them are then not read by the AI, and a deferral and `review.md` list them for a reviewer.

## Hawaiian

Tesseract has no Hawaiian model, so intake OCRs a Hawaiian scan with `eng`. On clean type it turned every ʻokina (U+02BB) into `‘` (U+2018), and lost every kahakō: dropped (`Kalākaua` → `Kalakaua`, `Māui` → `Maui`) or misread (`ʻōlelo` → `‘dlelo`, `ʻāina` → `‘Gina`). Older OCR layers (Acrobat 8) show the same.

- **An ʻokina read as a quote mark** inside a word of Hawaiian shape is a suspect, so the AI reads it from the scan. Hawaiian shape means only Hawaiian letters, ending in a vowel: `Hawai‘i`, `Moloka‘i`, `Lili‘uokalani`. English words with an apostrophe are not suspects (`don't`, `O'Brien`): they have letters Hawaiian doesn't, or end in a consonant. The readings filter keeps a reading that only adds an ʻokina or kahakō.
- **A dropped kahakō is not an OCR word.** It leaves a normal-looking word, and in Hawaiian the same letters can be two words (`na` / `nā`, `ʻaina` meal / `ʻāina` land). One reading is applied to every occurrence of a form, so it would be wrong wherever the other word is printed. Pages that are mostly Hawaiian can instead be [read whole](#pages-read-whole), which gives a reading per place.
- **Older orthography** (19th-century texts with neither mark) prints no ʻokina or kahakō, so the AI finds nothing to change there.

A born-digital Hawaiian text layer keeps both marks: one test book had 10,097 ʻokina as U+02BB, and 7,234 kahakō.

## Pages read whole

On a page that is mostly Hawaiian, the word sheets can't fix most errors: the ʻokina is dropped as often as it becomes a quote mark, and a dropped kahakō leaves a normal word. In one 93-page Hawaiian book, rendered and OCR'd with intake's settings (`eng`), none of the 14,417 words with an ʻokina or kahakō came out right. 62% of all its words share their letters with a differently marked word (`ʻo` / `o`, `ʻia` / `ia`, `no` / `nō`). So such pages are read whole.

It is on by default in `run_api.sh`; `PAGE_READS=off` turns it off. In the app, the estimate includes it and Spend sends it. Command-line batches leave it off unless `PAGE_READS=1`.

1. **Which pages.** `audit.py` lists the scanned pages where at least half the words of 4+ letters have Hawaiian shape. Short words such as *he* and *no* have it in English too. Hawaiian-language books have nearly every page listed; English books about Hawaiʻi, with a few names a page, have none (*hawaii3*: 1 of 279 pages over half). The work-order request never sees this list.
2. **The reading.** `read_pages.py` sends each page image in its own request, asking for a transcription exactly as printed: the ʻokina as U+02BB, a kahakō only where the page prints one, and never a modern spelling the page doesn't show.
   - It prints the Expected Cost and the Max Estimated Cost (a dense page cost about 3–4 cents with Sonnet 5.5), refuses over `PAGE_READS_MAX_USD` (default 3) or the credit, and asks first unless `AUTO=1`. What it costs counts as this PDF's money (see [What a run may cost](options.md#what-a-run-may-cost)).
   - A page read before with the same model, prompt and image is reused at no cost.
   - Replies cut off at the output limit are not used.
3. **Each place.** `apply.py` pairs the page's OCR words with the reading's words in order. An OCR word whose reading differs only by its marks (ʻokina, kahakō) gets the reading at that place. A word the OCR split or joined, or garbled too far, stays as the OCR read it. The word's OCR text is then rewritten to the reading; the page image is unchanged. The rules are in [Pairing a page with its reading](#pairing-a-page-with-its-reading).
4. **A person checks.** The report lists every page read, with its changes, and a CHECK row. AI text is a draft until a person who reads Hawaiian has compared each page with the scan (a decision by the sponsor, #49). The review page shows each reading as a card.

On 5 pages of one Hawaiian book, the readings got 1,256 of 1,258 words with marks right (one ʻokina missed; `hoʻi no` read as one word), and added no mark to any of the 2,547 words without one that it paired. On a page printed without ʻokina or kahakō, the reading added none, and kept the printed `ma'u`. Pages in older spelling need no date rule: the reading follows the print. Results on more test books are under [Results on test books](#results-on-test-books).

## Rewriting the OCR text

The project leads agreed that the hidden OCR text may be rewritten where it is misspelled (#49). Where the OCR layer was written by OCRmyPDF, the word's own text is rewritten. Search, copying, selection and every screen reader then get the printed spelling, Acrobat and Preview included.

Any other text (another OCR program's layer, a visible font) is wrapped in ActualText instead. ActualText is read by Chrome and by screen readers that use it (NVDA, JAWS), but not reliably in this OCR layer:
- Acrobat's Read Out Loud skipped, and its selection jumped over, every word wrapped this way on an OCRmyPDF page (#49).
- Apple's PDFKit ignores ActualText, so Preview, and VoiceOver reading a PDF in Preview, give the OCR spelling.

That is why the OCR text itself is rewritten where it can be.

The page image is unchanged, so `verify.py`'s pixel check holds, and its text check allows exactly the logged rewrites. On the four rendered test books, every changed word was rewritten, the pages render the same, veraPDF passes, and word positions move by under 2 points at a word's end.

## For developers

### Finding the words

- The rules are in `lib/ocrwords.py`. Words are split where a reader hears a break: at a space character, and also at a gap between glyphs (the rule `gaptext.py` uses for the digest), since some OCR layers draw each word apart with no space character between them.
- Word sheets are PNG, sent at full size: a macron is a few pixels. They go in the first request after the figure images. The AI returns `ocr_words`: the id and the word exactly as printed.
- About 11 of the 37 output tokens per word are the reading itself; the output limit allows 45.
- With `FIGURE_PASSES=off` (or no room), unsent sheets behave as before figure requests existed.

### The readings filter

`decide.py` drops a reading that isn't one word, is the same as the OCR text, or is too different from it. After removing diacritics, the edits from the OCR text to the reading may not pass a third of the reading's length. Changing or dropping a character OCR produces from unknown letters (`i l 1 J ; : t f z` …) counts a quarter.

On an earlier test book (a scanned book on Buddhism), this kept all 593 readings and let through 12 of 570 deliberately mismatched pairs. So the review's table is still checked by a person.

### Reused replies and fingerprints

The AI answers by id, and an id is a word's place in the audit's list. When a saved reply is reused (`REPLY=`, `FROM=`, the regression test) and the audit now lists different words (because the detection rules changed), the same ids name other words.

So `decide.py` records a fingerprint of the list it sent (`run.ocr_words.fingerprint`), and, from 2026-10-27, the list itself (`run.ocr_words.list`, id → form). `FROM=` and `tools/regression.py --seed` carry the fingerprint, the number of forms and the list with the saved reply. A run that itself reused a reply passes on what it was given, never the list it was replayed against.

The readings of a reused reply are used only when its fingerprint matches today's list. Otherwise they are dropped instead of applied to the wrong words:
- They are recorded in `validation_dropped`, and explained in review.md's OCR-words sentence and its CHECK row.
- They are not filed as a deferral by the AI (the AI did not defer them), so "Needs a person" counts this once, as the row. A new AI request reads the words.
- That covers a different fingerprint, a different number of forms, and a reply saved before fingerprints existed, whose ids cannot be checked at all. That last case used to be applied as "not checked": a replay of one test book's 2026-10-20 reply after the detection changes put 21 readings on the wrong words.

`review.md` then says how many forms the reply read (the list when it was written), not how many the audit lists now. Its "OCR words" row is a CHECK, whether the reply's readings were dropped or it gave none. The fields are listed under [Output files](output-files.md). After a change to the detection rules, re-seed the regression baseline of a scanned PDF with a new reply.

### How the text is rewritten

`apply.py` (`_write_fixes`) rewrites a word when it is invisible OCR text (render mode 3) shown by one `Tj` in a font of the shape OCRmyPDF writes: Type0, `Identity-H`, a ToUnicode of single codes, a `CIDToGIDMap` stream.

- A character the font has no code for (ā, ʻ) gets a new code, a ToUnicode entry, the width of its letter without the mark, and a real glyph (that letter's). Never `.notdef`, which PDF/UA forbids even in invisible text.
- The word's horizontal scaling (`Tz`) is set so it keeps its old width, then set back.
- Anywhere else, the text is wrapped in `/Span <</ActualText (…)>> BDC … EMC`.

The log lists each rewrite (`ocr_text_rewritten`, per page `[old, new]`). `verify.py` compares each word's marked content before and after, and passes a page only when every changed word is one of its logged rewrites (`ocr_text_rewritten` in `verify.json`; anything else is in `text_pages_changed`).

OCRmyPDF 17 draws each page's OCR layer in a form XObject. It is followed when only that page draws it; `ocr_words` follows it the same way.

### Listing the pages

`lib/pagereads.py` lists the pages, in `_audit/page_reads.json`, with a page image (long side 1,568 px) in `page_reads/`. The listing is not in the digest. `read_pages.py` uses `prompts/page_reading_v1.md`, and adds the readings to the work order as `page_readings` (`[{page, text}]`).

### Pairing a page with its reading

`apply.py` pairs the page's OCR words with the reading's words in order, by their letters without marks.

- **Marks only:** an OCR word whose reading differs only by its marks gets the reading at that place, whatever its length.
- **Longer words:** its letters may differ too, when both words have 4+ letters, by a misreading an `ocr_words` reading would also be allowed (`p6haku` → *pōhaku*, `hallow` → *shallows* at a curled page edge).
- **Shorter words:** only where the OCR has junk and the word gets no longer (`0` → *o*, `1a` → *lā*, `nd` → *nō*). On a hard page (two columns, a photographed magazine), a short OCR word could otherwise be paired with the wrong word (`a` → *sea*, `to` → *of*).
- **A word-initial ʻokina read as a quote mark** (`‘o`, `‘aina`): the reading's ʻ takes the quote mark's place, so a screen reader hears *ʻo*, never `‘ʻo` (`ocr_words` does the same). A real quotation mark before the word stays.

The AI sometimes writes every ʻokina on a page as a quote mark (once in 9 pages, all 169 on that page). A reading with no ʻokina at all and 5 or more quote marks inside Hawaiian-shaped words has them made ʻ (`okina_slip` in the log). A page that prints an apostrophe once or twice keeps it.

An `ocr_words` form met only on pages read whole counts as handled there, not as "not found".

### Results on test books

The born-digital Hawaiian book above is *Makalei a Stone* (93 pages). The page printed without marks is from *No ka hooulu*. Through the whole pipeline (intake, the work order, `PAGE_READS=1`, apply):

| Book | Pages read | Words with ʻokina or kahakō spoken right | Page readings cost |
|---|---:|---|---:|
| *Makalei a Stone*, 10-page excerpt (rendered, OCR'd by intake) | 9 | 0 → 2,084 of 2,125 (98%) | $0.26 |
| *04_1perreira* (Hawaiian, another typeface; rendered, OCR'd with `eng`) | 15 of 21 | 0 → 2,339 of 2,437 (96%) | $0.41 |
| *Na Kai Looloolo…* (a photographed magazine, English with Hawaiian words; `PAGE_READS=all`) | 9 of 13 | no known text: 131 ʻokina and kahakō added and 85 lost letters restored, checked by eye on one page | $0.24 |
| *He moʻolelo kaʻao no Punia* (Hale Kuamoʻo 1994, Ulukau; 12 pages rendered, OCR'd by intake) | 6 of 12 | 0 → 944 of 975 (97%) | $0.12 |
| *Ka moʻolelo o Keahiakahoe* (Hale Kuamoʻo 2000, Ulukau; 16 pages rendered, OCR'd by intake) | 5 of 16 | 0 → 210 of 215 (98%) | $0.04 |
| *Ka moolelo o Heneri Opukahaia* (1867, a real scan from Internet Archive, printed without marks; 10 pages, OCR'd with `eng`) | 9 of 10 | no mark added that the page does not print. Two printed accents, *màlaila* and *Nohò*, were kept; the printed apostrophe (`ko'u`) was read as ʻ on most pages | $0.14 |

*Makalei*, *perreira*, *Punia* and *Keahiakahoe* are renderings of born-digital books, so their true text is known. The two Ulukau books store it in a legacy Hawaiian font encoding (`ä` for ā and `ÿ` for ʻ), mapped back for the truth. *Na Kai* and *Heneri* are real scans.

Intake stopped the rendered *perreira* and the *Heneri* scan for CJK text they do not have (its script test), so they were OCR'd with OCRmyPDF (`eng`) first.

On *Punia* and *Keahiakahoe*, intake kept OCR text on only half the text pages. The others fell under its text-like test (60% of tokens words of 2+ letters), since Hawaiian has many one-letter words (*o, i, a, e*), and were left as pictures with no text, so they could not be read.
