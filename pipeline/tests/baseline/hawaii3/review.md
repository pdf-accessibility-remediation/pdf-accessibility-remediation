# Remediation Review: hawaii3.pdf

Result: `hawaii3_remediated.pdf`

301 pages · run November 13, 2026, at 3:26 PM · model `anthropic/claude-sonnet-5.5` · prompt `workorder_v11.md` (3fd29e7f3ef071ec) · AI cost $0.171 ($0.0006 per page), from the original AI request on November 13, 2026 · this run: no new AI request · tokens: saved reply reused, not counted

Intake: none (already tagged)

Libraries: python 3.13.9 · pikepdf 10.5.1 · pdfplumber 0.11.9 · pypdfium2 5.7.1 · pillow 13.0.0 · fonttools 4.62.1

Time: intake 0.5s · audit 27.1s · reuse saved reply 1.4s · apply 22.4s · verify 27.3s · total 78.7s

## Overview

[Open the dashboard](review.html)

**Status:** Not Ready

**Ready to ship?**
- Work Order Approval: Not Approved (applied without a review)
- ✓ OCR Text Approval: Not Applicable
- Safety Checks: Failed (all content tagged or decoration)
- ✓ Language Tags: Not Applicable
- Accessibility Evaluation: Not Completed

**Safety checks:** OK ✔ pages look the same · OK ✔ text unchanged · FAILED ✘ all content tagged or decoration · OK ✔ tag-tree index points into the tree · OK ✔ every font readable  
**Needs a person:** 24 (3 deferred by the AI · 18 deferred by the executor · 3 CHECK rows)  
**AI decisions:** 23 in the work order, applied without review by a person  
**Fixed automatically (no AI):** links tied and described 186 · link descriptions that were only a URL 62 · tag-tree index entries 6 · title shown in the window 1  
**veraPDF (WCAG 2.2 machine checks):** 1 WCAG rule failing before (7 checks) → 1 after (1 check) · 0 newly failing

Automated checks are evidence, not sign-off.

