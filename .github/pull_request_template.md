## Issue

<!-- Link the issue addressed by this pull request. -->
Closes #

## Squashed commits

<!-- List the commits included in this squashed pull request. -->
- 

## Test checklist

- [ ] `python -m compileall pipeline`
- [ ] `bash -n pipeline/run_api.sh`
- [ ] `bash -n pipeline/batch_api.sh`
- [ ] `python -m pytest pipeline/tests -q` passes; new rules in `lib/` have tests
- [ ] Regression: `python3 pipeline/tools/regression.py --jobs 3` passes locally or the "PDF validation" checks pass; if the output changed on purpose, the baseline was updated with `--update` (reason: ___)
- [ ] Intake changed: `python3 pipeline/tools/intake_cases.py <out_dir>` passes
- [ ] Docs updated in `docs/`, or not needed because: ___
