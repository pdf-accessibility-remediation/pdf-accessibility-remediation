# Remediation Review: fishers.pdf

Result: `fishers_remediated.pdf`

285 pages · run November 14, 2026, at 3:29 PM · model `anthropic/claude-sonnet-5.5` · prompt `workorder_v11.md` (3fd29e7f3ef071ec) · AI cost $0.230 ($0.0008 per page), from the original AI request on November 13, 2026 · this run: no new AI request · tokens: saved reply reused, not counted

Intake: none (already tagged)

Libraries: python 3.13.9 · pikepdf 10.5.1 · pdfplumber 0.11.9 · pypdfium2 5.7.1 · pillow 13.0.0 · fonttools 4.62.1

Time: intake 1.1s · audit 32.8s · reuse saved reply 1.4s · apply 96.4s · verify 45.4s · total 177.1s

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
**Needs a person:** 16 (8 deferred by the AI · 1 deferred by the executor · 7 CHECK rows)  
**AI decisions:** 117 in the work order, applied without review by a person  
**Fixed automatically (no AI):** links tied and described 4,277 · empty tags removed 163 · tag-tree index entries 61 · link descriptions that were only a URL 12 · Document root 1 · title shown in the window 1  
**veraPDF (WCAG 2.2 machine checks):** 3 WCAG rules failing before (104 checks) → 0 after (0 checks) · 0 newly failing

Automated checks are evidence, not sign-off.

