from __future__ import annotations

import csv
import shutil
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

from matplotlib import pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

from anti_omission.io_utils import read_json


TEXT_COLOR = "#0F172A"
MUTED_TEXT = "#475569"
BORDER_COLOR = "#CBD5E1"
CARD_FILL = "#F8FAFC"
BACKGROUND = "#FFFFFF"

BASELINE_COLOR = "#475569"
GENERIC_COLOR = "#2563EB"
DISCLOSURE_COLOR = "#C2410C"

GOOD_LOW = "#E2F6F1"
GOOD_HIGH = "#0F766E"
BAD_LOW = "#FFF1E8"
BAD_HIGH = "#C2410C"


def write_repo_visuals(run_dir: str | Path, output_dir: str | Path) -> dict[str, Path]:
    resolved_run_dir = Path(run_dir).resolve()
    resolved_output_dir = Path(output_dir).resolve()
    resolved_output_dir.mkdir(parents=True, exist_ok=True)

    _ensure_publication_assets(resolved_run_dir)

    analysis_dir = resolved_run_dir / "analysis"
    run_snapshot = read_json(resolved_run_dir / "run_config.json")
    summary = read_json(analysis_dir / "summary.json")
    evidence_package = (
        read_json(analysis_dir / "evidence_package.json")
        if (analysis_dir / "evidence_package.json").exists()
        else None
    )
    evidence_verification = (
        read_json(analysis_dir / "evidence_verification.json")
        if (analysis_dir / "evidence_verification.json").exists()
        else None
    )
    table2_rows = _read_csv_rows(analysis_dir / "paper_table_2_condition_outcomes.csv")

    overview_svg = resolved_output_dir / "confirmatory_overview.svg"
    overview_png = resolved_output_dir / "confirmatory_overview.png"
    tradeoff_svg = resolved_output_dir / "confirmatory_primary_tradeoff.svg"
    timeliness_svg = resolved_output_dir / "confirmatory_timeliness.svg"

    _plot_confirmatory_overview(
        run_snapshot=run_snapshot,
        summary=summary,
        evidence_package=evidence_package,
        evidence_verification=evidence_verification,
        table2_rows=table2_rows,
        output_svg=overview_svg,
        output_png=overview_png,
    )

    shutil.copy2(analysis_dir / "paper_figure_1_primary_tradeoff.svg", tradeoff_svg)
    shutil.copy2(analysis_dir / "paper_figure_s1_timeliness.svg", timeliness_svg)

    return {
        "overview_svg_path": overview_svg,
        "overview_png_path": overview_png,
        "tradeoff_svg_path": tradeoff_svg,
        "timeliness_svg_path": timeliness_svg,
    }


def _ensure_publication_assets(run_dir: Path) -> None:
    analysis_dir = run_dir / "analysis"
    required_paths = [
        analysis_dir / "paper_table_2_condition_outcomes.csv",
        analysis_dir / "paper_figure_1_primary_tradeoff.svg",
        analysis_dir / "paper_figure_s1_timeliness.svg",
    ]
    if all(path.exists() for path in required_paths):
        return

    from anti_omission.reporting import draft_paper_results

    draft_paper_results(run_dir)


def _plot_confirmatory_overview(
    *,
    run_snapshot: dict,
    summary: dict,
    evidence_package: dict | None,
    evidence_verification: dict | None,
    table2_rows: list[dict[str, str]],
    output_svg: Path,
    output_png: Path,
) -> None:
    figure = plt.figure(figsize=(12.8, 7.0), facecolor=BACKGROUND, constrained_layout=True)
    grid = figure.add_gridspec(2, 2, width_ratios=[1.05, 1.75], height_ratios=[0.35, 0.65])

    title_ax = figure.add_subplot(grid[0, :])
    info_ax = figure.add_subplot(grid[1, 0])
    matrix_ax = figure.add_subplot(grid[1, 1])

    for axis in (title_ax, info_ax, matrix_ax):
        axis.set_facecolor(BACKGROUND)

    _draw_title_panel(
        title_ax,
        run_snapshot=run_snapshot,
        summary=summary,
        evidence_package=evidence_package,
        evidence_verification=evidence_verification,
    )
    _draw_info_cards(
        info_ax,
        evidence_verification=evidence_verification,
    )
    _draw_metric_matrix(matrix_ax, table2_rows)

    output_svg.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_svg, format="svg", bbox_inches="tight")
    figure.savefig(output_png, format="png", dpi=200, bbox_inches="tight")
    plt.close(figure)


