"""
MME distribution figures.

Two complementary views:

  * make_mme_distribution_figure(...) — classic XY scatter. A continuous
    predictor on the X-axis (default: duration of surgery), an MME
    variable on the Y-axis, points coloured by exposure group, with a
    least-squares regression line fitted per group. Useful for "does the
    relationship between surgery complexity and MME shift between groups?"

  * make_mme_strip_plot(...) — categorical-X strip plot. One column per
    exposure group, each patient is a single dot at their MME value, with
    horizontal jitter for visibility and a short bar at the group median.
    Useful for "how spread out is MME within each group?"

Both share colour palette, p-value formatting, and small-N safety. Designed
for clinical residents — publication-friendly defaults, configurable
variable selection in the app.
"""

from __future__ import annotations

from io import BytesIO

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats


_COLOR_GROUP0 = "#2c5d8a"   # deeper blue for the unexposed group
_COLOR_GROUP1 = "#d97a2a"   # warm orange for the exposed group


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


def _fit_line(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray, float] | None:
    """Fit y = m·x + b by least squares. Returns (x_line, y_line, r²) or None."""
    if len(x) < 2:
        return None
    # Guard against zero-variance X (all same value) which crashes linregress
    if np.allclose(x, x[0]):
        return None
    res = stats.linregress(x, y)
    x_line = np.array([x.min(), x.max()])
    y_line = res.intercept + res.slope * x_line
    return x_line, y_line, res.rvalue ** 2


def _fit_line_with_band(
    x: np.ndarray, y: np.ndarray, alpha: float = 0.05, n_grid: int = 80
):
    """Fit y = m·x + b and compute a 95% CI band for the mean prediction.

    Returns (x_grid, y_fit, y_lo, y_hi, r²) or None if too few points.
    """
    n = len(x)
    if n < 3:  # need at least 3 points for a meaningful CI
        return None
    if np.allclose(x, x[0]):
        return None
    res = stats.linregress(x, y)
    x_grid = np.linspace(x.min(), x.max(), n_grid)
    y_fit = res.intercept + res.slope * x_grid

    # Standard error of the mean prediction at each x:
    #   SE = s · sqrt( 1/n + (x - x̄)² / Σ(xᵢ - x̄)² )
    x_mean = x.mean()
    s_xx = np.sum((x - x_mean) ** 2)
    y_pred = res.intercept + res.slope * x
    residuals = y - y_pred
    df = n - 2
    s = np.sqrt(np.sum(residuals ** 2) / df) if df > 0 else 0.0
    se = s * np.sqrt(1.0 / n + (x_grid - x_mean) ** 2 / s_xx)
    t_crit = stats.t.ppf(1.0 - alpha / 2.0, df) if df > 0 else 0.0
    y_lo = y_fit - t_crit * se
    y_hi = y_fit + t_crit * se
    return x_grid, y_fit, y_lo, y_hi, res.rvalue ** 2


