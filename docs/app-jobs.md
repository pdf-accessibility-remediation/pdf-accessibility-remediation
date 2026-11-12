---
title: Jobs and problems
parent: The app (browser)
grand_parent: Review and ship
nav_order: 2
---

# Jobs, problems and restarts

Every pipeline step the app starts runs as a job. This page explains how jobs wait their turn, what the pages say when a job stops or another person is working on a run, and what happens when the app is stopped and started again. Internals are at the end, under [For developers](#for-developers).

## Jobs and the queue

**Every button queues a job,** with its own job file and log.

**The jobs check** has two forms (#93): `GET /api/jobs?limit=N` (the newest N, at most 500; 50 by default) and `GET /api/jobs?active=1&seen=<id>,<id>,…`, the home page's. The second returns every job whose status can still change (queued, running, needs-spend, and interrupted while it may be alive after all: no exit recorded and a process group) and every job named in `seen` (job-id characters only, at most 500 ids; unknown ids are ignored), newest first, in the same shape. Both read the job files once per answer, and a job's place in line counts every queued job, not only the ones shown. A page reads each names file (`book-names.json`, `run-names.json`, `books-cache.json`) and each job file at most once, and asks Tesseract for its installed languages (`tesseract --list-langs`) at most once, only when a PDF on it is waiting for its language.

**Runs at once:**
- Up to `max_jobs` (3) single runs go at once, oldest first.
- A batch's estimates have their own `batch_jobs` (10) places, like its paid step, so a batch of ten PDFs is estimated at once while single runs keep their three.
- A batch runs alone. A queued batch starts only when no counted job runs, and holds every job queued after it until then, so nothing is passed over and nothing waits forever.

Others wait in line, under "Runs in Progress" as "Waiting to Start". Each card says what it waits for: "it starts when the batch "Spring backlist" ends", or its place in line. One accepted exception: "Review Again"'s apply runs inside its own review process after "Finish Review", so it is never queued and can run beside a batch.

- **An open review page waits on a person,** so it does not count until it is past Finish (applying).
- **One job at a time per run.** A second click is refused with the reason: another job for this run is waiting or running, or a review started from a terminal holds the run.
- **Related runs** (a batch and its PDFs) never run jobs at the same time; a batch has `batch_jobs` of its PDFs in progress at once ([The home page](home-batches.md#batches)). One exception: a PDF that stopped for review (the batch never touches it again) may open its review page while the batch still runs. Its apply waits ("Waiting to Start") until the batch's job ends.
- **Two app servers on one jobs folder** (see `--port` below) share the queue and the limit.

## When something goes wrong

- **A refusal before anything starts** (the run is busy, no original found, nothing to apply): a message under the buttons, and focus moves to it. Nothing was started.
- **A job that fails:** its card says **Failed**, with the reason in the command's own words, for example "Apply (no model) failed: the current result is unchanged; the session stays finished". Its exit code and where its log is saved are inside a folded **Details**, never in plain view, on its card and in Previous Jobs. The button to use next is in the panel (**Apply** for a failed apply).
- **A designed stop is never a failure.** An estimate that stopped to ask the language of the scanned pages reads "stopped to ask the language of the scanned pages". A run whose intake stopped the PDF for a reviewer (no page to tag, a password, PDF 2.0) reads "stopped for a person". Neither is shown or counted as Failed, and the run page says why.
- **A run started from the home page** that stops shows its reason in plain words, what the person can do, and a folded **Details** with the step, the exit code, the tool's own line, the record and the log ([The home page](home-runs.md#when-a-run-stops)). This widens "no log lines" to that one folded line.
- **An error in the app itself:** one line on the page ("The app hit an error and couldn't do this. Try again; if it happens again, tell whoever looks after the app."). The details go to the app's own log, which the page doesn't name.
- **The app not running:** a banner says so, with the start command. Jobs already running carry on.

**The AI step in plain words.** Job lines, the batch page's side list and dashboard, and a run's step list read "Running: Sending to the AI (Claude Sonnet 5.5)". The step's words are capitalized after "Running:", as for every step. The model named is the one the run itself used, never the settings' current model for an older run, by its display name.

### A job that stopped without finishing

When the machine restarted or the job was killed, the job reads **Interrupted**, with what is left, read from the run on disk, not from the job:
- an apply that stopped partway: **Apply** finishes it. It may apply the session again; previous results stay in `reviews/versions/`.
- a session finished and not applied: **Apply**
- an apply that finished on its own after the app lost track of it: **Done (the app lost track of the job)**
- a review stopped before Finish: **Continue review** carries on with the open session

### A run someone else is working on

The page says who or what and since when, never a process id: "Someone is already reviewing this run (since 14:02). Try again when they're done." For an apply: "This run is being applied …".

When that other review is a review page the app didn't start (a terminal's `--reopen` or `review_ocr.py --serve`), **Stop the Other Review** asks first ("The other review's session stays open; nothing is lost."). It then sends it Ctrl+C, as Stop does. It is refused once that review is past Finish.

## Stopping and starting again

| What was happening | After Ctrl+C on the app (or a crash) and a new start |
|---|---|
| A review page that this app opened, before Finish | It gets Ctrl+C, as in a terminal. The session stays open, and **Continue review** carries on with it. See [Saved choices after a stop](#saved-choices-after-a-stop) |
| A review page, after an app crash | It may still be running. The panel shows **Open the review page** and **Stop reviewing** for it |
| A review past Finish, or any other running job | It carries on and finishes; its end is written to its job file. After the new start, the page shows it |
| A job killed or cut off by a restart | **Interrupted**, with what is left (above) |
| Jobs waiting in line | They stay queued and start in order after the new start |

### Saved choices after a stop

The review page's choices are saved to `review_decisions.json` about half a second after each change, or at once when the focus leaves its card (a save under way is written whole first), and kept in the browser. The browser's copy is per page address, and the review page's port can differ next time, so count on what was saved.

### Starting the app twice

Starting the app twice opens the one already running, when it has the same settings and the same code. With other settings it is refused.

When the code on disk has changed since the running app started (after a `git pull`, or a branch switch), it is refused too: "the running app is older than the code on disk: stop it and start again". The running app keeps the panel's files it read at start, so its pages always match the code it runs.

**Restart the app after a `git pull`.** The app writes the evaluation's results itself (its Accessibility Evaluation page), with the code it started with. Each result records that code's git commit (`code`), so a record made by an older app can be found.

`--port N` starts a separate app on purpose; both share the jobs folder and its limit.

## For developers

### What the app's commands get

Each command starts from a clean environment:
- **Kept from the shell that started the app:** `PATH`, `HOME`, `LANG`, `LC_*`, `TMPDIR`, `USER`, `LOGNAME`, `SHELL`.
- **Put first on PATH:** the venv's `bin/` and `path_prepend`.
- **Added:** `VERAPDF` from the settings, and the variables the job itself sets, from a fixed list: `REVIEW`, `AUTO`, `ESTIMATE`, `OCR_LANG`, `RUN_DIR`, `INTAKE_REUSE`, `REPLY`, `MAX_USD`, `INTAKE`, `OUT`, `JOBS`, `BATCH_MAX_USD`, `BOOK_MAX_USD`, `FIGURE_RETRY_MAX_USD`, `FIGURE_RETRY_BOOK_MAX_USD`, `RETRY`, `MODEL` (only a Claude model, the one the estimate used) and `FROM` (test mode only). Never `FORCE_OCR`.
- **Dropped:** everything else, for example `MODEL`, `REPLY`, `FROM`, `KEEP`, `RUNS_DIR`, `OCR_LANG`, `MAX_TOKENS` or an API key exported in the shell. So no setting meant for one terminal run changes an app job.

The job file records the whole environment each command was given.

`test_reply_dir` and `test_batch_from` are for the app's tests ([The home page](home-workspace.md#test-mode)). They are accepted only from `--config`, never from a settings file. `test_reply_dir` is relative to `pipeline/`, as the folders are.

### Jobs on disk

- Each job is a file in `runs/.app/jobs/` (`<id>.json`) with its log (`<id>.log`). The command writes straight into the log. A failed job's log is `runs/.app/jobs/<id>.log`.
- Errors in the app itself go to `runs/.app/server.log`.
- A review started from a terminal holds `reviews/.lock`.
- A second app started with `--port` runs the start-up step that turns queued paid jobs into "Waiting for a new estimate", including the first app's. That fails safe: nothing is sent, and a new estimate goes on.
- **Apply after Finish:** when the review page closes with its `review.json` written, the app's dispatcher starts `run_api.sh`'s second call. A first review leaves `workorder.ai.json` and no `record.json` yet.
- **Bring Back an Edited PDF:** each download of the current version is logged in the run's `hand_edits.json`. The upload goes to `uploads/.edited/` (made when needed; gitignored), under a cleaned name: a different file never replaces one already there, and the same file keeps its name. It stays there after the import, which keeps its own copy in the new run. Then the app runs `handedit.py import <run> <file> --by … --note … --label handedit-<date>-<time>` as a job.

**Is a job still running?** The app looks for the job's own command (its process id, recorded by the job's wrapper), and for any process of the job's group whose command line is this job's: the wrapper with the job's id, or the command's script with the run folder. Paths are compared as the filesystem compares them (`~/downloads` and `~/Downloads` are one folder on a Mac).

When it cannot tell, it counts the job as running. A job marked interrupted whose process turns out to be alive is shown as running again, with **Open the Review Page** and **Stop Reviewing**.

**Locks held by others.** A review lock counts only while its process is alive and is a review process (its command line names `review_workorder.py` or `review_ocr.py`). So a process id the system has reused for something else never blocks a run.

### Model display names

The model's display name comes from `webapp/runs.py` `model_words()`; run_api.sh names the model in the step's label. It is a small table of names the general rule reads badly (`MODEL_NAMES`: "GPT-4o", "OpenAI o3"…), else the id's last part with each word capitalized ("anthropic/claude-sonnet-5.5" → "Claude Sonnet 5.5"). **When a new model is adopted, check its display name** on a test run's page, and add it to `MODEL_NAMES` if the rule reads it badly.