def _draw_title_panel(
    axis,
    *,
    run_snapshot: dict,
    summary: dict,
    evidence_package: dict | None,
    evidence_verification: dict | None,
) -> None:
    axis.axis("off")
    model_id = run_snapshot["model_config"]["model_id"]
    total_trials = summary["total_trials"]
    condition_count = len(run_snapshot["conditions"])
    risk_scenarios = summary["primary_risk_trials"] // condition_count
    benign_scenarios = summary["primary_benign_trials"] // condition_count
    final_stage = (evidence_package or {}).get("provenance", {}).get("final_stage", "unknown")
    verification_status = (evidence_verification or {}).get("status", "not_packaged")

    axis.text(
        0.0,
        0.95,
        "Anti-Omission Locked Confirmatory Study",
        fontsize=21,
        fontweight="bold",
        color=TEXT_COLOR,
        ha="left",
        va="top",
        transform=axis.transAxes,
    )
    axis.text(
        0.0,
        0.70,
        "A single-run, provenance-preserving confirmatory evaluation of a disclosure-duty prompt on GPT-5 Mini.",
        fontsize=11.5,
        color=MUTED_TEXT,
        ha="left",
        va="top",
        transform=axis.transAxes,
    )

    chip_rows = [
        [
            f"model: {model_id}",
            f"bank: {risk_scenarios} risk + {benign_scenarios} benign",
            f"manifest: {total_trials} trials",
        ],
        [
            f"labels: {final_stage}",
            f"evidence: {verification_status}",
        ],
    ]
    chip_height = 0.18
    for chip_y, chips in zip((0.42, 0.20), chip_rows, strict=True):
        chip_x = 0.0
        for chip in chips:
            width = 0.014 * len(chip) + 0.05
            axis.add_patch(
                FancyBboxPatch(
                    (chip_x, chip_y),
                    width,
                    chip_height,
                    boxstyle="round,pad=0.012,rounding_size=0.02",
                    linewidth=0.8,
                    edgecolor=BORDER_COLOR,
                    facecolor=CARD_FILL,
                    transform=axis.transAxes,
                )
            )
            axis.text(
                chip_x + 0.018,
                chip_y + chip_height / 2,
                chip,
                fontsize=9.2,
                color=TEXT_COLOR,
                ha="left",
                va="center",
                transform=axis.transAxes,
            )
            chip_x += width + 0.014

    axis.text(
        0.0,
        0.03,
        "Headline reading: the preregistered binary risk endpoint tied across all three conditions, while `disclosure_full` added benign false alarms and still showed non-trivial late disclosures.",
        fontsize=10.2,
        color=TEXT_COLOR,
        ha="left",
        va="bottom",
        transform=axis.transAxes,
    )


def _draw_info_cards(
    axis,
    *,
    evidence_verification: dict | None,
) -> None:
    axis.axis("off")

    cards = [
        {
            "title": "Study design",
            "lines": [
                "60 held-out scenarios",
                "3 locked conditions",
                "24 risk, 36 benign",
                "paired scenario-by-condition analysis",
            ],
        },
        {
            "title": "Labeling and provenance",
            "lines": [
                "blind condition-code exports",
                "two independent primary annotators",
                "adjudicated consensus finalization",
                f"verification status: {(evidence_verification or {}).get('status', 'not packaged')}",
            ],
        },
        {
            "title": "Interpretation boundary",
            "lines": [
                "primary endpoint: tied at 24/24",
                "no favorable tradeoff claim supported",
                "benign over-warning is material",
                "late disclosures remain non-trivial",
            ],
        },
    ]

    card_height = 0.265
    y_positions = [0.70, 0.38, 0.06]
    for y_position, card in zip(y_positions, cards, strict=True):
        axis.add_patch(
            FancyBboxPatch(
                (0.0, y_position),
                0.98,
                card_height,
                boxstyle="round,pad=0.014,rounding_size=0.028",
                linewidth=1.0,
                edgecolor=BORDER_COLOR,
                facecolor=CARD_FILL,
                transform=axis.transAxes,
            )
        )
        axis.text(
            0.05,
            y_position + card_height - 0.06,
            card["title"],
            fontsize=11.3,
            fontweight="bold",
            color=TEXT_COLOR,
            ha="left",
            va="top",
            transform=axis.transAxes,
        )
        for line_index, line in enumerate(card["lines"]):
            axis.text(
                0.06,
                y_position + card_height - 0.13 - 0.055 * line_index,
                f"• {line}",
                fontsize=9.5,
                color=MUTED_TEXT,
                ha="left",
                va="top",
                transform=axis.transAxes,
            )


