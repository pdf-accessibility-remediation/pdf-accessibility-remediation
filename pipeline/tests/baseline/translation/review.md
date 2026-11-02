# Remediation Review: translation.pdf

Result: `translation_remediated.pdf`

257 pages · run November 1, 2026, at 7:03 PM · model `anthropic/claude-sonnet-5.5` · prompt `workorder_v9.md` (465d4b1e1cd2299b) · AI cost not recorded · this run: no new call · tokens: saved reply reused, not counted

Intake: none (already tagged)

Libraries: python 3.13.9 · pikepdf 10.5.1 · pdfplumber 0.11.9 · pypdfium2 5.7.1 · pillow 13.0.0 · fonttools 4.62.1

Time: intake 1.6s · audit 33.0s · reuse saved reply 1.4s · apply 148.9s · verify 67.6s · total 252.5s

## Overview

[Open the dashboard](review.html)

**Status:** Not Ready

**Ready to ship?**
- Work Order Approval: Not Approved (applied without a review)
- ✓ OCR Text Approval: Not Applicable
- ✓ Safety Checks: Passed
- Accessibility Evaluation: Not Completed

**Safety checks:** OK ✔ pages look the same · OK ✔ text unchanged · OK ✔ all content tagged or decoration · OK ✔ tag-tree index points into the tree · OK ✔ every font readable  
**Needs a person:** 8 (5 deferred by the AI · 1 deferred by the executor · 2 CHECK rows)  
**AI decisions:** 66 in the work order, applied without review by a person  
**Fixed automatically (no AI):** links tied and described 2,822 · decorative lines marked 1,652 · note IDs 823 · pages given tab order 192 · empty tags removed 34 · figures moved to their page 15 · title shown in the window 2 · marked as tagged 1 · whole-page figures wrapped 1 · tag-tree index entries 1  
**veraPDF (WCAG 2.2 machine checks):** 7 WCAG rules failing before (3,953 checks) → 0 after (0 checks) · 0 newly failing

Automated checks are evidence, not sign-off.

