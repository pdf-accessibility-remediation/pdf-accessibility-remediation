---
title: The run page
parent: The app (browser)
grand_parent: Review and ship
nav_order: 1
---

# The run page

The run page shows one run's dashboard with the buttons that review it again, apply a session and bring back a PDF edited by hand. This page explains those buttons, how the page behaves while a review is open, and how the pages work with a keyboard and a screen reader. Internals are at the end, under [For developers](#for-developers).

## The run page

`http://127.0.0.1:8760/run/<run>/` is the run's `review.html` with a **Run Actions** panel at the top. The panel is added when the app serves the page; the file on disk is not changed. Opened as a file, `review.html` is the same report as before.

The panel shows:
- **The current result:** "Current Result: Session N". "Ready to ship?" is not repeated in the panel: the report's own card, right below, says it.
- **The buttons** (below).
- **The run's jobs** (see [The run's jobs](#the-runs-jobs)).
- **Session History,** newest first (see [Session History](#session-history)).
- **A PDF in a batch** links to the batch's page (`/batch/<label>/`).

A run made before the dashboards existed (no `review.html`) gets a page with the panel, the `review.md` link, and a line saying it has no dashboard. There is no rebuild button: rebuilding would write into the run.

### The review buttons

| Button | Runs (from `pipeline/`) |
|---|---|
| **Review Again** (from the latest finished session; **Continue Review** when a session is open) | `review_workorder.py <run> --reopen` |
| **Start Over from the AI's Decisions** | `… --reopen --from ai` |
| **Review Again from Session N** (in **Session History**) | `… --reopen --from N` |
| **Apply Session N** (only while the newest session is finished and not applied) | `… --apply` |

- **Starting over or going back with a session open** asks first. The dialog names the open session, and says its choices stay in Session History. OK adds `--discard-open`: the open session is marked abandoned, never deleted.
- **"Review Again from Session N" starts a new session** preloaded with session N's choices. Nothing is rolled back: the current result changes only when that new session is finished and applied, and every previous result stays in `reviews/versions/`.
- **A run never pinned** first gets a free re-audit (`--pin`), as a job of its own. The review follows when it succeeds.
- **The run's original PDF.** When the command needs it (a tagged PDF never pinned, or a basis whose path no longer holds the file), the app finds it by its sha256 in `samples/` (read only) and passes `--pdf`. If no copy is there, the click is refused, naming the file and its sha256.

**Discard Session N** (next to **Continue Review**, while a session is open) asks first: "Discard Session N?" / "Its choices are kept in "Session History" as abandoned; the current result (session M) doesn't change." It runs `review_workorder.py <run> --discard-open`, which marks the session abandoned (nothing is deleted), and the panel goes back to **Review Again (from Session M)**. It is refused while the session's review page is open (select **Stop Reviewing** first) or past Finish.

### Review OCR Text

**Review OCR Text** appears only when the PDF's OCR text needs approval: OCR text added by intake, or a flagged existing OCR layer. Beside the button is the current verdict alone: "OCR Text: Approved", "OCR Text: Not Approved", "OCR Text: Sent to a Language Reader" or "OCR Text: Not Yet Reviewed".

It runs `review_ocr.py <run> --serve`: the OCR-only review page, with each page's image and text, intake's findings and the verdict form (see [The OCR text](review-ocr.md#the-ocr-text)). It needs no session, so it works on runs that cannot be reviewed again. While it is open, the job card has **Open the OCR Text Review Page** and **Close Without a Verdict**.

**Finish OCR Review** on that page records the verdict, closes it, and comes back to the run page with the updated report already shown: focus on the result's heading, and the verdict announced. The outcome line says what was recorded: "closed (19:37); OCR verdict recorded: not approved (Lee, 19:36)".

The work-order review page has the same section, where **Record Verdict** records it and the page stays open. A verdict recorded on either page changes the run's report at once. A run page left open then says **OCR Verdict Recorded** with **Show the Updated Report**; it never reloads by itself.

### Bring Back an Edited PDF

**Bring Back an Edited PDF** brings back a copy of the result that a person changed in Acrobat, as a new run that stops for review (see [Editing the PDF by hand](hand-edits.md)):

1. Download the current version with **Download the Remediated PDF**. Each such download is logged as an export of the run (with no name: the app has no logins).
2. Edit it in Acrobat with text recognition off (Edit, then Edit settings, uncheck **Recognize scanned text**).
3. Select **Bring Back an Edited PDF**, choose the edited file (**Edited PDF**), and fill in **Edited By** and **What You Changed**. **Bring Back** uploads the file, showing "Uploading… N%". Cancel or Escape stops the upload.

The new run is made beside this one, with no AI call ($0), and this run is not changed. The job's card then has **Open the Edited Run**, where the new run waits for **Open the Review Page** like any run stopped for review. **Finish Review** applies it at once.

It is refused, with the reason in the dialog, when:
- the file is not a PDF, or is larger than `upload_max_mb`
- this PDF's working files were cleared (**Clear This Book's Files**): there is no result to compare it with
- it is the same file as the result
- the run's own PDF was changed after the run made it
- a name or note is missing, or longer than one line of 200 characters

The full pipeline with a new AI call is not offered here, because a job cannot answer the cost question. Use `handedit.py import … --to pipeline` in a terminal.

**Edited Copies** lists the runs made from edited copies of this one: who, when, the note, and its state:
- **finished** or **waiting for its review**, with **Open**
- **being prepared:** its job is running
- **not started:** brought back but never run (`handedit.py import --no-run`, or a job that failed or was stopped), with **Start**, which runs the same import again. A copy brought back for the full pipeline says to start it in a terminal, because it is a paid call.
- **removed**

A run made from an edited copy says which run it came from, with a link.

### While a review page is open

The job says "Waiting for you: the review page is open", with no spinner: it waits on a person, not the machine. **Open the Review Page** and **Stop Reviewing (the Session Stays Open)** replace the buttons. This holds after the app restarts, and after the review tab was closed without Finish: the review page is still running until Stop.

Stop is the terminal's Ctrl+C. Afterwards the panel says "The review page is closed. Session N stays open. Select "Continue Review" to pick up where you left off." It is refused once Finish has been accepted, because the review is then being recorded and applied.

On a run's first review (before its first apply), the button is **Stop Reviewing (Your Choices Are Saved)**. Afterwards the panel says "The review page is closed. Your choices so far are saved: select "Open the Review Page" to pick up where you left off."

On the review page, **Build a Draft PDF** makes a PDF of the choices so far, to check in Acrobat or with a screen reader without finishing. The run page doesn't list it, and it is removed when the review page closes (see [Checking a draft PDF while you review](review-finish.md#checking-a-draft-pdf-while-you-review)).

### The run's jobs

The jobs have no heading of their own:

- **Cards** for jobs that are running or waiting, and for failed or interrupted jobs that no later job of the run has succeeded after. A card's heading is the action in Title Case ("Review Again from Session 4"); its status line says what came of it, in sentence case ("Done: Session 5 applied (Kim, 21:04)").
- **One line** for the last finished job, after the label **Last Job:**, in sentence case: "Review again from Session 4 → Session 5 applied (Kim, 21:04)".
- **Every other job,** folded under **Previous Jobs (N)**, one line each in the same form. Nothing drops off.

A session is "Session N" and the OCR button "Review OCR Text" in every job line, also for jobs recorded before that rule (the line is formatted when shown): "Review OCR Text → closed (10:24); no verdict recorded".

**A running job** says its step in words, with a small spinner: "Running: checking the result (2 of 3)". Its list of steps shows the finished ones with their times ("Applying the reviewed decisions: done, 15.0s"), and the current one by name only. The spinner is decorative: screen readers skip it, and it stands still when the system asks for reduced motion.

**A failed or interrupted job** says why in plain words. One line says where the job's full output is saved, for whoever looks after the app. The page shows no log lines and no commands.

### Session History

Session History lists every session, newest first: its name under its number, who, when, where it started ("Session 1", or the AI's decisions), changes from the AI, and what changed in that session. Each has a link to its previous result, and a **Notes** button that opens its notes in a pop-up box (one box per session, several at once). An open session shows its name and notes as last saved. See [Session names and notes](review-page.md#session-names-and-notes).

### Review is always on in the app

Every run the app starts, single or in a batch, stops after the AI's decisions for review. That covers "Start Remediation", "Try Again", "New Run from the Saved Reply" and batches, whatever an older job file says. From a terminal, `REVIEW=1` stays optional.

**The OCR language** is asked only when it matters ([The home page](home-runs.md#language-of-the-scanned-pages)). Scans in the Latin script, or with no text to read, are OCR'd as English, as before. That includes a Hawaiian, Ilokano or Bikol scan; lost ʻokina or kahakō are caught at "OCR Text Approval", and the catalogue language (part 2 of #37) is the later fix.

**Before the first review.** A run stopped before its first review gets a page with **Open the Review Page** ("Waiting for Review"); `python3 app.py <run>` opens it too. Until the first apply, only that page, its state and those buttons answer for the run: no evaluation, downloads or files. See [Review step](review-page.md#steps).

**"Finish Review" applies at once.** When the review page closes with its review written, the app starts the apply once, in the run's own folder, with the original PDF looked up at that moment. The run page shows "Applying the reviewed decisions", or "Waiting to Start" while other runs hold the places. For a PDF in a batch, the apply writes the batch's summary again after it.

There is no **Apply** button. When the apply can't start (the original PDF is gone, for example) or fails, the page says why, with **Try Again**. While a Try Again is waiting or running, the page shows it applying; if it fails too, the page shows its own reason (the page follows the newest apply). A review finished before this change, never applied, still offers **Apply the Reviewed Decisions**.

**"Try Again" after a failed apply is offered only for the newest session.** A session whose apply failed stays finished, and the panel offers **Try Again** for it. If a later session is then reviewed and applied, the earlier one is never offered again: applying it would replace the newer result with older decisions.

### The flow

**Review Again** → the review page opens by itself → **Finish Review** → the run page, showing apply, verify and report with their times → when they end, "New result ready" and a **Show the New Result** button, which loads it. The page never reloads by itself.

The review page also has **Back to the Run Page**, which leaves the review open. It checks each choice as it is saved, and refuses **Finish Review** while one needs fixing (see [Checks as you go](review-page.md#checks-as-you-go)). So a choice the check doesn't accept is fixed on the review page, not dropped at apply.

**The same from a terminal** (not shown on the page), from `pipeline/`: `python3 review_workorder.py <run folder> --reopen [--from N|ai]`, `--sessions`, `--apply` (see [Reviewing again](review-again.md)).

### Every page has a way back

The browser's Back button is never the only way back:
- `/run/<run>/review.html` (which the "replaced by" note in a previous result's file links to) goes to the run page.
- **A previous result** (`reviews/versions/<id>/review.html`) shows a bar: "You're viewing a previous result (session N)", with **Back to the Current Result** and **Review Again from This Session** (for the result applied without review, **Start Over from the AI's Decisions**). The button starts the review and goes to the run page, which follows it. The file's own "replaced by" note is hidden in the app (the bar says it); it stays in the file.
- **review.md** opens inside a page with **Back to the Run Page** (and, for a previous result, its dashboard), and **The Plain File**.
- **A PDF** opens in the browser's own viewer; its tab or Back button returns.

### Wording on the pages

**Plain words.** The pages name no folders, files or command-line options. The one command a person may need is starting the app again: when the app is not running, the page says to open a terminal in the project's pipeline folder and type `python3 app.py`.

One exception to "no file names": wherever a PDF is named, "Source PDF: <file name>" follows its display name ([The home page](home-workspace.md#the-home-page)).

**Capitalization** on the panel, the review page and `review.html` (not `review.md`):
- Headings, card titles, fold toggles, table column headers and buttons are in Title Case ("Review of the AI's Decisions", "Current Result: Session 5", **Previous Jobs**).
- Articles, conjunctions and short prepositions (a, an, the, and, or, of, to, in, on, for, by, from, with) stay lowercase unless first or last.
- Words in parentheses are left as written, so a qualifier stays lowercase ("Pages (optional)", "veraPDF (WCAG rules)"), and a session there is named "Session N" ("Review Again (from Session 4)").
- Messages, explanations, status lines and list items are in sentence case.

**Messages that name a button, view or section** put the name in quotes, as it appears on screen: 'press "Continue Review" to carry on'.

## Accessibility of the panel

The panel follows WCAG 2.1 AA, the project's standard:

- **Keyboard:** every action is a real button or link, works by keyboard, and shows a visible focus.
- **Status:** always said in words, never by color alone. A failed job's card says "Failed".
- **Messages** (for example "Session 9 is discarded: …" or "The review page is closed. …") have a **×** button named "Dismiss message"; the × itself is hidden from screen readers. Dismissing moves focus to the **Run Actions** heading, and any other panel button clears the message too. A message has a neutral box; an error keeps its red border, and has the same button.
- **Announcements:** one polite live region, and only for a step change, a job's start, "the review page is ready", and a job's end. It never reads out log lines.
- **Status words:** a review closed with **Stop reviewing** says "Stopped (the session stays open)".
- **The panel's place:** it comes after the report's own heading and before its content, so the page's h1 comes first.

### In-page links and focus outlines

In-page links move focus, so a screen reader's cursor follows. The skip link ("Skip to the content") focuses the page's `<main>`. The report's § and Details links, its page map, and the review page's side list focus their target.

Headings, sections and messages focused this way show no outline: a heading or message the page moves focus to never does. The row a Details or § link lands on in the report keeps a thin blue outline (2 px), so a sighted reader sees where it landed. Tab focus on buttons, links and fields always shows an outline. The page map is unchanged.

### Where focus goes

Focus moves only after your own action:
- after a click: to the new job's heading, or to the refusal message
- after an upload: to the first new PDF's name box, or to the message when a file failed
- a pop-up (New Run, New Batch) takes focus into it, and gives it back to its opener when it closes
- after a "⋯" menu's dialog or name box closes: back to that "⋯"
- after Finish: to the apply's heading on the run page
- after **Show the New Result**: to "Current Result"

When a job ends in the background, it is announced ("New result ready" when an apply has made one), and focus stays where it is.

One exception: when a run started with **Start Remediation** stops for review, focus moves to **Open the Review Page**, but only when it is still where the page put it after the click, and no key or click has happened since ([The home page](home-runs.md#a-single-run)).

**Going on by itself:** only one thing does, the review page after your own **Review Again**, and only within 30 seconds of the click while you have not pressed a key or clicked since. Otherwise it says the page is ready and shows **Open the Review Page**. A new result never replaces the page you are reading.

The panel checks the run every second while a job runs or a review is open (every 5 s otherwise), and is redrawn only when what it shows changed. So a review page saving its draft never replaces the buttons under the mouse, or a text selection.

## For developers

### Endpoints

- **`/run/<run>/download?what=pdf|record&v=current|<version>`** gives a version's remediated PDF or record ZIP, named by its state. The version must be one of the run's own ([Accessibility evaluation and release](shipping.md#downloads)).
- **`POST /api/run/<run>/ship`** is "Mark as Shipped" (`{by, note, shown_sha256}`; refused unless the gate is open), through `review/manual.py` `ship()`. Nothing in `release/shipped/` is served; the accessibility statement was dropped (see [Accessibility evaluation and release](evaluation.md#the-accessibility-statement-dropped)).
- **`POST /api/run/<run>/remove-older-pdfs`** is "Clean Up Space" (`{by, chosen: [{id, sha256}]}`: the versions selected, each with the hash shown; refused when none is selected or one changed), through `review/prune.py` in the app's process.
- **`POST /api/run/<run>/upload`** takes the edited PDF's own bytes (`Content-Type: application/pdf`, `X-Pdfrem-Upload: 1` as "Upload a PDF" sends, its name percent-encoded in `X-File-Name`, at most `upload_max_mb`; it must start with `%PDF-`). It is streamed into `uploads/.edited/`, and answers `{file, sha256, size}`. An upload that stops partway leaves nothing.
- **`POST /api/run/<run>/bring-back`** is **Bring Back an Edited PDF** (`{file, by, note}`: a file name from `uploads/.edited/`'s own listing, never a path; or `{resume: label}`, **Start** for an edited copy never run), queued as a job. It answers 409 with the reason before anything runs.
- **`/run/<run>/checks`** is the Accessibility Evaluation page ([The accessibility evaluation](evaluation.md)). `/run/<run>/checks/` (with a slash) redirects to it, so the page's return after "Record" (relative to its own address) never lands elsewhere. `GET /api/run/<run>/checks` is its data, and `POST /api/run/<run>/checks/draft` and `/checks/record` its saves (JSON from the app's own pages only, as every POST).
- Every POST's `Content-Length` must be digits and at most 65,536 bytes, checked before reading (411 or 413 otherwise).
- `/run/<run>/ocr` stays reserved: OCR text is approved on the review page, or on the OCR-only page (**Review OCR Text**), both on the review server.
