---
title: Reviewing the work order
parent: Review and ship
nav_order: 3
has_children: true
has_toc: false
---

# Reviewing the work order before it is applied

With `REVIEW=1`, a run stops after the AI's decisions and before `apply.py`. A reviewer then checks the work order, approving, changing or rejecting each decision, and the run goes on with the reviewed version. Without `REVIEW=1`, runs work as before.

The review is for decisions where a wrong answer still passes every automated check. For example, one of the earlier sample books had its half-title (PDF 2) tagged as P under prompt v7 and as H1 under v8. Both versions pass "exactly one H1"; only a person looking at the pages can tell which is right.

This part of the docs has one page for each task:

- [Using the review page](review-page.md): one review from start to finish, each part of the page, the checks it makes as you go, and the gaps to answer.
- [Draft PDF and sign-off](review-finish.md): a draft of the PDF before finishing, when a PDF is ready to ship, what the report says, and the page's limits.
- [Reviewing again](review-again.md): review a finished run again, or edit the work order without the page.
- [Reading order on the review page](review-reading-order.md): the reading-order group, section moves, and fixing the order by hand.
- [The OCR text](review-ocr.md): approve the text that OCR added, or not.
