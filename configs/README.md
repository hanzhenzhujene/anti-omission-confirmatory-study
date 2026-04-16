# Configs

This folder keeps only the canonical configs needed to understand, rerun, or verify the final confirmatory package.

## Canonical files

- `experiment/mainline_confirmatory_holdout_v3_live.json`
  The locked confirmatory experiment definition used for the final run.
- `reporting/final_submission_manuscript_v1.json`
  The paper-generation spec used for the final anonymous manuscript.
- `conditions/mainline_freeze_*.json`
  The frozen condition texts for `baseline`, `generic_control`, and `disclosure_full`.
- `model/openai_subject.json`
  The model/runtime default used for the subject-model client.

## Kept for engineering verification

- `experiment/dev_smoke.json`
  A tiny mock-first config used only for smoke tests.
