from pathlib import Path
from types import SimpleNamespace

from anti_omission.cli import main
from anti_omission.typesetting import (
    _convert_markdown_fragment_to_latex,
    _extract_title,
    _normalize_appendix_latex_structure,
    _promote_appendix_headings,
    _stage_image_assets,
    typeset_full_manuscript,
)


def test_extract_title_removes_top_heading() -> None:
    title, body = _extract_title(
        "# Example Paper\n\n_Short title: Example_\n\n## Abstract\n\nBody.\n"
    )

    assert title == "Example Paper"
    assert body.startswith("_Short title: Example_")
    assert "# Example Paper" not in body


def test_stage_image_assets_converts_svg_and_rewrites_links(tmp_path: Path, monkeypatch) -> None:
    source_dir = tmp_path / "docs"
    source_dir.mkdir()
    markdown_path = source_dir / "paper.md"
    svg_path = source_dir / "figure.svg"
    svg_path.write_text("<svg></svg>\n", encoding="utf-8")
    assets_dir = source_dir / "paper_assets"

    def fake_convert(source_path: Path, target_path: Path) -> None:
        assert source_path == svg_path
        target_path.write_text("%PDF-1.4\n", encoding="utf-8")

    monkeypatch.setattr("anti_omission.typesetting._convert_svg_to_pdf", fake_convert)

    rewritten = _stage_image_assets(
        "![Figure](figure.svg)\n",
        source_markdown_path=markdown_path,
        assets_dir=assets_dir,
    )

    assert rewritten.strip() == "![Figure](paper_assets/figure.pdf)"
    assert (assets_dir / "figure.pdf").exists()


def test_stage_image_assets_prefers_sibling_pdf_for_svg(tmp_path: Path) -> None:
    source_dir = tmp_path / "docs"
    source_dir.mkdir()
    markdown_path = source_dir / "paper.md"
    svg_path = source_dir / "figure.svg"
    pdf_path = source_dir / "figure.pdf"
    svg_path.write_text("<svg></svg>\n", encoding="utf-8")
    pdf_path.write_text("%PDF-1.4\n", encoding="utf-8")
    assets_dir = source_dir / "paper_assets"

    rewritten = _stage_image_assets(
        "![Figure](figure.svg)\n",
        source_markdown_path=markdown_path,
        assets_dir=assets_dir,
    )

    assert rewritten.strip() == "![Figure](paper_assets/figure.pdf)"
    assert (assets_dir / "figure.pdf").read_text(encoding="utf-8") == "%PDF-1.4\n"


def test_convert_markdown_fragment_to_latex_allows_raw_tex_citations(
    tmp_path: Path,
    monkeypatch,
) -> None:
    seen_command: list[str] = []

    def fake_run(command, cwd, check, capture_output, text):
        nonlocal seen_command
        seen_command = command
        return SimpleNamespace(stdout="\\citet{demo2026}\n", stderr="")

    monkeypatch.setattr("anti_omission.typesetting.subprocess.run", fake_run)

    converted = _convert_markdown_fragment_to_latex(
        "Prior work \\citet{demo2026} matters.\n",
        cwd=tmp_path,
        pandoc="pandoc",
    )

    assert "--from=markdown+raw_tex+implicit_figures+pipe_tables+table_captions" in seen_command
    assert "\\citet{demo2026}" in converted


def test_promote_appendix_headings_makes_appendix_sections_top_level() -> None:
    promoted = _promote_appendix_headings(
        "### Condition Texts\n\n#### Table B1. Something\n"
    )

    assert promoted.splitlines()[0] == "# Condition Texts"
    assert promoted.splitlines()[2] == "## Table B1. Something"


def test_normalize_appendix_latex_structure_demotes_non_major_sections() -> None:
    normalized = _normalize_appendix_latex_structure(
        "\\section{Condition Texts}\n"
        "\\section{\\texorpdfstring{\\texttt{baseline}}{baseline}}\n"
        "\\section{Generated Tables}\n"
        "\\section{Table B1. Confirmatory Bank Composition}\n"
    )

    assert "\\section{Condition Texts}" in normalized
    assert "\\subsection{\\texorpdfstring{\\texttt{baseline}}{baseline}}" in normalized
    assert "\\section{Generated Tables}" in normalized
    assert "\\subsection{Table B1. Confirmatory Bank Composition}" in normalized


