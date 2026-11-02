# Remediation review: translation.pdf

Result: `translation_remediated.pdf`

257 pages · run 2026-11-01T18:33:09 · model `anthropic/claude-sonnet-5.5` · prompt `workorder_v10.md` (15b5aa0ade9c6549) · cost $0 (saved reply reused, no new call) · tokens: saved reply reused, not counted

Intake: none (already tagged)

Libraries: python 3.14.8 · pikepdf 10.5.1 · pdfplumber 0.11.9 · pypdfium2 5.7.1 · pillow 13.0.0 · fonttools 4.62.1

Time: intake 0.8s · audit 37.8s · reuse saved reply 0.4s · apply 81.7s · verify 49.5s · total 170.2s

## Overview

[Open the dashboard](review.html)

**Ready to ship?** No
- Work order approved on the review page: no (run without REVIEW=1)
- OCR text approved: not needed (intake added no OCR text)
- Safety checks: OK
- Manual check (PAC): not run

**Safety checks:** OK ✔ pages look the same · OK ✔ text unchanged · OK ✔ all content tagged or decoration · OK ✔ tag-tree index points into the tree · OK ✔ every font readable  
**Needs a person:** 9 (6 deferred by the AI · 1 deferred by the executor · 2 CHECK rows)  
**AI decisions:** 68 in the work order, applied without review by a person  
**Fixed automatically (no AI):** links tied and described 2,822 · decorative lines marked 1,652 · note IDs 824 · pages given tab order 192 · empty tags removed 34 · figures moved to their page 15 · title shown in the window 2 · marked as tagged 1 · whole-page figures wrapped 1 · tag-tree index entries 1  
**veraPDF (WCAG 2.2 machine checks):** 7 WCAG rules failing before (3,953 checks) → 0 after (0 checks) · 0 newly failing

Automated checks are evidence, not sign-off.

