---
title: Finding your way
parent: The home page (new runs and batches)
grand_parent: Review and ship
nav_order: 1
---

# Finding your way around the app

This page explains the home page's lists of PDFs, runs and batches, how to move between the app's pages, and how to move something to the Trash. Internals are at the end, under [For developers](#for-developers).

## The home page

The page is titled "PDF Accessibility Remediation". Its sections are cards like the run page's; each card's top border is the accent blue, and the status pills keep their colors. The review page's "seen" cards use the same blue.

- **Runs in Progress:** shown only while a job runs or waits to start. Each has its PDF, its run name, its step or "Waiting to Start", and **Open**, kept current while the page is open. A job that ends is announced; focus never moves by itself. To keep this light as the jobs add up (#93), the page asks the app only about jobs whose status can still change (waiting, running, waiting for a new estimate, or stopped without finishing while it may still be running) and about the ones it last saw (`/api/jobs?active=1&seen=…`): every 2 seconds while a job runs, else every 5, as before. Its first answer comes with the page (a JSON data block, `hm-first`: what that request would return for a page that has seen no job), so the list is drawn on first load with no "Loading…" (#93); later answers are asked for as before.
- **Upload a PDF:** a drop zone to add PDFs, and the list of PDFs added (see [Upload a PDF](home-runs.md#upload-a-pdf)).
- **My Workspace:** your single runs and batches (below).

### My Workspace

A switch between **Single Runs** and **Batches**, a search (by PDF or run name; by batch name), and a filter by status group with each group's count.

- **A single run's row:** its run name, the PDF's name, "Source PDF: <file name>", its status pill, **Pages**, **Date Created**, **Open** and a "⋯" menu.
- **A batch's row:** its name, its status pill with its state in words beside it ("0 of 2 Ready or Shipped"), Pages (the total of its PDFs; "(1 PDF not counted)" when one has no count), Date Created, **Open** and a "⋯" menu.

There is no AI Cost column: a run's cost is in its run page's header, a batch's on the batch page. Rows come 25 at a time (**Show More Runs** / **Show More Batches**). Listing a run never changes it.

The switch, a filter, a search and **Show More** swap the table in place, with no reload and no jump to the top. The address keeps the choice, so refreshing keeps it. Focus stays on the control used, and the new count ("3 batches · In Progress") is announced. Enter in the search box keeps the view shown, and after the table is swapped the caret is at the end of the search text, so typing goes on where it stopped (#93).

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
- Three pages have it in their own bar, after the bar's other buttons, instead: the Accessibility Evaluation page (after "Back to the Run Page"), a previous result's dashboard (after "Review Again from This Session") and review.md in a page (before "The Plain File"). Those pages have nothing above the title, which starts at the top.

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

## Move to Trash

**Move to Trash** is in the "⋯" menu of each single run and batch in My Workspace, and of each PDF in the PDF list. It is also on the batch page, for the whole batch or the PDFs ticked in its dashboard (**Move Selected to Trash**). Every move asks first, naming what goes in plain words.

Each confirmation ends with what happens (#93): "This PDF will be moved to the Trash on this computer and cannot be restored through the app." (for a run or a batch: "This folder will be moved to …"; for several PDFs ticked in a batch: "These folders will be moved to …"). After the move the home page says "Moved to the Trash: <name>." (the PDF's, run's or batch's name). After **Move Selected to Trash** moves only some of a batch's PDFs, the batch page says it instead, naming each PDF moved: up to three, then "and N more" ("Moved to the Trash: A, B, C and 2 more."); the message takes focus, as the home page's does. The app restores nothing: a PDF is used again by uploading the same PDF again with **Choose PDFs**, where the app finds it by its content (sha256).

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
- ""Review Again" will require this PDF: it can be uploaded again with "Choose PDFs" on the home page." (a tagged PDF whose review reads this very file: its review record names the original itself)
- ""Review Again" already doesn't work for this run: … Moving this PDF doesn't change that" (its own intake copy is missing, or its record doesn't say which PDF it was made from, so putting the PDF back wouldn't help)
- "Applying its reviewed decisions will require this PDF: it can be uploaded again with …" (waiting for its first apply)
- a run before its result gets no line

Those runs stay. A run that needs the PDF says on its page: "The original PDF was moved to the Trash. "Review Again" requires it: to continue, upload the same PDF again with "Choose PDFs" on the home page." "Start Remediation", refused for a PDF moved to the Trash, says the same, ending "then try again". The samples folder is never offered.

**A move is refused,** and nothing moves, while anything affected is processing, waiting to start or for a new estimate, has a review page open, or sits between "Finish Review" and its apply. A PDF is also refused while any job's command names it.

Where the items go, and how whoever looks after the app can put one back by hand: [The app](app-setup.md#move-to-trash).

## Clearing a shipped PDF

After a PDF has shipped and its record ZIP was downloaded, its run page may offer **Clear This Book's Files** to free space. It is optional, never suggested: see [Accessibility evaluation and release](shipping.md#clearing-a-shipped-book). It keeps the run's own original PDF (`source/`): a cleared run still holds the full PDF it was made from.

## For developers

### Where the app keeps names and the home list

- Display names of runs and batches: `runs/.app/run-names.json`.
- PDF names: `runs/.app/book-names.json`, by sha256, with each earlier name kept.
- The home list's cache: `runs/.app/home-index.json`, by each run's path and the times its records changed. Only the rows whose records changed are read again.

A finished run's status in the list is worked out from its record and `release/`, without hashing any PDF; the run page does the full check. Names are applied when the list is read, so a rename keeps the cache. The app refreshes the list in the background whenever a job ends and after a move to the Trash, so a click on **Home Page** is served from a ready list.

Before names were applied at read time, a rename threw the whole cache away. On 750 runs and 227 batches, the next home page then took 3.0 s to rebuild, against 0.03 s warm; now it takes 0.05 s after a rename.

The "⋯" menus are menu buttons (`aria-haspopup="menu"`, `aria-expanded`). Buttons keep the keyboard's focus ring with `:focus-visible`. The list's view is kept in the address with `history.replaceState`. The side list's choice is kept in a cookie and local storage, and the page layout is one CSS block in panel.css. Colors come from review/palette.css.

### Test mode

For the app's tests only, three keys are accepted only from `--config`, never from a settings file:
- `test_reply_dir`: "Start Remediation" runs `REPLY=<dir>/<short name>.txt INTAKE_REUSE=1` instead of a paid request. A missing reply is refused, never sent instead.
- `test_batch_from`: a batch's "Start Remediation" runs `FROM=<label>`, each PDF's saved reply found under `runs/batches/<label>/<short name>/` or `runs/<short name>/<label>/`.
- `trash_dir`: where **Move to Trash** moves things, instead of `~/.Trash`.

Every page then says "Test: saved replies, no AI request". Estimates still ask OpenRouter for prices and credit (free). A batch in test mode skips batch_api.sh's own estimate step and its cap (FROM= does), so only a real batch shows the cap working.

**Saved replies are found by the PDF's file name, not its content.** The short name comes from the file name's stem (`ilokano.pdf` → `ilokano`), so a test PDF must be added through **Upload a PDF** under its original file name. An upload renamed to `ilokano-2.pdf` would look for `ilokano-2.txt`.

A `--config` may also name its own `runs`, `uploads` and `jobs` folders: every job then writes into that runs folder (the app passes `RUNS_DIR`).