def test_typeset_full_manuscript_writes_tex_and_pdf_outputs(tmp_path: Path, monkeypatch) -> None:
    docs_dir = tmp_path / "generated"
    docs_dir.mkdir()
    figure_path = docs_dir / "figure.svg"
    figure_path.write_text("<svg></svg>\n", encoding="utf-8")
    run_markdown = docs_dir / "run_paper.md"
    repo_markdown = docs_dir / "repo_paper.md"
    manuscript_text = (
        "# Example Paper\n\n"
        "## Abstract\n\n"
        "Abstract body.\n\n"
        "## Introduction\n\n"
        "![Figure](figure.svg)\n"
    )
    run_markdown.write_text(manuscript_text, encoding="utf-8")
    repo_markdown.write_text(manuscript_text, encoding="utf-8")

    monkeypatch.setattr(
        "anti_omission.typesetting.draft_full_manuscript",
        lambda run_dir, manuscript_spec_path, output_path=None: {
            "run_local_path": run_markdown,
            "repo_output_path": repo_markdown,
        },
    )
    monkeypatch.setattr(
        "anti_omission.typesetting.load_manuscript_spec_bundle",
        lambda manuscript_spec_path: SimpleNamespace(
            manuscript_spec=SimpleNamespace(
                render_mode="neurips_anonymous_2025",
                bibliography_path="",
            ),
            manuscript_spec_path=tmp_path / "spec.json",
        ),
    )
    monkeypatch.setattr(
        "anti_omission.typesetting._require_command",
        lambda command_name: command_name,
    )
    monkeypatch.setattr(
        "anti_omission.typesetting._convert_markdown_fragment_to_latex",
        lambda markdown_text, *, cwd, pandoc: (
            "\\section{Introduction}\nBody.\n"
            if "## Introduction" in markdown_text or "# Introduction" in markdown_text
            else "Abstract body.\n"
        ),
    )

    def fake_run(command: list[str], *, cwd: Path) -> None:
        if command[0] == "rsvg-convert":
            target_path = Path(command[command.index("--output") + 1])
            target_path.write_text("%PDF-1.4\n", encoding="utf-8")
            return
        if command[0] == "pdflatex":
            output_path = cwd / Path(command[-1]).with_suffix(".pdf")
            output_path.write_text("%PDF-1.4\n", encoding="utf-8")
            return
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr("anti_omission.typesetting._run_command", fake_run)

    outputs = typeset_full_manuscript(
        run_dir="ignored-run-dir",
        manuscript_spec_path="ignored-spec.json",
    )

    assert outputs["run_local_tex_path"].exists()
    assert outputs["run_local_pdf_path"].exists()
    assert outputs["repo_tex_path"].exists()
    assert outputs["repo_pdf_path"].exists()
    tex_text = outputs["run_local_tex_path"].read_text(encoding="utf-8")
    assert "\\usepackage{neurips_2025}" in tex_text
    assert "Anonymous Submission" in tex_text
    assert "Anonymous Author(s)" not in tex_text
    assert (docs_dir / "run_paper_assets" / "figure.pdf").exists()
    assert (docs_dir / "repo_paper_assets" / "figure.pdf").exists()


