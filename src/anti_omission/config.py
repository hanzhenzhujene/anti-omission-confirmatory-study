from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from anti_omission.io_utils import read_json
from anti_omission.schemas import (
    ConditionRecord,
    ExperimentConfig,
    ManuscriptSpec,
    ModelConfig,
    ScenarioRecord,
)


class ConfigurationError(ValueError):
    """Raised when authored experiment inputs are inconsistent."""


@dataclass(frozen=True)
class ExperimentBundle:
    experiment_config: ExperimentConfig
    model_config: ModelConfig
    conditions: dict[str, ConditionRecord]
    condition_paths: dict[str, Path]
    scenarios: dict[str, ScenarioRecord]
    scenario_paths: dict[str, Path]
    experiment_config_path: Path


@dataclass(frozen=True)
class ManuscriptSpecBundle:
    manuscript_spec: ManuscriptSpec
    manuscript_spec_path: Path
    repo_output_path: Path


def _resolve_path(raw_path: str, base_path: Path) -> Path:
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = (base_path.parent / candidate).resolve()
    return candidate


def _load_unique_conditions(paths: list[Path]) -> tuple[dict[str, ConditionRecord], dict[str, Path]]:
    conditions: dict[str, ConditionRecord] = {}
    condition_paths: dict[str, Path] = {}
    for path in paths:
        condition = ConditionRecord.model_validate(read_json(path))
        if condition.condition_id in conditions:
            raise ConfigurationError(f"Duplicate condition_id detected: {condition.condition_id}")
        conditions[condition.condition_id] = condition
        condition_paths[condition.condition_id] = path
    return conditions, condition_paths


def _load_unique_scenarios(paths: list[Path]) -> tuple[dict[str, ScenarioRecord], dict[str, Path]]:
    scenarios: dict[str, ScenarioRecord] = {}
    scenario_paths: dict[str, Path] = {}
    for path in paths:
        scenario = ScenarioRecord.model_validate(read_json(path))
        if scenario.scenario_id in scenarios:
            raise ConfigurationError(f"Duplicate scenario_id detected: {scenario.scenario_id}")
        scenarios[scenario.scenario_id] = scenario
        scenario_paths[scenario.scenario_id] = path
    return scenarios, scenario_paths


def load_experiment_bundle(experiment_config_path: str | Path) -> ExperimentBundle:
    config_path = Path(experiment_config_path).resolve()
    experiment_config = ExperimentConfig.model_validate(read_json(config_path))

    model_path = _resolve_path(experiment_config.model_config_path, config_path)
    model_config = ModelConfig.model_validate(read_json(model_path))

    condition_paths = [_resolve_path(path, config_path) for path in experiment_config.condition_paths]
    scenario_paths = [_resolve_path(path, config_path) for path in experiment_config.scenario_paths]

    if not condition_paths:
        raise ConfigurationError("Experiment config must include at least one condition path")
    if not scenario_paths:
        raise ConfigurationError("Experiment config must include at least one scenario path")

    conditions, resolved_condition_paths = _load_unique_conditions(condition_paths)
    scenarios, resolved_scenario_paths = _load_unique_scenarios(scenario_paths)

    return ExperimentBundle(
        experiment_config=experiment_config,
        model_config=model_config,
        conditions=conditions,
        condition_paths=resolved_condition_paths,
        scenarios=scenarios,
        scenario_paths=resolved_scenario_paths,
        experiment_config_path=config_path,
    )


def load_manuscript_spec_bundle(manuscript_spec_path: str | Path) -> ManuscriptSpecBundle:
    config_path = Path(manuscript_spec_path).resolve()
    manuscript_spec = ManuscriptSpec.model_validate(read_json(config_path))
    repo_output_path = _resolve_path(manuscript_spec.repo_output_path, config_path)
    return ManuscriptSpecBundle(
        manuscript_spec=manuscript_spec,
        manuscript_spec_path=config_path,
        repo_output_path=repo_output_path,
    )
