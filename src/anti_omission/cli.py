from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

from anti_omission.analysis import summarize_run
from anti_omission.config import load_experiment_bundle
from anti_omission.evidence import draft_evidence_index, package_evidence, verify_evidence
from anti_omission.labeling import (
    export_adjudication_csv,
    export_annotation_csv,
    finalize_labels,
    import_labels_csv,
)
from anti_omission.manifest import initialize_run_dir
from anti_omission.preflight import inspect_run_dir
from anti_omission.repo_visuals import write_repo_visuals
from anti_omission.reporting import draft_full_manuscript, draft_manuscript_section, draft_paper_results
from anti_omission.runner import execute_run
from anti_omission.scenario_qc import inspect_scenario_bank, write_scenario_qc_report
from anti_omission.submission import build_submission_bundle, lock_manuscript_spec
from anti_omission.typesetting import typeset_full_manuscript


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="anti-omission")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="Validate authored experiment inputs")
    validate_parser.add_argument("--experiment-config", required=True)

    scenario_qc_parser = subparsers.add_parser(
        "qc-scenarios",
        help="Summarize scenario-bank composition and flag likely freeze/QC issues",
    )
    scenario_qc_parser.add_argument("--experiment-config", required=True)
    scenario_qc_parser.add_argument("--output-path")

    manifest_parser = subparsers.add_parser("make-manifest", help="Create a run directory and manifest")
    manifest_parser.add_argument("--experiment-config", required=True)
    manifest_parser.add_argument("--run-dir")

    preflight_parser = subparsers.add_parser(
        "preflight",
        help="Check whether a prepared run directory is clean and the OpenAI runtime looks usable",
    )
    preflight_parser.add_argument("--run-dir", required=True)

    run_parser = subparsers.add_parser("run", help="Execute a prepared manifest")
    run_parser.add_argument("--run-dir", required=True)

    export_parser = subparsers.add_parser("export-labels", help="Export a blind annotation CSV")
    export_parser.add_argument("--run-dir", required=True)

    adjudication_export_parser = subparsers.add_parser(
        "export-adjudication-sheet",
        help="Export an adjudicator-facing sheet from imported primary labels",
    )
    adjudication_export_parser.add_argument("--run-dir", required=True)

    import_parser = subparsers.add_parser("import-labels", help="Import labels for a specific stage")
    import_parser.add_argument("--run-dir", required=True)
    import_parser.add_argument("--labels-csv", required=True)
    import_parser.add_argument(
        "--stage",
        choices=["primary", "adjudicated"],
        default="adjudicated",
    )
    import_parser.add_argument("--annotator-id")
    import_parser.add_argument(
        "--annotator-type",
        choices=["human", "model", "ai_assisted", "unknown"],
        default="unknown",
    )
    import_parser.add_argument("--rubric-version", default="v1")
    import_parser.add_argument(
        "--blinding-mode",
        choices=["condition_code_blind", "unblinded", "unknown"],
        default="unknown",
    )
    import_parser.add_argument(
        "--agreement-sample-design",
        choices=[
            "random_reliability_subsample",
            "targeted_adjudication_subset",
            "full_double_primary",
            "unknown",
        ],
        default="unknown",
    )

    finalize_parser = subparsers.add_parser(
        "finalize-labels",
        help="Build final labels from staged primary and adjudicated inputs",
    )
    finalize_parser.add_argument("--run-dir", required=True)
    finalize_parser.add_argument(
        "--allow-provisional",
        action="store_true",
        help="Allow writing a non-final provisional merge when required adjudication is incomplete",
    )

    summarize_parser = subparsers.add_parser("summarize", help="Produce a minimal analysis summary")
    summarize_parser.add_argument("--run-dir", required=True)

    draft_parser = subparsers.add_parser(
        "draft-results",
        help="Draft paper-style result text and tables from a completed labeled run",
    )
    draft_parser.add_argument("--run-dir", required=True)

    manuscript_parser = subparsers.add_parser(
        "draft-manuscript",
        help="Draft a fuller manuscript-style section from a completed labeled run",
    )
    manuscript_parser.add_argument("--run-dir", required=True)

    full_manuscript_parser = subparsers.add_parser(
        "draft-full-manuscript",
        help="Generate a full manuscript draft from a labeled run and manuscript spec",
    )
    full_manuscript_parser.add_argument("--run-dir", required=True)
    full_manuscript_parser.add_argument("--manuscript-spec", required=True)
    full_manuscript_parser.add_argument("--output-path")

    lock_spec_parser = subparsers.add_parser(
        "lock-manuscript-spec",
        help="Write a run-locked copy of a manuscript spec by replacing a placeholder target_run_id",
    )
    lock_spec_parser.add_argument("--run-dir", required=True)
    lock_spec_parser.add_argument("--manuscript-spec", required=True)
    lock_spec_parser.add_argument("--output-path")

    typeset_parser = subparsers.add_parser(
        "typeset-full-manuscript",
        help="Generate markdown, LaTeX, and PDF manuscript outputs from a labeled run",
    )
    typeset_parser.add_argument("--run-dir", required=True)
    typeset_parser.add_argument("--manuscript-spec", required=True)
    typeset_parser.add_argument("--output-path")

    typeset_paper_parser = subparsers.add_parser(
        "typeset-paper",
        help="Alias for typeset-full-manuscript with paper-facing naming",
    )
    typeset_paper_parser.add_argument("--run-dir", required=True)
    typeset_paper_parser.add_argument("--manuscript-spec", required=True)
    typeset_paper_parser.add_argument("--output-path")

    submission_bundle_parser = subparsers.add_parser(
        "build-submission-bundle",
        help="Lock the manuscript spec, typeset the paper, and verify the final evidence package",
    )
    submission_bundle_parser.add_argument("--run-dir", required=True)
    submission_bundle_parser.add_argument("--manuscript-spec", required=True)
    submission_bundle_parser.add_argument("--output-path")
    submission_bundle_parser.add_argument("--locked-spec-output-path")

    evidence_parser = subparsers.add_parser(
        "package-evidence",
        help="Create a deterministic artifact inventory and provenance package for a completed run",
    )
    evidence_parser.add_argument("--run-dir", required=True)
    evidence_parser.add_argument("--output-path")

    verify_evidence_parser = subparsers.add_parser(
        "verify-evidence",
        help="Verify a stored evidence package against the current run directory",
    )
    verify_evidence_parser.add_argument("--run-dir", required=True)
    verify_evidence_parser.add_argument("--evidence-path")
    verify_evidence_parser.add_argument("--output-path")

    evidence_index_parser = subparsers.add_parser(
        "draft-evidence-index",
        help="Generate a canonical markdown landing page for a completed confirmatory evidence package",
    )
    evidence_index_parser.add_argument("--run-dir", required=True)
    evidence_index_parser.add_argument("--output-path")

    repo_visuals_parser = subparsers.add_parser(
        "generate-repo-assets",
        help="Generate GitHub-friendly visual assets from a locked run",
    )
    repo_visuals_parser.add_argument("--run-dir", required=True)
    repo_visuals_parser.add_argument("--output-dir", required=True)

    smoke_parser = subparsers.add_parser("smoke-test", help="Run the bundled mock smoke test")
    smoke_parser.add_argument(
        "--experiment-config",
        default="configs/experiment/dev_smoke.json",
        help="Path to the smoke experiment config",
    )
    smoke_parser.add_argument(
        "--labels-csv",
        default="fixtures/dev_smoke_labels.csv",
        help="Path to the adjudicated labels fixture",
    )
    smoke_parser.add_argument("--run-dir")

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "validate":
        bundle = load_experiment_bundle(args.experiment_config)
        print(
            f"Validated {len(bundle.scenarios)} scenarios and {len(bundle.conditions)} conditions "
            f"for model {bundle.model_config.model_id}."
        )
        return 0

    if args.command == "qc-scenarios":
        if args.output_path:
            output_path = write_scenario_qc_report(args.experiment_config, args.output_path)
            print(output_path)
        else:
            report = inspect_scenario_bank(args.experiment_config)
            print(json.dumps(report.model_dump(), indent=2, sort_keys=True))
        return 0

    if args.command == "make-manifest":
        bundle = load_experiment_bundle(args.experiment_config)
        run_dir = initialize_run_dir(bundle, args.run_dir)
        print(run_dir)
        return 0

    if args.command == "preflight":
        diagnostics = inspect_run_dir(args.run_dir)
        print(json.dumps(diagnostics, indent=2, sort_keys=True))
        return 0

    if args.command == "run":
        result = execute_run(args.run_dir)
        print(
            f"Completed {result['completed_trials']} of {result['total_trials']} trials in "
            f"{result['run_dir']}."
        )
        return 0

    if args.command == "export-labels":
        export_path = export_annotation_csv(args.run_dir)
        print(export_path)
        return 0

    if args.command == "export-adjudication-sheet":
        export_path = export_adjudication_csv(args.run_dir)
        print(export_path)
        return 0

    if args.command == "import-labels":
        output_path = import_labels_csv(
            args.run_dir,
            args.labels_csv,
            stage=args.stage,
            annotator_id=args.annotator_id,
            annotator_type=args.annotator_type,
            rubric_version=args.rubric_version,
            blinding_mode=args.blinding_mode,
            agreement_sample_design=args.agreement_sample_design,
        )
        print(output_path)
        return 0

    if args.command == "summarize":
        summary = summarize_run(args.run_dir)
        print(summary["run_id"])
        return 0

    if args.command == "finalize-labels":
        output_path = finalize_labels(args.run_dir, strict=not args.allow_provisional)
        print(output_path)
        return 0

    if args.command == "draft-results":
        output_path = draft_paper_results(args.run_dir)
        print(output_path)
        return 0

    if args.command == "draft-manuscript":
        output_path = draft_manuscript_section(args.run_dir)
        print(output_path)
        return 0

    if args.command == "draft-full-manuscript":
        outputs = draft_full_manuscript(
            args.run_dir,
            manuscript_spec_path=args.manuscript_spec,
            output_path=args.output_path,
        )
        print(
            json.dumps(
                {key: str(value) for key, value in outputs.items()},
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    if args.command == "lock-manuscript-spec":
        outputs = lock_manuscript_spec(
            args.run_dir,
            manuscript_spec_path=args.manuscript_spec,
            output_path=args.output_path,
        )
        print(
            json.dumps(
                {key: str(value) for key, value in outputs.items()},
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    if args.command in {"typeset-full-manuscript", "typeset-paper"}:
        outputs = typeset_full_manuscript(
            args.run_dir,
            manuscript_spec_path=args.manuscript_spec,
            output_path=args.output_path,
        )
        print(
            json.dumps(
                {key: str(value) for key, value in outputs.items()},
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    if args.command == "build-submission-bundle":
        outputs = build_submission_bundle(
            args.run_dir,
            manuscript_spec_path=args.manuscript_spec,
            output_path=args.output_path,
            locked_spec_output_path=args.locked_spec_output_path,
        )
        print(
            json.dumps(
                {key: str(value) for key, value in outputs.items()},
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    if args.command == "package-evidence":
        outputs = package_evidence(
            args.run_dir,
            output_path=args.output_path,
        )
        print(
            json.dumps(
                {key: str(value) for key, value in outputs.items()},
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    if args.command == "verify-evidence":
        outputs = verify_evidence(
            args.run_dir,
            evidence_path=args.evidence_path,
            output_path=args.output_path,
        )
        print(
            json.dumps(
                {key: str(value) for key, value in outputs.items()},
                indent=2,
                sort_keys=True,
            )
        )
        return 0 if outputs["status"] == "ok" else 1

    if args.command == "draft-evidence-index":
        outputs = draft_evidence_index(
            args.run_dir,
            output_path=args.output_path,
        )
        print(
            json.dumps(
                {key: str(value) for key, value in outputs.items()},
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    if args.command == "generate-repo-assets":
        outputs = write_repo_visuals(args.run_dir, args.output_dir)
        print(
            json.dumps(
                {key: str(value) for key, value in outputs.items()},
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    if args.command == "smoke-test":
        return run_smoke_test(
            experiment_config_path=args.experiment_config,
            labels_csv_path=args.labels_csv,
            run_dir=args.run_dir,
        )

    parser.error(f"Unhandled command: {args.command}")
    return 1


def run_smoke_test(
    *,
    experiment_config_path: str,
    labels_csv_path: str,
    run_dir: str | None = None,
) -> int:
    bundle = load_experiment_bundle(experiment_config_path)
    resolved_run_dir = initialize_run_dir(bundle, run_dir)
    execute_run(resolved_run_dir)
    export_annotation_csv(resolved_run_dir)
    import_labels_csv(resolved_run_dir, labels_csv_path)
    summarize_run(resolved_run_dir)
    print(resolved_run_dir)
    return 0
