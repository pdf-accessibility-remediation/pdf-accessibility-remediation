# Baseline updates

Why each regression baseline update was made (newest last). Written by `tools/regression.py --update`.

- 2026-10-25 · godzone, clans · Python 3.14 · workorder_v8.md: First baseline: the prompt v8 replies of batch all9-v8, replayed on the current code

- 2026-10-25 · godzone, clans, translation · Python 3.14 · workorder_v8.md: Add translation (tables, notes, captions, toc, page figures, merges, actual_text, untagged-path artifacts); review.md header now says a reused reply costs nothing

- 2026-10-25 · cadaverous, sands, buddhist · Python 3.14 · workorder_v8.md: Add cadaverous (language, lists, fix_figure_order), sands (adopt_orphans, language) and buddhist (ocr_words, tables)

- 2026-10-25 · ilokano · Python 3.14 · workorder_v8.md: Add ilokano: an untagged book (frozen OpenDataLoader intake), one-item list rule, gap-only word breaks; reply from a paid v8 run ($0.09)

- 2026-10-25 · godzone, clans, translation, cadaverous, sands, buddhist, ilokano · Python 3.14 · workorder_v8.md: book-wide reading-order check (1.3.2): one new row in the checks table (verify.py wcag.section_order, lib/readorder.py); sands also lists its cover, read last, as already in the original

- 2026-10-25 · sands, translation · Python 3.14 · workorder_v8.md: 1.3.2: small sections read more than 5 pages after their printed page are listed (not failed); sands 57, mostly figure sections read after their part

- 2026-10-25 · buddhist · Python 3.13 · workorder_v8.md: Issue #12: OCR words now split at gaps, skip web addresses and catch an ʻokina read as a quote mark, so buddhist's word list changed (648 → 645 forms) and the old reply's ids no longer matched; re-seeded with a new reply (2026-10-25, prompt v8)

- 2026-10-25 · sands · Python 3.13 · workorder_v8.md: Issue #12: OCR-word detection changes (gap splitting, ʻokina look-alikes, no web addresses) give sands 8 suspect forms instead of 4; the reply read all of them as correct, so nothing else changes

- 2026-10-27 · sands · Python 3.13 · workorder_v8.md: Branch fix-ocr-word-replay: review.md now says how many OCR-word forms a reused reply read, not how many the audit lists today. sands' reply saw 4 forms (its own note names them: Shiina, Kii, xiii–xxi, Chiiki; run.ocr_words.sent = 4 in runs/batches/v8-g3/sands and f2-g3/sands, made by the pre-#12 audit), so ocr_words_sent: 4 was added by hand to reply.txt.meta.json (the run it was seeded from is not under runs/). The OCR-words row is now a CHECK (8 forms listed today, none read by this reply), so Needs a person goes 13 → 14. Correction: the 2026-10-25 sands entry above ("the reply read all of them as correct") was wrong: the reply saw only 4 of today's 8 forms.

- 2026-10-31 · godzone, clans, translation, cadaverous, sands, buddhist · Python 3.14 · workorder_v9.md: prompt v9 (workorder/0.2): move_section is a list of up to 3 moves, fix_figure_order can be turned off. Paid re-seed 2026-10-31 (batch v9-seed, $1.765). New: cadaverous gets one move (NOTES, PDF 253-282, before PDF 283; made, but the original had no section out of place: it re-nests NOTES and the order is unchanged); sands gets two (the cover: refused, no host; PDF 4 before PDF 5: made, lands where it already was). No book turns fix_figure_order off. Other decisions differ as after any re-seed.

- 2026-10-31 · ilokano · Python 3.14 · workorder_v9.md: prompt v9 (workorder/0.2): paid single run 2026-10-31 ($0.10) on the frozen intake; no move, figure step on

