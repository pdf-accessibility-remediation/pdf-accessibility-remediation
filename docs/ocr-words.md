---
title: OCR words
nav_order: 9
---

# OCR words in scanned books

OCR engines read letters they don't know as look-alikes. In romanized Pali, Sanskrit and Japanese this is constant: ā and ū become "ii" (*nibbāna* → `nibbiina`, *rūpa* → `riipa`), ṇḍ becomes `t;l¢`, ü becomes "ii" (`Miiller`). A screen reader then says the wrong word, and copying gives it.

In a scanned book (the producer says OCR, or most pages are full-page images), `audit.py` lists every distinct word form that looks misread (`ii` inside a word, or `;` `¢` `£` between letters), most frequent first, up to 700. Each form is cropped once from the page image and placed on numbered **word sheets** (PNG, sent at full size: a macron is a few pixels). The model reads each crop and returns `ocr_words`: the id and the word exactly as printed, for the forms whose letters differ. Forms the OCR read correctly (`Hawaii`) are left out.

`decide.py` drops a reading that isn't one word, is the same as the OCR text, or is too different from it to be a misreading: after removing diacritics, the edits from the OCR text to the reading may not pass a third of the reading's length, where changing or dropping a character OCR produces from unknown letters (`i l 1 J ; : t f z` …) counts a quarter. On *Buddhist* this kept all 593 readings and let through 12 of 570 deliberately mismatched pairs, so the review's table is still checked by a person. `apply.py` then wraps every text operator that shows the form in `/Span <</ActualText (…)>> BDC … EMC`. Screen readers speak the printed spelling and copying gives it; the OCR text, its fonts and the page are unchanged, so `verify.py`'s pixel and text checks still hold (a text search still finds the OCR spelling). `review.md` lists every respelled form with its first pages for a person to check against the scan.

It costs about 1,400 input tokens per sheet (31 words) and about 37 output tokens per word, reasoning included (about 11 of them are the reading itself; the output limit allows 45). *Buddhist* (648 forms, 21 sheets) cost $0.51 in all, against $0.19–0.24 for books with no OCR words.
