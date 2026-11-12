---
title: The home page (new runs and batches)
parent: Review and ship
nav_order: 1
has_children: true
has_toc: false
---

# The home page: new runs and batches from the browser

The app's home page (`http://127.0.0.1:8760/`) is where library staff start work without a terminal (#45). Pick a PDF, see what the AI request could cost, select "Start Remediation", follow the run, and land on the review page.

It runs the pipeline's own commands (`run_api.sh`, `batch_api.sh`) as jobs, exactly as a person would type them, so the command line keeps working as before. See [The app](app.md) for its settings, jobs and security.

```bash
cd pipeline
python3 app.py              # opens the home page
```

This part of the docs has one page for each task:

- [Finding your way](home-workspace.md): the home page's lists, moving around the app, and Move to Trash.
- [Upload and single runs](home-runs.md): upload a PDF, get the free estimate and start a run.
- [Batches](home-batches.md): run several PDFs together.
