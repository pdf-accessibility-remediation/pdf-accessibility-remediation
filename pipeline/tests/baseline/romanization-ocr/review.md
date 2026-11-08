# Remediation Review: romanization-ocr.pdf

Result: `romanization-ocr_remediated.pdf`

49 pages · run November 3, 2026, at 1:22 AM · model `anthropic/claude-sonnet-5.5` · prompt `workorder_v10.md` (15b5aa0ade9c6549) · AI cost $0.300 ($0.0061 per page), from the original call on November 3, 2026 · this run: no new call · tokens: saved reply reused, not counted

Intake: 1 picture page without OCR text · auto-tagged · text layer: not enough pages scored · OCR layer doubtful · OCR layer lacks diacritics · tagged by OpenDataLoader 2.5.12 · the pipeline worked on `_intake/intake.pdf`; the original was not changed

Libraries: python 3.14.4 · pikepdf 10.5.1 · pdfplumber 0.11.9 · pypdfium2 5.7.1 · pillow 13.0.0 · fonttools 4.62.1

Time: intake 0.2s · audit 15.8s · reuse saved reply 1.5s · apply 10.7s · verify 20.2s · total 48.4s

## Overview

[Open the dashboard](review.html)

**Status:** Not Ready

**Ready to ship?**
- Work Order Approval: Not Approved (applied without a review)
- OCR Text Approval: Not Reviewed (the existing OCR layer is doubtful (12% character error) and missing diacritics)
- ✓ Safety Checks: Passed
- Accessibility Evaluation: Not Completed

**Safety checks:** OK ✔ pages look the same · OK ✔ text unchanged · OK ✔ all content tagged or decoration · OK ✔ tag-tree index points into the tree · OK ✔ every font readable  
**Needs a person:** 14 (7 deferred by the AI · 2 deferred by the executor · 5 CHECK rows)  
**AI decisions:** 159 in the work order, applied without review by a person  
**Fixed automatically (no AI):** one-item lists turned into paragraphs 38 · bookmarks built 22 · empty tags removed 9 · title shown in the window 2 · OCR fonts given defined glyphs 2 · marked as tagged 1  
**veraPDF (WCAG 2.2 machine checks):** 4 WCAG rules failing before (67 checks) → 0 after (0 checks) · 0 newly failing

Automated checks are evidence, not sign-off.

