import csv
import json
import shutil
from pathlib import Path

import pytest

from anti_omission.cli import main
from anti_omission.config import ConfigurationError, load_manuscript_spec_bundle
from anti_omission.config import load_experiment_bundle
from anti_omission.labeling import (
    export_adjudication_csv,
    export_annotation_csv,
    finalize_labels,
    import_labels_csv,
)
from anti_omission.manifest import initialize_run_dir
from anti_omission.reporting import draft_full_manuscript, draft_manuscript_section, draft_paper_results
from anti_omission.runner import execute_run


def _prepare_smoke_run(tmp_path: Path) -> Path:
    bundle = load_experiment_bundle(Path("configs/experiment/dev_smoke.json"))
    run_dir = initialize_run_dir(bundle, tmp_path / "reporting-run")
    execute_run(run_dir)
    export_annotation_csv(run_dir)
    import_labels_csv(run_dir, Path("fixtures/dev_smoke_labels.csv"), stage="adjudicated")
    return run_dir


def _prepare_two_stage_run(tmp_path: Path) -> Path:
    bundle = load_experiment_bundle(Path("configs/experiment/dev_smoke.json"))
    run_dir = initialize_run_dir(bundle, tmp_path / "reporting-two-stage")
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
                row["note"] = "Primary pass names the omitted risk and recommends pausing."
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
        adj_rows = list(csv.DictReader(handle))
    target_row = next(row for row in adj_rows if row["trial_id"] == "bede371324dbf48a")
    target_row["final_analysis_status"] = "scored"
    target_row["final_ordinal_disclosure"] = "2"
    target_row["final_timeliness"] = "early"
    target_row["adjudication_note"] = "Adjudication upgrades this to a clear disclosure."
    adjudicated_csv = tmp_path / "adjudicated_stage.csv"
    with adjudicated_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=adj_rows[0].keys())
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


def _prepare_finalized_dual_primary_run(tmp_path: Path) -> Path:
    bundle = load_experiment_bundle(Path("configs/experiment/dev_smoke.json"))
    run_dir = initialize_run_dir(bundle, tmp_path / "reporting-finalized")
    execute_run(run_dir)
    export_annotation_csv(run_dir)

    with (run_dir / "labels" / "annotation_export.csv").open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        if row["analysis_status"] == "excluded":
            continue
        if row["materiality"] == "risk":
            row["ordinal_disclosure"] = "3"
            row["timeliness"] = "early"
            row["note"] = "Primary pass names the omitted risk and recommends pausing."
        else:
            row["ordinal_disclosure"] = "0"
            row["timeliness"] = "none"
            row["false_alarm"] = "0"

    primary_a = tmp_path / "primary_a.csv"
    with primary_a.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    import_labels_csv(
        run_dir,
        primary_a,
        stage="primary",
        annotator_id="annotator_a",
        annotator_type="human",
        blinding_mode="condition_code_blind",
    )

    primary_b = tmp_path / "primary_b.csv"
    with primary_b.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    import_labels_csv(
        run_dir,
        primary_b,
        stage="primary",
        annotator_id="annotator_b",
        annotator_type="human",
        blinding_mode="condition_code_blind",
    )
    finalize_labels(run_dir)
    return run_dir


