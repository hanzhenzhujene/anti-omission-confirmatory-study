from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from anti_omission.config import ExperimentBundle
from anti_omission.io_utils import write_json, write_jsonl
from anti_omission.schemas import ManifestRow


def utc_now_string() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def timestamp_for_path() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def sanitize_run_name(run_name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "-", run_name.strip()).strip("-")
    return cleaned or "run"


def condition_code_map(condition_ids: list[str]) -> dict[str, str]:
    return {
        condition_id: f"C{index:02d}"
        for index, condition_id in enumerate(sorted(condition_ids), start=1)
    }


def build_trial_id(scenario_id: str, condition_id: str, model_id: str) -> str:
    payload = f"{scenario_id}|{condition_id}|{model_id}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


def build_manifest(bundle: ExperimentBundle) -> list[ManifestRow]:
    code_map = condition_code_map(list(bundle.conditions))
    rows: list[ManifestRow] = []
    for scenario_id in sorted(bundle.scenarios):
        scenario = bundle.scenarios[scenario_id]
        for condition_id in sorted(bundle.conditions):
            rows.append(
                ManifestRow(
                    trial_id=build_trial_id(
                        scenario_id=scenario_id,
                        condition_id=condition_id,
                        model_id=bundle.model_config.model_id,
                    ),
                    scenario_id=scenario_id,
                    condition_id=condition_id,
                    condition_code=code_map[condition_id],
                    model_id=bundle.model_config.model_id,
                    split=scenario.split,
                    family=scenario.family,
                    risk_class=scenario.risk_class,
                    materiality=scenario.materiality,
                    analysis_bucket=scenario.analysis_bucket,
                    scenario_path=str(bundle.scenario_paths[scenario_id]),
                    condition_path=str(bundle.condition_paths[condition_id]),
                )
            )
    return rows


def manifest_sha256(rows: list[ManifestRow]) -> str:
    digest = hashlib.sha256()
    for row in rows:
        digest.update(json.dumps(row.model_dump(), sort_keys=True).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def snapshot_run_config(bundle: ExperimentBundle, run_id: str, manifest_rows: list[ManifestRow] | None = None) -> dict:
    resolved_manifest = manifest_rows if manifest_rows is not None else build_manifest(bundle)
    codes = condition_code_map(list(bundle.conditions))
    return {
        "run_id": run_id,
        "created_at_utc": utc_now_string(),
        "experiment_config_path": str(bundle.experiment_config_path),
        "manifest_trial_count": len(resolved_manifest),
        "manifest_sha256": manifest_sha256(resolved_manifest),
        "experiment_config": bundle.experiment_config.model_dump(),
        "model_config": bundle.model_config.model_dump(),
        "conditions": [
            {
                **bundle.conditions[condition_id].model_dump(),
                "condition_code": codes[condition_id],
                "source_path": str(bundle.condition_paths[condition_id]),
            }
            for condition_id in sorted(bundle.conditions)
        ],
        "scenarios": [
            {
                "scenario_id": scenario_id,
                "split": bundle.scenarios[scenario_id].split,
                "analysis_bucket": bundle.scenarios[scenario_id].analysis_bucket,
                "source_path": str(bundle.scenario_paths[scenario_id]),
            }
            for scenario_id in sorted(bundle.scenarios)
        ],
    }


def initialize_run_dir(bundle: ExperimentBundle, run_dir: Optional[str | Path] = None) -> Path:
    if run_dir is None:
        run_name = sanitize_run_name(bundle.experiment_config.run_name)
        run_id = f"{timestamp_for_path()}_{run_name}"
        resolved = (Path(bundle.experiment_config.output_root) / run_id).resolve()
    else:
        resolved = Path(run_dir).resolve()
        run_id = resolved.name

    if resolved.exists() and any(resolved.iterdir()):
        raise FileExistsError(f"Run directory already exists and is not empty: {resolved}")

    resolved.mkdir(parents=True, exist_ok=True)
    manifest_rows = build_manifest(bundle)
    write_json(resolved / "run_config.json", snapshot_run_config(bundle, run_id, manifest_rows))
    write_jsonl(resolved / "manifest.jsonl", [row.model_dump() for row in manifest_rows])
    return resolved
