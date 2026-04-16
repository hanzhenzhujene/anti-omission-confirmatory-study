import csv
import json
from pathlib import Path

import pytest

from anti_omission.analysis import summarize_run
from anti_omission.cli import main
from anti_omission.config import load_experiment_bundle
from anti_omission.io_utils import read_jsonl, write_jsonl
from anti_omission.labeling import (
    export_adjudication_csv,
    export_annotation_csv,
    finalize_labels,
    import_labels_csv,
)
from anti_omission.manifest import initialize_run_dir
from anti_omission.runner import execute_run


def _prepare_smoke_run(tmp_path: Path) -> Path:
    bundle = load_experiment_bundle(Path("configs/experiment/dev_smoke.json"))
    run_dir = initialize_run_dir(bundle, tmp_path / "label-run")
    execute_run(run_dir)
    export_annotation_csv(run_dir)
    return run_dir


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv_rows(path: Path, rows: list[dict[str, str]]) -> Path:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    return path


def _filled_primary_csv(export_path: Path, out_path: Path) -> Path:
    rows = _read_csv_rows(export_path)
    for row in rows:
        if row["analysis_status"] == "excluded":
            continue
        if row["materiality"] == "risk":
            if row["condition_code"] == "C02":
                row["ordinal_disclosure"] = "3"
                row["timeliness"] = "early"
                row["note"] = "Primary pass names the omitted risk and recommends pausing."
            else:
                row["ordinal_disclosure"] = "0"
                row["timeliness"] = "none"
        else:
            row["ordinal_disclosure"] = "0"
            row["timeliness"] = "none"
            row["false_alarm"] = "0"
    return _write_csv_rows(out_path, rows)


def test_export_and_import_adjudicated_labels_round_trip(tmp_path: Path) -> None:
    run_dir = _prepare_smoke_run(tmp_path)

    output_path = import_labels_csv(run_dir, Path("fixtures/dev_smoke_labels.csv"), stage="adjudicated")

    labels = read_jsonl(output_path)
    assert len(labels) == 4
    assert all(label["resolution_method"] == "adjudicated" for label in labels)
    assert any(
        label["condition_id"] == "disclosure_full" and label["binary_disclosure"] == 1
        for label in labels
    )

    artifacts = json.loads((run_dir / "labels" / "label_artifacts.json").read_text(encoding="utf-8"))
    assert artifacts["final_stage"] == "adjudicated_only"


def test_import_rejects_false_alarm_on_risk_items(tmp_path: Path) -> None:
    run_dir = _prepare_smoke_run(tmp_path)
    bad_csv = tmp_path / "bad_labels.csv"

    with Path("fixtures/dev_smoke_labels.csv").open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    for row in rows:
        if row["trial_id"] == "fff9813cb68d6d2f":
            row["false_alarm"] = "1"

    _write_csv_rows(bad_csv, rows)

    with pytest.raises(ValueError, match="risk scenarios must not include false_alarm"):
        import_labels_csv(run_dir, bad_csv, stage="adjudicated")


def test_primary_import_writes_stage_and_final_artifacts(tmp_path: Path) -> None:
    run_dir = _prepare_smoke_run(tmp_path)
    filled_csv = _filled_primary_csv(
        run_dir / "labels" / "annotation_export.csv",
        tmp_path / "primary_labels.csv",
    )

    output_path = import_labels_csv(
        run_dir,
        filled_csv,
        stage="primary",
        annotator_id="annotator_a",
        annotator_type="human",
        blinding_mode="condition_code_blind",
    )

    assert output_path == run_dir / "labels" / "final_labels.jsonl"
    assert (run_dir / "labels" / "primary_labels.jsonl").exists()
    assert not (run_dir / "labels" / "adjudicated_labels.jsonl").exists()

    artifacts = json.loads((run_dir / "labels" / "label_artifacts.json").read_text(encoding="utf-8"))
    assert artifacts["final_stage"] == "primary_only"
    assert artifacts["primary"]["blinding_mode"] == "condition_code_blind"


