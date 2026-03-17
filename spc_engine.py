"""
spc_engine.py
=============
Core SPC computation engine.
- All 8 Western Electric (WECO) rules
- X-bar / R chart control limits (using standard A2/D3/D4 factors)
- Individual / Moving Range (I-MR) chart limits
- Process capability: Cp, Cpk, Pp, Ppk
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional

# ── Standard control chart constants (n = 2 to 10) ──────────────────────────
# A2 : X-bar UCL/LCL factor using R-bar
# D3 : R chart LCL factor
# D4 : R chart UCL factor
# d2 : unbiasing constant for sigma estimation from R-bar
CHART_CONSTANTS = {
    2:  {"A2": 1.880, "D3": 0.000, "D4": 3.267, "d2": 1.128},
    3:  {"A2": 1.023, "D3": 0.000, "D4": 2.575, "d2": 1.693},
    4:  {"A2": 0.729, "D3": 0.000, "D4": 2.282, "d2": 2.059},
    5:  {"A2": 0.577, "D3": 0.000, "D4": 2.115, "d2": 2.326},
    6:  {"A2": 0.483, "D3": 0.000, "D4": 2.004, "d2": 2.534},
    7:  {"A2": 0.419, "D3": 0.076, "D4": 1.924, "d2": 2.704},
    8:  {"A2": 0.373, "D3": 0.136, "D4": 1.864, "d2": 2.847},
    9:  {"A2": 0.337, "D3": 0.184, "D4": 1.816, "d2": 2.970},
    10: {"A2": 0.308, "D3": 0.223, "D4": 1.777, "d2": 3.078},
}


@dataclass
class ControlLimits:
    """All limit lines needed to draw a control chart."""
    center: float
    ucl: float       # ±3σ
    lcl: float
    ucl_2s: float    # ±2σ  (Zone B boundary)
    lcl_2s: float
    ucl_1s: float    # ±1σ  (Zone C boundary)
    lcl_1s: float
    sigma: float     # within-subgroup or moving-range sigma estimate


@dataclass
class WECOViolation:
    rule_number: int
    short_name: str
    description: str
    point_indices: List[int]
    severity: str    # 'high' | 'medium' | 'low'

    def to_dict(self, chart_name: str = "") -> Dict:
        return {
            "Chart": chart_name,
            "Rule": f"Rule {self.rule_number}",
            "Short name": self.short_name,
            "Description": self.description,
            "Points flagged": len(self.point_indices),
            "First at index": self.point_indices[0] if self.point_indices else "-",
            "Severity": self.severity,
        }


# ── WECO rule metadata ────────────────────────────────────────────────────────
WECO_META = {
    1: ("Beyond 3σ",          "1 point beyond ±3σ (outside UCL/LCL)",           "high"),
    2: ("9-point run",        "9 consecutive points on same side of centerline", "high"),
    3: ("6-point trend",      "6 consecutive points steadily increasing or decreasing", "medium"),
    4: ("14-point zigzag",    "14 consecutive points alternating up and down",   "medium"),
    5: ("2-of-3 beyond 2σ",  "2 of 3 consecutive points beyond ±2σ, same side","high"),
    6: ("4-of-5 beyond 1σ",  "4 of 5 consecutive points beyond ±1σ, same side","medium"),
    7: ("15 within 1σ",       "15 consecutive points within ±1σ (hugging center)","low"),
    8: ("8 beyond ±1σ",       "8 consecutive points on both sides, none within ±1σ","medium"),
}


class WECORuleEngine:
    """Applies all 8 WECO rules to a 1-D array of chart values."""

    def check_all(self, points: np.ndarray, limits: ControlLimits) -> List[WECOViolation]:
        if limits.sigma == 0:
            return []
        z = (points - limits.center) / limits.sigma   # standardised values

        violations: List[WECOViolation] = []
        for rule_fn in [
            self._rule1, self._rule2, self._rule3, self._rule4,
            self._rule5, self._rule6, self._rule7, self._rule8,
        ]:
            result = rule_fn(points, z, limits)
            if result:
                violations.append(result)
        return violations

    # ── individual rule implementations ──────────────────────────────────────

    def _rule1(self, pts, z, lim) -> Optional[WECOViolation]:
        """Rule 1: 1 point beyond ±3σ"""
        idxs = [i for i, v in enumerate(pts) if v > lim.ucl or v < lim.lcl]
        if idxs:
            m = WECO_META[1]
            return WECOViolation(1, m[0], m[1], idxs, m[2])

    def _rule2(self, pts, z, lim) -> Optional[WECOViolation]:
        """Rule 2: 9 consecutive points same side of centerline"""
        idxs = set()
        for i in range(len(z) - 8):
            w = z[i:i+9]
            if all(v > 0 for v in w) or all(v < 0 for v in w):
                idxs.update(range(i, i+9))
        if idxs:
            m = WECO_META[2]
            return WECOViolation(2, m[0], m[1], sorted(idxs), m[2])

    def _rule3(self, pts, z, lim) -> Optional[WECOViolation]:
        """Rule 3: 6 consecutive points strictly increasing OR decreasing"""
        idxs = set()
        for i in range(len(pts) - 5):
            w = pts[i:i+6]
            if all(w[j] < w[j+1] for j in range(5)) or all(w[j] > w[j+1] for j in range(5)):
                idxs.update(range(i, i+6))
        if idxs:
            m = WECO_META[3]
            return WECOViolation(3, m[0], m[1], sorted(idxs), m[2])

    def _rule4(self, pts, z, lim) -> Optional[WECOViolation]:
        """Rule 4: 14 consecutive points alternating up and down"""
        idxs = set()
        for i in range(len(pts) - 13):
            w = pts[i:i+14]
            diffs = np.diff(w)
            if all(diffs[j] * diffs[j+1] < 0 for j in range(len(diffs)-1)):
                idxs.update(range(i, i+14))
        if idxs:
            m = WECO_META[4]
            return WECOViolation(4, m[0], m[1], sorted(idxs), m[2])

    def _rule5(self, pts, z, lim) -> Optional[WECOViolation]:
        """Rule 5: 2 of 3 consecutive points beyond ±2σ, same side"""
        idxs = set()
        for i in range(len(z) - 2):
            w = z[i:i+3]
            if sum(v > 2 for v in w) >= 2 or sum(v < -2 for v in w) >= 2:
                idxs.update(range(i, i+3))
        if idxs:
            m = WECO_META[5]
            return WECOViolation(5, m[0], m[1], sorted(idxs), m[2])

    def _rule6(self, pts, z, lim) -> Optional[WECOViolation]:
        """Rule 6: 4 of 5 consecutive points beyond ±1σ, same side"""
        idxs = set()
        for i in range(len(z) - 4):
            w = z[i:i+5]
            if sum(v > 1 for v in w) >= 4 or sum(v < -1 for v in w) >= 4:
                idxs.update(range(i, i+5))
        if idxs:
            m = WECO_META[6]
            return WECOViolation(6, m[0], m[1], sorted(idxs), m[2])

    def _rule7(self, pts, z, lim) -> Optional[WECOViolation]:
        """Rule 7: 15 consecutive points within ±1σ (stratification / hugging)"""
        idxs = set()
        for i in range(len(z) - 14):
            w = z[i:i+15]
            if all(-1 < v < 1 for v in w):
                idxs.update(range(i, i+15))
        if idxs:
            m = WECO_META[7]
            return WECOViolation(7, m[0], m[1], sorted(idxs), m[2])

    def _rule8(self, pts, z, lim) -> Optional[WECOViolation]:
        """Rule 8: 8 consecutive points on both sides of centerline, none within ±1σ"""
        idxs = set()
        for i in range(len(z) - 7):
            w = z[i:i+8]
            if (all(abs(v) > 1 for v in w)
                    and any(v > 1 for v in w)
                    and any(v < -1 for v in w)):
                idxs.update(range(i, i+8))
        if idxs:
            m = WECO_META[8]
            return WECOViolation(8, m[0], m[1], sorted(idxs), m[2])


class SPCEngine:
    """High-level SPC engine: control limits, capability, WECO violations."""

    def __init__(self):
        self.weco = WECORuleEngine()

    # ── Subgroup helpers ──────────────────────────────────────────────────────

    def make_subgroups(self, data: np.ndarray, n: int) -> Tuple[np.ndarray, np.ndarray]:
        """Return (x-bar array, R array) for subgroup size n."""
        k = len(data) // n
        mat = data[:k * n].reshape(k, n)
        return mat.mean(axis=1), mat.max(axis=1) - mat.min(axis=1)

    # ── X-bar / R chart limits ────────────────────────────────────────────────

    def xbar_r_limits(self, xbar: np.ndarray, R: np.ndarray, n: int
                      ) -> Tuple[ControlLimits, ControlLimits]:
        c = CHART_CONSTANTS[n]
        xbar_bar = xbar.mean()
        R_bar    = R.mean()
        sigma    = R_bar / (c["d2"] * np.sqrt(n))   # within-subgroup σ estimate

        def zone(center, s):
            return ControlLimits(
                center  = center,
                ucl     = center + 3*s,
                lcl     = center - 3*s,
                ucl_2s  = center + 2*s,
                lcl_2s  = center - 2*s,
                ucl_1s  = center + s,
                lcl_1s  = center - s,
                sigma   = s,
            )

        # X-bar chart
        x_limits = zone(xbar_bar, sigma)

        # R chart  (sigma approximation for zone lines: use (UCL-R_bar)/3)
        R_ucl = c["D4"] * R_bar
        R_lcl = c["D3"] * R_bar
        R_s   = (R_ucl - R_bar) / 3  if (R_ucl - R_bar) > 0 else R_bar * 0.1
        r_limits = ControlLimits(
            center  = R_bar,
            ucl     = R_ucl,
            lcl     = max(0, R_lcl),
            ucl_2s  = R_bar + 2*R_s,
            lcl_2s  = max(0, R_bar - 2*R_s),
            ucl_1s  = R_bar + R_s,
            lcl_1s  = max(0, R_bar - R_s),
            sigma   = R_s,
        )

        return x_limits, r_limits

    # ── I-MR chart limits ─────────────────────────────────────────────────────

    def imr_limits(self, data: np.ndarray) -> Tuple[ControlLimits, ControlLimits]:
        mR     = np.abs(np.diff(data))
        mR_bar = mR.mean()
        x_bar  = data.mean()
        d2, D4 = 1.128, 3.267           # constants for n=2 moving range
        sigma  = mR_bar / d2

        def zone(center, s, min_lcl=None):
            lcl = center - 3*s
            if min_lcl is not None:
                lcl = max(min_lcl, lcl)
            return ControlLimits(
                center  = center,
                ucl     = center + 3*s,
                lcl     = lcl,
                ucl_2s  = center + 2*s,
                lcl_2s  = max(min_lcl or -np.inf, center - 2*s),
                ucl_1s  = center + s,
                lcl_1s  = max(min_lcl or -np.inf, center - s),
                sigma   = s,
            )

        i_lim  = zone(x_bar,  sigma)
        mR_s   = (D4 * mR_bar - mR_bar) / 3
        mr_lim = zone(mR_bar, mR_s, min_lcl=0.0)
        mr_lim.ucl = D4 * mR_bar
        return i_lim, mr_lim

    # ── Process capability ────────────────────────────────────────────────────

    def capability(
        self,
        data: np.ndarray,
        usl: Optional[float] = None,
        lsl: Optional[float] = None,
        sigma_within: Optional[float] = None,
    ) -> Dict:
        """Return Cp, Cpk, Pp, Ppk and descriptive stats."""
        mean     = float(np.mean(data))
        std_tot  = float(np.std(data, ddof=1))           # overall / long-term
        std_win  = sigma_within if sigma_within else std_tot

        res = dict(mean=mean, std_overall=std_tot, std_within=std_win, n=len(data))

        if usl is not None and lsl is not None:
            res["Cp"]  = (usl - lsl) / (6 * std_win)
            res["Cpu"] = (usl - mean) / (3 * std_win)
            res["Cpl"] = (mean - lsl) / (3 * std_win)
            res["Cpk"] = min(res["Cpu"], res["Cpl"])
            res["Pp"]  = (usl - lsl) / (6 * std_tot)
            res["Ppu"] = (usl - mean) / (3 * std_tot)
            res["Ppl"] = (mean - lsl) / (3 * std_tot)
            res["Ppk"] = min(res["Ppu"], res["Ppl"])
        elif usl is not None:
            res["Cpu"] = (usl - mean) / (3 * std_win)
            res["Cpk"] = res["Cpu"]
            res["Ppu"] = (usl - mean) / (3 * std_tot)
            res["Ppk"] = res["Ppu"]
        elif lsl is not None:
            res["Cpl"] = (mean - lsl) / (3 * std_win)
            res["Cpk"] = res["Cpl"]
            res["Ppl"] = (mean - lsl) / (3 * std_tot)
            res["Ppk"] = res["Ppl"]

        return res

    # ── Full analysis ─────────────────────────────────────────────────────────

    def full_analysis(
        self,
        data: np.ndarray,
        n: int = 5,
        usl: Optional[float] = None,
        lsl: Optional[float] = None,
    ) -> Dict:
        """
        Run complete SPC analysis for a 1-D array.
        Returns xbar, R (or individual/mR), control limits,
        WECO violations, and capability indices.
        """
        result: Dict = {"n": n, "raw": data}

        if n == 1:
            # Individual / Moving Range
            mR      = np.abs(np.diff(data))
            i_lim, mr_lim = self.imr_limits(data)
            result.update(
                chart_type   = "I-MR",
                individuals  = data,
                moving_range = np.insert(mR, 0, np.nan),
                i_limits     = i_lim,
                mr_limits    = mr_lim,
                weco_i       = self.weco.check_all(data, i_lim),
                weco_mr      = self.weco.check_all(np.insert(mR, 0, mR[0]), mr_lim),
                capability   = self.capability(data, usl, lsl, sigma_within=i_lim.sigma),
            )
        else:
            # X-bar / R
            xbar, R      = self.make_subgroups(data, n)
            x_lim, r_lim = self.xbar_r_limits(xbar, R, n)
            result.update(
                chart_type = "X-bar/R",
                xbar       = xbar,
                R          = R,
                x_limits   = x_lim,
                r_limits   = r_lim,
                weco_xbar  = self.weco.check_all(xbar, x_lim),
                weco_r     = self.weco.check_all(R,    r_lim),
                capability = self.capability(data, usl, lsl, sigma_within=x_lim.sigma),
            )

        return result
