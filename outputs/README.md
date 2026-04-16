# Outputs

Run artifacts are written to `outputs/runs/` as append-only timestamped directories.

Canonical final run in this curated repository:

- `outputs/runs/20260414T225156Z_mainline-confirmatory-holdout-v3-live`

- `run_config.json`: snapshot of the resolved experiment, model, and condition text.
- `manifest.jsonl`: deterministic `scenario × condition` trial plan.
- `raw_requests.jsonl`: exact request inputs used for each trial.
- `raw_responses.jsonl`: immutable model outputs.
- `failures.jsonl`: explicit failed trial records.
- `labels/`: blind annotation exports and imported adjudicated labels.
- `analysis/`: descriptive summaries, condition-level rates, and excluded-trial audit files.