| Top issues | Pages | Where |
|---|---|---|
| Private-use characters (checklist 3.6): 5 read-aloud characters with private-use codes (U+F036: 5) on 1 page | see Automated Checks | [Automated Checks](#automated-checks) |
| Reading order jumps back up a column (7 jumps) | PDF 10 (printed x) | [§13](#13-wcag-checks-verapdf-does-not-make) |
| text rule "hidden junk text grid (orphan)" matched no text on PDF 1–257 (printed i–236) | see §15 | [§15](#15-deferred-by-the-executor) |
| veraPDF 7.1-3 (content neither marked as artifact nor tagged): 1653 failures with no target object | PDF 1 (printed i), PDF 3 (printed iii), PDF 257 (printed 236) | [§14](#14-deferred-by-the-ai) |
| Reading order of the Story containers | PDF 2 (printed ii), PDF 255 (printed 234) | [§14](#14-deferred-by-the-ai) |
| … and 3 more | | §14 |

Automated checks are evidence, not legal sign-off. Items marked **CHECK**, and everything under "For a person to check", need a human.

## Automated Checks

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
| Figures: none with empty or placeholder alt | OK | 18 figures, 0 placeholder |
| Every Note has a unique ID | OK | 823 notes · 0 without ID · 0 duplicate · 0 not in the ID tree |
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
| Alt text: none like a file name or repeated on many figures (1.1.1) | OK | 0 of 18 figures flagged |
| Tables: every table has header cells (1.3.1) | OK | none without |
| Reading order: no page jumps back up a column (1.3.2) | **CHECK** | 1 of 228 pages flagged |
| Reading order: no section moved away from its printed place by this run (1.3.2) | OK | 0 new · 0 already in the original, of 22 sections and blocks |
| Title is not a file name or placeholder (2.4.2) | OK | "Found in Translation: Many Meanings on a North Australian Mission" |
| Link text: none like "click here" (2.4.4) | OK | 0 generic |
| Headings: none empty, very long or repeated in a row (2.4.6) | OK | 0 empty · 0 long · 0 repeated |

## For a Person to Check

### 1. Pages Wrapped as One Figure (1)

Pages with nothing tagged and nothing marked as decoration that hold a drawing (a full-page map, plate or cover). Each page was wrapped whole in one Figure; nothing on it was changed or removed.

- PDF 1 (printed i): read first in the document. Alt text from the AI: "Book cover: sepia photograph of a group of Anindilyakwa men and two white missionaries posing outdoors, with a coloured archival map of Groote Eylandt in the upper left. Title in large letters: Found in Translation. Subtitle: Many Meanings on a North Australian Mission. Author: Laura Rademaker."

### 2. Alt Text Written or Changed by the AI (17)

| Page | Before | After |
|---|---|---|
| PDF 3 (printed iii) | — | Indigenous Pacifics series logo |
| PDF 4 (printed iv) | — | University of Hawai‘i Press logo |
| PDF 23 (printed 2) | — | Black-and-white photograph: missionary Alfred Dyer, in a hat and shorts, stands with hands on hips in open woodland behind three Anindilyakwa men sitting on the ground. |
| PDF 26 (printed 5) | — | Map of northern Australia locating Groote Eylandt in the Gulf of Carpentaria, east of Arnhem Land. Darwin, Pine Creek and Katherine are marked, and an inset shows where the area lies within Australia. |
| PDF 59 (printed 38) | — | Black-and-white photograph from 1928 of a large group of Aboriginal children outdoors in front of palms and huts. Girls in light dresses sit and stand at left, boys stand at right, and a white man stands in the centre. |
| PDF 61 (printed 40) | — | Hand-drawn survey map of Groote Eylandt and nearby islands showing the Aboriginal reserve, the mission lease and the area excluded for the Flying Boat Base, with Central Hill, Port Langdon and Bluff Hill marked. The handwritten legend reads: Abo. Res. edged blue, Mission Lease tinted pink, Area tinted green excluded for Flying Boat Base 7000 acs., scale about 10 miles to an inch. |
| PDF 71 (printed 50) | — | Black-and-white photograph of Anindilyakwa men pushing a heavy log frame during construction at Angurugu while a man in a hat looks through a surveying instrument on a tripod. |
| PDF 84 (printed 63) | — | Plan of the layout of the Groote Eylandt Mission Station at Angurugu. Roads radiate from a circle around the church at the centre. Around it sit the mission houses, school, store, boys' and girls' dormitories, hospital and maternity block, people's houses and the native camp, with a playing field, gardens, a sawmill and a river along the top. |
| PDF 86 (printed 65) | — | Black-and-white photograph from 1951 of a crowd of Anindilyakwa people and missionaries standing in front of the Angurugu church, a long building with a pale roof, among trees. |
| PDF 87 (printed 66) | — | Black-and-white photograph of a missionary sitting on the ground holding up a picture board to a circle of Aboriginal boys at Sunday school. |
| PDF 88 (printed 67) | — | Black-and-white photograph from 1951 of Anindilyakwa adults and children standing and sitting in front of huts of bark and corrugated iron in the village. |
| PDF 90 (printed 69) | — | Judith Stokes, smiling and wearing glasses and a sleeveless checked dress, leaning on a verandah rail with trees behind her. |
| PDF 117 (printed 96) | — | Two Angurugu schoolchildren sitting at wooden desks in a classroom, one looking down at an open book. |
| PDF 137 (printed 116) | — | Judith Stokes seated on a chair beside Lawrence Jaragba and Gula Lalara in a room with floral curtains and a radio behind them. |
| PDF 170 (printed 149) | — | Johnny holding a concertina on a boat, with a sail, mast and the sea behind him. |
| PDF 171 (printed 150) | — | Two men with painted bodies dance in a funeral ceremony for Quartpot in 1968, one wearing a feathered headdress, in a clearing in front of a tin-roofed shed with onlookers seated behind. |
| PDF 189 (printed 168) | — | Evangelical poster titled 'The 2 Ways'. A broad road at left leads past scenes of fighting and wrongdoing towards flames. A narrow road at right leads up to a large cross and a heavenly landscape. People walk along both paths, and a sign near the bottom reads 'Enter ye in at the strait gate.' |

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
| H1 | H3 | retype (standard tag) | 38 |

Merged: `CN` into the next `CT`; `CST` into the prev `CT`

Spoken text set by the AI (should match what is printed):

| Page | Text |
|---|---|
| PDF 34 (printed 13) | 1 Meetings New Meanings on Southern Shores |
| PDF 52 (printed 31) | 2 Translating the Landscape Negotiating the Mission |
| PDF 82 (printed 61) | 3 Ears to Hear The Sounds of Speech |
| PDF 106 (printed 85) | 4 The Letter Kills Writing in English |
| PDF 129 (printed 108) | 5 The Mamarika Winds Turning to Anindilyakwa |
| PDF 148 (printed 127) | 6 Speaking to the Heart The Language of Faith |
| PDF 167 (printed 146) | 7 Singing in Tongues Translation through Song |

### 4. Elements Retyped by the AI (1)

Check each one is (or is not) a heading as decided.

| Page | Text | Before | After |
|---|---|---|---|
| PDF 4 (printed iv) | FOUND IN TRANSLATION | TPT | H1 |

### 5. Lists and Tables

- Header cells marked by the AI on PDF 27 (printed 6): 2 header row(s), 0 header column(s), 3 cells changed to header cells. Check they are the real headers.

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

### 6. Text a Screen Reader Could Not Reach (before this run)

111 pages had text outside the tag tree: 6216 orphan runs (marked, but no tag owns them) and 0 untagged runs. Running heads and page numbers among them can be hidden as decoration; real content must be added to the tag tree by a person. After this run: 0 untagged characters, 0 orphan runs remain.

Pages: PDF 15 (printed xv), PDF 19 (printed xix), PDF 25 (printed 4), PDF 27 (printed 6), PDF 29 (printed 8), PDF 31 (printed 10), PDF 33 (printed 12), PDF 37 (printed 16), PDF 39 (printed 18), PDF 41 (printed 20), PDF 43 (printed 22), PDF 45 (printed 24), PDF 47 (printed 26), PDF 49 (printed 28), PDF 51 (printed 30), PDF 53 (printed 32), PDF 55 (printed 34), PDF 57 (printed 36), PDF 59 (printed 38), PDF 63 (printed 42), PDF 65 (printed 44), PDF 67 (printed 46), PDF 69 (printed 48), PDF 71 (printed 50), PDF 73 (printed 52), PDF 75 (printed 54), PDF 77 (printed 56), PDF 79 (printed 58), PDF 81 (printed 60), PDF 83 (printed 62), PDF 85 (printed 64), PDF 87 (printed 66), PDF 89 (printed 68), PDF 91 (printed 70), PDF 93 (printed 72), PDF 95 (printed 74), PDF 97 (printed 76), PDF 99 (printed 78), PDF 101 (printed 80), PDF 103 (printed 82), PDF 105 (printed 84), PDF 107 (printed 86), PDF 109 (printed 88), PDF 111 (printed 90), PDF 113 (printed 92), PDF 115 (printed 94), PDF 117 (printed 96), PDF 119 (printed 98), PDF 121 (printed 100), PDF 123 (printed 102), PDF 125 (printed 104), PDF 127 (printed 106), PDF 131 (printed 110), PDF 133 (printed 112), PDF 135 (printed 114), PDF 137 (printed 116), PDF 139 (printed 118), PDF 141 (printed 120), PDF 143 (printed 122), PDF 145 (printed 124), PDF 147 (printed 126), PDF 149 (printed 128), PDF 151 (printed 130), PDF 153 (printed 132), PDF 155 (printed 134), PDF 157 (printed 136), PDF 159 (printed 138), PDF 161 (printed 140), PDF 163 (printed 142), PDF 165 (printed 144), PDF 167 (printed 146), PDF 169 (printed 148), PDF 171 (printed 150), PDF 173 (printed 152), PDF 175 (printed 154), PDF 177 (printed 156), PDF 179 (printed 158), PDF 181 (printed 160), PDF 183 (printed 162), PDF 185 (printed 164), PDF 187 (printed 166), PDF 189 (printed 168), PDF 191 (printed 170), PDF 195 (printed 174), PDF 197 (printed 176), PDF 199 (printed 178), PDF 201 (printed 180), PDF 203 (printed 182), PDF 205 (printed 184), PDF 209 (printed 188), PDF 211 (printed 190), PDF 213 (printed 192), PDF 215 (printed 194), PDF 217 (printed 196), PDF 219 (printed 198), PDF 221 (printed 200), PDF 223 (printed 202), PDF 225 (printed 204), PDF 227 (printed 206), PDF 229 (printed 208), PDF 231 (printed 210), PDF 233 (printed 212), PDF 235 (printed 214), PDF 237 (printed 216), PDF 239 (printed 218), PDF 241 (printed 220), PDF 243 (printed 222), PDF 245 (printed 224), PDF 249 (printed 228), PDF 251 (printed 230), PDF 257 (printed 236)

### 7. Hidden from Screen Readers (artifacts)

- 1 decorative elements ("second whole-page figure on the title page (PDF 4, printed iv); the title page is already carried by tagged text and the press logo in 7003 0") on PDF 4 (printed iv)
- "hidden junk text grid (tagged)": text matching `hn|hk|io|il|sy|SY|ek|eh` on PDF 2–257 (printed ii–236)
- "hidden junk text grid (orphan)": text matching `hn|hk|io|il|sy|SY|ek|eh` on PDF 1–257 (printed i–236)
- "running head Preface": text matching `xii Preface|xii|Preface` on PDF 13 (printed xiii)
- "running head Acknowledgments": text matching `Acknowl edgments xv|Acknowl edgments|xv` on PDF 16 (printed xvi)
- "running head Introduction": text matching `(2 )?Introduction( 3)?|2|3` on PDF 23–24 (printed 2–3)
- "running head Chapter 1": text matching `14 Chapter 1|Chapter 1|Meetings 15|Meetings|14|15` on PDF 35–36 (printed 14–15)
- "running head Notes to Pages": text matching `(\d+ )?Notes to Pages \d+–\d+( \d+)?|\d+` on PDF 207–231 (printed 186–210)
- "running head Index": text matching `(226 )?Index( 227)?|226|227` on PDF 247–248 (printed 226–227)
- "folios on chapter-opening pages": text matching `ix|\d+` on PDF 10–246 (printed x–225)

### 8. Reading Order Changes

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

### 9. Untagged Paths (rules, borders, lines)

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

### 10. Spoken Text (ActualText) Checked Against the Print (7 accepted with differences, 0 rejected)

A spoken text may differ from the printed characters only in spacing, letter case and line-end hyphens (sponsor rule 1). Accepted ones that differ are listed so a person can listen to them; rejected ones added or changed words or punctuation.

- Accepted, PDF 34 (printed 13): printed "1 MEETINGS New Meanings on Southern Shores" → spoken "1 Meetings New Meanings on Southern Shores"
- Accepted, PDF 52 (printed 31): printed "2 TRANSLATING THE LANDSCAPE Negotiating the Mission" → spoken "2 Translating the Landscape Negotiating the Mission"
- Accepted, PDF 82 (printed 61): printed "3 EARS TO HEAR The Sounds of Speech" → spoken "3 Ears to Hear The Sounds of Speech"
- Accepted, PDF 106 (printed 85): printed "4 THE LETTER KILLS Writing in En glish" → spoken "4 The Letter Kills Writing in English"
- Accepted, PDF 129 (printed 108): printed "5 THE MAMARIKA WINDS Turning to Anindilyakwa" → spoken "5 The Mamarika Winds Turning to Anindilyakwa"
- Accepted, PDF 148 (printed 127): printed "6 SPEAKING TO THE HEART The Language of Faith" → spoken "6 Speaking to the Heart The Language of Faith"
- Accepted, PDF 167 (printed 146): printed "7 SINGING IN TONGUES Translation through Song" → spoken "7 Singing in Tongues Translation through Song"

### 11. Empty Tags (34 removed, 0 kept)

A tag is removed only when proven empty: nothing under it holds content, it carries no Alt, ActualText, E or ID, and nothing in the file refers to it except its parent. Table cells are never removed one by one; a table goes only when every part is empty.

- Removed: 11 Table, 11 NormalParagraphStyle, 11 Story, 1 SERED
- 11 whole empty tables (64 parts each), page: not on this tag

### 12. veraPDF (WCAG 2.2 machine profile), Before and After

veraPDF 1.30.3, profile "WCAG 2.2 machine validation profile" (7da399cf5baa). Counts are failed checks; pages are from the first checks veraPDF lists for each rule, so a rule may fail on more pages. Rules that only PDF/UA requires are listed apart and do not count. "Who fixes" is who can act on the rule: the pipeline by itself, the AI through the work order, or only a person. **Newly failing** means this run broke something the original passed. Before: 7 rules failing (the AI can act on 2, the pipeline on 4, only a person on 1). After: 0.

| Rule | WCAG | What it checks | Who fixes | Before | After | Status | Pages (after, else before) |
|---|---|---|---|---:|---:|---|---|
| ISO 14289-1 7.18.5-1 | 2.4.4, 4.1.2 | Links shall be tagged according to ISO 32000-1:2008, 14.8.4.4.2, Link Element | the pipeline | 1977 | 0 | fixed | PDF 10 (printed x), PDF 34 (printed 13), PDF 52 (printed 31), PDF 82 (printed 61), PDF 106 (printed 85), PDF 129 (printed 108) |
| ISO 14289-1 7.1-3 | 1.3.1 | Content shall be marked as Artifact or tagged as real content | the AI (`artifacts`) | 1653 | 0 | fixed | PDF 1 (printed i), PDF 3 (printed iii) |
| ISO 14289-1 7.18.3-1 | 2.4.3 | Every page on which there is an annotation shall contain in its page dictionary the key Tabs, and its value shall be S | the pipeline (192 changed) | 192 | 0 | fixed | PDF 5 (printed v), PDF 10 (printed x), PDF 12 (printed xii), PDF 13 (printed xiii), PDF 14 (printed xiv), PDF 18 (printed xviii), PDF 20 (printed xx), PDF 22 (printed 1), PDF 24 (printed 3), PDF 25 (printed 4), PDF 27 (printed 6), PDF 28 (printed 7), PDF 29 (printed 8), PDF 30 (printed 9), PDF 31 (printed 10), PDF 32 (printed 11), PDF 34 (printed 13), PDF 35 (printed 14), PDF 36 (printed 15), PDF 37 (printed 16) |
| ISO 14289-1 7.20-2 | 1.3.1 | The content of Form XObjects shall be incorporated into structure elements according to ISO 32000-1:2008, 14.7.2 | a person | 111 | 0 | fixed | PDF 15 (printed xv), PDF 19 (printed xix), PDF 25 (printed 4), PDF 27 (printed 6), PDF 29 (printed 8), PDF 31 (printed 10), PDF 33 (printed 12), PDF 37 (printed 16), PDF 39 (printed 18), PDF 41 (printed 20), PDF 43 (printed 22), PDF 45 (printed 24), PDF 47 (printed 26), PDF 49 (printed 28), PDF 51 (printed 30), PDF 53 (printed 32), PDF 55 (printed 34), PDF 57 (printed 36), PDF 59 (printed 38), PDF 63 (printed 42) |
| ISO 14289-1 7.3-1 | 1.1.1 | Figure tags shall include an alternative representation or replacement text that represents the contents marked with the Figure tag as noted in ISO 32000-1:2008, 14.7.2, Table 323 | the AI (`alt`) | 18 | 0 | fixed | PDF 3 (printed iii), PDF 4 (printed iv), PDF 23 (printed 2), PDF 26 (printed 5), PDF 59 (printed 38), PDF 61 (printed 40), PDF 71 (printed 50), PDF 84 (printed 63), PDF 86 (printed 65), PDF 87 (printed 66), PDF 88 (printed 67), PDF 90 (printed 69), PDF 117 (printed 96), PDF 137 (printed 116), PDF 170 (printed 149), PDF 171 (printed 150), PDF 189 (printed 168) |
| ISO 14289-1 6.2-1 | 1.3.1 | The document catalog dictionary shall include a MarkInfo dictionary containing an entry, Marked, whose value shall be true | the pipeline (1 changed) | 1 | 0 | fixed | page: not on this tag |
| ISO 14289-1 7.1-10 | 2.4.2 | The document catalog dictionary shall include a ViewerPreferences dictionary containing a DisplayDocTitle key, whose value shall be true | the pipeline (1 changed) | 1 | 0 | fixed | page: not on this tag |

### 13. WCAG Checks veraPDF Does Not Make

Each item is something to look at, not a proven failure.

- 1.3.2 the reading order jumps back up the same column on 1 page. Listen through them with a screen reader (or the PAC screen-reader preview): PDF 10 (printed x) (7 jumps)
- 1.3.2 2 small sections are read more than 5 pages after their printed page, after a longer section that covers them. Not a failure (long stories overlap in InDesign books), but a screen reader hears them far from where they are printed: PDF 3 (printed iii) read after PDF 20 (printed xx); PDF 27 (printed 6) read after PDF 244 (printed 223)

### 14. Deferred by the AI

- **veraPDF 7.1-3 (content neither marked as artifact nor tagged): 1653 failures with no target object**: The artifact rules above remove the hidden 'hn hk io il sy SY ek eh' text. The remaining failures have no obj to target, so a person should re-run veraPDF and check what is left, including the cover page. [PDF 1 (printed i), PDF 3 (printed iii), PDF 257 (printed 236)]
- **Reading order of the Story containers**: The digest's reading order has Story containers well out of printed order: front matter, the junk grids, the Introduction and chapters. I cannot tell with certainty how to fix it with at most 3 moves, so a person should check it in Acrobat. [PDF 2 (printed ii), PDF 255 (printed 234)]
- **Index entries (styles IX/IXA)**: The text layer has dropped the commas and spaced page numbers, for example 'Aboriginal art, – 8687'. Page-number links and text need a person to check them. [PDF 246 (printed 225), PDF 252 (printed 231)]
- **Anindilyakwa-language passages (epigraphs, EXF/EXO block quotes, hymns)**: These are not language-tagged. Anindilyakwa (ISO 639-3 aoi) needs a person to decide on a language tag, and the OCR-like spacing in some lines also needs review. [PDF 12 (printed xii), PDF 193 (printed 172)]
- **Title-page figures: second whole-page figure 7004 0, which I artifacted as a duplicate**: I could not tell which of the two vector figures on PDF 4 (printed iv) is the press logo. 7003 0 got the logo alt text. A person should confirm which is correct. [PDF 4 (printed iv)]

Reviewer note from the AI: The file has a hidden grid of text ('hn hk io il sy SY ek eh') on about 110 pages. It is tagged as 7x8 tables on some pages and as orphan runs on others, and it does not show on the page images. I treated it as junk and artifacted it. The emptied tables should be removed by remove_empty_containers, so check that none remain. Heading plan: H1 is the book title on the title page (PDF 4, printed iv). H2 covers front/back-matter titles, the Introduction, chapter titles (chapter number and subtitle merged into the CT element) and the Notes, Bibliography, Index and About the Author headings. H3 covers the in-chapter section heads (style H1 remapped to H3), the Notes chapter heads and the Bibliography subheads. Chapter-number/title/subtitle merges rely on CN→next CT and CST→prev CT, and ActualText was written for the 7 merged chapter headings. Conclusion and Epilogue are single CT elements. The real clan table (PDF 27, printed 6) got 2 header rows.

### 15. Deferred by the Executor

- text rule "hidden junk text grid (orphan)" matched no text on PDF 1–257 (printed i–236): nothing was hidden by this rule; check its pattern against the page (spacing, split runs)

## What Was Changed

| Change | Count |
|---|---:|
| document: marked as tagged | 1 |
| document: DisplayDocTitle | 2 |
| artifact: "hidden junk text grid (tagged)" (inside a shared form XObject) | 616 |
| artifact: "second whole-page figure on the title page (PDF 4, printed iv); the title page is already carried by tagged text and the press logo in 7003 0" | 1 |
| artifact: "folios on chapter-opening pages" | 7 |
| artifact: "running head Preface" | 2 |
| artifact: "running head Acknowledgments" | 3 |
| artifact: "running head Introduction" | 5 |
| artifact: "running head Chapter 1" | 5 |
| artifact: "running head Notes to Pages" | 50 |
| artifact: "running head Index" | 5 |
| document: title | 1 |
| document: /Lang | 1 |
| heading: RoleMap level | 8 |
| heading: merged into next | 7 |
| heading: merged into prev | 7 |
| heading: ActualText | 7 |
| heading: standard tag H1 → H3 (retyped) | 38 |
| retype → H1 | 1 |
| table: header cells marked (work order) | 3 |
| figure: alt text | 17 |
| figure: caption tied (figure moved out of its paragraph) | 15 |
| contents: TOC entries | 17 |
| contents: TOC built | 1 |
| notes: Note with /ID | 823 |
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

## Accessibility Evaluation

A person evaluates this version of `translation_remediated.pdf` with PAC 2026 and a screen reader, on the app's "Accessibility Evaluation" page (or with manual_checks.py; docs/release.md). The "Ready to ship?" answer needs both parts. A Fail is recorded with its note and does not hold the book back. Each result is recorded against this version of the PDF (its sha256): after a new apply it no longer counts. The evaluation is a record of what a person found, not a legal certification.

**PAC 2026.** Open `translation_remediated.pdf` in PAC 2026 (https://pac.pdf-accessibility.org/en, Windows) and run its WCAG check. Anything it fails that is not listed above is a gap in the automated checks: note it in the issue tracker. Each item is Pass, Fail or Not Applicable, with notes:

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