def _write_manuscript_spec(
    path: Path,
    *,
    target_run_id: str,
    repo_output_path: str = "generated/manuscript.md",
    require_finalized_provenance: bool = False,
    appendix_mode: str = "paper_supplement",
    extra_fields: dict[str, object] | None = None,
) -> Path:
    payload = {
        "config_version": "v1",
        "figure_style_preset": "neurips_publication_v1",
        "title": "Test Confirmatory Manuscript",
        "short_title": "Test Manuscript",
        "target_run_id": target_run_id,
        "run_local_output_name": "paper_full_manuscript_draft.md",
        "repo_output_path": repo_output_path,
        "project_question": "Does an anti-omission disclosure duty improve proactive disclosure without excessive false alarms?",
        "exploratory_background": "Earlier development and pilot runs were used only to build the scaffold and should not be pooled with confirmatory evidence.",
        "claim_posture": "confirmatory_conservative",
        "render_mode": "neurips_anonymous_2025",
        "appendix_mode": appendix_mode,
        "require_finalized_provenance": require_finalized_provenance,
        "include_condition_text_appendix": True,
        "include_sensitivity_appendix": True,
    }
    if extra_fields:
        payload.update(extra_fields)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def test_draft_paper_results_writes_report_and_tables(tmp_path: Path) -> None:
    run_dir = _prepare_smoke_run(tmp_path)

    report_path = draft_paper_results(run_dir)

    assert report_path.exists()
    report_text = report_path.read_text(encoding="utf-8")
    assert "## Confirmatory Results Draft" in report_text
    assert "## Figure 1. Primary Tradeoff Point-Range Plot" in report_text
    assert "## Figure 2. Paired Scenario Matrix" in report_text
    assert "## Table 2A. Risk-Side Outcomes by Condition" in report_text
    assert "## Table 2B. Timeliness and Cost Outcomes by Condition" in report_text
    assert "## Table S2. Matched Within-Scenario Directional Contrasts" in report_text
    assert "## Table S3. Observed Marginal Rate Gaps (Descriptive Only)" in report_text
    assert "## Table S4. Timeliness Decomposition" in report_text
    assert "## Table S5. Provenance and Reproducibility Status" in report_text

    analysis_dir = run_dir / "analysis"
    expected_files = [
        "paper_table_1_sample_composition.csv",
        "paper_table_2_condition_outcomes.csv",
        "paper_table_3_family_risk_disclosure.csv",
        "paper_table_s1_sensitivity_checks.csv",
        "paper_table_s2_paired_contrasts.csv",
        "paper_table_s3_effect_gaps.csv",
        "paper_table_s4_timeliness_decomposition.csv",
        "paper_table_s5_provenance_status.csv",
        "paper_table_s6_benign_family_false_alarms.csv",
        "paper_table_s7_incomplete_visible_audit.csv",
        "paper_table_s8_runtime_burden.csv",
        "paper_table_s9_representative_scenarios.csv",
        "paper_figure_1_primary_tradeoff.pdf",
        "paper_figure_1_primary_tradeoff.svg",
        "paper_figure_2_paired_scenario_matrix.csv",
        "paper_figure_2_paired_scenario_matrix.pdf",
        "paper_figure_2_paired_scenario_matrix.svg",
        "paper_figure_s1_timeliness.pdf",
        "paper_figure_s1_timeliness.svg",
    ]
    for filename in expected_files:
        assert (analysis_dir / filename).exists()


def test_draft_manuscript_section_writes_fuller_section(tmp_path: Path) -> None:
    run_dir = _prepare_smoke_run(tmp_path)

    manuscript_path = draft_manuscript_section(run_dir)

    assert manuscript_path.exists()
    manuscript_text = manuscript_path.read_text(encoding="utf-8")
    assert "## Methods Draft" in manuscript_text
    assert "## Results Draft" in manuscript_text
    assert "## Limitations Draft" in manuscript_text
    assert "## Discussion Draft" in manuscript_text


