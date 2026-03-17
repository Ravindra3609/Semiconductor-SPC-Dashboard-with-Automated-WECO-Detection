"""
chart_utils.py
==============
Plotly figure builders for:
- X-bar chart with WECO annotations
- R / MR chart with WECO annotations
- Process capability histogram + normal curve
- Cp/Cpk gauge indicators
- WECO zone band overlay helper
"""

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import List, Optional, Dict

from spc_engine import ControlLimits, WECOViolation

# ── Colour palette ─────────────────────────────────────────────────────────────
CLR = {
    "line":     "#0ea5e9",   # main data line
    "cl":       "#64748b",   # center line
    "ucl_lcl":  "#ef4444",   # ±3σ limit
    "2s":       "#f97316",   # ±2σ line
    "1s":       "#22c55e",   # ±1σ line
    "zone_a":   "rgba(239,68,68,0.07)",
    "zone_b":   "rgba(249,115,22,0.06)",
    "zone_c":   "rgba(34,197,94,0.05)",
    "viol_high":   "#ef4444",
    "viol_med":    "#f97316",
    "viol_low":    "#eab308",
    "pass":     "#22c55e",
    "bg":       "#0f172a",
    "grid":     "rgba(255,255,255,0.07)",
    "text":     "#e2e8f0",
    "subtext":  "#94a3b8",
}

SEVERITY_CLR = {"high": CLR["viol_high"], "medium": CLR["viol_med"], "low": CLR["viol_low"]}


def _dark_layout(title: str = "", height: int = 380) -> Dict:
    return dict(
        title=dict(text=title, font=dict(color=CLR["text"], size=14)),
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor ="rgba(0,0,0,0)",
        font=dict(color=CLR["text"], family="'IBM Plex Mono', 'Courier New', monospace"),
        xaxis=dict(gridcolor=CLR["grid"], zeroline=False, showline=False),
        yaxis=dict(gridcolor=CLR["grid"], zeroline=False, showline=False),
        margin=dict(t=45, b=35, l=55, r=20),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=11)),
        showlegend=True,
    )


def _hline(fig, y: float, color: str, dash: str, label: str, row: int = 1, col: int = 1):
    fig.add_hline(y=y, line_color=color, line_dash=dash,
                  annotation_text=label,
                  annotation_font_color=color,
                  annotation_font_size=10,
                  annotation_position="top right",
                  row=row, col=col)


def _zone_bands(fig, lim: ControlLimits, n_pts: int, row: int = 1, col: int = 1):
    """Shade Zone A / B / C bands."""
    xs = [0, n_pts - 1, n_pts - 1, 0]

    def band(y0, y1, color):
        fig.add_trace(
            go.Scatter(x=xs, y=[y0, y0, y1, y1],
                       fill="toself", fillcolor=color,
                       line=dict(width=0), showlegend=False,
                       hoverinfo="skip"),
            row=row, col=col
        )

    band(lim.ucl_2s, lim.ucl,    CLR["zone_a"])
    band(lim.lcl,    lim.lcl_2s, CLR["zone_a"])
    band(lim.ucl_1s, lim.ucl_2s, CLR["zone_b"])
    band(lim.lcl_2s, lim.lcl_1s, CLR["zone_b"])
    band(lim.lcl_1s, lim.ucl_1s, CLR["zone_c"])


def _violation_markers(fig, pts: np.ndarray, violations: List[WECOViolation],
                        row: int = 1, col: int = 1):
    """Overlay coloured scatter markers for each WECO violation group."""
    added_rules = set()
    for v in violations:
        color = SEVERITY_CLR.get(v.severity, "#ef4444")
        label = f"R{v.rule_number}: {v.short_name}" if v.rule_number not in added_rules else None
        added_rules.add(v.rule_number)

        xs = [i for i in v.point_indices if i < len(pts)]
        ys = [pts[i] for i in xs]
        fig.add_trace(
            go.Scatter(
                x=xs, y=ys,
                mode="markers",
                marker=dict(color=color, size=9, symbol="circle-open",
                            line=dict(width=2, color=color)),
                name=label or f"R{v.rule_number}",
                showlegend=(label is not None),
                hovertemplate=f"Rule {v.rule_number} ({v.severity})<br>Index: %{{x}}<br>Value: %{{y:.4f}}<extra></extra>",
            ),
            row=row, col=col
        )


