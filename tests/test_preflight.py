from pathlib import Path

from anti_omission.config import load_experiment_bundle
from anti_omission.manifest import initialize_run_dir
from anti_omission.preflight import inspect_run_dir
from anti_omission.runner import execute_run


def test_preflight_reports_clean_run_dir_ready_to_run(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    bundle = load_experiment_bundle(Path("configs/experiment/dev_smoke.json"))
    run_dir = initialize_run_dir(bundle, tmp_path / "clean-run")

    diagnostics = inspect_run_dir(run_dir)

    assert diagnostics["ready_to_run"] is True
    assert diagnostics["manifest_rows"] == 4
    assert diagnostics["manifest_sha256"]
    assert diagnostics["manifest_sha256_matches_run_config"] is True
    assert diagnostics["raw_requests_count"] == 0
    assert diagnostics["raw_responses_count"] == 0
    assert diagnostics["failures_count"] == 0
    assert diagnostics["runtime_ready"] is True
    assert diagnostics["openai_runtime"]["is_set"] is True
    assert diagnostics["openai_runtime"]["starts_with_sk"] is True


def test_preflight_reports_dirty_run_dir_after_execution(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    bundle = load_experiment_bundle(Path("configs/experiment/dev_smoke.json"))
    run_dir = initialize_run_dir(bundle, tmp_path / "executed-run")
    execute_run(run_dir)

    diagnostics = inspect_run_dir(run_dir)

    assert diagnostics["ready_to_run"] is False
    assert diagnostics["raw_requests_count"] == 4
    assert diagnostics["raw_responses_count"] == 4
    assert diagnostics["failures_count"] == 0
    assert diagnostics["manifest_sha256_matches_run_config"] is True


def test_preflight_marks_live_run_not_ready_when_api_key_looks_like_shell_text(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "source .venv/bin/activate")
    bundle = load_experiment_bundle(Path("configs/experiment/mainline_confirmatory_holdout_v3_live.json"))
    run_dir = initialize_run_dir(bundle, tmp_path / "live-run-bad-key")

    diagnostics = inspect_run_dir(run_dir)

    assert diagnostics["runtime_ready"] is False
    assert diagnostics["ready_to_run"] is False
    assert diagnostics["openai_runtime"]["looks_like_shell_text"] is True
    assert diagnostics["openai_runtime"]["format_ok"] is False
