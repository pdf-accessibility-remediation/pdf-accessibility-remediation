# Remediation Review: sands.pdf

Result: `sands_remediated.pdf`

329 pages · run November 1, 2026, at 7:36 PM · model `anthropic/claude-sonnet-5.5` · prompt `workorder_v10.md` (15b5aa0ade9c6549) · AI cost not recorded · this run: no new call · tokens: saved reply reused, not counted

Intake: none (already tagged)

Libraries: python 3.13.9 · pikepdf 10.5.1 · pdfplumber 0.11.9 · pypdfium2 5.7.1 · pillow 13.0.0 · fonttools 4.62.1

Time: intake 3.8s · audit 35.4s · reuse saved reply 1.9s · apply 228.3s · verify 54.5s · total 323.9s

## Overview

[Open the dashboard](review.html)

**Status:** Not Ready

**Ready to ship?**
- Work Order Approval: Not Approved (applied without a review)
- ✓ OCR Text Approval: Not Applicable
- ✓ Safety Checks: Passed
- Accessibility Evaluation: Not Completed

**Safety checks:** OK ✔ pages look the same · OK ✔ text unchanged · OK ✔ all content tagged or decoration · OK ✔ tag-tree index points into the tree · OK ✔ every font readable  
**Needs a person:** 14 (6 deferred by the AI · 5 deferred by the executor · 3 CHECK rows)  
**AI decisions:** 100 in the work order, applied without review by a person  
**Fixed automatically (no AI):** links tied and described 2,309 · tag-tree index entries 1,182 · note IDs 495 · standard tags un-remapped (7.1-7) 83 · empty tags removed 69 · decorative lines marked 53 · figures moved to their page 15 · link descriptions that were only a URL 13 · title shown in the window 1  
**veraPDF (WCAG 2.2 machine checks):** 3 WCAG rules failing before (3,130 checks) → 1 after (1 check) · 0 newly failing

Automated checks are evidence, not sign-off.

