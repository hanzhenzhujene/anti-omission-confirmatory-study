from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Any

import matplotlib

matplotlib.use("Agg")

from matplotlib import pyplot as plt
from matplotlib.patches import Patch, Rectangle
from matplotlib.ticker import PercentFormatter
from matplotlib.transforms import blended_transform_factory

from anti_omission.analysis import wilson_interval

if TYPE_CHECKING:
    from anti_omission.reporting import ReportContext


BASELINE_COLOR = "#475569"
GENERIC_COLOR = "#2563EB"
DISCLOSURE_COLOR = "#C2410C"

GRID_COLOR = "#CBD5E1"
TEXT_COLOR = "#0F172A"
MUTED_TEXT = "#475569"
GUARDRAIL_COLOR = "#DC2626"
GUARDRAIL_FILL = "#FEE2E2"

STATE_COLORS = {
    "risk_full_early": "#0F766E",
    "risk_full_late": "#D97706",
    "risk_partial_early": "#2DD4BF",
    "risk_partial_late": "#F59E0B",
    "risk_none": "#E5E7EB",
    "benign_clean": "#E5E7EB",
    "benign_mild": "#FDE68A",
    "benign_strong": "#F97316",
}

STATE_LABELS = {
    "risk_full_early": "FE",
    "risk_full_late": "FL",
    "risk_partial_early": "PE",
    "risk_partial_late": "PL",
    "risk_none": "N",
    "benign_clean": "C",
    "benign_mild": "M",
    "benign_strong": "F",
}

STATE_LEGEND_LABELS = {
    "risk_full_early": "Full + early",
    "risk_full_late": "Full + late",
    "risk_partial_early": "Partial + early",
    "risk_partial_late": "Partial + late",
    "risk_none": "No disclosure",
    "benign_clean": "Clean",
    "benign_mild": "Mild false alarm",
    "benign_strong": "Stronger false alarm",
}


plt.rcParams.update(
    {
        "axes.edgecolor": GRID_COLOR,
        "axes.labelcolor": TEXT_COLOR,
        "axes.spines.right": False,
        "axes.spines.top": False,
        "axes.titleweight": "bold",
        "axes.titlesize": 9,
        "axes.labelsize": 9,
        "font.family": "serif",
        "font.serif": ["Times New Roman", "Times", "Nimbus Roman", "DejaVu Serif"],
        "font.size": 9,
        "legend.frameon": False,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "savefig.facecolor": "white",
        "savefig.transparent": False,
        "xtick.color": MUTED_TEXT,
        "ytick.color": TEXT_COLOR,
    }
)


def write_publication_figures(context: "ReportContext") -> None:
    _plot_primary_tradeoff(context, context.analysis_dir / "paper_figure_1_primary_tradeoff")
    _plot_paired_scenario_matrix(context, context.analysis_dir / "paper_figure_2_paired_scenario_matrix")
    _plot_timeliness(context, context.analysis_dir / "paper_figure_s1_timeliness")


