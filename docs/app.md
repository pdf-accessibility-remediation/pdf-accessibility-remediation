---
title: The app (browser)
nav_order: 3.6
---

# The pipeline in the browser

`app.py` is a small local web app. It shows a run's dashboard (`review.html`) with buttons that review it again, start over, go back to an earlier session's choices, and apply a finished session. Each button runs the same command a person would type (`review_workorder.py … --reopen`, `--apply`, `--pin`), so the command line keeps working exactly as before and both give the same result. The app adds no pipeline logic: the one exception is the Accessibility Evaluation page ([Accessibility evaluation and release](release.md)), whose forms are recorded directly in the app's process through `review/manual.py`, the same code as `manual_checks.py` (only pipeline steps run as jobs). The home page (`/`), where runs and batches are started, is described in [The home page](home.md).

```bash
cd pipeline
python3 app.py ../runs/teika/rv1            # opens that run's page at http://127.0.0.1:8760/run/teika/rv1/
```

After this one start command the terminal can be left alone. Everything the pages show is read from disk (the run folders, their `reviews/`, and `runs/.app/`), so stopping and restarting the app loses nothing.

## Setup

The app needs what the pipeline needs ([Setup](setup.md)). At start it checks each item and prints it as ready or missing, with the command that fixes it. The run page shows a **Setup** warning only when a tool is missing (nothing when every tool is ready).

- **Required** (the app does not start without them): the Python libraries, veraPDF (its version line, for example `veraPDF 1.30.3`) and Java.
- **Untagged books only** (a warning): OCRmyPDF, Tesseract and its language packs.
- **The API key is not checked at start.** It must be in a `.env` file (setup step 3), not only exported in the shell: the app gives its children a clean environment (below) and drops an exported `OPENROUTER_API_KEY`. The app never reads `.env`; `decide.py` reads it itself.

## Settings

One place, read in this order (later wins):

