"""
Univariate analysis (Tables 1 & 2).

Mirrors the R code's logic exactly:
  - Continuous: Shapiro-Wilk normality on each group; if BOTH p > 0.05,
    use Welch's t-test and report mean ± SD. Otherwise Mann-Whitney U
    and report median (IQR).
  - Categorical: Chi-square by default. If 2x2 AND any expected cell < 5,
    use Fisher's exact instead.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _fmt_p(p: float) -> str:
    if p is None or (isinstance(p, float) and np.isnan(p)):
        return ""
    if p < 0.001:
        return "<0.001"
    return f"{p:.3f}"


def _shapiro_safe(x: np.ndarray) -> float:
    """Shapiro-Wilk p-value; returns 0 (treat as non-normal) if n < 3."""
    if len(x) < 3:
        return 0.0
    try:
        return float(stats.shapiro(x).pvalue)
    except Exception:
        return 0.0


# ---------------------------------------------------------------------------
# Continuous variable summary
# ---------------------------------------------------------------------------
def cont_summary(
    data: pd.DataFrame,
    var: str,
    group: str = "Exposure",
    group0_label: str = "Unexposed",
    group1_label: str = "Exposed",
) -> dict:
    """Summarise a continuous variable by binary group."""
    x0 = pd.to_numeric(
        data.loc[data[group] == 0, var], errors="coerce"
    ).dropna().to_numpy()
    x1 = pd.to_numeric(
        data.loc[data[group] == 1, var], errors="coerce"
    ).dropna().to_numpy()

    if len(x0) == 0 or len(x1) == 0:
        return {
            "Variable": var,
            "Level": "",
            group0_label: f"n={len(x0)}",
            group1_label: f"n={len(x1)}",
            "p-value": "",
            "Statistical test": "Insufficient data",
            "_p_raw": np.nan,
            "_type": "continuous",
        }

    # Shapiro on each group
    p0 = _shapiro_safe(x0)
    p1 = _shapiro_safe(x1)
    normal = (p0 > 0.05) and (p1 > 0.05)

    if normal:
        # Welch t-test
        tt = stats.ttest_ind(x0, x1, equal_var=False)
        out0 = f"{x0.mean():.2f} ± {x0.std(ddof=1):.2f}"
        out1 = f"{x1.mean():.2f} ± {x1.std(ddof=1):.2f}"
        test = "Welch t-test"
        p = float(tt.pvalue)
    else:
        # Mann-Whitney U (Wilcoxon rank-sum)
        wt = stats.mannwhitneyu(x0, x1, alternative="two-sided", method="asymptotic")
        q0 = np.quantile(x0, [0.25, 0.50, 0.75])
        q1 = np.quantile(x1, [0.25, 0.50, 0.75])
        out0 = f"{q0[1]:.2f} (IQR {q0[0]:.2f}–{q0[2]:.2f})"
        out1 = f"{q1[1]:.2f} (IQR {q1[0]:.2f}–{q1[2]:.2f})"
        test = "Mann–Whitney U (Wilcoxon rank-sum)"
        p = float(wt.pvalue)

    return {
        "Variable": var,
        "Level": "",
        group0_label: out0,
        group1_label: out1,
        "p-value": _fmt_p(p),
        "Statistical test": test,
        "_p_raw": p,
        "_type": "continuous",
    }


# ---------------------------------------------------------------------------
# Categorical variable summary (one row per level)
# ---------------------------------------------------------------------------
def cat_summary(
    data: pd.DataFrame,
    var: str,
    group: str = "Exposure",
    group0_label: str = "Unexposed",
    group1_label: str = "Exposed",
) -> list[dict]:
    """Summarise a categorical variable by binary group. Returns one row per level."""
    sub = data[[var, group]].dropna(subset=[group])
    # Build crosstab
    tab = pd.crosstab(sub[var], sub[group])
    # Ensure both group columns are present
    for g in [0, 1]:
        if g not in tab.columns:
            tab[g] = 0
    tab = tab[[0, 1]]

    if tab.empty:
        return [{
            "Variable": var,
            "Level": "",
            group0_label: "",
            group1_label: "",
            "p-value": "",
            "Statistical test": "Insufficient data",
            "_p_raw": np.nan,
            "_type": "categorical",
        }]

    # Chi-square first to get expected counts
    try:
        chi2, p_chi, dof, expected = stats.chi2_contingency(tab.values, correction=False)
    except Exception:
        chi2, p_chi, expected = np.nan, np.nan, None

    # Fisher only when 2x2 AND any expected cell < 5
    use_fisher = (
        tab.shape == (2, 2)
        and expected is not None
        and (expected < 5).any()
    )

    if use_fisher:
        try:
            _, p = stats.fisher_exact(tab.values)
            p = float(p)
            test = "Fisher's exact"
        except Exception:
            p = float(p_chi)
            test = "Chi-square"
    else:
        p = float(p_chi)
        test = "Chi-square"

    n0 = int(tab[0].sum())
    n1 = int(tab[1].sum())

    rows: list[dict] = []
    for level in tab.index:
        c0 = int(tab.loc[level, 0])
        c1 = int(tab.loc[level, 1])
        rows.append({
            "Variable": var,
            "Level": str(level),
            group0_label: f"{c0} ({100 * c0 / n0:.1f}%)" if n0 else f"{c0} (—)",
            group1_label: f"{c1} ({100 * c1 / n1:.1f}%)" if n1 else f"{c1} (—)",
            "p-value": _fmt_p(p),
            "Statistical test": test,
            "_p_raw": p,
            "_type": "categorical",
        })
    return rows


# ---------------------------------------------------------------------------
# Public API: build a univariate table
# ---------------------------------------------------------------------------
def build_univariate_table(
    data: pd.DataFrame,
    continuous: list[str],
    categorical: list[str],
    group: str = "Exposure",
    group_labels: dict | None = None,
) -> pd.DataFrame:
    """Build a tidy univariate table for a list of continuous + categorical variables."""
    if group_labels is None:
        group_labels = {"0": "Unexposed", "1": "Exposed"}
    g0 = group_labels.get("0", "Group 0")
    g1 = group_labels.get("1", "Group 1")

    # Coerce group to integer 0/1
    df = data.copy()
    df[group] = pd.to_numeric(df[group], errors="coerce").astype("Int64")

    rows: list[dict] = []
    for v in continuous:
        if v in df.columns and v != group:
            rows.append(cont_summary(df, v, group=group,
                                     group0_label=g0, group1_label=g1))
    for v in categorical:
        if v in df.columns and v != group:
            rows.extend(cat_summary(df, v, group=group,
                                    group0_label=g0, group1_label=g1))

    cols = ["Variable", "Level", g0, g1, "p-value", "Statistical test",
            "_p_raw", "_type"]
    if not rows:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(rows)[cols]
