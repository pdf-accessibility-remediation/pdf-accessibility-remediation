# Remediation Review: moralfoods.pdf

Result: `moralfoods_remediated.pdf`

361 pages · run November 15, 2026, at 10:07 PM · model `anthropic/claude-sonnet-5.5` · prompt `workorder_v12.md` (762395b72330c407) · AI cost $0.214 ($0.0006 per page), from the original AI request on November 15, 2026 · this run: no new AI request · tokens: saved reply reused, not counted

Intake: none (already tagged)

Libraries: python 3.13.9 · pikepdf 10.5.1 · pdfplumber 0.11.9 · pypdfium2 5.7.1 · pillow 13.0.0 · fonttools 4.62.1

Time: intake 0.8s · audit 56.8s · reuse saved reply 1.6s · apply 194.8s · verify 62.2s · total 316.2s

## Overview

[Open the dashboard](review.html)

**Status:** Not Ready

**Ready to ship?**
- Work Order Approval: Not Approved (applied without a review)
- ✓ OCR Text Approval: Not Applicable
- Safety Checks: Failed (all content tagged or decoration)
- Language Tags: Not Done (the language step was not run)
- Accessibility Evaluation: Not Completed

**Safety checks:** OK ✔ pages look the same · OK ✔ text unchanged · FAILED ✘ all content tagged or decoration · OK ✔ tag-tree index points into the tree · OK ✔ every font readable  
**Needs a person:** 12 (3 deferred by the AI · 2 deferred by the executor · 7 CHECK rows)  
**AI decisions:** 64 in the work order, applied without review by a person  
**Fixed automatically (no AI):** links tied and described 2,963 · note IDs 838 · decorative lines marked 12 · link descriptions that were only a URL 7 · figures moved to their page 7 · empty tags removed 7 · marked as tagged 1 · title shown in the window 1 · whole-page figures wrapped 1 · tag-tree index entries 1 · pages given tab order 1  
**veraPDF (WCAG 2.2 machine checks):** 4 WCAG rules failing before (3,172 checks) → 1 after (260 checks) · 0 newly failing

Automated checks are evidence, not sign-off.

