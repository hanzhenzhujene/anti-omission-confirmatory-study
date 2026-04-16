from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from anti_omission.config import load_manuscript_spec_bundle
from anti_omission.reporting import draft_full_manuscript


IMAGE_PATTERN = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
TOP_LEVEL_SECTION_PATTERN = re.compile(r"^# (.+)$", re.MULTILINE)
SUPPORTED_RENDER_MODE = "neurips_anonymous_2025"
MAJOR_APPENDIX_SECTION_MARKERS = (
    "Condition Texts",
    "Generated Tables",
    "Paired Scenario Matrix",
    "Label Agreement and Reproducibility",
    "Artifact Provenance",
)


class TypesettingError(RuntimeError):
    """Raised when a manuscript cannot be converted to LaTeX or PDF."""


@dataclass(frozen=True)
class ManuscriptParts:
    title: str
    abstract_markdown: str
    body_markdown: str
    references_markdown: str
    appendix_markdown: str


def typeset_full_manuscript(
    run_dir: str | Path,
    manuscript_spec_path: str | Path,
    output_path: str | Path | None = None,
) -> dict[str, Path]:
    spec_bundle = load_manuscript_spec_bundle(manuscript_spec_path)
    manuscript_outputs = draft_full_manuscript(
        run_dir=run_dir,
        manuscript_spec_path=manuscript_spec_path,
        output_path=output_path,
    )

    if spec_bundle.manuscript_spec.render_mode != SUPPORTED_RENDER_MODE:
        raise TypesettingError(
            "Unsupported manuscript render_mode: "
            f"{spec_bundle.manuscript_spec.render_mode}"
        )

    run_local_markdown = manuscript_outputs["run_local_path"]
    repo_markdown = manuscript_outputs["repo_output_path"]

    bibliography_path = _resolve_optional_spec_path(
        spec_bundle.manuscript_spec_path,
        spec_bundle.manuscript_spec.bibliography_path,
    )

    run_local_typeset = _typeset_markdown_document(
        run_local_markdown,
        bibliography_path=bibliography_path,
    )
    repo_typeset = _typeset_markdown_document(
        repo_markdown,
        bibliography_path=bibliography_path,
    )

    return {
        "run_local_markdown_path": run_local_markdown,
        "run_local_tex_path": run_local_typeset["tex_path"],
        "run_local_pdf_path": run_local_typeset["pdf_path"],
        "repo_markdown_path": repo_markdown,
        "repo_tex_path": repo_typeset["tex_path"],
        "repo_pdf_path": repo_typeset["pdf_path"],
    }


def _typeset_markdown_document(
    markdown_path: str | Path,
    *,
    bibliography_path: Path | None = None,
) -> dict[str, Path]:
    resolved_markdown = Path(markdown_path).resolve()
    output_base = resolved_markdown.with_suffix("")
    tex_path = output_base.with_suffix(".tex")
    pdf_path = output_base.with_suffix(".pdf")
    assets_dir = output_base.parent / f"{output_base.name}_assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    manuscript_parts = _parse_manuscript_markdown(resolved_markdown.read_text(encoding="utf-8"))
    staged_abstract = _stage_image_assets(
        manuscript_parts.abstract_markdown,
        source_markdown_path=resolved_markdown,
        assets_dir=assets_dir,
    )
    staged_body = _stage_image_assets(
        manuscript_parts.body_markdown,
        source_markdown_path=resolved_markdown,
        assets_dir=assets_dir,
    )
    staged_references = _stage_image_assets(
        manuscript_parts.references_markdown,
        source_markdown_path=resolved_markdown,
        assets_dir=assets_dir,
    )
    staged_appendix = _stage_image_assets(
        manuscript_parts.appendix_markdown,
        source_markdown_path=resolved_markdown,
        assets_dir=assets_dir,
    )

    pandoc = _require_command("pandoc")
    pdflatex = _require_command("pdflatex")
    bibtex = _require_command("bibtex") if bibliography_path else None
    _stage_neurips_style(output_base.parent)

    abstract_latex = _convert_markdown_fragment_to_latex(staged_abstract, cwd=output_base.parent, pandoc=pandoc)
    body_latex = _convert_markdown_fragment_to_latex(staged_body, cwd=output_base.parent, pandoc=pandoc)
    references_latex = _convert_markdown_fragment_to_latex(
        staged_references,
        cwd=output_base.parent,
        pandoc=pandoc,
    )
    appendix_latex = _normalize_appendix_latex_structure(
        _convert_markdown_fragment_to_latex(staged_appendix, cwd=output_base.parent, pandoc=pandoc)
    )
    staged_bibliography = (
        _stage_bibliography_file(bibliography_path, output_base.parent)
        if bibliography_path is not None
        else None
    )
    tex_path.write_text(
        _build_neurips_latex_document(
            title=manuscript_parts.title,
            abstract_latex=abstract_latex,
            body_latex=body_latex,
            references_latex=references_latex,
            appendix_latex=appendix_latex,
            bibliography_basename="references" if staged_bibliography else None,
        ),
        encoding="utf-8",
    )

    _run_command(
        [
            pdflatex,
            "-interaction=nonstopmode",
            "-halt-on-error",
            tex_path.name,
        ],
        cwd=output_base.parent,
    )
    if staged_bibliography and bibtex:
        _run_command(
            [
                bibtex,
                tex_path.stem,
            ],
            cwd=output_base.parent,
        )
    _run_command(
        [
            pdflatex,
            "-interaction=nonstopmode",
            "-halt-on-error",
            tex_path.name,
        ],
        cwd=output_base.parent,
    )
    _cleanup_latex_auxiliaries(tex_path)

    return {
        "tex_path": tex_path,
        "pdf_path": pdf_path,
        "assets_dir": assets_dir,
    }


