from __future__ import annotations

from pathlib import Path
from typing import Any

from anti_omission.client import openai_runtime_diagnostics
from anti_omission.io_utils import read_json, read_jsonl
from anti_omission.manifest import manifest_sha256
from anti_omission.runner import load_run_snapshot


def inspect_run_dir(run_dir: str | Path) -> dict[str, Any]:
    resolved = Path(run_dir).resolve()
    experiment_config, model_config, conditions, manifest_rows = load_run_snapshot(resolved)
    run_snapshot = read_json(resolved / "run_config.json")

    raw_requests_path = resolved / "raw_requests.jsonl"
    raw_responses_path = resolved / "raw_responses.jsonl"
    failures_path = resolved / "failures.jsonl"

    raw_requests_count = _jsonl_count(raw_requests_path)
    raw_responses_count = _jsonl_count(raw_responses_path)
    failures_count = _jsonl_count(failures_path)
    computed_manifest_sha256 = manifest_sha256(manifest_rows)
    recorded_manifest_sha256 = run_snapshot.get("manifest_sha256", "")
    openai_runtime = openai_runtime_diagnostics(model_config.api_env_var)
    runtime_ready = (
        True
        if experiment_config.client_mode == "mock"
        else bool(openai_runtime.get("runtime_ready"))
    )

    materiality_counts: dict[str, int] = {}
    split_counts: dict[str, int] = {}
    for row in manifest_rows:
        materiality_counts[row.materiality] = materiality_counts.get(row.materiality, 0) + 1
        split_counts[row.split] = split_counts.get(row.split, 0) + 1

    return {
        "run_dir": str(resolved),
        "run_id": resolved.name,
        "client_mode": experiment_config.client_mode,
        "model_id": model_config.model_id,
        "manifest_rows": len(manifest_rows),
        "manifest_sha256": computed_manifest_sha256,
        "manifest_sha256_matches_run_config": (
            computed_manifest_sha256 == recorded_manifest_sha256
            if recorded_manifest_sha256
            else None
        ),
        "condition_ids": sorted(conditions),
        "materiality_counts": materiality_counts,
        "split_counts": split_counts,
        "files": {
            "run_config": (resolved / "run_config.json").exists(),
            "manifest": (resolved / "manifest.jsonl").exists(),
            "raw_requests": raw_requests_path.exists(),
            "raw_responses": raw_responses_path.exists(),
            "failures": failures_path.exists(),
        },
        "raw_requests_count": raw_requests_count,
        "raw_responses_count": raw_responses_count,
        "failures_count": failures_count,
        "runtime_ready": runtime_ready,
        "ready_to_run": (
            raw_requests_count == 0
            and raw_responses_count == 0
            and failures_count == 0
            and runtime_ready
        ),
        "openai_runtime": openai_runtime,
    }


def _jsonl_count(path: Path) -> int:
    if not path.exists():
        return 0
    return len(read_jsonl(path))
