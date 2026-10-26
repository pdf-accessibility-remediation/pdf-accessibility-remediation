# Baseline updates

Why each regression baseline update was made (newest last). Written by `tools/regression.py --update`.

- 2026-10-25 · godzone, clans · Python 3.14 · workorder_v8.md: First baseline: the prompt v8 replies of batch all9-v8, replayed on the current code

- 2026-10-25 · godzone, clans, translation · Python 3.14 · workorder_v8.md: Add translation (tables, notes, captions, toc, page figures, merges, actual_text, untagged-path artifacts); review.md header now says a reused reply costs nothing

- 2026-10-25 · cadaverous, sands, buddhist · Python 3.14 · workorder_v8.md: Add cadaverous (language, lists, fix_figure_order), sands (adopt_orphans, language) and buddhist (ocr_words, tables)

- 2026-10-25 · ilokano · Python 3.14 · workorder_v8.md: Add ilokano: an untagged book (frozen OpenDataLoader intake), one-item list rule, gap-only word breaks; reply from a paid v8 run ($0.09)

- 2026-10-25 · buddhist · Python 3.13 · workorder_v8.md: Issue #12: OCR words now split at gaps, skip web addresses and catch an ʻokina read as a quote mark, so buddhist's word list changed (648 → 645 forms) and the old reply's ids no longer matched; re-seeded with a new reply (2026-10-25, prompt v8)

- 2026-10-25 · sands · Python 3.13 · workorder_v8.md: Issue #12: OCR-word detection changes (gap splitting, ʻokina look-alikes, no web addresses) give sands 8 suspect forms instead of 4; the reply read all of them as correct, so nothing else changes
