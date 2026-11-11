---
title: Setup
nav_order: 2
---

# Setup (once)

Do these steps once on each computer that runs the pipeline. Steps 1, 3, 4 and 5 are enough for tagged PDFs; step 2 adds the tools for untagged PDFs. Run every command from the `pipeline/` folder unless a step says otherwise.

1. **Python packages:** First cd to pipeline, then create and activate the virtual environment with Python 3.13 or 3.14: `python3.13 -m venv .venv && source .venv/bin/activate` (or `python3.14`; not 3.15: pikepdf 10.5.1, which the pipeline pins, has no ready-made Python 3.15 build). CI runs the unit tests on 3.13 and 3.14, and the regression test on 3.14. Then `pip install -r requirements.txt` (pdfplumber must be 0.11.9: `lib/plumb_fix.py` patches its internals). Every run first checks that the required libraries import in the Python that runs the pipeline: if one is missing, it stops before any audit or paid call and prints the install command. Each `record.json` (`environment`) and the top of each `review.md` record the Python and library versions used. To run the tests as well, install `requirements-dev.txt` instead (it includes `requirements.txt` and adds pytest; see [Testing](testing.md)).
2. **For untagged PDFs (intake):** intake needs OCRmyPDF 17 (which brings Tesseract and Ghostscript), the Tesseract language packs, and Java 11 or later for the auto-tagger. Install OCRmyPDF on its own, not into the pipeline's virtual environment: its pip package needs newer pikepdf and pdfminer versions than this pipeline pins. The auto-tagger itself (`opendataloader-pdf`) comes with `requirements.txt`. These tools are checked only when a PDF needs them, so people who only run tagged PDFs, and the GitHub checks, need none of them.

   - **macOS with Homebrew:** `brew install ocrmypdf tesseract-lang`. `tesseract-lang` adds the language packs, including `chi_sim`, `chi_tra`, `jpn` and `kor`. For Java, install any Java 11 or later, for example `brew install --cask temurin` or Homebrew's `openjdk@21`.
   - **Linux or WSL (Debian, Ubuntu):** these are the commands CI uses.

     ```bash
     sudo apt install tesseract-ocr ghostscript openjdk-17-jre-headless pipx
     # language packs for Chinese, Japanese and Korean (the -vert packs read vertical text)
     sudo apt install tesseract-ocr-chi-sim tesseract-ocr-chi-sim-vert tesseract-ocr-chi-tra tesseract-ocr-chi-tra-vert \
       tesseract-ocr-jpn tesseract-ocr-jpn-vert tesseract-ocr-kor tesseract-ocr-kor-vert
     pipx install ocrmypdf==17.13.0
     ```

   `tesseract-lang` also brings the **script models** that intake's test of an existing OCR layer reads pages with: `script/Latin`, `script/Japanese` and `script/Japanese_vert`, `script/Hangul` and `script/Hangul_vert`, `script/HanS` and `script/HanS_vert`, `script/HanT` and `script/HanT_vert`. `tesseract --list-langs` shows which are installed. Without the model for a script, the pages in that script can't be scored, so a book whose existing OCR layer is in that script gets "OCR layer not checked" and needs its OCR text approved before it is ready to ship (with none installed, every book with an existing OCR layer does). The CHECK itself is described in [Intake](intake.md). On Linux or WSL (Debian, Ubuntu), the script models are separate packages. They install without the `script/` folder, so `tesseract --list-langs` shows `Latin`, `Japanese` and so on; intake uses either name:

   ```bash
   sudo apt install tesseract-ocr-script-latn tesseract-ocr-script-jpan tesseract-ocr-script-jpan-vert tesseract-ocr-script-hang tesseract-ocr-script-hang-vert tesseract-ocr-script-hans tesseract-ocr-script-hans-vert tesseract-ocr-script-hant tesseract-ocr-script-hant-vert
   ```
3. **Key:** put `OPENROUTER_API_KEY=…` in a `.env` file in `pipeline/` or any folder above it (e.g. the repo root). Keep `.env` in `.gitignore`.
4. **Check the key (free):** `python3 decide.py --check-key`. It prints where the key came from (the environment or the `.env` file) and its length, never the key itself (nor the label OpenRouter returns, which is part of the key), then asks OpenRouter whether the key works.
5. **veraPDF** (WCAG and PDF/UA checks, see [Verification with veraPDF](verapdf.md)): needs Java 11 or later; 17 is recommended (`sudo apt install openjdk-17-jre-headless`, or any Java runtime on `PATH`; the auto-tagger's Java works too). Then, from `pipeline/`, `bash verapdf/install.sh` installs veraPDF 1.30.3 in `~/.local/opt/verapdf` and prints the line to add to your shell profile: `export VERAPDF=~/.local/opt/verapdf/verapdf`. pip can't install it: it is a Java program, not a Python package. `python3 vera.py --check` prints the version. Every run checks it before any paid call and stops if it is missing; `VERAPDF=off` runs without it, and `review.md` then says its rows were not run.
6. **Prompts:** nothing to do. The prompts the AI is given ship in `prompts/` beside `pipeline/`, and `decide.py` finds the current one (`workorder_v10.md`) there. Older versions are kept only as a record. To try a different prompt for one run, pass `--prompt` to `decide.py`.
7. **PDFs:** the sample PDFs are in `samples/tagged/`, `samples/scanned/` and `samples/untagged/`. They are open-access books, listed with their licenses in [samples/README.md](https://github.com/pdf-accessibility-remediation/pdf-accessibility-remediation/blob/main/samples/README.md), and are never written to. Your own PDFs can go anywhere; the pipeline never changes the original. Outputs go to `runs/<name>/<run-label>/` (single runs) or `runs/batches/<label>/<name>/` (batches) beside `pipeline/`; set `RUNS_DIR` to put them elsewhere. Keep your own PDFs and `runs/` out of git, particularly when they contain copyrighted material.
