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
    figure = plt.figure(figsize=(14.0, 8.2), facecolor=BACKGROUND, constrained_layout=True)
    grid = figure.add_gridspec(3, 1, height_ratios=[0.26, 0.56, 0.18])

    title_ax = figure.add_subplot(grid[0, 0])
    cards_ax = figure.add_subplot(grid[1, 0])
    footer_ax = figure.add_subplot(grid[2, 0])

    for axis in (title_ax, cards_ax, footer_ax):
        axis.set_facecolor(BACKGROUND)

    _draw_title_panel(
        title_ax,
        run_snapshot=run_snapshot,
        summary=summary,
        evidence_package=evidence_package,
        evidence_verification=evidence_verification,
    )
    _draw_condition_cards(cards_ax, table2_rows)
    _draw_footer_banner(
        footer_ax,
        run_snapshot=run_snapshot,
        summary=summary,
        evidence_verification=evidence_verification,
    )

    output_svg.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_svg, format="svg", bbox_inches="tight")
    figure.savefig(output_png, format="png", dpi=220, bbox_inches="tight")
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
        fontsize=24,
        fontweight="bold",
        color=TEXT_COLOR,
        ha="left",
        va="top",
        transform=axis.transAxes,
    )
    axis.text(
        0.0,
        0.74,
        "A locked confirmatory evaluation of whether an explicit disclosure-duty prompt changes GPT-5 Mini behavior under omission pressure.",
        fontsize=12.5,
        color=MUTED_TEXT,
        ha="left",
        va="top",
        transform=axis.transAxes,
    )

    axis.text(
        0.0,
        0.56,
        (
            f"Model: {model_id}  |  "
            f"Bank: {risk_scenarios} risk + {benign_scenarios} benign  |  "
            f"Manifest: {total_trials} trials  |  "
            f"Labels: {final_stage}  |  "
            f"Evidence: {verification_status}"
        ),
        fontsize=10.8,
        color=TEXT_COLOR,
        ha="left",
        va="center",
        transform=axis.transAxes,
    )

    axis.add_patch(
        FancyBboxPatch(
            (0.0, 0.07),
            0.985,
            0.32,
            boxstyle="round,pad=0.012,rounding_size=0.03",
            linewidth=1.0,
            edgecolor=BORDER_COLOR,
            facecolor=CARD_FILL,
            transform=axis.transAxes,
        )
    )
    axis.text(
        0.02,
        0.31,
        "Confirmatory headline",
        fontsize=11.8,
        fontweight="bold",
        color=TEXT_COLOR,
        ha="left",
        va="center",
        transform=axis.transAxes,
    )
    axis.text(
        0.02,
        0.17,
        (
            "All three conditions reached 24/24 on the preregistered binary risk endpoint.\n"
            "`disclosure_full` slightly improved completeness and timeliness, but it also introduced 6/36 benign false alarms,\n"
            "so the locked run does not support a favorable tradeoff claim."
        ),
        fontsize=11.1,
        color=TEXT_COLOR,
        ha="left",
        va="center",
        transform=axis.transAxes,
    )


