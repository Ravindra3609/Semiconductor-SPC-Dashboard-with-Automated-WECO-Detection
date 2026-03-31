# 🔬 WaferGuard SPC System (Semiconductor Process Control Dashboard

**Statistical Process Control (SPC) monitoring system with automated WECO violation detection**  
Built for semiconductor manufacturing process monitoring — directly applicable to FDC, WAT, and yield engineering roles.

---
<img width="1462" height="836" alt="Screenshot 2026-03-31 at 9 34 41 AM" src="https://github.com/user-attachments/assets/c48e0ead-d006-4520-b7fe-58f9455a3d66" />
<img width="1462" height="836" alt="Screenshot 2026-03-31 at 9 35 04 AM" src="https://github.com/user-attachments/assets/b5f47413-79f1-43e8-b792-40faeffd9866" />
<img width="1462" height="830" alt="Screenshot 2026-03-31 at 9 35 53 AM" src="https://github.com/user-attachments/assets/fe7ae3d0-afab-4c17-b3ed-4945c2a52e04" />
<img width="1462" height="830" alt="Screenshot 2026-03-31 at 9 36 10 AM" src="https://github.com/user-attachments/assets/22d7fb0c-284a-43db-97da-624c21d91b94" />
<img width="1462" height="835" alt="Screenshot 2026-03-31 at 9 37 03 AM" src="https://github.com/user-attachments/assets/7cc6f125-d0d8-411a-9523-6fb6ea2e25a1" />
<img width="1166" height="718" alt="Screenshot 2026-03-31 at 9 37 27 AM" src="https://github.com/user-attachments/assets/bbfb9045-f223-4d8f-b67e-faedeee893bb" />
<img width="1257" height="295" alt="Screenshot 2026-03-31 at 9 48 14 AM" src="https://github.com/user-attachments/assets/cafe3c0b-7f98-4358-ae6d-264f8821a073" />
<img width="1263" height="718" alt="Screenshot 2026-03-31 at 9 37 58 AM" src="https://github.com/user-attachments/assets/70546398-cbe7-4660-a8ba-add507ddc614" />



## What this project does

| Feature | Detail |
|---|---|
| **All 8 WECO rules** | Automated detection with color-coded severity |
| **X-bar / R charts** | Subgroup control charts with standard A2/D3/D4 factors |
| **I-MR charts** | Individual + Moving Range for single measurements |
| **Cp / Cpk / Pp / Ppk** | Full process capability with gauge indicators |
| **UCI SECOM dataset** | 1,567 real semiconductor wafers, 590 features |
| **Synthetic demo** | Pre-injected WECO fault patterns for immediate demo |
| **Alarm log export** | CSV download of all violations |
| **Dark industrial UI** | Purpose-built for fab monitoring aesthetic |

---

## Quick start (macOS M4 — 3 steps)

### Step 1 — Install Python (if not already installed)

Open **Terminal** and check:
```bash
python3 --version
```

If you get `Python 3.11` or later — you're good. If not, install via Homebrew:
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install python
```

### Step 2 — Set up the project

```bash
# Navigate to the project folder
cd ~/Desktop/spc_dashboard        # or wherever you placed it

# Make setup script executable
chmod +x setup_and_run.sh

# Run setup (creates venv, installs packages, launches app)
bash setup_and_run.sh
```

That's it. Your browser opens automatically at **http://localhost:8501**

### Step 3 — Use the dashboard

1. In the sidebar → **Select dataset** → choose **"Synthetic demo data"**
2. Check **"Inject WECO fault patterns"** → click **Generate data**
3. Select any parameter (e.g. `Chamber_Pressure_mTorr`)
4. Choose chart type: **X-bar / R** (subgroup) or **Individual (I-MR)**
5. Click **Run SPC analysis**
6. Explore the 4 tabs: Control Charts → Capability → Alarm Log → Statistics

---

## Manual setup (if the script doesn't work)

```bash
cd ~/Desktop/spc_dashboard

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install packages
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

---

## Load the real SECOM dataset

1. In the sidebar → **Select dataset** → **UCI SECOM dataset**
2. Click **Load SECOM** — downloads ~1 MB from UCI (first time only, then cached)
3. Select any of the 60 pre-filtered high-quality features
4. Run analysis

The SECOM dataset has 1,567 real semiconductor wafer runs with 590 process sensor measurements and pass/fail yield labels.

---

## Upload your own CSV