def _parse_manuscript_markdown(markdown_text: str) -> ManuscriptParts:
    title, body_text = _extract_title(markdown_text)
    if not title:
        raise TypesettingError("Expected a top-level manuscript title heading.")

    normalized = _normalize_heading_levels(body_text)
    sections = _split_top_level_sections(normalized)
    abstract_markdown = sections.pop("Abstract", "").strip()
    references_markdown = sections.pop("References", "").strip()
    appendix_markdown = sections.pop("Appendix", "").strip()

    if not abstract_markdown:
        raise TypesettingError("Expected a top-level `Abstract` section in the manuscript markdown.")

    body_markdown = _join_sections(sections)
    return ManuscriptParts(
        title=title,
        abstract_markdown=abstract_markdown + "\n",
        body_markdown=body_markdown,
        references_markdown=references_markdown + ("\n" if references_markdown else ""),
        appendix_markdown=_promote_appendix_headings(appendix_markdown) + ("\n" if appendix_markdown else ""),
    )


def _extract_title(markdown_text: str) -> tuple[str | None, str]:
    lines = markdown_text.splitlines()
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("# "):
            title = stripped[2:].strip()
            remaining = lines[index + 1 :]
            while remaining and not remaining[0].strip():
                remaining = remaining[1:]
            return title, "\n".join(remaining).rstrip() + "\n"
        break
    return None, markdown_text if markdown_text.endswith("\n") else markdown_text + "\n"


def _normalize_heading_levels(markdown_text: str) -> str:
    normalized_lines: list[str] = []
    for line in markdown_text.splitlines():
        if line.startswith("_Generated deterministically "):
            continue
        if line.startswith("#### "):
            normalized_lines.append("### " + line[5:])
        elif line.startswith("### "):
            normalized_lines.append("## " + line[4:])
        elif line.startswith("## "):
            normalized_lines.append("# " + line[3:])
        else:
            normalized_lines.append(line)
    return "\n".join(normalized_lines).strip() + "\n"


def _promote_appendix_headings(markdown_text: str) -> str:
    if not markdown_text:
        return markdown_text

    promoted_lines: list[str] = []
    for line in markdown_text.splitlines():
        match = re.match(r"^(#{2,6})\s+(.*)$", line)
        if not match:
            promoted_lines.append(line)
            continue
        hashes, text = match.groups()
        promoted_level = max(1, len(hashes) - 2)
        promoted_lines.append("#" * promoted_level + " " + text)
    return "\n".join(promoted_lines)


def _split_top_level_sections(markdown_text: str) -> dict[str, str]:
    matches = list(TOP_LEVEL_SECTION_PATTERN.finditer(markdown_text))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        heading = match.group(1).strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown_text)
        content = markdown_text[start:end].strip()
        sections[heading] = content + ("\n" if content else "")
    return sections


def _join_sections(sections: dict[str, str]) -> str:
    chunks: list[str] = []
    for heading, content in sections.items():
        chunks.append(f"# {heading}\n\n{content.strip()}\n")
    return "\n".join(chunks).strip() + ("\n" if chunks else "")


def _stage_image_assets(
    markdown_text: str,
    *,
    source_markdown_path: Path,
    assets_dir: Path,
) -> str:
    assets_dir.mkdir(parents=True, exist_ok=True)

    def replace(match: re.Match[str]) -> str:
        alt_text, raw_target = match.groups()
        target = raw_target.strip().strip("<>")
        source_asset = (source_markdown_path.parent / target).resolve()
        if not source_asset.exists():
            raise TypesettingError(f"Referenced image asset does not exist: {source_asset}")

        asset_target = _stage_single_asset(source_asset, assets_dir)
        relative_target = asset_target.relative_to(source_markdown_path.with_suffix("").parent)
        return f"![{alt_text}]({relative_target.as_posix()})"

    return IMAGE_PATTERN.sub(replace, markdown_text)


