# Complex Spine Surgery Cohort Analysis — Project Handoff

A complete context document for continuing this project in a new Claude session.

---

## What this is

A standalone Streamlit web app that takes a de-identified Excel dataset
from a complex spine surgery cohort and reproduces every table and figure
from the original published R analysis pipeline. The app compares the
**exposed cohort** (received methadone + ketamine) with the **unexposed
cohort** (received neither). Built so that residents with no statistical
background can drop in an Excel file and get publication-ready output.

> **Naming note:** the repo, GitHub URL, and local folder are still called
> `NMDA-Analysis-App` for git/history continuity. The study itself was
> rebranded from "D-NMDA Antagonist Study" to a generic "exposed vs
> unexposed cohort" framing after the original framing was rejected for
> heterogeneity. The grouping column was renamed `D-NMDA` → `Exposure`
> (1 = exposed = methadone + ketamine; 0 = unexposed). All UI text,
> defaults, and Word output reflect the new naming; only the repo / folder
> name retain the legacy "NMDA" string.

**Owner:** Laurence Henson (anesthesiologist), laurence.cyril.henson@gmail.com

---

## Where it lives

- **GitHub repo (source of truth):** https://github.com/cyrilhenson/NMDA-Analysis-App
- **Live app (Streamlit Community Cloud):** the public URL ending in `.streamlit.app` for repo `nmda-analysis-app` (auto-deploys from the `main` branch)
- **Local working copy:** `C:\Users\Laurence\Desktop\NMDA-Analysis-App`

Workflow: edit locally → commit/push via **GitHub Desktop** → Streamlit Cloud auto-rebuilds in ~90 seconds.

---

## What the app produces

1. **Table 1** — baseline patient & surgical characteristics
2. **Table 2** — perioperative data and outcomes
3. **Multivariate** — OLS linear regression (outcome ~ group + Levels + Duration + ASA(factor))
4. **Sensitivity / per-protocol** — side-by-side comparison + β-coefficient stability check (when a 2nd dataset is uploaded)
5. **MDD power figure** — Power vs. Detectable Difference curve

All outputs are downloadable as **Word, CSV, PDF, or PNG**, plus a single
combined Word report in the *Download report* tab.

---

## Statistical methodology (mirrors the published R pipeline exactly)

| Test                   | When applied                                                                  |
|------------------------|-------------------------------------------------------------------------------|
| Shapiro-Wilk           | Each continuous variable, both groups separately. Normality if both p > 0.05. |
| Welch's t-test         | Continuous, both groups normal. Reports mean ± SD.                            |
| Mann-Whitney U         | Continuous, at least one group non-normal. Reports median (IQR).              |
| Chi-square             | Categorical, default.                                                         |
| Fisher's exact         | Categorical, **2×2** *and* any expected cell < 5.                             |
| OLS linear regression  | Multivariate: outcome ~ group + Levels + Duration + ASA(factor).              |
| Two-sample t-test power| MDD: pooled SD; non-central t for unequal n; bisection to solve for d.        |

Verified to match the original R outputs to within rounding precision.

---

## File map

```
NMDA-Analysis-App/
├── app.py                         # Main Streamlit app (UI + tab routing)
├── analysis/
│   ├── univariate.py              # Tables 1 & 2 (Shapiro/t-test/MWU; chi-sq/Fisher)
│   ├── multivariate.py            # OLS linear regression
│   ├── sensitivity.py             # Per-protocol side-by-side + β-stability
│   └── power.py                   # MDD power curve & figure
├── exports/
│   └── word_export.py             # Word report assembly
├── config/
│   └── default_variables.yaml     # Variable definitions (commented)
├── sample_data/
│   ├── Sample_Complex_Spine.xlsx  # generalized demo cohort
│   └── Sample_Sensitivity.xlsx    # generalized sensitivity cohort
├── .streamlit/
│   ├── config.toml                # headless=true, theme, 50MB upload limit
│   └── credentials.toml           # empty email to skip welcome prompt
├── .python-version                # 3.12 (pyenv convention; not used by Streamlit Cloud)
├── requirements.txt               # pinned to stable versions (see below)
├── run_local.bat                  # Windows one-click launcher
├── run_local.command              # macOS / Linux one-click launcher
└── README.md
```

---

## Tech stack & version pins

Pinned in `requirements.txt`:

```
streamlit>=1.30,<2.0
pandas>=2.1,<3.0
numpy>=1.24,<2.5
openpyxl>=3.1
scipy>=1.11,<1.16
statsmodels>=0.14,<0.15
matplotlib>=3.7,<4.0
python-docx>=1.1
PyYAML>=6.0
```

**Why pinned:** pandas 3.0 (released April 2026) breaks statsmodels/patsy.
Python 3.14 has no pre-built scipy wheel and Streamlit Cloud's sandbox
lacks `gfortran`, so it tries to compile scipy from source and fails.

