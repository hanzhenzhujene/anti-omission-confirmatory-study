# Confirmatory Evidence Index: 20260414T225156Z_mainline-confirmatory-holdout-v3-live

_This document is generated deterministically from run artifacts. Do not hand-edit it as a source of truth._

## Status

- Run ID: `20260414T225156Z_mainline-confirmatory-holdout-v3-live`
- Subject model: `gpt-5-mini`
- Conditions: `baseline`, `generic_control`, `disclosure_full`
- Trial count: `180` total, `180` scored, `0` excluded
- Evidence verification status: `ok`
- Provenance verdict: Verified byte-for-byte against a finalized dual-primary-plus-adjudication consensus package.

## Locked Pre-Run Artifacts

- Experiment config: `configs/experiment/mainline_confirmatory_holdout_v3_live.json`
- `docs/main-experiment-freeze.md`
- `docs/preregistration-template.md`
- `docs/mainline-confirmatory-runbook.md`

## Executed Run Artifacts

- Run directory: `outputs/runs/20260414T225156Z_mainline-confirmatory-holdout-v3-live`
- Run config snapshot: `outputs/runs/20260414T225156Z_mainline-confirmatory-holdout-v3-live/run_config.json`
- Manifest: `outputs/runs/20260414T225156Z_mainline-confirmatory-holdout-v3-live/manifest.jsonl`
- Raw requests: `outputs/runs/20260414T225156Z_mainline-confirmatory-holdout-v3-live/raw_requests.jsonl`
- Raw responses: `outputs/runs/20260414T225156Z_mainline-confirmatory-holdout-v3-live/raw_responses.jsonl`
- Final labels: `outputs/runs/20260414T225156Z_mainline-confirmatory-holdout-v3-live/labels/final_labels.jsonl`
- Analysis summary: `outputs/runs/20260414T225156Z_mainline-confirmatory-holdout-v3-live/analysis/summary.json`
- Evidence package: `outputs/runs/20260414T225156Z_mainline-confirmatory-holdout-v3-live/analysis/evidence_package.json`
- Evidence verification: `outputs/runs/20260414T225156Z_mainline-confirmatory-holdout-v3-live/analysis/evidence_verification.json`

## Interpretive Docs

- `docs/generated/final_submission_manuscript_v1.md`
- `docs/generated/final_submission_manuscript_v1.pdf`
- Run-local manuscript: `outputs/runs/20260414T225156Z_mainline-confirmatory-holdout-v3-live/analysis/paper_full_manuscript_submission.md`
- Run-local PDF: `outputs/runs/20260414T225156Z_mainline-confirmatory-holdout-v3-live/analysis/paper_full_manuscript_submission.pdf`

## Observed Outcome Snapshot

- `baseline` risk disclosure: `24/24 (100.0%)`
- `generic_control` risk disclosure: `24/24 (100.0%)`
- `disclosure_full` risk disclosure: `24/24 (100.0%)`
- `disclosure_full` benign false alarms: `6/36 (16.7%)`
- `disclosure_full` late risk disclosures: `7/24 (29.2%)`

## Known Provenance Caveats

- `absolute_benign_guardrail_failed`
- `comparative_benign_guardrail_failed`
- `late_disclosures_observed`

## Use Discipline

- Treat this package as the main locked confirmatory evidence for the executed run identified above.
- Do not reuse an inspected or executed confirmatory bank as if it were fresh.
- Byte-for-byte verification confirms artifact integrity, and this run also preserves staged primary, adjudicated, and finalized label provenance.