def _stage_single_asset(source_asset: Path, assets_dir: Path) -> Path:
    suffix = source_asset.suffix.lower()
    if suffix == ".svg":
        sibling_pdf = source_asset.with_suffix(".pdf")
        if sibling_pdf.exists():
            asset_target = assets_dir / sibling_pdf.name
            shutil.copy2(sibling_pdf, asset_target)
            return asset_target
        asset_target = assets_dir / f"{source_asset.stem}.pdf"
        _convert_svg_to_pdf(source_asset, asset_target)
        return asset_target

    asset_target = assets_dir / source_asset.name
    shutil.copy2(source_asset, asset_target)
    return asset_target


def _convert_markdown_fragment_to_latex(markdown_text: str, *, cwd: Path, pandoc: str) -> str:
    if not markdown_text.strip():
        return ""

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".md", dir=cwd, delete=False) as handle:
        temp_markdown_path = Path(handle.name)
        handle.write(markdown_text)

    try:
        result = subprocess.run(
            [
                pandoc,
                str(temp_markdown_path),
                "--from=markdown+raw_tex+implicit_figures+pipe_tables+table_captions",
                "--to=latex",
                "--wrap=none",
            ],
            cwd=str(cwd),
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() or exc.stdout.strip() or "no error output captured"
        raise TypesettingError(f"Command failed: pandoc fragment conversion\n{stderr}") from exc
    finally:
        temp_markdown_path.unlink(missing_ok=True)

    return _sanitize_latex_fragment(result.stdout)


def _build_neurips_latex_document(
    *,
    title: str,
    abstract_latex: str,
    body_latex: str,
    references_latex: str,
    appendix_latex: str,
    bibliography_basename: str | None = None,
) -> str:
    appendix_block = ""
    if appendix_latex.strip():
        appendix_block = "\n\\appendix\n" + appendix_latex.strip() + "\n"
    if bibliography_basename:
        cite_search_space = "\n".join(
            fragment.strip()
            for fragment in (body_latex, references_latex, appendix_latex)
            if fragment.strip()
        )
        nocite_block = "\n\\nocite{*}" if not _contains_latex_citation(cite_search_space) else ""
        references_block = (
            nocite_block
            + "\n\\bibliographystyle{plainnat}\n\\bibliography{"
            + _latex_escape(bibliography_basename)
            + "}\n"
        )
    elif references_latex.strip():
        references_block = "\n" + references_latex.strip() + "\n"
    else:
        references_block = ""

    return "\n".join(
        [
            "\\documentclass{article}",
            "\\usepackage{neurips_2025}",
            "\\usepackage[utf8]{inputenc}",
            "\\usepackage[T1]{fontenc}",
            "\\usepackage{lmodern}",
            "\\renewcommand{\\rmdefault}{lmr}",
            "\\renewcommand{\\sfdefault}{lmss}",
            "\\renewcommand{\\ttdefault}{lmtt}",
            "\\usepackage{hyperref}",
            "\\usepackage{url}",
            "\\usepackage{booktabs}",
            "\\usepackage{amsfonts}",
            "\\usepackage{microtype}",
            "\\usepackage{xcolor}",
            "\\usepackage{calc}",
            "\\usepackage{graphicx}",
            "\\usepackage{longtable,booktabs,array}",
            "\\usepackage{caption}",
            "\\usepackage{float}",
            "\\makeatletter",
            "\\newsavebox\\pandoc@box",
            "\\newcommand*\\pandocbounded[1]{%",
            "  \\sbox\\pandoc@box{#1}%",
            "  \\Gscale@div\\@tempa{\\textheight}{\\dimexpr\\ht\\pandoc@box+\\dp\\pandoc@box\\relax}%",
            "  \\Gscale@div\\@tempb{\\linewidth}{\\wd\\pandoc@box}%",
            "  \\ifdim\\@tempb\\p@<\\@tempa\\p@\\let\\@tempa\\@tempb\\fi%",
            "  \\ifdim\\@tempa\\p@<\\p@\\scalebox{\\@tempa}{\\usebox\\pandoc@box}%",
            "  \\else\\usebox{\\pandoc@box}%",
            "  \\fi%",
            "}",
            "\\makeatother",
            "\\providecommand{\\tightlist}{%",
            "  \\setlength{\\itemsep}{0pt}\\setlength{\\parskip}{0pt}}",
            "\\setlength{\\emergencystretch}{3em}",
            "\\hypersetup{pdftitle={" + _latex_escape(title) + "}, hidelinks}",
            "\\title{" + _latex_escape(title) + "}",
            "\\author{}",
            "\\date{}",
            "\\makeatletter",
            "\\renewcommand{\\@maketitle}{%",
            "  \\vbox{%",
            "    \\hsize\\textwidth",
            "    \\linewidth\\hsize",
            "    \\vskip 0.1in",
            "    \\@toptitlebar",
            "    \\centering",
            "    {\\LARGE\\bf \\@title\\par}",
            "    \\@bottomtitlebar",
            "    \\if@anonymous",
            "      \\begin{tabular}[t]{c}\\bf\\rule{\\z@}{24\\p@}",
            "        Anonymous Submission \\\\",
            "        {\\normalfont\\small Double-blind review copy} \\\\",
            "      \\end{tabular}%",
            "    \\else",
            "      \\def\\And{%",
            "        \\end{tabular}\\hfil\\linebreak[0]\\hfil%",
            "        \\begin{tabular}[t]{c}\\bf\\rule{\\z@}{24\\p@}\\ignorespaces%",
            "      }",
            "      \\def\\AND{%",
            "        \\end{tabular}\\hfil\\linebreak[4]\\hfil%",
            "        \\begin{tabular}[t]{c}\\bf\\rule{\\z@}{24\\p@}\\ignorespaces%",
            "      }",
            "      \\begin{tabular}[t]{c}\\bf\\rule{\\z@}{24\\p@}\\@author\\end{tabular}%",
            "    \\fi",
            "    \\vskip 0.26in \\@minus 0.08in",
            "  }",
            "}",
            "\\makeatother",
            "\\begin{document}",
            "\\maketitle",
            "\\begin{abstract}",
            abstract_latex.strip(),
            "\\end{abstract}",
            body_latex.strip(),
            references_block.rstrip(),
            appendix_block.rstrip(),
            "\\end{document}",
            "",
        ]
    )


def _sanitize_latex_fragment(text: str) -> str:
    sanitized = text
    sanitized = re.sub(r",\s*alt=\{[^}]*\}", "", sanitized)
    sanitized = re.sub(r"alt=\{[^}]*\},\s*", "", sanitized)
    sanitized = sanitized.replace("\\section{Appendix}", "")
    return sanitized.strip() + ("\n" if sanitized.strip() else "")


def _normalize_appendix_latex_structure(text: str) -> str:
    if not text.strip():
        return text

    normalized_lines: list[str] = []
    for line in text.splitlines():
        if line.startswith("\\section{") and not any(marker in line for marker in MAJOR_APPENDIX_SECTION_MARKERS):
            normalized_lines.append(line.replace("\\section{", "\\subsection{", 1))
            continue
        normalized_lines.append(line)
    return "\n".join(normalized_lines).strip() + "\n"


def _contains_latex_citation(text: str) -> bool:
    return bool(re.search(r"\\cite[a-zA-Z*]*\{", text))


def _stage_neurips_style(output_dir: Path) -> None:
    vendor_root = Path(__file__).resolve().parents[2] / "vendor"
    source_style = vendor_root / "neurips_2025" / "neurips_2025.sty"
    if not source_style.exists():
        raise TypesettingError(f"Vendored NeurIPS style file not found: {source_style}")
    shutil.copy2(source_style, output_dir / "neurips_2025.sty")
    environ_support = vendor_root / "tex_support" / "environ.sty"
    if environ_support.exists():
        shutil.copy2(environ_support, output_dir / "environ.sty")


def _convert_svg_to_pdf(source_path: Path, target_path: Path) -> None:
    converter = _require_command("rsvg-convert")
    _run_command(
        [
            converter,
            "--format=pdf",
            "--output",
            str(target_path),
            str(source_path),
        ],
        cwd=target_path.parent,
    )


def _cleanup_latex_auxiliaries(tex_path: Path) -> None:
    for suffix in (".aux", ".log", ".out", ".toc", ".blg"):
        tex_path.with_suffix(suffix).unlink(missing_ok=True)


def _resolve_optional_spec_path(spec_path: Path, raw_path: str) -> Path | None:
    if not raw_path:
        return None
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = (spec_path.parent / candidate).resolve()
    return candidate


def _stage_bibliography_file(source_path: Path, output_dir: Path) -> Path:
    if not source_path.exists():
        raise TypesettingError(f"Bibliography file not found: {source_path}")
    destination = output_dir / "references.bib"
    shutil.copy2(source_path, destination)
    return destination


def _latex_escape(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    escaped = text
    for old, new in replacements.items():
        escaped = escaped.replace(old, new)
    return escaped


def _require_command(command_name: str) -> str:
    resolved = shutil.which(command_name)
    if not resolved:
        raise TypesettingError(
            f"Required command `{command_name}` was not found on PATH."
        )
    return resolved


def _run_command(command: list[str], *, cwd: Path) -> None:
    try:
        subprocess.run(
            command,
            cwd=str(cwd),
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() or exc.stdout.strip() or "no error output captured"
        raise TypesettingError(
            f"Command failed: {' '.join(command)}\n{stderr}"
        ) from exc