---

## Streamlit Cloud configuration (set in the app's Settings UI)

- **Python version: 3.12** — set via the share.streamlit.io Settings dropdown, NOT via `.python-version` (Streamlit Cloud doesn't read that file).
- **Main file:** `app.py`
- **Branch:** `main`

If the build ever fails with a `scipy` compilation error mentioning
`gfortran`, the cause is Python having reverted to 3.14. Fix by going
back to Settings → Python version → 3.12.

---

## Privacy & HIPAA

The app displays a **🔒 Privacy & HIPAA notice** expander right under the
title on every page load.

Compliance posture:

- App is designed for de-identified data only (HIPAA Safe Harbor §164.514(b)).
- No raw row-level data is ever displayed in the UI — only aggregated tables and figures.
- Uploaded files are processed in memory only; nothing persists on Streamlit's servers.
- The bundled sample dataset has had its `Procedure` column generalized into 4 broad buckets (Posterior fusion / Anterior + posterior fusion / Posterior fusion with interbody / Cervical fusion) so it contains zero case-specific narrative text.
- All ages are ≤ 84, so the Safe Harbor "90+ aggregation" rule is moot.

---

## Robustness — what happens if columns are missing

The app is deliberately tolerant. Every section (Table 1, Table 2,
regression, MDD) filters its config defaults by `if c in df.columns`,
so missing columns are silently dropped from the relevant table rather
than crashing.

**The only required column** is the binary group column (`Exposure` by
default — renameable in the sidebar). If it's missing, the app stops
with a clear red error listing what columns it did find.

Residents can also add brand-new columns to their Excel files and they'll
be auto-detected (numeric with > 6 unique values → continuous, else
categorical) and surfaced in the *Variables* tab under "Unclassified" so
they can be added to either table with a multiselect.

---

## Adding new variables in a future study

Two equivalent options (residents can pick either):

1. **Edit `config/default_variables.yaml`** — clearly commented; add the column under `continuous:` or `categorical:` of `table1` or `table2`.
2. **Just upload the new Excel** — auto-detect handles it; classify in the *Variables* tab.

---

## Deployment & maintenance notes

- **Sleep mode:** Streamlit Community Cloud puts apps to sleep after ~7 days of zero traffic. First visitor sees a "wake this app up" button and waits ~30s. Nothing is lost — the app, repo, settings, and URL all persist.
- **The app only disappears if:** the GitHub repo is deleted, the app is manually removed from share.streamlit.io, or the repo is renamed without updating Streamlit settings.
- **Updates:** edit locally → commit/push via GitHub Desktop → Streamlit Cloud auto-redeploys (~90s).

---

## Lessons learned from the build (so they don't bite again)

- **patsy + Int64**: `astype(int)` on patsy formula columns breaks on `Int64Dtype`. Fix: defer the conversion until *after* `dropna()`. Already in `analysis/multivariate.py`.
- **CLI git push from a Windows .bat is fragile** — auth, identity config, and pull-rebase fallbacks all created friction. **GitHub Desktop is the right tool** for this user.
- **Streamlit Cloud Python version is set in the UI**, not via `.python-version` or `runtime.txt`. The `.python-version = 3.12` file in the repo is harmless but doesn't do anything on Streamlit Cloud.
- **Streamlit Cloud needs `headless = true`** in `.streamlit/config.toml`, otherwise the welcome-email prompt blocks startup and the health check fails with `connection refused`.

---

## How to continue this project in a new Claude session

1. On **claude.ai**, click **Projects** in the left sidebar → **Create Project** (e.g., "Complex Spine Cohort Analysis").
2. In the project's **Project knowledge** section, click **Add content** and upload:
   - This file (`NMDA-Analysis-App-Handoff.md`) — the master context.
   - Optionally: `app.py`, the four files in `analysis/`, `exports/word_export.py`, `config/default_variables.yaml`, `requirements.txt`, and `README.md` so Claude can read code directly without you pasting it.
3. In the project's **Custom instructions**, paste:
   > This project is the Complex Spine Surgery Cohort Analysis Streamlit app — a comparison of an exposed cohort (methadone + ketamine) vs. an unexposed cohort. The repo is at https://github.com/cyrilhenson/NMDA-Analysis-App (legacy repo name, kept for git continuity) and is auto-deployed to Streamlit Community Cloud. The grouping column in Excel files is `Exposure` (1 = exposed, 0 = unexposed). See the handoff doc in project knowledge for full context including version pins, the Python 3.12 requirement, and the HIPAA posture. When suggesting changes, assume the user will commit and push via GitHub Desktop.
4. Start a new chat in the project. Claude will have all the context needed to help with bug fixes, new features, or porting to a new study cohort.
