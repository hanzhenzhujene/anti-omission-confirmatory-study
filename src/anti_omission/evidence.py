from __future__ import annotations

import hashlib
from pathlib import Path

from anti_omission import __version__
from anti_omission.analysis import summarize_run
from anti_omission.io_utils import read_json, read_jsonl, write_json
from anti_omission.manifest import utc_now_string
from anti_omission.schemas import (
    ArtifactDigest,
    EvidencePackage,
    EvidenceProvenance,
    EvidenceVerificationArtifact,
    EvidenceVerificationReport,
)


REQUIRED_ARTIFACTS = (
    "run_config.json",
    "manifest.jsonl",
    "raw_requests.jsonl",
    "raw_responses.jsonl",
    "labels/final_labels.jsonl",
    "analysis/summary.json",
)

KNOWN_OPTIONAL_ARTIFACTS = (
    "failures.jsonl",
    "labels/annotation_export.csv",
    "labels/annotation_export_audit.csv",
    "labels/primary_labels.jsonl",
    "labels/adjudication_export.csv",
    "labels/adjudication_required.csv",
    "labels/adjudicated_labels.jsonl",
    "labels/import_metadata.json",
    "labels/import_metadata.primary.json",
    "labels/import_metadata.adjudicated.json",
    "labels/label_artifacts.json",
    "labels/agreement_summary.json",
    "labels/agreement_transition_rows.csv",
    "labels/finalization_report.json",
    "analysis/condition_rates.csv",
    "analysis/condition_rates_by_bucket.csv",
    "analysis/scenario_counts.csv",
    "analysis/family_condition_rates.csv",
    "analysis/timeliness_rates.csv",
    "analysis/sensitivity_rates.csv",
    "analysis/runtime_sensitivity_rates.csv",
    "analysis/paired_condition_contrasts.csv",
    "analysis/paired_discordance_tables.csv",
    "analysis/annotation_agreement_table.csv",
    "analysis/excluded_trials.csv",
    "analysis/paper_results_draft.md",
    "analysis/paper_manuscript_section_draft.md",
    "analysis/paper_full_manuscript_draft.md",
    "analysis/paper_full_manuscript_draft.tex",
    "analysis/paper_full_manuscript_draft.pdf",
    "analysis/paper_full_manuscript_submission.md",
    "analysis/paper_full_manuscript_submission.tex",
    "analysis/paper_full_manuscript_submission.pdf",
    "analysis/paper_full_manuscript_draft_assets/paper_figure_1_primary_tradeoff.pdf",
    "analysis/paper_full_manuscript_draft_assets/paper_figure_2_paired_scenario_matrix.pdf",
    "analysis/paper_full_manuscript_draft_assets/paper_figure_s1_timeliness.pdf",
    "analysis/paper_table_1_sample_composition.csv",
    "analysis/paper_table_2_condition_outcomes.csv",
    "analysis/paper_table_3_family_risk_disclosure.csv",
    "analysis/paper_table_s1_sensitivity_checks.csv",
    "analysis/paper_table_s2_paired_contrasts.csv",
    "analysis/paper_table_s3_effect_gaps.csv",
    "analysis/paper_table_s4_timeliness_decomposition.csv",
    "analysis/paper_table_s5_provenance_status.csv",
    "analysis/paper_table_s6_benign_family_false_alarms.csv",
    "analysis/paper_table_s7_incomplete_visible_audit.csv",
    "analysis/paper_table_s8_runtime_burden.csv",
    "analysis/paper_table_s9_representative_scenarios.csv",
    "analysis/paper_figure_1_primary_tradeoff.pdf",
    "analysis/paper_figure_1_primary_tradeoff.svg",
    "analysis/paper_figure_2_paired_scenario_matrix.csv",
    "analysis/paper_figure_2_paired_scenario_matrix.pdf",
    "analysis/paper_figure_2_paired_scenario_matrix.svg",
    "analysis/paper_figure_s1_timeliness.pdf",
    "analysis/paper_figure_s1_timeliness.svg",
)
SELF_EXCLUDED_ARTIFACTS = (
    "analysis/evidence_package.json",
    "analysis/evidence_verification.json",
    "analysis/evidence_index.md",
)
IGNORED_ARTIFACT_BASENAMES = {".DS_Store", "Thumbs.db"}


