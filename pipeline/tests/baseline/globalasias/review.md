# Remediation Review: globalasias.pdf

Result: `globalasias_remediated.pdf`

393 pages · run November 11, 2026, at 4:40 PM · model `anthropic/claude-sonnet-5.5` · prompt `workorder_v10.md` (15b5aa0ade9c6549) · AI cost $0.238 ($0.0006 per page), from the original AI request on November 3, 2026 · this run: no new AI request · tokens: saved reply reused, not counted

Intake: none (already tagged)

Libraries: python 3.14.4 · pikepdf 10.5.1 · pdfplumber 0.11.9 · pypdfium2 5.7.1 · pillow 13.0.0 · fonttools 4.62.1

Time: intake 0.5s · audit 49.5s · reuse saved reply 0.9s · apply 46.7s · verify 53.8s · total 151.4s

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
**AI decisions:** 41 in the work order, applied without review by a person  
**Fixed automatically (no AI):** links tied and described 4,247 · tag-tree index entries 242 · link descriptions that were only a URL 19 · Document root 1 · title shown in the window 1 · empty tags removed 1  
**veraPDF (WCAG 2.2 machine checks):** 0 WCAG rules failing before (0 checks) → 0 after (0 checks) · 0 newly failing

Automated checks are evidence, not sign-off.

