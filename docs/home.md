---
title: The home page (new runs and batches)
nav_order: 3.55
---

# The home page: new runs and batches from the browser

The app's home page (`http://127.0.0.1:8760/`) is where library staff start work without a terminal (#45, home
interface): pick a PDF, see what the AI call could cost, "Start Remediation", follow the run, and land on the review page. It runs
the pipeline's own commands (`run_api.sh`, `batch_api.sh`) as jobs, exactly as a person would type them, so the command
line keeps working as before. See [The app](app.md) for its settings, jobs and security.

```bash
cd pipeline
python3 app.py              # opens the home page
```

Every page the app serves except the home page itself has a **Home Page** button at the top (after "Skip to the
content"); on the run and batch pages it sits beside **Hide the Book List** / **Show the Book List (N)**, and on the
review page and the OCR-only page it follows the page count in the header line. Every link on the app's pages is drawn as
a button (round 4, P5).

## The home page

Titled "PDF Accessibility Remediation" (round 4, Patrick 2026-11-06). Its sections are cards like the run page's, in
review/palette.css's colors.

- **Runs in Progress:** shown only while a job runs or waits to start: each with its PDF, its run name, its step or
  "Waiting to Start", and **Open**, kept current while the page is open. A job that ends is announced; focus never moves
  by itself.
- **PDFs:** the PDFs added through **Add a PDF**, each with its pages and size, **New Run**, **Edit the Name**, **Move to
  Trash** and a box to select it for a batch. The samples folder is never listed (P3): the app only looks there, by
  sha256 and read only, for the original of a run made from it, so "Review Again" and the first apply of such runs keep
  working.
- **My Workspace:** a switch between **Single Runs** and **Batches**, a search (by PDF or run name; by batch name), and a
  filter by status group with each group's count. A single run's row: its run name, the PDF's name, "Source PDF: <file
  name>", its status, **Date Created**, its AI cost, **Open** and **Move to Trash**. A batch's row: its name, "N of M PDFs
  finished", its status, Date Created, cost, **Open** and **Move to Trash**. 25 rows at a time (**Show More Runs** /
  **Show More Batches**). Listing a run never changes it.

**Status groups** (D6, Patrick 2026-11-06). Each row has a pill naming its group in words (color is never the only
signal), with the exact status in small text beside it, so a Not Ready run never reads as done:

| Pill | Color | A run is in it when |
|---|---|---|
| Not Started | grey | its estimate is ready (or waits for a new one), nothing paid |
| Processing | blue | a job runs or waits to start for it (an apply after "Finish Review" included) |
| In Progress | amber | it waits for its review or its language, stopped for a person or was stopped, was interrupted (going on costs nothing when the reply is saved), Not Ready, Pending Evaluation |
| Done | green | Ready or Shipped only |
| Failed | red | its last job ended with an error |

A batch is Processing while it runs, Failed when its job failed, Done when every PDF is Ready or Shipped, Not Started
before "Start Remediation", else In Progress.