| Top issues | Pages | Where |
|---|---|---|
| Private-use characters (checklist 3.6): 5 read-aloud characters with private-use codes (U+F036: 5) on 1 page | see Automated checks | [Automated checks](#automated-checks) |
| Reading order jumps back up a column (7 jumps) | PDF 10 (printed x) | [§13](#13-wcag-checks-verapdf-does-not-make) |
| text rule "invisible filler text (orphan)" matched no text on PDF 1–257 (printed i–236) | see §15 | [§15](#15-deferred-by-the-executor) |
| Invisible filler text 'hn hk io il sy SY ek eh' | 11 pages, PDF 3 (printed iii) to PDF 255 (printed 234) | [§14](#14-deferred-by-the-ai) |
| Reading order of the tag tree | 8 pages, PDF 2 (printed ii) to PDF 244 (printed 223) | [§14](#14-deferred-by-the-ai) |
| … and 4 more | | §14 |

Automated checks are evidence, not legal sign-off. Items marked **CHECK**, and everything under "For a person to check", need a human.

## Automated checks

| Check | Result | Detail |
|---|---|---|
| Every page looks the same as the original | OK | 0 pages differ |
| Published text unchanged | OK | 0 pages changed |
| All content tagged or marked as decoration | OK | 0 untagged characters · 0 untagged objects |
| Untagged paths: none left | OK | 0 untagged paths · 1652 rules, borders and lines marked as decoration by this run |
| Invisible OCR text: every glyph defined | OK | no undefined glyphs in invisible text |
| Page-level figure wrap | OK | PDF 1 (printed i) wrapped as one Figure |
| Empty tags removed when proven empty | OK | 34 removed (11 whole empty tables) |
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
| Headings: no skipped levels | OK | H1 1 · H2 19 · H3 50 |
| Headings: exactly one H1 (the title) | OK | 1 H1 (several H1s usually mean parts or chapters were not demoted) |
| Figures: none with empty or placeholder alt | OK | 19 figures, 0 placeholder |
| Every Note has a unique ID | OK | 824 notes · 0 without ID · 0 duplicate · 0 not in the ID tree |
| Bookmarks present (documents over 9 pages) | OK | 45 bookmarks |
| Model reply held one work order | OK | one |
| Executor applied every decision | OK | 0 rejected · 0 failed (listed under "Decisions not applied") |
| Nothing deferred by the executor | **CHECK** | 1 deferred (listed under "Deferred by the executor") |
| Fonts: every glyph defined (no .notdef) | OK | none found |
| Fonts: every embedded font program could be read | OK | all read |
| Fonts: embedded and mapped to Unicode | OK | 0 not embedded · 0 without ToUnicode |
| Tab order follows the tag structure on pages with links or other annotations | OK | 0 of 192 pages with annotations lack /Tabs /S (log: 192 set by this run) |
| Characters with no Unicode value (checklist 3.6) | OK | 0 read-aloud characters with no Unicode value |
| Private-use characters (checklist 3.6) | **CHECK** | 5 read-aloud characters with private-use codes (U+F036: 5) on 1 page |
| Title and language set | OK | "Found in Translation: Many Meanings on a North Australian Mission" · en-US |
| veraPDF WCAG 2.2 (machine): no WCAG failures | OK | before: 7 WCAG rules failed (3953 checks) → after: 0 WCAG rules failed (0 checks) (listed under "veraPDF") |
| veraPDF: no rule newly failing or failing more often | OK | 7 fixed · 0 still failing · 0 newly failing |
| Alt text: none like a file name or repeated on many figures (1.1.1) | OK | 0 of 19 figures flagged |
| Tables: every table has header cells (1.3.1) | OK | none without |
| Reading order: no page jumps back up a column (1.3.2) | **CHECK** | 1 of 228 pages flagged |
| Reading order: no section moved away from its printed place by this run (1.3.2) | OK | 0 new · 0 already in the original, of 22 sections and blocks |
| Title is not a file name or placeholder (2.4.2) | OK | "Found in Translation: Many Meanings on a North Australian Mission" |
| Link text: none like "click here" (2.4.4) | OK | 0 generic |
| Headings: none empty, very long or repeated in a row (2.4.6) | OK | 0 empty · 0 long · 0 repeated |

## For a person to check

### 1. Pages wrapped as one Figure (1)

Pages with nothing tagged and nothing marked as decoration that hold a drawing (a full-page map, plate or cover). Each page was wrapped whole in one Figure; nothing on it was changed or removed.

- PDF 1 (printed i): read first in the document. Alt text from the AI: "Book cover of Found in Translation: Many Meanings on a North Australian Mission by Laura Rademaker. A sepia photograph shows a group of young Anindilyakwa men with two white missionaries, and an old map of Groote Eylandt is at upper left. The title and author's name are printed over the image."

### 2. Alt text written or changed by the AI (18)

| Page | Before | After |
|---|---|---|
| PDF 3 (printed iii) | — | Indigenous Pacifics series logo |
| PDF 4 (printed iv) | — | University of Hawai‘i Press logo |
| PDF 4 (printed iv) | — | University of Hawai‘i Press logo |
| PDF 23 (printed 2) | — | Black-and-white photograph of missionary Alfred Dyer, in a wide-brimmed hat and shorts with hands on hips, standing in open bush beside three Anindilyakwa men seated on the ground. |
| PDF 26 (printed 5) | — | Map of northern Australia showing Groote Eylandt in the Gulf of Carpentaria, east of Arnhem Land, with Darwin, Pine Creek and Katherine marked. An inset shows the location of the region within Australia. |
| PDF 59 (printed 38) | — | Black-and-white photograph, 1928, of a group of Aboriginal girls in light dresses and boys in loincloths, with a few adults, posed outdoors in front of palm trees and a building. |
| PDF 61 (printed 40) | — | Hand-drawn survey map of Groote Eylandt and nearby islands. It shows the Aboriginal Reserve, the Church Missionary Society lease tinted pink, and the area excluded for the Flying Boat Base. A handwritten legend gives the scale as 10 miles to an inch. |
| PDF 71 (printed 50) | — | Black-and-white photograph of Anindilyakwa men pushing a heavy timber frame during construction at Angurugu, while a man in a hat looks through a surveying instrument on a tripod. |
| PDF 84 (printed 63) | — | Plan of the Groote Eylandt Mission Station. A circular road around the church is at the center. Around it are the mission houses, store, boys' and girls' dormitories, school, hospital, maternity block, pump house, saw mill, gardens, playing field and the Native Camp. Rivers run along the top, and a track leads to the air strip. |
| PDF 86 (printed 65) | — | Black-and-white photograph of the Angurugu church in 1951, a large building with a pale roof. Missionaries and Anindilyakwa congregation members stand in a line in front of it. |
| PDF 87 (printed 66) | — | Photograph of a missionary teacher sitting on the ground outdoors and showing a picture board to a circle of Anindilyakwa boys at Sunday school. |
| PDF 88 (printed 67) | — | Black-and-white photograph, 1951, of Anindilyakwa adults and children standing and sitting in front of bush huts in the village. |
| PDF 90 (printed 69) | — | Photograph of Judith Stokes, a smiling woman with short curly hair and glasses, in a sleeveless checked dress, leaning on a veranda rail with trees behind her. |
| PDF 117 (printed 96) | — | Photograph of two Angurugu schoolchildren sitting at wooden desks in a classroom, one looking down at an open book. |
| PDF 137 (printed 116) | — | Photograph of Judith Stokes, Lawrence Jaragba and Gula Lalara seated side by side on chairs against a curtained wall, with a radio behind them. |
| PDF 170 (printed 149) | — | Black-and-white photograph of Johnny, a man in a singlet, sitting on a boat holding a concertina, with a sail, mast and the sea behind him. |
| PDF 171 (printed 150) | — | Black-and-white photograph of two men in a funeral dance for Quartpot in 1968. One wears a feathered headdress and the other has painted decoration. They dance in a clearing with huts and watching people behind them. |
| PDF 189 (printed 168) | — | Detail of the cloth poster 'The 2 Ways'. A broad road leads down to flames on the left, with scenes of drinking, fighting and wrongdoing along the way. A narrow path leads up toward a cross on the right, with a gate marked 'Enter ye in at the strait gate'. Long description: it contrasts the way to destruction with the way to life. |

### 3. Headings

Heading levels by style (as applied):

| Style | Level | How | Elements |
|---|---|---|---:|
| CT | H2 | RoleMap | 9 |
| CTINT | H2 | RoleMap | 1 |
| FMH | H2 | RoleMap | 4 |
| FMHS | H2 | RoleMap | 1 |
| BMH | H2 | RoleMap | 3 |
| ATAH | H2 | RoleMap | 1 |
| ENH | H3 | RoleMap | 10 |
| BMSH | H3 | RoleMap | 2 |
| CST | P | RoleMap | 7 |
| H1 | H3 | retype (standard tag) | 38 |

Merged: `CN` into the next `CT`; `CST` into the prev `CT`

Spoken text set by the AI (should match what is printed):

| Page | Text |
|---|---|
| PDF 34 (printed 13) | 1 MEETINGS New Meanings on Southern Shores |
| PDF 52 (printed 31) | 2 TRANSLATING THE LANDSCAPE Negotiating the Mission |
| PDF 82 (printed 61) | 3 EARS TO HEAR The Sounds of Speech |
| PDF 106 (printed 85) | 4 THE LETTER KILLS Writing in English |
| PDF 129 (printed 108) | 5 THE MAMARIKA WINDS Turning to Anindilyakwa |
| PDF 148 (printed 127) | 6 SPEAKING TO THE HEART The Language of Faith |
| PDF 167 (printed 146) | 7 SINGING IN TONGUES Translation through Song |

### 4. Elements retyped by the AI (1)

Check each one is (or is not) a heading as decided.

| Page | Text | Before | After |
|---|---|---|---|
| PDF 4 (printed iv) | FOUND IN TRANSLATION | TPT | H1 |

### 5. Lists and tables

- Header cells marked by the AI on PDF 27 (printed 6): 1 header row(s), 0 header column(s), 4 cells changed to header cells; 1 title row(s) made the caption, 28 data cell(s) tied to their headers by ID, 2 group row(s). Check they are the real headers.

Tables kept as tables (12): check header cells and reading order.

- PDF 3 (printed iii): 7 rows × 8 columns, 0 header cells. "hn | hk | io | il | sy | SY | ek | eh"
- PDF 13 (printed xiii): 7 rows × 8 columns, 0 header cells. "hn | hk | io | il | sy | SY | ek | eh"
- PDF 23 (printed 2): 7 rows × 8 columns, 0 header cells. "hn | hk | io | il | sy | SY | ek | eh"
- PDF 27 (printed 6): 18 rows × 2 columns, 0 header cells. "Table 1 Anindilyakwa Clans"
- PDF 35 (printed 14): 7 rows × 8 columns, 0 header cells. "hn | hk | io | il | sy | SY | ek | eh"
- PDF 61 (printed 40): 7 rows × 8 columns, 0 header cells. "hn | hk | io | il | sy | SY | ek | eh"
- PDF 129 (printed 108): 7 rows × 8 columns, 0 header cells. "hn | hk | io | il | sy | SY | ek | eh"
- PDF 193 (printed 172): 7 rows × 8 columns, 0 header cells. "hn | hk | io | il | sy | SY | ek | eh"
- PDF 207 (printed 186): 7 rows × 8 columns, 0 header cells. "hn | hk | io | il | sy | SY | ek | eh"
- PDF 247 (printed 226): 7 rows × 8 columns, 0 header cells. "hn | hk | io | il | sy | SY | ek | eh"
- PDF 253 (printed 232): 7 rows × 8 columns, 0 header cells. "hn | hk | io | il | sy | SY | ek | eh"
- PDF 255 (printed 234): 7 rows × 8 columns, 0 header cells. "hn | hk | io | il | sy | SY | ek | eh"

### 6. Text a screen reader could not reach (before this run)

111 pages had text outside the tag tree: 6216 orphan runs (marked, but no tag owns them) and 0 untagged runs. Running heads and page numbers among them can be hidden as decoration; real content must be added to the tag tree by a person. After this run: 0 untagged characters, 0 orphan runs remain.

Pages: PDF 15 (printed xv), PDF 19 (printed xix), PDF 25 (printed 4), PDF 27 (printed 6), PDF 29 (printed 8), PDF 31 (printed 10), PDF 33 (printed 12), PDF 37 (printed 16), PDF 39 (printed 18), PDF 41 (printed 20), PDF 43 (printed 22), PDF 45 (printed 24), PDF 47 (printed 26), PDF 49 (printed 28), PDF 51 (printed 30), PDF 53 (printed 32), PDF 55 (printed 34), PDF 57 (printed 36), PDF 59 (printed 38), PDF 63 (printed 42), PDF 65 (printed 44), PDF 67 (printed 46), PDF 69 (printed 48), PDF 71 (printed 50), PDF 73 (printed 52), PDF 75 (printed 54), PDF 77 (printed 56), PDF 79 (printed 58), PDF 81 (printed 60), PDF 83 (printed 62), PDF 85 (printed 64), PDF 87 (printed 66), PDF 89 (printed 68), PDF 91 (printed 70), PDF 93 (printed 72), PDF 95 (printed 74), PDF 97 (printed 76), PDF 99 (printed 78), PDF 101 (printed 80), PDF 103 (printed 82), PDF 105 (printed 84), PDF 107 (printed 86), PDF 109 (printed 88), PDF 111 (printed 90), PDF 113 (printed 92), PDF 115 (printed 94), PDF 117 (printed 96), PDF 119 (printed 98), PDF 121 (printed 100), PDF 123 (printed 102), PDF 125 (printed 104), PDF 127 (printed 106), PDF 131 (printed 110), PDF 133 (printed 112), PDF 135 (printed 114), PDF 137 (printed 116), PDF 139 (printed 118), PDF 141 (printed 120), PDF 143 (printed 122), PDF 145 (printed 124), PDF 147 (printed 126), PDF 149 (printed 128), PDF 151 (printed 130), PDF 153 (printed 132), PDF 155 (printed 134), PDF 157 (printed 136), PDF 159 (printed 138), PDF 161 (printed 140), PDF 163 (printed 142), PDF 165 (printed 144), PDF 167 (printed 146), PDF 169 (printed 148), PDF 171 (printed 150), PDF 173 (printed 152), PDF 175 (printed 154), PDF 177 (printed 156), PDF 179 (printed 158), PDF 181 (printed 160), PDF 183 (printed 162), PDF 185 (printed 164), PDF 187 (printed 166), PDF 189 (printed 168), PDF 191 (printed 170), PDF 195 (printed 174), PDF 197 (printed 176), PDF 199 (printed 178), PDF 201 (printed 180), PDF 203 (printed 182), PDF 205 (printed 184), PDF 209 (printed 188), PDF 211 (printed 190), PDF 213 (printed 192), PDF 215 (printed 194), PDF 217 (printed 196), PDF 219 (printed 198), PDF 221 (printed 200), PDF 223 (printed 202), PDF 225 (printed 204), PDF 227 (printed 206), PDF 229 (printed 208), PDF 231 (printed 210), PDF 233 (printed 212), PDF 235 (printed 214), PDF 237 (printed 216), PDF 239 (printed 218), PDF 241 (printed 220), PDF 243 (printed 222), PDF 245 (printed 224), PDF 249 (printed 228), PDF 251 (printed 230), PDF 257 (printed 236)

### 7. Hidden from screen readers (artifacts)

- "invisible filler text (tagged)": text matching `(?:(?:hn|hk|io|il|sy|SY|ek|eh) ?)+` on PDF 1–257 (printed i–236)
- "invisible filler text (orphan)": text matching `(?:(?:hn|hk|io|il|sy|SY|ek|eh) ?)+` on PDF 1–257 (printed i–236)
- "running head Preface": text matching `xii Preface|xii|Preface` on PDF 13 (printed xiii)
- "running head Acknowledgments": text matching `Acknowl ?edgments xv|Acknowl ?edgments|xv` on PDF 16 (printed xvi)
- "running head Introduction": text matching `2 Introduction|Introduction 3|Introduction|2|3` on PDF 23–24 (printed 2–3)
- "running head Chapter 1": text matching `14 Chapter 1|Meetings 15|Chapter 1|Meetings|14|15` on PDF 35–36 (printed 14–15)
- "running head Notes": text matching `(?:\d+ )?Notes to Pages \d+–\d+(?: \d+)?|\d+` on PDF 207–231 (printed 186–210)
- "running head Index": text matching `226 Index|Index 227|Index|226|227` on PDF 247–248 (printed 226–227)
- "page numbers at foot": text matching `\d+|[ivxlc]+` on PDF 1–257 (printed i–236)

### 8. Reading order changes

Listen through these spots with a screen reader.

- Figure on PDF 23 (printed 2) moved to read with its page (it read after PDF 254 (printed 233); now after PDF 23 (printed 2))
- Figure on PDF 26 (printed 5) moved to read with its page (it read after PDF 254 (printed 233); now after PDF 27 (printed 6))
- Figure on PDF 59 (printed 38) moved to read with its page (it read after PDF 254 (printed 233); now after PDF 59 (printed 38))
- Figure on PDF 61 (printed 40) moved to read with its page (it read after PDF 254 (printed 233); now after PDF 62 (printed 41))
- Figure on PDF 71 (printed 50) moved to read with its page (it read after PDF 254 (printed 233); now after PDF 72 (printed 51))
- Figure on PDF 84 (printed 63) moved to read with its page (it read after PDF 254 (printed 233); now after PDF 84 (printed 63))
- Figure on PDF 86 (printed 65) moved to read with its page (it read after PDF 254 (printed 233); now after PDF 87 (printed 66))
- Figure on PDF 87 (printed 66) moved to read with its page (it read after PDF 254 (printed 233); now after PDF 88 (printed 67))
- Figure on PDF 88 (printed 67) moved to read with its page (it read after PDF 254 (printed 233); now after PDF 89 (printed 68))
- Figure on PDF 90 (printed 69) moved to read with its page (it read after PDF 254 (printed 233); now after PDF 91 (printed 70))
- Figure on PDF 117 (printed 96) moved to read with its page (it read after PDF 254 (printed 233); now after PDF 118 (printed 97))
- Figure on PDF 137 (printed 116) moved to read with its page (it read after PDF 254 (printed 233); now after PDF 138 (printed 117))
- Figure on PDF 170 (printed 149) moved to read with its page (it read after PDF 254 (printed 233); now after PDF 170 (printed 149))
- Figure on PDF 171 (printed 150) moved to read with its page (it read after PDF 254 (printed 233); now after PDF 172 (printed 151))
- Figure on PDF 189 (printed 168) moved to read with its page (it read after PDF 254 (printed 233); now after PDF 190 (printed 169))

### 9. Untagged paths (rules, borders, lines)

1652 paths drawn outside any tag were marked as decoration (1524 of them inside shared form XObjects, each edited once): none of them carries text, an image or a link, and none touches untagged text or images.

Strokes directly under text, marked as decoration. An underline can carry meaning (emphasis, a sound in a romanization); if it does here, that meaning must be given another way (e.g. ActualText or a note):

- PDF 85 (printed 64): 1
- PDF 121 (printed 100): 1
- PDF 142 (printed 121): 2
- PDF 145 (printed 124): 1
- PDF 160 (printed 139): 8
- PDF 163 (printed 142): 2
- PDF 179 (printed 158): 1
- PDF 180 (printed 159): 2
- PDF 193 (printed 172): 2
- PDF 194 (printed 173): 3
- PDF 195 (printed 174): 1
- PDF 197 (printed 176): 1

### 10. Spoken text (ActualText) checked against the print (7 accepted with differences, 0 rejected)

A spoken text may differ from the printed characters only in spacing, letter case and line-end hyphens (sponsor rule 1). Accepted ones that differ are listed so a person can listen to them; rejected ones added or changed words or punctuation.

- Accepted, PDF 34 (printed 13): printed "1 MEETINGS New Meanings on Southern Shores" → spoken "1 MEETINGS New Meanings on Southern Shores"
- Accepted, PDF 52 (printed 31): printed "2 TRANSLATING THE LANDSCAPE Negotiating the Mission" → spoken "2 TRANSLATING THE LANDSCAPE Negotiating the Mission"
- Accepted, PDF 82 (printed 61): printed "3 EARS TO HEAR The Sounds of Speech" → spoken "3 EARS TO HEAR The Sounds of Speech"
- Accepted, PDF 106 (printed 85): printed "4 THE LETTER KILLS Writing in En glish" → spoken "4 THE LETTER KILLS Writing in English"
- Accepted, PDF 129 (printed 108): printed "5 THE MAMARIKA WINDS Turning to Anindilyakwa" → spoken "5 THE MAMARIKA WINDS Turning to Anindilyakwa"
- Accepted, PDF 148 (printed 127): printed "6 SPEAKING TO THE HEART The Language of Faith" → spoken "6 SPEAKING TO THE HEART The Language of Faith"
- Accepted, PDF 167 (printed 146): printed "7 SINGING IN TONGUES Translation through Song" → spoken "7 SINGING IN TONGUES Translation through Song"

### 11. Empty tags (34 removed, 0 kept)

A tag is removed only when proven empty: nothing under it holds content, it carries no Alt, ActualText, E or ID, and nothing in the file refers to it except its parent. Table cells are never removed one by one; a table goes only when every part is empty.

- Removed: 11 Table, 11 NormalParagraphStyle, 11 Story, 1 SERED
- 11 whole empty tables (64 parts each), page: not on this tag

### 12. veraPDF (WCAG 2.2 machine profile), before and after

veraPDF 1.30.0, profile "WCAG 2.2 machine validation profile" (7da399cf5baa). Counts are failed checks; pages are from the first checks veraPDF lists for each rule, so a rule may fail on more pages. Rules that only PDF/UA requires are listed apart and do not count. "Who fixes" is who can act on the rule: the pipeline by itself, the AI through the work order, or only a person. **Newly failing** means this run broke something the original passed. Before: 7 rules failing (the AI can act on 2, the pipeline on 4, only a person on 1). After: 0.

| Rule | WCAG | What it checks | Who fixes | Before | After | Status | Pages (after, else before) |
|---|---|---|---|---:|---:|---|---|
| ISO 14289-1 7.18.5-1 | 2.4.4, 4.1.2 | Links shall be tagged according to ISO 32000-1:2008, 14.8.4.4.2, Link Element | the pipeline | 1977 | 0 | fixed | PDF 10 (printed x), PDF 34 (printed 13), PDF 52 (printed 31), PDF 82 (printed 61), PDF 106 (printed 85), PDF 129 (printed 108) |
| ISO 14289-1 7.1-3 | 1.3.1 | Content shall be marked as Artifact or tagged as real content | the AI (`artifacts`) | 1653 | 0 | fixed | PDF 1 (printed i), PDF 3 (printed iii) |
| ISO 14289-1 7.18.3-1 | 2.4.3 | Every page on which there is an annotation shall contain in its page dictionary the key Tabs, and its value shall be S | the pipeline (192 changed) | 192 | 0 | fixed | PDF 5 (printed v), PDF 10 (printed x), PDF 12 (printed xii), PDF 13 (printed xiii), PDF 14 (printed xiv), PDF 18 (printed xviii), PDF 20 (printed xx), PDF 22 (printed 1), PDF 24 (printed 3), PDF 25 (printed 4), PDF 27 (printed 6), PDF 28 (printed 7), PDF 29 (printed 8), PDF 30 (printed 9), PDF 31 (printed 10), PDF 32 (printed 11), PDF 34 (printed 13), PDF 35 (printed 14), PDF 36 (printed 15), PDF 37 (printed 16) |
| ISO 14289-1 7.20-2 | 1.3.1 | The content of Form XObjects shall be incorporated into structure elements according to ISO 32000-1:2008, 14.7.2 | a person | 111 | 0 | fixed | PDF 15 (printed xv), PDF 19 (printed xix), PDF 25 (printed 4), PDF 27 (printed 6), PDF 29 (printed 8), PDF 31 (printed 10), PDF 33 (printed 12), PDF 37 (printed 16), PDF 39 (printed 18), PDF 41 (printed 20), PDF 43 (printed 22), PDF 45 (printed 24), PDF 47 (printed 26), PDF 49 (printed 28), PDF 51 (printed 30), PDF 53 (printed 32), PDF 55 (printed 34), PDF 57 (printed 36), PDF 59 (printed 38), PDF 63 (printed 42) |
| ISO 14289-1 7.3-1 | 1.1.1 | Figure tags shall include an alternative representation or replacement text that represents the contents marked with the Figure tag as noted in ISO 32000-1:2008, 14.7.2, Table 323 | the AI (`alt`) | 18 | 0 | fixed | PDF 3 (printed iii), PDF 4 (printed iv), PDF 23 (printed 2), PDF 26 (printed 5), PDF 59 (printed 38), PDF 61 (printed 40), PDF 71 (printed 50), PDF 84 (printed 63), PDF 86 (printed 65), PDF 87 (printed 66), PDF 88 (printed 67), PDF 90 (printed 69), PDF 117 (printed 96), PDF 137 (printed 116), PDF 170 (printed 149), PDF 171 (printed 150), PDF 189 (printed 168) |
| ISO 14289-1 6.2-1 | 1.3.1 | The document catalog dictionary shall include a MarkInfo dictionary containing an entry, Marked, whose value shall be true | the pipeline (1 changed) | 1 | 0 | fixed | page: not on this tag |
| ISO 14289-1 7.1-10 | 2.4.2 | The document catalog dictionary shall include a ViewerPreferences dictionary containing a DisplayDocTitle key, whose value shall be true | the pipeline (1 changed) | 1 | 0 | fixed | page: not on this tag |

### 13. WCAG checks veraPDF does not make

Each item is something to look at, not a proven failure.

- 1.3.2 the reading order jumps back up the same column on 1 page. Listen through them with a screen reader (or the PAC screen-reader preview): PDF 10 (printed x) (7 jumps)
- 1.3.2 2 small sections are read more than 5 pages after their printed page, after a longer section that covers them. Not a failure (long stories overlap in InDesign books), but a screen reader hears them far from where they are printed: PDF 3 (printed iii) read after PDF 20 (printed xx); PDF 27 (printed 6) read after PDF 244 (printed 223)

### 14. Deferred by the AI

- **Invisible filler text 'hn hk io il sy SY ek eh'**: These tokens occur on about 110 pages as tagged 7×8 tables, as tagged paragraphs and as orphan runs. They are not visible on the page images I saw, so I artifacted them with text rules and expect the emptied tables to be removed. A person should check a few pages to confirm nothing real was hidden and no empty Table tags remain. [PDF 3 (printed iii), PDF 13 (printed xiii), PDF 23 (printed 2), PDF 35 (printed 14), PDF 61 (printed 40), PDF 129 (printed 108), PDF 193 (printed 172), PDF 207 (printed 186), PDF 247 (printed 226), PDF 253 (printed 232), PDF 255 (printed 234)]
- **Reading order of the tag tree**: Top-level Story containers are out of printed order. The preface, series page and title page stories appear in odd positions. The endnotes (PDF 206–231) are read after the bibliography (PDF 232–244) because the bibliography sits inside the large 'Story pp22-244' container. No single container holds exactly the notes pages, so move_section could not be used safely. [PDF 2 (printed ii), PDF 3 (printed iii), PDF 13 (printed xiii), PDF 22 (printed 1), PDF 206 (printed 185), PDF 231 (printed 210), PDF 232 (printed 211), PDF 244 (printed 223)]
- **Second Figure on the title page (obj 7004 0)**: Two Figure tags exist on the title page and both crops are the whole page. I gave both the press logo alt text, but one of them may be a duplicate that should be artifacted. [PDF 4 (printed iv)]
- **Language tags for Anindilyakwa passages**: Epigraphs, hymns and quotations in Anindilyakwa (a language with no CJK or kana content) are not tagged with a language. The right tag (ISO 639-3 'aoi') should be chosen by a person. [PDF 12 (printed xii), PDF 82 (printed 61), PDF 159 (printed 138), PDF 178 (printed 157), PDF 187 (printed 166)]
- **Text layer spacing artifacts**: Many paragraphs have odd extracted spacing, such as 'Acknowl edgments', 'En glish' and letter-spaced runs on the Contents and index pages. Index entries have page numbers separated from their text. I did not change any text. [PDF 10 (printed x), PDF 246 (printed 225), PDF 252 (printed 231)]
- **veraPDF 7.1-3 (content neither artifact nor tagged)**: Addressed with artifact text rules for the filler text, running heads and page numbers. A person should re-run the checker to confirm none remain. [PDF 1 (printed i), PDF 3 (printed iii)]

Reviewer note from the AI: Headings: the book title (PDF 4, printed iv) is the single H1. Chapter titles, Introduction, the front-matter and back-matter titles (Preface, Acknowledgments, Note on Terminology and Language, Abbreviations, Notes, Bibliography, Index, About the Author) and Contents are H2. The in-chapter section heads, which were styled 'H1', are now H3, as are the endnote chapter heads (ENH) and the bibliography subheads (BMSH). Chapter number, title and subtitle are merged into one H2, with ActualText so a screen reader speaks them together. The words 'New Meanings on Southern Shores' and the like are the printed subtitles. The cover on PDF 1 (printed i) is handled through page_figures. I left fix_figure_order at its default.

### 15. Deferred by the executor

- text rule "invisible filler text (orphan)" matched no text on PDF 1–257 (printed i–236): nothing was hidden by this rule; check its pattern against the page (spacing, split runs)

## What was changed

| Change | Count |
|---|---:|
| document: marked as tagged | 1 |
| document: DisplayDocTitle | 2 |
| artifact: "invisible filler text (tagged)" (inside a shared form XObject) | 616 |
| artifact: "page numbers at foot" | 7 |
| artifact: "running head Preface" | 2 |
| artifact: "running head Acknowledgments" | 3 |
| artifact: "running head Introduction" | 5 |
| artifact: "running head Chapter 1" | 5 |
| artifact: "running head Notes" | 50 |
| artifact: "running head Index" | 5 |
| document: title | 1 |
| document: /Lang | 1 |
| heading: RoleMap level | 8 |
| heading: merged into next | 7 |
| heading: merged into prev | 7 |
| heading: ActualText | 7 |
| heading: standard tag H1 → H3 (retyped) | 38 |
| retype → H1 | 1 |
| table: header cells marked (work order) | 4 |
| table: data cells tied to their headers by ID | 28 |
| table: title row → Caption | 1 |
| figure: alt text | 18 |
| figure: caption tied (figure moved out of its paragraph) | 15 |
| contents: TOC entries | 17 |
| contents: TOC built | 1 |
| notes: Note with /ID | 824 |
| links: /Contents set | 2822 |
| links: joined existing Link | 2792 |
| links: new Link element created | 30 |
| links: wraps its text | 22 |
| links: note reference wrapped | 1 |
| links: placed beside nearest text | 7 |
| order: figure moved to its page | 15 |
| contents: entry wrapped in Reference | 17 |
| order: empty container removed | 40 |
| figure: whole page wrapped as one Figure | 1 |
| figure: alt text from the work order (page figure) | 1 |
| structure: empty table removed (every part proven empty) | 11 |
| structure: empty tag removed (proven empty) | 23 |
| artifact: untagged path with no content (rule, border, line) | 1652 |
| tag tree index: entries repaired | 1 |
| tab order: /Tabs /S set on pages with annotations | 192 |

## Final check with PAC 2026

Open `translation_remediated.pdf` in PAC 2026 (https://pac.pdf-accessibility.org/en, Windows) and run its WCAG check. Anything it fails that is not listed above is a gap in the automated checks: note it in the issue tracker.

No automated check here covers these WCAG 2.2 AA criteria; check them by hand, with PAC's screen-reader and structure previews:

- 1.1.1: alt text is accurate and gives the figure's purpose; decorative images are artifacts
- 1.3.1 / 1.3.2: headings, lists and tables match what is printed, and the reading order makes sense
- 1.4.1: no information is given by colour alone
- 1.4.3: contrast of text over images and coloured backgrounds (PAC's contrast checker)
- 1.4.5: no images of text where real text could be used (scanned pages: the OCR layer stands in)
- 2.4.6: headings describe their section
- 3.1.2: passages in another language carry their language (see `han_review.csv` if present)