def _plot_primary_tradeoff(context: "ReportContext", output_base: Path) -> None:
    figure, axes = plt.subplots(2, 2, figsize=(7.3, 4.4), sharey=True, constrained_layout=True)
    axes_flat = list(axes.flat)
    y_positions = list(range(len(context.condition_order)))
    labels = [_display_condition_name_plot(condition_id) for condition_id in context.condition_order]
    rows_by_condition = {row["condition_id"]: row for row in context.table2_rows}
    specs = [
        {
            "title": "Disc>=2 on risk",
            "success_key": "risk_disclosure_successes",
            "n_key": "risk_disclosure_n",
            "proportion_key": "risk_disclosure_proportion",
            "ci_low_key": "risk_disclosure_ci_low",
            "ci_high_key": "risk_disclosure_ci_high",
            "guardrail": False,
        },
        {
            "title": "Score3 on risk",
            "success_key": "score3_successes",
            "n_key": "score3_n",
            "proportion_key": "score3_proportion",
            "ci_low_key": "score3_ci_low",
            "ci_high_key": "score3_ci_high",
            "guardrail": False,
        },
        {
            "title": "Late risk rows",
            "success_key": "late_successes",
            "n_key": "late_n",
            "proportion_key": "late_proportion",
            "ci_low_key": "late_ci_low",
            "ci_high_key": "late_ci_high",
            "guardrail": False,
        },
        {
            "title": "Benign false alarm",
            "success_key": "benign_false_alarm_successes",
            "n_key": "benign_false_alarm_n",
            "proportion_key": "benign_false_alarm_proportion",
            "ci_low_key": "benign_false_alarm_ci_low",
            "ci_high_key": "benign_false_alarm_ci_high",
            "guardrail": True,
        },
    ]

    for axis, spec in zip(axes_flat, specs, strict=True):
        if spec["guardrail"]:
            axis.axvspan(0.10, 1.0, color=GUARDRAIL_FILL, alpha=0.7, zorder=0)
            axis.axvline(0.10, color=GUARDRAIL_COLOR, linestyle="--", linewidth=1.2, zorder=1)
            axis.text(
                0.102,
                1.02,
                "10% guardrail",
                color=GUARDRAIL_COLOR,
                fontsize=8,
                ha="left",
                va="bottom",
                transform=axis.get_xaxis_transform(),
            )

        for y_position, condition_id in zip(y_positions, context.condition_order, strict=True):
            row = rows_by_condition[condition_id]
            proportion = row[spec["proportion_key"]]
            ci_low = row[spec["ci_low_key"]]
            ci_high = row[spec["ci_high_key"]]
            color = _condition_color(condition_id)
            xerr = [
                [max(proportion - ci_low, 0.0)],
                [max(ci_high - proportion, 0.0)],
            ]
            axis.errorbar(
                proportion,
                y_position,
                xerr=xerr,
                fmt="o",
                color=color,
                ecolor=color,
                elinewidth=2.0,
                capsize=3,
                markersize=5.5,
                zorder=3,
            )
            axis.text(
                _annotation_x(proportion, side="auto"),
                y_position,
                f"{row[spec['success_key']]}/{row[spec['n_key']]}",
                color=color,
                fontsize=7.5,
                ha=_annotation_ha(proportion, side="auto"),
                va="center",
            )

        axis.set_title(spec["title"], loc="left")
        axis.set_xlim(0.0, 1.0)
        axis.set_xticks([0.0, 0.25, 0.5, 0.75, 1.0])
        axis.xaxis.set_major_formatter(PercentFormatter(1.0, decimals=0))
        axis.grid(axis="x", color=GRID_COLOR, linewidth=0.8, alpha=0.9)
        axis.set_axisbelow(True)
        axis.spines["left"].set_color(GRID_COLOR)
        axis.spines["bottom"].set_color(GRID_COLOR)
        axis.tick_params(axis="y", length=0)

    axes[0, 0].set_yticks(y_positions, labels=labels)
    axes[1, 0].set_yticks(y_positions, labels=labels)
    axes[0, 1].tick_params(axis="y", labelleft=False)
    axes[1, 1].tick_params(axis="y", labelleft=False)
    axes[0, 0].invert_yaxis()
    _save_figure(figure, output_base)


