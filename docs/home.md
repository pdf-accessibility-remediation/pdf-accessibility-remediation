---
title: The home page (new runs and batches)
parent: Review and ship
nav_order: 1
---

# The home page: new runs and batches from the browser

The app's home page (`http://127.0.0.1:8760/`) is where library staff start work without a terminal (#45). Pick a PDF, see what the AI request could cost, select "Start Remediation", follow the run, and land on the review page.

It runs the pipeline's own commands (`run_api.sh`, `batch_api.sh`) as jobs, exactly as a person would type them, so the command line keeps working as before. See [The app](app.md) for its settings, jobs and security.

```bash
cd pipeline
python3 app.py              # opens the home page
```

## The home page

The page is titled "PDF Accessibility Remediation". Its sections are cards like the run page's; each card's top border is the accent blue, and the status pills keep their colors. The review page's "seen" cards use the same blue.

- **Runs in Progress:** shown only while a job runs or waits to start. Each has its PDF, its run name, its step or "Waiting to Start", and **Open**, kept current while the page is open. A job that ends is announced; focus never moves by itself.
- **Upload a PDF:** a drop zone to add PDFs, and the list of PDFs added (see [Upload a PDF](#upload-a-pdf)).
- **My Workspace:** your single runs and batches (below).

### My Workspace

A switch between **Single Runs** and **Batches**, a search (by PDF or run name; by batch name), and a filter by status group with each group's count.

- **A single run's row:** its run name, the PDF's name, "Source PDF: <file name>", its status pill, **Pages**, **Date Created**, **Open** and a "⋯" menu.
- **A batch's row:** its name, its status pill with its state in words beside it ("0 of 2 Ready or Shipped"), Pages (the total of its PDFs; "(1 PDF not counted)" when one has no count), Date Created, **Open** and a "⋯" menu.

There is no AI Cost column: a run's cost is in its run page's header, a batch's on the batch page. Rows come 25 at a time (**Show More Runs** / **Show More Batches**). Listing a run never changes it.

The switch, a filter, a search and **Show More** swap the table in place, with no reload and no jump to the top. The address keeps the choice, so refreshing keeps it. Focus stays on the control used, and the new count ("3 batches · In Progress") is announced. Enter in the search box keeps the view shown.

### The "⋯" menus

Beside **Open** (on a PDF, beside **New Run**), a "⋯" button named "More Actions for <name>" opens a menu: **Edit Name** and **Move to Trash** (in red).

It is a menu button. Enter, Space or the arrow keys open it; the arrow keys, Home and End move in it; Esc closes it and puts focus back on "⋯"; Tab or a click outside closes it. Opened with the mouse, no item is highlighted; opened with the keyboard, the first item is.

**Edit Name** turns the row's name into a text box in place (**Save Name** or Enter; **Cancel** or Esc). On a run or a batch it changes the plain name the pages show, never its folder; a batch's PDFs are named by their batch. After a Trash dialog or a name box closes, focus is back on the row's "⋯".

### Status groups

Each row has a pill naming its group in words; color is never the only signal. A batch has its state in small text beside it, a little apart from the pill. A single run has the pill alone, and its exact status is on its run page. Done is Ready or Shipped only, so a Not Ready run never reads as done.

| Pill | Color | A run is in it when |
|---|---|---|
| Not Started | grey | its estimate is ready (or waits for a new one), nothing paid |
| Processing | blue | a job runs or waits to start for it (an apply after "Finish Review" included) |
| In Progress | amber | it waits for its review or its language, stopped for a reviewer or was stopped, was interrupted (going on costs nothing when the reply is saved), Not Ready, Pending Evaluation |
| Done | green | Ready or Shipped only |
| Failed | red | its last job ended with an error |

A batch is Processing while it runs, Failed when its job failed, Done when every PDF is Ready or Shipped, Not Started before "Start Remediation", else In Progress.

**Statuses** use one set of words everywhere:
- Not Ready, Pending Evaluation, Ready, Shipped (each followed by "· N issues noted" when it has them)
- Waiting for Review, Waiting for a Language
- Estimating, Estimate Ready, Running, Waiting to Start
- Stopped: Needs a Person, Failed, Cleared

### PDF names

A PDF is named by its Book Name. That is the name a person gave it, else the PDF's own Title with a conservative cleanup, else the file name without ".pdf", with "_" and "-" read as spaces. The cleanup removes a leading "_tag_" such as "_no template_", and a trailing " copy" or " copy 2"; the Title is used only when it still looks like a title (not empty, not "untitled", not a file or program name).

After an upload, each new PDF comes first in the list, highlighted, with its name in a text box to check or change (**Save Name** or Enter; **Cancel** or Esc keeps it). The message reads "Added "<name>"" or "Added 3 PDFs", and the first box takes focus. **Edit Name** in a row's "⋯" menu opens the same box in place at any time.

Names are the app's own: never written into a run's record.json or review.html, and read each time a page is drawn, so a new name shows everywhere at once. Names are cleaned (no control or direction characters) and escaped.

Under the name, everywhere a PDF is named (the home page, a run page's header, the batch page and its side column), a line reads "Source PDF: <file name>". This is the one file name the pages show: it tells two copies of a PDF apart.

## Moving around the app

**The Home Page button.** Every page the app serves except the home page itself has a **Home Page** button at the top, after "Skip to the content":
- On a single run's page it ends the "Source PDF:" line, as on any page without a PDF list button.
- On the batch page, **Hide the PDF List** / **Show the PDF List (N)** comes first, then **Home Page**.
- On a batch PDF's page, both are on its "Assigned to the batch" line, in that order.
- On the review page and the OCR-only page, it follows the page count in the header line, spaced so it touches nothing else.

"Home Page" and "Show/Hide the PDF List" are the same size wherever they sit together.

**Links look like buttons.** Every link on the app's pages is drawn as a button; the side list's entries, "Batch: <name>" at its top included, are drawn as list rows. A button's only hover feedback is a highlight, never an underline. The keyboard's focus ring stays.

### The run page's header

The header starts at the top of the screen: the PDF's name, "Source PDF: <file name>", then the run's details in plain words on one line where the width allows. They start with the run's name, for example "mm · 321 pages · Run on November 6, 2026, at 9:29 PM · AI Model: Claude Sonnet 5.5 · AI Cost: $0.27 (expected $0.31, max estimated $0.67)". Labels are in Title Case.

The model is named in plain words, never by its id; for a run made from a saved reply, it is the original call's model. The AI Cost reads:
- "AI Cost: none (a saved reply was used)" when no new request was made
- "AI Cost: none (no AI request: a PDF edited by hand)" for a run made from a hand edit and brought back for review (no model is named)
- "AI Cost: not recorded" when the record has no cost
- nothing, before the AI has answered

A PDF in a batch adds "Assigned to the batch "<name>"", with the list's button and **Home Page** after it. "Batch: <name>" in the side list leads to the batch page.

Run Actions meets the header with no gap, and doesn't repeat the cost. Run Actions, "Ready to Ship?" and the Accessibility Evaluation keep their gaps between each other, and start at the side list's edge when it is shown. The review's own sections below them keep their gap from the list. While a job runs, its card has the one spinner, on its status line.

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
   - Focus moves to that button only when it is still where the page put it after **Start Remediation**, and no key or click has happened since. Otherwise the page only announces it. This is the one exception to "focus stays where it is" ([The app](app.md)).
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

## Batches

1. **Select two or more PDFs** on the home page and choose **Create a New Batch**. A pop-up like New Run's opens, with **Batch Name** (required), **Get the Estimates**, **Save Batch for Later** and **Cancel**. A batch holds up to 50 PDFs; more is refused: "A batch can hold up to 50 PDFs. Split them into two batches".
2. **Get the Estimates** moves each PDF into its own folder in the batch, and queues one free estimate per PDF.
3. **Language of the Scanned Pages:** a PDF whose pages need OCR stops with the same question on its own row of the batch page; the other PDFs go on. The batch can start once every one is answered.
4. **The batch page** shows the batch's state, its costs, the PDFs that stopped and need a person (not sent), **Start Remediation**, the total cost, and the batch dashboard (see [The batch page](#the-batch-page)).
5. **Start Remediation** sends the batch. It estimates again (intake and audits reused) and refuses on its own when over the limit.
6. **Every PDF stops for review.** The batch page then says how many wait, and each PDF's page offers **Open the Review Page**, even while the batch still runs. Its "Finish Review" applies that PDF and writes the batch's summary again after.
   - A review finished while the batch still runs shows "Waiting to Start" until the batch's job ends.
   - Until a PDF is applied, its dashboard row shows its status with the result columns (Needs a Person, AI Decisions, Safety, veraPDF) blank, never 0 or OK.
   - A PDF waiting for review is never sent again.
7. **Run the Unfinished PDFs Again** gets new estimates for the PDFs without a result (not those waiting for review). The next "Start Remediation" finishes only those.

### Saving a batch for later

**Save Batch for Later** saves the batch with its name and PDFs, and no estimates. The PDFs move into the batch (and leave the upload list), and it is a Not Started batch in My Workspace.

Its **Open** shows the same pop-up on the home page, with the name editable and each PDF with **Remove from Batch** (back to the upload list). A PDF the batch took as a copy, because an older run still reads the upload, is removed instead, so the list never shows it twice. **Get the Estimates** starts it.

Saving runs nothing, so it never needs text recognition (OCR). A batch with untagged PDFs is saved even where OCRmyPDF or Tesseract is missing, and **Get the Estimates** is where it is refused then; the batch stays saved. Until then, **Move to Trash** sends the batch to the Trash and its PDFs back to the upload list (nothing was run), as the confirmation says.

### The batch page

The state is one of: Waiting for a Language, Estimating, Ready to Start, Running, Waiting for Review, Finished, Stopped.

The costs read:
- "Expected Cost: $4.10 for 14 PDFs"
- "Max Estimated Cost: $8.80 for 14 PDFs (18 AI requests) · Batch Limit: $10.00 · Credit: …"
- "Already Spent in This Batch: $1.20", when something has been spent
- while the estimates come in: "Max Estimated Cost So Far: $0.42 for 1 of 4 PDFs (estimating)". Nothing is shown before the first one: never "$0.00".
- **Total Cost:** "$1.20 so far (expected $4.10, max estimated $8.80)". Every PDF's cost counts, also while it waits for review, and so do PDFs moved to the Trash.

The batch dashboard is drawn in the page: no separate page to open.

**The dashboard's rows** each have **Open** and a "⋯" menu, the same menu button as My Workspace's ("More Actions for <PDF name>"):
- **Edit Name** changes the PDF's display name in place. It is kept by sha256, so it shows on the dashboard, the side list, its run page and any other run of the same file. It is never a file, folder or run name: a batch's PDFs are named by the batch.
- **New Run of This PDF** opens New Run's pop-up.

The "This Batch" panel joins the header, and the side list when it is shown.

### The side list

The side column ("PDFs in This Batch") is on the batch page and on every PDF's page in the batch. It lists each PDF with its display name, "Source PDF:" and its status in words. Its left border shows the PDF's state:

- **grey:** its review isn't opened yet, or it is processing or waiting to start. While processing it also has a small spinning circle at its right edge: a still dot with reduced motion, named "Processing" for a screen reader.
- **blue:** its review is opened, up to Pending Evaluation
- **yellow:** it stopped for a reviewer (its language, for example)
- **green:** Ready or Shipped
- **red:** its last job failed

The current PDF has the darker background and bold text; hovering gives a lighter shade. "Batch: <name>" (the way to the batch page) is styled like the PDFs (no underline, the same hover shade and focus ring), only larger, with "(N PDFs)" smaller under it. Both start where the PDFs' names do, the list starts near the top, and on a wide screen the page's header and panels sit right against the list.

**Hide the PDF List** / **Show the PDF List (N)**, beside **Home Page**, closes and opens it. The choice is remembered in this browser, and the server lays the page out with it, so moving from PDF to PDF doesn't shift the page. The panel also keeps its height until it is drawn, the list keeps its scroll place, and pages cross-fade.

Below 48em (a phone, 320 px included) the list starts closed, in the page's flow, so nothing scrolls sideways. "Skip to the content" skips it.

### Runs at once

- Up to 3 single runs go at once (`max_jobs`).
- A batch's estimates go up to 10 at once (`batch_jobs`), in their own places.
- A batch runs alone, with up to 10 PDFs in progress inside it.

A queued batch starts only when no run is going, and the runs queued after it wait behind it. So jobs still start oldest first, and none waits forever. A waiting job's card says "Waiting to Start: it starts when the batch "Spring backlist" ends", or its place in line.

One accepted exception: the apply that "Review Again" makes runs inside its own review process after "Finish Review", so it can run beside a batch.

### Run and batch names

Staff type a plain name. The folder label, used in paths, commands and the address bar, is made from it:
- letters and digits folded to plain ASCII, other characters as "-"
- at most 64 characters
- the date when nothing is left
- "_2", "_3"… when a folder or job already has it

The plain name is kept only by the app and shown on every page; a run made from the terminal shows its label. The home page's search matches both.

## Move to Trash

**Move to Trash** is in the "⋯" menu of each single run and batch in My Workspace, and of each PDF in the PDF list. It is also on the batch page, for the whole batch or the PDFs ticked in its dashboard (**Move Selected to Trash**). Every move asks first, naming what goes in plain words.

**A run:** its run name and PDF, and "The remediated PDF, its report and its review go with it." A shipped run adds "This run was shipped. Its record of what was shipped and who approved it goes with it."

**A batch, or PDFs in it:** each PDF is named. After a partial move:
- The PDFs are out of the batch's list of PDFs, its record and its OCR languages, so nothing sends them again.
- summary.md, summary.html and the page's dashboard are drawn from the PDFs left.
- **Total Cost:** counts those, and a line follows: "1 PDF moved to the Trash (AI cost $0.45)", so the spend is never hidden. summary.md has the same line.
- Moving every PDF moves the batch.

**An added PDF:** when runs were made from it (by sha256), each is listed under "These runs were made from:" with its date and status, then "These runs keep their remediated PDF, report and downloads." Each run gets a line on what the move changes for it:
- ""Review Again" still works: the run kept its own copy" (its intake made one)
- "…the run uses another copy of the PDF" (its review reads a different file with the same content, e.g. in samples/)
- "…another copy of the PDF is in the app's folders" (found by sha256)
- ""Review Again" will need it back" (a tagged PDF whose review reads this very file: its review record names the original itself)
- ""Review Again" already doesn't work for this run: … Moving this PDF doesn't change that" (its own intake copy is missing, or its record doesn't say which PDF it was made from, so putting the PDF back wouldn't help)
- "Applying its reviewed decisions will need it back" (waiting for its first apply)
- a run before its result gets no line

Those runs stay. A run that needs the PDF says on its page that the original PDF was moved to the Trash, and how to put it back. The samples folder is never offered.

**A move is refused,** and nothing moves, while anything affected is processing, waiting to start or for a new estimate, has a review page open, or sits between "Finish Review" and its apply. A PDF is also refused while any job's command names it.

Where the items go and how to put them back: [The app](app.md#move-to-trash).

## Clearing a shipped PDF

After a PDF has shipped and its record ZIP was downloaded, its run page may offer **Clear This Book's Files** to free space. It is optional, never suggested: see [Accessibility evaluation and release](release.md#clearing-a-shipped-book). It keeps the run's own original PDF (`source/`): a cleared run still holds the full PDF it was made from.

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

### Where the app keeps names and the home list

- Display names of runs and batches: `runs/.app/run-names.json`.
- PDF names: `runs/.app/book-names.json`, by sha256, with each earlier name kept.
- The home list's cache: `runs/.app/home-index.json`, by each run's path and the times its records changed. Only the rows whose records changed are read again.

A finished run's status in the list is worked out from its record and `release/`, without hashing any PDF; the run page does the full check. Names are applied when the list is read, so a rename keeps the cache. The app refreshes the list in the background whenever a job ends and after a move to the Trash, so a click on **Home Page** is served from a ready list.

Before names were applied at read time, a rename threw the whole cache away. On 750 runs and 227 batches, the next home page then took 3.0 s to rebuild, against 0.03 s warm; now it takes 0.05 s after a rename.

The "⋯" menus are menu buttons (`aria-haspopup="menu"`, `aria-expanded`). Buttons keep the keyboard's focus ring with `:focus-visible`. The list's view is kept in the address with `history.replaceState`. The side list's choice is kept in a cookie and local storage, and the page layout is one CSS block in panel.css. Colors come from review/palette.css.

### Failure cards

`webapp/failures.py` holds every "Stopped:" case as a table by step, each matched string checked against the tool that prints it.

### Test mode

For the app's tests only, three keys are accepted only from `--config`, never from a settings file:
- `test_reply_dir`: "Start Remediation" runs `REPLY=<dir>/<short name>.txt INTAKE_REUSE=1` instead of a paid request. A missing reply is refused, never sent instead.
- `test_batch_from`: a batch's "Start Remediation" runs `FROM=<label>`, each PDF's saved reply found under `runs/batches/<label>/<short name>/` or `runs/<short name>/<label>/`.
- `trash_dir`: where **Move to Trash** moves things, instead of `~/.Trash`.

Every page then says "Test: saved replies, no AI request". Estimates still ask OpenRouter for prices and credit (free). A batch in test mode skips batch_api.sh's own estimate step and its cap (FROM= does), so only a real batch shows the cap working.

**Saved replies are found by the PDF's file name, not its content.** The short name comes from the file name's stem (`ilokano.pdf` → `ilokano`), so a test PDF must be added through **Upload a PDF** under its original file name. An upload renamed to `ilokano-2.pdf` would look for `ilokano-2.txt`.

A `--config` may also name its own `runs`, `uploads` and `jobs` folders: every job then writes into that runs folder (the app passes `RUNS_DIR`).
