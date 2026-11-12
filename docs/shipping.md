---
title: Downloads and shipping
parent: Accessibility evaluation and release
grand_parent: Review and ship
nav_order: 2
---

# Downloads, shipping and clearing

This page is for library staff releasing a finished PDF: downloading a version and its record, marking it as shipped, withdrawing it, and freeing disk space afterwards. Internals are at the end, under [For developers](#for-developers).

## Downloads

Any version of the PDF can be downloaded at any time, ready or not, from **Available Downloads**. It is on the run page's strip (under "Complete Evaluation") and on the evaluation page, laid out the same on both:
- the heading, which is the list's label
- the list of versions
- the line saying how the chosen version's files are marked (the list's description)
- **Download the Remediated PDF** and **Download the Record (ZIP)**, in a row

**The list** holds the current version and each previous result whose PDF still exists. It decides which version the two buttons give. It never changes what the evaluation records: the evaluation is always for the current version.

The line under it says how the files are marked ('The downloaded files are marked "not ready."'), never their names. A shipped version has no line, because the line above the downloads and its own label already say it was shipped. On the evaluation page, a version that is not the current one adds "Results on this page are recorded for the current version only." to that line.

### File names

The PDF's bytes are never changed, only the name it is saved under:

| That version | PDF | ZIP |
|---|---|---|
| Not Ready or Pending Evaluation | `<book>_session-6_not-ready.pdf` | `<book>_record_session-6_not-ready.zip` |
| Ready | `<book>_session-6_not-shipped.pdf` | `<book>_record_session-6_not-shipped.zip` |
| Shipped (the shipped file) | `<book>.pdf` | `<book>_record_shipment-2.zip` |
| A withdrawn shipped copy | `<book>_shipment-1_withdrawn.pdf` | `<book>_record_shipment-1_withdrawn.zip` |
| A previous version | `<book>_session-5_previous-version.pdf` | `<book>_record_session-5_previous-version.zip` |
| No review | `<book>_no-review_not-ready.pdf` | `<book>_record_no-review_not-ready.zip` |

`<book>` is the remediated PDF's name without ".pdf", made safe for any computer (see [Download names](#download-names)). The session's number is used, never its name.

### The record ZIP

The record ZIP is for library staff. It holds one folder named as the ZIP, with only:
- the PDF, under its own name
- review.html: the report, with the evaluation's results in it
- han_review.csv, when the PDF has one (review.html sends staff to it). The read-me calls it "passages in Chinese or Japanese a person needs to check, as a spreadsheet".
- `READ-ME.txt`, in plain words (below)

It never holds review.md or `evaluation-results.json`: they stay in the run folder and in `release/shipped/NNN/`, which keep their full set. It never holds record.json either, because that holds the AI's raw reply.

The ZIP's review.html keeps only the links that work inside the ZIP. Its header's link to review.md is dropped, and any other link that would lead outside the ZIP (a previous result, a file of the run folder) is left as plain text. Links within the page and to the web stay. review.html on disk is unchanged.

