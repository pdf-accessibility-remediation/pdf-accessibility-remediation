---
title: Reading order on the review page
parent: Reviewing the work order
grand_parent: Review and ship
nav_order: 4
---

# Reading order on the review page

The review page groups everything about the order a screen reader reads the PDF in. This page explains that group, the section moves a reviewer can approve or add, and what to do when the pipeline cannot fix the order. Internals are at the end, under [For developers](#for-developers).

## The reading-order group

Group 5 of **Check these first** holds:
- the section move (`move_section`), with the pages it touches
- elements moved to the start (`move_to_document_start`)
- orphan text added to the tags (`adopt_orphans`)
- the captions decision (`captions`), which ties each caption to its figure and so moves it in the reading order
- the **reading-order checks:** findings in the original's reading order that no decision answers (below). They can only be marked **Seen**, with a note; nothing is applied.

The group opens with the reading-order panel and is always listed, so a PDF with nothing in it says so ("5. Reading Order (0)").

### Reading Order in the Original (Before Changes)

This panel is a fold at the top of group 5 in **Check first**, and at the top of the reading-order decisions in **All** (the first of "Reading order" and "Reading order check"). **Not reviewed** does not show it, because every finding left there is a card.

Its heading says how many findings there are to check ("3 findings to check"). Inside are a short explanation, then the findings in sentences, each with a link to its card. The kinds of finding follow.

#### A section read out of its printed place

…that no decoration rule removes. A section is out of place when it does not fit the longest run of its sibling sections that reads in page order (the run covering the most pages). So a one-page running-head story read before the chapter it sits in is flagged, not the chapter.

A child section is never compared with the section around it, and a Div around a figure or a note is not compared ("placed where the text refers to it"). Each such section gets a card, for example a cover that is a top-level Article read last.

#### Sections the AI's decisions take care of

Three kinds of out-of-place section are not findings, while the decisions that take care of them are not rejected:

- **A one-page section every text run of which is matched by one of the AI's text rules.** One rule can match it all, or several together. In one earlier sample, a notes running head's page number ("186") is matched by one rule and its title ("Notes to Pages 7–11") by another. Once the rules are applied, a screen reader skips it.
- **A section made only of captions in the AI's captions style (and figures).** `apply.py` ties each caption to its figure, so it is read with the figure and never compared.
- **A section out of place only because of siblings the rules remove.** Once they are gone, it is read in its place. In one earlier sample, an About the Author section (PDF 254) was read after a block of stray letters on PDF 255. The letter rules remove that block, and the rule cards say they put About the Author back in its printed place. review.md, after the changes, finds it in place.

These get no card of their own. Each rule's card says which sections it removes ("This rule, alone or with the AI's other rules, removes 2 sections …"), and the captions decision's card says which it ties to their figures. In one earlier sample, all 24 flags were such sections.

**If you reject a rule or the captions decision, the page lists the sections it no longer takes care of as findings again at once.** A section that two rules each remove whole (stray letter blocks, for example) stays removed until both are rejected. A section uncovered this way has no card; note it on the decision's card.

#### Pages where the text jumps back up the same column

…two or more times in reading order: the same page check review.md makes after the changes. Each page gets a card with its image. The pipeline cannot change the order within a page, so the card asks for a note, for example a fix by hand in Acrobat.

#### Figures the executor moves back to their page

`apply.py` runs a step that moves figures back to their page (`fix_figure_order`), unless the work order turns it off for the PDF. The figures it would move are worked out at the review stop by a trial run of `apply.py` on a copy (see [The trial run](#the-trial-run)).

One card, **Figures Moved**, lists them as review.md does ("Figure on PDF p. 81 (printed 72): read after PDF 139 now; after PDF 82 after the changes"). Two earlier samples had 15 each.

This card is the decision for the step:
- **Approve** has the figures moved back.
- **Reject** leaves every figure where it is read now (`fix_figure_order: false`), for example in a plates section the text refers to by number.

When the AI turned the step off, the card says so: Approve keeps it off, Reject turns it on. A run with no trial run lists `fix_figure_order` under Other decisions instead; rejecting it there turns the step off too. Runs prepared before this card existed have no card.

A change you make on the page (for example rejecting the captions decision) can change which figures move; review.md lists the moves actually made.

#### Small sections read late

These are one or two pages, read more than 5 pages after their printed page because an earlier sibling already reached that far: a figure caption read after the chapter it sits in, for example. Overlapping stories are normal in InDesign books, so this is not a failure.

One card, **Small Sections Read Late**, lists the first 12 and the count of those the AI's decisions do not take care of. It says how many more they do take care of (text the rules remove, captions tied to their figures); those are no longer read late after the changes. In one earlier sample: 2 listed (the series editors on PDF 3, Table 1 on PDF 27, the same 2 review.md lists after the changes), 27 removed by rules, 15 captions tied.

#### The list of sections

Below the findings is the list of sections in the order a screen reader meets them, indented by nesting, with their pages and first words. By default it shows only the sections named in the findings, the section the AI moves and the place it lands.

**Show Every Section in the Book** shows all of them, each finding written out ("Read out of place: it is read between PDF 3 and PDF 22."), with a link to the rule that removes it where one does. Select a row to see its first page.

This is the order before any change. Figure moves and added orphan text happen in `apply.py`, after the review, and the final order is checked in `review.md` (WCAG 1.3.2). When the AI moves a section, its row and the place it lands are marked, and the marks follow the section move card (approved, rejected, changed, not reviewed).

A PDF whose tags have no sections says so. Its page-jump findings still get cards, and review.md's page-by-page 1.3.2 check still covers it.

### Reading-order check cards

These cards say what was found and what you can do. Mark each **Seen**. The note you write (for example "move it before PDF 255 by hand in Acrobat" or "fine as it is") is recorded with your review, in `review.md`'s "Reviewer notes".

"Reviewer notes" names each note by its card ("Text on PDF 10 jumps back up the page (`reading_order:jump:10`): …"), on any card, not only these. A note on something you added is named "Your addition: …".

Finish counts these cards as unreviewed until they are marked. A choice on one carries to a later session like any other. The out-of-place and page-jump cards link to [Fixing the reading order by hand](#fixing-the-reading-order-by-hand).

### Section moves

The AI can ask for up to 3 section moves. There is one card per move, made by the executor in order: `move_section`, then `move_section:1`, `move_section:2`. Each card's preview is worked out on the order the earlier moves leave, as its **Worked Out** row says.

**The preview** shows the sections around the move now and after it, worked out with the executor's own match on the original's tags. It also shows how many sections in the PDF are read away from their place before and after.

The preview leaves out the blocks the text rules remove: `apply.py` removes them before it moves sections, so a move onto a removed block, or of one, is refused. `apply.py` matches again on the file it edits, so this is a preview: review.md says where the executor actually put the section, and says so if that differs from the preview.

**When the executor would refuse the move,** the card says so, and names the text rules when they are the reason. The executor refuses when no section, or more than one, lies inside the pages, or when no section holds pages both before the range and from the target page on. Rejecting such a rule keeps its blocks, so the move can work again: the preview follows your rule decisions within a second (with the auto-save).

**Change** gives three numbers: the pages, and the page to read before. The preview for them is worked out the same way within a second. A card you are typing in is redrawn once you leave it.

**Trial Run** on the AI's move card says what the review stop's trial run of `apply.py` did with the move: where it put the section, or why it refused it. It is the most exact answer, so when it differs from the preview, the card says the trial run is what will happen. It used the AI's decisions as written, so it is hidden once you change the move or reject a text rule.

#### Adding a section move

While the work order holds fewer than 3 section moves, an out-of-place card that no move of the AI's covers has **Add a Section Move**. It opens **Add a decision** with that section, a suggested page to read it before, and the same preview the AI's move card has. The suggestion is the first page of the next sibling that reads in page order, leaving out blocks the rules remove.

It is offered only when that preview shows the executor can make the move. The executor moves a section within the section around it, before a page another section of it starts on. So a section at the top of the tree (a cover, for example), or one that belongs before everything else in its section, cannot be moved this way, and its card says so.

Change the numbers on the added card: its preview follows within a second (with the auto-save). An added move is made after the AI's, so its preview is worked out on the order they leave. When the AI's move covers the section, the card links to that move instead. With 3 moves already, it says to reject or change one first.

### The trial run

At the review stop, the pipeline runs `apply.py` once on a copy, with the AI's decisions as written and the figure step on even when the AI turned it off. It records the figures the step moves, and what became of each of the AI's section moves (the move cards' **Trial Run** row). It uses no AI, and takes as long as the apply step: about 2 minutes for a 250-page PDF. `REVIEW_DRYRUN=off` skips it.

A later review of the same PDF (**Review Again**) reuses that trial run's result while nothing it depends on has changed, so the page opens without the wait and shows exactly the same. It depends on the PDF, the AI's decisions, the pipeline's code, the Python packages and Tesseract it runs with, and the settings `apply.py` reads.

A run applied from the AI's own decisions without a review stop keeps its apply's own figure and section moves the same way (#93): its apply is the same `apply.py` on the same PDF and decisions, so it found exactly what the trial run would. Its first **Review Again** opens without the trial run too. Not when the AI turned the figure step off for the PDF (the trial run has it on, the apply had it off), and not for a run applied after a review or re-applied (they applied other decisions).

After any of these changes, for example after updating the pipeline, the trial run is made again; one that failed or was skipped is always made again. `REVIEW_DRYRUN=fresh` makes it again regardless.

## Fixing the reading order by hand

Some reading-order problems are left to a reviewer: a page whose text jumps back up a column, a second section out of place, or a move the executor refuses. Fix them in Adobe Acrobat Pro, on an exported copy of the **remediated** PDF, and say what you did in the card's note. Never fix the original, or a draft PDF from the review page: Finish builds a new file and those fixes would be lost.

- **A screen reader follows the tag order.** Change the order in the **Tags** panel: drag a section's tag to where it belongs. The **Order** panel (and Acrobat's "reflow" order) does not change what a screen reader reads; changing it alone is a common mistake.
- **A section read out of place:** in the Tags panel, find the section's tag (its first words are on the card) and drag it to just before the section it should be read before (the card's "read before PDF …").
- **A page whose text jumps back up a column:** on that page, reorder its paragraph tags in the Tags panel so they follow the printed columns, or select the page with the **Reading Order** tool and retag it in order.
- **Check it:** listen to the page with a screen reader (NVDA on Windows, VoiceOver on a Mac) or PAC's screen reader preview, then rerun veraPDF (see [Verification with veraPDF](verapdf.md)).
- **Bring it back:** make the fix on an exported copy (`handedit.py export`), then bring the edited file back as a new run (`handedit.py import`), so it is audited, verified and reported again and can be evaluated and shipped. A fix made on the run's own PDF changes its sha256, so the accessibility evaluation refuses it. See [Editing the PDF by hand](hand-edits.md).

## For developers

### The section-membership data

Counting a captions-only section as taken care of needs the section's child styles, which the audit records in `fulltext.json`. Runs audited earlier count no captions this way. The full reading order comes from `_audit/fulltext.json`; a run audited before this was added shows the digest's section lines only, with no move preview and no page-jump findings.

Text-rule matching on the page is done as `apply.py` matches: the whole run, the pattern as written or with its spaces optional.
