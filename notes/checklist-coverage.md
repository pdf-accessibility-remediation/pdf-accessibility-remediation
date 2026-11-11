# Checklist coverage

This table tracks which steps of the sponsor's PDF remediation checklist the pipeline handles. The checklist itself is the sponsor's document and is not in the repository; the step numbers and names below are its own. It is for the team and the sponsor. The published docs in `docs/` describe what the pipeline does in plain words and don't cite checklist numbers, so this is the one place the numbers are kept.

The pipeline remediates the PDF itself: it doesn't build a separate document model or write HTML, so the checklist's HTML and document-model steps are marked "Not yet".

**Status:**
- **Done:** the pipeline does this step.
- **Partly:** it does some of the step, as the note says.
- **Not yet:** not built.
- **To check:** not yet confirmed against the code. Confirm it and update the row.

The first version was built on 2026-11-11 from the checklist numbers the docs cited before #22. Update a row in the same PR as the change that moves it.

| # | Step | Status | Where it is handled |
|---|---|---|---|
| 1.1 | Flag documents containing personal information | Not yet | The app doesn't ask yet ([The home page](../docs/home.md)) |
| 1.2 | Check whether the existing text layer is usable | Done | Intake's text-layer test and OCR-layer check ([Intake](../docs/intake.md)) |
| 2.1 | Rasterise each page | Done | OCRmyPDF, in intake |
| 2.2 | Deskew, despeckle, threshold | Not yet | [Intake](../docs/intake.md), "Not done yet" |
| 3.1 | Detect and read text lines (OCR) | Done | OCRmyPDF and Tesseract, in intake |
| 3.2 | Re-read low-confidence lines at higher resolution | Not yet | [Intake](../docs/intake.md), "Not done yet" |
| 3.3 | Rejoin words hyphenated at line ends | To check | |
| 3.4 | Restore missing spaces after punctuation | Done | Intake's word-break check |
| 3.5 | Detect superscript citation markers | To check | |
| 3.6 | Map characters the output font lacks | Done | Intake's private-use characters; font-map corrections in `apply.py`; `verify.py` checks ([Work order](../docs/work-order.md)) |
| 3.7 | Detect document language | Done | Intake's OCR language; the document language in the work order |
| 4.1 | Find column gutter and column edges | Partly | Intake finds two printed pages on one PDF page |
| 4.2 | Mark running heads and page numbers by position | Done | Auto-tagger; band rules in `apply.py` ([Work order](../docs/work-order.md)) |
| 4.3 | Confirm running heads by repetition across pages | To check | |
| 4.4 | Measure ink weight and type size per line | To check | |
| 5.1 | Find figures the PDF declares as images | Done | Audit figure crops; intake marks a whole-page scan image as decoration |
| 5.2 | Find figures from non-text ink | To check | |
| 5.3 | Reject ruled boxes and borders as figures | To check | |
| 5.4 | Absorb chart labels into their figure | To check | |
| 5.5 | Attach captions | To check | |
| 5.6 | Detect tables | Partly | Auto-tagger (OpenDataLoader, local mode); hybrid mode not yet |
| 5.7 | Build table rows, columns, cells | Partly | As 5.6 |
| 5.8 | Handle spanning and nested cells | Partly | As 5.6 |
| 5.9 | Decide header rows and columns | Done | The AI's table headers in the work order |
| 5.10 | Identify asides, sidebars, adverts | To check | |
| 5.11 | Declare regions detection misses | To check | |
| 6.1 | Split pages into full-width and multi-column bands | Partly | Intake reorders spreads by half |
| 6.2 | Order blocks within each band | Partly | As 6.1 |
| 6.3 | Detect side-by-side blocks within a column | To check | |
| 6.4 | Flag pages whose order is ambiguous | Done | The audit flags sections read out of their printed place (`lib/readorder.py`) |
| 6.5 | Resolve order on flagged pages | Done | The AI's section moves (`move_section`), checked by the reviewer |
| 7.1 | Identify the document title | Done | Title in the work order |
| 7.2 | Detect headings | Partly | Auto-tagger for untagged PDFs; the AI retypes tags |
| 7.3 | Merge headings wrapped over two lines | To check | |
| 7.4 | Assign heading levels | Done | The AI's heading levels in the work order |
| 7.5 | Detect lists and list items | Partly | Auto-tagger; list rule (`lib/listrule.py`) |
| 7.6 | Join lines into paragraphs | To check | |
| 7.7 | Correct roles the steps above got wrong | Done | Review page ([Reviewing the work order](../docs/review-step.md)); hand edits |
| 8.1 | Decide decorative vs informative | Done | The AI's decoration decisions |
| 8.2 | Draft alt text and long description | Done | The AI's alt text; intake removes the auto-tagger's placeholder alt text |
| 8.3 | Review and approve each description | Done | Review page; release evaluation ([Accessibility evaluation and release](../docs/release.md)) |
| 9.1 | Assemble one document model | Not yet | The pipeline edits the PDF directly |
| 9.2 | Record provenance and review status per element | Partly | `record.json` keeps the AI's work order, the model, the prompt and who reviewed it |
| 9.3 | Check every human correction still attaches to an element | To check | Reopened reviews carry earlier decisions |
| 10.1 | Emit semantic HTML | Not yet | |
| 10.2 | Export figure images alongside the HTML | Not yet | |
| 10.3 | Rebuild PDF pages as image artifacts | Done | OCRmyPDF, for scanned pages |
| 10.4 | Add an invisible text layer with a Unicode-mapped font | Done | OCRmyPDF, for scanned pages |
| 10.5 | Build the PDF structure tree and tags | Done | Auto-tagger in intake; placeholder tag trees are retagged |
| 10.6 | Set title and language metadata | Done | Work order (PDF only) |
| 10.7 | Reflowable tagged PDF | Not yet | |
| 10.8 | DOCX or EPUB output | Not yet | |
| 11.1 | Score text against a hand-corrected reference | Not yet | [Intake](../docs/intake.md), "Not done yet" |
| 11.2 | Run automated checkers | Partly | veraPDF on every run ([Verification with veraPDF](../docs/verapdf.md)); PAC in the release evaluation; no HTML, so no axe-core |
| 11.3 | Screen-reader task test with real users | Not yet | The release evaluation is a staff check ([Accessibility evaluation and release](../docs/release.md)) |
| 11.4 | Time the whole job vs remediating by hand | To check | |
| 11.5 | Track cost and runtime | Done | Cost per page in batch summaries; cost and timing in `record.json` |
| 11.6 | Process many documents in one run | Done | [Batch runs](../docs/batch-runs.md) |

The three AI rules:

1. **The AI never writes the document's text.** Spoken text (ActualText) must match the print ([Work order](../docs/work-order.md)); OCR readings of Hawaiian pages are drafts until a reader of Hawaiian approves them ([OCR words](../docs/ocr-words.md)).
2. **A person reviews AI output before it ships.** Done: the review step and the release evaluation. `record.json` stores the model, the prompt and the reviewer.
3. **Documents with personal information never go to a cloud API.** Not yet: depends on 1.1.