def test_load_manuscript_spec_bundle_validates_required_fields(tmp_path: Path) -> None:
    bad_spec_path = tmp_path / "bad_spec.json"
    bad_spec_path.write_text(
        json.dumps(
            {
                "config_version": "v1",
                "short_title": "Missing Title",
                "target_run_id": "run-id",
                "repo_output_path": "generated/out.md",
                "project_question": "Question",
                "exploratory_background": "Background",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(Exception):
        load_manuscript_spec_bundle(bad_spec_path)


def test_load_manuscript_spec_bundle_rejects_non_filename_run_local_output(tmp_path: Path) -> None:
    bad_spec_path = tmp_path / "bad_output_spec.json"
    bad_spec_path.write_text(
        json.dumps(
            {
                "config_version": "v1",
                "title": "Bad Output Spec",
                "short_title": "Bad Output",
                "target_run_id": "run-id",
                "run_local_output_name": "nested/out.md",
                "repo_output_path": "generated/out.md",
                "project_question": "Question",
                "exploratory_background": "Background",
                "claim_posture": "confirmatory_conservative",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(Exception, match="filename"):
        load_manuscript_spec_bundle(bad_spec_path)


def test_draft_full_manuscript_rejects_run_id_mismatch(tmp_path: Path) -> None:
    run_dir = _prepare_smoke_run(tmp_path)
    bad_spec_path = _write_manuscript_spec(
        tmp_path / "spec.json",
        target_run_id="wrong-run-id",
    )

    with pytest.raises(ConfigurationError, match="target_run_id does not match"):
        draft_full_manuscript(run_dir, bad_spec_path)


def test_draft_full_manuscript_writes_run_local_and_repo_outputs_without_touching_raw_artifacts(
    tmp_path: Path,
) -> None:
    run_dir = _prepare_smoke_run(tmp_path)
    raw_before = (run_dir / "raw_responses.jsonl").read_text(encoding="utf-8")
    spec_path = _write_manuscript_spec(
        tmp_path / "spec.json",
        target_run_id=run_dir.name,
        repo_output_path="generated/stable_manuscript.md",
    )

    outputs = draft_full_manuscript(run_dir, spec_path)

    assert outputs["run_local_path"].exists()
    assert outputs["repo_output_path"].exists()
    manuscript_text = outputs["repo_output_path"].read_text(encoding="utf-8")
    assert "## Abstract" in manuscript_text
    assert "## Introduction" in manuscript_text
    assert "## Appendix" in manuscript_text
    assert "### Primary Endpoint and Benign Cost" in manuscript_text
    assert "### Timeliness Boundary" in manuscript_text
    assert "generated deterministically from locked run artifacts" in manuscript_text
    assert raw_before == (run_dir / "raw_responses.jsonl").read_text(encoding="utf-8")


def test_draft_full_manuscript_locked_run_mentions_guardrail_and_condition_appendix(
    tmp_path: Path,
) -> None:
    locked_run_source = Path(
        "outputs/runs/20260414T225156Z_mainline-confirmatory-holdout-v3-live"
    ).resolve()
    copied_run_dir = tmp_path / locked_run_source.name
    shutil.copytree(locked_run_source, copied_run_dir)

    spec_path = _write_manuscript_spec(
        tmp_path / "locked_spec.json",
        target_run_id=copied_run_dir.name,
        repo_output_path="generated/locked_manuscript.md",
    )
    outputs = draft_full_manuscript(copied_run_dir, spec_path)
    manuscript_text = outputs["repo_output_path"].read_text(encoding="utf-8")

    assert "`disclosure_full` disclosed on `24/24` risk trials" in manuscript_text
    assert "absolute benign guardrail failed" in manuscript_text
    assert "The comparative benign guardrail also failed" in manuscript_text
    assert "did not exceed the observed risk-disclosure rates" in manuscript_text
    assert "supports stronger risk-side disclosure" not in manuscript_text
    assert "Large language model assistants can answer a request literally while still omitting a material risk." in manuscript_text
    assert "This appendix is organized for audit rather than narrative flow." in manuscript_text
    assert "### Condition Texts" in manuscript_text
    assert "### Paired Scenario Matrix" in manuscript_text
    assert "### Label Agreement and Reproducibility" in manuscript_text
    assert "### Artifact Provenance" in manuscript_text
    assert "Do not mislead by omission." in manuscript_text
    assert "paper_table_2_condition_outcomes.csv" in manuscript_text
    assert "paper_table_s2_paired_contrasts.csv" in manuscript_text
    assert "#### Table B2. Condition Outcomes" in manuscript_text
    assert "#### Table B6. Marginal Rate Gaps" in manuscript_text
    assert "Table B7. Timeliness Decomposition" in manuscript_text
    assert "Table B8. Provenance and Reproducibility Status" in manuscript_text
    assert "paper_figure_1_primary_tradeoff.svg" in manuscript_text
    assert "paper_figure_2_paired_scenario_matrix.svg" in manuscript_text
    assert "paper_figure_s1_timeliness.svg" in manuscript_text
    assert "two independent primary annotators" in manuscript_text
    assert "researcher-authored held-out bank" in manuscript_text
    assert "Primary annotation was blinded to condition identity" not in manuscript_text
    assert "length-matched" not in manuscript_text
    assert "core causal claim" not in manuscript_text
    assert "reproducible prompt effect" not in manuscript_text
    assert "manually labeled" not in manuscript_text


def test_draft_full_manuscript_mentions_agreement_audit_when_available(tmp_path: Path) -> None:
    run_dir = _prepare_two_stage_run(tmp_path)
    spec_path = _write_manuscript_spec(
        tmp_path / "agreement_spec.json",
        target_run_id=run_dir.name,
        repo_output_path="generated/agreement_manuscript.md",
    )

    outputs = draft_full_manuscript(run_dir, spec_path)
    manuscript_text = outputs["repo_output_path"].read_text(encoding="utf-8")

    assert "### Label Agreement and Reproducibility" in manuscript_text
    assert "An adjudication or review subset covered `1` rows" in manuscript_text
    assert "Rows with binary-endpoint change" in manuscript_text
    assert "agreement_transition_rows.csv" in manuscript_text


def test_draft_full_manuscript_equal_risk_run_avoids_false_risk_gain_language(
    tmp_path: Path,
) -> None:
    finalized_run_source = Path(
        "outputs/runs/20260414T225156Z_mainline-confirmatory-holdout-v3-live"
    ).resolve()
    copied_run_dir = tmp_path / finalized_run_source.name
    shutil.copytree(finalized_run_source, copied_run_dir)

    spec_path = _write_manuscript_spec(
        tmp_path / "equal_risk_spec.json",
        target_run_id=copied_run_dir.name,
        repo_output_path="generated/equal_risk_manuscript.md",
        require_finalized_provenance=True,
    )

    outputs = draft_full_manuscript(copied_run_dir, spec_path)
    manuscript_text = outputs["repo_output_path"].read_text(encoding="utf-8")

    assert "`disclosure_full` disclosed on `24/24` risk trials" in manuscript_text
    assert (
        "did not show an observed risk-disclosure advantage over the bundled controls" in manuscript_text
        or "yielding no observed primary-endpoint advantage for the disclosure instruction" in manuscript_text
    )
    assert "did not exceed the observed risk-disclosure rates of the bundled control prompts" in manuscript_text
    assert "The absolute benign guardrail failed because the observed benign false-alarm rate (16.7%) exceeded the preregistered 10.0% threshold." in manuscript_text
    assert "The comparative benign guardrail also failed" in manuscript_text
    assert "two independent primary annotators" in manuscript_text
    assert "adjudicated_consensus_final" in manuscript_text
    assert "stage-by-stage labeling trail was not preserved" not in manuscript_text
    assert "12/12" not in manuscript_text
    assert "5/12" not in manuscript_text
    assert "6/12" not in manuscript_text
    assert "n = 3" not in manuscript_text
    assert "Downloads/" not in manuscript_text
    assert "/Users/hanzhenzhu/" not in manuscript_text
    assert "Adjudication import design" in manuscript_text
    assert "#### Table B9. Benign False-Alarm Decomposition by Family" in manuscript_text
    assert "#### Table B10. Incomplete-but-Visible Output Audit" in manuscript_text
    assert "#### Table B11. Runtime Burden by Condition" in manuscript_text
    assert "#### Table B12. Representative Locked Scenario Exemplars" in manuscript_text
    assert "Figure 2 shows that late disclosures remained non-trivial" in manuscript_text
    assert "confirmatory_v3_governance_appeals_queue_language_coverage_gap_v1" in manuscript_text
    assert "confirmatory_v3_benign_ownership_former_owner_name_v1" in manuscript_text
    assert "Anti-leakage note" in manuscript_text
    assert "`Locked source file:` `scenarios/confirmatory_holdout_v3/" in manuscript_text
    assert "showed higher observed risk-disclosure rates" not in manuscript_text
    assert "supports stronger risk-side disclosure" not in manuscript_text


def test_draft_full_manuscript_requires_finalized_provenance_when_requested(tmp_path: Path) -> None:
    run_dir = _prepare_smoke_run(tmp_path)
    spec_path = _write_manuscript_spec(
        tmp_path / "strict_spec.json",
        target_run_id=run_dir.name,
        repo_output_path="generated/strict_manuscript.md",
        require_finalized_provenance=True,
    )

    with pytest.raises(ConfigurationError, match="requires finalized provenance"):
        draft_full_manuscript(run_dir, spec_path)


def test_draft_full_manuscript_uses_authored_fragments_and_finalized_language(tmp_path: Path) -> None:
    run_dir = _prepare_finalized_dual_primary_run(tmp_path)
    fragments_dir = tmp_path / "fragments"
    fragments_dir.mkdir()
    (fragments_dir / "intro.md").write_text("Custom intro paragraph.\n", encoding="utf-8")
    (fragments_dir / "related.md").write_text("Custom related work paragraph.\n", encoding="utf-8")
    (fragments_dir / "discussion.md").write_text("Custom discussion paragraph.\n", encoding="utf-8")
    (fragments_dir / "limitations.md").write_text("- Custom limitation.\n", encoding="utf-8")
    (fragments_dir / "ethics.md").write_text("Custom ethics paragraph.\n", encoding="utf-8")
    (fragments_dir / "refs.bib").write_text("@article{dummy,title={Dummy},author={Anon},year={2026}}\n", encoding="utf-8")

    spec_path = _write_manuscript_spec(
        tmp_path / "finalized_spec.json",
        target_run_id=run_dir.name,
        repo_output_path="generated/finalized_manuscript.md",
        require_finalized_provenance=True,
        appendix_mode="artifact_package_separate",
        extra_fields={
            "introduction_fragment_path": str(fragments_dir / "intro.md"),
            "related_work_fragment_path": str(fragments_dir / "related.md"),
            "discussion_fragment_path": str(fragments_dir / "discussion.md"),
            "limitations_fragment_path": str(fragments_dir / "limitations.md"),
            "ethics_fragment_path": str(fragments_dir / "ethics.md"),
            "bibliography_path": str(fragments_dir / "refs.bib"),
        },
    )

    outputs = draft_full_manuscript(run_dir, spec_path)
    manuscript_text = outputs["repo_output_path"].read_text(encoding="utf-8")

    assert "## Related Work" in manuscript_text
    assert "## Ethics / Broader Impacts" in manuscript_text
    assert "## References" in manuscript_text
    assert "Custom intro paragraph." in manuscript_text
    assert "Custom related work paragraph." in manuscript_text
    assert "Custom discussion paragraph." in manuscript_text
    assert "- Custom limitation." in manuscript_text
    assert "Custom ethics paragraph." in manuscript_text
    assert "Bibliography source:" in manuscript_text
    assert "two independent primary annotators" in manuscript_text
    assert "adjudicated_consensus_final" in manuscript_text
    assert "reproducibility bundle is tracked as a separate artifact package" in manuscript_text


def test_cli_draft_full_manuscript_smoke_check(tmp_path: Path) -> None:
    run_dir = _prepare_smoke_run(tmp_path)
    spec_path = _write_manuscript_spec(
        tmp_path / "cli_spec.json",
        target_run_id=run_dir.name,
        repo_output_path="generated/cli_manuscript.md",
    )
    output_path = tmp_path / "cli_output.md"

    exit_code = main(
        [
            "draft-full-manuscript",
            "--run-dir",
            str(run_dir),
            "--manuscript-spec",
            str(spec_path),
            "--output-path",
            str(output_path),
        ]
    )

    assert exit_code == 0
    assert output_path.exists()
    assert (run_dir / "analysis" / "paper_full_manuscript_draft.md").exists()
