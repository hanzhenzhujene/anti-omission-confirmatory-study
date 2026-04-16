from __future__ import annotations

from pathlib import Path

from anti_omission.analysis import summarize_run
from anti_omission.config import ConfigurationError, load_manuscript_spec_bundle
from anti_omission.evidence import draft_evidence_index, package_evidence, verify_evidence
from anti_omission.io_utils import read_json, write_json
from anti_omission.typesetting import typeset_full_manuscript


PLACEHOLDER_RUN_ID_PREFIXES = (
    "LOCK_AFTER_",
    "REPLACE_WITH_",
    "TBD",
    "UNSET",
)


def lock_manuscript_spec(
    run_dir: str | Path,
    manuscript_spec_path: str | Path,
    output_path: str | Path | None = None,
) -> dict[str, Path]:
    resolved_run_dir = Path(run_dir).resolve()
    summary = summarize_run(resolved_run_dir)
    spec_bundle = load_manuscript_spec_bundle(manuscript_spec_path)
    template_payload = read_json(spec_bundle.manuscript_spec_path)

    template_target = spec_bundle.manuscript_spec.target_run_id
    run_id = summary["run_id"]
    if not _target_can_be_locked(template_target, run_id):
        raise ConfigurationError(
            "manuscript spec already points at a different run_id and will not be rewritten: "
            f"{template_target} != {run_id}"
        )

    if spec_bundle.manuscript_spec.require_finalized_provenance:
        final_stage = (summary.get("label_artifacts") or {}).get("final_stage", "unknown")
        if final_stage != "adjudicated_consensus_final":
            raise ConfigurationError(
                "cannot lock a finalized-provenance manuscript spec to a run whose label package "
                f"is `{final_stage}`"
            )

    template_payload["target_run_id"] = run_id
    _normalize_locked_spec_paths(template_payload, spec_bundle.manuscript_spec_path)

    run_local_path = resolved_run_dir / "analysis" / _locked_spec_filename(spec_bundle.manuscript_spec_path)
    write_json(run_local_path, template_payload)

    outputs = {"run_local_path": run_local_path}
    if output_path is not None:
        repo_output_path = Path(output_path).resolve()
        write_json(repo_output_path, template_payload)
        outputs["repo_output_path"] = repo_output_path
    return outputs


def build_submission_bundle(
    run_dir: str | Path,
    manuscript_spec_path: str | Path,
    *,
    output_path: str | Path | None = None,
    locked_spec_output_path: str | Path | None = None,
) -> dict[str, Path]:
    locked_spec_outputs = lock_manuscript_spec(
        run_dir=run_dir,
        manuscript_spec_path=manuscript_spec_path,
        output_path=locked_spec_output_path,
    )
    locked_spec_path = locked_spec_outputs.get("repo_output_path", locked_spec_outputs["run_local_path"])

    summarize_run(run_dir)
    manuscript_outputs = typeset_full_manuscript(
        run_dir=run_dir,
        manuscript_spec_path=locked_spec_path,
        output_path=output_path,
    )
    evidence_outputs = package_evidence(run_dir)
    verification_outputs = verify_evidence(run_dir)
    if verification_outputs["status"] != "ok":
        raise RuntimeError(
            "submission bundle verification failed; inspect analysis/evidence_verification.json "
            "before using this run for paper generation"
        )
    evidence_index_outputs = draft_evidence_index(run_dir)

    outputs: dict[str, Path] = {
        "locked_spec_path": locked_spec_path,
        "evidence_package_path": evidence_outputs["run_local_path"],
        "evidence_verification_path": verification_outputs["run_local_path"],
        "evidence_index_path": evidence_index_outputs["run_local_path"],
    }
    outputs.update(manuscript_outputs)
    return outputs


def _target_can_be_locked(template_target: str, run_id: str) -> bool:
    if template_target == run_id:
        return True
    return any(template_target.startswith(prefix) for prefix in PLACEHOLDER_RUN_ID_PREFIXES)


def _locked_spec_filename(spec_path: Path) -> str:
    return f"{spec_path.stem}.locked.json"


def _normalize_locked_spec_paths(payload: dict[str, object], source_spec_path: Path) -> None:
    for field_name in (
        "repo_output_path",
        "introduction_fragment_path",
        "related_work_fragment_path",
        "discussion_fragment_path",
        "limitations_fragment_path",
        "ethics_fragment_path",
        "bibliography_path",
    ):
        raw_value = payload.get(field_name)
        if not isinstance(raw_value, str) or not raw_value:
            continue
        candidate = Path(raw_value)
        if candidate.is_absolute():
            continue
        payload[field_name] = str((source_spec_path.parent / candidate).resolve())
