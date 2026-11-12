# Remediation Review: moralfoods.pdf

Result: `moralfoods_remediated.pdf`

361 pages · run November 11, 2026, at 6:34 PM · model `anthropic/claude-sonnet-5.5` · prompt `workorder_v10.md` (15b5aa0ade9c6549) · AI cost $0.240 ($0.0007 per page), from the original AI request on November 3, 2026 · this run: no new AI request · tokens: saved reply reused, not counted

Intake: none (already tagged)

Libraries: python 3.13.9 · pikepdf 10.5.1 · pdfplumber 0.11.9 · pypdfium2 5.7.1 · pillow 13.0.0 · fonttools 4.62.1

Time: intake 1.0s · audit 48.6s · reuse saved reply 1.4s · apply 177.4s · verify 58.5s · total 286.9s

## Overview

[Open the dashboard](review.html)

**Status:** Not Ready

**Ready to ship?**
- Work Order Approval: Not Approved (applied without a review)
- ✓ OCR Text Approval: Not Applicable
- Safety Checks: Failed (all content tagged or decoration)
- Accessibility Evaluation: Not Completed

**Safety checks:** OK ✔ pages look the same · OK ✔ text unchanged · FAILED ✘ all content tagged or decoration · OK ✔ tag-tree index points into the tree · OK ✔ every font readable  
**Needs a person:** 18 (6 deferred by the AI · 5 deferred by the executor · 7 CHECK rows)  
**AI decisions:** 74 in the work order, applied without review by a person  
**Fixed automatically (no AI):** links tied and described 2,963 · note IDs 838 · decorative lines marked 12 · link descriptions that were only a URL 7 · empty tags removed 7 · marked as tagged 1 · title shown in the window 1 · whole-page figures wrapped 1 · tag-tree index entries 1 · pages given tab order 1  
**veraPDF (WCAG 2.2 machine checks):** 4 WCAG rules failing before (3,172 checks) → 1 after (260 checks) · 0 newly failing

Automated checks are evidence, not sign-off.