| Top issues | Pages | Where |
|---|---|---|
| All content tagged or marked as decoration: 1526 untagged characters · 260 untagged objects (258 text, 2 image) | see Automated Checks | [Automated Checks](#automated-checks) |
| Page-level figure wrap: PDF 1 (printed COVER) wrapped as one Figure · not wrapped: PDF 5 (printed iv) (has 2 annotation(s) (links)) | PDF 1 (printed COVER), PDF 5 (printed iv) | [Automated Checks](#automated-checks) |
| Empty tags removed when proven empty: 7 removed · 1 kept: something refers to them or they carry an attribute (listed) | see §11 | [§11](#11-empty-tags-7-removed-1-kept) |
| No empty tags: 1 empty tag (page: not on this tag) | see §11 | [§11](#11-empty-tags-7-removed-1-kept) |
| No link whose only text is a URL: 2: PDF 5 (printed iv) | PDF 5 (printed iv) | [§10](#10-links-whose-description-was-only-a-url-9-and-1-address-that-looks-broken) |
| … and 7 more | | §13, §15, §16, §17 |

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
| Executor applied every decision | **CHECK** | 2 rejected · 0 failed (listed under "Decisions not applied") |
| Language tags hold their words | OK | 317 tags checked · 0 not matching their words or language |
| Nothing deferred by the executor | **CHECK** | 3 deferred (listed under "Deferred by the executor") |
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
| Reading order: no section moved away from its printed place by this run (1.3.2) | OK | 0 new · 2 already in the original, of 16 sections and blocks |
| Title is not a file name or placeholder (2.4.2) | OK | "Moral Foods: The Construction of Nutrition and Health in Modern Asia" |
| Link text: none like "click here" (2.4.4) | OK | 0 generic |
| Headings: none empty, very long or repeated in a row (2.4.6) | OK | 0 empty · 0 long · 0 repeated |

## For a Person to Check

### 1. Pages Wrapped as One Figure (1)

Pages with nothing tagged and nothing marked as decoration that hold a drawing (a full-page map, plate or cover). Each page was wrapped whole in one Figure; nothing on it was changed or removed.

- PDF 1 (printed COVER): read first in the document. Alt text from the AI: "Book cover: two photographs, a green rice plant on the left and a bowl of white rice sprinkled with seeds on the right, on a dark background. Title: Moral Foods: The Construction of Nutrition and Health in Modern Asia. Edited by Angela Ki Che Leung and Melissa L. Caldwell."
- PDF 5 (printed iv): not wrapped, left as it is (has 2 annotation(s) (links)).

### 2. Alt Text Written or Changed by the AI (7)

| Page | Before | After |
|---|---|---|
| PDF 106 (printed 93) | Map of China in the 1940s showing Japanese-occupied areas. Source: GIS Center, Academia Sinica, Taipei, Taiwan. | Map of China in the 1940s showing Japanese-occupied areas. Japanese-occupied territory (gray) covers the north and east, from the Inner Mongolia border and Hebei through Shanxi, Shandong, Henan, Jiangsu and Anhui to Shanghai and Zhejiang. Korea and Taiwan are shown in black as Japanese colonies, and India, Burma and Indochina as territories under western powers. Territories under Chinese rule, white, lie in the west and southwest, with the wartime capital Chongqing marked. Railroads, Great Walls, lakes and rivers are also drawn. |
| PDF 155 (printed 142) | Annual consumption (per capita) of rice, wheat, and barley in South Korea, 1970–2016. Drawn by the author, based on the statistics from “Grain Consumption, per Capita, per Year, 1963–2016,” Korean Statistical Information Service, http://kosis.kr. | Line chart of annual per capita consumption of rice, wheat and barley in South Korea, 1970–2016. Rice falls steadily from 136.4 to 71.2. Wheat stays almost flat at about 30 to 37, ending at 35.0. Barley drops sharply from 37.3 to 1.3 by the late 1980s. |
| PDF 202 (printed 189) | “Central Market, Hong Kong; Retail Stores, Ground Floor,” 1895. The National Archives of the UK (TNA): Public Record Office (PRO), Kew, Colonial Office Records (CO), Series 1069/446 (28). | Photograph from 1895 of the upper floor of the Central Market, Hong Kong: a long, empty hall under a timber-trussed pitched roof, with rows of wooden shop stalls and benches on both sides of a central aisle. |
| PDF 204 (printed 191) | “Cattle Slaughter House Interior, Hong Kong,” 1894. The National Archives of the UK (TNA): Public Record Office (PRO), Kew, Colonial Office Records (CO), Series 1069/446 (23). | Photograph from 1894 of the interior of the cattle slaughterhouse in Hong Kong: an empty, wet-floored hall with exposed roof beams, iron columns and winch machinery along the back wall. |
| PDF 276 (printed 263) | The Chinese Food Pagoda, 2016. The left side of the pagoda’s second-highest tier represents dairy products. Used with permission from Chinese Nutrition Society, 2016 Dietary Guideline for Chinese (Zhongguo jumin shanshi zhinan 2016) (Beijing: People’s Medical Publishing House, 2016). | The Chinese Food Pagoda, 2016, titled in Chinese as the Chinese Residents' Balanced Diet Pagoda. A five-tier pagoda shows food groups from top to bottom: a cup and spoon at the peak; dairy products, with milk on the left, and soy products; fish, meat and eggs; vegetables and fruit; and grains and tubers at the base. A jogger and a glass of water are beside it, with the note to walk 6,000 steps daily. |
| PDF 286 (printed 273) | The Food Guide Pyramid of the United States Department of Agriculture, 1992. Dairy products are located on the left-hand side of the second-highest tier, just as in the later Chinese food pagoda. Courtesy of the U.S. Department of Agriculture. | The US Department of Agriculture Food Guide Pyramid, 1992, titled 'A Guide to Daily Food Choices'. From the tip down: fats, oils and sweets (use sparingly); the milk, yogurt and cheese group (2–3 servings) beside the meat, poultry, fish, dry beans, eggs and nuts group (2–3 servings); the vegetable group (3–5 servings) beside the fruit group (2–4 servings); and the bread, cereal, rice and pasta group (6–11 servings) at the base. Dairy sits on the left of the second-highest tier. |
| PDF 293 (printed 280) | 2016 Balanced Diet Plate for Chinese. Used with permission from Chinese Nutrition Society, 2016 Dietary Guideline for Chinese (Zhongguo jumin shanshi zhinan 2016) (Beijing: People’s Medical Publishing House, 2016). | The 2016 Balanced Diet Plate for Chinese, with Chinese labels. A round plate is divided into four sections: grains and tubers (largest), fish, meat, eggs and beans, vegetables, and fruit. Beside it are a cup of milk, chopsticks and a spoon. |

### 3. Headings

Heading levels by style (as applied):

| Style | Level | How | Elements |
|---|---|---|---:|
| TPHT | P | RoleMap | 2 |
| TPST | P | RoleMap | 1 |
| FMH | H2 | RoleMap | 2 |
| CT | H2 | RoleMap | 13 |
| CST | P | RoleMap | 13 |
| PN | P | RoleMap | 3 |
| PT | H2 | RoleMap | 3 |
| _H1_ | H3 | RoleMap | 63 |
| ENH | H3 | RoleMap | 13 |
| BMH | H2 | RoleMap | 4 |
| H2 | H4 | retype (standard tag) | 8 |

Merged: `CST` into the prev `CT`; `PN` into the next `PT`

Spoken text set by the AI (should match what is printed):

| Page | Text |
|---|---|
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

- "front matter running heads and folios": text matching `(?:Contents )?[ivx]+(?: Contents)?` on PDF 6–8 (printed v–vii)
- "introduction running heads and folios (top)": text matching `(?:Caldwell and Leung )?\d+(?: Introduction)?` on PDF 14–16 (printed 1–3)
- "introduction running heads and folios (bottom)": text matching `(?:Caldwell and Leung )?\d+(?: Introduction)?` on PDF 14–16 (printed 1–3)
- "chapter 3 opening folio": text matching `\d+` on PDF 79 (printed 66)
- "index running heads and folios (top)": text matching `(?:Index )?\d+(?: Index)?` on PDF 348–350 (printed 335–337)
- "index running heads and folios (bottom)": text matching `(?:Index )?\d+(?: Index)?` on PDF 348–350 (printed 335–337)

### 6. Reading Order Changes

Listen through these spots with a screen reader.

- Figure on PDF 106 (printed 93) moved to read with its page (it read after PDF 356 (printed 343); now after PDF 107 (printed 94))
- Figure on PDF 155 (printed 142) moved to read with its page (it read after PDF 356 (printed 343); now after PDF 156 (printed 143))
- Figure on PDF 202 (printed 189) moved to read with its page (it read after PDF 356 (printed 343); now after PDF 202 (printed 189))
- Figure on PDF 204 (printed 191) moved to read with its page (it read after PDF 356 (printed 343); now after PDF 205 (printed 192))
- Figure on PDF 276 (printed 263) moved to read with its page (it read after PDF 356 (printed 343); now after PDF 277 (printed 264))
- Figure on PDF 286 (printed 273) moved to read with its page (it read after PDF 356 (printed 343); now after PDF 286 (printed 273))
- Figure on PDF 293 (printed 280) moved to read with its page (it read after PDF 356 (printed 343); now after PDF 293 (printed 280))

### 7. Untagged Paths (rules, borders, lines)

12 paths drawn outside any tag were marked as decoration: none of them carries text, an image or a link, and none touches untagged text or images.

### 8. Untagged Content (260 objects)

Drawn content that is neither tagged nor marked as decoration (content reused on several pages counts once). Not changed by the pipeline; a person decides whether each is real content (tag it) or decoration (artifact it). Pages with the most:

- PDF 5 (printed iv): 258 text, 2 image

### 9. Spoken Text (ActualText) Checked Against the Print (16 accepted with differences, 0 rejected)

A spoken text may differ from the printed characters only in spacing, letter case and line-end hyphens (sponsor rule 1). Accepted ones that differ are listed so a person can listen to them; rejected ones added or changed words or punctuation.

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

### 10. Links Whose Description Was Only a URL (9, and 1 address that looks broken)

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

### 11. Empty Tags (7 removed, 1 kept)

A tag is removed only when proven empty: nothing under it holds content, it carries no Alt, ActualText, E or ID, and nothing in the file refers to it except its parent. Table cells are never removed one by one; a table goes only when every part is empty.

- Removed: 4 TNI, 3 P
- **Kept, empty: Note (page: not on this tag)**, because carries /ID "note-0838"; IDTree "note-0838".

### 12. Structure Left for a Person

- 1 empty tag: Note (page: not on this tag)
- PDF 5 (printed iv): a link's description is only its URL (www.knowledgeunlatched.org)
- PDF 5 (printed iv): a link's description is only its URL (https://creativecommons.org/licenses/by-nc-nd/4.0/)

### 13. veraPDF (WCAG 2.2 machine profile), Before and After

veraPDF 1.30.3, profile "WCAG 2.2 machine validation profile" (7da399cf5baa). Counts are failed checks; pages are from the first checks veraPDF lists for each rule, so a rule may fail on more pages. Rules that only PDF/UA requires are listed apart and do not count. "Who fixes" is who can act on the rule: the pipeline by itself, the AI through the work order, or only a person. **Newly failing** means this run broke something the original passed. Before: 4 rules failing (the AI can act on 1, the pipeline on 3, only a person on 0). After: 1.

| Rule | WCAG | What it checks | Who fixes | Before | After | Status | Pages (after, else before) |
|---|---|---|---|---:|---:|---|---|
| ISO 14289-1 7.1-3 | 1.3.1 | Content shall be marked as Artifact or tagged as real content e.g. "Content is neither marked as Artifact nor tagged as real content" | the AI (`artifacts`) | 273 | 260 | still failing | PDF 5 (printed iv) |
| ISO 14289-1 7.18.5-1 | 2.4.4, 4.1.2 | Links shall be tagged according to ISO 32000-1:2008, 14.8.4.4.2, Link Element | the pipeline | 2897 | 0 | fixed | PDF 5 (printed iv), PDF 6 (printed v), PDF 8 (printed vii), PDF 14 (printed 1), PDF 15 (printed 2), PDF 16 (printed 3), PDF 17 (printed 4), PDF 18 (printed 5), PDF 19 (printed 6) |
| ISO 14289-1 6.2-1 | 1.3.1 | The document catalog dictionary shall include a MarkInfo dictionary containing an entry, Marked, whose value shall be true | the pipeline (1 changed) | 1 | 0 | fixed | page: not on this tag |
| ISO 14289-1 7.18.3-1 | 2.4.3 | Every page on which there is an annotation shall contain in its page dictionary the key Tabs, and its value shall be S | the pipeline (1 changed) | 1 | 0 | fixed | PDF 5 (printed iv) |

### 14. WCAG Checks veraPDF Does Not Make

Each item is something to look at, not a proven failure.

- 1.3.2 1 small section is read more than 5 pages after its printed page, after a longer section that covers it. Not a failure (long stories overlap in InDesign books), but a screen reader hears them far from where they are printed: PDF 106 (printed 93) read after PDF 343 (printed 330)
- 1.3.2 2 sections read away from their printed place, as in the original (this run did not move them). Listen through each where it is read, or move it with move_section:
  - PDF 7 (printed vi): Story "vi Contents", read before PDF 2 (printed i)
  - PDF 8 (printed vii): Story "Contents vii", read before PDF 2 (printed i)

### 15. Deferred by the AI

- **Copyright page text and Library of Congress CIP data are untagged real content (veraPDF 7.1-3, 26 untagged runs). The remaining 7.1-3 failures are the untagged cover (handled by page_figures).**: Real content cannot be artifacted. A person must tag it as paragraphs. [PDF 5 (printed iv)]
- **Index pages appear to read the two columns merged line by line (for example, PDF 338 starts 'Hani Motoko, 80–81 infectious diseases and epidemics: animal'). Check the reading order of the index text.**: Cannot be fixed with the available work-order keys; a person must review. [PDF 351 (printed 338), PDF 352 (printed 339), PDF 353 (printed 340), PDF 354 (printed 341), PDF 355 (printed 342), PDF 356 (printed 343)]
- **Pages 344–348 show no tagged text in the page map (Contributors and the first Index page). Check that this content is tagged and in order.**: The page map does not show enough to decide. [PDF 344 (printed 331), PDF 345 (printed 332), PDF 346 (printed 333), PDF 347 (printed 334), PDF 348 (printed 335)]

Reviewer note from the AI: Headings: the book title (TPT, PDF 4) is the only H1. Half-title (TPHT) and subtitle (TPST) lines are demoted to P. Front and back matter titles, chapter titles and part titles are H2. Chapter subtitles (CST) are merged into their chapter title (CT), and 'Part N' is merged into its part title. In-chapter section heads (_H1_) are H3, the bold sub-heads in the Korean grains chapter (style H2) are H4, and each chapter's 'Notes' heading is H3. The merged heading texts were typed from the digest; check them against the page. Running heads and folios (RHR, RHV, DFOL) on the sampled pages are artifacted by band and regex. Figure captions (CAP) are tied to their figures.

### 16. Deferred by the Executor

- **1020 Han-only CJK runs** need a Japanese / Chinese decision: fill in `han_review.csv`.
- link on a page with no tagged text (PDF 5 (printed iv)): tied to tagged text on PDF 4 (printed iii)
- link on a page with no tagged text (PDF 5 (printed iv)): tied to tagged text on PDF 4 (printed iii)

### 17. Decisions Not Applied (2)

Rejected by validation or by the executor; nothing was half-applied.

- {"op": "artifact front matter running heads and folios (12557, 0)", "why": "element is not a single marked-content run"}
- {"op": "artifact front matter running heads and folios (12558, 0)", "why": "element is not a single marked-content run"}

### 18. Language Tags

Words and passages in another language get a language tag, so a screen reader switches to that language's voice (WCAG 3.1.2). Tags from the language step are decided by a person; kana and Hangul are tagged by a fixed rule.

## What Was Changed

| Change | Count |
|---|---:|
| document: marked as tagged | 1 |
| artifact: "front matter running heads and folios" | 1 |
| artifact: "introduction running heads and folios (bottom)" | 1 |
| artifact: "introduction running heads and folios (top)" | 5 |
| artifact: "chapter 3 opening folio" | 1 |
| artifact: "index running heads and folios (bottom)" | 1 |
| artifact: "index running heads and folios (top)" | 4 |
| document: title | 1 |
| document: DisplayDocTitle | 1 |
| document: /Lang | 1 |
| heading: RoleMap level | 10 |
| heading: merged into prev | 13 |
| heading: merged into next | 3 |
| heading: ActualText | 16 |
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
| order: figure moved to its page | 7 |
| contents: entry wrapped in Reference | 34 |
| order: empty container removed | 8 |
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