# ── Public chart builders ─────────────────────────────────────────────────────

def control_chart_figure(
    pts: np.ndarray,
    lim: ControlLimits,
    violations: List[WECOViolation],
    title: str = "Control Chart",
    y_label: str = "Value",
    x_labels: Optional[List] = None,
) -> go.Figure:
    """Build a single control chart (X-bar, I, or R/MR) with WECO markers."""
    n = len(pts)
    xs = list(range(n)) if x_labels is None else x_labels

    fig = go.Figure()
    fig.update_layout(**_dark_layout(title))

    # Zone bands (drawn first so they sit behind the line)
    _zone_bands(fig, lim, n)

    # Limit lines
    _hline(fig, lim.ucl,    CLR["ucl_lcl"], "dash",  f"UCL {lim.ucl:.3g}")
    _hline(fig, lim.center, CLR["cl"],      "solid", f"CL {lim.center:.3g}")
    _hline(fig, lim.lcl,    CLR["ucl_lcl"], "dash",  f"LCL {lim.lcl:.3g}")
    _hline(fig, lim.ucl_2s, CLR["2s"],      "dot",   "+2σ")
    _hline(fig, lim.lcl_2s, CLR["2s"],      "dot",   "-2σ")
    _hline(fig, lim.ucl_1s, CLR["1s"],      "dot",   "+1σ")
    _hline(fig, lim.lcl_1s, CLR["1s"],      "dot",   "-1σ")

    # Main data line
    fig.add_trace(go.Scatter(
        x=xs, y=pts,
        mode="lines+markers",
        line=dict(color=CLR["line"], width=1.5),
        marker=dict(color=CLR["line"], size=5),
        name=y_label,
        hovertemplate="Index: %{x}<br>Value: %{y:.4f}<extra></extra>",
    ))

    # WECO violation markers
    _violation_markers(fig, pts, violations)

    fig.update_yaxes(title_text=y_label)
    fig.update_xaxes(title_text="Subgroup / Sample index")
    return fig


def xbar_r_figure(
    xbar: np.ndarray, R: np.ndarray,
    x_lim: ControlLimits, r_lim: ControlLimits,
    weco_xbar: List[WECOViolation], weco_r: List[WECOViolation],
    feature_name: str = "Parameter",
) -> go.Figure:
    """Side-by-side X-bar (top) and R (bottom) chart in a single figure."""
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.12,
        subplot_titles=(f"X̄ chart — {feature_name}", f"R chart — {feature_name}"),
    )
    fig.update_layout(
        height=620,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor ="rgba(0,0,0,0)",
        font=dict(color=CLR["text"], family="'IBM Plex Mono', 'Courier New', monospace"),
        margin=dict(t=60, b=40, l=60, r=20),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=11)),
        showlegend=True,
    )
    for ax in fig.layout:
        if ax.startswith("xaxis") or ax.startswith("yaxis"):
            fig.layout[ax].update(gridcolor=CLR["grid"], zeroline=False, showline=False)

    def add_chart(pts, lim, violations, row, name):
        n = len(pts)
        _zone_bands(fig, lim, n, row=row)
        for y, color, dash, label in [
            (lim.ucl,    CLR["ucl_lcl"], "dash",  f"UCL {lim.ucl:.4g}"),
            (lim.center, CLR["cl"],      "solid", f"CL {lim.center:.4g}"),
            (lim.lcl,    CLR["ucl_lcl"], "dash",  f"LCL {lim.lcl:.4g}"),
            (lim.ucl_2s, CLR["2s"],      "dot",   ""),
            (lim.lcl_2s, CLR["2s"],      "dot",   ""),
            (lim.ucl_1s, CLR["1s"],      "dot",   ""),
            (lim.lcl_1s, CLR["1s"],      "dot",   ""),
        ]:
            fig.add_hline(y=y, line_color=color, line_dash=dash,
                          annotation_text=label,
                          annotation_font_color=color,
                          annotation_font_size=10,
                          annotation_position="top right",
                          row=row, col=1)
        fig.add_trace(go.Scatter(
            x=list(range(n)), y=pts,
            mode="lines+markers",
            line=dict(color=CLR["line"], width=1.5),
            marker=dict(color=CLR["line"], size=4),
            name=name,
            hovertemplate="Index: %{x}<br>Value: %{y:.4f}<extra></extra>",
        ), row=row, col=1)
        _violation_markers(fig, pts, violations, row=row)

    add_chart(xbar, x_lim, weco_xbar, row=1, name="X̄")
    add_chart(R,    r_lim, weco_r,    row=2, name="R")
    return fig


