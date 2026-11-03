# Remediation Review: migrant.pdf

Result: `migrant_remediated.pdf`

321 pages · run November 3, 2026, at 12:32 AM · model `anthropic/claude-sonnet-5.5` · prompt `workorder_v10.md` (15b5aa0ade9c6549) · AI cost $0.244 ($0.0008 per page), from the original call on November 3, 2026 · this run: no new call · tokens: saved reply reused, not counted

Intake: none (already tagged)

Libraries: python 3.14.4 · pikepdf 10.5.1 · pdfplumber 0.11.9 · pypdfium2 5.7.1 · pillow 13.0.0 · fonttools 4.62.1

Time: intake 0.8s · audit 72.4s · reuse saved reply 0.8s · apply 88.5s · verify 80.8s · total 243.3s

## Overview

[Open the dashboard](review.html)

**Status:** Not Ready

**Ready to ship?**
- Work Order Approval: Not Approved (applied without a review)
- ✓ OCR Text Approval: Not Applicable
- ✓ Safety Checks: Passed
- Accessibility Evaluation: Not Completed

**Safety checks:** OK ✔ pages look the same · OK ✔ text unchanged · OK ✔ all content tagged or decoration · OK ✔ tag-tree index points into the tree · OK ✔ every font readable  
**Needs a person:** 9 (6 deferred by the AI · 0 deferred by the executor · 3 CHECK rows)  
**AI decisions:** 54 in the work order, applied without review by a person  
**Fixed automatically (no AI):** links tied and described 6,486 · note IDs 1,013 · tag-tree index entries 43 · link descriptions that were only a URL 5 · Document root 1 · title shown in the window 1  
**veraPDF (WCAG 2.2 machine checks):** 0 WCAG rules failing before (0 checks) → 0 after (0 checks) · 0 newly failing

Automated checks are evidence, not sign-off.