def test_export_adjudication_sheet_uses_primary_labels_and_blank_final_fields(tmp_path: Path) -> None:
    run_dir = _prepare_smoke_run(tmp_path)
    filled_csv = _filled_primary_csv(
        run_dir / "labels" / "annotation_export.csv",
        tmp_path / "primary_labels.csv",
    )
    import_labels_csv(
        run_dir,
        filled_csv,
        stage="primary",
        annotator_id="annotator_a",
        annotator_type="human",
    )

    adjudication_path = export_adjudication_csv(run_dir)
    rows = _read_csv_rows(adjudication_path)

    assert "condition_id" not in rows[0]
    assert "response_provider_status" not in rows[0]
    assert rows[0]["primary_a_analysis_status"] in {"scored", "excluded"}
    assert rows[0]["required_adjudication"] in {"0", "1"}
    visible_row = next(row for row in rows if row["primary_a_analysis_status"] == "scored")
    assert visible_row["primary_a_ordinal_disclosure"] != ""
    assert visible_row["primary_b_analysis_status"] == ""
    assert visible_row["final_ordinal_disclosure"] == ""


def test_adjudicated_subset_updates_final_and_agreement_summary(tmp_path: Path) -> None:
    run_dir = _prepare_smoke_run(tmp_path)
    filled_csv = _filled_primary_csv(
        run_dir / "labels" / "annotation_export.csv",
        tmp_path / "primary_labels.csv",
    )
    import_labels_csv(
        run_dir,
        filled_csv,
        stage="primary",
        annotator_id="annotator_a",
        annotator_type="human",
        blinding_mode="condition_code_blind",
    )

    adjudication_path = export_adjudication_csv(run_dir)
    rows = _read_csv_rows(adjudication_path)
    target_row = next(row for row in rows if row["trial_id"] == "bede371324dbf48a")
    target_row["final_analysis_status"] = "scored"
    target_row["final_ordinal_disclosure"] = "2"
    target_row["final_timeliness"] = "early"
    target_row["adjudication_note"] = "Adjudication upgrades this to a clear disclosure."
    subset_csv = _write_csv_rows(tmp_path / "adjudicated_subset.csv", [target_row])

    import_labels_csv(
        run_dir,
        subset_csv,
        stage="adjudicated",
        annotator_id="adjudicator_a",
        annotator_type="human",
        blinding_mode="condition_code_blind",
        agreement_sample_design="targeted_adjudication_subset",
    )

    final_labels = read_jsonl(run_dir / "labels" / "final_labels.jsonl")
    upgraded = next(label for label in final_labels if label["trial_id"] == "bede371324dbf48a")
    untouched = next(label for label in final_labels if label["trial_id"] == "3f72ee9093263087")
    agreement = json.loads((run_dir / "labels" / "agreement_summary.json").read_text(encoding="utf-8"))

    assert upgraded["resolution_method"] == "adjudicated"
    assert len(upgraded["source_label_ids"]) == 2
    assert upgraded["binary_disclosure"] == 1
    assert untouched["resolution_method"] == "single_primary"
    assert agreement["status"] == "available"
    assert agreement["overlap_row_count"] == 1
    assert agreement["n_changed_binary"] == 1
    assert agreement["agreement_sample_design"] == "targeted_adjudication_subset"


def test_dual_primary_finalize_requires_adjudication_for_disagreement(tmp_path: Path) -> None:
    run_dir = _prepare_smoke_run(tmp_path)
    filled_csv = _filled_primary_csv(
        run_dir / "labels" / "annotation_export.csv",
        tmp_path / "primary_labels_a.csv",
    )
    import_labels_csv(
        run_dir,
        filled_csv,
        stage="primary",
        annotator_id="annotator_a",
        annotator_type="human",
        blinding_mode="condition_code_blind",
    )

    rows = _read_csv_rows(filled_csv)
    target = next(row for row in rows if row["trial_id"] == "bede371324dbf48a")
    target["ordinal_disclosure"] = "2"
    target["timeliness"] = "early"
    target["note"] = "Second primary says this is a clear disclosure."
    second_csv = _write_csv_rows(tmp_path / "primary_labels_b.csv", rows)
    import_labels_csv(
        run_dir,
        second_csv,
        stage="primary",
        annotator_id="annotator_b",
        annotator_type="human",
        blinding_mode="condition_code_blind",
    )

    with pytest.raises(ValueError, match="required adjudication rows are still missing"):
        finalize_labels(run_dir)


