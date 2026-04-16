import csv
import json
import shutil
from pathlib import Path

from anti_omission.cli import main
from anti_omission.config import load_experiment_bundle
from anti_omission.evidence import draft_evidence_index, package_evidence, verify_evidence
from anti_omission.labeling import export_adjudication_csv, export_annotation_csv, import_labels_csv
from anti_omission.manifest import initialize_run_dir
from anti_omission.runner import execute_run


def _prepare_two_stage_run(tmp_path: Path) -> Path:
    bundle = load_experiment_bundle(Path("configs/experiment/dev_smoke.json"))
    run_dir = initialize_run_dir(bundle, tmp_path / "evidence-two-stage")
    execute_run(run_dir)
    export_annotation_csv(run_dir)

    with (run_dir / "labels" / "annotation_export.csv").open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        if row["analysis_status"] == "excluded":
            continue
        if row["materiality"] == "risk":
            row["ordinal_disclosure"] = "3" if row["condition_code"] == "C02" else "0"
            row["timeliness"] = "early" if row["condition_code"] == "C02" else "none"
            if row["condition_code"] == "C02":
                row["note"] = "Primary pass names the omitted risk."
        else:
            row["ordinal_disclosure"] = "0"
            row["timeliness"] = "none"
            row["false_alarm"] = "0"
    primary_csv = tmp_path / "primary_stage.csv"
    with primary_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    import_labels_csv(
        run_dir,
        primary_csv,
        stage="primary",
        annotator_id="annotator_a",
        annotator_type="human",
        blinding_mode="condition_code_blind",
    )

    adjudication_path = export_adjudication_csv(run_dir)
    with adjudication_path.open("r", encoding="utf-8", newline="") as handle:
        adjudication_rows = list(csv.DictReader(handle))
    target_row = next(row for row in adjudication_rows if row["trial_id"] == "bede371324dbf48a")
    target_row["final_analysis_status"] = "scored"
    target_row["final_ordinal_disclosure"] = "2"
    target_row["final_timeliness"] = "early"
    target_row["adjudication_note"] = "Adjudication upgrades this to a clear disclosure."
    adjudicated_csv = tmp_path / "adjudicated_stage.csv"
    with adjudicated_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=adjudication_rows[0].keys())
        writer.writeheader()
        writer.writerow(target_row)
    import_labels_csv(
        run_dir,
        adjudicated_csv,
        stage="adjudicated",
        annotator_id="adjudicator_a",
        annotator_type="human",
        blinding_mode="condition_code_blind",
        agreement_sample_design="targeted_adjudication_subset",
    )
    return run_dir


def test_package_evidence_writes_inventory_for_two_stage_run(tmp_path: Path) -> None:
    run_dir = _prepare_two_stage_run(tmp_path)
    (run_dir / ".DS_Store").write_text("finder-noise", encoding="utf-8")

    outputs = package_evidence(run_dir)

    payload = json.loads(outputs["run_local_path"].read_text(encoding="utf-8"))
    assert payload["provenance"]["final_stage"] == "merged_primary_adjudicated"
    assert payload["provenance"]["has_agreement_summary"] is True
    assert "analysis/evidence_package.json" not in {
        artifact["relative_path"] for artifact in payload["artifacts"]
    }

    artifact_map = {artifact["relative_path"]: artifact for artifact in payload["artifacts"]}
    assert artifact_map["labels/final_labels.jsonl"]["exists"] is True
    assert artifact_map["labels/final_labels.jsonl"]["sha256"]
    assert artifact_map["labels/agreement_summary.json"]["exists"] is True
    assert ".DS_Store" not in artifact_map


def test_package_evidence_captures_final_locked_run_provenance(tmp_path: Path) -> None:
    locked_run_source = Path(
        "outputs/runs/20260414T225156Z_mainline-confirmatory-holdout-v3-live"
    ).resolve()
    copied_run_dir = tmp_path / locked_run_source.name
    shutil.copytree(locked_run_source, copied_run_dir)

    outputs = package_evidence(copied_run_dir)
    payload = json.loads(outputs["run_local_path"].read_text(encoding="utf-8"))
    caveats = set(payload["caveats"])

    assert payload["provenance"]["final_stage"] == "adjudicated_consensus_final"
    assert payload["provenance"]["has_import_metadata"] is True
    assert payload["provenance"]["has_primary_stage_labels"] is True
    assert payload["provenance"]["has_adjudicated_stage_labels"] is True
    assert payload["provenance"]["has_agreement_summary"] is True
    assert "absolute_benign_guardrail_failed" in caveats
    assert "comparative_benign_guardrail_failed" in caveats
    assert "late_disclosures_observed" in caveats

    artifact_map = {artifact["relative_path"]: artifact for artifact in payload["artifacts"]}
    assert artifact_map["labels/primary_labels.jsonl"]["exists"] is True
    assert artifact_map["labels/final_labels.jsonl"]["exists"] is True


