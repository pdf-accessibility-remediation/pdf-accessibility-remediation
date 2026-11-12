---
title: Reviewing again
parent: Reviewing the work order
grand_parent: Review and ship
nav_order: 3
---

# Reviewing a run again

A finished run can be reviewed again, starting from the AI's decisions or from an earlier session, and a reviewer can also edit the work order without the page. This page covers both. Internals are at the end, under [For developers](#for-developers).

## From the browser

`python3 app.py <run folder>` opens a finished run's page with buttons for everything below: **Review Again**, **Start Over from the AI's Decisions**, **Review Again from Session N**, **Apply Session N** and **Session History**. Each button runs the command shown here. See [The run page](app-run-page.md#the-review-buttons); the commands below work as before.

**Finish** goes back to the run page, which shows the re-apply. When it ends, the page says "New result ready" and a **Show the New Result** button loads it; the page never reloads by itself. Ctrl+C on the review page while Finish is being recorded waits until the review is recorded.

## Reviewing again

A finished run, with or without `REVIEW=1`, can be reviewed again. The page opens with every earlier choice preloaded, you change only what is needed, and Finish applies the reviewed order at once, with no AI request. The result is a new remediated PDF, `review.md` and `review.html`. Nothing earlier is overwritten.

```bash
cd pipeline
python3 review_workorder.py ../runs/teika/rv1 --reopen                # the latest session's choices, preloaded
python3 review_workorder.py ../runs/teika/rv1 --reopen --from 1       # start from an earlier session (--from ai: the AI's decisions)
python3 review_workorder.py ../runs/teika/rv1 --sessions              # every session: who, when, from where, what changed, which is current
python3 review_workorder.py ../runs/teika/rv1 --apply                 # apply a finished session that was not applied (--no-apply, or a failed apply)
```

`--return-to URL` (with `--serve` or `--reopen`) makes the review page go to that page after Finish, and link back to it. The app passes its run page. Only `http://127.0.0.1:<port>/…` or `http://localhost:<port>/…` is accepted.

### What the page shows

The page says which session it is, where it started, how many choices were preloaded, and any that could not be carried. Each preloaded card says which session set its choice.

The page links the current result's `review.html`, served by the review server, because a browser cannot open a local file from the page. It keeps the gap reasons given last time.

### Finishing a review again

**Finish** records the session and applies it: apply, verify and report run in the terminal, each with its time. `--no-apply` stops after Finish.

The current result moves to `reviews/versions/<session>/` (or `versions/ai/` for a result applied without review) only after all three succeed. If one fails, the current result is unchanged and the session stays *finished*: run `--apply` again.

Until the session is applied, "Ready to ship?" says **No** ("the latest review … is finished but not applied"), because the PDF on disk is older than the sign-off.

### One review at a time

Only one review of a run can be open at a time. Ctrl+C leaves the session *open*, and `--reopen` carries on with it.

`--reopen --from N` while a session is open is refused, unless you add `--discard-open`: the open session is kept, marked *abandoned*. `--discard-open` on its own does only that: the open session is marked abandoned and no new one is opened, and the current result does not change.

### The OCR text verdict

There is one OCR text verdict per run (the latest wins), and reopening never rolls it back. It is recorded on its own under **OCR Text** (see [The OCR text](review-ocr.md#the-ocr-text)), not with Finish. Finish keeps a copy of the verdict in force in the session record.

### Older runs and runs that can't be reviewed again

A session is opened and applied only when the input PDF, the kept digest and the AI's order are exactly the ones the run was made with. Anything else is refused, never re-matched (see [Exactness](#exactness)).

**Runs finished before every run kept its digest** need it pinned once:

```bash
python3 review_workorder.py <run> --pin [--pdf <original.pdf>]
```

This re-audits the run's input (free, no AI request), checks the digest against the record, and keeps it. A PDF with no intake result needs `--pdf` (its sha256 is checked). `--reopen` pins first by itself. If today's audit no longer matches (because the audit code, veraPDF or Python changed), the run cannot be reviewed again. More in [Pinning](#pinning).

**When a run cannot be reviewed again** (the pin is refused, or the kept digest cannot be read), the fallback is a new run of the PDF from its saved reply, on today's code. It is not a review of the old result: the audit, the checks and the result are today's.

The app's run page says this in plain words ("This run can't be reviewed again: the pipeline has changed since it was made. A new run of the book from its saved AI reply is needed …"). The commands are in the job's log, and in [Replaying a saved reply](#replaying-a-saved-reply).

**Reviews made before sessions were kept** become session 1, *summary only*: "Session 1 (summary only): 159 approved, 8 seen, no changes; per-decision choices were not recorded before 2026-10-27". When nothing was accepted without review, each card's choice is rebuilt from the recorded changes. Those cards show "approved (inferred)" and point to session 1. Otherwise the new session starts from the AI's decisions, with the summary on the page.

**Batches:** re-applying a PDF in a batch folder rebuilds the batch's `summary.html`; `summary.md` stays as the batch run wrote it.

## Without the page

Edit `workorder.json` by hand (the AI's version stays in `workorder.ai.json`), then:

```bash
python3 review_workorder.py ../runs/teika/rv1 --reviewer "Your Name" [--note TEXT]
```

The edited order goes through the same checks, and `review.json` gets the same record with `method: hand-edit`. Leave `source` as it is, or the command refuses. Bad JSON is reported with its line number. Gaps are printed as warnings and recorded with `--note` as their reason; without a note, the reason recorded is "hand edit: no reason asked for".

## For developers

### Exactness

The decisions point at objects, styles and list positions. A session is opened and applied only when these are exactly the ones the run was made with; anything else is refused, never re-matched:
- the input PDF
- the kept digest (`reviews/_audit/digest.json`), whose fingerprint must be the one `decide.py` recorded as `run.digest_sha256`
- the AI's order

So is a kept digest that this version of the review step cannot read (after a change to the digest's format). A preloaded choice is carried only onto the same decision with the same AI value. One that is not (after a change to how the review page lists decisions) is shown as not reviewed and listed.

### Pinning

`--pin` keeps the digest with `fulltext.json`: the whole texts review.md quotes, so a re-apply quotes them as the first run did.

A run pinned before `--pin` kept `fulltext.json` gets it added by a second `--pin`, but only when today's audit reproduces the kept digest byte for byte. Otherwise nothing is added and the run stays reviewable; a re-apply then quotes the digest's shortened excerpts.

`--reopen` also pins a `KEEP=1` review run, whose digest was not kept.

### Replaying a saved reply

When a run can't be reviewed again:

1. `python3 review_workorder.py <run> --replay-to <new run folder>` copies the run's `_intake/` (`intake.json`, `intake.pdf`) into the new folder. Beside it, it writes the saved reply (`record.json`'s `raw_reply`) as `<folder>.reply.txt`, with a `.meta.json` holding the original model and the OCR-word list the reply was written for (as `FROM=` batches do). It prints the command to run next.
2. That command is `INTAKE_REUSE=1 REPLY=<folder>.reply.txt REVIEW=1 RUN_DIR=<folder> bash run_api.sh <original.pdf> <name> <label>`: no AI request. `INTAKE_REUSE=1` with the copied `_intake/` keeps the intake result the reply was written for. `REPLY=` alone would redo OCR and auto-tagging, and the reply's ids could then name other elements.
3. After the review, apply with the command run_api.sh prints (`RUN_DIR=<folder> bash run_api.sh …`). The apply step does not run intake again (step 4 above), so the copied intake result is the one applied to.

The reply is checked against today's audit as any reused reply is: what no longer fits is dropped and listed. OCR-word readings are used only when the OCR-word list is the same. A reply that predates the fingerprint loses them, and the OCR-words row is a CHECK.

**Summary-only sessions.** When an old review's choices are rebuilt from its recorded changes, each is kept only if the rebuilt order gives exactly the recorded changes and counts.
