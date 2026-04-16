from anti_omission.schemas import (
    AgreementSummary,
    ArtifactDigest,
    EvidencePackage,
    EvidenceVerificationArtifact,
    EvidenceVerificationReport,
    EvidenceProvenance,
    FinalLabelRecord,
    LabelArtifactMetadata,
    LabelArtifactsIndex,
    LabelRecord,
    ScenarioRecord,
    ScenarioQCIssue,
    ScenarioQCReport,
)


def test_scenario_record_accepts_dev_example() -> None:
    scenario = ScenarioRecord(
        scenario_id="dev_example_v1",
        family="medical_biosafety",
        risk_class="assay_reliability",
        materiality="risk",
        analysis_bucket="primary",
        split="dev",
        role_context="role",
        task_context="task",
        hidden_artifact="hidden artifact",
        user_query="user query",
        pressure_source="pressure",
        gold_material_risk_summary="risk summary",
        notes_for_authors="note",
    )
    assert scenario.split == "dev"


def test_scenario_record_defaults_analysis_bucket_to_primary() -> None:
    scenario = ScenarioRecord(
        scenario_id="dev_example_default_bucket_v1",
        family="benign_control",
        risk_class="internal_metadata_only",
        materiality="benign",
        split="dev",
        role_context="role",
        task_context="task",
        hidden_artifact="hidden artifact",
        user_query="user query",
        pressure_source="pressure",
        gold_material_risk_summary="risk summary",
    )
    assert scenario.analysis_bucket == "primary"


def test_label_record_requires_note_for_edge_cases() -> None:
    try:
        LabelRecord(
            trial_id="trial",
            scenario_id="scenario",
            condition_id="baseline",
            condition_code="C01",
            model_id="gpt-5-mini",
            family="family",
            materiality="risk",
            annotator_id="ann",
            ordinal_disclosure=1,
            binary_disclosure=0,
            timeliness="none",
            note="",
        )
    except ValueError as exc:
        assert "note is required" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Expected validation error for missing note")


def test_excluded_label_record_allows_blank_scoring_fields() -> None:
    label = LabelRecord(
        trial_id="trial",
        scenario_id="scenario",
        condition_id="baseline",
        condition_code="C01",
        model_id="gpt-5-mini",
        family="family",
        materiality="risk",
        annotator_id="ann",
        analysis_status="excluded",
        note="Excluded from primary analysis: no_visible_output.",
    )
    assert label.analysis_status == "excluded"
    assert label.ordinal_disclosure is None


def test_final_label_record_accepts_resolution_metadata() -> None:
    label = FinalLabelRecord(
        trial_id="trial",
        scenario_id="scenario",
        condition_id="baseline",
        condition_code="C01",
        model_id="gpt-5-mini",
        family="family",
        materiality="risk",
        analysis_status="scored",
        ordinal_disclosure=2,
        binary_disclosure=1,
        timeliness="early",
        resolution_method="adjudicated",
        source_label_ids=["abc123", "def456"],
        note="Resolved at adjudication.",
    )
    assert label.resolution_method == "adjudicated"
    assert len(label.source_label_ids) == 2


def test_label_artifacts_index_accepts_stage_metadata() -> None:
    index = LabelArtifactsIndex(
        final_stage="merged_primary_adjudicated",
        primary=LabelArtifactMetadata(
            stage="primary",
            labels_path="labels/primary_labels.jsonl",
            import_metadata_path="labels/import_metadata.primary.json",
            row_count=72,
            blinding_mode="condition_code_blind",
        ),
        adjudicated=LabelArtifactMetadata(
            stage="adjudicated",
            labels_path="labels/adjudicated_labels.jsonl",
            import_metadata_path="labels/import_metadata.adjudicated.json",
            row_count=12,
            agreement_sample_design="targeted_adjudication_subset",
        ),
        final=LabelArtifactMetadata(
            stage="final",
            labels_path="labels/final_labels.jsonl",
            row_count=72,
        ),
    )
    assert index.final_stage == "merged_primary_adjudicated"
    assert index.adjudicated is not None


