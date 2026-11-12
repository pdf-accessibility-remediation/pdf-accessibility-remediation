---
title: Overview
nav_order: 1
---

# PDF Accessibility Remediation Pipeline

These pages explain how to set up and run the pipeline, review its results and ship an accessible PDF. Start with [Setup](setup.md) and [Running](running.md). Words the pages use without explaining them are in the [Glossary](glossary.md).

The pipeline helps make PDF books accessible. The AI (Claude by default, through OpenRouter) reads a short summary of a tagged PDF and returns a **work order**: a JSON list of decisions such as heading levels, alternative text, decorative content to hide (artifacts), the document language and reading-order fixes. The code carries out those decisions on a copy, checks the result and writes a report for a reviewer. The original PDF is never changed.

Two steps can cost money: the AI's work order (`decide.py`) and, for scanned pages that are mostly in Hawaiian, a reading of each page by the AI (`read_pages.py`). Both show an estimate and ask before anything is sent. See [What a run may cost](options.md#what-a-run-may-cost).

## How it works

```
original.pdf
   ↓
intake.py*      OCR and tagging
   ↓
audit.py        a summary for the AI
   ↓
decide.py       the AI's work order (paid)
   ↓
read_pages.py   reads Hawaiian pages (paid)
   ↓
review step     a reviewer checks (optional)
   ↓
apply.py        makes the fixes on a copy
   ↓
verify.py       checks the result
   ↓
report.py       the PDF and the reports

* untagged PDFs only
```

**Untagged PDFs** first go through `intake.py`. It uses local tools to add text by OCR where pages have none, then tags the PDF automatically, with checks after each step. Intake makes no AI request. See [Intake: untagged PDFs](intake.md).

**Tagged PDFs** skip intake and go straight to the audit.

The pipeline checks the PDF with veraPDF's WCAG 2.2 machine profile, which includes the PDF/UA-1 rules, twice: on the original during the audit, and on the result during verification. The report sorts every failed rule into fixed, still failing or newly failing. A newly failing rule may be a problem the remediation caused, so it is flagged for review. See [Verification with veraPDF](verapdf.md).

**Not supported yet: PDF 2.0.** A PDF 2.0 file, or one whose tags declare namespaces, is stopped before any paid request or change and goes to a reviewer. See [Not supported yet: PDF 2.0](troubleshooting.md#not-supported-yet-pdf-20).

## Where to go next

The sidebar groups these pages the same way.

**[Get started](get-started.md)**
- [Setup](setup.md): install Python, veraPDF and the intake tools, and add your OpenRouter key.
- [Running](running.md): run one PDF from the terminal, step by step.
- [Batch runs](batch-runs.md): run a folder of PDFs.
- [Options](options.md): every setting you can put before the command, and what a run may cost.
- [Models](models.md): choose which AI model to use.

**[Review and ship](review-and-ship.md)**
- [The home page](home.md) and [The app](app.md): start runs and review them in the browser.
- [Reviewing the work order](review-step.md): check the AI's decisions before they are applied.
- [Editing the PDF by hand](hand-edits.md): fix something in Acrobat and bring the PDF back.
- [Accessibility evaluation and release](release.md): what "ready to ship" means and how a PDF is released.

**[How it works](how-it-works.md)**
- [Intake](intake.md), [OCR words](ocr-words.md), [Work order](work-order.md) and [Verification with veraPDF](verapdf.md): how each part works.
- [Output files](output-files.md): what a run leaves behind.

**Help**
- [Troubleshooting](troubleshooting.md): what an error means and what to do.
- [Glossary](glossary.md): the terms these pages use.

**[For developers](developers.md)**
- [Testing](testing.md): the unit tests, the regression test and the checks in CI.
- [Files](files.md): what each script and module does.