def imr_figure(
    individuals: np.ndarray, mr: np.ndarray,
    i_lim: ControlLimits, mr_lim: ControlLimits,
    weco_i: List[WECOViolation], weco_mr: List[WECOViolation],
    feature_name: str = "Parameter",
) -> go.Figure:
    """Individual (top) + Moving Range (bottom) chart."""
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.12,
        subplot_titles=(f"Individual chart — {feature_name}", f"Moving Range — {feature_name}"),
    )
    fig.update_layout(
        height=620,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=CLR["text"], family="'IBM Plex Mono', 'Courier New', monospace"),
        margin=dict(t=60, b=40, l=60, r=20),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=11)),
        showlegend=True,
    )
    for ax in fig.layout:
        if ax.startswith("xaxis") or ax.startswith("yaxis"):
            fig.layout[ax].update(gridcolor=CLR["grid"], zeroline=False)

    def add_panel(pts, lim, violations, row, name):
        n = len(pts)
        _zone_bands(fig, lim, n, row=row)
        for y, color, dash, label in [
            (lim.ucl,    CLR["ucl_lcl"], "dash",  f"UCL {lim.ucl:.4g}"),
            (lim.center, CLR["cl"],      "solid", f"CL {lim.center:.4g}"),
            (lim.lcl,    CLR["ucl_lcl"], "dash",  f"LCL {lim.lcl:.4g}"),
        ]:
            fig.add_hline(y=y, line_color=color, line_dash=dash,
                          annotation_text=label, annotation_font_color=color,
                          annotation_font_size=10, annotation_position="top right",
                          row=row, col=1)
        valid = ~np.isnan(pts)
        fig.add_trace(go.Scatter(
            x=np.where(valid)[0].tolist(), y=pts[valid].tolist(),
            mode="lines+markers",
            line=dict(color=CLR["line"], width=1.5),
            marker=dict(color=CLR["line"], size=4),
            name=name,
        ), row=row, col=1)
        _violation_markers(fig, pts, violations, row=row)

    add_panel(individuals, i_lim, weco_i,  row=1, name="Individual")
    add_panel(mr,          mr_lim, weco_mr, row=2, name="MR")
    return fig


