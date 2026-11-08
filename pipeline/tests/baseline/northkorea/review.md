# Remediation Review: northkorea.pdf

Result: `northkorea_remediated.pdf`

239 pages · run November 3, 2026, at 12:35 AM · model `anthropic/claude-sonnet-5.5` · prompt `workorder_v10.md` (15b5aa0ade9c6549) · AI cost $0.115 ($0.0005 per page), from the original call on November 3, 2026 · this run: no new call · tokens: saved reply reused, not counted

Intake: none (already tagged)

Libraries: python 3.14.4 · pikepdf 10.5.1 · pdfplumber 0.11.9 · pypdfium2 5.7.1 · pillow 13.0.0 · fonttools 4.62.1

Time: intake 0.2s · audit 25.4s · reuse saved reply 0.6s · apply 29.0s · verify 40.4s · total 95.6s

## Overview

[Open the dashboard](review.html)

**Status:** Not Ready

**Ready to ship?**
- Work Order Approval: Not Approved (applied without a review)
- ✓ OCR Text Approval: Not Applicable
- ✓ Safety Checks: Passed
- Accessibility Evaluation: Not Completed

**Safety checks:** OK ✔ pages look the same · OK ✔ text unchanged · OK ✔ all content tagged or decoration · OK ✔ tag-tree index points into the tree · OK ✔ every font readable  
**Needs a person:** 10 (5 deferred by the AI · 1 deferred by the executor · 4 CHECK rows)  
**AI decisions:** 70 in the work order, applied without review by a person  
**Fixed automatically (no AI):** tag-tree index entries 1,994 · links tied and described 1,963 · link descriptions that were only a URL 14 · empty tags removed 13 · title shown in the window 1 · Document root 1  
**veraPDF (WCAG 2.2 machine checks):** 0 WCAG rules failing before (0 checks) → 0 after (0 checks) · 0 newly failing

Automated checks are evidence, not sign-off.

