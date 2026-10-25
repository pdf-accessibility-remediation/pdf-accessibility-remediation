# Remediation review: godzone.pdf

Result: `godzone_remediated.pdf`

217 pages · run 2026-10-25T02:50:52 · model `anthropic/claude-sonnet-5.5` · prompt `workorder_v8.md` (4555d20a2fa08a40) · cost: call did not finish · tokens: call did not finish

Intake: none (already tagged)

Libraries: python 3.14.4 · pikepdf 10.5.1 · pdfplumber 0.11.9 · pypdfium2 5.7.1 · pillow 13.0.0 · fonttools 4.62.1

Time: intake 0.3s · audit 28.9s · reuse saved reply 1.2s · apply 18.2s · verify 24.1s · total 72.7s

## Overview

[Open the dashboard](review.html)

**Ready to ship?** No
- Work order approved on the review page: no (run without REVIEW=1)
- OCR text approved: not needed (intake added no OCR text)
- Safety checks: OK
- Manual check (PAC): not run

**Safety checks:** OK ✔ pages look the same · OK ✔ text unchanged · OK ✔ all content tagged or decoration · OK ✔ tag-tree index points into the tree · OK ✔ every font readable  
**Needs a person:** 6 (4 deferred by the AI · 0 deferred by the executor · 2 CHECK rows)  
**AI decisions:** 26 in the work order, applied without review by a person  
**Fixed automatically (no AI):** links tied and described 281 · bookmarks built 39 · tag-tree index entries 6 · title shown in the window 2 · empty tags removed 2 · Document root 1  
**veraPDF (WCAG 2.2 machine checks):** 5 WCAG rules failing before (14,150 checks) → 0 after (0 checks) · 0 newly failing

Automated checks are evidence, not sign-off.

