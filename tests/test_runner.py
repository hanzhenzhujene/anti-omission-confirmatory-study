from pathlib import Path

import pytest

from anti_omission.client import GenerationResult
from anti_omission.config import load_experiment_bundle
from anti_omission.io_utils import read_jsonl
from anti_omission.manifest import initialize_run_dir
from anti_omission.runner import execute_run


def test_mock_run_creates_raw_artifacts(tmp_path: Path) -> None:
    bundle = load_experiment_bundle(Path("configs/experiment/dev_smoke.json"))
    run_dir = initialize_run_dir(bundle, tmp_path / "mock-run")

    result = execute_run(run_dir)

    assert result["completed_trials"] == 4
    assert len(read_jsonl(run_dir / "raw_requests.jsonl")) == 4
    assert len(read_jsonl(run_dir / "raw_responses.jsonl")) == 4


def test_failure_logging_happens_before_error_is_raised(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bundle = load_experiment_bundle(Path("configs/experiment/dev_smoke.json"))
    run_dir = initialize_run_dir(bundle, tmp_path / "failing-run")

    class AlwaysFailClient:
        def generate(self, **_: object) -> GenerationResult:
            raise RuntimeError("boom")

    monkeypatch.setattr("anti_omission.runner.build_client", lambda *_args, **_kwargs: AlwaysFailClient())

    with pytest.raises(RuntimeError, match="boom"):
        execute_run(run_dir)

    failures = read_jsonl(run_dir / "failures.jsonl")
    assert len(failures) == 1
    assert failures[0]["error_message"] == "boom"