**READ-ME.txt** gives:
- the title and "Source PDF: …" (the original PDF's name)
- the version, and its status. For a previous version it says "previous version", naming the current one.
- each shipment of that file ("Shipment 1, shipped on November 1, 2026 by Kim"; "Withdrawn on … by …: …" for a withdrawn one)
- the number of evaluation results recorded on it
- the run details of that version's own record (below)
- what each file is
- "automated checks are evidence, not legal sign-off" and "the evaluation is a record of what a person found, not a legal certification"

It gives no hash: a file's sha256 is in its record (`document.output_sha256`) and its shipped folder's READ-ME.txt. The run details read, for example:

```
Pages: 437
Remediated: October 26, 2026, at 6:48 AM
AI model: anthropic/claude-sonnet-5.5 · Instructions: workorder_v8
AI cost: $0.256, from the original AI request on October 26, 2026 · Cost per page: $0.0006
OCR and Auto-Tagging: 6 pages are pictures with no text, so no text was added for them; the PDF had no tags and was tagged automatically.
Total runtime: 3 min 52 s (intake 4 s, audit 37 s, AI request (a previous answer reused) 2 s, preparing the review 8 s, applying and checks 3 min 2 s); the review time is not counted.
Software: Python 3.13.9, pikepdf 10.5.1, pdfplumber 0.11.9, pypdfium2 5.7.1, Pillow 13.0.0, fontTools 4.62.1
```

- **The AI cost** is always the request's real cost: for a reused reply, the original request's. It reads "not recorded" only when none is kept anywhere. Any missing value reads "not recorded".
- **OCR and Auto-Tagging** says plainly what intake did, from OCR's own lists of pages: "1 page is a picture with no text, so no text was added for it", "…, so OCR added its text", "7 pages are pictures with no text: OCR added text to 6 of them, and no text was added for the other one", or "every page has text, so no OCR was needed".
- **Then the tags:** "the PDF had no tags and was tagged automatically", or "the PDF's tags held no text structure, so it was tagged again automatically". A tagged PDF, which intake skips, reads "not needed: the PDF was already tagged."; a record with no intake, "not recorded".
- **Total runtime** is the computer's time across the whole run, with its parts in parentheses: intake, audit, the AI call (named "a previous answer reused" for a reused reply: the time of reading it, not the original call's), preparing the review (a run stopped with `REVIEW=1`), and applying and checks. It ends "the review time is not counted". A part with no time kept reads "not recorded", and the total then says "at least".

A version applied from a later review carries the run's steps before the review from the record it replaces, and adds its own applying and checks. A `REVIEW=1` run applied before 2026-11-01 kept only the apply's steps.

### When a download is refused

A download is refused while a new version is being put in place and did not finish, or when the PDF on disk is not the one the report describes. A re-apply under way, or a finished session not yet applied, does not stop a download.

"Which Version Is This File?" (a PDF hashed in the browser and named as a version) was removed from the evaluation page.

## Mark as Shipped

"Mark as Shipped" records that a person published this version elsewhere, for example in ScholarSpace. The app publishes nothing.

**It is offered only when:**
- the current version is Ready
- the PDF on disk is the one the report describes
- no refusal stands: a session finished and not applied, a new version being made, a record out of step
- **this file has not already shipped**, in a shipment that is not withdrawn. The same file never ships twice; after a withdrawal it may ship again.

Beside the button: "Records that this version was reviewed and shipped." Otherwise the strip says why, once:
- "This version was shipped on November 2, 2026 (Shipment 1)."
- or, while a refusal stands, the strip's one refusal line, worded for both recording and shipping: "…so no results can be recorded for it and it can't be marked as shipped."

A version that is not Ready gets no line: the card above says what is unsatisfied. After a shipment, a newer version that becomes Ready is offered again as the next shipment.

**The dialog** says "Records that this version was reviewed and shipped.", with the number of issues noted that ship with the copy, **Shipped By** (required, empty at first) and **Note (optional)**. It doesn't ask where the PDF was published. After it: "Marked as shipped: Shipment 1."

From the terminal: `manual_checks.py <run> --ship --by NAME [--note …]`.

### What shipping keeps

Shipping writes `release/shipped/NNN/`, whole or not at all. The folder holds:
- the PDF (a copy)
- review.md and review.html as they read once shipped; the copy's page says "Shipped copy (Shipment 1, …)"
- han_review.csv
- `evaluation-results.json`: the results on that file, with their issues
- `READ-ME.txt`, in plain words: the shipment's line ("Shipment 1, shipped on November 1, 2026 by Kim"), its status, what each file is, and the PDF's fingerprint. It is written once: a later withdrawal is said in a downloaded ZIP's read-me, not in this one.
- record.json, for the local archive only, never served and never in a ZIP

If anything fails before the folder is complete, the folder is removed and the pages redrawn, so nothing says Shipped.

Shipment numbers are never reused. A shipment is "Shipment N" in Title Case wherever a person reads it (the message, the strip, review.html, review.md, the read-me, "Available Downloads"); file names keep `_shipment-N`.

### After shipping

- The status reads "Shipped" (with "· N issues noted"), with Ready's green border.
- review.md's evaluation section names each shipment.
- review.html's Shipments list names each shipment, by whom and when.
- The shipped file downloads under its plain names.
- A shipped copy that a newer version replaced is listed in "Available Downloads" as "Shipment 1, shipped on …".
- A previous result's own page reads "Previous version (the current version is Session N)", naming its shipment when it was itself shipped.

