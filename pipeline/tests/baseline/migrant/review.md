# Remediation Review: migrant.pdf

Result: `migrant_remediated.pdf`

321 pages · run November 16, 2026, at 2:29 AM · model `anthropic/claude-sonnet-5.5` · prompt `workorder_v12.md` (762395b72330c407) · AI cost $0.241 ($0.0008 per page), from the original AI request on November 15, 2026 · this run: no new AI request · tokens: saved reply reused, not counted

Intake: none (already tagged)

Libraries: python 3.14.4 · pikepdf 10.5.1 · pdfplumber 0.11.9 · pypdfium2 5.7.1 · pillow 13.0.0 · fonttools 4.62.1

Time: intake 0.8s · audit 72.0s · reuse saved reply 1.0s · apply 127.9s · verify 78.3s · total 280.0s

## Overview

[Open the dashboard](review.html)

**Status:** Not Ready

**Ready to ship?**
- Work Order Approval: Not Approved (applied without a review)
- ✓ OCR Text Approval: Not Applicable
- ✓ Safety Checks: Passed
- Language Tags: Not Done (the language step was not run)
- Accessibility Evaluation: Not Completed

**Safety checks:** OK ✔ pages look the same · OK ✔ text unchanged · OK ✔ all content tagged or decoration · OK ✔ tag-tree index points into the tree · OK ✔ every font readable  
**Needs a person:** 14 (9 deferred by the AI · 0 deferred by the executor · 5 CHECK rows)  
**AI decisions:** 55 in the work order, applied without review by a person  
**Fixed automatically (no AI):** links tied and described 6,486 · note IDs 1,013 · tag-tree index entries 43 · figures moved to their page 20 · link descriptions that were only a URL 5 · Document root 1 · title shown in the window 1  
**veraPDF (WCAG 2.2 machine checks):** 0 WCAG rules failing before (0 checks) → 0 after (0 checks) · 0 newly failing

Automated checks are evidence, not sign-off.