| Top issues | Pages | Where |
|---|---|---|
| All content tagged or marked as decoration: 1526 untagged characters · 260 untagged objects (258 text, 2 image) | see Automated Checks | [Automated Checks](#automated-checks) |
| Page-level figure wrap: PDF 1 (printed COVER) wrapped as one Figure · not wrapped: PDF 5 (printed iv) (has 2 annotation(s) (links)) | PDF 1 (printed COVER), PDF 5 (printed iv) | [Automated Checks](#automated-checks) |
| Empty tags removed when proven empty: 7 removed · 1 kept: something refers to them or they carry an attribute (listed) | see §10 | [§10](#10-empty-tags-7-removed-1-kept) |
| No empty tags: 1 empty tag (page: not on this tag) | see §10 | [§10](#10-empty-tags-7-removed-1-kept) |
| No link whose only text is a URL: 2: PDF 5 (printed iv) | PDF 5 (printed iv) | [§9](#9-links-whose-description-was-only-a-url-9-and-1-address-that-looks-broken) |
| … and 13 more | | §12, §14, §15, §16 |

Automated checks are evidence, not legal sign-off. Items marked **CHECK**, and everything under "For a person to check", need a human.

## Automated Checks

| Check | Result | Detail |
|---|---|---|
| Every page looks the same as the original | OK | 0 pages differ |
| Published text unchanged | OK | 0 pages changed |
| All content tagged or marked as decoration | **CHECK** | 1526 untagged characters · 260 untagged objects (258 text, 2 image) |
| Untagged paths: none left | OK | 0 untagged paths · 12 rules, borders and lines marked as decoration by this run |
| Invisible OCR text: every glyph defined | OK | no undefined glyphs in invisible text |
| Page-level figure wrap | **CHECK** | PDF 1 (printed COVER) wrapped as one Figure · not wrapped: PDF 5 (printed iv) (has 2 annotation(s) (links)) |
| Empty tags removed when proven empty | **CHECK** | 7 removed · 1 kept: something refers to them or they carry an attribute (listed) |
| Tag-tree index points only into the tree | OK | 0 dangling entries · 1 stale entries (marked content no longer drawn) |
| No empty tables | OK | none |
| No empty tags | **CHECK** | 1 empty tag (page: not on this tag) |
| No paragraph holding only figures | OK | none |
| Every caption grouped with its figure | OK | all grouped |
| No link whose only text is a URL | **CHECK** | 2: PDF 5 (printed iv) |
| Tag tree consistent | OK | 0 missing · 0 mismatched |
| All marked text reachable from the tag tree | OK | 0 orphan runs |
| One Document root | OK | Document 1 |
| Every link tied to its text and described | OK | 0 unresolved · 0 without description · 0 pointing to no annotation |
| No link nested inside another | OK | 0 |
| Headings: no skipped levels | OK | H1 1 · H2 22 · H3 76 · H4 8 |
| Headings: exactly one H1 (the title) | OK | 1 H1 (several H1s usually mean parts or chapters were not demoted) |
| Figures: none with empty or placeholder alt | OK | 8 figures, 0 placeholder |
| Every Note has a unique ID | OK | 838 notes · 0 without ID · 0 duplicate · 0 not in the ID tree |
| Bookmarks present (documents over 9 pages) | OK | 27 bookmarks |
| Model reply held one work order | OK | one |
| Executor applied every decision | **CHECK** | 1 rejected · 0 failed (listed under "Decisions not applied") |
| Nothing deferred by the executor | **CHECK** | 6 deferred (listed under "Deferred by the executor") |
| Fonts: every glyph defined (no .notdef) | OK | none found |
| Fonts: every embedded font program could be read | OK | all read |
| Fonts: embedded and mapped to Unicode | OK | 0 not embedded · 0 without ToUnicode (3 more have none and need none: standard encoding, non-symbolic) |
| Tab order follows the tag structure on pages with links or other annotations | OK | 0 of 238 pages with annotations lack /Tabs /S (log: 1 set by this run) |
| Characters with no Unicode value (checklist 3.6) | OK | 0 read-aloud characters with no Unicode value |
| Private-use characters (checklist 3.6) | OK | 0 read-aloud characters with private-use codes |
| Title and language set | OK | "Moral Foods: The Construction of Nutrition and Health in Modern Asia" · en-US |
| veraPDF WCAG 2.2 (machine): no WCAG failures | **CHECK** | before: 4 WCAG rules failed (3172 checks) → after: 1 WCAG rule failed (260 checks) (listed under "veraPDF") |
| veraPDF: no rule newly failing or failing more often | OK | 3 fixed · 1 still failing · 0 newly failing |
| Alt text: none like a file name or repeated on many figures (1.1.1) | OK | 0 of 8 figures flagged |
| Tables: every table has header cells (1.3.1) | OK | none without |
| Reading order: no page jumps back up a column (1.3.2) | OK | 0 of 304 pages flagged |
| Reading order: no section moved away from its printed place by this run (1.3.2) | OK | 0 new · 6 already in the original, of 20 sections and blocks |
| Title is not a file name or placeholder (2.4.2) | OK | "Moral Foods: The Construction of Nutrition and Health in Modern Asia" |
| Link text: none like "click here" (2.4.4) | OK | 0 generic |
| Headings: none empty, very long or repeated in a row (2.4.6) | OK | 0 empty · 0 long · 0 repeated |

## For a Person to Check

### 1. Pages Wrapped as One Figure (1)

Pages with nothing tagged and nothing marked as decoration that hold a drawing (a full-page map, plate or cover). Each page was wrapped whole in one Figure; nothing on it was changed or removed.

- PDF 1 (printed COVER): read first in the document. Alt text from the AI: "Front cover of Moral Foods: The Construction of Nutrition and Health in Modern Asia, edited by Angela Ki Che Leung and Melissa L. Caldwell. On a dark background, one photograph shows a green rice plant with grain heads and the other a bowl of white cooked rice sprinkled with seeds. The title appears in large yellow-green capitals, with the subtitle in pale yellow."
- PDF 5 (printed iv): not wrapped, left as it is (has 2 annotation(s) (links)).

### 2. Alt Text Written or Changed by the AI (7)

| Page | Before | After |
|---|---|---|
| PDF 106 (printed 93) | Map of China in the 1940s showing Japanese-occupied areas. Source: GIS Center, Academia Sinica, Taipei, Taiwan. | Map of China in the 1940s showing Japanese-occupied areas. The occupied areas, shaded gray, cover the northeast and the eastern provinces from Rehe and Liaoning south through Hebei, Shanxi, Shandong, Jiangsu and Anhui to Zhejiang. Korea and Taiwan are shown in black as Japanese colonies. Shanghai on the east coast and the wartime capital Chongqing in the interior are labelled, and darker areas along the southern and western borders (India, Burma, Indochina) are territories under western powers. The legend also marks railroads, Great Walls, and lakes and rivers. |
| PDF 155 (printed 142) | Annual consumption (per capita) of rice, wheat, and barley in South Korea, 1970–2016. Drawn by the author, based on the statistics from “Grain Consumption, per Capita, per Year, 1963–2016,” Korean Statistical Information Service, http://kosis.kr. | Line chart of annual per capita grain consumption in South Korea, 1970–2016. Rice falls steadily from 136.4 to 71.2. Wheat stays roughly level between about 26 and 35, ending at 35.0. Barley drops from about 37 in the early 1970s to 1.3 by 2016. |
| PDF 202 (printed 189) | “Central Market, Hong Kong; Retail Stores, Ground Floor,” 1895. The National Archives of the UK (TNA): Public Record Office (PRO), Kew, Colonial Office Records (CO), Series 1069/446 (28). | Black-and-white 1895 photograph of the upper floor of Central Market, City of Victoria, Hong Kong: a long, empty hall under an exposed iron-truss roof, with rows of wooden stalls and benches along both sides of a central aisle. |
| PDF 204 (printed 191) | “Cattle Slaughter House Interior, Hong Kong,” 1894. The National Archives of the UK (TNA): Public Record Office (PRO), Kew, Colonial Office Records (CO), Series 1069/446 (23). | Black-and-white 1894 photograph of the interior of the cattle slaughterhouse in the City of Victoria, Hong Kong: an empty room with a wet concrete floor, iron roof trusses, supporting columns and winch wheels along the back wall. |
| PDF 276 (printed 263) | The Chinese Food Pagoda, 2016. The left side of the pagoda’s second-highest tier represents dairy products. Used with permission from Chinese Nutrition Society, 2016 Dietary Guideline for Chinese (Zhongguo jumin shanshi zhinan 2016) (Beijing: People’s Medical Publishing House, 2016). | The Chinese Food Pagoda (2016), titled in Chinese, “Balanced Diet Pagoda for Chinese Residents.” It is a five-tier pagoda: grains and starchy foods at the base, then vegetables and fruit, fish, meat and eggs, and dairy products with soy on the second-highest tier, and a measuring cup and spoon at the top. A jogger and a glass of water appear beside it, with a note to walk 6,000 steps a day. |
| PDF 286 (printed 273) | The Food Guide Pyramid of the United States Department of Agriculture, 1992. Dairy products are located on the left-hand side of the second-highest tier, just as in the later Chinese food pagoda. Courtesy of the U.S. Department of Agriculture. | The U.S. Department of Agriculture Food Guide Pyramid, 1992, “A Guide to Daily Food Choices.” At the base is the bread, cereal, rice and pasta group (6–11 servings). Above it are vegetables (3–5 servings) and fruit (2–4 servings). Higher up are the milk, yogurt and cheese group (2–3 servings) beside the meat, poultry, fish, dry beans, eggs and nuts group (2–3 servings). The small tip is fats, oils and sweets, to be used sparingly. |
| PDF 293 (printed 280) | 2016 Balanced Diet Plate for Chinese. Used with permission from Chinese Nutrition Society, 2016 Dietary Guideline for Chinese (Zhongguo jumin shanshi zhinan 2016) (Beijing: People’s Medical Publishing House, 2016). | The 2016 Balanced Diet Plate for Chinese residents, with Chinese labels. A round plate is divided into four sections: cereals and tubers (largest), vegetables, fruit, and fish, meat, eggs and beans. A cup labelled for milk sits beside the plate, with chopsticks and a spoon. |

### 3. Headings

Heading levels by style (as applied):

| Style | Level | How | Elements |
|---|---|---|---:|
| TPHT | P | RoleMap | 2 |
| TPT | H1 | RoleMap | 1 |
| TPST | P | RoleMap | 1 |
| FMH | H2 | RoleMap | 2 |
| BMH | H2 | RoleMap | 4 |
| CT | H2 | RoleMap | 13 |
| CST | P | RoleMap | 13 |
| PN | P | RoleMap | 3 |
| PT | H2 | RoleMap | 3 |
| _H1_ | H3 | RoleMap | 63 |
| ENH | H3 | RoleMap | 13 |
| H2 | H4 | retype (standard tag) | 8 |

Merged: `TPST` into the prev `TPT`; `CST` into the prev `CT`; `PN` into the next `PT`

Spoken text set by the AI (should match what is printed):

| Page | Text |
|---|---|
| PDF 4 (printed iii) | Moral Foods THE CONSTRUCTION OF NUTRITION AND HEALTH IN MODERN ASIA |
| PDF 6 (printed v) | Acknowledgments ix |
| PDF 8 (printed vii) | Glossary 285 |
| PDF 8 (printed vii) | Bibliography 293 |
| PDF 8 (printed vii) | Index 335 |
| PDF 14 (printed 1) | Introduction Food and Health: Fortification and Modern Asian State Making |
| PDF 34 (printed 21) | Part I GOOD FOODS |
| PDF 36 (printed 23) | 1 Health, Wealth, and Solidarity Rice as Self in Japan and Malaysia |
| PDF 60 (printed 47) | 2 Confronting the Cow Soybean Milk and the Fashioning of a Chinese Dairy Alternative |
| PDF 79 (printed 66) | 3 Moral Responsibility for Nutritional Milk Motherhood and Breastfeeding in Modern Japan |
| PDF 102 (printed 89) | 4 Eating Well for Survival Chinese Nutrition Experiments during World War II |
| PDF 122 (printed 109) | Part II BAD FOODS |
| PDF 124 (printed 111) | 5 The Good, the Bad, and the Toxic Moral Foods in British India |
| PDF 143 (printed 130) | 6 The Good, the Bad, and the Foreign Trajectories of Three Grains in Modern South Korea |
| PDF 163 (printed 150) | 7 Snacking, Health, Modernity Moralizing Confections in Japan, 1890–1930 |
| PDF 186 (printed 173) | 8 Bad Meat Food and the Medicine of Modern Hygiene in Colonial Hong Kong |
| PDF 212 (printed 199) | Part III MORAL FOODS |
| PDF 214 (printed 201) | 9 Becoming Healthy Changing Perception of Tea’s Effects on the Body |
| PDF 234 (printed 221) | 10 To Build or to Transform Vegetarian China Two Republican Projects |
| PDF 254 (printed 241) | 11 From Civilizing Foods for Nourishing Life to a Global Traditional Chinese Medicine Dietetics Changing Perceptions of Foods in Chinese Medicine |
| PDF 275 (printed 262) | 12 Good Food, Bad Bodies Lactose Intolerance and the Rise of Milk Culture in China |

### 4. Text a Screen Reader Could Not Reach (before this run)

1 pages had text outside the tag tree: 0 orphan runs (marked, but no tag owns them) and 26 untagged runs. Running heads and page numbers among them can be hidden as decoration; real content must be added to the tag tree by a person. After this run: 1526 untagged characters, 0 orphan runs remain.

Pages: PDF 5 (printed iv)

### 5. Hidden from Screen Readers (artifacts)

- "running head (Contents)": text matching `(vi Contents|Contents vii)` on PDF 7–8 (printed vi–vii)
- "running head (Introduction)": text matching `(2 Introduction|Caldwell and Leung 3)` on PDF 15–16 (printed 2–3)
- "running head (Index)": text matching `(336 Index|Index 337)` on PDF 349–350 (printed 336–337)
- "folio v": text matching `v` on PDF 6 (printed v)
- "folio 1": text matching `1` on PDF 14 (printed 1)
- "folio 66": text matching `66` on PDF 79 (printed 66)
- "folio 335": text matching `335` on PDF 348 (printed 335)

### 6. Untagged Paths (rules, borders, lines)

12 paths drawn outside any tag were marked as decoration: none of them carries text, an image or a link, and none touches untagged text or images.

### 7. Untagged Content (260 objects)

Drawn content that is neither tagged nor marked as decoration (content reused on several pages counts once). Not changed by the pipeline; a person decides whether each is real content (tag it) or decoration (artifact it). Pages with the most:

- PDF 5 (printed iv): 258 text, 2 image

### 8. Spoken Text (ActualText) Checked Against the Print (18 accepted with differences, 0 rejected)

A spoken text may differ from the printed characters only in spacing, letter case and line-end hyphens (sponsor rule 1). Accepted ones that differ are listed so a person can listen to them; rejected ones added or changed words or punctuation.

- Accepted, PDF 4 (printed iii): printed "Moral Foods THE CONSTRUCTION OF NUTRITION AND HEALTH IN MODERN ASIA" → spoken "Moral Foods THE CONSTRUCTION OF NUTRITION AND HEALTH IN MODERN ASIA"
- Accepted, PDF 6 (printed v): printed "Acknowl edgments ix" → spoken "Acknowledgments ix"
- Accepted, PDF 14 (printed 1): printed "Introduction Food and Health: Fortification and Modern Asian State Making" → spoken "Introduction Food and Health: Fortification and Modern Asian State Making"
- Accepted, PDF 34 (printed 21): printed "Part I GOOD FOODS" → spoken "Part I GOOD FOODS"
- Accepted, PDF 36 (printed 23): printed "1 Health, Wealth, and Solidarity Rice as Self in Japan and Malaysia" → spoken "1 Health, Wealth, and Solidarity Rice as Self in Japan and Malaysia"
- Accepted, PDF 60 (printed 47): printed "2 Confronting the Cow Soybean Milk and the Fashioning of a Chinese Dairy Alternative" → spoken "2 Confronting the Cow Soybean Milk and the Fashioning of a Chinese Dairy Alternative"
- Accepted, PDF 79 (printed 66): printed "3 Moral Responsibility for Nutritional Milk Motherhood and Breastfeeding in Modern Japan" → spoken "3 Moral Responsibility for Nutritional Milk Motherhood and Breastfeeding in Modern Japan"
- Accepted, PDF 102 (printed 89): printed "4 Eating Well for Survival Chinese Nutrition Experiments during World War II" → spoken "4 Eating Well for Survival Chinese Nutrition Experiments during World War II"
- Accepted, PDF 122 (printed 109): printed "Part II BAD FOODS" → spoken "Part II BAD FOODS"
- Accepted, PDF 124 (printed 111): printed "5 The Good, the Bad, and the Toxic Moral Foods in British India" → spoken "5 The Good, the Bad, and the Toxic Moral Foods in British India"
- Accepted, PDF 143 (printed 130): printed "6 The Good, the Bad, and the Foreign Trajectories of Three Grains in Modern South Korea" → spoken "6 The Good, the Bad, and the Foreign Trajectories of Three Grains in Modern South Korea"
- Accepted, PDF 163 (printed 150): printed "7 Snacking, Health, Modernity Moralizing Confections in Japan, 1890–1930" → spoken "7 Snacking, Health, Modernity Moralizing Confections in Japan, 1890–1930"
- Accepted, PDF 186 (printed 173): printed "8 Bad Meat Food and the Medicine of Modern Hygiene in Colonial Hong Kong" → spoken "8 Bad Meat Food and the Medicine of Modern Hygiene in Colonial Hong Kong"
- Accepted, PDF 212 (printed 199): printed "Part III MORAL FOODS" → spoken "Part III MORAL FOODS"
- Accepted, PDF 214 (printed 201): printed "9 Becoming Healthy Changing Perception of Tea’s Effects on the Body" → spoken "9 Becoming Healthy Changing Perception of Tea’s Effects on the Body"
- Accepted, PDF 234 (printed 221): printed "10 To Build or to Transform Vegetarian China Two Republican Projects" → spoken "10 To Build or to Transform Vegetarian China Two Republican Projects"
- Accepted, PDF 254 (printed 241): printed "11 From Civilizing Foods for Nourishing Life to a Global Traditional Chinese Medicine Dietetics…" → spoken "11 From Civilizing Foods for Nourishing Life to a Global Traditional Chinese Medicine Dietetics Changing Perceptions of Foods in Chinese Medicine"
- Accepted, PDF 275 (printed 262): printed "12 Good Food, Bad Bodies Lactose Intolerance and the Rise of Milk Culture in China" → spoken "12 Good Food, Bad Bodies Lactose Intolerance and the Rise of Milk Culture in China"

### 9. Links Whose Description Was Only a URL (9, and 1 address that looks broken)

The description (what a screen reader announces) was set to the book's own sentence around the link, with the URL removed. No words were added and the visible URL is unchanged. Replace any of these with a better description if needed.

| Page | URL | Description now |
|---|---|---|
| PDF 5 (printed iv) | http://www.knowledgeunlatched.org | **still the URL: the URL was not found in the text around the link** |
| PDF 5 (printed iv) | https://creativecommons.org/licenses/by-nc-nd/4.0/ | **still the URL: the URL was not found in the text around the link** |
| PDF 101 (printed 88) | http://www.mhlw.go.jp. | Ministry of Health, Labour, and Welfare, accessed April 1, 2017,4 Eating Well for SurvivalChinese Nutrition Experiments during World War IIMichael Shiyung LiuWar has an enormous impact on human health. |
| PDF 231 (printed 218) | http://www.telegraph.co.uk | For example, see Luisa Dillner, “Is Drinking Tea Bad for You?” Guardian, April 1, 2013, “Tea: Is It Good or Bad for You?” Telegraph, June 18, 2010,5. |
| PDF 233 (printed 220) | http://www.cbc.ca | Megan Griffith-Greene, “Pesticide Traces in Some Tea Exceed Allowable Limits,” CBC News, March 8, 2014,10 To Build or to Transform Vegetarian ChinaTwo Republican ProjectsAngela Ki Che LeungMeat avoidance had an important place in Chinese dietary prac-tices, not only as a Buddhist food taboo but also as a popular food ritual.1 It was ambiguous in the dietetic tradition of the literati elite, often called “life-nurturing” (yangsheng) practices, for the maintenance of the individual’s somatic vitality, intellectual acuity, and spiritual fulfilment. |
| PDF 274 (printed 261) | http://www.nobelprize.org | “Youyou Tu—Facts,” Nobelprize.org, accessed December 9, 2015,35. |
| PDF 293 (printed 280) | http://news.xinhuanet.com | Zhao Cheng and Huang Huo, “Wen Jiabao Chongqing kaocha: Rang meige Zhongguoren mei tian he shang yi jin nai,” Xinhua, April 24, 2006,2. |
| PDF 293 (printed 280) | http://www.cnsoc.org | Hexin tuijian ji zhaiyao,” Chinese Nutrition Society, accessed September 26, 2016,3. |
| PDF 343 (printed 330) | http://www.cnsoc.org | Chinese Nutrition Society, accessed September 26, 2016. |

Link addresses that look broken (listed, not changed):

- PDF 101 (printed 88): `http://www.mhlw.go.jp.`: the address ends with punctuation or an unmatched closing bracket from the printed text; probably broken

### 10. Empty Tags (7 removed, 1 kept)

A tag is removed only when proven empty: nothing under it holds content, it carries no Alt, ActualText, E or ID, and nothing in the file refers to it except its parent. Table cells are never removed one by one; a table goes only when every part is empty.

- Removed: 4 TNI, 3 P
- **Kept, empty: Note (page: not on this tag)**, because carries /ID "note-0838"; IDTree "note-0838".

### 11. Structure Left for a Person

- 1 empty tag: Note (page: not on this tag)
- PDF 5 (printed iv): a link's description is only its URL (www.knowledgeunlatched.org)
- PDF 5 (printed iv): a link's description is only its URL (https://creativecommons.org/licenses/by-nc-nd/4.0/)

### 12. veraPDF (WCAG 2.2 machine profile), Before and After

veraPDF 1.30.3, profile "WCAG 2.2 machine validation profile" (7da399cf5baa). Counts are failed checks; pages are from the first checks veraPDF lists for each rule, so a rule may fail on more pages. Rules that only PDF/UA requires are listed apart and do not count. "Who fixes" is who can act on the rule: the pipeline by itself, the AI through the work order, or only a person. **Newly failing** means this run broke something the original passed. Before: 4 rules failing (the AI can act on 1, the pipeline on 3, only a person on 0). After: 1.

| Rule | WCAG | What it checks | Who fixes | Before | After | Status | Pages (after, else before) |
|---|---|---|---|---:|---:|---|---|
| ISO 14289-1 7.1-3 | 1.3.1 | Content shall be marked as Artifact or tagged as real content e.g. "Content is neither marked as Artifact nor tagged as real content" | the AI (`artifacts`) | 273 | 260 | still failing | PDF 5 (printed iv) |
| ISO 14289-1 7.18.5-1 | 2.4.4, 4.1.2 | Links shall be tagged according to ISO 32000-1:2008, 14.8.4.4.2, Link Element | the pipeline | 2897 | 0 | fixed | PDF 5 (printed iv), PDF 6 (printed v), PDF 8 (printed vii), PDF 14 (printed 1), PDF 15 (printed 2), PDF 16 (printed 3), PDF 17 (printed 4), PDF 18 (printed 5), PDF 19 (printed 6) |
| ISO 14289-1 6.2-1 | 1.3.1 | The document catalog dictionary shall include a MarkInfo dictionary containing an entry, Marked, whose value shall be true | the pipeline (1 changed) | 1 | 0 | fixed | page: not on this tag |
| ISO 14289-1 7.18.3-1 | 2.4.3 | Every page on which there is an annotation shall contain in its page dictionary the key Tabs, and its value shall be S | the pipeline (1 changed) | 1 | 0 | fixed | PDF 5 (printed iv) |

### 13. WCAG Checks veraPDF Does Not Make

Each item is something to look at, not a proven failure.

- 1.3.2 2 small sections are read more than 5 pages after their printed page, after a longer section that covers them. Not a failure (long stories overlap in InDesign books), but a screen reader hears them far from where they are printed: PDF 12 (printed xi) read after PDF 350 (printed 337); PDF 106 (printed 93) read after PDF 350 (printed 337)
- 1.3.2 6 sections read away from their printed place, as in the original (this run did not move them). Listen through each where it is read, or move it with move_section:
  - PDF 7 (printed vi): Story "vi Contents", read before PDF 2 (printed i)
  - PDF 8 (printed vii): Story "Contents vii", read before PDF 2 (printed i)
  - PDF 15 (printed 2): Story "2 Introduction", read before PDF 2 (printed i)
  - PDF 16 (printed 3): Story "Caldwell and Leung 3", read before PDF 2 (printed i)
  - PDF 349 (printed 336): Story "336 Index", read before PDF 2 (printed i)
  - PDF 350 (printed 337): Story "Index 337", read before PDF 2 (printed i)

### 14. Deferred by the AI

- **Page 5 (copyright, CIP data) is untagged text**: veraPDF 7.1-3: about 26 runs of real content are in no tag and not marked as artifact. A person must tag them as paragraphs in the source file; they cannot be artifacted. The other 7.1-3 failures are on cover page 1, which is handled by page_figures. [PDF 5 (printed iv)]
- **Chapter-opening paragraphs (style CO) have lost their drop-cap first letters in the text layer, e.g. “n today’s world” for “In today’s world”, “apan” for “Japan”, “ar” for “War”**: The text layer is incomplete and I cannot supply whole paragraphs as ActualText without changing the text. A person should check how the drop caps are tagged. [PDF 14 (printed 1), PDF 36 (printed 23), PDF 60 (printed 47), PDF 79 (printed 66), PDF 102 (printed 89), PDF 124 (printed 111), PDF 143 (printed 130), PDF 163 (printed 150), PDF 186 (printed 173), PDF 214 (printed 201), PDF 234 (printed 221), PDF 254 (printed 241), PDF 275 (printed 262)]
- **About 150 Korean (hangul) runs have no language tag**: The language key only offers kana → ja and per-run entries that need certain page and mcid values, which the digest does not give. A person should tag the hangul runs ko, mostly in the notes and bibliography of chapter 6 and the bibliography. [PDF 143 (printed 130), PDF 159 (printed 146), PDF 305 (printed 292), PDF 306 (printed 293), PDF 324 (printed 311), PDF 325 (printed 312)]
- **Han-only Chinese/Japanese runs (about 1,020, in the glossary, bibliography and notes)**: Han-only runs cannot be told apart as Chinese or Japanese; the executor sends them to a human. [PDF 298 (printed 285), PDF 299 (printed 286), PDF 300 (printed 287), PDF 301 (printed 288), PDF 302 (printed 289), PDF 303 (printed 290), PDF 304 (printed 291), PDF 305 (printed 292), PDF 306 (printed 293)]
- **Chapter-end endnotes are interleaved with the body, so sections.notes_pages is not set**: The Notes sections are scattered through the book, not one contiguous block. Each is headed H3 “Notes” and its paragraphs become Note elements. [PDF 28 (printed 15), PDF 297 (printed 284)]
- **Trailing PDF pages 357–361 have no tagged text**: They could be blank pages or advertisements or a back cover; the digest does not show their content. A person should check them. [PDF 357 (printed 344), PDF 358 (printed 345), PDF 359 (printed 346), PDF 360 (printed 347), PDF 361 (printed 348)]

Reviewer note from the AI: Heading plan: H1 is the book title (TPT merged with its subtitle TPST). H2 are part titles (“Part I GOOD FOODS” merged), chapter titles (number and title merged with subtitle), and Contents, Acknowledgments, Glossary, Bibliography, Contributors and Index. H3 are the _H1_ sections and the chapter “Notes” heads. H4 are the bold subsection heads (style H2). The half-title “Moral Foods” (TPHT) is demoted to P. Running heads and folios were found only as a handful of stray Story elements (RHR, RHV, DFOL), and I artifacted them page by page. The folio rules use the bottom band and exact pages so that note-reference numerals are not hit; the reviewer should confirm that they matched. The four actual_text entries on contents entries (12431 0, 12461 0, 12462 0, 12464 0) are guesses at the printed text; the executor may reject them. Figure alt text was rewritten because the publisher alts only repeated the captions; the captions are still tagged as Caption.

### 15. Deferred by the Executor

- **1020 Han-only CJK runs** need a Japanese / Chinese decision: fill in `han_review.csv`.
- text rule "running head (Contents)" matched no text on PDF 7–8 (printed vi–vii): nothing was hidden by this rule; check its pattern against the page (spacing, split runs)
- text rule "running head (Introduction)" matched no text on PDF 15–16 (printed 2–3): nothing was hidden by this rule; check its pattern against the page (spacing, split runs)
- text rule "running head (Index)" matched no text on PDF 349–350 (printed 336–337): nothing was hidden by this rule; check its pattern against the page (spacing, split runs)
- link on a page with no tagged text (PDF 5 (printed iv)): tied to tagged text on PDF 4 (printed iii)
- link on a page with no tagged text (PDF 5 (printed iv)): tied to tagged text on PDF 4 (printed iii)

### 16. Decisions Not Applied (1)

Rejected by validation or by the executor; nothing was half-applied.

- {"op": "figure order PDF 106 (printed 93)", "why": "no target block"}

## What Was Changed

| Change | Count |
|---|---:|
| document: marked as tagged | 1 |
| artifact: "folio v" | 1 |
| artifact: "folio 1" | 1 |
| artifact: "folio 66" | 1 |
| artifact: "folio 335" | 1 |
| document: title | 1 |
| document: DisplayDocTitle | 1 |
| document: /Lang | 1 |
| heading: RoleMap level | 10 |
| heading: merged into prev | 14 |
| heading: merged into next | 3 |
| heading: ActualText | 21 |
| heading: standard tag H2 → H4 (retyped) | 8 |
| figure: alt text | 7 |
| figure: caption tied (figure moved out of its paragraph) | 7 |
| contents: TOC entries | 34 |
| contents: TOC built | 1 |
| notes: Note with /ID | 838 |
| language: ja Span | 166 |
| language: ko Span | 150 |
| language: ja on existing Span | 1 |
| links: /Contents set | 2963 |
| links: new Link element created | 2894 |
| links: placed beside nearest text | 2 |
| links: joined existing Link | 69 |
| links: wraps its text | 854 |
| links: placed after shared text | 2038 |
| links: URL-only description replaced by the sentence around it | 7 |
| contents: entry wrapped in Reference | 34 |
| order: empty container removed | 4 |
| figure: whole page wrapped as one Figure | 1 |
| figure: alt text from the work order (page figure) | 1 |
| structure: empty tag removed (proven empty) | 7 |
| artifact: untagged path with no content (rule, border, line) | 12 |
| tag tree index: entries repaired | 1 |
| tab order: /Tabs /S set on pages with annotations | 1 |

## Accessibility Evaluation

A person evaluates this version of `moralfoods_remediated.pdf` with PAC 2026 and a screen reader, on the app's "Accessibility Evaluation" page (or with manual_checks.py; docs/release.md). The "Ready to ship?" answer needs both parts. A Fail is recorded with its note and does not hold the book back. Each result is recorded against this version of the PDF (its sha256): after a new apply it no longer counts. The evaluation is a record of what a person found, not a legal certification.

**PAC 2026.** Open `moralfoods_remediated.pdf` in PAC 2026 (https://pac.pdf-accessibility.org/en, Windows) and run its WCAG check. Anything it fails that is not listed above is a gap in the automated checks: note it in the issue tracker. Each item is Pass, Fail or Not Applicable, with notes:

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
