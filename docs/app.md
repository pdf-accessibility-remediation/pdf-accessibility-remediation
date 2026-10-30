---
title: The app (browser)
nav_order: 3.6
---

# The pipeline in the browser

`app.py` is a small local web app. It shows a run's dashboard (`review.html`) with buttons that review it again, start over, go back to an earlier session's choices, and apply a finished session. Each button runs the same command a person would type (`review_workorder.py … --reopen`, `--apply`, `--pin`), so the command line keeps working exactly as before and both give the same result. The app adds no pipeline logic. A home page with books and new runs is planned (branch home-interface).

```bash
cd pipeline
python3 app.py ../runs/godzone/rv1          # opens that run's page at http://127.0.0.1:8760/run/godzone/rv1/
```

After this one start command the terminal can be left alone. Everything the pages show is read from disk (the run folders, their `reviews/`, and `runs/.app/`), so stopping and restarting the app loses nothing.

## Setup

The app needs what the pipeline needs ([Setup](setup.md)). At start it checks each item and prints it as ready or missing, with the command that fixes it; the run page shows the same list under **Setup**.

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
| `runs`, `samples`, `uploads` | `../runs`, `../samples`, `../uploads` | The folders, relative to `pipeline/` (or absolute). `uploads` is for the planned home page. |
| `jobs` | `../runs/.app` | The job files, their logs, and the app's own small files (below). |
| `max_jobs` | `2` | How many jobs run at once, across every run (open review pages do not count until they apply). |
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

`test_reply_dir` is for the tests of the planned home page. It is accepted only from `--config`, never from a settings file.

**What the app's commands get.** Each command starts from a clean environment:
- **Kept from the shell that started the app:** `PATH`, `HOME`, `LANG`, `LC_*`, `TMPDIR`, `USER`, `LOGNAME`, `SHELL`.
- **Put first on PATH:** the venv's `bin/` and `path_prepend`.
- **Added:** `VERAPDF` from the settings, and the variables the job itself sets.
- **Dropped:** everything else, for example `MODEL`, `REPLY`, `FROM`, `KEEP`, `RUNS_DIR`, `OCR_LANG`, `MAX_TOKENS` or an API key exported in the shell. So no setting meant for one terminal run changes an app job.
- The job file records the whole environment each command was given.

## The run page

`http://127.0.0.1:8760/run/<run>/` is the run's `review.html` with a **Run actions** panel at the top. The panel is added when the app serves the page; the file on disk is not changed. Opened as a file, `review.html` is the same report as before, with the command that reopens the review.

The panel shows:
- **The current result:** which session it comes from. "Ready to ship?" is not repeated in the panel: the report's own card, right below, says it.
- **The buttons:**

  | Button | Runs (from `pipeline/`) |
  |---|---|
  | **Review again** (from the latest finished session; **Continue review** when a session is open) | `review_workorder.py <run> --reopen` |
  | **Start over from the AI's decisions** | `… --reopen --from ai` |
  | **Review again from session N** (in **Session history**) | `… --reopen --from N` |
  | **Apply session N** (only while the newest session is finished and not applied) | `… --apply` |

  - **Starting over or going back with a session open** asks first. The dialog names the open session and the file it is kept in. OK adds `--discard-open`: the open session is marked abandoned, never deleted.
  - **"Review again from session N" starts a new session** preloaded with session N's choices. Nothing is rolled back: the current result changes only when that new session is finished and applied, and every earlier result stays in `reviews/versions/`.
  - **A run never pinned** first gets a free re-audit (`--pin`), as a job of its own. The review follows when it succeeds.
  - **The run's original PDF.** When the command needs it (a tagged book never pinned, or a basis whose path no longer holds the file), the app finds it by its sha256 in `samples/` (read only) and passes `--pdf`. If no copy is there, the click is refused, naming the file and its sha256.
- **While a review page is open:** the job says "Waiting for you: the review page is open" (no spinner: it waits on a person, not the machine), with **Open the review page** and **Stop reviewing (the session stays open)** instead of the buttons. This holds after the app restarts, and after the review tab was closed without Finish: the review page is still running until Stop. Stop is the terminal's Ctrl+C. It is refused once Finish has been accepted (the review is then being recorded and applied).
- **Jobs for this run:**
  - **Cards** for jobs that are running or waiting, and for failed or interrupted jobs that no later job of the run has succeeded after.
  - **One line** for the last finished job.
  - **Every other job** folded under **Earlier jobs (N)**. Nothing drops off.
  - **Titles say what happened,** for example "Review again from session 2 → session 3 applied (Kim, 18:19)" or "Apply session 2 → failed (10:04)".
  - **A running job** says its step in words, with a small spinner: "Running: checking the result (2 of 3)". The spinner is decorative: screen readers skip it, and it stands still when the system asks for reduced motion.
  - **A failed or interrupted job** says why in plain words, and one line says where its log is saved (`runs/.app/jobs/<id>.log`). The page shows no log lines and no commands.
- **Session history:** every session (who, when, where it started, changes from the AI, what changed in that session), with a link to each earlier result.
- **A book in a batch** links to the batch's page (`/batch/<label>/`).