def make_mme_distribution_figure(
    df: pd.DataFrame,
    x_var: str,
    y_vars: list[str],
    group_var: str = "Exposure",
    group0_label: str = "Unexposed",
    group1_label: str = "Exposed",
    pretty_labels: dict | None = None,
    show_regression: bool = True,
):
    """Build a grid of scatter plots (y_vars vs x_var, colored by group_var).

    One subplot per Y variable. Returns a matplotlib Figure.
    The grid auto-sizes (max 2 columns so each plot stays readable).
    """
    if not y_vars:
        fig, ax = plt.subplots(figsize=(6, 3))
        ax.text(0.5, 0.5, "Select one or more MME variables to plot",
                ha="center", va="center", transform=ax.transAxes, fontsize=12)
        ax.set_axis_off()
        return fig

    pretty_labels = pretty_labels or {}
    n = len(y_vars)
    ncols = min(2, n)
    nrows = (n + ncols - 1) // ncols
    fig, axes = plt.subplots(
        nrows, ncols, figsize=(6.0 * ncols, 4.5 * nrows), squeeze=False
    )
    axes = axes.flatten()

    x_label = pretty_labels.get(x_var, x_var)

    for i, y_var in enumerate(y_vars):
        ax = axes[i]
        # Pull x/y for each group, dropping rows missing either value
        sub = df[[x_var, y_var, group_var]].copy()
        sub[x_var] = pd.to_numeric(sub[x_var], errors="coerce")
        sub[y_var] = pd.to_numeric(sub[y_var], errors="coerce")
        sub = sub.dropna(subset=[x_var, y_var, group_var])

        x0 = sub.loc[sub[group_var] == 0, x_var].to_numpy()
        y0 = sub.loc[sub[group_var] == 0, y_var].to_numpy()
        x1 = sub.loc[sub[group_var] == 1, x_var].to_numpy()
        y1 = sub.loc[sub[group_var] == 1, y_var].to_numpy()

        # Scatter
        ax.scatter(
            x0, y0,
            color=_COLOR_GROUP0, alpha=0.75, s=42,
            edgecolors="white", linewidths=0.7,
            label=f"{group0_label} (n = {len(x0)})",
            zorder=3,
        )
        ax.scatter(
            x1, y1,
            color=_COLOR_GROUP1, alpha=0.85, s=42,
            edgecolors="white", linewidths=0.7,
            label=f"{group1_label} (n = {len(x1)})",
            zorder=3,
        )

        # Regression lines + 95% CI bands per group
        r2_parts = []
        if show_regression:
            fit0 = _fit_line_with_band(x0, y0)
            fit1 = _fit_line_with_band(x1, y1)
            if fit0 is not None:
                xg, yf, ylo, yhi, r2 = fit0
                ax.fill_between(xg, ylo, yhi, color=_COLOR_GROUP0,
                                alpha=0.15, zorder=1, linewidth=0)
                ax.plot(xg, yf, color=_COLOR_GROUP0, linewidth=2.0,
                        alpha=0.95, zorder=2)
                r2_parts.append(f"{group0_label} R² = {r2:.2f}")
            if fit1 is not None:
                xg, yf, ylo, yhi, r2 = fit1
                ax.fill_between(xg, ylo, yhi, color=_COLOR_GROUP1,
                                alpha=0.18, zorder=1, linewidth=0)
                ax.plot(xg, yf, color=_COLOR_GROUP1, linewidth=2.0,
                        alpha=0.95, zorder=2)
                r2_parts.append(f"{group1_label} R² = {r2:.2f}")

        # Mann-Whitney U on the Y variable (still useful as overall group comparison)
        try:
            _, p = stats.mannwhitneyu(y0, y1, alternative="two-sided")
        except Exception:
            p = float("nan")

        y_title = pretty_labels.get(y_var, y_var)
        ax.set_title(f"{y_title}    {_fmt_p(p)}", fontsize=11)
        ax.set_xlabel(x_label)
        ax.set_ylabel(y_title)
        ax.grid(True, linestyle="--", alpha=0.4)
        ax.set_axisbelow(True)
        ax.legend(loc="best", fontsize=9, framealpha=0.85)

        if r2_parts:
            # R² annotation below the title
            ax.text(
                0.02, 0.98, "   ".join(r2_parts),
                transform=ax.transAxes,
                fontsize=8, va="top", ha="left",
                color="#444444",
                bbox=dict(facecolor="white", edgecolor="none", alpha=0.7),
            )

    # Hide unused subplots
    for j in range(n, len(axes)):
        axes[j].set_visible(False)

    fig.suptitle(
        f"MME vs {x_label} — by exposure group",
        fontsize=14, y=1.00,
    )
    fig.tight_layout()
    return fig