def test_cli_finalize_labels_succeeds_for_consensus_dual_primary_run(tmp_path: Path) -> None:
    run_dir = _prepare_smoke_run(tmp_path)
    filled_csv = _filled_primary_csv(
        run_dir / "labels" / "annotation_export.csv",
        tmp_path / "primary_labels_a.csv",
    )
    import_labels_csv(
        run_dir,
        filled_csv,
        stage="primary",
        annotator_id="annotator_a",
        annotator_type="human",
        blinding_mode="condition_code_blind",
    )
    import_labels_csv(
        run_dir,
        filled_csv,
        stage="primary",
        annotator_id="annotator_b",
        annotator_type="human",
        blinding_mode="condition_code_blind",
    )

    exit_code = main(["finalize-labels", "--run-dir", str(run_dir)])

    assert exit_code == 0
    artifacts = json.loads((run_dir / "labels" / "label_artifacts.json").read_text(encoding="utf-8"))
    report = json.loads((run_dir / "labels" / "finalization_report.json").read_text(encoding="utf-8"))
    assert artifacts["final_stage"] == "adjudicated_consensus_final"
    assert report["status"] == "finalized"

    summary = summarize_run(run_dir)
    assert summary["model_id"] == "gpt-5-mini"
    assert summary["agreement_summary"]["covered_required_adjudication_row_count"] == report["covered_required_adjudication_row_count"]
    assert summary["agreement_summary"]["missing_required_adjudication_row_count"] == report["missing_required_adjudication_row_count"]


def test_summary_reports_expected_condition_rates(tmp_path: Path) -> None:
    run_dir = _prepare_smoke_run(tmp_path)
    import_labels_csv(run_dir, Path("fixtures/dev_smoke_labels.csv"), stage="adjudicated")

    summary = summarize_run(run_dir)

    metrics = {
        (row["condition_id"], row["metric"]): row
        for row in summary["condition_metrics"]
    }
    assert metrics[("baseline", "risk_disclosure")]["successes"] == 0
    assert metrics[("disclosure_full", "risk_disclosure")]["successes"] == 1
    assert metrics[("baseline", "benign_false_alarm")]["successes"] == 0
    assert summary["guardrail_assessment"]["absolute_benign_false_alarm"]["passed"] is True
    assert summary["label_artifacts"]["final_stage"] == "adjudicated_only"
    assert summary["agreement_summary"]["status"] == "unavailable"


def test_summary_writes_planned_breakdown_and_sensitivity_outputs(tmp_path: Path) -> None:
    run_dir = _prepare_smoke_run(tmp_path)
    import_labels_csv(run_dir, Path("fixtures/dev_smoke_labels.csv"), stage="adjudicated")

    summary = summarize_run(run_dir)

    assert len(summary["scenario_counts"]) == 2
    assert len(summary["family_condition_metrics"]) == 2
    assert len(summary["timeliness_metrics"]) == 6
    assert len(summary["sensitivity_metrics"]) == 6
    assert len(summary["runtime_sensitivity_metrics"]) == 4
    assert len(summary["paired_condition_contrasts"]) == 2

    analysis_dir = run_dir / "analysis"
    expected_outputs = [
        "scenario_counts.csv",
        "family_condition_rates.csv",
        "timeliness_rates.csv",
        "sensitivity_rates.csv",
        "runtime_sensitivity_rates.csv",
        "paired_condition_contrasts.csv",
    ]
    for filename in expected_outputs:
        assert (analysis_dir / filename).exists()


def test_export_prefills_excluded_status_for_no_visible_output(tmp_path: Path) -> None:
    run_dir = _prepare_smoke_run(tmp_path)
    raw_responses = read_jsonl(run_dir / "raw_responses.jsonl")
    for row in raw_responses:
        if row["trial_id"] == "bede371324dbf48a":
            row["response_text"] = ""
            row["provider_status"] = "incomplete"
            row["incomplete_reason"] = "max_output_tokens"
            row["response_has_output_text"] = False
    write_jsonl(run_dir / "raw_responses.jsonl", raw_responses)

    export_path = export_annotation_csv(run_dir)
    audit_export_path = run_dir / "labels" / "annotation_export_audit.csv"

    rows = _read_csv_rows(export_path)
    audit_rows = _read_csv_rows(audit_export_path)

    excluded_row = next(row for row in rows if row["trial_id"] == "bede371324dbf48a")
    audit_row = next(row for row in audit_rows if row["trial_id"] == "bede371324dbf48a")
    assert excluded_row["analysis_status"] == "excluded"
    assert "response_has_output_text" not in excluded_row
    assert audit_row["response_has_output_text"] == "0"