def test_agreement_summary_accepts_change_audit_fields() -> None:
    summary = AgreementSummary(
        status="available",
        agreement_sample_design="targeted_adjudication_subset",
        primary_row_count=72,
        adjudicated_row_count=12,
        overlap_row_count=12,
        n_exact_ordinal_match=9,
        n_exact_binary_match=10,
        n_timeliness_comparable=12,
        n_timeliness_match=8,
        n_false_alarm_comparable=4,
        n_false_alarm_match=4,
        n_changed_any=3,
        n_changed_binary=2,
        ordinal_transition_counts={"0->0": 6, "0->2": 2, "3->3": 4},
        agreement_rows_path="labels/agreement_transition_rows.csv",
    )
    assert summary.status == "available"
    assert summary.ordinal_transition_counts["0->2"] == 2


def test_evidence_package_accepts_artifact_inventory_and_provenance() -> None:
    evidence = EvidencePackage(
        run_id="run-id",
        generated_from_run_dir="/tmp/run-id",
        package_version="0.1.0",
        model_id="gpt-5-mini",
        client_mode="mock",
        manifest_trial_count=12,
        final_label_row_count=12,
        scored_trial_count=11,
        excluded_trial_count=1,
        primary_risk_trial_count=6,
        primary_benign_trial_count=6,
        condition_ids=["baseline", "disclosure_full"],
        guardrail_assessment={"comparative_benign_false_alarm": {"passed": False}},
        provenance=EvidenceProvenance(
            has_import_metadata=True,
            has_label_artifacts_index=True,
            has_primary_stage_labels=True,
            has_adjudicated_stage_labels=False,
            has_agreement_summary=False,
            final_stage="primary_only",
        ),
        caveats=["comparative_benign_guardrail_failed"],
        artifacts=[
            ArtifactDigest(
                relative_path="labels/final_labels.jsonl",
                category="labels",
                required=True,
                exists=True,
                size_bytes=128,
                sha256="abc123",
            )
        ],
    )
    assert evidence.provenance.final_stage == "primary_only"
    assert evidence.artifacts[0].category == "labels"


def test_evidence_verification_report_accepts_drift_summary() -> None:
    report = EvidenceVerificationReport(
        package_path="/tmp/evidence_package.json",
        run_dir="/tmp/run-id",
        run_id_expected="run-id",
        run_id_actual="run-id",
        run_id_match=True,
        packaged_final_stage="legacy_final_only",
        packaged_caveats=["legacy_final_labels_only"],
        provenance_verdict="Verified legacy final-only package.",
        verified_at_utc="2026-04-13T00:00:00Z",
        status="drift_detected",
        artifact_count=2,
        mismatch_count=1,
        missing_required_count=0,
        unexpected_artifacts=["analysis/extra_note.txt"],
        artifact_checks=[
            EvidenceVerificationArtifact(
                relative_path="labels/final_labels.jsonl",
                category="labels",
                required=True,
                expected_exists=True,
                actual_exists=True,
                exists_match=True,
                expected_size_bytes=120,
                actual_size_bytes=121,
                size_match=False,
                expected_sha256="abc",
                actual_sha256="def",
                sha256_match=False,
            )
        ],
    )
    assert report.status == "drift_detected"
    assert report.unexpected_artifacts == ["analysis/extra_note.txt"]


def test_scenario_qc_report_accepts_issue_inventory() -> None:
    report = ScenarioQCReport(
        experiment_config_path="/tmp/config.json",
        model_id="gpt-5-mini",
        condition_count=3,
        scenario_count=60,
        manifest_trial_count=180,
        manifest_sha256="abc123",
        split_counts={"confirmatory": 60},
        materiality_counts={"risk": 24, "benign": 36},
        analysis_bucket_counts={"primary": 60},
        family_counts={"medical_biosafety": 6},
        issue_count=1,
        issues=[
            ScenarioQCIssue(
                issue_type="broad_query_pattern",
                scenario_ids=["scenario_a"],
                field="user_query",
                message="Broad completeness wording detected.",
                evidence="Is this ready?",
            )
        ],
    )
    assert report.issue_count == 1
    assert report.issues[0].issue_type == "broad_query_pattern"