def package_evidence(
    run_dir: str | Path,
    output_path: str | Path | None = None,
) -> dict[str, Path]:
    resolved = Path(run_dir).resolve()
    summary = summarize_run(resolved)
    run_snapshot = read_json(resolved / "run_config.json")

    run_local_path = resolved / "analysis" / "evidence_package.json"
    repo_output_path = Path(output_path).resolve() if output_path else None
    excluded_paths = _excluded_paths_for_run(resolved, extra_paths=[repo_output_path])

    evidence = EvidencePackage(
        run_id=summary["run_id"],
        generated_from_run_dir=str(resolved),
        package_version=__version__,
        model_id=run_snapshot["model_config"]["model_id"],
        client_mode=run_snapshot["experiment_config"]["client_mode"],
        manifest_trial_count=len(read_jsonl(resolved / "manifest.jsonl")),
        final_label_row_count=summary["total_trials"],
        scored_trial_count=summary["scored_trials"],
        excluded_trial_count=summary["excluded_trials"],
        primary_risk_trial_count=summary["primary_risk_trials"],
        primary_benign_trial_count=summary["primary_benign_trials"],
        condition_ids=[condition["condition_id"] for condition in run_snapshot["conditions"]],
        guardrail_assessment=summary["guardrail_assessment"],
        provenance=_build_provenance(summary, resolved),
        caveats=_build_caveats(summary, resolved),
        artifacts=_inventory_artifacts(resolved, excluded_paths),
    )

    write_json(run_local_path, evidence.model_dump())

    outputs = {"run_local_path": run_local_path}
    if repo_output_path is not None:
        write_json(repo_output_path, evidence.model_dump())
        outputs["repo_output_path"] = repo_output_path
    return outputs


def verify_evidence(
    run_dir: str | Path,
    *,
    evidence_path: str | Path | None = None,
    output_path: str | Path | None = None,
) -> dict[str, Path | str]:
    resolved = Path(run_dir).resolve()
    package_path = Path(evidence_path).resolve() if evidence_path else resolved / "analysis" / "evidence_package.json"
    evidence = EvidencePackage.model_validate(read_json(package_path))
    run_snapshot = read_json(resolved / "run_config.json")

    run_local_path = resolved / "analysis" / "evidence_verification.json"
    repo_output_path = Path(output_path).resolve() if output_path else None
    excluded_paths = _excluded_paths_for_run(
        resolved,
        extra_paths=[package_path, run_local_path, repo_output_path],
    )

    artifact_checks = _verify_artifacts(
        run_dir=resolved,
        expected_artifacts=evidence.artifacts,
    )
    unexpected_artifacts = sorted(
        path.as_posix()
        for path in _discover_files(resolved, excluded_paths)
        if path.as_posix() not in {artifact.relative_path for artifact in evidence.artifacts}
    )
    mismatch_count = sum(
        1
        for check in artifact_checks
        if not (check.exists_match and check.size_match and check.sha256_match)
    )
    missing_required_count = sum(
        1
        for check in artifact_checks
        if check.required and not check.actual_exists
    )
    run_id_actual = run_snapshot["run_id"]
    run_id_match = run_id_actual == evidence.run_id
    status = (
        "ok"
        if mismatch_count == 0 and missing_required_count == 0 and not unexpected_artifacts and run_id_match
        else "drift_detected"
    )

    report = EvidenceVerificationReport(
        package_path=str(package_path),
        run_dir=str(resolved),
        run_id_expected=evidence.run_id,
        run_id_actual=run_id_actual,
        run_id_match=run_id_match,
        packaged_final_stage=evidence.provenance.final_stage,
        packaged_caveats=evidence.caveats,
        provenance_verdict=_provenance_verdict(evidence),
        verified_at_utc=utc_now_string(),
        status=status,
        artifact_count=len(artifact_checks),
        mismatch_count=mismatch_count,
        missing_required_count=missing_required_count,
        unexpected_artifacts=unexpected_artifacts,
        artifact_checks=artifact_checks,
    )

    write_json(run_local_path, report.model_dump())
    outputs: dict[str, Path | str] = {
        "run_local_path": run_local_path,
        "status": report.status,
    }
    if repo_output_path is not None:
        write_json(repo_output_path, report.model_dump())
        outputs["repo_output_path"] = repo_output_path
    return outputs


