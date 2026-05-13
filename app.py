"""
Complex Spine Surgery Cohort Analysis App
=========================================

Plug-and-play Streamlit app for residents to upload a deidentified
dataset and reproduce every table/figure from the original R analysis:

  • Table 1 — baseline characteristics
  • Table 2 — perioperative data
  • Multivariate (linear) regression
  • Per-protocol / sensitivity analysis (when a 2nd dataset is supplied)
  • MDD power figure
  • Word / CSV / PDF / PNG downloads

Run locally:   streamlit run app.py
Or one-click:  double-click run_local.bat (Windows) or run_local.command (Mac)
Or cloud:      deploy to https://streamlit.io/cloud (see README.md)
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st
import yaml

from analysis.univariate import build_univariate_table
from analysis.multivariate import run_multivariate
from analysis.sensitivity import run_sensitivity_comparison
from analysis.power import compute_mdd, make_mdd_figure, fig_to_bytes
from analysis.distribution import (
    detect_mme_variables,
    make_mme_distribution_figure,
    make_mme_strip_plot,
    fig_to_bytes as dist_fig_to_bytes,
)
from exports.word_export import build_report_docx, df_to_docx_bytes


APP_DIR = Path(__file__).parent
CONFIG_PATH = APP_DIR / "config" / "default_variables.yaml"
SAMPLE_PRIMARY = APP_DIR / "sample_data" / "Sample_Complex_Spine.xlsx"
SAMPLE_SENSITIVITY = APP_DIR / "sample_data" / "Sample_Sensitivity.xlsx"


# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Complex Spine Cohort Analysis",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _read_xlsx(file_or_bytes) -> pd.DataFrame:
    if isinstance(file_or_bytes, (bytes, bytearray)):
        return pd.read_excel(BytesIO(file_or_bytes))
    return pd.read_excel(file_or_bytes)


def auto_classify(df: pd.DataFrame, group_col: str) -> tuple[list[str], list[str]]:
    """Heuristic: numeric column with > 6 unique values is continuous,
    everything else (or numeric with ≤ 6 distinct values) is categorical."""
    continuous, categorical = [], []
    for col in df.columns:
        if col == group_col:
            continue
        s = df[col]
        if pd.api.types.is_numeric_dtype(s):
            n_unique = s.dropna().nunique()
            if n_unique > 6:
                continuous.append(col)
            else:
                categorical.append(col)
        else:
            categorical.append(col)
    return continuous, categorical


def _hide_internal(df: pd.DataFrame) -> pd.DataFrame:
    drop_cols = [c for c in df.columns if c.startswith("_")]
    return df.drop(columns=drop_cols, errors="ignore")


def _download_button(label, data, file_name, mime, key):
    st.download_button(
        label=label, data=data, file_name=file_name, mime=mime, key=key,
        use_container_width=True,
    )


# ---------------------------------------------------------------------------
# Sidebar — data input + config
# ---------------------------------------------------------------------------
st.sidebar.title("📂 Data & Configuration")

cfg = load_config(str(CONFIG_PATH))

st.sidebar.markdown("**Step 1. Upload primary dataset (.xlsx)**")
primary_file = st.sidebar.file_uploader(
    "Primary dataset",
    type=["xlsx", "xls"],
    key="primary",
    label_visibility="collapsed",
)

use_sample = st.sidebar.checkbox(
    "Use bundled sample (de-identified complex spine cohort)",
    value=primary_file is None and SAMPLE_PRIMARY.exists(),
)

st.sidebar.markdown("**Step 2. (Optional) Upload sensitivity dataset (.xlsx)**")
sensitivity_file = st.sidebar.file_uploader(
    "Sensitivity / per-protocol dataset",
    type=["xlsx", "xls"],
    key="sensitivity",
    label_visibility="collapsed",
)
use_sample_sens = st.sidebar.checkbox(
    "Use bundled sensitivity sample",
    value=sensitivity_file is None and SAMPLE_SENSITIVITY.exists(),
)

st.sidebar.markdown("---")
st.sidebar.markdown("**Step 3. Group variable & labels**")
group_var = st.sidebar.text_input(
    "Group column name",
    value=cfg.get("group_variable", "Exposure"),
    help="Column with binary 0/1 values defining the two comparison groups "
         "(1 = exposed cohort, 0 = unexposed).",
)
g_labels = cfg.get("group_labels", {"0": "Unexposed", "1": "Exposed"})
group0_label = st.sidebar.text_input("Label for group=0", value=g_labels.get("0", "Group 0"))
group1_label = st.sidebar.text_input("Label for group=1", value=g_labels.get("1", "Group 1"))


# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
df_primary = None
df_sensitivity = None

if primary_file is not None:
    df_primary = _read_xlsx(primary_file.getvalue())
elif use_sample and SAMPLE_PRIMARY.exists():
    df_primary = _read_xlsx(str(SAMPLE_PRIMARY))

if sensitivity_file is not None:
    df_sensitivity = _read_xlsx(sensitivity_file.getvalue())
elif use_sample_sens and SAMPLE_SENSITIVITY.exists():
    df_sensitivity = _read_xlsx(str(SAMPLE_SENSITIVITY))


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("💊 Complex Spine Surgery Cohort Analysis")
st.caption(
    "Compare the exposed cohort (received methadone + ketamine) with the "
    "unexposed cohort. Upload a deidentified dataset and instantly reproduce "
    "every table and figure from the original R analysis pipeline. Built for "
    "clinical residents — no statistical background required."
)

with st.expander("🔒 Privacy & HIPAA notice", expanded=False):
    st.markdown(
        """
        This app is designed for **de-identified datasets only**, conforming
        to the **HIPAA Safe Harbor** standard (45 CFR §164.514(b)).

        **Do not upload** files containing any of the 18 HIPAA identifiers,
        including patient names, dates (date of birth, admission, surgery,
        discharge), medical record numbers, addresses, phone numbers, email
        addresses, or any other directly identifying information.

        Uploaded files are processed **in memory only** for the duration of
        your session and are never written to permanent storage on the
        server. Closing the browser tab discards all uploaded data.

        The bundled sample dataset has been further generalized — surgical
        procedure descriptions are collapsed into broad categories
        (e.g. "Posterior fusion", "Anterior + posterior fusion") to remove
        any case-specific detail. Raw row-level data is never displayed in
        the app; only aggregated summary tables and figures are shown.
        """
    )

if df_primary is None:
    st.info(
        "👈 Upload a dataset (or check the **Use bundled sample** box in the "
        "sidebar) to get started."
    )
    with st.expander("📘 Quick start guide", expanded=True):
        st.markdown(
            """
            **What this app does**
            1. Reads your Excel file (must contain a binary group column,
               e.g. `Exposure`, with values 1 = exposed and 0 = unexposed).
            2. Auto-detects continuous vs categorical variables (you can
               override this in the *Variables* tab).
            3. Runs the same statistical tests used in the published study:
               - Shapiro-Wilk normality test → Welch t-test or Mann-Whitney U
               - Chi-square or Fisher's exact for categorical variables
               - Linear regression adjusted for levels involved, duration,
                 and ASA class
               - Power analysis to compute the minimum detectable difference
            4. Lets you download the results as Word, CSV, PDF, or PNG.

            **Adding new variables in a future study**
            - Either edit `config/default_variables.yaml` (see comments inside),
              **or** simply add the column to your Excel file — the app will
              auto-detect it and let you classify it in the *Variables* tab.
            """
        )
    st.stop()


if group_var not in df_primary.columns:
    st.error(
        f"❌ The group column **{group_var!r}** was not found in the primary "
        f"dataset. Available columns include: "
        f"{', '.join(list(df_primary.columns)[:20])}…"
    )
    st.stop()

# Coerce group to int 0/1
df_primary[group_var] = pd.to_numeric(df_primary[group_var], errors="coerce").astype("Int64")
n0 = int((df_primary[group_var] == 0).sum())
n1 = int((df_primary[group_var] == 1).sum())

c1, c2, c3, c4 = st.columns(4)
c1.metric("Rows", len(df_primary))
c2.metric(f"{group0_label}", n0)
c3.metric(f"{group1_label}", n1)
c4.metric("Variables", len(df_primary.columns))


# ---------------------------------------------------------------------------
# Variable configuration tab + analysis tabs
# ---------------------------------------------------------------------------
auto_cont, auto_cat = auto_classify(df_primary, group_var)

# Resolve current variable lists from config + autodetect
cfg_table1 = cfg.get("table1", {})
cfg_table2 = cfg.get("table2", {})
cfg_mv = cfg.get("multivariate", {})

defaults_t1_cont = [c for c in cfg_table1.get("continuous", []) if c in df_primary.columns]
defaults_t1_cat = [c for c in cfg_table1.get("categorical", []) if c in df_primary.columns]
defaults_t2_cont = [c for c in cfg_table2.get("continuous", []) if c in df_primary.columns]
defaults_t2_cat = [c for c in cfg_table2.get("categorical", []) if c in df_primary.columns]

# Variables in dataset that aren't classified anywhere
all_classified = set(defaults_t1_cont + defaults_t1_cat + defaults_t2_cont + defaults_t2_cat)
unclassified = [
    c for c in df_primary.columns
    if c not in all_classified and c != group_var and c != "Procedure"
]

tabs = st.tabs([
    "🧪 Variables",
    "📋 Table 1 (baseline)",
    "📊 Table 2 (perioperative)",
    "🔬 MME vs covariate",
    "📍 MME by group",
    "📈 Multivariate / Sensitivity",
    "⚡ Power (MDD figure)",
    "📥 Download report",
])

# ---------- Variables tab ----------
with tabs[0]:
    st.subheader("Variable configuration")
    st.write(
        "Use this tab to confirm or change which columns go into Table 1 vs "
        "Table 2, and whether each variable is treated as continuous or "
        "categorical. Defaults come from `config/default_variables.yaml` — "
        "any *new* columns in your file appear in the **Unclassified** list."
    )

    if unclassified:
        st.warning(
            f"🆕 {len(unclassified)} unclassified variable(s) detected: "
            + ", ".join(unclassified)
        )

    cA, cB = st.columns(2)
    with cA:
        st.markdown("**Table 1 — Continuous**")
        t1_cont = st.multiselect(
            "Table 1 continuous", options=auto_cont + auto_cat,
            default=defaults_t1_cont, key="t1_cont",
            label_visibility="collapsed",
        )
        st.markdown("**Table 1 — Categorical**")
        t1_cat = st.multiselect(
            "Table 1 categorical", options=auto_cat + auto_cont,
            default=defaults_t1_cat, key="t1_cat",
            label_visibility="collapsed",
        )
    with cB:
        st.markdown("**Table 2 — Continuous**")
        t2_cont = st.multiselect(
            "Table 2 continuous", options=auto_cont + auto_cat,
            default=defaults_t2_cont, key="t2_cont",
            label_visibility="collapsed",
        )
        st.markdown("**Table 2 — Categorical**")
        t2_cat = st.multiselect(
            "Table 2 categorical", options=auto_cat + auto_cont,
            default=defaults_t2_cat, key="t2_cat",
            label_visibility="collapsed",
        )

    st.markdown("---")
    st.markdown("**Multivariate regression**")
    mv_outcomes_default = (
        cfg_mv.get("outcomes_mme", []) + cfg_mv.get("outcomes_los", [])
    )
    mv_outcomes_default = [c for c in mv_outcomes_default if c in df_primary.columns]
    mv_outcomes = st.multiselect(
        "Outcomes",
        options=auto_cont,
        default=mv_outcomes_default,
        key="mv_outcomes",
    )

    cov_cont_default = [
        c for c in cfg_mv.get("covariates", []) if c in df_primary.columns and c != "ASA"
    ]
    mv_cov_cont = st.multiselect(
        "Continuous covariates",
        options=auto_cont, default=cov_cont_default, key="mv_cov_cont",
    )
    mv_cov_cat = st.multiselect(
        "Categorical covariates",
        options=auto_cat,
        default=[c for c in ["ASA"] if c in df_primary.columns],
        key="mv_cov_cat",
    )

    st.markdown("---")
    st.markdown("**MDD power figure**")
    mdd_outcome = st.selectbox(
        "Outcome for power curve",
        options=auto_cont,
        index=auto_cont.index(cfg.get("mdd", {}).get("outcome", "Total_MME"))
        if cfg.get("mdd", {}).get("outcome") in auto_cont
        else 0,
    )
    mdd_unit = st.text_input("Unit", value=cfg.get("mdd", {}).get("unit", "MME"))

# Build Table 1 / Table 2 / multivariate results
group_labels = {"0": group0_label, "1": group1_label}

table1 = build_univariate_table(
    df_primary, continuous=t1_cont, categorical=t1_cat,
    group=group_var, group_labels=group_labels,
)
table2 = build_univariate_table(
    df_primary, continuous=t2_cont, categorical=t2_cat,
    group=group_var, group_labels=group_labels,
)

multivariate_df = run_multivariate(
    df_primary, outcomes=mv_outcomes, group_var=group_var,
    covariates_continuous=mv_cov_cont, covariates_categorical=mv_cov_cat,
)

sensitivity_results = None
if df_sensitivity is not None and group_var in df_sensitivity.columns:
    df_sensitivity[group_var] = pd.to_numeric(
        df_sensitivity[group_var], errors="coerce"
    ).astype("Int64")
    sensitivity_results = run_sensitivity_comparison(
        df_primary=df_primary,
        df_sensitivity=df_sensitivity,
        outcomes=mv_outcomes,
        group_var=group_var,
        covariates_continuous=mv_cov_cont,
        covariates_categorical=mv_cov_cat,
        primary_label="Primary",
        sensitivity_label="Sensitivity",
    )

mdd = compute_mdd(df_primary, outcome=mdd_outcome, group_var=group_var,
                  alpha=cfg.get("mdd", {}).get("alpha", 0.05))
mdd["unit"] = mdd_unit
fig = make_mdd_figure(
    mdd, unit=mdd_unit,
    group0_label=group0_label, group1_label=group1_label,
    title_outcome=cfg.get("pretty_labels", {}).get(mdd_outcome, mdd_outcome),
)
fig_png = fig_to_bytes(fig, "png")
fig_pdf = fig_to_bytes(fig, "pdf")


# ---------- Table 1 ----------
with tabs[1]:
    st.subheader(f"Table 1. Baseline / Demographics ({group1_label} vs {group0_label})")
    st.dataframe(_hide_internal(table1), use_container_width=True, hide_index=True)
    cA, cB = st.columns(2)
    with cA:
        _download_button(
            "⬇️ Download Table 1 (CSV)",
            _hide_internal(table1).to_csv(index=False).encode("utf-8"),
            "Table1.csv", "text/csv", key="dl_t1_csv",
        )
    with cB:
        _download_button(
            "⬇️ Download Table 1 (Word)",
            df_to_docx_bytes(_hide_internal(table1), title="Table 1. Baseline / Demographics"),
            "Table1.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            key="dl_t1_docx",
        )

# ---------- Table 2 ----------
with tabs[2]:
    st.subheader(f"Table 2. Perioperative Data ({group1_label} vs {group0_label})")
    st.dataframe(_hide_internal(table2), use_container_width=True, hide_index=True)
    cA, cB = st.columns(2)
    with cA:
        _download_button(
            "⬇️ Download Table 2 (CSV)",
            _hide_internal(table2).to_csv(index=False).encode("utf-8"),
            "Table2.csv", "text/csv", key="dl_t2_csv",
        )
    with cB:
        _download_button(
            "⬇️ Download Table 2 (Word)",
            df_to_docx_bytes(_hide_internal(table2), title="Table 2. Perioperative Data"),
            "Table2.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            key="dl_t2_docx",
        )

# ---------- MME distribution (scatter) ----------
mme_dist_png = None   # made available to the combined Word report below
mme_dist_pdf = None

with tabs[3]:
    st.subheader(f"MME vs covariate — {group1_label} vs {group0_label}")
    st.caption(
        "Each dot is one patient, colored by exposure group. Solid lines are "
        "least-squares regression fits per group, with a shaded 95% confidence "
        "band around each fit. R² shows how strongly the X-axis predictor "
        "explains MME within each group; the p-value at the top of each "
        "subplot is a Mann-Whitney U comparing the overall MME distribution "
        "between groups."
    )

    detected_mme = detect_mme_variables(df_primary)
    if not detected_mme:
        st.info(
            "No MME columns detected in the dataset. Use the *Variables* tab "
            "to confirm what's present, then return here."
        )
    else:
        # Build the X-axis option list — any numeric column that's NOT the group
        # column. Default to Duration_surgery if present, else Levels_involved.
        x_options = [
            c for c in df_primary.columns
            if c != group_var and pd.api.types.is_numeric_dtype(df_primary[c])
        ]
        default_x = next(
            (v for v in ["Duration_surgery", "Levels_involved", "Preop_MME"]
             if v in x_options),
            x_options[0] if x_options else None,
        )
        cA, cB = st.columns([1, 2])
        with cA:
            x_var = st.selectbox(
                "X-axis variable",
                options=x_options,
                index=x_options.index(default_x) if default_x in x_options else 0,
                key="mme_dist_x",
                help="The continuous predictor on the X-axis (default: "
                     "Duration of surgery — the strongest covariate in the "
                     "multivariate model).",
            )
            show_reg = st.checkbox(
                "Show regression lines",
                value=True, key="mme_dist_show_reg",
            )
        with cB:
            mme_vars = st.multiselect(
                "MME variables (Y-axis)",
                options=detected_mme,
                default=detected_mme,
                key="mme_dist_vars",
                help="One subplot per selected MME variable.",
            )

        dist_fig = make_mme_distribution_figure(
            df_primary,
            x_var=x_var,
            y_vars=mme_vars,
            group_var=group_var,
            group0_label=group0_label,
            group1_label=group1_label,
            pretty_labels=cfg.get("pretty_labels", {}),
            show_regression=show_reg,
        )
        st.pyplot(dist_fig, use_container_width=True)

        if mme_vars:
            mme_dist_png = dist_fig_to_bytes(dist_fig, "png")
            mme_dist_pdf = dist_fig_to_bytes(dist_fig, "pdf")
            dA, dB = st.columns(2)
            with dA:
                _download_button(
                    "⬇️ MME distribution (PNG, 300dpi)",
                    mme_dist_png, "MME_Distribution.png", "image/png",
                    key="dl_dist_png",
                )
            with dB:
                _download_button(
                    "⬇️ MME distribution (PDF)",
                    mme_dist_pdf, "MME_Distribution.pdf", "application/pdf",
                    key="dl_dist_pdf",
                )

# ---------- MME by group (strip plot) ----------
mme_strip_png = None   # made available to the combined Word report below
mme_strip_pdf = None

with tabs[4]:
    st.subheader(f"MME by group — {group1_label} vs {group0_label}")
    st.caption(
        "Each dot is one patient at their MME value. Dots stack vertically "
        "at a single X position per group — patients with similar values "
        "overlap, producing a darker spot where more cases cluster. The "
        "optional I-beam to the left of each column shows the group median "
        "(thick bar) and interquartile range (Q1 to Q3, with caps). "
        "P-values from Mann-Whitney U (robust to non-normal MME data)."
    )

    if not detect_mme_variables(df_primary):
        st.info(
            "No MME columns detected in the dataset. Use the *Variables* tab "
            "to confirm what's present, then return here."
        )
    else:
        sC1, sC2 = st.columns([2, 1])
        with sC1:
            strip_vars = st.multiselect(
                "MME variables to plot",
                options=detect_mme_variables(df_primary),
                default=detect_mme_variables(df_primary),
                key="mme_strip_vars",
                help="Defaults to every numeric column whose name contains "
                     "'MME'.",
            )
        with sC2:
            show_error_bars = st.checkbox(
                "Show error bars (median + IQR)",
                value=True, key="mme_strip_errorbars",
                help="When on, an I-beam to the left of each column shows "
                     "the group median (thick bar) and interquartile range "
                     "(Q1 to Q3, with caps).",
            )

        strip_fig = make_mme_strip_plot(
            df_primary,
            variables=strip_vars,
            group_var=group_var,
            group0_label=group0_label,
            group1_label=group1_label,
            pretty_labels=cfg.get("pretty_labels", {}),
            unit=mdd_unit,
            show_error_bars=show_error_bars,
        )
        st.pyplot(strip_fig, use_container_width=True)

        if strip_vars:
            mme_strip_png = dist_fig_to_bytes(strip_fig, "png")
            mme_strip_pdf = dist_fig_to_bytes(strip_fig, "pdf")
            sA, sB = st.columns(2)
            with sA:
                _download_button(
                    "⬇️ MME by group (PNG, 300dpi)",
                    mme_strip_png, "MME_by_group.png", "image/png",
                    key="dl_strip_png",
                )
            with sB:
                _download_button(
                    "⬇️ MME by group (PDF)",
                    mme_strip_pdf, "MME_by_group.pdf", "application/pdf",
                    key="dl_strip_pdf",
                )

# ---------- Multivariate / Sensitivity ----------
with tabs[5]:
    st.subheader("Multivariate Linear Regression")
    show_cols = ["Outcome", "Estimate (95% CI)", "p-value", "n"]
    st.dataframe(multivariate_df[show_cols], use_container_width=True, hide_index=True)

    if sensitivity_results is not None:
        st.markdown("---")
        st.subheader("Sensitivity / Per-protocol Comparison")
        st.dataframe(sensitivity_results["side_by_side"], use_container_width=True, hide_index=True)

        st.markdown("**β-coefficient stability check**")
        st.dataframe(sensitivity_results["stability"], use_container_width=True, hide_index=True)
    else:
        st.info(
            "Upload a sensitivity / per-protocol dataset in the sidebar (or "
            "check the bundled-sample box) to enable side-by-side comparison."
        )

    cA, cB = st.columns(2)
    with cA:
        _download_button(
            "⬇️ Multivariate (CSV)",
            multivariate_df[show_cols].to_csv(index=False).encode("utf-8"),
            "Multivariate.csv", "text/csv", key="dl_mv_csv",
        )
    with cB:
        if sensitivity_results is not None:
            _download_button(
                "⬇️ Sensitivity comparison (CSV)",
                sensitivity_results["side_by_side"].to_csv(index=False).encode("utf-8"),
                "Sensitivity_comparison.csv", "text/csv", key="dl_sens_csv",
            )

# ---------- Power figure ----------
with tabs[6]:
    st.subheader("Minimum Detectable Difference — Power Curve")
    cA, cB, cC = st.columns(3)
    cA.metric("Pooled SD", f"{mdd['pooled_sd']:.1f} {mdd_unit}")
    cB.metric("MDD @ 80% power", f"{mdd['mdd_80']:.0f} {mdd_unit}")
    cC.metric("MDD @ 90% power", f"{mdd['mdd_90']:.0f} {mdd_unit}")

    cD, cE, cF = st.columns(3)
    cD.metric(f"{group0_label} mean ± SD", f"{mdd['mean0']:.1f} ± {mdd['sd0']:.1f}")
    cE.metric(f"{group1_label} mean ± SD", f"{mdd['mean1']:.1f} ± {mdd['sd1']:.1f}")
    cF.metric("Observed difference", f"{mdd['observed_diff']:.0f} {mdd_unit}")

    st.pyplot(fig, use_container_width=True)

    cA, cB = st.columns(2)
    with cA:
        _download_button(
            "⬇️ Figure (PNG, 300dpi)", fig_png,
            "MDD_Power_Figure.png", "image/png", key="dl_fig_png",
        )
    with cB:
        _download_button(
            "⬇️ Figure (PDF)", fig_pdf,
            "MDD_Power_Figure.pdf", "application/pdf", key="dl_fig_pdf",
        )

# ---------- Download report ----------
with tabs[7]:
    st.subheader("📥 Combined Word report")
    st.write(
        "One-click download containing every table and figure above, formatted "
        "for sharing."
    )

    word_bytes = build_report_docx(
        table1_df=table1,
        table2_df=table2,
        multivariate_df=multivariate_df,
        sensitivity_results=sensitivity_results,
        mdd={**mdd, "unit": mdd_unit},
        figure_png_bytes=fig_png,
        mme_distribution_png_bytes=mme_dist_png,
        group0_label=group0_label,
        group1_label=group1_label,
        pretty_labels=cfg.get("pretty_labels", {}),
        n_group0=n0,
        n_group1=n1,
    )

    _download_button(
        "⬇️ Download full Word report (.docx)",
        word_bytes, "Cohort_Analysis_Report.docx",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        key="dl_full_report",
    )

    st.markdown("---")
    st.markdown("**Individual files**")
    cA, cB, cC, cD = st.columns(4)
    with cA:
        _download_button(
            "Table 1 (CSV)",
            _hide_internal(table1).to_csv(index=False).encode("utf-8"),
            "Table1.csv", "text/csv", key="dl_full_t1",
        )
    with cB:
        _download_button(
            "Table 2 (CSV)",
            _hide_internal(table2).to_csv(index=False).encode("utf-8"),
            "Table2.csv", "text/csv", key="dl_full_t2",
        )
    with cC:
        _download_button(
            "Multivariate (CSV)",
            multivariate_df[["Outcome", "Estimate (95% CI)", "p-value", "n"]]
            .to_csv(index=False).encode("utf-8"),
            "Multivariate.csv", "text/csv", key="dl_full_mv",
        )
    with cD:
        _download_button(
            "Figure (PDF)", fig_pdf,
            "MDD_Power_Figure.pdf", "application/pdf", key="dl_full_fig",
        )

st.sidebar.markdown("---")
st.sidebar.caption(
    "📁 To add new variables in a future study, edit "
    "`config/default_variables.yaml` (clearly commented) — or just upload "
    "your new Excel file, and unclassified columns will appear in the "
    "*Variables* tab."
)