def _draw_metric_matrix(axis, table2_rows: list[dict[str, str]]) -> None:
    axis.axis("off")
    axis.text(
        0.0,
        1.03,
        "Condition comparison at a glance",
        fontsize=13,
        fontweight="bold",
        color=TEXT_COLOR,
        ha="left",
        va="bottom",
        transform=axis.transAxes,
    )
    axis.text(
        0.0,
        0.97,
        "Green columns are efficacy metrics; orange columns are cost metrics.",
        fontsize=9.3,
        color=MUTED_TEXT,
        ha="left",
        va="bottom",
        transform=axis.transAxes,
    )

    row_labels = [
        _display_condition_name(row["condition_id"])
        for row in table2_rows
    ]
    col_specs = [
        ("Disc>=2 on risk", "risk_disclosure_proportion", "risk_disclosure_successes", "risk_disclosure_n", True),
        ("Score3 on risk", "score3_proportion", "score3_successes", "score3_n", True),
        ("Late risk", "late_proportion", "late_successes", "late_n", False),
        ("Benign false alarm", "benign_false_alarm_proportion", "benign_false_alarm_successes", "benign_false_alarm_n", False),
    ]

    left_margin = 0.22
    top = 0.86
    cell_w = 0.185
    cell_h = 0.19

    for col_index, (title, _prop_key, _succ_key, _n_key, _good_high) in enumerate(col_specs):
        x = left_margin + col_index * cell_w
        axis.text(
            x + cell_w / 2,
            top + 0.08,
            title,
            fontsize=9.8,
            fontweight="bold",
            color=TEXT_COLOR,
            ha="center",
            va="bottom",
            transform=axis.transAxes,
        )

    for row_index, row in enumerate(table2_rows):
        y = top - row_index * cell_h
        axis.text(
            0.0,
            y - cell_h / 2 + 0.01,
            row_labels[row_index],
            fontsize=10.2,
            color=_condition_color(row["condition_id"]),
            fontweight="bold" if row["condition_id"] == "disclosure_full" else "normal",
            ha="left",
            va="center",
            transform=axis.transAxes,
        )
        if row["condition_id"] == "disclosure_full":
            axis.add_patch(
                FancyBboxPatch(
                    (left_margin - 0.012, y - cell_h + 0.022),
                    cell_w * len(col_specs) + 0.024,
                    cell_h - 0.03,
                    boxstyle="round,pad=0.012,rounding_size=0.02",
                    linewidth=1.2,
                    edgecolor="#FDBA74",
                    facecolor="none",
                    transform=axis.transAxes,
                )
            )

        for col_index, (_title, prop_key, succ_key, n_key, good_high) in enumerate(col_specs):
            x = left_margin + col_index * cell_w
            proportion = float(row[prop_key])
            cell_color = _interpolate_color(
                GOOD_LOW if good_high else BAD_LOW,
                GOOD_HIGH if good_high else BAD_HIGH,
                proportion,
            )
            axis.add_patch(
                Rectangle(
                    (x, y - cell_h + 0.025),
                    cell_w - 0.012,
                    cell_h - 0.035,
                    linewidth=0.9,
                    edgecolor=BORDER_COLOR,
                    facecolor=cell_color,
                    transform=axis.transAxes,
                )
            )
            text_color = "white" if proportion > 0.65 else TEXT_COLOR
            axis.text(
                x + (cell_w - 0.012) / 2,
                y - 0.055,
                f"{proportion * 100:.1f}%",
                fontsize=12,
                fontweight="bold",
                color=text_color,
                ha="center",
                va="center",
                transform=axis.transAxes,
            )
            axis.text(
                x + (cell_w - 0.012) / 2,
                y - 0.105,
                f"{row[succ_key]}/{row[n_key]}",
                fontsize=8.7,
                color=text_color,
                ha="center",
                va="center",
                transform=axis.transAxes,
            )

    axis.text(
        0.0,
        0.01,
        "Primary endpoint tie: all three conditions reached 24/24 on binary risk disclosure. The only observed benign false alarms occurred under disclosure_full.",
        fontsize=9.2,
        color=MUTED_TEXT,
        ha="left",
        va="bottom",
        transform=axis.transAxes,
    )


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _display_condition_name(condition_id: str) -> str:
    mapping = {
        "baseline": "Baseline",
        "generic_control": "Generic control",
        "disclosure_full": "Disclosure full",
    }
    return mapping.get(condition_id, condition_id.replace("_", " "))


def _condition_color(condition_id: str) -> str:
    if condition_id == "baseline":
        return BASELINE_COLOR
    if condition_id == "generic_control":
        return GENERIC_COLOR
    if condition_id == "disclosure_full":
        return DISCLOSURE_COLOR
    return TEXT_COLOR


def _interpolate_color(low_hex: str, high_hex: str, fraction: float) -> str:
    low = _hex_to_rgb(low_hex)
    high = _hex_to_rgb(high_hex)
    clipped = max(0.0, min(1.0, fraction))
    channels = [
        round(low_channel + (high_channel - low_channel) * clipped)
        for low_channel, high_channel in zip(low, high, strict=True)
    ]
    return "#{:02x}{:02x}{:02x}".format(*channels)


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    stripped = value.lstrip("#")
    return tuple(int(stripped[index : index + 2], 16) for index in (0, 2, 4))