def test_typeset_full_manuscript_runs_bibtex_when_bibliography_present(tmp_path: Path, monkeypatch) -> None:
    docs_dir = tmp_path / "generated"
    docs_dir.mkdir()
    run_markdown = docs_dir / "run_paper.md"
    repo_markdown = docs_dir / "repo_paper.md"
    bibliography = tmp_path / "refs.bib"
    bibliography.write_text("@article{dummy,title={Dummy},author={Anon},year={2026}}\n", encoding="utf-8")
    manuscript_text = (
        "# Example Paper\n\n"
        "## Abstract\n\n"
        "Abstract body.\n\n"
        "## Introduction\n\n"
        "Intro body.\n\n"
        "## References\n\n"
        "Bibliography source note.\n"
    )
    run_markdown.write_text(manuscript_text, encoding="utf-8")
    repo_markdown.write_text(manuscript_text, encoding="utf-8")

    monkeypatch.setattr(
        "anti_omission.typesetting.draft_full_manuscript",
        lambda run_dir, manuscript_spec_path, output_path=None: {
            "run_local_path": run_markdown,
            "repo_output_path": repo_markdown,
        },
    )
    monkeypatch.setattr(
        "anti_omission.typesetting.load_manuscript_spec_bundle",
        lambda manuscript_spec_path: SimpleNamespace(
            manuscript_spec=SimpleNamespace(
                render_mode="neurips_anonymous_2025",
                bibliography_path=str(bibliography),
            ),
            manuscript_spec_path=tmp_path / "spec.json",
        ),
    )
    monkeypatch.setattr(
        "anti_omission.typesetting._require_command",
        lambda command_name: command_name,
    )
    monkeypatch.setattr(
        "anti_omission.typesetting._convert_markdown_fragment_to_latex",
        lambda markdown_text, *, cwd, pandoc: "Converted.\n",
    )

    seen_commands: list[list[str]] = []

    def fake_run(command: list[str], *, cwd: Path) -> None:
        seen_commands.append(command)
        if command[0] == "pdflatex":
            output_path = cwd / Path(command[-1]).with_suffix(".pdf")
            output_path.write_text("%PDF-1.4\n", encoding="utf-8")
            return
        if command[0] == "bibtex":
            (cwd / f"{command[1]}.bbl").write_text("% generated bibliography\n", encoding="utf-8")
            return
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr("anti_omission.typesetting._run_command", fake_run)

    outputs = typeset_full_manuscript(
        run_dir="ignored-run-dir",
        manuscript_spec_path="ignored-spec.json",
    )

    tex_text = outputs["run_local_tex_path"].read_text(encoding="utf-8")
    assert "\\nocite{*}" in tex_text
    assert "\\bibliography{references}" in tex_text
    assert any(command[0] == "bibtex" for command in seen_commands)
    assert (docs_dir / "references.bib").exists()


def test_cli_typeset_full_manuscript_smoke(tmp_path: Path, monkeypatch) -> None:
    expected = {
        "run_local_markdown_path": tmp_path / "run.md",
        "run_local_tex_path": tmp_path / "run.tex",
        "run_local_pdf_path": tmp_path / "run.pdf",
        "repo_markdown_path": tmp_path / "repo.md",
        "repo_tex_path": tmp_path / "repo.tex",
        "repo_pdf_path": tmp_path / "repo.pdf",
    }
    monkeypatch.setattr(
        "anti_omission.cli.typeset_full_manuscript",
        lambda run_dir, manuscript_spec_path, output_path=None: expected,
    )

    exit_code = main(
        [
            "typeset-full-manuscript",
            "--run-dir",
            "outputs/runs/example",
            "--manuscript-spec",
            "configs/reporting/example.json",
        ]
    )

    assert exit_code == 0


def test_cli_typeset_paper_alias_smoke(tmp_path: Path, monkeypatch) -> None:
    expected = {
        "run_local_markdown_path": tmp_path / "run.md",
        "run_local_tex_path": tmp_path / "run.tex",
        "run_local_pdf_path": tmp_path / "run.pdf",
        "repo_markdown_path": tmp_path / "repo.md",
        "repo_tex_path": tmp_path / "repo.tex",
        "repo_pdf_path": tmp_path / "repo.pdf",
    }
    monkeypatch.setattr(
        "anti_omission.cli.typeset_full_manuscript",
        lambda run_dir, manuscript_spec_path, output_path=None: expected,
    )

    exit_code = main(
        [
            "typeset-paper",
            "--run-dir",
            "outputs/runs/example",
            "--manuscript-spec",
            "configs/reporting/example.json",
        ]
    )

    assert exit_code == 0
