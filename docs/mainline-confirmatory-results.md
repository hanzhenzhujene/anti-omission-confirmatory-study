# Mainline Confirmatory Results

## Status

The final locked confirmatory run completed on **2026-04-14** and is preserved here with full staged labeling provenance.

Primary artifact paths:

- run directory: `outputs/runs/20260414T225156Z_mainline-confirmatory-holdout-v3-live`
- summary JSON: `outputs/runs/20260414T225156Z_mainline-confirmatory-holdout-v3-live/analysis/summary.json`
- condition rates: `outputs/runs/20260414T225156Z_mainline-confirmatory-holdout-v3-live/analysis/condition_rates.csv`
- final labels: `outputs/runs/20260414T225156Z_mainline-confirmatory-holdout-v3-live/labels/final_labels.jsonl`
- evidence package: `outputs/runs/20260414T225156Z_mainline-confirmatory-holdout-v3-live/analysis/evidence_package.json`
- evidence verification report: `outputs/runs/20260414T225156Z_mainline-confirmatory-holdout-v3-live/analysis/evidence_verification.json`
- run-local manuscript: `outputs/runs/20260414T225156Z_mainline-confirmatory-holdout-v3-live/analysis/paper_full_manuscript_submission.md`
- stable manuscript export: `docs/generated/final_submission_manuscript_v1.md`
- canonical paper PDF: `docs/generated/final_submission_manuscript_v1.pdf`
- canonical evidence index: `docs/generated/mainline_confirmatory_evidence_index_v1.md`

All `180/180` trials produced visible output, `0` rows were excluded as no-output execution artifacts, and the stored package verifies byte-for-byte against the finalized staged-label bundle.

## Provenance Status

This run is the final confirmatory evidence package for the repository.

- final stage: `adjudicated_consensus_final`
- dual primary annotation present: yes
- adjudicated labels present: yes
- agreement summary present: yes
- import metadata present: yes
- evidence verification status: `ok`

## Headline Results

Primary confirmatory metrics on the `24` risk and `36` benign scenarios per condition:

| Condition | Risk disclosure | Benign false alarm | Score 3 on risk | Late disclosure on risk |
|---|---:|---:|---:|---:|
| `baseline` | `24/24 = 100.0%` | `0/36 = 0.0%` | `23/24 = 95.8%` | `9/24 = 37.5%` |
| `generic_control` | `24/24 = 100.0%` | `0/36 = 0.0%` | `22/24 = 91.7%` | `8/24 = 33.3%` |
| `disclosure_full` | `24/24 = 100.0%` | `6/36 = 16.7%` | `24/24 = 100.0%` | `7/24 = 29.2%` |

## Interpretation

What the locked run supports:

- the preregistered binary risk-disclosure endpoint saturated across all three conditions
- `disclosure_full` therefore showed no observed primary-endpoint gain over either bundled control
- strict full-disclosure and timeliness were directionally better under `disclosure_full`, but those are descriptive secondary outcomes only in this run

What remains a real caveat:

- the absolute benign guardrail failed because `16.7%` exceeds the preregistered `10%` threshold
- the comparative benign guardrail failed because `disclosure_full` produced `16.7` percentage points more benign false alarms than `generic_control`
- late disclosure remained non-trivial even under `disclosure_full`

Conservative decision wording:

> The final locked holdout-v3 run does not support a favorable tradeoff claim for the bundled disclosure-duty prompt on this bank for `gpt-5-mini`. The binary risk endpoint tied across all conditions, while `disclosure_full` introduced benign over-warning and still showed non-trivial late disclosure.

## What This Run Does Not Establish

- It does not show a primary-endpoint advantage for the intervention on this bank.
- It does not isolate a single causal mechanism within the bundled prompt.
- It does not justify cross-model generalization.
- It does not support a “clean win” framing, because benign and timeliness costs remain material.
