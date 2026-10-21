---
title: Setup
nav_order: 2
---

# Setup (once)

1. **Python packages:** First cd to pipeline, then create and activate the virtual environment with Python 3.13: `python3.13 -m venv .venv && source .venv/bin/activate` (not 3.15: pikepdf 10.5.1, which the pipeline pins, has no ready-made Python 3.15 build). Then `pip install -r requirements.txt` (pdfplumber must be 0.11.9: `lib/plumb_fix.py` patches its internals). Every run first checks that the required libraries import in the Python that runs the pipeline: if one is missing, it stops before any audit or paid call and prints the install command. Each `record.json` (`environment`) and the top of each `review.md` record the Python and library versions used.
2. **For untagged PDFs (intake), once:** `brew install ocrmypdf tesseract-lang` (OCRmyPDF 17 brings Tesseract and Ghostscript; `tesseract-lang` adds the language packs, including `chi_sim`, `chi_tra`, `jpn`, `kor`) and Java 11 or later for auto-tagging (for example `brew install --cask temurin`; any Java 11+ install works, e.g. Homebrew's `openjdk@21`). OCRmyPDF is installed by Homebrew, not pip, because its pip package needs newer pikepdf and pdfminer versions than this pipeline pins. `opendataloader-pdf` (the auto-tagger) comes with `requirements.txt`. These are checked only when a book needs them: tagged books, teammates who only run tagged books and the GitHub checks need none of them.
3. **Key:** put `OPENROUTER_API_KEY=…` in a `.env` file in `pipeline/` or any folder above it (e.g. the repo root). Keep `.env` in `.gitignore`.
4. **Check the key (free):** `python3 decide.py --check-key`.
5. **veraPDF** (WCAG and PDF/UA checks, see [Verification with veraPDF](verapdf.md)): needs Java 17 (`sudo apt install openjdk-17-jre-headless`, or any Java 17 runtime on `PATH`; the auto-tagger's Java works too if it is 17 or later). Then, from `pipeline/`, `bash verapdf/install.sh` installs veraPDF 1.30.3 in `~/.local/opt/verapdf` and prints the line to add to your shell profile: `export VERAPDF=~/.local/opt/verapdf/verapdf`. pip can't install it: it is a Java program, not a Python package. `python3 vera.py --check` prints the version. Every run checks it before any paid call and stops if it is missing; `VERAPDF=off` runs without it, and `review.md` then says its rows were not run.
6. **Prompt:** `workorder_v8.md` goes in `pipeline/prompts/` or in `prompts/` beside `pipeline/`. Older versions are kept only as a record.
7. **PDFs:** originals go in `samples/<name>/` and are never written to. Outputs go in `runs/<name>/<run-label>/` (single runs) or `runs/batches/<label>/<name>/` (batches) beside `pipeline/` (set `RUNS_DIR` to put them elsewhere). Keep both out of git: the books are in copyright.
