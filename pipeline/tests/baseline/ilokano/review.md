# Remediation review: ilokano.pdf

Result: `ilokano_remediated.pdf`

49 pages · run 2026-10-25T15:31:19 · model `anthropic/claude-sonnet-5.5` · prompt `workorder_v8.md` (4555d20a2fa08a40) · cost $0 (saved reply reused, no new call) · tokens: saved reply reused, not counted

Intake: 1 picture page without OCR text · auto-tagged · tagged by OpenDataLoader 2.5.12 · the pipeline worked on `_intake/intake.pdf`; the original was not changed

Libraries: python 3.14.4 · pikepdf 10.5.1 · pdfplumber 0.11.9 · pypdfium2 5.7.1 · pillow 13.0.0 · fonttools 4.62.1

Time: intake 0.2s · audit 4.5s · reuse saved reply 0.9s · apply 4.9s · verify 7.9s · total 18.4s

## Overview

[Open the dashboard](review.html)

**Ready to ship?** No
- Work order approved on the review page: no (run without REVIEW=1)
- OCR text approved: not needed (intake added no OCR text)
- Safety checks: OK
- Manual check (PAC): not run

**Safety checks:** OK ✔ pages look the same · OK ✔ text unchanged · OK ✔ all content tagged or decoration · OK ✔ tag-tree index points into the tree · OK ✔ every font readable  
**Needs a person:** 5 (5 deferred by the AI · 0 deferred by the executor · 0 CHECK rows)  
**AI decisions:** 33 in the work order, applied without review by a person  
**Fixed automatically (no AI):** links tied and described 17 · one-item lists turned into paragraphs 15 · pages given tab order 3 · title shown in the window 2 · link descriptions that were only a URL 2 · marked as tagged 1  
**veraPDF (WCAG 2.2 machine checks):** 4 WCAG rules failing before (9 checks) → 0 after (0 checks) · 0 newly failing

Automated checks are evidence, not sign-off.

