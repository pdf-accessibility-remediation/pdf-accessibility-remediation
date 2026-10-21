# PDF Accessibility Remediation Pipeline

[![CI](https://github.com/pdf-accessibility-remediation/pdf-accessibility-remediation/actions/workflows/ci.yml/badge.svg)](https://github.com/pdf-accessibility-remediation/pdf-accessibility-remediation/actions/workflows/ci.yml)

This pipeline uses Claude via OpenRouter to help remediate PDF accessibility issues. The model reads a compact summary of a tagged PDF and returns a JSON **work order** containing decisions such as heading levels, alternative text, artifacts, document language, and reading-order fixes. The code applies those decisions, validates the result, and generates a review report. The original PDF is never modified.

The only paid step is the model call in `decide.py`.

## How it works

```
original.pdf ──► intake.py* ──► audit.py ──► decide.py ──► apply.py ──► verify.py ──► report.py
                  OCR +          summary +     Claude via                 veraPDF        │
                  auto-tag       veraPDF       OpenRouter                 (after)        ▼
                                 (before)                                               original_remediated.pdf
                                                                                        review.md + review.html
                                                                                        record.json

* Untagged PDFs only; tagged PDFs skip intake.py.
```

**Untagged PDFs** first go through `intake.py`, which uses local tools to perform OCR when pages lack text and then attempts automatic tagging. Checks run after each step. This process does not require an AI model call.

**Tagged PDFs** skip intake and proceed directly to the audit.

The pipeline uses veraPDF's WCAG 2.2 machine profile for validation during both audit and verification. The review report classifies failed rules as fixed, still failing, or newly failing. Newly failing rules indicate potential regressions introduced by remediation and are flagged for review.

## Setup

The following steps are sufficient for processing tagged PDFs. Untagged PDFs need additional intake dependencies.

1. **Install Python dependencies.** From the `pipeline/` directory, create and activate a virtual environment with Python 3.13, then install the requirements. Don't use Python 3.15: pikepdf 10.5.1, which the pipeline pins, has no ready-made Python 3.15 build.
    ```
    python3.13 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    ```
    The pipeline requires `pdfplumber 0.11.9` because `lib/plumb_fix.py` patches its internals.

2. **Configure your OpenRouter API key.** Add `OPENROUTER_API_KEY=...` to a `.env` file in `pipeline/` or a parent directory, such as the repository root. Keep `.env` out of version control.

3. **Check your API key.** From `pipeline/`, run:
    ```
    python3 decide.py --check-key
    ```

4. **Install veraPDF.**

    Java 11 or later is required; Java 17 is recommended.
    - **Ubuntu/Debian:**
        ```
        sudo apt install openjdk-17-jre-headless
        ```
    - **macOS with Homebrew:**
        ```
        brew install openjdk@17
        ```
        Follow Homebrew's instructions to make Java discoverable by macOS and your shell. See the [OpenJDK 17 Homebrew formula](https://formulae.brew.sh/formula/openjdk@17) for details.

    - **Other systems:** Follow the [Java 17 installation guide](https://docs.oracle.com/en/java/javase/17/install/).

    Then install veraPDF from `pipeline/`:

    ```
    bash verapdf/install.sh
    ```

    Follow the script's instructions for setting the VERAPDF environment variable, then check the installation:
    ```
    python3 vera.py --check
    ```

    The pipeline checks veraPDF before making a paid model call. To run without veraPDF, set `VERAPDF=off`; the WCAG checks are then skipped.

5. **Prepare your files.** Sample PDFs are in `samples/<name>/`; place your own PDFs there as well. The system prompts ship in `prompts/`, so no setup is needed. Outputs are written to `runs/<name>/<run-label>/` beside `pipeline/`.

    Keep your own PDFs and run outputs out of version control, particularly when they contain copyrighted material.

## Run

From the repository's `pipeline/` directory, run:

```
bash run_api.sh <original.pdf> <short-name> [run-label]
```

For example:

```bash
bash run_api.sh ../samples/group1/clans.pdf clanstest apirun1
```

The short name sets the output folder, `runs/<short-name>/<run-label>/`. The run label is optional and defaults to a timestamp.

The script audits the PDF, displays a cost estimate and available credit, and asks for confirmation before calling the API. It then applies the model's work order, verifies the result, and generates the review report: `review.md`, which opens with an "At a glance" summary (including "Ready to ship?"), and `review.html`, the same run as an offline dashboard. A batch also gets `summary.html`. See [Output files](docs/output-files.md).

A label that already holds a finished run is refused, so use a new label for each new run. If a run stops partway, rerun the same command with the same label: it picks up where it stopped, reusing the audit and any usable reply already paid for.

To retain intermediate files for debugging, set `KEEP=1`:

```
KEEP=1 bash run_api.sh ../samples/group1/clans.pdf clanstest apirun2
```

## Documentation

The full documentation, covering setup, run options, batch runs, models, output files, intake, veraPDF verification, and troubleshooting, is available at the [PDF Accessibility Remediation documentation](https://pdf-accessibility-remediation.github.io/) site. Documentation source files are maintained in `docs/` in this repository so documentation changes can be reviewed alongside pipeline changes.

## Automated checks

GitHub Actions runs the following checks:

- **CI** — Compiles Python sources, validates shell-script syntax, installs dependencies, and runs `pip-audit`.
- **PDF validation** — Installs Java 17 and veraPDF, then runs `audit.py` (with veraPDF on the original) against a sample PDF when pipeline or sample files change.
- **Dependency review** — Reviews dependency changes in pull requests and fails on high-severity vulnerabilities.
- **CodeQL** — Performs static security analysis of the Python code on pushes, pull requests, and weekly.
- **Documentation checks** — Checks documentation links and requires documentation changes when `pipeline/` or `prompts/` changes, unless the pull request has the `no-docs-needed` label.

These workflows do not run `run_api.sh` or make OpenRouter API calls automatically.

## Limitations and human review

Automated remediation and validation do not guarantee that a PDF is fully accessible. Machine-checkable rules cannot assess every aspect of accessibility, and model-generated alternative text, heading assignments, and reading-order decisions may require correction.

PDF 2.0 is not supported yet. A PDF 2.0 file, or one whose tag tree declares namespaces, is stopped before any paid call or change and goes to a person.

**Review `review.md` and manually inspect the remediated PDF before relying on it.** Pay particular attention to unresolved failures and newly failing rules.