def test_export_keeps_runtime_status_out_of_scorer_csv(tmp_path: Path) -> None:
    run_dir = _prepare_smoke_run(tmp_path)

    export_path = export_annotation_csv(run_dir)
    audit_export_path = run_dir / "labels" / "annotation_export_audit.csv"

    with export_path.open("r", encoding="utf-8", newline="") as handle:
        scorer_fieldnames = csv.DictReader(handle).fieldnames or []
    with audit_export_path.open("r", encoding="utf-8", newline="") as handle:
        audit_fieldnames = csv.DictReader(handle).fieldnames or []

    assert "response_provider_status" not in scorer_fieldnames
    assert "response_incomplete_reason" not in scorer_fieldnames
    assert "response_has_output_text" not in scorer_fieldnames
    assert "response_provider_status" in audit_fieldnames
    assert "response_incomplete_reason" in audit_fieldnames
    assert "response_has_output_text" in audit_fieldnames


def test_export_rejects_runs_that_failed_before_any_raw_response(tmp_path: Path) -> None:
    bundle = load_experiment_bundle(Path("configs/experiment/dev_smoke.json"))
    run_dir = initialize_run_dir(bundle, tmp_path / "failed-run")
    (run_dir / "failures.jsonl").write_text(
        '{"trial_id":"abc","error_type":"AuthenticationError","error_message":"bad key"}\n',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="failed before completion"):
        export_annotation_csv(run_dir)


def test_import_allows_excluded_rows_with_blank_scores(tmp_path: Path) -> None:
    run_dir = _prepare_smoke_run(tmp_path)
    raw_responses = read_jsonl(run_dir / "raw_responses.jsonl")
    for row in raw_responses:
        if row["trial_id"] == "bede371324dbf48a":
            row["response_text"] = ""
            row["provider_status"] = "incomplete"
            row["incomplete_reason"] = "max_output_tokens"
            row["response_has_output_text"] = False
    write_jsonl(run_dir / "raw_responses.jsonl", raw_responses)

    export_path = export_annotation_csv(run_dir)
    filled_csv = _filled_primary_csv(export_path, tmp_path / "labels_with_exclusion.csv")

    output_path = import_labels_csv(
        run_dir,
        filled_csv,
        stage="primary",
        annotator_id="annotator_a",
        annotator_type="human",
    )
    imported = [json.loads(line) for line in output_path.read_text().splitlines() if line.strip()]
    excluded_label = next(row for row in imported if row["trial_id"] == "bede371324dbf48a")
    assert excluded_label["analysis_status"] == "excluded"


def test_import_rejects_manual_exclusion_for_visible_output_rows(tmp_path: Path) -> None:
    run_dir = _prepare_smoke_run(tmp_path)
    rows = _read_csv_rows(run_dir / "labels" / "annotation_export.csv")
    visible_row = next(row for row in rows if row["analysis_status"] == "scored")
    visible_row["analysis_status"] = "excluded"
    bad_csv = _write_csv_rows(tmp_path / "manual_exclusion.csv", rows)

    with pytest.raises(ValueError, match="Visible-output rows cannot be manually excluded"):
        import_labels_csv(
            run_dir,
            bad_csv,
            stage="primary",
            annotator_id="annotator_a",
            annotator_type="human",
        )


def test_import_writes_stage_specific_metadata(tmp_path: Path) -> None:
    run_dir = _prepare_smoke_run(tmp_path)
    filled_csv = _filled_primary_csv(
        run_dir / "labels" / "annotation_export.csv",
        tmp_path / "primary_labels.csv",
    )

    import_labels_csv(
        run_dir,
        filled_csv,
        stage="primary",
        annotator_id="annotator_a",
        annotator_type="human",
        blinding_mode="condition_code_blind",
    )

    metadata = json.loads((run_dir / "labels" / "import_metadata.primary.json").read_text(encoding="utf-8"))
    assert metadata["stage"] == "primary"
    assert metadata["annotator_id"] == "annotator_a"
    assert metadata["artifact_metadata"]["blinding_mode"] == "condition_code_blind"
    assert Path(metadata["import_copy_path"]).exists()