| Top issues | Pages | Where |
|---|---|---|
| OCR text not yet reviewed | see §1 | [§1](#1-intake-ocr-and-auto-tagging) |
| Fonts: embedded and mapped to Unicode: 8 not embedded · 8 without ToUnicode | see §8 | [§8](#8-fonts) |
| Text layer agrees with OCR of the page (checklist 1.2): not enough pages scored | see §1 | [§1](#1-intake-ocr-and-auto-tagging) |
| Existing OCR layer agrees with a fresh OCR reading (checklist 1.2, 3.1): doubtful: median character error 11.7% on 9 sample pages; pages over 5%: PDF 26, PDF 35, PDF 39, PDF 44, PDF 49; diacritics missing from the layer (222 marked vowels read, 0 in the layer: PDF 12, PDF 17, PDF 21, PDF 30, PDF 35, PDF 39) | 9 pages, PDF 12 to PDF 49 | [§1](#1-intake-ocr-and-auto-tagging) |
| Reading order jumps back up a column (9 jumps) | PDF 12, PDF 29, PDF 31 | [§12](#12-wcag-checks-verapdf-does-not-make) |
| … and 9 more | | §13, §14 |

Automated checks are evidence, not legal sign-off. Items marked **CHECK**, and everything under "For a person to check", need a human.

## Automated Checks

| Check | Result | Detail |
|---|---|---|
| Every page looks the same as the original | OK | 0 pages differ |
| Published text unchanged | OK | 0 pages changed |
| All content tagged or marked as decoration | OK | 0 untagged characters · 0 untagged objects |
| Untagged paths: none left | OK | 0 untagged paths |
| Invisible OCR text: every glyph defined | OK | HiddenHorzOCR: blank glyphs added for 12 glyph references on 2 pages (replay: no page changed) |
| OCR words: every printed spelling attached | OK | 10 misread forms given their printed spelling in 15 places |
| Page-level figure wrap | OK | no page with only an untagged drawing |
| Empty tags removed when proven empty | OK | 9 removed |
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
| Headings: no skipped levels | OK | H1 1 · H2 4 · H3 10 · H4 7 |
| Headings: exactly one H1 (the title) | OK | 1 H1 (several H1s usually mean parts or chapters were not demoted) |
| Figures: none with empty or placeholder alt | OK | 4 figures, 0 placeholder |
| Every Note has a unique ID | OK | 0 notes · 0 without ID · 0 duplicate · 0 not in the ID tree |
| Bookmarks present (documents over 9 pages) | OK | 22 bookmarks (built from 22 heading tags) |
| Model reply held one work order | OK | one |
| Executor applied every decision | OK | 0 rejected · 0 failed (listed under "Decisions not applied") |
| Nothing deferred by the executor | **CHECK** | 2 deferred (listed under "Deferred by the executor") |
| Fonts: every glyph defined (no .notdef) | OK | none found |
| Fonts: every embedded font program could be read | OK | all read |
| Fonts: embedded and mapped to Unicode | **CHECK** | 8 not embedded · 8 without ToUnicode |
| Text layer agrees with OCR of the page (checklist 1.2) | **CHECK** | not enough pages scored |
| Existing OCR layer agrees with a fresh OCR reading (checklist 1.2, 3.1) | **CHECK** | doubtful: median character error 11.7% on 9 sample pages; pages over 5%: PDF 26, PDF 35, PDF 39, PDF 44, PDF 49; diacritics missing from the layer (222 marked vowels read, 0 in the layer: PDF 12, PDF 17, PDF 21, PDF 30, PDF 35, PDF 39) |
| Words separated in the text layer (checklist 3.4) | OK | yes on every sample page |
| OCR text added where pages had none (checklist 3.1) | OK | no image-only page held text |
| OCR text reviewed by a person | **CHECK** | the existing OCR layer is doubtful (12% character error) and missing diacritics: not yet reviewed (checklist rule 2; record a verdict on the review page's OCR Text section, or with review_ocr.py) |
| Auto-tagging kept every page as it was | OK | appearance and text unchanged on all 49 pages (OCR'd pages: text added) |
| Tab order follows the tag structure on pages with links or other annotations | OK | 0 of 0 pages with annotations lack /Tabs /S |
| Characters with no Unicode value (checklist 3.6) | OK | 0 read-aloud characters with no Unicode value |
| Private-use characters (checklist 3.6) | OK | 0 read-aloud characters with private-use codes |
| Title and language set | OK | "Chinese Romanization Self-Study Guide" · en-US |
| veraPDF WCAG 2.2 (machine): no WCAG failures | OK | before: 4 WCAG rules failed (67 checks) → after: 0 WCAG rules failed (0 checks) (listed under "veraPDF") |
| veraPDF: no rule newly failing or failing more often | OK | 4 fixed · 0 still failing · 0 newly failing |
| Alt text: none like a file name or repeated on many figures (1.1.1) | OK | 0 of 4 figures flagged |
| Tables: every table has header cells (1.3.1) | OK | none without |
| Reading order: no page jumps back up a column (1.3.2) | **CHECK** | 3 of 48 pages flagged |
| Reading order: no section moved away from its printed place by this run (1.3.2) | OK | 0 new · 0 already in the original, of 288 sections and blocks |
| Title is not a file name or placeholder (2.4.2) | OK | "Chinese Romanization Self-Study Guide" |
| Link text: none like "click here" (2.4.4) | OK | 0 generic |
| Headings: none empty, very long or repeated in a row (2.4.6) | OK | 0 empty · 0 long · 0 repeated |

## For a Person to Check

### 1. Intake: OCR and Auto-tagging

The original had no tags. Local tools prepared it before the model saw it; no model wrote or changed any text. Pages: 48 ocr-layer, 1 image-only.

Text-layer test (checklist 1.2): each sample page was OCR'd at 300 dpi and compared with its text layer.

| Page | Character error | Verdict |
|---|---:|---|
| PDF 8 | — | not scored: images cover 100% of the page |
| PDF 10 | — | not scored: images cover 100% of the page |
| PDF 12 | — | not scored: images cover 100% of the page |
| PDF 14 | — | not scored: images cover 100% of the page |
| PDF 16 | — | not scored: images cover 100% of the page |
| PDF 18 | — | not scored: images cover 100% of the page |
| PDF 20 | — | not scored: images cover 100% of the page |
| PDF 23 | — | not scored: images cover 100% of the page |
| PDF 25 | — | not scored: images cover 100% of the page |
| PDF 27 | — | not scored: images cover 100% of the page |
| PDF 29 | — | not scored: images cover 100% of the page |
| PDF 31 | — | not scored: images cover 100% of the page |
| PDF 33 | — | not scored: images cover 100% of the page |
| PDF 36 | — | not scored: images cover 100% of the page |
| PDF 38 | — | not scored: images cover 100% of the page |
| PDF 40 | — | not scored: images cover 100% of the page |
| PDF 42 | — | not scored: images cover 100% of the page |
| PDF 44 | — | not scored: images cover 100% of the page |
| PDF 46 | — | not scored: images cover 100% of the page |
| PDF 49 | — | not scored: images cover 100% of the page |

- **Narrow word gaps**: 0.2 narrow word breaks per text page on average (11 in all): gaps narrower than 19% of the type size with no space character (checklist 3.4), where readers such as Acrobat may run words together (e.g. "concernedwithChinese" on bringing PDF 86). Below 10 per page: a note
- **Text layer**: only 0 sample pages could be scored (fewer than 5): the text layer was not tested enough; a person should compare a few pages by eye
- **OCR layer**: the existing OCR layer on the scanned pages and a fresh reading by a different OCR model disagree (median character error 12% on 9 sample pages; worst first): a person compares these pages with the page image. The layer is kept as it is (it may be the library's record) (PDF 26, PDF 35, PDF 39, PDF 44, PDF 49)
- **OCR layer: diacritics**: the page images show diacritics the existing OCR layer lacks (222 marked vowels read on 6 sample pages, 0 in the layer: e.g. ŏ/ŭ lost as o/u). The OCR model reads the marks only roughly, so a person compares the pages; the layer is not changed (PDF 12, PDF 17, PDF 21, PDF 30, PDF 35, PDF 39)
- **Image pages with no text**: image-only pages where OCR found no readable text: left as pictures for the figure step (alt text). Check none is a page of text (PDF 4)
- **Placeholder alt text removed**: the auto-tagger wrote alt text that says nothing (53 figures "image N", 0 links "Annotation"); it was removed, so those figures count as having no alt text (the AI or a person writes it) and each link is read by its own text

### 2. Alt Text Written or Changed by the AI (4)

| Page | Before | After |
|---|---|---|
| PDF 1 | — | University of Hawai‘i Press logo |
| PDF 6 | — | University of Hawai‘i Press logo |
| PDF 40 | — | Wade-Giles exercise item: hao4-ma3-erh |
| PDF 40 | — | Wade-Giles exercise item: shêng1-êrh |

### 3. Elements Retyped by the AI (30)

Check each one is (or is not) a heading as decided.

| Page | Text | Before | After |
|---|---|---|---|
| PDF 2 | Chinese Romanization Self-Study Guide | H2 | P |
| PDF 5 | DENNIS K. YEE | H3 | P |
| PDF 6 | PRESS | H1 | P |
| PDF 6 | OPEN ACCESS | H2 | P |
| PDF 7 | Contents | H1 | H2 |
| PDF 7 | I. Summary of Pinyin Romanization 18 | H2 | P |
| PDF 7 | II. Comparison of Pinyin and Wade-Giles Romanizations 19 | H2 | P |
| PDF 9 | Preface | H1 | H2 |
| PDF 10 | COMPARISON OF YALE AND PINYIN ROMANIZATIONS | H3 | P |
| PDF 11 | II. COMPARISON OF YR AND PY | H1 | H3 |
| PDF 13 | Comparison of Yale and Pinyin Romanizations | H2 | P |
| PDF 14 | B. Comparison of Initials | H3 | H4 |
| PDF 14 | rem rem | H1 | P |
| PDF 21 | III. IDENTICAL SPELLINGS, DIFFERENT PRONUNCIATIONS | H1 | H3 |
| PDF 22 | IV. OVERALL REVIEW EXERCISES:t: | H2 | H3 |
| PDF 23 | V. ANSWERS TO EXERCISES | H1 | H3 |
| PDF 27 | Comparison of Pinyin and Wade-Giles Romanizations | H1 | H2 |
| PDF 27 | COMPARISON OF PINYIN AND WADE-GILES ROMANIZATIONS | H2 | P |
| PDF 27 | I. SUMMARY OF PINYIN ROMANIZATION | H2 | H3 |
| PDF 27 | A. Tones | H3 | H4 |
| PDF 27 | B. Initials. | H1 | H4 |
| PDF 28 | II. COMPARISON OF PY AND WG | H1 | H3 |
| PDF 30 | 21 | H2 | P |
| PDF 32 | s s | H3 | P |
| PDF 32 | e | H3 | P |
| PDF 40 | F. Differences within Wade-Giles System of Romanization | P | H4 |
| PDF 40 | F. Differences Within WG System . Some sources, such as Mathews' Chinese-English Dictionary, use a… | H3 | P |
| PDF 41 | III. IDENTICAL SPELLINGS, DIFFERENT PRONUNCIATIONS | H1 | H3 |
| PDF 43 | IV. OVERALL REVIEW EXERCISES§ | H2 | H3 |
| PDF 45 | V. ANSWERS TO EXERCISES | H1 | H3 |

### 4. Lists and Tables

- Flattened list on PDF 7: "1 1 1 1 2 2 2 / 2 5 7" (page numbers of contents entries, not a list)
- Flattened list on PDF 7: "1 1 1 2 2 / 2" (page numbers, not a list)
- Flattened list on PDF 7: "1 1 2 / 2" (page numbers, not a list)
- Flattened list on PDF 7: "1 / 2" (page numbers, not a list)
- Flattened list on PDF 11: "C. Finals 1. a-group: -a, -ai, -an, -ang, -au. 2. e-group: -e, -ei, -en, -eng. 3. a-group: -ou. 4…" (headings merged into list items)
- Flattened list on PDF 11: "A. Identical Features" (heading, not a list)
- Flattened list on PDF 12: "m a ai ba pa ma bai pai mai f fa d t / n" (syllable chart rows)
- Flattened list on PDF 12: "g k / h" (syllable chart rows)
- Flattened list on PDF 13: "r ran rang / s sa sai san sang e ei en eng b bei ben beng p pei pen peng m me mei men meng f fei fen…" (syllable chart rows)
- Flattened list on PDF 13: "f fei fen feng d de dei deng t te teng n ne nei nen neng le lei Ieng / g ge gei gen geng k ke kei…" (syllable chart rows)
- Flattened list on PDF 13: "r re ren reng / s se sen seng" (syllable chart rows)
- Flattened list on PDF 14: "g gou k kou / h hou sh shou" (syllable chart rows)
- Flattened list on PDF 14: "r rou / s sou" (syllable chart rows)
- Flattened list on PDF 15: "Exercise 2A. YR: jai ch6u sheng rang jan che shen PY: / Exercise 2B. PY: zha che shou reng zhou…" (exercise lines)
- Flattened list on PDF 15: "3. Sibilants. YR dz, ts are z, c in PY. s is the same in both. YR: dz ts s dza tse sai PY: z c s za…" (paragraph, not a list)
- Flattened list on PDF 15: "Exercise 3A. YR: dzan tsou sang dzei tse san PY: Exercise 3B: PY: za cai sou ZOU cang sen YR: - -4…" (exercise lines)
- Flattened list on PDF 15: "1. chan tsan sai jin jen shen" (exercise row)
- Flattened list on PDF 16: "Chinese Romanization Self-Study Guide / 2. ren dzou jou jeng shai ran" (running head and exercise rows)
- Flattened list on PDF 16: "Exercise 4B . Give YR equivalents for the following PY syllables: a b C d e 1. jing qin xin ran she…" (exercise lines and heading)
- Flattened list on PDF 16: "1. jing qin xin ran she / 2. zhai chen shang re zhan" (exercise rows)
- Flattened list on PDF 17: "Exercise 6B. PY: dong cong r6ng kong long YR: 3. Where YR uses thew-semivowel, PY uses u. YR: -wa…" (exercise lines)
- Flattened list on PDF 17: "Exercise 8A. YR: fw6 gwei rwei jwun hwun mw6 PY: / Exercise 8B. PY: tui cui b6 dim sun po YR:" (exercise lines)
- Flattened list on PDF 17: "4. Where YR uses the y-semivowel, PY uses i. YR: -ya -yan -yang -yau -ye -yung PY: -ia -ian -iang…" (paragraph, not a list)
- Flattened list on PDF 23: "Exercise 2A. PY: zhai ch6u sheng rang zhan che shen r6u Exercise 2B. YR: ja che shou reng jou chang…" (exercise lines)
- Flattened list on PDF 24: "Exercise 3B. YR: dza tsai sou dzou tsang sen Exercise 4A. a b C d e f 1. chan can sai jin zhen shen…" (exercise lines)
- Flattened list on PDF 25: "Exercise 12A. a b C d 1. hao ta.or chong hong 2. zhuan guang tuo huai 3. fo po shu'i zhui 4. qiong…" (exercise lines)
- Flattened list on PDF 26: "Exercise 13A. a b C d e f 1. tui si xue sao ri xun 2. tian xingr tiao sui rang xiu 3. liang ji huai…" (exercise lines)
- Flattened list on PDF 27: "3. Velars: g, k, h. These are made in the area of the" (paragraph, not a list)
- Flattened list on PDF 28: "C. Finals. 1.a-group:-a,-ai, -an, -ang,-ao. 2.e-group:-e,-ei, -en, -eng. 3.o-group:-o,-ong,-ou…" (headings merged into list items)
- Flattened list on PDF 28: "A. Identical Features" (heading, not a list)
- Flattened list on PDF 29: "3.Initial-less finals: a.a-group: a, ai, an, ang, ao. b.e-group: ei, en. c. a-group: ou. d.u-group…" (mixed paragraphs)
- Flattened list on PDF 29: "m / n 1 f h sh" (table cell text)
- Flattened list on PDF 29: "m / n 1 f h sh" (table cell text)
- Flattened list on PDF 29: "m / n 1" (table cell text)
- Flattened list on PDF 30: "B. Comparison of Tones" (heading, not a list)
- Flattened list on PDF 30: "B. Comparison of Tones. WG uses numbers placed at the top right-hand corner of the syllables. First…" (headings, not list items)
- Flattened list on PDF 31: "Exercise 2A. PY: jiang WG: Exercise 2B. WG: ching1 PY: ch'iang1 ch'in hsin4 chiao3 xiang hsiang3 qiu…" (exercise lines)
- Flattened list on PDF 31: "Exercise 2B. WG: ching1 PY: ch'iang1 ch'in hsin4 chiao3 xiang hsiang3 qiu xia jin qiao xing ch'ia4…" (mixed paragraphs)
- Flattened list on PDF 33: "D. Comparison of Finals" (heading, not a list)
- Flattened list on PDF 33: "1. For PY -e final, WG generally also uses -e. Since e has two" (paragraph, not a list)
- Flattened list on PDF 34: "Exercise 6B. WG: se4 k'en3 leng3 he1 t'eng2 she4 04 PY: 2. After the labials, both PY and WG use…" (exercise lines)
- Flattened list on PDF 35: "Exercise 8A. PY: tu6 cuo chuo guo zhuo kuo WG: / Exercise 8B." (exercise lines)
- Flattened list on PDF 35: "Exercise 9A. PY: cui kui shui dui WG: / Exercise 9B." (exercise lines)
- Flattened list on PDF 36: "Exercise 12A. yan yen4 PY: pian nian xian yan WG: / Exercise 12B." (exercise lines)
- Flattened list on PDF 37: "Exercise 13A. PY: nu yuan que WG: / Exercise 13B." (exercise lines)
- Flattened list on PDF 41: "pan tan kan chan pang tang kang chang / pao tao kao chao te ke che" (syllable chart rows)
- Flattened list on PDF 45: "Exercise 2B. jing qia xiao jiu qiang xiu Exercise 3A. chua1 ch'ou3 jeng1 chang3 ch'en2 jao3 /…" (exercise lines)
- Flattened list on PDF 46: "Exercise 6B. se ken Ieng he teng she e Exercise 7 A. lung2 sung4 k'ung3 ts'ung1 chung4 tsung3 /…" (exercise lines)
- Flattened list on PDF 46: "Exercise SA. t'o2 ts'o4 ch'o1 kuo3 cho1 k'uo4 / Exercise SB. duo suo ruo shuo guo huo" (exercise lines)
- Flattened list on PDF 46: "Exercise 9A. ts'ui4 k'uei 1 shui4 tui1 tsui3 kuei4 / Exercise 9B. tui sui" (exercise lines)
- Flattened list on PDF 47: "Exercise 12A. p'ien1 nien4 hsien3 yen2 / Exercise 12B. mian dian qian lian" (exercise lines)
- Flattened list on PDF 47: "Exercise 13A. nu3 yuan2 ch'ueh4 chun1 lueh4 yueh1 / Exercise 13B. qu juan yue qun yu nu" (exercise lines)
- Flattened list on PDF 47: "Exercise 14A. a b C d e f 1. 04 k'o3 men2 nen4 leng3 ts'o4 2. chui1 t'ui3 jui4 lung2 t'ung1 ch'o1 3…" (exercise lines)
- Flattened list on PDF 48: "Exercise 16A. a b C d e 1. p'a t'eng ch'ou p'u ch'ih 2. k'uai chu t'ing p'o chuan 3. p'ei k'ou t'uan…" (exercise lines)
- Header cells marked by the AI on PDF 29: 1 header row(s), 1 header column(s), 1 cells changed to header cells; 1 false header cell(s) set back to data. Check they are the real headers.
- Header cells marked by the AI on PDF 29: 1 header row(s), 1 header column(s), 1 cells changed to header cells; 1 false header cell(s) set back to data. Check they are the real headers.
- Header cells marked by the AI on PDF 29: 1 header row(s), 1 header column(s), 1 cells changed to header cells; 1 false header cell(s) set back to data. Check they are the real headers.
- Header cells marked by the AI on PDF 29: 1 header row(s), 1 header column(s), 1 cells changed to header cells; 1 false header cell(s) set back to data. Check they are the real headers.

Tables kept as tables (4): check header cells and reading order.

- PDF 29: 2 rows × 2 columns, 2 header cells. "| a ai an ang ao"
- PDF 29: 2 rows × 2 columns, 2 header cells. "| e ei en eng OU"
- PDF 29: 2 rows × 2 columns, 2 header cells. "| ua uai uang"
- PDF 29: 2 rows × 2 columns, 2 header cells. "| ia iang iao in ing iu"

### 5. Scanned Book: The Text Layer Comes from OCR

49 of 49 pages are full-page images. Screen readers read the OCR text, which may contain recognition errors (suspect-token rate 52.5 per 1,000). Spot-check these pages against the scan: PDF 13, PDF 14, PDF 15, PDF 19, PDF 32, PDF 39, PDF 47, PDF 48. Misread words the AI could read from the scan are listed under "OCR words given their printed spelling"; other errors stay. Corrections to the text itself are an editorial decision.

### 6. OCR Words Given Their Printed Spelling (10 forms, 15 places)

The OCR misread these words, mostly letters with diacritics (ā or ū read as "ii"). The AI read each word from a crop of the scan. Screen readers now speak the printed spelling, and copying gives it (ActualText); the OCR text underneath is unchanged, so a text search still finds the OCR spelling. Apps that ignore ActualText (Preview and other PDFKit readers, some checkers) still show the OCR spelling. Check each reading against the scan on its first page.

| OCR text | Printed (AI's reading) | Places | First pages |
|---|---|---:|---|
| k'e | k’ê | 5 | PDF 39, PDF 40 |
| syiin | syūn | 2 | PDF 18, PDF 22 |
| syiing | syūng | 1 | PDF 18 |
| EXERCISES:t | EXERCISES‡ | 1 | PDF 22 |
| iian | üan | 1 | PDF 28 |
| iie | üe | 1 | PDF 28 |
| iin | ün | 1 | PDF 28 |
| h'i | bǐ | 1 | PDF 46 |
| m'i | mǐ | 1 | PDF 46 |
| liiyezi | lǜyèzi | 1 | PDF 48 |

- 30 suspect forms were checked by the AI; 20 were judged correct as the OCR read them, or unreadable (e.g. "Hawaii"), and left alone.

### 7. Hidden from Screen Readers (artifacts)

- 49 decorative elements ("page scan PDF 1", "page scan PDF 10", "page scan PDF 11", "page scan PDF 12", "page scan PDF 13", "page scan PDF 14", "page scan PDF 15", "page scan PDF 16", "page scan PDF 17", "page scan PDF 18", "page scan PDF 19", "page scan PDF 2", "page scan PDF 20", "page scan PDF 21", "page scan PDF 22", "page scan PDF 23", "page scan PDF 24", "page scan PDF 25", "page scan PDF 26", "page scan PDF 27", "page scan PDF 28", "page scan PDF 29", "page scan PDF 3", "page scan PDF 30", "page scan PDF 31", "page scan PDF 32", "page scan PDF 33", "page scan PDF 34", "page scan PDF 35", "page scan PDF 36", "page scan PDF 37", "page scan PDF 38", "page scan PDF 39", "page scan PDF 4 (blank)", "page scan PDF 40", "page scan PDF 41", "page scan PDF 42", "page scan PDF 43", "page scan PDF 44", "page scan PDF 45", "page scan PDF 46", "page scan PDF 47", "page scan PDF 48", "page scan PDF 49", "page scan PDF 5", "page scan PDF 6", "page scan PDF 7", "page scan PDF 8", "page scan PDF 9") on PDF 1, PDF 2, PDF 3, PDF 4, PDF 5, PDF 6, PDF 7, PDF 8, PDF 9, PDF 10, PDF 11, PDF 12, PDF 13, PDF 14, PDF 15, PDF 16, PDF 17, PDF 18, PDF 19, PDF 20, PDF 21, PDF 22, PDF 23, PDF 24, PDF 25, PDF 26, PDF 27, PDF 28, PDF 29, PDF 30, PDF 31, PDF 32, PDF 33, PDF 34, PDF 35, PDF 36, PDF 37, PDF 38, PDF 39, PDF 40, PDF 41, PDF 42, PDF 43, PDF 44, PDF 45, PDF 46, PDF 47, PDF 48, PDF 49
- "running head (first half)": text matching `Comparison of Yale and Pinyin Romanizations|Comparison of Pinyin and Wade-Giles Romanizations|Chinese Romanization Self-Study Guide` on PDF 11–26
- "running head (second half)": text matching `Comparison of Yale and Pinyin Romanizations|Comparison of Pinyin and Wade-Giles Romanizations|Chinese Romanization Self-Study Guide` on PDF 28–49

### 8. Fonts

- **HiddenHorzOCR** (fixed by the pipeline): the invisible OCR layer of the scanned pages used a font whose program held only `.notdef`. Its program was swapped for a blank one in which every character is a defined, empty glyph of the same width (2 font objects, 12 glyph references on 2 pages). Same character codes, same ToUnicode map, same widths, still invisible; a replay of 2 pages showed none looking different and no text changed. The fix does not make the OCR text accurate: recognition errors stay, so spot-check the OCR text against the scan.

The pipeline changes no other font: it never embeds one, replaces a visible one, or rewrites text. These need a person:

- **Not embedded** (8): Helvetica, Helvetica-Bold, Helvetica-BoldOblique, Helvetica-Oblique, Times-Bold, Times-BoldItalic, Times-Italic, Times-Roman. PDF/UA requires embedded fonts (7.21.4.1); a person must embed them with a PDF tool (e.g. Acrobat Preflight) and check that no page changes.
- **No ToUnicode map** (8): Helvetica, Helvetica-Bold, Helvetica-BoldOblique, Helvetica-Oblique, Times-Bold, Times-BoldItalic, Times-Italic, Times-Roman. Text in these fonts may not be read correctly; a map can only be added where every character code's meaning is certain.

### 9. One-item Lists Turned Into Paragraphs by Rule (38)

A list with one item whose label is not a list marker (the auto-tagger took a paragraph's first word or a year for a label) was made one paragraph, label and text together. Listen to a few; a real one-item list can be kept with `keep_lists`.

- PDF 13: label "m": "m min ming mou"
- PDF 13: label "f": "f fou"
- PDF 14: label "t": "t ting tou"
- PDF 14: label "n": "n nin ning nou lin ling lou"
- PDF 15: label "Exercise 4A.": "Exercise 4A. Give PY equivalents for the following YR syllables: a b c d e f"
- PDF 16: label "Exercise 5": "Exercise 5B. PY: ao mao dao kao shao YR:"
- PDF 16: label "Exercise 6": "Exercise 6A. YR: gung nung dzung jung chung PY:"
- PDF 17: label "Exercise 9A": "Exercise 9A."
- PDF 18: label "Exercise 9B": "Exercise 9B. PY: jia qian xiang qiao xie jiong YR:"
- PDF 18: label "Exercise 1": "Exercise 1 lA. YR: ywe jywe syiin jywan chyun lywe PY: - --"
- PDF 18: label "Exercise 1": "Exercise 1 lB. PY: XU nue lil jun quan que qu YR:"
- PDF 20: label "Exercise 12": "Exercise 12. Review of Finals Comparison."
- PDF 20: label "Exercise 12A.": "Exercise 12A. Give the PY equivalents for the following YR syl-lables:"
- PDF 21: label "Exercise 12B.": "Exercise 12B. Give the YR equivalents for the following PY syl-lables:"
- PDF 22: label "Exercise 13": "Exercise 13B. Rewrite the following, PY to YR: a b c d e f"
- PDF 23: label "Exercise 2": "Exercise 2B. YR: ja che shou reng jou chang shai ran"
- PDF 24: label "Exercise 9": "Exercise 9A."
- PDF 25: label "Exercise 9": "Exercise 9B. YR: jya chyan syang chyau sye jyung"
- PDF 25: label "Exercise 1 0": "Exercise 1 0A. PY: qiu diu jiu niu"
- PDF 25: label "Exercise 1": "Exercise 1 lA. PY: yue jue xun juan qun Hie lil"
- PDF 25: label "Exercise 1": "Exercise 1 lB. YR: syu nywe lyujyun chywan chywe chyu"
- PDF 31: label "Exercise 4A": "Exercise 4A. PY: zang cou"
- PDF 32: label "Exercise 4B": "Exercise 4B."
- PDF 32: label "5": "5. Comparative Table of PY and WG Initials. PY: b p m f"
- PDF 32: label "Exercise 5": "Exercise 5. Review of Initials Comparison."
- PDF 33: label "Exercise 5": "Exercise 5B. Rewrite the following WG syllables into PY equiva-lents."
- PDF 36: label "Exercise 1": "Exercise 1 lA. PY: mie tie qie nie WG:"
- PDF 36: label "Exercise 1": "Exercise 1 lB."
- PDF 39: label "Exercise 14": "Exercise 14. Review of Finals Comparison. Exercise 14A. Rewrite the following PY syllables into WG"
- PDF 39: label "Exercise 14": "Exercise 14B. Rewrite the following WG syllables into PY equiv alents."
- PDF 40: label "Exercise 15": "Exercise 15A. PY: chang ger pibaor xiaoshuor fengr WG:"
- PDF 40: label "Exercise 15": "Exercise 15B. WG: hsiao3 t'u4-erh PY:"
- PDF 42: label "Exercise 16": "Exercise 16A. Rewrite the following PY syllables into WG equiv-alents."
- PDF 42: label "Exercise 16": "Exercise 16B. Rewrite the following WG syllables into PY equiv-alents."
- PDF 43: label "Exercise 1 7": "Exercise 1 7 A. Rewrite the following PY combinations into WG equivalents."
- PDF 44: label "Exercise 1 7": "Exercise 1 7B. Rewrite the following WG words and combina tions into PY equivalents."
- PDF 47: label "Exercise 15A": "Exercise 15A. ch'ang4 ke1-erh p'i2-pao1-erh"
- PDF 48: label "Exercise 15B": "Exercise 15B. xiao tur haomar kour shengr"
- Not changed: PDF 13 "m": label or body holds tags of its own
- Not changed: PDF 34 "Exercise 6": label or body holds tags of its own
- Not changed: PDF 45 "Exercise 2": label or body holds tags of its own
- Not changed: PDF 46 "Exercise 6": label or body holds tags of its own

### 10. Empty Tags (9 removed, 0 kept)

A tag is removed only when proven empty: nothing under it holds content, it carries no Alt, ActualText, E or ID, and nothing in the file refers to it except its parent. Table cells are never removed one by one; a table goes only when every part is empty.

- Removed: 9 P
- 9 of them were empty parts of tables or lists the work order flattened (e.g. cells whose content had been hidden as decoration)

### 11. veraPDF (WCAG 2.2 machine profile), Before and After

veraPDF 1.30.3, profile "WCAG 2.2 machine validation profile" (7da399cf5baa). Counts are failed checks; pages are from the first checks veraPDF lists for each rule, so a rule may fail on more pages. Rules that only PDF/UA requires are listed apart and do not count. "Who fixes" is who can act on the rule: the pipeline by itself, the AI through the work order, or only a person. **Newly failing** means this run broke something the original passed. Before: 4 rules failing (the AI can act on 1, the pipeline on 3, only a person on 0). After: 0.

| Rule | WCAG | What it checks | Who fixes | Before | After | Status | Pages (after, else before) |
|---|---|---|---|---:|---:|---|---|
| ISO 14289-1 7.3-1 | 1.1.1 | Figure tags shall include an alternative representation or replacement text that represents the contents marked with the Figure tag as noted in ISO 32000-1:2008, 14.7.2, Table 323 | the AI (`alt`) | 53 | 0 | fixed | PDF 1, PDF 2, PDF 3, PDF 4, PDF 5, PDF 6, PDF 7, PDF 8, PDF 9, PDF 10, PDF 11, PDF 12, PDF 13, PDF 14, PDF 15, PDF 16, PDF 17, PDF 18 |
| ISO 14289-1 7.21.8-1 | 1.3.1 | A PDF/UA compliant document shall not contain a reference to the .notdef glyph from any of the text showing operators, regardless of text rendering mode, in any content stream | the pipeline | 12 | 0 | fixed | PDF 6, PDF 40 |
| ISO 14289-1 6.2-1 | 1.3.1 | The document catalog dictionary shall include a MarkInfo dictionary containing an entry, Marked, whose value shall be true | the pipeline (1 changed) | 1 | 0 | fixed | page: not on this tag |
| ISO 14289-1 7.1-10 | 2.4.2 | The document catalog dictionary shall include a ViewerPreferences dictionary containing a DisplayDocTitle key, whose value shall be true | the pipeline (1 changed) | 1 | 0 | fixed | page: not on this tag |

### 12. WCAG Checks veraPDF Does Not Make

Each item is something to look at, not a proven failure.

- 1.3.2 the reading order jumps back up the same column on 3 pages. Listen through them with a screen reader (or the PAC screen-reader preview): PDF 12 (5 jumps), PDF 29 (2 jumps), PDF 31 (2 jumps)

### 13. Deferred by the AI

- **Contents pages: entries are tagged as nested lists plus mis-tagged headings, with page numbers split into separate lists**: A TOC/TOCI rebuild cannot be targeted safely from the digest; a person should check the structure [PDF 7, PDF 8]
- **Four tables on PDF 29 (printed 29): each column is one merged cell holding several rows of syllables**: Header row and header column are set as far as possible, but the grid itself needs re-tagging by a person [PDF 29]
- **Syllable charts on PDF 12–14 (printed 12–14) and PDF 41 (printed 41) are tagged as lists or flattened to paragraphs**: They are really tables; a person should re-tag them [PDF 12, PDF 13, PDF 14, PDF 41]
- **Printed page numbers (bottom of each page) and footnotes (PDF 12, 19, 25, 28, 34, 43, 44) left as they are**: The page number sits outside the 60 pt bottom band and a text rule could also hit real content; footnotes are not in a Note style [PDF 12, PDF 19, PDF 25, PDF 28, PDF 34, PDF 43, PDF 44]
- **Section sub-headings (e.g. 'C. Finals', 'D. Terminal r-suffix', 'B. Comparison of Tones', 'C. Comparison of Initials', 'D. Comparison of Finals') sit inside list items and have no heading tag**: They cannot be pulled out of the list items with these keys [PDF 11, PDF 28, PDF 30, PDF 33]
- **Poor OCR text layer (about 52 suspect tokens per 1000), worst on PDF 32, 15, 13, 48, 14, 19, 39, 47; tables and exercise lines have scrambled order**: The text cannot be changed here; a person should check reading order and OCR errors, including the garbled contents-page and headings text [PDF 13, PDF 14, PDF 15, PDF 19, PDF 32, PDF 39, PDF 47, PDF 48]
- **veraPDF 7.3-1 (Figure alt) on the 49 full-page scan figures**: Handled by artifacting them (Layout); the OCR text layer carries the content. Only the four small figures get alt text [PDF 1, PDF 49]

Reviewer note from the AI: This is an OCRmyPDF scan with an automatic tag tree. Every page has a full-page Figure, which is the scan image itself, and these are artifacted. That includes the cover (PDF 1), whose title text is still in the OCR text layer, and the blank PDF 4. Headings were re-leveled per element: H1 is the cover title (PDF 1); the two chapters, Contents and Preface are H2; their numbered sections are H3; lettered subsections are H4. Running-head text is hidden by rule on PDF 11–26 and 28–49. The chapter-title pages (PDF 10, 27) are left alone. Printed page numbers are not artifacted; they sit outside the band. Only forms whose crop showed different letters are in ocr_words. Straight and curly apostrophes and the ʻokina were left as the OCR has them.

### 14. Deferred by the Executor

- text rule "running head (first half)" matched no text on PDF 11–26: nothing was hidden by this rule; check its pattern against the page (spacing, split runs)
- text rule "running head (second half)" matched no text on PDF 28–49: nothing was hidden by this rule; check its pattern against the page (spacing, split runs)

## What Was Changed

| Change | Count |
|---|---:|
| document: marked as tagged | 1 |
| document: DisplayDocTitle | 2 |
| artifact: "page scan PDF 1" | 1 |
| artifact: "page scan PDF 2" | 1 |
| artifact: "page scan PDF 3" | 1 |
| artifact: "page scan PDF 4 (blank)" | 1 |
| artifact: "page scan PDF 5" | 1 |
| artifact: "page scan PDF 6" | 1 |
| artifact: "page scan PDF 7" | 1 |
| artifact: "page scan PDF 8" | 1 |
| artifact: "page scan PDF 9" | 1 |
| artifact: "page scan PDF 10" | 1 |
| artifact: "page scan PDF 11" | 1 |
| artifact: "page scan PDF 12" | 1 |
| artifact: "page scan PDF 13" | 1 |
| artifact: "page scan PDF 14" | 1 |
| artifact: "page scan PDF 15" | 1 |
| artifact: "page scan PDF 16" | 1 |
| artifact: "page scan PDF 17" | 1 |
| artifact: "page scan PDF 18" | 1 |
| artifact: "page scan PDF 19" | 1 |
| artifact: "page scan PDF 20" | 1 |
| artifact: "page scan PDF 21" | 1 |
| artifact: "page scan PDF 22" | 1 |
| artifact: "page scan PDF 23" | 1 |
| artifact: "page scan PDF 24" | 1 |
| artifact: "page scan PDF 25" | 1 |
| artifact: "page scan PDF 26" | 1 |
| artifact: "page scan PDF 27" | 1 |
| artifact: "page scan PDF 28" | 1 |
| artifact: "page scan PDF 29" | 1 |
| artifact: "page scan PDF 30" | 1 |
| artifact: "page scan PDF 31" | 1 |
| artifact: "page scan PDF 32" | 1 |
| artifact: "page scan PDF 33" | 1 |
| artifact: "page scan PDF 34" | 1 |
| artifact: "page scan PDF 35" | 1 |
| artifact: "page scan PDF 36" | 1 |
| artifact: "page scan PDF 37" | 1 |
| artifact: "page scan PDF 38" | 1 |
| artifact: "page scan PDF 39" | 1 |
| artifact: "page scan PDF 40" | 1 |
| artifact: "page scan PDF 41" | 1 |
| artifact: "page scan PDF 42" | 1 |
| artifact: "page scan PDF 43" | 1 |
| artifact: "page scan PDF 44" | 1 |
| artifact: "page scan PDF 45" | 1 |
| artifact: "page scan PDF 46" | 1 |
| artifact: "page scan PDF 47" | 1 |
| artifact: "page scan PDF 48" | 1 |
| artifact: "page scan PDF 49" | 1 |
| document: title | 1 |
| document: /Lang | 1 |
| OCR words: printed spelling given as ActualText | 15 |
| retype → P | 14 |
| retype → H2 | 3 |
| retype → H3 | 9 |
| retype → H4 | 4 |
| one-item list → paragraph (rule) | 38 |
| flatten: false list → paragraphs | 47 |
| flatten: nested list/table already flattened with its parent | 7 |
| table: header cells marked (work order) | 4 |
| table: cells wrongly tagged as headers set back to data cells | 4 |
| figure: alt text | 4 |
| structure: empty tag removed (proven empty) | 9 |
| bookmarks: built from heading tags | 22 |
| fonts: invisible OCR-layer font given defined blank glyphs | 2 |

## Accessibility Evaluation

A person evaluates this version of `romanization-ocr_remediated.pdf` with PAC 2026 and a screen reader, on the app's "Accessibility Evaluation" page (or with manual_checks.py; docs/release.md). The "Ready to ship?" answer needs both parts. A Fail is recorded with its note and does not hold the book back. Each result is recorded against this version of the PDF (its sha256): after a new apply it no longer counts. The evaluation is a record of what a person found, not a legal certification.

**PAC 2026.** Open `romanization-ocr_remediated.pdf` in PAC 2026 (https://pac.pdf-accessibility.org/en, Windows) and run its WCAG check. Anything it fails that is not listed above is a gap in the automated checks: note it in the issue tracker. Each item is Pass, Fail or Not Applicable, with notes:

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