def _draw_condition_cards(axis, table2_rows: list[dict[str, str]]) -> None:
    axis.axis("off")
    axis.text(
        0.0,
        1.02,
        "What is being compared",
        fontsize=15,
        fontweight="bold",
        color=TEXT_COLOR,
        ha="left",
        va="bottom",
        transform=axis.transAxes,
    )
    axis.text(
        0.0,
        0.97,
        "Each card shows one locked condition, its role in the study, and its key confirmatory outcomes.",
        fontsize=10.5,
        color=MUTED_TEXT,
        ha="left",
        va="bottom",
        transform=axis.transAxes,
    )

    card_count = max(len(table2_rows), 1)
    card_gap = 0.04
    total_width = 0.96
    card_width = (total_width - card_gap * (card_count - 1)) / card_count
    start_x = (1.0 - (card_width * card_count + card_gap * (card_count - 1))) / 2
    card_x_positions = [start_x + index * (card_width + card_gap) for index in range(card_count)]
    card_height = 0.84
    metric_specs = [
        ("Risk disclosure", "risk_disclosure_proportion", "risk_disclosure_successes", "risk_disclosure_n", True),
        ("Full disclosure", "score3_proportion", "score3_successes", "score3_n", True),
        ("Late risk", "late_proportion", "late_successes", "late_n", False),
        (
            "Benign false alarm",
            "benign_false_alarm_proportion",
            "benign_false_alarm_successes",
            "benign_false_alarm_n",
            False,
        ),
    ]
    metric_gap = 0.02
    metric_width = (card_width - 0.08) / 2
    metric_height = 0.16
    metric_positions = [
        (0.03, 0.40),
        (0.03 + metric_width + metric_gap, 0.40),
        (0.03, 0.20),
        (0.03 + metric_width + metric_gap, 0.20),
    ]

    for row, card_x in zip(table2_rows, card_x_positions, strict=True):
        condition_id = row["condition_id"]
        edge_color = _condition_color(condition_id)
        axis.add_patch(
            FancyBboxPatch(
                (card_x, 0.08),
                card_width,
                card_height,
                boxstyle="round,pad=0.012,rounding_size=0.03",
                linewidth=2.0 if condition_id == "disclosure_full" else 1.4,
                edgecolor=edge_color,
                facecolor=_condition_fill(condition_id),
                transform=axis.transAxes,
            )
        )
        badge_width = 0.16 if condition_id != "disclosure_full" else 0.22
        axis.add_patch(
            FancyBboxPatch(
                (card_x + 0.03, 0.84),
                badge_width,
                0.06,
                boxstyle="round,pad=0.01,rounding_size=0.02",
                linewidth=0.0,
                facecolor=edge_color,
                transform=axis.transAxes,
            )
        )
        axis.text(
            card_x + 0.04,
            0.87,
            _condition_badge(condition_id),
            fontsize=8.9,
            fontweight="bold",
            color="white",
            ha="left",
            va="center",
            transform=axis.transAxes,
        )
        axis.text(
            card_x + 0.03,
            0.77,
            _display_condition_name(condition_id),
            fontsize=16,
            fontweight="bold",
            color=TEXT_COLOR,
            ha="left",
            va="center",
            transform=axis.transAxes,
        )
        axis.text(
            card_x + 0.03,
            0.71,
            _condition_role(condition_id),
            fontsize=10.7,
            color=MUTED_TEXT,
            ha="left",
            va="center",
            transform=axis.transAxes,
        )
        axis.text(
            card_x + 0.03,
            0.65,
            _condition_description(condition_id),
            fontsize=10.0,
            color=MUTED_TEXT,
            ha="left",
            va="center",
            transform=axis.transAxes,
        )

        for (metric_x, metric_y), (
            metric_title,
            proportion_key,
            success_key,
            n_key,
            good_high,
        ) in zip(metric_positions, metric_specs, strict=True):
            proportion = float(row[proportion_key])
            fill_color = _interpolate_color(
                GOOD_LOW if good_high else BAD_LOW,
                GOOD_HIGH if good_high else BAD_HIGH,
                proportion,
            )
            box_left = card_x + metric_x
            box_bottom = metric_y
            axis.add_patch(
                Rectangle(
                    (box_left, box_bottom),
                    metric_width,
                    metric_height,
                    linewidth=1.0,
                    edgecolor=BORDER_COLOR,
                    facecolor=fill_color,
                    transform=axis.transAxes,
                )
            )
            text_color = "white" if proportion > 0.65 else TEXT_COLOR
            axis.text(
                box_left + 0.012,
                box_bottom + 0.126,
                metric_title,
                fontsize=8.7,
                fontweight="bold",
                color=text_color,
                ha="left",
                va="center",
                transform=axis.transAxes,
            )
            axis.text(
                box_left + metric_width / 2,
                box_bottom + 0.073,
                f"{proportion * 100:.1f}%",
                fontsize=15.8,
                fontweight="bold",
                color=text_color,
                ha="center",
                va="center",
                transform=axis.transAxes,
            )
            axis.text(
                box_left + metric_width / 2,
                box_bottom + 0.026,
                f"{row[success_key]}/{row[n_key]}",
                fontsize=9.1,
                color=text_color,
                ha="center",
                va="center",
                transform=axis.transAxes,
            )

        axis.add_patch(
            FancyBboxPatch(
                (card_x + 0.03, 0.10),
                card_width - 0.06,
                0.07,
                boxstyle="round,pad=0.01,rounding_size=0.02",
                linewidth=0.9,
                edgecolor=BORDER_COLOR,
                facecolor=BACKGROUND,
                transform=axis.transAxes,
            )
        )
        axis.text(
            card_x + 0.04,
            0.135,
            _condition_reading(condition_id),
            fontsize=9.4,
            color=TEXT_COLOR,
            ha="left",
            va="center",
            transform=axis.transAxes,
        )