def test_cli_package_evidence_writes_run_local_and_optional_output(tmp_path: Path) -> None:
    run_dir = _prepare_two_stage_run(tmp_path)
    output_path = tmp_path / "stable_evidence.json"

    exit_code = main(
        [
            "package-evidence",
            "--run-dir",
            str(run_dir),
            "--output-path",
            str(output_path),
        ]
    )

    assert exit_code == 0
    assert output_path.exists()
    assert (run_dir / "analysis" / "evidence_package.json").exists()


def test_verify_evidence_reports_ok_for_fresh_package(tmp_path: Path) -> None:
    run_dir = _prepare_two_stage_run(tmp_path)
    package_evidence(run_dir)

    outputs = verify_evidence(run_dir)

    payload = json.loads(Path(outputs["run_local_path"]).read_text(encoding="utf-8"))
    assert payload["status"] == "ok"
    assert payload["mismatch_count"] == 0
    assert payload["unexpected_artifacts"] == []
    assert payload["packaged_final_stage"] == "merged_primary_adjudicated"
    assert "Verified byte-for-byte" in payload["provenance_verdict"]


def test_verify_evidence_detects_hash_drift_after_artifact_change(tmp_path: Path) -> None:
    run_dir = _prepare_two_stage_run(tmp_path)
    package_evidence(run_dir)

    summary_path = run_dir / "analysis" / "summary.json"
    summary_path.write_text(summary_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")

    outputs = verify_evidence(run_dir)

    payload = json.loads(Path(outputs["run_local_path"]).read_text(encoding="utf-8"))
    assert outputs["status"] == "drift_detected"
    assert payload["status"] == "drift_detected"
    assert payload["mismatch_count"] >= 1
    summary_check = next(
        item for item in payload["artifact_checks"] if item["relative_path"] == "analysis/summary.json"
    )
    assert summary_check["sha256_match"] is False


def test_cli_verify_evidence_returns_nonzero_on_drift(tmp_path: Path) -> None:
    run_dir = _prepare_two_stage_run(tmp_path)
    package_evidence(run_dir)

    raw_path = run_dir / "raw_responses.jsonl"
    raw_path.write_text(raw_path.read_text(encoding="utf-8") + " ", encoding="utf-8")
    output_path = tmp_path / "verification.json"

    exit_code = main(
        [
            "verify-evidence",
            "--run-dir",
            str(run_dir),
            "--output-path",
            str(output_path),
        ]
    )

    assert exit_code == 1
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["status"] == "drift_detected"


def test_draft_evidence_index_writes_run_local_and_repo_output(tmp_path: Path) -> None:
    run_dir = _prepare_two_stage_run(tmp_path)
    package_evidence(run_dir)
    verify_evidence(run_dir)
    output_path = tmp_path / "evidence_index.md"

    outputs = draft_evidence_index(run_dir, output_path=output_path)

    assert outputs["run_local_path"].exists()
    assert outputs["repo_output_path"].exists()
    text = output_path.read_text(encoding="utf-8")
    assert "# Confirmatory Evidence Index:" in text
    assert "Known Provenance Caveats" in text
    assert "Evidence verification status" in text


def test_cli_draft_evidence_index_smoke_check(tmp_path: Path) -> None:
    run_dir = _prepare_two_stage_run(tmp_path)
    package_evidence(run_dir)
    verify_evidence(run_dir)
    output_path = tmp_path / "cli_evidence_index.md"

    exit_code = main(
        [
            "draft-evidence-index",
            "--run-dir",
            str(run_dir),
            "--output-path",
            str(output_path),
        ]
    )

    assert exit_code == 0
    assert output_path.exists()
    assert (run_dir / "analysis" / "evidence_index.md").exists()
