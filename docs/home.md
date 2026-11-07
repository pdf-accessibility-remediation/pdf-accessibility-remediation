---
title: The home page (new runs and batches)
nav_order: 3.55
---

# The home page: new runs and batches from the browser

The app's home page (`http://127.0.0.1:8760/`) is where library staff start work without a terminal (#45, home
interface): pick a book, see what the AI call could cost, "Start Remediation", follow the run, and land on the review page. It runs
the pipeline's own commands (`run_api.sh`, `batch_api.sh`) as jobs, exactly as a person would type them, so the command
line keeps working as before. See [The app](app.md) for its settings, jobs and security.

```bash
cd pipeline
python3 app.py              # opens the home page
```

Every page the app serves has **Home** at the top (after "Skip to the content"); the review page and the OCR-only
page have **Home** beside **Back to the Run Page**.

## The home page

- **Runs in Progress:** each job queued or running, with its book and step, kept current while the page is open. A job
  that ends is announced; focus never moves by itself.
- **Books:** the books in the samples folder ("Sample Books") and the ones added here ("Added Books"), each with its
  pages and size, a **New Run** link and a box to select it for a batch.
- **Earlier Runs:** every run under `runs/` (single runs and the books of batches), newest first, 25 at a time
  (**Show More Runs**), with a search by book or run name. Each row: the book, the Run Name, the status, the date, the AI
  cost and **Open**. Listing a run never changes it.
- **Batches:** every batch, newest first, with its books, state, date and cost, and **Open**.

