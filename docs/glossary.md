---
title: Glossary
nav_order: 6
---

# Glossary

These are the words the other pages use without explaining them each time. Each entry links to the page that covers it in full.

**ActualText.** Text stored in the PDF that a screen reader speaks instead of the printed characters, for example a word whose characters don't read correctly. The pipeline only accepts one that matches the print apart from spacing, letter case and line-end hyphens. See [Work order](work-order.md).

**The AI.** The large language model that reads the summary of a PDF and writes the work order. It is Claude by default, reached through OpenRouter; any OpenRouter model that takes images can be used. The pages say "model" only when choosing one. See [Models](models.md).

**Alt text (alternative text).** A short description of a figure that a screen reader speaks in place of the image. The AI drafts it, and a reviewer checks it. See [Reviewing the work order](review-step.md).

**Artifact.** In a PDF, content marked as decoration (running heads, page numbers, rules, blank-page marks) so a screen reader skips it. See [Work order](work-order.md).

**Audit.** The step (`audit.py`) that reads the PDF, writes the digest, crops the figures and runs veraPDF on the original. It costs nothing.

**Batch.** Several PDFs run together with one command or from the app's home page, with one summary. See [Batch runs](batch-runs.md).

**CHECK.** A line in the report that needs a reviewer's attention before the PDF ships, for example a newly failing rule or OCR text that may be wrong. See [Output files](output-files.md).

**Digest.** The short summary of a PDF that the audit writes and the AI reads: its tags, headings, figures, reading order and the veraPDF failures the AI can act on. See [Files](files.md).

**Expected Cost and Max Estimated Cost.** Before an AI request, the pipeline shows what it usually costs (Expected Cost, from past requests of the same kind) and the most it could cost (Max Estimated Cost, which the dollar limits are checked against). See [What a run may cost](options.md#what-a-run-may-cost).

**Hand edit.** A change made to the PDF itself in Acrobat, then brought back into the pipeline as a new run. See [Editing the PDF by hand](hand-edits.md).

**Intake.** The first step for an untagged PDF (`intake.py`): OCR where pages have no text, then automatic tagging. Local tools only, no AI request. See [Intake](intake.md).

**Low-resolution figure.** A figure whose image is printed at under 150 pixels per inch (ppi), so it is likely to look blurry when printed or zoomed. The audit lists them, and the report flags them for a person to replace by hand. See [Finding images that need a better copy](hand-edits.md#finding-images-that-need-a-better-copy).

**Newly failing rule.** A veraPDF rule that passed on the original and fails on the result. It may be a problem the remediation caused, so the report flags it. See [Verification with veraPDF](verapdf.md).

**OCR layer.** The invisible text laid over a scanned page so it can be searched and read aloud. It comes from optical character recognition, so it can contain misread words. See [OCR words](ocr-words.md).

**Ready to Ship?** The line at the top of the report's Overview that says whether the PDF can be released, or what is still open. See [Accessibility evaluation and release](release.md).

**Remediation.** Making a PDF accessible: adding or correcting its tags, alt text, language, reading order and the like.

**Reviewer.** The person who checks the AI's decisions and the report before a PDF ships, usually library staff. See [Reviewing the work order](review-step.md).

**Run.** One PDF taken through the pipeline once. Its results go to `runs/<short name>/<run label>/`. See [Running](running.md).

**Run label.** The name of one run of a PDF, such as `api-run1`. A label that already holds a finished run can't be used again; rerunning an unfinished one resumes it. It defaults to a timestamp.

**Saved reply.** The AI's answer from an earlier run, used again so the work order can be applied with no new cost (`REPLY=` for one run, `FROM=` for a batch). See [Options](options.md).

**Short name.** The name that groups a PDF's runs, such as `nktest` in `runs/nktest/api-run1/`.

**Tags (tag tree).** The structure inside a PDF that tells a screen reader what each part is (heading, paragraph, list, table, figure) and in what order to read it. A tagged PDF has one; an untagged PDF goes through intake first.

**veraPDF.** The open-source checker that tests a PDF against the WCAG 2.2 and PDF/UA rules a machine can check. See [Verification with veraPDF](verapdf.md).

**Work order.** The JSON list of decisions the AI returns for one PDF, which `apply.py` carries out. See [Work order](work-order.md).
