# Mainline Confirmatory Holdout V3 Runbook

This runbook is the operator checklist that was used for the completed confirmatory cycle built around `scenarios/confirmatory_holdout_v3/`. Treat it as a historical execution record for `outputs/runs/20260414T225156Z_mainline-confirmatory-holdout-v3-live`; any future live follow-up should use a new versioned bank rather than rerunning this one as fresh confirmatory evidence.

## Before execution

1. Human-QC the authored scenario bank without running the live model on it.
   Recommended deterministic check:

```bash
PYTHONPATH=src python -m anti_omission qc-scenarios \
  --experiment-config configs/experiment/mainline_confirmatory_holdout_v3_live.json \
  --output-path docs/generated/mainline_confirmatory_holdout_v3_qc.json
```

2. Freeze:
   - `configs/experiment/mainline_confirmatory_holdout_v3_live.json`
   - `scenarios/confirmatory_holdout_v3/`
   - `configs/reporting/final_submission_manuscript_v1.json`
3. Record the exact repo snapshot or archival bundle used for the run.
4. Confirm the environment:
   - Python 3.11 environment active
   - project dependencies installed
   - `OPENAI_API_KEY` exported without trailing newline

The QC report is not a substitute for human review, but it should be checked for broad-query leakage, duplicate authored text, or hidden artifacts that read like labels rather than realistic internal notes.

## Execution commands

```bash
PYTHONPATH=src python -m anti_omission validate \
  --experiment-config configs/experiment/mainline_confirmatory_holdout_v3_live.json

PYTHONPATH=src python -m anti_omission make-manifest \
  --experiment-config configs/experiment/mainline_confirmatory_holdout_v3_live.json

PYTHONPATH=src python -m anti_omission preflight \
  --run-dir outputs/runs/<timestamped_run_dir>

PYTHONPATH=src python -m anti_omission run \
  --run-dir outputs/runs/<timestamped_run_dir>

PYTHONPATH=src python -m anti_omission export-labels \
  --run-dir outputs/runs/<timestamped_run_dir>
```

`preflight` also reports the deterministic manifest SHA256 and whether the current `manifest.jsonl` still matches the hash recorded in `run_config.json`.

## Labeling workflow

### Primary A

1. Fill `labels/annotation_export.csv` blind to condition identity.
2. Import:

```bash
PYTHONPATH=src python -m anti_omission import-labels \
  --run-dir outputs/runs/<timestamped_run_dir> \
  --labels-csv /absolute/path/to/primary_a.csv \
  --stage primary \
  --annotator-id primary_a \
  --annotator-type human \
  --blinding-mode condition_code_blind \
  --agreement-sample-design full_double_primary
```

### Primary B

Repeat the same import flow with `--annotator-id primary_b`.

### Adjudication

1. Export the merged adjudication sheet:

```bash
PYTHONPATH=src python -m anti_omission export-adjudication-sheet \
  --run-dir outputs/runs/<timestamped_run_dir>
```

2. Prioritize `labels/adjudication_required.csv`.
3. Import the completed adjudication sheet:

```bash
PYTHONPATH=src python -m anti_omission import-labels \
  --run-dir outputs/runs/<timestamped_run_dir> \
  --labels-csv /absolute/path/to/adjudicated.csv \
  --stage adjudicated \
  --annotator-id adjudicator \
  --annotator-type human \
  --blinding-mode condition_code_blind \
  --agreement-sample-design targeted_adjudication_subset
```

### Finalization

```bash
PYTHONPATH=src python -m anti_omission finalize-labels \
  --run-dir outputs/runs/<timestamped_run_dir>
```

The run is not submission-grade until `labels/finalization_report.json` shows `status = finalized` and `labels/label_artifacts.json` shows `final_stage = adjudicated_consensus_final`.

## Analysis and evidence commands

```bash
PYTHONPATH=src python -m anti_omission summarize \
  --run-dir outputs/runs/<timestamped_run_dir>

PYTHONPATH=src python -m anti_omission lock-manuscript-spec \
  --run-dir outputs/runs/<timestamped_run_dir> \
  --manuscript-spec configs/reporting/final_submission_manuscript_v1.json

PYTHONPATH=src python -m anti_omission build-submission-bundle \
  --run-dir outputs/runs/<timestamped_run_dir>
  --manuscript-spec configs/reporting/final_submission_manuscript_v1.json
```

`lock-manuscript-spec` writes a run-local locked reporting spec. `build-submission-bundle` then typesets the anonymous paper and refreshes `analysis/evidence_package.json`, `analysis/evidence_verification.json`, and `analysis/evidence_index.md` in one deterministic pass.

## Submission gate

Do not treat the run as the paper's final evidence source unless all of the following are true:

- the bank is the fresh `confirmatory_holdout_v3` bank
- the three conditions remain unchanged
- dual-primary imports are present
- adjudication artifacts are present
- `finalize-labels` succeeded
- `package-evidence` and `verify-evidence` both succeeded
