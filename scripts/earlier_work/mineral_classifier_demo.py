"""
Proof-of-concept: classify mineral identity directly from a raw ER-IR scan.

Key design choices (documented inline because they matter for defensibility):
1. Each mineral was scanned as TWO physical samples, each measured at multiple
   spots. Scans from the same physical sample are correlated (same surface,
   same alignment quirks) -- so train/test splits must keep all scans from one
   sample together, or the model "cheats" by recognizing the sample rather
   than the mineral. We use GroupKFold grouped by (mineral, sample_id).
2. Preprocessing: Standard Normal Variate (SNV) -- subtract each spectrum's
   own mean and divide by its own std. This is a standard, published
   chemometric preprocessing step (unlike the per-max normalization we used,
   and rejected, for the K-K attempt). SNV corrects for overall scan-to-scan
   intensity offsets while preserving relative peak shape, which is exactly
   the kind of correction that's defensible here.
3. Every spectrum is resampled onto one common wavenumber grid so that all
   minerals can be compared feature-by-feature, since raw scans may not share
   identical wavenumber sampling across different acquisition sessions.
"""

import re
import numpy as np
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GroupKFold, cross_val_predict
from sklearn.metrics import classification_report, confusion_matrix
import matplotlib.pyplot as plt

DATA_ROOT = Path("/home/claude")

MINERAL_DIRS = {
    "Aragonite": DATA_ROOT / "aragonite/Aragonite_DPT",
    "Azurite": DATA_ROOT / "minerals/Azurite_DPT/Azurite_DPT",
    "Calcite": DATA_ROOT / "minerals/Calcite_DPT/Calcite_DPT",
    "Cerussite": DATA_ROOT / "minerals/Cerussite_DPT/Cerussite_DPT",
    "Dolemite": DATA_ROOT / "minerals/Dolemite_DPT/Dolemite_DPT",
    "Malachite": DATA_ROOT / "minerals/Malachite_DPT/Malachite_DPT",
    "Goethite": DATA_ROOT / "minerals/Goethite_DPT/Goethite_DPT",
    "Hematite": DATA_ROOT / "minerals/Hematite_DPT/Hematite_DPT",
    "Magnetite": DATA_ROOT / "minerals/Magnetite_DPT/Magnetite_DPT",
    "Lazurite": DATA_ROOT / "minerals/Lazurite_DPT/Lazurite_DPT",
    "Cinnabar": DATA_ROOT / "minerals/Cinnabar_DPT/Cinnabar_DPT",
    "Orpiment": DATA_ROOT / "minerals/Orpiment_DPT/Orpiment_DPT",
}

FNAME_PATTERN = re.compile(r"^([A-Za-z]+)_(\d+)_(\d+)")
COMMON_GRID = np.linspace(650, 3990, 800)  # cm-1, covers the shared measured range


def load_dpt(path):
    data = np.loadtxt(path)
    return data[:, 0], data[:, 1]


def snv(spectrum):
    return (spectrum - spectrum.mean()) / spectrum.std()


X, y, groups, labels_for_plot = [], [], [], []

for mineral, folder in MINERAL_DIRS.items():
    scan_files = sorted(folder.glob(f"{mineral}_*.dpt"))
    for f in scan_files:
        if "ATR" in f.name.upper() or f.stat().st_size == 0:
            continue
        m = FNAME_PATTERN.match(f.name)
        if not m:
            continue
        sample_id = m.group(2)
        wn, val = load_dpt(f)
        order = np.argsort(wn)
        wn_s, val_s = wn[order], val[order]
        # resample onto the common grid, clipping to the overlap range
        val_interp = np.interp(COMMON_GRID, wn_s, val_s, left=np.nan, right=np.nan)
        if np.isnan(val_interp).any():
            continue  # scan didn't cover the full common range
        X.append(snv(val_interp))
        y.append(mineral)
        groups.append(f"{mineral}_{sample_id}")

X = np.array(X)
y = np.array(y)
groups = np.array(groups)

print(f"Total usable scans: {len(y)}")
print(f"Classes: {sorted(set(y))}")
print(f"Unique (mineral, sample) groups: {len(set(groups))}")

# GroupKFold: scans from the same physical sample never split across train/test
n_splits = 2  # capped by minerals with only 2 groups (e.g. two samples each)
gkf = GroupKFold(n_splits=n_splits)

clf = RandomForestClassifier(n_estimators=300, random_state=42)
y_pred = cross_val_predict(clf, X, y, cv=gkf, groups=groups)

print("\n=== Classification report (grouped cross-validation) ===")
print(classification_report(y, y_pred, zero_division=0))

# Confusion matrix
labels_sorted = sorted(set(y))
cm = confusion_matrix(y, y_pred, labels=labels_sorted)

fig, ax = plt.subplots(figsize=(8, 7))
im = ax.imshow(cm, cmap="Reds")
ax.set_xticks(range(len(labels_sorted)))
ax.set_yticks(range(len(labels_sorted)))
ax.set_xticklabels(labels_sorted, rotation=45, ha="right")
ax.set_yticklabels(labels_sorted)
ax.set_xlabel("Predicted mineral")
ax.set_ylabel("True mineral")
ax.set_title("Confusion Matrix — ER-IR Mineral Classifier\n(GroupKFold, sample-level held out)")
for i in range(len(labels_sorted)):
    for j in range(len(labels_sorted)):
        ax.text(j, i, cm[i, j], ha="center", va="center",
                 color="white" if cm[i, j] > cm.max() / 2 else "black", fontsize=8)
fig.colorbar(im, ax=ax, shrink=0.8)
fig.tight_layout()
fig.savefig("/mnt/user-data/outputs/mineral_classifier_confusion_matrix.png", dpi=150)
print("\nSaved confusion matrix plot.")
