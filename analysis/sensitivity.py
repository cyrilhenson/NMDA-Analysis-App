"""
Per-protocol / sensitivity analysis.

Runs the same multivariate model on a second (sensitivity) dataset and
produces a side-by-side comparison plus a beta-coefficient stability check.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .multivariate import run_multivariate


def run_sensitivity_comparison(
    df_primary: pd.DataFrame,
    df_sensitivity: pd.DataFrame,
    outcomes: list[str],
    group_var: str = "D-NMDA",
    covariates_continuous: list[str] | None = None,
    covariates_categorical: list[str] | None = None,
    primary_label: str | None = None,
    sensitivity_label: str | None = None,
) -> dict:
    """Run the same multivariate model on both datasets and compare.

    Returns a dict with three DataFrames:
      - 'comparison': long-format combined results
      - 'side_by_side': wide table (Outcome | β primary | p primary | β sens | p sens)
      - 'stability': β stability check (% change between primary and sensitivity)
    """
    n0_p = int((df_primary[group_var] == 0).sum())
    n1_p = int((df_primary[group_var] == 1).sum())
    n0_s = int((df_sensitivity[group_var] == 0).sum())
    n1_s = int((df_sensitivity[group_var] == 1).sum())

    if primary_label is None:
        primary_label = f"Primary (n={n1_p} vs n={n0_p})"
    if sensitivity_label is None:
        sensitivity_label = f"Sensitivity (n={n1_s} vs n={n0_s})"

    primary = run_multivariate(df_primary, outcomes, group_var,
                               covariates_continuous, covariates_categorical)
    primary["Model"] = primary_label

    sens = run_multivariate(df_sensitivity, outcomes, group_var,
                            covariates_continuous, covariates_categorical)
    sens["Model"] = sensitivity_label

    comparison = (
        pd.concat([primary, sens], ignore_index=True)
        .sort_values(["Outcome", "Model"])
        .reset_index(drop=True)
    )

    # Wide side-by-side
    side_by_side = pd.DataFrame({"Outcome": outcomes})
    p_lookup = {r["Outcome"]: r for _, r in primary.iterrows()}
    s_lookup = {r["Outcome"]: r for _, r in sens.iterrows()}
    side_by_side[f"{primary_label}: β (95% CI)"] = [
        p_lookup[o]["Estimate (95% CI)"] for o in outcomes
    ]
    side_by_side[f"{primary_label}: p-value"] = [
        p_lookup[o]["p-value"] for o in outcomes
    ]
    side_by_side[f"{sensitivity_label}: β (95% CI)"] = [
        s_lookup[o]["Estimate (95% CI)"] for o in outcomes
    ]
    side_by_side[f"{sensitivity_label}: p-value"] = [
        s_lookup[o]["p-value"] for o in outcomes
    ]

    # Stability table
    stability_rows = []
    for o in outcomes:
        b_p = p_lookup[o]["beta"]
        b_s = s_lookup[o]["beta"]
        if b_p is None or np.isnan(b_p) or b_p == 0:
            pct = np.nan
            stable = "—"
        else:
            pct = abs((b_s - b_p) / b_p) * 100
            stable = "Yes" if pct <= 20 else "No"
        stability_rows.append({
            "Outcome": o,
            "β primary": round(b_p, 3) if b_p is not None and not np.isnan(b_p) else "",
            "β sensitivity": round(b_s, 3) if b_s is not None and not np.isnan(b_s) else "",
            "% change": round(pct, 1) if not np.isnan(pct) else "",
            "Stable (≤20% change)": stable,
        })
    stability = pd.DataFrame(stability_rows)

    return {
        "comparison": comparison,
        "side_by_side": side_by_side,
        "stability": stability,
        "primary_label": primary_label,
        "sensitivity_label": sensitivity_label,
    }
