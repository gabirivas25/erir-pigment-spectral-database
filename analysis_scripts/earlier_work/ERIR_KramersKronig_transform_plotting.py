import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

DATA_DIR = Path("/home/claude/aragonite/Aragonite_DPT")
OUT_DIR = Path("/mnt/user-data/outputs/Aragonite_ERIR_KK_vs_ATR")
OUT_DIR.mkdir(parents=True, exist_ok=True)

MINERAL = "Aragonite"
ATR_FILE = DATA_DIR / f"{MINERAL}_ATR.dpt"

# ---------------------------------------------------------------
# Kramers-Kronig phase retrieval for specular reflectance spectra
# ---------------------------------------------------------------
def kk_phase_retrieval(nu_meas, R_meas, pad_low_to=5.0, pad_high_to=8000.0, pad_step=10.0):
    """
    nu_meas: wavenumbers (ascending), R_meas: reflectance (0-1, normalized)
    Returns theta (phase, same length/order as nu_meas)
    Uses constant-value extrapolation beyond the measured range to reduce
    truncation error in the KK integral (standard practical approximation).
    """
    order = np.argsort(nu_meas)
    nu_meas = nu_meas[order]
    R_meas = R_meas[order]

    # constant-value padding below and above the measured window
    pad_low_nu = np.arange(pad_low_to, nu_meas[0], pad_step)
    pad_high_nu = np.arange(nu_meas[-1] + pad_step, pad_high_to, pad_step)
    pad_low_R = np.full(pad_low_nu.shape, R_meas[0])
    pad_high_R = np.full(pad_high_nu.shape, R_meas[-1])

    nu_full = np.concatenate([pad_low_nu, nu_meas, pad_high_nu])
    R_full = np.concatenate([pad_low_R, R_meas, pad_high_R])
    lnR_full = np.log(np.clip(R_full, 1e-6, None))

    start_idx = len(pad_low_nu)  # index of nu_meas[0] within nu_full
    theta = np.zeros_like(nu_meas)

    for j in range(len(nu_meas)):
        idx = start_idx + j
        nu_j = nu_meas[j]
        lnR_j = lnR_full[idx]
        diff = lnR_full - lnR_j
        denom = nu_full**2 - nu_j**2
        denom[idx] = 1.0   # placeholder to avoid /0, numerator is 0 there anyway
        integrand = diff / denom
        integrand[idx] = 0.0
        theta[j] = (2.0 * nu_j / np.pi) * np.trapezoid(integrand, nu_full)

    return theta, order


def compute_nk(R, theta):
    sqrtR = np.sqrt(R)
    denom = 1 + R - 2 * sqrtR * np.cos(theta)
    n = (1 - R) / denom
    k = (-2 * sqrtR * np.sin(theta)) / denom
    return n, k


def load_dpt(path):
    data = np.loadtxt(path)
    return data[:, 0], data[:, 1]


# Load ATR standard
atr_wn, atr_val = load_dpt(ATR_FILE)

scan_files = sorted(
    [f for f in DATA_DIR.glob(f"{MINERAL}_*.dpt") if f.name != ATR_FILE.name],
    key=lambda p: p.name
)

print(f"Found {len(scan_files)} scan files. Running K-K transform...")

for scan_path in scan_files:
    wn, val = load_dpt(scan_path)
    scan_name = scan_path.stem

    # sort ascending for KK math, normalize into (0,1] since raw values exceed 1
    order = np.argsort(wn)
    wn_s = wn[order]
    R_s = val[order] / val[order].max()
    R_s = np.clip(R_s, 1e-6, 1.0)

    theta, _ = kk_phase_retrieval(wn_s, R_s)
    n, k = compute_nk(R_s, theta)

    # re-order back to original (descending) wavenumber for plotting consistency
    plot_wn = wn_s
    plot_k = k

    fig, ax1 = plt.subplots(figsize=(9, 5.5))

    color1 = "#c0392b"
    ax1.set_xlabel("Wavenumber (cm$^{-1}$)")
    ax1.set_ylabel("K-K derived absorption index, k (a.u.)", color=color1)
    l1, = ax1.plot(plot_wn, plot_k, color=color1, linewidth=1.1, label=f"{scan_name} (ER-IR, K-K transformed)")
    ax1.tick_params(axis="y", labelcolor=color1)
    ax1.invert_xaxis()

    ax2 = ax1.twinx()
    color2 = "#2471a3"
    ax2.set_ylabel("ATR Absorbance (a.u.)", color=color2)
    l2, = ax2.plot(atr_wn, atr_val, color=color2, linewidth=1.1, alpha=0.85, label=f"{MINERAL}_ATR (standard)")
    ax2.tick_params(axis="y", labelcolor=color2)

    ax1.set_title(f"{scan_name} — K-K transformed ER-IR vs. {MINERAL} ATR standard")
    ax1.grid(alpha=0.25)

    lines = [l1, l2]
    ax1.legend(lines, [l.get_label() for l in lines], loc="upper right", fontsize=9)

    fig.tight_layout()
    out_path = OUT_DIR / f"{scan_name}_KK_vs_ATR.png"
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"  done: {scan_name}")

print(f"Saved {len(scan_files)} K-K figures to {OUT_DIR}")
