# Language tags

Words and passages in a language other than the document's get a language tag (`/Lang`), so a screen reader switches
to that language's voice (WCAG 3.1.2, #118). This page covers how the tags are found, decided, applied, checked and
approved.

## How it works

1. **The audit finds candidates** (`lib/langcands.py`, `lang_candidates.json`): words with marks that English does not
   use (kahakō, macrons, ʻokina), runs in another script (Chinese characters, kana, hangul, Greek, Cyrillic, …) and
   words outside the English word list (SCOWL 2020.12.07). Each printed form is one candidate, with every place it
   occurs. A publisher's own `/Lang` tags are listed too ("existing").
   - **A word that ends in a hyphen is joined with the next word** only when the hyphen is at a real line end (the
     line-end test below), or when the joined word is English (a real break the test misjudges, beside a drop cap or a
     narrow gutter: "prac-" + "tices"). A hyphen inside its line ("homes-abroad", whose second part some PDFs draw
     after the next line's first word) is no join: each part is a word of its own, as an unbroken word is.
   - **A word broken by a hyphen at a line end** is checked joined, both without its hyphen ("infor-" + "mation") and
     with it ("long-" + "standing"); English either way, it is no candidate. The form with the hyphen counts only when
     each half has three or more plain letters and the joined word does not have the shape of romanized Japanese or
     Chinese, so a romanized word split into English-looking syllables ("keg-" + "are" for *kegare*) stays a candidate.
     And a broken word the book also prints whole somewhere stays a candidate ("bum-" + "bye" where *bumbye* is printed
     whole; `langcands.book` reads the book twice, the second time only on the pages concerned). Any whole spelling
     counts, including those inside URLs and bibliography entries.
   - **Both halves of a broken candidate are tagged** when the break is a real line end: the hyphen is the last visible
     character on its line (nothing visible to its right within about one em, its font size) and the second half
     starts its own line (nothing visible to its left within one em). Then, in one run, one place covers both halves;
     in two runs, the second half is a place of its own with the same word form, so one decision tags both lines.
     Otherwise the hyphen is inside a line ("homes-abroad", "non- Western", whose second part some PDFs draw after the
     next line's first word): the word that follows in the text keeps no tag of the first part's, as before.
   - **Known misses of the hyphen check:** a non-English word broken at a line end whose two halves are both English
     words, that has no romanized Japanese or Chinese shape, and that the book never prints whole, is taken for
     English, so that place goes untagged. It happens in any language (Javanese, Indonesian, Hawaiʻi Pidgin, Dutch, …).
     Javanese *madjoe* broken as "mad-" + "joe" was one; it is found now, since its book prints *madjoe* whole elsewhere.
     The Dutch suspended hyphen in "taal-, land- en volkenkunde" stays one: *taal* is itself in the English word list.
     A second pattern: a word hyphenated inside its line whose real continuation the PDF draws elsewhere in the text,
     and whose first part alone is short (under four letters), capitalized without marks, or English, is no candidate.
     Examples: the Anindilyakwa morphemes on an interlinear page ("ki-", "ku-", "na-"), and Hawaiian "uka-".
2. **The language step asks the AI** (`name_languages.py`, prompt `prompts/language_v3.md`): each word form with its
   context, each snippet once per request, through OpenRouter with `data_collection: deny`. The context
   (`lib/langreq.py` `CTX`) is 10 words on each side of up to two places per form (a word is a piece with a letter or
   a CJK character; numbers and punctuation ride along without counting); a piece of CJK characters with no spaces
   keeps only the 40 characters nearest the place; windows that meet on a page are sent as one snippet, and each word
   form lists the numbers of the snippets that hold it. This setup was chosen by paid experiments (2026-11-14, 473 test
   items, 3 runs per variant) against 5, 15 and 30 words, 15 space-separated pieces, a sentence each side, and unjoined
   or unnumbered snippets: longer contexts gave more wrong answers, and so did 5 words. Against 15 pieces, 10 words gave
   fewer wrong answers where the reading beside Chinese characters was removed and left a few more to a person, at the
   same cost; the differences are small (a few items). Requests of 150 and 50 forms: see [Request size](#request-size).
   The review page shows each form's first
   place exactly as it is sent; rows of runs made before this keep the context stored when their language step ran. The AI names
   a language and a confidence, or says it is a name or English. Nothing else of the book is sent for this step. A book
   flagged for personal information (1.1) is never sent. Requests and replies are kept in `language_run.json`.
   A decision's tag must be one the pipeline can name (`lib/langtag.py` `NAMES`): every tag the prompt asks for is
   there (a test checks it), as are romanized Ancient Greek (`grc-Latn`) and Tok Pisin (`tpi`), added after the AI gave
   them with good reason (#137), and Javanese (`jv`) and Anindilyakwa (`aoi`), whose words the finder's line-end join
   gives back (#140); a tag outside the table is not used, and its word goes to a person. As with every language in the
   table, a publisher's `/Lang` that names Javanese or Anindilyakwa ("Javanese") is now written by the executor as `jv`
   or `aoi` when its words fit, and the three-letter `jav` is shortened to `jv`.
   Each decision echoes its word form, as a guard against an answer landing on the wrong word. A request shows a form
   twice: cleaned in its item ("Tenpyō hōji ninen Naishōsen") and as printed where it is marked in the text
   ("Tenpyō hōji ninen: Naishōsen", or one line's half of a word broken at a line end), and the AI sometimes copies the
   printed one. So an echo is used when it matches the item's form with spacing and case ignored, or when its letters
   and digits alone match the item's form or one of its marked texts and no other item's in the same request (#137);
   otherwise it is not used. Each request's marked texts are kept in `language_run.json` (`id_marks`, not in the
   record), so a replay compares them as sent. An answer the check throws away is kept in the record
   (`language_run.dropped`: the word form, what the answer echoed, its tag and confidence, and a `code`: `echo`, `tag`,
   `invalid`, …; up to 2,000, with `dropped_count`). Each word form with no AI decision carries why in its
   `language_parts` entry (`no_answer`: `echo`, `tag`, `invalid`, `not_answered`, `cut_off` or `failed`), which the
   review page words as "No AI answer (…)" and review.md counts in its Language Tags section ("No AI answer (N word
   forms): …", in plain words). Phrases English dictionaries
   list (*a priori*, *ad hoc*) count as English. (language_v3 is language_v1 with these two lines from language_v2,
   adopted after a paid check on the test items, 2026-11-13: 248 and 249 right against 246 and 232, the same one wrong
   medium-confidence answer, no reply cut off.)
3. **The decisions go into the work order** as `language_parts` (version 2: one row per word form, with its places).
   The work-order prompt (`workorder_v11.md`, and `workorder_v12.md` after it) leaves language tags to this step.
4. **A person decides every form** on the review page's "Languages" section (see [Review page](review-page.md#languages)),
   one by one or with a group approval ([Group approval](review-page.md#group-approval), #124).
5. **The executor applies the tags** (`apply.py`, `op_language`): a tagged word gets its own Span with `/Lang`; a whole
   element gets `/Lang` on itself. A publisher's tag a person removed is taken off the element and its marked content;
   one a person kept ("Keep the Tag") loses only a different `/Lang` in its marked content, so the kept tag is the one
   read. A publisher's language name (`Hawaii`, `Hungarian`) is shown on the review page by the language it names, with
   the value as written; the executor writes its code and lists each conversion in review.md, unless the words look like
   another language (then it stays for a person: see [veraPDF](verapdf.md), 7.2-29).
   A tag the executor can't place (the page would look different, the words sit under an element with its own spoken
   text, …) is left out, and the page and its text stay as they were. review.md's "Not placed by the executor (N)" counts
   these by reason. Under each reason it lists every place: the words (an excerpt), the language and the page, as
   `"mono no aware" (Japanese (Romanized)) · PDF 12 (printed 3)`. It shows 20 per reason; the rest are in
   `record.json` (`apply.language_parts.refused_places`, the first 200 places in all). review.html shows the same list,
   nested under each reason.
6. **verify.py checks** that every tag holds its words and language. A tag that does not match is a rank-1 finding.

### Chinese, Japanese and Korean

The local rule (`lib/scripts.py`) runs first on every run: hangul is tagged Korean and kana Japanese automatically.
AI parts in the same language as the local tag are dropped; AI parts in another language are split under it.
Chinese characters with no kana (Han-only) may be named Japanese or Chinese by the AI; a person approves it before the
book ships. Han the AI leaves untagged goes to a person (`han_review.csv`), as before.

**Decided by the reading printed beside them (#123).** Before any request, `lib/hanreading.py` decides a Han-only word
form without the AI when every place of it has a reading directly beside it and all of them name the same language:

- **Readings:** kana or a Hepburn word (Japanese), a pinyin word (Chinese), or hangul, a McCune-Reischauer word with
  breves or a Revised Romanization word in a book on Korea (Korean), printed right before the characters (a piece of
  punctuation alone may sit between), or kana or hangul right after them. A romanization after the characters is never
  taken: in a list it is the next entry's. These are the rules the test tools used to make answer keys
  (`tools/lang_test.py` now imports them).
- **A word that introduces the characters is never their reading:** one ending with a colon, semicolon or period. In a
  bibliography that is the publisher's name before a title ("Tokyo: Kōdansha. 自然と文化…", invented), the trap that
  made the issue ask to leave glossary and bibliography lines out. This guard is the pipeline's only; the test tools'
  answer keys were made without it.
- **Glossaries and bibliographies are not left out.** The issue asked for it, but measured (2026-11-15) it cut the forms
  decided on the large Japanese-subject test book from 492 to 318 and on the Ryukyu book from 18 to 0, while every form
  it left out that was checked was right (35 of 35 sampled, and all 18). The guard above catches the real trap.
- **Never in a Chinese, Japanese or Korean document** (its Han-only text is the body's language).
- **What it writes:** the decision (`rule: "reading"`, high confidence, the reading as evidence) goes into
  `language_parts` like the AI's, and into `language_run.json` under `local` (the AI's stay under `decisions`). The
  form is never sent and never counted in the estimate (`language_estimate.json` `local`). A person approves it on
  the review page like the AI's. A saved reply never overrides it.
- **Turn it off** with `LANG_READING_RULE=off`.

Measured 2026-11-15 (free, no AI request; checked by eye where it says so):
- **The large Japanese-subject test book** (cadaverous, 2,722 forms, 1,276 of them Han-only): 492 decided (425 Japanese, 67 Chinese), against 494 by the rule without the guard. The step's worst case drops from $4.84 to $3.98 (19 requests to 15). Checked by eye: the 47 Chinese outside the bibliography and index, 40 Japanese, and 35 of the 174 in the bibliography and index; one is wrong (see the known limit).
- **The Ryukyu book** (814 forms, 488 Han-only, its characters all in its character list and bibliographies): 18
  decided, all checked right by eye; the guard refused 16 that the issue's count of 34 had included, publisher names
  read as readings.
- **Moral Foods**: 302 (209 Chinese, 92 Japanese, 1 Korean), most in its glossary; 36 checked, all right. **Teika**: 4 (the guard refuses a Chinese couplet after "the Wakan rōeishū:"). **Global Asias**: 5.
- **Known limit:** a name in another language whose romanization has the shape of pinyin is read as Chinese (one on the
  large test book: a Korean monk's name). A person approves every form, and the row shows the reading.

**Every Han-only form's reading (#124)** is kept with its `language_parts` entry as `reading` (its language, every
language found, the first reading, places with one, places), counted over its places outside bibliographies, with kana
in the same phrase as the characters (大福もち) counted too. The review page's "Approve Characters with Matching
Readings" uses it: see [Review page](review-page.md#group-approval). Measured 2026-11-15: 370 forms on cadaverous have a
reading of one language this way (361 of them decided by the rule), 90 on moralfoods (73) and 40 on the Ryukyu book (5).
A form the rule decided only from bibliography entries has none, so it is approved on its own row.

### Hawaiian

Most Hawaiian words carry a kahakō or ʻokina and are found by their marks. Names of people and places stay untagged.
On scanned pages read whole by the AI (page readings, `PAGE_READS`), a whole line or element (a paragraph, a list
item, a cell) is tagged `haw` when at least 60% of its words, and at least 3, have Hawaiian shape and one of them is not
an English word, and none of its words is outside the English list with a letter Hawaiian lacks (the letter guard: *te*,
*whare*, *fiefia* rule out Māori, Tongan, Samoan …; a word the page reading corrected is read as corrected) (`apply.py`
`haw_elements`). These tags come from a fixed rule, not the Languages section: review.md lists each one under "Language
Tags" for the person who reads Hawaiian and checks those pages, and verify.py counts them with the other language tags.
See [OCR words](ocr-words.md#pages-read-whole).

### What stays untagged

- names of people and places (listed, not decided)
- words in the English list inside English sentences, and dictionary phrases (counted as English)
- titles of works in another language are tagged

## Running it

Two options are off by default: `LANG_GROW=on` tags a title in another language whole (the voice switches once, not
mid-title), and `LANG_GROUP=on` makes adjacent single Chinese characters one word form. Title growth stays off until a
screen-reader check of a title tagged in pieces (see [Options](options.md#language-tags)).

The step is on by default (`LANG_TAGS=on`, see [Options](options.md#language-tags)). It has its own model
(`LANGUAGE_MODEL`, default Sonnet 5.5, whatever model the work order uses), limit (`LANGUAGE_MAX_USD`, default $6) and form limit
(`LANGUAGE_MAX_FORMS`, default 5000). The PDF's limit (`BOOK_MAX_USD`, default $8) is shared by the work order, the
page readings and this step. The step never stops the work order: when it doesn't fit the PDF's limit with the work order,
or passes its own limit, it alone is left out and the PDF goes on without language tags (see
[The limit per PDF](options.md#the-limit-per-pdf)).

### Sending, retries and interruptions

#135 (parallel requests):
- **Several requests at once:** up to `AI_PARALLEL` (default 4, per PDF; see [Options](options.md#model-and-cost)).
  `AI_PARALLEL=1` sends them one after another, in order. The replies are kept in request order, whatever order they
  come back in. The log prints one line per request as it finishes ("request 3 of 15: …, done in 41 s (5 of 15 done)").
- **One retry:** a request that fails (an error from OpenRouter, no connection, no reply in time, or a reply with no
  decisions that can be read) is sent once more, 60 s after "too many requests" (429) and 20 s after anything else. It is
  sent only when its worst case still fits both the step's limit (`LANGUAGE_MAX_USD`) and the PDF's (`BOOK_MAX_USD`, with
  what the PDF has spent); otherwise the record says which limit had no room. A request that still fails leaves its word
  forms to a person ("No AI answer", `failed`).
- **A reply cut off, or read only in pieces** (not valid JSON as a whole, its decisions read one by one), keeps every
  decision it finished. The word forms it never reached (no decision, and no refused answer of their own) are sent once
  more, as one smaller request
  (`language_requests/NNNr.request.json`; its entry in `language_run.json` has `resend_of`). That resend is never resent
  itself. Answers the check refused (`echo`, `tag`, `invalid`) are never sent again: the same answer would most likely
  come back, and it would be paid for twice. A rerun with the same model and prompt reuses the pair, with no new request.
- **An interruption** (Ctrl+C in a terminal run of `run_api.sh`, `batch_api.sh` or `name_languages.py`, or an error
  while requests are out) sends nothing more: no waiting request starts, and the step does not wait for the requests
  already sent. Those may still be charged. Each is kept in `language_run.json` under `stopped_in_flight` at its worst
  case, since its charge isn't known, and counts toward the PDF's limit (never as money spent). So an interruption can
  cost what the requests already sent cost, at most their worst cases. A rerun keeps these, and what an earlier attempt
  paid (`earlier_cost_usd`), even with another model or prompt. review.md's run line names any such worst case apart
  from the cost ("up to $X more for N AI request(s) … whose charge is not known").

| File | What it holds |
|---|---|
| `audit/lang_candidates.json` | every candidate form and its places |
| `language_estimate.json` | the expected and worst-case cost, before any request |
| `language_run.json` | model, prompt, each request's reply, usage, cost, the AI's decisions by form, the reading rule's (`local`, `reading_rule`); while requests are out, `in_flight` (each one's worst case); after an interruption, `stopped_in_flight` |
| `reviews/_audit/language_contexts.json` | the context lines the review page shows |

## The Ready rule

"Ready to Ship?" lists "Language Tags":
- **Not Applicable** when the word forms for the language step were counted and there were none: the audit's
  candidates (kana and hangul are tagged locally and don't count) and the PDF's own language tags;
- **Not Done (why)** when it found some but the step decided none. This blocks Ready, since the book would ship
  without language tags. The reason is one of:
  - "the language step was turned off" (`LANG_TAGS=off`);
  - "the language step was left out: over the limit per PDF";
  - "the language step was left out: over its own limit";
  - "the language step did not finish";
  - "the language step was not run".
- **Not Done (not checked)** when the count couldn't be made (the audit's `lang_candidates.json` missing, or an
  error): the line fails closed and blocks Ready.
- **Not Reviewed (N word forms to decide on the review page)** until a person has decided every form;
- **Not Reviewed (N word forms the AI left untagged to confirm on the review page)** when the step ran but the AI
  proposed no tag at all: every form is then a row under "Left Untagged by the AI", for a person to confirm or tag,
  so the line never reads Not Applicable after the step ran;
- **Approved (reviewer on date)** when none is left.

The record keeps what happened as `language_status` (`candidates`: the word forms found, and `state`). A record made
before this (2026-11-14) has none, and its line reads as it did.

Work orders from before #118 (the work-order prompt's `language` key: kana runs and explicit runs) are approved with the
work order and read "Not Applicable" here. Runs made during #118's stage C (`language_parts` version 1, before the
Languages section existed) have no rows to decide: their "Language Tags" line stays "Not Reviewed". To review such a
book, run it again (a fresh run, or a FROM= rerun with LANG_REPLY= of a version 2 language run).

## Request size

A request holds up to 150 word forms of one book (`lib/langreq.py` `FORMS_PER_REQUEST`), under that book's title.
This was tested on 2026-11-14 against 50 forms a request, on the same first 300 or 150 word forms of three test books
(Chinese in Hawaii, the Ryukyus, a book on Japan), each request under its own book's title, 3 runs each: 150 forms gave
no more wrong answers than 50 (2 against 14 over three runs on 46 test items; 0 against 4 counted once per item) and
the same number left for a person, at a lower cost. An earlier test that mixed books in one request lost each book's
title, and showed how much the title matters (Cantonese answers on the book on Chinese in Hawaii).

## Cost

Each request's answer may run to 800 tokens plus 200 for each of its first 20 word forms and 130 for each further one
(`lib/costs.py allowance`; raised 2026-11-14 after 58 of 1,040 test replies reached the earlier 300 + 100 per form).
Output is billed as used, so this raises only the worst case the estimate shows, not what a book costs. On cadaverous (2,722 forms, 19 requests, 10 words of context) the worst case is about $4.84 (expected about $2.90),
within the language step's default limit of $6; with the work order it is about $5.46, within the default $8 per PDF.

Sonnet 5.5 stays the language step's model (2026-11-14): Opus 5.5 was no more accurate on the 473 test items and costs
about 2.2 times as much. Sonnet 5.5, measured on the test books (2026-11-13): about $0.09 per 100 forms. A book with 2,800 forms (cadaverous)
cost $2.53; one with 840 forms (ryukyu) $0.78. A book with no candidates costs nothing.