| Top issues | Pages | Where |
|---|---|---|
| Executor applied every decision: 1 rejected · 0 failed (listed under "Decisions not applied") | see §21 | [§21](#21-decisions-not-applied-2) |
| Content neither tagged nor marked as decoration (veraPDF 7.1-3, 1 check) | PDF 152 (printed 143) | [§17](#17-verapdf-wcag-22-machine-profile-before-and-after) |
| Reading order jumps back up a column (6 jumps) | PDF 149 (printed 140) | [§18](#18-wcag-checks-verapdf-does-not-make) |
| 230 Han-only runs need Japanese or Chinese (han_review.csv) | 9 pages, PDF 59 (printed 50) to PDF 319 (printed 310) | [§20](#20-deferred-by-the-executor) |
| 13 captions not grouped: several figures on the page | PDF 149 (printed 140), PDF 152 (printed 143), PDF 232 (printed 223), PDF 284 (printed 275) | [§20](#20-deferred-by-the-executor) |
| … and 6 more | | §19 |

Automated checks are evidence, not legal sign-off. Items marked **CHECK**, and everything under "For a person to check", need a human.

## Automated Checks

| Check | Result | Detail |
|---|---|---|
| Every page looks the same as the original | OK | 0 pages differ |
| Published text unchanged | OK | 0 pages changed |
| All content tagged or marked as decoration | OK | 0 untagged characters · 0 untagged objects |
| Untagged paths: none left | OK | 0 untagged paths · 53 rules, borders and lines marked as decoration by this run |
| Invisible OCR text: every glyph defined | OK | no undefined glyphs in invisible text |
| OCR words: every printed spelling attached | OK | 0 misread forms given their printed spelling in 0 places |
| Page-level figure wrap | OK | no page with only an untagged drawing |
| Empty tags removed when proven empty | OK | 69 removed |
| Tag-tree index points only into the tree | OK | 0 dangling entries · 21 stale entries (marked content no longer drawn) |
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
| Headings: no skipped levels | OK | H1 1 · H2 22 · H3 56 · H4 4 |
| Headings: exactly one H1 (the title) | OK | 1 H1 (several H1s usually mean parts or chapters were not demoted) |
| Figures: none with empty or placeholder alt | OK | 86 figures, 0 placeholder |
| Every Note has a unique ID | OK | 495 notes · 0 without ID · 0 duplicate · 0 not in the ID tree |
| Bookmarks present (documents over 9 pages) | OK | 22 bookmarks |
| Model reply held one work order | OK | one |
| Executor applied every decision | **CHECK** | 1 rejected · 0 failed (listed under "Decisions not applied") |
| Nothing deferred by the executor | **CHECK** | 14 deferred (listed under "Deferred by the executor") |
| Fonts: every glyph defined (no .notdef) | OK | none found |
| Fonts: every embedded font program could be read | OK | all read |
| Fonts: embedded and mapped to Unicode | OK | 0 not embedded · 0 without ToUnicode |
| Tab order follows the tag structure on pages with links or other annotations | OK | 0 of 229 pages with annotations lack /Tabs /S |
| Characters with no Unicode value (checklist 3.6) | OK | 0 read-aloud characters with no Unicode value |
| Private-use characters (checklist 3.6) | OK | 0 read-aloud characters with private-use codes |
| Title and language set | OK | "Countless Sands: Medieval Buddhists and Their Environments" · en-US |
| veraPDF WCAG 2.2 (machine): no WCAG failures | **CHECK** | before: 3 WCAG rules failed (3130 checks) → after: 1 WCAG rule failed (1 checks) · 1 PDF/UA-only rules not counted (listed under "veraPDF") |
| veraPDF: no rule newly failing or failing more often | OK | 2 fixed · 2 still failing · 0 newly failing |
| Alt text: none like a file name or repeated on many figures (1.1.1) | OK | 0 of 86 figures flagged |
| Tables: every table has header cells (1.3.1) | OK | none without |
| Reading order: no page jumps back up a column (1.3.2) | **CHECK** | 1 of 302 pages flagged |
| Reading order: no section moved away from its printed place by this run (1.3.2) | OK | 0 new · 1 already in the original, of 157 sections and blocks |
| Title is not a file name or placeholder (2.4.2) | OK | "Countless Sands: Medieval Buddhists and Their Environments" |
| Link text: none like "click here" (2.4.4) | OK | 0 generic |
| Headings: none empty, very long or repeated in a row (2.4.6) | OK | 0 empty · 0 long · 0 repeated |

## For a Person to Check

### 1. Alt Text Written or Changed by the AI (26)

| Page | Before | After |
|---|---|---|
| PDF 1 (printed COVER) | The cover of Countless Sands: Medieval Buddhists and Their Environments, edited by Jeffrey Moser and Jason Protass features a carbon print image of a pagoda on a small island surrounded by water. The pagoda's image is reflected in the water, creating a mirror effect. The top of the book cover is blue with an ombre-fade into an orange- yellow on the bottom of the cover.\x00 | Cover of Countless Sands: Medieval Buddhists and Their Environments, edited by Jeffrey Moser and Jason Protass. A colorized carbon-print photograph of a pagoda-topped pavilion on a small island with a large tree, reflected in still water; the sky fades from blue at the top to orange-yellow at the bottom. The title is at the top and the editors’ names at the bottom. |
| PDF 4 (printed iii) | Illustration. | University of Hawai‘i Press logo |
| PDF 85 (printed 76) | Low-relief stone-carved image of a stupa with one section highlighted, showing a small scene of people venerating another stupa | Nāgārjunakoṇḍa drum slab relief of a stupa; a white box marks a small scene of people venerating another stupa, enlarged in the detail beside it. |
| PDF 85 (printed 76) | Low-relief stone-carved image of a stupa with one section highlighted, showing a small scene of people venerating another stupa | Close-up of the highlighted panel: a small relief of a stupa with attendant figures on either side. |
| PDF 85 (printed 76) | Low-relief stone-carved image of a stupa with one section showing a partial view of an image of another stupa in the circumambulatory path. | Amarāvatī drum slab relief of a stupa; a white box marks the section, in the circumambulatory path, that is enlarged in the detail beside it. |
| PDF 85 (printed 76) | Low-relief stone-carved image of a stupa with one section showing a partial view of an image of another stupa in the circumambulatory path. | Close-up of the highlighted section: a partial view of another stupa image carved into the circumambulatory path of the slab. |
| PDF 149 (printed 140) | Three photographs of cave entrances and plan of cave interior on lower right. | Photograph (a), shown rotated sideways, of the columned front of Cave 29 (Dumar Lena) at Ellora. |
| PDF 149 (printed 140) | Three photographs of cave entrances and plan of cave interior on lower right. | Photograph, shown rotated sideways, of a steep rock face with a cave opening and a railed path climbing beside it. |
| PDF 149 (printed 140) | Three photographs of cave entrances and plan of cave interior on lower right. | Photograph (b) looking down a narrow stepped passage into the cave entrance. |
| PDF 149 (printed 140) | Three photographs of cave entrances and plan of cave interior on lower right. | Plan of Cave 29 (Dumar Lena) with a compass rose, showing the central hall, the shrine at left and the three entrances marked a, b and c. |
| PDF 152 (printed 143) | Six photographs of rock-cut sculptures of deities and plan of cave at center. | Photograph (a), shown rotated sideways, of a relief panel of a multi-armed Śiva and attendants on a cave wall between pillars. |
| PDF 152 (printed 143) | Six photographs of rock-cut sculptures of deities and plan of cave at center. | Photograph (b), shown rotated sideways, of a relief panel of a dancing deity on a cave wall. |
| PDF 152 (printed 143) | Six photographs of rock-cut sculptures of deities and plan of cave at center. | Photograph (c), shown rotated sideways, of a worn relief panel of rows of small figures. |
| PDF 152 (printed 143) | Six photographs of rock-cut sculptures of deities and plan of cave at center. | Photograph (d), shown rotated sideways, of a relief panel of standing figures between carved pillars. |
| PDF 152 (printed 143) | Six photographs of rock-cut sculptures of deities and plan of cave at center. | Photograph (f), shown rotated sideways, of a carved figure in a recess between pillars, with an inscription at right. |
| PDF 152 (printed 143) | Six photographs of rock-cut sculptures of deities and plan of cave at center. | Plan of Cave 29 (Dumar Lena), shown rotated sideways, with a compass rose and the relief locations lettered a to f. |
| PDF 176 (printed 167) | Ink Painting of Bodhidharma standing on a reed in the middle of the Yangzi River
 | Ink painting of Bodhidharma standing on a reed in the middle of the Yangzi River, with a column of inscription and seals at the top left. |
| PDF 179 (printed 170) | Old photograph of Jinshan Monastery with boats moored by its entrance.
 | Old photograph of Jinshan Monastery on its hill, with a pagoda and pavilion above the temple halls and boats moored at its entrance. |
| PDF 180 (printed 171) | Woodcut image of Changlu Monastery near waterways.
 | Woodcut spread of Changlu Monastery among trees, fields and waterways, with sails on the river. |
| PDF 183 (printed 174) | Woodcut image of Ganlu Monastery abutting the Yangzi River at Zhenjiang
 | Woodcut of Ganlu Monastery on Mount Beigu above the Yangzi River, with sailboats on the water and a pagoda at the right. |
| PDF 184 (printed 175) | Photograph of remnants of Iron Pagoda at Ganlu Monastery taken in 2019
 | Photograph, taken in 2019, of the remnants of the Iron Pagoda at Ganlu Monastery: a tiered octagonal pagoda of dark iron among trees. |
| PDF 193 (printed 184) | Photograph of Nanjing Chemical Industrial Park take from gate of Old Changlu Monastery in 2018
 | Photograph, taken in 2018 from the gate of Old Changlu Monastery, of the chimneys, pipes and buildings of a chemical plant. |
| PDF 193 (printed 184) | Photograph of Old Changlu Monastery front gate taken in 2018
 | Photograph of the front gate of Old Changlu Monastery in 2018: a red-pillared gate with tiled roofs, closed, with a red banner across it. |
| PDF 194 (printed 185) | Photograph of new Changlu Monastery under construction taken in 2018
 | Photograph, taken in 2018, of the main hall of the new Changlu Monastery under construction: a large two-tiered hall with orange roofs and two flags. |
| PDF 210 (printed 201) | Satellite image showing location of Stone Treasure Mountain and Dharma Treasury Temple in relation to Dali
 | Satellite map of part of Yunnan marking the locations of Stone Treasure Mountain, Dali, Dharma Treasury Temple and Kunming. |
| PDF 211 (printed 202) | Satellite image showing location of Stone Treasure Mountain adjacent to Mingjianshao
 | Satellite image, shown rotated sideways, of the Jianchuan region marking Stone Treasure Mountain next to Mingjianshao, with Baoxiang Temple to the south. |

### 2. Figures That Kept Their Existing Alt Text (60)

Not changed by the AI. Check they are adequate.

| Page | Alt text |
|---|---|
| PDF 81 (printed 72) | Low-relief stone-carved image of a large seated Buddha surrounded by figures, one of whom carries a small representation of the Buddha |
| PDF 83 (printed 74) | Low-relief stone-carved image of a large, domed stupa covered by small relief sculptures and surrounded by worshipping figures |
| PDF 84 (printed 75) | Diagram of a stupa showing locations where images of stupas appear on its surface, and where images of stupas appear within those images |
| PDF 86 (printed 77) | Low-relief stone-carved image of a stupa with images on it depicted other sacred sites and/or objects |
| PDF 87 (printed 78) | Monumental sculpture of a multi-armed bodhisattva wearing a painted lower garment |
| PDF 88 (printed 79) | Detail of a painting on the lower garment of a monumental sculpture, showing scenes of devotees at temples in a landscape |
| PDF 89 (printed 80) | Detail of a painting on the lower garment of a monumental sculpture, showing a green-skinned goddess in a temple with water in front |
| PDF 90 (printed 81) | Diagram of a sculpture in a shrine, with detail showing the painted figures on its surface are similarly sculptures standing inside shrines |
| PDF 92 (printed 83) | Supine figure of an ogress whose body is depicted as the landscape of Tibet, including major temples and sacred sites |
| PDF 100 (printed 91) | Pale green inkstone with fine lateral striations, held in a pale green stone box with ocher-colored low relief carving of lotuses. |
| PDF 101 (printed 92) | Monumental reclining Buddha carved into natural sandstone rock face. |
| PDF 107 (printed 98) | Small cross-legged Buddhas carved into stone protruding down from the ceiling of a natural cavern. |
| PDF 109 (printed 100) | Two luohans carved in high relief on rocky protrusion. One is oriented toward the viewer, while the other is oriented ninety degrees to the viewer’s left. |
| PDF 110 (printed 101) | Carving of rotund, smiling Budai surrounding by eighteen luohans in a rocky grotto. |
| PDF 112 (printed 103) | Square niche holding rock-cut image of Amitāyus cut into irregular rock face. |
| PDF 114 (printed 105) | Rectangular niche holding rock-cut Buddha cut into irregular rock face. |
| PDF 115 (printed 106) | Rectilinear niche in natural rock face containing secondary, sculpted niche holding image of multi-armed figure flanked by fierce guardians. |
| PDF 123 (printed 114) | Map of the world, surrounded by surging sea and numerous blocks of text in white boxes. |
| PDF 127 (printed 118) | Map of the world with the Himalaya Mountains at the center and the regions of China and Japan colored. |
| PDF 132 (printed 123) | Black and white image of mountains in a V-shape, with columns of Chinese characters at the middle. |
| PDF 134 (printed 125) | Image of the world as a red and blue column set on a stepped pyramid. |
| PDF 135 (printed 126) | Map showing Eurasia, Africa, and Australia with blue and green bands of sea and continents above. |
| PDF 136 (printed 127) | Black and white images of the world as a v-shaped landmass with blocks of text between many rivers. |
| PDF 143 (printed 134) | Satellite image of Ellora and surrounding area. |
| PDF 147 (printed 138) | Photograph of steps leading to elevated path around small olive green pool. |
| PDF 148 (printed 139) | Photograph of cave entrances at base of steep slope with scattered brush. |
| PDF 157 (printed 148) | Photograph of narrow drainage channel passing through tall vertical cave entrance. |
| PDF 159 (printed 150) | Photograph of beige rock-cut cave entrances in a grey stone slope. |
| PDF 160 (printed 151) | Photograph of rock-cut sculpture of twelve cross-legged Buddhist deities on four tiers. |
| PDF 216 (printed 207) | Photograph of rock-cut niche with crowed royal figure at center and surrounding retinue. |
| PDF 217 (printed 208) | Photograph of grey rock-cut niche with raised curtain over royal figure and retinue. |
| PDF 218 (printed 209) | Photograph of rock-cut Buddhist triad flanked with fierce, multi-headed guardian figures. |
| PDF 219 (printed 210) | Photograph of rock-cut images of fierce, multi-headed guardian figures. |
| PDF 221 (printed 212) | Photograph of stone niche containing dark, oil-stained vulva-shaped depression. |
| PDF 229 (printed 220) | Photograph of hillside with bamboo, conifers, and brick building |
| PDF 231 (printed 222) | Map of Shizhuanshan showing temple to east and carved niches to west and south |
| PDF 232 (printed 223) | Photograph of Buddhist sculptures carved in sandstone—three main seated figures and numerous standing figures |
| PDF 232 (printed 223) | Photograph of low-relief standing figured carved into sandstone cliff |
| PDF 233 (printed 224) | Photograph of Buddhist sculptures carved into cliff face above and man seated beside an offering table below |
| PDF 234 (printed 225) | Photograph of low-relief carved sculpture of standing Buddhist deity with smaller standing human attendants |
| PDF 236 (printed 227) | Photograph of long Chinese text engraved in cliff face with wooden protective structure at top |
| PDF 238 (printed 229) | Photograph of seated buddha with clouds surrounding head and standing attendants carved into sandstone cliff |
| PDF 239 (printed 230) | Photograph of low-relief standing figures carved into sandstone cliff |
| PDF 242 (printed 233) | Photograph of multi-sided pillar supported by demon carved into sandstone cliff, with wrathful guardian behind |
| PDF 270 (printed 261) | Photograph of rock-cut sculpture of the heads and torsos of three fierce deities. |
| PDF 271 (printed 262) | Photograph of multicolored rock-cut sculpture of numerous figures beneath a large stone overhang. |
| PDF 276 (printed 267) | Photograph of rock-cut sculptures overlaid with numerals 1 to 10 and white text “Liu’s Followers,” etc. |
| PDF 276 (printed 267) | Photograph of rock-cut sculpture of Liu Benzun’s sixth austerity, with inscription. |
| PDF 278 (printed 269) | Photograph of the rock-cut standing figure with demonic face holding the wheel of reincarnation. |
| PDF 282 (printed 273) | Plan showing distribution of reliefs at the Large Buddha Bend. |
| PDF 284 (printed 275) | Photograph of rock-cut reliefs of judges seated behind altars above and the punishment of the dead in hell below. |
| PDF 284 (printed 275) | Photograph of rock-cut relief carving of nine armored standing figures. |
| PDF 285 (printed 276) | Photograph of rock-cut niche containing large central image of the Buddha, flanked by the eight protectors. |
| PDF 286 (printed 277) | Photograph of rock-cut carving of a pair of fierce, multi-armed deities holding various ritual implements. |
| PDF 291 (printed 282) | Aerial photography of small reservoir surrounded by woodland, with several narrow inlets on the right. |
| PDF 295 (printed 286) | Woodblock printed image of an inverted stepped pyramid on top of a steeped pyramid, surrounded by concentric squares and circles. |
| PDF 301 (printed 292) | Photograph of a small volcano behind a blue lake. |
| PDF 305 (printed 296) | Map of Masuda Lake, showing location of two adjacent keyhole-shaped tombs. |
| PDF 306 (printed 297) | Woodblock printed image of enormous stele foundation stone amid rolling hills. |
| PDF 307 (printed 298) | Rubbing of twelve columns of Kukai’s Masuda Lake inscription. |

### 3. Headings

Heading levels by style (as applied):

| Style | Level | How | Elements |
|---|---|---|---:|
| part_n | H2 | RoleMap | 4 |
| part_tit | H2 | RoleMap | 4 |
| chap_n | H2 | RoleMap | 13 |
| chap_tit | H2 | RoleMap | 14 |
| chap_stit | H2 | RoleMap | 6 |
| FMT_BMT | H2 | RoleMap | 5 |
| h1 | H3 | RoleMap | 44 |
| BMT_notes | H3 | RoleMap | 12 |
| bibh1 | H4 | RoleMap | 4 |

Merged: `part_n` into the next `part_tit`; `chap_n` into the next `chap_tit`; `chap_stit` into the prev `chap_tit`

Spoken text set by the AI (should match what is printed):

| Page | Text |
|---|---|
| PDF 10 (printed 1) | PART I Introductions |
| PDF 12 (printed 3) | CHAPTER 1 Medieval Buddhists and Their Environments |
| PDF 23 (printed 14) | CHAPTER 2 Contextualizing the Relationship between Nature and Culture in East Asian Buddhism |
| PDF 62 (printed 53) | PART II Matters of Scale and the Environment |
| PDF 64 (printed 55) | CHAPTER 3 Flesh Mountain Human Bodies on a Nonhuman Scale |
| PDF 79 (printed 70) | CHAPTER 4 Movements and Patterns in Embodied Landscapes for Art |
| PDF 99 (printed 90) | CHAPTER 5 Geomorphism at “The Peak That Flew in from Afar” |
| PDF 122 (printed 113) | CHAPTER 6 The Japanese Image of the Buddhist Earth Geography, Cosmology, and the Culture of Vision |
| PDF 140 (printed 131) | PART III Environments in the Shaping of Medieval Buddhism |
| PDF 142 (printed 133) | CHAPTER 7 Human Places and Cosmic Spaces Ecological Engagements at Ellora |
| PDF 172 (printed 163) | CHAPTER 8 Riverine Buddhism at Changlu Monastery |
| PDF 204 (printed 195) | CHAPTER 9 Masculine Mountains Gendered Affordances at Dali’s Stone Treasure Grottoes |
| PDF 228 (printed 219) | CHAPTER 10 The Geoaesthetics of Ritual in the Chinese Buddhist Sanctuary of Shizhuanshan (ca. 1082–1096) |
| PDF 252 (printed 243) | PART IV Environments as Mediums of Practice |
| PDF 254 (printed 245) | CHAPTER 11 “Occasions Both Worldly and Transcendent” Sacred Trees in Buddha’s India |
| PDF 269 (printed 260) | CHAPTER 12 Vidyārājas and the Articulation of Ecological Interdependence at Cave Temples |
| PDF 290 (printed 281) | CHAPTER 13 Mountains, Waters, and Dharmakāya Kūkai’s Irrigation Projects |

### 4. Elements Retyped by the AI (2)

Check each one is (or is not) a heading as decided.

| Page | Text | Before | After |
|---|---|---|---|
| PDF 4 (printed iii) | Countless Sands | dev_p | H1 |
| PDF 23 (printed 14) | (no text) | H1 | P |

### 5. Scanned Book: The Text Layer Comes from OCR

6 of 329 pages are full-page images. Screen readers read the OCR text, which may contain recognition errors (suspect-token rate 16.4 per 1,000). Spot-check these pages against the scan: PDF 4 (printed iii), PDF 84 (printed 75), PDF 123 (printed 114), PDF 136 (printed 127), PDF 152 (printed 143), PDF 266 (printed 257), PDF 290 (printed 281), PDF 315 (printed 306). Corrections to the text itself are an editorial decision.

### 6. OCR Words Given Their Printed Spelling (0 forms, 0 places)

The OCR misread these words, mostly letters with diacritics (ā or ū read as "ii"). The AI read each word from a crop of the scan. Screen readers now speak the printed spelling, and copying gives it (ActualText); the OCR text underneath is unchanged, so a text search still finds the OCR spelling. Apps that ignore ActualText (Preview and other PDFKit readers, some checkers) still show the OCR spelling. Check each reading against the scan on its first page.

- 8 suspect forms were checked by the AI; 8 were judged correct as the OCR read them, or unreadable (e.g. "Hawaii"), and left alone.

### 7. Text a Screen Reader Could Not Reach (before this run)

13 pages had text outside the tag tree: 1184 orphan runs (marked, but no tag owns them) and 0 untagged runs. Running heads and page numbers among them can be hidden as decoration; real content must be added to the tag tree by a person. After this run: 0 untagged characters, 0 orphan runs remain.

Pages: PDF 20 (printed 11), PDF 54 (printed 45), PDF 78 (printed 69), PDF 95 (printed 86), PDF 120 (printed 111), PDF 138 (printed 129), PDF 169 (printed 160), PDF 200 (printed 191), PDF 225 (printed 216), PDF 248 (printed 239), PDF 267 (printed 258), PDF 288 (printed 279), PDF 314 (printed 305)

### 8. Hidden from Screen Readers (artifacts)

- 10 decorative elements ("decorative landscape on Part I opener", "decorative landscape on half-title page", "decorative landscape vignette on title page", "wave ornament") on PDF 2 (printed i), PDF 4 (printed iii), PDF 10 (printed 1), PDF 68 (printed 59), PDF 93 (printed 84), PDF 165 (printed 156), PDF 195 (printed 186), PDF 244 (printed 235), PDF 264 (printed 255), PDF 309 (printed 300)

### 9. Reading Order Changes

Listen through these spots with a screen reader.

- Figure on PDF 81 (printed 72) moved to read with its page (it read after PDF 139 (printed 130); now after PDF 82 (printed 73))
- Figure on PDF 83 (printed 74) moved to read with its page (it read after PDF 139 (printed 130); now after PDF 84 (printed 75))
- Figure on PDF 84 (printed 75) moved to read with its page (it read after PDF 139 (printed 130); now after PDF 86 (printed 77))
- Figure on PDF 85 (printed 76) moved to read with its page (it read after PDF 307 (printed 298); now after PDF 86 (printed 77))
- Figure on PDF 85 (printed 76) moved to read with its page (it read after PDF 307 (printed 298); now after PDF 86 (printed 77))
- Figure on PDF 86 (printed 77) moved to read with its page (it read after PDF 307 (printed 298); now after PDF 87 (printed 78))
- Figure on PDF 143 (printed 134) moved to read with its page (it read after PDF 250 (printed 241); now after PDF 144 (printed 135))
- Figure on PDF 147 (printed 138) moved to read with its page (it read after PDF 250 (printed 241); now after PDF 148 (printed 139))
- Figure on PDF 148 (printed 139) moved to read with its page (it read after PDF 250 (printed 241); now after PDF 148 (printed 139))
- Figure on PDF 270 (printed 261) moved to read with its page (it read after PDF 329 (printed 320); now after PDF 271 (printed 262))
- Figure on PDF 271 (printed 262) moved to read with its page (it read after PDF 329 (printed 320); now after PDF 272 (printed 263))
- Figure on PDF 276 (printed 267) moved to read with its page (it read after PDF 329 (printed 320); now after PDF 277 (printed 268))
- Figure on PDF 276 (printed 267) moved to read with its page (it read after PDF 329 (printed 320); now after PDF 277 (printed 268))
- Figure on PDF 278 (printed 269) moved to read with its page (it read after PDF 329 (printed 320); now after PDF 279 (printed 270))
- Figure on PDF 282 (printed 273) moved to read with its page (it read after PDF 329 (printed 320); now after PDF 283 (printed 274))

### 10. Untagged Paths (rules, borders, lines)

53 paths drawn outside any tag were marked as decoration: none of them carries text, an image or a link, and none touches untagged text or images.

### 11. Orphan Content Added to the Tag Tree (247 paragraphs)

Real content that was marked but in no tag, now read in page order after the last tagged block on its page. Listen through these pages:

- PDF 20 (printed 11) ("endnotes and works cited"): 4 runs → 3 paragraphs, starting "NOTES"
- PDF 54 (printed 45) ("endnotes"): 108 runs → 21 paragraphs, starting "115."
- PDF 78 (printed 69) ("endnotes"): 77 runs → 16 paragraphs, starting "41."
- PDF 95 (printed 86) ("endnotes"): 125 runs → 28 paragraphs, starting "19."
- PDF 120 (printed 111) ("endnotes"): 88 runs → 22 paragraphs, starting "share with those traditions: the deliberate, sculptural highlighting of a rough and unfin"
- PDF 138 (printed 129) ("endnotes"): 115 runs → 20 paragraphs, starting "6."
- PDF 169 (printed 160) ("endnotes"): 91 runs → 20 paragraphs, starting "61."
- PDF 200 (printed 191) ("endnotes"): 93 runs → 25 paragraphs, starting "71."
- PDF 225 (printed 216) ("endnotes"): 87 runs → 14 paragraphs, starting "35."
- PDF 248 (printed 239) ("endnotes and works cited"): 81 runs → 18 paragraphs, starting "WORKS CITED"
- PDF 267 (printed 258) ("endnotes"): 119 runs → 19 paragraphs, starting "Pali- English Dictionary,"
- PDF 288 (printed 279) ("endnotes"): 106 runs → 22 paragraphs, starting "5."
- PDF 314 (printed 305) ("endnotes"): 90 runs → 19 paragraphs, starting "inscription refers to the monk as “En risshi,” the Vinaya Master En. However, Shūen was"

### 12. Spoken Text (ActualText) Checked Against the Print (17 accepted with differences, 0 rejected)

A spoken text may differ from the printed characters only in spacing, letter case and line-end hyphens (sponsor rule 1). Accepted ones that differ are listed so a person can listen to them; rejected ones added or changed words or punctuation.

- Accepted, PDF 10 (printed 1): printed "PART I Introductions" → spoken "PART I Introductions"
- Accepted, PDF 12 (printed 3): printed "CHAPTER 1 Medieval Buddhists and Their Environments" → spoken "CHAPTER 1 Medieval Buddhists and Their Environments"
- Accepted, PDF 23 (printed 14): printed "CHAPTER 2 Contextualizing the Relationship between Nature and Culture in East Asian Buddhism" → spoken "CHAPTER 2 Contextualizing the Relationship between Nature and Culture in East Asian Buddhism"
- Accepted, PDF 62 (printed 53): printed "PART II Matters of Scale and the Environment" → spoken "PART II Matters of Scale and the Environment"
- Accepted, PDF 64 (printed 55): printed "CHAPTER 3 Flesh Mountain Human Bodies on a Nonhuman Scale" → spoken "CHAPTER 3 Flesh Mountain Human Bodies on a Nonhuman Scale"
- Accepted, PDF 79 (printed 70): printed "CHAPTER 4 Movements and Patterns in Embodied Landscapes for Art" → spoken "CHAPTER 4 Movements and Patterns in Embodied Landscapes for Art"
- Accepted, PDF 99 (printed 90): printed "CHAPTER 5 Geomorphism at “The Peak That Flew in from Afar”" → spoken "CHAPTER 5 Geomorphism at “The Peak That Flew in from Afar”"
- Accepted, PDF 122 (printed 113): printed "CHAPTER 6 The Japanese Image of the Buddhist Earth Geography, Cosmology, and the Culture of Vision" → spoken "CHAPTER 6 The Japanese Image of the Buddhist Earth Geography, Cosmology, and the Culture of Vision"
- Accepted, PDF 140 (printed 131): printed "PART III Environments in the Shaping of Medieval Buddhism" → spoken "PART III Environments in the Shaping of Medieval Buddhism"
- Accepted, PDF 142 (printed 133): printed "CHAPTER 7 Human Places and Cosmic Spaces Ecological Engagements at Ellora" → spoken "CHAPTER 7 Human Places and Cosmic Spaces Ecological Engagements at Ellora"
- Accepted, PDF 172 (printed 163): printed "CHAPTER 8 Riverine Buddhism at Changlu Monastery" → spoken "CHAPTER 8 Riverine Buddhism at Changlu Monastery"
- Accepted, PDF 204 (printed 195): printed "CHAPTER 9 Masculine Mountains Gendered Affordances at Dali’s Stone Treasure Grottoes" → spoken "CHAPTER 9 Masculine Mountains Gendered Affordances at Dali’s Stone Treasure Grottoes"
- Accepted, PDF 228 (printed 219): printed "CHAPTER 10 The Geoaesthetics of Ritual in the Chinese Buddhist Sanctuary of Shizhuanshan (ca…" → spoken "CHAPTER 10 The Geoaesthetics of Ritual in the Chinese Buddhist Sanctuary of Shizhuanshan (ca. 1082–1096)"
- Accepted, PDF 252 (printed 243): printed "PART IV Environments as Mediums of Practice" → spoken "PART IV Environments as Mediums of Practice"
- Accepted, PDF 254 (printed 245): printed "CHAPTER 11 “Occasions Both Worldly and Transcendent” Sacred Trees in Buddha’s India" → spoken "CHAPTER 11 “Occasions Both Worldly and Transcendent” Sacred Trees in Buddha’s India"
- Accepted, PDF 269 (printed 260): printed "CHAPTER 12 Vidyārājas and the Articulation of Ecological Interdependence at Cave Temples" → spoken "CHAPTER 12 Vidyārājas and the Articulation of Ecological Interdependence at Cave Temples"
- Accepted, PDF 290 (printed 281): printed "CHAPTER 13 Mountains, Waters, and Dharmakāya Kūkai’s Irrigation Projects" → spoken "CHAPTER 13 Mountains, Waters, and Dharmakāya Kūkai’s Irrigation Projects"

### 13. Links Whose Description Was Only a URL (13, and 2 addresses that look broken)

The description (what a screen reader announces) was set to the book's own sentence around the link, with the URL removed. No words were added and the visible URL is unchanged. Replace any of these with a better description if needed.

| Page | URL | Description now |
|---|---|---|
| PDF 5 (printed iv) | https://lccn.loc.gov/2024003970 | LC record available at |
| PDF 5 (printed iv) | https://lccn.loc.gov/2024003971 | LC ebook record available at |
| PDF 76 (printed 67) | https://www.theatlantic.com | Alan Taylor, “Photos: The 15 Tallest Statues in the World,” Atlantic, October 31, 2018,6. |
| PDF 76 (printed 67) | https://www.travelogyindia.com | “Top 20 Tallest Statues in the World,” Travelogy India, accessed June 20, 2019,7. |
| PDF 77 (printed 68) | https://www.scientificamerican.com | As I am not mathematically inclined, I do not really understand all of the details—but for one basic explanation of the different “sizes” of infinity, see John Matson, “Strange but True: Infinity Comes in Different Sizes,” Scientific American, July 19, 2007,33. |
| PDF 96 (printed 87) | https://doi.org/10.4000/emscat.1803 | “Skirting the Bodhisattva: Fabricating Visionary Art.” Études mongoles et sibériennes, centrasiatiques et tibétaines, no. 42 (December 19, 2011). |
| PDF 98 (printed 89) | https://www.persee.fr/doc/asie_0766-1177_2011_num_20_1_1373 | Early Eleventh Century Dhāraṇī Prints in the Ruiguangsi Pagoda.” Cahiers d’Extrême- Asie 20 (2011): 127–160. |
| PDF 139 (printed 130) | http://www.buddhism-dict.net/ddb/ | July 1995. |
| PDF 200 (printed 191) | https://www.basf.com  | Accessed June 4, 2020, at in BYC_2018_EN.pdf. |
| PDF 200 (printed 191) | http://id.lib.harvard.edu | Accessed online at the Harvard- Yenching Library Chinese Local Gazetteers Digitization Project.Fenyang wude chanshi yulu. |
| PDF 200 (printed 191) | https://archive.wul.waseda.ac.jp/kosho/ru05/ru05_03342/ | Accessed online from Waseda University Library, June 19, 2020. |
| PDF 202 (printed 193) | https://www.basf.com | BASF, 2005. |
| PDF 289 (printed 280) | https://critinq.wordpress.com/2020/04/17/novel-corona-posthuman-virus/ | April 17, 2020. |

Link addresses that look broken (listed, not changed):

- PDF 49 (printed 40): `https://tomdispatch.com/post/174949,`: the address ends with punctuation or an unmatched closing bracket from the printed text; probably broken
- PDF 49 (printed 40): `https://tomdispatch.com/post/174949,`: the address ends with punctuation or an unmatched closing bracket from the printed text; probably broken

### 14. Empty Tags (69 removed, 0 kept)

A tag is removed only when proven empty: nothing under it holds content, it carries no Alt, ActualText, E or ID, and nothing in the file refers to it except its parent. Table cells are never removed one by one; a table goes only when every part is empty.

- Removed: 22 index, 20 glossaire, 11 copy, 7 Ancre, 4 Unumbered_headnote, 3 dev_p, 1 P, 1 Story

### 15. Tag-tree Index Entries Cleared (1)

Entries that pointed at a tag no longer in the tag tree (left by the source file, or by a tag the run removed). Nothing reads such a tag; no page, text or reachable tag changed.

- ParentTree, PDF 152 (printed 143): MCID 8228 (Figure)

### 16. Captions Paired by Position (8)

Pages with several figures: each caption was tied to the figure right next to it. Check the pairs.

- PDF 85 (printed 76): "Figure 4.4 Nāgārjunakoṇḍa drum slab, Metropolitan Museum 28.31. Left photograph courtesy of the…"
- PDF 85 (printed 76): "Figure 4.5 Amarāvatī drum slab, British Museum 1880,0709.72. Left photograph courtesy of the British…"
- PDF 193 (printed 184): "Figure 8.6 View of Nanjing Titanium Dioxide Chemical Company from the front gate of Old Changlu…"
- PDF 193 (printed 184): "Figure 8.7 Old Changlu Monastery’s front gate, Luhe County, 2018. Photograph by the author."
- PDF 232 (printed 223): "Figure 10.4 Wen Weijian et al., Zimu dian niches 3 and 4: Earth God (and Mountain God?) (left); and…"
- PDF 276 (printed 267): "Figure 12.3 The Four Levels of Beings in the Ten Austerities of Liu Benzun, Large Buddha Bend…"
- PDF 276 (printed 267): "Figure 12.4 Liu Benzun’s sixth austerity, from the Ten Austerities of Liu Benzun, Large Buddha Bend…"
- PDF 284 (printed 275): "Figure 12.8 Nine Protectors of the Law, Large Buddha Bend, Baodingshan, Dazu, Chongqing, 1177–1249…"

### 17. veraPDF (WCAG 2.2 machine profile), Before and After

veraPDF 1.30.3, profile "WCAG 2.2 machine validation profile" (7da399cf5baa). Counts are failed checks; pages are from the first checks veraPDF lists for each rule, so a rule may fail on more pages. Rules that only PDF/UA requires are listed apart and do not count. "Who fixes" is who can act on the rule: the pipeline by itself, the AI through the work order, or only a person. **Newly failing** means this run broke something the original passed. Before: 3 rules failing (the AI can act on 1, the pipeline on 2, only a person on 0). After: 1.

| Rule | WCAG | What it checks | Who fixes | Before | After | Status | Pages (after, else before) |
|---|---|---|---|---:|---:|---|---|
| ISO 14289-1 7.1-3 | 1.3.1 | Content shall be marked as Artifact or tagged as real content e.g. "Content is neither marked as Artifact nor tagged as real content" | the AI (`artifacts`) | 1504 | 1 | still failing | PDF 152 (printed 143) |
| ISO 14289-1 7.18.5-1 | 2.4.4, 4.1.2 | Links shall be tagged according to ISO 32000-1:2008, 14.8.4.4.2, Link Element | the pipeline | 1543 | 0 | fixed | PDF 322 (printed 313) |
| ISO 14289-1 7.1-7 | 1.3.1, 4.1.2 | Standard tags defined in ISO 32000-1:2008, 14.8.4, shall not be remapped | the pipeline (83 changed) | 83 | 0 | fixed | PDF 81 (printed 72), PDF 83 (printed 74), PDF 84 (printed 75), PDF 85 (printed 76), PDF 86 (printed 77), PDF 87 (printed 78), PDF 88 (printed 79), PDF 89 (printed 80), PDF 90 (printed 81), PDF 92 (printed 83), PDF 100 (printed 91), PDF 101 (printed 92), PDF 107 (printed 98), PDF 109 (printed 100), PDF 110 (printed 101), PDF 112 (printed 103), PDF 114 (printed 105), PDF 115 (printed 106), PDF 123 (printed 114) |

PDF/UA-only, not required for WCAG (not counted):

- 7.21.5-1: glyph width consistency (2 checks, PDF 5 (printed iv)), still failing

### 18. WCAG Checks veraPDF Does Not Make

Each item is something to look at, not a proven failure.

- 1.3.2 the reading order jumps back up the same column on 1 page. Listen through them with a screen reader (or the PAC screen-reader preview): PDF 149 (printed 140) (6 jumps)
- 1.3.2 57 small sections are read more than 5 pages after their printed page, after a longer section that covers them (56 holding figures). Not a failure (long stories overlap in InDesign books), but a screen reader hears them far from where they are printed: PDF 4 (printed iii) read after PDF 60 (printed 51); PDF 87 (printed 78) read after PDF 139 (printed 130); PDF 88 (printed 79) read after PDF 139 (printed 130); PDF 89 (printed 80) read after PDF 139 (printed 130); PDF 90 (printed 81) read after PDF 139 (printed 130); PDF 92 (printed 83) read after PDF 139 (printed 130); PDF 100 (printed 91) read after PDF 139 (printed 130); PDF 101 (printed 92) read after PDF 139 (printed 130); PDF 107 (printed 98) read after PDF 139 (printed 130); PDF 109 (printed 100) read after PDF 139 (printed 130); PDF 110 (printed 101) read after PDF 139 (printed 130); PDF 112 (printed 103) read after PDF 139 (printed 130) and 45 more
- 1.3.2 1 section read away from its printed place, as in the original (this run did not move it). Listen through each where it is read, or move it with move_section:
  - PDF 1 (printed COVER): Article, read after PDF 329 (printed 320)

### 19. Deferred by the AI

- **Reading order of the pages whose notes and works-cited text was untagged (adopted as paragraphs)**: These pages (20, 54, 78, 95, 120, 138, 169, 200, 225, 248, 267, 288, 314) had their text marked but owned by no tag. adopt_orphans adds it in drawing order. Italic fragments and note numbers may be split into many short runs, so a person should check the order and the note numbering (veraPDF 7.1-3). [PDF 20 (printed 11), PDF 54 (printed 45), PDF 78 (printed 69), PDF 95 (printed 86), PDF 120 (printed 111), PDF 138 (printed 129), PDF 169 (printed 160), PDF 200 (printed 191), PDF 225 (printed 216), PDF 248 (printed 239), PDF 267 (printed 258), PDF 288 (printed 279), PDF 314 (printed 305)]
- **veraPDF 7.1-3: other content neither tagged nor marked as an artifact**: Examples sit on PDF 10 and 12 (part and chapter openers), probably decorative vector rules or ornaments with no digest entry. The digest lists no objects for them, so they cannot be targeted. A person should check these pages. [PDF 10 (printed 1), PDF 12 (printed 3)]
- **Index reading order (two-column index)**: The first lines of the index pages (e.g. PDF 323, 324, 326) show entries from adjacent columns interleaved, and 1543 Index elements sit at the tree root. The order cannot be verified from the digest. [PDF 322 (printed 313), PDF 323 (printed 314), PDF 324 (printed 315), PDF 325 (printed 316), PDF 326 (printed 317), PDF 327 (printed 318), PDF 328 (printed 319), PDF 329 (printed 320)]
- **Poor OCR text layer on some pages**: text_quality shows a producer OCR plug-in with a high suspect-token rate (16.4 per 1000). Worst pages are 152, 266, 315, 84, 290, 123, 136 and 4. Text was not changed. Hyphenation artifacts such as “confer ence” and “cli mate” are also present. [PDF 4 (printed iii), PDF 84 (printed 75), PDF 123 (printed 114), PDF 136 (printed 127), PDF 152 (printed 143), PDF 266 (printed 257), PDF 290 (printed 281), PDF 315 (printed 306)]
- **Caption for Figure 12.5 and captions of figures whose parent is the Article**: Figure 12.5 (obj 8828 0, PDF 278) has no caption sibling; its caption “Figure 12.5 Wheel of …” sits elsewhere on the page. Several figures on PDF 85 and 149 are Article children with caption fragments in separate Story elements. The captions step may not tie them, so a person should check. [PDF 85 (printed 76), PDF 149 (printed 140), PDF 152 (printed 143), PDF 278 (printed 269)]
- **Multi-panel figures on PDF 149 and 152 have panel letters in separate Story elements (a, b, c, d, e, f)**: The stray letters were left as tagged. A person could tie each to its panel or artifact them. [PDF 149 (printed 140), PDF 152 (printed 143)]

Reviewer note from the AI: Heading outline: H1 is the book title (title page, PDF 4). Part titles, chapter titles (chapter number, title and subtitle merged, with ActualText giving the full printed string) and front/back-matter titles (Contents, Acknowledgments, Glossary, Contributors, Index) are H2. Section headings and NOTES are H3. The Abbreviations and Secondary sub-heads are H4. The word-sheet crops for ocr_words (Hawai‘i, Shiina, Kaku’a, Kii, l’homme, xiii–xxi, Chiiki, L’Homme) all matched the OCR text, so no ocr_words were given. Han-only CJK runs (230, mostly the glossary and PDF 59, 138, 197–198) are left to the executor's automatic deferral to a human. Decorative wave ornaments (Ancre figures) and the landscape vignettes were artifacted. Existing good publisher alt text was kept; duplicate or junk alt text on multi-panel and chapter 8 and 9 figures was rewritten. The cover Article is moved to the start of the Document; this is a reading-order change I am fairly but not completely sure of.

### 20. Deferred by the Executor

- **230 Han-only CJK runs** need a Japanese / Chinese decision: fill in `han_review.csv`.
- caption (PDF 149 (printed 140)): 4 figures on page
- caption (PDF 149 (printed 140)): 4 figures on page
- caption (PDF 149 (printed 140)): 4 figures on page
- caption (PDF 149 (printed 140)): 4 figures on page
- caption (PDF 152 (printed 143)): 6 figures on page
- caption (PDF 152 (printed 143)): 6 figures on page
- caption (PDF 152 (printed 143)): 6 figures on page
- caption (PDF 152 (printed 143)): 6 figures on page
- caption (PDF 152 (printed 143)): 6 figures on page
- caption (PDF 152 (printed 143)): 6 figures on page
- caption (PDF 152 (printed 143)): 6 figures on page
- caption (PDF 232 (printed 223)): 2 figures on page
- caption (PDF 284 (printed 275)): 2 figures on page

### 21. Decisions Not Applied (2)

Rejected by validation or by the executor; nothing was half-applied.

- {"op": "move_section", "why": "1 candidate sections, host found: False"}
- {"where": "rolemap", "item": {"BMT_works_cited": "H3"}, "why": "unknown style"}

## What Was Changed

| Change | Count |
|---|---:|
| artifact: "decorative landscape on half-title page" | 1 |
| artifact: "decorative landscape vignette on title page" | 1 |
| artifact: "decorative landscape on Part I opener" | 1 |
| artifact: "wave ornament" | 7 |
| document: title | 1 |
| document: DisplayDocTitle | 1 |
| document: /Lang | 1 |
| orphans: adopted as paragraphs ("endnotes and works cited") | 21 |
| orphans: adopted as paragraphs ("endnotes") | 226 |
| heading: RoleMap level | 9 |
| heading: merged into next | 17 |
| heading: merged into prev | 6 |
| heading: ActualText | 17 |
| retype → H1 | 1 |
| retype → P | 1 |
| figure: alt text | 26 |
| figure: caption tied (figure moved out of its paragraph) | 70 |
| figure: caption paired by position (several figures on the page) | 8 |
| figure: caption retyped only | 13 |
| contents: TOC entries | 34 |
| contents: TOC built | 2 |
| notes: Note with /ID | 495 |
| links: /Contents set | 2309 |
| links: joined existing Link | 687 |
| links: placed after shared text | 1602 |
| links: wraps its text | 20 |
| links: new Link element created | 1 |
| links: URL-only description replaced by the sentence around it | 13 |
| order: figure moved to its page | 15 |
| contents: entry wrapped in Reference | 34 |
| structure: empty tag removed (proven empty) | 69 |
| artifact: untagged path with no content (rule, border, line) | 53 |
| role map: standard tag Caption was remapped to P; retyped | 83 |
| tag tree index: entries repaired | 1181 |
| tag tree index: entries pointing outside the tree cleared (ParentTree) | 1 |

## Accessibility Evaluation

A person evaluates this version of `sands_remediated.pdf` with PAC 2026 and a screen reader, on the app's "Accessibility Evaluation" page (or with manual_checks.py; docs/release.md). The "Ready to ship?" answer needs both parts. A Fail is recorded with its note and does not hold the book back. Each result is recorded against this version of the PDF (its sha256): after a new apply it no longer counts. The evaluation is a record of what a person found, not a legal certification.

**PAC 2026.** Open `sands_remediated.pdf` in PAC 2026 (https://pac.pdf-accessibility.org/en, Windows) and run its WCAG check. Anything it fails that is not listed above is a gap in the automated checks: note it in the issue tracker. Each item is Pass, Fail or Not Applicable, with notes:

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
