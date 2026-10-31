# Remediation review: buddhist.pdf

Result: `buddhist_remediated.pdf`

213 pages · run 2026-10-25T19:12:30 · model `anthropic/claude-sonnet-5.5` · prompt `workorder_v8.md` (4555d20a2fa08a40) · cost $0 (saved reply reused, no new call) · tokens: saved reply reused, not counted

Intake: none (already tagged)

Libraries: python 3.13.5 · pikepdf 10.5.1 · pdfplumber 0.11.9 · pypdfium2 5.7.1 · pillow 13.0.0 · fonttools 4.62.1

Time: intake 0.2s · audit 45.8s · reuse saved reply 0.8s · apply 31.8s · verify 62.0s · total 140.6s

## Overview

[Open the dashboard](review.html)

**Ready to ship?** No
- Work order approved on the review page: no (run without REVIEW=1)
- OCR text approved: not needed (intake added no OCR text; the publisher's text layer is OCR, see §4)
- Safety checks: OK
- Manual check (PAC): not run

**Safety checks:** OK ✔ pages look the same · OK ✔ text unchanged · OK ✔ all content tagged or decoration · OK ✔ tag-tree index points into the tree · OK ✔ every font readable  
**Needs a person:** 10 (7 deferred by the AI · 1 deferred by the executor · 2 CHECK rows)  
**AI decisions:** 694 in the work order, applied without review by a person  
**Fixed automatically (no AI):** tag-tree index entries 212 · OCR fonts given defined glyphs 61 · links tied and described 57 · table header directions 7 · title shown in the window 2 · Document root 1  
**veraPDF (WCAG 2.2 machine checks):** 6 WCAG rules failing before (69,350 checks) → 0 after (0 checks) · 0 newly failing

Automated checks are evidence, not sign-off.

| Top issues | Pages | Where |
|---|---|---|
| No link whose only text is a URL: 1: PDF 5 (printed iv) | PDF 5 (printed iv) | [§9](#9-links-whose-description-was-only-a-url-1-and-17-addresses-that-look-broken) |
| Fonts: embedded and mapped to Unicode: 8 not embedded · 0 without ToUnicode | see §8 | [§8](#8-fonts) |
| text rule "bare page number" matched no text on PDF 24–212 (printed 1–189) | see §14 | [§14](#14-deferred-by-the-executor) |
| Table of Figure 1 (faculty / object diagram laid out as a table, 20 rows × 5 columns, existing header cells) | PDF 46 (printed 23) | [§13](#13-deferred-by-the-ai) |
| Reading order and section nesting | PDF 24 (printed 1), PDF 213 (printed 190) | [§13](#13-deferred-by-the-ai) |
| … and 5 more | | §13 |

Automated checks are evidence, not legal sign-off. Items marked **CHECK**, and everything under "For a person to check", need a human.

## Automated checks

| Check | Result | Detail |
|---|---|---|
| Every page looks the same as the original | OK | 0 pages differ |
| Published text unchanged | OK | 0 pages changed |
| All content tagged or marked as decoration | OK | 0 untagged characters · 0 untagged objects |
| Untagged paths: none left | OK | 0 untagged paths |
| Invisible OCR text: every glyph defined | OK | HiddenHorzOCR: blank glyphs added for 1651 glyph references on 61 pages (replay: no page changed) |
| OCR words: every printed spelling attached | OK | 619 misread forms given their printed spelling in 1020 places |
| Page-level figure wrap | OK | no page with only an untagged drawing |
| Empty tags removed when proven empty | OK | 0 removed |
| Tag-tree index points only into the tree | OK | 0 dangling entries · 0 stale entries (marked content no longer drawn) |
| No empty tables | OK | none |
| No empty tags | OK | 0 empty tags |
| No paragraph holding only figures | OK | none |
| Every caption grouped with its figure | OK | all grouped |
| No link whose only text is a URL | **CHECK** | 1: PDF 5 (printed iv) |
| Tag tree consistent | OK | 0 missing · 0 mismatched |
| All marked text reachable from the tag tree | OK | 0 orphan runs |
| One Document root | OK | Document 1 |
| Every link tied to its text and described | OK | 0 unresolved · 0 without description · 0 pointing to no annotation |
| No link nested inside another | OK | 0 |
| Headings: no skipped levels | OK | H1 1 · H2 23 · H3 24 |
| Headings: exactly one H1 (the title) | OK | 1 H1 (several H1s usually mean parts or chapters were not demoted) |
| Figures: none with empty or placeholder alt | OK | 1 figures, 0 placeholder |
| Every Note has a unique ID | OK | 0 notes · 0 without ID · 0 duplicate · 0 not in the ID tree |
| Bookmarks present (documents over 9 pages) | OK | 22 bookmarks |
| Model reply held one work order | OK | one |
| Executor applied every decision | OK | 0 rejected · 0 failed (listed under "Decisions not applied") |
| Nothing deferred by the executor | **CHECK** | 1 deferred (listed under "Deferred by the executor") |
| Fonts: every glyph defined (no .notdef) | OK | none found |
| Fonts: every embedded font program could be read | OK | all read |
| Fonts: embedded and mapped to Unicode | **CHECK** | 8 not embedded · 0 without ToUnicode |
| Tab order follows the tag structure on pages with links or other annotations | OK | 0 of 38 pages with annotations lack /Tabs /S |
| Characters with no Unicode value (checklist 3.6) | OK | 0 read-aloud characters with no Unicode value |
| Private-use characters (checklist 3.6) | OK | 0 read-aloud characters with private-use codes |
| Title and language set | OK | "Buddhist Philosophy: A Historical Analysis" · en-US |
| veraPDF WCAG 2.2 (machine): no WCAG failures | OK | before: 6 WCAG rules failed (69350 checks) → after: 0 WCAG rules failed (0 checks) (listed under "veraPDF") |
| veraPDF: no rule newly failing or failing more often | OK | 7 fixed · 0 still failing · 0 newly failing |
| Alt text: none like a file name or repeated on many figures (1.1.1) | OK | 0 of 1 figures flagged |
| Tables: every table has header cells (1.3.1) | OK | none without |
| Reading order: no page jumps back up a column (1.3.2) | OK | 0 of 203 pages flagged |
| Reading order: no section moved away from its printed place by this run (1.3.2) | OK | 0 new · 0 already in the original, of 22 sections and blocks |
| Title is not a file name or placeholder (2.4.2) | OK | "Buddhist Philosophy: A Historical Analysis" |
| Link text: none like "click here" (2.4.4) | OK | 0 generic |
| Headings: none empty, very long or repeated in a row (2.4.6) | OK | 0 empty · 0 long · 0 repeated |

## For a person to check

### 1. Alt text written or changed by the AI (1)

| Page | Before | After |
|---|---|---|
| PDF 1 (printed cover) | — | Cover photograph of a red sandstone figure of the Bodhisattva, presumably Sakya Muni, the Buddha: seated cross-legged with the right hand raised, a topknot and a scalloped halo behind the head, set against a bright lime-green background. Mathura, first or second century A.D. |

### 2. Elements retyped by the AI (51)

Check each one is (or is not) a heading as decided.

| Page | Text | Before | After |
|---|---|---|---|
| PDF 2 (printed i) | Buddhist Philosophy | H3 | H1 |
| PDF 5 (printed iv) | Library of Congress Cataloging-in-Publication Data | H6 | P |
| PDF 8 (printed vii) | Early Buddhism | H5 | P |
| PDF 8 (printed vii) | Later Buddhism | H5 | P |
| PDF 8 (printed vii) | Contents | H4 | H2 |
| PDF 10 (printed ix) | Foreword | H4 | H2 |
| PDF 12 (printed xi) | Preface | H4 | H2 |
| PDF 18 (printed xvii) | Acknowledgments | H3 | H2 |
| PDF 20 (printed xix) | Abbreviations | H3 | H2 |
| PDF 24 (printed 1) | Early Buddhism | H2 | H2 |
| PDF 26 (printed 3) | Chapter One Historical Background | P | H2 |
| PDF 37 (printed 14) | Notes | H5 | H3 |
| PDF 38 (printed 15) | Selected Readings | H5 | H3 |
| PDF 39 (printed 16) | Chapter Two Epistemology | H3 | H2 |
| PDF 47 (printed 24) | Notes | P | H3 |
| PDF 48 (printed 25) | Selected Readings | H5 | H3 |
| PDF 49 (printed 26) | Chapter Three Causality | H4 | H2 |
| PDF 56 (printed 33) | Notes | P | H3 |
| PDF 57 (printed 34) | Selected Readings | H5 | H3 |
| PDF 59 (printed 36) | Chapter Four The Three Characteristics of Existence | P | H2 |
| PDF 65 (printed 42) | Notes | H5 | H3 |
| PDF 65 (printed 42) | Selected Readings | H5 | H3 |
| PDF 67 (printed 44) | Chapter Five Karma and Rebirth | P | H2 |
| PDF 76 (printed 53) | Notes | P | H3 |
| PDF 77 (printed 54) | Selected Readings | H5 | H3 |
| PDF 79 (printed 56) | Chapter Six Morality and Ethics | P | H2 |
| PDF 89 (printed 66) | Notes | P | H3 |
| PDF 90 (printed 67) | Selected Readings | H5 | H3 |
| PDF 92 (printed 69) | Chapter Seven Nirvana | P | H2 |
| PDF 111 (printed 88) | Notes | H5 | H3 |
| PDF 112 (printed 89) | Selected Readings | P | H3 |
| PDF 114 (printed 91) | Later Buddhism | P | H2 |
| PDF 116 (printed 93) | Chapter Eight Beginnings of Scholasticism and Mahayana | P | H2 |
| PDF 119 (printed 96) | Notes | P | H3 |
| PDF 120 (printed 97) | Chapter Nine Scholasticism-Theravada, Sarv3stivada, and Sautrantika | P | H2 |
| PDF 132 (printed 109) | Selected Readings | P | H3 |
| PDF 135 (printed 112) | Chapter Ten Development of Mahayana | P | H2 |
| PDF 149 (printed 126) | Notes | H5 | H3 |
| PDF 150 (printed 127) | Selected Readings | P | H3 |
| PDF 152 (printed 129) | Chapter Eleven Madhyamika Transcendentalism | P | H2 |
| PDF 162 (printed 139) | Notes | P | H3 |
| PDF 163 (printed 140) | Selected Readings | P | H3 |
| PDF 165 (printed 142) | Chapter Twelve Y ogacara Idealism | P | H2 |
| PDF 174 (printed 151) | Notes | P | H3 |
| PDF 174 (printed 151) | Selected Readings | P | H3 |
| PDF 176 (printed 153) | Appendix I Metaphysics and the Buddha | P | H2 |
| PDF 184 (printed 161) | Notes | P | H3 |
| PDF 186 (printed 163) | Appendix 2 Reflections on the Relation between Early Buddhism and Zen | P | H2 |
| PDF 200 (printed 177) | Selected Readings | P | H3 |
| PDF 202 (printed 179) | Index | P | H2 |
| PDF 212 (printed 189) | About the Author | P | H2 |

### 3. Lists and tables

- Header cells marked by the AI on PDF 20 (printed xix): 0 header row(s), 1 header column(s), 11 cells changed to header cells. Check they are the real headers.
- Header cells marked by the AI on PDF 21 (printed xx): 0 header row(s), 1 header column(s), 14 cells changed to header cells. Check they are the real headers.

Tables kept as tables (3): check header cells and reading order.

- PDF 20 (printed xix): 12 rows × 4 columns, 2 header cells. "A | Anguttara-nikiiya, ed. R. Morris and E. Hardy, 5 vols., London: PTS, 1885-1900; tr. F. L…"
- PDF 21 (printed xx): 15 rows × 3 columns, 2 header cells. "MKV | Madhyamakavrtti (Madhyamakakiirikiis) , ed. L. de la Vallee Poussin, Bibliotheca Buddhica 4…"
- PDF 46 (printed 23): 20 rows × 5 columns, 5 header cells. "EYE | human eye mat]1sacakkhu | I I | I form I rupa | I"

### 4. Scanned book: the text layer comes from OCR

212 of 213 pages are full-page images. Screen readers read the OCR text, which may contain recognition errors (suspect-token rate 14.3 per 1,000). Spot-check these pages against the scan: PDF 38 (printed 15), PDF 47 (printed 24), PDF 65 (printed 42), PDF 77 (printed 54), PDF 90 (printed 67), PDF 119 (printed 96), PDF 150 (printed 127), PDF 184 (printed 161). Misread words the AI could read from the scan are listed under "OCR words given their printed spelling"; other errors stay. Corrections to the text itself are an editorial decision.

### 5. OCR words given their printed spelling (619 forms, 1020 places)

The OCR misread these words, mostly letters with diacritics (ā or ū read as "ii"). The AI read each word from a crop of the scan. Screen readers now speak the printed spelling, and copying gives it (ActualText); the OCR text underneath is unchanged, so a text search still finds the OCR spelling. Apps that ignore ActualText (Preview and other PDFKit readers, some checkers) still show the OCR spelling. Check each reading against the scan on its first page.

| OCR text | Printed (AI's reading) | Places | First pages |
|---|---|---:|---|
| iitman | ātman | 31 | PDF 29 (printed 6), PDF 31 (printed 8), PDF 34 (printed 11) |
| tathiigata | tathāgata | 26 | PDF 15 (printed xiv), PDF 103 (printed 80), PDF 107 (printed 84) |
| svabhiiva | svabhāva | 25 | PDF 35 (printed 12), PDF 49 (printed 26), PDF 50 (printed 27) |
| nibbiina | nibbāna | 20 | PDF 10 (printed ix), PDF 87 (printed 64), PDF 94 (printed 71) |
| paticcasamuppiida | paṭiccasamuppāda | 15 | PDF 44 (printed 21), PDF 53 (printed 30), PDF 86 (printed 63) |
| sammii | sammā | 10 | PDF 41 (printed 18), PDF 43 (printed 20), PDF 82 (printed 59) |
| Udiina | Udāna | 9 | PDF 21 (printed xx), PDF 97 (printed 74), PDF 99 (printed 76) |
| satkiiryaviida | satkāryavāda | 8 | PDF 128 (printed 105), PDF 130 (printed 107), PDF 153 (printed 130) |
| Sutta-nipiita | Sutta-nipāta | 7 | PDF 21 (printed xx), PDF 82 (printed 59), PDF 86 (printed 63) |
| vedanii | vedanā | 7 | PDF 44 (printed 21), PDF 55 (printed 32), PDF 63 (printed 40) |
| dhammatii | dhammatā | 7 | PDF 49 (printed 26), PDF 87 (printed 64), PDF 94 (printed 71) |
| upiidiina | upādāna | 7 | PDF 83 (printed 60), PDF 101 (printed 78), PDF 108 (printed 85) |
| Majjhima-nikiiya | Majjhima-nikāya | 6 | PDF 20 (printed xix), PDF 40 (printed 17), PDF 43 (printed 20) |
| avyiikata | avyākata | 6 | PDF 63 (printed 40), PDF 103 (printed 80), PDF 107 (printed 84) |
| sanniivedayitanirodha | saññāvedayitanirodha | 6 | PDF 99 (printed 76), PDF 101 (printed 78) |
| asatkiiryaviida | asatkāryavāda | 6 | PDF 129 (printed 106), PDF 130 (printed 107), PDF 153 (printed 130) |
| Prajiiiipiiramitii | Prajñāpāramitā | 6 | PDF 141 (printed 118), PDF 147 (printed 124), PDF 155 (printed 132) |
| Subhiiti | Subhūti | 6 | PDF 142 (printed 119), PDF 146 (printed 123), PDF 147 (printed 124) |
| Anguttara-nikiiya | Aṅguttara-nikāya | 5 | PDF 20 (printed xix), PDF 71 (printed 48), PDF 135 (printed 112) |
| Chiindogya | Chāndogya | 5 | PDF 31 (printed 8), PDF 34 (printed 11), PDF 37 (printed 14) |
| samiidhi | samādhi | 5 | PDF 42 (printed 19), PDF 82 (printed 59), PDF 121 (printed 98) |
| tathatii | tathatā | 5 | PDF 50 (printed 27), PDF 141 (printed 118), PDF 145 (printed 122) |
| niimariipa | nāmarūpa | 5 | PDF 55 (printed 32), PDF 74 (printed 51), PDF 75 (printed 52) |
| dhammii | dhammā | 5 | PDF 87 (printed 64), PDF 104 (printed 81), PDF 208 (printed 185) |
| iiyatana | āyatana | 5 | PDF 118 (printed 95), PDF 143 (printed 120), PDF 182 (printed 159) |
| riipa | rūpa | 5 | PDF 122 (printed 99), PDF 126 (printed 103), PDF 148 (printed 125) |
| Vajracchedikii | Vajracchedikā | 5 | PDF 144 (printed 121), PDF 145 (printed 122), PDF 147 (printed 124) |
| dhyiina | dhyāna | 5 | PDF 166 (printed 143), PDF 186 (printed 163), PDF 190 (printed 167) |
| parammaralJii | parammaraṇā | 4 | PDF 15 (printed xiv), PDF 179 (printed 156) |
| uppiida | uppāda | 4 | PDF 60 (printed 37), PDF 123 (printed 100), PDF 124 (printed 101) |
| Mahii-parinibbiina-suttanta | Mahā-parinibbāna-suttanta | 4 | PDF 94 (printed 71), PDF 99 (printed 76), PDF 112 (printed 89) |
| vinniit;la | viññāṇa | 4 | PDF 108 (printed 85) |
| desanii | desanā | 4 | PDF 120 (printed 97), PDF 121 (printed 98) |
| Hsiian | Hsüan | 4 | PDF 133 (printed 110), PDF 165 (printed 142), PDF 175 (printed 152) |
| Sunyatii | śūnyatā | 4 | PDF 143 (printed 120), PDF 160 (printed 137), PDF 195 (printed 172) |
| dharma-kiiya | dharma-kāya | 4 | PDF 145 (printed 122), PDF 147 (printed 124), PDF 173 (printed 150) |
| Prajiiiipiiramitiis | Prajñāpāramitās | 4 | PDF 147 (printed 124), PDF 155 (printed 132) |
| Miilamadhyamakakiirikii | Mūlamadhyamakakārikā | 4 | PDF 152 (printed 129), PDF 156 (printed 133), PDF 161 (printed 138) |
| Vijnaptimiitratiisiddhi | Vijñaptimātratāsiddhi | 4 | PDF 166 (printed 143), PDF 173 (printed 150), PDF 174 (printed 151) |
| tathiigato | tathāgato | 4 | PDF 179 (printed 156) |
| bhiisitii | bhāsitā | 4 | PDF 191 (printed 168), PDF 192 (printed 169) |
| kattii | kattā | 4 | PDF 191 (printed 168), PDF 192 (printed 169) |
| gajjitii | gajjitā | 4 | PDF 191 (printed 168), PDF 192 (printed 169) |
| vassitii | vassitā | 4 | PDF 191 (printed 168), PDF 192 (printed 169) |
| dharmakiiya | dharmakāya | 3 | PDF 15 (printed xiv), PDF 141 (printed 118), PDF 161 (printed 138) |
| Samyutta-nikiiya | Saṃyutta-nikāya | 3 | PDF 21 (printed xx), PDF 60 (printed 37), PDF 107 (printed 84) |
| jhiina | jhāna | 3 | PDF 29 (printed 6), PDF 206 (printed 183) |
| anviiya | anvāya | 3 | PDF 41 (printed 18) |
| vijjii | vijjā | 3 | PDF 42 (printed 19), PDF 101 (printed 78), PDF 138 (printed 115) |
| sannii | saññā | 3 | PDF 43 (printed 20), PDF 63 (printed 40), PDF 101 (printed 78) |
| avijjii | avijjā | 3 | PDF 55 (printed 32), PDF 101 (printed 78), PDF 147 (printed 124) |
| sankhiira | saṅkhāra | 3 | PDF 55 (printed 32), PDF 87 (printed 64) |
| Triibner | Trübner | 3 | PDF 58 (printed 35), PDF 151 (printed 128) |
| Assutavii-sutta | Assutavā-sutta | 3 | PDF 60 (printed 37), PDF 65 (printed 42), PDF 202 (printed 179) |
| sukhakiima | sukhakāma | 3 | PDF 61 (printed 38), PDF 70 (printed 47), PDF 88 (printed 65) |
| avyiikrta | avyākṛta | 3 | PDF 63 (printed 40), PDF 176 (printed 153), PDF 211 (printed 188) |
| Alagaddiipama-sutta | Alagaddūpama-sutta | 3 | PDF 65 (printed 42), PDF 113 (printed 90), PDF 202 (printed 179) |
| riiga | rāga | 3 | PDF 70 (printed 47), PDF 94 (printed 71), PDF 112 (printed 89) |
| vipiika | vipāka | 3 | PDF 70 (printed 47), PDF 170 (printed 147) |
| jiiti | jāti | 3 | PDF 80 (printed 57), PDF 102 (printed 79), PDF 124 (printed 101) |
| musii | musā | 3 | PDF 86 (printed 63), PDF 159 (printed 136) |
| iisavas | āsavas | 3 | PDF 107 (printed 84) |
| niima | nāma | 3 | PDF 121 (printed 98), PDF 123 (printed 100) |
| Jiitaka-nidiina-kathii | Jātaka-nidāna-kathā | 3 | PDF 141 (printed 118), PDF 150 (printed 127), PDF 206 (printed 183) |
| Kathiivatthu | Kathāvatthu | 3 | PDF 141 (printed 118), PDF 150 (printed 127), PDF 206 (printed 183) |
| upiiyakausalya | upāyakauśalya | 3 | PDF 142 (printed 119), PDF 211 (printed 188) |
| Prajniipiiramitiis | Prajñāpāramitās | 3 | PDF 152 (printed 129), PDF 156 (printed 133) |
| pratityasamutpiida | pratītyasamutpāda | 3 | PDF 162 (printed 139), PDF 203 (printed 180) |
| TrifJ1sikii | Triṃśikā | 3 | PDF 170 (printed 147) |
| iilaya | ālaya | 3 | PDF 170 (printed 147), PDF 174 (printed 151), PDF 178 (printed 155) |
| vijiiaptimatra | vijñaptimātra | 3 | PDF 172 (printed 149) |
| Brahmajiila-suttanta | Brahmajāla-suttanta | 3 | PDF 178 (printed 155), PDF 185 (printed 162), PDF 203 (printed 180) |
| Siinyatii | śūnyatā | 3 | PDF 155 (printed 132), PDF 161 (printed 138) |
| parinirviina | parinirvāṇa | 2 | PDF 10 (printed ix), PDF 130 (printed 107) |
| siitra | sūtra | 2 | PDF 13 (printed xii), PDF 129 (printed 106) |
| Siitra | Sūtra | 2 | PDF 13 (printed xii) |
| abhiiiiiii | abhiññā | 2 | PDF 16 (printed xv), PDF 206 (printed 183) |
| Miiller | Müller | 2 | PDF 20 (printed xix) |
| Miila-madhyamaka-kiirikii | Mūla-madhyamaka-kārikā | 2 | PDF 20 (printed xix), PDF 147 (printed 124) |
| ariipa | arūpa | 2 | PDF 29 (printed 6), PDF 30 (printed 7) |
| Mahiibhiirata | Mahābhārata | 2 | PDF 35 (printed 12), PDF 38 (printed 15) |
| utpiida | utpāda | 2 | PDF 36 (printed 13), PDF 160 (printed 137) |
| Kiiliima-sutta | Kālāma-sutta | 2 | PDF 39 (printed 16), PDF 206 (printed 183) |
| yathiibhiita | yathābhūta | 2 | PDF 41 (printed 18), PDF 62 (printed 39) |
| iinupubblkathii | ānupubbīkathā | 2 | PDF 43 (printed 20), PDF 206 (printed 183) |
| manasikiira | manasikāra | 2 | PDF 43 (printed 20) |
| kiiya | kāya | 2 | PDF 46 (printed 23), PDF 145 (printed 122) |
| avitathatii | avitathatā | 2 | PDF 50 (printed 27), PDF 51 (printed 28) |
| anannathatii | anaññathatā | 2 | PDF 50 (printed 27), PDF 51 (printed 28) |
| idappaccayatii | idappaccayatā | 2 | PDF 50 (printed 27), PDF 178 (printed 155) |
| adhiccasamuppiida | adhiccasamuppāda | 2 | PDF 51 (printed 28), PDF 206 (printed 183) |
| niitta | ñāṇa | 2 | PDF 53 (printed 30) |
| kamma-niyiima | kamma-niyāma | 2 | PDF 53 (printed 30), PDF 69 (printed 46) |
| aniitman | anātman | 2 | PDF 61 (printed 38), PDF 177 (printed 154) |
| amaritukiima | amaritukāma | 2 | PDF 61 (printed 38), PDF 180 (printed 157) |
| cetanii | cetanā | 2 | PDF 70 (printed 47), PDF 170 (printed 147) |
| jfvitukiima | jīvitukāma | 2 | PDF 70 (printed 47), PDF 180 (printed 157) |
| vinniilJa | viññāṇa | 2 | PDF 74 (printed 51), PDF 116 (printed 93) |
| talJhii | taṇhā | 2 | PDF 83 (printed 60), PDF 99 (printed 76) |
| viipasama | vūpasama | 2 | PDF 83 (printed 60), PDF 84 (printed 61) |
| Ambalatthikii | Ambalaṭṭhikā | 2 | PDF 85 (printed 62) |
| Riihuloviida-sutta | Rāhulovāda-sutta | 2 | PDF 85 (printed 62) |
| sabbasankhiirasamatha | sabbasaṅkhārasamatha | 2 | PDF 87 (printed 64), PDF 97 (printed 74) |
| dhamma-niyiima | dhamma-niyāma | 2 | PDF 87 (printed 64), PDF 97 (printed 74) |
| viriiga | virāga | 2 | PDF 87 (printed 64), PDF 104 (printed 81) |
| nirodhasamiipatti | nirodhasamāpatti | 2 | PDF 94 (printed 71), PDF 203 (printed 180) |
| jhiinas | jhānas | 2 | PDF 99 (printed 76), PDF 104 (printed 81) |
| vohiira | vohāra | 2 | PDF 121 (printed 98), PDF 122 (printed 99) |
| upiidiiya | upādāya | 2 | PDF 122 (printed 99), PDF 123 (printed 100) |
| yathiitva | yathātva | 2 | PDF 127 (printed 104), PDF 128 (printed 105) |
| bhiiva | bhāva | 2 | PDF 127 (printed 104), PDF 153 (printed 130) |
| iisavii | āsavā | 2 | PDF 135 (printed 112), PDF 139 (printed 116) |
| iisavakkhaya | āsavakkhaya | 2 | PDF 139 (printed 116), PDF 206 (printed 183) |
| Mahiivastu | Mahāvastu | 2 | PDF 141 (printed 118), PDF 150 (printed 127) |
| satthii | satthā | 2 | PDF 143 (printed 120), PDF 144 (printed 121) |
| piiramitii | pāramitā | 2 | PDF 144 (printed 121), PDF 199 (printed 176) |
| Prajniipiiramitii | Prajñāpāramitā | 2 | PDF 144 (printed 121), PDF 152 (printed 129) |
| chedikii | chedikā | 2 | PDF 145 (printed 122), PDF 147 (printed 124) |
| sal']1siira | saṃsāra | 2 | PDF 147 (printed 124) |
| Prajiiaparamita | Prajñāpāramitā | 2 | PDF 151 (printed 128), PDF 188 (printed 165) |
| Prasannapadii | Prasannapadā | 2 | PDF 152 (printed 129), PDF 163 (printed 140) |
| Miidhyamikavrtti | Mādhyamikavṛtti | 2 | PDF 152 (printed 129), PDF 163 (printed 140) |
| Miilamadhaymakakiirikii | Mūlamadhaymakakārikā | 2 | PDF 152 (printed 129), PDF 163 (printed 140) |
| iitma-tradition | ātma-tradition | 2 | PDF 153 (printed 130), PDF 202 (printed 179) |
| aniitma-tradition | anātma-tradition | 2 | PDF 153 (printed 130), PDF 202 (printed 179) |
| miirga | mārga | 2 | PDF 161 (printed 138), PDF 208 (printed 185) |
| Vijnaptimiitratii | Vijñaptimātratā | 2 | PDF 165 (printed 142), PDF 175 (printed 152) |
| Vijiiaptimiitratiisiddhi | Vijñaptimātratāsiddhi | 2 | PDF 165 (printed 142), PDF 174 (printed 151) |
| eka-yiina | eka-yāna | 2 | PDF 170 (printed 147), PDF 211 (printed 188) |
| iilaya-vijniina | ālaya-vijñāna | 2 | PDF 170 (printed 147), PDF 171 (printed 148) |
| viisanii | vāsanā | 2 | PDF 170 (printed 147) |
| PramiilJasamuccaya | Pramāṇasamuccaya | 2 | PDF 173 (printed 150) |
| Sandhinirmocana-siitra | Sandhinirmocana-sūtra | 2 | PDF 173 (printed 150), PDF 209 (printed 186) |
| Culla-Miilunkyaputta-sutta | Culla-Māluṅkyaputta-sutta | 2 | PDF 183 (printed 160), PDF 185 (printed 162) |
| Prajiiaparamitas | Prajñāpāramitās | 2 | PDF 188 (printed 165) |
| Pataiijali | Patañjali | 2 | PDF 193 (printed 170) |
| iilaya-vijiiiina | ālaya-vijñāna | 2 | PDF 198 (printed 175), PDF 202 (printed 179) |
| viida | vāda | 2 | PDF 208 (printed 185) |
| nibbiilla | nibbāna | 1 | PDF 10 (printed ix) |
| jniipiiramitii | jñāpāramitā | 1 | PDF 11 (printed x) |
| AvatalJ1saka-siitra | Avataṃsaka-sūtra | 1 | PDF 13 (printed xii) |
| ucchedaviidl | ucchedavādī | 1 | PDF 15 (printed xiv) |
| sadii | sadā | 1 | PDF 15 (printed xiv) |
| sthitii | sthitāḥ | 1 | PDF 15 (printed xiv) |
| aviicya | avācya | 1 | PDF 15 (printed xiv) |
| Vibhii~iiprabhiivrtti | Vibhāṣāprabhāvṛtti | 1 | PDF 20 (printed xix) |
| Vibhii$iiprabhiivrtti | Vibhāṣāprabhāvṛtti | 1 | PDF 20 (printed xix) |
| Digha-nikiiya | Digha-nikāya | 1 | PDF 20 (printed xix) |
| Sumangalaviliisinr | Sumaṅgalavilāsinī | 1 | PDF 20 (printed xix) |
| Digha-nikiiya-atthakathii | Digha-nikāya-aṭṭhakathā | 1 | PDF 20 (printed xix) |
| tthasiilin | Atthasālini | 1 | PDF 20 (printed xix) |
| Dhammasanganl-atthakathii | Dhammasaṅganī-aṭṭhakathā | 1 | PDF 20 (printed xix) |
| Madhyamakakiirikiis | Madhyamakakārikās | 1 | PDF 21 (printed xx) |
| Sphutiirthabhidharmakosa-vyiikhyii | Sphuṭârthâbhidharmakośa-vyākhyā | 1 | PDF 21 (printed xx) |
| SaddharmapulJljar"ika-siitra | Saddharmapuṇḍarīka-sūtra | 1 | PDF 21 (printed xx) |
| Thera-gathii | Thera-gathā | 1 | PDF 21 (printed xx) |
| Thera-ther"i-giithii | Thera-therī-gāthā | 1 | PDF 21 (printed xx) |
| Vajracchedikii-prajniipiiramitii | Vajracchedikā-prajñāpāramitā | 1 | PDF 21 (printed xx) |
| Vibhanga-atthakathii | Vibhaṅga-aṭṭhakathā | 1 | PDF 21 (printed xx) |
| mahiiyogin | mahāyogin | 1 | PDF 26 (printed 3) |
| briihmat/a | brāhmaṇa | 1 | PDF 28 (printed 5) |
| jiiiina | jñāna | 1 | PDF 29 (printed 6) |
| Brhadiirat:tyaka | Bṛhadāraṇyaka | 1 | PDF 31 (printed 8) |
| sarviin | sarvān | 1 | PDF 34 (printed 11) |
| vediin | vedān | 1 | PDF 34 (printed 11) |
| Siimaveda | Sāmaveda | 1 | PDF 34 (printed 11) |
| mahiibhuta | mahābhūta | 1 | PDF 35 (printed 12) |
| niyati-viida | niyati-vāda | 1 | PDF 35 (printed 12) |
| briihma(la | brāhmaṇa | 1 | PDF 35 (printed 12) |
| Siinti-parvan | Śānti-parvan | 1 | PDF 35 (printed 12) |
| catuyiimasal11vara}.14 | catuyāmasaṃvara | 1 | PDF 36 (printed 13) |
| viid"i | vādī | 1 | PDF 36 (printed 13) |
| jniina | jñāna | 1 | PDF 36 (printed 13) |
| Vriitya | Vrātya | 1 | PDF 37 (printed 14) |
| Briihmal;la | Brāhmaṇa | 1 | PDF 37 (printed 14) |
| Saiijaya | Sañjaya | 1 | PDF 39 (printed 16) |
| sviinussutalfl | svānussutaṃ | 1 | PDF 40 (printed 17) |
| bhiitalfl | bhūtaṃ | 1 | PDF 40 (printed 17) |
| anassiisika | anassāsika | 1 | PDF 40 (printed 17) |
| vlmalflsii | vīmaṃsā | 1 | PDF 40 (printed 17) |
| Brahmajiila-suttanta,8 | Brahmajāla-suttanta | 1 | PDF 41 (printed 18) |
| iitappam | ātappam | 1 | PDF 41 (printed 18) |
| padhiinam | padhānam | 1 | PDF 41 (printed 18) |
| allviiya | anvāya | 1 | PDF 41 (printed 18) |
| mallasikiiram | manasikāram | 1 | PDF 41 (printed 18) |
| anupiidii | anupādā | 1 | PDF 41 (printed 18) |
| abhinnii | abhiññā | 1 | PDF 42 (printed 19) |
| matii).1 | matā | 1 | PDF 42 (printed 19) |
| upanisii | upanisā | 1 | PDF 42 (printed 19) |
| chaJabhinnii | chaḷabhiññā | 1 | PDF 42 (printed 19) |
| ditthijiila | diṭṭhijāla | 1 | PDF 42 (printed 19) |
| yathiibhiitaniit;/a | yathābhūtañāṇa | 1 | PDF 42 (printed 19) |
| tat;thii | taṇhā | 1 | PDF 44 (printed 21) |
| miina | māna | 1 | PDF 44 (printed 21) |
| adhitthiina | adhiṭṭhāna | 1 | PDF 44 (printed 21) |
| cetopariyaiiatza | cetopariyañāṇa | 1 | PDF 45 (printed 22) |
| pubbenivasanussatiiiatza | pubbenivāsânussatiñāṇa | 1 | PDF 45 (printed 22) |
| asavakkhayaiiatza | āsavakkhayañāṇa | 1 | PDF 45 (printed 22) |
| ghiil;la | ghāṇa | 1 | PDF 46 (printed 23) |
| jivhii | jivhā | 1 | PDF 46 (printed 23) |
| asamiihita | asamāhita | 1 | PDF 46 (printed 23) |
| samiihita | samāhita | 1 | PDF 46 (printed 23) |
| pubbeniviisanussatiniil;la | pubbenivāsânussatiñāṇa | 1 | PDF 46 (printed 23) |
| cetopariyaniil;la | cetopariyañāṇa | 1 | PDF 46 (printed 23) |
| iisavakkhayaniil;la | āsavakkhayañāṇa | 1 | PDF 46 (printed 23) |
| jiiQussoQl | Jāṇussoṇī | 1 | PDF 46 (printed 23) |
| hitatii | ṭhitatā | 1 | PDF 49 (printed 26) |
| dhammaniyiimatii | dhammaniyāmatā | 1 | PDF 49 (printed 26) |
| paticcasamppiida | paṭiccasamppāda | 1 | PDF 49 (printed 26) |
| viicarambhanaf11 | vācârambhanaṃ | 1 | PDF 51 (printed 28) |
| niimadheyaf11);4 | nāmadheyaṃ | 1 | PDF 51 (printed 28) |
| dhammadhiitu | dhammadhātu | 1 | PDF 51 (printed 28) |
| puriit;laf11 | purāṇaṃ | 1 | PDF 51 (printed 28) |
| riijadhiinif11).6 | rājadhāniṃ | 1 | PDF 51 (printed 28) |
| cayatii | cayatā | 1 | PDF 51 (printed 28) |
| niyativiida | niyativāda | 1 | PDF 51 (printed 28) |
| adhiccasamuppanna-viida | adhiccasamuppanna-vāda | 1 | PDF 51 (printed 28) |
| uppiidii | uppādā | 1 | PDF 52 (printed 29) |
| nirodhii | nirodhā | 1 | PDF 52 (printed 29) |
| satkiirya-viida | satkārya-vāda | 1 | PDF 52 (printed 29) |
| asatkiirya-viida | asatkārya-vāda | 1 | PDF 52 (printed 29) |
| utu-niyiima | utu-niyāma | 1 | PDF 53 (printed 30) |
| bija-niyiima | bīja-niyāma | 1 | PDF 53 (printed 30) |
| citta-niyiima | citta-niyāma | 1 | PDF 53 (printed 30) |
| dhamma-niyiima).17 | dhamma-niyāma | 1 | PDF 53 (printed 30) |
| viiiiiatla | viññāṇa | 1 | PDF 55 (printed 32) |
| viiiiialJa | viññāṇa | 1 | PDF 55 (printed 32) |
| namariipa | nāmarūpa | 1 | PDF 55 (printed 32) |
| kiima | kāma | 1 | PDF 55 (printed 32) |
| viiiiiiitla | viññāṇa | 1 | PDF 55 (printed 32) |
| tal;lha | taṇhā | 1 | PDF 56 (printed 33) |
| Arya-salistamba-siitra | Ārya-śālistamba-sūtra | 1 | PDF 57 (printed 34) |
| pratltyasamutpada-siitra | pratītyasamutpāda-sūtra | 1 | PDF 57 (printed 34) |
| Nava-Niilandii | Nava-Nālandā | 1 | PDF 58 (printed 35) |
| Mahiivihiira | Mahāvihāra | 1 | PDF 58 (printed 35) |
| viipa | vūpa | 1 | PDF 59 (printed 36) |
| upiidiinakkhandha | upādānakkhandha | 1 | PDF 60 (printed 37) |
| assiida | assāda | 1 | PDF 60 (printed 37) |
| iisviida | āsvāda | 1 | PDF 60 (printed 37) |
| iidlnava | ādīnava | 1 | PDF 60 (printed 37) |
| unsatiifactory | unsatisfactory | 1 | PDF 61 (printed 38) |
| ahamkiira | ahamkāra | 1 | PDF 61 (printed 38) |
| kiira | kāra | 1 | PDF 61 (printed 38) |
| Fvitukiima | jīvitukāma | 1 | PDF 61 (printed 38) |
| ditthinijjhiinakkhanti | diṭṭhinijjhānakkhanti | 1 | PDF 61 (printed 38) |
| Siiti | Sāti | 1 | PDF 63 (printed 40) |
| vinniilJal'f1 | viññāṇaṃ | 1 | PDF 63 (printed 40) |
| antaryiimin | antaryāmin | 1 | PDF 63 (printed 40) |
| attii | attā | 1 | PDF 63 (printed 40) |
| aviparilJiimadhammo | apariṇāmadhammo | 1 | PDF 63 (printed 40) |
| sankhiirii | saṅkhārā | 1 | PDF 63 (printed 40) |
| khat/dhii | khandhā | 1 | PDF 63 (printed 40) |
| Brhadiiral;lyaka | Bṛhadāraṇyaka | 1 | PDF 65 (printed 42) |
| Mahiital;lhiisankhaya-sutta | Mahātaṇhāsaṅkhaya-sutta | 1 | PDF 65 (printed 42) |
| Anattii | Anattā | 1 | PDF 66 (printed 43) |
| Nibbiina | Nibbāna | 1 | PDF 66 (printed 43) |
| EARl:Y | EARLY | 1 | PDF 69 (printed 46) |
| amaritukiima),8 | amaritukāma | 1 | PDF 70 (printed 47) |
| dukkhapatikkiila | dukkhapaṭikkūla | 1 | PDF 70 (printed 47) |
| Mahii-kammavibhm1ga-sutta | Mahā-kammavibhaṅga-sutta | 1 | PDF 73 (printed 50) |
| Mahii-mmigala-sutta | Mahā-maṅgala-sutta | 1 | PDF 73 (printed 50) |
| Mahii-kammavibhatiga-sutta | Mahā-kammavibhaṅga-sutta | 1 | PDF 73 (printed 50) |
| beiief | belief | 1 | PDF 74 (printed 51) |
| Mahii-nidiina-suttanta,16 | Mahā-nidāna-suttanta | 1 | PDF 74 (printed 51) |
| vinniitta | viññāṇa | 1 | PDF 74 (printed 51) |
| bhavatalJhii | bhavataṇhā | 1 | PDF 75 (printed 52) |
| patiUhii | patiṭṭhā | 1 | PDF 75 (printed 52) |
| antariibhava | antarābhava | 1 | PDF 75 (printed 52) |
| pubbeniviisanussati | pubbenivāsânussati | 1 | PDF 75 (printed 52) |
| Ciila-kammavibhanga-sutta | Cūla-kammavibhaṅga-sutta | 1 | PDF 77 (printed 54) |
| Mahii-kammavibhanga-sutta | Mahā-kammavibhaṅga-sutta | 1 | PDF 77 (printed 54) |
| Nidiiniini | Nidānāni | 1 | PDF 77 (printed 54) |
| Anekajatisalrzsiiral]1 | Anekajātisaṃsāraṃ | 1 | PDF 80 (printed 57) |
| sandhiivissalJl | sandhāvissaṃ | 1 | PDF 80 (printed 57) |
| gahakiirakal]1 | gahakārakaṃ | 1 | PDF 80 (printed 57) |
| dukkhii | dukkhā | 1 | PDF 80 (printed 57) |
| Gahakiiraka | Gahakāraka | 1 | PDF 80 (printed 57) |
| phasukii | phāsukā | 1 | PDF 80 (printed 57) |
| bhaggii | bhaggā | 1 | PDF 80 (printed 57) |
| visatikhiiragatalJl | visaṅkhāragataṃ | 1 | PDF 80 (printed 57) |
| tarhiinal]1 | taṇhānaṃ | 1 | PDF 80 (printed 57) |
| ajjhagii.)3 | ajjhagā | 1 | PDF 80 (printed 57) |
| rat;liyo | raṇīyo | 1 | PDF 81 (printed 58) |
| pubbasikkhii | pubbasikkhā | 1 | PDF 81 (printed 58) |
| anupubbakiriyii | anupubbakiriyā | 1 | PDF 81 (printed 58) |
| anupubbapatipadii | anupubbapaṭipadā | 1 | PDF 81 (printed 58) |
| Mahii-assapura-sutta | Mahā-assapura-sutta | 1 | PDF 81 (printed 58) |
| Gat;lakamoggalliina-sutta | Gaṇakamoggallāna-sutta | 1 | PDF 81 (printed 58) |
| piipassa | pāpassa | 1 | PDF 81 (printed 58) |
| akarat;la | akaraṇa | 1 | PDF 81 (printed 58) |
| upasampadii | upasampadā | 1 | PDF 81 (printed 58) |
| Brahmajiila | Brahmajāla | 1 | PDF 82 (printed 59) |
| ciila | cūla | 1 | PDF 82 (printed 59) |
| mahii | mahā | 1 | PDF 82 (printed 59) |
| Mahii-mangala-sutta | Mahā-maṅgala-sutta | 1 | PDF 82 (printed 59) |
| Singiiloviida-sutta | Singālovāda-sutta | 1 | PDF 82 (printed 59) |
| Dfgha-nikiiya | Dīgha-nikāya | 1 | PDF 82 (printed 59) |
| adhipannii | adhipaññā | 1 | PDF 82 (printed 59) |
| iijlva | ājīva | 1 | PDF 82 (printed 59) |
| viiyiima | vāyāma | 1 | PDF 82 (printed 59) |
| sa'1'lsiira | saṃsāra | 1 | PDF 83 (printed 60) |
| Majjhima-nikiiya,14 | Majjhima-nikāya | 1 | PDF 85 (printed 62) |
| byiibiidha | byābādha | 1 | PDF 85 (printed 62) |
| vodiina | vodāna | 1 | PDF 87 (printed 64) |
| sariiga | sarāga | 1 | PDF 87 (printed 64) |
| dukkha-patikkiila | dukkha-paṭikkūla | 1 | PDF 88 (printed 65) |
| bhiita | bhūta | 1 | PDF 88 (printed 65) |
| pisiica | pisāca | 1 | PDF 88 (printed 65) |
| brahmal;la | brāhmaṇa | 1 | PDF 89 (printed 66) |
| Sigiiloviida-suttanta | Sigālovāda-suttanta | 1 | PDF 90 (printed 67) |
| Mahii-Assapura-sutta | Mahā-Assapura-sutta | 1 | PDF 90 (printed 67) |
| Ambalatthikii-Riihuloviida-sutta | Ambalaṭṭhikā-Rāhulovāda-sutta | 1 | PDF 90 (printed 67) |
| Kltiigiri-sutta | Kīṭāgiri-sutta | 1 | PDF 90 (printed 67) |
| GmJakamoggalliina-sutta | Gaṇakamoggallāna-sutta | 1 | PDF 90 (printed 67) |
| Sundarlka-Bhiiradviija-sutta | Sundarīka-Bhāradvāja-sutta | 1 | PDF 90 (printed 67) |
| Mahii-mm1gala-sutta | Mahā-maṅgala-sutta | 1 | PDF 90 (printed 67) |
| parinibbiina | parinibbāna | 1 | PDF 94 (printed 71) |
| saupii | saupā | 1 | PDF 94 (printed 71) |
| viniiatla | viññāṇa | 1 | PDF 95 (printed 72) |
| anusotagiimi | anusotagāmi | 1 | PDF 97 (printed 74) |
| putJ¢arlka | puṇḍarīka | 1 | PDF 97 (printed 74) |
| samsiira | saṃsāra | 1 | PDF 97 (printed 74) |
| nibbiina-pa{isannutta | nibbāna-paṭisaññutta | 1 | PDF 97 (printed 74) |
| riipaloka | rūpaloka | 1 | PDF 99 (printed 76) |
| ariipaloka | arūpaloka | 1 | PDF 99 (printed 76) |
| paccayii | paccayā | 1 | PDF 99 (printed 76) |
| maniipa | manāpa | 1 | PDF 99 (printed 76) |
| amaniipa | amanāpa | 1 | PDF 99 (printed 76) |
| vedayitiini | vedayitāni | 1 | PDF 101 (printed 78) |
| anabhinanditiini | anabhinanditāni | 1 | PDF 101 (printed 78) |
| bhutiini | bhūtāni | 1 | PDF 101 (printed 78) |
| niil;la | ñāṇa | 1 | PDF 101 (printed 78) |
| tal;lhii | taṇhā | 1 | PDF 101 (printed 78) |
| tal;lhakkhaya | taṇhakkhaya | 1 | PDF 101 (printed 78) |
| anupiidiina | anupādāna | 1 | PDF 101 (printed 78) |
| KhllJii | Khīṇā | 1 | PDF 102 (printed 79) |
| itthattiiyii | itthattāyā | 1 | PDF 102 (printed 79) |
| dujjiino | dujjāno | 1 | PDF 102 (printed 79) |
| pamiiIJa | pamāṇa | 1 | PDF 103 (printed 80) |
| pramiiIJa | pramāṇa | 1 | PDF 103 (printed 80) |
| nipiita | nipāta | 1 | PDF 103 (printed 80) |
| udiihu | udāhu | 1 | PDF 103 (printed 80) |
| sassatiyii | sassatiyā | 1 | PDF 103 (printed 80) |
| vinniil;1a | viññāṇa | 1 | PDF 104 (printed 81) |
| vinniil;1assa | viññāṇassa | 1 | PDF 104 (printed 81) |
| tat:zhakkhaya | taṇhakkhaya | 1 | PDF 104 (printed 81) |
| pahiilJa | pahāṇa | 1 | PDF 105 (printed 82) |
| biina | bāna | 1 | PDF 105 (printed 82) |
| iirammat;la | ārammaṇa | 1 | PDF 108 (printed 85) |
| vlnnaJ;la-processes | viññāṇa-processes | 1 | PDF 109 (printed 86) |
| itthattiiya | itthattāya | 1 | PDF 110 (printed 87) |
| existem:e | existence | 1 | PDF 110 (printed 87) |
| abbhiicikkhana | abbhācikkhana | 1 | PDF 110 (printed 87) |
| Uivitukiima | jīvitukāma | 1 | PDF 111 (printed 88) |
| Mahiiparinibbiina-suttanta | Mahāparinibbāna-suttanta | 1 | PDF 116 (printed 93) |
| antariiyikii | antarāyikā | 1 | PDF 116 (printed 93) |
| dhammii).3 | dhammā | 1 | PDF 116 (printed 93) |
| nikiiya | nikāya | 1 | PDF 117 (printed 94) |
| Piisiidika | Pāsādika | 1 | PDF 117 (printed 94) |
| miitikii | mātikā | 1 | PDF 118 (printed 95) |
| miitrkii | mātṛkā | 1 | PDF 118 (printed 95) |
| dhiitu | dhātu | 1 | PDF 118 (printed 95) |
| sappariyiiya | sappariyāya | 1 | PDF 120 (printed 97) |
| nippariyiiya | nippariyāya | 1 | PDF 120 (printed 97) |
| niimariipapariccheda | nāmarūpapariccheda | 1 | PDF 121 (printed 98) |
| iipatti | āpatti | 1 | PDF 121 (printed 98) |
| aniipatti | anāpatti | 1 | PDF 121 (printed 98) |
| amalii | amalā | 1 | PDF 121 (printed 98) |
| prajnii | prajñā | 1 | PDF 121 (printed 98) |
| niimarupapariccheda | nāmarūpapariccheda | 1 | PDF 121 (printed 98) |
| poriir:zii | porāṇā | 1 | PDF 122 (printed 99) |
| cattiiro | cattāro | 1 | PDF 122 (printed 99) |
| mahiibhiitii | mahābhūtā | 1 | PDF 122 (printed 99) |
| lakkhar:za | lakkhaṇa | 1 | PDF 122 (printed 99) |
| kappanii).11 | kappanā | 1 | PDF 122 (printed 99) |
| sabhiiva | sabhāva | 1 | PDF 122 (printed 99) |
| upiidii | upādā | 1 | PDF 123 (printed 100) |
| citta-sampayuttii | citta-sampayuttā | 1 | PDF 123 (printed 100) |
| sutriinta-ika | sūtrānta-ika | 1 | PDF 123 (printed 100) |
| sutrapramiilJika | sūtrapramāṇika | 1 | PDF 123 (printed 100) |
| SiistrapramiilJika | śāstrapramāṇika | 1 | PDF 123 (printed 100) |
| khalJaviida | khaṇavāda | 1 | PDF 123 (printed 100) |
| k~alJaviida | kṣaṇavāda | 1 | PDF 123 (printed 100) |
| paramdlJuviida | paramâṇuvāda | 1 | PDF 123 (printed 100) |
| pancadviirtivajjana | pañcadvārâvajjana | 1 | PDF 125 (printed 102) |
| cakkhuvinniina | cakkhuviññāṇa | 1 | PDF 125 (printed 102) |
| tadiirammat;la | tadārammaṇa | 1 | PDF 125 (printed 102) |
| iilayavijniina | ālayavijñāna | 1 | PDF 125 (printed 102) |
| iitmaviida | ātmavāda | 1 | PDF 125 (printed 102) |
| vijniina | vijñāna | 1 | PDF 125 (printed 102) |
| biihydrthdnumeya | bāhyârthânumeya | 1 | PDF 126 (printed 103) |
| paramdlJusmighiita | paramâṇusaṅghāta | 1 | PDF 126 (printed 103) |
| sanghiitariipa | saṅghātarūpa | 1 | PDF 127 (printed 104) |
| sanghiita | saṅghāta | 1 | PDF 127 (printed 104) |
| pa(iccasamuppiida | paṭiccasamuppāda | 1 | PDF 127 (printed 104) |
| bhiivdn | bhāvân | 1 | PDF 127 (printed 104) |
| ak~a1Jdnyathiitva | lakṣaṇânyathātva | 1 | PDF 127 (printed 104) |
| arthakriyii-kiiritva | arthakriyā-kāritva | 1 | PDF 128 (printed 105) |
| kiiritra | kāritra | 1 | PDF 128 (printed 105) |
| anyonyathiitva | anyonyathātva | 1 | PDF 128 (printed 105) |
| svabhiivata | svabhāvata | 1 | PDF 128 (printed 105) |
| abhiitvii | abhūtvā | 1 | PDF 129 (printed 106) |
| Paramiirthasiinyatii | Paramārthaśūnyatā | 1 | PDF 129 (printed 106) |
| Sik~iisamuccaya | Śikṣāsamuccaya | 1 | PDF 129 (printed 106) |
| svabhiivarahitatviit | svabhāvarahitatvāt | 1 | PDF 129 (printed 106) |
| abhiitviibhiivautpiida | abhūtvābhāvautpāda | 1 | PDF 129 (printed 106) |
| pannii | paññā | 1 | PDF 130 (printed 107) |
| khal;lapaccuppanna | khaṇapaccuppanna | 1 | PDF 132 (printed 109) |
| antariivosiinam | antarāvosānam | 1 | PDF 136 (printed 113) |
| iipanna | āpanna | 1 | PDF 136 (printed 113) |
| siimanna-phala | sāmañña-phala | 1 | PDF 138 (printed 115) |
| Siimannaphala | Sāmaññaphala | 1 | PDF 138 (printed 115) |
| sabbannutii | sabbaññutā | 1 | PDF 138 (printed 115) |
| sabbadassiivl | sabbadassāvī | 1 | PDF 138 (printed 115) |
| niiIJadassana | ñāṇadassana | 1 | PDF 138 (printed 115) |
| sattiina'11 | sattānaṃ | 1 | PDF 138 (printed 115) |
| cutupapiitaniiIJa | cutûpapātañāṇa | 1 | PDF 138 (printed 115) |
| pubbeniviisanussatiiiiiIJa | pubbenivāsânussatiñāṇa | 1 | PDF 138 (printed 115) |
| iisavakkhayaiiiiIJa)-all | āsavakkhayañāṇa | 1 | PDF 138 (printed 115) |
| Mahiipadiina-suttanta | Mahāpadāna-suttanta | 1 | PDF 139 (printed 116) |
| puriittam | purāṇam | 1 | PDF 139 (printed 116) |
| puriilJa1J1 | purāṇaṃ | 1 | PDF 139 (printed 116) |
| riijadhiini1J1 | rājadhāniṃ | 1 | PDF 139 (printed 116) |
| sammiisam | sammāsam | 1 | PDF 139 (printed 116) |
| anuyiita1J1 | anuyātaṃ | 1 | PDF 139 (printed 116) |
| Mahii-hatthipadopama-sutta | Mahā-hatthipadopama-sutta | 1 | PDF 139 (printed 116) |
| Arya-siilistamba-siitra,13 | Ārya-śālistamba-sūtra | 1 | PDF 139 (printed 116) |
| viitza | vāṇa | 1 | PDF 140 (printed 117) |
| Sraddhii | śraddhā | 1 | PDF 140 (printed 117) |
| sammiisambuddha | sammāsambuddha | 1 | PDF 141 (printed 118) |
| Saddharmaput;qartka-siitras | Saddharmapuṇḍarīka-sūtras | 1 | PDF 141 (printed 118) |
| dharmaput;qarlka | dharmapuṇḍarīka | 1 | PDF 141 (printed 118) |
| Saddharmaput;qarika | Saddharmapuṇḍarīka | 1 | PDF 141 (printed 118) |
| Saddharmaput;l¢arlka | Saddharmapuṇḍarīka | 1 | PDF 142 (printed 119) |
| Saddharmaput;l¢arika | Saddharmapuṇḍarīka | 1 | PDF 142 (printed 119) |
| Saddharmaput;l¢aiika | Saddharmapuṇḍarīka | 1 | PDF 142 (printed 119) |
| tathiigatas | tathāgatas | 1 | PDF 143 (printed 120) |
| udiira-sthiimatii | udāra-sthāmatā | 1 | PDF 144 (printed 121) |
| siistr | śāstṛ | 1 | PDF 144 (printed 121) |
| putra-pratiriipakii | putra-pratirūpakā | 1 | PDF 144 (printed 121) |
| Sukhiivatlvyiiha-siitra | Sukhāvatīvyūha-sūtra | 1 | PDF 144 (printed 121) |
| Amitayurdhyiina-siitra | Amitâyurdhyāna-sūtra | 1 | PDF 144 (printed 121) |
| Prajnii | Prajñā | 1 | PDF 144 (printed 121) |
| prajniipiiramitii | prajñāpāramitā | 1 | PDF 144 (printed 121) |
| nirmiilJa | nirmāṇa | 1 | PDF 145 (printed 122) |
| M£ila-madhyamaka-kiirikii | Mūla-madhyamaka-kārikā | 1 | PDF 147 (printed 124) |
| Mahii-prajniipiiramitii-siistra | Mahā-prajñāpāramitā-śāstra | 1 | PDF 147 (printed 124) |
| ta/;thii | taṇhā | 1 | PDF 147 (printed 124) |
| Saddharmaput;l4arlka | Saddharmapuṇḍarīka | 1 | PDF 147 (printed 124) |
| avidyii | avidyā | 1 | PDF 148 (printed 125) |
| sa1J7siira | saṃsāra | 1 | PDF 148 (printed 125) |
| Arya-siilistamba-sutra | Ārya-śālistamba-sūtra | 1 | PDF 150 (printed 127) |
| SaddharmaputI4arika-siitra | Saddharmapuṇḍarīka-sūtra | 1 | PDF 151 (printed 128) |
| dviibhyiim | dvābhyām | 1 | PDF 152 (printed 129) |
| parabhiiva | parabhāva | 1 | PDF 154 (printed 131) |
| priisangika | prāsaṅgika | 1 | PDF 154 (printed 131) |
| siinyata | śūnyatā | 1 | PDF 155 (printed 132) |
| atpiiramitiinaya | ṣaṭpāramitānaya | 1 | PDF 155 (printed 132) |
| Mahiiprajniipiiramitii-siistra | Mahāprajñāpāramitā-śāstra | 1 | PDF 156 (printed 133) |
| prat'ityasamutpiida | pratītyasamutpāda | 1 | PDF 156 (printed 133) |
| yathabhiitalfl | yathābhūtaṃ | 1 | PDF 157 (printed 134) |
| sacciini | saccāni | 1 | PDF 159 (printed 136) |
| bahiini | bahūni | 1 | PDF 159 (printed 136) |
| niinii | nānā | 1 | PDF 159 (printed 136) |
| sanniiya | saññāya | 1 | PDF 159 (printed 136) |
| nicciini | niccāni | 1 | PDF 159 (printed 136) |
| pakappayitvii | pakappayitvā | 1 | PDF 159 (printed 136) |
| iihu | āhu | 1 | PDF 159 (printed 136) |
| Mulamadhyamakakiirikii | Mūlamadhyamakakārikā | 1 | PDF 160 (printed 137) |
| asunyatii | aśūnyatā | 1 | PDF 160 (printed 137) |
| Ratniivali | Ratnāvalī | 1 | PDF 161 (printed 138) |
| sat-tii | sat-tā | 1 | PDF 161 (printed 138) |
| a-prapaiicita | a-prapañcita | 1 | PDF 161 (printed 138) |
| niistika | nāstika | 1 | PDF 161 (printed 138) |
| pratrtyasamutpiida | pratītyasamutpāda | 1 | PDF 162 (printed 139) |
| Ratniivall | Ratnāvalī | 1 | PDF 163 (printed 140) |
| Miilamadhyamakakiirikiis | Mūlamadhyamakakārikās | 1 | PDF 163 (printed 140) |
| Niigar;una | Nāgârjuna | 1 | PDF 163 (printed 140) |
| Vigrahavyiivartant | Vigrahavyāvartanī | 1 | PDF 163 (printed 140) |
| Miidhyamika | Mādhyamika | 1 | PDF 164 (printed 141) |
| Lanktivatiira-sutra | Laṅkâvatāra-sūtra | 1 | PDF 165 (printed 142) |
| Vilf1_~atikii | Viṃśatikā | 1 | PDF 165 (printed 142) |
| Trilf1sikii | Triṃśikā | 1 | PDF 165 (printed 142) |
| Mahiiyiinasangraha | Mahāyānasaṅgraha | 1 | PDF 165 (printed 142) |
| Mahiiyiinasutrtifankiira | Mahāyānasūtrâlaṅkāra | 1 | PDF 165 (printed 142) |
| Madhytintavibhiiga | Madhyântavibhāga | 1 | PDF 165 (printed 142) |
| Yogticiirabhumi-siistra | Yogâcārabhūmi-śāstra | 1 | PDF 165 (printed 142) |
| biihytirthtinumeya | bāhyârthânumeya | 1 | PDF 165 (printed 142) |
| nirmocana-siitra | nirmocana-sūtra | 1 | PDF 166 (printed 143) |
| Lmikavatiira-siitra | Laṅkâvatāra-sūtra | 1 | PDF 166 (printed 143) |
| VilJ1satikii | Viṃśatikā | 1 | PDF 166 (printed 143) |
| TrilJ1Sikii | Triṃśikā | 1 | PDF 166 (printed 143) |
| vijnaptimiitram | vijñaptimātram | 1 | PDF 166 (printed 143) |
| kiila-niyama | kāla-niyama | 1 | PDF 167 (printed 144) |
| santiina-aniyama | santāna-aniyama | 1 | PDF 167 (printed 144) |
| krtya-kriyii | kṛtya-kriyā | 1 | PDF 167 (printed 144) |
| paramdl;lu | paramâṇu | 1 | PDF 169 (printed 146) |
| vijniina-parittiima | vijñāna-pariṇāma | 1 | PDF 170 (printed 147) |
| paripiika | paripāka | 1 | PDF 170 (printed 147) |
| manaskiira | manaskāra | 1 | PDF 170 (printed 147) |
| safJ1Jnii | saṃjñā | 1 | PDF 170 (printed 147) |
| mano-vijniina | mano-vijñāna | 1 | PDF 170 (printed 147) |
| iilambana | ālambana | 1 | PDF 170 (printed 147) |
| iitma-dr~ti | ātma-dṛṣṭi | 1 | PDF 171 (printed 148) |
| iitma-moha | ātma-moha | 1 | PDF 171 (printed 148) |
| iitma-miina | ātma-māna | 1 | PDF 171 (printed 148) |
| iitma-sneha | ātma-sneha | 1 | PDF 171 (printed 148) |
| salJ1siira | saṃsāra | 1 | PDF 171 (printed 148) |
| ancidikiilika | anâdikālika | 1 | PDF 171 (printed 148) |
| pravrtti-vijniina | pravṛtti-vijñāna | 1 | PDF 171 (printed 148) |
| vasanii | vāsanā | 1 | PDF 172 (printed 149) |
| sambhoga-kiiya | sambhoga-kāya | 1 | PDF 173 (printed 150) |
| nirmiit;/a-kiiya | nirmāṇa-kāya | 1 | PDF 173 (printed 150) |
| Lat1kavatiira-siitra | Laṅkâvatāra-sūtra | 1 | PDF 173 (printed 150) |
| iilambana-pratyaya | ālambana-pratyaya | 1 | PDF 174 (printed 151) |
| vifniina | vijñāna | 1 | PDF 174 (printed 151) |
| vijiiaptimiitra | vijñaptimātra | 1 | PDF 174 (printed 151) |
| abhriinta | abhrānta | 1 | PDF 174 (printed 151) |
| biihya | bāhya | 1 | PDF 174 (printed 151) |
| VilJlsatikii | Viṃśatikā | 1 | PDF 174 (printed 151) |
| TrilJlsikii | Triṃśikā | 1 | PDF 174 (printed 151) |
| Mahiiyiinasiitriilankiira | Mahāyānasūtrālaṅkāra | 1 | PDF 174 (printed 151) |
| Vi'1'lsatikii | Viṃśatikā | 1 | PDF 175 (printed 152) |
| Tri'1'lsikii | Triṃśikā | 1 | PDF 175 (printed 152) |
| Vijnaptimiitra | Vijñaptimātra | 1 | PDF 175 (printed 152) |
| Vediinta | Vedānta | 1 | PDF 175 (printed 152) |
| Latikdvatiira-siitra | Laṅkâvatāra-sūtra | 1 | PDF 175 (printed 152) |
| Yogdciira | Yogâcāra | 1 | PDF 175 (printed 152) |
| Nikiiya | Nikāya | 1 | PDF 176 (printed 153) |
| asayal]1kiiral]1 | asayaṃkāraṃ | 1 | PDF 176 (printed 153) |
| aparal]1kiiral]1 | aparaṃkāraṃ | 1 | PDF 176 (printed 153) |
| upiiya-upiidiina-abhinivesa-vinibandha | upāya-upādāna-abhinivesa-vinibandha | 1 | PDF 177 (printed 154) |
| antavii | antavā | 1 | PDF 178 (printed 155) |
| anantavii | anantavā | 1 | PDF 179 (printed 156) |
| parammararii | parammaraṇā | 1 | PDF 179 (printed 156) |
| sassataviidl | sassatavādī | 1 | PDF 179 (printed 156) |
| appiitihlrakatalJl,ll | appāṭihīrakataṃ | 1 | PDF 181 (printed 158) |
| appiitih'rakatalJl.12 | appāṭihīrakataṃ | 1 | PDF 181 (printed 158) |
| SalJlyutta-nikiiya | Saṃyutta-nikāya | 1 | PDF 181 (printed 158) |
| viiiiiiittahiiralJ1 | viññāṇâhāraṃ | 1 | PDF 182 (printed 159) |
| iihiiretiti).14 | āhāretîti | 1 | PDF 182 (printed 159) |
| SalJ1yutta-nikiiya | Saṃyutta-nikāya | 1 | PDF 183 (printed 160) |
| siimaiiiialJ1 | sāmaññaṃ | 1 | PDF 183 (printed 160) |
| natidhii | nâtidhā | 1 | PDF 183 (printed 160) |
| Majjhimanikiiya-atthakathii | Majjhimanikāya-aṭṭhakathā | 1 | PDF 184 (printed 161) |
| Potthapiida-suttanta | Poṭṭhapāda-suttanta | 1 | PDF 185 (printed 162) |
| Vdiina | Udāna | 1 | PDF 185 (printed 162) |
| SukhiivatlvyUha | Sukhāvatīvyūha | 1 | PDF 186 (printed 163) |
| Siitras | Sūtras | 1 | PDF 187 (printed 164) |
| Saddharmaputz¢arTka-sutra | Saddharmapuṇḍarīka-sūtra | 1 | PDF 188 (printed 165) |
| put;lgarlka | puṇḍarīka | 1 | PDF 189 (printed 166) |
| Saddharmaput;lgarlka-sutra | Saddharmapuṇḍarīka-sūtra | 1 | PDF 189 (printed 166) |
| dharma-svabhiiva | dharma-svabhāva | 1 | PDF 189 (printed 166) |
| aniit | anāt | 1 | PDF 189 (printed 166) |
| sunyatii | śūnyatā | 1 | PDF 191 (printed 168) |
| siistras | śāstras | 1 | PDF 191 (printed 168) |
| valiihaka | valāhaka | 1 | PDF 191 (printed 168) |
| veyyiikaralJa | veyyākaraṇa | 1 | PDF 192 (printed 169) |
| giithii | gāthā | 1 | PDF 192 (printed 169) |
| upiirambhanisa'!lsii | upārambhânisaṃsā | 1 | PDF 192 (printed 169) |
| itiviidap | itivādap | 1 | PDF 192 (printed 169) |
| pamokkhanisa'!lsii | pamokkhânisaṃsā | 1 | PDF 192 (printed 169) |
| nittharal;la | nittharaṇa | 1 | PDF 192 (printed 169) |
| iisava | āsava | 1 | PDF 193 (printed 170) |
| Lal1ktivatiira | Laṅkâvatāra | 1 | PDF 194 (printed 171) |
| satipatthiina).13 | satipaṭṭhāna | 1 | PDF 194 (printed 171) |
| Therl-giithiis | Therī-gāthās | 1 | PDF 198 (printed 175) |
| Abhisamayalankiira-prajiiiipiiramitii-upadda-siistra | Abhisamayâlaṅkāra-prajñāpāramitā-upadeśa-śāstra | 1 | PDF 199 (printed 176) |
| Prajiiii | Prajñā | 1 | PDF 199 (printed 176) |
| Anguttara-nikiiya-atthakathii | Aṅguttara-nikāya-aṭṭhakathā | 1 | PDF 200 (printed 177) |
| Yogavaciira's | Yogâvacāra's | 1 | PDF 200 (printed 177) |
| KathiivatthuppakaralJa-atthakathii | Kathāvatthuppakaraṇa-aṭṭhakathā | 1 | PDF 200 (printed 177) |
| Abhisamayalankiira-prajiiiipiiramitii-upadesa-siistra | Abhisamayâlaṅkāra-prajñāpāramitā-upadeśa-śāstra | 1 | PDF 200 (printed 177) |
| Abhidharmakosavyiikhyii | Abhidharmakośavyākhyā | 1 | PDF 202 (printed 179) |
| Abhisamayalankiira-prajiiiipiiramitii | Abhisamayâlaṅkāra-prajñāpāramitā | 1 | PDF 202 (printed 179) |
| upadeSa-siistra | upadeśa-śāstra | 1 | PDF 202 (printed 179) |
| krtyakriyii | kṛtyakriyā | 1 | PDF 202 (printed 179) |
| Ambala((hika-Riihuloviida-sutta | Ambalaṭṭhika-Rāhulovāda-sutta | 1 | PDF 202 (printed 179) |
| Amitiiyurdhyiina-siitra | Amitāyurdhyāna-sūtra | 1 | PDF 202 (printed 179) |
| Arya-siilistamba-siitra | Ārya-śālistamba-sūtra | 1 | PDF 202 (printed 179) |
| paramavuviida | paramâṇuvāda | 1 | PDF 202 (printed 179) |
| Avadiina | Avadāna | 1 | PDF 203 (printed 180) |
| avatiir | avatār | 1 | PDF 203 (printed 180) |
| arthakriyiikiiritva | arthakriyākāritva | 1 | PDF 203 (printed 180) |
| saiiiiiivedayitanirodha | saññāvedayitanirodha | 1 | PDF 203 (printed 180) |
| adhiccasamuppannaviida | adhiccasamuppannavāda | 1 | PDF 206 (printed 183) |
| anaiiiiathatii | anaññathatā | 1 | PDF 206 (printed 183) |
| Jit:J.ussot:J.l | Jāṇussoṇī | 1 | PDF 206 (printed 183) |
| jiiana | jñāna | 1 | PDF 206 (printed 183) |
| Uiiiina | jñāna | 1 | PDF 206 (printed 183) |
| iiiiua | ñāṇa | 1 | PDF 206 (printed 183) |
| cutupapiita | cutūpapāta | 1 | PDF 206 (printed 183) |
| chaiabhiiiiia | chaḷabhiññā | 1 | PDF 206 (printed 183) |
| yathiibhuta | yathābhūta | 1 | PDF 206 (printed 183) |
| Lmikiivatiira-sutra | Laṅkâvatāra-sūtra | 1 | PDF 206 (printed 183) |
| Madhupitl¢ika-sutta | Madhupiṇḍika-sutta | 1 | PDF 207 (printed 184) |
| Maha-prajiiaparamita-.iastra | Mahā-prajñāpāramitā-śāstra | 1 | PDF 207 (printed 184) |
| anekantaviidi | anekântavādī | 1 | PDF 208 (printed 185) |
| aniigiimi | anāgāmī | 1 | PDF 208 (printed 185) |
| dharmanairiitmya | dharmanairātmya | 1 | PDF 208 (printed 185) |
| pudgalanairiitmya | pudgalanairātmya | 1 | PDF 208 (printed 185) |
| kevalajniina | kevalajñāna | 1 | PDF 208 (printed 185) |
| sabbaiiiiuta | sabbaññutā | 1 | PDF 208 (printed 185) |
| Paramarthasunyatii-sutra | Paramârthaśūnyatā-sūtra | 1 | PDF 208 (printed 185) |
| Piisadika-suttanta | Pāsādika-suttanta | 1 | PDF 208 (printed 185) |
| nevasanniinasan | nevasaññānâsañ | 1 | PDF 208 (printed 185) |
| iia | ñā | 1 | PDF 208 (printed 185) |
| biihyarthtinumeya | bāhyârthânumeya | 1 | PDF 208 (printed 185) |
| Prajniipiiramita-sutra | Prajñāpāramitā-sūtra | 1 | PDF 208 (printed 185) |
| PramaJ;laSamUCcaxa | Pramāṇasamuccaya | 1 | PDF 209 (printed 186) |
| siinya | śūnya | 1 | PDF 209 (printed 186) |
| naJ;la | ñāṇa | 1 | PDF 209 (printed 186) |
| SaddharmapulJ~arika-siitra | Saddharmapuṇḍarīka-sūtra | 1 | PDF 209 (printed 186) |
| dukkhatii | dukkhatā | 1 | PDF 211 (printed 188) |
| Brhadiiratlyaka | Bṛhadāraṇyaka | 1 | PDF 211 (printed 188) |
| Prajniipiiramita | Prajñāpāramitā | 1 | PDF 211 (printed 188) |
| Vijnaptimatratiisiddhi | Vijñaptimātratāsiddhi | 1 | PDF 211 (printed 188) |
| Vi'11satikii | Viṃśatikā | 1 | PDF 211 (printed 188) |
| YogQcarabhumi-siistra | Yogâcārabhūmi-śāstra | 1 | PDF 211 (printed 188) |

- 645 suspect forms were checked by the AI; 26 were judged correct as the OCR read them, or unreadable (e.g. "Hawaii"), and left alone.

### 6. Hidden from screen readers (artifacts)

- 9 decorative elements ("blank page scan") on PDF 3 (printed ii), PDF 7 (printed vi), PDF 9 (printed viii), PDF 17 (printed xvi), PDF 19 (printed xviii), PDF 23 (printed xxii), PDF 25 (printed 2), PDF 115 (printed 92), PDF 213 (printed 190)
- "running foot (chapter titles with page number)": text matching `(?i)\d* ?(earl ?y buddhism( and zen)?|later buddhism|appendix ?\w+|nirvana|karma and rebirth|morality and ethics|scholasticism|development of mahayana|madhyam.ka transcendentalism|causality|y ?ogacara idealism|metaphysics and the buddha|epistemology|characteristics of existence|index) ?\d*` on PDF 24–212 (printed 1–189)
- "bare page number": text matching `\d+` on PDF 24–212 (printed 1–189)
- "front matter running foot": text matching `(?i)\w* ?(foreword|preface|acknowledgments|abbreviations|contents) ?\w*` on PDF 8–23 (printed vii–xxii)

### 7. Reading order changes

Listen through these spots with a screen reader.

- Cover figure moved to the start of the document

### 8. Fonts

- **HiddenHorzOCR** (fixed by the pipeline): the invisible OCR layer of the scanned pages used a font whose program held only `.notdef`. Its program was swapped for a blank one in which every character is a defined, empty glyph of the same width (61 font objects, 1651 glyph references on 61 pages). Same character codes, same ToUnicode map, same widths, still invisible; a replay of 61 pages showed none looking different and no text changed. The fix does not make the OCR text accurate: recognition errors stay, so spot-check the OCR text against the scan.

The pipeline changes no other font: it never embeds one, replaces a visible one, or rewrites text. These need a person:

- **Not embedded** (8): Helvetica, Helvetica-Bold, Helvetica-BoldOblique, Helvetica-Oblique, Times-Bold, Times-BoldItalic, Times-Italic, Times-Roman. PDF/UA requires embedded fonts (7.21.4.1); a person must embed them with a PDF tool (e.g. Acrobat Preflight) and check that no page changes.

### 9. Links whose description was only a URL (1, and 17 addresses that look broken)

The description (what a screen reader announces) was set to the book's own sentence around the link, with the URL removed. No words were added and the visible URL is unchanged. Replace any of these with a better description if needed.

| Page | URL | Description now |
|---|---|---|
| PDF 5 (printed iv) | www.uhpress.hawaii.edu | **still the URL: no words around the URL in its sentence; a person must write the description** |

Link addresses that look broken (listed, not changed):

- PDF 53 (printed 30): `https://dhamma-niyiima).17`: the address ends with punctuation or an unmatched closing bracket from the printed text; probably broken
- PDF 87 (printed 64): `https://muni).17`: the address ends with punctuation or an unmatched closing bracket from the printed text; probably broken
- PDF 103 (printed 80): `https://arogo).21`: the address ends with punctuation or an unmatched closing bracket from the printed text; probably broken
- PDF 106 (printed 83): `https://ananuvejjo).32`: the address ends with punctuation or an unmatched closing bracket from the printed text; probably broken
- PDF 122 (printed 99): `https://kappanii).11`: the address ends with punctuation or an unmatched closing bracket from the printed text; probably broken
- PDF 123 (printed 100): `https://giihaka).14`: the address ends with punctuation or an unmatched closing bracket from the printed text; probably broken
- PDF 124 (printed 101): `https://bhanga).18`: the address ends with punctuation or an unmatched closing bracket from the printed text; probably broken
- PDF 126 (printed 103): `https://viida).26`: the address ends with punctuation or an unmatched closing bracket from the printed text; probably broken
- PDF 128 (printed 105): `https://iitmatab).31`: the address ends with punctuation or an unmatched closing bracket from the printed text; probably broken
- PDF 147 (printed 124): `https://Siinyatii).26`: the address ends with punctuation or an unmatched closing bracket from the printed text; probably broken
- PDF 158 (printed 135): `https://apara-pratyaya).14`: the address ends with punctuation or an unmatched closing bracket from the printed text; probably broken
- PDF 181 (printed 158): `https://avisaya).13`: the address ends with punctuation or an unmatched closing bracket from the printed text; probably broken
- PDF 182 (printed 159): `https://iihiiretiti).14`: the address ends with punctuation or an unmatched closing bracket from the printed text; probably broken
- PDF 183 (printed 160): `https://veyya).18`: the address ends with punctuation or an unmatched closing bracket from the printed text; probably broken
- PDF 183 (printed 160): `https://bhavissati).16`: the address ends with punctuation or an unmatched closing bracket from the printed text; probably broken
- PDF 194 (printed 171): `https://satipatthiina).13`: the address ends with punctuation or an unmatched closing bracket from the printed text; probably broken
- PDF 209 (printed 186): `https://Brahmal).as`: the address ends with punctuation or an unmatched closing bracket from the printed text; probably broken

### 10. Tag-tree index entries cleared (212)

Entries that pointed at a tag no longer in the tag tree (left by the source file, or by a tag the run removed). Nothing reads such a tag; no page, text or reachable tag changed.

- ParentTree, entries not tied to page content (annotations, forms, or keys nothing uses): key 5 (Link), key 39 (Link), key 40 (Link), key 41 (Link), key 96 (Link), key 97 (Link), key 107 (Link), key 122 (Link), key 133 (Link), key 135 (Link), key 137 (Link), key 149 (Link), key 152 (Link), key 155 (Link), key 157 (Link), key 159 (Link), key 160 (Link), key 162 (Link), key 163 (Link), key 165 (Link), key 168 (Link), key 169 (Link), key 170 (Link), key 184 (Link), key 186 (Link), key 187 (Link), key 189 (Link), key 190 (Link), key 192 (Link), key 194 (Link), key 195 (Link), key 196 (Link), key 198 (Link), key 199 (Link), key 201 (Link), key 214 (Link), key 216 (Link), key 219 (Link), key 221 (Link), key 223 (Link), key 224 (Link), key 227 (Link), key 229 (Link), key 230 (Link), key 241 (Link), key 242 (Link), key 243 (Link), key 246 (Link), key 268 (Link), key 269 (Link), key 271 (Link), key 273 (Link), key 274 (Link), key 286 (Link), key 292 (Link), key 293 (Link), key 304 (Link)
- IDTree: "AD260915-1612-26.2.21931-ADBE-000000090769" (Figure), "AD260915-1612-26.2.21931-ADBE-000000090823" (Figure), "AD260915-1612-26.2.21931-ADBE-000000090857" (Figure), "AD260915-1612-26.2.21931-ADBE-000000090880" (P), "AD260915-1612-26.2.21931-ADBE-000000090902" (P), "AD260915-1612-26.2.21931-ADBE-000000090915" (P), "AD260915-1612-26.2.21931-ADBE-000000090926" (P), "AD260915-1612-26.2.21931-ADBE-000000090941" (P), "AD260915-1612-26.2.21931-ADBE-000000090944" (Figure), "AD260915-1612-26.2.21931-ADBE-000000090960" (Figure), "AD260915-1612-26.2.21931-ADBE-000000091113" (P), "AD260915-1612-26.2.21931-ADBE-000000091125" (P), "AD260915-1612-26.2.21931-ADBE-000000091128" (Figure), "AD260915-1612-26.2.21931-ADBE-000000091134" (Figure), "AD260915-1612-26.2.21931-ADBE-000000091152" (P), "AD260915-1612-26.2.21931-ADBE-000000091219" (P), "AD260915-1612-26.2.21931-ADBE-000000091243" (P), "AD260915-1612-26.2.21931-ADBE-000000091267" (P), "AD260915-1612-26.2.21931-ADBE-000000091353" (P), "AD260915-1612-26.2.21931-ADBE-000000091402" (P), "AD260915-1612-26.2.21931-ADBE-000000091409" (P), "AD260915-1612-26.2.21931-ADBE-000000091424" (P), "AD260915-1612-26.2.21931-ADBE-000000091458" (P), "AD260915-1612-26.2.21931-ADBE-000000091508" (P), "AD260915-1612-26.2.21931-ADBE-000000091695" (P), "AD260915-1612-26.2.21931-ADBE-000000091763" (P), "AD260915-1612-26.2.21931-ADBE-000000091819" (P), "AD260915-1612-26.2.21931-ADBE-000000091832" (P), "AD260915-1612-26.2.21931-ADBE-000000091849" (P), "AD260915-1612-26.2.21931-ADBE-000000091872" (P), "AD260915-1612-26.2.21931-ADBE-000000091900" (P), "AD260915-1612-26.2.21931-ADBE-000000091934" (P), "AD260915-1612-26.2.21931-ADBE-000000091974" (P), "AD260915-1612-26.2.21931-ADBE-000000091983" (P), "AD260915-1612-26.2.21931-ADBE-000000092016" (P), "AD260915-1612-26.2.21931-ADBE-000000092044" (P), "AD260915-1612-26.2.21931-ADBE-000000092057" (P), "AD260915-1612-26.2.21931-ADBE-000000092066" (P), "AD260915-1612-26.2.21931-ADBE-000000092116" (P), "AD260915-1612-26.2.21931-ADBE-000000092125" (P), "AD260915-1612-26.2.21931-ADBE-000000092164" (P), "AD260915-1612-26.2.21931-ADBE-000000092207" (P), "AD260915-1612-26.2.21931-ADBE-000000092232" (P), "AD260915-1612-26.2.21931-ADBE-000000092241" (P), "AD260915-1612-26.2.21931-ADBE-000000092253" (P), "AD260915-1612-26.2.21931-ADBE-000000092298" (P), "AD260915-1612-26.2.21931-ADBE-000000092321" (P), "AD260915-1612-26.2.21931-ADBE-000000092360" (P), "AD260915-1612-26.2.21931-ADBE-000000092365" (P), "AD260915-1612-26.2.21931-ADBE-000000092394" (P), "AD260915-1612-26.2.21931-ADBE-000000092410" (P), "AD260915-1612-26.2.21931-ADBE-000000092459" (P), "AD260915-1612-26.2.21931-ADBE-000000092468" (P), "AD260915-1612-26.2.21931-ADBE-000000092479" (P), "AD260915-1612-26.2.21931-ADBE-000000092512" (P), "AD260915-1612-26.2.21931-ADBE-000000092532" (P), "AD260915-1612-26.2.21931-ADBE-000000092544" (P), "AD260915-1612-26.2.21931-ADBE-000000092559" (P), "AD260915-1612-26.2.21931-ADBE-000000092588" (P), "AD260915-1612-26.2.21931-ADBE-000000092621" (P), "AD260915-1612-26.2.21931-ADBE-000000092628" (P), "AD260915-1612-26.2.21931-ADBE-000000092673" (P), "AD260915-1612-26.2.21931-ADBE-000000092684" (P), "AD260915-1612-26.2.21931-ADBE-000000092704" (P), "AD260915-1612-26.2.21931-ADBE-000000092730" (P), "AD260915-1612-26.2.21931-ADBE-000000092741" (P), "AD260915-1612-26.2.21931-ADBE-000000092752" (P), "AD260915-1612-26.2.21931-ADBE-000000092767" (P), "AD260915-1612-26.2.21931-ADBE-000000092782" (P), "AD260915-1612-26.2.21931-ADBE-000000092807" (P), "AD260915-1612-26.2.21931-ADBE-000000092826" (P), "AD260915-1612-26.2.21931-ADBE-000000092861" (P), "AD260915-1612-26.2.21931-ADBE-000000092877" (P), "AD260915-1612-26.2.21931-ADBE-000000092937" (P), "AD260915-1612-26.2.21931-ADBE-000000092955" (P), "AD260915-1612-26.2.21931-ADBE-000000092975" (P), "AD260915-1612-26.2.21931-ADBE-000000092987" (P), "AD260915-1612-26.2.21931-ADBE-000000093035" (P), "AD260915-1612-26.2.21931-ADBE-000000093130" (P), "AD260915-1612-26.2.21931-ADBE-000000093147" (P), "AD260915-1612-26.2.21931-ADBE-000000093153" (Figure), "AD260915-1612-26.2.21931-ADBE-000000093185" (P), "AD260915-1612-26.2.21931-ADBE-000000093235" (P), "AD260915-1612-26.2.21931-ADBE-000000093263" (P), "AD260915-1612-26.2.21931-ADBE-000000093293" (P), "AD260915-1612-26.2.21931-ADBE-000000093318" (P), "AD260915-1612-26.2.21931-ADBE-000000093337" (P), "AD260915-1612-26.2.21931-ADBE-000000093371" (P), "AD260915-1612-26.2.21931-ADBE-000000093416" (P), "AD260915-1612-26.2.21931-ADBE-000000093438" (P), "AD260915-1612-26.2.21931-ADBE-000000093455" (P), "AD260915-1612-26.2.21931-ADBE-000000093468" (P), "AD260915-1612-26.2.21931-ADBE-000000093489" (P), "AD260915-1612-26.2.21931-ADBE-000000093550" (P), "AD260915-1612-26.2.21931-ADBE-000000093641" (P), "AD260915-1612-26.2.21931-ADBE-000000093673" (P), "AD260915-1612-26.2.21931-ADBE-000000093736" (P), "AD260915-1612-26.2.21931-ADBE-000000093761" (P), "AD260915-1612-26.2.21931-ADBE-000000093778" (P), "AD260915-1612-26.2.21931-ADBE-000000093814" (P), "AD260915-1612-26.2.21931-ADBE-000000093831" (P), "AD260915-1612-26.2.21931-ADBE-000000093852" (P), "AD260915-1612-26.2.21931-ADBE-000000093872" (P), "AD260915-1612-26.2.21931-ADBE-000000093885" (P), "AD260915-1612-26.2.21931-ADBE-000000093929" (P), "AD260915-1612-26.2.21931-ADBE-000000094031" (P), "AD260915-1612-26.2.21931-ADBE-000000094048" (P), "AD260915-1612-26.2.21931-ADBE-000000094069" (P), "AD260915-1612-26.2.21931-ADBE-000000094093" (P), "AD260915-1612-26.2.21931-ADBE-000000094107" (P), "AD260915-1612-26.2.21931-ADBE-000000094128" (P), "AD260915-1612-26.2.21931-ADBE-000000094162" (P), "AD260915-1612-26.2.21931-ADBE-000000094218" (P), "AD260915-1612-26.2.21931-ADBE-000000094277" (P), "AD260915-1612-26.2.21931-ADBE-000000094320" (P), "AD260915-1612-26.2.21931-ADBE-000000094333" (P), "AD260915-1612-26.2.21931-ADBE-000000094354" (P), "AD260915-1612-26.2.21931-ADBE-000000094381" (P), "AD260915-1612-26.2.21931-ADBE-000000094405" (P), "AD260915-1612-26.2.21931-ADBE-000000094414" (P), "AD260915-1612-26.2.21931-ADBE-000000094443" (P), "AD260915-1612-26.2.21931-ADBE-000000094472" (P), "AD260915-1612-26.2.21931-ADBE-000000094483" (P), "AD260915-1612-26.2.21931-ADBE-000000094509" (P), "AD260915-1612-26.2.21931-ADBE-000000094522" (P), "AD260915-1612-26.2.21931-ADBE-000000094566" (P), "AD260915-1612-26.2.21931-ADBE-000000094597" (P), "AD260915-1612-26.2.21931-ADBE-000000094638" (P), "AD260915-1612-26.2.21931-ADBE-000000094650" (P), "AD260915-1612-26.2.21931-ADBE-000000094688" (P), "AD260915-1612-26.2.21931-ADBE-000000094706" (P), "AD260915-1612-26.2.21931-ADBE-000000094725" (P), "AD260915-1612-26.2.21931-ADBE-000000094766" (P), "AD260915-1612-26.2.21931-ADBE-000000094812" (P), "AD260915-1612-26.2.21931-ADBE-000000094833" (P), "AD260915-1612-26.2.21931-ADBE-000000094844" (P), "AD260915-1612-26.2.21931-ADBE-000000094865" (P), "AD260915-1612-26.2.21931-ADBE-000000094882" (P), "AD260915-1612-26.2.21931-ADBE-000000094899" (P), "AD260915-1612-26.2.21931-ADBE-000000094911" (P), "AD260915-1612-26.2.21931-ADBE-000000094926" (P), "AD260915-1612-26.2.21931-ADBE-000000094945" (P), "AD260915-1612-26.2.21931-ADBE-000000094966" (P), "AD260915-1612-26.2.21931-ADBE-000000095008" (P), "AD260915-1612-26.2.21931-ADBE-000000095023" (P), "AD260915-1612-26.2.21931-ADBE-000000095046" (P), "AD260915-1612-26.2.21931-ADBE-000000095164" (P), "AD260915-1612-26.2.21931-ADBE-000000095183" (P), "AD260915-1612-26.2.21931-ADBE-000000095303" (P), "AD260915-1612-26.2.21931-ADBE-000000095382" (P), "AD260915-1612-26.2.21931-ADBE-000000095482" (P), "AD260915-1612-26.2.21931-ADBE-000000095547" (P), "AD260915-1612-26.2.21931-ADBE-000000095574" (P), "AD260915-1612-26.2.21931-ADBE-000000095610" (P), "AD260915-1612-26.2.21931-ADBE-000000095620" (Figure)

### 11. Structure left for a person

- PDF 5 (printed iv): a link's description is only its URL (www.uhpress.hawaii.edu)

### 12. veraPDF (WCAG 2.2 machine profile), before and after

veraPDF 1.30.0, profile "WCAG 2.2 machine validation profile" (7da399cf5baa). Counts are failed checks; pages are from the first checks veraPDF lists for each rule, so a rule may fail on more pages. Rules that only PDF/UA requires are listed apart and do not count. "Who fixes" is who can act on the rule: the pipeline by itself, the AI through the work order, or only a person. **Newly failing** means this run broke something the original passed. Before: 6 rules failing (the AI can act on 4, the pipeline on 2, only a person on 0). After: 0.

| Rule | WCAG | What it checks | Who fixes | Before | After | Status | Pages (after, else before) |
|---|---|---|---|---:|---:|---|---|
| ISO 14289-1 7.2-34 | 3.1.1 | Natural language for text in page content shall be determined | the AI (`document`) | 68241 | 0 | fixed | PDF 1 (printed cover), PDF 2 (printed i), PDF 4 (printed iii) |
| ISO 14289-1 7.21.8-1 | 1.3.1 | A PDF/UA compliant document shall not contain a reference to the .notdef glyph from any of the text showing operators, regardless of text rendering mode, in any content stream | the pipeline | 1057 | 0 | fixed | PDF 14 (printed xiii), PDF 15 (printed xiv) |
| ISO 14289-1 7.2-2 | 3.1.2 | Natural language in the Outline entries shall be determined | the AI (`document`) | 22 | 0 | fixed | page: not on this tag |
| ISO 14289-1 7.2-21 | 3.1.1, 3.1.2 | Natural language for text in ActualText attribute shall be determined | the AI (`document`) | 19 | 0 | fixed | PDF 5 (printed iv), PDF 35 (printed 12), PDF 37 (printed 14), PDF 43 (printed 20), PDF 55 (printed 32), PDF 56 (printed 33), PDF 59 (printed 36), PDF 74 (printed 51), PDF 123 (printed 100), PDF 163 (printed 140), PDF 189 (printed 166), PDF 200 (printed 177), PDF 202 (printed 179), PDF 203 (printed 180), PDF 205 (printed 182), PDF 206 (printed 183), PDF 207 (printed 184), PDF 209 (printed 186) |
| ISO 14289-1 7.3-1 | 1.1.1 | Figure tags shall include an alternative representation or replacement text that represents the contents marked with the Figure tag as noted in ISO 32000-1:2008, 14.7.2, Table 323 | the AI (`alt`) | 10 | 0 | fixed | PDF 1 (printed cover), PDF 3 (printed ii), PDF 7 (printed vi), PDF 9 (printed viii), PDF 17 (printed xvi), PDF 19 (printed xviii), PDF 23 (printed xxii), PDF 25 (printed 2), PDF 115 (printed 92), PDF 213 (printed 190) |
| ISO 14289-1 7.1-10 | 2.4.2 | The document catalog dictionary shall include a ViewerPreferences dictionary containing a DisplayDocTitle key, whose value shall be true | the pipeline (1 changed) | 1 | 0 | fixed | page: not on this tag |

### 13. Deferred by the AI

- **Table of Figure 1 (faculty / object diagram laid out as a table, 20 rows × 5 columns, existing header cells)**: Layout is a diagram of sense faculties and objects; header rows and columns cannot be told from the digest. A person should decide whether to keep it as a table (and set its headers) or tag it as a Figure with a long description. [PDF 46 (printed 23)]
- **Reading order and section nesting**: The tree has two Part containers, and sections (chapters, Notes, Selected Readings) are nested inside one another (e.g. Chapter Two section spanning PDF 39–213). I can't tell from the digest whether the reading order is actually wrong, so I made no move_section. A person should check that chapters, notes and readings are read in printed order. [PDF 24 (printed 1), PDF 213 (printed 190)]
- **Heading outline**: Chapters, parts and back matter are all H2 and Notes / Selected Readings are H3, set per element from the text and size. Headings on PDF 177 (printed 154) and 178 (printed 155, 'SECONDARY SOURCES') are not in the digest's heading candidates, so please check them. [PDF 177 (printed 154), PDF 178 (printed 155)]
- **Poor OCR text layer**: Paper Capture OCR, about 14 suspect tokens per 1000. Worst pages are PDF 90, 184, 77, 65, 47, 150, 38 and 119. The text itself is not changed. Diacritics were corrected only through ocr_words, and only where the crop was legible. Forms I left out were uncertain (e.g. ids 330, 349, 428, 609) or contained spaces or punctuation (ids 74, 79, 176, 200, 239). [PDF 38 (printed 15), PDF 47 (printed 24), PDF 65 (printed 42), PDF 77 (printed 54), PDF 90 (printed 67), PDF 119 (printed 96), PDF 150 (printed 127), PDF 184 (printed 161)]
- **Contents page**: Each contents paragraph holds several entries (title and page number run together), so TOC/TOCI wraps whole paragraphs rather than single entries. A person should check the contents page. The part labels 'Early Buddhism' and 'Later Buddhism' were demoted from H5 to P. [PDF 8 (printed vii)]
- **Endnote lists**: Endnote paragraphs are tagged as L/LI lists with their numbers as labels, and some items are split or merged oddly (e.g. an item with notes 2 and 3 in one LI). I left them as tagged because they are real numbered notes. A person should spot-check them. [PDF 37 (printed 14), PDF 200 (printed 177)]
- **veraPDF 7.2-2, 7.2-34, 7.2-21 and 7.1-9 (language, ActualText language, dc:title)**: Addressed by document.lang en-US and the title. Romanized Pali and Sanskrit words are not language-tagged. Please re-run veraPDF to confirm. [PDF 1 (printed cover), PDF 213 (printed 190)]

Reviewer note from the AI: Scanned book (Paper Capture OCR), 213 pages. Full-page Figures on blank pages (PDF 3, 7, 9, 17, 19, 23, 25, 115, 213) are artifacted as page scans. The only real image is the cover photograph (PDF 1). Running heads and page numbers sit at the bottom of the page and are artifacted by text rules with patterns taken from repeated_lines. The executor reports any rule that matches nothing. Heading levels: H1 book title; H2 front-matter titles, parts, chapters, appendices, index and About the Author; H3 Notes and Selected Readings.

### 14. Deferred by the executor

- text rule "bare page number" matched no text on PDF 24–212 (printed 1–189): nothing was hidden by this rule; check its pattern against the page (spacing, split runs)

### 15. Decisions not applied (11)

Rejected by validation or by the executor; nothing was half-applied.

| What | Why | Count |
|---|---|---:|
| ocr_words | too different from the OCR text to be a misreading of it | 11 |

Each one:

- {"where": "ocr_words", "item": {"id": "196", "reads": "ñassati"}, "why": "too different from the OCR text to be a misreading of it"}
- {"where": "ocr_words", "item": {"id": "258", "reads": "viññāṇa"}, "why": "too different from the OCR text to be a misreading of it"}
- {"where": "ocr_words", "item": {"id": "275", "reads": "viññāṇ"}, "why": "too different from the OCR text to be a misreading of it"}
- {"where": "ocr_words", "item": {"id": "312", "reads": "dhammâdāsa"}, "why": "too different from the OCR text to be a misreading of it"}
- {"where": "ocr_words", "item": {"id": "392", "reads": "gāhaka"}, "why": "too different from the OCR text to be a misreading of it"}
- {"where": "ocr_words", "item": {"id": "394", "reads": "bhavā"}, "why": "too different from the OCR text to be a misreading of it"}
- {"where": "ocr_words", "item": {"id": "408", "reads": "vāda"}, "why": "too different from the OCR text to be a misreading of it"}
- {"where": "ocr_words", "item": {"id": "419", "reads": "ātmataḥ"}, "why": "too different from the OCR text to be a misreading of it"}
- {"where": "ocr_words", "item": {"id": "421", "reads": "vyākhyā"}, "why": "too different from the OCR text to be a misreading of it"}
- {"where": "ocr_words", "item": {"id": "469", "reads": "śūnyatā"}, "why": "too different from the OCR text to be a misreading of it"}
- {"where": "ocr_words", "item": {"id": "587", "reads": "gahaṇa"}, "why": "too different from the OCR text to be a misreading of it"}

## What was changed

| Change | Count |
|---|---:|
| document: Document root created | 1 |
| document: DisplayDocTitle | 2 |
| artifact: "blank page scan" | 9 |
| artifact: "front matter running foot" | 7 |
| artifact: "running foot (chapter titles with page number)" | 139 |
| document: title | 1 |
| document: /Lang | 1 |
| OCR words: printed spelling given as ActualText | 1020 |
| retype → H1 | 1 |
| retype → P | 3 |
| retype → H2 | 23 |
| retype → H3 | 24 |
| table: header cells marked (work order) | 25 |
| figure: alt text | 1 |
| contents: TOC entries | 13 |
| contents: TOC built | 3 |
| links: /Contents set | 57 |
| links: joined existing Link | 57 |
| contents: entry wrapped in Reference | 13 |
| table: header cells given a direction (Scope) | 7 |
| tag tree index: entries pointing outside the tree cleared (ParentTree) | 57 |
| tag tree index: entries pointing outside the tree removed (IDTree) | 155 |
| fonts: invisible OCR-layer font given defined blank glyphs | 61 |

## Final check with PAC 2026

Open `buddhist_remediated.pdf` in PAC 2026 (https://pac.pdf-accessibility.org/en, Windows) and run its WCAG check. Anything it fails that is not listed above is a gap in the automated checks: note it in the issue tracker.

No automated check here covers these WCAG 2.2 AA criteria; check them by hand, with PAC's screen-reader and structure previews:

- 1.1.1: alt text is accurate and gives the figure's purpose; decorative images are artifacts
- 1.3.1 / 1.3.2: headings, lists and tables match what is printed, and the reading order makes sense
- 1.4.1: no information is given by colour alone
- 1.4.3: contrast of text over images and coloured backgrounds (PAC's contrast checker)
- 1.4.5: no images of text where real text could be used (scanned pages: the OCR layer stands in)
- 2.4.6: headings describe their section
- 3.1.2: passages in another language carry their language (see `han_review.csv` if present)