1. `pipeline/webapp/settings.json`: committed, neutral defaults.
2. `pipeline/webapp/settings.local.json`: this machine's own values. It is git-ignored; create it by hand.
3. `--config FILE`: a file of your own, for example for tests. It may not be either of the two files above.
4. An exported `VERAPDF` (the launcher's path), which wins over every file.

| Key | Default | What it sets |
|---|---|---|
| `host` | `127.0.0.1` | Where the app listens. Only `127.0.0.1` is accepted: the app has no logins, so it is not reachable from other computers. |
| `port` | `8760` | The app's port. The review pages use 8765–8784, as from the terminal. |
| `runs`, `samples`, `uploads` | `../runs`, `../samples`, `../uploads` | The folders, relative to `pipeline/` (or absolute). `uploads` holds the PDFs added with "Upload a PDF" and not used yet ([The home page](home.md#upload-a-pdf)): a run started from the app moves its PDF into its own `source/` folder (R17); `samples` is never listed, only searched by sha256 for the original of a run made before that. Every job writes into `runs` (the app passes it as `RUNS_DIR`). |
| `jobs` | `../runs/.app` | The job files, their logs, and the app's own small files (below). |
| `max_jobs` | `3` | How many single runs go at once (open review pages do not count until they apply). A batch runs alone: it starts when no run is going, and nothing else starts while it runs. |
| `batch_jobs` | `10` | How many PDFs of a batch are in progress at once, the next starting as each finishes (batch_api.sh's `JOBS`); also how many batch estimates go at once (R12). Subject to change once the hardware limits are measured. |
| `max_books_per_batch` | `50` | The most books "New Batch" accepts. A setting whoever looks after the app can change; batch_api.sh in a terminal has no cap. |
| `upload_max_mb` | `1024` | The largest PDF "Upload a PDF" accepts, in MB. |
| `limits` | `{"per_call_usd": 2, "per_book_usd": 5, "per_batch_usd": 10}` | Dollars: what the estimates are compared with, and the most a "Start Remediation" may bind (`MAX_USD`, `BOOK_MAX_USD`, `BATCH_MAX_USD`). The batch limit is $10 (R13, Patrick's test 2026-11-07; `lib/costs.py`'s default for the terminal stays $40); a page to change the limits is a later issue. The pipeline's own caps stay as they are. |
| `tools.VERAPDF` | empty | The veraPDF launcher. Empty: `verapdf` on the PATH. |
| `tools.path_prepend` | `[]` | Folders put first on the PATH the app's commands get, for example Java's. |

**Java that is not on PATH.** Put its `bin` folder in `path_prepend` in `settings.local.json`. For example, with Homebrew's openjdk@21 and veraPDF installed in your home folder:

```json
{
 "tools": {"VERAPDF": "~/verapdf/verapdf", "path_prepend": ["/opt/homebrew/opt/openjdk@21/bin"]}
}
```

On Linux or WSL, Java is usually on PATH already. If it is not, use the folder `which java` would show (for example `/usr/lib/jvm/java-17-openjdk-amd64/bin`).

**veraPDF is never off in the app.** `VERAPDF=off` is refused from any source: a settings file, `--config`, or the shell. The start check passes only with a veraPDF version line; the command line's `VERAPDF=off` (which `vera.py --check` accepts) does not count. The app's own tests do not weaken this: they unset `VERAPDF` and give, through `--config`, a small script that answers `--version` as veraPDF does. No setting skips the check.

`test_reply_dir` and `test_batch_from` are for the app's tests ([The home page](home.md#test-mode)). They are accepted only from `--config`, never from a settings file; `test_reply_dir` is relative to `pipeline/`, as the folders are.

**What the app's commands get.** Each command starts from a clean environment:
- **Kept from the shell that started the app:** `PATH`, `HOME`, `LANG`, `LC_*`, `TMPDIR`, `USER`, `LOGNAME`, `SHELL`.
- **Put first on PATH:** the venv's `bin/` and `path_prepend`.
- **Added:** `VERAPDF` from the settings, and the variables the job itself sets, from a fixed list: `REVIEW`, `AUTO`, `ESTIMATE`, `OCR_LANG`, `RUN_DIR`, `INTAKE_REUSE`, `REPLY`, `MAX_USD`, `INTAKE`, `OUT`, `JOBS`, `BATCH_MAX_USD`, `BOOK_MAX_USD`, `RETRY`, `MODEL` (only a Claude model, the one the estimate used) and `FROM` (test mode only). Never `FORCE_OCR`.
- **Dropped:** everything else, for example `MODEL`, `REPLY`, `FROM`, `KEEP`, `RUNS_DIR`, `OCR_LANG`, `MAX_TOKENS` or an API key exported in the shell. So no setting meant for one terminal run changes an app job.
- The job file records the whole environment each command was given.

## The run page

`http://127.0.0.1:8760/run/<run>/` is the run's `review.html` with a **Run Actions** panel at the top. The panel is added when the app serves the page; the file on disk is not changed. Opened as a file, `review.html` is the same report as before (since 2026-10-29 without the terminal command; it is below and in [Reviewing the work order](review-step.md)).

**Capitalization**, on the panel, the review page and `review.html` (not `review.md`): headings, card titles, fold toggles, table column headers and buttons are in Title Case ("Review of the AI's Decisions", "Current Result: Session 5", **Previous Jobs**). Articles, conjunctions and short prepositions (a, an, the, and, or, of, to, in, on, for, by, from, with) stay lowercase unless first or last. Words in parentheses are left as written, so a qualifier stays lowercase ("Pages (optional)", "veraPDF (WCAG rules)") and a session there is named "Session N" ("Review Again (from Session 4)"). Messages, explanations, status lines and list items are in sentence case.

The panel shows:
- **The current result:** "Current Result: Session N". "Ready to ship?" is not repeated in the panel: the report's own card, right below, says it.
- **The buttons:**

  | Button | Runs (from `pipeline/`) |
  |---|---|
  | **Review Again** (from the latest finished session; **Continue Review** when a session is open) | `review_workorder.py <run> --reopen` |
  | **Start Over from the AI's Decisions** | `… --reopen --from ai` |
  | **Review Again from Session N** (in **Session History**) | `… --reopen --from N` |
  | **Apply Session N** (only while the newest session is finished and not applied) | `… --apply` |

  - **Starting over or going back with a session open** asks first. The dialog names the open session and says its choices stay in Session History. OK adds `--discard-open`: the open session is marked abandoned, never deleted.
  - **"Review Again from Session N" starts a new session** preloaded with session N's choices. Nothing is rolled back: the current result changes only when that new session is finished and applied, and every previous result stays in `reviews/versions/`.
  - **Discard Session N** (next to **Continue Review**, while a session is open) asks first: "Discard Session N?" / "Its choices are kept in "Session History" as abandoned; the current result (session M) doesn't change." It runs `review_workorder.py <run> --discard-open`, which marks the session abandoned (nothing is deleted), and the panel goes back to **Review Again (from Session M)**. It is refused while the session's review page is open (select **Stop Reviewing** first) or past Finish.
  - **A run never pinned** first gets a free re-audit (`--pin`), as a job of its own. The review follows when it succeeds.
  - **Review OCR Text** (only when the book's OCR text needs approval: OCR text added by intake, or a flagged existing OCR layer) runs `review_ocr.py <run> --serve`: the OCR-only review page, with each page's image and text, intake's findings and the verdict form (see [The OCR text](review-step.md#the-ocr-text)). It needs no session, so it works on runs that cannot be reviewed again. While it is open, the job card has **Open the OCR Text Review Page** and **Close Without a Verdict**. **Finish OCR Review** on that page records the verdict, closes it and comes back to the run page with the updated report already shown (focus on the result's heading, and the verdict announced); the outcome line says what was recorded ("closed (19:37); OCR verdict recorded: not approved (Lee, 19:36)"). The work-order review page has the same section, where **Record Verdict** records it and the page stays open; the run page then says **OCR Verdict Recorded** with **Show the Updated Report**. Beside the button, the current verdict alone: "OCR Text: Approved", "OCR Text: Not Approved", "OCR Text: Sent to a Language Reader" or "OCR Text: Not Yet Reviewed".
  - **A verdict recorded** on either page changes the run's report at once. A run page left open says "OCR Verdict Recorded" with **Show the Updated Report**; it never reloads by itself.
  - **The run's original PDF.** When the command needs it (a tagged book never pinned, or a basis whose path no longer holds the file), the app finds it by its sha256 in `samples/` (read only) and passes `--pdf`. If no copy is there, the click is refused, naming the file and its sha256.
- **While a review page is open:** the job says "Waiting for you: the review page is open" (no spinner: it waits on a person, not the machine), with **Open the Review Page** and **Stop Reviewing (the Session Stays Open)** instead of the buttons. This holds after the app restarts, and after the review tab was closed without Finish: the review page is still running until Stop. Stop is the terminal's Ctrl+C; afterwards the panel says "The review page is closed. Session N stays open. Select "Continue Review" to pick up where you left off." It is refused once Finish has been accepted (the review is then being recorded and applied). On the review page, **Build a Draft PDF** makes a PDF of the choices so far to check in Acrobat or a screen reader without finishing; the run page doesn't list it, and it is removed when the review page closes (see [Checking a draft PDF while you review](review-step.md#checking-a-draft-pdf-while-you-review)). On a run's first review (before its first apply) the button is **Stop Reviewing (Your Choices Are Saved)**, and afterwards the panel says "The review page is closed. Your choices so far are saved: select "Open the Review Page" to pick up where you left off."
- **The run's jobs** (no heading of their own):
  - **Cards** for jobs that are running or waiting, and for failed or interrupted jobs that no later job of the run has succeeded after. A card's heading is the action in Title Case ("Review Again from Session 4"); its status line says what came of it, in sentence case ("Done: Session 5 applied (Kim, 21:04)").
  - **One line** for the last finished job, after the label **Last Job:**, in sentence case: "Review again from Session 4 → Session 5 applied (Kim, 21:04)". A session is "Session N" and the OCR button "Review OCR Text" in every job line, also for jobs recorded before that rule (the line is formatted when shown): "Review OCR Text → closed (10:24); no verdict recorded".
  - **Every other job** folded under **Previous Jobs (N)**, one line each in the same form. Nothing drops off.
  - **A running job** says its step in words, with a small spinner: "Running: checking the result (2 of 3)". Its list of steps shows the finished ones with their times ("Applying the reviewed decisions: done, 15.0s") and the current one by name only. The spinner is decorative: screen readers skip it, and it stands still when the system asks for reduced motion.
  - **A failed or interrupted job** says why in plain words, and one line says where the job's full output is saved, for whoever looks after the app (`runs/.app/jobs/<id>.log`). The page shows no log lines and no commands.
- **Plain words** (CLAUDE.md's interface rule): the pages name no folders, files or command-line options. The one command a person may need is starting the app again: when the app is not running, the page says to open a terminal in the project's pipeline folder and type `python3 app.py`.
- **Session History**, newest first: every session (its name under its number, who, when, where it started ("Session 1", or the AI's decisions), changes from the AI, what changed in that session, a **Notes** button that opens its notes in a pop-up box, one box per session and several at once: see [Session names and notes](review-step.md#session-names-and-notes)), with a link to each previous result. An open session shows its name and notes as last saved. See [Session names and notes](review-step.md#session-names-and-notes).
- **A book in a batch** links to the batch's page (`/batch/<label>/`).

A run made before the dashboards existed (no `review.html`) gets a page with the panel, the `review.md` link and a line saying it has no dashboard. There is no rebuild button: rebuilding would write into the run.

**The OCR language** is asked only when it matters ([The home page](home.md#language-of-the-scanned-pages)): scans in
the Latin script, or with no text to read, are OCR'd as English, as before (a Hawaiian, Ilokano or Bikol scan included;
lost ʻokina or kahakō are caught at "OCR Text Approval"; the catalogue language, part 2 of #37, is the later fix).

**Review is always on in the app** (D2, Patrick 2026-11-06): every run the app starts, single or in a batch, stops after the AI's decisions for a person's review (`REVIEW=1` on "Start Remediation", "Try Again", "New Run from the Saved Reply" and batches, whatever an older job file says). From a terminal `REVIEW=1` stays optional.

A run stopped before its first review (`workorder.ai.json`, no `record.json` yet; `python3 app.py <run>` opens it too) gets a page with **Open the Review Page** ("Waiting for Review"). **"Finish Review" applies at once** (D3): when the review page closes with its `review.json` written, the app's dispatcher starts `run_api.sh`'s second call in the run's own folder (the original PDF looked up at that moment), once, and the run page shows "Applying the reviewed decisions", or "Waiting to Start" while other runs hold the places. There is no **Apply** button: when the apply can't start (the original PDF is gone, for example) or fails, the page says why with **Try Again**; while a Try Again is waiting or running the page shows it applying, and if it fails too, its own reason (the page follows the newest apply). A review finished before this change, never applied, still offers **Apply the Reviewed Decisions**. For a PDF in a batch, the apply writes the batch's summary again after it. Until the first apply only that page, its state and those buttons answer for the run: no evaluation, downloads or files. See [Review step](review-step.md#steps).

**Every page has a way back,** so the browser's Back button is never the only one:
- `/run/<run>/review.html` (which the "replaced by" note in a previous result's file links to) goes to the run page.
- **A previous result** (`reviews/versions/<id>/review.html`) shows a bar: "You're viewing a previous result (session N)", with **Back to the Current Result** and **Review Again from This Session** (for the result applied without review, **Start Over from the AI's Decisions**). The button starts the review and goes to the run page, which follows it. The file's own "replaced by" note is hidden in the app (the bar says it); it stays in the file.
- **review.md** opens inside a page with **Back to the Run Page** (and, for a previous result, its dashboard), and **The Plain File**.
- **A PDF** opens in the browser's own viewer; its tab or Back button returns.

**The same from a terminal** (not shown on the page), from `pipeline/`: `python3 review_workorder.py <run folder> --reopen [--from N|ai]`, `--sessions`, `--apply` (see [Reviewing the work order](review-step.md)).

**The flow:** **Review Again** → the review page opens by itself → **Finish Review** → the run page, showing apply, verify and report with their times → when they end, "New result ready" and a **Show the New Result** button, which loads it. The page never reloads by itself. The review page also has **Back to the Run Page**, which leaves the review open. It checks each choice as it is saved and refuses **Finish Review** while one needs fixing (see [Checks as you go](review-step.md#checks-as-you-go)), so a choice the check doesn't accept is fixed on the review page, not dropped at apply.

**Focus outlines:** a heading or message the page moves focus to (after a click, or when a page it opened loads) never shows an outline. Tab focus on buttons, links and fields always shows one.

**"Try Again" after a failed apply is offered only for the newest session.** A session whose apply failed stays finished, and the panel offers **Try Again** for it. If a later session is then reviewed and applied, the earlier one is never offered again: applying it would replace the newer result with older decisions.

## Jobs and the queue

- **Every button queues a job:** a file in `runs/.app/jobs/` (`<id>.json`) and its log (`<id>.log`). The command writes straight into the log.
- **Runs at once** (D1): up to `max_jobs` (3) single runs go at once, oldest first. A batch's estimates have their own `batch_jobs` (10) places, like its paid step (R12, Patrick's test 2026-11-07), so a batch of ten PDFs is estimated at once while single runs keep their three. A batch runs alone: a queued batch starts only when no counted job runs, and holds every job queued after it until then, so nothing is passed over and nothing waits forever. Others wait in line, under "Runs in Progress" as "Waiting to Start", and each card says what it waits for ("it starts when the batch "Spring backlist" ends", or its place in line). Accepted exception: "Review Again"'s apply runs inside its own review process after "Finish Review", so it is never queued and can run beside a batch.
- **An open review page waits on a person,** so it does not count until it is past Finish (applying).
- **One job at a time per run.** A second click is refused with the reason: another job for this run is waiting or running, or `reviews/.lock` is held by a review started from a terminal.
- **Two app servers on one jobs folder** (see `--port` below) share the queue and the limit. A second app started with `--port` runs the start-up step that turns queued paid jobs into "Waiting for a new estimate", including the first app's: that fails safe (nothing is sent; a new estimate goes on).
- **Related runs** (a batch and its PDFs) never run jobs at the same time; a batch has `batch_jobs` of its PDFs in progress at once ([The home page](home.md#batches)). One exception: a PDF that stopped for review (the batch never touches it again) may open its review page while the batch still runs; its apply waits ("Waiting to Start") until the batch's job ends.

## When something goes wrong

- **A refusal before anything starts** (the run is busy, no original found, nothing to apply): a message under the buttons, and focus moves to it. Nothing was started.
- **A job that fails:** its card says **Failed**, with the reason in the command's own words (for example "Apply (no model) failed (exit 1): the current result is unchanged; the session stays finished") and where its log is saved. The button to use next is in the panel (**Apply** for a failed apply).
- **A job that stopped without finishing** (the machine restarted, or the job was killed): **Interrupted**, with what is left, read from the run on disk, not from the job:
  - an apply that stopped partway: **Apply** finishes it (it may apply the session again; previous results stay in `reviews/versions/`);
  - a session finished and not applied: **Apply**;
  - an apply that finished on its own after the app lost track of it: **Done (the app lost track of the job)**;
  - a review stopped before Finish: **Continue review** carries on with the open session.
- **An error in the app itself:** one line on the page ("The app hit an error and couldn't do this. Try again; if it happens again, tell whoever looks after the app."); the details go to `runs/.app/server.log`, which the page doesn't name.
- **A run someone else is working on:** the page says who or what and since when, never a process id: "Someone is already reviewing this run (since 14:02). Try again when they're done." (for an apply: "This run is being applied …"). When that other review is a review page the app didn't start (a terminal's `--reopen` or `review_ocr.py --serve`), **Stop the Other Review** asks first ("The other review's session stays open; nothing is lost.") and sends it Ctrl+C, as Stop does; it is refused once that review is past Finish. The lock counts only while its process is alive and is a review process (its command line names `review_workorder.py` or `review_ocr.py`), so a process id the system has reused for something else never blocks a run.
- **Is a job still running?** The app looks for the job's own command (its process id, recorded by the job's wrapper) and for any process of the job's group whose command line is this job's: the wrapper with the job's id, or the command's script with the run folder, compared as the filesystem compares paths (`~/downloads` and `~/Downloads` are one folder on a Mac). When it cannot tell, it counts the job as running. A job marked interrupted whose process turns out to be alive is shown as running again, with **Open the Review Page** and **Stop Reviewing**.
- **Messages that name a button, view or section** put the name in quotes, as it appears on screen: 'press "Continue Review" to carry on'.
- **A run started from the home page** that stops shows its reason in plain words, what the person can do, and a folded **Details** with the step, the exit code, the tool's own line, the record and the log ([The home page](home.md#when-a-run-stops)). This widens "no log lines" to that one folded line.
- **File names on the page:** one exception to "no file names": wherever a book is named, "Source PDF: <file name>" follows its display name ([The home page](home.md#the-home-page)).
- **The app not running:** a banner says so, with the start command. Jobs already running carry on.

## Stopping and starting again

| What was happening | After Ctrl+C on the app (or a crash) and a new start |
|---|---|
| A review page that this app opened, before Finish | It gets Ctrl+C, as in a terminal. The session stays open, and **Continue review** carries on with it. The page's choices are saved to `review_decisions.json` about half a second after each change, or at once when the focus leaves its card (a save under way is written whole first), and kept in the browser. The browser's copy is per page address, and the review page's port can differ next time, so count on what was saved. |
| A review page, after an app crash | It may still be running. The panel shows **Open the review page** and **Stop reviewing** for it. |
| A review past Finish, or any other running job | It carries on and finishes; its end is written to its job file. After the new start, the page shows it. |
| A job killed or cut off by a restart | **Interrupted**, with what is left (above). |
| Jobs waiting in line | They stay queued and start in order after the new start. |

**Starting the app twice** opens the one already running when it has the same settings and the same code. With other settings it is refused. When the code on disk has changed since the running app started (after a `git pull`, or a branch switch), it is refused too: "the running app is older than the code on disk: stop it and start again". The running app keeps the panel's files it read at start, so its pages always match the code it runs. **Restart the app after a `git pull`:** the app writes the evaluation's results itself (its Accessibility Evaluation page), with the code it started with. Each result records that code's git commit (`code`), so a record made by an older app can be found. `--port N` starts a separate app on purpose; both share the jobs folder and its limit.

## Accessibility of the panel

The panel follows WCAG 2.1 AA, the project's standard:
- **Keyboard:** every action is a real button or link, works by keyboard, and shows a visible focus.
- **Status:** always said in words, never by color alone. A failed job's card says "Failed".
- **In-page links move focus**, so a screen reader's cursor follows: the skip link ("Skip to the content") focuses the page's `<main>`; the report's § and Details links, its page map, and the review page's side list focus their target. Headings, sections and messages focused this way show no outline; the row a Details or § link lands on in the report keeps a thin blue outline (2 px), so a sighted reader sees where it landed. The page map is unchanged.
- **Messages** (for example "Session 9 is discarded: …" or "The review page is closed. …") have a **×** button named "Dismiss message" (the × itself is hidden from screen readers). Dismissing moves focus to the **Run Actions** heading; any other panel button clears the message too. A message has a neutral box; an error keeps its red border and has the same button.
- **Announcements:** one polite live region, and only for a step change, a job's start, "the review page is ready", and a job's end. It never reads out log lines.
- **Focus:** it moves only after your own action. After a click it goes to the new job's heading, or to the refusal message. After an upload it goes to the first new PDF's name box, or to the message when a file failed; a pop-up (New Run, New Batch: T4) takes focus into it and gives it back to its opener when it closes; after a "⋯" menu's dialog or name box closes, back to that "⋯" (Patrick's test, 2026-11-07). After Finish it goes to the apply's heading on the run page; after **Show the New Result**, to "Current Result". When a job ends in the background it is announced ("New result ready" when an apply has made one), and focus stays where it is. One exception (Patrick, 2026-11-05): when a run started with **Start Remediation** stops for review, focus moves to **Open the Review Page** only when it is still where the page put it after the click and no key or click has happened since ([The home page](home.md#a-single-run)). The panel checks the run every second while a job runs or a review is open (every 5 s otherwise) and is redrawn only when what it shows changed, so a review page saving its draft never replaces the buttons under the mouse or a text selection.
- **Going on by itself:** only one thing does, the review page after your own **Review Again**, and only within 30 seconds of the click while you have not pressed a key or clicked since. Otherwise it says the page is ready and shows **Open the Review Page**. A new result never replaces the page you are reading.
- **Status words:** a review closed with **Stop reviewing** says "Stopped (the session stays open)".
- **The panel's place:** it comes after the report's own heading and before its content, so the page's h1 comes first.

## Security

- **Only `127.0.0.1`.** No logins, no access from other computers. The settings keep the host and the folders in one place for a shared machine later.
- **Only the app's own pages can act:** every request must name the app as its host, and every button's request must be JSON from the app's own pages.
- **No framing:** every response of the app, and of the review page, says it may not be shown inside another page (`X-Frame-Options: DENY`, `Content-Security-Policy: frame-ancestors 'none'`). So another site cannot frame a run page and trick a click on a button.
- **Scripts:** a run page (and any report page the app serves) runs only the app's own panel script and the page's one inline script, identified by its sha256 when it is served. A `javascript:` link in a report's text, or any other script, does not run. review.html on disk is unchanged; opened as a file it has no such policy, and no buttons.
- **Files:** only the files the run's pages need are served, and nothing outside the runs folder (never `.env`).

## Limits

- **The review page is still review/server.py,** on its own port. The app starts it and sends the browser there.
- **The lock does not cover `--pin` or `run_api.sh`.** The app checks its own jobs, but a pin or a run started in a terminal on the same run at the same time is not stopped.
- **`/run/<run>/download?what=pdf|record&v=current|<version>`** gives a version's remediated PDF or record ZIP, named by its state; the version must be one of the run's own ([Accessibility evaluation and release](release.md#downloads)). **`POST /api/run/<run>/ship`** is "Mark as Shipped" (`{by, note, shown_sha256}`; refused unless the gate is open), through `review/manual.py` `ship()`. Nothing in `release/shipped/` is served (the accessibility statement was dropped, Patrick, 2026-11-01; see [Accessibility evaluation and release](release.md#the-accessibility-statement-dropped)). **`POST /api/run/<run>/remove-older-pdfs`** is "Clean Up Space" (`{by, chosen: [{id, sha256}]}`: the versions selected, each with the hash shown; refused when none is selected or one changed), through `review/prune.py` in the app's process.
- **`/run/<run>/checks`** is the Accessibility Evaluation page ([Accessibility evaluation and release](release.md)); `/run/<run>/checks/` (with a slash) redirects to it, so the page's return after "Record" (relative to its own address) never lands elsewhere; `GET /api/run/<run>/checks` is its data, and `POST /api/run/<run>/checks/draft` and `/checks/record` its saves (JSON from the app's own pages only, as every POST). Every POST's `Content-Length` must be digits and at most 65,536 bytes, checked before reading (411 or 413 otherwise). `/run/<run>/ocr` stays reserved: OCR text is approved on the review page, or on the OCR-only page (**Review OCR Text**), both on the review server.

## Move to Trash

**Move to Trash** (D8, Patrick 2026-11-06; [The home page](home.md#move-to-trash) says where the buttons are and what each
confirmation says) never deletes anything:

- **Where things go:** the macOS Trash (`~/.Trash`), moved there whole by renaming, never copied then deleted. A name
  already in the Trash gets " 2", " 3"… (before a PDF's ".pdf": "ilokano 2.pdf", with its note "ilokano 2.json"): a single run arrives as `<short name> - <run label>` (for example `ilokano -
  First-pass-March`), a whole batch as `batch - <label>`, one PDF of a batch as `batch - <label> - <short name>` (with its
  files from the batch folder in `_batch-files/` inside it), and an added PDF under its own file name, with its note
  from "Upload a PDF" (`<name>.json`) beside it. When the Trash is
  on another disk than the app's folders the move is refused.
- **The record of every move:** `runs/.app/trash-log.json` (what, from which folder, to which name in the Trash, when;
  for a PDF its sha256 and the runs made from it). A run's or batch's plain name moves from `run-names.json` into it. The
  run's job files stay in `runs/.app/jobs/` (the home page lists folders, so nothing shows for a moved run).
- **Putting one back:** Finder's **Put Back** doesn't know items the app moved (Finder only remembers its own moves).
  Open the Trash in Finder and drag the item back to the folder the log names under `from`: a run back into
  `runs/<short name>/` under its label, a batch into `runs/batches/` under its label, an added PDF into the uploads folder
  (`uploads/` at the repository root) under its file name. The app finds it again at once: a run is listed again, and a
  PDF's runs can "Review Again" again. A run's plain name doesn't come back by itself (the log keeps it).
- **Only what the home page lists can be moved:** a run folder (never `runs/.app` or another folder whose name starts
  with "."), a batch folder, a PDF in the uploads folder.
- **When a move is refused:** while anything affected is processing, waiting to start or waiting for a new estimate, has a
  review page open, or sits between "Finish Review" and its apply; a PDF also while any job's command names it. The
  confirmation then says why, and nothing moves.
- **Locks:** each run's record lock is taken once, in path order, around its move; the move log has its own lock. A
  partial batch move rewrites the app's book list (`runs/.app/batches/<label>.books.txt`) and record, so "Run the
  Unfinished PDFs Again" or a `RETRY=1` never sends a PDF that is in the Trash; any estimate of the batch is stale from
  then on (its fingerprint covers the PDFs it was made for).
