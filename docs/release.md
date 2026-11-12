---
title: Accessibility evaluation and release
parent: Review and ship
nav_order: 5
has_children: true
has_toc: false
---

# Accessibility evaluation, status and release

This part of the docs explains what has to happen before a remediated PDF ships: the accessibility evaluation a person records by hand, the PDF's status, and how a version is downloaded, marked as shipped, withdrawn or cleared.

- [The accessibility evaluation](evaluation.md): evaluate the PDF with PAC 2026 and a screen reader, record the results, and see how "Ready to ship?" is answered.
- [Downloads and shipping](shipping.md): download a version and its record, mark it as shipped, withdraw it, and free disk space.

## The status

The status follows the requirements in ["Ready to ship?"](evaluation.md#ready-to-ship).

| Status | When |
|---|---|
| **Not Ready** | a requirement among the first three is unsatisfied |
| **Pending Evaluation** | those three are satisfied; the evaluation is not completed for this version |
| **Ready** | all four are satisfied |
| **Shipped** | a shipment exists that is not withdrawn; the status is about the shipped copy |

- **"· N issues noted"** follows any status whose version has Fails in its evaluation: "Pending Evaluation · 1 issue noted", "Ready · 2 issues noted", "Shipped · 2 issues noted". After a shipment they are the shipped file's.
- **A Shipped PDF** has Ready's green border on the card. summary.html counts the two apart: "Ready: N · Shipped: M · Pending Evaluation: P".
- **Withdrawal:** the status falls back to the latest shipment not withdrawn; with none, the statuses before shipping apply.
- **Where the status is shown:** review.md's Overview (`**Status:** …` above "**Ready to ship?**"), review.html's card, summary.html's Status column, and the evaluation page ("Overall Status") and the strip.

**After a shipment, a second line** says what comes next:
- "Newer version: Session 7 finished, not applied" (being applied, or its apply failed)
- else "Newer version: Session 7 being reviewed" (an open session, also while the shipped file is still the current one)
- else, when the current file is not the shipped one, that version's own status: "Newer version (Session 7): Pending Evaluation"
