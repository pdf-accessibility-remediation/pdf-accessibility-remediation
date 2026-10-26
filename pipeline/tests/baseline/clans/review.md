# Remediation review: clans.pdf

Result: `clans_remediated.pdf`

194 pages · run 2026-10-25T15:30:28 · model `anthropic/claude-sonnet-5.5` · prompt `workorder_v8.md` (4555d20a2fa08a40) · cost $0 (saved reply reused, no new call) · tokens: saved reply reused, not counted

Intake: none (already tagged)

Libraries: python 3.14.4 · pikepdf 10.5.1 · pdfplumber 0.11.9 · pypdfium2 5.7.1 · pillow 13.0.0 · fonttools 4.62.1

Time: intake 0.2s · audit 18.4s · reuse saved reply 0.8s · apply 16.6s · verify 25.7s · total 61.7s

## Overview

[Open the dashboard](review.html)

**Ready to ship?** No
- Work order approved on the review page: no (run without REVIEW=1)
- OCR text approved: not needed (intake added no OCR text)
- Safety checks: OK
- Manual check (PAC): not run

**Safety checks:** OK ✔ pages look the same · OK ✔ text unchanged · OK ✔ all content tagged or decoration · OK ✔ tag-tree index points into the tree · OK ✔ every font readable  
**Needs a person:** 5 (4 deferred by the AI · 0 deferred by the executor · 1 CHECK row)  
**AI decisions:** 77 in the work order, applied without review by a person  
**Fixed automatically (no AI):** tag-tree index entries 195 · standard tags un-remapped (7.1-7) 45 · title shown in the window 1  
**veraPDF (WCAG 2.2 machine checks):** 3 WCAG rules failing before (760 checks) → 0 after (0 checks) · 0 newly failing

Automated checks are evidence, not sign-off.