def _plot_paired_scenario_matrix(context: "ReportContext", output_base: Path) -> None:
    grouped = _paired_rows_by_materiality(context)
    risk_rows = _discordant_rows(grouped["risk"], context.condition_order)
    benign_rows = _discordant_rows(grouped["benign"], context.condition_order)
    figure_height = max(4.6, 2.4 + 0.34 * (len(risk_rows) + len(benign_rows)))
    figure, axes = plt.subplots(2, 1, figsize=(6.7, figure_height), sharex=True, constrained_layout=False)
    materials = [
        ("risk", "Discordant risk scenarios", risk_rows),
        ("benign", "Discordant benign scenarios", benign_rows),
    ]

    present_states = {
        _cell_state(materiality, row["values"][condition_id])
        for materiality, _title, rows in materials
        for row in rows
        for condition_id in context.condition_order
    }

    for axis, (materiality, title, rows) in zip(axes, materials, strict=True):
        axis.set_title(title, loc="left")
        if not rows:
            axis.text(
                0.5,
                0.5,
                "No discordant rows in this slice",
                ha="center",
                va="center",
                fontsize=9,
                color=MUTED_TEXT,
                transform=axis.transAxes,
            )
            axis.set_axis_off()
            continue

        for y_position, row in enumerate(rows):
            for x_position, condition_id in enumerate(context.condition_order):
                cell = row["values"][condition_id]
                state = _cell_state(materiality, cell)
                axis.add_patch(
                    Rectangle(
                        (x_position - 0.5, y_position - 0.5),
                        1.0,
                        1.0,
                        facecolor=STATE_COLORS[state],
                        edgecolor="white",
                        linewidth=1.2,
                    )
                )
                axis.text(
                    x_position,
                    y_position,
                    STATE_LABELS[state],
                    ha="center",
                    va="center",
                    fontsize=7.0,
                    color=_state_text_color(state),
                )

        axis.set_xlim(-0.5, len(context.condition_order) - 0.5)
        axis.set_ylim(-0.5, len(rows) - 0.5)
        axis.set_yticks(range(len(rows)), labels=[row["scenario_label"] for row in rows])
        axis.set_xticks(
            range(len(context.condition_order)),
            labels=[_display_condition_name_plot(condition_id) for condition_id in context.condition_order],
        )
        axis.tick_params(axis="x", top=True, bottom=False, labeltop=True, labelbottom=False, rotation=0)
        axis.tick_params(axis="y", length=0)
        axis.invert_yaxis()
        axis.set_xticks([index - 0.5 for index in range(1, len(context.condition_order))], minor=True)
        axis.set_yticks([index - 0.5 for index in range(1, len(rows))], minor=True)
        axis.grid(which="minor", color="white", linewidth=1.2)
        axis.set_axisbelow(False)
        for spine in axis.spines.values():
            spine.set_color(GRID_COLOR)

        family_blocks = _family_blocks(rows)
        transform = blended_transform_factory(axis.transAxes, axis.transData)
        for family_label, start_index, end_index in family_blocks:
            axis.hlines(
                end_index + 0.5,
                -0.5,
                len(context.condition_order) - 0.5,
                colors=GRID_COLOR,
                linewidth=1.2,
            )
            midpoint = (start_index + end_index) / 2
            axis.text(
                -0.30,
                midpoint,
                family_label,
                transform=transform,
                ha="right",
                va="center",
                fontsize=7.4,
                color=MUTED_TEXT,
            )

    legend_order = [
        "risk_full_early",
        "risk_full_late",
        "risk_partial_early",
        "risk_partial_late",
        "benign_clean",
        "benign_mild",
        "benign_strong",
    ]
    handles = [
        Patch(facecolor=STATE_COLORS[state], edgecolor=GRID_COLOR, label=STATE_LEGEND_LABELS[state])
        for state in legend_order
        if state in present_states
    ]
    if handles:
        figure.legend(
            handles=handles,
            loc="lower center",
            ncol=min(4, len(handles)),
            bbox_to_anchor=(0.5, 0.02),
            fontsize=8,
        )
    figure.subplots_adjust(left=0.25, right=0.98, top=0.97, bottom=0.11, hspace=0.18)
    _save_figure(figure, output_base)