**A shipped PDF that later changes on disk** keeps "Shipped", with "The current PDF has changed since this report was made." beside it, and never Ready's green. Mark as Shipped stays refused until it is resolved. The shipped copy in `release/shipped/` is untouched and still downloads.

## Withdrawal

Withdrawal is from the terminal only:

```bash
manual_checks.py <run> --withdraw-shipment N --by NAME --reason "…"
```

- It writes `withdrawn: {by, date, reason}` (local time, to the second) on that shipment; nothing is deleted.
- It is refused for an unknown shipment, one already withdrawn, or without a name and a reason.
- **The status** falls back to the latest shipment not withdrawn, and with none left to the statuses before shipping.
- **"Available Downloads"** still lists a withdrawn copy, marked "(withdrawn)", named `_shipment-N_withdrawn`.

## Clean Up Space

Every version is kept as a real PDF; there is no rebuilding from work orders. Repeated reviews keep one full PDF per version (13 MB and 96 MB for two earlier test books). So the run page offers a **Clean Up Space** button under Session History when there is something to remove, with no line under it.

Its dialog explains: "Deletes the PDF files of the previous versions you select to free up space. Their records and decisions stay in "Session History." The original AI-generated version is always kept."

**Never removed:**
- the current version
- the AI's own version (`reviews/versions/ai`: the result before any review, the evidence of what the AI did)
- any version with an evaluation result on its PDF
- any shipped version, withdrawn or not

**What goes:** only the PDF. The version's record.json, review.md and review.html, and the session's work order, stay. The version's page says the PDF was removed, whenever it is built.

**The dialog** has a checkbox per removable version, with its session, date and size. Any number can be selected; nothing is selected at first. It shows the selection's count and size, "Removed By" (empty at first), and "This can't be undone."
- The remove button names the count ("Remove 2 PDFs"), and is disabled while none is selected.
- Only the selected versions go, and only if each is still offered with the PDF it showed. If one changed meanwhile, nothing is removed.
- It is refused while a review is open or a new version is being made.
- The deletion is permanent. Escape or Cancel closes it, and focus returns to the button.

**Session History** keeps every row; a version whose PDF was removed is marked "PDF removed". **"Available Downloads"** lists only versions whose PDF exists.

**From the terminal:** `python3 review_workorder.py <run> --remove-older-pdfs` lists them, with their session numbers. `--remove-older-pdfs 3 5` names the sessions to remove (a dry run); add `--yes --by NAME` to remove those PDFs only. `--yes` without sessions is refused: nothing is removed unless chosen.

## Clearing a shipped book

**Clearing is optional.** A shipped PDF that is never cleared stays a full run, reachable from the home page at any time: **Review Again**, a newer version shipping as Shipment N+1, withdrawal, the downloads and the evaluation all keep working.

**Clear This Book's Files** is offered only on the run page, and only once its gate is open. The home page never prompts for it, counts it, highlights it or lists it as a to-do, and no status or message suggests that a shipped PDF should be cleared.

**The gate** is open when:
- the PDF is **Shipped**: its current PDF, hashed now, has a live (not withdrawn) shipment's hash
- the **record ZIP of that version was downloaded** in full. That the person kept it is not known.
- the **shipped copy** in `release/shipped/NNN/` still has the shipment's hash
- **nothing is in progress:** no job of the run, no review lock, no promotion or re-apply, no open session, no finished session waiting to be applied
- it is not cleared already

**The dialog** lists what goes, with sizes, and what stays, then asks for "Your Name" (never prefilled) and "Type CLEAR to Confirm". Afterwards the browser goes to the home page, where the row reads "Cleared on November 5, 2026 · shipped as Shipment 1".

### What is deleted

