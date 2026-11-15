# Language tags

Words and passages in a language other than the document's get a language tag (`/Lang`), so a screen reader switches
to that language's voice (WCAG 3.1.2, #118). This page covers how the tags are found, decided, applied, checked and
approved.

## How it works

1. **The audit finds candidates** (`lib/langcands.py`, `lang_candidates.json`): words with marks that English does not
   use (kahakō, macrons, ʻokina), runs in another script (Chinese characters, kana, hangul, Greek, Cyrillic, …) and
   words outside the English word list (SCOWL 2020.12.07). Each printed form is one candidate, with every place it
   occurs. A publisher's own `/Lang` tags are listed too ("existing").
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
   Each decision echoes its word form; one whose form doesn't match its item is not used. Phrases English dictionaries
   list (*a priori*, *ad hoc*) count as English. (language_v3 is language_v1 with these two lines from language_v2,
   adopted after a paid check on the test items, 2026-11-13: 248 and 249 right against 246 and 232, the same one wrong
   medium-confidence answer, no reply cut off.)
3. **The decisions go into the work order** as `language_parts` (version 2: one row per word form, with its places).
   The work-order prompt (`workorder_v11.md`) leaves language tags to this step.
4. **A person decides every form** on the review page's "Languages" section (see [Review page](review-page.md#languages)).
5. **The executor applies the tags** (`apply.py`, `op_language`): a tagged word gets its own Span with `/Lang`; a whole
   element gets `/Lang` on itself. A publisher's tag a person removed is taken off the element and its marked content;
   one a person kept ("Keep the Tag") loses only a different `/Lang` in its marked content, so the kept tag is the one
   read. A publisher's language name (`Hawaii`, `Hungarian`) is shown on the review page by the language it names, with
   the value as written; the executor writes its code and lists each conversion in review.md, unless the words look like
   another language (then it stays for a person: see [veraPDF](verapdf.md), 7.2-29).
6. **verify.py checks** that every tag holds its words and language. A tag that does not match is a rank-1 finding.

### Chinese, Japanese and Korean

The local rule (`lib/scripts.py`) runs first on every run: hangul is tagged Korean and kana Japanese automatically.
AI parts in the same language as the local tag are dropped; AI parts in another language are split under it.
Chinese characters with no kana (Han-only) may be named Japanese or Chinese by the AI; a person approves it before the
book ships. Han the AI leaves untagged goes to a person (`han_review.csv`), as before.

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
(`LANGUAGE_MODEL`, default Sonnet 5.5, whatever model the work order uses), limit (`LANGUAGE_MAX_USD`, default $4) and form limit
(`LANGUAGE_MAX_FORMS`, default 5000). The PDF's limit (`BOOK_MAX_USD`, default $5) is shared by the work order, the
page readings and this step. The step never stops the work order: when it doesn't fit the PDF's limit with the work order,
or passes its own limit, it alone is left out and the PDF goes on without language tags (see
[The limit per PDF](options.md#the-limit-per-pdf)).

| File | What it holds |
|---|---|
| `audit/lang_candidates.json` | every candidate form and its places |
| `language_estimate.json` | the expected and worst-case cost, before any request |
| `language_run.json` | model, prompt, each request's reply, usage, cost, the decisions by form |
| `reviews/_audit/language_contexts.json` | the context lines the review page shows |

## The Ready rule

"Ready to Ship?" lists "Language Tags":
- **Not Applicable** when the book has no word forms to decide;
- **Not Reviewed (N word forms to decide on the review page)** until a person has decided every form;
- **Approved (reviewer on date)** when none is left.

Work orders from before #118 (the work-order prompt's `language` key: kana runs and explicit runs) are approved with the
work order and read "Not Applicable" here. Runs made during #118's stage C (`language_parts` version 1, before the
Languages section existed) have no rows to decide: their "Language Tags" line stays "Not Reviewed". To review such a
book, run it again (a fresh run, or a FROM= rerun with LANG_REPLY= of a version 2 language run).

## Request size

A request holds up to 150 word forms of one book (`lib/langreq.py` `FORMS_PER_REQUEST`), under that book's title.

## Cost

Each request's answer may run to 800 tokens plus 200 for each of its first 20 word forms and 130 for each further one
(`lib/costs.py allowance`; raised 2026-11-14 after 58 of 1,040 test replies reached the earlier 300 + 100 per form).
Output is billed as used, so this raises only the worst case the estimate shows, not what a book costs. On cadaverous
(2,722 forms, 19 requests) the worst case is now about $4.91 (was $3.74), which passes the default `LANGUAGE_MAX_USD` of
$4: the step is then left out of the run unless the limit is raised (see [The limit per PDF](options.md#the-limit-per-pdf)).

Sonnet 5.5 stays the language step's model (2026-11-14): Opus 5.5 was no more accurate on the 473 test items and costs
about 2.2 times as much. Sonnet 5.5, measured on the test books (2026-11-13): about $0.09 per 100 forms. A book with 2,800 forms (cadaverous)
cost $2.53; one with 840 forms (ryukyu) $0.78. A book with no candidates costs nothing.
