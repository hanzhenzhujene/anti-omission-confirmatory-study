from __future__ import annotations

import re
from collections import Counter, defaultdict
from pathlib import Path

from anti_omission.config import load_experiment_bundle
from anti_omission.io_utils import write_json
from anti_omission.manifest import build_manifest, manifest_sha256
from anti_omission.schemas import ScenarioQCIssue, ScenarioQCReport


BROAD_QUERY_CHECKS = (
    (
        re.compile(r"\banything else\b", re.IGNORECASE),
        "User query asks for broad completeness rather than a narrow local answer.",
    ),
    (
        re.compile(r"\banything i should know\b", re.IGNORECASE),
        "User query directly invites catch-all caveats.",
    ),
    (
        re.compile(r"\bshould i worry\b", re.IGNORECASE),
        "User query explicitly asks whether there is a concern to worry about.",
    ),
    (
        re.compile(r"\bare there risks\b", re.IGNORECASE),
        "User query explicitly asks about risks, which weakens omission pressure.",
    ),
    (
        re.compile(r"\bis this (ready|complete|fine)\b", re.IGNORECASE),
        "User query uses a broad readiness or completeness framing that can give baseline an easy truthful escape.",
    ),
)

EXPLICIT_LABEL_LANGUAGE_CHECKS = (
    (
        re.compile(r"\b(?:danger|dangerous)\b", re.IGNORECASE),
        "Hidden artifact contains explicit danger language.",
    ),
    (
        re.compile(r"\bmaterial risk\b", re.IGNORECASE),
        "Hidden artifact names the issue as a material risk instead of describing it naturally.",
    ),
    (
        re.compile(r"\b(?:must|should)(?: definitely)? disclose\b", re.IGNORECASE),
        "Hidden artifact directly states that the issue should be disclosed.",
    ),
    (
        re.compile(r"\bunsafe\b", re.IGNORECASE),
        "Hidden artifact uses an explicit unsafe label.",
    ),
)


def inspect_scenario_bank(experiment_config_path: str | Path) -> ScenarioQCReport:
    bundle = load_experiment_bundle(experiment_config_path)
    manifest_rows = build_manifest(bundle)
    scenarios = list(bundle.scenarios.values())

    split_counts = Counter(scenario.split for scenario in scenarios)
    materiality_counts = Counter(scenario.materiality for scenario in scenarios)
    analysis_bucket_counts = Counter(scenario.analysis_bucket for scenario in scenarios)
    family_counts = Counter(scenario.family for scenario in scenarios)

    issues: list[ScenarioQCIssue] = []
    issues.extend(_broad_query_issues(scenarios))
    issues.extend(_explicit_label_language_issues(scenarios))
    issues.extend(_duplicate_field_issues(scenarios, field_name="user_query"))
    issues.extend(_duplicate_field_issues(scenarios, field_name="hidden_artifact"))

    if len(split_counts) > 1:
        issues.append(
            ScenarioQCIssue(
                issue_type="mixed_split_bank",
                scenario_ids=sorted(scenario.scenario_id for scenario in scenarios),
                field="split",
                message="Experiment config mixes multiple scenario splits; final confirmatory banks should be single-split.",
                evidence=", ".join(f"{split}={count}" for split, count in sorted(split_counts.items())),
            )
        )

    return ScenarioQCReport(
        experiment_config_path=str(Path(experiment_config_path).resolve()),
        model_id=bundle.model_config.model_id,
        condition_count=len(bundle.conditions),
        scenario_count=len(scenarios),
        manifest_trial_count=len(manifest_rows),
        manifest_sha256=manifest_sha256(manifest_rows),
        split_counts=dict(sorted(split_counts.items())),
        materiality_counts=dict(sorted(materiality_counts.items())),
        analysis_bucket_counts=dict(sorted(analysis_bucket_counts.items())),
        family_counts=dict(sorted(family_counts.items())),
        issue_count=len(issues),
        issues=issues,
    )


def write_scenario_qc_report(
    experiment_config_path: str | Path,
    output_path: str | Path,
) -> Path:
    report = inspect_scenario_bank(experiment_config_path)
    resolved_output_path = Path(output_path).resolve()
    write_json(resolved_output_path, report.model_dump())
    return resolved_output_path


def _broad_query_issues(scenarios: list) -> list[ScenarioQCIssue]:
    issues: list[ScenarioQCIssue] = []
    for scenario in scenarios:
        for pattern, message in BROAD_QUERY_CHECKS:
            match = pattern.search(scenario.user_query)
            if match:
                issues.append(
                    ScenarioQCIssue(
                        issue_type="broad_query_pattern",
                        scenario_ids=[scenario.scenario_id],
                        field="user_query",
                        message=message,
                        evidence=match.group(0),
                    )
                )
    return issues


def _explicit_label_language_issues(scenarios: list) -> list[ScenarioQCIssue]:
    issues: list[ScenarioQCIssue] = []
    for scenario in scenarios:
        for pattern, message in EXPLICIT_LABEL_LANGUAGE_CHECKS:
            match = pattern.search(scenario.hidden_artifact)
            if match:
                issues.append(
                    ScenarioQCIssue(
                        issue_type="explicit_label_language",
                        scenario_ids=[scenario.scenario_id],
                        field="hidden_artifact",
                        message=message,
                        evidence=match.group(0),
                    )
                )
    return issues


def _duplicate_field_issues(scenarios: list, *, field_name: str) -> list[ScenarioQCIssue]:
    groups: dict[str, list[str]] = defaultdict(list)
    original_text: dict[str, str] = {}
    for scenario in scenarios:
        raw_value = getattr(scenario, field_name)
        normalized = _normalize_text(raw_value)
        if not normalized:
            continue
        groups[normalized].append(scenario.scenario_id)
        original_text.setdefault(normalized, raw_value.strip())

    issues: list[ScenarioQCIssue] = []
    for normalized_value, scenario_ids in sorted(groups.items()):
        if len(scenario_ids) < 2:
            continue
        issue_type = "duplicate_user_query" if field_name == "user_query" else "duplicate_hidden_artifact"
        issues.append(
            ScenarioQCIssue(
                issue_type=issue_type,
                scenario_ids=sorted(scenario_ids),
                field=field_name,
                message=f"Multiple scenarios reuse the same normalized {field_name}.",
                evidence=original_text[normalized_value][:240],
            )
        )
    return issues


def _normalize_text(text: str) -> str:
    collapsed = " ".join(text.lower().split())
    return re.sub(r"[^a-z0-9 ]+", "", collapsed).strip()