| Top issues | Pages | Where |
|---|---|---|
| Figures: none below 150 ppi: 30 figures below 150 ppi, likely to look blurry: 96 ppi on PDF 11 (printed x); 96 ppi on PDF 12 (printed xi); 96 ppi on PDF 29 (printed 12); 96 ppi on PDF 31 (printed 14); 96 ppi on PDF 34 (printed 17); 96 ppi on PDF 50 (printed 33); 96 ppi on PDF 57 (printed 40); 96 ppi on PDF 72 (printed 55); 96 ppi on PDF 75 (printed 58); 96 ppi on PDF 78 (printed 61); 96 ppi on PDF 88 (printed 71); 96 ppi on PDF 89 (printed 72); 96 ppi on PDF 92 (printed 75); 96 ppi on PDF 108 (printed 91); 96 ppi on PDF 110 (printed 93); 96 ppi on PDF 111 (printed 94); 96 ppi on PDF 121 (printed 104); 96 ppi on PDF 126 (printed 109); 96 ppi on PDF 128 (printed 111); 96 ppi on PDF 135 (printed 118); and 10 more · a person puts in a sharper copy by hand, where one exists | 20 pages, PDF 11 (printed x) to PDF 135 (printed 118) | [Automated Checks](#automated-checks) |
| Every caption grouped with its figure: PDF 31 (printed 14) (caption inside Div), PDF 121 (printed 104) (caption inside Div), PDF 126 (printed 109) (caption inside Div), PDF 126 (printed 109) (caption inside Div), PDF 126 (printed 109) (caption inside Div), PDF 213 (printed 196) (caption inside Div), PDF 221 (printed 204) (caption inside Div) | 5 pages, PDF 31 (printed 14) to PDF 221 (printed 204) | [§8](#8-structure-left-for-a-person) |
| Executor applied every decision: 1 rejected · 0 failed (listed under "Decisions not applied") | see §12 | [§12](#12-decisions-not-applied-1) |
| Reading order jumps back up a column (6 jumps) | PDF 210 (printed 193), PDF 211 (printed 194) | [§9](#9-wcag-checks-verapdf-does-not-make) |
| Headings: none empty, very long or repeated in a row (2.4.6): 0 empty · 0 long · 6 repeated | see §9 | [§9](#9-wcag-checks-verapdf-does-not-make) |
| … and 9 more | | §10 |

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
| Figures: none below 150 ppi | **CHECK** | 30 figures below 150 ppi, likely to look blurry: 96 ppi on PDF 11 (printed x); 96 ppi on PDF 12 (printed xi); 96 ppi on PDF 29 (printed 12); 96 ppi on PDF 31 (printed 14); 96 ppi on PDF 34 (printed 17); 96 ppi on PDF 50 (printed 33); 96 ppi on PDF 57 (printed 40); 96 ppi on PDF 72 (printed 55); 96 ppi on PDF 75 (printed 58); 96 ppi on PDF 78 (printed 61); 96 ppi on PDF 88 (printed 71); 96 ppi on PDF 89 (printed 72); 96 ppi on PDF 92 (printed 75); 96 ppi on PDF 108 (printed 91); 96 ppi on PDF 110 (printed 93); 96 ppi on PDF 111 (printed 94); 96 ppi on PDF 121 (printed 104); 96 ppi on PDF 126 (printed 109); 96 ppi on PDF 128 (printed 111); 96 ppi on PDF 135 (printed 118); and 10 more · a person puts in a sharper copy by hand, where one exists |
| Empty tags removed when proven empty | OK | 0 removed |
| Tag-tree index points only into the tree | OK | 0 dangling entries · 0 stale entries (marked content no longer drawn) |
| No empty tables | OK | none |
| No empty tags | OK | 0 empty tags |
| No paragraph holding only figures | OK | none |
| Every caption grouped with its figure | **CHECK** | PDF 31 (printed 14) (caption inside Div), PDF 121 (printed 104) (caption inside Div), PDF 126 (printed 109) (caption inside Div), PDF 126 (printed 109) (caption inside Div), PDF 126 (printed 109) (caption inside Div), PDF 213 (printed 196) (caption inside Div), PDF 221 (printed 204) (caption inside Div) |
| No link whose only text is a URL | OK | none |
| Tag tree consistent | OK | 0 missing · 0 mismatched |
| All marked text reachable from the tag tree | OK | 0 orphan runs |
| One Document root | OK | Document 1 |
| Every link tied to its text and described | OK | 0 unresolved · 0 without description · 0 pointing to no annotation |
| No link nested inside another | OK | 0 |
| Headings: no skipped levels | OK | H1 1 · H2 66 |
| Headings: exactly one H1 (the title) | OK | 1 H1 (several H1s usually mean parts or chapters were not demoted) |
| Figures: none with empty or placeholder alt | OK | 35 figures, 0 placeholder |
| Every Note has a unique ID | OK | 1013 notes · 0 without ID · 0 duplicate · 0 not in the ID tree |
| Bookmarks present (documents over 9 pages) | OK | 22 bookmarks |
| Model reply held one work order | OK | one |
| Executor applied every decision | **CHECK** | 1 rejected · 0 failed (listed under "Decisions not applied") |
| Nothing deferred by the executor | **CHECK** | 1 deferred (listed under "Deferred by the executor") |
| Fonts: every glyph defined (no .notdef) | OK | none found |
| Fonts: every embedded font program could be read | OK | all read |
| Fonts: embedded and mapped to Unicode | OK | 0 not embedded · 0 without ToUnicode |
| Tab order follows the tag structure on pages with links or other annotations | OK | 0 of 247 pages with annotations lack /Tabs /S |
| Characters with no Unicode value (checklist 3.6) | OK | 0 read-aloud characters with no Unicode value |
| Private-use characters (checklist 3.6) | OK | 0 read-aloud characters with private-use codes |
| Title and language set | OK | "Migrant Ecologies: Environmental Histories of the Pacific World" · en-US |
| veraPDF WCAG 2.2 (machine): no WCAG failures | OK | before: 0 WCAG rules failed (0 checks) → after: 0 WCAG rules failed (0 checks) |
| veraPDF: no rule newly failing or failing more often | OK | 0 fixed · 0 still failing · 0 newly failing |
| Alt text: none like a file name or repeated on many figures (1.1.1) | OK | 0 of 35 figures flagged |
| Tables: every table has header cells (1.3.1) | OK | none without |
| Reading order: no page jumps back up a column (1.3.2) | **CHECK** | 2 of 248 pages flagged |
| Reading order: no section moved away from its printed place by this run (1.3.2) | OK | 0 new · 3 already in the original, of 62 sections and blocks |
| Title is not a file name or placeholder (2.4.2) | OK | "Migrant Ecologies: Environmental Histories of the Pacific World" |
| Link text: none like "click here" (2.4.4) | OK | 0 generic |
| Headings: none empty, very long or repeated in a row (2.4.6) | **CHECK** | 0 empty · 0 long · 6 repeated |

## For a Person to Check

### 1. Alt Text Written or Changed by the AI (35)

| Page | Before | After |
|---|---|---|
| PDF 1 (printed Cover) | COVER\x00 | Cover of Migrant Ecologies: Environmental Histories of the Pacific World, edited by James Beattie, Ryan Tucker Jones, and Edward Dallam Melillo. A teal band across the middle carries the title and editors' names. Behind it, a pale abstract painting is split by a vertical dark line. The left half is white with small dark curved boat-like marks. The right half has stacked panels of sea, sky and a grey arc in muted tones. |
| PDF 3 (printed ii) | Logo | Perspectives on the Global Past series logo: two arrows in a circle |
| PDF 5 (printed iv) | Logo\x00 | Knowledge Unlatched open access logo |
| PDF 5 (printed iv) | Creative Commons logo\x00 | Creative Commons license logo: Attribution, NonCommercial, NoDerivatives (CC BY-NC-ND) |
| PDF 11 (printed x) | Map of Pacific Ocean | Map of the Pacific World, western half (left page of a two-page spread). It shows the Pacific Ocean from Russia, Mongolia, China, Japan and Southeast Asia down to Australia, New Zealand and Antarctica. The Pacific island groups appear in between: the Philippines, Micronesia, Marshall Islands, Papua New Guinea, Solomon Islands, Fiji, Samoa and Tonga. A key in the lower left lists country abbreviations. |
| PDF 12 (printed xi) | Map of Pacific Ocean | Map of the Pacific World, eastern half (right page of a two-page spread). It shows the North American west coast from Alaska and Canada through the United States and Mexico to Central and South America. It also shows Hawai‘i, Kiribati, French Polynesia, the Cook Islands, Pitcairn, Easter Island and the Galápagos in the eastern Pacific. A small inset globe shows the projection. Credit: G. Wallace Cartography & GIS. |
| PDF 29 (printed 12) | Map of Fukushima Radioisotopes and migratory species | Graphic map of the North Pacific, printed rotated, titled 'Fukushima radioisotopes can track the routes and rates of migratory species.' Arrows trace juvenile bluefin tuna born in 2011 that fed in Japanese waters contaminated with cesium-134 from the Dai-ichi nuclear plant. They then migrated across the Pacific to feed off the California coast. Bluefin tuna born before the disaster lacked elevated cesium-134. Yellowfin tuna, which do not migrate and feed near Japan, did not contain it. Silhouettes of tuna, a turtle, a seabird and a shark mark the species. |
| PDF 31 (printed 14) | Energy Distribution Tsunami | NOAA map of the maximum wave amplitudes of the March 11, 2011 Tohoku tsunami across the Pacific Ocean, printed rotated. Energy radiates from Japan in bands, shown in shades of grey from low to high amplitude. Triangular markers show sensor stations along coasts and islands such as Hawai‘i and Pago Pago. |
| PDF 34 (printed 17) | Sooty Shearwater Migrations | Map of the Pacific showing the tracked migrations of three twenty-first-century sooty shearwaters. White lines loop from breeding grounds around New Zealand north to Japan, Alaska and California, then back down the eastern Pacific near South America, forming a large figure-eight across the ocean. |
| PDF 50 (printed 33) | Map of Tuna Diaspora | Map of Pacific Ocean diasporas. Triangle lines connect Hawai‘i, Rapa Nui and Aotearoa as the Polynesian triangle. Dotted lines show sweet potato dispersal and marked points show breadfruit encounters. Arrows from the Northwest Coast, Columbia River and San Francisco to Hawai‘i, China and elsewhere show the spread of salmon, furs, sugar and labor, 1786–1893. Symbols mark tuna fisheries, canneries and consumers in places such as Samoa, Pago Pago, Fiji, Tonga and Niue. |
| PDF 57 (printed 40) | Photo of shipping container | Photograph of stacked shipping containers, including Maersk and Cronos units, on a quayside at Pago Pago Harbor, American Samoa, with a green hill behind. |
| PDF 72 (printed 55) | Railway Image | Nineteenth-century illustration titled 'Across the Continent: The Snow Sheds on the Central Pacific Railroad, in the Sierra Nevada Mountains.' A steam train emerges from a snow shed in a snowy mountain pass while workers and onlookers wave. |
| PDF 75 (printed 58) | Dairy Farm on Aurora Road | Historic black-and-white photograph of a dairy factory building on Aurora Road in Taranaki, New Zealand, with horse-drawn carts, milk cans and people in front, in cleared land beside a ditch. |
| PDF 78 (printed 61) | Chew Chong and Family | Studio photograph, around 1903, of Chew Chong and his family: an elderly man seated at the center, surrounded by women, men and a young boy in formal Victorian clothing. |
| PDF 88 (printed 71) | Map of California | Map of California showing Spanish missions, forts (presidios) and towns (pueblos) from San Diego to Sonoma. It also labels the territories of native tribes, such as Chumash, Miwok, Ohlone, Yokuts and Pomo, with Oregon, Nevada and Arizona at the borders. |
| PDF 89 (printed 72) | Vista del Presidio | Drawing by José Cardero, 1791–1792, of the Presidio of Monterey in California. A walled log fort stands on a plain near the coast, with ships offshore and small figures working in the foreground. |
| PDF 92 (printed 75) | Cattle Roundup | Pen-and-ink drawing by Emanuel Wyttenbach of a rodeo at a mission. A mounted vaquero herds sheep and cattle across a yard in front of a long mission building with a bell gable. |
| PDF 108 (printed 91) | Stoveboat Smashed | Painting by Charles Sidney Raleigh, 1877, of a whale's tail striking and smashing a whaleboat. Splintered oars and crew members are thrown through the air above a rough sea, with a sailing ship in the distance. |
| PDF 110 (printed 93) | Portrait of Amos Haskins | Daguerreotype portrait of Captain Amos Haskins, a Wampanoag man, in a dark jacket and white cravat, seated and looking at the camera in an ornate frame. |
| PDF 111 (printed 94) | Depiction of American whalemen in Japan | Japanese scroll painting by Usui Shozo showing three American whalemen standing in line, one holding a telescope and another raising a hat. Columns of Japanese text surround them and part of a ship's rigging appears at the left. |
| PDF 121 (printed 104) | Cocospalme | Black-and-white photograph from 1900 of a coconut palm seen from below, with large fronds and a cluster of nuts at the crown of the trunk. |
| PDF 126 (printed 109) | Fruit-Bearing Coconut Tree | Photograph, around 1900, of a fruit-bearing coconut palm with a man climbing the trunk toward the nuts. Cut fronds lie at the base and other palms and trees stand in the background. |
| PDF 128 (printed 111) | Map of DHPG Plantation in Mulifanua | Historic survey map of the German plantation (DHPG) at Mulifanua, Samoa, 1900. Two panels, 'Le Utu Sao Vaa' and 'Fagalepolu & Fatuosofia', show the plantation divided into narrow numbered parcels, with a legend and scale bar. |
| PDF 135 (printed 118) | Rongo, the Maori god of kumara | Photograph of Rongo, a carved stone figure of the Māori god of kumara and cultivated plants. The face has spiral eyes and a wide mouth, and the figure rests on a wooden floor. |
| PDF 138 (printed 121) | Engraving Depicting Confiscation and Destruction of Idol Gods | Engraving of missionaries seated before a mission house among palm trees and mountains while islanders carry out and lay down carved idols for destruction. The caption inside reads 'And the idols he shall utterly abolish.' Isaiah ii. 18. |
| PDF 162 (printed 145) | Man with a Horse | Photograph of Edwin Dun in riding clothes holding a saddled dark horse imported from the United States, in a field with farm buildings behind, Hokkaido, 1878. |
| PDF 164 (printed 147) | Stacks of Lumber | Photograph of the Ōji paper manufacturing company at Tomakomai in the 1900s: tall smoking chimneys and factory buildings beyond stacks of cut logs in the foreground. |
| PDF 165 (printed 148) | Ainu Men in Cano | Early modern ink-and-wash illustration of three Ainu men in a long wooden boat paddling across water, with Japanese text at the right edge. |
| PDF 193 (printed 176) | Ka Nupepa Kuokoa | Masthead of the Hawaiian-language newspaper Ka Nupepa Kuokoa, January 7, 1871 (Buke X, Helu 1, Honolulu), in ornate decorative lettering inside a framed banner. |
| PDF 196 (printed 179) | Growing Kona Coffee | Close-up photograph of a person's cupped hands holding freshly picked red Kona coffee cherries above a bucket full of more cherries. |
| PDF 203 (printed 186) | Maunalua 1915 | Photograph from 1915 looking down from Kohelepelepe, Pu‘uma‘i, over the Maunalua landscape: a broad bay and coastal flats with scattered trees, tall poles in the foreground and hills beyond. |
| PDF 213 (printed 196) | Endonyms | Map of the endonyms (Hawaiian place names) of Maunalua, O‘ahu, with a theoretical landscape of the area. It is printed rotated, with a 3-mile scale and a compass. Named valleys, ridges, fishing ponds, springs, heiau, ko‘a fishing shrines and cultural features are marked along the coast from Makapu‘u to Niu. An inset of O‘ahu shows the mapped area. |
| PDF 221 (printed 204) | Exonyms | Map of the exonyms (English place names) of Hawai‘i Kai and the current landscape, printed rotated, with a 3-mile scale and a compass. Labeled sites include Koko Marina, Koko Head, Koko Crater, Toilet Bowl, Witches Brew, Spitting Caves, China Walls, Pele's Chair and Hawaii Kai Golf Course along the Kalwi Channel coast. An inset of O‘ahu shows the mapped area. |
| PDF 248 (printed 231) | Drawing of two snipes (birds) | Nineteenth-century lithograph of two wading birds, Latham's snipe on the left and an Australian painted snipe on the right, standing on a shore with reeds behind. |
| PDF 316 (printed 299) | Logo | Series logo: two arrows forming a circle |

### 2. Headings

Heading levels by style (as applied):

| Style | Level | How | Elements |
|---|---|---|---:|
| TPT | H1 | RoleMap | 1 |
| FMH | H2 | RoleMap | 1 |
| ENH | H2 | RoleMap | 17 |
| H1 | H2 | retype (standard tag) | 48 |

Spoken text set by the AI (should match what is printed):

| Page | Text |
|---|---|
| PDF 2 (printed i) | Migrant Ecologies |
| PDF 4 (printed iii) | Migrant Ecologies |

### 3. Lists and Tables

- Header cells marked by the AI on PDF 210 (printed 193): 1 header row(s), 0 header column(s), 0 cells changed to header cells; 5 false header cell(s) set back to data. Check they are the real headers.

Tables kept as tables (1): check header cells and reading order.

- PDF 210 (printed 193): 15 rows × 11 columns, 11 header cells. "Endonym (meaning) | | Last | | Traditional Use | | Exonym | | First | | Current Use"

### 4. Reading Order Changes

Listen through these spots with a screen reader.

- Figure on PDF 29 (printed 12) moved to read with its page (it read after PDF 50 (printed 33); now after PDF 28 (printed 11))
- Figure on PDF 50 (printed 33) moved to read with its page (it read after PDF 317 (printed 300); now after PDF 51 (printed 34))
- Figure on PDF 57 (printed 40) moved to read with its page (it read after PDF 72 (printed 55); now after PDF 58 (printed 41))
- Figure on PDF 72 (printed 55) moved to read with its page (it read after PDF 317 (printed 300); now after PDF 72 (printed 55))
- Figure on PDF 75 (printed 58) moved to read with its page (it read after PDF 89 (printed 72); now after PDF 76 (printed 59))
- Figure on PDF 78 (printed 61) moved to read with its page (it read after PDF 89 (printed 72); now after PDF 79 (printed 62))
- Figure on PDF 88 (printed 71) moved to read with its page (it read after PDF 108 (printed 91); now after PDF 87 (printed 70))
- Figure on PDF 89 (printed 72) moved to read with its page (it read after PDF 317 (printed 300); now after PDF 89 (printed 72))
- Figure on PDF 92 (printed 75) moved to read with its page (it read after PDF 108 (printed 91); now after PDF 93 (printed 76))
- Figure on PDF 108 (printed 91) moved to read with its page (it read after PDF 317 (printed 300); now after PDF 109 (printed 92))
- Figure on PDF 111 (printed 94) moved to read with its page (it read after PDF 317 (printed 300); now after PDF 111 (printed 94))
- Figure on PDF 128 (printed 111) moved to read with its page (it read after PDF 317 (printed 300); now after PDF 129 (printed 112))
- Figure on PDF 135 (printed 118) moved to read with its page (it read after PDF 193 (printed 176); now after PDF 134 (printed 117))
- Figure on PDF 138 (printed 121) moved to read with its page (it read after PDF 193 (printed 176); now after PDF 139 (printed 122))
- Figure on PDF 162 (printed 145) moved to read with its page (it read after PDF 193 (printed 176); now after PDF 163 (printed 146))
- Figure on PDF 164 (printed 147) moved to read with its page (it read after PDF 193 (printed 176); now after PDF 165 (printed 148))
- Figure on PDF 165 (printed 148) moved to read with its page (it read after PDF 193 (printed 176); now after PDF 166 (printed 149))
- Figure on PDF 193 (printed 176) moved to read with its page (it read after PDF 317 (printed 300); now after PDF 194 (printed 177))
- Figure on PDF 196 (printed 179) moved to read with its page (it read after PDF 300 (printed 283); now after PDF 197 (printed 180))
- Figure on PDF 203 (printed 186) moved to read with its page (it read after PDF 300 (printed 283); now after PDF 204 (printed 187))

### 5. Spoken Text (ActualText) Checked Against the Print (2 accepted with differences, 0 rejected)

A spoken text may differ from the printed characters only in spacing, letter case and line-end hyphens (sponsor rule 1). Accepted ones that differ are listed so a person can listen to them; rejected ones added or changed words or punctuation.

- Accepted, PDF 2 (printed i): printed "MI GRANT ECOLOGIES" → spoken "Migrant Ecologies"
- Accepted, PDF 4 (printed iii): printed "Mi grant Ecologies" → spoken "Migrant Ecologies"

### 6. Links Whose Description Was Only a URL (5)

The description (what a screen reader announces) was set to the book's own sentence around the link, with the URL removed. No words were added and the visible URL is unchanged. Replace any of these with a better description if needed.

| Page | URL | Description now |
|---|---|---|
| PDF 5 (printed iv) | http://www.knowledgeunlatched.org | More information about the initiative and links to the open-access version can be found at. |
| PDF 5 (printed iv) | https://lccn.loc.gov/2022026302 | Classifcation: LCC GF798.M53 2022 (print) | LCC GF798 (ebook) | DDC 304.209164—dc23/eng20220922 LC record available at LC ebook record available at An electronic version of this book is freely available, thanks to the support of libraries working with Knowledge Unlatched. |
| PDF 5 (printed iv) | https://lccn.loc.gov/2022026303 | Classifcation: LCC GF798.M53 2022 (print) | LCC GF798 (ebook) | DDC 304.209164—dc23/eng20220922 LC record available at LC ebook record available at An electronic version of this book is freely available, thanks to the support of libraries working with Knowledge Unlatched. |
| PDF 44 (printed 27) | https://doi.org/10.1098/rsbl.2015.0071 | Lee, “A Grey Whale Breaks the Rec ord for Longest Mammal Migration,” National Geographic, April 14, 2015; Bruce Mate et al. “Critically Endangered Western Gray Whales Migrate to the Eastern North Pacific,” Biology Letters 11, no. 4 (April 2015),25. |
| PDF 240 (printed 223) | https://doi.org/10.1641/b570707 | Spalding et al. “Marine Ecoregions of the World: A Bioregionalization of Coastal and Shelf Areas,” BioScience 57, no. 7 (2007): Box 1,10. |

### 7. Tag-tree Index Entries Cleared (43)

Entries that pointed at a tag no longer in the tag tree (left by the source file, or by a tag the run removed). Nothing reads such a tag; no page, text or reachable tag changed.

- ParentTree, PDF 3 (printed ii): MCID 9 (Artifact)
- ParentTree, PDF 28 (printed 11): MCID 1102 (Artifact)
- ParentTree, PDF 34 (printed 17): MCID 1380 (Artifact)
- ParentTree, PDF 50 (printed 33): MCID 2569 (Artifact)
- ParentTree, PDF 57 (printed 40): MCID 3009 (Artifact)
- ParentTree, PDF 72 (printed 55): MCID 4143 (Artifact)
- ParentTree, PDF 75 (printed 58): MCID 4363 (Artifact)
- ParentTree, PDF 89 (printed 72): MCID 5296 (Artifact)
- ParentTree, PDF 92 (printed 75): MCID 5545 (Artifact)
- ParentTree, PDF 103 (printed 86): MCID 6478 (Artifact)
- ParentTree, PDF 108 (printed 91): MCID 6845 (Artifact)
- ParentTree, PDF 110 (printed 93): MCID 6920 (Artifact)
- ParentTree, PDF 111 (printed 94): MCID 7030 (Artifact)
- ParentTree, PDF 117 (printed 100): MCID 7475 (Artifact)
- ParentTree, PDF 121 (printed 104): MCID 7817 (Artifact)
- ParentTree, PDF 126 (printed 109): MCID 8154 (Artifact)
- ParentTree, PDF 128 (printed 111): MCID 8303 (Artifact)
- ParentTree, PDF 134 (printed 117): MCID 8763 (Artifact)
- ParentTree, PDF 138 (printed 121): MCID 8966 (Artifact)
- ParentTree, PDF 152 (printed 135): MCID 10032 (Artifact)
- ParentTree, PDF 162 (printed 145): MCID 10721 (Artifact)
- ParentTree, PDF 164 (printed 147): MCID 10857 (Artifact)
- ParentTree, PDF 165 (printed 148): MCID 10878 (Artifact)
- ParentTree, PDF 171 (printed 154): MCID 11407 (Artifact)
- ParentTree, PDF 185 (printed 168): MCID 12539 (Artifact)
- ParentTree, PDF 193 (printed 176): MCID 13279 (Artifact)
- ParentTree, PDF 196 (printed 179): MCID 13435 (Artifact)
- ParentTree, PDF 202 (printed 185): MCID 13975 (Artifact)
- ParentTree, PDF 203 (printed 186): MCID 14016 (Artifact)
- ParentTree, PDF 204 (printed 187): MCID 14082 (Artifact), MCID 14083 (Artifact)
- ParentTree, PDF 210 (printed 193): MCID 14770 (Art), MCID 14774 (Artifact), MCID 14775 (Artifact)
- ParentTree, PDF 211 (printed 194): MCID 14735 (Artifact)
- ParentTree, PDF 226 (printed 209): MCID 15706 (Artifact)
- ParentTree, PDF 246 (printed 229): MCID 17352 (Artifact)
- ParentTree, PDF 248 (printed 231): MCID 17472 (Artifact)
- ParentTree, PDF 258 (printed 241): MCID 18312 (Artifact)
- ParentTree, PDF 274 (printed 257): MCID 19549 (Artifact)
- ParentTree, PDF 316 (printed 299): MCID 1 (H1)
- ParentTree, entries not tied to page content (annotations, forms, or keys nothing uses): key 6754 MCID 33085 (Artifact)
- IDTree: "AD221016-1502-22.3.20263-ADBE-000000000616" (H1)

### 8. Structure Left for a Person

- PDF 31 (printed 14): a caption is not grouped with a figure (it sits inside Div)
- PDF 121 (printed 104): a caption is not grouped with a figure (it sits inside Div)
- PDF 126 (printed 109): a caption is not grouped with a figure (it sits inside Div)
- PDF 126 (printed 109): a caption is not grouped with a figure (it sits inside Div)
- PDF 126 (printed 109): a caption is not grouped with a figure (it sits inside Div)
- PDF 213 (printed 196): a caption is not grouped with a figure (it sits inside Div)
- PDF 221 (printed 204): a caption is not grouped with a figure (it sits inside Div)

### 9. WCAG Checks veraPDF Does Not Make

Each item is something to look at, not a proven failure.

- 1.3.2 the reading order jumps back up the same column on 2 pages. Listen through them with a screen reader (or the PAC screen-reader preview): PDF 210 (printed 193) (3 jumps), PDF 211 (printed 194) (3 jumps)
- 1.3.2 3 sections read away from their printed place, as in the original (this run did not move them). Listen through each where it is read, or move it with move_section:
  - PDF 1 (printed Cover): Article, read after PDF 316 (printed 299)
  - PDF 210–211 (printed 193–194): Story "(Continued)", read after PDF 317 (printed 300)
  - PDF 211 (printed 194): Story "Current Use", read after PDF 317 (printed 300)
- 2.4.6 PDF 26 (printed 9): the heading "NOTES" twice in a row
- 2.4.6 PDF 223 (printed 206): the heading "NOTES" twice in a row
- 2.4.6 PDF 239 (printed 222): the heading "NOTES" twice in a row
- 2.4.6 PDF 255 (printed 238): the heading "NOTES" twice in a row
- 2.4.6 PDF 270 (printed 253): the heading "NOTES" twice in a row
- 2.4.6 PDF 288 (printed 271): the heading "NOTES" twice in a row

### 10. Deferred by the AI

- **Chapter titles and other major headings are not tagged as headings**: The Introduction, the 14 chapter titles, Preface, Map of the Pacific World and About the Contributors have no heading tag. The Index heading and the Notes titles are also not confirmed as headings. No element ids are given for them, so they cannot be retyped here. A person should tag them H2. In-chapter section heads (style H1) are currently mapped to H2 to avoid skipping levels; once chapter titles are H2, remap those sections to H3. [PDF 14 (printed xiii), PDF 18 (printed 1), PDF 28 (printed 11), PDF 47 (printed 30), PDF 64 (printed 47), PDF 85 (printed 68), PDF 103 (printed 86), PDF 117 (printed 100), PDF 134 (printed 117), PDF 152 (printed 135), PDF 171 (printed 154), PDF 185 (printed 168), PDF 202 (printed 185), PDF 226 (printed 209), PDF 246 (printed 229), PDF 258 (printed 241), PDF 274 (printed 257), PDF 296 (printed 279), PDF 302 (printed 285)]
- **Chapter opening drop caps**: The first letter of each chapter opening paragraph (CO style) is a separate element or missing from the paragraph (e.g. 'n 1994, a young environmental historian'). A person should check that the reading order puts the drop cap before its paragraph. [PDF 18 (printed 1), PDF 28 (printed 11), PDF 47 (printed 30), PDF 64 (printed 47), PDF 85 (printed 68), PDF 103 (printed 86), PDF 117 (printed 100), PDF 134 (printed 117), PDF 152 (printed 135), PDF 171 (printed 154), PDF 185 (printed 168), PDF 202 (printed 185), PDF 226 (printed 209), PDF 246 (printed 229), PDF 258 (printed 241), PDF 274 (printed 257)]
- **Table of contents**: The contents entries are Link elements on a plain page, not paragraph styles, so TOC/TOCI tagging cannot be done from the digest. A person should tag it as TOC. [PDF 8 (printed vii), PDF 9 (printed viii)]
- **Table 11.1 continuation on the next page**: The '(Continued)' note and repeated header cells on the following page are Art/Story elements outside the Table. The 15-row, 11-column table has empty spacer columns and the source notes (TSN) sit outside it. A person should check that the table structure and headers are correct across the page break. [PDF 210 (printed 193), PDF 211 (printed 194)]
- **Reading order at the end of the book and the copyright page**: The tree puts the series-editor page (Part, PDF 316) after the container that ends at PDF 317, and the copyright page (PDF 5) does not appear in a named container. The sections cannot be moved precisely from the digest. [PDF 5 (printed iv), PDF 316 (printed 299), PDF 317 (printed 300)]
- **Index text**: In the Index (IX/IXA styles) the page numbers are extracted apart from their terms (e.g. 'activism, anti-war, , – 245249252'). The index reads wrongly to a screen reader, and ActualText cannot be written for hundreds of entries. A person should decide how to repair it. [PDF 302 (printed 285), PDF 315 (printed 298)]
- **Stray spaces inside words in extracted text**: Many words have spurious spaces ('Mi grant', 'Rus sian', 'Eu ro pean', 'eigh teenth'). Only the book title is corrected here. [PDF 4 (printed iii), PDF 317 (printed 300)]
- **Alt text for the open-access logo on PDF 5 (obj 1692 0)**: No image was supplied for this logo; the alt text 'Knowledge Unlatched open access logo' is inferred from the adjacent text and needs checking. [PDF 5 (printed iv)]
- **Interior-page notes sections**: Notes are in separate per-chapter sections, not a single section, so sections.notes_pages is left unset. [PDF 16 (printed xv), PDF 288 (printed 271)]

Reviewer note from the AI: veraPDF reported no machine-checkable failures. Decisions: the book title is H1 (the title-page text, TPT). Contents and the NOTES headings are H2. The in-chapter section heads (style 'H1') are mapped to H2 until chapter titles are tagged (see deferrals). The cover figure is moved to the front. Page-image figures got alt text, including the 35 captioned figures, the maps on PDF 11 and 12, and the logos. Figure and caption grouping is left to the executor. No running heads or page numbers were found tagged as text (the 'repeated_lines' entries are heading words), so there are no artifact rules.

### 11. Deferred by the Executor

- the source file already claims PDF/UA conformance: not verified by this pipeline; check it with PAC before relying on it

### 12. Decisions Not Applied (1)

Rejected by validation or by the executor; nothing was half-applied.

- {"op": "move_section", "why": "1 candidate sections, host found: False"}

## What Was Changed

| Change | Count |
|---|---:|
| document: second Document root merged | 1 |
| document: title | 1 |
| document: DisplayDocTitle | 1 |
| document: /Lang | 1 |
| heading: RoleMap level | 3 |
| heading: ActualText | 2 |
| heading: standard tag H1 → H2 (retyped) | 48 |
| table: header cells marked (work order) | 0 |
| table: cells wrongly tagged as headers set back to data cells | 5 |
| figure: alt text | 35 |
| figure: caption tied (figure moved out of its paragraph) | 35 |
| list: built | 1 |
| notes: Note with /ID | 1013 |
| links: /Contents set | 6486 |
| links: joined existing Link | 6486 |
| links: URL-only description replaced by the sentence around it | 5 |
| order: figure moved to its page | 20 |
| tag tree index: entries pointing outside the tree cleared (ParentTree) | 42 |
| tag tree index: entries pointing outside the tree removed (IDTree) | 1 |

## Accessibility Evaluation

A person evaluates this version of `migrant_remediated.pdf` with PAC 2026 and a screen reader, on the app's "Accessibility Evaluation" page (or with manual_checks.py; docs/release.md). The "Ready to ship?" answer needs both parts. A Fail is recorded with its note and does not hold the book back. Each result is recorded against this version of the PDF (its sha256): after a new apply it no longer counts. The evaluation is a record of what a person found, not a legal certification.

**PAC 2026.** Open `migrant_remediated.pdf` in PAC 2026 (https://pac.pdf-accessibility.org/en, Windows) and run its WCAG check. Anything it fails that is not listed above is a gap in the automated checks: note it in the issue tracker. Each item is Pass, Fail or Not Applicable, with notes:

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
