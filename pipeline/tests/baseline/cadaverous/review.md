# Remediation review: cadaverous.pdf

Result: `cadaverous_remediated.pdf`

323 pages · run 2026-10-25T03:55:40 · model `anthropic/claude-sonnet-5.5` · prompt `workorder_v8.md` (4555d20a2fa08a40) · cost $0 (saved reply reused, no new call) · tokens: saved reply reused, not counted

Intake: none (already tagged)

Libraries: python 3.14.4 · pikepdf 10.5.1 · pdfplumber 0.11.9 · pypdfium2 5.7.1 · pillow 13.0.0 · fonttools 4.62.1

Time: intake 1.1s · audit 60.6s · reuse saved reply 1.1s · apply 68.8s · verify 61.8s · total 193.4s

## Overview

[Open the dashboard](review.html)

**Ready to ship?** No
- Work order approved on the review page: no (run without REVIEW=1)
- OCR text approved: not needed (intake added no OCR text)
- Safety checks: OK
- Manual check (PAC): not run

**Safety checks:** OK ✔ pages look the same · OK ✔ text unchanged · OK ✔ all content tagged or decoration · OK ✔ tag-tree index points into the tree · OK ✔ every font readable  
**Needs a person:** 7 (6 deferred by the AI · 1 deferred by the executor · 0 CHECK rows)  
**AI decisions:** 71 in the work order, applied without review by a person  
**Fixed automatically (no AI):** links tied and described 3,252 · note IDs 713 · link descriptions that were only a URL 6 · figures moved to their page 3 · tag-tree index entries 2 · title shown in the window 1 · Document root 1  
**veraPDF (WCAG 2.2 machine checks):** 1 WCAG rule failing before (1,793 checks) → 0 after (0 checks) · 0 newly failing

Automated checks are evidence, not sign-off.

