# Language tags

Words and passages in a language other than the document's get a language tag (`/Lang`), so a screen reader switches
to that language's voice (WCAG 3.1.2, #118). This page covers how the tags are found, decided, applied, checked and
approved.

## How it works

1. **The audit finds candidates** (`lib/langcands.py`, `lang_candidates.json`): words with marks that English does not
   use (kahakō, macrons, ʻokina), runs in another script (Chinese characters, kana, hangul, Greek, Cyrillic, …) and
   words outside the English word list (SCOWL 2020.12.07). Each printed form is one candidate, with every place it
   occurs. A publisher's own `/Lang` tags are listed too ("existing").
2. **The language step asks the AI** (`name_languages.py`, prompt `prompts/language_v1.md`): each word form with about
   15 words of context, each sentence once per request, through OpenRouter with `data_collection: deny`. The AI names
   a language and a confidence, or says it is a name or English. Nothing else of the book is sent for this step. A book
   flagged for personal information (1.1) is never sent. Requests and replies are kept in `language_run.json`.
3. **The decisions go into the work order** as `language_parts` (version 2: one row per word form, with its places).
   The work-order prompt (`workorder_v11.md`) leaves language tags to this step.
4. **A person decides every form** on the review page's "Languages" section (see [Review page](review-page.md#languages)).
5. **The executor applies the tags** (`apply.py`, `op_language`): a tagged word gets its own Span with `/Lang`; a whole
   element gets `/Lang` on itself. A publisher's tag a person removed is taken off the element and its marked content.
6. **verify.py checks** that every tag holds its words and language. A tag that does not match is a rank-1 finding.

### Chinese, Japanese and Korean

The local rule (`lib/scripts.py`) runs first on every run: hangul is tagged Korean and kana Japanese automatically.
AI parts in the same language as the local tag are dropped; AI parts in another language are split under it.
Chinese characters with no kana (Han-only) may be named Japanese or Chinese by the AI; a person approves it before the
book ships. Han the AI leaves untagged goes to a person (`han_review.csv`), as before.

### Hawaiian

Most Hawaiian words carry a kahakō or ʻokina and are found by their marks. Names of people and places stay untagged.
On pages read whole by the AI (`PAGE_READS`), see [OCR words](ocr-words.md#pages-read-whole).

### What stays untagged

- names of people and places (listed, not decided)
- words in the English list inside English sentences, and dictionary phrases (counted as English)
- titles of works in another language are tagged

## Running it

The step is on by default (`LANG_TAGS=on`, see [Options](options.md#language-tags)). It has its own model
(`LANGUAGE_MODEL`, default the work order's), limit (`LANGUAGE_MAX_USD`, default $4) and form limit
(`LANGUAGE_MAX_FORMS`, default 5000). The PDF's limit (`BOOK_MAX_USD`, default $5) is shared by the work order, the
page readings and this step.

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

Work orders from before #118 (language parts written by the work-order prompt, version 1) are approved with the work
order and read "Not Applicable" here.

## Cost

Sonnet 5.5, measured on the test books (2026-11-13): about $0.09 per 100 forms. A book with 2,800 forms (cadaverous)
cost $2.53; one with 840 forms (ryukyu) $0.78. A book with no candidates costs nothing.