def draft_evidence_index(
    run_dir: str | Path,
    *,
    output_path: str | Path | None = None,
) -> dict[str, Path]:
    resolved = Path(run_dir).resolve()
    summary = summarize_run(resolved)
    run_snapshot = read_json(resolved / "run_config.json")
    evidence_package_path = resolved / "analysis" / "evidence_package.json"
    evidence_verification_path = resolved / "analysis" / "evidence_verification.json"

    if not evidence_package_path.exists():
        package_evidence(resolved)
    if not evidence_verification_path.exists():
        verify_evidence(resolved)

    evidence = EvidencePackage.model_validate(read_json(evidence_package_path))
    verification = EvidenceVerificationReport.model_validate(read_json(evidence_verification_path))

    run_local_path = resolved / "analysis" / "evidence_index.md"
    repo_output_path = Path(output_path).resolve() if output_path else None
    text = _build_evidence_index_markdown(
        run_dir=resolved,
        run_snapshot=run_snapshot,
        summary=summary,
        evidence=evidence,
        verification=verification,
    )

    run_local_path.parent.mkdir(parents=True, exist_ok=True)
    run_local_path.write_text(text, encoding="utf-8")
    outputs = {"run_local_path": run_local_path}
    if repo_output_path is not None:
        repo_output_path.parent.mkdir(parents=True, exist_ok=True)
        repo_output_path.write_text(text, encoding="utf-8")
        outputs["repo_output_path"] = repo_output_path
    return outputs


def _build_provenance(summary: dict, run_dir: Path) -> EvidenceProvenance:
    label_artifacts = summary.get("label_artifacts") or {}
    final_stage = label_artifacts.get("final_stage")
    if not final_stage:
        final_stage = _infer_final_stage(run_dir)

    return EvidenceProvenance(
        has_import_metadata=(
            (run_dir / "labels" / "import_metadata.json").exists()
            or (run_dir / "labels" / "import_metadata.primary.json").exists()
        ),
        has_label_artifacts_index=(run_dir / "labels" / "label_artifacts.json").exists(),
        has_primary_stage_labels=_has_primary_stage_labels(run_dir),
        has_adjudicated_stage_labels=(run_dir / "labels" / "adjudicated_labels.jsonl").exists(),
        has_agreement_summary=(run_dir / "labels" / "agreement_summary.json").exists(),
        final_stage=final_stage,
    )


def _infer_final_stage(run_dir: Path) -> str:
    has_primary = _has_primary_stage_labels(run_dir)
    primary_annotator_count = _primary_annotator_count(run_dir)
    has_adjudicated = (run_dir / "labels" / "adjudicated_labels.jsonl").exists()
    finalization_report_path = run_dir / "labels" / "finalization_report.json"
    if finalization_report_path.exists():
        report = read_json(finalization_report_path)
        final_stage = report.get("final_stage")
        if isinstance(final_stage, str) and final_stage:
            return final_stage
    if primary_annotator_count >= 2 and has_adjudicated:
        return "dual_primary_with_adjudication"
    if primary_annotator_count >= 2:
        return "dual_primary_only"
    if has_primary and has_adjudicated:
        return "merged_primary_adjudicated"
    if has_primary:
        return "primary_only"
    if has_adjudicated:
        return "adjudicated_only"
    if (run_dir / "labels" / "final_labels.jsonl").exists():
        return "legacy_final_only"
    return "unknown"


def _build_caveats(summary: dict, run_dir: Path) -> list[str]:
    caveats: list[str] = []

    if not (run_dir / "labels" / "import_metadata.json").exists():
        caveats.append("missing_label_import_metadata")
        caveats.append("import_provenance_incomplete")
    if not (run_dir / "labels" / "label_artifacts.json").exists():
        caveats.append("missing_label_artifacts_index")
    if not _has_primary_stage_labels(run_dir):
        caveats.append("missing_primary_stage_labels")
    if not (run_dir / "labels" / "adjudicated_labels.jsonl").exists():
        caveats.append("missing_adjudicated_stage_labels")
    if not (run_dir / "labels" / "agreement_summary.json").exists():
        caveats.append("no_paired_agreement_audit")
    if _infer_final_stage(run_dir) == "legacy_final_only":
        caveats.append("legacy_final_labels_only")
    if _infer_final_stage(run_dir) in {
        "primary_only",
        "dual_primary_only",
        "dual_primary_with_adjudication",
        "merged_primary_adjudicated",
        "adjudicated_only",
    }:
        caveats.append("final_consensus_not_fully_finalized")
    if summary["excluded_trials"] > 0:
        caveats.append("excluded_trials_present")
    if _guardrail_failed(summary, "absolute_benign_false_alarm"):
        caveats.append("absolute_benign_guardrail_failed")
    if _guardrail_failed(summary, "comparative_benign_false_alarm"):
        caveats.append("comparative_benign_guardrail_failed")
    if _late_disclosures_observed(summary):
        caveats.append("late_disclosures_observed")
    return caveats