def make_mme_strip_plot(
    df: pd.DataFrame,
    variables: list[str],
    group_var: str = "Exposure",
    group0_label: str = "Unexposed",
    group1_label: str = "Exposed",
    pretty_labels: dict | None = None,
    unit: str = "MME",
    show_error_bars: bool = True,
):
    """Categorical-X strip plot: one column per exposure group, each patient
    a single dot at their MME value. Overlapping patients stack visibly via
    layered transparency. Optionally an I-beam (median + IQR) sits to the
    left of each column.

    Returns a matplotlib Figure. The grid auto-sizes (max 3 columns).
    Mann-Whitney U p-value annotated in each subplot title.
    """
    if not variables:
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

    for i, var in enumerate(variables):
        ax = axes[i]
        x0 = pd.to_numeric(
            df.loc[df[group_var] == 0, var], errors="coerce"
        ).dropna().to_numpy()
        x1 = pd.to_numeric(
            df.loc[df[group_var] == 1, var], errors="coerce"
        ).dropna().to_numpy()

        # X positions of the two "columns" — dots and their I-beams share
        # the same X so the error-bar sits centered on the dot column.
        x_dot_0 = x_bar_0 = 1.10
        x_dot_1 = x_bar_1 = 2.10

        # Dots stack vertically at a single X per group. Overlapping patients
        # at the same Y compound via alpha layering, producing a darker spot
        # — that's the visual cue for "more patients here".
        ax.scatter(
            np.full(len(x0), x_dot_0), x0,
            color=_COLOR_GROUP0, alpha=0.55, s=42,
            edgecolors="white", linewidths=0.6, zorder=3,
        )
        ax.scatter(
            np.full(len(x1), x_dot_1), x1,
            color=_COLOR_GROUP1, alpha=0.65, s=42,
            edgecolors="white", linewidths=0.6, zorder=3,
        )

        # Optional median + IQR I-beam centered on each dot column.
        # Drawn with high zorder so the median bar and caps remain visible
        # on top of the dot cluster.
        if show_error_bars:
            def _draw_errorbar(values, x_center, line_color,
                               cap_half_width=0.13, median_half_width=0.18):
                if len(values) == 0:
                    return
                q1, med, q3 = np.percentile(values, [25, 50, 75])
                # Vertical IQR line (sits behind dots, partially hidden by
                # the densest part — caps + median bar carry the message).
                ax.vlines(x_center, q1, q3, color=line_color,
                          linewidth=2.0, zorder=6)
                # Q1 and Q3 caps — extend past dot column so they stand out
                ax.hlines([q1, q3],
                          xmin=x_center - cap_half_width,
                          xmax=x_center + cap_half_width,
                          color=line_color, linewidth=2.0, zorder=6)
                # Median bar — widest, drawn last on top of everything
                ax.hlines(med,
                          xmin=x_center - median_half_width,
                          xmax=x_center + median_half_width,
                          color=line_color, linewidth=3.0, zorder=7)

            _draw_errorbar(x0, x_bar_0, "black")
            _draw_errorbar(x1, x_bar_1, "black")

        # Mann-Whitney U
        try:
            _, p = stats.mannwhitneyu(x0, x1, alternative="two-sided")
        except Exception:
            p = float("nan")

        ax.set_xticks([x_dot_0, x_dot_1])
        ax.set_xticklabels([
            f"{group0_label}\n(n = {len(x0)})",
            f"{group1_label}\n(n = {len(x1)})",
        ])
        title = pretty_labels.get(var, var)
        ax.set_title(f"{title}\n{_fmt_p(p)}", fontsize=11)
        ax.set_ylabel(unit)
        ax.grid(True, axis="y", linestyle="--", alpha=0.4)
        ax.set_axisbelow(True)
        ax.set_xlim(0.7, 2.5)

    for j in range(n, len(axes)):
        axes[j].set_visible(False)

    fig.suptitle(
        f"MME by exposure group — {group1_label} vs {group0_label}",
        fontsize=14, y=1.00,
    )
    fig.tight_layout()
    return fig


def fig_to_bytes(fig, fmt: str = "png", dpi: int = 300) -> bytes:
    """Render a matplotlib Figure to bytes (PNG @300dpi or PDF)."""
    buf = BytesIO()
    fig.savefig(buf, format=fmt, dpi=dpi, bbox_inches="tight")
    return buf.getvalue()
