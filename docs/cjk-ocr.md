# CJK OCR

Scanned books with Chinese, Japanese or Korean text get their text layer from Tesseract (through OCRmyPDF, in
[intake](intake.md)). Tesseract misreads and drops CJK characters, most of all in vertical text, Hanja inside Korean,
furigana and old print. The OCR text is all a screen reader has, and [language tags](languages.md) can only tag text that
exists. This page covers how those pages are read again by the AI and how the readings are attached (#119), and what
the measurements behind it showed.

## How it works

1. **The audit lists the pages** (`audit.py`, `page_reads.json`): every scanned page whose OCR text holds 20 or more
   Chinese, Japanese or Korean characters, as `kind: cjk`, with a page image 2,000 pixels on its long side.
2. **The page readings step reads them** (`read_pages.py`, the same paid step as Hawaiian pages, see
   [OCR words](ocr-words.md#pages-read-whole)), with its own prompt (`prompts/page_reading_cjk_v1.md`) and its own model:
   `PAGE_READS_CJK_MODEL`, by default Gemini 3.8 Flash, never the work order's. The AI transcribes the page exactly as
   printed, one printed line (or vertical column) per line, without furigana. A reply that refuses instead of reading is
   recorded as `refused` and never used. The readings go into the work order as `page_readings` with `kind: "cjk"`.
3. **apply.py matches each reading to the OCR's lines** (`lib/cjkocr.py`):
   - the OCR's lines are its text objects (OCRmyPDF writes each line as one `BT … ET`);
   - the reading's lines are paired with them in order, each pair similar enough (`ACCEPT`); between two paired lines,
     the same number of unpaired lines on both sides (at most 3) are paired by order, so a line Tesseract read as junk
     still gets its reading;
   - each paired line's reading is split over the line's OCR words: one to one when the reading has as many words as
     the line, else by character alignment (a character the OCR dropped goes with its neighbour);
   - each word's hidden text is rewritten in place, at the same width, as for Hawaiian pages
     ([Rewriting the OCR text](ocr-words.md#rewriting-the-ocr-text)); verify.py allows exactly these changes.
4. **Furigana Tesseract read as its own line** (type under 70% of the page's usual size, mostly kana, and not paired with
   the reading, which leaves furigana out) is blanked, so a screen reader doesn't read the word twice. Logged like every
   rewrite.
5. **A page whose lines mostly don't match** (under 70% paired: a map, a newspaper, lines the OCR never found) is left as
   it was. Its reading is a draft for a person who reads the language: review.md marks it "CJK OCR: needs a person".
6. **A person who reads the language checks each page** against the scan, on the review page's "Page readings" cards
   (one per page, beside its image). review.md lists, per page, the lines matched, the OCR words changed and examples,
   and the "CJK page readings" row stays CHECK.
7. **A draft a person approves or corrects on its card** is attached at the re-apply (`checked_by: "person"` in the
   reviewed work order): the reading's lines are spread over the OCR's lines in order, each OCR line's first word
   carrying its share and the line's other words a single space. The text is read in the right order near where it is
   printed, but not word by word.

The page image never changes, and nothing is read without the step's own estimate and limit (`PAGE_READS_MAX_USD`) and
the PDF's (`BOOK_MAX_USD`). `PAGE_READS=off` turns the step off for Hawaiian and CJK pages alike.

## Measurements (2026-11-22)

**The test set** (`pipeline/tools/cjk_ocr_test.py`): 27 pages.
- 20 born-digital pages made to look scanned (200 dpi, grayscale, slight skew, blur, speckle, JPEG), whose own text is
  the answer key: simplified Chinese (6), traditional Chinese (4), Korean (6), Japanese inside English (4). These pages
  come from books and papers, so they stay local.
- 7 synthetic pages typeset with text written for the test, degraded the same way: vertical Japanese (2), vertical
  traditional Chinese, Japanese with furigana, Japanese only, Korean with Hanja (2). `cjk_ocr_test.py synth` makes them.

Scores count CJK characters only: **read** (answer-key characters found, in order), **invented** (characters that match
nothing in the answer key) and **CER** (edit distance over the answer key's length).

| Approach | Read | Invented | CER | Cost, 27 pages |
|---|---:|---:|---:|---:|
| Tesseract as intake runs it (`<lang>+eng`) | 89.7% | 1.9% | 11.2% | free |
| Free: a second pass on CJK and low-confidence lines, vertical models, furigana dropped | 96.0% | 3.4% | 5.7% | free |
| AI reads the hard lines only (Opus 5.5, Sonnet 5.5, Gemini) | 98.1–98.4% | 1.3–1.6% | 2.5–2.8% | $0.53–$1.61 |
| AI reads whole pages: Gemini 3.8 Flash | 98.5% | 0.6% | 1.8% | $0.10 |
| AI reads whole pages: Gemini 4 Carbon | 98.6% | 0.5% | 1.7% | $0.26 |
| AI reads whole pages: Opus 5.5 | 98.6% | 0.5% | 1.6% | $1.05 |
| **Gemini 3.8 Flash's pages matched back to the OCR's lines** (what apply.py does) | **98.3%** | **1.2%** | **2.5%** | $0.10 |

- **By group**, Tesseract as intake runs it read vertical text 0%, Korean with Hanja 38%, Japanese inside English 78%
  and furigana pages with 20% invented. Gemini 3.8 Flash's matched readings: vertical 100%, Korean with Hanja 100%,
  Japanese inside English 98.6%.
- **Whole pages beat hard lines** for every model tried, more accurate and inventing about a third as much, and cost
  less.
- **Stable:** Gemini 3.8 Flash and Gemini 4 Carbon gave the same scores on three runs each.
- **Sonnet 5.5 refused one page** as copyrighted text, the same page on both runs: whole-page reading needs the refusal
  check (`lib/cjkocr.refused`), and Sonnet is not the default.
- **Answer-key artifacts:** the traditional-Chinese group's remaining CER (about 11% for every method) is a map whose
  labels the answer key orders differently, and a PDF that writes 市 as the look-alike 巿. They are not misreadings.
- **Real old print** (5 scanned pages, checked by eye): on clean horizontal pages Tesseract and the AI agree (98–99%); on
  a vertical Japanese newspaper clipping and a dense Korean newspaper with Hanja, Tesseract's text is noise and the AI's
  reads as printed. A whole real run on a synthetic Korean-with-Hanja scan (intake, then this step) took the output
  PDF's text from 37% to 99.7% read, for $0.003.
- **Cost:** about $0.004 a page with Gemini 3.8 Flash, so about $1.10 for a 300-page book with CJK on every page.

## What it doesn't do yet

- **The OCR approval's own section** (OCR Text) doesn't list draft pages: they are checked on their Page readings cards,
  which an OCR Text approval doesn't cover.
- **Spaces between characters of one word:** where Tesseract split one word into two boxes, the rewritten text keeps a
  space between them. Dropping it was tried and measured: OCRmyPDF's word boxes overlap, and without the space pdfium
  drops the characters whose box overlaps the next word's (宮, 觀 on the test pages). Screen readers read the characters
  the same either way.
- **Vertical pages OCR'd as horizontal:** when intake reads a vertical page without a `_vert` pack, its OCR lines are noise
  and too few match: the page goes to a person as a draft (who can approve the reading, step 7). Intake already
  suggests the `_vert` pack. Changing intake to rerun such pages is left to intake's owner.
- **The interim stop for CJK under an English-only OCR layer** (#119 item 8) is unchanged: intake is not changed by this
  work. A suggestion for intake's owner: with this step on, a book whose existing OCR layer lacks the CJK the image shows
  could go on to an intake OCR pass and then this step, instead of stopping.

## For developers

- `lib/cjkocr.py`: the score, `align_page`, `split_line`, `is_ruby`, `refused`, and the calibrated thresholds
  (`ACCEPT`, `MATCH_MIN`, `GAP_MAX`).
- `pipeline/tools/cjk_ocr_test.py`: the test set and every measurement above (`synth`, `ocr`, `noruby`, `ai`, `align`,
  `score`). Paid requests are cached by their exact content and logged; `--max-usd` and `--total-usd` cap them.
- Tests: `tests/test_cjkocr.py` (the module), `tests/test_cjk_page_readings.py` (an OCRmyPDF-shaped synthetic layer: the
  audit's listing, read_pages.py with a fake OpenRouter, apply.py and verify.py, and run_api.sh end to end).
