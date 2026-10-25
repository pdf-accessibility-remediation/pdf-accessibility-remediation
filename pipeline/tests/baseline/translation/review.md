# Remediation review: translation.pdf

Result: `translation_remediated.pdf`

257 pages · run 2026-10-25T03:28:14 · model `anthropic/claude-sonnet-5.5` · prompt `workorder_v8.md` (4555d20a2fa08a40) · cost $0 (saved reply reused, no new call) · tokens: saved reply reused, not counted

Intake: none (already tagged)

Libraries: python 3.14.4 · pikepdf 10.5.1 · pdfplumber 0.11.9 · pypdfium2 5.7.1 · pillow 13.0.0 · fonttools 4.62.1

Time: intake 0.7s · audit 50.8s · reuse saved reply 1.0s · apply 103.1s · verify 68.3s · total 223.9s

## Overview

[Open the dashboard](review.html)

**Ready to ship?** No
- Work order approved on the review page: no (run without REVIEW=1)
- OCR text approved: not needed (intake added no OCR text)
- Safety checks: OK
- Manual check (PAC): not run

**Safety checks:** OK ✔ pages look the same · OK ✔ text unchanged · OK ✔ all content tagged or decoration · OK ✔ tag-tree index points into the tree · OK ✔ every font readable  
**Needs a person:** 10 (7 deferred by the AI · 1 deferred by the executor · 2 CHECK rows)  
**AI decisions:** 88 in the work order, applied without review by a person  
**Fixed automatically (no AI):** links tied and described 2,822 · decorative lines marked 1,652 · note IDs 823 · empty tags removed 727 · pages given tab order 192 · figures moved to their page 15 · title shown in the window 2 · marked as tagged 1 · whole-page figures wrapped 1 · tag-tree index entries 1  
**veraPDF (WCAG 2.2 machine checks):** 7 WCAG rules failing before (3,953 checks) → 0 after (0 checks) · 0 newly failing

Automated checks are evidence, not sign-off.