Only PDFs and images at named places, never a whole folder:
- the run folder's finished PDF, only when its hash is the shipment's (the shipped copy keeps the same file)
- `_intake/intake.pdf`
- every `reviews/versions/*/` PDF, including the AI's own version (`ai`) and versions with evaluation results. After shipping, the AI's decisions (`workorder.ai.json`, the sessions' work orders) and the records are the evidence; the PDF is a by-product. Before shipping, **Clean Up Space** still keeps the AI's version.
- figure crops and page images (`.png`, `.jpg`, `.jpeg`) under `_audit/` and `reviews/_audit/`

**What is kept:**
- every `.json`, `.md`, `.html` and `.csv` file: record.json, review.md, review.html, han_review.csv, the sessions, the digest, intake's record and the OCR verdict, `release/*.json`
- all of `release/shipped/NNN/`
- the original in `samples/` or `uploads/`, which is never touched, and the run's own original PDF (`source/`)

A clear that stopped partway shows on the run page, and **Clear This Book's Files** finishes it: each file still there is deleted only when it is the one planned; one that changed is kept and named.

### After clearing, the run is read only

From the app and the terminal alike, these are refused ("This book's working files were cleared after it shipped …"): Review Again, Apply, an OCR verdict, the evaluation's Record, Mark as Shipped, Clean Up Space, and New Run from the Saved Reply.

- Withdrawing a shipment still works.
- **Available Downloads** lists the shipped copies (built from `release/shipped/NNN/`) and no current version.
- `batch_api.sh` with `FROM=` refuses a cleared run as its source too ("cleared after shipping: its saved reply can't be reused"), since its intake result is gone.

A rebuild from `workorder.ai.json` after clearing would run on today's code, and would not be the original file. To work on the PDF again, start a new run from the home page.

## For developers

### Downloads

- **One moment per download:** every file is opened under the record lock (a page waits at most 5 s), then the lock is released and the bytes are sent. A new version put in place meanwhile never mixes into a download.
- **A download that fails** after opening its files closes them before the error goes on.
- **The PDF's own name**, as its record gives it, must be a plain file name: no "/", "\", "..", leading dot or control character. Otherwise the current version is refused ("This version's file name in its record is not a plain file name …"), and a previous version or a shipped copy is not listed. So a hand-edited record.json never makes a ZIP entry or a path outside its folder.
- **The record ZIP** stores the PDF without compressing it again. It never holds digests, crops, `reviews/`, `_intake/`, `release/drafts.json` or dot-files. It is built as it is sent, and never kept on disk.
- **The ZIP's review.html:** when the app draws the ZIP's review.html, it also drops an older page's statement links and "where:".
- **The read-me's run details:** the AI cost comes from `lib/origin.py`. A shipped copy's run details come from its folder's record.json, which is never zipped. The stop at the review keeps its step times in `timing.json` for the second call to add to, and an AI request made by the run counts with the seconds `decide.py` kept.
- A refused download while a new version is being put in place means `reviews/promoting.json` exists.

#### Download names

`<book>` is made safe for any computer: NFC; control characters dropped; `< > : " / \ | ? *` and `;` replaced by `_`; no leading or trailing dot or space; at most 150 UTF-8 bytes. It is sent with `Content-Disposition` (RFC 6266/5987: an ASCII fallback and the UTF-8 name).

The list's arrow is drawn by the app's stylesheet, centered on the list's height in the page's text color (the browser's own sat high). With forced colors (Windows High Contrast), the browser's own list comes back.

### Clearing

The gate is `review/clear.py`, read when the page is drawn and again under the locks. The app adds a line to `release/downloads.json` after the ZIP's last byte is written. Locks are taken in Clean Up Space's order: `reviews/.lock`, which refuses, then the record lock. Read-only after clearing is `review/sessions.py` `not_cleared`, read in either state of cleared.json.

**The record:** `release/cleared.json` lists every deleted file with its path, size and sha256 (`versions/ai`'s included). It is written as `planned` before anything is deleted, and marked `done` after, with the space freed and the code's commit. To finish a partial clear, each planned file still there is hashed and deleted only when it matches the plan.

**A record is never an image or a PDF.** Under `_audit/` and `reviews/_audit/`, the records (the digest, the full text, dryrun.json, the OCR-word list) are `.json` or `.csv`. Clearing removes only the PDFs and images there ([Files](files.md)), so a later feature cannot lose a record by its choice of folder or file type, as long as it keeps that rule.
