from pathlib import Path

from anti_omission.cli import main
from anti_omission.config import load_experiment_bundle
from anti_omission.labeling import export_annotation_csv, finalize_labels, import_labels_csv
from anti_omission.manifest import initialize_run_dir
from anti_omission.repo_visuals import write_repo_visuals
from anti_omission.runner import execute_run


def _prepare_finalized_smoke_run(tmp_path: Path) -> Path:
    bundle = load_experiment_bundle(Path("configs/experiment/dev_smoke.json"))
    run_dir = initialize_run_dir(bundle, tmp_path / "repo-visuals-run")
    execute_run(run_dir)
    export_annotation_csv(run_dir)
    labels_csv = Path("fixtures/dev_smoke_labels.csv")
    import_labels_csv(
        run_dir,
        labels_csv,
        stage="primary",
        annotator_id="annotator_a",
        annotator_type="human",
        blinding_mode="condition_code_blind",
        agreement_sample_design="full_double_primary",
    )
    import_labels_csv(
        run_dir,
        labels_csv,
        stage="primary",
        annotator_id="annotator_b",
        annotator_type="human",
        blinding_mode="condition_code_blind",
        agreement_sample_design="full_double_primary",
    )
    finalize_labels(run_dir)
    return run_dir


def test_write_repo_visuals_writes_expected_assets(tmp_path: Path) -> None:
    run_dir = _prepare_finalized_smoke_run(tmp_path)
    output_dir = tmp_path / "docs" / "assets"

    outputs = write_repo_visuals(run_dir, output_dir)

    assert outputs["overview_svg_path"].exists()
    assert outputs["overview_png_path"].exists()
    assert outputs["tradeoff_svg_path"].exists()
    assert outputs["timeliness_svg_path"].exists()
    assert "Anti-Omission Locked Confirmatory Study" in outputs["overview_svg_path"].read_text(
        encoding="utf-8"
    )


def test_cli_generate_repo_assets_smoke(tmp_path: Path, monkeypatch) -> None:
    expected = {
        "overview_svg_path": tmp_path / "assets" / "overview.svg",
        "overview_png_path": tmp_path / "assets" / "overview.png",
        "tradeoff_svg_path": tmp_path / "assets" / "tradeoff.svg",
        "timeliness_svg_path": tmp_path / "assets" / "timeliness.svg",
    }

    monkeypatch.setattr(
        "anti_omission.cli.write_repo_visuals",
        lambda run_dir, output_dir: expected,
    )

    exit_code = main(
        [
            "generate-repo-assets",
            "--run-dir",
            "outputs/runs/example",
            "--output-dir",
            "docs/assets",
        ]
    )

    assert exit_code == 0