| Top issues | Pages | Where |
|---|---|---|
| Empty tags removed when proven empty: 163 removed · 3 kept: something refers to them or they carry an attribute (listed) | see §10 | [§10](#10-empty-tags-163-removed-3-kept) |
| No empty tags: 3 empty tags (page: not on this tag) | see §10 | [§10](#10-empty-tags-163-removed-3-kept) |
| Every link tied to its text and described: 1 unresolved · 0 without description · 0 pointing to no annotation | see §9 | [§9](#9-links-whose-description-was-only-a-url-12-and-4-addresses-that-look-broken) |
| No link nested inside another: 11 | see §9 | [§9](#9-links-whose-description-was-only-a-url-12-and-4-addresses-that-look-broken) |
| Fonts: embedded and mapped to Unicode: 1 not embedded · 0 without ToUnicode | see §7 | [§7](#7-fonts) |
| … and 11 more | | §7, §14, §15, §16 |

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
| Empty tags removed when proven empty | **CHECK** | 163 removed · 3 kept: something refers to them or they carry an attribute (listed) |
| Tag-tree index points only into the tree | OK | 0 dangling entries · 3 stale entries (marked content no longer drawn) |
| No empty tables | OK | none |
| No empty tags | **CHECK** | 3 empty tags (page: not on this tag) |
| No paragraph holding only figures | OK | none |
| Every caption grouped with its figure | OK | all grouped |
| No link whose only text is a URL | OK | none |
| Tag tree consistent | OK | 0 missing · 0 mismatched |
| All marked text reachable from the tag tree | OK | 0 orphan runs |
| One Document root | OK | Document 1 |
| Every link tied to its text and described | **CHECK** | 1 unresolved · 0 without description · 0 pointing to no annotation |
| No link nested inside another | **CHECK** | 11 |
| Headings: no skipped levels | OK | H1 1 · H2 15 · H3 40 · H4 5 |
| Headings: exactly one H1 (the title) | OK | 1 H1 (several H1s usually mean parts or chapters were not demoted) |
| Figures: none with empty or placeholder alt | OK | 15 figures, 0 placeholder |
| Every Note has a unique ID | OK | 60 notes · 0 without ID · 0 duplicate · 0 not in the ID tree |
| Bookmarks present (documents over 9 pages) | OK | 16 bookmarks |
| Model reply held one work order | OK | one |
| Executor applied every decision | OK | 0 rejected · 0 failed (listed under "Decisions not applied") |
| Nothing deferred by the executor | **CHECK** | 1 deferred (listed under "Deferred by the executor") |
| Fonts: every glyph defined (no .notdef) | OK | none found |
| Fonts: every embedded font program could be read | OK | all read |
| Fonts: embedded and mapped to Unicode | **CHECK** | 1 not embedded · 0 without ToUnicode |
| Tab order follows the tag structure on pages with links or other annotations | OK | 0 of 67 pages with annotations lack /Tabs /S |
| Characters with no Unicode value (checklist 3.6) | OK | 0 read-aloud characters with no Unicode value |
| Private-use characters (checklist 3.6) | **CHECK** | 7 read-aloud characters with private-use codes (U+F068: 7) on 7 pages |
| Title and language set | OK | "Fishers, Monks and Cadres: Navigating State, Religion and the South China Sea in Central Vietnam" · en-GB |
| veraPDF WCAG 2.2 (machine): no WCAG failures | OK | before: 3 WCAG rules failed (104 checks) → after: 0 WCAG rules failed (0 checks) · 1 PDF/UA-only rules not counted (listed under "veraPDF") |
| veraPDF: no rule newly failing or failing more often | OK | 4 fixed · 1 still failing · 0 newly failing |
| Alt text: none like a file name or repeated on many figures (1.1.1) | OK | 0 of 15 figures flagged |
| Tables: every table has header cells (1.3.1) | OK | none without |
| Reading order: no page jumps back up a column (1.3.2) | **CHECK** | 1 of 279 pages flagged |
| Reading order: no section moved away from its printed place by this run (1.3.2) | OK | 0 new · 0 already in the original, of 6 sections and blocks |
| Title is not a file name or placeholder (2.4.2) | OK | "Fishers, Monks and Cadres: Navigating State, Religion and the South China Sea in Central Vietnam" |
| Link text: none like "click here" (2.4.4) | OK | 0 generic |
| Headings: none empty, very long or repeated in a row (2.4.6) | OK | 0 empty · 0 long · 0 repeated |

## For a Person to Check

### 1. Alt Text Written or Changed by the AI (15)

| Page | Before | After |
|---|---|---|
| PDF 1 (printed COVER) | Couverture | Book cover: colour photograph of a blue fishing boat dressed with flags, balloons, a portrait and a red banner, moving along a river in central Vietnam with a green hill behind. The title 'Fishers, Monks and Cadres: Navigating State, Religion and the South China Sea in Central Vietnam' is printed at the top and the author's name, Edyta Roszko, at the bottom. |
| PDF 5 (printed iv) | Illustrations | Creative Commons logo: CC BY-NC-ND (Attribution, NonCommercial, NoDerivatives). |
| PDF 20 (printed xix) | Map of the field sites of Sa Huỳnh and Lý Sơn. | Map 1: the field sites of Sa Huỳnh and Lý Sơn. Map of the Vietnamese coast and the South China Sea. Sa Huỳnh (Phổ Thạnh commune) is on the central coast and Lý Sơn Island lies just offshore. The Paracel Islands lie further east, Hainan and China to the north, and Laos, Thailand and Cambodia to the west. Hanoi and Phnom Penh are marked. |
| PDF 21 (printed xx) | Map of the religious sites in Sa Huỳnh in Quảng Ngãi Province in Central Vietnam.\x00 | Map 2: religious sites in Sa Huỳnh (Phổ Thạnh commune), Quảng Ngãi Province, Central Vietnam. Map of a coastal strip between hills and the South China Sea, crossed by a railway and a road. Villages are shaded by main income source (salt-making, fishing, agriculture, forestry and agriculture). Twelve numbered sacred places and temples are marked, including Thanh Minh temple, the Quan Âm statue, Whale Spirit temples, Thủy Long palace, Thiên Ya Na temple and Từ Phước pagoda. |
| PDF 22 (printed xxi) | Map of the religious sites in An Hải Commune on Lý Sơn Island.\x00 | Map 3: religious sites in An Hải Commune, Lý Sơn Island. Non-scaled sketch map. A volcanic mountain with a crater sits in the centre, surrounded by fields and forest. The built-up East Village and West Village lie along the south coast, and An Vĩnh Commune is to the west. Seventeen numbered sacred places are marked, including temples, a pagoda, shrines, a cemetery and a palace. |
| PDF 23 (printed xxii) | Map of the religious sites in An Vĩnh Commune on Lý Sơn Island.\x00 | Map 4: religious sites in An Vĩnh Commune, Lý Sơn Island. Non-scaled sketch map. Pasture and fields fill the interior, and West Village and East Village run along the western and southern coast with a harbour at the west. An Hải Commune is to the east. Twenty-three numbered sacred places are marked, including pagodas, temples, shrines, tombs and the village founders' shrine. |
| PDF 25 (printed xxiv) | Photo of a wooden statue recovered by fishermen from the South China Sea.  | Black-and-white photograph: a small wooden statue of a seated figure, sheltered by an umbrella and fenced in with chain-link among potted plants. Two men crouch in front of it. This is the statue recovered by fishermen from the South China Sea. |
| PDF 53 (printed 28) | View of Sa Huỳnh in Central Vietnam.\x00 | Black-and-white photograph: view from a hillside over Sa Huỳnh, with rice fields on the left, houses along a sandy beach and a wooded headland reaching into the sea. |
| PDF 79 (printed 54) | Photo of an altar in the yard of a house for the Earth Spirit in Sa Huỳnh.\x00 | Black-and-white photograph: an altar for the Earth Spirit in a yard in Sa Huỳnh. A concrete pillar topped with an old television casing holds an incense pot and offerings, with palms and a fence behind. |
| PDF 105 (printed 80) | Photo of a procession in honour of the village’s founders in An Hải Village in Lý Sơn.\x00 | Black-and-white photograph: men in dark traditional robes and headdresses carry a canopied ceremonial shrine in a procession in front of a tile-roofed temple in An Hải Village, Lý Sơn. Onlookers stand behind. |
| PDF 131 (printed 106) | Photo of the head of the fishing community worshipping Quan Âm in Sa Huỳnh.\x00 | Black-and-white photograph: a white statue of the bodhisattva Quan Âm stands on a stepped stone base beside the water in Sa Huỳnh, framed by trees and a stone balustrade. |
| PDF 151 (printed 126) | Photo of the Paracel Memorial erected by Quảng Ngãi Province on Lý Sơn Island.\x00 | Black-and-white photograph: the Paracel (Hoàng Sa) Memorial on Lý Sơn Island. A tall stone slab with sculpted figures of three men stands on a stone base in a paved courtyard, with a tile-roofed building behind. |
| PDF 154 (printed 129) | Imaginary map of Vietnam’s land and the sea with Lý Sơn in the middle.\x00 | Imaginary map of Vietnam's land and the sea, in a circle. Vietnam's long, S-shaped landmass fills the left side. Lý Sơn Island is marked with a star on the central coast, in the middle of the picture. The Paracel Islands lie to the east and the Spratly Islands to the south-east, with open sea between them and the mainland. |
| PDF 185 (printed 160) | Photo of women on the way to Thiên Y A Na temple in Sa Huỳnh.\x00 | Black-and-white photograph: four women walk towards the camera across a sandy beach in Sa Huỳnh, with boats and a harbour behind them. One carries a pair of sandals and another a bunch of flowers, on their way to the Thiên Y A Na temple. |
| PDF 221 (printed 196) | Photo of monks, cadres and fishers during the ‘Celebration for the Peace of the Paracels and Spratlys’ in Lý Sơn Island.\x00 | Black-and-white photograph: Buddhist monks in robes and local officials gather around an altar with offerings during the 'Celebration for the Peace of the Paracels and Spratlys' on Lý Sơn Island. A man in a white shirt holds out a paper, and a microphone is held at the right. |

### 2. Figures That Kept Their Existing Alt Text (23)

Not changed by the AI. Check they are adequate.

| Page | Alt text |
|---|---|
| PDF 4 (printed iii) | Illustrations |
| PDF 8 (printed vii) | Illustrations |
| PDF 8 (printed vii) | Illustrations |
| PDF 8 (printed vii) | Illustrations |
| PDF 8 (printed vii) | Illustrations |
| PDF 8 (printed vii) | Illustrations |
| PDF 8 (printed vii) | Illustrations |
| PDF 8 (printed vii) | Illustrations |
| PDF 8 (printed vii) | Illustrations |
| PDF 10 (printed ix) | — |
| PDF 16 (printed xv) | — |
| PDF 26 (printed 1) | I |
| PDF 54 (printed 29) | S |
| PDF 54 (printed 29) | Illustrations |
| PDF 54 (printed 29) | Illustrations |
| PDF 80 (printed 55) | — |
| PDF 86 (printed 61) | Illustrations |
| PDF 86 (printed 61) | Illustrations |
| PDF 106 (printed 81) | — |
| PDF 132 (printed 107) | — |
| PDF 152 (printed 127) | — |
| PDF 186 (printed 161) | — |
| PDF 222 (printed 197) | T |

### 3. Headings

Heading levels by style (as applied):

| Style | Level | How | Elements |
|---|---|---|---:|
| Artifact | Span | RoleMap (added: the style had no mapping) | 1 |

### 4. Elements Retyped by the AI (84)

Check each one is (or is not) a heading as decided.

| Page | Text | Before | After |
|---|---|---|---|
| PDF 4 (printed iii) | Navigating State, Religion and the South China Sea in Central Vietnam | H1 | P |
| PDF 8 (printed vii) | Contents | P | H2 |
| PDF 10 (printed ix) | Acknowledgements | P | H2 |
| PDF 16 (printed xv) | Note on Transliteration and Translation | P | H2 |
| PDF 18 (printed xvii) | Glossary | P | H2 |
| PDF 18 (printed xvii) | ADMINISTRATIVE TERMS | P | H3 |
| PDF 18 (printed xvii) | TERRITORIAL DENOMINATIONS | P | H3 |
| PDF 20 (printed xix) | Maps | P | H2 |
| PDF 26 (printed 1) | A Triad of Confrontation | P | H2 |
| PDF 31 (printed 6) | Beyond the coastal fringe of central Vietnam | P | H3 |
| PDF 36 (printed 11) | Charting the contours of religion in Vietnam | P | H3 |
| PDF 40 (printed 15) | Navigating a triad of contested categories: state–religion–village | P | H3 |
| PDF 45 (printed 20) | Multi-sited research and methodology | P | H3 |
| PDF 48 (printed 23) | Structure of the book | P | H3 |
| PDF 54 (printed 29) | The Coastal Society: Historical and Vernacular Geographies | P | H2 |
| PDF 56 (printed 31) | Cham and Viê.t legacies | P | H3 |
| PDF 60 (printed 35) | Local mobilities vis-a-vis highlands–lowlands–islands | P | H3 |
| PDF 63 (printed 38) | Post-revolutionary realities and economic liberalization | P | H3 |
| PDF 68 (printed 43) | Shifting administrative boundaries | P | H3 |
| PDF 69 (printed 44) | Sa Huynh – the coast | P | H4 |
| PDF 73 (printed 48) | Lý Sơn – the island | P | H4 |
| PDF 80 (printed 55) | Doing and Making Religion in Vietnam | P | H2 |
| PDF 81 (printed 56) | Institutionalized religion versus beliefs | P | H3 |
| PDF 85 (printed 60) | High modernism versus religion | P | H3 |
| PDF 89 (printed 64) | Religious versus secular | P | H3 |
| PDF 97 (printed 72) | Science, beliefs, and religious superstition | P | H3 |
| PDF 106 (printed 81) | Between Land and Sea: Spatial and Social Boundaries among Fishers and Farmers | P | H2 |
| PDF 111 (printed 86) | The land–sea dichotomy | P | H3 |
| PDF 111 (printed 86) | Inland versus coast | P | H4 |
| PDF 113 (printed 88) | Island versus mainland | P | H4 |
| PDF 115 (printed 90) | Fisher as a relational category | P | H4 |
| PDF 116 (printed 91) | Va.n as ‘guild’ and ‘territorial unit’ | P | H3 |
| PDF 122 (printed 97) | Lang system | P | H3 |
| PDF 126 (printed 101) | Growing status of the va.n | P | H3 |
| PDF 132 (printed 107) | Discipline, Purification, | P | H2 |
| PDF 134 (printed 109) | Forbidden Hill and Gia’s defence of the Quan Âm statue | P | H3 |
| PDF 140 (printed 115) | Buddhist purifying discipline | P | H3 |
| PDF 149 (printed 124) | Shifting binary oppositions | P | H3 |
| PDF 152 (printed 127) | Making the Paracels and Spratlys Vietnamese through Commemoration | P | H2 |
| PDF 155 (printed 130) | Islanders as guardians of the Paracels and Spratlys | P | H3 |
| PDF 159 (printed 134) | Commemoration and ancestor worship | P | H3 |
| PDF 162 (printed 137) | Local contestations – The competition between lineages | P | H3 |
| PDF 166 (printed 141) | Provincial authorities and their incentives | P | H3 |
| PDF 175 (printed 150) | Local contestations of the Pha. m’s female ancestor | P | H3 |
| PDF 186 (printed 161) | Women and New Gendered Ritual Divisions | P | H2 |
| PDF 191 (printed 166) | Pre-revolutionary gender divisions in ritual life | P | H3 |
| PDF 195 (printed 170) | Women and religious practices in the coastal society | P | H3 |
| PDF 201 (printed 176) | Women’s interpretation of the spirit world | P | H3 |
| PDF 204 (printed 179) | Negotiating female identity and the quest for divine protection | P | H3 |
| PDF 210 (printed 185) | Quest for authority as a gendered process | P | H3 |
| PDF 215 (printed 190) | Transforming crisis into accomplishment | P | H3 |
| PDF 220 (printed 195) | Conclusion | P | H3 |
| PDF 222 (printed 197) | Shifting Confrontations in the State–Religion–Society Triadic Relationship | P | H2 |
| PDF 225 (printed 200) | Beyond the religious–secular binary | P | H3 |
| PDF 228 (printed 203) | Blurring the boundaries between religion and politics | P | H3 |
| PDF 231 (printed 206) | Navigating authoritative state and religious semiotic ideologies | P | H3 |
| PDF 240 (printed 215) | Bibliography | P | H2 |
| PDF 240 (printed 215) | Official documents | P | H3 |
| PDF 242 (printed 217) | Unpublished Manuscripts | P | H3 |
| PDF 242 (printed 217) | Published sources cited in Vietnamese | P | H3 |
| PDF 266 (printed 241) | Index | P | H2 |
| page: not on this tag | (no text) | (no style) | P |
| page: not on this tag | (no text) | (no style) | Span |
| page: not on this tag | (no text) | (no style) | Span |
| page: not on this tag | (no text) | (no style) | Span |
| page: not on this tag | (no text) | (no style) | Span |
| page: not on this tag | (no text) | (no style) | Span |
| page: not on this tag | (no text) | (no style) | Span |
| page: not on this tag | (no text) | (no style) | Span |
| page: not on this tag | (no text) | (no style) | Span |
| page: not on this tag | (no text) | (no style) | Span |
| page: not on this tag | (no text) | (no style) | Span |
| page: not on this tag | (no text) | (no style) | Span |
| page: not on this tag | (no text) | (no style) | Span |
| page: not on this tag | (no text) | (no style) | Span |
| page: not on this tag | (no text) | (no style) | Span |
| page: not on this tag | (no text) | (no style) | Span |
| page: not on this tag | (no text) | (no style) | Span |
| page: not on this tag | (no text) | (no style) | Span |
| page: not on this tag | (no text) | (no style) | Span |
| page: not on this tag | (no text) | (no style) | Span |
| page: not on this tag | (no text) | (no style) | Span |
| page: not on this tag | (no text) | (no style) | Span |
| page: not on this tag | (no text) | (no style) | Span |

### 5. Text a Screen Reader Could Not Reach (before this run)

10 pages had text outside the tag tree: 55 orphan runs (marked, but no tag owns them) and 0 untagged runs. Running heads and page numbers among them can be hidden as decoration; real content must be added to the tag tree by a person. After this run: 0 untagged characters, 0 orphan runs remain.

Pages: PDF 8 (printed vii), PDF 18–19 (printed xvii–xviii), PDF 54 (printed 29), PDF 86 (printed 61), PDF 94 (printed 69), PDF 112 (printed 87), PDF 178 (printed 153), PDF 198 (printed 173), PDF 209 (printed 184)

### 6. Reading Order Changes

Listen through these spots with a screen reader.

- Cover figure moved to the start of the document

### 7. Fonts

The pipeline changes no other font: it never embeds one, replaces a visible one, or rewrites text. These need a person:

- **Not embedded** (1): Times-Roman. PDF/UA requires embedded fonts (7.21.4.1); a person must embed them with a PDF tool (e.g. Acrobat Preflight) and check that no page changes.

### 8. Orphan Content Added to the Tag Tree (28 paragraphs)

Real content that was marked but in no tag, now read in page order after the last tagged block on its page. Listen through these pages:

- PDF 8 (printed vii) ("contents label"): 1 runs → 1 paragraphs, starting "1."
- PDF 18 (printed xvii) ("glossary entries"): 30 runs → 16 paragraphs, starting "và Du Lịch"
- PDF 19 (printed xviii) ("glossary entries"): 8 runs → 3 paragraphs, starting "Giáo Hội Phật Giáo Việt"
- PDF 54 (printed 29) ("chapter 1 notes"): 2 runs → 1 paragraphs, starting "In 1909, the French scholar M. Vinet identified jar burials, pottery, and other objects with…"
- PDF 86 (printed 61) ("chapter 2 notes"): 4 runs → 1 paragraphs, starting "Scott speaks of any state, not just authoritarian or socialist ones, and his argument thus remains…"
- PDF 94 (printed 69) ("chapter 2 notes"): 2 runs → 1 paragraphs, starting "According to the Ministry of Culture, by 1996 a total of 1,860 ‘historical and cultural monuments’…"
- PDF 112 (printed 87) ("chapter 3 notes"): 2 runs → 1 paragraphs, starting "In many cases, villages founded by northern migrants in central Vietnam were named after their…"
- PDF 178 (printed 153) ("chapter 5 notes"): 2 runs → 1 paragraphs, starting "According to Murray (1987), piracy emerged in the South China Sea only in the late eighteenth…"
- PDF 198 (printed 173) ("chapter 6 notes"): 2 runs → 1 paragraphs, starting "For comparative cases, see Wolf (1975), Ahern (1975), Kendall (1985), Yü (2001), and Lhamo (2003)."
- PDF 209 (printed 184) ("chapter 6 notes"): 2 runs → 2 paragraphs, starting "For a good discussion of lộc, see Soucy (2012)."

### 9. Links Whose Description Was Only a URL (12, and 4 addresses that look broken)

The description (what a screen reader announces) was set to the book's own sentence around the link, with the URL removed. No words were added and the visible URL is unchanged. Replace any of these with a better description if needed.

| Page | URL | Description now |
|---|---|---|
| PDF 5 (printed iv) | https://creativecommons.org/licenses/by-nc-nd/4.0 | For details, see /. |
| PDF 31 (printed 6) | https://en.vietnamplus.vn/ly-son-island-harmed-by-unplanned-building/100317.vnp | See ‘Ly Son Island harmed by unplanned building’, available at, accessed 27 April 2020. |
| PDF 37 (printed 12) | https://www.bbc.com/news/world-asia-17343596 | See ‘Vietnam to send Buddhist monks to Spratly Islands’, available at, accessed 29 April 2020. |
| PDF 37 (printed 12) | https://www.theguardian.com/world/2014/may/23/vietnamese-woman-dies-self-immolation-protest-china | See ‘Vietnamese woman dies in self-immolation protest against China’, available at, accessed 29 April 2020. |
| PDF 40 (printed 15) | https://www.marinelink.com/articles/maritime/navigation-100154 | See ‘Navigation’, accessed 30 April 2020. |
| PDF 102 (printed 77) | http://www.thuvienphapluat.vn/archive/Phap-lenh/Ordinance-No-21-2004-PL-UBTVQH11-of-June-29-2004-on-beliefs-and-religions-vb76132t14.aspx | See also Ordinance of the Standing Committee of the National Assembly No.21/2004/Pl-UBTVQH11 of June 2004 Regarding Religious Beliefs and Religious Organizations (available at, last accessed 4 June 2018). |
| PDF 152 (printed 127) | http://vovworld.vn/en-US/current-affairs/china-has-no-reason-when-citing-the-1958-diplomatic-note-250365 | See ‘China has no reason when citing the 1958 Diplomatic Note’, accessed 12 September 2018. |
| PDF 152 (printed 127) | http://www.bbc.co.uk/vietnamese/vietnam/story/2008/09/080917_luuvanloi_inv.shtml | For a defence of Ph m Văn Đồng by Lưu Văn Lợi, a retired Vietnamese diplomat, see, accessed 22 February 2018. |
| PDF 158 (printed 133) | https://en.vietnam.com/news/article/ly-son-island-of-history-and-economy.html | See, accessed 12 September 2018. |
| PDF 167 (printed 142) | http://www.iseas.edu.sg/viewpoint/mr22mar10.pdf | China claims over 80 per cent of the South China Sea; see for example Michael Richardson, ‘Territorial Claims in South China: LNG deal with KL shows Beijing may be easing off ’, Strait Times, 22 March 2010, ac-cessed 26 August 2010. |
| PDF 244 (printed 219) | http://www.archives.gov.vn/cong_bo_gioi_thien_tl/mlnews.2006=9-18.75735954401 | Nguyễn Thị Kim Bình. ‘Đời sống làng xã tỉnh Quảng Ngãi qua các bản hương ước’ [Village Life of Quảng Ngãi Province through the ‘Convention’], access on 18 September 2006. |
| PDF 256 (printed 231) | https://doi.org/10.1017/trn.2016.3 | TRaNS: Trans-Regional and -National Studies of Southeast Asia, Available on CJO DOI |

Link addresses that look broken (listed, not changed):

- PDF 100 (printed 75): `http:1987).10`: the address ends with punctuation or an unmatched closing bracket from the printed text; probably broken
- PDF 103 (printed 78): `http:minh).13`: the address ends with punctuation or an unmatched closing bracket from the printed text; probably broken
- PDF 214 (printed 189): `http:Trˆˆi).13`: the address ends with punctuation or an unmatched closing bracket from the printed text; probably broken
- PDF 244 (printed 219): `http:Vietnam].Hà`: the address ends with punctuation or an unmatched closing bracket from the printed text; probably broken

### 10. Empty Tags (163 removed, 3 kept)

A tag is removed only when proven empty: nothing under it holds content, it carries no Alt, ActualText, E or ID, and nothing in the file refers to it except its parent. Table cells are never removed one by one; a table goes only when every part is empty.

- Removed: 62 Link, 54 TOCI, 18 TOCI_Page, 16 P, 4 Sect, 3 Index, 2 TOC, 2 Div, 2 Part
- Empty Link (page: not on this tag), Link (page: not on this tag), Link (page: not on this tag), Link (page: not on this tag), Link (page: not on this tag), Link (page: not on this tag), Link (page: not on this tag), Link (page: not on this tag), Link (page: not on this tag), Link (page: not on this tag), Link (page: not on this tag), Link (page: not on this tag), Link (page: not on this tag), Link (page: not on this tag), Link (page: not on this tag), Link (page: not on this tag), Link (page: not on this tag), Link (page: not on this tag), Link (page: not on this tag), Link (page: not on this tag), Link (page: not on this tag), Link (page: not on this tag), Link (page: not on this tag), Link (page: not on this tag), Link (page: not on this tag), Link (page: not on this tag), Link (page: not on this tag), Link (page: not on this tag), Link (page: not on this tag), Link (page: not on this tag), Link (page: not on this tag), Link (page: not on this tag), Link (page: not on this tag), Link (page: not on this tag), Link (page: not on this tag), Link (page: not on this tag), Link (page: not on this tag), Link (page: not on this tag), Link (page: not on this tag), Link (page: not on this tag), Link (page: not on this tag), Link (page: not on this tag), Link (page: not on this tag), Link (page: not on this tag), Link (page: not on this tag), Link (page: not on this tag), Link (page: not on this tag), Link (page: not on this tag), Link (page: not on this tag), Link (page: not on this tag), Link (page: not on this tag), Link (page: not on this tag), Link (page: not on this tag), Link (page: not on this tag), Link (page: not on this tag), Link (page: not on this tag), Link (page: not on this tag), Link (page: not on this tag), Link (page: not on this tag), Link (page: not on this tag), Link (page: not on this tag), Link (page: not on this tag), TOCI (page: not on this tag), TOCI (page: not on this tag), TOCI (page: not on this tag), TOCI (page: not on this tag), TOCI (page: not on this tag), TOCI (page: not on this tag), TOCI (page: not on this tag), TOCI (page: not on this tag), TOCI (page: not on this tag), TOCI (page: not on this tag), TOCI (page: not on this tag), TOCI (page: not on this tag), TOCI (page: not on this tag), TOCI (page: not on this tag), TOCI (page: not on this tag), TOCI (page: not on this tag), TOCI (page: not on this tag), TOCI_Page (page: not on this tag), TOCI (page: not on this tag), TOCI (page: not on this tag), TOCI_Page (page: not on this tag), TOCI_Page (page: not on this tag), TOCI_Page (page: not on this tag), TOCI_Page (page: not on this tag), TOCI_Page (page: not on this tag), TOCI_Page (page: not on this tag), TOCI_Page (page: not on this tag), TOCI_Page (page: not on this tag), TOCI (page: not on this tag), TOCI (page: not on this tag), TOCI (page: not on this tag), TOCI (page: not on this tag), TOCI (page: not on this tag), TOCI (page: not on this tag), TOCI (page: not on this tag), TOCI (page: not on this tag), TOCI (page: not on this tag), TOCI (page: not on this tag), TOCI (page: not on this tag), TOCI (page: not on this tag), TOCI (page: not on this tag), TOCI (page: not on this tag), TOCI (page: not on this tag), TOCI_Page (page: not on this tag), TOCI (page: not on this tag), TOCI (page: not on this tag), TOCI_Page (page: not on this tag), TOCI_Page (page: not on this tag), TOCI_Page (page: not on this tag), TOCI_Page (page: not on this tag), TOCI_Page (page: not on this tag), TOCI_Page (page: not on this tag), TOCI_Page (page: not on this tag), TOCI_Page (page: not on this tag), TOCI (page: not on this tag), TOCI (page: not on this tag), TOCI (page: not on this tag), TOCI (page: not on this tag), TOCI (page: not on this tag), TOCI (page: not on this tag), TOCI (page: not on this tag), TOCI (page: not on this tag), TOCI (page: not on this tag), TOCI (page: not on this tag), TOCI (page: not on this tag), TOCI (page: not on this tag), TOCI (page: not on this tag), TOCI (page: not on this tag), TOCI (page: not on this tag), TOCI (page: not on this tag), TOCI (page: not on this tag), TOCI (page: not on this tag) removed (no content under them)
- **Kept, empty: P (page: not on this tag)**, because ParentTree key 8836 (stale: no annotation uses this key).
- **Kept, empty: P (page: not on this tag)**, because ParentTree key 8837 (stale: no annotation uses this key).
- **Kept, empty: P (page: not on this tag)**, because ParentTree key 8838 (stale: no annotation uses this key).

### 11. Tag-tree Index Entries Cleared (7)

Entries that pointed at a tag no longer in the tag tree (left by the source file, or by a tag the run removed). Nothing reads such a tag; no page, text or reachable tag changed.

- ParentTree, PDF 8 (printed vii): MCID 21 (TOCI_Page), MCID 23 (TOCI_Title), MCID 24 (TOCI_Page), MCID 26 (TOCI_Title), MCID 27 (TOCI_Page), MCID 29 (TOCI_Title), MCID 30 (TOCI_Page)

### 12. Structure Left for a Person

- 3 empty tags: P (page: not on this tag), P (page: not on this tag), P (page: not on this tag)

### 13. veraPDF (WCAG 2.2 machine profile), Before and After

veraPDF 1.30.3, profile "WCAG 2.2 machine validation profile" (7da399cf5baa). Counts are failed checks; pages are from the first checks veraPDF lists for each rule, so a rule may fail on more pages. Rules that only PDF/UA requires are listed apart and do not count. "Who fixes" is who can act on the rule: the pipeline by itself, the AI through the work order, or only a person. **Newly failing** means this run broke something the original passed. Before: 3 rules failing (the AI can act on 2, the pipeline on 1, only a person on 0). After: 0.

| Rule | WCAG | What it checks | Who fixes | Before | After | Status | Pages (after, else before) |
|---|---|---|---|---:|---:|---|---|
| ISO 14289-1 7.1-3 | 1.3.1 | Content shall be marked as Artifact or tagged as real content | the AI (`artifacts`) | 100 | 0 | fixed | PDF 8 (printed vii), PDF 18 (printed xvii) |
| ISO 14289-1 7.18.5-1 | 2.4.4, 4.1.2 | Links shall be tagged according to ISO 32000-1:2008, 14.8.4.4.2, Link Element | the pipeline | 3 | 0 | fixed | PDF 21 (printed xx), PDF 284 (printed 259) |
| ISO 14289-1 7.1-5 | 1.3.1, 4.1.2 | All non-standard structure types shall be mapped to the nearest functionally equivalent standard type, as defined in ISO 32000-1:2008, 14.8.4, in the role map dictionary of the structure tree root. This mapping may be indirect; within the role map a non-standard type can map directly to another non-standard type, but eventually the mapping shall terminate at a standard type | the AI (`rolemap`) | 1 | 0 | fixed | PDF 4 (printed iii) |

PDF/UA-only, not required for WCAG (not counted):

- 7.21.4.1-1: font program embedding (text stays readable through its Unicode mapping) (1 checks, PDF 4 (printed iii)), still failing
- fixed by this run: 7.9-1

### 14. WCAG Checks veraPDF Does Not Make

Each item is something to look at, not a proven failure.

- 1.3.2 the reading order jumps back up the same column on 1 page. Listen through them with a screen reader (or the PAC screen-reader preview): PDF 8 (printed vii) (2 jumps)

### 15. Deferred by the AI

- **Empty L elements (no LI children) holding footnote labels and notes**: The lists on PDF 54 (printed 29), 86 (printed 61), 94 (printed 69), 112 (printed 87), 178 (printed 153), 198 (printed 173) and 209 (printed 184) have no list items. They are footnotes and need a person to check their structure. The two real footnote lists (PDF 37 and 144) are kept. [PDF 54 (printed 29), PDF 86 (printed 61), PDF 94 (printed 69), PDF 112 (printed 87), PDF 178 (printed 153), PDF 198 (printed 173), PDF 209 (printed 184)]
- **Headings 'List of Illustrations', 'Maps', 'Figures' on PDF 9 (printed viii), and 'TERMS FOR ORGANIZATIONS' on PDF 19 (printed xviii)**: They are not clearly identifiable as body-tagged candidates. 'Maps' and 'Figures' (11 pt bold) would need a parent H2 that is not safely identifiable, so no heading level was assigned. [PDF 9 (printed viii), PDF 19 (printed xviii)]
- **Chapter 4 title is split over four P lines (11762 0 to 11765 0)**: Only the first line was made H2. A person should merge the four lines into one heading. The other three lines (11763 0, 11764 0, 11765 0) remain P. [PDF 132 (printed 107)]
- **'INTRODUCTION' (PDF 26) and 'CONCLUSION' (PDF 222) labels and 'CHAPTER n' labels on chapter openers**: These sit as separate P lines before the H2 titles. A person should decide whether to fold them into the headings. [PDF 26 (printed 1), PDF 54 (printed 29), PDF 80 (printed 55), PDF 106 (printed 81), PDF 132 (printed 107), PDF 152 (printed 127), PDF 186 (printed 161), PDF 222 (printed 197)]
- **Drop capitals retyped from Figure to Span**: Their letter is part of the first word, but the executor cannot verify that the glyph is text. Check the reading of the first word on each chapter opening. [PDF 10 (printed ix), PDF 16 (printed xv), PDF 26 (printed 1), PDF 54 (printed 29), PDF 80 (printed 55), PDF 106 (printed 81), PDF 132 (printed 107), PDF 152 (printed 127), PDF 186 (printed 161), PDF 222 (printed 197)]
- **veraPDF 7.1-3 (content neither tagged nor artifact)**: Orphan runs on the glossary, contents and notes pages are adopted into the tree. The adopted text sits after the last tagged block on each page, so a person must check the reading order on those pages. Any remaining unmarked content should be re-run after this order is applied. [PDF 8 (printed vii), PDF 18 (printed xvii), PDF 19 (printed xviii), PDF 54 (printed 29), PDF 86 (printed 61), PDF 94 (printed 69), PDF 112 (printed 87), PDF 178 (printed 153), PDF 198 (printed 173), PDF 209 (printed 184)]
- **Text-layer quality**: Vietnamese diacritic letters are missing or wrong in places (e.g. 'Ph m', 'Th nh', 'Viê.t', 'Hương ưóc'), with 36 suspect tokens per 1000. The text was not changed. The worst pages are listed. [PDF 18 (printed xvii), PDF 151 (printed 126), PDF 185 (printed 160), PDF 240 (printed 215), PDF 241 (printed 216), PDF 242 (printed 217), PDF 243 (printed 218), PDF 244 (printed 219)]
- **Figure captions**: Captions are plain P elements directly after each figure. The executor groups captions with figures by itself. A person should confirm they are paired. [PDF 20 (printed xix), PDF 21 (printed xx), PDF 22 (printed xxi), PDF 23 (printed xxii), PDF 25 (printed xxiv), PDF 53 (printed 28), PDF 79 (printed 54), PDF 105 (printed 80), PDF 131 (printed 106), PDF 151 (printed 126), PDF 154 (printed 129), PDF 185 (printed 160), PDF 221 (printed 196)]

Reviewer note from the AI: The title page had two H1s; the book title stays H1 and the subtitle became P. Chapter titles, front/back-matter titles and the Introduction/Conclusion titles are H2, 14 pt bold section heads are H3 and 11 pt bold sub-heads are H4. Language was fr-FR; it is now en-GB (British spelling). The 'Figure' tag on 22 elements was a misuse: they hold contents-page text, note text, the title-page publisher line or drop capitals, so they were retyped (Span or P). The 16 real images got new alt text, which replaces alt text containing stray NUL characters. The existing TOC/TOCI tags were kept, so no toc key is given. The reading order of the large nested Part/Sect/Div containers looks to be in page order, so no move_section was made.

### 16. Deferred by the Executor

- link on a page with no tagged text (PDF 21 (printed xx)): tied to tagged text on PDF 20 (printed xix)

## What Was Changed

| Change | Count |
|---|---:|
| document: Document root created | 1 |
| document: title | 1 |
| document: DisplayDocTitle | 1 |
| document: /Lang | 1 |
| orphans: adopted as paragraphs ("contents label") | 1 |
| orphans: adopted as paragraphs ("glossary entries") | 19 |
| orphans: adopted as paragraphs ("chapter 1 notes") | 1 |
| orphans: adopted as paragraphs ("chapter 2 notes") | 2 |
| orphans: adopted as paragraphs ("chapter 3 notes") | 1 |
| orphans: adopted as paragraphs ("chapter 5 notes") | 1 |
| orphans: adopted as paragraphs ("chapter 6 notes") | 3 |
| role map: style with no mapping mapped | 1 |
| retype → P | 2 |
| retype → H2 | 15 |
| retype → H3 | 40 |
| retype → H4 | 5 |
| retype → Span | 22 |
| figure: alt text | 15 |
| links: /Contents set | 4277 |
| links: joined existing Link | 4273 |
| links: new Link element created | 3 |
| links: placed after shared text | 1 |
| links: wraps its text | 1 |
| links: placed beside nearest text | 1 |
| links: already tied to a Link inside the document | 1 |
| links: references to off-page annotations removed | 3 |
| links: URL-only description replaced by the sentence around it | 12 |
| notes: unique /ID added | 60 |
| structure: empty tag removed (proven empty) | 163 |
| tag tree index: entries repaired | 54 |
| tag tree index: entries pointing outside the tree cleared (ParentTree) | 7 |

## Accessibility Evaluation

A person evaluates this version of `fishers_remediated.pdf` with PAC 2026 and a screen reader, on the app's "Accessibility Evaluation" page (or with manual_checks.py; docs/release.md). The "Ready to ship?" answer needs both parts. A Fail is recorded with its note and does not hold the book back. Each result is recorded against this version of the PDF (its sha256): after a new apply it no longer counts. The evaluation is a record of what a person found, not a legal certification.

**PAC 2026.** Open `fishers_remediated.pdf` in PAC 2026 (https://pac.pdf-accessibility.org/en, Windows) and run its WCAG check. Anything it fails that is not listed above is a gap in the automated checks: note it in the issue tracker. Each item is Pass, Fail or Not Applicable, with notes:

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
