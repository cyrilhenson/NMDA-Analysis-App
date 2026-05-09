"""
Multivariate (linear regression) analysis.

Mirrors the R code:
  outcome ~ Exposure + Levels_involved + Duration_surgery + ASA (factor)

Reports the Exposure=1 coefficient with 95% CI and p-value for each outcome.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.formula.api import ols


def _safe_name(name: str) -> str:
    """Return a Python-identifier-safe alias for a column name."""
    return "_v_" + "".join(c if c.isalnum() else "_" for c in name)


def _fit_linear(
    df: pd.DataFrame,
    outcome: str,
    group_var: str,
    covariates_continuous: list[str],
    covariates_categorical: list[str],
) -> dict:
    """Fit OLS and return tidy coefficient row for the group variable (level=1)."""
    use_cols = [outcome, group_var] + covariates_continuous + covariates_categorical
    use_cols = [c for c in use_cols if c in df.columns]
    work = df[use_cols].copy()

    # Coerce types
    work[outcome] = pd.to_numeric(work[outcome], errors="coerce")
    work[group_var] = pd.to_numeric(work[group_var], errors="coerce")
    for c in covariates_continuous:
        if c in work.columns:
            work[c] = pd.to_numeric(work[c], errors="coerce")

    # Drop missing rows (listwise like R's lm default) BEFORE astype(int)
    work = work.dropna()

    if not work.empty:
        # Now safe to convert group + categorical covariates to plain int/category
        work[group_var] = work[group_var].astype(int)
        for c in covariates_categorical:
            if c in work.columns:
                work[c] = work[c].astype("category")
    if work.empty or work[group_var].nunique() < 2:
        return {
            "Outcome": outcome,
            "Model": "Linear regression",
            "n": len(work),
            "beta": np.nan,
            "ci_low": np.nan,
            "ci_high": np.nan,
            "p_value": np.nan,
            "Estimate (95% CI)": "Insufficient data",
            "p-value": "",
        }

    # Build alias map so column names with spaces / dashes work in the formula
    alias = {c: _safe_name(c) for c in work.columns}
    work_aliased = work.rename(columns=alias)

    rhs_terms = [f"C({alias[group_var]})"]
    for c in covariates_continuous:
        if c in work.columns:
            rhs_terms.append(alias[c])
    for c in covariates_categorical:
        if c in work.columns:
            rhs_terms.append(f"C({alias[c]})")
    formula = f"{alias[outcome]} ~ " + " + ".join(rhs_terms)

    fit = ols(formula, data=work_aliased).fit()

    # Find the Exposure=1 (exposed-cohort) term
    target_prefixes = (
        f"C({alias[group_var]})[T.1]",
        f"C({alias[group_var]})[T.1.0]",
    )
    target_term = None
    for term in fit.params.index:
        if term.startswith(target_prefixes[0]) or term.startswith(target_prefixes[1]):
            target_term = term
            break
    if target_term is None:
        # try any non-Intercept term referencing the group variable
        for term in fit.params.index:
            if alias[group_var] in term and "Intercept" not in term:
                target_term = term
                break

    if target_term is None:
        return {
            "Outcome": outcome,
            "Model": "Linear regression",
            "n": int(fit.nobs),
            "beta": np.nan,
            "ci_low": np.nan,
            "ci_high": np.nan,
            "p_value": np.nan,
            "Estimate (95% CI)": "Group term not found",
            "p-value": "",
        }

    beta = float(fit.params[target_term])
    ci = fit.conf_int().loc[target_term]
    ci_low, ci_high = float(ci[0]), float(ci[1])
    p_val = float(fit.pvalues[target_term])

    p_str = "<0.001" if p_val < 0.001 else f"{p_val:.3f}"

    return {
        "Outcome": outcome,
        "Model": "Linear regression",
        "n": int(fit.nobs),
        "beta": beta,
        "ci_low": ci_low,
        "ci_high": ci_high,
        "p_value": p_val,
        "Estimate (95% CI)": f"β = {beta:.3f} (95% CI: {ci_low:.3f}, {ci_high:.3f})",
        "p-value": p_str,
    }


def run_multivariate(
    df: pd.DataFrame,
    outcomes: list[str],
    group_var: str = "Exposure",
    covariates_continuous: list[str] | None = None,
    covariates_categorical: list[str] | None = None,
) -> pd.DataFrame:
    """Run linear regression on each outcome and return a tidy DataFrame."""
    if covariates_continuous is None:
        covariates_continuous = ["Levels_involved", "Duration_surgery"]
    if covariates_categorical is None:
        covariates_categorical = ["ASA"]

    rows = [
        _fit_linear(df, o, group_var, covariates_continuous, covariates_categorical)
        for o in outcomes
    ]
    return pd.DataFrame(rows)
