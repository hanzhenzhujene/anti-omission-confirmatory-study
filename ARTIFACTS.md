# Artifact Guide

This file is the fastest path through the repository if you want the paper, the locked evidence, or the executable pipeline without browsing the tree manually.

## Final paper

- Anonymous PDF: [docs/generated/final_submission_manuscript_v1.pdf](docs/generated/final_submission_manuscript_v1.pdf)
- Markdown manuscript: [docs/generated/final_submission_manuscript_v1.md](docs/generated/final_submission_manuscript_v1.md)
- LaTeX source: [docs/generated/final_submission_manuscript_v1.tex](docs/generated/final_submission_manuscript_v1.tex)
- Locked reporting spec snapshot: [docs/generated/final_submission_manuscript_v1.locked.json](docs/generated/final_submission_manuscript_v1.locked.json)

## Final visuals

- GitHub overview figure: [docs/assets/confirmatory_overview.svg](docs/assets/confirmatory_overview.svg)
- Primary tradeoff figure: [docs/assets/confirmatory_primary_tradeoff.svg](docs/assets/confirmatory_primary_tradeoff.svg)
- Timeliness figure: [docs/assets/confirmatory_timeliness.svg](docs/assets/confirmatory_timeliness.svg)

## Locked confirmatory run

- Run directory: [outputs/runs/20260414T225156Z_mainline-confirmatory-holdout-v3-live](outputs/runs/20260414T225156Z_mainline-confirmatory-holdout-v3-live)
- Run config snapshot: [run_config.json](outputs/runs/20260414T225156Z_mainline-confirmatory-holdout-v3-live/run_config.json)
- Manifest: [manifest.jsonl](outputs/runs/20260414T225156Z_mainline-confirmatory-holdout-v3-live/manifest.jsonl)
- Raw requests: [raw_requests.jsonl](outputs/runs/20260414T225156Z_mainline-confirmatory-holdout-v3-live/raw_requests.jsonl)
- Raw responses: [raw_responses.jsonl](outputs/runs/20260414T225156Z_mainline-confirmatory-holdout-v3-live/raw_responses.jsonl)

## Labels and provenance

- Final labels: [labels/final_labels.jsonl](outputs/runs/20260414T225156Z_mainline-confirmatory-holdout-v3-live/labels/final_labels.jsonl)
- Label artifact index: [labels/label_artifacts.json](outputs/runs/20260414T225156Z_mainline-confirmatory-holdout-v3-live/labels/label_artifacts.json)
- Agreement summary: [labels/agreement_summary.json](outputs/runs/20260414T225156Z_mainline-confirmatory-holdout-v3-live/labels/agreement_summary.json)
- Finalization report: [labels/finalization_report.json](outputs/runs/20260414T225156Z_mainline-confirmatory-holdout-v3-live/labels/finalization_report.json)

## Analysis and verification

- Summary: [analysis/summary.json](outputs/runs/20260414T225156Z_mainline-confirmatory-holdout-v3-live/analysis/summary.json)
- Condition rates: [analysis/condition_rates.csv](outputs/runs/20260414T225156Z_mainline-confirmatory-holdout-v3-live/analysis/condition_rates.csv)
- Paper outcomes table: [analysis/paper_table_2_condition_outcomes.csv](outputs/runs/20260414T225156Z_mainline-confirmatory-holdout-v3-live/analysis/paper_table_2_condition_outcomes.csv)
- Paired contrasts: [analysis/paper_table_s2_paired_contrasts.csv](outputs/runs/20260414T225156Z_mainline-confirmatory-holdout-v3-live/analysis/paper_table_s2_paired_contrasts.csv)
- Evidence package: [analysis/evidence_package.json](outputs/runs/20260414T225156Z_mainline-confirmatory-holdout-v3-live/analysis/evidence_package.json)
- Evidence verification: [analysis/evidence_verification.json](outputs/runs/20260414T225156Z_mainline-confirmatory-holdout-v3-live/analysis/evidence_verification.json)

## Canonical study docs

- Confirmatory preregistration: [docs/mainline-confirmatory-holdout-v3-prereg.md](docs/mainline-confirmatory-holdout-v3-prereg.md)
- Confirmatory runbook: [docs/mainline-confirmatory-holdout-v3-runbook.md](docs/mainline-confirmatory-holdout-v3-runbook.md)
- Confirmatory results memo: [docs/mainline-confirmatory-results.md](docs/mainline-confirmatory-results.md)

## Code entry points

- CLI: [src/anti_omission/cli.py](src/anti_omission/cli.py)
- Runner: [src/anti_omission/runner.py](src/anti_omission/runner.py)
- Labeling: [src/anti_omission/labeling.py](src/anti_omission/labeling.py)
- Reporting: [src/anti_omission/reporting.py](src/anti_omission/reporting.py)
- GitHub visual assets: [src/anti_omission/repo_visuals.py](src/anti_omission/repo_visuals.py)