**Book names** (Patrick, 2026-11-06). A book is named by its Book Name: the name a person gave it, else the PDF's own
Title with a conservative cleanup (a leading "_tag_" such as "_no template_", and a trailing " copy" or " copy 2", removed)
when it still looks like a title (not empty, not "untitled", not a file or program name), else the file name without
".pdf", with "_" and "-" read as spaces. After **Add a Book** the app shows the Book Name prefilled, to check or change;
**Edit the Name** on the home page changes it at any time. The names are the app's own (`runs/.app/book-names.json`, by
sha256, with each earlier name kept): never written into a run's record.json or review.html, and read each time a page is
drawn, so a new name shows everywhere at once. Under it,
everywhere a book is named (the home page, a run page's header, the batch page and its side column), a line reads
"Source PDF Filename: <file name>". This is the one file name the pages show (Patrick, 2026-11-05): it tells two copies of
a book apart. Names are cleaned (no control or direction characters) and escaped.

**Statuses** use one set of words everywhere: Not Ready, Pending Evaluation, Ready, Shipped (each followed by "· N
issues noted" when it has them), Waiting for Review, Estimating, Estimate Ready, Running, Waiting to Start,
Stopped: Needs a Person, Failed, Cleared. A finished run's status is worked out from its record and `release/` without
hashing any PDF (the run page does the full check). The list is cached in `runs/.app/home-index.json`, by each run's path
and the times its records changed.

## Add a Book

**Add a Book** copies a PDF from your computer into the uploads folder (`uploads/` at the repository root, git-ignored).
The file you choose is only read by your browser; the app never sees its path.

- The PDF itself is sent, and four checks come first, each required: it is sent as a PDF, by the app's own page (a
  header only the app's page sets), to the app's own address, with a stated length within the limit
  (`upload_max_mb`, 1 GB by default).
- It is written to `uploads/.incoming/<random>.part`, hashed as it arrives, and must start like a PDF (`%PDF-`).
- **Never replaced:** it gets its final name with a link that fails when the name exists, so a second book of the same
  name becomes `name-2.pdf`. One lock covers the check for the same content and the link.
- **The same content already listed** (a sample or an added book, by sha256) is refused, naming where it is.
- Free space is checked first (the size plus 100 MB), and an upload that stalls for 60 s ends.
- A note beside it, `uploads/<name>.json`, keeps the original name, size, sha256, pages and when it was added.
- A PDF locked with a password is listed as locked, with no **New Run**.

## A single run

1. **New Run** opens a short form: **Run Name** (optional, in your own words; without one the run is named by its date),
   **OCR Language** (English by default, chosen by name; used only
   for pages that need OCR; never guessed) and **Review First** (on by default).
2. **Get the Estimate** queues a free job, `ESTIMATE=1 OCR_LANG=… bash run_api.sh <book> <name> <run name>`: intake, the
   audit and `decide.py --dry-run`. It asks OpenRouter for prices and the credit (free calls; no book content is sent).
   The browser goes to the run's own page at once, which follows each step.
3. **The estimate card** says "Worst-case estimate $0.54 · Limit $2.00 per AI call · Credit $22.68" and what would be
   sent: "Sent to the AI (Claude, through OpenRouter): the book's structure and much of its text, 37 figure images, and 4
   images of hard-to-read scanned words." When #65 (dollar-only cost limits) adds an expected cost, the line starts
   "About $0.25 (usually $0.18–$0.36) ·".
4. **Start Remediation** is the only button that leads to a paid call, shown only when the estimate fits the limits and the credit.
   The worst-case line is read with the button by a screen reader (`aria-describedby`). The next section says what it
   checks.
5. **Progress:** the run page shows each step and the step running now. With **Review First**, the run stops after the AI
   call; the page announces "The AI's decisions are ready for your review" and shows **Open the Review Page**. Focus
   moves to that button only when it is still where the page put it after **Start Remediation** and no key or click has happened
   since; otherwise the page only announces it (the one exception to "focus stays where it is", [The app](app.md)).
   Without **Review First** the run goes on to its result and the page offers **Show the Result**.

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

The spend job is then `AUTO=1 MAX_USD=<bound> MODEL=<the estimate's model> [REVIEW=1] [OCR_LANG] bash run_api.sh …`, with
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
  `AUTO`); otherwise the app gets a new estimate first, and a new call needs **Start Remediation** again. A free rerun that would
  reach a new call stops before it (the page then says to get a new estimate).
- **Continue** appears when the estimate found a saved reply: "No AI call is needed".
- **A run made from the terminal** (an estimate-only folder, for example) is listed and opens, but its page offers no
  "Start Remediation", Get a New Estimate or Try Again: its settings are not known to the app. It says to start a new run of the book
  from the home page.
- **A book in a batch** has no "Start Remediation" of its own: its page points to the batch page, where the batch is sent.
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

1. Select two or more books on the home page and **New Batch with the Selected Books**.
2. The form: **Batch Name** (optional, in your own words) and **OCR Language** for every book. A batch holds up to 50
   books (`max_books_per_batch`): more is refused, "A batch can hold up to 50 books. Split them into two batches". Books
   in a batch are applied without a review first; each book's page offers **Review Again** afterwards.
3. **Get the Estimates** writes the book list `runs/.app/batches/<label>.books.txt` (one `<short name> <absolute path>`
   per line; names unique in the batch; a path with "#" or "|" is refused) and the batch's record
   `runs/.app/batches/<label>.json`, then queues one free estimate per book: `ESTIMATE=1 RUN_DIR=runs/batches/<label>/<name>
   bash run_api.sh …`, exactly batch_api.sh's own estimate step.
4. **The batch page** (`/batch/<label>/`): the state (Estimating, Ready to Start, Running, Finished, Stopped), the worst
   case for the books to send, the batch limit and the credit, the books that stopped and need a person (not sent), and
   **Start Remediation**.
5. **Start Remediation** runs `AUTO=1 JOBS=… BATCH_MAX_USD=<total, rounded up> MAX_USD=<largest book's call> MODEL=… bash batch_api.sh
   <label> <book list>`. batch_api.sh estimates again (intake and audits reused) and refuses on its own when over. While
   it runs, the page shows the money spent so far; when it ends, **Open the Batch Dashboard** (summary.html).
6. **Run the Unfinished Books Again** gets new estimates for the books without a result; the next "Start Remediation" adds `RETRY=1`.

**One run at a time** (Patrick, 2026-11-06). The app runs one thing at a time: a single run or a whole batch (`max_jobs`
1). Inside a batch, up to `batch_jobs` books (10) are in progress at once, the next starting as each finishes. "New Run"
and "New Batch" still accept a request while something runs: the new job waits, and its card says "Waiting: it starts when
the batch "Spring backlist" ends" (or the run's name). A batch and its books never run jobs at the same time.

**Run and batch names.** Staff type a plain name. The folder label (used in paths, commands and the address bar) is
derived from it: letters and digits folded to plain ASCII, other characters as "-", at most 64, the date when nothing is
left, and "_2", "_3"… when a folder or job already has it. The plain name is kept only by the app
(`runs/.app/run-names.json`) and shown on every page; a run made from the terminal shows its label. The home page's search
matches both.

**The side column** ("Books in This Batch") is on the batch page and on every book's page in the batch: each book with
its display name, its file name and its status in words, the current one marked. **Hide the Book List** / **Show the Book
List** closes and opens it (remembered in this browser). Below 48em (a phone, 320 px included) it starts closed under its
button, in the page's flow, so nothing scrolls sideways. "Skip to the content" skips it.

## Test mode

For the app's tests only, two keys accepted only from `--config` (never from a settings file): `test_reply_dir` ("Start Remediation"
runs `REPLY=<dir>/<short name>.txt INTAKE_REUSE=1` instead of a paid call; a missing reply is refused, never sent instead)
and `test_batch_from` (a batch's "Start Remediation" runs `FROM=<label>`). Every page then says "Test: saved replies, no AI call".
Estimates still ask OpenRouter for prices and credit (free). A batch in test mode skips batch_api.sh's own estimate step
and its cap (FROM= does), so only a real batch shows the cap working.

## Clearing a shipped book

After a book has shipped and its record ZIP was downloaded, its run page may offer **Clear This Book's Files** to free
space. It is optional, never suggested: see [Accessibility evaluation and release](release.md#clearing-a-shipped-book).