def _draw_footer_banner(
    axis,
    *,
    run_snapshot: dict,
    summary: dict,
    evidence_verification: dict | None,
) -> None:
    axis.axis("off")
    panels = [
        (
            "Design",
            [
                f"{summary['primary_risk_trials'] // len(run_snapshot['conditions'])} risk + "
                f"{summary['primary_benign_trials'] // len(run_snapshot['conditions'])} benign scenarios",
                "single locked run across three conditions",
            ],
        ),
        (
            "Labeling",
            [
                "two blind primary annotators on every row",
                "adjudicated consensus finalization",
            ],
        ),
        (
            "Reading",
            [
                "primary endpoint tied at 24/24 across conditions",
                f"evidence verification: {(evidence_verification or {}).get('status', 'not packaged')}",
            ],
        ),
    ]
    panel_width = 0.31
    x_positions = [0.0, 0.345, 0.69]

    for x_position, (title, lines) in zip(x_positions, panels, strict=True):
        axis.add_patch(
            FancyBboxPatch(
                (x_position, 0.10),
                panel_width,
                0.78,
                boxstyle="round,pad=0.012,rounding_size=0.03",
                linewidth=1.0,
                edgecolor=BORDER_COLOR,
                facecolor=CARD_FILL,
                transform=axis.transAxes,
            )
        )
        axis.text(
            x_position + 0.03,
            0.73,
            title,
            fontsize=11.0,
            fontweight="bold",
            color=TEXT_COLOR,
            ha="left",
            va="center",
            transform=axis.transAxes,
        )
        for index, line in enumerate(lines):
            axis.text(
                x_position + 0.03,
                0.50 - index * 0.22,
                f"• {line}",
                fontsize=9.5,
                color=MUTED_TEXT,
                ha="left",
                va="center",
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


def _condition_fill(condition_id: str) -> str:
    if condition_id == "baseline":
        return "#F8FAFC"
    if condition_id == "generic_control":
        return "#EFF6FF"
    if condition_id == "disclosure_full":
        return "#FFF7ED"
    return CARD_FILL


def _condition_badge(condition_id: str) -> str:
    mapping = {
        "baseline": "BASELINE CONTROL",
        "generic_control": "GENERIC CONTROL",
        "disclosure_full": "INTERVENTION UNDER TEST",
    }
    return mapping.get(condition_id, condition_id.replace("_", " ").upper())


def _condition_role(condition_id: str) -> str:
    mapping = {
        "baseline": "Direct-answer control",
        "generic_control": "General-caution control",
        "disclosure_full": "Disclosure-duty prompt",
    }
    return mapping.get(condition_id, condition_id.replace("_", " "))


def _condition_description(condition_id: str) -> str:
    mapping = {
        "baseline": "Answers the task without an explicit\n duty to surface omitted risk.",
        "generic_control": "Adds generic carefulness language\n without the specific intervention.",
        "disclosure_full": "Explicitly tells the model to disclose\n material omitted risk.",
    }
    return mapping.get(condition_id, condition_id.replace("_", " "))


def _condition_reading(condition_id: str) -> str:
    mapping = {
        "baseline": "Ceilinged risk endpoint; no benign over-warning.",
        "generic_control": "Ceilinged risk endpoint; no benign over-warning.",
        "disclosure_full": "No primary gain; benign over-warning added.",
    }
    return mapping.get(condition_id, condition_id.replace("_", " "))


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
