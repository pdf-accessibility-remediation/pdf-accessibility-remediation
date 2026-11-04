# Remediation Review: teika.pdf

Result: `teika_remediated.pdf`

281 pages · run November 4, 2026, at 2:26 AM · model `anthropic/claude-sonnet-5.5` · prompt `workorder_v10.md` (15b5aa0ade9c6549) · AI cost $0.226 ($0.0008 per page), from the original call on November 3, 2026 · this run: no new call · tokens: saved reply reused, not counted

Intake: none (already tagged)

Libraries: python 3.14.4 · pikepdf 10.5.1 · pdfplumber 0.11.9 · pypdfium2 5.7.1 · pillow 13.0.0 · fonttools 4.62.1

Time: intake 0.5s · audit 42.2s · reuse saved reply 0.7s · apply 59.4s · verify 52.6s · total 155.4s

## Overview

[Open the dashboard](review.html)

**Status:** Not Ready

**Ready to ship?**
- Work Order Approval: Not Approved (applied without a review)
- ✓ OCR Text Approval: Not Applicable
- Safety Checks: Failed (all content tagged or decoration)
- Accessibility Evaluation: Not Completed

**Safety checks:** OK ✔ pages look the same · OK ✔ text unchanged · FAILED ✘ all content tagged or decoration · OK ✔ tag-tree index points into the tree · OK ✔ every font readable  
**Needs a person:** 15 (7 deferred by the AI · 4 deferred by the executor · 4 CHECK rows)  
**AI decisions:** 50 in the work order, applied without review by a person  
**Fixed automatically (no AI):** links tied and described 1,648 · note IDs 411 · pages given tab order 194 · decorative lines marked 47 · title shown in the window 2 · whole-page figures wrapped 2 · tag-tree index entries 2 · marked as tagged 1 · empty tags removed 1  
**veraPDF (WCAG 2.2 machine checks):** 9 WCAG rules failing before (3,433 checks) → 1 after (251 checks) · 0 newly failing

Automated checks are evidence, not sign-off.

