import csv
import json
from pathlib import Path

import pytest

from anti_omission.cli import main
from anti_omission.config import ConfigurationError, load_experiment_bundle
from anti_omission.labeling import export_annotation_csv, finalize_labels, import_labels_csv
from anti_omission.manifest import initialize_run_dir
from anti_omission.runner import execute_run
from anti_omission.submission import build_submission_bundle, lock_manuscript_spec


def _prepare_finalized_dual_primary_run(tmp_path: Path) -> Path:
    bundle = load_experiment_bundle(Path("configs/experiment/dev_smoke.json"))
    run_dir = initialize_run_dir(bundle, tmp_path / "submission-finalized")
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

    for annotator_id in ("annotator_a", "annotator_b"):
        csv_path = tmp_path / f"{annotator_id}.csv"
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        import_labels_csv(
            run_dir,
            csv_path,
            stage="primary",
            annotator_id=annotator_id,
            annotator_type="human",
            blinding_mode="condition_code_blind",
            agreement_sample_design="full_double_primary",
        )

    finalize_labels(run_dir)
    return run_dir


def _write_manuscript_spec(
    path: Path,
    *,
    target_run_id: str = "LOCK_AFTER_V3_EXECUTION",
    require_finalized_provenance: bool = True,
) -> Path:
    payload = {
        "config_version": "v1",
        "figure_style_preset": "neurips_publication_v1",
        "title": "Submission Bundle Test",
        "short_title": "Bundle Test",
        "target_run_id": target_run_id,
        "run_local_output_name": "paper_full_manuscript_submission.md",
        "repo_output_path": "generated/submission_bundle.md",
        "project_question": "Does the disclosure-duty intervention improve risk disclosure without unacceptable benign cost?",
        "exploratory_background": "Exploratory runs were used only for scaffold-building and are not pooled with confirmatory evidence.",
        "claim_posture": "confirmatory_conservative",
        "render_mode": "neurips_anonymous_2025",
        "appendix_mode": "artifact_package_separate",
        "require_finalized_provenance": require_finalized_provenance,
        "include_condition_text_appendix": True,
        "include_sensitivity_appendix": True,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def test_lock_manuscript_spec_writes_run_locked_copy(tmp_path: Path) -> None:
    run_dir = _prepare_finalized_dual_primary_run(tmp_path)
    spec_path = _write_manuscript_spec(tmp_path / "template_spec.json")

    outputs = lock_manuscript_spec(run_dir, spec_path)

    locked_payload = json.loads(outputs["run_local_path"].read_text(encoding="utf-8"))
    assert locked_payload["target_run_id"] == run_dir.name
    assert outputs["run_local_path"].name == "template_spec.locked.json"


def test_lock_manuscript_spec_rewrites_relative_fragment_paths(tmp_path: Path) -> None:
    run_dir = _prepare_finalized_dual_primary_run(tmp_path)
    fragments_dir = tmp_path / "fragments"
    fragments_dir.mkdir()
    intro_path = fragments_dir / "intro.md"
    bib_path = fragments_dir / "refs.bib"
    intro_path.write_text("intro\n", encoding="utf-8")
    bib_path.write_text("@article{dummy,title={Dummy},author={Anon},year={2026}}\n", encoding="utf-8")

    spec_path = _write_manuscript_spec(tmp_path / "relative_paths_spec.json")
    payload = json.loads(spec_path.read_text(encoding="utf-8"))
    payload["introduction_fragment_path"] = "fragments/intro.md"
    payload["bibliography_path"] = "fragments/refs.bib"
    spec_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    outputs = lock_manuscript_spec(run_dir, spec_path)
    locked_payload = json.loads(outputs["run_local_path"].read_text(encoding="utf-8"))

    assert locked_payload["introduction_fragment_path"] == str(intro_path.resolve())
    assert locked_payload["bibliography_path"] == str(bib_path.resolve())
    assert Path(locked_payload["repo_output_path"]).is_absolute()


def test_lock_manuscript_spec_rejects_mismatched_non_placeholder_target(tmp_path: Path) -> None:
    run_dir = _prepare_finalized_dual_primary_run(tmp_path)
    spec_path = _write_manuscript_spec(
        tmp_path / "wrong_target_spec.json",
        target_run_id="20260414T225156Z_mainline-confirmatory-holdout-v3-live",
    )

    with pytest.raises(ConfigurationError, match="already points at a different run_id"):
        lock_manuscript_spec(run_dir, spec_path)


def test_build_submission_bundle_writes_locked_spec_and_verified_package(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir = _prepare_finalized_dual_primary_run(tmp_path)
    spec_path = _write_manuscript_spec(tmp_path / "bundle_spec.json")

    def fake_typeset(run_dir: str | Path, manuscript_spec_path: str | Path, output_path: str | Path | None = None) -> dict[str, Path]:
        resolved_run_dir = Path(run_dir).resolve()
        analysis_dir = resolved_run_dir / "analysis"
        run_local_markdown = analysis_dir / "paper_full_manuscript_submission.md"
        run_local_tex = analysis_dir / "paper_full_manuscript_submission.tex"
        run_local_pdf = analysis_dir / "paper_full_manuscript_submission.pdf"
        repo_markdown = Path(output_path).resolve() if output_path else tmp_path / "generated" / "submission_bundle.md"
        repo_tex = repo_markdown.with_suffix(".tex")
        repo_pdf = repo_markdown.with_suffix(".pdf")
        for path in (run_local_markdown, run_local_tex, run_local_pdf, repo_markdown, repo_tex, repo_pdf):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("generated\n", encoding="utf-8")
        return {
            "run_local_markdown_path": run_local_markdown,
            "run_local_tex_path": run_local_tex,
            "run_local_pdf_path": run_local_pdf,
            "repo_markdown_path": repo_markdown,
            "repo_tex_path": repo_tex,
            "repo_pdf_path": repo_pdf,
        }

    monkeypatch.setattr("anti_omission.submission.typeset_full_manuscript", fake_typeset)

    outputs = build_submission_bundle(
        run_dir,
        spec_path,
        output_path=tmp_path / "generated" / "submission_bundle.md",
    )

    assert outputs["locked_spec_path"].exists()
    assert outputs["evidence_package_path"].exists()
    assert outputs["evidence_verification_path"].exists()
    assert outputs["evidence_index_path"].exists()
    verification_payload = json.loads(outputs["evidence_verification_path"].read_text(encoding="utf-8"))
    assert verification_payload["status"] == "ok"
    locked_payload = json.loads(outputs["locked_spec_path"].read_text(encoding="utf-8"))
    assert locked_payload["target_run_id"] == run_dir.name


def test_cli_lock_manuscript_spec_and_build_submission_bundle_smoke(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir = _prepare_finalized_dual_primary_run(tmp_path)
    spec_path = _write_manuscript_spec(tmp_path / "cli_bundle_spec.json")
    locked_output = tmp_path / "locked" / "cli_bundle_spec.locked.json"

    exit_code = main(
        [
            "lock-manuscript-spec",
            "--run-dir",
            str(run_dir),
            "--manuscript-spec",
            str(spec_path),
            "--output-path",
            str(locked_output),
        ]
    )

    assert exit_code == 0
    assert locked_output.exists()

    def fake_build(run_dir: str | Path, manuscript_spec_path: str | Path, *, output_path: str | Path | None = None, locked_spec_output_path: str | Path | None = None) -> dict[str, Path]:
        repo_output = Path(output_path).resolve() if output_path else tmp_path / "generated" / "cli_submission.md"
        locked_path = Path(locked_spec_output_path).resolve() if locked_spec_output_path else tmp_path / "locked" / "bundle.locked.json"
        for path in (repo_output, repo_output.with_suffix(".tex"), repo_output.with_suffix(".pdf"), locked_path):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("generated\n", encoding="utf-8")
        return {
            "locked_spec_path": locked_path,
            "run_local_markdown_path": Path(run_dir) / "analysis" / "paper.md",
            "run_local_tex_path": Path(run_dir) / "analysis" / "paper.tex",
            "run_local_pdf_path": Path(run_dir) / "analysis" / "paper.pdf",
            "repo_markdown_path": repo_output,
            "repo_tex_path": repo_output.with_suffix(".tex"),
            "repo_pdf_path": repo_output.with_suffix(".pdf"),
            "evidence_package_path": Path(run_dir) / "analysis" / "evidence_package.json",
            "evidence_verification_path": Path(run_dir) / "analysis" / "evidence_verification.json",
            "evidence_index_path": Path(run_dir) / "analysis" / "evidence_index.md",
        }

    monkeypatch.setattr("anti_omission.cli.build_submission_bundle", fake_build)
    output_path = tmp_path / "generated" / "cli_submission.md"

    exit_code = main(
        [
            "build-submission-bundle",
            "--run-dir",
            str(run_dir),
            "--manuscript-spec",
            str(spec_path),
            "--output-path",
            str(output_path),
            "--locked-spec-output-path",
            str(locked_output),
        ]
    )

    assert exit_code == 0
    assert output_path.exists()