def _guardrail_failed(summary: dict, key: str) -> bool:
    assessment = summary.get("guardrail_assessment", {})
    metric = assessment.get(key) or {}
    return bool(metric) and not bool(metric.get("passed"))


def _late_disclosures_observed(summary: dict) -> bool:
    for row in summary.get("timeliness_metrics", []):
        if row["timeliness"] == "late" and row["successes"] > 0:
            return True
    return False


def _inventory_artifacts(run_dir: Path, excluded_paths: set[Path]) -> list[ArtifactDigest]:
    discovered = _discover_files(run_dir, excluded_paths)
    known = {Path(path) for path in REQUIRED_ARTIFACTS}
    known.update(Path(path) for path in KNOWN_OPTIONAL_ARTIFACTS)
    all_paths = sorted(discovered | known, key=lambda path: path.as_posix())

    return [
        ArtifactDigest(
            relative_path=relative_path.as_posix(),
            category=_artifact_category(relative_path),
            required=relative_path.as_posix() in REQUIRED_ARTIFACTS,
            exists=(run_dir / relative_path).exists(),
            size_bytes=(run_dir / relative_path).stat().st_size if (run_dir / relative_path).exists() else 0,
            sha256=_sha256_file(run_dir / relative_path) if (run_dir / relative_path).exists() else "",
        )
        for relative_path in all_paths
        if relative_path not in excluded_paths
    ]


def _verify_artifacts(
    *,
    run_dir: Path,
    expected_artifacts: list[ArtifactDigest],
) -> list[EvidenceVerificationArtifact]:
    checks: list[EvidenceVerificationArtifact] = []
    for artifact in expected_artifacts:
        actual_path = run_dir / artifact.relative_path
        actual_exists = actual_path.exists()
        actual_size_bytes = actual_path.stat().st_size if actual_exists else 0
        actual_sha256 = _sha256_file(actual_path) if actual_exists else ""
        checks.append(
            EvidenceVerificationArtifact(
                relative_path=artifact.relative_path,
                category=artifact.category,
                required=artifact.required,
                expected_exists=artifact.exists,
                actual_exists=actual_exists,
                exists_match=(actual_exists == artifact.exists),
                expected_size_bytes=artifact.size_bytes,
                actual_size_bytes=actual_size_bytes,
                size_match=(actual_size_bytes == artifact.size_bytes),
                expected_sha256=artifact.sha256,
                actual_sha256=actual_sha256,
                sha256_match=(actual_sha256 == artifact.sha256),
            )
        )
    return checks


def _discover_files(run_dir: Path, excluded_paths: set[Path]) -> set[Path]:
    return {
        path.relative_to(run_dir)
        for path in run_dir.rglob("*")
        if path.is_file()
        and path.name not in IGNORED_ARTIFACT_BASENAMES
        and path.relative_to(run_dir) not in excluded_paths
    }


def _excluded_paths_for_run(run_dir: Path, extra_paths: list[Path | None] | None = None) -> set[Path]:
    excluded_paths = {Path(path) for path in SELF_EXCLUDED_ARTIFACTS}
    for extra_path in extra_paths or []:
        if extra_path is None:
            continue
        try:
            excluded_paths.add(extra_path.relative_to(run_dir))
        except ValueError:
            continue
    return excluded_paths


def _has_primary_stage_labels(run_dir: Path) -> bool:
    if (run_dir / "labels" / "primary_labels.jsonl").exists():
        return True
    primary_dir = run_dir / "labels" / "primary"
    return primary_dir.exists() and any(primary_dir.glob("*.jsonl"))


def _primary_annotator_count(run_dir: Path) -> int:
    primary_dir = run_dir / "labels" / "primary"
    if primary_dir.exists():
        return len(list(primary_dir.glob("*.jsonl")))
    return 1 if (run_dir / "labels" / "primary_labels.jsonl").exists() else 0


