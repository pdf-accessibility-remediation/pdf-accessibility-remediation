---
title: Upload and single runs
parent: The home page (new runs and batches)
grand_parent: Review and ship
nav_order: 2
---

# Uploading a PDF and starting a run

This page is for library staff starting work on one PDF: uploading it, getting the free estimate, choosing the language of scanned pages, and selecting "Start Remediation". Internals are at the end, under [For developers](#for-developers).

## Upload a PDF

The drop zone (dashed border, an upload icon) has **Choose PDFs**, "or drag PDFs here", and "A copy goes into the app's folder; the file you choose is not changed." You can add several PDFs at once, chosen or dropped; **Choose PDFs** is the keyboard path.

Each PDF is copied from your computer into the uploads folder (`uploads/` at the repository root, git-ignored), one after the other. The files you choose are only read by your browser; the app never sees their paths. A PDF dropped elsewhere on the page is ignored; it never opens in the tab.

Under the drop zone are the PDFs added this way, each with its pages and size, **New Run**, a "⋯" menu (**Edit Name**, **Move to Trash**), and a narrow **Select** column to pick PDFs for **Create a New Batch** ("Select two or more PDFs first.").

**When a file fails,** it gets its own sentence ("notes.txt": this file isn't a PDF; "x.pdf": This PDF is already in the list as "…"). A PDF added but locked with a password, or unreadable, says so. The PDFs that were added are still shown first.

- **The same content already listed** (an added PDF, by sha256) is refused, naming where it is.
- **Never replaced:** a second PDF with the same file name becomes `name-2.pdf`.
- **A PDF locked with a password** is listed as locked, with no **New Run**.

The samples folder is never listed. The app only looks there, by sha256 and read only, for the original of a run made from it, so "Review Again" and the first apply of such runs keep working.

### Each run carries its own PDF

The upload list holds only PDFs not used yet.

- **Starting a run** ("Get the Estimate") moves the PDF, with its note, into the run's own folder, `runs/<name>/<label>/source/<file name>.pdf`. It leaves the upload list, and every step of that run uses that copy: the estimate's command, "Start Remediation", the first apply, the review record and **Review Again**. Nothing writes to it, and report.py's clean-up leaves it.
- **When the move can't be made,** the run isn't started and nothing is moved ("The PDF couldn't be moved into the run's folder …").
- **A batch** does the same for each of its PDFs, all or none (`runs/batches/<label>/<name>/source/`).
- **"New Run of This PDF"** (a single run's "⋯" menu, and a batch PDF's "⋯" menu on the batch page) copies that run's PDF into the new run: the one time a second copy is made. "New Run from the Saved Reply" gives its new run a copy the same way.
- **A run whose estimate fails** keeps its PDF and its page, with **Try Again**: a folder holding only its PDF is a run ("Not Started").
- **Moving a run, a batch or a batch's PDFs to the Trash** takes their PDFs with them, and the confirmation says so.
- **The PDF's name** travels with it: names and Titles are kept by sha256.

**Runs made before this change** find their original as before, by sha256 in uploads/ and samples/. When such a run still reads the very upload a new run starts from (its estimate or "Start Remediation" waiting, its first apply, an older batch's list of PDFs, or a finished run with no other copy), the new run gets a copy instead, and the upload stays listed. Moving a PDF in the upload list to the Trash lists only runs made before this change.

## A single run

1. **New Run** opens a pop-up on the page with one field, **Run Name** (required), and **Get the Estimate** and **Cancel**. There is no OCR language and no review choice: every app run stops for review, and the language is asked only when needed (see [The pop-ups](#the-pop-ups)).
2. **Get the Estimate** queues a free job: intake, the audit and the cost estimate. It asks OpenRouter for prices and the credit (free calls; no content of the PDF is sent). The browser goes to the run's own page at once, which follows each step.
3. **Language of the Scanned Pages:** when pages need OCR, the estimate stops before any OCR and the run page asks their language (see [below](#language-of-the-scanned-pages)). Otherwise this step doesn't appear.
4. **The estimate card** says "Expected Cost: $0.31", then "Max Estimated Cost: $0.67 · Credit: $22.68", and **Start Remediation**, nothing else. Expected Cost is what to read first; it can also read "Not Available Yet" (see [What a run may cost](options.md#what-a-run-may-cost)).
   - A PDF with more than 100 images needs several AI requests (see [Files](files.md)). The second line then gives the whole PDF's maximum, every request together: "Max Estimated Cost: $3.13 for 6 AI requests · Credit: …".
   - After a paid previous attempt, it adds "Counted Toward This PDF's Limit So Far: $0.60".
5. **Start Remediation** is the only button that leads to a paid request. It is shown only when the estimate fits the limits and the credit. Both cost lines are read with the button by a screen reader. See [What "Start Remediation" checks](#what-start-remediation-checks).
6. **Progress:** the run page shows each step and the step running now. The run always stops after the AI request: every run the app starts stops for review (the terminal's `REVIEW=1` stays optional). The page announces "The AI's decisions are ready for your review" and shows **Open the Review Page**.
   - Focus moves to that button only when it is still where the page put it after **Start Remediation**, and no key or click has happened since. Otherwise the page only announces it. This is the one exception to "focus stays where it is" ([Where focus goes](app-run-page.md#where-focus-goes)).
7. **"Finish Review" applies at once.** The review page goes back to the run page, which shows "Applying the reviewed decisions" (or "Waiting to Start" while other runs hold the places), then **Show the Result**. There is no "Apply" button: if the apply can't start or fails, the page says why and offers **Try Again**.

The short name (`runs/<name>/`) comes from the PDF's file name, and is unique per PDF: a folder that already holds runs of another file (another sha256) gets "-2", "-3"…

**Personal information.** The app doesn't yet ask whether a PDF holds personal information. Such a PDF should never be sent to a cloud AI service. Until the app asks, a person decides before starting: a PDF with personal information is never sent to the AI service. That check is its own issue.

### The pop-ups

The New Run pop-up is a native dialog. Focus moves into it, Tab stays inside, a heading names it ("New Run"), and **Cancel** or Esc closes it, changes nothing, and gives focus back to the button that opened it. A refusal is shown inside it, under the name field when it is about the name.

"New Run of This PDF" opens the same pop-up, which says what it does:
- from a batch's PDF: "This makes a separate single run with its own copy of this PDF. The batch and its run are not changed."
- from a run: "This makes a separate run with its own copy of this PDF. The run it comes from is not changed."

While a pop-up is open (New Run, New Batch, a Trash confirmation), the page behind doesn't scroll, and it is where it was when the pop-up closes. The old `/new` and `/new-batch` addresses go to the home page.

### Language of the Scanned Pages

When the language of scanned pages matters for OCR, the run page asks for it (#37), with its suggestion preselected and the evidence in plain words: "Of the 3 scanned pages checked, 2 look like Japanese; 1 has no text to read (a picture or a cover)". The rules are in [Intake](intake.md).

- Japanese kana → Japanese; Korean (Hangul) → Korean; Vietnamese letters → Vietnamese.
- Chinese characters with no kana, or more than one CJK script: nothing is preselected. Japanese and Chinese are never guessed: a person picks Chinese (Traditional), Chinese (Simplified) or Japanese.
- Another script, or text whose script couldn't be told: asked, with English preselected when the text layer is Latin.
- **Not asked:** the Latin script only, or no text to read on the scanned pages (a cover, a picture). The run goes on as before, OCR'd as English.

A Hawaiian, Ilokano or Bikol scan is Latin script, so it is read as English too. Lost ʻokina or kahakō are caught at "OCR Text Approval"; the catalogue language (part 2 of #37) is the later fix.

**Continue** starts the estimate again with that language. English is intake's own default, so the run is exactly what it was before the question existed.

The full intake still checks every page to be OCR'd for Chinese, Japanese or Korean text. When it finds some and the chosen language has no CJK pack, the PDF stops as before, and the same question comes back with that evidence, offering only the CJK languages.

**In a batch,** each waiting PDF has its own row with its list and **Continue**. With two or more waiting, each row also has **Use for All Waiting PDFs**, which gives the language chosen on that row to every PDF still waiting.
- A PDF whose question doesn't offer that language keeps its question, and the page names it. (Intake's CJK stop offers only Chinese, Japanese and Korean.)
- Nothing is preselected for a PDF with Chinese characters alone: the person chose the language.
- The page follows the estimates while you answer. A language chosen but not yet sent stays chosen when the page is drawn again, and the page isn't redrawn while a language list has focus.
- After **Continue**, focus goes to the batch's status heading; no notice repeats it.

### When the credit couldn't be checked

An estimate reads the OpenRouter credit (free: nothing of the PDF is sent). When that read fails, the run or batch page says why, in place of "Start Remediation", and offers **Check Credit Again**:
- the app has no key: whoever looks after the app adds it
- OpenRouter refused the key (HTTP 401 or 403: revoked or replaced): whoever looks after the app checks it
- OpenRouter couldn't be reached: check this computer's connection
- any other answer: try again in a moment

**Check Credit Again** reads the credit now and keeps it for 10 minutes. When it fits, "Start Remediation" comes back. Every check below still applies to it, and the estimate's fingerprint never covers the credit, so nothing else changes.

The advice under a refusal fits its reason: not enough credit says to add credit, a limit says to raise it or use fewer PDFs, and a credit that couldn't be read never says either. The reason stays on the page (it has no ×) while it is why "Start Remediation" is missing.

### What "Start Remediation" checks

At the click, the app checks:
- that the estimate shown is the estimate on disk. A change is refused: "The estimate changed since it was shown. Look at the new estimate."
- that the model and prompt are still the ones the estimate used, and the model is a Claude model. A change is refused: "The estimate is out of date. Get a new estimate."
- the limits and the credit
- that the PDF is still the one estimated (its sha256)

The request is then sent, bound to the estimate shown: it can't spend more than the Max Estimated Cost on the card. Details are in [For developers](#the-spend-gate).

### Try Again, Get a New Estimate, Continue

- **Try Again** is decided from the run folder. When a complete AI reply is saved, the run goes on with it, free. Otherwise the app gets a new estimate first, and a new request needs **Start Remediation** again. A free rerun that would reach a new request stops before it, and the page says to get a new estimate.
- **When a run stopped during its figure requests,** "Try Again" asks for a new estimate first: what it spent is logged and counted toward the PDF's limit.
- **Continue** appears when the estimate found a saved reply: "No AI request is needed".
- **Get a New Estimate** appears only when the estimate is stale: the app restarted before the paid request started. The card is then headed "Waiting for a New Estimate".
- **New Run from the Saved Reply** appears on a finished run that can no longer be reviewed, because the pipeline changed since. It makes a new run of the PDF from its saved reply, free, on today's code, stopping for review. It is refused for a cleared PDF.
- **A run made from the terminal** (an estimate-only folder, for example) is listed and opens, but its page offers no "Start Remediation", Get a New Estimate or Try Again: its settings are not known to the app. It says to start a new run of the PDF from the home page.
- **A PDF in a batch** has no "Start Remediation" of its own: its page points to the batch page, where the batch is sent. Its page is headed "Batch".

## When a run stops

The card says "Stopped:" with the reason in plain words, one sentence on what it means, and **What You Can Do** with the buttons that apply. A closed **Details** is for whoever looks after the app: the step, the exit code, the tool's own error line, the record that holds it, and where the full log is. Tool text and commands appear only there. [Troubleshooting](troubleshooting.md#runs-started-from-the-app) lists every case.

## For developers

### Commands the app runs

- **Get the Estimate:** `ESTIMATE=1 ASK_LANG=1 bash run_api.sh <book> <name> <run name>`: intake, the audit and `decide.py --dry-run`.
- **A batch's estimates:** one per PDF, `ESTIMATE=1 ASK_LANG=1 RUN_DIR=runs/batches/<label>/<name> bash run_api.sh …`, exactly batch_api.sh's own estimate step. Before them, the app writes the list of PDFs `runs/.app/batches/<label>.books.txt` (one `<short name> <absolute path>` per line, the path its own copy; names unique in the batch; a path with "#" or "|" is refused) and the batch's record `runs/.app/batches/<label>.json`.
- **A batch's Start Remediation:** `AUTO=1 REVIEW=1 JOBS=… BATCH_MAX_USD=<total, rounded up> MAX_USD=<largest book's call> MODEL=… bash batch_api.sh <label> <book list>`. Run the Unfinished PDFs Again adds `RETRY=1`.
- **After a batch PDF's apply:** `SUMMARY_ONLY=1 bash batch_api.sh <label>` writes the summary again.
- **Try Again with a saved reply:** no `AUTO`, with `REVIEW=1`.

**Batch OCR languages.** A batch PDF's answer is kept in the batch's record (`langs`) and, when it isn't English, in the batch folder's `ocr_langs.tsv`, which batch_api.sh reads to give that PDF its own `OCR_LANG`. English leaves `OCR_LANG` unset. A partial move to the Trash removes the PDFs from the list file, the record and `ocr_langs.tsv`.

**Language detection.** `intake.py --languages` writes `_intake/languages.json`. It does page triage and intake's own script detection: the text layer's scripts and Tesseract's on up to 5 scanned pages. There is no text-layer test and no OCR, so it takes seconds. The catalogue language (part 2 of #37) is not read.

### The spend gate

`webapp/spend.py` is the one gate every "Start Remediation" goes through, at the click:
- The estimate fingerprint covers the estimate (without the credit), the request, the digest, the model and the prompt.
- `decide.py`'s model and prompt are read from decide.py's source, never by importing it. decide.py checks its dollar caps for Claude models only, so the model must be a Claude model.

The spend job is then `AUTO=1 MAX_USD=<bound> MODEL=<the estimate's model> REVIEW=1 [OCR_LANG] bash run_api.sh …`. Its settings are copied from the estimate's own job, so intake and the audit are reused. It is marked paid, with the fingerprint in its job file.

**How the limits are bound:**
- `MAX_USD` is the largest request's worst case shown, rounded up to the cent from the stored value plus 0.0001, never above the limit. `run_api.sh` passes it to `decide.py --max-usd`. It binds decide.py's estimate, not the bill; the worst case allows the input 25% over its estimate (billed input has run up to 14.4% over it).
- Every PDF also gets `BOOK_MAX_USD`: its whole worst case plus what previous attempts in the same folder spent, bound the same way and never above the $5 limit per PDF.
- A batch binds `BATCH_MAX_USD` to what it has already spent plus the sum of its PDFs, `MAX_USD` to its largest request, and `BOOK_MAX_USD` to its largest PDF.
- Every Spend also passes the real limits for one thing only, the doubled retry of a figure request cut off (`FIGURE_RETRY_MAX_USD`, `FIGURE_RETRY_BOOK_MAX_USD`; see [What a run may cost](options.md#what-a-run-may-cost)). The first send of every request stays bound to the estimate shown.

**The paid-path rule** (`webapp/jobs.py`, where every job is made): `AUTO` appears only in a spend or batch job that is paid and carries the fingerprint. A paid job is never a follow-on (`then`) of another job. A paid job still queued when the app starts becomes "Waiting for a new estimate"; a new estimate or **Dismiss** ends it, so a restart never leaves a run blocked.

**The credit check** (`webapp/credit.py`) reads the same two OpenRouter endpoints decide.py reads, and keeps the result in `runs/.app/credit.json` for 10 minutes. Both cost lines are tied to the Start Remediation button with `aria-describedby`.

### Uploads

The PDF itself is sent, and four checks come first, each required: it is sent as a PDF, by the app's own page (a header only the app's page sets), to the app's own address, and with a stated length within the limit (`upload_max_mb`, 1 GB by default).

- It is written to `uploads/.incoming/<random>.part`, hashed as it arrives, and must start like a PDF (`%PDF-`).
- It gets its final name with a link that fails when the name exists, so it is never replaced. One lock covers the check for the same content and the link.
- Free space is checked first (the size plus 100 MB), and an upload that stalls for 60 s ends.
- A note beside it, `uploads/<name>.json`, keeps the original name, size, sha256, pages, and when it was added.

Moving a PDF into a run's folder is a rename on the same disk. A copy for "New Run of This PDF" is written under a temporary name, checked by sha256, then renamed.

### Failure cards

`webapp/failures.py` holds every "Stopped:" case as a table by step, each matched string checked against the tool that prints it.
