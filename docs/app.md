---
title: The app (browser)
parent: Review and ship
nav_order: 2
has_children: true
has_toc: false
---

# The pipeline in the browser

`app.py` is a small local web app. It shows a run's dashboard (`review.html`) with buttons that review it again, start over, go back to an earlier session's choices, and apply a finished session. The home page (`/`), where runs and batches are started, is described in [The home page](home.md).

Each button runs the same command a person would type (`review_workorder.py … --reopen`, `--apply`, `--pin`), so the command line keeps working exactly as before, and both give the same result. The app adds no pipeline logic. The one exception is the Accessibility Evaluation page ([Accessibility evaluation and release](release.md)), whose forms are recorded directly in the app's process through `review/manual.py`, the same code as `manual_checks.py`. Only pipeline steps run as jobs.

```bash
cd pipeline
python3 app.py ../runs/teika/rv1            # opens that run's page at http://127.0.0.1:8760/run/teika/rv1/
```

After this one start command, the terminal can be left alone. Everything the pages show is read from disk (the run folders, their `reviews/`, and `runs/.app/`), so stopping and restarting the app loses nothing.

This part of the docs has one page for each task:

- [The run page](app-run-page.md): the run's buttons, Bring Back an Edited PDF, Session History, and using the pages with a keyboard or screen reader.
- [Jobs and problems](app-jobs.md): how jobs wait their turn, what the pages say when something goes wrong, and stopping and starting the app.
- [Setup, settings and security](app-setup.md): what the app needs, its settings and limits, its security, and Move to Trash.
