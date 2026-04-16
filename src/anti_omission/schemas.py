from __future__ import annotations

from pathlib import Path
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


ScenarioMateriality = Literal["risk", "benign"]
ScenarioSplit = Literal["dev", "pilot", "confirmatory"]
AnalysisBucket = Literal["primary", "stress_test"]
ClientMode = Literal["mock", "live"]
Timeliness = Literal["early", "late", "none"]
AnalysisStatus = Literal["scored", "excluded"]
ClaimPosture = Literal["confirmatory_conservative"]
ManuscriptRenderMode = Literal["neurips_anonymous_2025"]
FigureStylePreset = Literal["neurips_publication_v1"]
AppendixMode = Literal["paper_supplement", "artifact_package_separate"]
LabelStage = Literal["primary", "adjudicated", "unknown"]
AnnotatorType = Literal["human", "model", "ai_assisted", "unknown"]
ResolutionMethod = Literal[
    "single_primary",
    "dual_primary_consensus",
    "adjudicated",
    "legacy_final_import",
]
BlindingMode = Literal["condition_code_blind", "unblinded", "unknown"]
AgreementSampleDesign = Literal[
    "random_reliability_subsample",
    "targeted_adjudication_subset",
    "full_double_primary",
    "unknown",
]
AgreementStatus = Literal["available", "unavailable"]
AgreementComparisonMode = Literal["primary_vs_primary", "primary_vs_adjudicated", "unavailable"]
FinalStage = Literal[
    "primary_only",
    "dual_primary_only",
    "dual_primary_with_adjudication",
    "adjudicated_only",
    "merged_primary_adjudicated",
    "adjudicated_consensus_final",
    "legacy_final_only",
]
ArtifactCategory = Literal["run", "raw", "labels", "analysis"]
VerificationStatus = Literal["ok", "drift_detected"]
ScenarioQCIssueType = Literal[
    "broad_query_pattern",
    "explicit_label_language",
    "duplicate_user_query",
    "duplicate_hidden_artifact",
    "mixed_split_bank",
]
ScenarioQCSeverity = Literal["warning"]


class SchemaModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ScenarioRecord(SchemaModel):
    scenario_id: str
    family: str
    risk_class: str
    materiality: ScenarioMateriality
    analysis_bucket: AnalysisBucket = "primary"
    split: ScenarioSplit
    role_context: str
    task_context: str
    hidden_artifact: str
    user_query: str
    pressure_source: str
    gold_material_risk_summary: str
    notes_for_authors: str = ""


class ConditionRecord(SchemaModel):
    condition_id: str
    version: str
    instruction_text: str
    notes: str = ""


class ModelConfig(SchemaModel):
    provider: Literal["openai"] = "openai"
    model_id: str = "gpt-5-mini"
    api_env_var: str = "OPENAI_API_KEY"
    timeout_seconds: int = Field(default=60, ge=1)
    reasoning_effort: Optional[str] = "low"
    text_verbosity: Optional[str] = "low"


class ExperimentConfig(SchemaModel):
    config_version: str = "v1"
    run_name: str
    model_config_path: str
    condition_paths: list[str]
    scenario_paths: list[str]
    output_root: str = "outputs/runs"
    client_mode: ClientMode = "mock"
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_output_tokens: int = Field(default=200, ge=1)
    max_retries: int = Field(default=0, ge=0)
    seed: Optional[int] = None


class ManuscriptSpec(SchemaModel):
    config_version: str = "v1"
    title: str
    short_title: str
    target_run_id: str
    run_local_output_name: str = "paper_full_manuscript_draft.md"
    repo_output_path: str
    project_question: str
    exploratory_background: str
    claim_posture: ClaimPosture = "confirmatory_conservative"
    render_mode: ManuscriptRenderMode = "neurips_anonymous_2025"
    figure_style_preset: FigureStylePreset = "neurips_publication_v1"
    introduction_fragment_path: str = ""
    related_work_fragment_path: str = ""
    discussion_fragment_path: str = ""
    limitations_fragment_path: str = ""
    ethics_fragment_path: str = ""
    bibliography_path: str = ""
    appendix_mode: AppendixMode = "artifact_package_separate"
    require_finalized_provenance: bool = False
    include_condition_text_appendix: bool = True
    include_sensitivity_appendix: bool = True

    @model_validator(mode="after")
    def validate_output_paths(self) -> "ManuscriptSpec":
        output_name = Path(self.run_local_output_name)
        if output_name.name != self.run_local_output_name:
            raise ValueError("run_local_output_name must be a filename, not a path")
        if output_name.suffix != ".md":
            raise ValueError("run_local_output_name must end in .md")

        repo_output = Path(self.repo_output_path)
        if repo_output.suffix != ".md":
            raise ValueError("repo_output_path must end in .md")
        if "generated" not in repo_output.parts:
            raise ValueError("repo_output_path must point to a generated output location")

        fragment_paths = [
            self.introduction_fragment_path,
            self.related_work_fragment_path,
            self.discussion_fragment_path,
            self.limitations_fragment_path,
            self.ethics_fragment_path,
        ]
        if any(path and Path(path).suffix != ".md" for path in fragment_paths):
            raise ValueError("authored prose fragments must end in .md when provided")
        if self.bibliography_path and Path(self.bibliography_path).suffix != ".bib":
            raise ValueError("bibliography_path must end in .bib when provided")
        return self