| Top issues | Pages | Where |
|---|---|---|
| Private-use characters (checklist 3.6): 5 read-aloud characters with private-use codes (U+F036: 5) on 1 page | see Automated checks | [Automated checks](#automated-checks) |
| Reading order jumps back up a column (7 jumps) | PDF 10 (printed x) | [§12](#12-wcag-checks-verapdf-does-not-make) |
| text rule "stray two-letter token blocks (orphans), not real content" matched no text on PDF 1–257 (printed i–236) | see §14 | [§14](#14-deferred-by-the-executor) |
| Stray token blocks (hn hk io il sy SY ek eh) on many pages, as orphan runs, tagged paragraphs and 11 tables,… | PDF 3 (printed iii), PDF 257 (printed 236) | [§13](#13-deferred-by-the-ai) |
| veraPDF 7.1-3: the 1653 unmarked-content failures | PDF 1 (printed i), PDF 3 (printed iii) | [§13](#13-deferred-by-the-ai) |
| … and 5 more | | §13 |

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
| Empty tags removed when proven empty | OK | 727 removed |
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
| Title is not a file name or placeholder (2.4.2) | OK | "Found in Translation: Many Meanings on a North Australian Mission" |
| Link text: none like "click here" (2.4.4) | OK | 0 generic |
| Headings: none empty, very long or repeated in a row (2.4.6) | OK | 0 empty · 0 long · 0 repeated |

## For a person to check

### 1. Pages wrapped as one Figure (1)

Pages with nothing tagged and nothing marked as decoration that hold a drawing (a full-page map, plate or cover). Each page was wrapped whole in one Figure; nothing on it was changed or removed.

- PDF 1 (printed i): read first in the document. Alt text from the AI: "Front cover of Found in Translation: Many Meanings on a North Australian Mission by Laura Rademaker. A sepia photograph shows a large group of Anindilyakwa men and boys with two missionaries standing and crouching outdoors. Above them is a tinted archival map of Groote Eylandt. The title is in large brown and grey letters and the author's name is at the bottom."

### 2. Alt text written or changed by the AI (17)

| Page | Before | After |
|---|---|---|
| PDF 3 (printed iii) | — | Series page: the Indigenous Pacifics series logo (a black block with a line graph over a map-like shape and the words INDIGENOUS PACIFICS), above the series editors, Noelani Goodyear-Ka‘ōpua and April K. Henderson. |
| PDF 4 (printed iv) | — | Title page of Found in Translation: Many Meanings on a North Australian Mission by Laura Rademaker, with the University of Hawai‘i Press logo and the imprint Honolulu. |
| PDF 23 (printed 2) | — | Black-and-white photograph of missionary Alfred Dyer, in a pith helmet and shorts with hands on hips, standing in bushland on Groote Eylandt behind three Anindilyakwa men seated on the ground. |
| PDF 26 (printed 5) | — | Map of northern Australia locating Groote Eylandt, an island in the Gulf of Carpentaria off the east of Arnhem Land. Darwin, Pine Creek and Katherine are marked on the mainland, and an inset shows the region's place on the Australian continent. |
| PDF 59 (printed 38) | — | Black-and-white 1928 photograph of a large group posed outdoors: girls in light dresses seated and standing at the front, boys and men at the right, and a man in a suit at the centre, with palm trees and a thatched building behind. |
| PDF 61 (printed 40) | — | Hand-drawn archival map of Groote Eylandt and nearby islands showing the Aboriginal Reserve, the Church Missionary Society mission lease in the northwest tinted pink, and an area tinted green excluded for the Flying Boat Base. A handwritten note gives the legend and the scale of ten miles to an inch. |
| PDF 71 (printed 50) | — | Black-and-white photograph of Anindilyakwa men pushing and lifting timber on a building frame at Angurugu while a man in a hat at right looks through a camera on a tripod. |
| PDF 84 (printed 63) | — | Plan of the Groote Eylandt mission station layout. Roads radiate from a circle around a central church. Around it are the mission houses, school, boys' and girls' dormitories, hospital, maternity block, store, pump house, saw mill, native camp, people's houses, playing field and gardens, with a river to the north and an air strip road at upper right. |
| PDF 86 (printed 65) | — | Black-and-white photograph of a large group of people standing in front of the long white-roofed Angurugu church among trees, 1951. |
| PDF 87 (printed 66) | — | Photograph of a missionary in a white shirt holding up a picture board to a circle of Aboriginal boys seated on the ground outdoors at the Sunday school. |
| PDF 88 (printed 67) | — | Black-and-white photograph of Anindilyakwa adults and children standing in front of bark and tin huts in the village, 1951. |
| PDF 90 (printed 69) | — | Photograph of Judith Stokes, a smiling woman with glasses and a sleeveless checked dress, leaning on a verandah rail with trees behind her. |
| PDF 117 (printed 96) | — | Photograph of two Anindilyakwa schoolchildren at classroom desks, the boy at left looking at an open book and the boy at right resting his cheek on his hand, with other children behind them. |
| PDF 137 (printed 116) | — | Photograph of Judith Stokes, Lawrence Jaragba and Gula Lalara seated side by side on chairs in front of curtains, with a radio behind them. |
| PDF 170 (printed 149) | — | Photograph of Johnny, a man in a singlet, sitting on a boat holding an accordion, with a sail, mast and the sea behind him. |
| PDF 171 (printed 150) | — | Photograph of two men with body paint and ceremonial headdress dancing in a dirt clearing in a funeral dance for Quartpot in 1968, with onlookers and a tin-roofed shed behind them. |
| PDF 189 (printed 168) | — | Missionary poster titled The 2 Ways, contrasting two paths. At left a broad road runs among flames and scenes of fighting, gambling and violence. At right a narrow path leads past a cross toward a heavenly city. A signpost reads Broadway and a text panel reads Enter ye in at the strait gate. |

### 3. Headings

Heading levels by style (as applied):

| Style | Level | How | Elements |
|---|---|---|---:|
| TPT | H1 | RoleMap | 1 |
| FMHS | H2 | RoleMap | 1 |
| FMH | H2 | RoleMap | 4 |
| CTINT | H2 | RoleMap | 1 |
| CT | H2 | RoleMap | 9 |
| BMH | H2 | RoleMap | 3 |
| ATAH | H2 | RoleMap | 1 |
| ENH | H3 | RoleMap | 10 |
| BMSH | H3 | RoleMap | 2 |
| H1 | H3 | retype (standard tag) | 38 |

Merged: `CN` into the next `CT`; `CST` into the prev `CT`

Spoken text set by the AI (should match what is printed):

| Page | Text |
|---|---|
| PDF 14 (printed xiv) | Acknowledgments |
| PDF 34 (printed 13) | 1 MEETINGS New Meanings on Southern Shores |
| PDF 52 (printed 31) | 2 TRANSLATING THE LANDSCAPE Negotiating the Mission |
| PDF 82 (printed 61) | 3 EARS TO HEAR The Sounds of Speech |
| PDF 106 (printed 85) | 4 THE LETTER KILLS Writing in English |
| PDF 114 (printed 93) | English Literacy and Australian Citizenship |
| PDF 118 (printed 97) | Anindilyakwa Uses of English Literacy |
| PDF 129 (printed 108) | 5 THE MAMARIKA WINDS Turning to Anindilyakwa |
| PDF 148 (printed 127) | 6 SPEAKING TO THE HEART The Language of Faith |
| PDF 159 (printed 138) | Anindilyakwa Ownership of the Heart Language |
| PDF 167 (printed 146) | 7 SINGING IN TONGUES Translation through Song |

### 4. Lists and tables

- Flattened table on PDF 3 (printed iii): "hn | hk | io | il | sy | SY | ek | eh / hn | hk | io | il | sy | SY | ek | eh" (stray token block, not a table)
- Flattened table on PDF 13 (printed xiii): "hn | hk | io | il | sy | SY | ek | eh / hn | hk | io | il | sy | SY | ek | eh" (stray token block, not a table)
- Flattened table on PDF 193 (printed 172): "hn | hk | io | il | sy | SY | ek | eh / hn | hk | io | il | sy | SY | ek | eh" (stray token block, not a table)
- Flattened table on PDF 23 (printed 2): "hn | hk | io | il | sy | SY | ek | eh / hn | hk | io | il | sy | SY | ek | eh" (stray token block, not a table)
- Flattened table on PDF 207 (printed 186): "hn | hk | io | il | sy | SY | ek | eh / hn | hk | io | il | sy | SY | ek | eh" (stray token block, not a table)
- Flattened table on PDF 129 (printed 108): "hn | hk | io | il | sy | SY | ek | eh / hn | hk | io | il | sy | SY | ek | eh" (stray token block, not a table)
- Flattened table on PDF 61 (printed 40): "hn | hk | io | il | sy | SY | ek | eh / hn | hk | io | il | sy | SY | ek | eh" (stray token block, not a table)
- Flattened table on PDF 35 (printed 14): "hn | hk | io | il | sy | SY | ek | eh / hn | hk | io | il | sy | SY | ek | eh" (stray token block, not a table)
- Flattened table on PDF 247 (printed 226): "hn | hk | io | il | sy | SY | ek | eh / hn | hk | io | il | sy | SY | ek | eh" (stray token block, not a table)
- Flattened table on PDF 253 (printed 232): "hn | hk | io | il | sy | SY | ek | eh / hn | hk | io | il | sy | SY | ek | eh" (stray token block, not a table)
- Flattened table on PDF 255 (printed 234): "hn | hk | io | il | sy | SY | ek | eh / hn | hk | io | il | sy | SY | ek | eh" (stray token block, not a table)
- Header cells marked by the AI on PDF 27 (printed 6): 2 header row(s), 0 header column(s), 3 cells changed to header cells. Check they are the real headers.

Tables kept as tables (1): check header cells and reading order.

- PDF 27 (printed 6): 18 rows × 2 columns, 0 header cells. "Table 1 Anindilyakwa Clans"

### 5. Text a screen reader could not reach (before this run)

111 pages had text outside the tag tree: 6216 orphan runs (marked, but no tag owns them) and 0 untagged runs. Running heads and page numbers among them can be hidden as decoration; real content must be added to the tag tree by a person. After this run: 0 untagged characters, 0 orphan runs remain.

Pages: PDF 15 (printed xv), PDF 19 (printed xix), PDF 25 (printed 4), PDF 27 (printed 6), PDF 29 (printed 8), PDF 31 (printed 10), PDF 33 (printed 12), PDF 37 (printed 16), PDF 39 (printed 18), PDF 41 (printed 20), PDF 43 (printed 22), PDF 45 (printed 24), PDF 47 (printed 26), PDF 49 (printed 28), PDF 51 (printed 30), PDF 53 (printed 32), PDF 55 (printed 34), PDF 57 (printed 36), PDF 59 (printed 38), PDF 63 (printed 42), PDF 65 (printed 44), PDF 67 (printed 46), PDF 69 (printed 48), PDF 71 (printed 50), PDF 73 (printed 52), PDF 75 (printed 54), PDF 77 (printed 56), PDF 79 (printed 58), PDF 81 (printed 60), PDF 83 (printed 62), PDF 85 (printed 64), PDF 87 (printed 66), PDF 89 (printed 68), PDF 91 (printed 70), PDF 93 (printed 72), PDF 95 (printed 74), PDF 97 (printed 76), PDF 99 (printed 78), PDF 101 (printed 80), PDF 103 (printed 82), PDF 105 (printed 84), PDF 107 (printed 86), PDF 109 (printed 88), PDF 111 (printed 90), PDF 113 (printed 92), PDF 115 (printed 94), PDF 117 (printed 96), PDF 119 (printed 98), PDF 121 (printed 100), PDF 123 (printed 102), PDF 125 (printed 104), PDF 127 (printed 106), PDF 131 (printed 110), PDF 133 (printed 112), PDF 135 (printed 114), PDF 137 (printed 116), PDF 139 (printed 118), PDF 141 (printed 120), PDF 143 (printed 122), PDF 145 (printed 124), PDF 147 (printed 126), PDF 149 (printed 128), PDF 151 (printed 130), PDF 153 (printed 132), PDF 155 (printed 134), PDF 157 (printed 136), PDF 159 (printed 138), PDF 161 (printed 140), PDF 163 (printed 142), PDF 165 (printed 144), PDF 167 (printed 146), PDF 169 (printed 148), PDF 171 (printed 150), PDF 173 (printed 152), PDF 175 (printed 154), PDF 177 (printed 156), PDF 179 (printed 158), PDF 181 (printed 160), PDF 183 (printed 162), PDF 185 (printed 164), PDF 187 (printed 166), PDF 189 (printed 168), PDF 191 (printed 170), PDF 195 (printed 174), PDF 197 (printed 176), PDF 199 (printed 178), PDF 201 (printed 180), PDF 203 (printed 182), PDF 205 (printed 184), PDF 209 (printed 188), PDF 211 (printed 190), PDF 213 (printed 192), PDF 215 (printed 194), PDF 217 (printed 196), PDF 219 (printed 198), PDF 221 (printed 200), PDF 223 (printed 202), PDF 225 (printed 204), PDF 227 (printed 206), PDF 229 (printed 208), PDF 231 (printed 210), PDF 233 (printed 212), PDF 235 (printed 214), PDF 237 (printed 216), PDF 239 (printed 218), PDF 241 (printed 220), PDF 243 (printed 222), PDF 245 (printed 224), PDF 249 (printed 228), PDF 251 (printed 230), PDF 257 (printed 236)

### 6. Hidden from screen readers (artifacts)

- 1 decorative elements ("duplicate whole-page figure of the title page (PDF 4); the title-page text is tagged and the other whole-page Figure carries the alt text") on PDF 4 (printed iv)
- "stray two-letter token blocks (tagged), not real content": text matching `hn|hk|io|il|sy|SY|ek|eh` on PDF 1–257 (printed i–236)
- "stray two-letter token blocks (orphans), not real content": text matching `hn|hk|io|il|sy|SY|ek|eh` on PDF 1–257 (printed i–236)
- "running head, notes": text matching `\d* ?Notes to Pages \d+–\d+ ?\d*` on PDF 207–231 (printed 186–210)
- "running head page number, notes": text matching `\d+` on PDF 207–231 (printed 186–210)
- "running head, Preface": text matching `(\d+|[ivxlc]+)|((\d+ |[ivxlc]+ )?(Preface|Acknowl ?edgments|Introduction|Chapter 1|Meetings|Index)( \d+| [ivxlc]+)?)` on PDF 13 (printed xiii)
- "running head, Acknowledgments": text matching `(\d+|[ivxlc]+)|((\d+ |[ivxlc]+ )?(Preface|Acknowl ?edgments|Introduction|Chapter 1|Meetings|Index)( \d+| [ivxlc]+)?)` on PDF 16 (printed xvi)
- "running head, Introduction": text matching `(\d+|[ivxlc]+)|((\d+ |[ivxlc]+ )?(Preface|Acknowl ?edgments|Introduction|Chapter 1|Meetings|Index)( \d+| [ivxlc]+)?)` on PDF 23–24 (printed 2–3)
- "running head, Chapter 1": text matching `(\d+|[ivxlc]+)|((\d+ |[ivxlc]+ )?(Preface|Acknowl ?edgments|Introduction|Chapter 1|Meetings|Index)( \d+| [ivxlc]+)?)` on PDF 35–36 (printed 14–15)
- "running head, Index": text matching `(\d+|[ivxlc]+)|((\d+ |[ivxlc]+ )?(Preface|Acknowl ?edgments|Introduction|Chapter 1|Meetings|Index)( \d+| [ivxlc]+)?)` on PDF 247–248 (printed 226–227)
- "folio at chapter opening and section opening pages": text matching `[ivxlc]+|\d+` on PDF 10 (printed x)
- "folio at chapter opening pages": text matching `[ivxlc]+|\d+` on PDF 22 (printed 1)
- "folio at chapter opening pages": text matching `[ivxlc]+|\d+` on PDF 34 (printed 13)
- "folio at chapter opening pages": text matching `[ivxlc]+|\d+` on PDF 129 (printed 108)
- "folio at chapter opening pages": text matching `[ivxlc]+|\d+` on PDF 193 (printed 172)
- "folio at notes opening page": text matching `[ivxlc]+|\d+` on PDF 206 (printed 185)
- "folio at index opening page": text matching `[ivxlc]+|\d+` on PDF 246 (printed 225)

### 7. Reading order changes

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

### 8. Untagged paths (rules, borders, lines)

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

### 9. Spoken text (ActualText) checked against the print (11 accepted with differences, 0 rejected)

A spoken text may differ from the printed characters only in spacing, letter case and line-end hyphens (sponsor rule 1). Accepted ones that differ are listed so a person can listen to them; rejected ones added or changed words or punctuation.

- Accepted, PDF 34 (printed 13): printed "1 MEETINGS New Meanings on Southern Shores" → spoken "1 MEETINGS New Meanings on Southern Shores"
- Accepted, PDF 52 (printed 31): printed "2 TRANSLATING THE LANDSCAPE Negotiating the Mission" → spoken "2 TRANSLATING THE LANDSCAPE Negotiating the Mission"
- Accepted, PDF 82 (printed 61): printed "3 EARS TO HEAR The Sounds of Speech" → spoken "3 EARS TO HEAR The Sounds of Speech"
- Accepted, PDF 106 (printed 85): printed "4 THE LETTER KILLS Writing in En glish" → spoken "4 THE LETTER KILLS Writing in English"
- Accepted, PDF 114 (printed 93): printed "En glish Literacy and Australian Citizenship" → spoken "English Literacy and Australian Citizenship"
- Accepted, PDF 118 (printed 97): printed "Anindilyakwa Uses of En glish Literacy" → spoken "Anindilyakwa Uses of English Literacy"
- Accepted, PDF 129 (printed 108): printed "5 THE MAMARIKA WINDS Turning to Anindilyakwa" → spoken "5 THE MAMARIKA WINDS Turning to Anindilyakwa"
- Accepted, PDF 148 (printed 127): printed "6 SPEAKING TO THE HEART The Language of Faith" → spoken "6 SPEAKING TO THE HEART The Language of Faith"
- Accepted, PDF 159 (printed 138): printed "Anindilyakwa Owner ship of the Heart Language" → spoken "Anindilyakwa Ownership of the Heart Language"
- Accepted, PDF 167 (printed 146): printed "7 SINGING IN TONGUES Translation through Song" → spoken "7 SINGING IN TONGUES Translation through Song"
- Accepted, page: not on this tag: printed "Acknowl edgments" → spoken "Acknowledgments"

### 10. Empty tags (727 removed, 0 kept)

A tag is removed only when proven empty: nothing under it holds content, it carries no Alt, ActualText, E or ID, and nothing in the file refers to it except its parent. Table cells are never removed one by one; a table goes only when every part is empty.

- Removed: 616 P, 88 Div, 11 NormalParagraphStyle, 11 Story, 1 SERED
- 704 of them were empty parts of tables or lists the work order flattened (e.g. cells whose content had been hidden as decoration)

### 11. veraPDF (WCAG 2.2 machine profile), before and after

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

### 12. WCAG checks veraPDF does not make

Each item is something to look at, not a proven failure.

- 1.3.2 the reading order jumps back up the same column on 1 page. Listen through them with a screen reader (or the PAC screen-reader preview): PDF 10 (printed x) (7 jumps)

### 13. Deferred by the AI

- **Stray token blocks (hn hk io il sy SY ek eh) on many pages, as orphan runs, tagged paragraphs and 11 tables, treated as junk and artifacted**: They are not meaningful text, but a person should confirm nothing real was hidden and that no empty tags remain (veraPDF 7.1-3 failures may remain where content is neither tagged nor artifact) [PDF 3 (printed iii), PDF 257 (printed 236)]
- **veraPDF 7.1-3: the 1653 unmarked-content failures**: Only runs matching the artifact rules are fixed. Any remaining untagged page content on PDF 1 and 3 needs a person. [PDF 1 (printed i), PDF 3 (printed iii)]
- **Running heads and folios other than those targeted**: Only the pages whose running heads or folios appear in the digest are covered. Page numbers on other pages could not be identified from the digest. [PDF 13 (printed xiii), PDF 248 (printed 227)]
- **Anindilyakwa text (epigraphs, hymns, quotations) has no language tag**: No reliable BCP 47 code is given in the digest, so a person should decide whether to tag these runs [PDF 34 (printed 13), PDF 193 (printed 172)]
- **Duplicate whole-page Figures on the title page and series page (PDF 3, PDF 4)**: The title-page text is tagged and also covered by a whole-page Figure. 7003 0 was given alt text and 7004 0 artifacted. A person should check how the page reads. [PDF 3 (printed iii), PDF 4 (printed iv)]
- **Chapter heading merges (number + title + subtitle)**: The merged headings carry ActualText. A person should check heading text and the outline. [PDF 34 (printed 13), PDF 167 (printed 146)]
- **Contents entry 'Note on Terminology and Language xv ii' has a garbled page number**: The text layer reads 'xv ii'; this may need a person to fix [PDF 10 (printed x)]

Reviewer note from the AI: Heading outline: the book title (TPT, PDF 4) is H1. Front and back matter titles, Introduction, Conclusion, Epilogue, and the merged chapter number/title/subtitle headings are H2. The publisher's H1-styled section headings are mapped to H3, as are the endnote chapter headings and the bibliography subheadings. The table on PDF 27 is given two header rows (title row plus column heads). Photo captions use the CAP style and are tied to their figures. Alt text was written from the figure images and captions. The 'hn hk io il…' blocks are treated as junk and hidden, then flattened tables are emptied and removed.

### 14. Deferred by the executor

- text rule "stray two-letter token blocks (orphans), not real content" matched no text on PDF 1–257 (printed i–236): nothing was hidden by this rule; check its pattern against the page (spacing, split runs)

## What was changed

| Change | Count |
|---|---:|
| document: marked as tagged | 1 |
| document: DisplayDocTitle | 2 |
| artifact: "stray two-letter token blocks (tagged), not real content" (inside a shared form XObject) | 616 |
| artifact: "duplicate whole-page figure of the title page (PDF 4); the title-page text is tagged and the other whole-page Figure carries the alt text" | 1 |
| artifact: "folio at chapter opening and section opening pages" | 1 |
| artifact: "running head, Preface" | 2 |
| artifact: "running head, Acknowledgments" | 3 |
| artifact: "folio at chapter opening pages" | 4 |
| artifact: "running head, Introduction" | 5 |
| artifact: "running head, Chapter 1" | 5 |
| artifact: "folio at notes opening page" | 1 |
| artifact: "running head page number, notes" | 50 |
| artifact: "folio at index opening page" | 1 |
| artifact: "running head, Index" | 5 |
| document: title | 1 |
| document: /Lang | 1 |
| heading: RoleMap level | 9 |
| heading: merged into next | 7 |
| heading: merged into prev | 7 |
| heading: ActualText | 11 |
| heading: standard tag H1 → H3 (retyped) | 38 |
| flatten: false table → paragraphs | 11 |
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
| structure: empty tag removed (proven empty) | 727 |
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