| Top issues | Pages | Where |
|---|---|---|
| Empty tags removed when proven empty: 13 removed · 1 kept: something refers to them or they carry an attribute (listed) | see §7 | [§7](#7-empty-tags-13-removed-1-kept) |
| Every caption grouped with its figure: PDF 75 (printed 62) (caption inside root), PDF 75 (printed 62) (caption inside root) | PDF 75 (printed 62) | [§9](#9-structure-left-for-a-person) |
| One Document root: P 707, H1 1, Figure 1, H2 10, TOC 1, H3 27, Caption 2, Table 2, L 3, H4 16, Div 1, Sect 1, Document 1 | see Automated Checks | [Automated Checks](#automated-checks) |
| Fonts: embedded and mapped to Unicode: 1 not embedded · 0 without ToUnicode | see §5 | [§5](#5-fonts) |
| elements still outside the Document | see §13 | [§13](#13-deferred-by-the-executor) |
| … and 5 more | | §12 |

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
| Empty tags removed when proven empty | **CHECK** | 13 removed · 1 kept: something refers to them or they carry an attribute (listed) |
| Tag-tree index points only into the tree | OK | 0 dangling entries · 0 stale entries (marked content no longer drawn) |
| No empty tables | OK | none |
| No empty tags | OK | 0 empty tags |
| No paragraph holding only figures | OK | none |
| Every caption grouped with its figure | **CHECK** | PDF 75 (printed 62) (caption inside root), PDF 75 (printed 62) (caption inside root) |
| No link whose only text is a URL | OK | none |
| Tag tree consistent | OK | 0 missing · 0 mismatched |
| All marked text reachable from the tag tree | OK | 0 orphan runs |
| One Document root | **CHECK** | P 707, H1 1, Figure 1, H2 10, TOC 1, H3 27, Caption 2, Table 2, L 3, H4 16, Div 1, Sect 1, Document 1 |
| Every link tied to its text and described | OK | 0 unresolved · 0 without description · 0 pointing to no annotation |
| No link nested inside another | OK | 0 |
| Headings: no skipped levels | OK | H1 1 · H2 11 · H3 27 · H4 16 |
| Headings: exactly one H1 (the title) | OK | 1 H1 (several H1s usually mean parts or chapters were not demoted) |
| Figures: none with empty or placeholder alt | OK | 3 figures, 0 placeholder |
| Every Note has a unique ID | OK | 0 notes · 0 without ID · 0 duplicate · 0 not in the ID tree |
| Bookmarks present (documents over 9 pages) | OK | 11 bookmarks |
| Model reply held one work order | OK | one |
| Executor applied every decision | OK | 0 rejected · 0 failed (listed under "Decisions not applied") |
| Nothing deferred by the executor | **CHECK** | 1 deferred (listed under "Deferred by the executor") |
| Fonts: every glyph defined (no .notdef) | OK | none found |
| Fonts: every embedded font program could be read | OK | all read |
| Fonts: embedded and mapped to Unicode | **CHECK** | 1 not embedded · 0 without ToUnicode |
| Tab order follows the tag structure on pages with links or other annotations | OK | 0 of 25 pages with annotations lack /Tabs /S |
| Characters with no Unicode value (checklist 3.6) | OK | 0 read-aloud characters with no Unicode value |
| Private-use characters (checklist 3.6) | OK | 0 read-aloud characters with private-use codes |
| Title and language set | OK | "Language and Truth in North Korea" · en-US |
| veraPDF WCAG 2.2 (machine): no WCAG failures | OK | before: 0 WCAG rules failed (0 checks) → after: 0 WCAG rules failed (0 checks) · 1 PDF/UA-only rules not counted |
| veraPDF: no rule newly failing or failing more often | OK | 0 fixed · 1 still failing · 0 newly failing |
| Alt text: none like a file name or repeated on many figures (1.1.1) | OK | 0 of 3 figures flagged |
| Tables: every table has header cells (1.3.1) | OK | none without |
| Reading order: no page jumps back up a column (1.3.2) | OK | 0 of 231 pages flagged |
| Reading order: no section moved away from its printed place by this run (1.3.2) | OK | 0 new · 1 already in the original, of 7 sections and blocks |
| Title is not a file name or placeholder (2.4.2) | OK | "Language and Truth in North Korea" |
| Link text: none like "click here" (2.4.4) | OK | 0 generic |
| Headings: none empty, very long or repeated in a row (2.4.6) | OK | 0 empty · 0 long · 0 repeated |

## For a Person to Check

### 1. Alt Text Written or Changed by the AI (3)

| Page | Before | After |
|---|---|---|
| PDF 1 (printed Cover) | Cover Page of Language and Truth in North Korea

Author: Sonia Ryang\x00 | Book cover of Language and Truth in North Korea by Sonia Ryang. A map of the Korean peninsula, with the north colored blue and red-and-white like the North Korean flag with its red star, and a bronze statue of a man in a long coat with one arm raised in front. Faint Korean characters fill the beige background. The title is printed in red at the top and the author's name at the bottom. |
| PDF 4 (printed iii) | Logo of University of Hawai‘i Press\x00 | University of Hawai‘i Press logo |
| PDF 5 (printed iv) | Creative Commons logo\x00 | Creative Commons Attribution-NonCommercial-NoDerivatives (CC BY-NC-ND) license logo |

### 2. Elements Retyped by the AI (58)

Check each one is (or is not) a heading as decided.

| Page | Text | Before | After |
|---|---|---|---|
| PDF 2 (printed i) | LANGUAGE AND TRUTH IN NORTH KOREA | H1 | P |
| PDF 6 (printed v) | Contents | H1 | H2 |
| PDF 8 (printed vii) | Acknowledgments | H1 | H2 |
| PDF 12 (printed xi) | LANGUAGE AND TRUTH IN NORTH KOREA | H1 | P |
| PDF 14 (printed 1) | INTRODUCTION Truth | H1 | H2 |
| PDF 14 (printed 1) | Overture | H2 | H3 |
| PDF 17 (printed 4) | Dominant Discourse in North Korea | H2 | H3 |
| PDF 21 (printed 8) | Anthropology as Method | H2 | H3 |
| PDF 28 (printed 15) | Language as Formula | H2 | H3 |
| PDF 35 (printed 22) | Outline of Chapters | H2 | H3 |
| PDF 39 (printed 26) | CHAPTER 1 Purge | H1 | H2 |
| PDF 39 (printed 26) | Historical Background | H2 | H3 |
| PDF 43 (printed 30) | Language of the Purge | H2 | H3 |
| PDF 50 (printed 37) | Peers and Reviewers | H2 | H3 |
| PDF 56 (printed 43) | The Demise of Diversity | H2 | H3 |
| PDF 62 (printed 49) | CHAPTER 2 Words | H1 | H2 |
| PDF 62 (printed 49) | Linguistic Reforms | H2 | H3 |
| PDF 68 (printed 55) | The Guidebook | H2 | H3 |
| PDF 75 (printed 62) | Table 1. Hamgyeong dialect | H2 | Caption |
| PDF 75 (printed 62) | Table 2. Pyeongan dialect | H2 | Caption |
| PDF 76 (printed 63) | Juche and the Red Book | H2 | H3 |
| PDF 86 (printed 73) | Linguistic Manual | H2 | H3 |
| PDF 94 (printed 81) | Vocabulary Management | H2 | H3 |
| PDF 100 (printed 87) | Language’s New Role | H2 | H3 |
| PDF 107 (printed 94) | CHAPTER 3 The Chronicle | H1 | H2 |
| PDF 107 (printed 94) | The Question of Truth | H2 | H3 |
| PDF 115 (printed 102) | Good Government of the Details | H2 | H3 |
| PDF 115 (printed 102) | In a Mountain Village | H3 | H4 |
| PDF 117 (printed 104) | Building an Industrial City | H3 | H4 |
| PDF 122 (printed 109) | Parenting Each and Every One | H2 | H3 |
| PDF 122 (printed 109) | A Story of Orphans | H3 | H4 |
| PDF 124 (printed 111) | Veterans’ Stories | H3 | H4 |
| PDF 127 (printed 114) | Stories from the Peripheries | H3 | H4 |
| PDF 133 (printed 120) | Kim Il Sung and Women | H2 | H3 |
| PDF 133 (printed 120) | Giving New Names | H3 | H4 |
| PDF 135 (printed 122) | Mentoring Women | H3 | H4 |
| PDF 140 (printed 127) | Native Truth | H2 | H3 |
| PDF 150 (printed 137) | CHAPTER 4 The Memoirs | H1 | H2 |
| PDF 150 (printed 137) | Locating Authenticity | H2 | H3 |
| PDF 155 (printed 142) | The Native Reader | H2 | H3 |
| PDF 155 (printed 142) | Background | H3 | H4 |
| PDF 160 (printed 147) | Becoming Native | H3 | H4 |
| PDF 164 (printed 151) | All Too Human | H2 | H3 |
| PDF 164 (printed 151) | Life in Exile | H3 | H4 |
| PDF 166 (printed 153) | An Inexperienced Youth | H3 | H4 |
| PDF 170 (printed 157) | Sinophilia | H3 | H4 |
| PDF 173 (printed 160) | Mother | H3 | H4 |
| PDF 176 (printed 163) | Faith and Beliefs | H3 | H4 |
| PDF 178 (printed 165) | Not the Best nor the Only | H3 | H4 |
| PDF 179 (printed 166) | Reviving Abolished Words | H3 | H4 |
| PDF 181 (printed 168) | Rehumanizing Kim Il Sung | H2 | H3 |
| PDF 187 (printed 174) | CONCLUSION Self | H1 | H2 |
| PDF 187 (printed 174) | New Nation, New Truth | H2 | H3 |
| PDF 193 (printed 180) | Self | H2 | H3 |
| PDF 203 (printed 190) | Final Note: The Anthropology of North Korea | H2 | H3 |
| PDF 208 (printed 195) | References | H1 | H2 |
| PDF 228 (printed 215) | Index | H1 | H2 |
| PDF 238 (printed 225) | About the Author | H1 | H2 |

### 3. Lists and Tables

- Flattened list on PDF 216 (printed 203): "1. Pyongyang: Joseon rodongdang chulpansa. ———. 1992b. Hoegorok: Segiwa deobureo (With the Century…" (bibliography entries (publisher lines of References) tagged as a numbered list, not a real list)
- Header cells marked by the AI on PDF 75 (printed 62): 1 header row(s), 0 header column(s), 0 cells changed to header cells. Check they are the real headers.
- Header cells marked by the AI on PDF 75 (printed 62): 1 header row(s), 0 header column(s), 0 cells changed to header cells. Check they are the real headers.

Tables kept as tables (2): check header cells and reading order.

- PDF 75 (printed 62): 16 rows × 3 columns, 3 header cells. "English | Hamgyeong dialect | Standardized Korean"
- PDF 75 (printed 62): 16 rows × 3 columns, 3 header cells. "English | Pyeongan dialect | Standardized Korean"

### 4. Reading Order Changes

Listen through these spots with a screen reader.

- Cover figure moved to the start of the document

### 5. Fonts

The pipeline changes no other font: it never embeds one, replaces a visible one, or rewrites text. These need a person:

- **Not embedded** (1): Times-Roman. PDF/UA requires embedded fonts (7.21.4.1); a person must embed them with a PDF tool (e.g. Acrobat Preflight) and check that no page changes.

### 6. Links Whose Description Was Only a URL (14)

The description (what a screen reader announces) was set to the book's own sentence around the link, with the URL removed. No words were added and the visible URL is unchanged. Replace any of these with a better description if needed.

| Page | URL | Description now |
|---|---|---|
| PDF 152 (printed 139) | http://www.korea-dpr.info/lib/202.pdf | An English translation of the complete set is available in PDF format on North Korea’s official state website. |
| PDF 210 (printed 197) | https://www.dailynk.com/english/north-korean-history-through-the-l/ | “North Korean History through the Lens of Soviet Power,”. |
| PDF 213 (printed 200) | https://web.archive.org/web/20031217175315/ | Online: (retrieved February 22, 2019). |
| PDF 213 (printed 200) | http://www.iaea.org/Publications/Documents/Infcircs/Others/infcirc457.pdf | Online: (retrieved February 22, 2019). |
| PDF 214 (printed 201) | https://jbpress.ismedia.jp/articles/-/59068 | Online: (accessed March 9, 2020). |
| PDF 216 (printed 203) | https://www.marxists.org/archive/kim-il-sung/1955/12/28.htm | Online: (accessed June 25, 2019). |
| PDF 217 (printed 204) | http://www.korea-dpr.info/lib/103.pdf | Online: (accessed June 27, 2018). |
| PDF 218 (printed 205) | http://www.nukestrat.com/korea/koreahistory.htm | “A History of US Nuclear Weapons in South Korea.” The. |
| PDF 218 (printed 205) | https://www.latimes.com/archives/la-xpm-1986-09-27-mn-10375-story.html | “Nakasone Apologizes to Americans for March 9, 2020). |
| PDF 220 (printed 207) | https://apjjf.org/-C.-Douglas-Lummis/2474/article.html | “Ruth Benedict’s Obituary for Japanese Culture.” Japan. |
| PDF 222 (printed 209) | http://www.reuters.com/article/us-northkorea-defector-kim-clapton-idUSKBN15I132 | “Wonderful Tonight: Taking Kim Jong Un’s Brother to a (accessed August 1, 2017). |
| PDF 222 (printed 209) | http://www.apu.ac.jp/iaaps/modules/publication/apw/vol1/no2/content0002.html/ | “To Be or Not to Be—in Japan and Beyond: Summing Up and Sizing (accessed February 24, 2019). |
| PDF 223 (printed 210) | https://apjjf.org/2016/15/Ryang.html | “The Rise and Fall of Chongryun—from Chōsenjin to Zainichi and. |
| PDF 224 (printed 211) | https://archive.ph/20061009231151/http://vn.vladnews.ru/Arch/2003/ISS345/News/upd10.HTM#selection-447.0%E2%80%93447.14 | Vladivostok Novosti. |

### 7. Empty Tags (13 removed, 1 kept)

A tag is removed only when proven empty: nothing under it holds content, it carries no Alt, ActualText, E or ID, and nothing in the file refers to it except its parent. Table cells are never removed one by one; a table goes only when every part is empty.

- Removed: 13 P
- **Kept, empty: P (page: not on this tag)**, because carries /ActualText "Library of Congress Cataloging-in-Publication Data ".

### 8. Tag-tree Index Entries Cleared (1994)

Entries that pointed at a tag no longer in the tag tree (left by the source file, or by a tag the run removed). Nothing reads such a tag; no page, text or reachable tag changed.

- ParentTree, entries not tied to page content (annotations, forms, or keys nothing uses): key 4 (Link), key 5 (Link), key 151 (Link), key 207 (Link), key 208 (Link), key 210 (Link), key 211 (Link), key 213 (Link), key 214 (Link), key 215 (Link), key 219 (Link), key 220 (Link), key 221 (Link), key 222 (Link), key 224 (Link), key 225 (Link), key 226 (Link), key 229 (Link), key 231 (Link), key 232 (Link), key 233 (Link), key 234 (Link), key 235 (Link), key 237 (Link), key 238 (Link), key 239 (Link), key 240 (Link), key 241 (Link), key 242 (Link), key 244 (Link), key 245 (Link), key 246 (Link), key 247 (Link), key 249 (Link), key 250 (Link), key 252 (Link), key 253 (Link), key 255 (Link), key 256 (Link), key 257 (Link), key 258 (Link), key 259 (Link), key 260 (Link), key 261 (Link), key 262 (Link), key 263 (Link), key 264 (Link), key 265 (Link), key 266 (Link), key 268 (Link), key 269 (Link), key 271 (Link), key 272 (Link), key 273 (Link), key 274 (Link), key 275 (Link), key 276 (Link), key 277 (Link), key 281 (Link), key 282 (Link), key 283 (Link), key 284 (Link), key 285 (Link), key 286 (Link), key 287 (Link), key 288 (Link), key 289 (Link), key 290 (Link), key 291 (Link), key 292 (Link), key 293 (Link), key 294 (Link), key 295 (Link), key 296 (Link), key 297 (Link), key 298 (Link), key 299 (Link), key 300 (Link), key 301 (Link), key 302 (Link), key 303 (Link), key 304 (Link), key 305 (Link), key 306 (Link), key 307 (Link), key 308 (Link), key 309 (Link), key 310 (Link), key 311 (Link), key 312 (Link), key 313 (Link), key 314 (Link), key 315 (Link), key 316 (Link), key 317 (Link), key 318 (Link), key 319 (Link), key 320 (Link), key 321 (Link), key 322 (Link), key 323 (Link), key 324 (Link), key 325 (Link), key 326 (Link), key 327 (Link), key 328 (Link), key 329 (Link), key 330 (Link), key 331 (Link), key 332 (Link), key 333 (Link), key 334 (Link), key 335 (Link), key 336 (Link), key 337 (Link), key 338 (Link), key 339 (Link), key 340 (Link), key 341 (Link), key 342 (Link), key 343 (Link), key 344 (Link), key 345 (Link), key 346 (Link), key 347 (Link), key 348 (Link), key 349 (Link), key 350 (Link), key 351 (Link), key 352 (Link), key 353 (Link), key 354 (Link), key 355 (Link), key 356 (Link), key 357 (Link), key 358 (Link), key 359 (Link), key 360 (Link), key 361 (Link), key 362 (Link), key 363 (Link), key 364 (Link), key 365 (Link), key 366 (Link), key 367 (Link), key 368 (Link), key 369 (Link), key 370 (Link), key 371 (Link), key 372 (Link), key 373 (Link), key 374 (Link), key 375 (Link), key 376 (Link), key 377 (Link), key 378 (Link), key 379 (Link), key 380 (Link), key 381 (Link), key 382 (Link), key 383 (Link), key 384 (Link), key 385 (Link), key 386 (Link), key 387 (Link), key 388 (Link), key 389 (Link), key 390 (Link), key 391 (Link), key 392 (Link), key 393 (Link), key 394 (Link), key 395 (Link), key 396 (Link), key 397 (Link), key 398 (Link), key 399 (Link), key 400 (Link), key 401 (Link), key 402 (Link), key 403 (Link), key 404 (Link), key 405 (Link), key 406 (Link), key 407 (Link), key 408 (Link), key 409 (Link), key 410 (Link), key 411 (Link), key 412 (Link), key 413 (Link), key 414 (Link), key 415 (Link), key 416 (Link), key 417 (Link), key 418 (Link), key 419 (Link), key 420 (Link), key 421 (Link), key 422 (Link), key 423 (Link), key 424 (Link), key 425 (Link), key 426 (Link), key 427 (Link), key 428 (Link), key 429 (Link), key 430 (Link), key 431 (Link), key 432 (Link), key 433 (Link), key 434 (Link), key 435 (Link), key 436 (Link), key 437 (Link), key 438 (Link), key 439 (Link), key 440 (Link), key 441 (Link), key 442 (Link), key 443 (Link), key 444 (Link), key 445 (Link), key 446 (Link), key 447 (Link), key 448 (Link), key 449 (Link), key 450 (Link), key 451 (Link), key 452 (Link), key 453 (Link), key 454 (Link), key 455 (Link), key 456 (Link), key 457 (Link), key 459 (Link), key 460 (Link), key 461 (Link), key 462 (Link), key 463 (Link), key 464 (Link), key 465 (Link), key 466 (Link), key 467 (Link), key 468 (Link), key 469 (Link), key 470 (Link), key 471 (Link), key 472 (Link), key 473 (Link), key 474 (Link), key 475 (Link), key 476 (Link), key 477 (Link), key 478 (Link), key 479 (Link), key 480 (Link), key 481 (Link), key 482 (Link), key 483 (Link), key 484 (Link), key 485 (Link), key 486 (Link), key 487 (Link), key 488 (Link), key 489 (Link), key 490 (Link), key 491 (Link), key 492 (Link), key 493 (Link), key 494 (Link), key 495 (Link), key 496 (Link), key 497 (Link), key 498 (Link), key 499 (Link), key 500 (Link), key 501 (Link), key 502 (Link), key 503 (Link), key 504 (Link), key 505 (Link), key 506 (Link), key 507 (Link), key 508 (Link), key 509 (Link), key 510 (Link), key 511 (Link), key 512 (Link), key 513 (Link), key 514 (Link), key 515 (Link), key 516 (Link), key 517 (Link), key 518 (Link), key 519 (Link), key 520 (Link), key 521 (Link), key 522 (Link), key 523 (Link), key 524 (Link), key 525 (Link), key 526 (Link), key 527 (Link), key 528 (Link), key 529 (Link), key 530 (Link), key 531 (Link), key 532 (Link), key 533 (Link), key 534 (Link), key 535 (Link), key 536 (Link), key 537 (Link), key 538 (Link), key 539 (Link), key 540 (Link), key 541 (Link), key 542 (Link), key 543 (Link), key 544 (Link), key 545 (Link), key 546 (Link), key 547 (Link), key 548 (Link), key 549 (Link), key 550 (Link), key 551 (Link), key 552 (Link), key 553 (Link), key 554 (Link), key 555 (Link), key 556 (Link), key 557 (Link), key 558 (Link), key 559 (Link), key 560 (Link), key 561 (Link), key 562 (Link), key 563 (Link), key 564 (Link), key 565 (Link), key 566 (Link), key 567 (Link), key 568 (Link), key 569 (Link), key 570 (Link), key 571 (Link), key 572 (Link), key 573 (Link), key 574 (Link), key 575 (Link), key 576 (Link), key 577 (Link), key 578 (Link), key 579 (Link), key 580 (Link), key 581 (Link), key 582 (Link), key 583 (Link), key 584 (Link), key 585 (Link), key 586 (Link), key 587 (Link), key 588 (Link), key 589 (Link), key 590 (Link), key 591 (Link), key 592 (Link), key 593 (Link), key 594 (Link), key 595 (Link), key 596 (Link), key 597 (Link), key 598 (Link), key 599 (Link), key 600 (Link), key 601 (Link), key 602 (Link), key 603 (Link), key 604 (Link), key 605 (Link), key 606 (Link), key 607 (Link), key 608 (Link), key 609 (Link), key 610 (Link), key 611 (Link), key 612 (Link), key 613 (Link), key 614 (Link), key 615 (Link), key 616 (Link), key 617 (Link), key 618 (Link), key 619 (Link), key 620 (Link), key 621 (Link), key 622 (Link), key 623 (Link), key 624 (Link), key 625 (Link), key 626 (Link), key 627 (Link), key 628 (Link), key 629 (Link), key 630 (Link), key 631 (Link), key 632 (Link), key 633 (Link), key 634 (Link), key 635 (Link), key 636 (Link), key 637 (Link), key 638 (Link), key 639 (Link), key 640 (Link), key 641 (Link), key 642 (Link), key 643 (Link), key 644 (Link), key 645 (Link), key 646 (Link), key 647 (Link), key 648 (Link), key 649 (Link), key 650 (Link), key 651 (Link), key 652 (Link), key 653 (Link), key 654 (Link), key 655 (Link), key 656 (Link), key 657 (Link), key 658 (Link), key 659 (Link), key 660 (Link), key 661 (Link), key 662 (Link), key 663 (Link), key 664 (Link), key 665 (Link), key 666 (Link), key 667 (Link), key 668 (Link), key 669 (Link), key 670 (Link), key 671 (Link), key 672 (Link), key 673 (Link), key 674 (Link), key 675 (Link), key 676 (Link), key 677 (Link), key 678 (Link), key 679 (Link), key 680 (Link), key 681 (Link), key 682 (Link), key 683 (Link), key 684 (Link), key 685 (Link), key 686 (Link), key 687 (Link), key 688 (Link), key 689 (Link), key 690 (Link), key 691 (Link), key 693 (Link), key 694 (Link), key 695 (Link), key 696 (Link), key 697 (Link), key 698 (Link), key 699 (Link), key 700 (Link), key 701 (Link), key 702 (Link), key 703 (Link), key 704 (Link), key 705 (Link), key 706 (Link), key 707 (Link), key 708 (Link), key 709 (Link), key 710 (Link), key 711 (Link), key 712 (Link), key 713 (Link), key 714 (Link), key 715 (Link), key 716 (Link), key 717 (Link), key 718 (Link), key 719 (Link), key 720 (Link), key 721 (Link), key 722 (Link), key 723 (Link), key 724 (Link), key 725 (Link), key 726 (Link), key 727 (Link), key 728 (Link), key 729 (Link), key 730 (Link), key 731 (Link), key 732 (Link), key 733 (Link), key 734 (Link), key 735 (Link), key 736 (Link), key 737 (Link), key 738 (Link), key 739 (Link), key 740 (Link), key 741 (Link), key 742 (Link), key 743 (Link), key 744 (Link), key 745 (Link), key 746 (Link), key 747 (Link), key 748 (Link), key 749 (Link), key 750 (Link), key 751 (Link), key 752 (Link), key 753 (Link), key 754 (Link), key 755 (Link), key 756 (Link), key 757 (Link), key 758 (Link), key 759 (Link), key 760 (Link), key 761 (Link), key 762 (Link), key 763 (Link), key 764 (Link), key 765 (Link), key 766 (Link), key 767 (Link), key 768 (Link), key 769 (Link), key 770 (Link), key 771 (Link), key 772 (Link), key 773 (Link), key 774 (Link), key 775 (Link), key 776 (Link), key 777 (Link), key 778 (Link), key 779 (Link), key 780 (Link), key 781 (Link), key 782 (Link), key 783 (Link), key 784 (Link), key 785 (Link), key 786 (Link), key 787 (Link), key 788 (Link), key 789 (Link), key 790 (Link), key 791 (Link), key 792 (Link), key 793 (Link), key 794 (Link), key 795 (Link), key 796 (Link), key 797 (Link), key 798 (Link), key 799 (Link), key 800 (Link), key 801 (Link), key 802 (Link), key 803 (Link), key 804 (Link), key 805 (Link), key 806 (Link), key 807 (Link), key 808 (Link), key 809 (Link), key 810 (Link), key 811 (Link), key 812 (Link), key 813 (Link), key 814 (Link), key 815 (Link), key 816 (Link), key 817 (Link), key 818 (Link), key 819 (Link), key 820 (Link), key 821 (Link), key 822 (Link), key 823 (Link), key 824 (Link), key 825 (Link), key 826 (Link), key 827 (Link), key 828 (Link), key 829 (Link), key 830 (Link), key 831 (Link), key 832 (Link), key 833 (Link), key 834 (Link), key 835 (Link), key 836 (Link), key 837 (Link), key 838 (Link), key 839 (Link), key 840 (Link), key 841 (Link), key 842 (Link), key 843 (Link), key 844 (Link), key 845 (Link), key 846 (Link), key 847 (Link), key 848 (Link), key 849 (Link), key 850 (Link), key 851 (Link), key 852 (Link), key 853 (Link), key 854 (Link), key 855 (Link), key 856 (Link), key 857 (Link), key 858 (Link), key 859 (Link), key 860 (Link), key 861 (Link), key 862 (Link), key 863 (Link), key 864 (Link), key 865 (Link), key 866 (Link), key 867 (Link), key 868 (Link), key 869 (Link), key 870 (Link), key 871 (Link), key 872 (Link), key 873 (Link), key 874 (Link), key 875 (Link), key 876 (Link), key 877 (Link), key 878 (Link), key 879 (Link), key 880 (Link), key 881 (Link), key 882 (Link), key 883 (Link), key 884 (Link), key 885 (Link), key 886 (Link), key 887 (Link), key 888 (Link), key 889 (Link), key 890 (Link), key 891 (Link), key 892 (Link), key 893 (Link), key 894 (Link), key 895 (Link), key 896 (Link), key 897 (Link), key 898 (Link), key 899 (Link), key 900 (Link), key 901 (Link), key 902 (Link), key 903 (Link), key 904 (Link), key 905 (Link), key 906 (Link), key 907 (Link), key 908 (Link), key 909 (Link), key 910 (Link), key 911 (Link), key 912 (Link), key 913 (Link), key 914 (Link), key 915 (Link), key 916 (Link), key 917 (Link), key 918 (Link), key 919 (Link), key 920 (Link), key 921 (Link), key 922 (Link), key 923 (Link), key 924 (Link), key 925 (Link), key 926 (Link), key 927 (Link), key 928 (Link), key 929 (Link), key 930 (Link), key 931 (Link), key 933 (Link), key 934 (Link), key 935 (Link), key 936 (Link), key 937 (Link), key 938 (Link), key 939 (Link), key 940 (Link), key 941 (Link), key 942 (Link), key 943 (Link), key 944 (Link), key 945 (Link), key 946 (Link), key 947 (Link), key 948 (Link), key 949 (Link), key 950 (Link), key 951 (Link), key 952 (Link), key 953 (Link), key 954 (Link), key 955 (Link), key 956 (Link), key 957 (Link), key 958 (Link), key 959 (Link), key 960 (Link), key 961 (Link), key 962 (Link), key 963 (Link), key 964 (Link), key 965 (Link), key 966 (Link), key 967 (Link), key 968 (Link), key 969 (Link), key 970 (Link), key 971 (Link), key 972 (Link), key 973 (Link), key 974 (Link), key 975 (Link), key 976 (Link), key 977 (Link), key 978 (Link), key 979 (Link), key 980 (Link), key 981 (Link), key 982 (Link), key 983 (Link), key 984 (Link), key 985 (Link), key 986 (Link), key 987 (Link), key 988 (Link), key 989 (Link), key 990 (Link), key 991 (Link), key 992 (Link), key 993 (Link), key 994 (Link), key 995 (Link), key 996 (Link), key 997 (Link), key 998 (Link), key 999 (Link), key 1000 (Link), key 1001 (Link), key 1002 (Link), key 1003 (Link), key 1004 (Link), key 1005 (Link), key 1006 (Link), key 1007 (Link), key 1008 (Link), key 1009 (Link), key 1010 (Link), key 1011 (Link), key 1012 (Link), key 1013 (Link), key 1014 (Link), key 1015 (Link), key 1016 (Link), key 1017 (Link), key 1018 (Link), key 1019 (Link), key 1020 (Link), key 1021 (Link), key 1022 (Link), key 1023 (Link), key 1024 (Link), key 1025 (Link), key 1026 (Link), key 1027 (Link), key 1028 (Link), key 1029 (Link), key 1030 (Link), key 1031 (Link), key 1032 (Link), key 1033 (Link), key 1034 (Link), key 1035 (Link), key 1036 (Link), key 1037 (Link), key 1038 (Link), key 1039 (Link), key 1040 (Link), key 1041 (Link), key 1042 (Link), key 1043 (Link), key 1044 (Link), key 1045 (Link), key 1046 (Link), key 1047 (Link), key 1048 (Link), key 1049 (Link), key 1050 (Link), key 1051 (Link), key 1052 (Link), key 1053 (Link), key 1054 (Link), key 1055 (Link), key 1056 (Link), key 1057 (Link), key 1058 (Link), key 1059 (Link), key 1060 (Link), key 1061 (Link), key 1062 (Link), key 1063 (Link), key 1064 (Link), key 1065 (Link), key 1066 (Link), key 1067 (Link), key 1068 (Link), key 1069 (Link), key 1070 (Link), key 1071 (Link), key 1072 (Link), key 1073 (Link), key 1074 (Link), key 1075 (Link), key 1076 (Link), key 1077 (Link), key 1078 (Link), key 1079 (Link), key 1080 (Link), key 1081 (Link), key 1082 (Link), key 1083 (Link), key 1084 (Link), key 1085 (Link), key 1086 (Link), key 1087 (Link), key 1088 (Link), key 1089 (Link), key 1090 (Link), key 1091 (Link), key 1092 (Link), key 1093 (Link), key 1094 (Link), key 1095 (Link), key 1096 (Link), key 1097 (Link), key 1098 (Link), key 1099 (Link), key 1100 (Link), key 1101 (Link), key 1102 (Link), key 1103 (Link), key 1104 (Link), key 1105 (Link), key 1106 (Link), key 1107 (Link), key 1108 (Link), key 1109 (Link), key 1110 (Link), key 1111 (Link), key 1112 (Link), key 1113 (Link), key 1114 (Link), key 1115 (Link), key 1116 (Link), key 1117 (Link), key 1118 (Link), key 1119 (Link), key 1120 (Link), key 1121 (Link), key 1122 (Link), key 1123 (Link), key 1124 (Link), key 1125 (Link), key 1126 (Link), key 1127 (Link), key 1128 (Link), key 1129 (Link), key 1130 (Link), key 1131 (Link), key 1132 (Link), key 1133 (Link), key 1134 (Link), key 1135 (Link), key 1136 (Link), key 1137 (Link), key 1138 (Link), key 1139 (Link), key 1140 (Link), key 1141 (Link), key 1142 (Link), key 1143 (Link), key 1144 (Link), key 1145 (Link), key 1146 (Link), key 1147 (Link), key 1148 (Link), key 1149 (Link), key 1150 (Link), key 1151 (Link), key 1152 (Link), key 1153 (Link), key 1154 (Link), key 1155 (Link), key 1156 (Link), key 1157 (Link), key 1158 (Link), key 1159 (Link), key 1160 (Link), key 1161 (Link), key 1162 (Link), key 1163 (Link), key 1164 (Link), key 1165 (Link), key 1166 (Link), key 1167 (Link), key 1168 (Link), key 1169 (Link), key 1170 (Link), key 1171 (Link), key 1172 (Link), key 1173 (Link), key 1174 (Link), key 1175 (Link), key 1176 (Link), key 1177 (Link), key 1178 (Link), key 1179 (Link), key 1180 (Link), key 1181 (Link), key 1182 (Link), key 1183 (Link), key 1184 (Link), key 1185 (Link), key 1186 (Link), key 1187 (Link), key 1188 (Link), key 1189 (Link), key 1190 (Link), key 1191 (Link), key 1192 (Link), key 1193 (Link), key 1194 (Link), key 1195 (Link), key 1196 (Link), key 1197 (Link), key 1198 (Link), key 1199 (Link), key 1200 (Link), key 1201 (Link), key 1202 (Link), key 1203 (Link), key 1204 (Link), key 1205 (Link), key 1206 (Link), key 1207 (Link), key 1209 (Link), key 1210 (Link), key 1211 (Link), key 1212 (Link), key 1213 (Link), key 1214 (Link), key 1215 (Link), key 1216 (Link), key 1217 (Link), key 1218 (Link), key 1219 (Link), key 1220 (Link), key 1221 (Link), key 1222 (Link), key 1223 (Link), key 1224 (Link), key 1225 (Link), key 1226 (Link), key 1227 (Link), key 1228 (Link), key 1229 (Link), key 1230 (Link), key 1231 (Link), key 1232 (Link), key 1233 (Link), key 1234 (Link), key 1235 (Link), key 1236 (Link), key 1237 (Link), key 1238 (Link), key 1239 (Link), key 1240 (Link), key 1241 (Link), key 1242 (Link), key 1243 (Link), key 1244 (Link), key 1245 (Link), key 1246 (Link), key 1247 (Link), key 1248 (Link), key 1249 (Link), key 1250 (Link), key 1251 (Link), key 1252 (Link), key 1253 (Link), key 1254 (Link), key 1255 (Link), key 1256 (Link), key 1257 (Link), key 1258 (Link), key 1259 (Link), key 1260 (Link), key 1261 (Link), key 1262 (Link), key 1263 (Link), key 1264 (Link), key 1265 (Link), key 1266 (Link), key 1267 (Link), key 1268 (Link), key 1269 (Link), key 1270 (Link), key 1271 (Link), key 1272 (Link), key 1273 (Link), key 1274 (Link), key 1275 (Link), key 1276 (Link), key 1277 (Link), key 1278 (Link), key 1279 (Link), key 1280 (Link), key 1281 (Link), key 1282 (Link), key 1283 (Link), key 1284 (Link), key 1285 (Link), key 1286 (Link), key 1287 (Link), key 1288 (Link), key 1289 (Link), key 1290 (Link), key 1291 (Link), key 1292 (Link), key 1293 (Link), key 1294 (Link), key 1295 (Link), key 1296 (Link), key 1297 (Link), key 1298 (Link), key 1299 (Link), key 1300 (Link), key 1301 (Link), key 1302 (Link), key 1303 (Link), key 1304 (Link), key 1305 (Link), key 1306 (Link), key 1307 (Link), key 1308 (Link), key 1309 (Link), key 1310 (Link), key 1311 (Link), key 1312 (Link), key 1313 (Link), key 1314 (Link), key 1315 (Link), key 1316 (Link), key 1317 (Link), key 1318 (Link), key 1319 (Link), key 1320 (Link), key 1321 (Link), key 1322 (Link), key 1323 (Link), key 1324 (Link), key 1325 (Link), key 1326 (Link), key 1327 (Link), key 1328 (Link), key 1329 (Link), key 1330 (Link), key 1331 (Link), key 1332 (Link), key 1333 (Link), key 1334 (Link), key 1335 (Link), key 1336 (Link), key 1337 (Link), key 1338 (Link), key 1339 (Link), key 1340 (Link), key 1341 (Link), key 1342 (Link), key 1343 (Link), key 1344 (Link), key 1345 (Link), key 1346 (Link), key 1347 (Link), key 1348 (Link), key 1349 (Link), key 1350 (Link), key 1351 (Link), key 1352 (Link), key 1353 (Link), key 1354 (Link), key 1355 (Link), key 1356 (Link), key 1357 (Link), key 1358 (Link), key 1359 (Link), key 1360 (Link), key 1361 (Link), key 1362 (Link), key 1363 (Link), key 1364 (Link), key 1365 (Link), key 1366 (Link), key 1367 (Link), key 1368 (Link), key 1369 (Link), key 1370 (Link), key 1371 (Link), key 1372 (Link), key 1373 (Link), key 1374 (Link), key 1375 (Link), key 1376 (Link), key 1377 (Link), key 1378 (Link), key 1379 (Link), key 1380 (Link), key 1381 (Link), key 1382 (Link), key 1383 (Link), key 1384 (Link), key 1385 (Link), key 1386 (Link), key 1387 (Link), key 1388 (Link), key 1389 (Link), key 1390 (Link), key 1391 (Link), key 1392 (Link), key 1393 (Link), key 1394 (Link), key 1395 (Link), key 1396 (Link), key 1397 (Link), key 1398 (Link), key 1399 (Link), key 1400 (Link), key 1401 (Link), key 1402 (Link), key 1403 (Link), key 1404 (Link), key 1405 (Link), key 1406 (Link), key 1407 (Link), key 1408 (Link), key 1409 (Link), key 1410 (Link), key 1411 (Link), key 1412 (Link), key 1413 (Link), key 1414 (Link), key 1415 (Link), key 1416 (Link), key 1417 (Link), key 1418 (Link), key 1419 (Link), key 1420 (Link), key 1421 (Link), key 1422 (Link), key 1423 (Link), key 1424 (Link), key 1425 (Link), key 1426 (Link), key 1427 (Link), key 1428 (Link), key 1429 (Link), key 1430 (Link), key 1431 (Link), key 1432 (Link), key 1433 (Link), key 1434 (Link), key 1435 (Link), key 1436 (Link), key 1437 (Link), key 1438 (Link), key 1439 (Link), key 1440 (Link), key 1441 (Link), key 1442 (Link), key 1443 (Link), key 1444 (Link), key 1445 (Link), key 1446 (Link), key 1447 (Link), key 1448 (Link), key 1449 (Link), key 1450 (Link), key 1451 (Link), key 1452 (Link), key 1453 (Link), key 1454 (Link), key 1455 (Link), key 1456 (Link), key 1457 (Link), key 1458 (Link), key 1459 (Link), key 1460 (Link), key 1461 (Link), key 1462 (Link), key 1463 (Link), key 1464 (Link), key 1465 (Link), key 1466 (Link), key 1467 (Link), key 1468 (Link), key 1469 (Link), key 1470 (Link), key 1471 (Link), key 1472 (Link), key 1473 (Link), key 1474 (Link), key 1475 (Link), key 1476 (Link), key 1477 (Link), key 1478 (Link), key 1479 (Link), key 1480 (Link), key 1481 (Link), key 1482 (Link), key 1483 (Link), key 1484 (Link), key 1485 (Link), key 1486 (Link), key 1487 (Link), key 1488 (Link), key 1489 (Link), key 1490 (Link), key 1491 (Link), key 1492 (Link), key 1493 (Link), key 1494 (Link), key 1495 (Link), key 1496 (Link), key 1497 (Link), key 1498 (Link), key 1500 (Link), key 1501 (Link), key 1502 (Link), key 1503 (Link), key 1504 (Link), key 1505 (Link), key 1506 (Link), key 1507 (Link), key 1508 (Link), key 1509 (Link), key 1510 (Link), key 1511 (Link), key 1512 (Link), key 1513 (Link), key 1514 (Link), key 1515 (Link), key 1516 (Link), key 1517 (Link), key 1518 (Link), key 1519 (Link), key 1520 (Link), key 1521 (Link), key 1522 (Link), key 1523 (Link), key 1524 (Link), key 1525 (Link), key 1526 (Link), key 1527 (Link), key 1528 (Link), key 1529 (Link), key 1530 (Link), key 1531 (Link), key 1532 (Link), key 1533 (Link), key 1534 (Link), key 1535 (Link), key 1536 (Link), key 1537 (Link), key 1538 (Link), key 1539 (Link), key 1540 (Link), key 1541 (Link), key 1542 (Link), key 1543 (Link), key 1544 (Link), key 1545 (Link), key 1546 (Link), key 1547 (Link), key 1548 (Link), key 1549 (Link), key 1550 (Link), key 1551 (Link), key 1552 (Link), key 1553 (Link), key 1554 (Link), key 1555 (Link), key 1556 (Link), key 1557 (Link), key 1558 (Link), key 1559 (Link), key 1560 (Link), key 1561 (Link), key 1562 (Link), key 1563 (Link), key 1564 (Link), key 1565 (Link), key 1566 (Link), key 1567 (Link), key 1568 (Link), key 1569 (Link), key 1570 (Link), key 1571 (Link), key 1572 (Link), key 1573 (Link), key 1574 (Link), key 1575 (Link), key 1576 (Link), key 1577 (Link), key 1578 (Link), key 1579 (Link), key 1580 (Link), key 1581 (Link), key 1582 (Link), key 1583 (Link), key 1584 (Link), key 1585 (Link), key 1586 (Link), key 1587 (Link), key 1588 (Link), key 1589 (Link), key 1590 (Link), key 1591 (Link), key 1592 (Link), key 1593 (Link), key 1594 (Link), key 1595 (Link), key 1596 (Link), key 1597 (Link), key 1598 (Link), key 1599 (Link), key 1600 (Link), key 1601 (Link), key 1602 (Link), key 1603 (Link), key 1604 (Link), key 1605 (Link), key 1606 (Link), key 1607 (Link), key 1608 (Link), key 1609 (Link), key 1610 (Link), key 1611 (Link), key 1612 (Link), key 1613 (Link), key 1614 (Link), key 1615 (Link), key 1616 (Link), key 1617 (Link), key 1618 (Link), key 1619 (Link), key 1620 (Link), key 1621 (Link), key 1622 (Link), key 1623 (Link), key 1624 (Link), key 1625 (Link), key 1626 (Link), key 1627 (Link), key 1628 (Link), key 1629 (Link), key 1630 (Link), key 1631 (Link), key 1632 (Link), key 1633 (Link), key 1634 (Link), key 1635 (Link), key 1636 (Link), key 1637 (Link), key 1638 (Link), key 1639 (Link), key 1640 (Link), key 1641 (Link), key 1642 (Link), key 1643 (Link), key 1644 (Link), key 1645 (Link), key 1646 (Link), key 1647 (Link), key 1648 (Link), key 1649 (Link), key 1650 (Link), key 1651 (Link), key 1652 (Link), key 1653 (Link), key 1654 (Link), key 1655 (Link), key 1656 (Link), key 1657 (Link), key 1658 (Link), key 1659 (Link), key 1660 (Link), key 1661 (Link), key 1662 (Link), key 1663 (Link), key 1664 (Link), key 1665 (Link), key 1666 (Link), key 1667 (Link), key 1668 (Link), key 1669 (Link), key 1670 (Link), key 1671 (Link), key 1672 (Link), key 1673 (Link), key 1674 (Link), key 1675 (Link), key 1676 (Link), key 1677 (Link), key 1678 (Link), key 1679 (Link), key 1680 (Link), key 1681 (Link), key 1682 (Link), key 1683 (Link), key 1684 (Link), key 1685 (Link), key 1686 (Link), key 1687 (Link), key 1688 (Link), key 1689 (Link), key 1690 (Link), key 1691 (Link), key 1692 (Link), key 1693 (Link), key 1694 (Link), key 1695 (Link), key 1696 (Link), key 1697 (Link), key 1698 (Link), key 1699 (Link), key 1700 (Link), key 1701 (Link), key 1702 (Link), key 1704 (Link), key 1705 (Link), key 1706 (Link), key 1707 (Link), key 1708 (Link), key 1709 (Link), key 1710 (Link), key 1711 (Link), key 1712 (Link), key 1713 (Link), key 1714 (Link), key 1715 (Link), key 1716 (Link), key 1717 (Link), key 1718 (Link), key 1719 (Link), key 1720 (Link), key 1721 (Link), key 1722 (Link), key 1723 (Link), key 1724 (Link), key 1725 (Link), key 1726 (Link), key 1727 (Link), key 1728 (Link), key 1729 (Link), key 1730 (Link), key 1731 (Link), key 1732 (Link), key 1733 (Link), key 1734 (Link), key 1735 (Link), key 1736 (Link), key 1737 (Link), key 1738 (Link), key 1739 (Link), key 1740 (Link), key 1741 (Link), key 1742 (Link), key 1743 (Link), key 1744 (Link), key 1745 (Link), key 1746 (Link), key 1747 (Link), key 1748 (Link), key 1749 (Link), key 1750 (Link), key 1751 (Link), key 1752 (Link), key 1753 (Link), key 1754 (Link), key 1755 (Link), key 1756 (Link), key 1757 (Link), key 1758 (Link), key 1759 (Link), key 1760 (Link), key 1761 (Link), key 1762 (Link), key 1763 (Link), key 1764 (Link), key 1765 (Link), key 1766 (Link), key 1767 (Link), key 1768 (Link), key 1769 (Link), key 1770 (Link), key 1771 (Link), key 1772 (Link), key 1773 (Link), key 1774 (Link), key 1775 (Link), key 1776 (Link), key 1777 (Link), key 1778 (Link), key 1779 (Link), key 1780 (Link), key 1781 (Link), key 1782 (Link), key 1783 (Link), key 1784 (Link), key 1785 (Link), key 1786 (Link), key 1787 (Link), key 1788 (Link), key 1789 (Link), key 1790 (Link), key 1791 (Link), key 1792 (Link), key 1793 (Link), key 1794 (Link), key 1795 (Link), key 1796 (Link), key 1797 (Link), key 1798 (Link), key 1799 (Link), key 1800 (Link), key 1801 (Link), key 1802 (Link), key 1803 (Link), key 1804 (Link), key 1805 (Link), key 1806 (Link), key 1807 (Link), key 1808 (Link), key 1809 (Link), key 1810 (Link), key 1811 (Link), key 1812 (Link), key 1813 (Link), key 1814 (Link), key 1815 (Link), key 1816 (Link), key 1817 (Link), key 1818 (Link), key 1819 (Link), key 1820 (Link), key 1821 (Link), key 1822 (Link), key 1823 (Link), key 1824 (Link), key 1825 (Link), key 1826 (Link), key 1827 (Link), key 1828 (Link), key 1829 (Link), key 1830 (Link), key 1831 (Link), key 1832 (Link), key 1833 (Link), key 1834 (Link), key 1835 (Link), key 1836 (Link), key 1837 (Link), key 1838 (Link), key 1839 (Link), key 1840 (Link), key 1841 (Link), key 1842 (Link), key 1843 (Link), key 1844 (Link), key 1845 (Link), key 1846 (Link), key 1847 (Link), key 1848 (Link), key 1849 (Link), key 1850 (Link), key 1851 (Link), key 1852 (Link), key 1853 (Link), key 1854 (Link), key 1855 (Link), key 1856 (Link), key 1857 (Link), key 1858 (Link), key 1859 (Link), key 1860 (Link), key 1861 (Link), key 1862 (Link), key 1863 (Link), key 1864 (Link), key 1865 (Link), key 1866 (Link), key 1867 (Link), key 1868 (Link), key 1869 (Link), key 1870 (Link), key 1871 (Link), key 1872 (Link), key 1873 (Link), key 1874 (Link), key 1875 (Link), key 1876 (Link), key 1877 (Link), key 1878 (Link), key 1879 (Link), key 1880 (Link), key 1881 (Link), key 1882 (Link), key 1883 (Link), key 1884 (Link), key 1885 (Link), key 1886 (Link), key 1887 (Link), key 1888 (Link), key 1889 (Link), key 1890 (Link), key 1891 (Link), key 1892 (Link), key 1893 (Link), key 1894 (Link), key 1895 (Link), key 1896 (Link), key 1897 (Link), key 1898 (Link), key 1899 (Link), key 1900 (Link), key 1901 (Link), key 1902 (Link), key 1903 (Link), key 1905 (Link), key 1906 (Link), key 1907 (Link), key 1908 (Link), key 1909 (Link), key 1910 (Link), key 1911 (Link), key 1912 (Link), key 1913 (Link), key 1914 (Link), key 1915 (Link), key 1916 (Link), key 1917 (Link), key 1918 (Link), key 1919 (Link), key 1920 (Link), key 1921 (Link), key 1922 (Link), key 1923 (Link), key 1924 (Link), key 1925 (Link), key 1926 (Link), key 1927 (Link), key 1928 (Link), key 1929 (Link), key 1930 (Link), key 1931 (Link), key 1932 (Link), key 1933 (Link), key 1934 (Link), key 1935 (Link), key 1936 (Link), key 1937 (Link), key 1938 (Link), key 1939 (Link), key 1940 (Link), key 1941 (Link), key 1942 (Link), key 1943 (Link), key 1944 (Link), key 1945 (Link), key 1946 (Link), key 1947 (Link), key 1948 (Link), key 1949 (Link), key 1950 (Link), key 1951 (Link), key 1952 (Link), key 1953 (Link), key 1954 (Link), key 1955 (Link), key 1956 (Link), key 1957 (Link), key 1958 (Link), key 1959 (Link), key 1960 (Link), key 1961 (Link), key 1962 (Link), key 1963 (Link), key 1964 (Link), key 1965 (Link), key 1966 (Link), key 1967 (Link), key 1968 (Link), key 1969 (Link), key 1970 (Link), key 1971 (Link), key 1972 (Link), key 1973 (Link), key 1974 (Link), key 1975 (Link), key 1976 (Link), key 1977 (Link), key 1978 (Link), key 1979 (Link), key 1980 (Link), key 1981 (Link), key 1982 (Link), key 1983 (Link), key 1984 (Link), key 1985 (Link), key 1986 (Link), key 1987 (Link), key 1988 (Link), key 1989 (Link), key 1990 (Link), key 1991 (Link), key 1992 (Link), key 1993 (Link), key 1994 (Link), key 1995 (Link), key 1996 (Link), key 1997 (Link), key 1998 (Link), key 1999 (Link), key 2000 (Link), key 2001 (Link), key 2002 (Link), key 2003 (Link), key 2004 (Link), key 2005 (Link), key 2006 (Link), key 2007 (Link), key 2008 (Link), key 2009 (Link), key 2010 (Link), key 2011 (Link), key 2012 (Link), key 2013 (Link), key 2014 (Link), key 2015 (Link), key 2016 (Link), key 2017 (Link), key 2018 (Link), key 2019 (Link), key 2020 (Link), key 2021 (Link), key 2022 (Link), key 2023 (Link), key 2024 (Link), key 2025 (Link), key 2026 (Link), key 2027 (Link), key 2028 (Link), key 2029 (Link), key 2030 (Link), key 2031 (Link), key 2032 (Link), key 2033 (Link), key 2034 (Link), key 2035 (Link), key 2036 (Link), key 2037 (Link), key 2038 (Link), key 2039 (Link), key 2040 (Link), key 2041 (Link), key 2042 (Link), key 2043 (Link), key 2044 (Link), key 2045 (Link), key 2046 (Link), key 2047 (Link), key 2048 (Link), key 2049 (Link), key 2050 (Link), key 2051 (Link), key 2052 (Link), key 2053 (Link), key 2054 (Link), key 2055 (Link), key 2056 (Link), key 2057 (Link), key 2058 (Link), key 2059 (Link), key 2060 (Link), key 2061 (Link), key 2062 (Link), key 2063 (Link), key 2064 (Link), key 2065 (Link), key 2066 (Link), key 2067 (Link), key 2068 (Link), key 2069 (Link), key 2070 (Link), key 2071 (Link), key 2072 (Link), key 2073 (Link), key 2074 (Link), key 2075 (Link), key 2076 (Link), key 2077 (Link), key 2078 (Link), key 2079 (Link), key 2080 (Link), key 2081 (Link), key 2082 (Link), key 2083 (Link), key 2084 (Link), key 2085 (Link), key 2086 (Link), key 2087 (Link), key 2088 (Link), key 2089 (Link), key 2090 (Link), key 2091 (Link), key 2092 (Link), key 2093 (Link), key 2094 (Link), key 2095 (Link), key 2096 (Link), key 2097 (Link), key 2098 (Link), key 2099 (Link), key 2100 (Link), key 2101 (Link), key 2102 (Link), key 2103 (Link), key 2104 (Link), key 2105 (Link), key 2106 (Link), key 2107 (Link), key 2108 (Link), key 2109 (Link), key 2110 (Link), key 2111 (Link), key 2112 (Link), key 2113 (Link), key 2114 (Link), key 2115 (Link), key 2116 (Link), key 2117 (Link), key 2118 (Link), key 2119 (Link), key 2120 (Link), key 2121 (Link), key 2122 (Link), key 2123 (Link), key 2124 (Link), key 2125 (Link), key 2126 (Link), key 2127 (Link), key 2128 (Link), key 2129 (Link), key 2130 (Link), key 2131 (Link), key 2132 (Link), key 2133 (Link), key 2134 (Link), key 2135 (Link), key 2136 (Link), key 2137 (Link), key 2138 (Link), key 2139 (Link), key 2140 (Link), key 2141 (Link), key 2142 (Link), key 2143 (Link), key 2144 (Link), key 2145 (Link), key 2146 (Link), key 2147 (Link), key 2148 (Link), key 2149 (Link), key 2150 (Link), key 2151 (Link), key 2152 (Link), key 2153 (Link), key 2154 (Link), key 2155 (Link), key 2156 (Link), key 2157 (Link), key 2158 (Link), key 2159 (Link), key 2160 (Link), key 2161 (Link), key 2162 (Link), key 2163 (Link), key 2164 (Link), key 2166 (Link), key 2167 (Link), key 2168 (Link), key 2169 (Link), key 2170 (Link), key 2171 (Link), key 2172 (Link), key 2173 (Link), key 2174 (Link), key 2175 (Link), key 2176 (Link), key 2177 (Link), key 2178 (Link), key 2179 (Link), key 2180 (Link), key 2181 (Link), key 2182 (Link), key 2183 (Link), key 2184 (Link), key 2185 (Link), key 2186 (Link), key 2187 (Link), key 2188 (Link), key 2189 (Link), key 2190 (Link), key 2191 (Link), key 2192 (Link), key 2193 (Link), key 2194 (Link), key 2195 (Link), key 2196 (Link), key 2197 (Link), key 2198 (Link), key 2199 (Link), key 2200 (Link), key 2201 (Link), key 2202 (Link), key 2203 (Link), key 2204 (Link), key 2205 (Link), key 2206 (Link), key 2207 (Link), key 2208 (Link), key 2209 (Link), key 2210 (Link), key 2211 (Link), key 2212 (Link), key 2213 (Link), key 2214 (Link), key 2215 (Link), key 2216 (Link), key 2217 (Link), key 2218 (Link), key 2219 (Link), key 2220 (Link), key 2221 (Link), key 2222 (Link), key 2223 (Link), key 2224 (Link)

### 9. Structure Left for a Person

- PDF 75 (printed 62): a caption is not grouped with a figure (it sits inside root)
- PDF 75 (printed 62): a caption is not grouped with a figure (it sits inside root)

### 10. veraPDF (WCAG 2.2 machine profile), Before and After

veraPDF 1.30.3, profile "WCAG 2.2 machine validation profile" (7da399cf5baa). Counts are failed checks; pages are from the first checks veraPDF lists for each rule, so a rule may fail on more pages. Rules that only PDF/UA requires are listed apart and do not count. "Who fixes" is who can act on the rule: the pipeline by itself, the AI through the work order, or only a person. **Newly failing** means this run broke something the original passed. Before: 0 rules failing (the AI can act on 0, the pipeline on 0, only a person on 0). After: 0.

PDF/UA-only, not required for WCAG (not counted):

- 7.21.4.1-1: font program embedding (text stays readable through its Unicode mapping) (1 checks, PDF 119 (printed 106)), still failing

### 11. WCAG Checks veraPDF Does Not Make

Each item is something to look at, not a proven failure.

- 1.3.2 1 section read away from its printed place, as in the original (this run did not move it). Listen through each where it is read, or move it with move_section:
  - PDF 5 (printed iv): Article "© 2021 University of Hawai‘i Press Library of Congress Control Number: 202094698", read after PDF 236 (printed 223)

### 12. Deferred by the AI

- **Reading position of the Index section (Sect, PDF 228–236) and of the copyright-page Article (PDF 5)**: The digest's reading_order lists the Index Sect first, before the front matter, so it may be read out of printed order. The listing is truncated and I can't confirm where the container sits after the executor moves it into the Document. [PDF 5 (printed iv), PDF 228 (printed 215), PDF 236 (printed 223)]
- **Drop caps split from their words in the text layer (e.g. 'W riting' on PDF 8, 'S onia' on PDF 238)**: These are ActualText candidates, but the digest gives no obj for the paragraphs concerned, so I can't target them. [PDF 8 (printed vii), PDF 238 (printed 225)]
- **Pages with no tagged text (PDF 3, 7, 13, 194, 214, 224, 226)**: They are probably blank pages. A person should confirm they have no untagged content. [PDF 3 (printed ii), PDF 7 (printed vi), PDF 13 (printed xii), PDF 194 (printed 181), PDF 214 (printed 201), PDF 224 (printed 211), PDF 226 (printed 213)]
- **page_map ends at PDF 226 although the file has 239 pages, and its labels (e.g. 'About the Author' at PDF 225) don't match the headings list (PDF 238)**: The digest's page numbering is inconsistent in the back matter. I cited page numbers from the headings list. [PDF 225 (printed 212), PDF 226 (printed 213), PDF 238 (printed 225), PDF 239 (printed 226)]
- **veraPDF reports 1 failed rule that no work-order key can fix**: It is not listed in pdfua_check.rules, so I can't tell what it is. A person should review it.

Reviewer note from the AI: Heading outline is rebuilt by per-element retype: the book title on PDF 4 (printed iii) stays the only H1. The half-title repeats on PDF 2 (printed i) and PDF 12 (printed xi) became P. Contents, Acknowledgments, Introduction, chapters, References, Index and About the Author are H2. The former H2 sections are H3 and the former H3 subsections are H4. The publisher's Table 1 and 2 titles on PDF 75 (printed 62) were tagged H2 at 9 pt and are now Captions. Chapter headings already combine the number and title in one element, so no merges are needed. The bibliography 'list' on PDF 216 (printed 203) was flattened. The three numbered lists on PDF 86–88 (printed 73–75) are kept. Figure alt texts contained NUL characters and were replaced. The TOC is already tagged TOC/TOCI. Language stays en-US. Romanized Korean is not language-tagged.

### 13. Deferred by the Executor

- elements still outside the Document

## What Was Changed

| Change | Count |
|---|---:|
| document: title | 1 |
| document: DisplayDocTitle | 1 |
| document: /Lang | 1 |
| retype → P | 2 |
| retype → H2 | 11 |
| retype → H3 | 27 |
| retype → Caption | 2 |
| retype → H4 | 16 |
| flatten: false list → paragraphs | 1 |
| table: header cells marked (work order) | 0 |
| figure: alt text | 3 |
| figure: moved into Document, first | 1 |
| links: /Contents set | 1963 |
| links: joined existing Link | 1963 |
| links: URL-only description replaced by the sentence around it | 14 |
| structure: empty tag removed (proven empty) | 13 |
| tag tree index: entries pointing outside the tree cleared (ParentTree) | 1994 |

## Accessibility Evaluation

A person evaluates this version of `northkorea_remediated.pdf` with PAC 2026 and a screen reader, on the app's "Accessibility Evaluation" page (or with manual_checks.py; docs/release.md). The "Ready to ship?" answer needs both parts. A Fail is recorded with its note and does not hold the book back. Each result is recorded against this version of the PDF (its sha256): after a new apply it no longer counts. The evaluation is a record of what a person found, not a legal certification.

**PAC 2026.** Open `northkorea_remediated.pdf` in PAC 2026 (https://pac.pdf-accessibility.org/en, Windows) and run its WCAG check. Anything it fails that is not listed above is a gap in the automated checks: note it in the issue tracker. Each item is Pass, Fail or Not Applicable, with notes:

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