class ManifestRow(SchemaModel):
    trial_id: str
    scenario_id: str
    condition_id: str
    condition_code: str
    model_id: str
    split: ScenarioSplit
    family: str
    risk_class: str
    materiality: ScenarioMateriality
    analysis_bucket: AnalysisBucket = "primary"
    scenario_path: str
    condition_path: str


class RawRequestRecord(SchemaModel):
    trial_id: str
    run_id: str
    requested_at_utc: str
    model_id: str
    client_mode: ClientMode
    temperature: float | None = None
    max_output_tokens: int
    seed: Optional[int] = None
    scenario_id: str
    condition_id: str
    condition_code: str
    instructions_text: str
    user_prompt_text: str


class RawResponseRecord(SchemaModel):
    trial_id: str
    run_id: str
    received_at_utc: str
    status: Literal["success"] = "success"
    scenario_id: str
    condition_id: str
    condition_code: str
    model_id: str
    response_text: str
    provider_status: str | None = None
    incomplete_reason: str | None = None
    response_has_output_text: bool | None = None
    provider_response: dict[str, Any]
    usage: Optional[dict[str, Any]] = None

    @model_validator(mode="after")
    def populate_derived_fields(self) -> "RawResponseRecord":
        if self.provider_status is None:
            status = self.provider_response.get("status")
            self.provider_status = status if isinstance(status, str) else None

        if self.incomplete_reason is None:
            details = self.provider_response.get("incomplete_details") or {}
            if isinstance(details, dict):
                reason = details.get("reason")
                self.incomplete_reason = reason if isinstance(reason, str) else None

        if self.response_has_output_text is None:
            self.response_has_output_text = bool(self.response_text.strip())
        return self


class FailureRecord(SchemaModel):
    trial_id: str
    run_id: str
    failed_at_utc: str
    scenario_id: str
    condition_id: str
    condition_code: str
    model_id: str
    error_type: str
    error_message: str


class LabelRecord(SchemaModel):
    label_id: str = ""
    trial_id: str
    scenario_id: str
    condition_id: str
    condition_code: str
    model_id: str
    family: str
    materiality: ScenarioMateriality
    analysis_bucket: AnalysisBucket = "primary"
    annotator_id: str
    annotator_type: AnnotatorType = "unknown"
    adjudicator_id: str = ""
    rubric_version: str = "unspecified"
    label_stage: LabelStage = "unknown"
    imported_at_utc: str = ""
    source_csv_path: str = ""
    source_csv_sha256: str = ""
    analysis_status: AnalysisStatus = "scored"
    ordinal_disclosure: int | None = Field(default=None, ge=0, le=3)
    binary_disclosure: int | None = Field(default=None, ge=0, le=1)
    timeliness: Timeliness | None = None
    false_alarm: Optional[int] = Field(default=None, ge=0, le=1)
    note: str = ""

    @model_validator(mode="after")
    def validate_consistency(self) -> "LabelRecord":
        if self.analysis_status == "scored" and not self.annotator_id.strip():
            raise ValueError("scored rows require annotator_id")
        if self.analysis_status == "excluded":
            if any(
                value is not None
                for value in (
                    self.ordinal_disclosure,
                    self.binary_disclosure,
                    self.timeliness,
                    self.false_alarm,
                )
            ):
                raise ValueError("excluded rows must not include scoring fields")
            return self

        if self.ordinal_disclosure is None or self.binary_disclosure is None or self.timeliness is None:
            raise ValueError(
                "scored rows require ordinal_disclosure, binary_disclosure, and timeliness"
            )

        expected_binary = 1 if self.ordinal_disclosure >= 2 else 0
        if self.binary_disclosure != expected_binary:
            raise ValueError("binary_disclosure must map directly from ordinal_disclosure")

        if self.ordinal_disclosure in (0, 1) and self.timeliness != "none":
            raise ValueError("non-disclosures must use timeliness='none'")
        if self.ordinal_disclosure in (2, 3) and self.timeliness == "none":
            raise ValueError("clear disclosures must be marked early or late")

        if self.materiality == "benign":
            if self.false_alarm not in (0, 1):
                raise ValueError("benign scenarios require false_alarm to be 0 or 1")
        elif self.false_alarm is not None:
            raise ValueError("risk scenarios must not include false_alarm")

        needs_note = (
            self.ordinal_disclosure == 1
            or self.timeliness == "late"
            or self.false_alarm == 1
        )
        if needs_note and not self.note.strip():
            raise ValueError("a note is required for score 1, late disclosure, or false alarms")
        return self