| Top issues | Pages | Where |
|---|---|---|
| Reading order and page assignment of the OCR-generated tag tree | 14 pages, PDF 15 to PDF 49 | [§8](#8-deferred-by-the-ai) |
| Poor OCR text layer | 8 pages, PDF 18 to PDF 47 | [§8](#8-deferred-by-the-ai) |
| repeated_lines entries | see §8 | [§8](#8-deferred-by-the-ai) |
| Contents page (PDF 6) | PDF 6 | [§8](#8-deferred-by-the-ai) |
| Language of Ilokano example sentences | PDF 9, PDF 49 | [§8](#8-deferred-by-the-ai) |

Automated checks are evidence, not legal sign-off. Items marked **CHECK**, and everything under "For a person to check", need a human.

## Automated checks

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
| Headings: no skipped levels | OK | H1 1 · H2 13 |
| Headings: exactly one H1 (the title) | OK | 1 H1 (several H1s usually mean parts or chapters were not demoted) |
| Figures: none with empty or placeholder alt | OK | 4 figures, 0 placeholder |
| Every Note has a unique ID | OK | 0 notes · 0 without ID · 0 duplicate · 0 not in the ID tree |
| Bookmarks present (documents over 9 pages) | OK | 14 bookmarks |
| Model reply held one work order | OK | one |
| Executor applied every decision | OK | 0 rejected · 0 failed (listed under "Decisions not applied") |
| Nothing deferred by the executor | OK | 0 deferred (listed under "Deferred by the executor") |
| Fonts: every glyph defined (no .notdef) | OK | none found |
| Fonts: every embedded font program could be read | OK | all read |
| Fonts: embedded and mapped to Unicode | OK | 0 not embedded · 0 without ToUnicode (1 more have none and need none: standard encoding, non-symbolic) |
| Text layer agrees with OCR of the page (checklist 1.2) | OK | usable: median character error 2.6% on 18 sample pages |
| Words separated in the text layer (checklist 3.4) | OK | yes on every sample page |
| OCR text added where pages had none (checklist 3.1) | OK | no image-only page held text |
| Auto-tagging kept every page as it was | OK | appearance and text unchanged on all 49 pages (OCR'd pages: text added) |
| Tab order follows the tag structure on pages with links or other annotations | OK | 0 of 3 pages with annotations lack /Tabs /S (log: 3 set by this run) |
| Characters with no Unicode value (checklist 3.6) | OK | 0 read-aloud characters with no Unicode value |
| Private-use characters (checklist 3.6) | OK | 0 read-aloud characters with private-use codes |
| Title and language set | OK | "Ilokano Reference Grammar" · en-US |
| veraPDF WCAG 2.2 (machine): no WCAG failures | OK | before: 4 WCAG rules failed (9 checks) → after: 0 WCAG rules failed (0 checks) (listed under "veraPDF") |
| veraPDF: no rule newly failing or failing more often | OK | 4 fixed · 0 still failing · 0 newly failing |
| Alt text: none like a file name or repeated on many figures (1.1.1) | OK | 0 of 4 figures flagged |
| Tables: every table has header cells (1.3.1) | OK | none without |
| Reading order: no page jumps back up a column (1.3.2) | OK | 0 of 48 pages flagged |
| Reading order: no section moved away from its printed place by this run (1.3.2) | OK | 0 new · 0 already in the original, of 64 sections and blocks |
| Title is not a file name or placeholder (2.4.2) | OK | "Ilokano Reference Grammar" |
| Link text: none like "click here" (2.4.4) | OK | 0 generic |
| Headings: none empty, very long or repeated in a row (2.4.6) | OK | 0 empty · 0 long · 0 repeated |

## For a person to check

### 1. Intake: OCR and auto-tagging

The original had no tags. Local tools prepared it before the model saw it; no model wrote or changed any text. Pages: 1 image-only, 48 text.

Text-layer test (checklist 1.2): each sample page was OCR'd at 300 dpi and compared with its text layer.

| Page | Character error | Verdict |
|---|---:|---|
| PDF 8 | 0.8% | usable |
| PDF 10 | 2.4% | usable (reading order differs) |
| PDF 12 | 4.5% | usable (reading order differs) |
| PDF 14 | 1.1% | usable |
| PDF 16 | 2.7% | usable (reading order differs) |
| PDF 18 | 0.4% | usable |
| PDF 20 | 0.0% | usable (reading order differs) |
| PDF 23 | — | not scored: OCR did not read the diacritics (49 marked letters in the text layer, 3 in OCR; 5% with them, 2% without) |
| PDF 25 | 1.3% | usable |
| PDF 27 | 4.1% | usable |
| PDF 29 | 3.2% | usable |
| PDF 31 | 0.9% | usable |
| PDF 33 | — | not scored: only 79 characters in the text layer (replaced by PDF 34) |
| PDF 34 | 3.1% | usable |
| PDF 36 | 3.1% | usable |
| PDF 38 | 4.2% | usable (reading order differs) |
| PDF 40 | 3.9% | usable |
| PDF 42 | 1.8% | usable |
| PDF 44 | 2.6% | usable |
| PDF 46 | — | not scored: OCR did not read the diacritics (28 marked letters in the text layer, 0 in OCR; 6% with them, 2% without) |
| PDF 49 | 4.6% | usable (reading order differs) |

- **Word breaks rely on gaps**: 92% of text pages (44 of 48) mark most word breaks only by a gap between letters, with no space character (checklist 3.4). A note: readers infer such gaps differently; narrow ones are checked separately
- **Narrow word gaps**: 0.1 narrow word breaks per text page on average (6 in all): gaps narrower than 19% of the type size with no space character (checklist 3.4), where readers such as Acrobat may run words together (e.g. "concernedwithChinese" on bringing PDF 86). Below 10 per page: a note
- **Text layer: diacritics**: on these sample pages OCR read the letters but not the diacritics (tone marks, accents) that the born-digital text layer has, so the page was not scored (the OCR missed them, not the text layer) (PDF 23, PDF 46)
- **Image pages with no text**: image-only pages where OCR found no readable text: left as pictures for the figure step (alt text). Check none is a page of text (PDF 1)
- **Placeholder alt text removed**: the auto-tagger wrote alt text that says nothing (4 figures "image N", 15 links "Annotation"); it was removed, so those figures count as having no alt text (the AI or a person writes it) and each link is read by its own text

### 2. Alt text written or changed by the AI (4)

| Page | Before | After |
|---|---|---|
| PDF 1 | — | Book cover: a tan upper panel with the green University of Hawaiʻi Press logo, over a black panel. The author's name, Ernesto Constantino, appears above the title Ilokano Reference Grammar. |
| PDF 4 | — | University of Hawaiʻi Press Open Access logo |
| PDF 4 | — | Humanities Open Book logo, showing the National Endowment for the Humanities and Andrew W. Mellon Foundation marks |
| PDF 4 | — | Creative Commons BY-NC-SA license icons |

### 3. Elements retyped by the AI (14)

Check each one is (or is not) a heading as decided.

| Page | Text | Before | After |
|---|---|---|---|
| PDF 5 | Copyright © 1971 by University of Hawaii Press All rights reserved | H2 | P |
| PDF 6 | CONTENTS | H1 | H2 |
| PDF 7 | PREFACE | H1 | H2 |
| PDF 8 | INTRODUCTION | H1 | H2 |
| PDF 9 | PHONOLOGY | H1 | H2 |
| PDF 15 | CHAPTER 3 PARTS OF SPEECH | H1 | H2 |
| PDF 18 | CHAPTER 4 SENTENCE CLASSIFICATION | H1 | H2 |
| PDF 21 | CHAPTER 5 VERBAL SENTENCES | H1 | H2 |
| PDF 31 | CHAPTER 6 NONVERBAL SENTENCES | H1 | H2 |
| PDF 34 | CHAPTER 7 OTHER SIMPLE SENTENCES | H1 | H2 |
| PDF 37 | CHAPTER 8 CAUSATIVE SENTENCES | H1 | H2 |
| PDF 42 | CHAPTER 9 COMPLEX AND COMPOUND SENTENCES | H1 | H2 |
| PDF 44 | CHAPTER 10 NEGATIVE, INTERROGATIVE AND OTHER MODAL SENTENCES | H1 | H2 |
| PDF 47 | CHAPTER 11 OTHER SYNTACTIC CONSTRUCTIONS | H1 | H2 |

### 4. Lists and tables

- Flattened list on PDF 9: "2.0. Introduction. The minimal phonological units of Ilokano described in this chapter consist of…" (numbered section paragraphs (2.0, 2.1), not a list)
- Flattened list on PDF 14: "2.7. Pitch and intonation. The pitch of a normal Ilokano sen-tence or utterance generally stays on…" (numbered section paragraphs (2.7, 2.8), not a list)
- Flattened list on PDF 15: "3.0. Introduction. Our principal aim in this grammar of Ilokano is to present a simple and…" (numbered section paragraphs (3.0, 3.1), not a list)
- Flattened list on PDF 18: "4.0. Introduction. The sentence is the largest grammatical unit treated in this grammar. We may…" (numbered section paragraphs (4.0, 4.1 ...), not a list)
- Flattened list on PDF 23: "5.1.5. Direction complement. The direction complement refers to the person or thing toward which the…" (numbered section paragraphs (5.1.5, 5.1.6), not a list)
- Flattened list on PDF 29: "5.8.2. Temporal sentences. A temporal sentence is an imper-sonal sentence with a temporal verb as…" (numbered section paragraphs (5.8.2, 5.8.3), not a list)
- Flattened list on PDF 32: "6.4. Topicless adjectival sentences. Some adjectival sen-tences consist of an adjective without a…" (numbered section paragraphs (6.4, 6.5), not a list)
- Flattened list on PDF 34: "7.0. Introduction. The sentences described in this chapter are the existential, the exclamatory, the…" (numbered section paragraphs (7.0, 7.1), not a list)
- Flattened list on PDF 35: "7.2. Exclamatory sentences. Exclamatory sentences consist of interjections. Some of them express…" (numbered section paragraphs (7.2, 7.3), not a list)
- Flattened list on PDF 43: "9.1.3. Adjectival complex sentences. An adjectival complex sentence is one whose predicate is an…" (numbered section paragraphs (9.1.3, 9.1.4), not a list)
- Flattened list on PDF 45: "10.2.2. Suppletive questions. A suppletive question is a sen-tence whose subject is an interrogative…" (numbered section paragraphs (10.2.2, 10.3), not a list)

### 5. One-item lists turned into paragraphs by rule (15)

A list with one item whose label is not a list marker (the auto-tagger took a paragraph's first word or a year for a label) was made one paragraph, label and text together. Listen to a few; a real one-item list can be kept with `keep_lists`.

- PDF 11: label "2.3.": "2.3. Long consonants. Each of the consonants, except h and"
- PDF 12: label "2.4.": "2.4. Consonant clusters. In Ilokano, two consonants may"
- PDF 12: label "as": "as the first consonant."
- PDF 16: label "3.3.": "3.3. Functions. The members of the parts of speech have"
- PDF 17: label "3.4.": "3.4. Phrases. As we said earlier, the members of the parts of"
- PDF 19: label "4.4.": "4.4. Sentence inversion. As we mentioned above, the normal"
- PDF 20: label "4.5.": "4.5. Verbal and nonverbal sentences. The sentences of"
- PDF 22: label "5.1.3.": "5.1.3. Beneficiary complement. The beneficiary complement"
- PDF 23: label "5.1.4.": "5.1.4. Instrument complement. The instrument complement"
- PDF 31: label "6.2.": "6.2. Topicless nominal sentences. Some nominal sentences"
- PDF 32: label "6.3.": "6.3. Adjectival sentences. The center of the predicate of"
- PDF 46: label "10": "10.3.2. Non-desiderative. The center of the predicate of non-"
- PDF 47: label "11": "11.0. Introduction, The syntactic constructions which are"
- PDF 48: label "11.2.": "11.2. Coordination. A coordination construction consists of"
- PDF 49: label "11.3.": "11.3. Comparison. A structure of comparison consists of an"

### 6. Links whose description was only a URL (2)

The description (what a screen reader announces) was set to the book's own sentence around the link, with the URL removed. No words were added and the visible URL is unchanged. Replace any of these with a better description if needed.

| Page | URL | Description now |
|---|---|---|
| PDF 4 | https://creativecommons.org/licenses/by-nc-sa/4.0/ | national(CCBY-NC-SA4.0),whichpermitsreaderstofreelydownloadandsharetheworkinprintorelectronicformatfornon-commercialpurposes,solongascreditisgiventotheauthor.Thelicensealsopermitsreaderstocreateandsharede-rivativesofthework,solongassuchderivativesaresharedunderthesametermsofthislicense.Commercialusesrequirepermissionfromthepublisher.Fordetails,see.TheCre-ativeCommonslicensedescribedabovedoesnotapplytoanymaterialthatisseparatelycopyrighted. |
| PDF 4 | http://www.hawaiiopen.org | PleasevisitformoreOpenAccessworksfromUniversityofHawai‘iPress. |

### 7. veraPDF (WCAG 2.2 machine profile), before and after

veraPDF 1.30.3, profile "WCAG 2.2 machine validation profile" (7da399cf5baa). Counts are failed checks; pages are from the first checks veraPDF lists for each rule, so a rule may fail on more pages. Rules that only PDF/UA requires are listed apart and do not count. "Who fixes" is who can act on the rule: the pipeline by itself, the AI through the work order, or only a person. **Newly failing** means this run broke something the original passed. Before: 4 rules failing (the AI can act on 1, the pipeline on 3, only a person on 0). After: 0.

| Rule | WCAG | What it checks | Who fixes | Before | After | Status | Pages (after, else before) |
|---|---|---|---|---:|---:|---|---|
| ISO 14289-1 7.3-1 | 1.1.1 | Figure tags shall include an alternative representation or replacement text that represents the contents marked with the Figure tag as noted in ISO 32000-1:2008, 14.7.2, Table 323 | the AI (`alt`) | 4 | 0 | fixed | PDF 1, PDF 4 |
| ISO 14289-1 7.18.3-1 | 2.4.3 | Every page on which there is an annotation shall contain in its page dictionary the key Tabs, and its value shall be S | the pipeline (3 changed) | 3 | 0 | fixed | PDF 4, PDF 6, PDF 21 |
| ISO 14289-1 6.2-1 | 1.3.1 | The document catalog dictionary shall include a MarkInfo dictionary containing an entry, Marked, whose value shall be true | the pipeline (1 changed) | 1 | 0 | fixed | page: not on this tag |
| ISO 14289-1 7.1-10 | 2.4.2 | The document catalog dictionary shall include a ViewerPreferences dictionary containing a DisplayDocTitle key, whose value shall be true | the pipeline (1 changed) | 1 | 0 | fixed | page: not on this tag |

### 8. Deferred by the AI

- **Reading order and page assignment of the OCR-generated tag tree**: Heading page numbers disagree with page_map. For example, the chapter 3 heading is on PDF 15 while 'PARTS OF SPEECH' is the first tagged line on PDF 17. The reading_order list is empty, so I cannot confirm any order and made no move_section decision. A person should check the order of the chapter-title pages. [PDF 15, PDF 17, PDF 18, PDF 19, PDF 31, PDF 33, PDF 34, PDF 35, PDF 42, PDF 43, PDF 44, PDF 45, PDF 47, PDF 49]
- **Poor OCR text layer**: The suspect-token rate is about 393 per 1000. Examples include running text such as 'senten#es' and '#hapter'. The text was not changed. [PDF 18, PDF 21, PDF 31, PDF 34, PDF 37, PDF 42, PDF 44, PDF 47]
- **repeated_lines entries**: These are ordinary first words of pages ('The', 'CHAPTER', 'and'), not running heads, so no artifact rules were made. No running heads or page numbers were identified.
- **Contents page (PDF 6)**: The contents entries are already tagged as L/LI with links. I left them as they are. A person should check that the listed page numbers match the actual pagination, which differs from the PDF page order. [PDF 6]
- **Language of Ilokano example sentences**: Ilokano words and sentences are embedded throughout the English text. They can't be language-tagged by run with this work order (no language code is given for them). A human could tag them as 'ilo' if desired. [PDF 9, PDF 49]

Reviewer note from the AI: Only the book title (137 0) stays H1. The front-matter and chapter titles were individually retyped to H2, and the copyright line was demoted to P. Single-item lists (flattened_by_rule) are left to the executor. Numbered example-sentence lists such as '(1) ...' and the '(a)–(d)' lists were kept as real lists. The 1971 grammar's OCR layer is of poor quality.

## What was changed

| Change | Count |
|---|---:|
| document: marked as tagged | 1 |
| document: DisplayDocTitle | 2 |
| document: title | 1 |
| document: /Lang | 1 |
| retype → P | 1 |
| retype → H2 | 13 |
| one-item list → paragraph (rule) | 15 |
| flatten: false list → paragraphs | 11 |
| figure: alt text | 4 |
| links: /Contents set | 17 |
| links: joined existing Link | 17 |
| links: URL-only description replaced by the sentence around it | 2 |
| tab order: /Tabs /S set on pages with annotations | 3 |

## Final check with PAC 2026

Open `ilokano_remediated.pdf` in PAC 2026 (https://pac.pdf-accessibility.org/en, Windows) and run its WCAG check. Anything it fails that is not listed above is a gap in the automated checks: note it in the issue tracker.

No automated check here covers these WCAG 2.2 AA criteria; check them by hand, with PAC's screen-reader and structure previews:

- 1.1.1: alt text is accurate and gives the figure's purpose; decorative images are artifacts
- 1.3.1 / 1.3.2: headings, lists and tables match what is printed, and the reading order makes sense
- 1.4.1: no information is given by colour alone
- 1.4.3: contrast of text over images and coloured backgrounds (PAC's contrast checker)
- 1.4.5: no images of text where real text could be used (scanned pages: the OCR layer stands in)
- 2.4.6: headings describe their section
- 3.1.2: passages in another language carry their language (see `han_review.csv` if present)