| Top issues | Pages | Where |
|---|---|---|
| All content tagged or marked as decoration: 399 untagged characters · 7 untagged objects (7 text) | see Automated Checks | [Automated Checks](#automated-checks) |
| If the Lang entry is present in the document's Catalog dictionary or i (veraPDF 7.2-29, 1 check) | PDF 224 (printed 211) | [§8](#8-verapdf-wcag-22-machine-profile-before-and-after) |
| Reading order jumps back up a column (2 jumps) | PDF 71 (printed 58) | [§9](#9-wcag-checks-verapdf-does-not-make) |
| /Lang "Hawaii" on Span names Hawaiian, but "Tengan" is not spelled with Hawaiian letters: "P. Kāwika Tengan" (2) | PDF 75 (printed 62), PDF 78 (printed 65) | [§11](#11-deferred-by-the-executor) |
| /Lang "Hawaii" on Span names Hawaiian, but "Nyéléni" is not spelled with Hawaiian letters: "Nyéléni" (2) | PDF 127 (printed 114) | [§11](#11-deferred-by-the-executor) |
| … and 15 more | | §10, §11 |

Automated checks are evidence, not legal sign-off. Items marked **CHECK**, and everything under "For a person to check", need a human.

## Automated Checks

| Check | Result | Detail |
|---|---|---|
| Every page looks the same as the original | OK | 0 pages differ |
| Published text unchanged | OK | 0 pages changed |
| All content tagged or marked as decoration | **CHECK** | 399 untagged characters · 7 untagged objects (7 text) |
| Untagged paths: none left | OK | 0 untagged paths |
| Invisible OCR text: every glyph defined | OK | no undefined glyphs in invisible text |
| Page-level figure wrap | OK | no page with only an untagged drawing |
| Empty tags removed when proven empty | OK | 0 removed |
| Tag-tree index points only into the tree | OK | 0 dangling entries · 3 stale entries (marked content no longer drawn) |
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
| Headings: no skipped levels | OK | H1 1 · H2 73 · H3 113 · H4 8 |
| Headings: exactly one H1 (the title) | OK | 1 H1 (several H1s usually mean parts or chapters were not demoted) |
| Figures: none with empty or placeholder alt | OK | 11 figures, 0 placeholder |
| Every Note has a unique ID | OK | 11 notes · 0 without ID · 0 duplicate · 0 not in the ID tree |
| Bookmarks present (documents over 9 pages) | OK | 198 bookmarks |
| Model reply held one work order | OK | one |
| Executor applied every decision | OK | 0 rejected · 0 failed (listed under "Decisions not applied") |
| Nothing deferred by the executor | **CHECK** | 22 deferred (listed under "Deferred by the executor") |
| Fonts: every glyph defined (no .notdef) | OK | none found |
| Fonts: every embedded font program could be read | OK | all read |
| Fonts: embedded and mapped to Unicode | OK | 0 not embedded · 0 without ToUnicode |
| Tab order follows the tag structure on pages with links or other annotations | OK | 0 of 36 pages with annotations lack /Tabs /S |
| Characters with no Unicode value (checklist 3.6) | OK | 0 read-aloud characters with no Unicode value |
| Private-use characters (checklist 3.6) | OK | 0 read-aloud characters with private-use codes |
| Title and language set | OK | "The Value of Hawaiʻi 3: Hulihia, the Turning" · en-US |
| veraPDF WCAG 2.2 (machine): no WCAG failures | **CHECK** | before: 1 WCAG rule failed (7 checks) → after: 1 WCAG rule failed (1 checks) · 1 PDF/UA-only rules not counted (listed under "veraPDF") |
| veraPDF: no rule newly failing or failing more often | OK | 0 fixed · 2 still failing · 0 newly failing |
| Alt text: none like a file name or repeated on many figures (1.1.1) | OK | 0 of 11 figures flagged |
| Tables: every table has header cells (1.3.1) | OK | none without |
| Reading order: no page jumps back up a column (1.3.2) | **CHECK** | 1 of 288 pages flagged |
| Reading order: no section moved away from its printed place by this run (1.3.2) | OK | 0 new · 0 already in the original, of 179 sections and blocks |
| Title is not a file name or placeholder (2.4.2) | OK | "The Value of Hawaiʻi 3: Hulihia, the Turning" |
| Link text: none like "click here" (2.4.4) | OK | 0 generic |
| Headings: none empty, very long or repeated in a row (2.4.6) | OK | 0 empty · 0 long · 0 repeated |

## For a Person to Check

### 1. Alt Text Written or Changed by the AI (11)

| Page | Before | After |
|---|---|---|
| PDF 1 (printed Cover) | Cover: The Value of Hawaiʻi 3: Hulihia, the Turning Edited by Noelani Goodyear-Ka‘ōpua, Craig Howes, Jonathan Kay Kamakawiwo‘ole Osorio, and Aiko Yamashiro\x00 | Front cover: a painting of a black teardrop shape filled with glowing red and orange lava-like cracks, set against a green background with a swirling white border. The title 'The Value of Hawaiʻi 3: Hulihia, the Turning' appears at the top, and the editors' names (Noelani Goodyear-Kaʻōpua, Craig Howes, Jonathan Kay Kamakawiwoʻole Osorio, and Aiko Yamashiro) appear at the bottom. |
| PDF 5 (printed iv) | CC BY-NC-ND 4.0\x00 | Creative Commons license icon: CC BY-NC-ND 4.0 (Attribution, NonCommercial, NoDerivatives). |
| PDF 93 (printed 80) | Illustration of different ecosystems from the mountains to the plains, shore, and sea, with human dwellings, agriculture, and aquaculture depicted\x00 | Painting 'Makamalunohonaokalani' by Marilyn Kahalewai showing an ahupuaʻa from mountain to sea: a stream runs down through forest and terraced taro fields to a shore with thatched houses, past a fishing canoe house, to the ocean where canoes and swimmers are shown. |
| PDF 121 (printed 108) | Word cloud where the words indigenous, agriculture, people, system, family, practices, and Hawaiian are most prominent\x00 | Word cloud made from the speakers' transcripts. The most prominent words are Indigenous, people, system, agriculture, food, family, practices, land, Hawaiian, knowledge, and values. |
| PDF 244 (printed 231) | Map of world showing higher temperatures in more urban areas\x00 | World map made of dots from climate sensors. The dots are densest, and the temperatures higher, in urban regions such as eastern North America, Europe, India, East Asia, and coastal South America, showing the extent of urbanism. |
| PDF 245 (printed 232) | Map of Oahu highlighting areas around Schofield barracks, Pearl Harbor, Fort Kamehameha, Fort Armstrong, Fort DeRussey, and Diamond Head\x00 | Relief map of Oʻahu with the original land defenses highlighted in red: Schofield Barracks, Pearl Harbor, Fort Kamehameha, Fort Armstrong, Fort DeRussy, and Diamond Head. Dotted lines mark the railway gun route, direct lines of visibility, and the Diamond Head fire range. |
| PDF 246 (printed 233) | Graphic image of a row of tanks compared to Aloha Tower, each tank is about two to three times as large as Aloha Tower\x00 | Rendering comparing the underground Red Hill fuel tanks with Aloha Tower. A row of large red tanks stands behind a row of Aloha Tower models, and each tank is about two to three times as large as the tower. |
| PDF 247 (printed 234) | Two maps of Oahu showing high correlation between military training areas and bases and urbanism\x00 | Two side-by-side maps of Oʻahu. The left map, 'Military Land Use (Territory)', shows training areas and bases. The right map, 'State Land Use (2020)', shows agriculture and urban areas. Urban areas and military bases overlap closely, showing the correlation between military land and urbanism. |
| PDF 248 (printed 235) | Map of Waikiki’s wetlands, streams, marshes, fields, dams, reefs, and direction of storm water inputs and clean water outputs \x00 | Aerial map of Waikīkī with a hypothetical plan to recover its hydrology. It labels Mānoa-Pālolo marsh, Waikīkī kalo fields, Kapahulu linear wetland, Ala Wai wetland park, Makiki stream park, Kālia fens, Kālia dam, and an oyster reef. Red arrows show stormwater inputs and blue arrows show clean water outputs. |
| PDF 273 (printed 260) | Chart titled Advancing Justice for Kanaka Maoli in One Generation Through Health Policy, a vision statement for health policy to advance equity for Native Hawaiians—and eliminate health disparities—within one generation. Seven steps are described, beginning with “cultural foundation” and ending with “population strengthening,” spanning history through 2030\x00 | Chart titled 'Ulu Kukui o Kaulike: Advancing Justice for Kānaka Maoli in One Generation Through Health Policy', a vision for health policy that advances equity for Native Hawaiians and eliminates health disparities within one generation. Long description: seven steps, each shown by a plant illustration over a timeline from millennia ago to 2020–2030. 1. Cultural foundation: improving health from an authentic worldview of Mauli Ola and Kānaka Maoli well-being. 2. Community cohesion (2010–2014): population health goals to eliminate health disparities and inequalities among Native Hawaiians. 3. Equity research and policy analyses (2014): cross-sectoral research based on community needs shapes appropriate health policy solutions. 4. Systems advocacy (2015): harness community cohesion to enact legislation that integrates Native Hawaiian values. 5. Legislative compliance and enforcement (2015–2019): substantive policy change requires ongoing attention for complex health goals to be achieved. 6. Investment for SDOH and disparate populations (2019): meaningful long-term investment by federal, state, and local government is needed to uplift Native Hawaiians. 7. Population strengthening (2020–2030): at the core of social justice for Kānaka Maoli is racial equity and healing. |
| PDF 297 (printed 284) | Illustration of an ahupuaa from the mountains to the sea, with plants, animals, people, and other natural features\x00 | Digital illustration, a vision map for a future Hāmākua, by Haley Kailiehu. A flowering ʻōhiʻa tree stands on a headland above a winding stream and waterfall that run to the sea. Seabirds fly overhead, fish and whales swim below, and gardens, stone structures, and a gathering house with people sit between the mountain and the shore. |

### 2. Headings

Heading levels by style (as applied):

| Style | Level | How | Elements |
|---|---|---|---:|
| H1 | H2 | retype (standard tag) | 76 |
| H2 | H3 | retype (standard tag) | 113 |
| H3 | H4 | retype (standard tag) | 8 |

### 3. Elements Retyped by the AI (3)

Check each one is (or is not) a heading as decided.

| Page | Text | Before | After |
|---|---|---|---|
| PDF 2 (printed i) | The Value of Hawaiʻi 3 | H1 | H1 |
| PDF 3 (printed ii) | BIOGRAPHY MONOGRAPHS | H1 | P |
| PDF 4 (printed iii) | The Value of Hawaiʻi 3 the Turning Hulihia, | H1 | P |

### 4. Text a Screen Reader Could Not Reach (before this run)

3 pages had text outside the tag tree: 0 orphan runs (marked, but no tag owns them) and 7 untagged runs. Running heads and page numbers among them can be hidden as decoration; real content must be added to the tag tree by a person. After this run: 399 untagged characters, 0 orphan runs remain.

Pages: PDF 9–10 (printed viii–ix), PDF 35 (printed 22)

### 5. Untagged Content (7 objects)

Drawn content that is neither tagged nor marked as decoration (content reused on several pages counts once). Not changed by the pipeline; a person decides whether each is real content (tag it) or decoration (artifact it). Pages with the most:

- PDF 35 (printed 22): 5 text
- PDF 9 (printed viii): 1 text
- PDF 10 (printed ix): 1 text

### 6. Links Whose Description Was Only a URL (62)

The description (what a screen reader announces) was set to the book's own sentence around the link, with the URL removed. No words were added and the visible URL is unchanged. Replace any of these with a better description if needed.

| Page | URL | Description now |
|---|---|---|
| PDF 3 (printed ii) | http://blog.hawaii.edu/cbrhawaii/ | For further information about the Center or its publications, contact the Center for Biographical Research, University of Hawai‘i at Mānoa, Honolulu, Hawai‘i 96822 USA; biograph@hawaii.edu |
| PDF 5 (printed iv) | https://creativecommons.org/licenses/by-nc-nd/4.0/ | For details, see. |
| PDF 31 (printed 18) | https://www.kathyjetnilkijiner.com/a-poem-grounded/ | Originally published on Kathy Jetñil-Kijiner’s website on May 28, 2020, at. |
| PDF 35 (printed 22) | https://www.wri.org/blog/2019/08/17-countries-home-one-quarter-world-population-face-extremely-high-water-stress | “17 Countries, Home to One-Quarter of the World’s Population, Face Extremely High Water Stress.” World Resources Institute, 6 Aug. 2019, world-population-face-extremely-high-water-stress. |
| PDF 35 (printed 22) | https://www.worldweatherattribution.org/human-contribution-to-the-record-breaking-july-2019-heat-wave-in-western-europe/ | “Human contribution to the record-breaking July 2019 heatwave in Western Europe.” 2 Aug. 2019, org/human-contribution-to-the-record-breaking-july-2019-heat-wave-in­western-europe/. |
| PDF 54 (printed 41) | https://www.civilbeat.org/2020/05/the-hotel-tax-should-be-raised-a-lot/ | “The Hotel Tax Should Be Raised — A Lot.” Civil Beat, 17 May 2020 |
| PDF 54 (printed 41) | https://uhero.hawaii.edu/prevention-of-travel-related-reintroduction-of-covid-19-infection-in-the-state-of-hawaii/ | “Prevention of Travel-related Reintroduction of COVID-19 Infection in the State of Hawaii.” UHERO, 9 June 2020, infection-in-the-state-of-hawaii/. |
| PDF 70 (printed 57) | https://www.americamagazine.org/politics-society/2020/05/01/cardinal-dolan-defends-comments-about-trump-argues-he-has-critics-both | “Cardinal Dolan Defends Comments About Trump, Argues He Has Critics on Both Sides.” America: The Jesuit Review, 1 May 2020, americamagazine.org/politics-society/2020/05/01/cardinal-dolan-defends-comments­about-trump-argues-he-has-critics-both. |
| PDF 73 (printed 60) | https://www.ainaalohafutures.com/ | See ʻĀina Aloha Economic Futures and Building Bridges, Not Walking on Backs: A Feminist Economic Recovery Plan for COVID-19 ( 4.13.20-Final-Cover-D2-Feminist-Economic-Recovery-D1.pdf). |
| PDF 73 (printed 60) | https://humanservices.hawaii.gov/wp-content/uploads/2020/04/4.13.20-Final-Cover-D2-Feminist-Economic-Recovery-D1.pdf | See ʻĀina Aloha Economic Futures ( and Building Bridges, Not Walking on Backs: A Feminist Economic Recovery Plan for COVID-19. |
| PDF 74 (printed 61) | https://hehiale.wordpress.com/2015/04/03/we-live-in-the-future-come-join-us/ | Come Join Us.” Ke Kaupu Hehi Ale, 3 April 2015 |
| PDF 74 (printed 61) | https://health.hawaii.gov/coronavirusdisease2019/ | “Disease Outbreak Control Division | COVID-19,”. |
| PDF 74 (printed 61) | https://covid19.who.int | “WHO Coronavirus Disease (COVID-19) Dashboard,”. |
| PDF 78 (printed 65) | https://hehiale.wordpress.com/2015/07/06/we-are-not-warriors-we-are-a-grove-of-trees/ | We are a grove of trees.” Ke Kaupu Hehi Ale, 6 July 2015 |
| PDF 78 (printed 65) | https://on.ft.com/2N9x6wn | “The pandemic is a portal.” Financial Times, 3 Apr. 2020 |
| PDF 95 (printed 82) | http://bit.ly/ainaaloha-tool | “AAEF Assessment Tool for Policies, Projects, and Programs.” ʻĀina Aloha Economic Futures |
| PDF 95 (printed 82) | http://files.hawaii.gov/dbedt/op/sustainability/hawaii_2050_plan_final.pdf | Hawaiʻi 2050 Sustainability Task Force, State of Hawaiʻi, Jan. 2008 |
| PDF 95 (printed 82) | https://www.ksbe.edu/assets/site/special_section/land/pdf/NRMP_Flier.pdf | Kamehameha Schools, 2011 |
| PDF 103 (printed 90) | https://www.westhawaiitoday.com/2019/08/12/opinion/my-turn-maunakea-can-be-beacon-for-us-other-count | “My Turn: Maunakea can be beacon for us, other countries.” West Hawaii Today, 12 Aug. 2019, ries/. |
| PDF 119 (printed 106) | https://www.ainaalohafutures.com/declaration | “‘Āina Aloha Economic Futures Declaration.” ʻĀina Aloha Economic Futures, 19 May 2020 |
| PDF 119 (printed 106) | https://humanservices.hawaii.gov/wp-content/uploads/2020/04/4.13.20-Final-Cover-D2-Feminist-Economic-Recovery-D1.pdf | Hawaiʻi State Commission on the Status of Women and the Department of Human Services, State of Hawaiʻi, 14 Apr. 2020, wp-content/uploads/2020/04/4.13.20-Final-Cover-D2-Feminist-Economic­Recovery-D1.pdf. |
| PDF 130 (printed 117) | https://dps.hawaii.gov/wp-content/uploads/2019/11/PSD-ANNUAL-REPORT-2019.pdf | State of Hawaii Department of Public Safety, 2019 |
| PDF 130 (printed 117) | https://www.courts.state.hi.us/wp-content/uploads/2018/12/HCR-85_task_force_final_report.pdf | HCR 85 Task Force, Hawaiʻi Judiciary, Dec. 2018 |
| PDF 130 (printed 117) | https://ag.hawaii.gov/cpja/crime-in-hawaii-2017/ | “Crime in Hawaii 2017.” State of Hawaii Crime Prevention and Justice Assistance Division, 11 Jan. 2019 |
| PDF 130 (printed 117) | https://dps.hawaii.gov/wp-content/uploads/2020/02/Pop-Reports-EOM-2020-01-31.pdf | State of Hawaii Department of Public Safety, 31 Jan. 2020 |
| PDF 130 (printed 117) | http://oeqc2.doh.hawaii.gov/EA_EIS_Library/2018-07-08-OA-FEIS-Replacement-of-Oahu-Community-Correctional-Center.pdf | State of Hawaii Department of Accounting and General Services (DAGS), 26 June 2018, gov/EA_EIS_Library/2018-07-08-OA-FEIS-Replacement-of-Oahu-Community­Correctional-Center.pdf. |
| PDF 131 (printed 118) | https://www.courts.state.hi.us/wp-content/uploads/2018/12/POST_12-14-18_HCR134TF_REPORT.pdf | Criminal Pretrial Task Force, Hawai‘i State Judiciary, Dec. 2018 |
| PDF 131 (printed 118) | https://www.ncjrs.gov/pdffiles1/digitization/111098ncjrs.pdf | Department of Justice, May 1988 |
| PDF 131 (printed 118) | http://www.safetyandjusticechallenge.org/wp-content/uploads/2015/01/incarcerations-front-door-report.pdf | Vera Institute of Justice, Feb. 2015 |
| PDF 131 (printed 118) | https://icis.hawaii.gov/wp-content/uploads/2018/08/Hawaii-Revidivism-2017.pdf | State of Hawaii Interagency Council on Intermediate Sanctions (ICIS), July 2018 |
| PDF 135 (printed 122) | https://hehiale.wordpress.com/2017/02/01/where-will-you-be-why-black-lives-matter-in-the-hawaiian-kingdom/ | Black Lives Matter in the Hawaiian Kingdom.” Ke Kaupu Hehi Ale, 1 Feb. 2017 |
| PDF 139 (printed 126) | https://www.hawaiitourismauthority.org/media/4052/2019-annual-report-to-the-hawaii-state-legislature.pdf | Hawai‘i Tourism Authority. 2019 Annual Report to the Hawai‘i State Legislature |
| PDF 139 (printed 126) | https://www.hawaiipublicradio.org/post/sports-tourism-hawai-i-2019 | “Sports Tourism in Hawai‘i in 2019.” Hawai‘i Public Radio, 4 Feb. 2019 |
| PDF 161 (printed 148) | https://acluhi.org/sites/default/files/SJ-Blueprint-HI_1.pdf | American Civil Liberties Union, 2019 |
| PDF 161 (printed 148) | https://www.courts.state.hi.us/wp-content/uploads/2018/12/HCR-85_task_force_final_report.pdf | HCR 85 Task Force, Hawaiʻi Judiciary, Dec. 2018 |
| PDF 161 (printed 148) | https://caphawaii.files.wordpress.com/2012/07/disparate-treatment-of-native-hawaiians-in-cj.pdf | Office of Hawaiian Affairs, 2012 |
| PDF 161 (printed 148) | http://kahea.org/issues/environmental-justice/environmental-justice-bill-of-rights | “Environmental Justice Bill of Rights for the People of Waiʻanae.” KAHEA: The Hawaiian- Environmental Alliance |
| PDF 161 (printed 148) | https://hiappleseed.org/blog/ | Hawai‘i Appleseed Center for Law and Economic Justice, 2016– 2020 |
| PDF 161 (printed 148) | https://19of32x2yl33s8o4xza0gf14-wpengine.netdna-ssl.com/wp-content/uploads/2012NHJTF_REPORT_FINAL_0.pdf | Native Hawaiian Justice Task Force, 2012 |
| PDF 165 (printed 152) | https://www.youtube.com/watch?v=oxdGmlBCtSY | “Molokai Sustainability Conference Part 3.” YouTube, uploaded by molokaimatt, 19 Aug. 2009 |
| PDF 165 (printed 152) | https://www.youtube.com/watch?v=EA-P9_YlDLI | Kalani English: Mokulana, sacred floating islands of Hawaii.” YouTube, uploaded by seasteading, 19 June 2017 |
| PDF 176 (printed 163) | https://www.facebook.com/ryan.mandado/posts/10217584061618908 | “Poor instructional design. ” Facebook, 30 June 2020 |
| PDF 176 (printed 163) | https://www.facebook.com/sarah.miliantalaffin/posts/10115414963496449 | “I appreciate the requests. ” Facebook, 2 July 2020 |
| PDF 176 (printed 163) | https://educationpost.org/teachers-must-hold-themselves-accountable-for-dismantling-racial-oppression/ | “Teachers Must Hold Themselves Accountable for Dismantling Racism.”Education Post, 29 May 2020, themselves-accountable-for-dismantling-racial-oppression/. |
| PDF 180 (printed 167) | https://www.nytimes.com/2018/07/19/opinion/national-politics-localism-populism.html | “The Localist Revolution.” New York Times, 19 July 2018 |
| PDF 180 (printed 167) | https://www.theatlantic.com/magazine/archive/2019/08/raj-chettys-american-dream/592804/ | “Raj Chetty’s American Dream.” The Atlantic, 17 July 2019 |
| PDF 194 (printed 181) | https://onbeing.org/programs/wendell-berry-ellen-davis-the-art-of-being-creatures/ | “Wendell Berry and Ellen Davis: The Art of Being Creatures.” On Being, 10 June 2020 |
| PDF 198 (printed 185) | https://www.documentcloud.org/documents/6476457-HEC-Government-Report-FINAL.html#document/p1 | Hawai‘i Executive Conference, 2 Oct. 2019 |
| PDF 206 (printed 193) | http://boe.hawaii.gov/policies/Pages/Board-Policies.aspx | Hawai‘i State Board of Education |
| PDF 206 (printed 193) | http://www.hawaiipublicschools.org/DOE%20Forms/Advancing%20Education/2030PromisePlan.pdf | Hawai‘i State Department of Education |
| PDF 229 (printed 216) | https://doi.org/10.6084/m9.figshare.11434494.v1 | “A Native Hawaiian-led summary of the current impact of constructing the Thirty Meter Telescope on Maunakea.” figshare, preprint, 5 Jan. 2020 |
| PDF 239 (printed 226) | https://humanservices.hawaii.gov/wp-content/uploads/2020/04/4.13.20-Final-Cover-D2-Feminist-Economic-Recovery-D1.pdf | Hawaiʻi State Commission on the Status of Women, Department of Human Services, State of Hawaiʻi, 14 Apr. 2020 |
| PDF 243 (printed 230) | https://health.hawaii.gov/cab/files/2019/12/2016-Inventory_Final-Report_December2019-1.pdf | Prepared for the State of Hawai‘i Department of Health, 2019 |
| PDF 243 (printed 230) | https://www.bbc.com/news/av/science-environment-52508829/coronavirus-and-climate-change-a-double-crisis | “Coronavirus and Climate Change a ‘Double Crisis.’” BBC News, 6 May 2020 |
| PDF 243 (printed 230) | https://www.nature.com/articles/s41558-020-0797-x | “Temporary Reduction in Daily Global CO2 Emissions During the COVID-19 Forced Confinement.” Nature Climate Change, vol. 10, 2020, pp. 647–53 |
| PDF 243 (printed 230) | https://earthobservatory.nasa.gov/images/146362/airborne-nitrogen-dioxide-plummets-over-china | “Airborne Nitrogen Dioxide Plummets Over China.” Earth Observatory, 2020, plummets-over-china. |
| PDF 243 (printed 230) | https://www.bizjournals.com/pacific/news/2020/06/29/visitor-arrivals-continue-to-decline.html | “Hawai‘i Visitor Arrivals Drop by Nearly 100% for Second Consecu­tive Month.” Pacific Business News, 29 June 2020 |
| PDF 243 (printed 230) | https://uhero.hawaii.edu/wp-content/uploads/2019/08/Climate_Change_Overview_Oct20.pdf | Regional and National Climate Change Mitigation Strategies: Lessons for Hawai‘i.” 25 Aug. 2008 |
| PDF 249 (printed 236) | http://www.ao-projects.com | Sean Connelly (b. 1984, Oʻahu, Hawaiʻi) is an artist-architect based in Honolulu. |
| PDF 257 (printed 244) | http://dps.hawaii.gov/blog/2020/03/17/coronavirus-covid-19-information-and-resources/ | “Coronavirus (Covid-19) Information and Resources.” Department of Public Safety, State of Hawaiʻi, 17 Mar. 2020, covid-19-information-and-resources/. |
| PDF 294 (printed 281) | http://www.marimatsudapeaceorchestra.com | Richardson School of Law and an artist |
| PDF 298 (printed 285) | https://www.ft.com/content/10d8f5e8-74eb-11ea-95fe-fcd274e920ca | “The pandemic is a portal.” Financial Times, 3 Apr. 2020 |

### 7. Tag-tree Index Entries Cleared (6)

Entries that pointed at a tag no longer in the tag tree (left by the source file, or by a tag the run removed). Nothing reads such a tag; no page, text or reachable tag changed.

- ParentTree, PDF 11 (printed x): MCID 48 (Link), MCID 49 (Link), MCID 50 (Link)
- ParentTree, entries not tied to page content (annotations, forms, or keys nothing uses): key 2 (Link), key 3 (Link), key 6 (Link)

### 8. veraPDF (WCAG 2.2 machine profile), Before and After

veraPDF 1.30.3, profile "WCAG 2.2 machine validation profile" (7da399cf5baa). Counts are failed checks; pages are from the first checks veraPDF lists for each rule, so a rule may fail on more pages. Rules that only PDF/UA requires are listed apart and do not count. "Who fixes" is who can act on the rule: the pipeline by itself, the AI through the work order, or only a person. **Newly failing** means this run broke something the original passed. Before: 1 rule failing (the AI can act on 0, the pipeline on 1, only a person on 0). After: 1.

| Rule | WCAG | What it checks | Who fixes | Before | After | Status | Pages (after, else before) |
|---|---|---|---|---:|---:|---|---|
| ISO 14289-1 7.2-29 | 3.1.1, 3.1.2 | If the Lang entry is present in the document's Catalog dictionary or in a structure element dictionary or property list, its value shall be a language identifier as described in ISO 32000-1:2008, 14.9.2. A language identifier shall be a Language-Tag as defined in RFC 3066, Tags for the Identification of Languages e.g. "Value Hungarian of the Lang entry is not a Language-Tag" | the pipeline (401 changed) | 7 | 1 | still failing | PDF 224 (printed 211) |

PDF/UA-only, not required for WCAG (not counted):

- 7.21.5-1: glyph width consistency (48 checks, PDF 31 (printed 18), PDF 32 (printed 19), PDF 34 (printed 21), PDF 63 (printed 50), PDF 75 (printed 62), PDF 77 (printed 64), PDF 104 (printed 91), PDF 124 (printed 111)), still failing

### 9. WCAG Checks veraPDF Does Not Make

Each item is something to look at, not a proven failure.

- 1.3.2 the reading order jumps back up the same column on 1 page. Listen through them with a screen reader (or the PAC screen-reader preview): PDF 71 (printed 58) (2 jumps)

### 10. Deferred by the AI

- **Untagged body text: five lines of running text in the chapter on 'Catastrophic Failure of the Planet' (starting 'place on natural systems. Across 65% of the terre…') are in no tag and not marked.**: This is real content, which this work order can neither artifact nor tag. A person must tag it and place it in the correct reading order. [PDF 35 (printed 22)]
- **Untagged page numbers in the contents ('198' on PDF 9 (printed viii) and '253' on PDF 10 (printed ix)).**: They are the page-number part of contents entries, so they are real content and not pagination. A person must tag them into their TOC entries. [PDF 9 (printed viii), PDF 10 (printed ix)]
- **veraPDF reports 2 failed rules, but pdfua_check lists no rule that a work-order key can fix.**: These are failures only a person can fix, or the executor fixes by itself. Re-run veraPDF after applying this work order.

Reviewer note from the AI: Heading plan: the book title is the only H1 (half-title, PDF 2 (printed i)). The rolemap shifts every H1-styled chapter, part, and front/back-matter title to H2, subheads to H3, and the lower subheads to H4. Parts (I–IV) and chapters are therefore both H2, as the convention directs. The title-page lines and the series page are demoted to P. Contributor names under chapter titles are already P and were left alone. Epigraph questions on part-opener pages (e.g. PDF 28 (printed 15), 88 (printed 75), 154 (printed 141), 234 (printed 221)) are left as P. Several part-opener pages have no tagged text (e.g. PDF 13, 27, 29, 72, 74, 76, 85, 87, 89); these look like blank pages or artwork and may be worth a quick visual check. All figure alt texts originally contained NUL characters, and all have been replaced with clean text. The six existing bullet lists, the TOC/TOCI structure, and the Notes were judged correct and left as is. Reading order looked correct in the digest, so no move_section was requested.

### 11. Deferred by the Executor

- the source file already claims PDF/UA conformance: not verified by this pipeline; check it with PAC before relying on it
- /Lang "Hawaii" on Span names Hawaiian, but "Tengan" is not spelled with Hawaiian letters: "P. Kāwika Tengan" (PDF 75 (printed 62)): set the right tag (e.g. haw, en), or remove it
- /Lang "Hawaii" on Span names Hawaiian, but "Tengan" is not spelled with Hawaiian letters: "P. Kāwika Tengan" (PDF 78 (printed 65)): set the right tag (e.g. haw, en), or remove it
- /Lang "Hawaii" on Span names Hawaiian, but "Nyéléni" is not spelled with Hawaiian letters: "Nyéléni" (PDF 127 (printed 114)): set the right tag (e.g. haw, en), or remove it
- /Lang "Hawaii" on Span names Hawaiian, but "Nyéléni" is not spelled with Hawaiian letters: "Nyéléni" (PDF 127 (printed 114)): set the right tag (e.g. haw, en), or remove it
- /Lang "Hawaii" on Span names Hawaiian, but "mī-gusui" is not spelled with Hawaiian letters: "“mī-gusui, mimi-gusui, nuchi-gusui.”" (PDF 148 (printed 135)): set the right tag (e.g. haw, en), or remove it
- /Lang "Hawaii" on Span names Hawaiian, but "Mī-gusui" is not spelled with Hawaiian letters: "Mī-gusui, mimi-gusui, nuchi-gusui" (PDF 148 (printed 135)): set the right tag (e.g. haw, en), or remove it
- /Lang "Hawaii" on Span names Hawaiian, but "mimi-gusui" is not spelled with Hawaiian letters: "mimi-gusui." (PDF 150 (printed 137)): set the right tag (e.g. haw, en), or remove it
- /Lang "Hawaii" on Span names Hawaiian, but "mī-gusui" is not spelled with Hawaiian letters: "mī-gusui" (PDF 150 (printed 137)): set the right tag (e.g. haw, en), or remove it
- /Lang "Hawaii" on Span names Hawaiian, but "mimi-gusui" is not spelled with Hawaiian letters: "mimi-gusui" (PDF 150 (printed 137)): set the right tag (e.g. haw, en), or remove it
- /Lang "Hawaii" on Span names Hawaiian, but "nuchi-gusui" is not spelled with Hawaiian letters: "nuchi-gusui" (PDF 150 (printed 137)): set the right tag (e.g. haw, en), or remove it
- /Lang "Hawaii" on Span names Hawaiian, but "Sustʻāinable" is not spelled with Hawaiian letters: "Sustʻāinable" (PDF 163 (printed 150)): set the right tag (e.g. haw, en), or remove it
- /Lang "Hawaii" on Span names Hawaiian, but "Sustʻāinable" is not spelled with Hawaiian letters: "Sustʻāinable" (PDF 164 (printed 151)): set the right tag (e.g. haw, en), or remove it
- /Lang "Hawaii" on Span names Hawaiian, but "Sustʻāinable" is not spelled with Hawaiian letters: "Sustʻāinable" (PDF 164 (printed 151)): set the right tag (e.g. haw, en), or remove it
- /Lang "Hawaii" on Span names Hawaiian, but "Sustʻāinable" is not spelled with Hawaiian letters: "Sustʻāinable" (PDF 165 (printed 152)): set the right tag (e.g. haw, en), or remove it
- /Lang "Hawaii" on Span names Hawaiian, but "Sustʻāinable" is not spelled with Hawaiian letters: "Sustʻāinable" (PDF 165 (printed 152)): set the right tag (e.g. haw, en), or remove it
- /Lang "Hawaii" on Span names Hawaiian, but "Tatiana" is not spelled with Hawaiian letters: "Tatiana Kalaniʻōpua Young" (PDF 187 (printed 174)): set the right tag (e.g. haw, en), or remove it
- /Lang "Hawaii" on Span names Hawaiian, but "Tatiana" is not spelled with Hawaiian letters: "Tatiana Kalaniʻōpua Young" (PDF 190 (printed 177)): set the right tag (e.g. haw, en), or remove it
- /Lang "Hawaii" on Span names Hawaiian, but most of its words are English: "Sāmoan," (PDF 207 (printed 194)): set the right tag (e.g. haw, en), or remove it
- /Lang "Hawaii" on Span names Hawaiian, but "irensia" is not spelled with Hawaiian letters: "I irensia na'lå'la' i espiritu-ta." (PDF 218 (printed 205)): set the right tag (e.g. haw, en), or remove it
- /Lang "Hawaii" on Span names Hawaiian, but "Famalåo'an" is not spelled with Hawaiian letters: "Famalåo'an:" (PDF 221 (printed 208)): set the right tag (e.g. haw, en), or remove it
- 8 more language names whose words look like another language

### 12. Language Tags

Words and passages in another language get a language tag, so a screen reader switches to that language's voice (WCAG 3.1.2). Tags from the language step are decided by a person; kana and Hangul are tagged by a fixed rule.

**The PDF's language names, written as language codes (401 tags):** a language's name is not a language tag, so each is replaced by the code it names. Check that the words are in that language.

- "Hawaii" → haw (Hawaiian): 330 tags · e.g. "Noelani Goodyear-Ka‘ōpua,", "Mānoa,", "Goodyear-Ka‘ōpua," · PDF 3 (printed ii), PDF 4 (printed iii), PDF 12 (printed xi), PDF 14 (printed 1)
- "Hawaiian" → haw (Hawaiian): 63 tags · e.g. "Hulihia,", "Kuaʻāina", "ʻāina momona" · PDF 4 (printed iii), PDF 229 (printed 216), PDF 237 (printed 224), PDF 249 (printed 236)
- "Marshallese" → mh (Marshallese): 6 tags · e.g. "Kathy Jetñil-Kijiner", "“Bwebwenato in Lōrro”/“Story about Lōrro", "lōrro" · PDF 30 (printed 17), PDF 31 (printed 18)
- "Hawai" → haw (Hawaiian): 1 tag · e.g. "Ka ʻĀina Moana" · PDF 104 (printed 91)
- "hawaii" → haw (Hawaiian): 1 tag · e.g. "kānaka" · PDF 107 (printed 94)

**Language names left for a person (28):** the words under them look like another language, so they stay as written.

- "Hawaii" (Hawaiian) on "P. Kāwika Tengan": "Tengan" is not spelled with Hawaiian letters · PDF 75 (printed 62)
- "Hawaii" (Hawaiian) on "P. Kāwika Tengan": "Tengan" is not spelled with Hawaiian letters · PDF 78 (printed 65)
- "Hawaii" (Hawaiian) on "Nyéléni": "Nyéléni" is not spelled with Hawaiian letters · PDF 127 (printed 114)
- "Hawaii" (Hawaiian) on "Nyéléni": "Nyéléni" is not spelled with Hawaiian letters · PDF 127 (printed 114)
- "Hawaii" (Hawaiian) on "“mī-gusui, mimi-gusui, nuchi-gusui.”": "mī-gusui" is not spelled with Hawaiian letters · PDF 148 (printed 135)
- "Hawaii" (Hawaiian) on "Mī-gusui, mimi-gusui, nuchi-gusui": "Mī-gusui" is not spelled with Hawaiian letters · PDF 148 (printed 135)
- "Hawaii" (Hawaiian) on "mimi-gusui.": "mimi-gusui" is not spelled with Hawaiian letters · PDF 150 (printed 137)
- "Hawaii" (Hawaiian) on "mī-gusui": "mī-gusui" is not spelled with Hawaiian letters · PDF 150 (printed 137)
- "Hawaii" (Hawaiian) on "mimi-gusui": "mimi-gusui" is not spelled with Hawaiian letters · PDF 150 (printed 137)
- "Hawaii" (Hawaiian) on "nuchi-gusui": "nuchi-gusui" is not spelled with Hawaiian letters · PDF 150 (printed 137)
- "Hawaii" (Hawaiian) on "Sustʻāinable": "Sustʻāinable" is not spelled with Hawaiian letters · PDF 163 (printed 150)
- "Hawaii" (Hawaiian) on "Sustʻāinable": "Sustʻāinable" is not spelled with Hawaiian letters · PDF 164 (printed 151)
- "Hawaii" (Hawaiian) on "Sustʻāinable": "Sustʻāinable" is not spelled with Hawaiian letters · PDF 164 (printed 151)
- "Hawaii" (Hawaiian) on "Sustʻāinable": "Sustʻāinable" is not spelled with Hawaiian letters · PDF 165 (printed 152)
- "Hawaii" (Hawaiian) on "Sustʻāinable": "Sustʻāinable" is not spelled with Hawaiian letters · PDF 165 (printed 152)
- "Hawaii" (Hawaiian) on "Tatiana Kalaniʻōpua Young": "Tatiana" is not spelled with Hawaiian letters · PDF 187 (printed 174)
- "Hawaii" (Hawaiian) on "Tatiana Kalaniʻōpua Young": "Tatiana" is not spelled with Hawaiian letters · PDF 190 (printed 177)
- "Hawaii" (Hawaiian) on "Sāmoan,": most of its words are English · PDF 207 (printed 194)
- "Hawaii" (Hawaiian) on "I irensia na'lå'la' i espiritu-ta.": "irensia" is not spelled with Hawaiian letters · PDF 218 (printed 205)
- "Hawaii" (Hawaiian) on "Famalåo'an:": "Famalåo'an" is not spelled with Hawaiian letters · PDF 221 (printed 208)
- "Hawaii" (Hawaiian) on "famalåo'an": "famalåo'an" is not spelled with Hawaiian letters · PDF 221 (printed 208)
- "Hawaii" (Hawaiian) on "Guåhan": "Guåhan" is not spelled with Hawaiian letters · PDF 222 (printed 209)
- "Hungarian" (Hungarian) on "Noa Emmett Aluli, MD": its words look Hawaiian · PDF 224 (printed 211)
- "Hawaii" (Hawaiian) on "Davianna Pōmaikaʻi McGregor": "Davianna" is not spelled with Hawaiian letters · PDF 225 (printed 212)
- "Hawaiian" (Hawaiian) on "Oʻahu, a Giant Military Base": most of its words are English · PDF 245 (printed 232)
- "Hawaiian" (Hawaiian) on "Benjamin Treviño and Victoria Treviño": "Treviño" is not spelled with Hawaiian letters · PDF 250 (printed 237)
- "Hawaiian" (Hawaiian) on "Ulu Kukui o Kaulike: Kealoha Fox. Kukui art: Lisanne Paikai.": "Lisanne" is not spelled with Hawaiian letters · PDF 273 (printed 260)
- "Hawaiian" (Hawaiian) on "Puʻuhonua o Puʻuhuluhulu en masse": "masse" is not spelled with Hawaiian letters · PDF 279 (printed 266)

## What Was Changed

| Change | Count |
|---|---:|
| document: title | 1 |
| document: DisplayDocTitle | 1 |
| document: /Lang | 1 |
| heading: standard tag H1 → H2 (retyped) | 76 |
| heading: standard tag H2 → H3 (retyped) | 113 |
| heading: standard tag H3 → H4 (retyped) | 8 |
| retype → H1 | 1 |
| retype → P | 2 |
| figure: alt text | 11 |
| links: /Contents set | 186 |
| links: joined existing Link | 186 |
| links: URL-only description replaced by the sentence around it | 62 |
| language: a language name written as /Lang replaced by its code | 401 |
| tag tree index: entries pointing outside the tree cleared (ParentTree) | 6 |

## Accessibility Evaluation

A person evaluates this version of `hawaii3_remediated.pdf` with PAC 2026 and a screen reader, on the app's "Accessibility Evaluation" page (or with manual_checks.py; docs/release.md). The "Ready to ship?" answer needs both parts. A Fail is recorded with its note and does not hold the book back. Each result is recorded against this version of the PDF (its sha256): after a new apply it no longer counts. The evaluation is a record of what a person found, not a legal certification.

**PAC 2026.** Open `hawaii3_remediated.pdf` in PAC 2026 (https://pac.pdf-accessibility.org/en, Windows) and run its WCAG check. Anything it fails that is not listed above is a gap in the automated checks: note it in the issue tracker. Each item is Pass, Fail or Not Applicable, with notes:

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