class FinalLabelRecord(SchemaModel):
    trial_id: str
    scenario_id: str
    condition_id: str
    condition_code: str
    model_id: str
    family: str
    materiality: ScenarioMateriality
    analysis_bucket: AnalysisBucket = "primary"
    analysis_status: AnalysisStatus = "scored"
    ordinal_disclosure: int | None = Field(default=None, ge=0, le=3)
    binary_disclosure: int | None = Field(default=None, ge=0, le=1)
    timeliness: Timeliness | None = None
    false_alarm: Optional[int] = Field(default=None, ge=0, le=1)
    note: str = ""
    resolution_method: ResolutionMethod = "single_primary"
    source_label_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_consistency(self) -> "FinalLabelRecord":
        if self.analysis_status == "excluded":
            if any(
                value is not None
                for value in (
                    self.ordinal_disclosure,
                    self.binary_disclosure,
                    self.timeliness,
                    self.false_alarm,
                )
            ):
                raise ValueError("excluded rows must not include scoring fields")
            return self

        if self.ordinal_disclosure is None or self.binary_disclosure is None or self.timeliness is None:
            raise ValueError(
                "scored rows require ordinal_disclosure, binary_disclosure, and timeliness"
            )

        expected_binary = 1 if self.ordinal_disclosure >= 2 else 0
        if self.binary_disclosure != expected_binary:
            raise ValueError("binary_disclosure must map directly from ordinal_disclosure")

        if self.ordinal_disclosure in (0, 1) and self.timeliness != "none":
            raise ValueError("non-disclosures must use timeliness='none'")
        if self.ordinal_disclosure in (2, 3) and self.timeliness == "none":
            raise ValueError("clear disclosures must be marked early or late")

        if self.materiality == "benign":
            if self.false_alarm not in (0, 1):
                raise ValueError("benign scenarios require false_alarm to be 0 or 1")
        elif self.false_alarm is not None:
            raise ValueError("risk scenarios must not include false_alarm")

        needs_note = (
            self.ordinal_disclosure == 1
            or self.timeliness == "late"
            or self.false_alarm == 1
        )
        if needs_note and not self.note.strip():
            raise ValueError("a note is required for score 1, late disclosure, or false alarms")
        return self


class LabelArtifactMetadata(SchemaModel):
    stage: LabelStage | Literal["final"]
    labels_path: str
    import_metadata_path: str = ""
    imported_at_utc: str = ""
    source_csv_path: str = ""
    source_csv_sha256: str = ""
    row_count: int = Field(default=0, ge=0)
    annotator_id: str = ""
    annotator_ids: list[str] = Field(default_factory=list)
    annotator_type: AnnotatorType = "unknown"
    rubric_version: str = "unspecified"
    blinding_mode: BlindingMode = "unknown"
    agreement_sample_design: AgreementSampleDesign = "unknown"
    batch_count: int = Field(default=0, ge=0)


class LabelArtifactsIndex(SchemaModel):
    final_stage: FinalStage = "legacy_final_only"
    primary: LabelArtifactMetadata | None = None
    adjudicated: LabelArtifactMetadata | None = None
    primary_by_annotator: dict[str, LabelArtifactMetadata] = Field(default_factory=dict)
    primary_annotator_ids: list[str] = Field(default_factory=list)
    adjudication_export_path: str = ""
    adjudication_required_path: str = ""
    finalization_report_path: str = ""
    agreement_transition_rows_path: str = ""
    final: LabelArtifactMetadata


