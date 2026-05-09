# Complex Spine Surgery Cohort — Standalone Analysis App

A plug-and-play web app that compares the **exposed cohort** (received methadone
+ ketamine) with the **unexposed cohort** in elective complex spine surgery.
Takes a deidentified Excel dataset and instantly reproduces every table and
figure from the original R analysis pipeline:

- **Table 1** — baseline patient & surgical characteristics
- **Table 2** — perioperative data and outcomes
- **Multivariate** — linear regression for MME and length-of-stay outcomes,
  adjusted for levels involved, duration of surgery, and ASA class
- **Sensitivity / per-protocol** — side-by-side comparison + β-coefficient
  stability check (when a 2nd dataset is supplied)
- **MDD power figure** — Power vs. Detectable Difference curve

Outputs can be downloaded as **Word, CSV, PDF, or PNG**, and the whole report
is one click away in the *Download report* tab.

The app was designed for residents with no statistical background — they only
need to upload an Excel file. All statistical methodology mirrors the original
R code exactly (Shapiro-Wilk → Welch t-test or Mann-Whitney U; chi-square or
Fisher's exact when 2×2 with any expected cell <5; OLS linear regression).

---

## Quickest path (Windows)

1. Make sure **Python 3.10 or newer** is installed
   ([download](https://www.python.org/downloads/) — tick *Add Python to PATH*).
2. Double-click `run_local.bat`.
3. The first run installs everything (~2 minutes). Future runs are instant.
4. Your browser opens at `http://localhost:8501`.

## Quickest path (macOS / Linux)

1. Install python3 (`brew install python` on macOS).
2. Double-click `run_local.command` (right-click → Open the first time).
3. First run installs deps (~2 min). Future runs instant.
4. Browser opens at `http://localhost:8501`.

## Manual launch (any OS)

```
pip install -r requirements.txt
streamlit run app.py
```

---

## Cloud deployment (Streamlit Community Cloud — free)

Residents won't even need Python installed if you deploy this once.

1. Create a free GitHub repository and push this whole folder to it.
2. Sign in to [https://share.streamlit.io](https://share.streamlit.io)
   with the same GitHub account.
3. Click **New app** → pick the repo, branch (`main`), and main file
   (`app.py`). Click **Deploy**.
4. You'll get a permanent URL like
   `https://nmda-analysis.streamlit.app` to share with the team.

The included `requirements.txt` and `.streamlit/config.toml` are everything
the cloud needs — no extra config required.

---

## How residents use it

1. **Sidebar → Upload primary dataset (.xlsx).** Or check
   *Use bundled sample* to try with the original cohort.
2. *(Optional)* Upload a sensitivity / per-protocol dataset to enable the
   side-by-side comparison.
3. **Variables tab** — quickly confirm what's in Table 1 vs Table 2 and
   whether each is continuous or categorical. Any **new column** the app
   doesn't recognise is auto-detected and listed in *Unclassified* so it
   can be added with one click.
4. **Other tabs** display each result. Each has CSV + Word download
   buttons.
5. **Download report tab** assembles everything into a single Word file.

---

## Adding new variables in a future study

You have two options — either is fine:

### Option A — edit the config file (more control)

Open `config/default_variables.yaml` in any text editor. Each section is
clearly commented. Add the new column name to either `continuous:` or
`categorical:` under `table1` or `table2`, save, and refresh the app.

### Option B — just upload the new Excel (zero editing)

The app will:
- Auto-detect the new column (numeric with > 6 unique values → continuous,
  otherwise categorical).
- Surface it in the **Variables** tab under *Unclassified*.
- Let you add it to either table with a multiselect dropdown.

Both options coexist — choose whichever the resident prefers.

---

## File / folder map

```
NMDA-Analysis-App/
├── app.py                          # Main Streamlit app
├── analysis/
│   ├── univariate.py               # Tables 1 & 2 (Shapiro/t-test/MWU; chi-sq/Fisher)
│   ├── multivariate.py             # OLS linear regression
│   ├── sensitivity.py              # Per-protocol side-by-side + β-stability
│   └── power.py                    # MDD power curve & figure
├── exports/
│   └── word_export.py              # Word report assembly
├── config/
│   └── default_variables.yaml      # Variable definitions (commented)
├── sample_data/
│   ├── Sample_Complex_Spine.xlsx       # generalized demo cohort
│   └── Sample_Sensitivity.xlsx         # generalized sensitivity cohort
├── .streamlit/config.toml          # App theme + upload limits
├── requirements.txt                # Python deps
├── run_local.bat                   # Windows one-click launcher
├── run_local.command               # macOS / Linux one-click launcher
└── README.md
```

---

## Statistical methodology (matches the published R pipeline)

| Test                      | When applied                                                                  |
|---------------------------|-------------------------------------------------------------------------------|
| Shapiro-Wilk              | Each continuous variable, both groups separately. Normality if both p > 0.05. |
| Welch's t-test            | Continuous, both groups normal. Reports mean ± SD.                            |
| Mann-Whitney U            | Continuous, at least one group non-normal. Reports median (IQR).              |
| Chi-square                | Categorical, default.                                                         |
| Fisher's exact            | Categorical, **2×2** *and* any expected cell < 5.                             |
| OLS linear regression     | Multivariate: outcome ~ group + Levels + Duration + ASA(factor).              |
| Two-sample t-test power   | MDD: pooled SD; non-central t for unequal n; bisection to solve for d.        |

p-values < 0.001 are reported as `<0.001`; p < 0.05 are starred (`*`) in the
Word tables.

---

## Troubleshooting

- **`Python is not installed or not on your PATH`** — install Python and tick
  *Add Python to PATH* during setup.
- **First launch is slow** — that's the dependency install (~2 min). Every
  subsequent launch is instant.
- **Excel file rejected** — must be `.xlsx` or `.xls`, ≤ 50 MB, and contain
  the group column (default: `Exposure`) with values 0 (unexposed) or 1 (exposed).
- **Browser doesn't open** — manually visit
  [http://localhost:8501](http://localhost:8501).
- **Streamlit Cloud deploy fails** — ensure `requirements.txt` is in the
  repo root and `app.py` is the entry-point.