def capability_figure(
    data: np.ndarray,
    cap: Dict,
    usl: Optional[float] = None,
    lsl: Optional[float] = None,
    feature_name: str = "Parameter",
) -> go.Figure:
    """Histogram overlaid with normal curve and spec / control limit lines."""
    mean   = cap["mean"]
    std    = cap["std_overall"]

    # Histogram
    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=data, nbinsx=30,
        name="Measurements",
        marker_color="rgba(14,165,233,0.55)",
        marker_line_color="rgba(14,165,233,0.85)",
        marker_line_width=0.8,
    ))

    # Normal fit curve (scale to histogram counts)
    x_fit  = np.linspace(data.min() - 3*std, data.max() + 3*std, 400)
    from scipy.stats import norm
    y_fit  = norm.pdf(x_fit, mean, std)
    bin_w  = (data.max() - data.min()) / 30
    y_fit *= len(data) * bin_w
    fig.add_trace(go.Scatter(
        x=x_fit, y=y_fit,
        mode="lines", name="Normal fit",
        line=dict(color="#38bdf8", width=2),
    ))

    # Spec limit lines
    if usl is not None:
        fig.add_vline(x=usl, line_color="#ef4444", line_dash="dash",
                      annotation_text=f"USL={usl:.4g}",
                      annotation_font_color="#ef4444")
    if lsl is not None:
        fig.add_vline(x=lsl, line_color="#ef4444", line_dash="dash",
                      annotation_text=f"LSL={lsl:.4g}",
                      annotation_font_color="#ef4444")

    # Mean line
    fig.add_vline(x=mean, line_color=CLR["cl"], line_dash="solid",
                  annotation_text=f"Mean={mean:.4g}",
                  annotation_font_color=CLR["cl"])

    # ±3σ lines
    for direction, label in [(3, "+3σ"), (-3, "-3σ")]:
        fig.add_vline(x=mean + direction*std,
                      line_color="#94a3b8", line_dash="dot",
                      annotation_text=label,
                      annotation_font_color="#94a3b8")

    fig.update_layout(
        **_dark_layout(f"Process capability — {feature_name}", height=380),
        bargap=0.05,
    )
    fig.update_xaxes(title_text=feature_name)
    fig.update_yaxes(title_text="Count")
    return fig


def capability_gauges(cap: Dict) -> go.Figure:
    """Gauge indicators for Cpk and Ppk."""
    indices = []
    if "Cpk" in cap: indices.append(("Cpk", cap["Cpk"]))
    if "Ppk" in cap: indices.append(("Ppk", cap["Ppk"]))
    if "Cp"  in cap: indices.append(("Cp",  cap["Cp"]))
    if "Pp"  in cap: indices.append(("Pp",  cap["Pp"]))

    if not indices:
        fig = go.Figure()
        fig.add_annotation(text="Set USL and/or LSL to compute capability",
                           xref="paper", yref="paper", x=0.5, y=0.5,
                           showarrow=False, font=dict(color=CLR["subtext"], size=14))
        fig.update_layout(**_dark_layout("", height=220))
        return fig

    n_gauges = len(indices)
    fig = make_subplots(
        rows=1, cols=n_gauges,
        specs=[[{"type": "indicator"}] * n_gauges],
    )

    def gauge_color(val):
        if val is None or np.isnan(val): return "#64748b"
        if val >= 1.67: return "#22c55e"
        if val >= 1.33: return "#86efac"
        if val >= 1.00: return "#f97316"
        return "#ef4444"

    for col_i, (name, val) in enumerate(indices, start=1):
        safe_val = val if val is not None and not np.isnan(val) else 0
        color    = gauge_color(val)
        fig.add_trace(go.Indicator(
            mode="gauge+number",
            value=round(safe_val, 3),
            title=dict(text=name, font=dict(color=CLR["text"], size=14)),
            gauge=dict(
                axis=dict(range=[0, 2.5], tickcolor=CLR["subtext"],
                          tickfont=dict(color=CLR["subtext"], size=10)),
                bar=dict(color=color),
                bgcolor="rgba(0,0,0,0)",
                borderwidth=0,
                steps=[
                    dict(range=[0, 1.00], color="rgba(239,68,68,0.15)"),
                    dict(range=[1.00, 1.33], color="rgba(249,115,22,0.15)"),
                    dict(range=[1.33, 1.67], color="rgba(134,239,172,0.15)"),
                    dict(range=[1.67, 2.50], color="rgba(34,197,94,0.15)"),
                ],
                threshold=dict(line=dict(color="#f8fafc", width=2), value=1.33),
            ),
            number=dict(font=dict(color=color, size=28)),
        ), row=1, col=col_i)

    fig.update_layout(
        height=220,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=CLR["text"], family="'IBM Plex Mono', 'Courier New', monospace"),
        margin=dict(t=20, b=10, l=20, r=20),
    )
    return fig
