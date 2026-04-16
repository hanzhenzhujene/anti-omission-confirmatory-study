from pathlib import Path

from anti_omission.cli import main
from anti_omission.io_utils import read_json


def test_cli_smoke_test_runs_end_to_end(tmp_path: Path) -> None:
    run_dir = tmp_path / "smoke-cli-run"

    exit_code = main(
        [
            "smoke-test",
            "--experiment-config",
            str(Path("configs/experiment/dev_smoke.json").resolve()),
            "--labels-csv",
            str(Path("fixtures/dev_smoke_labels.csv").resolve()),
            "--run-dir",
            str(run_dir),
        ]
    )

    assert exit_code == 0
    summary = read_json(run_dir / "analysis" / "summary.json")
    assert summary["total_trials"] == 4
