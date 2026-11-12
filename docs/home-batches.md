---
title: Batches
parent: The home page (new runs and batches)
grand_parent: Review and ship
nav_order: 3
---

# Batches of PDFs

A batch runs several PDFs together, with one estimate and one "Start Remediation". This page explains how to start, save and follow a batch, how many runs go at once, and how runs and batches are named.

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