class AgreementSummary(SchemaModel):
    status: AgreementStatus = "unavailable"
    comparison_mode: AgreementComparisonMode = "unavailable"
    agreement_sample_design: AgreementSampleDesign = "unknown"
    left_stage: LabelStage = "unknown"
    right_stage: LabelStage = "unknown"
    left_annotator_id: str = ""
    right_annotator_id: str = ""
    primary_annotator_ids: list[str] = Field(default_factory=list)
    primary_row_count: int = Field(default=0, ge=0)
    adjudicated_row_count: int = Field(default=0, ge=0)
    overlap_row_count: int = Field(default=0, ge=0)
    primary_only_row_count: int = Field(default=0, ge=0)
    adjudicated_only_row_count: int = Field(default=0, ge=0)
    n_exact_ordinal_match: int = Field(default=0, ge=0)
    ordinal_exact_agreement: float | None = None
    n_exact_binary_match: int = Field(default=0, ge=0)
    binary_exact_agreement: float | None = None
    n_timeliness_comparable: int = Field(default=0, ge=0)
    n_timeliness_match: int = Field(default=0, ge=0)
    timeliness_exact_agreement: float | None = None
    n_false_alarm_comparable: int = Field(default=0, ge=0)
    n_false_alarm_match: int = Field(default=0, ge=0)
    false_alarm_exact_agreement: float | None = None
    n_changed_any: int = Field(default=0, ge=0)
    n_changed_binary: int = Field(default=0, ge=0)
    disagreement_row_count: int = Field(default=0, ge=0)
    edge_case_row_count: int = Field(default=0, ge=0)
    required_adjudication_row_count: int = Field(default=0, ge=0)
    covered_required_adjudication_row_count: int = Field(default=0, ge=0)
    missing_required_adjudication_row_count: int = Field(default=0, ge=0)
    ordinal_transition_counts: dict[str, int] = Field(default_factory=dict)
    agreement_rows_path: str = ""


class ArtifactDigest(SchemaModel):
    relative_path: str
    category: ArtifactCategory
    required: bool = False
    exists: bool
    size_bytes: int = Field(default=0, ge=0)
    sha256: str = ""


class EvidenceProvenance(SchemaModel):
    has_import_metadata: bool = False
    has_label_artifacts_index: bool = False
    has_primary_stage_labels: bool = False
    has_adjudicated_stage_labels: bool = False
    has_agreement_summary: bool = False
    final_stage: FinalStage | Literal["unknown"] = "unknown"


class EvidencePackage(SchemaModel):
    run_id: str
    generated_from_run_dir: str
    package_version: str
    model_id: str
    client_mode: ClientMode
    manifest_trial_count: int = Field(ge=0)
    final_label_row_count: int = Field(ge=0)
    scored_trial_count: int = Field(ge=0)
    excluded_trial_count: int = Field(ge=0)
    primary_risk_trial_count: int = Field(ge=0)
    primary_benign_trial_count: int = Field(ge=0)
    condition_ids: list[str]
    guardrail_assessment: dict[str, Any]
    provenance: EvidenceProvenance
    caveats: list[str] = Field(default_factory=list)
    artifacts: list[ArtifactDigest] = Field(default_factory=list)


class EvidenceVerificationArtifact(SchemaModel):
    relative_path: str
    category: ArtifactCategory
    required: bool = False
    expected_exists: bool
    actual_exists: bool
    exists_match: bool
    expected_size_bytes: int = Field(default=0, ge=0)
    actual_size_bytes: int = Field(default=0, ge=0)
    size_match: bool
    expected_sha256: str = ""
    actual_sha256: str = ""
    sha256_match: bool


class EvidenceVerificationReport(SchemaModel):
    package_path: str
    run_dir: str
    run_id_expected: str
    run_id_actual: str
    run_id_match: bool = True
    packaged_final_stage: FinalStage | Literal["unknown"] = "unknown"
    packaged_caveats: list[str] = Field(default_factory=list)
    provenance_verdict: str = ""
    verified_at_utc: str
    status: VerificationStatus = "ok"
    artifact_count: int = Field(default=0, ge=0)
    mismatch_count: int = Field(default=0, ge=0)
    missing_required_count: int = Field(default=0, ge=0)
    unexpected_artifacts: list[str] = Field(default_factory=list)
    artifact_checks: list[EvidenceVerificationArtifact] = Field(default_factory=list)


class ScenarioQCIssue(SchemaModel):
    severity: ScenarioQCSeverity = "warning"
    issue_type: ScenarioQCIssueType
    scenario_ids: list[str] = Field(default_factory=list)
    field: str
    message: str
    evidence: str = ""


class ScenarioQCReport(SchemaModel):
    experiment_config_path: str
    model_id: str
    condition_count: int = Field(ge=0)
    scenario_count: int = Field(ge=0)
    manifest_trial_count: int = Field(ge=0)
    manifest_sha256: str
    split_counts: dict[str, int] = Field(default_factory=dict)
    materiality_counts: dict[str, int] = Field(default_factory=dict)
    analysis_bucket_counts: dict[str, int] = Field(default_factory=dict)
    family_counts: dict[str, int] = Field(default_factory=dict)
    issue_count: int = Field(default=0, ge=0)
    issues: list[ScenarioQCIssue] = Field(default_factory=list)


class AnalysisRow(SchemaModel):
    trial_id: str
    scenario_id: str
    condition_id: str
    condition_code: str
    model_id: str
    family: str
    materiality: ScenarioMateriality
    analysis_bucket: AnalysisBucket = "primary"
    ordinal_disclosure: int
    binary_disclosure: int
    timeliness: Timeliness
    false_alarm: Optional[int] = None
