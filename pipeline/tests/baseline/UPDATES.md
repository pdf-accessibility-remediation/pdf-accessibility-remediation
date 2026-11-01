# Baseline updates

Why each regression baseline update was made (newest last). Written by `tools/regression.py --update`.

- 2026-10-25 · godzone, clans · Python 3.14 · workorder_v8.md: First baseline: the prompt v8 replies of batch all9-v8, replayed on the current code

- 2026-10-25 · godzone, clans, translation · Python 3.14 · workorder_v8.md: Add translation (tables, notes, captions, toc, page figures, merges, actual_text, untagged-path artifacts); review.md header now says a reused reply costs nothing

- 2026-10-25 · cadaverous, sands, buddhist · Python 3.14 · workorder_v8.md: Add cadaverous (language, lists, fix_figure_order), sands (adopt_orphans, language) and buddhist (ocr_words, tables)

- 2026-10-25 · ilokano · Python 3.14 · workorder_v8.md: Add ilokano: an untagged book (frozen OpenDataLoader intake), one-item list rule, gap-only word breaks; reply from a paid v8 run ($0.09)

- 2026-10-25 · buddhist · Python 3.13 · workorder_v8.md: Issue #12: OCR words now split at gaps, skip web addresses and catch an ʻokina read as a quote mark, so buddhist's word list changed (648 → 645 forms) and the old reply's ids no longer matched; re-seeded with a new reply (2026-10-25, prompt v8)

- 2026-10-25 · sands · Python 3.13 · workorder_v8.md: Issue #12: OCR-word detection changes (gap splitting, ʻokina look-alikes, no web addresses) give sands 8 suspect forms instead of 4; the reply read all of them as correct, so nothing else changes

- 2026-10-27 · sands · Python 3.13 · workorder_v8.md: Branch fix-ocr-word-replay: review.md now says how many OCR-word forms a reused reply read, not how many the audit lists today. sands' reply saw 4 forms (its own note names them: Shiina, Kii, xiii–xxi, Chiiki; run.ocr_words.sent = 4 in runs/batches/v8-g3/sands and f2-g3/sands, made by the pre-#12 audit), so ocr_words_sent: 4 was added by hand to reply.txt.meta.json (the run it was seeded from is not under runs/). The OCR-words row is now a CHECK (8 forms listed today, none read by this reply), so Needs a person goes 13 → 14. Correction: the 2026-10-25 sands entry above ("the reply read all of them as correct") was wrong: the reply saw only 4 of today's 8 forms.

- 2026-10-31 · godzone, clans, translation, cadaverous, sands, buddhist, ilokano · Python 3.13 · workorder_v8.md: Branch review-disclosure stage 1 (#38): review.md's headings in Title Case; the Overview gains a Status line above Ready to ship, a sixth safety check (no WCAG rule newly failing in veraPDF) and the PAC line's new wording (PAC is now a condition: no (not done for this version)); the Final Check with PAC 2026 section lists the manual checks. No record field changed; the same normalised compare as rd0/rd1 is empty for all 7 books

- 2026-10-31 · godzone, clans, translation, cadaverous, sands, buddhist, ilokano · Python 3.13 · workorder_v8.md: Branch review-disclosure (#38), review 06: the PAC section's What Needs a Person item names review.md's For a Person to Check section, and the screen-reader paragraph says a check made before shipping counts when the shipped file is the same file. Only those 2 lines changed in each book; no record field changed

- 2026-10-31 · godzone, clans, translation, cadaverous, sands, buddhist, ilokano · Python 3.13 · workorder_v8.md: #38 stage-2 revisions (13, review 14): review.md's ready block (the label alone, the four requirements in one wording), five safety checks (veraPDF is a finding), the Accessibility Evaluation section; the run-start line's date format (left out by compare_runs). regr6: 0 record fields differ; compare_norm13 empty for all 7.
