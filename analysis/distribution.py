"""
MME distribution figures.

Side-by-side scatter / strip plots comparing the unexposed and exposed
groups for each selected MME variable. Each dot is one patient; horizontal
jitter is purely cosmetic so overlapping values are visible. A short
horizontal line marks the group median.

Designed for clinical residents — small-N safe (individual points stay
visible), publication-friendly layout, matches the colour palette of the
rest of the app.
"""

from __future__ import annotations

from io import BytesIO

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats


# Colour palette aligned with the app theme
_COLOR_GROUP0 = "#4a8fc2"   # blue-ish, used for the unexposed group
_COLOR_GROUP1 = "#e89a4a"   # warm orange for the exposed group


def detect_mme_variables(df: pd.DataFrame) -> list[str]:
    """Return all numeric columns whose name contains 'MME'."""
    return [
        c for c in df.columns
        if "MME" in c.upper() and pd.api.types.is_numeric_dtype(df[c])
    ]


def _fmt_p(p: float) -> str:
    if np.isnan(p):
        return "p = N/A"
    if p < 0.001:
        return "p < 0.001"
    return f"p = {p:.3f}"


def make_mme_distribution_figure(
    df: pd.DataFrame,
    variables: list[str],
    group_var: str = "Exposure",
    group0_label: str = "Unexposed",
    group1_label: str = "Exposed",
    pretty_labels: dict | None = None,
    unit: str = "MME",
):
    """Build a grid of box + strip plots for the given MME variables.

    Returns a matplotlib Figure. The grid auto-sizes (3 columns max).
    Each subplot shows:
      - Box plot (median, IQR, whiskers) for each group
      - Jittered individual data points
      - n per group on the x-axis labels
      - Mann-Whitney U p-value in the subplot title
    """
    if not variables:
        # Empty placeholder figure
        fig, ax = plt.subplots(figsize=(6, 3))
        ax.text(0.5, 0.5, "Select one or more MME variables to plot",
                ha="center", va="center", transform=ax.transAxes, fontsize=12)
        ax.set_axis_off()
        return fig

    pretty_labels = pretty_labels or {}
    n = len(variables)
    ncols = min(3, n)
    nrows = (n + ncols - 1) // ncols
    fig, axes = plt.subplots(
        nrows, ncols, figsize=(4.5 * ncols, 4.2 * nrows), squeeze=False
    )
    axes = axes.flatten()

    rng = np.random.RandomState(42)  # reproducible jitter

    for i, var in enumerate(variables):
        ax = axes[i]
        x0 = pd.to_numeric(
            df.loc[df[group_var] == 0, var], errors="coerce"
        ).dropna().to_numpy()
        x1 = pd.to_numeric(
            df.loc[df[group_var] == 1, var], errors="coerce"
        ).dropna().to_numpy()

        # Scatter: one dot per patient, horizontal jitter for visibility
        ax.scatter(
            1 + rng.uniform(-0.18, 0.18, len(x0)), x0,
            color=_COLOR_GROUP0, alpha=0.75, s=36, zorder=3,
            edgecolors="white", linewidths=0.7,
        )
        ax.scatter(
            2 + rng.uniform(-0.18, 0.18, len(x1)), x1,
            color=_COLOR_GROUP1, alpha=0.75, s=36, zorder=3,
            edgecolors="white", linewidths=0.7,
        )

        # Short horizontal line at each group's median
        if len(x0):
            ax.hlines(
                np.median(x0), xmin=0.70, xmax=1.30,
                color="#1f3d54", linewidth=2.0, zorder=4,
            )
        if len(x1):
            ax.hlines(
                np.median(x1), xmin=1.70, xmax=2.30,
                color="#8a4d0f", linewidth=2.0, zorder=4,
            )

        # Mann-Whitney U (robust to non-normal MME data)
        try:
            _, p = stats.mannwhitneyu(x0, x1, alternative="two-sided")
        except Exception:
            p = float("nan")

        # Axis cosmetics
        ax.set_xticks([1, 2])
        ax.set_xticklabels([
            f"{group0_label}\n(n = {len(x0)})",
            f"{group1_label}\n(n = {len(x1)})",
        ])
        title = pretty_labels.get(var, var)
        ax.set_title(f"{title}\n{_fmt_p(p)}", fontsize=11)
        ax.set_ylabel(unit)
        ax.grid(True, axis="y", linestyle="--", alpha=0.4)
        ax.set_axisbelow(True)
        ax.set_xlim(0.4, 2.6)

    # Hide any unused subplots in the grid
    for j in range(n, len(axes)):
        axes[j].set_visible(False)

    fig.suptitle(
        f"MME distribution — {group1_label} vs {group0_label}",
        fontsize=14, y=1.00,
    )
    fig.tight_layout()
    return fig


def fig_to_bytes(fig, fmt: str = "png", dpi: int = 300) -> bytes:
    """Render a matplotlib Figure to bytes (PNG @300dpi or PDF)."""
    buf = BytesIO()
    fig.savefig(buf, format=fmt, dpi=dpi, bbox_inches="tight")
    return buf.getvalue()
