# Anti-Omission Locked Confirmatory Study

This repository is the clean, GitHub-ready package for the final anti-omission confirmatory study on `gpt-5-mini`.

It is intentionally narrower than the original local scaffold:

- it includes the locked `holdout_v3` confirmatory bank
- it includes the final three-condition package: `baseline`, `generic_control`, and `disclosure_full`
- it includes the final paper bundle and the fully staged evidence package
- it excludes older pilot runs, exploratory run directories, scratch assets, and local Codex workflow files

The only non-confirmatory extras kept here are the tiny `dev` smoke fixtures used to verify that the code path still works end to end.

## Final package

- Final locked run: `outputs/runs/20260414T225156Z_mainline-confirmatory-holdout-v3-live`
- Final generated paper: `docs/generated/final_submission_manuscript_v1.pdf`
- Final manuscript source: `docs/generated/final_submission_manuscript_v1.md`
- Final reporting spec: `configs/reporting/final_submission_manuscript_v1.json`
- Final preregistration lock: `docs/mainline-confirmatory-holdout-v3-prereg.md`
- Final runbook: `docs/mainline-confirmatory-holdout-v3-runbook.md`

## Headline confirmatory result

On the locked `holdout_v3` run, all three conditions disclosed on `24/24` risk trials under the preregistered binary endpoint. `disclosure_full` therefore showed no observed primary-endpoint gain over `baseline` or `generic_control`. The same condition also produced `6/36` benign false alarms (`16.7%`) and `7/24` late disclosures on risk rows (`29.2%`), so the final confirmatory reading is a tradeoff-failure result rather than a prompt-success claim.

## Repository layout

```text
.
├── README.md
├── pyproject.toml
├── configs/
│   ├── conditions/
│   ├── experiment/
│   ├── model/
│   └── reporting/
├── docs/
│   ├── generated/
│   ├── paper_fragments/final_submission/
│   ├── mainline-confirmatory-holdout-v3-prereg.md
│   ├── mainline-confirmatory-holdout-v3-runbook.md
│   └── mainline-confirmatory-results.md
├── outputs/runs/20260414T225156Z_mainline-confirmatory-holdout-v3-live/
├── scenarios/
│   ├── confirmatory_holdout_v3/
│   └── dev/
├── src/anti_omission/
├── tests/
└── vendor/neurips_2025/
```

## Setup

Use Python `3.11+`.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

If you want to run live model calls, export `OPENAI_API_KEY` first.

## Core commands

Validate the locked confirmatory config:

```bash
PYTHONPATH=src python -m anti_omission validate \
  --experiment-config configs/experiment/mainline_confirmatory_holdout_v3_live.json
```

Build a fresh manifest for the locked study:

```bash
PYTHONPATH=src python -m anti_omission make-manifest \
  --experiment-config configs/experiment/mainline_confirmatory_holdout_v3_live.json
```

Run a locked manifest directory:

```bash
PYTHONPATH=src python -m anti_omission run \
  --run-dir outputs/runs/<timestamped_run_dir>
```

Export blind labeling sheets:

```bash
PYTHONPATH=src python -m anti_omission export-labels \
  --run-dir outputs/runs/<timestamped_run_dir>
```

Finalize staged labels and summarize:

```bash
PYTHONPATH=src python -m anti_omission finalize-labels \
  --run-dir outputs/runs/<timestamped_run_dir>

PYTHONPATH=src python -m anti_omission summarize \
  --run-dir outputs/runs/<timestamped_run_dir>
```

Generate the submission manuscript:

```bash
PYTHONPATH=src python -m anti_omission typeset-paper \
  --run-dir outputs/runs/20260414T225156Z_mainline-confirmatory-holdout-v3-live \
  --manuscript-spec configs/reporting/final_submission_manuscript_v1.json
```

Verify the final evidence bundle:

```bash
PYTHONPATH=src python -m anti_omission verify-evidence \
  --run-dir outputs/runs/20260414T225156Z_mainline-confirmatory-holdout-v3-live
```

## Smoke path

The `dev` fixtures are retained only for engineering verification:

```bash
PYTHONPATH=src python -m anti_omission smoke-test \
  --experiment-config configs/experiment/dev_smoke.json \
  --labels-csv fixtures/dev_smoke_labels.csv
```

## Scope discipline

- The main-text evidence source is only `20260414T225156Z_mainline-confirmatory-holdout-v3-live`.
- Earlier pilot and exploratory runs are intentionally not included in this repository.
- Raw artifacts are preserved under the locked run directory.
- The paper is anonymous-submission formatted, but the repository itself is a normal research code release.
