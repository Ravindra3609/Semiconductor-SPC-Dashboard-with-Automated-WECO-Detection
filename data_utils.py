"""
data_utils.py
=============
Data loading and preprocessing utilities.
- Download and parse UCI SECOM dataset
- Synthetic semiconductor data generator (demo / offline use)
- Feature quality scoring and selection helpers
"""

import io
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Tuple, Optional, List

# ── SECOM dataset (UCI Machine Learning Repository) ───────────────────────────

SECOM_DATA_URL   = "https://archive.ics.uci.edu/ml/machine-learning-databases/secom/secom.data"
SECOM_LABELS_URL = "https://archive.ics.uci.edu/ml/machine-learning-databases/secom/secom_labels.data"

SECOM_CACHE_DIR  = Path("data")


def load_secom(cache: bool = True) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load UCI SECOM dataset.
    Returns (features_df, labels_df).
    Caches locally after first download.
    """
    feat_path   = SECOM_CACHE_DIR / "secom.csv"
    labels_path = SECOM_CACHE_DIR / "secom_labels.csv"

    if cache and feat_path.exists() and labels_path.exists():
        feat_df   = pd.read_csv(feat_path)
        label_df  = pd.read_csv(labels_path)
        return feat_df, label_df

    try:
        import urllib.request
        SECOM_CACHE_DIR.mkdir(exist_ok=True)

        print("Downloading SECOM features...")
        feat_data, _ = urllib.request.urlretrieve(SECOM_DATA_URL)
        feat_df = pd.read_csv(feat_data, sep=" ", header=None,
                               na_values=["NaN", "nan", ""])
        feat_df.columns = [f"Feature_{i+1}" for i in range(feat_df.shape[1])]

        print("Downloading SECOM labels...")
        lbl_data, _  = urllib.request.urlretrieve(SECOM_LABELS_URL)
        label_df = pd.read_csv(lbl_data, sep=" ", header=None,
                                names=["label", "timestamp"])
        label_df["timestamp"] = pd.to_datetime(label_df["timestamp"])
        label_df["pass_fail"]  = label_df["label"].map({-1: "Pass", 1: "Fail"})

        feat_df.to_csv(feat_path,   index=False)
        label_df.to_csv(labels_path, index=False)

        return feat_df, label_df

    except Exception as e:
        raise RuntimeError(
            f"Could not download SECOM dataset: {e}\n"
            "Use generate_synthetic_data() for offline demo."
        )


def good_secom_features(feat_df: pd.DataFrame, max_nan_pct: float = 0.3,
                         min_std: float = 0.01, top_n: int = 50) -> List[str]:
    """Return features with low NaN rate and enough variance for SPC."""
    nan_pct = feat_df.isna().mean()
    std_val = feat_df.std(numeric_only=True)
    good    = feat_df.columns[
        (nan_pct < max_nan_pct) & (std_val > min_std)
    ].tolist()
    return good[:top_n]


def clean_feature(series: pd.Series) -> np.ndarray:
    """Fill NaNs with linear interpolation + ffill/bfill, return numpy array."""
    s = series.interpolate(method="linear").ffill().bfill()
    return s.to_numpy(dtype=float)


# ── Synthetic semiconductor-like data generator ───────────────────────────────

def generate_synthetic_data(
    n: int = 300,
    seed: int = 42,
    inject_faults: bool = True,
) -> pd.DataFrame:
    """
    Generate realistic synthetic semiconductor process parameter data.
    Includes optional injected faults to trigger various WECO rules.
    """
    rng = np.random.default_rng(seed)

    timestamps = pd.date_range("2025-01-01", periods=n, freq="2h")

    # ── Base process parameters ───────────────────────────────────────────────
    # CVD Film Thickness (Å) – target 500, σ ≈ 8
    thickness = 500 + rng.normal(0, 8, n)

    # Etch Rate (Å/min) – target 1200, σ ≈ 15
    etch_rate = 1200 + rng.normal(0, 15, n)

    # Chamber Pressure (mTorr) – target 40, σ ≈ 1.2
    pressure = 40 + rng.normal(0, 1.2, n)

    # RF Power (W) – target 800, σ ≈ 12
    rf_power = 800 + rng.normal(0, 12, n)

    # Temperature (°C) – target 350, σ ≈ 3
    temperature = 350 + rng.normal(0, 3, n)

    # ── Inject specific fault patterns for demo ────────────────────────────────
    if inject_faults:
        # Rule 1 spike on thickness at index 60
        thickness[60] += 32          # > 3σ excursion

        # Rule 2 run (9 points above mean) on etch_rate [80:89]
        etch_rate[80:89] += 25

        # Rule 3 trend (6 increasing points) on pressure [120:126]
        for j, k in enumerate(range(120, 126)):
            pressure[k] += j * 1.5

        # Rule 5 (2-of-3 beyond 2σ) on rf_power [150:153]
        rf_power[150] += 28
        rf_power[151] += 26
        rf_power[152] -= 5

        # Rule 6 (4-of-5 beyond 1σ) on temperature [180:185]
        temperature[180:184] += 9

        # Rule 7 (15 points hugging CL) on thickness [200:215]
        thickness[200:215] = thickness[200:215] * 0.05 + 500

        # General drift in pressure from index 230 onward (chamber aging)
        pressure[230:] += np.linspace(0, 4, n - 230)

    df = pd.DataFrame({
        "timestamp":   timestamps,
        "Film_Thickness_A":   thickness,
        "Etch_Rate_A_min":    etch_rate,
        "Chamber_Pressure_mTorr": pressure,
        "RF_Power_W":         rf_power,
        "Temperature_C":      temperature,
    })

    return df


# ── Spec limit presets for synthetic parameters ───────────────────────────────
SYNTHETIC_SPECS = {
    "Film_Thickness_A":       {"usl": 530, "lsl": 470},
    "Etch_Rate_A_min":        {"usl": 1260, "lsl": 1140},
    "Chamber_Pressure_mTorr": {"usl": 43.5, "lsl": 36.5},
    "RF_Power_W":             {"usl": 850, "lsl": 750},
    "Temperature_C":          {"usl": 362, "lsl": 338},
}