**Book names** (Patrick, 2026-11-06). A book is named by its Book Name: the name a person gave it, else the PDF's own
Title with a conservative cleanup (a leading "_tag_" such as "_no template_", and a trailing " copy" or " copy 2", removed)
when it still looks like a title (not empty, not "untitled", not a file or program name), else the file name without
".pdf", with "_" and "-" read as spaces. After **Add a PDF** the app shows the PDF Name prefilled, to check or change
(**Save Name**);
**Edit the Name** on the home page changes it at any time. The names are the app's own (`runs/.app/book-names.json`, by
sha256, with each earlier name kept): never written into a run's record.json or review.html, and read each time a page is
drawn, so a new name shows everywhere at once. Under it,
everywhere a book is named (the home page, a run page's header, the batch page and its side column), a line reads
"Source PDF: <file name>". This is the one file name the pages show (Patrick, 2026-11-05): it tells two copies of
a book apart. Names are cleaned (no control or direction characters) and escaped.

**Statuses** use one set of words everywhere: Not Ready, Pending Evaluation, Ready, Shipped (each followed by "· N
issues noted" when it has them), Waiting for Review, Waiting for a Language, Estimating, Estimate Ready, Running, Waiting
to Start, Stopped: Needs a Person, Failed, Cleared. A finished run's status is worked out from its record and `release/` without
hashing any PDF (the run page does the full check). The list is cached in `runs/.app/home-index.json`, by each run's path
and the times its records changed.

## Add a PDF

**Add a PDF** copies a PDF from your computer into the uploads folder (`uploads/` at the repository root, git-ignored).
The file you choose is only read by your browser; the app never sees its path.

- The PDF itself is sent, and four checks come first, each required: it is sent as a PDF, by the app's own page (a
  header only the app's page sets), to the app's own address, with a stated length within the limit
  (`upload_max_mb`, 1 GB by default).
- It is written to `uploads/.incoming/<random>.part`, hashed as it arrives, and must start like a PDF (`%PDF-`).
- **Never replaced:** it gets its final name with a link that fails when the name exists, so a second book of the same
  name becomes `name-2.pdf`. One lock covers the check for the same content and the link.
- **The same content already listed** (an added PDF, by sha256) is refused, naming where it is.
- Free space is checked first (the size plus 100 MB), and an upload that stalls for 60 s ends.
- A note beside it, `uploads/<name>.json`, keeps the original name, size, sha256, pages and when it was added.
- A PDF locked with a password is listed as locked, with no **New Run**.

## A single run

1. **New Run** opens a short form with one field: **Run Name** (required, in your own words). There is no OCR language
   and no review choice on it (round 4: every app run stops for review, and the language is asked only when needed).
2. **Get the Estimate** queues a free job, `ESTIMATE=1 ASK_LANG=1 bash run_api.sh <book> <name> <run name>`: intake, the
   audit and `decide.py --dry-run`. It asks OpenRouter for prices and the credit (free calls; no book content is sent).
   The browser goes to the run's own page at once, which follows each step.
3. **Language of the Scanned Pages** (D4, part 1 of #37, intake: suggest the OCR language). When pages need OCR, the
   estimate stops before any OCR and the run page asks their language (see below). Otherwise this step doesn't appear.
4. **The estimate card** says "Worst-case estimate $0.54 · Limit $2.00 per AI call · Credit $22.68" and **Start
   Remediation**, nothing else (no "Get a New Estimate", no job lines). When #65 (dollar-only cost limits) adds an
   expected cost, the line starts "About $0.25 (usually $0.18–$0.36) ·".
5. **Start Remediation** is the only button that leads to a paid call, shown only when the estimate fits the limits and the credit.
   The worst-case line is read with the button by a screen reader (`aria-describedby`). The next section says what it
   checks.
6. **Progress:** the run page shows each step and the step running now. The run always stops after the AI call (D2:
   every run the app starts stops for review; the terminal's `REVIEW=1` stays optional). The page announces "The AI's
   decisions are ready for your review" and shows **Open the Review Page**. Focus moves to that button only when it is
   still where the page put it after **Start Remediation** and no key or click has happened since; otherwise the page only
   announces it (the one exception to "focus stays where it is", [The app](app.md)).
7. **"Finish Review" applies at once** (D3). The review page goes back to the run page, which shows "Applying the
   reviewed decisions" (or "Waiting to Start" while other runs hold the places), then **Show the Result**. There is no
   "Apply" button: if the apply can't start or fails, the page says why and offers **Try Again**.

### Language of the Scanned Pages

`intake.py --languages` (page triage and intake's own script detection: the text layer's scripts and Tesseract's on up
to 5 scanned pages; no text-layer test, no OCR, seconds) writes `_intake/languages.json`. The question is asked only when
the language matters (Patrick, 2026-11-07; the rules are in [Intake](intake.md)), with its suggestion preselected and the
evidence in plain words ("Of the 3 scanned pages checked, 2 look like Japanese; 1 has no text to read (a picture or a
cover)"):

- Japanese kana → Japanese; Korean (Hangul) → Korean; Vietnamese letters → Vietnamese.
- Chinese characters with no kana, or more than one CJK script: nothing is preselected. Japanese and Chinese are never
  guessed: a person picks Chinese (Traditional), Chinese (Simplified) or Japanese.
- Another script, or text whose script couldn't be told: asked, with English preselected when the text layer is Latin.
- **Not asked:** the Latin script only, or no text to read on the scanned pages (a cover, a picture). The run goes on as
  before, OCR'd as English. A Hawaiian, Ilokano or Bikol scan is Latin script, so it is read as English too; lost ʻokina
  or kahakō are caught at "OCR Text Approval", and the catalogue language (part 2 of #37) is the later fix.

**Continue** starts the estimate again with that language. English leaves `OCR_LANG` unset (English is intake's own
default), so the run is exactly what it was before the question existed. The full intake still checks every page to be
OCR'd for Chinese, Japanese or Korean text: when it finds some and the chosen language has no CJK pack, the PDF stops as
before, and the same question comes back with that evidence, offering only the CJK languages. The catalogue language
(part 2 of #37) is not read.

The short name (`runs/<name>/`) comes from the book's file name and is unique per book: a folder that already holds runs
of another file (another sha256) gets "-2", "-3"…

**Personal information.** The app doesn't yet ask whether a book holds personal information (sponsor checklist 1.1).
Until it does, a person decides before starting: a book with personal information is never sent to the AI service. That
check is its own issue and branch.

### What "Start Remediation" checks

`webapp/spend.py` is the one gate every "Start Remediation" goes through, at the click:

- that the estimate shown is the estimate on disk: a fingerprint over the estimate (without the credit), the request, the
  digest, the model and the prompt. A change is refused: "The estimate changed since it was shown. Look at the new
  estimate.";
- that `decide.py`'s model and prompt are still the ones the estimate used, and the model is a Claude model (decide.py
  checks its dollar caps for Claude models only). They are read from decide.py's source, never by importing it. A change
  is refused: "The estimate is out of date. Get a new estimate.";
- the limits and the credit;
- that the book's file is still the one estimated (its sha256).

The spend job is then `AUTO=1 MAX_USD=<bound> MODEL=<the estimate's model> REVIEW=1 [OCR_LANG] bash run_api.sh …`, with
the settings copied from the estimate's own job (so intake and the audit are reused), marked paid, with the fingerprint
in its job file. `MAX_USD` is the largest request's worst case shown, rounded up to the cent from the stored
value plus 0.0001, never above the limit (`run_api.sh` passes it to `decide.py --max-usd`). It binds decide.py's
estimate, not the bill: billed input has run up to 14% over the estimate until #63 (alt text past 100 images) adds its
margin. For a run.json in the shape #63 (alt text past 100 images) writes, `BOOK_MAX_USD` is bound the same way.

**The paid-path rule** (webapp/jobs.py, where every job is made): `AUTO` appears only in a spend or batch job that is
paid and carries the fingerprint. A paid job is never a follow-on (`then`) of another job. A paid job still
queued when the app starts becomes "Waiting for a new estimate"; a new estimate or **Dismiss** ends it, so a restart never leaves
a run blocked.

### Try Again, Get a New Estimate, Continue

- **Try Again** is decided from the run folder: when a complete AI reply is saved, the run goes on with it, free (no
  `AUTO`, with `REVIEW=1`); otherwise the app gets a new estimate first, and a new call needs **Start Remediation** again. A free rerun that would
  reach a new call stops before it (the page then says to get a new estimate).
- **Continue** appears when the estimate found a saved reply: "No AI call is needed".
- **A run made from the terminal** (an estimate-only folder, for example) is listed and opens, but its page offers no
  "Start Remediation", Get a New Estimate or Try Again: its settings are not known to the app. It says to start a new run of the book
  from the home page.
- **A PDF in a batch** has no "Start Remediation" of its own: its page points to the batch page, where the batch is sent.
- **Get a New Estimate** appears only when the estimate is stale: the app restarted before the paid call started. The card
  is then headed "Waiting for a New Estimate" (07 L2).
- **New Run from the Saved Reply** appears on a finished run that can no longer be reviewed (the pipeline changed since):
  a new run of the book from its saved reply, free, on today's code, stopping for review. It is refused for a cleared
  book.

## When a run stops

The card says "Stopped:" with the reason in plain words, one sentence on what it means, **What You Can Do** with the
buttons that apply, and a closed **Details** for whoever looks after the app: the step, the exit code, the tool's own
error line, the record that holds it and where the full log is. Tool text and commands appear only there.
`webapp/failures.py` holds every case as a table by step, each matched string checked against the tool that prints it
([Troubleshooting](troubleshooting.md#runs-started-from-the-app) lists them).

## Batches

1. Select two or more PDFs on the home page and **New Batch with the Selected PDFs**.
2. The form: **Batch Name** (required, in your own words). A batch holds up to 50 PDFs (`max_books_per_batch`): more is
   refused, "A batch can hold up to 50 PDFs. Split them into two batches".
3. **Get the Estimates** writes the book list `runs/.app/batches/<label>.books.txt` (one `<short name> <absolute path>`
   per line; names unique in the batch; a path with "#" or "|" is refused) and the batch's record
   `runs/.app/batches/<label>.json`, then queues one free estimate per PDF: `ESTIMATE=1 ASK_LANG=1
   RUN_DIR=runs/batches/<label>/<name> bash run_api.sh …`, exactly batch_api.sh's own estimate step.
4. **Language of the Scanned Pages:** a PDF whose pages need OCR stops with the same question on its own row of the batch
   page; the other PDFs go on. Its answer is kept in the batch's record (`langs`) and, when it isn't English, in the
   batch folder's `ocr_langs.tsv`, which batch_api.sh reads to give that PDF its own `OCR_LANG`. The batch can start once
   every one is answered.
5. **The batch page** (`/batch/<label>/`): the state (Waiting for a Language, Estimating, Ready to Start, Running,
   Waiting for Review, Finished, Stopped), the worst case for the PDFs to send, the batch limit and the credit, the PDFs
   that stopped and need a person (not sent), **Start Remediation**, **Total Cost:**, and the batch dashboard drawn in
   the page (report_html's own rows: no separate page to open).
6. **Start Remediation** runs `AUTO=1 REVIEW=1 JOBS=… BATCH_MAX_USD=<total, rounded up> MAX_USD=<largest book's call>
   MODEL=… bash batch_api.sh <label> <book list>`. batch_api.sh estimates again (intake and audits reused) and refuses on
   its own when over.
7. **Every PDF stops for review** (D2): the batch page then says how many wait, and each PDF's page offers **Open the
   Review Page**, even while the batch still runs. Its "Finish Review" applies that PDF (D3) and writes the batch's summary again after
   (`SUMMARY_ONLY=1 bash batch_api.sh <label>`). A review finished while the batch still runs shows "Waiting to Start"
   until the batch's job ends. Until a PDF is applied, its dashboard row shows its status with the result columns
   (Needs a Person, AI Decisions, Safety, veraPDF) blank, never 0 or OK. A PDF waiting for review is never sent again.
8. **Run the Unfinished PDFs Again** gets new estimates for the PDFs without a result (not those waiting for review);
   the next "Start Remediation" adds `RETRY=1`.

**Runs at once** (D1, Patrick 2026-11-06). Up to `max_jobs` (3) single runs go at once; a batch runs alone, with up to
`batch_jobs` PDFs (10) in progress inside it. A queued batch starts only when no run is going, and the runs queued after it
wait behind it, so jobs still start oldest first and none waits forever. A waiting job's card says "Waiting to Start: it
starts when the batch "Spring backlist" ends", or its place in line. One accepted exception: the apply that "Review
Again" makes runs inside its own review process after "Finish Review", so it can run beside a batch.

**Run and batch names.** Staff type a plain name. The folder label (used in paths, commands and the address bar) is
derived from it: letters and digits folded to plain ASCII, other characters as "-", at most 64, the date when nothing is
left, and "_2", "_3"… when a folder or job already has it. The plain name is kept only by the app
(`runs/.app/run-names.json`) and shown on every page; a run made from the terminal shows its label. The home page's search
matches both.

**The side column** ("PDFs in This Batch") is on the batch page and on every PDF's page in the batch: each PDF with its
display name, "Source PDF:" and its status in words. Its left border shows its state (P15): grey while its review isn't
opened yet, or while it is processing or waiting to start (then also a small spinning circle at its right edge, a still dot
with reduced motion, named "Processing" for a screen reader); blue once its review is opened, up to Pending Evaluation;
yellow when it stopped for a person (its language, for example); green when Ready or Shipped; red when its last job
failed. The current PDF has the darker background and bold text; hovering gives a lighter shade. **Hide the Book List** /
**Show the Book List (N)**, beside **Home Page**, closes and opens it; the choice is remembered in this browser (a cookie
and local storage), and the server lays the page out with it, so moving from PDF to PDF doesn't shift the page (D7: the
panel also keeps its height until it is drawn, the list keeps its scroll place, and pages cross-fade). Below 48em (a
phone, 320 px included) it starts closed, in the page's flow, so nothing scrolls sideways. "Skip to the content" skips it.

## Move to Trash

**Move to Trash** (D8, Patrick 2026-11-06) is on each single run and batch in My Workspace, on each PDF in the PDF list,
and on the batch page (the whole batch, or the PDFs ticked in its dashboard: **Move Selected to Trash**). Every move asks
first, naming what goes in plain words:

- **A run:** its run name and PDF, and "The remediated PDF, its report and its review go with it." A shipped run adds
  "This run was shipped. Its record of what was shipped and who approved it goes with it."
- **A batch, or PDFs in it:** each PDF named. After a partial move the PDFs are out of the batch's book list, its record
  and `ocr_langs.tsv` (so nothing sends them again), and summary.md, summary.html and the page's dashboard are drawn from
  the PDFs left. **Total Cost:** counts those, and a line follows: "1 PDF moved to the Trash (AI cost $0.45)", so the
  spend is never hidden (summary.md has the same line, from the batch folder's `trashed.json`). summary.md and
  summary.html are written again by a job of their own; when a job of the batch was queued during the move, that job is
  skipped and the files wait for the batch's next run, apply or move (the batch page is drawn live either way). Moving
  every PDF moves the batch.
- **An added PDF:** when runs were made from it (by sha256), each is listed with its date and status, "These runs keep
  their remediated PDF, report and downloads", and, per run, what the move changes (Patrick, 2026-11-07): ""Review
  Again" still works: the run kept its own copy" (its intake made one), "…the run uses another copy of the PDF" (its
  review reads a different file with the same content, e.g. in samples/) or "…another copy of the PDF is in the app's
  folders" (found by sha256); ""Review Again" will need it back" (a tagged PDF whose review reads this very file: its
  review record names the original itself, review 12 M2); ""Review Again" already doesn't work for this run: …
  Moving this PDF doesn't change that" (its own intake copy is missing, or its record doesn't say which PDF it was made
  from: putting the PDF back wouldn't help, review 12 N2); "Applying its reviewed
  decisions will need it back" (waiting for its first apply); "Going on with this run will need it back" (before its
  result). Those runs stay; a run that needs it says on its page that the original PDF was moved to the Trash and how to
  put it back. The samples folder is never offered.

A move is refused, and nothing moves, while anything affected is processing, waiting to start or for a new estimate, has
a review page open, or sits between "Finish Review" and its apply; a PDF also while any job's command names it. Where the
items go and how to put them back: [The app](app.md#move-to-trash).

## Test mode

For the app's tests only, three keys accepted only from `--config` (never from a settings file): `test_reply_dir`
("Start Remediation" runs `REPLY=<dir>/<short name>.txt INTAKE_REUSE=1` instead of a paid call; a missing reply is refused,
never sent instead), `test_batch_from` (a batch's "Start Remediation" runs `FROM=<label>`, each PDF's saved reply found
under `runs/batches/<label>/<short name>/` or `runs/<short name>/<label>/`) and `trash_dir` (where **Move to Trash**
moves things instead of `~/.Trash`). Every page then says "Test: saved replies, no AI call". Estimates still ask
OpenRouter for prices and credit (free). A batch in test mode skips batch_api.sh's own estimate step and its cap (FROM=
does), so only a real batch shows the cap working.

**Saved replies are found by the PDF's file name, not its content.** The short name comes from the file name's stem
(`ilokano.pdf` → `ilokano`), so a test PDF must be added through **Add a PDF** under its original file name (an upload
renamed to `ilokano-2.pdf` would look for `ilokano-2.txt`). A `--config` may also name its own `runs`, `uploads` and
`jobs` folders: every job then writes into that runs folder (the app passes `RUNS_DIR`).

## Clearing a shipped book

After a book has shipped and its record ZIP was downloaded, its run page may offer **Clear This Book's Files** to free
space. It is optional, never suggested: see [Accessibility evaluation and release](release.md#clearing-a-shipped-book).