| Top issues | Pages | Where |
|---|---|---|
| Executor applied every decision: 1 rejected · 0 failed (listed under "Decisions not applied") | see §11 | [§11](#11-decisions-not-applied-1) |
| Reading order jumps back up a column (6 jumps) | PDF 210 (printed 193), PDF 211 (printed 194) | [§8](#8-wcag-checks-verapdf-does-not-make) |
| Headings: none empty, very long or repeated in a row (2.4.6): 0 empty · 0 long · 6 repeated | see §8 | [§8](#8-wcag-checks-verapdf-does-not-make) |
| Chapter and front/back-matter titles have no heading tag of their own. The Introduction (PDF 18), the 14 cha… | 19 pages, PDF 14 (printed xiii) to PDF 302 (printed 285) | [§9](#9-deferred-by-the-ai) |
| The continuation of Table 11.1 on PDF 211 (printed 194) sits outside the table, in Art containers and a Stor… | PDF 210 (printed 193), PDF 211 (printed 194) | [§9](#9-deferred-by-the-ai) |
| … and 4 more | | §9 |

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
| Empty tags removed when proven empty | OK | 0 removed |
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
| Reading order: no section moved away from its printed place by this run (1.3.2) | OK | 0 new · 3 already in the original, of 27 sections and blocks |
| Title is not a file name or placeholder (2.4.2) | OK | "Migrant Ecologies: Environmental Histories of the Pacific World" |
| Link text: none like "click here" (2.4.4) | OK | 0 generic |
| Headings: none empty, very long or repeated in a row (2.4.6) | **CHECK** | 0 empty · 0 long · 6 repeated |

## For a Person to Check

### 1. Alt Text Written or Changed by the AI (35)

| Page | Before | After |
|---|---|---|
| PDF 1 (printed Cover) | COVER\x00 | Book cover: Migrant Ecologies: Environmental Histories of the Pacific World, edited by James Beattie, Ryan Tucker Jones, and Edward Dallam Melillo. Title and editors appear on a teal band across a pale abstract artwork of sea and horizon, with small dark curved boat-like shapes. |
| PDF 3 (printed ii) | Logo | Perspectives on the Global Past series logo: two arrows forming a circle. |
| PDF 5 (printed iv) | Logo\x00 | Knowledge Unlatched logo, marking the open access edition. |
| PDF 5 (printed iv) | Creative Commons logo\x00 | Creative Commons license logo: Attribution, NonCommercial, NoDerivatives (CC BY-NC-ND). |
| PDF 11 (printed x) | Map of Pacific Ocean | Left half of a two-page map of the Pacific World. It shows East and Southeast Asia, Russia, Japan, Australia, New Zealand and the island groups of Micronesia, Melanesia and Polynesia, with latitude and longitude lines and a key of country abbreviations. |
| PDF 12 (printed xi) | Map of Pacific Ocean | Right half of the two-page map of the Pacific World. It shows Alaska, Canada, the United States, Mexico, Central and South America, Hawai‘i, French Polynesia, the Galápagos and Easter Island, with an inset showing the map projection. Credit: G. Wallace Cartography & GIS. |
| PDF 29 (printed 12) | Map of Fukushima Radioisotopes and migratory species | Infographic map of the North Pacific, rotated sideways, titled 'Fukushima radioisotopes can track the routes and rates of migratory species.' Arrows show bluefin tuna born in 2011 in Japanese waters contaminated with cesium-134 from the Dai-ichi nuclear plant migrating across the Pacific to the California coast. Bluefin caught before the disaster had no elevated cesium-134. Yellowfin tuna, which stay near Japan, did not contain it. |
| PDF 31 (printed 14) | Energy Distribution Tsunami | Rotated map of the Pacific Ocean showing maximum wave amplitudes, in centimeters, of the Tohoku tsunami of March 11, 2011. The energy radiates from Japan, strongest in beams across the central and eastern Pacific, with monitoring stations marked along the Americas and islands. NOAA Center for Tsunami Research. |
| PDF 34 (printed 17) | Sooty Shearwater Migrations | Map of the Pacific with white tracks of three sooty shearwaters. The birds loop from their New Zealand breeding grounds to feeding areas off Japan and Alaska and the North American coast, and return along the South American side, in a figure-eight pattern. |
| PDF 50 (printed 33) | Map of Tuna Diaspora | Map of the Pacific Ocean showing diasporas. Lines mark Polynesian triangles and outposts (c. 1000–1500 C.E.), sweet potato dispersals, breadfruit encounters (1789–1889) and the spread of salmon, furs, sugar and labor around the Northwest Coast, Hawai‘i and Guangzhou (1786–1893). Symbols mark tuna fisheries, canneries and consumers, 1954–2015. |
| PDF 57 (printed 40) | Photo of shipping container | Photograph of stacked shipping containers, some marked Maersk, on a paved container yard at Pago Pago Harbor, American Samoa, with a green hillside behind. |
| PDF 72 (printed 55) | Railway Image | Nineteenth-century engraving 'Across the Continent: The Snow Sheds on the Central Pacific Railroad, in the Sierra Nevada Mountains.' A steam train emerges from a snow shed and tunnel in a mountain landscape while workers wave hats. |
| PDF 75 (printed 58) | Dairy Farm on Aurora Road | Historic photograph of a wooden dairy factory on Aurora Road in Taranaki, with horse-drawn wagons loaded with milk cans in front and tree stumps and cleared ground around it. |
| PDF 78 (printed 61) | Chew Chong and Family | Studio portrait, c. 1903, of Chew Chong and his family. The elderly Chew Chong sits at the center, surrounded by seated and standing adult children and a young boy in Western dress. |
| PDF 88 (printed 71) | Map of California | Map of California and neighboring states showing Spanish missions, forts (presidios) and towns (pueblos) from 1769 to 1844, with the names of Native tribes such as Pomo, Miwok, Chumash and Yokuts across their territories. A scale bar is included. |
| PDF 89 (printed 72) | Vista del Presidio | Drawing by José Cardero (1791–1792) of the Presidio of Monterey, a walled adobe fort on open ground by the sea, with small figures at work and ships on the horizon. |
| PDF 92 (printed 75) | Cattle Roundup | Pen-and-ink drawing by Emanuel Wyttenbach of a rodeo. Mounted vaqueros drive cattle and sheep past the long arcaded facade of a California mission. |
| PDF 108 (printed 91) | Stoveboat Smashed | Painting by Charles Sidney Raleigh (1877) of a whale's tail smashing a whaleboat. Oars, a barrel and whalemen are flung into the air above rough seas, with a ship in the distance. |
| PDF 110 (printed 93) | Portrait of Amos Haskins | Daguerreotype portrait of Captain Amos Haskins, a Wampanoag man in a dark coat and white waistcoat, shown half-length in an ornate frame. |
| PDF 111 (printed 94) | Depiction of American whalemen in Japan | Japanese scroll painting by Usui Shozo of three American whalemen in Japan, standing in a row in hats and vests, with a ship at left and columns of Japanese text. |
| PDF 121 (printed 104) | Cocospalme | Photograph from 1900 of a coconut palm laden with nuts, seen from below, with fronds spreading against the sky. |
| PDF 126 (printed 109) | Fruit-Bearing Coconut Tree | Photograph c. 1900 of a fruit-bearing coconut palm in Samoa. A man climbs the trunk, with other palms and a clearing behind and cut fronds on the ground. |
| PDF 128 (printed 111) | Map of DHPG Plantation in Mulifanua | Historical map of the DHPG plantation at Mulifanua, Samoa, 1900. It shows two plantation areas, Le Utu Sao Vaa and Fagalepolu & Fatuosofia, divided into long numbered parcels of cultivated and uncultivated land, with a legend. |
| PDF 135 (printed 118) | Rongo, the Maori god of kumara | Black-and-white photograph of a carved stone head representing Rongo, the Māori god of kumara and cultivated plants, with spiral-carved eyes and a mouth. |
| PDF 138 (printed 121) | Engraving Depicting Confiscation and Destruction of Idol Gods | Engraving of the confiscation and destruction of idol gods on Rarotonga. A crowd gathers before missionaries seated in front of a house, with carved idols laid on the ground, palms and mountains behind. Caption in the image: 'And the idols he shall utterly abolish.' Isaiah ii. 18. |
| PDF 162 (printed 145) | Man with a Horse | Photograph from 1878 of Edwin Dun in riding clothes standing beside a saddled horse imported from the United States, on a farm in Hokkaido. |
| PDF 164 (printed 147) | Stacks of Lumber | Photograph from the 1900s of the Ōji paper manufacturing company plant in Tomakomai, with tall smoking chimneys and stacks of cut logs in the foreground. |
| PDF 165 (printed 148) | Ainu Men in Cano | Early modern ink painting of three Ainu men paddling a wooden canoe across water, with vertical Japanese text at right. |
| PDF 193 (printed 176) | Ka Nupepa Kuokoa | Masthead of the Hawaiian-language newspaper Ka Nupepa Kuokoa, Honolulu, January 7, 1871 (Buke X, Helu 1), with ornate lettering inside a decorative frame. |
| PDF 196 (printed 179) | Growing Kona Coffee | Photograph of a coffee harvester's hands holding ripe red Kona coffee cherries above a bucket full of cherries. |
| PDF 203 (printed 186) | Maunalua 1915 | Photograph from 1915 looking down from Kohelepelepe over Maunalua, Hawai‘i: dry scrubby land with tall poles in the foreground, a wide bay and hills beyond. |
| PDF 213 (printed 196) | Endonyms | Rotated map of Maunalua on O‘ahu showing its Hawaiian place names (endonyms) along the coast, including Makapu‘u, Hālona, Kahauloa and Kuapā, with valleys, springs, fishing ponds, fishing shrines, heiau and other features marked. An inset of O‘ahu marks the mapped area. |
| PDF 221 (printed 204) | Exonyms | Rotated map of Hawai‘i Kai, the same area as Maunalua, showing the current landscape and English-language names (exonyms) such as Koko Head, Koko Marina, Sandy Beach, Toilet Bowl, Pele's Chair and Spitting Caves. An inset of O‘ahu marks the mapped area. |
| PDF 248 (printed 231) | Drawing of two snipes (birds) | Nineteenth-century illustration of two shorebirds standing by water and reeds: a Latham's snipe at left with a long bill and streaked brown plumage, and an Australian painted snipe at right with a black breast and white eye ring. |
| PDF 316 (printed 299) | Logo | Perspectives on the Global Past series logo: two arrows forming a circle. |

### 2. Headings

Heading levels by style (as applied):

| Style | Level | How | Elements |
|---|---|---|---:|
| ENH | H2 | RoleMap | 17 |
| FMH | H2 | RoleMap | 1 |
| H1 | H2 | retype (standard tag) | 48 |

Spoken text set by the AI (should match what is printed):

| Page | Text |
|---|---|
| PDF 2 (printed i) | MIGRANT ECOLOGIES |
| PDF 4 (printed iii) | Migrant Ecologies |

### 3. Elements Retyped by the AI (1)

Check each one is (or is not) a heading as decided.

| Page | Text | Before | After |
|---|---|---|---|
| PDF 4 (printed iii) | Mi grant Ecologies | TPT | H1 |

### 4. Lists and Tables

- Header cells marked by the AI on PDF 210 (printed 193): 1 header row(s), 0 header column(s), 0 cells changed to header cells; 5 false header cell(s) set back to data. Check they are the real headers.

Tables kept as tables (1): check header cells and reading order.

- PDF 210 (printed 193): 15 rows × 11 columns, 11 header cells. "Endonym (meaning) | | Last | | Traditional Use | | Exonym | | First | | Current Use"

### 5. Spoken Text (ActualText) Checked Against the Print (2 accepted with differences, 0 rejected)

A spoken text may differ from the printed characters only in spacing, letter case and line-end hyphens (sponsor rule 1). Accepted ones that differ are listed so a person can listen to them; rejected ones added or changed words or punctuation.

- Accepted, PDF 2 (printed i): printed "MI GRANT ECOLOGIES" → spoken "MIGRANT ECOLOGIES"
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

### 8. WCAG Checks veraPDF Does Not Make

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

### 9. Deferred by the AI

- **Chapter and front/back-matter titles have no heading tag of their own. The Introduction (PDF 18), the 14 chapter openers, the Preface, About the Contributors and Index are not listed as elements, so I cannot target them. A person should tag them as H2.**: Chapter openers are on PDF 28, 47, 64, 85, 103, 117, 134, 152, 171, 185, 202, 226, 246, 258 and 274. I mapped the in-chapter section headings (style H1) and 'NOTES' to H2 to avoid skipping from H1 to H3. If chapter titles become H2, these section headings should drop to H3. [PDF 14 (printed xiii), PDF 18 (printed 1), PDF 28 (printed 11), PDF 47 (printed 30), PDF 64 (printed 47), PDF 85 (printed 68), PDF 103 (printed 86), PDF 117 (printed 100), PDF 134 (printed 117), PDF 152 (printed 135), PDF 171 (printed 154), PDF 185 (printed 168), PDF 202 (printed 185), PDF 226 (printed 209), PDF 246 (printed 229), PDF 258 (printed 241), PDF 274 (printed 257), PDF 297 (printed 280), PDF 302 (printed 285)]
- **The continuation of Table 11.1 on PDF 211 (printed 194) sits outside the table, in Art containers and a Story container read after the Index, with empty Art elements and the title and source notes.**: I cannot tell from the digest which pieces belong to the table, and merging them is outside this work order's vocabulary. [PDF 210 (printed 193), PDF 211 (printed 194)]
- **The Index text layer separates entries from their page numbers (e.g. 'activism, anti-war, , – 245249252'), so the index reads wrongly.**: ActualText per entry is not feasible here; a person should check or retag it. [PDF 302 (printed 285), PDF 303 (printed 286), PDF 304 (printed 287), PDF 305 (printed 288), PDF 306 (printed 289), PDF 307 (printed 290), PDF 308 (printed 291), PDF 309 (printed 292), PDF 310 (printed 293), PDF 311 (printed 294), PDF 312 (printed 295), PDF 313 (printed 296), PDF 314 (printed 297), PDF 315 (printed 298)]
- **The contents entries on PDF 8–9 (printed vii–viii) are Link elements inside body paragraphs, with no entry style, so I could not request TOC/TOCI.**: The `toc` key needs an entry style or P with exact pages, and the digest does not show how the entries are tagged. [PDF 8 (printed vii), PDF 9 (printed viii)]
- **Several pages have no tagged text: 7, 13, 17, 301 and 318–321, and perhaps 11–12 apart from the map figures.**: They are probably blank or ad pages, but the digest does not confirm it. A person should check for lost content. [PDF 7 (printed vi), PDF 13 (printed xii), PDF 17 (printed xvi), PDF 301 (printed 284), PDF 318 (printed 301), PDF 319 (printed 302), PDF 320 (printed 303), PDF 321 (printed 304)]
- **The extracted text has stray word breaks ('Rus sian', 'Pa cific', 'Mi grant') and drop-cap chapter openers whose first letter is split off ('O', 'T', 'F').**: I can only choose ActualText for headings, so I fixed the title only. A person should check the chapter openers. [PDF 28 (printed 11), PDF 47 (printed 30), PDF 64 (printed 47), PDF 85 (printed 68), PDF 103 (printed 86), PDF 117 (printed 100), PDF 134 (printed 117), PDF 152 (printed 135), PDF 171 (printed 154), PDF 185 (printed 168), PDF 202 (printed 185), PDF 226 (printed 209), PDF 246 (printed 229), PDF 258 (printed 241), PDF 274 (printed 257)]

Reviewer note from the AI: Language changed from en-GB to en-US because the text uses American spelling and the publisher is a US press. The two Figure alts with NUL characters (1692 0, 1696 0) and the cover alt (26594 0) are replaced. The logo on PDF 5 (obj 1692 0) has no image in the digest; I inferred 'Knowledge Unlatched' from the neighboring text, so please verify. The numbered list on PDF 158 is a low-confidence request. The cover move is a reading-order fix, and the executor will reject it if the container does not match. The repeated_lines entries (THE, AND, ariki) are ordinary words, not running heads, so I made no artifact rules. No pdfua_check failures were reported.

### 10. Deferred by the Executor

- the source file already claims PDF/UA conformance: not verified by this pipeline; check it with PAC before relying on it

### 11. Decisions Not Applied (1)

Rejected by validation or by the executor; nothing was half-applied.

- {"op": "move_section", "why": "1 candidate sections, host found: False"}

## What Was Changed

| Change | Count |
|---|---:|
| document: second Document root merged | 1 |
| document: title | 1 |
| document: DisplayDocTitle | 1 |
| document: /Lang | 1 |
| heading: RoleMap level | 2 |
| heading: ActualText | 2 |
| heading: standard tag H1 → H2 (retyped) | 48 |
| retype → H1 | 1 |
| table: header cells marked (work order) | 0 |
| table: cells wrongly tagged as headers set back to data cells | 5 |
| figure: alt text | 35 |
| list: built | 1 |
| notes: Note with /ID | 1013 |
| links: /Contents set | 6486 |
| links: joined existing Link | 6486 |
| links: URL-only description replaced by the sentence around it | 5 |
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