1. In the sidebar → **Select dataset** → **Upload CSV**
2. Upload any CSV with numeric process data columns
3. Select the column to monitor, set spec limits, run analysis

---

## Project file structure

```
spc_dashboard/
│
├── app.py              Main Streamlit dashboard (UI + layout)
├── spc_engine.py       Core SPC math engine
│                         - All 8 WECO rules (WECORuleEngine)
│                         - X-bar/R and I-MR control limits
│                         - Cp, Cpk, Pp, Ppk computation
│
├── chart_utils.py      Plotly figure builders
│                         - X-bar/R chart with WECO markers
│                         - I-MR chart with WECO markers
│                         - Capability histogram + normal fit
│                         - Cpk/Ppk gauge indicators
│
├── data_utils.py       Data layer
│                         - UCI SECOM downloader + cacher
│                         - Synthetic data generator with injected faults
│                         - Feature quality scoring
│
├── requirements.txt    Python package dependencies
├── setup_and_run.sh    One-shot macOS setup script
├── data/               SECOM cache directory (auto-created)
└── README.md           This file
```

---

## The 8 WECO rules — quick reference

| Rule | Name | Trigger | Severity |
|---|---|---|---|
| 1 | Beyond 3σ | 1 point outside UCL/LCL | 🔴 High |
| 2 | 9-point run | 9 consecutive points same side of centerline | 🔴 High |
| 3 | 6-point trend | 6 consecutive points steadily increasing/decreasing | 🟠 Medium |
| 4 | 14-point zigzag | 14 points alternating up and down | 🟠 Medium |
| 5 | 2-of-3 beyond 2σ | 2 of 3 consecutive points beyond ±2σ, same side | 🔴 High |
| 6 | 4-of-5 beyond 1σ | 4 of 5 consecutive points beyond ±1σ, same side | 🟠 Medium |
| 7 | 15 within 1σ | 15 consecutive points within ±1σ (hugging) | 🟡 Low |
| 8 | 8 beyond ±1σ | 8 consecutive points on both sides, none within ±1σ | 🟠 Medium |

---

## Troubleshooting

**Port 8501 already in use**
```bash
streamlit run app.py --server.port 8502
```

**ModuleNotFoundError**  
Make sure the virtual environment is activated:
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

**SECOM download fails**  
UCI servers are occasionally slow. Use synthetic demo data or upload your own CSV. The SECOM dataset can also be downloaded manually from:  
https://archive.ics.uci.edu/ml/datasets/secom

**scipy not found on M4**  
```bash
pip install scipy --no-binary :all:
```

---

## Resume framing

Use this exact line on your resume:

> **Semiconductor SPC Dashboard** — Built end-to-end SPC monitoring system in Python/Streamlit on real semiconductor manufacturing data (UCI SECOM: 1,567 wafers, 590 features). Implemented all 8 Western Electric (WECO) control rules with automated alarm engine, X-bar/R and I-MR control charts, Cp/Cpk/Pp/Ppk process capability indices, and an interactive dark-theme dashboard with CSV alarm export. Demonstrated WECO violation detection on injected fault patterns including mean shift, trend drift, and stratification.

**GitHub repository name suggestion:** `semiconductor-spc-dashboard`

**Tags to add:** `semiconductor` `spc` `statistical-process-control` `weco` `process-control` `yield-engineering` `streamlit` `plotly` `manufacturing-analytics`

---

## Interview talking points

When asked about this project:

1. **"Why SPC in semiconductors?"** — SPC is the first line of defense against yield loss. Every parameter that drifts outside control limits is a potential wafer failure. WECO rules catch drift before it causes actual yield loss — that's the value.

2. **"What are WECO rules?"** — 8 pattern-detection tests that catch non-random behavior even when points stay within 3σ limits. Rule 2 (9-point run) and Rule 3 (6-point trend) are the most important in fabs — they detect gradual drift from chamber aging or consumable wear.

3. **"What's Cpk and why does it matter?"** — Cpk measures how well the process is centered within its spec window, accounting for both spread and offset. Semiconductor fabs require Cpk ≥ 1.33 (at minimum), often 1.67 for critical parameters. A Cpk below 1.0 means you're producing out-of-spec product right now.

4. **"What dataset did you use?"** — UCI SECOM: 1,567 real semiconductor wafer runs from a manufacturing process, 590 sensor measurements, with pass/fail yield labels. It's the standard public benchmark dataset for semiconductor process analytics.
