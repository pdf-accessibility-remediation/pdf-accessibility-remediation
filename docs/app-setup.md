---
title: Setup, settings and security
parent: The app (browser)
grand_parent: Review and ship
nav_order: 3
---

# Setup, settings and security

This page is for whoever installs and runs the app: what it needs, its settings and limits, how it keeps other pages and programs out, and how Move to Trash works. Internals are at the end, under [For developers](#for-developers).

## Setup

The app needs what the pipeline needs ([Setup](setup.md)). At start it checks each item and prints it as ready or missing, with the command that fixes it. The run page shows a **Setup** warning only when a tool is missing.

- **Required** (the app does not start without them): the Python libraries, veraPDF (its version line, for example `veraPDF 1.30.3`) and Java.
- **Untagged PDFs only** (a warning): OCRmyPDF, Tesseract and its language packs.
- **The API key is not checked at start.** It must be in a `.env` file ([Setup](setup.md), step 3), not only exported in the shell. The app gives its commands a clean environment and drops an exported `OPENROUTER_API_KEY`. The app never reads `.env`; `decide.py` reads it itself.

## Settings

Settings come from one place, read in this order (later wins):

1. `pipeline/webapp/settings.json`: committed, neutral defaults.
2. `pipeline/webapp/settings.local.json`: this machine's own values. It is git-ignored; create it by hand.
3. `--config FILE`: a file of your own, for example for tests. It may not be either of the two files above.
4. An exported `VERAPDF` (the launcher's path), which wins over every file.

| Key | Default | What it sets |
|---|---|---|
| `host` | `127.0.0.1` | Where the app listens. Only `127.0.0.1` is accepted: the app has no logins, so it is not reachable from other computers |
| `port` | `8760` | The app's port. The review pages use 8765–8784, as from the terminal |
| `runs`, `samples`, `uploads` | `../runs`, `../samples`, `../uploads` | The folders, relative to `pipeline/` (or absolute). See [The folders](#the-folders) |
| `jobs` | `../runs/.app` | The job files, their logs, and the app's own small files |
| `max_jobs` | `3` | How many single runs go at once. Open review pages do not count until they apply. A batch runs alone |
| `batch_jobs` | `10` | How many PDFs of a batch are in progress at once (batch_api.sh's `JOBS`), and how many batch estimates go at once. Subject to change once the hardware limits are measured |
| `max_books_per_batch` | `50` | The most PDFs "New Batch" accepts. batch_api.sh in a terminal has no cap |
| `upload_max_mb` | `1024` | The largest PDF "Upload a PDF" and **Bring Back an Edited PDF** accept, in MB |
| `limits` | not set | The dollar limits (see [The limits](#the-limits)) |
| `tools.VERAPDF` | empty | The veraPDF launcher. Empty: `verapdf` on the PATH |
| `tools.path_prepend` | `[]` | Folders put first on the PATH the app's commands get, for example Java's |

### The folders

`uploads` holds the PDFs added with "Upload a PDF" and not used yet ([The home page](home-runs.md#upload-a-pdf)). A run started from the app moves its PDF into its own `source/` folder. Edited copies uploaded with **Bring Back an Edited PDF** go to its `.edited/` folder, which is never listed as PDFs.

`samples` is never listed; it is only searched by sha256 for the original of a run made before runs kept their own PDF. Every job writes into `runs` (the app passes it as `RUNS_DIR`).

### The limits

`limits` sets, in dollars, what the estimates are compared with and the most a "Start Remediation" may bind (`MAX_USD`, `BOOK_MAX_USD`, `BATCH_MAX_USD`). The defaults are `DEFAULT_LIMITS` in `lib/costs.py`, one place for the app and the terminal: `{"per_call_usd": 2, "per_book_usd": 5, "per_batch_usd": 10}`.

A value here or in `settings.local.json` overrides them. A page to change the limits is a later issue (#87). See [What a run may cost](options.md#what-a-run-may-cost).

"Check Credit Again" keeps the last credit read for 10 minutes in `runs/.app/credit.json`: dollars and the reason a read failed, never the key.

### Java that is not on PATH

Put its `bin` folder in `path_prepend` in `settings.local.json`. For example, with Homebrew's openjdk@21 and veraPDF installed in your home folder:

```json
{
 "tools": {"VERAPDF": "~/verapdf/verapdf", "path_prepend": ["/opt/homebrew/opt/openjdk@21/bin"]}
}
```

On Linux or WSL, Java is usually on PATH already. If it is not, use the folder `which java` would show (for example `/usr/lib/jvm/java-17-openjdk-amd64/bin`).

### veraPDF is never off in the app

`VERAPDF=off` is refused from any source: a settings file, `--config`, or the shell. The start check passes only with a veraPDF version line; the command line's `VERAPDF=off` (which `vera.py --check` accepts) does not count. No setting skips the check.

The app's own tests do not weaken this: they unset `VERAPDF` and give, through `--config`, a small script that answers `--version` as veraPDF does.

## Security

- **Only `127.0.0.1`.** No logins, no access from other computers. The settings keep the host and the folders in one place for a shared machine later.
- **Only the app's own pages can act:** every request must name the app as its host, and every button's request must be JSON from the app's own pages.
- **No framing:** every response of the app, and of the review page, says it may not be shown inside another page (`X-Frame-Options: DENY`, `Content-Security-Policy: frame-ancestors 'none'`). So another site cannot frame a run page and trick a click on a button.
- **Scripts:** a run page (and any report page the app serves) runs only the app's own scripts, the app's own one-line calls to them (a fixed set of nine, see [Page changes in one step](app-run-page.md#page-changes-in-one-step)) and the page's one other inline script (the report's), each inline script identified by its sha256 when it is served. A `javascript:` link in a report's text, or any other script, does not run (and report_html.py no longer makes such a link live in the first place: only "#…", http:, https: and relative paths). review.html on disk is unchanged; opened as a file it has no such policy, and no buttons.
- **Files:** only the files the run's pages need are served, and nothing outside the runs folder (never `.env`).

## Limits

- **The review page is still review/server.py,** on its own port. The app starts it and sends the browser there.
- **The lock does not cover `--pin` or `run_api.sh`.** The app checks its own jobs, but a pin or a run started in a terminal on the same run at the same time is not stopped.

## Move to Trash

**Move to Trash** never deletes anything. [The home page](home-workspace.md#move-to-trash) says where the buttons are and what each confirmation says.

**Where things go:** the macOS Trash (`~/.Trash`), moved there whole by renaming, never copied then deleted. When the Trash is on another disk than the app's folders, the move is refused. Names in the Trash:
- a single run: `<short name> - <run label>`, for example `ilokano - First-pass-March`
- a whole batch: `batch - <label>`
- one PDF of a batch: `batch - <label> - <short name>`, with its files from the batch folder in `_batch-files/` inside it
- an added PDF: its own file name, with its note from "Upload a PDF" (`<name>.json`) beside it

A name already in the Trash gets " 2", " 3"…, before a PDF's ".pdf": "ilokano 2.pdf", with its note "ilokano 2.json".

**Nothing is restored through the app** (#93). Its pages say so ("… cannot be restored through the app."), and point a person who needs a PDF again to uploading the same PDF again with **Choose PDFs** on the home page. The app finds it by its sha256, so its runs can "Review Again" again, and a run that was waiting for "Start Remediation" (or "Get a New Estimate") goes on with the copy, its estimate unchanged. A different file name is fine: the copy's sha256 is read again before it is used, and the result is named after the copy's file name.

**Putting one back by hand** (for whoever looks after the app, not offered on its pages): Finder's **Put Back** doesn't know items the app moved; Finder only remembers its own moves. Open the Trash in Finder and drag the item back to the folder the move log names under `from`:
- a run back into `runs/<short name>/` under its label
- a batch into `runs/batches/` under its label
- an added PDF into the uploads folder (`uploads/` at the repository root) under its file name

The app finds it again at once: a run is listed again, and a PDF's runs can "Review Again" again. A run's plain name doesn't come back by itself; the log keeps it.

**Only what the home page lists can be moved:** a run folder (never `runs/.app` or another folder whose name starts with "."), a batch folder, a PDF in the uploads folder.

**When a move is refused:** while anything affected is processing, waiting to start or waiting for a new estimate, has a review page open, or sits between "Finish Review" and its apply. A PDF is also refused while any job's command names it. The confirmation then says why, and nothing moves.

## For developers

### Move to Trash internals

- **The record of every move:** `runs/.app/trash-log.json` holds what, from which folder, to which name in the Trash, and when; for a PDF, its sha256 and the runs made from it. A run's or batch's plain name moves from `run-names.json` into it.
- The run's job files stay in `runs/.app/jobs/`. The home page lists folders, so nothing shows for a moved run.
- **Locks:** each run's record lock is taken once, in path order, around its move; the move log has its own lock.
- A partial batch move rewrites the app's list of PDFs (`runs/.app/batches/<label>.books.txt`) and record, so "Run the Unfinished PDFs Again" or a `RETRY=1` never sends a PDF that is in the Trash. Any estimate of the batch is stale from then on, because its fingerprint covers the PDFs it was made for.

Opened as a file, `review.html` has had no terminal command since 2026-10-29; the command is in [Reviewing the work order](review-step.md).