def _plot_timeliness(context: "ReportContext", output_base: Path) -> None:
    rows = _risk_family_late_rows(context)
    families = [row["family"] for row in rows]
    family_positions = list(range(len(families)))
    offsets = {
        "baseline": -0.20,
        "generic_control": 0.0,
        "disclosure_full": 0.20,
    }
    figure, axis = plt.subplots(1, 1, figsize=(6.8, 2.9), constrained_layout=True)

    for row_index, row in enumerate(rows):
        for condition_id in context.condition_order:
            metric = row["conditions"][condition_id]
            y_position = family_positions[row_index] + offsets.get(condition_id, 0.0)
            proportion = metric["proportion"]
            xerr = [
                [max(proportion - metric["ci_low"], 0.0)],
                [max(metric["ci_high"] - proportion, 0.0)],
            ]
            color = _condition_color(condition_id)
            axis.errorbar(
                proportion,
                y_position,
                xerr=xerr,
                fmt="o",
                color=color,
                ecolor=color,
                elinewidth=2.0,
                capsize=3,
                markersize=5.0,
                zorder=3,
            )
            axis.text(
                _annotation_x(proportion, side="auto"),
                y_position,
                f"{metric['successes']}/{metric['n']}",
                color=color,
                fontsize=7.3,
                ha=_annotation_ha(proportion, side="auto"),
                va="center",
            )

    axis.set_title("Family-level late disclosure on risk rows", loc="left")
    axis.set_xlim(0.0, 1.0)
    axis.set_xticks([0.0, 0.25, 0.5, 0.75, 1.0])
    axis.xaxis.set_major_formatter(PercentFormatter(1.0, decimals=0))
    axis.grid(axis="x", color=GRID_COLOR, linewidth=0.8, alpha=0.9)
    axis.set_axisbelow(True)
    axis.set_yticks(family_positions, labels=[_display_family_name(family) for family in families])
    axis.tick_params(axis="y", length=0)
    axis.invert_yaxis()
    axis.legend(
        handles=[
            Patch(facecolor=_condition_color(condition_id), edgecolor=_condition_color(condition_id), label=_display_condition_name_plot(condition_id))
            for condition_id in context.condition_order
        ],
        loc="lower center",
        ncol=len(context.condition_order),
        bbox_to_anchor=(0.5, 1.02),
        fontsize=8,
    )
    _save_figure(figure, output_base)


def _paired_rows_by_materiality(context: "ReportContext") -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in context.paired_matrix_rows:
        materiality = row["materiality"]
        scenario_id = row["scenario_id"]
        entry = grouped[materiality].setdefault(
            scenario_id,
            {
                "scenario_label": row["scenario_label"],
                "family": row["family"],
                "materiality": row["materiality"],
                "values": {},
            },
        )
        entry["values"][row["condition_id"]] = row

    output: dict[str, list[dict[str, Any]]] = {}
    for materiality, rows in grouped.items():
        output[materiality] = sorted(
            rows.values(),
            key=lambda row: (_family_sort_key(str(row["family"])), str(row["scenario_label"])),
        )
    return output


