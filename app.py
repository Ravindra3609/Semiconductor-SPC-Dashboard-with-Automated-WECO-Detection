"""
app.py
======
Semiconductor SPC Dashboard — Streamlit application.

Features:
 - Load UCI SECOM dataset or generate synthetic data (offline demo)
 - Upload your own CSV
 - X-bar/R chart  OR  Individual / Moving Range chart
 - All 8 WECO rules with colour-coded violation markers
 - Cp / Cpk / Pp / Ppk gauges
 - Process capability histogram + normal fit
 - Alarm log table with CSV export
 - Dark theme throughout
"""

import numpy as np
import pandas as pd
import streamlit as st

from spc_engine import SPCEngine
from data_utils  import (generate_synthetic_data, SYNTHETIC_SPECS,
                          load_secom, good_secom_features, clean_feature)
from chart_utils import (xbar_r_figure, imr_figure,
                          capability_figure, capability_gauges)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Semiconductor SPC Dashboard",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS (dark theme) ────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', sans-serif;
}
.stApp { background: #0b1120; color: #e2e8f0; }

/* Sidebar */
section[data-testid="stSidebar"] {
    background: #0f172a;
    border-right: 1px solid #1e293b;
}
section[data-testid="stSidebar"] * { color: #cbd5e1 !important; }

/* Metric cards */
[data-testid="metric-container"] {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 14px 18px 10px;
}
[data-testid="stMetricValue"] { font-family: 'IBM Plex Mono', monospace !important; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] { gap: 8px; border-bottom: 1px solid #1e293b; }
.stTabs [data-baseweb="tab"] {
    background: transparent;
    border-radius: 8px 8px 0 0;
    color: #94a3b8;
    font-size: 13px;
    padding: 8px 18px;
}
.stTabs [aria-selected="true"] {
    background: #1e293b !important;
    color: #e2e8f0 !important;
    border-bottom: 2px solid #0ea5e9;
}

/* Dataframe */
[data-testid="stDataFrame"] { border: 1px solid #1e293b; border-radius: 8px; }

/* Inputs */
.stSelectbox > div, .stSlider, .stNumberInput { color: #e2e8f0; }

/* Section headings inside main area */
h1, h2, h3 { color: #f1f5f9; font-family: 'IBM Plex Sans', sans-serif; font-weight: 500; }
h1 { font-size: 1.6rem; letter-spacing: -0.02em; }
h3 { font-size: 1.0rem; color: #94a3b8; font-weight: 400; }

/* Alert boxes */
.alarm-high   { background:#3b1010; border-left:3px solid #ef4444; padding:8px 12px; border-radius:0 6px 6px 0; margin:4px 0; font-size:13px; }
.alarm-medium { background:#2d1d09; border-left:3px solid #f97316; padding:8px 12px; border-radius:0 6px 6px 0; margin:4px 0; font-size:13px; }
.alarm-low    { background:#312509; border-left:3px solid #eab308; padding:8px 12px; border-radius:0 6px 6px 0; margin:4px 0; font-size:13px; }
.alarm-none   { background:#0d2014; border-left:3px solid #22c55e; padding:8px 12px; border-radius:0 6px 6px 0; margin:4px 0; font-size:13px; }

.weco-legend  { font-family:'IBM Plex Mono',monospace; font-size:12px; color:#94a3b8; line-height:1.9; }
.badge-high   { display:inline-block; background:#ef4444; color:#fff; padding:1px 8px; border-radius:12px; font-size:11px; }
.badge-med    { display:inline-block; background:#f97316; color:#fff; padding:1px 8px; border-radius:12px; font-size:11px; }
.badge-low    { display:inline-block; background:#eab308; color:#000; padding:1px 8px; border-radius:12px; font-size:11px; }
.badge-ok     { display:inline-block; background:#22c55e; color:#000; padding:1px 8px; border-radius:12px; font-size:11px; }
</style>
""", unsafe_allow_html=True)


# ── Session state defaults ─────────────────────────────────────────────────────
if "df"         not in st.session_state: st.session_state["df"]         = None
if "df_source"  not in st.session_state: st.session_state["df_source"]  = None
if "analysis"   not in st.session_state: st.session_state["analysis"]   = None


engine = SPCEngine()


# ═════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("## 🔬 SPC Dashboard")
    st.markdown("---")

    # ── Data source ──────────────────────────────────────────────────────────
    st.markdown("### Data source")
    data_source = st.selectbox(
        "Select dataset",
        ["Synthetic demo data", "UCI SECOM dataset", "Upload CSV"],
        key="data_source_select",
    )

    df: pd.DataFrame = None
    feature_cols: list = []

    if data_source == "Synthetic demo data":
        n_pts = st.slider("Number of wafer runs", 100, 600, 300, step=50)
        inject = st.checkbox("Inject WECO fault patterns", value=True)
        if st.button("Generate data", use_container_width=True):
            df = generate_synthetic_data(n=n_pts, inject_faults=inject)
            st.session_state["df"] = df
            st.session_state["df_source"] = "synthetic"
        if st.session_state["df"] is not None and st.session_state["df_source"] == "synthetic":
            df = st.session_state["df"]

    elif data_source == "UCI SECOM dataset":
        st.caption("Downloads ~1 MB from UCI on first use, then caches locally.")
        if st.button("Load SECOM", use_container_width=True):
            with st.spinner("Downloading SECOM dataset..."):
                try:
                    feat_df, label_df = load_secom()
                    good_cols = good_secom_features(feat_df, top_n=60)
                    secom_clean = pd.DataFrame(
                        {col: clean_feature(feat_df[col]) for col in good_cols}
                    )
                    secom_clean.insert(0, "pass_fail", label_df["pass_fail"].values)
                    st.session_state["df"] = secom_clean
                    st.session_state["df_source"] = "secom"
                    st.success(f"Loaded {len(secom_clean)} wafers, {len(good_cols)} features")
                except Exception as e:
                    st.error(str(e))
        if st.session_state["df"] is not None and st.session_state["df_source"] == "secom":
            df = st.session_state["df"]

    else:  # Upload CSV
        uploaded = st.file_uploader("Upload CSV file", type=["csv"])
        if uploaded:
            try:
                df = pd.read_csv(uploaded)
                st.session_state["df"] = df
                st.session_state["df_source"] = "upload"
                st.success(f"Loaded {len(df)} rows, {df.shape[1]} columns")
            except Exception as e:
                st.error(f"Could not read file: {e}")
        if st.session_state["df"] is not None and st.session_state["df_source"] == "upload":
            df = st.session_state["df"]

    if df is None:
        st.info("👆 Generate or load data to begin.")
        st.stop()

    # ── Feature selection ─────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### Parameter selection")

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if not numeric_cols:
        st.error("No numeric columns found.")
        st.stop()

    feature = st.selectbox("Process parameter", numeric_cols, key="feature_sel")

    # ── Chart type ────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### Chart settings")
    chart_type = st.radio("Chart type", ["X-bar / R", "Individual (I-MR)"],
                          horizontal=True)
    n_subgroup = 5
    if chart_type == "X-bar / R":
        n_subgroup = st.slider("Subgroup size (n)", 2, 10, 5)

    # ── WECO rule selection ───────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### WECO rules")
    active_rules = {}
    rule_labels = {
        1: "R1 — Beyond 3σ",
        2: "R2 — 9-point run",
        3: "R3 — 6-point trend",
        4: "R4 — 14-point zigzag",
        5: "R5 — 2-of-3 beyond 2σ",
        6: "R6 — 4-of-5 beyond 1σ",
        7: "R7 — 15 within 1σ",
        8: "R8 — 8 beyond ±1σ",
    }
    for r, label in rule_labels.items():
        active_rules[r] = st.checkbox(label, value=True, key=f"rule_{r}")

    # ── Spec limits ───────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### Spec limits (optional)")
    use_specs = st.checkbox("Set specification limits", value=True)
    usl, lsl = None, None
    if use_specs:
        # Pre-fill from synthetic specs if available
        preset = SYNTHETIC_SPECS.get(feature, {})
        col_data  = df[feature].dropna().to_numpy(float)
        data_mean = float(col_data.mean())
        data_std  = float(col_data.std())
        default_u = preset.get("usl", round(data_mean + 3*data_std, 3))
        default_l = preset.get("lsl", round(data_mean - 3*data_std, 3))
        usl = st.number_input("USL", value=float(default_u), format="%.4f")
        lsl = st.number_input("LSL", value=float(default_l), format="%.4f")
        if lsl >= usl:
            st.warning("LSL must be less than USL")
            usl, lsl = None, None

    # ── Run analysis ──────────────────────────────────────────────────────────
    st.markdown("---")
    run_btn = st.button("Run SPC analysis", type="primary", use_container_width=True)

    if run_btn:
        raw = df[feature].dropna().to_numpy(float)
        n   = 1 if chart_type == "Individual (I-MR)" else n_subgroup
        result = engine.full_analysis(raw, n=n, usl=usl if usl else None,
                                       lsl=lsl if lsl else None)

        # Filter by active rules
        def filter_violations(violations):
            return [v for v in violations if active_rules.get(v.rule_number, True)]

        if "weco_xbar" in result:
            result["weco_xbar"] = filter_violations(result["weco_xbar"])
            result["weco_r"]    = filter_violations(result["weco_r"])
        else:
            result["weco_i"]    = filter_violations(result["weco_i"])
            result["weco_mr"]   = filter_violations(result["weco_mr"])

        st.session_state["analysis"] = {
            "result":  result,
            "feature": feature,
            "usl":     usl,
            "lsl":     lsl,
            "n":       n,
        }


# ═════════════════════════════════════════════════════════════════════════════
# MAIN CONTENT
# ═════════════════════════════════════════════════════════════════════════════

st.markdown("# Semiconductor SPC Dashboard")
st.markdown("### Statistical Process Control with automated WECO violation detection")

if st.session_state["analysis"] is None:
    # Landing state
    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("""
        **Step 1 — Load data**
        Select a data source in the sidebar:
        synthetic demo, SECOM dataset, or your own CSV.
        """)
    with c2:
        st.markdown("""
        **Step 2 — Configure**
        Choose the process parameter, chart type,
        subgroup size, and specification limits.
        """)
    with c3:
        st.markdown("""
        **Step 3 — Analyse**
        Click *Run SPC analysis* to generate
        control charts and WECO alarm report.
        """)

    st.markdown("---")
    st.markdown("#### WECO rules reference")
    rules_ref = pd.DataFrame([
        {"#": 1, "Name": "Beyond 3σ",       "Description": "1 point outside UCL/LCL",                       "Severity": "🔴 High"},
        {"#": 2, "Name": "9-point run",      "Description": "9 consecutive points same side of centerline",  "Severity": "🔴 High"},
        {"#": 3, "Name": "6-point trend",    "Description": "6 points steadily increasing or decreasing",    "Severity": "🟠 Medium"},
        {"#": 4, "Name": "14-point zigzag",  "Description": "14 points alternating up and down",             "Severity": "🟠 Medium"},
        {"#": 5, "Name": "2-of-3 beyond 2σ","Description": "2 of 3 consecutive points beyond ±2σ, same side","Severity": "🔴 High"},
        {"#": 6, "Name": "4-of-5 beyond 1σ","Description": "4 of 5 consecutive points beyond ±1σ, same side","Severity": "🟠 Medium"},
        {"#": 7, "Name": "15 within 1σ",    "Description": "15 consecutive points hugging centerline",       "Severity": "🟡 Low"},
        {"#": 8, "Name": "8 beyond ±1σ",    "Description": "8 points on both sides, none within ±1σ",        "Severity": "🟠 Medium"},
    ])
    st.dataframe(rules_ref, hide_index=True, use_container_width=True)
    st.stop()


# ── Unpack analysis results ───────────────────────────────────────────────────
A       = st.session_state["analysis"]
result  = A["result"]
feature = A["feature"]
usl_val = A["usl"]
lsl_val = A["lsl"]
cap     = result.get("capability", {})

is_xbar = result["chart_type"] == "X-bar/R"

# ── Summary metric bar ────────────────────────────────────────────────────────
weco_all = []
if is_xbar:
    weco_all = result["weco_xbar"] + result["weco_r"]
else:
    weco_all = result["weco_i"] + result["weco_mr"]

high_ct   = sum(1 for v in weco_all if v.severity == "high")
med_ct    = sum(1 for v in weco_all if v.severity == "medium")
low_ct    = sum(1 for v in weco_all if v.severity == "low")
total_pts = sum(len(v.point_indices) for v in weco_all)
cpk_val   = cap.get("Cpk", None)

m1, m2, m3, m4, m5 = st.columns(5)
with m1:
    st.metric("Parameter", feature[:22])
with m2:
    st.metric("Total WECO violations", len(weco_all),
              delta="rules fired" if weco_all else "clean",
              delta_color="inverse")
with m3:
    st.metric("Points flagged", total_pts)
with m4:
    st.metric("Cpk", f"{cpk_val:.3f}" if cpk_val else "N/A",
              delta="≥1.33 = capable" if cpk_val and cpk_val >= 1.33 else
                    "<1.33 = review" if cpk_val else "set spec limits")
with m5:
    status = "ALARM" if weco_all else "IN CONTROL"
    st.metric("Process status", status)

st.markdown("---")

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_chart, tab_cap, tab_alarms, tab_stats = st.tabs([
    "📈 Control Charts", "⚙️ Process Capability", "🚨 Alarm Log", "📊 Statistics"
])


# ════════════════════ TAB 1: Control Charts ═══════════════════════════════════
with tab_chart:
    if is_xbar:
        fig = xbar_r_figure(
            result["xbar"], result["R"],
            result["x_limits"], result["r_limits"],
            result["weco_xbar"], result["weco_r"],
            feature_name=feature,
        )
    else:
        fig = imr_figure(
            result["individuals"], result["moving_range"],
            result["i_limits"], result["mr_limits"],
            result["weco_i"], result["weco_mr"],
            feature_name=feature,
        )

    st.plotly_chart(fig, use_container_width=True)

    # WECO zone colour legend
    st.markdown("""
    <div class="weco-legend">
    Zone bands:&nbsp;&nbsp;
    <span style="color:#22c55e">■ Zone C (±1σ)</span> &nbsp;
    <span style="color:#f97316">■ Zone B (±2σ)</span> &nbsp;
    <span style="color:#ef4444">■ Zone A (±3σ)</span> &nbsp;&nbsp;|&nbsp;&nbsp;
    Violations:&nbsp;
    <span class="badge-high">High</span>&nbsp;
    <span class="badge-med">Medium</span>&nbsp;
    <span class="badge-low">Low</span>
    </div>
    """, unsafe_allow_html=True)


# ════════════════════ TAB 2: Process Capability ═══════════════════════════════
with tab_cap:
    raw_data = result["raw"]

    gauge_fig = capability_gauges(cap)
    st.plotly_chart(gauge_fig, use_container_width=True)

    cap_fig = capability_figure(raw_data, cap, usl_val, lsl_val, feature)
    st.plotly_chart(cap_fig, use_container_width=True)

    if cap:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Within-subgroup (short-term)**")
            cap_tbl = {k: round(v, 4) for k, v in cap.items()
                       if k in ("Cp", "Cpu", "Cpl", "Cpk")}
            if cap_tbl:
                st.dataframe(pd.DataFrame.from_dict(cap_tbl, orient="index",
                             columns=["Value"]), use_container_width=True)
            else:
                st.caption("Set spec limits to compute Cp/Cpk.")
        with c2:
            st.markdown("**Overall (long-term)**")
            cap_tbl2 = {k: round(v, 4) for k, v in cap.items()
                        if k in ("Pp", "Ppu", "Ppl", "Ppk")}
            if cap_tbl2:
                st.dataframe(pd.DataFrame.from_dict(cap_tbl2, orient="index",
                             columns=["Value"]), use_container_width=True)
            else:
                st.caption("Set spec limits to compute Pp/Ppk.")

        st.markdown("""
        | Index | Rating | Meaning |
        |---|---|---|
        | < 1.00 | ❌ Not capable | Process produces out-of-spec product |
        | 1.00 – 1.33 | ⚠️ Marginal | Barely capable — needs improvement |
        | 1.33 – 1.67 | ✅ Capable | Industry minimum for most processes |
        | ≥ 1.67 | 🟢 Excellent | Six-sigma level; semiconductor target |
        """)


# ════════════════════ TAB 3: Alarm Log ════════════════════════════════════════
with tab_alarms:
    if not weco_all:
        st.markdown('<div class="alarm-none">✅ No WECO violations detected — process is in statistical control.</div>',
                    unsafe_allow_html=True)
    else:
        # Build alarm dataframe
        rows = []
        for v in weco_all:
            chart_name = "X̄ chart" if (is_xbar and v in result.get("weco_xbar", [])) else \
                         "R chart"  if (is_xbar and v in result.get("weco_r",    [])) else \
                         "I chart"  if (not is_xbar and v in result.get("weco_i", [])) else \
                         "MR chart"
            rows.append(v.to_dict(chart_name))

        alarm_df = pd.DataFrame(rows)

        # Colour-coded summary
        for v in weco_all:
            cls = {"high": "alarm-high", "medium": "alarm-medium", "low": "alarm-low"}.get(v.severity, "alarm-none")
            st.markdown(
                f'<div class="{cls}"><strong>Rule {v.rule_number} — {v.short_name}</strong> &nbsp;'
                f'({len(v.point_indices)} pts flagged) &nbsp;— {v.description}</div>',
                unsafe_allow_html=True
            )

        st.markdown("---")
        st.markdown("**Full violation table**")
        st.dataframe(alarm_df, hide_index=True, use_container_width=True)

        # CSV export
        csv = alarm_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇ Export alarm log (CSV)",
            data=csv,
            file_name=f"spc_alarms_{feature}.csv",
            mime="text/csv",
        )


# ════════════════════ TAB 4: Statistics ═══════════════════════════════════════
with tab_stats:
    raw_data = result["raw"]
    q1, q3   = np.percentile(raw_data, [25, 75])
    iqr      = q3 - q1

    stat_data = {
        "Count":        len(raw_data),
        "Mean":         round(float(np.mean(raw_data)), 6),
        "Std dev":      round(float(np.std(raw_data, ddof=1)), 6),
        "Min":          round(float(np.min(raw_data)), 6),
        "Q1 (25%)":     round(float(q1), 6),
        "Median":       round(float(np.median(raw_data)), 6),
        "Q3 (75%)":     round(float(q3), 6),
        "IQR":          round(float(iqr), 6),
        "Max":          round(float(np.max(raw_data)), 6),
        "Skewness":     round(float(pd.Series(raw_data).skew()), 4),
        "Kurtosis":     round(float(pd.Series(raw_data).kurt()), 4),
    }

    if usl_val and lsl_val:
        out_of_spec = np.sum((raw_data > usl_val) | (raw_data < lsl_val))
        stat_data["Out-of-spec (%)"] = round(out_of_spec / len(raw_data) * 100, 3)

    s1, s2 = st.columns([1, 2])
    with s1:
        st.markdown("**Descriptive statistics**")
        stat_df = pd.DataFrame.from_dict(stat_data, orient="index", columns=["Value"])
        st.dataframe(stat_df, use_container_width=True)

    with s2:
        st.markdown("**Control limit summary**")
        if is_xbar:
            xl = result["x_limits"]
            rl = result["r_limits"]
            lim_data = {
                "X̄ Center Line": round(xl.center, 6),
                "X̄ UCL (+3σ)":  round(xl.ucl, 6),
                "X̄ LCL (-3σ)":  round(xl.lcl, 6),
                "X̄ +2σ":        round(xl.ucl_2s, 6),
                "X̄ -2σ":        round(xl.lcl_2s, 6),
                "X̄ σ estimate": round(xl.sigma, 6),
                "R̄ (R-bar)":    round(rl.center, 6),
                "R UCL":         round(rl.ucl, 6),
                "R LCL":         round(rl.lcl, 6),
            }
        else:
            il = result["i_limits"]
            ml = result["mr_limits"]
            lim_data = {
                "I Center Line": round(il.center, 6),
                "I UCL (+3σ)":   round(il.ucl, 6),
                "I LCL (-3σ)":   round(il.lcl, 6),
                "I σ estimate":  round(il.sigma, 6),
                "MR-bar":        round(ml.center, 6),
                "MR UCL":        round(ml.ucl, 6),
            }
        lim_df = pd.DataFrame.from_dict(lim_data, orient="index", columns=["Value"])
        st.dataframe(lim_df, use_container_width=True)

        # WECO violation count per rule
        if weco_all:
            st.markdown("**Violations by rule**")
            rule_counts = {}
            for v in weco_all:
                key = f"Rule {v.rule_number} — {v.short_name}"
                rule_counts[key] = len(v.point_indices)
            rc_df = pd.DataFrame.from_dict(rule_counts, orient="index", columns=["Points flagged"])
            st.dataframe(rc_df, use_container_width=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<p style='text-align:center;color:#334155;font-size:12px'>"
    "SPC Dashboard &nbsp;|&nbsp; WECO rules &nbsp;|&nbsp; Cp/Cpk/Pp/Ppk &nbsp;|&nbsp; SECOM dataset"
    "</p>",
    unsafe_allow_html=True
)