def _provenance_verdict(evidence: EvidencePackage) -> str:
    if evidence.provenance.final_stage == "legacy_final_only":
        return (
            "Verified byte-for-byte against a legacy final-only label package. "
            "Artifact integrity is clean, but stage-level label provenance remains incomplete."
        )
    if evidence.provenance.final_stage == "merged_primary_adjudicated":
        return (
            "Verified byte-for-byte against a staged primary-plus-adjudicated package."
        )
    if evidence.provenance.final_stage == "dual_primary_only":
        return (
            "Verified byte-for-byte against a dual-primary package with no adjudication stage yet."
        )
    if evidence.provenance.final_stage == "dual_primary_with_adjudication":
        return (
            "Verified byte-for-byte against a dual-primary package with adjudication artifacts, "
            "but the labels are not yet marked as fully finalized consensus."
        )
    if evidence.provenance.final_stage == "adjudicated_consensus_final":
        return (
            "Verified byte-for-byte against a finalized dual-primary-plus-adjudication consensus package."
        )
    if evidence.provenance.final_stage == "primary_only":
        return (
            "Verified byte-for-byte against a staged primary-only package."
        )
    if evidence.provenance.final_stage == "adjudicated_only":
        return (
            "Verified byte-for-byte against an adjudicated-only package."
        )
    return "Verified byte-for-byte against the current evidence package."


def _build_evidence_index_markdown(
    *,
    run_dir: Path,
    run_snapshot: dict,
    summary: dict,
    evidence: EvidencePackage,
    verification: EvidenceVerificationReport,
) -> str:
    repo_root = Path(__file__).resolve().parents[2]
    ordered_condition_ids = _preferred_condition_order(evidence.condition_ids)
    observed_snapshot_lines = [
        f"- `baseline` risk disclosure: `{_format_metric(summary, 'baseline', 'risk_disclosure')}`",
    ]
    if _has_condition_metric(summary, "generic_control", "risk_disclosure"):
        observed_snapshot_lines.append(
            f"- `generic_control` risk disclosure: `{_format_metric(summary, 'generic_control', 'risk_disclosure')}`"
        )
    observed_snapshot_lines.extend(
        [
            f"- `disclosure_full` risk disclosure: `{_format_metric(summary, 'disclosure_full', 'risk_disclosure')}`",
            f"- `disclosure_full` benign false alarms: `{_format_metric(summary, 'disclosure_full', 'benign_false_alarm')}`",
            f"- `disclosure_full` late risk disclosures: `{_format_timeliness_metric(summary, 'disclosure_full', 'late')}`",
        ]
    )
    lines = [
        f"# Confirmatory Evidence Index: {summary['run_id']}",
        "",
        "_This document is generated deterministically from run artifacts. Do not hand-edit it as a source of truth._",
        "",
        "## Status",
        "",
        f"- Run ID: `{summary['run_id']}`",
        f"- Subject model: `{run_snapshot['model_config']['model_id']}`",
        f"- Conditions: {', '.join(f'`{condition_id}`' for condition_id in ordered_condition_ids)}",
        f"- Trial count: `{summary['total_trials']}` total, `{summary['scored_trials']}` scored, `{summary['excluded_trials']}` excluded",
        f"- Evidence verification status: `{verification.status}`",
        f"- Provenance verdict: {verification.provenance_verdict}",
        "",
        "## Locked Pre-Run Artifacts",
        "",
        f"- Experiment config: `{_repo_relative_path(Path(run_snapshot['experiment_config_path']))}`",
        *_existing_repo_lines(
            repo_root,
            [
                Path("docs/main-experiment-freeze.md"),
                Path("docs/preregistration-template.md"),
                Path("docs/mainline-confirmatory-runbook.md"),
            ],
        ),
        "",
        "## Executed Run Artifacts",
        "",
        f"- Run directory: `{_repo_relative_path(run_dir)}`",
        f"- Run config snapshot: `{_repo_relative_path(run_dir / 'run_config.json')}`",
        f"- Manifest: `{_repo_relative_path(run_dir / 'manifest.jsonl')}`",
        f"- Raw requests: `{_repo_relative_path(run_dir / 'raw_requests.jsonl')}`",
        f"- Raw responses: `{_repo_relative_path(run_dir / 'raw_responses.jsonl')}`",
        f"- Final labels: `{_repo_relative_path(run_dir / 'labels' / 'final_labels.jsonl')}`",
        f"- Analysis summary: `{_repo_relative_path(run_dir / 'analysis' / 'summary.json')}`",
        f"- Evidence package: `{_repo_relative_path(run_dir / 'analysis' / 'evidence_package.json')}`",
        f"- Evidence verification: `{_repo_relative_path(run_dir / 'analysis' / 'evidence_verification.json')}`",
        "",
        "## Interpretive Docs",
        "",
        *_existing_repo_lines(
            repo_root,
            [
                Path("docs/generated/final_submission_manuscript_v1.md"),
                Path("docs/generated/final_submission_manuscript_v1.pdf"),
            ],
        ),
        f"- Run-local manuscript: `{_repo_relative_path(run_dir / 'analysis' / 'paper_full_manuscript_submission.md')}`",
        f"- Run-local PDF: `{_repo_relative_path(run_dir / 'analysis' / 'paper_full_manuscript_submission.pdf')}`",
        "",
        "## Observed Outcome Snapshot",
        "",
        *observed_snapshot_lines,
        "",
        "## Known Provenance Caveats",
        "",
    ]
    if evidence.caveats:
        lines.extend(f"- `{caveat}`" for caveat in evidence.caveats)
    else:
        lines.append("- None recorded in the current evidence package.")
    lines.extend(
        [
            "",
            "## Use Discipline",
            "",
            "- Treat this package as the main locked confirmatory evidence for the executed run identified above.",
            "- Do not reuse an inspected or executed confirmatory bank as if it were fresh.",
            (
                "- Byte-for-byte verification confirms artifact integrity, and this run also preserves staged primary, adjudicated, "
                "and finalized label provenance."
                if evidence.provenance.final_stage == "adjudicated_consensus_final"
                else "- Byte-for-byte verification does not, by itself, upgrade missing staged annotation provenance into stronger evidence."
            ),
        ]
    )
    return "\n".join(_collapse_blank_lines(lines)) + "\n"


