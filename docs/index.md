---
title: Overview
nav_order: 1
---

# PDF Accessibility Remediation Pipeline

Claude reads a compact summary of a tagged PDF and returns a **work order**: a JSON file of decisions (heading levels, alt text, what to artifact, language, reading-order fixes). The code carries those decisions out, checks the result, writes a review for a person, and never changes the original. The only paid step is the model call in `decide.py`.

```
original.pdf ─► intake.py ─► audit.py ─► decide.py (model via OpenRouter) ─► apply.py ─► verify.py ─► report.py
                untagged only:  digest     work order                        original_remediated.pdf review.md + record.json
                OCR + auto-tag  + veraPDF (before)                                       + veraPDF (after)
```

An **untagged** PDF first goes through `intake.py` (local tools, no model, no cost): OCR where pages have no text, then auto-tagging, with checks after each step (see [Intake: untagged PDFs](intake.md)). A tagged PDF skips it.

The same validator, veraPDF's WCAG 2.2 machine profile (which includes the PDF/UA-1 rules), runs on the original during the audit and on the result during verify. `review.md` sorts every failed rule into fixed, still failing, or **newly failing** (something the run broke, flagged as a CHECK). See [Verification with veraPDF](verapdf.md).