A run made before the dashboards existed (no `review.html`) gets a page with the panel, the `review.md` link and a line saying it has no dashboard. There is no rebuild button: rebuilding would write into the run.

**Every page has a way back,** so the browser's Back button is never the only one:
- `/run/<run>/review.html` (which the "replaced by" note on an earlier result links to) goes to the run page.
- **An earlier result** (`reviews/versions/<id>/review.html`) shows a bar: "You're viewing an earlier result (session N)", with **Back to the current result** and **Review again from this session** (for the result applied without review, **Start over from the AI's decisions**). The button starts the review and goes to the run page, which follows it.
- **review.md** opens inside a page with **Back to the run page** (and, for an earlier result, its dashboard), and a link to the plain file.
- **A PDF** opens in the browser's own viewer; its tab or Back button returns.

**The same from a terminal** (not shown on the page), from `pipeline/`: `python3 review_workorder.py <run folder> --reopen [--from N|ai]`, `--sessions`, `--apply` (see [Reviewing the work order](review-step.md)).

**The flow:** **Review again** → the review page opens by itself → **Finish review** → the run page, showing apply, verify and report with their times → when they end, "New result ready" and a **Show the new result** button, which loads it. The page never reloads by itself. The review page also has **Back to the run page**, which leaves the review open.

**Apply is offered only for the newest session.** A session whose apply failed stays finished. If a later session is then reviewed and applied, the earlier one is never offered again: applying it would replace the newer result with older decisions.

## Jobs and the queue

- **Every button queues a job:** a file in `runs/.app/jobs/` (`<id>.json`) and its log (`<id>.log`). The command writes straight into the log.
- **The limit:** up to `max_jobs` jobs run at once, oldest first. Others wait in line, and each card says where.
- **An open review page waits on a person,** so it does not count until it is past Finish (applying).
- **One job at a time per run.** A second click is refused with the reason: another job for this run is waiting or running, or `reviews/.lock` is held by a review started from a terminal.
- **Two app servers on one jobs folder** (see `--port` below) share the queue and the limit.

## When something goes wrong

- **A refusal before anything starts** (the run is busy, no original found, nothing to apply): a message under the buttons, and focus moves to it. Nothing was started.
- **A job that fails:** its card says **Failed**, with the reason in the command's own words (for example "Apply (no model) failed (exit 1): the current result is unchanged; the session stays finished") and where its log is saved. The button to use next is in the panel (**Apply** for a failed apply).
- **A job that stopped without finishing** (the machine restarted, or the job was killed): **Interrupted**, with what is left, read from the run on disk, not from the job:
  - an apply that stopped partway: **Apply** finishes it (it may apply the session again; earlier results stay in `reviews/versions/`);
  - a session finished and not applied: **Apply**;
  - an apply that finished on its own after the app lost track of it: **Done (the app lost track of the job)**;
  - a review stopped before Finish: **Continue review** carries on with the open session.
- **An error in the app itself:** one line on the page; the details go to `runs/.app/server.log`.
- **The app not running:** a banner says so, with the start command. Jobs already running carry on.

## Stopping and starting again

| What was happening | After Ctrl+C on the app (or a crash) and a new start |
|---|---|
| A review page that this app opened, before Finish | It gets Ctrl+C, as in a terminal. The session stays open, and **Continue review** carries on with it. The page's choices are kept in `review_decisions.json` after each **Save**, and in the browser. The browser's copy is per page address, and the review page's port can differ next time, so count on what was saved. |
| A review page, after an app crash | It may still be running. The panel shows **Open the review page** and **Stop reviewing** for it. |
| A review past Finish, or any other running job | It carries on and finishes; its end is written to its job file. After the new start, the page shows it. |
| A job killed or cut off by a restart | **Interrupted**, with what is left (above). |
| Jobs waiting in line | They stay queued and start in order after the new start. |

**Starting the app twice** opens the one already running when it has the same settings and the same code. With other settings it is refused. When the code on disk has changed since the running app started (after a `git pull`, or a branch switch), it is refused too: "the running app is older than the code on disk: stop it and start again". The running app keeps the panel's files it read at start, so its pages always match the code it runs. `--port N` starts a separate app on purpose; both share the jobs folder and its limit.

## Accessibility of the panel

The panel follows WCAG 2.1 AA, the project's standard:
- **Keyboard:** every action is a real button or link, works by keyboard, and shows a visible focus.
- **Status:** always said in words, never by colour alone. A failed job's card says "Failed".
- **Announcements:** one polite live region, and only for a step change, a job's start, "the review page is ready", and a job's end. It never reads out log lines.
- **Focus:** it moves only after your own action. After a click it goes to the new job's heading, or to the refusal message. After Finish it goes to the apply's heading on the run page; after **Show the new result**, to "Current result". When a job ends in the background it is announced ("New result ready" when an apply has made one), and focus stays where it is.
- **Going on by itself:** only one thing does, the review page after your own **Review again**, and only within 30 seconds of the click while you have not pressed a key or clicked since. Otherwise it says the page is ready and shows **Open the review page**. A new result never replaces the page you are reading.
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
- **Planned pages** have reserved addresses but are not built: `/run/<run>/ocr` (approving OCR text), `/run/<run>/release` (the release sign-off) and `/run/<run>/screen-reader` (the after-ship check).
