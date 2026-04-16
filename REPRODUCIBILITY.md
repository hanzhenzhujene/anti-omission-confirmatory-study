# Reproducibility

This repository is organized around one canonical confirmatory evidence source:

- `outputs/runs/20260414T225156Z_mainline-confirmatory-holdout-v3-live`

Everything in the paper-level package should trace back to that run.

## Environment

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

If you want to execute new live runs, export `OPENAI_API_KEY` first.

## Quick verification path

Validate the final experiment config:

```bash
PYTHONPATH=src python -m anti_omission validate \
  --experiment-config configs/experiment/mainline_confirmatory_holdout_v3_live.json
```

Run the engineering smoke path:

```bash
PYTHONPATH=src python -m anti_omission smoke-test \
  --experiment-config configs/experiment/dev_smoke.json \
  --labels-csv fixtures/dev_smoke_labels.csv
```

Verify the locked evidence package:

```bash
PYTHONPATH=src python -m anti_omission verify-evidence \
  --run-dir outputs/runs/20260414T225156Z_mainline-confirmatory-holdout-v3-live
```

## Regenerate public-facing assets

Generate the GitHub visuals:

```bash
PYTHONPATH=src python -m anti_omission generate-repo-assets \
  --run-dir outputs/runs/20260414T225156Z_mainline-confirmatory-holdout-v3-live \
  --output-dir docs/assets
```

Regenerate the paper bundle:

```bash
PYTHONPATH=src python -m anti_omission typeset-paper \
  --run-dir outputs/runs/20260414T225156Z_mainline-confirmatory-holdout-v3-live \
  --manuscript-spec configs/reporting/final_submission_manuscript_v1.json
```

Rebuild the locked submission package:

```bash
PYTHONPATH=src python -m anti_omission build-submission-bundle \
  --run-dir outputs/runs/20260414T225156Z_mainline-confirmatory-holdout-v3-live \
  --manuscript-spec configs/reporting/final_submission_manuscript_v1.json
```

## Final test slice

The curated repo keeps a focused test slice that covers the runnable and reporting-critical paths:

```bash
PYTHONPATH=src pytest \
  tests/test_client.py \
  tests/test_evidence.py \
  tests/test_labeling.py \
  tests/test_preflight.py \
  tests/test_repo_visuals.py \
  tests/test_reporting.py \
  tests/test_runner.py \
  tests/test_scenario_qc.py \
  tests/test_schemas.py \
  tests/test_smoke_run.py \
  tests/test_submission.py \
  tests/test_typesetting.py -q
```

## Scope discipline

- The main-text paper evidence comes only from the locked `holdout_v3` run.
- The `dev` bank exists only for smoke verification and should not be cited as confirmatory evidence.
- Raw artifacts under the locked run directory are preserved as historical outputs rather than being hand-edited for cosmetic cleanup.