- 2026-10-31 · godzone, clans, translation, cadaverous, sands, buddhist, ilokano · Python 3.13 · workorder_v8.md: Branch review-disclosure stage 1 (#38): review.md's headings in Title Case; the Overview gains a Status line above Ready to ship, a sixth safety check (no WCAG rule newly failing in veraPDF) and the PAC line's new wording (PAC is now a condition: no (not done for this version)); the Final Check with PAC 2026 section lists the manual checks. No record field changed; the same normalised compare as rd0/rd1 is empty for all 7 books

- 2026-10-31 · cadaverous, sands · Python 3.14 · workorder_v9.md: workorder_check drops a section move when the audit finds no section read out of place in its pages or where it lands: cadaverous's NOTES move (PDF 253-282, the original has none out of place; it only re-nested NOTES) and sands' PDF 4 move (landed where it was) are dropped and listed under Decisions not applied; sands' cover move stays (refused by the executor: no host). cadaverous' figure on PDF 152 now reads after PDF 282, as NOTES keeps its place

- 2026-10-31 · godzone, clans, translation, cadaverous, sands, buddhist, ilokano · Python 3.13 · workorder_v8.md: Branch review-disclosure (#38), review 06: the PAC section's What Needs a Person item names review.md's For a Person to Check section, and the screen-reader paragraph says a check made before shipping counts when the shipped file is the same file. Only those 2 lines changed in each book; no record field changed

- 2026-10-31 · godzone, clans, translation, cadaverous, sands, buddhist, ilokano · Python 3.13 · workorder_v8.md: #38 stage-2 revisions (13, review 14): review.md's ready block (the label alone, the four requirements in one wording), five safety checks (veraPDF is a finding), the Accessibility Evaluation section; the run-start line's date format (left out by compare_runs). regr6: 0 record fields differ; compare_norm13 empty for all 7.

- 2026-10-31 · godzone, clans, translation, cadaverous, sands, buddhist, ilokano · Python 3.13 · workorder_v9.md: Merge of main (PR #51, prompt v9 replies) into review-disclosure (#38): review.md regenerated on the merged code from main's v9 replies. regr7: 0 record fields differ; compared with main's baselines, the only differences are #38's (stage 1: Title Case headings, Status line, Automated Checks; stage 2 revisions: the ready block, five safety checks, the Accessibility Evaluation section): compare_norm16 empty for all 7. Replies and expect.json are main's, unchanged.

- 2026-11-01 · godzone, clans, translation, cadaverous, sands, buddhist, ilokano · Python 3.13 · workorder_v9.md: Branch review-disclosure (#38), Patrick's changes after reviewing the app (2026-11-01): the ready block's Accessibility Evaluation reads "Not Completed" alone when neither part is recorded (was "Not Completed (neither part recorded for this version)"), and OCR Text Approval reads "Not Applicable" (was "Not Required (no OCR text was added during intake)", or its variant naming the publisher's OCR layer in sands and buddhist). Two lines per book, made on 0cb0901 (runs/review-disclosure/regr12); no record field changed

- 2026-11-01 · godzone, clans, translation, cadaverous, sands, buddhist, ilokano · Python 3.13 · workorder_v9.md: review.md's Accessibility Evaluation paragraph reworded so it no longer ends a sentence on a quoted name: 'Both parts are needed for "Ready to ship?".' is now 'The "Ready to ship?" answer needs both parts.' (one line per book; Patrick, 2026-11-01, periods inside quotes)

- 2026-11-01 · godzone, clans, translation, cadaverous, sands, buddhist · Python 3.14 · workorder_v10.md: prompt v10: tables read by row (title, note, group and repeated rows); digest gains row_shapes. Paid re-seed 2026-11-01, $1.69 for the six

- 2026-11-01 · ilokano · Python 3.14 · workorder_v10.md: prompt v10: paid single run 2026-11-01 ($0.10) on the frozen intake

- 2026-11-01 · godzone, clans, translation, cadaverous, sands, buddhist, ilokano · Python 3.13 · workorder_v9.md: Branch review-disclosure (#38), 362b0aa (Patrick, 2026-11-01: "colour" to "color" wherever a person reads them): the Accessibility Evaluation section's screen-reader list reads "Color Alone: ... by color alone" and "... colored backgrounds" (was "Colour Alone", "colour", "coloured"). Two lines per book; final round on d037c75 (runs/review-disclosure/final-regression.log); no record field changed, expect.json and the replies unchanged. The stored files also carry the run-start line and the Time line, which the compare leaves out: the run-start line now reads "November 1, 2026, at 7:08 PM" (the comma, lib/dates.py) and "AI cost not recorded · this run: no new call" (was "cost $0 (saved reply reused, no new call)": 1d2d6ea names the original call, and these replies' meta predates it, the known M5 follow-up until a re-seed)

- 2026-11-01 · godzone, clans, translation, cadaverous, sands, buddhist, ilokano · Python 3.13 · workorder_v10.md: Merge of main (PR #53, harder tables, prompt v10) into review-disclosure (#38), b8248d9: review.md regenerated on the merged code from Min's v10 replies (regr19, runs/review-disclosure/regr19). 0 record fields differ; compared with main's baselines, the only differences are #38's: compare_norm19 (compare_norm16 plus the run line's date and cost wording, the evaluation's words on the Needs a person line, and the veraPDF version as regression.py reads it) is empty for all 7 (runs/review-disclosure/regr19-vs-main.txt). Replies, expect.json and meta.json are main's, unchanged.

- 2026-11-03 · hawaii3, globalasias, northkorea, fishers, moralfoods, teika, migrant · Python 3.14 · workorder_v10.md: #61: the old tagged samples were not open source; replaced by seven CC BY-NC-ND 4.0 University of Hawaiʻi Press open-access books (samples/README.md). Paid re-seed 2026-11-03 (batch v10-open), $1.49 for the seven

- 2026-11-03 · romanization-ocr · Python 3.14 · workorder_v10.md: #61 follow-up: ocr_words on a real OCR layer again (lost with buddhist and sands). romanization-ocr: Chinese Romanization Self-Study Guide (CC BY-NC-SA 4.0), pages rasterized and OCR'd in Acrobat 2026.002.22031 at 300 dpi, which drops every tone mark. Paid single run 2026-11-03 (runs/romanization-ocr/seed1)

- 2026-11-03 · teika · Python 3.14 · workorder_v10.md: #67: teika Table 3's note cell held a paragraph (TSN, mapped to P); it now moves out after the table as it is instead of being wrapped in a new P (P inside P), so one P fewer

- 2026-11-04 · teika · Python 3.14 · workorder_v10.md: #67: the applied label counts Captions, not title rows (table: title row → Caption → table: caption made from the title rows; teika's 3 tables each have one title row, so still 3)
