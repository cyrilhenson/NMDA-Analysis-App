"""
Minimum Detectable Difference (MDD) power analysis + figure.

Uses pooled SD and a two-sample two-sided t-test (matches R's pwr.t2n.test
when feasible).
"""

from __future__ import annotations

from io import BytesIO
import math

import matplotlib

matplotlib.use("Agg")  # safe for headless / Streamlit cloud
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats


def _power_two_sample(d: float, n1: int, n2: int, alpha: float = 0.05) -> float:
    """Power for a two-sample (unequal n) two-sided t-test using non-central t.

    Equivalent to R's pwr::pwr.t2n.test(n1, n2, d, sig.level)$power.
    """
    if d == 0 or n1 < 2 or n2 < 2:
        return alpha
    df = n1 + n2 - 2
    nc = d * math.sqrt(1.0 / (1.0 / n1 + 1.0 / n2))
    crit = stats.t.ppf(1 - alpha / 2, df)
    # Non-central t survival on both tails
    power = (
        1.0
        - stats.nct.cdf(crit, df, nc)
        + stats.nct.cdf(-crit, df, nc)
    )
    return float(power)


def _solve_d_for_power(target: float, n1: int, n2: int, alpha: float = 0.05) -> float:
    """Solve effect size d that yields the requested power. Bisection."""
    lo, hi = 0.0, 5.0
    for _ in range(80):
        mid = (lo + hi) / 2
        p = _power_two_sample(mid, n1, n2, alpha)
        if p < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def compute_mdd(
    df: pd.DataFrame,
    outcome: str = "Total_MME",
    group_var: str = "D-NMDA",
    alpha: float = 0.05,
) -> dict:
    """Compute pooled SD and MDD at 80% / 90% power."""
    x0 = pd.to_numeric(df.loc[df[group_var] == 0, outcome], errors="coerce").dropna()
    x1 = pd.to_numeric(df.loc[df[group_var] == 1, outcome], errors="coerce").dropna()

    n0, n1 = len(x0), len(x1)
    mean0, mean1 = float(x0.mean()), float(x1.mean())
    sd0, sd1 = float(x0.std(ddof=1)), float(x1.std(ddof=1))

    pooled_sd = math.sqrt(
        ((n0 - 1) * sd0 ** 2 + (n1 - 1) * sd1 ** 2) / (n0 + n1 - 2)
    )

    d_80 = _solve_d_for_power(0.80, n0, n1, alpha)
    d_90 = _solve_d_for_power(0.90, n0, n1, alpha)

    return {
        "outcome": outcome,
        "n0": n0, "n1": n1,
        "mean0": mean0, "mean1": mean1,
        "sd0": sd0, "sd1": sd1,
        "pooled_sd": pooled_sd,
        "mdd_80": d_80 * pooled_sd,
        "mdd_90": d_90 * pooled_sd,
        "observed_diff": abs(mean0 - mean1),
        "alpha": alpha,
    }


def make_mdd_figure(
    mdd: dict,
    unit: str = "MME",
    group0_label: str = "No D-NMDA",
    group1_label: str = "D-NMDA",
    title_outcome: str = "Total Opioid Consumption",
):
    """Build the MDD power curve figure. Returns the matplotlib Figure."""
    pooled_sd = mdd["pooled_sd"]
    n0, n1 = mdd["n0"], mdd["n1"]
    alpha = mdd["alpha"]

    upper = max(int(round(mdd["mdd_90"] * 1.3)), 100, int(round(mdd["observed_diff"] * 1.5)))
    diff_seq = np.arange(1, upper + 1, 1)
    cohens_d = diff_seq / pooled_sd
    powers = np.array([_power_two_sample(d, n0, n1, alpha) for d in cohens_d])

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(diff_seq, powers, color="#2166AC", linewidth=2.0)

    # 80 / 90 reference lines
    ax.axhline(0.80, linestyle="--", color="gray", linewidth=0.8)
    ax.axhline(0.90, linestyle=":", color="gray", linewidth=0.8)

    # MDD points
    ax.plot([mdd["mdd_80"]], [0.80], "o", color="#2166AC", markersize=8)
    ax.plot([mdd["mdd_90"]], [0.90], "o", color="#2166AC", markersize=8)

    ax.annotate(
        f"80% power\nMDD = {mdd['mdd_80']:.0f} {unit}",
        (mdd["mdd_80"], 0.80),
        xytext=(8, -22), textcoords="offset points",
        ha="left", color="gray", fontsize=9,
    )
    ax.annotate(
        f"90% power\nMDD = {mdd['mdd_90']:.0f} {unit}",
        (mdd["mdd_90"], 0.90),
        xytext=(8, -22), textcoords="offset points",
        ha="left", color="gray", fontsize=9,
    )

    # Observed diff
    ax.axvline(mdd["observed_diff"], linestyle="--", color="#D6604D", linewidth=0.9)
    ax.annotate(
        f"Observed\ndifference\n{mdd['observed_diff']:.0f} {unit}",
        (mdd["observed_diff"], 0.25),
        xytext=(6, 0), textcoords="offset points",
        ha="left", color="#D6604D", fontsize=9,
    )

    ax.set_ylim(0, 1)
    ax.set_xlim(0, upper)
    ax.set_yticks(np.arange(0, 1.01, 0.2))
    ax.set_yticklabels([f"{int(t*100)}%" for t in np.arange(0, 1.01, 0.2)])
    ax.set_xlabel(f"Minimum Detectable Difference ({unit})", fontweight="bold")
    ax.set_ylabel("Statistical Power", fontweight="bold")

    ax.set_title(
        f"Power vs. Detectable Difference — {title_outcome} ({unit})",
        fontweight="bold", fontsize=12,
    )
    fig.text(
        0.5,
        0.91,
        f"Fixed sample: {group0_label} n={n0}, {group1_label} n={n1}  |  "
        f"Pooled SD = {pooled_sd:.0f}  |  Two-sided α = {alpha:.2f}",
        ha="center", color="gray", fontsize=10,
    )
    fig.text(
        0.01, 0.01,
        f"Observed difference = {mdd['observed_diff']:.0f} {unit}  "
        f"({group0_label}: {mdd['mean0']:.0f} ± {mdd['sd0']:.0f} vs "
        f"{group1_label}: {mdd['mean1']:.0f} ± {mdd['sd1']:.0f}).",
        color="gray", fontsize=8, ha="left",
    )

    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout(rect=[0, 0.03, 1, 0.92])
    return fig


def fig_to_bytes(fig, fmt: str = "png", dpi: int = 300) -> bytes:
    buf = BytesIO()
    fig.savefig(buf, format=fmt, dpi=dpi, bbox_inches="tight")
    return buf.getvalue()
