---
title: Troubleshooting
nav_order: 12
---

# Troubleshooting

This page explains what an error message means and what to do about it: when the AI request fails, when a run started from the app stops, and when a PDF is a kind the pipeline doesn't support yet.

## When the AI request fails

`decide.py` prints OpenRouter's own message and code, and says whether anything was charged. The error is also saved in `run.json` (and the full reply in `response.json` or `error.txt`), so a batch summary shows the reason in the PDF's row.

OpenRouter sometimes sends an error inside a normal-looking reply (for example a 429); it is caught the same way. Find the message you see in the first column:

| What you see | What it means | What to do |
|---|---|---|
| `OpenRouter error 429 … rate-limited … Nothing was charged` | The model's maker is throttling requests, often when a batch sends several at once | Wait a few minutes. Single run: the same command again. Batch: `RETRY=1 JOBS=1 MODEL=<same model> AUTO=1 bash batch_api.sh <label> <same folders>` (the summary prints it) |
| `reply was cut off at 48,000 output tokens` | The reply ran out of output tokens; it was paid for | The same command again (batches: add `RETRY=1`): the next attempt allows twice as much, and the estimate shows what it could cost. The previous cost stays in the record. If it was already at the model's maximum, choose another model |
| `rejected the temperature setting … Add "<model>" … to OMIT_TEMPERATURE` | The model refuses a temperature value; nothing was charged or retried | Add the model id (or its prefix) to `OMIT_TEMPERATURE` in `decide.py`, then run again |
| `no provider of <model> accepts our "don't keep or train on the data" setting` | No provider will serve the model under `data_collection: deny`; nothing was sent | Choose another model |
| `OpenRouter error 402` | Not enough credit for the request | Add credit |
| `OpenRouter error 413` | The request was too large | Report it: the figure images are already shrunk to fit |
| `the reply held 2 JSON work orders and the last one … could not be read` / `could not parse a JSON work order` | The reply was paid for but holds no usable work order | Rerun the same command (batches: `RETRY=1`): the saved reply is read again first, then a new request is made if it still can't be used |
| `refusing: …` (before sending) | The model check failed: unknown id, no image input, it can't write as long an answer as the request needs, or the request is too large for its context window | Choose another model; nothing was sent |
| `refusing: this request could cost up to $X, more than the limit of $2.00 per AI request` | One request's Max Estimated Cost passes `MAX_USD` | Run it with the value it names, e.g. `MAX_USD=3`; nothing was sent |
| `refusing before any request: this PDF's N requests could cost up to $X, more than the limit of $5.00 per PDF` | A PDF's requests together, with what previous attempts in the folder spent, pass `BOOK_MAX_USD` (one-request PDFs too) | Run it with the value it names, e.g. `BOOK_MAX_USD=6`; nothing was sent |
| `figure request K: OpenRouter 429; trying once more in 60 s` | A figure request failed without being charged | Nothing: it is sent once more. If it fails again its figures go to a reviewer ("Alt text for N figures") and the run goes on |
| `figure request K: cut off at 32,000 output tokens; sending it once more with room for 64,000` | A figure request's answer ran out of room | Nothing: it is sent once more with twice the room, if your limits allow. If that can't be sent or is cut off again, its figures go to a reviewer ("Alt text for N figures") and the run goes on |
| `the previous attempt was stopped while its figure requests were being sent` | A run was interrupted (Ctrl-C, a crash, the machine asleep) while its figure requests were being sent | Nothing: every cost it had is logged (`earlier_attempts`, and review.md's cost line), and the run starts over after the y/N. A request that was in flight is logged with its charge unknown |
| `refusing: this reply was made with N figure requests, and their answers (reply.txt.passes.json) are not beside it` | A replay (`REPLY=`, `FROM=`) of a run with figure requests, without its answers file | Copy `reply.txt.passes.json` from where the reply came (`FROM=` and `--replay-to` write it); a replay never makes a new request |
| `OpenRouter error <other code>: <message>` | Any other error from OpenRouter or the provider | Read the message; usually run again later |

A failed request that OpenRouter did charge for is logged with its cost and counted in the record and the summary; a rerun with the same label makes a new request.

## Runs started from the app

A run started from the home page that stops shows a card with the reason in plain words. A folded **Details** under it
holds the step, the exit code, the tool's own line, the record and the log. The cases, by step:

| Step | Cases (the card's headline) | The tool's own words (in Details) |
|---|---|---|
| Starting | the book's file can't be found; the app's tools are not set up; the run has already finished; it is waiting for a review; not the same file; a cost limit the run couldn't read | run_api.sh's first lines |
| Intake | locked with a password; a newer format (PDF 2.0, namespaced tags); nothing to tag; the text doesn't match the pages; Chinese, Japanese or Korean text needs its OCR language; can't be opened; a tool is missing; a safety check (a step changed pages); recognition or tagging failed; an error | `_intake/intake.json` `summary` |
| Estimate | the request couldn't be built; the model can't take this book; an error | decide.py's line |
| AI request | the connection failed before anything was sent; the cost went over the limit after the estimate (nothing sent); not enough credit; no key; the service refused; busy (429); the connection was lost during the call (charge unknown); the answer was cut off (its cost kept); the answer couldn't be read; a new AI request is needed (a free rerun that would have called) | decide.py's line, `run.json` `error` |
| Review, apply | the review page couldn't be prepared; decisions made for another file; an error while applying, checking or writing the report | the step's log line |
| Interrupted | stopped before it finished (nothing sent); stopped during the AI request (charge unknown); stopped after the reply (going on is free) | the job file |

"The text doesn't match the pages" offers no button. A reviewer compares the pages, or whoever looks after the app runs
the PDF from the terminal with every page recognized again (`FORCE_OCR=1 OCR_LANG=… bash run_api.sh …`, shown in Details).

An encrypted PDF with only an owner password is not caught yet.

A run from the terminal with `INTAKE=off` skips intake, so `audit.py` is the first step to open the PDF. It stops the
same PDFs with the same words as intake:
- a PDF locked with a password: exit 3, flagged for a reviewer, printed as `audit: stopped: …`
- a PDF that can't be opened at all, such as a damaged or cut-short file: exit 1, printed as `audit: failed: …`

Nothing is written for the PDF, and the app shows the same card as at intake. `apply.py` does the same when it is run on
such a file.

## Not supported yet: PDF 2.0

The pipeline is built for PDF 1.x tagging (PDF/UA-1). Every sample PDF is PDF 1.3–1.7, and the auto-tagger writes PDF 1.x. A PDF 2.0 file is therefore **stopped before any paid request and before any change**, and goes to a reviewer.

A PDF counts as PDF 2.0 when:
- its PDF version is 2.0 or later (the catalog's `/Version` counts when it is later than the header), or
- its tag tree declares namespaces (`/Namespaces` in the structure tree root): PDF 2.0 tagging, even under a 1.7 header.

Intake checks first, tagged or not. It stops the PDF with status `stopped` and exit 3, and `intake.md` / `intake.json` give the reason. A batch shows the PDF as **flagged at intake** and leaves it out of the cost estimate.

**Why it stops instead of running.** veraPDF runs the PDF 1.x WCAG profile, and the audit, executor and checks read only the plain `/RoleMap`. A PDF 2.0 file would be described against the wrong standard, and its correct PDF 2.0 tags could be changed into PDF 1.7 ones. The details are below.

## For developers

### Where the app's failure cards come from

Every case in [Runs started from the app](#runs-started-from-the-app) is a row of `webapp/failures.py`, keyed by step. Each matched string is checked against the tool that prints it (`tests/test_failures.py`).

### How the PDF 2.0 check works

The check is in `lib/support.py`.

- `audit.py` and `apply.py` check again (exit 3) for runs that skip intake (`INTAKE=off`) or reuse an older audit or a saved reply (`FROM=`, `REPLY=`), so no output file is written for such a PDF.
- `tests/test_support.py` checks each of these stops on small PDFs made by the test.
- `scan.py` shows each PDF's support in a **Supported** column, and counts unsupported PDFs in its totals.
- `ALLOW_PDF20=1` lets a PDF through. It is only for building PDF 2.0 support; never use it on real work.

**What would go wrong without the stop.** A copy of an earlier sample book saved as PDF 2.0 gets exactly the PDF/UA-1 result (4 rules), while veraPDF's PDF/UA-2 check (`-f ua2`) fails 8: structure destinations for internal links, `Ref` on contents entries, the Document tag's namespace, the PDF/UA-2 identifier, and others. review.md would describe the PDF against the wrong standard.

Worse, PDF 2.0 types (`FENote`, `Title`, `Aside`, `Em`, `Strong`, `Sub`, `DocumentFragment`) are not standard in PDF 1.7. They can be reported as unmapped (7.1-5) and sent to the AI as `rolemap` decisions. The executor would then retype correct PDF 2.0 tags into PDF 1.7 ones, for example every `FENote` into `Note`, which PDF 2.0 no longer has.

### What full PDF 2.0 support needs

Then remove the guard for PDF 2.0:

1. **veraPDF profile by version:** pin `WCAG-2-2-Machine-PDF20.xml` (veraPDF-validation-profiles `rel/1.30`), and have `vera.start()` choose it for PDF 2.0. Classify its ISO 14289-2 rules in `verapdf/rules.json` (WCAG or PDF/UA-only) and in `vera.py` (`EXECUTOR`, `KEY`, `PERSON`).
2. **Namespace-aware role mapping:** read `/NS` on tags and `/Namespaces` with `RoleMapNS` in `audit.py` (`mapped`, styles), `apply.py` (`mapped`, `RMAP`, `op_rolemap`, `fix_standard_remaps`, `fix_rolemap_cycles`) and `verify.py`.
3. **PDF 2.0 types:** treat `FENote`, `Title`, `Aside`, `Em`, `Strong`, `Sub` and `DocumentFragment` as standard, and never map them back to PDF 1.7 types. Teach the prompt (a new version) the PDF 2.0 equivalents for notes, titles and lists.
4. **PDF/UA-2 requirements the executor could meet:** structure destinations for internal links (8.8-2), `Ref` on TOCI (8.2.5.8-1), the Document tag in the PDF 2.0 namespace (8.2.5.2-2), `Lbl`/`LI` rules, and MathML for formulas (associated files).
5. **Test files:** at least one real tagged PDF 2.0 book; there is none in `samples/` yet.