| Top issues | Pages | Where |
|---|---|---|
| Fonts: embedded and mapped to Unicode: 1 not embedded · 0 without ToUnicode | see §7 | [§7](#7-fonts) |
| Section headings "I" and "II" of "The Remembered Shadow of the Yi Dynasty" are not marked as headings or hea… | PDF 118 (printed 111), PDF 134 (printed 127) | [§10](#10-deferred-by-the-ai) |
| The contents entry "Seeking Life amidst Death … 47 When the Hibiscus Blooms 73" is a single TOCI holding two… | PDF 6 (printed v) | [§10](#10-deferred-by-the-ai) |
| Extracted text has stray characters in place of macron and diacritic letters (e.g. "ò", "ôô", "∆", missing l… | PDF 4 (printed iii), PDF 5 (printed iv), PDF 9 (printed 2), PDF 48 (printed 41) | [§10](#10-deferred-by-the-ai) |
| The "Footnote" style is mapped to P, not Note. | PDF 15 (printed 8), PDF 190 (printed 183) | [§10](#10-deferred-by-the-ai) |

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
| Tag-tree index points only into the tree | OK | 0 dangling entries · 5 stale entries (marked content no longer drawn) |
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
| Headings: no skipped levels | OK | H1 1 · H2 7 · H3 21 |
| Headings: exactly one H1 (the title) | OK | 1 H1 (several H1s usually mean parts or chapters were not demoted) |
| Figures: none with empty or placeholder alt | OK | 4 figures, 0 placeholder |
| Every Note has a unique ID | OK | 0 notes · 0 without ID · 0 duplicate · 0 not in the ID tree |
| Bookmarks present (documents over 9 pages) | OK | 7 bookmarks |
| Model reply held one work order | OK | one |
| Executor applied every decision | OK | 0 rejected · 0 failed (listed under "Decisions not applied") |
| Nothing deferred by the executor | OK | 0 deferred (listed under "Deferred by the executor") |
| Fonts: every glyph defined (no .notdef) | OK | none found |
| Fonts: every embedded font program could be read | OK | all read |
| Fonts: embedded and mapped to Unicode | **CHECK** | 1 not embedded · 0 without ToUnicode |
| Tab order follows the tag structure on pages with links or other annotations | OK | 0 of 0 pages with annotations lack /Tabs /S |
| Characters with no Unicode value (checklist 3.6) | OK | 0 read-aloud characters with no Unicode value |
| Private-use characters (checklist 3.6) | OK | 0 read-aloud characters with private-use codes |
| Title and language set | OK | "The Clan Records: Five Stories of Korea" · en-US |
| veraPDF WCAG 2.2 (machine): no WCAG failures | OK | before: 3 WCAG rules failed (760 checks) → after: 0 WCAG rules failed (0 checks) · 1 PDF/UA-only rules not counted (listed under "veraPDF") |
| veraPDF: no rule newly failing or failing more often | OK | 3 fixed · 1 still failing · 0 newly failing |
| Alt text: none like a file name or repeated on many figures (1.1.1) | OK | 0 of 4 figures flagged |
| Tables: every table has header cells (1.3.1) | OK | none without |
| Reading order: no page jumps back up a column (1.3.2) | OK | 0 of 191 pages flagged |
| Reading order: no section moved away from its printed place by this run (1.3.2) | OK | 0 new · 0 already in the original, of 106 sections and blocks |
| Title is not a file name or placeholder (2.4.2) | OK | "The Clan Records: Five Stories of Korea" |
| Link text: none like "click here" (2.4.4) | OK | 0 generic |
| Headings: none empty, very long or repeated in a row (2.4.6) | OK | 0 empty · 0 long · 0 repeated |

## For a person to check

### 1. Alt text written or changed by the AI (4)

| Page | Before | After |
|---|---|---|
| PDF 1 (printed cover) | — | Book cover: title "The Clan Records", subtitle "Five Stories of Korea", author Kajiyama Toshiyuki. A brush-and-ink drawing shows a fountain pen lying diagonally across a sheet of manuscript grid paper. |
| PDF 4 (printed iii) | — | University of Hawai‘i Press logo |
| PDF 11 (printed 4) | — | Black-and-white studio portrait of the Kajiyama family, Seoul, 1937: a woman in a kimono, a man in a suit holding a baby, a woman in Korean traditional dress, and three young boys seated in front. |
| PDF 12 (printed 5) | — | Kajiyama Toshiyuki, in a dark kimono and glasses, standing among crowded bookshelves in his personal library in Tokyo, 1971, holding an open book. |

### 2. Headings

Heading levels by style (as applied):

| Style | Level | How | Elements |
|---|---|---|---:|
| Footnote | P | RoleMap | 22 |

### 3. Elements retyped by the AI (34)

Check each one is (or is not) a heading as decided.

| Page | Text | Before | After |
|---|---|---|---|
| PDF 2 (printed i) | The Clan Records | H1 | P |
| PDF 4 (printed iii) | The Clan Records | H1 | H1 |
| PDF 4 (printed iii) | FIVE STORIE S OF KORE A | H1 | P |
| PDF 4 (printed iii) | Translated by Yoshiko Dykstra | H1 | P |
| PDF 5 (printed iv) | In memory of Ryz and Mitsue Ariyoshi òò | H1 | P |
| PDF 6 (printed v) | Contents | H1 | H2 |
| PDF 8 (printed 1) | Introduction | H1 | H2 |
| PDF 8 (printed 1) | George Akita and Yong-ho Choe | H2 | P |
| PDF 14 (printed 7) | The Clan Records | H1 | H2 |
| PDF 54 (printed 47) | Seeking Life amidst Death: The Last Day of the War | H1 | H2 |
| PDF 80 (printed 73) | When the Hibiscus Blooms | H1 | H2 |
| PDF 80 (printed 73) | I | H2 | H3 |
| PDF 83 (printed 76) | II | H2 | H3 |
| PDF 86 (printed 79) | III | H2 | H3 |
| PDF 89 (printed 82) | IV | H2 | H3 |
| PDF 92 (printed 85) | V | H2 | H3 |
| PDF 97 (printed 90) | VI | H2 | H3 |
| PDF 103 (printed 96) | VII | P | H3 |
| PDF 105 (printed 98) | VIII | H2 | H3 |
| PDF 109 (printed 102) | IX | H2 | H3 |
| PDF 113 (printed 106) | X | H2 | H3 |
| PDF 118 (printed 111) | The Remembered Shadow of the Yi Dynasty | H1 | H2 |
| PDF 134 (printed 127) | III | H2 | H3 |
| PDF 145 (printed 138) | IV | H2 | H3 |
| PDF 152 (printed 145) | V | H2 | H3 |
| PDF 159 (printed 152) | VI | H2 | H3 |
| PDF 168 (printed 161) | A Crane on a Dunghill: Seoul in 1936 | H1 | H2 |
| PDF 168 (printed 161) | I | H2 | H3 |
| PDF 171 (printed 164) | II | H2 | H3 |
| PDF 175 (printed 168) | III | H2 | H3 |
| PDF 178 (printed 171) | IV | H2 | H3 |
| PDF 183 (printed 176) | V | H2 | H3 |
| PDF 185 (printed 178) | VI | H2 | H3 |
| PDF 189 (printed 182) | VII | H2 | H3 |

### 4. Lists and tables

- Flattened list on PDF 31 (printed 24): "“Yes, I do. He is very pro-Japanese. Is something wrong?” / “Yes, something is wrong. He has not…" (dialogue lines, not a list)
- Flattened list on PDF 32 (printed 25): "“No, chief. Sl Chin-yng is not that kind of man.” ôô / “You really stick up for him, don’t you? At a…" (dialogue lines, not a list)
- Flattened list on PDF 32 (printed 25): "“I will do my best.” I bowed angrily. / “Wait. Look at this.” His voice was harsh. He pushed a paper…" (dialogue lines, not a list)
- Flattened list on PDF 34 (printed 27): "“How are you now?” I asked." (dialogue lines, not a list)
- Flattened list on PDF 48 (printed 41): "“You mean Mr. Sl Chin-yng?” ôô" (dialogue lines, not a list)
- Flattened list on PDF 48 (printed 41): "“Don’t criticize the dead! He was not a traitor.”" (dialogue lines, not a list)
- Flattened list on PDF 88 (printed 81): "“To tell me?”" (dialogue lines, not a list)
- Flattened list on PDF 88 (printed 81): "“Yes. In America. I don’t think I would benefit much from study in Japan,” said Ch’r-in, looking…" (dialogue lines, not a list)
- Flattened list on PDF 97 (printed 90): "“What are you doing?” Km-ju appeared in the kitchen. ∆ / “Look! This bowl! It’s so beautiful . . .”" (dialogue lines, not a list)
- Flattened list on PDF 99 (printed 92): "“But I just want to look at it.”" (dialogue lines, not a list)
- Flattened list on PDF 102 (printed 95): "“Well, what do you think?” / “Well, as you’ve guessed, these probably came from the Yi dynasty…" (dialogue lines, not a list)
- Flattened list on PDF 102 (printed 95): "Yamanoi all but caressed the incense burner. / “Do you think they’re only cheap trifles?”" (dialogue lines, not a list)
- Flattened list on PDF 102 (printed 95): "“Indeed. That’s why they’re beautiful.”" (dialogue lines, not a list)
- Flattened list on PDF 106 (printed 99): "“Yes. You were more pure in those days.”" (dialogue lines, not a list)
- Flattened list on PDF 128 (printed 121): "“Then you are an artist?” / “Yes. I like this section of Chongno. But I am sad because everything’s…" (dialogue lines, not a list)
- Flattened list on PDF 128 (printed 121): "“A dance? What kind of dance?” asked Noguchi. / “A court dance from olden times.”" (dialogue lines, not a list)
- Flattened list on PDF 144 (printed 137): "“Then where can I see it?” / “The best place is the Kynghoeru Hall in the Kyngbok Palace.” ôô" (dialogue lines, not a list)
- Flattened list on PDF 148 (printed 141): "“Hi! Professor Pak has come already,” Noguchi told her, almost dancing for joy." (dialogue lines, not a list)
- Flattened list on PDF 153 (printed 146): "“Why did you go to a place like this?”" (dialogue lines, not a list)
- Flattened list on PDF 154 (printed 147): "“Didn’t you gather peaches and grapes perhaps?”" (dialogue lines, not a list)
- Flattened list on PDF 154 (printed 147): "“Maybe you were not born yet . . . or was that the year when you were born?”" (dialogue lines, not a list)
- Flattened list on PDF 154 (printed 147): "“That was the time when some young and foolish Koreans caused a great deal of unrest by shouting out…" (dialogue lines, not a list)
- Flattened list on PDF 154 (printed 147): "“Yes, the garrison subdued the rioters. . . . Isn’t this enough, now? I’m busy.”" (dialogue lines, not a list)
- Flattened list on PDF 164 (printed 157): "“No particular reason?” / “That’s right. Its theme is an ancient court dance of the Yi dynasty.”" (dialogue lines, not a list)
- Flattened list on PDF 164 (printed 157): "“What do you mean?”" (dialogue lines, not a list)
- Flattened list on PDF 164 (printed 157): "“I’m not.” / “Don’t lie to me! What’s this?”" (dialogue lines, not a list)
- Flattened list on PDF 164 (printed 157): "“We searched your atelier and found this! Do you still keep saying that you had no deliberate…" (dialogue lines, not a list)
- Flattened list on PDF 164 (printed 157): "“Yes! That pamphlet had nothing to do with the painting.” / “Then why was it in your atelier?”" (dialogue lines, not a list)
- Flattened list on PDF 172 (printed 165): "“What’s the trouble?”" (dialogue lines, not a list)
- Flattened list on PDF 184 (printed 177): "“Why do you want to know?” Km-ju asked, in fluent Japanese. ∆ / “Why? Because I know you are using…" (dialogue lines, not a list)
- Flattened list on PDF 184 (printed 177): "“But we are just friends.”" (dialogue lines, not a list)
- Flattened list on PDF 184 (printed 177): "“I am sorry. I won’t do it again.”" (dialogue lines, not a list)

### 5. Text a screen reader could not reach (before this run)

187 pages had text outside the tag tree: 367 orphan runs (marked, but no tag owns them) and 0 untagged runs. Running heads and page numbers among them can be hidden as decoration; real content must be added to the tag tree by a person. After this run: 0 untagged characters, 0 orphan runs remain.

Pages: PDF 6 (printed v), PDF 8–193 (printed 1–186)

### 6. Hidden from screen readers (artifacts)

- "running heads and folios (top)": every orphan run in the top band on PDF 9–193 (printed 2–186)
- "folios on chapter-opening pages (bottom)": every orphan run in the bottom band on PDF 6–193 (printed v–186)

### 7. Fonts

The pipeline changes no other font: it never embeds one, replaces a visible one, or rewrites text. These need a person:

- **Not embedded** (1): Times-Roman. PDF/UA requires embedded fonts (7.21.4.1); a person must embed them with a PDF tool (e.g. Acrobat Preflight) and check that no page changes.

### 8. Tag-tree index entries cleared (195)

Entries that pointed at a tag no longer in the tag tree (left by the source file, or by a tag the run removed). Nothing reads such a tag; no page, text or reachable tag changed.

- IDTree: "Reference_AD260817-0629-1218-ADBE-000000000729" (0), "SLTP_rev7000_1" (null: points at nothing), "SLTP_rev7000_10" (null: points at nothing), "SLTP_rev7000_100" (null: points at nothing), "SLTP_rev7000_101" (null: points at nothing), "SLTP_rev7000_102" (null: points at nothing), "SLTP_rev7000_103" (null: points at nothing), "SLTP_rev7000_104" (null: points at nothing), "SLTP_rev7000_105" (null: points at nothing), "SLTP_rev7000_106" (null: points at nothing), "SLTP_rev7000_107" (null: points at nothing), "SLTP_rev7000_108" (null: points at nothing), "SLTP_rev7000_109" (null: points at nothing), "SLTP_rev7000_11" (null: points at nothing), "SLTP_rev7000_110" (null: points at nothing), "SLTP_rev7000_111" (null: points at nothing), "SLTP_rev7000_112" (null: points at nothing), "SLTP_rev7000_113" (null: points at nothing), "SLTP_rev7000_114" (null: points at nothing), "SLTP_rev7000_115" (null: points at nothing), "SLTP_rev7000_116" (null: points at nothing), "SLTP_rev7000_117" (null: points at nothing), "SLTP_rev7000_118" (null: points at nothing), "SLTP_rev7000_119" (null: points at nothing), "SLTP_rev7000_12" (null: points at nothing), "SLTP_rev7000_120" (null: points at nothing), "SLTP_rev7000_121" (null: points at nothing), "SLTP_rev7000_122" (null: points at nothing), "SLTP_rev7000_123" (null: points at nothing), "SLTP_rev7000_124" (null: points at nothing), "SLTP_rev7000_125" (null: points at nothing), "SLTP_rev7000_126" (null: points at nothing), "SLTP_rev7000_127" (null: points at nothing), "SLTP_rev7000_128" (null: points at nothing), "SLTP_rev7000_129" (null: points at nothing), "SLTP_rev7000_13" (null: points at nothing), "SLTP_rev7000_130" (null: points at nothing), "SLTP_rev7000_131" (null: points at nothing), "SLTP_rev7000_132" (null: points at nothing), "SLTP_rev7000_133" (null: points at nothing), "SLTP_rev7000_134" (null: points at nothing), "SLTP_rev7000_135" (null: points at nothing), "SLTP_rev7000_136" (null: points at nothing), "SLTP_rev7000_137" (null: points at nothing), "SLTP_rev7000_138" (null: points at nothing), "SLTP_rev7000_139" (null: points at nothing), "SLTP_rev7000_14" (null: points at nothing), "SLTP_rev7000_140" (null: points at nothing), "SLTP_rev7000_141" (null: points at nothing), "SLTP_rev7000_142" (null: points at nothing), "SLTP_rev7000_143" (null: points at nothing), "SLTP_rev7000_144" (null: points at nothing), "SLTP_rev7000_145" (null: points at nothing), "SLTP_rev7000_146" (null: points at nothing), "SLTP_rev7000_147" (null: points at nothing), "SLTP_rev7000_148" (null: points at nothing), "SLTP_rev7000_149" (null: points at nothing), "SLTP_rev7000_15" (null: points at nothing), "SLTP_rev7000_150" (null: points at nothing), "SLTP_rev7000_151" (null: points at nothing), "SLTP_rev7000_152" (null: points at nothing), "SLTP_rev7000_153" (null: points at nothing), "SLTP_rev7000_154" (null: points at nothing), "SLTP_rev7000_155" (null: points at nothing), "SLTP_rev7000_156" (null: points at nothing), "SLTP_rev7000_157" (null: points at nothing), "SLTP_rev7000_158" (null: points at nothing), "SLTP_rev7000_159" (null: points at nothing), "SLTP_rev7000_16" (null: points at nothing), "SLTP_rev7000_160" (null: points at nothing), "SLTP_rev7000_161" (null: points at nothing), "SLTP_rev7000_162" (null: points at nothing), "SLTP_rev7000_163" (null: points at nothing), "SLTP_rev7000_164" (null: points at nothing), "SLTP_rev7000_165" (null: points at nothing), "SLTP_rev7000_166" (null: points at nothing), "SLTP_rev7000_167" (null: points at nothing), "SLTP_rev7000_168" (null: points at nothing), "SLTP_rev7000_169" (null: points at nothing), "SLTP_rev7000_17" (null: points at nothing), "SLTP_rev7000_170" (null: points at nothing), "SLTP_rev7000_171" (null: points at nothing), "SLTP_rev7000_172" (null: points at nothing), "SLTP_rev7000_173" (null: points at nothing), "SLTP_rev7000_174" (null: points at nothing), "SLTP_rev7000_175" (null: points at nothing), "SLTP_rev7000_176" (null: points at nothing), "SLTP_rev7000_177" (null: points at nothing), "SLTP_rev7000_178" (null: points at nothing), "SLTP_rev7000_179" (null: points at nothing), "SLTP_rev7000_18" (null: points at nothing), "SLTP_rev7000_180" (null: points at nothing), "SLTP_rev7000_181" (null: points at nothing), "SLTP_rev7000_182" (null: points at nothing), "SLTP_rev7000_183" (null: points at nothing), "SLTP_rev7000_184" (null: points at nothing), "SLTP_rev7000_185" (null: points at nothing), "SLTP_rev7000_186" (null: points at nothing), "SLTP_rev7000_187" (null: points at nothing), "SLTP_rev7000_188" (null: points at nothing), "SLTP_rev7000_189" (null: points at nothing), "SLTP_rev7000_19" (null: points at nothing), "SLTP_rev7000_190" (null: points at nothing), "SLTP_rev7000_191" (null: points at nothing), "SLTP_rev7000_192" (null: points at nothing), "SLTP_rev7000_193" (null: points at nothing), "SLTP_rev7000_194" (null: points at nothing), "SLTP_rev7000_2" (null: points at nothing), "SLTP_rev7000_20" (null: points at nothing), "SLTP_rev7000_21" (null: points at nothing), "SLTP_rev7000_22" (null: points at nothing), "SLTP_rev7000_23" (null: points at nothing), "SLTP_rev7000_24" (null: points at nothing), "SLTP_rev7000_25" (null: points at nothing), "SLTP_rev7000_26" (null: points at nothing), "SLTP_rev7000_27" (null: points at nothing), "SLTP_rev7000_28" (null: points at nothing), "SLTP_rev7000_29" (null: points at nothing), "SLTP_rev7000_3" (null: points at nothing), "SLTP_rev7000_30" (null: points at nothing), "SLTP_rev7000_31" (null: points at nothing), "SLTP_rev7000_32" (null: points at nothing), "SLTP_rev7000_33" (null: points at nothing), "SLTP_rev7000_34" (null: points at nothing), "SLTP_rev7000_35" (null: points at nothing), "SLTP_rev7000_36" (null: points at nothing), "SLTP_rev7000_37" (null: points at nothing), "SLTP_rev7000_38" (null: points at nothing), "SLTP_rev7000_39" (null: points at nothing), "SLTP_rev7000_4" (null: points at nothing), "SLTP_rev7000_40" (null: points at nothing), "SLTP_rev7000_41" (null: points at nothing), "SLTP_rev7000_42" (null: points at nothing), "SLTP_rev7000_43" (null: points at nothing), "SLTP_rev7000_44" (null: points at nothing), "SLTP_rev7000_45" (null: points at nothing), "SLTP_rev7000_46" (null: points at nothing), "SLTP_rev7000_47" (null: points at nothing), "SLTP_rev7000_48" (null: points at nothing), "SLTP_rev7000_49" (null: points at nothing), "SLTP_rev7000_5" (null: points at nothing), "SLTP_rev7000_50" (null: points at nothing), "SLTP_rev7000_51" (null: points at nothing), "SLTP_rev7000_52" (null: points at nothing), "SLTP_rev7000_53" (null: points at nothing), "SLTP_rev7000_54" (null: points at nothing), "SLTP_rev7000_55" (null: points at nothing), "SLTP_rev7000_56" (null: points at nothing), "SLTP_rev7000_57" (null: points at nothing), "SLTP_rev7000_58" (null: points at nothing), "SLTP_rev7000_59" (null: points at nothing), "SLTP_rev7000_6" (null: points at nothing), "SLTP_rev7000_60" (null: points at nothing), "SLTP_rev7000_61" (null: points at nothing), "SLTP_rev7000_62" (null: points at nothing), "SLTP_rev7000_63" (null: points at nothing), "SLTP_rev7000_64" (null: points at nothing), "SLTP_rev7000_65" (null: points at nothing), "SLTP_rev7000_66" (null: points at nothing), "SLTP_rev7000_67" (null: points at nothing), "SLTP_rev7000_68" (null: points at nothing), "SLTP_rev7000_69" (null: points at nothing), "SLTP_rev7000_7" (null: points at nothing), "SLTP_rev7000_70" (null: points at nothing), "SLTP_rev7000_71" (null: points at nothing), "SLTP_rev7000_72" (null: points at nothing), "SLTP_rev7000_73" (null: points at nothing), "SLTP_rev7000_74" (null: points at nothing), "SLTP_rev7000_75" (null: points at nothing), "SLTP_rev7000_76" (null: points at nothing), "SLTP_rev7000_77" (null: points at nothing), "SLTP_rev7000_78" (null: points at nothing), "SLTP_rev7000_79" (null: points at nothing), "SLTP_rev7000_8" (null: points at nothing), "SLTP_rev7000_80" (null: points at nothing), "SLTP_rev7000_81" (null: points at nothing), "SLTP_rev7000_82" (null: points at nothing), "SLTP_rev7000_83" (null: points at nothing), "SLTP_rev7000_84" (null: points at nothing), "SLTP_rev7000_85" (null: points at nothing), "SLTP_rev7000_86" (null: points at nothing), "SLTP_rev7000_87" (null: points at nothing), "SLTP_rev7000_88" (null: points at nothing), "SLTP_rev7000_89" (null: points at nothing), "SLTP_rev7000_9" (null: points at nothing), "SLTP_rev7000_90" (null: points at nothing), "SLTP_rev7000_91" (null: points at nothing), "SLTP_rev7000_92" (null: points at nothing), "SLTP_rev7000_93" (null: points at nothing), "SLTP_rev7000_94" (null: points at nothing), "SLTP_rev7000_95" (null: points at nothing), "SLTP_rev7000_96" (null: points at nothing), "SLTP_rev7000_97" (null: points at nothing), "SLTP_rev7000_98" (null: points at nothing), "SLTP_rev7000_99" (null: points at nothing)

### 9. veraPDF (WCAG 2.2 machine profile), before and after

veraPDF 1.30.3, profile "WCAG 2.2 machine validation profile" (7da399cf5baa). Counts are failed checks; pages are from the first checks veraPDF lists for each rule, so a rule may fail on more pages. Rules that only PDF/UA requires are listed apart and do not count. "Who fixes" is who can act on the rule: the pipeline by itself, the AI through the work order, or only a person. **Newly failing** means this run broke something the original passed. Before: 3 rules failing (the AI can act on 3, the pipeline on 0, only a person on 0). After: 0.

| Rule | WCAG | What it checks | Who fixes | Before | After | Status | Pages (after, else before) |
|---|---|---|---|---:|---:|---|---|
| ISO 14289-1 7.1-3 | 1.3.1 | Content shall be marked as Artifact or tagged as real content | the AI (`artifacts`) | 734 | 0 | fixed | PDF 6 (printed v), PDF 8 (printed 1), PDF 9 (printed 2), PDF 10 (printed 3), PDF 11 (printed 4), PDF 12 (printed 5) |
| ISO 14289-1 7.1-5 | 1.3.1, 4.1.2 | All non-standard structure types shall be mapped to the nearest functionally equivalent standard type, as defined in ISO 32000-1:2008, 14.8.4, in the role map dictionary of the structure tree root. This mapping may be indirect; within the role map a non-standard type can map directly to another non-standard type, but eventually the mapping shall terminate at a standard type | the AI (`rolemap`) | 22 | 0 | fixed | PDF 15 (printed 8), PDF 47 (printed 40), PDF 72 (printed 65), PDF 108 (printed 101), PDF 124 (printed 117), PDF 136 (printed 129), PDF 142 (printed 135), PDF 157 (printed 150), PDF 165 (printed 158), PDF 166 (printed 159), PDF 170 (printed 163), PDF 172 (printed 165), PDF 176 (printed 169), PDF 179 (printed 172), PDF 180 (printed 173), PDF 181 (printed 174), PDF 190 (printed 183) |
| ISO 14289-1 7.3-1 | 1.1.1 | Figure tags shall include an alternative representation or replacement text that represents the contents marked with the Figure tag as noted in ISO 32000-1:2008, 14.7.2, Table 323 | the AI (`alt`) | 4 | 0 | fixed | PDF 1 (printed cover), PDF 4 (printed iii), PDF 11 (printed 4), PDF 12 (printed 5) |

PDF/UA-only, not required for WCAG (not counted):

- 7.21.4.1-1: font program embedding (text stays readable through its Unicode mapping) (1 checks, PDF 2 (printed i)), still failing

### 10. Deferred by the AI

- **Section headings "I" and "II" of "The Remembered Shadow of the Yi Dynasty" are not marked as headings or heading candidates; a person should check them and make them H3.**: The digest shows no separate element for them (the chapter title is followed by a P starting with "I"). [PDF 118 (printed 111), PDF 134 (printed 127)]
- **The contents entry "Seeking Life amidst Death … 47 When the Hibiscus Blooms 73" is a single TOCI holding two entries.**: Splitting a TOC item is not possible in this work order. [PDF 6 (printed v)]
- **Extracted text has stray characters in place of macron and diacritic letters (e.g. "ò", "ôô", "∆", missing letters in Korean names).**: The text layer is damaged and the published text must not be changed; a person should check it. [PDF 4 (printed iii), PDF 5 (printed iv), PDF 9 (printed 2), PDF 48 (printed 41)]
- **The "Footnote" style is mapped to P, not Note.**: Its samples are fragments of ordinary narrative, not real footnotes. A person should check the reading order of these fragments. [PDF 15 (printed 8), PDF 190 (printed 183)]

Reviewer note from the AI: One H1 (book title, PDF 4, printed iii). Contents, Introduction and the five story titles are H2; section numerals are H3. The half-title and title-page lines, the dedication and the byline are demoted to P. Running heads and folios are artifacted by band rules on orphan runs, covering veraPDF 7.1-3. All 32 lists are dialogue lines and are flattened. The "Footnote" role is mapped to P to fix veraPDF 7.1-5. Alt text is written for all four figures (veraPDF 7.3-1). The cover is tagged as a Figure plus separate text P elements.

## What was changed

| Change | Count |
|---|---:|
| artifact: "folios on chapter-opening pages (bottom)" | 7 |
| artifact: "running heads and folios (top)" | 360 |
| document: title | 1 |
| document: DisplayDocTitle | 1 |
| document: /Lang | 1 |
| heading: RoleMap level | 1 |
| retype → P | 5 |
| retype → H1 | 1 |
| retype → H2 | 7 |
| retype → H3 | 21 |
| flatten: false list → paragraphs | 26 |
| flatten: nested list/table already flattened with its parent | 6 |
| figure: alt text | 4 |
| links: references to off-page annotations removed | 5 |
| role map: standard tag Sub was remapped to Span; retyped | 45 |
| tag tree index: entries pointing outside the tree removed (IDTree) | 195 |

## Final check with PAC 2026

Open `clans_remediated.pdf` in PAC 2026 (https://pac.pdf-accessibility.org/en, Windows) and run its WCAG check. Anything it fails that is not listed above is a gap in the automated checks: note it in the issue tracker.

No automated check here covers these WCAG 2.2 AA criteria; check them by hand, with PAC's screen-reader and structure previews:

- 1.1.1: alt text is accurate and gives the figure's purpose; decorative images are artifacts
- 1.3.1 / 1.3.2: headings, lists and tables match what is printed, and the reading order makes sense
- 1.4.1: no information is given by colour alone
- 1.4.3: contrast of text over images and coloured backgrounds (PAC's contrast checker)
- 1.4.5: no images of text where real text could be used (scanned pages: the OCR layer stands in)
- 2.4.6: headings describe their section
- 3.1.2: passages in another language carry their language (see `han_review.csv` if present)