def _discordant_rows(
    rows: list[dict[str, Any]],
    condition_order: list[str],
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for row in rows:
        states = [
            _cell_state(str(row["materiality"]), row["values"][condition_id])
            for condition_id in condition_order
        ]
        if len(set(states)) > 1:
            output.append(row)
    return output


def _cell_state(materiality: str, cell: dict[str, Any]) -> str:
    if materiality == "risk":
        ordinal = int(cell.get("ordinal_disclosure") or 0)
        if ordinal <= 0:
            return "risk_none"
        strictness = "risk_full" if ordinal >= 3 else "risk_partial"
        timing = str(cell.get("timeliness") or "none")
        if timing == "late":
            return f"{strictness}_late"
        return f"{strictness}_early"

    endpoint_value = int(cell.get("endpoint_value") or 0)
    if endpoint_value == 0:
        return "benign_clean"
    ordinal = int(cell.get("ordinal_disclosure") or 0)
    return "benign_mild" if ordinal <= 1 else "benign_strong"


def _state_text_color(state: str) -> str:
    if state in {"risk_full_early", "risk_full_late", "benign_strong"}:
        return "#FFFFFF"
    return TEXT_COLOR if state != "benign_clean" else MUTED_TEXT


def _family_blocks(rows: list[dict[str, Any]]) -> list[tuple[str, int, int]]:
    blocks: list[tuple[str, int, int]] = []
    current_family = None
    start_index = 0
    for index, row in enumerate(rows):
        family = str(row["family"])
        if current_family is None:
            current_family = family
            start_index = index
            continue
        if family != current_family:
            blocks.append((_display_family_name(current_family), start_index, index - 1))
            current_family = family
            start_index = index
    if current_family is not None:
        blocks.append((_display_family_name(current_family), start_index, len(rows) - 1))
    return blocks


def _risk_family_late_rows(context: "ReportContext") -> list[dict[str, Any]]:
    rows = [
        row
        for row in context.labels
        if row.get("analysis_bucket") == "primary"
        and row.get("analysis_status", "scored") == "scored"
        and row.get("materiality") == "risk"
    ]
    grouped: dict[str, dict[str, dict[str, float | int | None]]] = defaultdict(dict)
    for family in sorted({str(row["family"]) for row in rows}, key=_family_sort_key):
        for condition_id in context.condition_order:
            subset = [
                row
                for row in rows
                if row["family"] == family and row["condition_id"] == condition_id
            ]
            successes = sum(1 for row in subset if row.get("timeliness") == "late")
            ci_low, ci_high = wilson_interval(successes, len(subset))
            grouped[family][condition_id] = {
                "successes": successes,
                "n": len(subset),
                "proportion": successes / len(subset) if subset else 0.0,
                "ci_low": ci_low or 0.0,
                "ci_high": ci_high or 0.0,
            }
    return [
        {"family": family, "conditions": grouped[family]}
        for family in sorted(grouped, key=_family_sort_key)
    ]


def _condition_color(condition_id: str) -> str:
    mapping = {
        "baseline": BASELINE_COLOR,
        "generic_control": GENERIC_COLOR,
        "disclosure_full": DISCLOSURE_COLOR,
    }
    return mapping.get(condition_id, DISCLOSURE_COLOR)


def _display_condition_name_plot(condition_id: str) -> str:
    mapping = {
        "baseline": "Baseline",
        "generic_control": "Generic control",
        "disclosure_full": "Disclosure Full",
    }
    return mapping.get(condition_id, condition_id.replace("_", " ").title())


def _display_family_name(family: str) -> str:
    mapping = {
        "medical_biosafety": "Medical/biosafety",
        "cyber_infrastructure": "Cyber infrastructure",
        "finance_forecasting": "Finance forecasting",
        "governance_fairness": "Governance fairness",
        "benign_archive_routing": "Archive/routing",
        "benign_formatting_layout": "Formatting/layout",
        "benign_internal_implementation": "Internal implementation",
        "benign_metadata_aliasing": "Metadata aliasing",
        "benign_ownership_history": "Ownership/history",
        "benign_roster_scheduling": "Roster/scheduling",
        "compliance_fairness_governance": "Compliance/fairness/governance",
        "cybersecurity_infrastructure": "Cybersecurity/infrastructure",
        "finance_forecasting_risk": "Finance/forecasting risk",
    }
    return mapping.get(family, family.replace("_", " "))


def _family_sort_key(family: str) -> tuple[int, str]:
    preferred = [
        "medical_biosafety",
        "cyber_infrastructure",
        "finance_forecasting",
        "governance_fairness",
        "benign_archive_routing",
        "benign_formatting_layout",
        "benign_internal_implementation",
        "benign_metadata_aliasing",
        "benign_ownership_history",
        "benign_roster_scheduling",
        "cybersecurity_infrastructure",
        "finance_forecasting_risk",
        "compliance_fairness_governance",
        "benign_control",
    ]
    if family in preferred:
        return preferred.index(family), family
    return len(preferred), family


def _annotation_x(proportion: float, side: str = "auto") -> float:
    resolved_side = side
    if side == "auto":
        resolved_side = "left" if proportion >= 0.9 else "right"
    if resolved_side == "left":
        return max(proportion - 0.045, 0.02)
    return min(proportion + 0.045, 0.985)


def _annotation_ha(proportion: float, side: str = "auto") -> str:
    resolved_side = side
    if side == "auto":
        resolved_side = "left" if proportion >= 0.9 else "right"
    return "right" if resolved_side == "left" else "left"


def _save_figure(figure: plt.Figure, output_base: Path) -> None:
    output_base.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_base.with_suffix(".pdf"), bbox_inches="tight", pad_inches=0.02)
    figure.savefig(output_base.with_suffix(".svg"), bbox_inches="tight", pad_inches=0.02)
    plt.close(figure)