| Top issues | Pages | Where |
|---|---|---|
| Figures: none below 150 ppi: 20 figures below 150 ppi, likely to look blurry: 96 ppi on PDF 25 (printed 10); 96 ppi on PDF 42 (printed 27); 96 ppi on PDF 67 (printed 52); 96 ppi on PDF 72 (printed 57); 96 ppi on PDF 74 (printed 59); 96 ppi on PDF 86 (printed 71); 96 ppi on PDF 88 (printed 73); 96 ppi on PDF 119 (printed 104); 96 ppi on PDF 138 (printed 123); 96 ppi on PDF 177 (printed 162); 96 ppi on PDF 178 (printed 163); 96 ppi on PDF 241 (printed 226); 96 ppi on PDF 297 (printed 282); 96 ppi on PDF 313 (printed 298); 96 ppi on PDF 313 (printed 298); 96 ppi on PDF 313 (printed 298); 96 ppi on PDF 318 (printed 303); 96 ppi on PDF 334 (printed 319); 96 ppi on PDF 336 (printed 321); 96 ppi on PDF 336 (printed 321) · a person puts in a sharper copy by hand, where one exists | 17 pages, PDF 25 (printed 10) to PDF 336 (printed 321) | [Automated Checks](#automated-checks) |
| Executor applied every decision: 6 rejected · 0 failed (listed under "Decisions not applied") | see §11 | [§11](#11-decisions-not-applied-6) |
| 35 Han-only runs need Japanese or Chinese (han_review.csv) | 18 pages, PDF 52 (printed 37) to PDF 363 (printed 348) | [§10](#10-deferred-by-the-executor) |
| Two Hangul (Korean) runs are not language-tagged | PDF 177 (printed 162) | [§9](#9-deferred-by-the-ai) |
| Index entries: page-number strings are extracted out of order or missing (e.g. “Aboriginal Australians, , ,… | PDF 368 (printed 353), PDF 386 (printed 371) | [§9](#9-deferred-by-the-ai) |
| … and 3 more | | §9 |

Automated checks are evidence, not legal sign-off. Items marked **CHECK**, and everything under "For a person to check", need a human.

## Automated Checks

| Check | Result | Detail |
|---|---|---|
| Every page looks the same as the original | OK | 0 pages differ |
| Published text unchanged | OK | 0 pages changed |
| All content tagged or marked as decoration | OK | 0 untagged characters · 0 untagged objects |
| Untagged paths: none left | OK | 0 untagged paths |
| Invisible OCR text: every glyph defined | OK | no undefined glyphs in invisible text |
| Page-level figure wrap | OK | no page with only an untagged drawing |
| Figures: none below 150 ppi | **CHECK** | 20 figures below 150 ppi, likely to look blurry: 96 ppi on PDF 25 (printed 10); 96 ppi on PDF 42 (printed 27); 96 ppi on PDF 67 (printed 52); 96 ppi on PDF 72 (printed 57); 96 ppi on PDF 74 (printed 59); 96 ppi on PDF 86 (printed 71); 96 ppi on PDF 88 (printed 73); 96 ppi on PDF 119 (printed 104); 96 ppi on PDF 138 (printed 123); 96 ppi on PDF 177 (printed 162); 96 ppi on PDF 178 (printed 163); 96 ppi on PDF 241 (printed 226); 96 ppi on PDF 297 (printed 282); 96 ppi on PDF 313 (printed 298); 96 ppi on PDF 313 (printed 298); 96 ppi on PDF 313 (printed 298); 96 ppi on PDF 318 (printed 303); 96 ppi on PDF 334 (printed 319); 96 ppi on PDF 336 (printed 321); 96 ppi on PDF 336 (printed 321) · a person puts in a sharper copy by hand, where one exists |
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
| Headings: no skipped levels | OK | H1 1 · H2 17 · H3 26 · H4 53 · H5 51 |
| Headings: exactly one H1 (the title) | OK | 1 H1 (several H1s usually mean parts or chapters were not demoted) |
| Figures: none with empty or placeholder alt | OK | 22 figures, 0 placeholder |
| Every Note has a unique ID | OK | 0 notes · 0 without ID · 0 duplicate · 0 not in the ID tree |
| Bookmarks present (documents over 9 pages) | OK | 84 bookmarks |
| Model reply held one work order | OK | one |
| Executor applied every decision | **CHECK** | 6 rejected · 0 failed (listed under "Decisions not applied") |
| Nothing deferred by the executor | **CHECK** | 2 deferred (listed under "Deferred by the executor") |
| Fonts: every glyph defined (no .notdef) | OK | none found |
| Fonts: every embedded font program could be read | OK | all read |
| Fonts: embedded and mapped to Unicode | OK | 0 not embedded · 0 without ToUnicode |
| Tab order follows the tag structure on pages with links or other annotations | OK | 0 of 187 pages with annotations lack /Tabs /S |
| Characters with no Unicode value (checklist 3.6) | OK | 0 read-aloud characters with no Unicode value |
| Private-use characters (checklist 3.6) | OK | 0 read-aloud characters with private-use codes |
| Title and language set | OK | "Global Asias: Tactics & Theories" · en-US |
| veraPDF WCAG 2.2 (machine): no WCAG failures | OK | before: 0 WCAG rules failed (0 checks) → after: 0 WCAG rules failed (0 checks) · 1 PDF/UA-only rules not counted |
| veraPDF: no rule newly failing or failing more often | OK | 0 fixed · 1 still failing · 0 newly failing |
| Alt text: none like a file name or repeated on many figures (1.1.1) | OK | 0 of 22 figures flagged |
| Tables: every table has header cells (1.3.1) | OK | none without |
| Reading order: no page jumps back up a column (1.3.2) | OK | 0 of 376 pages flagged |
| Reading order: no section moved away from its printed place by this run (1.3.2) | OK | 0 new · 1 already in the original, of 22 sections and blocks |
| Title is not a file name or placeholder (2.4.2) | OK | "Global Asias: Tactics & Theories" |
| Link text: none like "click here" (2.4.4) | OK | 0 generic |
| Headings: none empty, very long or repeated in a row (2.4.6) | OK | 0 empty · 0 long · 0 repeated |

## For a Person to Check

### 1. Alt Text Written or Changed by the AI (22)

| Page | Before | After |
|---|---|---|
| PDF 1 (printed Cover) | Global Asias: Tactics & Theories, edited by Tina Chen and Charlotte Eubanks. Cover image shows a Mattang navigation chart, a stick chart made by a Marshallese creator. The chart is in the shape of a square, with interwoven sticks in both straight and curved lines.\x00 | Cover of Global Asias: Tactics & Theories, edited by Tina Chen and Charlotte Eubanks. At the top left on a black background is a Marshallese mattang navigation chart, a square lattice of straight and curved sticks with two small shells. A light blue band across the middle carries the title and subtitle. Blue concentric curves and green vertical stripes fill the right-hand corners. |
| PDF 5 (printed iv) | Logo\x00 | Creative Commons logo for the Attribution-NonCommercial-NoDerivatives (CC BY-NC-ND) license. |
| PDF 25 (printed 10) | black text on white background, detailing time zones, and daily shedule for conference | Timeline graphic of the project's collaborative journey, with time zones (GMT+8, GMT+1, GMT, GMT-5, GMT-6, GMT-8) across the top above a wavy line. Eight stages follow from summer 2021 to fall 2022: Make Craft; Embarking; Waypoint: Sounding; Waypoint: Bearing; Waypoint: Deviation; Drifting/Drafting; Parallax; Voyaging. Each has a short description of the team's tasks, from setting keywords and forming teams to drafting research forums and pedagogical materials and submitting the final draft to the press. |
| PDF 42 (printed 27) | long banner with white background and random patches of black, purple, brown, and red runnning its length | Rirkrit Tiravanija, Untitled 2008–2011 (the map of the land of feeling). Three horizontal strips of paper are stacked, each covered in dense black line drawings, maps and patterns. A purple band runs along the length of each strip. Red triangles and circles, a red maze-like square, a red street grid and black concentric contour shapes are scattered across the strips. |
| PDF 67 (printed 52) | Spilhaus World Ocean Map based on the Spilhause projection world oceans form a singular, contiguous and connected body of water | Spilhaus World Ocean Map. In this projection the world's oceans form one continuous body of blue water, with the continents (North and South America, Europe, Africa, Asia, Australia, Antarctica) as separate pale shapes around its edges. The Atlantic, Pacific, Southern and Arctic Oceans are labeled. Places from the chapter are marked, including Kochi, Palestine, Việt Nam, Guåhan, South Korea, Tokyo, Hawaiʻi, Alaska, British Columbia, Tulare County and the US South. |
| PDF 72 (printed 57) | flyer format for meeting notes, green, blue, and white text on grey background | Slide of meeting notes titled “Meeting 2: Feb 22 at noon PT (3pm ET)” on a dark grey background. The task is to figure out what pedagogical resources the team wants to develop. Headings and bulleted notes cover “Questions and conversations” (using transits to understand syllabi and courses), “What are we hoping to disrupt?” (linearity, singularity, imposed rigid structure) and “What does it look like?” (student choice in readings, mapping exercises, a podcast exercise, multiple syllabi, course and program structures). |
| PDF 74 (printed 59) | definition of transire in black and white text | Etymology of “transit” on a white page headed “Interlude.” Latin trans (across, beyond) plus ire (to go) gives transire (cross over, go over, pass over, pass away) and transitus (going over, a passage). The noun transit is dated mid-15th century: the act of passing across or through. The verb transit is listed with two senses. 1. To be in motion: transplant, transgress, transfer (move or transfer); translate, transpose, transect (change sequence); transfuse, transpire (change form); transmigrate, transmute, transmogrify (transform entirely). 2. To be motionless: transfix (to be still with shock, horror or awe). |
| PDF 86 (printed 71) | Confederate flags juxtaposed with South Vietnamese flags at the January 6 insurrection. | Photograph by Evelyn Hockstein of the January 6, 2021 attack on the US Capitol. A huge US flag hangs from scaffolding in front of the Capitol dome. Among the many smaller flags are Confederate flags alongside the yellow-and-red-striped flag of South Vietnam. A crowd gathers at the base. |
| PDF 88 (printed 73) | white and purple sheets of paper with text hanging on wires in wooden room | Installation by Hương Ngô, And we are still here . . . but we are still here (2021). White and purple sheets of paper printed with text hang from wires across a room with a wooden ceiling. One sheet reads “We are still here”; others carry the same words in Vietnamese, such as “Chúng tôi vẫn ở đây.” |
| PDF 119 (printed 104) | Illustration of adult man in red shirt and short pants smiling at woman in purple gown on a white background with floral design border. | Watercolor illustration from the “Sino-Spanish Codex” (Boxer Codex), labeled “Naturales Tagalos.” A man in a red tunic and short red trousers with gold chains and a red headband stands beside a woman in a long purple gown with gold trim and a dark shawl. A border of flowers, birds and small animals surrounds the scene. |
| PDF 138 (printed 123) | Middle aged woman in blue suit stands behind next to middle aged man behind a second podium against a background of text  | Photograph of the 2016 apology ceremony at Taiwan's Presidential Office. President Tsai Ing-wen stands at a podium at left, facing an Indigenous man in a pink cap and striped shirt at a second podium at right. The backdrop is covered in the names of Indigenous peoples of Taiwan and shows large gold Chinese characters and the year 2016, with the words for truth and reconciliation. |
| PDF 177 (printed 162) | Black text on white background in two columns. One column in Japanese script, one in English. On second page same design, one column in English the other in Arabic. Final column beneath these in English. | Page of poetry in two columns. At left, in English, is “Murmurs as Political Thought (or, A Political Theory of Murmurs): In Search of Ways to See the Sorrow and Things Hidden,” by Lee Chonghwa, with a poem titled “Bē/Boat” about things we don't know and words that cannot be consumed. The Korean word “bē” means a person's stomach and the Japanese word “boat.” At right is the same text in Japanese. The poem ends “Nation-state • Ethnos/Race • Man • Woman.” |
| PDF 178 (printed 163) | Black text on white background in two columns. One column in Japanese script, one in English. On second page same design, one column in English the other in Arabic. Final column beneath these in English. | Page with three texts. At top left, in English, is “The Passport” by Mahmoud Darwish, in which the speaker is not recognized in the shadows and asks that the birds, wheat fields, prisons and eyes not be dropped from the passport. Its Arabic original is in the right column. Below, centered, is “Mirror Words” by Don Mee Choi, a prose piece on translation as an anti-neocolonial mode that creates “mirror words” which compel disobedience. |
| PDF 241 (printed 226) | Black text on white background split into columns on left and right side of page. Divided by dotted black line running down the middle of the page. | Two facing pages divided by a dotted vertical line, with short lines of a poem and vertical ellipsis marks between them. Left page: “No language is old—or young—beyond English. So what of a common tongue beyond English?” and “I know some words for war, all of them sharp, but the sharpest one is jung—beyond English!” Right page: “Heartbroken, I tottered out ‘into the windless snow,’ Snowflakes on my lips, silence stung beyond English.” It is attributed to “Beyond English,” Agha Shahid Ali (1949–2001). |
| PDF 297 (printed 282) | A blue orb with yellow flecks and an orange orb rest against a grey background, bordered in yellow. | Jill Samuels, New Roots/New Routes, 2022. A mixed-media painting on a dark blue-grey ground edged in yellow and purple. At left a blue orb with yellow flecks and a small pale blue shape, and at right an orange orb with a dark blue wedge. Thin red-brown vertical lines cross both shapes and a white line runs beside the orange one. |
| PDF 313 (printed 298) | Three maps depict the territory of Kashmir, each showing Kashmir as an extension of either China, Pakistan, or India. | Map titled “The Kashmir region from a Chinese perspective.” Kashmir is split by a dashed Line of Control into Pakistan-administered Kashmir (north-west) and Indian-administered Kashmir (south). Aksai Chin and the Shaksgam Valley are shaded the same brown as China, and the Siachen Glacier is marked. Afghanistan, Pakistan, India and China are labeled, and an inset shows China. |
| PDF 313 (printed 298) | Three maps depict the territory of Kashmir, each showing Kashmir as an extension of either China, Pakistan, or India. | Map titled “The Kashmir region from a Pakistani perspective.” Gilgit-Baltistan, Azad Jammu and Kashmir, Khyber Pakhtunkhwa and Punjab are shaded the same brown as Pakistan, with Jammu and Kashmir beyond the Line of Control hatched and labeled “Indian illegally occupied Jammu and Kashmir.” The border with China is marked “Frontier undefined.” The Siachen Glacier is marked, and an inset shows Pakistan. |
| PDF 313 (printed 298) | Three maps depict the territory of Kashmir, each showing Kashmir as an extension of either China, Pakistan, or India. | Map titled “The Kashmir region from an Indian perspective.” The whole of Kashmir, including Ladakh and Jammu and Kashmir (both Union territories), Aksai Chin and Gilgit-Baltistan, is shaded the same brown as the Indian Union, with Himachal Pradesh and Punjab to the south. The Line of Actual Control, Daulat Beg Oldie and the Siachen Glacier are marked, and an inset shows India. |
| PDF 318 (printed 303) | Map of the world showing Afro-Asian connections, with multiple lines indicating individuals who traveled to attend conferences.  | Rotated map of the world's northern hemisphere in grey, with green, yellow and red lines connecting conference sites. Marked points include the Asian Women's Conference, the Asian Socialist Conference, the Afro-Asian Writers' Conference, the Asian-African Conference, the Afro-Asian People's Solidarity Organisation Conference, the Second Afro-Asian People's Solidarity Organisation Conference and the All-Africa People's Conference. Thicker green lines show heavier travel to the Asian-African Conference and the Afro-Asian People's Solidarity Organisation conferences. |
| PDF 334 (printed 319) | A brick building at night illuminated by neon lights. Beside the entrace a neon sign reads "Pizza Hut." | Night photograph of a traditional Chinese-style brick building with a tiled roof edged in white lights. Red lanterns hang beside an illuminated wooden sign with Chinese characters above an open red door. A neon sign to the right reads “Pizza Hut.” |
| PDF 336 (printed 321) | A busy intesection with numerous cars and pedestrians crossing at a crosswalk in the foreground, a city scape in the background. | Photograph taken from above of a busy intersection in Flushing, Queens. Many pedestrians cross at a crosswalk in the foreground, cars wait at the light, and storefronts with Chinese and English signs line the far side, including “Modell's.” |
| PDF 336 (printed 321) | Beige brick building with three signs, one on top of the other, reading "Goon's 1 Stop", "Grocery and Sunderies", "Thank You Come Again." | Photograph of a low beige brick building with a large white sign reading “Goon's Package Store.” On a pole in front are three stacked signs: “Goon's Stop,” “Grocery and Sundries” and “Thank You Come Again.” Utility wires cross a blue sky above. |

### 2. Headings

Merged: `TPST` into the prev `TPT`

Spoken text set by the AI (should match what is printed):

| Page | Text |
|---|---|
| PDF 4 (printed iii) | Global Asias Tactics & Theories |
| PDF 28 (printed 13) | Editors’ Introduction Acts of Suspension |
| PDF 67 (printed 52) | Interleaf—Oceanic Transits |
| PDF 119 (printed 104) | Interleaf–“Naturales tagalos” |
| PDF 241 (printed 226) | Interleaf—“Beyond English” |
| PDF 297 (printed 282) | Interleaf—New Roots/New Routes |

### 3. Spoken Text (ActualText) Checked Against the Print (1 accepted with differences, 5 rejected)

A spoken text may differ from the printed characters only in spacing, letter case and line-end hyphens (sponsor rule 1). Accepted ones that differ are listed so a person can listen to them; rejected ones added or changed words or punctuation.

- Accepted, PDF 4 (printed iii): printed "Global Asias Tactics & Theories" → spoken "Global Asias Tactics & Theories"
- **Rejected**, PDF 28 (printed 13): printed "Editors’­Introduction Acts of Suspension" → spoken "Editors’ Introduction Acts of Suspension"
- **Rejected**, PDF 67 (printed 52): printed "Interleaf—O­ceanic­Transits" → spoken "Interleaf—Oceanic Transits"
- **Rejected**, PDF 119 (printed 104): printed "Interleaf–­“Naturales­tagalos”" → spoken "Interleaf–“Naturales tagalos”"
- **Rejected**, PDF 241 (printed 226): printed "Interleaf—­“Beyond­­English”" → spoken "Interleaf—“Beyond English”"
- **Rejected**, PDF 297 (printed 282): printed "Interleaf—New ­ ­Roots/New­Routes" → spoken "Interleaf—New Roots/New Routes"

### 4. Links Whose Description Was Only a URL (19)

The description (what a screen reader announces) was set to the book's own sentence around the link, with the URL removed. No words were added and the visible URL is unchanged. Replace any of these with a better description if needed.

| Page | URL | Description now |
|---|---|---|
| PDF 5 (printed iv) | https://lccn.loc.gov/2024017605 | LC record available at |
| PDF 5 (printed iv) | https://lccn.loc.gov/2024017606 | LC ebook record available at |
| PDF 5 (printed iv) | https://creativecommons.org/licenses/by-nc-nd/4.0/ | For details, see. |
| PDF 166 (printed 151) | https://ngaitahu.iwi.nz/ngai-tahu/the-settlement/settlement-offer/the-crowns-apology/ | Accessed September 11, 2023. |
| PDF 166 (printed 151) | https://www.indigenous.gov.au/reconciliation/apology-australias-indigenous-peoples | Accessed September 12, 2023. |
| PDF 166 (printed 151) | https://english.president.gov.tw/NEWS/4950 | “President Tsai Apologizes to Indigenous Peoples on Behalf of Government.” Accessed September 12, 2023. |
| PDF 345 (printed 330) | https://www.thisamericanlife.org/664/the-room-of-requirement/act-one-5 | Podcast, 7:00. |
| PDF 346 (printed 331) | https://www.antiatlas-journal.net/01-border-art-and-the-borders-of-art/ | “Border Art and Borders of Art, an Extra-disciplinary Approach.” antiAtlas Journal 1.On the border between art and knowledge, the map is a tool for explorers and world- builders. |
| PDF 346 (printed 331) | https://vimeo.com/64225987 | “Nothing to Declare.” Performance intro. |
| PDF 346 (printed 331) | https://www.jadaliyya.com/Details/29851 | “Nothing to Declare: A Review.” Jadaliyya. |
| PDF 347 (printed 332) | https://www.thefreelibrary.com/Defunt+railway+reflects+a+country+divided.-a0342683205 | F ree Library. |
| PDF 347 (printed 332) | https://www.thefreelibrary.com/Defunt+railway+reflects+a+country+divided.-a0342683205 | F ree Library. |
| PDF 350 (printed 335) | https://apdpkashmir.com/ | On the 10th of each month, families of the disappeared come together under the a egis of APDP to hold a public protest in Srinagar to commemorate the disappearance of their loved ones and to seek answers from the state about the whereabouts of the missing persons” (from APDP, “What We Do,”). |
| PDF 357 (printed 342) | https://www.sutori.com/en/item/kangnido-map-1402-europeans-were-not-the-only-ones-to-make-maps-in-fact-4144 | New York: Penguin Books. |
| PDF 357 (printed 342) | https://www.sutori.com/en/item/kangnido-map-1402-europeans-were-not-the-only-ones-to-make-maps-in-fact-4144 | Made in Kor ea. |
| PDF 357 (printed 342) | https://apjjf.org/-James-Orr/2692/article.html | Made in Japan. |
| PDF 357 (printed 342) | https://artsandculture.google.com/asset/four-large-cities-in-the-world-map-of-the-world-unknown-japanese-painter/NQFF3EzEWIpZyg | Made in Japan. |
| PDF 359 (printed 344) | https://digital.library.cornell.edu/catalog/ss:3293857 | Cornell University Library. |
| PDF 359 (printed 344) | https://fordschool.umich.edu/news/2021/anti-asian-hate-poverty-solutions-supports-u-m-chronicle-location-nature-more-1000 | Map of anti- Asian racism incidents since the COVID-19 pandemic. |

### 5. Empty Tags (1 removed, 0 kept)

A tag is removed only when proven empty: nothing under it holds content, it carries no Alt, ActualText, E or ID, and nothing in the file refers to it except its parent. Table cells are never removed one by one; a table goes only when every part is empty.

- Removed: 1 IX

### 6. Tag-tree Index Entries Cleared (242)

Entries that pointed at a tag no longer in the tag tree (left by the source file, or by a tag the run removed). Nothing reads such a tag; no page, text or reachable tag changed.

- ParentTree, PDF 3 (printed ii): MCID 4 (SERTF), MCID 5 (SEREDF), MCID 13 (SERED), MCID 15 (SERAU)
- ParentTree, PDF 4 (printed iii): MCID 25 (TPPUB)
- ParentTree, PDF 8 (printed vii): MCID 80 (Span), MCID 86 (Span), MCID 92 (CCST)
- ParentTree, PDF 9 (printed viii): MCID 111 (CCST), MCID 130 (CCST)
- ParentTree, PDF 10 (printed ix): MCID 164 (CCST)
- ParentTree, PDF 11 (printed x): MCID 182 (CCST), MCID 188 (Span)
- ParentTree, PDF 16 (printed 1): MCID 314 (CST)
- ParentTree, PDF 28 (printed 13): MCID 885 (CST)
- ParentTree, PDF 29 (printed 14): MCID 926 (INT_ATTR), MCID 928 (Span), MCID 929 (INT_QF), MCID 932 (INT_ATTR), MCID 933 (INT_QF), MCID 936 (INT_ATTR), MCID 937 (INT_QF), MCID 938 (INT_ATTR), MCID 940 (Span), MCID 942 (Span), MCID 943 (INT_QF), MCID 944 (INT_ATTR), MCID 946 (Span), MCID 949 (INT_QF), MCID 950 (INT_ATTR), MCID 951 (INT_QF), MCID 952 (INT_ATTR)
- ParentTree, PDF 30 (printed 15): MCID 954 (Span), MCID 958 (Span), MCID 960 (Span), MCID 962 (INT_ATTRL)
- ParentTree, PDF 32 (printed 17): MCID 1066 (Span), MCID 1068 (BL), MCID 1076 (BL), MCID 1081 (Span), MCID 1083 (BL), MCID 1085 (Span), MCID 1087 (BL), MCID 1090 (BL), MCID 1092 (Span), MCID 1098 (Span), MCID 1099 (BLL)
- ParentTree, PDF 68 (printed 53): MCID 3154 (Span), MCID 3155 (CT), MCID 3157 (Span), MCID 3159 (Span), MCID 3160 (CST), MCID 3162 (Span)
- ParentTree, PDF 70 (printed 55): MCID 3240 (Span), MCID 3243 (BL), MCID 3245 (Span), MCID 3248 (BLL)
- ParentTree, PDF 73 (printed 58): MCID 3351 (H2A)
- ParentTree, PDF 80 (printed 65): MCID 3711 (VF), MCID 3712 (V), MCID 3713 (V)
- ParentTree, PDF 81 (printed 66): MCID 3715 (V), MCID 3716 (V), MCID 3717 (VL), MCID 3720 (H2A)
- ParentTree, PDF 88 (printed 73): MCID 4154 (CAP)
- ParentTree, PDF 89 (printed 74): MCID 4162 (VF), MCID 4163 (V), MCID 4165 (V), MCID 4168 (V), MCID 4169 (V), MCID 4170 (VL), MCID 4173 (H2A)
- ParentTree, PDF 95 (printed 80): MCID 4510 (VF), MCID 4511 (V), MCID 4512 (V), MCID 4513 (V), MCID 4516 (V), MCID 4517 (V), MCID 4518 (V), MCID 4519 (V), MCID 4520 (V), MCID 4521 (VL)
- ParentTree, PDF 96 (printed 81): MCID 4524 (Span), MCID 4526 (H2A)
- ParentTree, PDF 109 (printed 94): MCID 5397 (Span), MCID 5403 (Span)
- ParentTree, PDF 112 (printed 97): MCID 5556 (Span), MCID 5557 (Span)
- ParentTree, PDF 120 (printed 105): MCID 5805 (Span), MCID 5806 (CT), MCID 5808 (CST), MCID 5810 (Span)
- ParentTree, PDF 121 (printed 106): MCID 5821 (TEPC), MCID 5829 (TEP2), MCID 5830 (TEPC), MCID 5834 (TEP2), MCID 5836 (TEPC)
- ParentTree, PDF 128 (printed 113): MCID 6237 (H2A)
- ParentTree, PDF 135 (printed 120): MCID 6601 (H2A)
- ParentTree, PDF 140 (printed 125): MCID 6915 (Span)
- ParentTree, PDF 142 (printed 127): MCID 7003 (H2A)
- ParentTree, PDF 147 (printed 132): MCID 7257 (H2A), MCID 7261 (TEPC)
- ParentTree, PDF 161 (printed 146): MCID 8153 (Span), MCID 8157 (Span), MCID 8162 (BL), MCID 8167 (BL), MCID 8170 (Span), MCID 8173 (BL), MCID 8188 (BL), MCID 8190 (P), MCID 8192 (P), MCID 8194 (P), MCID 8197 (P), MCID 8198 (P), MCID 8201 (P), MCID 8202 (P), MCID 8204 (P)
- ParentTree, PDF 179 (printed 164): MCID 9041 (Span), MCID 9042 (CT), MCID 9044 (CST), MCID 9046 (Span)
- ParentTree, PDF 180 (printed 165): MCID 9061 (H2A)
- ParentTree, PDF 183 (printed 168): MCID 9220 (H2A)
- ParentTree, PDF 189 (printed 174): MCID 9601 (H2A)
- ParentTree, PDF 196 (printed 181): MCID 10071 (H2A)
- ParentTree, PDF 197 (printed 182): MCID 10107 (ULF), MCID 10108 (ULL), MCID 10109 (TNI), MCID 10113 (ULF), MCID 10114 (UL), MCID 10115 (UL), MCID 10117 (UL2L), MCID 10118 (TNI), MCID 10120 (ULF), MCID 10126 (ULO), MCID 10127 (P), MCID 10128 (Span), MCID 10132 (Span), MCID 10134 (UL)
- ParentTree, PDF 198 (printed 183): MCID 10138 (UL), MCID 10140 (ULL)
- ParentTree, PDF 203 (printed 188): MCID 10425 (H2A)
- ParentTree, PDF 213 (printed 198): MCID 10977 (H2A), MCID 11006 (BL)
- ParentTree, PDF 214 (printed 199): MCID 11008 (BL), MCID 11009 (BL), MCID 11010 (Artifact), MCID 11011 (BLL)
- ParentTree, PDF 216 (printed 201): MCID 11152 (H2A), MCID 11166 (Span), MCID 11170 (Span), MCID 11173 (Span)
- ParentTree, PDF 217 (printed 202): MCID 11196 (Span)
- ParentTree, PDF 220 (printed 205): MCID 11473 (H2A)
- ParentTree, PDF 221 (printed 206): MCID 11486 (Span), MCID 11489 (Span), MCID 11495 (Span), MCID 11500 (Span)
- ParentTree, PDF 224 (printed 209): MCID 11698 (H2A), MCID 11707 (Span), MCID 11719 (Span), MCID 11726 (Span)
- ParentTree, PDF 227 (printed 212): MCID 11914 (H2A), MCID 11928 (Span), MCID 11930 (Span), MCID 11935 (Span), MCID 11944 (Span)
- ParentTree, PDF 230 (printed 215): MCID 12147 (H2A), MCID 12157 (Span), MCID 12166 (Span)
- ParentTree, PDF 231 (printed 216): MCID 12173 (Span), MCID 12176 (Span), MCID 12178 (Span)
- ParentTree, PDF 233 (printed 218): MCID 12379 (H2A)
- ParentTree, PDF 234 (printed 219): MCID 12393 (Span), MCID 12400 (Span), MCID 12402 (Span), MCID 12407 (Span), MCID 12410 (Span)
- ParentTree, PDF 236 (printed 221): MCID 12648 (H2A)
- ParentTree, PDF 237 (printed 222): MCID 12664 (Span), MCID 12673 (Span), MCID 12684 (Span), MCID 12689 (Span)
- ParentTree, PDF 239 (printed 224): MCID 12820 (Span), MCID 12830 (Span), MCID 12832 (Span)
- ParentTree, PDF 240 (printed 225): MCID 12836 (H2A)
- ParentTree, PDF 242 (printed 227): MCID 12892 (Span), MCID 12893 (CT), MCID 12894 (CST), MCID 12896 (Span)
- ParentTree, PDF 246 (printed 231): MCID 13091 (Span), MCID 13093 (H2A)
- ParentTree, PDF 252 (printed 237): MCID 13442 (H2A)
- ParentTree, PDF 261 (printed 246): MCID 13914 (Span), MCID 13916 (H2A)
- ParentTree, PDF 262 (printed 247): MCID 13990 (Span), MCID 13996 (EXULS), MCID 13999 (EXULS), MCID 14000 (EXULS), MCID 14003 (Span)
- ParentTree, PDF 276 (printed 261): MCID 14933 (H2A)
- ParentTree, PDF 281 (printed 266): MCID 15169 (H2A)
- ParentTree, PDF 286 (printed 271): MCID 15431 (H2A)
- ParentTree, PDF 288 (printed 273): MCID 15574 (Span)
- ParentTree, PDF 292 (printed 277): MCID 15811 (EXL), MCID 15823 (EXL)
- ParentTree, PDF 298 (printed 283): MCID 16132 (Span), MCID 16133 (CT), MCID 16135 (CST), MCID 16137 (Span)
- ParentTree, PDF 313 (printed 298): MCID 16897 (Span)
- ParentTree, PDF 324 (printed 309): MCID 17441 (H2A)
- ParentTree, PDF 329 (printed 314): MCID 17695 (H2A)
- ParentTree, PDF 333 (printed 318): MCID 17954 (H2A), MCID 17959 (TEPC)
- ParentTree, PDF 336 (printed 321): MCID 18083 (Span)
- ParentTree, PDF 346 (printed 331): MCID 18698 (Span), MCID 18750 (LBody), MCID 18764 (LBody), MCID 18765 (LBody)
- ParentTree, PDF 351 (printed 336): MCID 19041 (LBody), MCID 19050 (LBody), MCID 19051 (LBody)
- ParentTree, PDF 354 (printed 339): MCID 19187 (Span)
- ParentTree, PDF 355 (printed 340): MCID 19203 (Span)
- ParentTree, PDF 358 (printed 343): MCID 19386 (BL)
- ParentTree, PDF 359 (printed 344): MCID 19383 (Span)
- ParentTree, entries not tied to page content (annotations, forms, or keys nothing uses): key 152 MCID 5805 (Span), key 152 MCID 5806 (CT), key 152 MCID 5808 (CST), key 152 MCID 5810 (Span), key 434 MCID 12892 (Span), key 434 MCID 12893 (CT), key 434 MCID 12894 (CST), key 434 MCID 12896 (Span), key 514 MCID 16132 (Span), key 514 MCID 16133 (CT), key 514 MCID 16135 (CST)

### 7. veraPDF (WCAG 2.2 machine profile), Before and After

veraPDF 1.30.3, profile "WCAG 2.2 machine validation profile" (7da399cf5baa). Counts are failed checks; pages are from the first checks veraPDF lists for each rule, so a rule may fail on more pages. Rules that only PDF/UA requires are listed apart and do not count. "Who fixes" is who can act on the rule: the pipeline by itself, the AI through the work order, or only a person. **Newly failing** means this run broke something the original passed. Before: 0 rules failing (the AI can act on 0, the pipeline on 0, only a person on 0). After: 0.

PDF/UA-only, not required for WCAG (not counted):

- 7.21.5-1: glyph width consistency (2 checks, PDF 25 (printed 10), PDF 74 (printed 59)), still failing

### 8. WCAG Checks veraPDF Does Not Make

Each item is something to look at, not a proven failure.

- 1.3.2 1 section read away from its printed place, as in the original (this run did not move it). Listen through each where it is read, or move it with move_section:
  - PDF 1 (printed Cover): Article, read after PDF 386 (printed 371)

### 9. Deferred by the AI

- **Two Hangul (Korean) runs are not language-tagged**: The language key only covers kana; the exact runs (page, MCID) are not in the digest, so a human should tag them ko. [PDF 177 (printed 162)]
- **Index entries: page-number strings are extracted out of order or missing (e.g. “Aboriginal Australians, , , –, , 148 151 155156 300 301”, “442nd Infantry Regiment, – 8586”)**: A screen reader will speak the number ranges wrongly. Correcting about 780 entries with ActualText needs a person checking against the printed pages. [PDF 368 (printed 353), PDF 386 (printed 371)]
- **Caption of the Afro-Asian conference map has reversed, garbled text (“y la p ia dem . n ia as ro f a//:spt …”)**: The rotated caption extracts backwards. The printed text must be checked against the page before ActualText can be written. [PDF 318 (printed 303)]
- **Japanese poem and dialogue lines (EXVF, EXF) begin with an empty “()” and extract without spaces**: Needs a reader of Japanese to check the extracted text and its language tagging. [PDF 290 (printed 275), PDF 291 (printed 276)]
- **Han-only runs such as 原住民, 少数民族 and 本土民主前線 may be Chinese or Japanese**: They are ambiguous between languages and are left to the executor's automatic deferral to a human. [PDF 52 (printed 37), PDF 53 (printed 38), PDF 123 (printed 108), PDF 137 (printed 122), PDF 139 (printed 124), PDF 148 (printed 133), PDF 149 (printed 134), PDF 151 (printed 136), PDF 153 (printed 138)]

Reviewer note from the AI: The publisher's tagging is largely sound: headings run H1 > H2 (front and back matter, chapters, interleaves) > H3 (forums) > H4 (essays) > H5 (sections), lists, TOC and Notes are already tagged, and veraPDF reports no fixable failures. The work order does these things. (1) It sets the full title in the metadata and folds the H2 subtitle “Tactics & Theories” into the H1 title. (2) It replaces the placeholder alt text for the logo and the cover, both of which contained NUL characters. (3) It gives the three Kashmir maps and the two poetry pages distinct descriptions (they had duplicate alt text), and rewrites the others from the images. (4) It adds ActualText to the interleaf and introduction headings whose soft hyphens run words together. (5) It moves the cover figure (PDF 1) to the start of the reading order with move_section; please confirm. PDF 387–393 are blank. Front-matter pages vi, xiv and PDF 7, 15, 103 and 352 have no tagged text. I did not set sections.notes_pages because notes are at the end of each Convergence rather than in one block.

### 10. Deferred by the Executor

- **35 Han-only CJK runs** need a Japanese / Chinese decision: fill in `han_review.csv`.
- the source file already claims PDF/UA conformance: not verified by this pipeline; check it with PAC before relying on it

### 11. Decisions Not Applied (6)

Rejected by validation or by the executor; nothing was half-applied.

- {"op": "actual_text 18548 0", "why": "the spoken text adds or changes words or punctuation (sponsor rule 1): printed \"Editors’­Introduction Acts of Suspension\", spoken \"Editors’ Introduction Acts of Suspension\""}
- {"op": "actual_text 16322 0", "why": "the spoken text adds or changes words or punctuation (sponsor rule 1): printed \"Interleaf—O­ceanic­Transits\", spoken \"Interleaf—Oceanic Transits\""}
- {"op": "actual_text 18516 0", "why": "the spoken text adds or changes words or punctuation (sponsor rule 1): printed \"Interleaf–­“Naturales­tagalos”\", spoken \"Interleaf–“Naturales tagalos”\""}
- {"op": "actual_text 14996 0", "why": "the spoken text adds or changes words or punctuation (sponsor rule 1): printed \"Interleaf—New ­ ­Roots/New­Routes\", spoken \"Interleaf—New Roots/New Routes\""}
- {"op": "actual_text 16459 0", "why": "the spoken text adds or changes words or punctuation (sponsor rule 1): printed \"Interleaf—­“Beyond­­English”\", spoken \"Interleaf—“Beyond English”\""}
- {"op": "move_section", "why": "1 candidate sections, host found: False"}

## What Was Changed

| Change | Count |
|---|---:|
| document: second Document root merged | 1 |
| document: title | 1 |
| document: DisplayDocTitle | 1 |
| document: /Lang | 1 |
| document: empty AcroForm removed | 1 |
| heading: merged into prev | 1 |
| heading: ActualText | 1 |
| figure: alt text | 22 |
| language: ja on existing Span | 10 |
| language: ko on existing Span | 2 |
| links: /Contents set | 4247 |
| links: already tied to a Link inside the document | 218 |
| links: joined existing Link | 4029 |
| links: URL-only description replaced by the sentence around it | 19 |
| structure: empty tag removed (proven empty) | 1 |
| language: /Lang spelling tidied | 32 |
| tag tree index: entries pointing outside the tree cleared (ParentTree) | 242 |

## Accessibility Evaluation

A person evaluates this version of `globalasias_remediated.pdf` with PAC 2026 and a screen reader, on the app's "Accessibility Evaluation" page (or with manual_checks.py; docs/release.md). The "Ready to ship?" answer needs both parts. A Fail is recorded with its note and does not hold the book back. Each result is recorded against this version of the PDF (its sha256): after a new apply it no longer counts. The evaluation is a record of what a person found, not a legal certification.

**PAC 2026.** Open `globalasias_remediated.pdf` in PAC 2026 (https://pac.pdf-accessibility.org/en, Windows) and run its WCAG check. Anything it fails that is not listed above is a gap in the automated checks: note it in the issue tracker. Each item is Pass, Fail or Not Applicable, with notes:

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
