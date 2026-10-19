---
title: Troubleshooting
nav_order: 12
---

# Troubleshooting

## When the model call fails

`decide.py` prints OpenRouter's own message and code, and says whether anything was charged. The error is also saved in `run.json` (and the full reply in `response.json` or `error.txt`), so a batch summary shows the reason in the book's row. OpenRouter sometimes sends an error inside a normal-looking reply (for example a 429); it is caught the same way.

| What you see | What it means | What to do |
|---|---|---|
| `OpenRouter error 429 … rate-limited … Nothing was charged` | The model's maker is throttling requests, often when a batch sends several at once | Wait a few minutes. Single run: the same command again. Batch: `RETRY=1 JOBS=1 MODEL=<same model> AUTO=1 bash batch_api.sh <label> <same folders>` (the summary prints it) |
| `reply was cut off at 48000 output tokens` | The reply ran out of output tokens; it was paid for | The same command with `MAX_TOKENS=96000` (batches: add `RETRY=1`). The earlier cost stays in the record |
| `rejected the temperature setting … Add "<model>" … to OMIT_TEMPERATURE` | The model refuses a temperature value; nothing was charged or retried | Add the model id (or its prefix) to `OMIT_TEMPERATURE` in `decide.py`, then run again |
| `no provider of <model> accepts our "don't keep or train on the data" setting` | No provider will serve the model under `data_collection: deny`; nothing was sent | Choose another model |
| `OpenRouter error 402` | Not enough credit for the request | Add credit, or lower `MAX_TOKENS` |
| `OpenRouter error 413` | The request was too large | Report it: the figure images are already shrunk to fit |
| `the reply held 2 JSON work orders and the last one … could not be read` / `could not parse a JSON work order` | The reply was paid for but holds no usable work order | Rerun the same command (batches: `RETRY=1`): the saved reply is read again first, then a new call is made if it still can't be used |
| `refusing: …` (before sending) | The model check failed: unknown id, no image input, output limit under `MAX_TOKENS`, or the request too large for its context window | Choose another model or adjust `MAX_TOKENS`; nothing was sent |
| `OpenRouter error <other code>: <message>` | Any other error from OpenRouter or the provider | Read the message; usually run again later |

A failed call that OpenRouter did charge for is logged with its cost and counted in the record and the summary; a rerun with the same label makes a new call.

## Not supported yet: PDF 2.0

The pipeline is built for PDF 1.x tagging (PDF/UA-1): veraPDF runs the PDF 1.x WCAG profile, and the audit, executor and checks read only the plain `/RoleMap`. Every sample book is PDF 1.3–1.7, and the auto-tagger writes PDF 1.x. A PDF 2.0 book is therefore **stopped before any paid call and before any change**, and goes to a person.

**What happens now** (`lib/support.py`):

- A book is unsupported when its PDF version is 2.0 or later (the catalog's `/Version` counts when it is later than the header), or when its tag tree declares namespaces (`/Namespaces` in the structure tree root: PDF 2.0 tagging, even under a 1.7 header).
- `intake.py` checks first, tagged or not: it stops with status `stopped` and exit 3, and `intake.md` / `intake.json` give the reason. A batch shows the book as **flagged at intake** and leaves it out of the cost estimate.
- `audit.py` and `apply.py` check again (exit 3) for runs that skip intake (`INTAKE=off`) or reuse an older audit or a saved reply (`FROM=`, `REPLY=`), so no output file is written for such a book.
- `scan.py` shows each book's support in a **Supported** column, and counts unsupported books in its totals.
- `ALLOW_PDF20=1` lets a book through. It is only for building PDF 2.0 support; never use it on real work.

**Why it stops instead of running.** A copy of clans saved as PDF 2.0 gets exactly the PDF/UA-1 result (4 rules), while veraPDF's PDF/UA-2 check (`-f ua2`) fails 8 (structure destinations for internal links, `Ref` on contents entries, the Document tag's namespace, the PDF/UA-2 identifier …): review.md would describe the book against the wrong standard. Worse, PDF 2.0 types (`FENote`, `Title`, `Aside`, `Em`, `Strong`, `Sub`, `DocumentFragment`) are not standard in PDF 1.7, so they can be reported as unmapped (7.1-5) and sent to the model as `rolemap` decisions; the executor would then retype correct PDF 2.0 tags into PDF 1.7 ones (e.g. every `FENote` into `Note`, which PDF 2.0 no longer has).

**Future implementation** (what full support needs, then remove the guard for PDF 2.0):

1. **veraPDF profile by version:** pin `WCAG-2-2-Machine-PDF20.xml` (veraPDF-validation-profiles `rel/1.30`), have `vera.start()` choose it for PDF 2.0, and classify its ISO 14289-2 rules in `verapdf/rules.json` (WCAG or PDF/UA-only) and in `vera.py` (`EXECUTOR`, `KEY`, `PERSON`).
2. **Namespace-aware role mapping:** read `/NS` on tags and `/Namespaces` with `RoleMapNS` in `audit.py` (`mapped`, styles), `apply.py` (`mapped`, `RMAP`, `op_rolemap`, `fix_standard_remaps`, `fix_rolemap_cycles`) and `verify.py`.
3. **PDF 2.0 types:** treat `FENote`, `Title`, `Aside`, `Em`, `Strong`, `Sub` and `DocumentFragment` as standard and never map them back to PDF 1.7 types; teach the prompt (a new version) the PDF 2.0 equivalents for notes, titles and lists.
4. **PDF/UA-2 requirements the executor could meet:** structure destinations for internal links (8.8-2), `Ref` on TOCI (8.2.5.8-1), the Document tag in the PDF 2.0 namespace (8.2.5.2-2), `Lbl`/`LI` rules, and MathML for formulas (associated files).
5. **Test files:** at least one real PDF 2.0 tagged book; there is none in `samples/` yet.