def _existing_repo_lines(repo_root: Path, relative_paths: list[Path]) -> list[str]:
    lines: list[str] = []
    for relative_path in relative_paths:
        full_path = repo_root / relative_path
        if full_path.exists():
            lines.append(f"- `{_repo_relative_path(full_path)}`")
    return lines


def _repo_relative_path(path: Path) -> str:
    repo_root = Path(__file__).resolve().parents[2]
    try:
        return path.resolve().relative_to(repo_root).as_posix()
    except ValueError:
        return str(path.resolve())


def _format_metric(summary: dict, condition_id: str, metric: str) -> str:
    row = next(
        row
        for row in summary["condition_metrics"]
        if row["condition_id"] == condition_id and row["metric"] == metric
    )
    return f"{row['successes']}/{row['n']} ({row['proportion'] * 100:.1f}%)"


def _format_timeliness_metric(summary: dict, condition_id: str, timeliness: str) -> str:
    row = next(
        row
        for row in summary["timeliness_metrics"]
        if row["condition_id"] == condition_id and row["timeliness"] == timeliness
    )
    return f"{row['successes']}/{row['n']} ({row['proportion'] * 100:.1f}%)"


def _collapse_blank_lines(lines: list[str]) -> list[str]:
    collapsed: list[str] = []
    for line in lines:
        if line == "" and (not collapsed or collapsed[-1] == ""):
            continue
        collapsed.append(line)
    return collapsed


def _has_condition_metric(summary: dict, condition_id: str, metric: str) -> bool:
    return any(
        row["condition_id"] == condition_id and row["metric"] == metric
        for row in summary["condition_metrics"]
    )


def _preferred_condition_order(condition_ids: list[str]) -> list[str]:
    preferred = ["baseline", "generic_control", "disclosure_full", "disclosure_compact"]
    ordered = [condition_id for condition_id in preferred if condition_id in condition_ids]
    ordered.extend(condition_id for condition_id in condition_ids if condition_id not in ordered)
    return ordered


def _artifact_category(relative_path: Path) -> str:
    if relative_path.parts[0] == "labels":
        return "labels"
    if relative_path.parts[0] == "analysis":
        return "analysis"
    if relative_path.name in {"raw_requests.jsonl", "raw_responses.jsonl", "failures.jsonl"}:
        return "raw"
    return "run"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()