| Top issues | Pages | Where |
|---|---|---|
| All content tagged or marked as decoration: 6846 untagged characters · 251 untagged objects (251 text) | see Automated Checks | [Automated Checks](#automated-checks) |
| Page-level figure wrap: PDF 1 (printed Cover), PDF 5 (printed iv) wrapped as one Figure · not wrapped: PDF 85 (printed 72) (has 2 annotation(s) (links)); PDF 157 (printed 144) (has 2 annotation(s) (links)); PDF 158 (printed 145) (has 2 annotation(s) (links)) | 5 pages, PDF 1 (printed Cover) to PDF 158 (printed 145) | [Automated Checks](#automated-checks) |
| Executor applied every decision: 37 rejected · 0 failed (listed under "Decisions not applied") | see §17 | [§17](#17-decisions-not-applied-40) |
| Content neither tagged nor marked as decoration (veraPDF 7.1-3, 251 checks) | PDF 85 (printed 72) | [§13](#13-verapdf-wcag-22-machine-profile-before-and-after) |
| 68 Han-only runs need Japanese or Chinese (han_review.csv) | 19 pages, PDF 60 (printed 47) to PDF 247 (printed 234) | [§16](#16-deferred-by-the-executor) |
| … and 8 more | | §15, §16 |

Automated checks are evidence, not legal sign-off. Items marked **CHECK**, and everything under "For a person to check", need a human.

## Automated Checks

| Check | Result | Detail |
|---|---|---|
| Every page looks the same as the original | OK | 0 pages differ |
| Published text unchanged | OK | 0 pages changed |
| All content tagged or marked as decoration | **CHECK** | 6846 untagged characters · 251 untagged objects (251 text) |
| Untagged paths: none left | OK | 0 untagged paths · 47 rules, borders and lines marked as decoration by this run |
| Invisible OCR text: every glyph defined | OK | no undefined glyphs in invisible text |
| Page-level figure wrap | **CHECK** | PDF 1 (printed Cover), PDF 5 (printed iv) wrapped as one Figure · not wrapped: PDF 85 (printed 72) (has 2 annotation(s) (links)); PDF 157 (printed 144) (has 2 annotation(s) (links)); PDF 158 (printed 145) (has 2 annotation(s) (links)) |
| Empty tags removed when proven empty | OK | 1 removed |
| Tag-tree index points only into the tree | OK | 0 dangling entries · 0 stale entries (marked content no longer drawn) |
| No empty tables | OK | none |
| No empty tags | OK | 0 empty tags |
| No paragraph holding only figures | OK | none |
| Every caption grouped with its figure | OK | all grouped |
| No link whose only text is a URL | OK | none |
| Tag tree consistent | OK | 0 missing · 0 mismatched |
| All marked text reachable from the tag tree | OK | 0 orphan runs |
| One Document root | OK | Document 1 |
| Every link tied to its text and described | OK | 0 unresolved · 0 without description · 0 pointing to no annotation |
| No link nested inside another | OK | 0 |
| Headings: no skipped levels | OK | H1 1 · H2 14 · H3 61 · H4 3 |
| Headings: exactly one H1 (the title) | OK | 1 H1 (several H1s usually mean parts or chapters were not demoted) |
| Figures: none with empty or placeholder alt | OK | 3 figures, 0 placeholder |
| Every Note has a unique ID | OK | 411 notes · 0 without ID · 0 duplicate · 0 not in the ID tree |
| Bookmarks present (documents over 9 pages) | OK | 36 bookmarks |
| Model reply held one work order | OK | one |
| Executor applied every decision | **CHECK** | 37 rejected · 0 failed (listed under "Decisions not applied") |
| Nothing deferred by the executor | **CHECK** | 7 deferred (listed under "Deferred by the executor") |
| Fonts: every glyph defined (no .notdef) | OK | none found |
| Fonts: every embedded font program could be read | OK | all read |
| Fonts: embedded and mapped to Unicode | OK | 0 not embedded · 0 without ToUnicode (5 more have none and need none: standard encoding, non-symbolic) |
| Tab order follows the tag structure on pages with links or other annotations | OK | 0 of 194 pages with annotations lack /Tabs /S (log: 194 set by this run) |
| Characters with no Unicode value (checklist 3.6) | OK | 0 read-aloud characters with no Unicode value |
| Private-use characters (checklist 3.6) | OK | 0 read-aloud characters with private-use codes |
| Title and language set | OK | "Teika: The Life and Works of a Medieval Japanese Poet" · en-US |
| veraPDF WCAG 2.2 (machine): no WCAG failures | **CHECK** | before: 9 WCAG rules failed (3433 checks) → after: 1 WCAG rule failed (251 checks) (listed under "veraPDF") |
| veraPDF: no rule newly failing or failing more often | OK | 9 fixed · 1 still failing · 0 newly failing |
| Alt text: none like a file name or repeated on many figures (1.1.1) | OK | 0 of 3 figures flagged |
| Tables: every table has header cells (1.3.1) | OK | none without |
| Reading order: no page jumps back up a column (1.3.2) | OK | 0 of 267 pages flagged |
| Reading order: no section moved away from its printed place by this run (1.3.2) | OK | 0 new · 9 already in the original, of 46 sections and blocks |
| Title is not a file name or placeholder (2.4.2) | OK | "Teika: The Life and Works of a Medieval Japanese Poet" |
| Link text: none like "click here" (2.4.4) | OK | 0 generic |
| Headings: none empty, very long or repeated in a row (2.4.6) | OK | 0 empty · 0 long · 0 repeated |

## For a Person to Check

### 1. Pages Wrapped as One Figure (2)

Pages with nothing tagged and nothing marked as decoration that hold a drawing (a full-page map, plate or cover). Each page was wrapped whole in one Figure; nothing on it was changed or removed.

- PDF 1 (printed Cover): read first in the document. Alt text from the AI: "Front cover of Teika: The Life and Works of a Medieval Japanese Poet by Paul S. Atkins. Three maple leaves, two in grey and one in white, on a black background, with the title TEIKA in large white capitals, the subtitle in gold, and the author's name at the bottom."
- PDF 5 (printed iv): read after "" on PDF 4 (printed iii). Alt text from the AI: "Copyright page. © 2017 University of Hawaiʻi Press, all rights reserved, printed in the United States of America. Library of Congress Cataloging-in-Publication data for Teika: the life and works of a medieval Japanese poet by Paul S. Atkins (LCCN 2016032550; subject: Fujiwara, Sadaie, 1162–1241). Creative Commons BY-NC-ND 4.0 open access notice with ISBNs 9798880702541 (OA PDF) and 9798880702558 (OA EPUB). Funded by the National Endowment for the Humanities Fellowships Open Book Program. Printed on acid-free paper."
- PDF 85 (printed 72): not wrapped, left as it is (has 2 annotation(s) (links)).
- PDF 157 (printed 144): not wrapped, left as it is (has 2 annotation(s) (links)).
- PDF 158 (printed 145): not wrapped, left as it is (has 2 annotation(s) (links)).

### 2. Alt Text Written or Changed by the AI (1)

| Page | Before | After |
|---|---|---|
| PDF 4 (printed iii) | — | University of Hawaiʻi Press logo |

### 3. Headings

Heading levels by style (as applied):

| Style | Level | How | Elements |
|---|---|---|---:|
| CT | H2 | RoleMap | 7 |
| FMH | H2 | RoleMap | 2 |
| BMH | H2 | RoleMap | 4 |
| ATAH | H2 | RoleMap | 1 |
| BMH1 | H3 | RoleMap | 6 |
| H1 | H3 | retype (standard tag) | 58 |

Merged: `CN` into the next `CT`; `CST` into the prev `CT`

Spoken text set by the AI (should match what is printed):

| Page | Text |
|---|---|
| PDF 22 (printed 9) | Chapter One A Documentary Biography |
| PDF 56 (printed 43) | Chapter Two The Bodhidharma Style and the Poetry Contest in Six Hundred Rounds |
| PDF 101 (printed 88) | Chapter Three Teika’s Poetics |
| PDF 114 (printed 101) | Revisiting MAIGETSUSHŌ and TEIKA JITTEI |
| PDF 125 (printed 112) | Teika’s Judgments at SENGOHYAKUBAN UTAAWASE |
| PDF 137 (printed 124) | Chapter Four Spirit of Han, Genius of Yamato |
| PDF 169 (printed 156) | China in THE TALE OF MATSURA |
| PDF 177 (printed 164) | Chapter Five Teika after Teika A History of Reception |

### 4. Elements Retyped by the AI (4)

Check each one is (or is not) a heading as decided.

| Page | Text | Before | After |
|---|---|---|---|
| PDF 4 (printed iii) | Teika | TPT | H1 |
| PDF 102 (printed 89) | I. Texts That May Be Attributed to Teika with Confidence | H1 | H4 |
| PDF 104 (printed 91) | II. Texts Whose Authorship Is Disputed | H1 | H4 |
| PDF 104 (printed 91) | III. Texts That Are Clearly Forgeries | H1 | H4 |

### 5. Lists and Tables

- Header cells marked by the AI on PDF 94 (printed 81): 1 header row(s), 0 header column(s), 2 cells changed to header cells; 1 title row(s) made the caption, 1 note row(s) moved after the table. Check they are the real headers.
- Header cells marked by the AI on PDF 95 (printed 82): 1 header row(s), 0 header column(s), 3 cells changed to header cells; 1 title row(s) made the caption. Check they are the real headers.
- Header cells marked by the AI on PDF 96 (printed 83): 1 header row(s), 0 header column(s), 3 cells changed to header cells; 1 title row(s) made the caption. Check they are the real headers.

Tables kept as tables (3): check header cells and reading order.

- PDF 94 (printed 81): 11 rows × 3 columns, 0 header cells. "Table 1. Frequency of taigen- dome in seasonal poems of the Hachidaishū"
- PDF 95 (printed 82): 14 rows × 5 columns, 0 header cells. "Table 2. Frequency of taigen- dome at Roppyakuban utaawase"
- PDF 96 (printed 83): 19 rows × 5 columns, 0 header cells. "Table 3. Frequency of taigen- dome in Omuro gojisshu"

### 6. Text a Screen Reader Could Not Reach (before this run)

4 pages had text outside the tag tree: 0 orphan runs (marked, but no tag owns them) and 154 untagged runs. Running heads and page numbers among them can be hidden as decoration; real content must be added to the tag tree by a person. After this run: 6846 untagged characters, 0 orphan runs remain.

Pages: PDF 5 (printed iv), PDF 85 (printed 72), PDF 157–158 (printed 144–145)

### 7. Hidden from Screen Readers (artifacts)

- "notes running heads and page numbers": text matching `(\d+ )?Notes to Pages \d+–\d+( \d+)?|\d+` on PDF 229–256 (printed 216–243)
- "running heads, acknowledgments": text matching `((\d+|[ivxl]+) )?(Acknowl edgments|Index of Poems Cited|Index|Introduction|Chapter One|A Documentary Biography)( (\d+|[ivxl]+))?|\d+|[ivxl]+` on PDF 11 (printed x)
- "running heads, introduction": text matching `((\d+|[ivxl]+) )?(Acknowl edgments|Index of Poems Cited|Index|Introduction|Chapter One|A Documentary Biography)( (\d+|[ivxl]+))?|\d+|[ivxl]+` on PDF 15–16 (printed 2–3)
- "running heads, chapter one": text matching `((\d+|[ivxl]+) )?(Acknowl edgments|Index of Poems Cited|Index|Introduction|Chapter One|A Documentary Biography)( (\d+|[ivxl]+))?|\d+|[ivxl]+` on PDF 23–24 (printed 10–11)
- "running heads, index": text matching `((\d+|[ivxl]+) )?(Acknowl edgments|Index of Poems Cited|Index|Introduction|Chapter One|A Documentary Biography)( (\d+|[ivxl]+))?|\d+|[ivxl]+` on PDF 271–272 (printed 258–259)
- "running heads, index of poems": text matching `((\d+|[ivxl]+) )?(Acknowl edgments|Index of Poems Cited|Index|Introduction|Chapter One|A Documentary Biography)( (\d+|[ivxl]+))?|\d+|[ivxl]+` on PDF 277–278 (printed 264–265)
- "drop folios": text matching `[ivxlc]+|\d+` on PDF 8–270 (printed vii–257)

### 8. Untagged Paths (rules, borders, lines)

47 paths drawn outside any tag were marked as decoration: none of them carries text, an image or a link, and none touches untagged text or images.

Strokes directly under text, marked as decoration. An underline can carry meaning (emphasis, a sound in a romanization); if it does here, that meaning must be given another way (e.g. ActualText or a note):

- PDF 132 (printed 119): 8

### 9. Untagged Content (251 objects)

Drawn content that is neither tagged nor marked as decoration (a form XObject counts once). Not changed by the pipeline; a person decides whether each is real content (tag it) or decoration (artifact it). Pages with the most:

- PDF 157 (printed 144): 87 text
- PDF 158 (printed 145): 86 text
- PDF 85 (printed 72): 78 text

### 10. Spoken Text (ActualText) Checked Against the Print (5 accepted with differences, 0 rejected)

A spoken text may differ from the printed characters only in spacing, letter case and line-end hyphens (sponsor rule 1). Accepted ones that differ are listed so a person can listen to them; rejected ones added or changed words or punctuation.

- Accepted, PDF 22 (printed 9): printed "Chapter One A Documentary Biography" → spoken "Chapter One A Documentary Biography"
- Accepted, PDF 56 (printed 43): printed "Chapter Two The Bodhidharma Style and the Poetry Contest in Six Hundred Rounds" → spoken "Chapter Two The Bodhidharma Style and the Poetry Contest in Six Hundred Rounds"
- Accepted, PDF 101 (printed 88): printed "Chapter Three Teika’s Poetics" → spoken "Chapter Three Teika’s Poetics"
- Accepted, PDF 137 (printed 124): printed "Chapter Four Spirit of Han, Genius of Yamato" → spoken "Chapter Four Spirit of Han, Genius of Yamato"
- Accepted, PDF 177 (printed 164): printed "Chapter Five Teika after Teika A History of Reception" → spoken "Chapter Five Teika after Teika A History of Reception"

### 11. Text a Running-head or Page-number Rule Matched But Left Visible (6)

A rule for the top or bottom band hides a run only when everything else on that line is matched too. These runs matched the rule but share their line with other text (for example a note number in the first line of body text), so they were left as they are.

- PDF 271 (printed 258): rule "running heads, index" matched "9" on the line "Fujiwara no Teika: biography, 9–42; honka-dori (allusive variation), 174, 190"
- PDF 271 (printed 258): rule "running heads, index" matched "42" on the line "Fujiwara no Teika: biography, 9–42; honka-dori (allusive variation), 174, 190"
- PDF 271 (printed 258): rule "running heads, index" matched "174" on the line "Fujiwara no Teika: biography, 9–42; honka-dori (allusive variation), 174, 190"
- PDF 271 (printed 258): rule "running heads, index" matched "190" on the line "Fujiwara no Teika: biography, 9–42; honka-dori (allusive variation), 174, 190"
- PDF 272 (printed 259): rule "running heads, index" matched "202" on the line "Kindai shūka (Superior poems of our and kokugaku scholars, 202, 204; and"
- PDF 272 (printed 259): rule "running heads, index" matched "204" on the line "Kindai shūka (Superior poems of our and kokugaku scholars, 202, 204; and"

### 12. Empty Tags (1 removed, 0 kept)

A tag is removed only when proven empty: nothing under it holds content, it carries no Alt, ActualText, E or ID, and nothing in the file refers to it except its parent. Table cells are never removed one by one; a table goes only when every part is empty.

- Removed: 1 TPCIT

### 13. veraPDF (WCAG 2.2 machine profile), Before and After

veraPDF 1.30.3, profile "WCAG 2.2 machine validation profile" (7da399cf5baa). Counts are failed checks; pages are from the first checks veraPDF lists for each rule, so a rule may fail on more pages. Rules that only PDF/UA requires are listed apart and do not count. "Who fixes" is who can act on the rule: the pipeline by itself, the AI through the work order, or only a person. **Newly failing** means this run broke something the original passed. Before: 9 rules failing (the AI can act on 5, the pipeline on 4, only a person on 0). After: 1.

| Rule | WCAG | What it checks | Who fixes | Before | After | Status | Pages (after, else before) |
|---|---|---|---|---:|---:|---|---|
| ISO 14289-1 7.1-3 | 1.3.1 | Content shall be marked as Artifact or tagged as real content e.g. "Content is neither marked as Artifact nor tagged as real content" | the AI (`artifacts`) | 372 | 251 | still failing | PDF 85 (printed 72) |
| ISO 14289-1 7.2-34 | 3.1.1 | Natural language for text in page content shall be determined | the AI (`document`) | 1235 | 0 | fixed | PDF 5 (printed iv) |
| ISO 14289-1 7.18.5-1 | 2.4.4, 4.1.2 | Links shall be tagged according to ISO 32000-1:2008, 14.8.4.4.2, Link Element | the pipeline | 1232 | 0 | fixed | PDF 8 (printed vii), PDF 10 (printed ix), PDF 14 (printed 1), PDF 22 (printed 9), PDF 56 (printed 43), PDF 85 (printed 72), PDF 94 (printed 81), PDF 95 (printed 82) |
| ISO 14289-1 7.2-30 | 3.1.1, 3.1.2 | Natural language for text in ActualText attribute in Span Marked Content shall be determined | the AI (`document`) | 361 | 0 | fixed | PDF 5 (printed iv), PDF 17 (printed 4) |
| ISO 14289-1 7.18.3-1 | 2.4.3 | Every page on which there is an annotation shall contain in its page dictionary the key Tabs, and its value shall be S | the pipeline (194 changed) | 194 | 0 | fixed | PDF 8 (printed vii), PDF 10 (printed ix), PDF 14 (printed 1), PDF 15 (printed 2), PDF 20 (printed 7), PDF 22 (printed 9), PDF 24 (printed 11), PDF 28 (printed 15), PDF 29 (printed 16), PDF 30 (printed 17), PDF 31 (printed 18), PDF 32 (printed 19), PDF 33 (printed 20), PDF 34 (printed 21), PDF 35 (printed 22), PDF 36 (printed 23), PDF 37 (printed 24), PDF 38 (printed 25), PDF 39 (printed 26), PDF 41 (printed 28) |
| ISO 14289-1 7.2-2 | 3.1.2 | Natural language in the Outline entries shall be determined | the AI (`document`) | 36 | 0 | fixed | page: not on this tag |
| ISO 14289-1 6.2-1 | 1.3.1 | The document catalog dictionary shall include a MarkInfo dictionary containing an entry, Marked, whose value shall be true | the pipeline (1 changed) | 1 | 0 | fixed | page: not on this tag |
| ISO 14289-1 7.1-10 | 2.4.2 | The document catalog dictionary shall include a ViewerPreferences dictionary containing a DisplayDocTitle key, whose value shall be true | the pipeline (1 changed) | 1 | 0 | fixed | page: not on this tag |
| ISO 14289-1 7.3-1 | 1.1.1 | Figure tags shall include an alternative representation or replacement text that represents the contents marked with the Figure tag as noted in ISO 32000-1:2008, 14.7.2, Table 323 | the AI (`alt`) | 1 | 0 | fixed | PDF 4 (printed iii) |

### 14. WCAG Checks veraPDF Does Not Make

Each item is something to look at, not a proven failure.

- 1.3.2 31 small sections are read more than 5 pages after their printed page, after a longer section that covers them. Not a failure (long stories overlap in InDesign books), but a screen reader hears them far from where they are printed: PDF 94 (printed 81) read after PDF 269 (printed 256); PDF 95 (printed 82) read after PDF 269 (printed 256); PDF 96 (printed 83) read after PDF 269 (printed 256); PDF 229 (printed 216) read after PDF 269 (printed 256); PDF 230 (printed 217) read after PDF 269 (printed 256); PDF 231 (printed 218) read after PDF 269 (printed 256); PDF 232 (printed 219) read after PDF 269 (printed 256); PDF 233 (printed 220) read after PDF 269 (printed 256); PDF 234 (printed 221) read after PDF 269 (printed 256); PDF 235 (printed 222) read after PDF 269 (printed 256); PDF 236 (printed 223) read after PDF 269 (printed 256); PDF 237 (printed 224) read after PDF 269 (printed 256) and 19 more
- 1.3.2 9 sections read away from their printed place, as in the original (this run did not move them). Listen through each where it is read, or move it with move_section:
  - PDF 11 (printed x): Story "Acknowl edgments", read before PDF 2 (printed i)
  - PDF 15 (printed 2): Story "Introduction", read between PDF 12 (printed xi) and PDF 14 (printed 1)
  - PDF 16 (printed 3): Story "Introduction", read between PDF 12 (printed xi) and PDF 14 (printed 1)
  - PDF 23 (printed 10): Story "Chapter One", read between PDF 12 (printed xi) and PDF 14 (printed 1)
  - PDF 24 (printed 11): Story "A Documentary Biography", read between PDF 12 (printed xi) and PDF 14 (printed 1)
  - PDF 271 (printed 258): Story "Index", read between PDF 256 (printed 243) and PDF 270 (printed 257)
  - PDF 272 (printed 259): Story "Index", read between PDF 256 (printed 243) and PDF 270 (printed 257)
  - PDF 277 (printed 264): Story "Index of Poems Cited", read between PDF 256 (printed 243) and PDF 270 (printed 257)
  - PDF 278 (printed 265): Story "Index of Poems Cited", read between PDF 256 (printed 243) and PDF 270 (printed 257)

### 15. Deferred by the AI

- **Entire body text of three pages is untagged (not in any tag, not artifact): real content that cannot be fixed by this work order. A person must tag it in reading order. This is the main source of veraPDF 7.1-3 failures.**: veraPDF 7.1-3. Untagged real content (poem, quotations, running text); cannot be artifacted. [PDF 85 (printed 72), PDF 157 (printed 144), PDF 158 (printed 145)]
- **Copyright/CIP page is untagged text. It is given a descriptive alt text as a page figure, but ideally the text should be tagged as real paragraphs.**: veraPDF 7.1-3. Untagged real content on a page treated as a figure. [PDF 5 (printed iv)]
- **Index entries have lost or scrambled page numbers in the text layer (for example 'calligraphy, , , –, , –, 38164196972012069 242'). Reading order and numbers need a human check.**: Text-layer problem; the text cannot be changed here. [PDF 270 (printed 257), PDF 278 (printed 265)]
- **Numbered and lettered paragraph runs (styles NLF/NL/NLL, intro and chapter 3 outlines) and the bulleted participant lists (BLF/BL/BLL) are plain P with literal markers; not converted to L/LI.**: Mixed numbering schemes (1., I., A.) and literal bullets in the text; converting could duplicate markers. [PDF 20 (printed 7), PDF 21 (printed 8), PDF 77 (printed 64), PDF 102 (printed 89), PDF 104 (printed 91)]
- **Title page has ornament-like elements (style TPTORNF/TPTORNL with text 'P') and an empty TPCIT element.**: Meaning unclear; harmless but a person should check the title page reading order. [PDF 4 (printed iii)]
- **Heading levels inside chapters: all H1-styled section heads are mapped to H3; small-cap-run heads (8 pt) may be a lower level in some chapters (for example chapter 5 under 'Muromachi Period'). Only the 'I./II./III.' heads on PDF 102–104 were set to H4.**: Digest does not show a clear hierarchy for the rest. [PDF 58 (printed 45), PDF 220 (printed 207)]
- **Han-only CJK runs (68) left for the executor to defer to a human (Japanese or Chinese ambiguity).**: Ambiguous language, never guessed. [PDF 60 (printed 47), PDF 61 (printed 48), PDF 73 (printed 60), PDF 76 (printed 63), PDF 98 (printed 85), PDF 137 (printed 124)]

Reviewer note from the AI: Rolemap: CT (chapter titles), FMH, BMH and ATAH become H2; BMH1 (chapter heads in Notes) H3; the existing H1 style (in-chapter section heads) H3; the only H1 is the book title on PDF 4 (printed iii). Chapter labels (CN) are merged into the chapter titles and the Chapter Five subtitle (CST) is merged into its title. Running heads and drop folios are artifacted by rule; check that a rule did not miss a run on PDF 11, 15–16, 23–24, 229–256, 271–272 and 277–278. The three tables (PDF 94–96) are read after the main text in the current tree, so move_section puts each one before the first block on PDF 97; please check this reading order after the move. Language of the whole document is en-US; romanized Japanese is not tagged.

### 16. Deferred by the Executor

- **68 Han-only CJK runs** need a Japanese / Chinese decision: fill in `han_review.csv`.
- link on a page with no tagged text (PDF 85 (printed 72)): tied to tagged text on PDF 84 (printed 71)
- link on a page with no tagged text (PDF 85 (printed 72)): tied to tagged text on PDF 84 (printed 71)
- link on a page with no tagged text (PDF 157 (printed 144)): tied to tagged text on PDF 156 (printed 143)
- link on a page with no tagged text (PDF 157 (printed 144)): tied to tagged text on PDF 156 (printed 143)
- link on a page with no tagged text (PDF 158 (printed 145)): tied to tagged text on PDF 159 (printed 146)
- link on a page with no tagged text (PDF 158 (printed 145)): tied to tagged text on PDF 159 (printed 146)

### 17. Decisions Not Applied (40)

Rejected by validation or by the executor; nothing was half-applied.

| What | Why | Count |
|---|---|---:|
| artifact notes running heads and page numbers | element is not a single marked-content run | 28 |
| move_section | the audit finds no section read out of place in these pages or where it lands | 3 |
| artifact running heads, introduction | element is not a single marked-content run | 2 |
| artifact running heads, chapter one | element is not a single marked-content run | 2 |
| artifact running heads, index | element is not a single marked-content run | 2 |
| artifact running heads, index of poems | element is not a single marked-content run | 2 |
| artifact running heads, acknowledgments | element is not a single marked-content run | 1 |

Each one:

- {"op": "artifact notes running heads and page numbers (5344, 0)", "why": "element is not a single marked-content run"}
- {"op": "artifact notes running heads and page numbers (5342, 0)", "why": "element is not a single marked-content run"}
- {"op": "artifact notes running heads and page numbers (5340, 0)", "why": "element is not a single marked-content run"}
- {"op": "artifact notes running heads and page numbers (5338, 0)", "why": "element is not a single marked-content run"}
- {"op": "artifact notes running heads and page numbers (5336, 0)", "why": "element is not a single marked-content run"}
- {"op": "artifact notes running heads and page numbers (5334, 0)", "why": "element is not a single marked-content run"}
- {"op": "artifact notes running heads and page numbers (5332, 0)", "why": "element is not a single marked-content run"}
- {"op": "artifact notes running heads and page numbers (5330, 0)", "why": "element is not a single marked-content run"}
- {"op": "artifact notes running heads and page numbers (5328, 0)", "why": "element is not a single marked-content run"}
- {"op": "artifact notes running heads and page numbers (5326, 0)", "why": "element is not a single marked-content run"}
- {"op": "artifact notes running heads and page numbers (5324, 0)", "why": "element is not a single marked-content run"}
- {"op": "artifact notes running heads and page numbers (5322, 0)", "why": "element is not a single marked-content run"}
- {"op": "artifact notes running heads and page numbers (5320, 0)", "why": "element is not a single marked-content run"}
- {"op": "artifact notes running heads and page numbers (5318, 0)", "why": "element is not a single marked-content run"}
- {"op": "artifact notes running heads and page numbers (5316, 0)", "why": "element is not a single marked-content run"}
- {"op": "artifact notes running heads and page numbers (5314, 0)", "why": "element is not a single marked-content run"}
- {"op": "artifact notes running heads and page numbers (5312, 0)", "why": "element is not a single marked-content run"}
- {"op": "artifact notes running heads and page numbers (5310, 0)", "why": "element is not a single marked-content run"}
- {"op": "artifact notes running heads and page numbers (5308, 0)", "why": "element is not a single marked-content run"}
- {"op": "artifact notes running heads and page numbers (5306, 0)", "why": "element is not a single marked-content run"}
- {"op": "artifact notes running heads and page numbers (5304, 0)", "why": "element is not a single marked-content run"}
- {"op": "artifact notes running heads and page numbers (5302, 0)", "why": "element is not a single marked-content run"}
- {"op": "artifact notes running heads and page numbers (5300, 0)", "why": "element is not a single marked-content run"}
- {"op": "artifact notes running heads and page numbers (5298, 0)", "why": "element is not a single marked-content run"}
- {"op": "artifact notes running heads and page numbers (5296, 0)", "why": "element is not a single marked-content run"}
- {"op": "artifact notes running heads and page numbers (5294, 0)", "why": "element is not a single marked-content run"}
- {"op": "artifact notes running heads and page numbers (5292, 0)", "why": "element is not a single marked-content run"}
- {"op": "artifact notes running heads and page numbers (5290, 0)", "why": "element is not a single marked-content run"}
- {"op": "artifact running heads, acknowledgments (10916, 0)", "why": "element is not a single marked-content run"}
- {"op": "artifact running heads, introduction (10863, 0)", "why": "element is not a single marked-content run"}
- {"op": "artifact running heads, introduction (10861, 0)", "why": "element is not a single marked-content run"}
- {"op": "artifact running heads, chapter one (10859, 0)", "why": "element is not a single marked-content run"}
- {"op": "artifact running heads, chapter one (10857, 0)", "why": "element is not a single marked-content run"}
- {"op": "artifact running heads, index (5288, 0)", "why": "element is not a single marked-content run"}
- {"op": "artifact running heads, index (5286, 0)", "why": "element is not a single marked-content run"}
- {"op": "artifact running heads, index of poems (5284, 0)", "why": "element is not a single marked-content run"}
- {"op": "artifact running heads, index of poems (5282, 0)", "why": "element is not a single marked-content run"}
- {"where": "move_section", "item": {"pages": [94, 94], "before_page": 97, "why": "Table 1 container is read after the main text; return it to its place in printed order"}, "why": "the audit finds no section read out of place in these pages or where it lands"}
- {"where": "move_section", "item": {"pages": [95, 95], "before_page": 97, "why": "Table 2 container is read after the main text"}, "why": "the audit finds no section read out of place in these pages or where it lands"}
- {"where": "move_section", "item": {"pages": [96, 96], "before_page": 97, "why": "Table 3 container is read after the main text"}, "why": "the audit finds no section read out of place in these pages or where it lands"}

## What Was Changed

| Change | Count |
|---|---:|
| document: marked as tagged | 1 |
| document: DisplayDocTitle | 2 |
| artifact: "drop folios" | 5 |
| artifact: "running heads, acknowledgments" | 1 |
| artifact: "running heads, introduction" | 2 |
| artifact: "running heads, chapter one" | 2 |
| artifact: "notes running heads and page numbers" | 28 |
| artifact: "running heads, index" | 2 |
| artifact: "running heads, index of poems" | 2 |
| document: title | 1 |
| document: /Lang | 1 |
| document: empty AcroForm removed | 1 |
| heading: RoleMap level | 5 |
| heading: merged into next | 7 |
| heading: merged into prev | 1 |
| heading: ActualText | 8 |
| heading: standard tag H1 → H3 (retyped) | 58 |
| retype → H1 | 1 |
| retype → H4 | 3 |
| table: header cells marked (work order) | 8 |
| table: caption made from the title rows | 3 |
| table: note row → paragraph after the table | 1 |
| figure: alt text | 1 |
| contents: TOC entries | 11 |
| contents: TOC built | 1 |
| notes: Note with /ID | 411 |
| links: /Contents set | 1648 |
| links: new Link element created | 31 |
| links: wraps its text | 19 |
| links: placed after shared text | 5 |
| links: note reference wrapped | 1 |
| links: joined existing Link | 1617 |
| links: placed beside nearest text | 6 |
| contents: entry wrapped in Reference | 10 |
| order: empty container removed | 5 |
| figure: whole page wrapped as one Figure | 2 |
| figure: alt text from the work order (page figure) | 2 |
| structure: empty tag removed (proven empty) | 1 |
| artifact: untagged path with no content (rule, border, line) | 47 |
| tag tree index: entries repaired | 2 |
| tab order: /Tabs /S set on pages with annotations | 194 |

## Accessibility Evaluation

A person evaluates this version of `teika_remediated.pdf` with PAC 2026 and a screen reader, on the app's "Accessibility Evaluation" page (or with manual_checks.py; docs/release.md). The "Ready to ship?" answer needs both parts. A Fail is recorded with its note and does not hold the book back. Each result is recorded against this version of the PDF (its sha256): after a new apply it no longer counts. The evaluation is a record of what a person found, not a legal certification.

**PAC 2026.** Open `teika_remediated.pdf` in PAC 2026 (https://pac.pdf-accessibility.org/en, Windows) and run its WCAG check. Anything it fails that is not listed above is a gap in the automated checks: note it in the issue tracker. Each item is Pass, Fail or Not Applicable, with notes:

- PAC 2026: WCAG Check: PAC 2026's WCAG check on this version of the PDF. Anything it fails that the report does not list is a gap in the automated checks.
- Title and Language: The title shown in the window is the book's title, and the document language is the book's main language.
- Spot-Check of Pages: A few pages compared with the original in PAC's structure preview: headings, lists, tables and figures as printed.
- Color Alone: No information is given by color alone (WCAG 1.4.1).
- Contrast: Text over images and colored backgrounds has enough contrast (WCAG 1.4.3; PAC's contrast checker).
- Images of Text: No images of text where real text could be used; on scanned pages the OCR text stands in (WCAG 1.4.5).
- What Needs a Person: Every item the report lists under "For a Person to Check" was looked at.

**Screen-reader test.** Listen with a screen reader and record which one and its version:

- Title Announced: The screen reader announces the book's title when the PDF opens.
- Document Language and Passages in Other Languages: The text is read in the book's language, and passages in another language are pronounced in theirs (WCAG 3.1.1, 3.1.2).
- Heading Navigation: Moving by heading reaches each part and chapter, at the right level (WCAG 1.3.1, 2.4.6).
- Reading Order on Sample Pages: On a few sample pages, the text is read in the order it is meant to be read (WCAG 1.3.2).
- Figure Alt Text: Each figure's alt text is read, is accurate and gives its purpose; decorative images are skipped (WCAG 1.1.1).
- Tables Read with Their Headers: Moving through a table, each cell is read with its row or column header (WCAG 1.3.1).
- Links Say Where They Go: Each link's text, or its description, says where it goes (WCAG 2.4.4).
- Lists: Lists are announced as lists, with their number of items.
- OCR Pages Read Sensibly: Pages whose text comes from OCR are read as words, not as junk characters.
- Formulas: Each formula is read with the description a person wrote, or is marked for one (math goes to a person).