| Top issues | Pages | Where |
|---|---|---|
| 1475 Han-only runs need Japanese or Chinese (han_review.csv) | 227 pages, PDF 7 (printed v) to PDF 305 (printed 289) | [§13](#13-deferred-by-the-executor) |
| Drop caps at the start of chapter and section openings (dev_let paragraphs, e.g. "his project began…" for "T… | 10 pages, PDF 11 (printed ix) to PDF 246 (printed 230) | [§12](#12-deferred-by-the-ai) |
| The Index (1793 Index elements at the tree root) and the Link elements at the root are moved into the Docume… | PDF 307 (printed 291), PDF 321 (printed 305) | [§12](#12-deferred-by-the-ai) |
| Han-only Chinese-character runs, such as the mantra on the dedication page and many terms in the text, notes… | PDF 7 (printed v), PDF 17 (printed 1), PDF 284 (printed 268), PDF 323 (printed 307) | [§12](#12-deferred-by-the-ai) |
| The text layer has quirks that suggest hyphenation or italic extraction problems (suspect-token rate 23.8 pe… | 8 pages, PDF 152 (printed 136) to PDF 318 (printed 302) | [§12](#12-deferred-by-the-ai) |
| … and 2 more | | §12 |

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
| Empty tags removed when proven empty | OK | 0 removed |
| Tag-tree index points only into the tree | OK | 0 dangling entries · 719 stale entries (marked content no longer drawn) |
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
| Headings: no skipped levels | OK | H1 1 · H2 18 · H3 50 · H4 17 |
| Headings: exactly one H1 (the title) | OK | 1 H1 (several H1s usually mean parts or chapters were not demoted) |
| Figures: none with empty or placeholder alt | OK | 12 figures, 0 placeholder |
| Every Note has a unique ID | OK | 713 notes · 0 without ID · 0 duplicate · 0 not in the ID tree · 141 empty Note tags removed |
| Bookmarks present (documents over 9 pages) | OK | 17 bookmarks |
| Model reply held one work order | OK | one |
| Executor applied every decision | OK | 0 rejected · 0 failed (listed under "Decisions not applied") |
| Nothing deferred by the executor | **CHECK** | 1 deferred (listed under "Deferred by the executor") |
| Fonts: every glyph defined (no .notdef) | OK | none found |
| Fonts: every embedded font program could be read | OK | all read |
| Fonts: embedded and mapped to Unicode | OK | 0 not embedded · 0 without ToUnicode |
| Tab order follows the tag structure on pages with links or other annotations | OK | 0 of 250 pages with annotations lack /Tabs /S |
| Characters with no Unicode value (checklist 3.6) | OK | 0 read-aloud characters with no Unicode value |
| Private-use characters (checklist 3.6) | OK | 0 read-aloud characters with private-use codes |
| Title and language set | OK | "Cadaverous: Postmortem Contagion and Ritual Immunity in Medieval Japanese Buddhism" · en-US |
| veraPDF WCAG 2.2 (machine): no WCAG failures | OK | before: 1 WCAG rule failed (1793 checks) → after: 0 WCAG rules failed (0 checks) (listed under "veraPDF") |
| veraPDF: no rule newly failing or failing more often | OK | 2 fixed · 0 still failing · 0 newly failing |
| Alt text: none like a file name or repeated on many figures (1.1.1) | OK | 0 of 12 figures flagged |
| Tables: every table has header cells (1.3.1) | OK | none without |
| Reading order: no page jumps back up a column (1.3.2) | OK | 0 of 288 pages flagged |
| Title is not a file name or placeholder (2.4.2) | OK | "Cadaverous: Postmortem Contagion and Ritual Immunity in Medieval Japanese Buddhism" |
| Link text: none like "click here" (2.4.4) | OK | 0 generic |
| Headings: none empty, very long or repeated in a row (2.4.6) | OK | 0 empty · 0 long · 0 repeated |

## For a person to check

### 1. Alt text written or changed by the AI (2)

| Page | Before | After |
|---|---|---|
| PDF 1 (printed A) | Book cover for Cadaverous: Postmortem Contagion and Ritual Immunity in Medieval Japanese Buddhism by Andrew Macomber. The cover features a brown-toned sketch illustration of a human corpse from head to pelvis in an advanced state of decomposition, showing exposed internal organs and skeletal elements. The background has a mottled, parchment-like texture. The title and the author's name appear in dark colored text above and below the image.\x00 | Book cover of Cadaverous: Postmortem Contagion and Ritual Immunity in Medieval Japanese Buddhism by Andrew Macomber. A brown-toned sketch of a decomposing human corpse lying on its back with long hair and exposed ribs, on a mottled parchment-colored background. The title appears above the image and the author's name below it. |
| PDF 5 (printed iii) | Illustration | University of Hawai‘i Press logo |

### 2. Figures that kept their existing alt text (10)

Not changed by the AI. Check they are adequate.

| Page | Alt text |
|---|---|
| PDF 62 (printed 46) | statue of the wrathful deity Fudo Myoo sitting. |
| PDF 66 (printed 50) | statue of the bodhisattva Senju Kannon standing. |
| PDF 124 (printed 108) | painting of the monk Zoyo performing healing prayers for his patient, Tadazane. |
| PDF 142 (printed 126) | illustration of a ritual altar mandala in a manuscript for the Ritual for Expelling Demons. |
| PDF 144 (printed 128) | first section of a scroll manuscript for the Ritual for Expelling Demons, written in classical Chinese. |
| PDF 152 (printed 136) | hanging scroll of the wrathful deity Shomen Kongō. |
| PDF 160 (printed 144) | an illustration of the decomposing corpse of a woman. |
| PDF 218 (printed 202) | a line illustration of the back of a male body for moxibustion treatment. |
| PDF 218 (printed 202) | a line illustration of the front of a male body for moxibustion treatment. |
| PDF 239 (printed 223) | painting of a village doctor in Song China applying moxibustion to a patient who is screaming. |

### 3. Headings

Heading levels by style (as applied):

| Style | Level | How | Elements |
|---|---|---|---:|
| pre_tit | H2 | RoleMap | 3 |
| pre_tit.autre | H2 | RoleMap | 1 |
| part_n | H2 | RoleMap | 2 |
| part_tit | H2 | RoleMap | 2 |
| chap_n | H2 | RoleMap | 7 |
| chap_tit | H2 | RoleMap | 1 |
| chap_tit.seul | H2 | RoleMap | 5 |
| chap_tit.autre | H2 | RoleMap | 1 |
| chap_stit | H2 | RoleMap | 1 |
| appen_tit | H2 | RoleMap | 4 |
| appen_tit.autre | H2 | RoleMap | 1 |
| dev_int1 | H3 | RoleMap | 37 |
| dev_int1.autre | H3 | RoleMap | 2 |
| dev_int1.biblio | H3 | RoleMap | 2 |
| nfniv1_int | H3 | RoleMap | 9 |
| dev_int2 | H4 | RoleMap | 17 |

Merged: `part_n` into the next `part_tit`; `chap_n` into the next `chap_tit.seul/chap_tit/chap_tit.autre`; `chap_stit` into the prev `chap_tit.autre`

Spoken text set by the AI (should match what is printed):

| Page | Text |
|---|---|
| PDF 5 (printed iii) | Cadaverous |
| PDF 47 (printed 31) | Part I Spirit Disease |
| PDF 49 (printed 33) | Chapter 1 Ritual Healing in the Jimon Lineage |
| PDF 78 (printed 62) | Chapter 2 Evil Dead in the Aristocratic Mansion |
| PDF 112 (printed 96) | Chapter 3 The Ghostbusters of Onjōji |
| PDF 139 (printed 123) | Part II Corpse Disease |
| PDF 141 (printed 125) | Chapter 4 The Ritual of Shōmen Kongō for Expelling Demons and Māras |
| PDF 154 (printed 138) | Chapter 5 Corpse Influx in a Defiled Capital |
| PDF 182 (printed 166) | Chapter 6 Demons, Māras, and Corpse-Worms |
| PDF 211 (printed 195) | Chapter 7 Playing with Fire Therapeutic Violence Through Ritual Pyrotechnics |

### 4. Elements retyped by the AI (1)

Check each one is (or is not) a heading as decided.

| Page | Text | Before | After |
|---|---|---|---|
| PDF 5 (printed iii) | Cadaverous | ident_tit | H1 |

### 5. Hidden from screen readers (artifacts)

- 16 decorative elements ("ornament") on PDF 9 (printed vii), PDF 11 (printed ix), PDF 15 (printed xiii), PDF 17 (printed 1), PDF 49 (printed 33), PDF 78 (printed 62), PDF 112 (printed 96), PDF 141 (printed 125), PDF 154 (printed 138), PDF 182 (printed 166), PDF 211 (printed 195), PDF 246 (printed 230), PDF 253 (printed 237), PDF 283 (printed 267), PDF 307 (printed 291), PDF 323 (printed 307)
- "running head (Notes to Pages)": text matching `Notes to Pages? [\d–]+` on PDF 254–282 (printed 238–266)

### 6. Reading order changes

Listen through these spots with a screen reader.

- Cover figure moved to the start of the document
- Figure on PDF 144 (printed 128) moved to read with its page (it read after PDF 153 (printed 137); now after PDF 145 (printed 129))
- Figure on PDF 152 (printed 136) moved to read with its page (it read after PDF 282 (printed 266); now after PDF 153 (printed 137))
- Figure on PDF 160 (printed 144) moved to read with its page (it read after PDF 181 (printed 165); now after PDF 161 (printed 145))

### 7. Spoken text (ActualText) checked against the print (9 accepted with differences, 0 rejected)

A spoken text may differ from the printed characters only in spacing, letter case and line-end hyphens (sponsor rule 1). Accepted ones that differ are listed so a person can listen to them; rejected ones added or changed words or punctuation.

- Accepted, PDF 47 (printed 31): printed "Part I Spirit Disease" → spoken "Part I Spirit Disease"
- Accepted, PDF 49 (printed 33): printed "ChaPter 1 Ritual Healing in the Jimon Lineage" → spoken "Chapter 1 Ritual Healing in the Jimon Lineage"
- Accepted, PDF 78 (printed 62): printed "ChaPter 2 Evil Dead in the Aristocratic Mansion" → spoken "Chapter 2 Evil Dead in the Aristocratic Mansion"
- Accepted, PDF 112 (printed 96): printed "ChaPter 3 The Ghostbusters of Onjōji" → spoken "Chapter 3 The Ghostbusters of Onjōji"
- Accepted, PDF 139 (printed 123): printed "Part II Corpse Disease" → spoken "Part II Corpse Disease"
- Accepted, PDF 141 (printed 125): printed "ChaPter 4 The Ritual of Shōmen Kongō for Expelling Demons and Māras" → spoken "Chapter 4 The Ritual of Shōmen Kongō for Expelling Demons and Māras"
- Accepted, PDF 154 (printed 138): printed "ChaPter 5 Corpse Influx in a Defiled Capital" → spoken "Chapter 5 Corpse Influx in a Defiled Capital"
- Accepted, PDF 182 (printed 166): printed "ChaPter 6 Demons, Māras, and Corpse-Worms" → spoken "Chapter 6 Demons, Māras, and Corpse-Worms"
- Accepted, PDF 211 (printed 195): printed "ChaPter 7 Playing with Fire Therapeutic Violence Through Ritual Pyrotechnics" → spoken "Chapter 7 Playing with Fire Therapeutic Violence Through Ritual Pyrotechnics"

### 8. Links whose description was only a URL (6, and 2 addresses that look broken)

The description (what a screen reader announces) was set to the book's own sentence around the link, with the URL removed. No words were added and the visible URL is unchanged. Replace any of these with a better description if needed.

| Page | URL | Description now |
|---|---|---|
| PDF 6 (printed iv) | https://lccn.loc.gov/2025039144 | LC record available at |
| PDF 6 (printed iv) | https://lccn.loc.gov/2025039145 | LC ebook record available at |
| PDF 6 (printed iv) | https://colbase.nich.go.jp/collection_items/kyuhaku/A70) | ColBase. |
| PDF 160 (printed 144) | https://colbase.nich.go.jp/collection_items/kyuhaku/A70) | Figure 7. Detail from Kusō zukan. Fourteenth century. Kyushu National Museum. Source: ColBase. |
| PDF 284 (printed 268) | http://www.buddhism-dict.net/ddb/ | Digital Dictionary of Buddhism. |
| PDF 286 (printed 270) | https://japanknowledge.com/ | Japan Knowledge |

Link addresses that look broken (listed, not changed):

- PDF 6 (printed iv): `https://colbase.nich.go.jp/collection_items/kyuhaku/A70)`: the address ends with punctuation or an unmatched closing bracket from the printed text; probably broken
- PDF 160 (printed 144): `https://colbase.nich.go.jp/collection_items/kyuhaku/A70)`: the address ends with punctuation or an unmatched closing bracket from the printed text; probably broken

### 9. Tag-tree index entries cleared (2)

Entries that pointed at a tag no longer in the tag tree (left by the source file, or by a tag the run removed). Nothing reads such a tag; no page, text or reachable tag changed.

- ParentTree, entries not tied to page content (annotations, forms, or keys nothing uses): key 30 (Link), key 40 (Link)

### 10. Figure holders

- PDF 218 (printed 202): caption grouped with the 2 figures in the holder just above it: "Figure 8. Denshibyō kanjin shō narabini sōbyō chihō. Manuscript. Detail of body chart (front and…"

### 11. veraPDF (WCAG 2.2 machine profile), before and after

veraPDF 1.30.3, profile "WCAG 2.2 machine validation profile" (7da399cf5baa). Counts are failed checks; pages are from the first checks veraPDF lists for each rule, so a rule may fail on more pages. Rules that only PDF/UA requires are listed apart and do not count. "Who fixes" is who can act on the rule: the pipeline by itself, the AI through the work order, or only a person. **Newly failing** means this run broke something the original passed. Before: 1 rule failing (the AI can act on 0, the pipeline on 1, only a person on 0). After: 0.

| Rule | WCAG | What it checks | Who fixes | Before | After | Status | Pages (after, else before) |
|---|---|---|---|---:|---:|---|---|
| ISO 14289-1 7.18.5-1 | 2.4.4, 4.1.2 | Links shall be tagged according to ISO 32000-1:2008, 14.8.4.4.2, Link Element | the pipeline | 1793 | 0 | fixed | PDF 307 (printed 291) |

### 12. Deferred by the AI

- **Drop caps at the start of chapter and section openings (dev_let paragraphs, e.g. "his project began…" for "This project began…") are extracted without their first letter or as a separate run. A person should check how the first word is read.**: The digest does not show the drop-cap runs, so ActualText for these paragraphs cannot be written safely. [PDF 11 (printed ix), PDF 17 (printed 1), PDF 49 (printed 33), PDF 78 (printed 62), PDF 112 (printed 96), PDF 141 (printed 125), PDF 154 (printed 138), PDF 182 (printed 166), PDF 211 (printed 195), PDF 246 (printed 230)]
- **The Index (1793 Index elements at the tree root) and the Link elements at the root are moved into the Document by the executor. Check that the index reads after the bibliography in the right order.**: The digest does not show where in the Document they will land. [PDF 307 (printed 291), PDF 321 (printed 305)]
- **Han-only Chinese-character runs, such as the mantra on the dedication page and many terms in the text, notes and bibliography, are ambiguous between Japanese and Chinese.**: Left to the executor's automatic deferral; a human must set the language. [PDF 7 (printed v), PDF 17 (printed 1), PDF 284 (printed 268), PDF 323 (printed 307)]
- **The text layer has quirks that suggest hyphenation or italic extraction problems (suspect-token rate 23.8 per 1000), for example in notes and bibliography entries such as "O“nmyōji" and "Mak-".**: The text must not be changed here; a person should spot-check these pages. [PDF 152 (printed 136), PDF 262 (printed 246), PDF 267 (printed 251), PDF 270 (printed 254), PDF 275 (printed 259), PDF 285 (printed 269), PDF 294 (printed 278), PDF 318 (printed 302)]
- **veraPDF reports 2 failed rules that are not listed with any work-order key, so they were not addressed.**: pdfua_check.rules is empty, so there is no key or target to act on. [PDF 1 (printed A), PDF 323 (printed 307)]
- **Figure 3, Figure 4 and Figure 5 style frames (dev_fig_img paragraphs) and their captions were tied together by the captions key; check that each caption sits with the correct figure.**: Some captions sit in Story containers at different depths. [PDF 62 (printed 46), PDF 66 (printed 50), PDF 124 (printed 108), PDF 142 (printed 126), PDF 144 (printed 128), PDF 152 (printed 136), PDF 160 (printed 144), PDF 218 (printed 202), PDF 239 (printed 223)]

Reviewer note from the AI: The publisher's rolemap mapped nearly every title style to H1. I made the half-title-page book title (ident_tit, PDF 5 (printed iii)) the only H1. Part, chapter, front-matter and back-matter titles are H2. Part and chapter number labels are merged into their titles, and the Chapter 7 subtitle is merged into its title. Section heads are H3 and subsections are H4. The notes chapter heads (nfniv1_int) and the bibliography heads are H3. Existing alt text on the content figures was kept. The 16 decorative flourishes near chapter titles are artifacted. The cover figure at the root had a NUL character in its alt text, which I replaced, and I moved the cover to the start of the Document. The Notes running heads are artifacted on PDF 254–282 (printed 238–266).

### 13. Deferred by the executor

- **1475 Han-only CJK runs** need a Japanese / Chinese decision: fill in `han_review.csv`.

## What was changed

| Change | Count |
|---|---:|
| artifact: "ornament" | 16 |
| artifact: "running head (Notes to Pages)" | 29 |
| document: title | 1 |
| document: DisplayDocTitle | 1 |
| document: /Lang | 1 |
| heading: RoleMap level | 16 |
| heading: merged into next | 9 |
| heading: merged into prev | 1 |
| heading: ActualText | 10 |
| retype → H1 | 1 |
| figure: alt text | 2 |
| figure: moved into Document, first | 1 |
| figure: caption tied (figure moved out of its paragraph) | 3 |
| figure: caption tied (figure holder just before it → Div) | 6 |
| list: built | 1 |
| contents: TOC entries | 16 |
| contents: TOC built | 1 |
| notes: empty Note shell removed | 141 |
| notes: Note with /ID | 713 |
| language: ja Span | 177 |
| links: /Contents set | 3252 |
| links: joined existing Link | 735 |
| links: placed after shared text | 1888 |
| links: wraps its text | 625 |
| links: note reference wrapped | 4 |
| links: URL-only description replaced by the sentence around it | 6 |
| order: figure moved to its page | 3 |
| contents: annotation-less Link → Span | 24 |
| contents: entry wrapped in Reference | 16 |
| order: empty container removed | 29 |
| tag tree index: entries pointing outside the tree cleared (ParentTree) | 2 |

## Final check with PAC 2026

Open `cadaverous_remediated.pdf` in PAC 2026 (https://pac.pdf-accessibility.org/en, Windows) and run its WCAG check. Anything it fails that is not listed above is a gap in the automated checks: note it in the issue tracker.

No automated check here covers these WCAG 2.2 AA criteria; check them by hand, with PAC's screen-reader and structure previews:

- 1.1.1: alt text is accurate and gives the figure's purpose; decorative images are artifacts
- 1.3.1 / 1.3.2: headings, lists and tables match what is printed, and the reading order makes sense
- 1.4.1: no information is given by colour alone
- 1.4.3: contrast of text over images and coloured backgrounds (PAC's contrast checker)
- 1.4.5: no images of text where real text could be used (scanned pages: the OCR layer stands in)
- 2.4.6: headings describe their section
- 3.1.2: passages in another language carry their language (see `han_review.csv` if present)
