---
title: OCR words
nav_order: 9
---

# OCR words in scanned books

OCR engines read letters they don't know as look-alikes. In romanized Pali, Sanskrit and Japanese this is constant: ā and ū become "ii" (*nibbāna* → `nibbiina`, *rūpa* → `riipa`), ṇḍ becomes `t;l¢`, ü becomes "ii" (`Miiller`). A screen reader then says the wrong word, and copying gives it.

In a scanned book (the producer says OCR, or most pages are full-page images), `audit.py` lists every distinct word form that looks misread (`ii` inside a word, `;` `¢` `£` between letters, or a quote mark standing for an ʻokina: see [Hawaiian](#hawaiian)), most frequent first, up to 700. Words are split where a reader hears a break: at a space character, and also at a gap between glyphs (the rule `gaptext.py` uses for the digest), since some OCR layers draw each word apart with no space character between them. The rules are in `lib/ocrwords.py`. Each form is cropped once from the page image and placed on numbered **word sheets** (PNG, sent at full size: a macron is a few pixels). The model reads each crop and returns `ocr_words`: the id and the word exactly as printed, for the forms whose letters differ. Forms the OCR read correctly (`Hawaii`) are left out.

`decide.py` drops a reading that isn't one word, is the same as the OCR text, or is too different from it to be a misreading: after removing diacritics, the edits from the OCR text to the reading may not pass a third of the reading's length, where changing or dropping a character OCR produces from unknown letters (`i l 1 J ; : t f z` …) counts a quarter. On *Buddhist* this kept all 593 readings and let through 12 of 570 deliberately mismatched pairs, so the review's table is still checked by a person. `apply.py` then wraps every text operator that shows the form in `/Span <</ActualText (…)>> BDC … EMC`. Screen readers speak the printed spelling and copying gives it; the OCR text, its fonts and the page are unchanged, so `verify.py`'s pixel and text checks still hold (a text search still finds the OCR spelling). `review.md` lists every respelled form with its first pages for a person to check against the scan.

Word sheets share the 100 image slots of one request with the figure images, and are sent after them, within the same 20 MB budget (see [Files](files.md)). In a book with many figures, some sheets, or all of them, may not be sent. The words on those sheets are not read by the AI: a deferral and `review.md` list them for a person. With `REVIEW=1`, the reviewer can add their readings on the review page.

It costs about 1,400 input tokens per sheet (31 words) and about 37 output tokens per word, reasoning included (about 11 of them are the reading itself; the output limit allows 45). *Buddhist* (648 forms, 21 sheets) cost $0.51 in all, against $0.19–0.24 for books with no OCR words.

The model answers by id, and an id is a word's place in the audit's list. When a saved reply is reused (`REPLY=`, `FROM=`, the regression test) and the audit now lists different words (because the detection rules changed), the same ids name other words. So `decide.py` records a fingerprint of the list it sent (`run.ocr_words.fingerprint`) and, from 2026-10-27, the list itself (`run.ocr_words.list`, id → form). `FROM=` and `tools/regression.py --seed` carry the fingerprint, the number of forms and the list with the saved reply. A run that itself reused a reply passes on what it was given, never the list it was replayed against. The readings of a reused reply are used only when its fingerprint matches today's list. Otherwise they are dropped (deferred: "a new call reads them") instead of applied to the wrong words. That covers a different fingerprint, a different number of forms, and a reply saved before fingerprints existed, whose ids cannot be checked at all. That last case used to be applied as "not checked": a replay of *Buddhist*'s 2026-10-20 reply after the detection changes put 21 readings on the wrong words. `review.md` then says how many forms the reply read (the list when it was written), not how many the audit lists now. Its "OCR words" row is a CHECK, whether the reply's readings were dropped or it gave none. The fields are listed under [Output files](output-files.md). After a change to the detection rules, re-seed the regression baseline of a scanned book with a new reply.

ActualText is read by Acrobat, Chrome and screen readers that use them (NVDA, JAWS). Apple's PDFKit ignores it, so Preview, and VoiceOver reading a PDF in Preview, still give the OCR spelling: check readings in Acrobat or Chrome.

## Hawaiian

Tesseract has no Hawaiian model, so intake OCRs a Hawaiian scan with `eng`. On clean type it turned every ʻokina (U+02BB) into `‘` (U+2018) and lost every kahakō: dropped (`Kalākaua` → `Kalakaua`, `Māui` → `Maui`) or misread (`ʻōlelo` → `‘dlelo`, `ʻāina` → `‘Gina`). Older OCR layers (Acrobat 8) show the same.

- **ʻokina read as a quote mark** inside a word of Hawaiian shape (only Hawaiian letters, ending in a vowel: `Hawai‘i`, `Moloka‘i`, `Lili‘uokalani`) is a suspect, so the model reads it from the scan. English words with an apostrophe are not (`don't`, `O'Brien`: they have letters Hawaiian doesn't, or end in a consonant). The readings filter keeps a reading that only adds an ʻokina or kahakō.
- **A dropped kahakō is not fixed.** It leaves a normal-looking word, and in Hawaiian the same letters can be two words (`na` / `nā`, `ʻaina` meal / `ʻāina` land). One reading is applied to every occurrence of a form, so it would be wrong wherever the other word is printed. Fixing these needs a reading per occurrence; a person checks them.
- **Older orthography** (19th-century texts with neither mark) prints no ʻokina or kahakō, so the model finds nothing to change there.

A born-digital Hawaiian text layer keeps both marks (*Makalei a Stone*: 10,097 ʻokina as U+02BB, 7,234 kahakō).