| Top issues | Pages | Where |
|---|---|---|
| Empty tags removed when proven empty: 2 removed · 1 kept: something refers to them or they carry an attribute (listed) | see §7 | [§7](#7-empty-tags-2-removed-1-kept) |
| No empty tags: 1 empty tag (page: not on this tag) | see §7 | [§7](#7-empty-tags-2-removed-1-kept) |
| Chapter-number paragraphs (1–8) that open each chapter appear as separate first tagged lines, apparently not… | 8 pages, PDF 33 (printed 14) to PDF 194 (printed 175) | [§11](#11-deferred-by-the-ai) |
| Two lists on page 59 split one three-item enumeration (1)-(3) across two L elements, one item without a label | PDF 59 (printed 40) | [§11](#11-deferred-by-the-ai) |
| Possible running heads/folios in the index (e.g. 'Index 197' as first tagged line) and in other chapters (e.… | PDF 119 (printed 100), PDF 148 (printed 129), PDF 179 (printed 160), PDF 197 (printed 178) | [§11](#11-deferred-by-the-ai) |
| … and 1 more | | §11 |

Automated checks are evidence, not legal sign-off. Items marked **CHECK**, and everything under "For a person to check", need a human.

## Automated checks

| Check | Result | Detail |
|---|---|---|
| Every page looks the same as the original | OK | 0 pages differ |
| Published text unchanged | OK | 0 pages changed |
| All content tagged or marked as decoration | OK | 0 untagged characters · 0 untagged objects |
| Untagged paths: none left | OK | 0 untagged paths |
| Invisible OCR text: every glyph defined | OK | no undefined glyphs in invisible text |
| Page-level figure wrap | OK | no page with only an untagged drawing |
| Empty tags removed when proven empty | **CHECK** | 2 removed · 1 kept: something refers to them or they carry an attribute (listed) |
| Tag-tree index points only into the tree | OK | 0 dangling entries · 0 stale entries (marked content no longer drawn) |
| No empty tables | OK | none |
| No empty tags | **CHECK** | 1 empty tag (page: not on this tag) |
| No paragraph holding only figures | OK | none |
| Every caption grouped with its figure | OK | all grouped |
| No link whose only text is a URL | OK | none |
| Tag tree consistent | OK | 0 missing · 0 mismatched |
| All marked text reachable from the tag tree | OK | 0 orphan runs |
| One Document root | OK | Document 1 |
| Every link tied to its text and described | OK | 0 unresolved · 0 without description · 0 pointing to no annotation |
| No link nested inside another | OK | 0 |
| Headings: no skipped levels | OK | H1 1 · H2 14 · H3 24 |
| Headings: exactly one H1 (the title) | OK | 1 H1 (several H1s usually mean parts or chapters were not demoted) |
| Figures: none with empty or placeholder alt | OK | 3 figures, 0 placeholder |
| Every Note has a unique ID | OK | 0 notes · 0 without ID · 0 duplicate · 0 not in the ID tree |
| Bookmarks present (documents over 9 pages) | OK | 39 bookmarks (built from 39 heading tags) |
| Model reply held one work order | OK | one |
| Executor applied every decision | OK | 0 rejected · 0 failed (listed under "Decisions not applied") |
| Nothing deferred by the executor | OK | 0 deferred (listed under "Deferred by the executor") |
| Fonts: every glyph defined (no .notdef) | OK | none found |
| Fonts: every embedded font program could be read | OK | all read |
| Fonts: embedded and mapped to Unicode | OK | 0 not embedded · 0 without ToUnicode |
| Tab order follows the tag structure on pages with links or other annotations | OK | 0 of 8 pages with annotations lack /Tabs /S |
| Characters with no Unicode value (checklist 3.6) | OK | 0 read-aloud characters with no Unicode value |
| Private-use characters (checklist 3.6) | OK | 0 read-aloud characters with private-use codes |
| Title and language set | OK | "Mapping the Godzone: A Primer on New Zealand Literature and Culture" · en-US |
| veraPDF WCAG 2.2 (machine): no WCAG failures | OK | before: 5 WCAG rules failed (14150 checks) → after: 0 WCAG rules failed (0 checks) (listed under "veraPDF") |
| veraPDF: no rule newly failing or failing more often | OK | 6 fixed · 0 still failing · 0 newly failing |
| Alt text: none like a file name or repeated on many figures (1.1.1) | OK | 0 of 3 figures flagged |
| Tables: every table has header cells (1.3.1) | OK | none without |
| Reading order: no page jumps back up a column (1.3.2) | OK | 0 of 211 pages flagged |
| Title is not a file name or placeholder (2.4.2) | OK | "Mapping the Godzone: A Primer on New Zealand Literature and Culture" |
| Link text: none like "click here" (2.4.4) | OK | 0 generic |
| Headings: none empty, very long or repeated in a row (2.4.6) | OK | 0 empty · 0 long · 0 repeated |

## For a person to check

### 1. Alt text written or changed by the AI (3)

| Page | Before | After |
|---|---|---|
| PDF 1 (printed cover) | — | Front cover of Mapping the Godzone: A Primer on New Zealand Literature and Culture by William J. Schafer. A painting of a small New Zealand town street with weatherboard houses, a red fence, power poles and a water tower under a blue sky with clouds, beside a turquoise Maori-style spiral border on the left. |
| PDF 4 (printed iii) | — | University of Hawai‘i Press logo |
| PDF 9 (printed viii) | — | Outline map of Aotearoa New Zealand showing the North Island and South Island, with places labelled and linked to authors and novels set there: Bay of Islands (Maurice Shadbolt, The House of Strife); Waipu (Fiona Kidman, The Book of Secrets); Taranaki (Shadbolt, Monday's Warriors); Hawera (Ronald Hugh Morrieson, The Scarecrow, Came a Hot Friday, Predicament); Wellington and Marlborough Sound (Ian Wedde, Symmes Hole); Urewera (Barry Crump, Wild Pork and Watercress); Kaimanawa (John Mulgan, Man Alone); Waituhi (Witi Ihimaera, The Matriarch; Shadbolt, Season of the Jew); Oamaru and Dunedin (Janet Frame, To the Is-Land, An Angel at My Table). Hamilton, Rotorua, Christchurch and Invercargill are also marked. |

### 2. Headings

Heading levels by style (as applied):

| Style | Level | How | Elements |
|---|---|---|---:|
| H4 | H3 | retype (standard tag) | 25 |

### 3. Elements retyped by the AI (10)

Check each one is (or is not) a heading as decided.

| Page | Text | Before | After |
|---|---|---|---|
| PDF 2 (printed i) | Mapping the Godzone | H2 | H1 |
| PDF 4 (printed iii) | A Primer on New Zealand Literature and Culture | H3 | P |
| PDF 4 (printed iii) | William J. Schafer | H3 | P |
| PDF 5 (printed iv) | For Martha—little blue penguins, pukeko, tuatara & all | H4 | P |
| PDF 5 (printed iv) | Library of Congress Cataloging-in-Publication Data | H5 | P |
| PDF 8 (printed vii) | Contents | P | H2 |
| PDF 10 (printed ix) | Preface: Sailing to Aotearoa | H3 | H2 |
| PDF 206 (printed 187) | Bibliography | H3 | H2 |
| PDF 210 (printed 191) | Index | P | H2 |
| PDF 217 (printed 198) | About the Author | H3 | H2 |

### 4. Lists and tables

- Flattened table on PDF 5 (printed iv): "culture / William J. Schafer. / p. | cm." (CIP catalog data laid out as a table; it is plain text lines, not a data table)
- Flattened list on PDF 167 (printed 148): "— It’s an interesting story, she said. I prefer Dostoevsky to Truth. (Frame 10)" (dialogue line introduced by a dash, not a list)
- Flattened list on PDF 167 (printed 148): "— The sort of story they put in Truth, she said. On the morning of the tragedy witness saw defendant…" (dialogue lines introduced by a dash, not a list)

### 5. Hidden from screen readers (artifacts)

- 1 decorative elements ("decorative wave ornament on title page") on PDF 4 (printed iii)
- "running head Fishing with Maui": text matching `Fishing with Maui` on PDF 22–28 (printed 3–9)
- "running head Preface": text matching `Preface` on PDF 11 (printed x)

### 6. Reading order changes

Listen through these spots with a screen reader.

- Cover figure moved to the start of the document

### 7. Empty tags (2 removed, 1 kept)

A tag is removed only when proven empty: nothing under it holds content, it carries no Alt, ActualText, E or ID, and nothing in the file refers to it except its parent. Table cells are never removed one by one; a table goes only when every part is empty.

- Removed: 2 P
- 2 of them were empty parts of tables or lists the work order flattened (e.g. cells whose content had been hidden as decoration)
- **Kept, empty: P (page: not on this tag)**, because carries /ID "R9C1"; IDTree "R9C1".

### 8. Tag-tree index entries cleared (6)

Entries that pointed at a tag no longer in the tag tree (left by the source file, or by a tag the run removed). Nothing reads such a tag; no page, text or reachable tag changed.

- IDTree: "AD260915-1612-26.2.21931-ADBE-000000091491" (Figure), "AD260915-1612-26.2.21931-ADBE-000000091660" (P), "AD260915-1612-26.2.21931-ADBE-000000091936" (P), "AD260915-1612-26.2.21931-ADBE-000000091998" (P), "AD260915-1612-26.2.21931-ADBE-000000092055" (P), "AD260915-1612-26.2.21931-ADBE-000000092112" (P)

### 9. Structure left for a person

- 1 empty tag: P (page: not on this tag)

### 10. veraPDF (WCAG 2.2 machine profile), before and after

veraPDF 1.30.3, profile "WCAG 2.2 machine validation profile" (7da399cf5baa). Counts are failed checks; pages are from the first checks veraPDF lists for each rule, so a rule may fail on more pages. Rules that only PDF/UA requires are listed apart and do not count. "Who fixes" is who can act on the rule: the pipeline by itself, the AI through the work order, or only a person. **Newly failing** means this run broke something the original passed. Before: 5 rules failing (the AI can act on 3, the pipeline on 2, only a person on 0). After: 0.

| Rule | WCAG | What it checks | Who fixes | Before | After | Status | Pages (after, else before) |
|---|---|---|---|---:|---:|---|---|
| ISO 14289-1 7.2-34 | 3.1.1 | Natural language for text in page content shall be determined | the AI (`document`) | 12960 | 0 | fixed | PDF 2 (printed i), PDF 4 (printed iii), PDF 5 (printed iv) |
| ISO 14289-1 7.2-21 | 3.1.1, 3.1.2 | Natural language for text in ActualText attribute shall be determined | the AI (`document`) | 904 | 0 | fixed | PDF 6 (printed v), PDF 10 (printed ix), PDF 11 (printed x), PDF 12 (printed xi), PDF 13 (printed xii) |
| ISO 14289-1 7.18.5-1 | 2.4.4, 4.1.2 | Links shall be tagged according to ISO 32000-1:2008, 14.8.4.4.2, Link Element | the pipeline | 281 | 0 | fixed | PDF 8 (printed vii), PDF 210 (printed 191) |
| ISO 14289-1 7.3-1 | 1.1.1 | Figure tags shall include an alternative representation or replacement text that represents the contents marked with the Figure tag as noted in ISO 32000-1:2008, 14.7.2, Table 323 | the AI (`alt`) | 4 | 0 | fixed | PDF 1 (printed cover), PDF 4 (printed iii), PDF 9 (printed viii) |
| ISO 14289-1 7.1-10 | 2.4.2 | The document catalog dictionary shall include a ViewerPreferences dictionary containing a DisplayDocTitle key, whose value shall be true | the pipeline (1 changed) | 1 | 0 | fixed | page: not on this tag |

### 11. Deferred by the AI

- **Chapter-number paragraphs (1–8) that open each chapter appear as separate first tagged lines, apparently not part of the chapter heading**: The digest gives no obj for them, so I cannot safely merge or retype them; a person should check that they are folded into or placed with the chapter titles [PDF 33 (printed 14), PDF 56 (printed 37), PDF 75 (printed 56), PDF 112 (printed 93), PDF 135 (printed 116), PDF 156 (printed 137), PDF 179 (printed 160), PDF 194 (printed 175)]
- **Two lists on page 59 split one three-item enumeration (1)-(3) across two L elements, one item without a label**: Unclear how the author intended the list; kept as lists for a person to check [PDF 59 (printed 40)]
- **Possible running heads/folios in the index (e.g. 'Index 197' as first tagged line) and in other chapters (e.g. page 119 'Concepts of Holy War', 148, 179 headings) were not artifacted**: Cannot tell from the digest whether they are running heads or real headings [PDF 119 (printed 100), PDF 148 (printed 129), PDF 179 (printed 160), PDF 197 (printed 178)]
- **Chapter running heads other than 'Fishing with Maui' (pages 22–28) not identified**: repeated_lines lists only one pattern [PDF 22 (printed 3), PDF 28 (printed 9)]

Reviewer note from the AI: Outline: H1 = book title (half-title, PDF 2); chapters, Contents, Preface, Bibliography, Index and About the Author = H2; the former H4 section heads = H3. Title-page lines, dedication and CIP label were demoted to P. The CIP table and two dialogue 'lists' were flattened. The wave ornament on PDF 4 is artifacted. Document language set to en-US, which should resolve the language failures (veraPDF 7.2-34, 7.2-21, 7.2-33). Alt text was added for the cover, press logo and map (veraPDF 7.3-1). The existing TOC/TOCI structure was left as is.

## What was changed

| Change | Count |
|---|---:|
| document: Document root created | 1 |
| document: DisplayDocTitle | 2 |
| artifact: "decorative wave ornament on title page" | 1 |
| artifact: "running head Preface" | 1 |
| artifact: "running head Fishing with Maui" | 4 |
| document: title | 1 |
| document: /Lang | 1 |
| heading: standard tag H4 → H3 (retyped) | 25 |
| retype → H1 | 1 |
| retype → P | 4 |
| retype → H2 | 5 |
| flatten: false table → paragraphs | 1 |
| flatten: false list → paragraphs | 1 |
| flatten: nested list/table already flattened with its parent | 1 |
| figure: alt text | 3 |
| links: /Contents set | 281 |
| links: joined existing Link | 2 |
| links: new Link element created | 279 |
| links: placed after shared text | 279 |
| structure: empty tag removed (proven empty) | 2 |
| bookmarks: built from heading tags | 39 |
| tag tree index: entries pointing outside the tree removed (IDTree) | 6 |

## Final check with PAC 2026

Open `godzone_remediated.pdf` in PAC 2026 (https://pac.pdf-accessibility.org/en, Windows) and run its WCAG check. Anything it fails that is not listed above is a gap in the automated checks: note it in the issue tracker.

No automated check here covers these WCAG 2.2 AA criteria; check them by hand, with PAC's screen-reader and structure previews:

- 1.1.1: alt text is accurate and gives the figure's purpose; decorative images are artifacts
- 1.3.1 / 1.3.2: headings, lists and tables match what is printed, and the reading order makes sense
- 1.4.1: no information is given by colour alone
- 1.4.3: contrast of text over images and coloured backgrounds (PAC's contrast checker)
- 1.4.5: no images of text where real text could be used (scanned pages: the OCR layer stands in)
- 2.4.6: headings describe their section
- 3.1.2: passages in another language carry their language (see `han_review.csv` if present)
