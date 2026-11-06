#!/usr/bin/env python3
"""Does starting the grid at 600 cm-1 instead of 650 change the matches?
Same pipeline as match_unknown.py (SNV, Savitzky-Golay 11/2 derivative, peaks prominence 0.5,
distance 20 cm-1, tolerance 8 cm-1). Same grid step; the 600 grid only adds 12 points at the low end.
Synthetic malachite is pooled with Malachite, as in Table 3.2 and Test B (221 and 67 scans).
Test A: leave-one-specimen-out. Test B: leave-one-scan-out on single-specimen materials. Tav: 15 scans."""
import glob, json, os, re, sqlite3, sys
import numpy as np
from math import comb
from scipy.signal import savgol_filter, find_peaks

DB, TAVGLOB = sys.argv[1], sys.argv[2]
G650 = np.linspace(650.0, 3990.0, 800)
STEP = G650[1] - G650[0]
G600 = np.concatenate([G650[0] - STEP * np.arange(12, 0, -1), G650])
print("grid 650: %.2f-%.2f (%d pts); grid 600: %.2f-%.2f (%d pts); step %.4f" %
      (G650[0], G650[-1], len(G650), G600[0], G600[-1], len(G600), STEP))

def snv(a): return (a - a.mean()) / a.std()
def peaks_of(a, g):
    p, _ = find_peaks(a, prominence=0.5, distance=max(1, int(round(20 / STEP))))
    return g[p]
def pscore(pu, ps, tol=8.0):
    if len(pu) + len(ps) == 0: return 0.0
    used, m = set(), 0
    for u in pu:
        best, bd = None, tol + 1
        for j, s in enumerate(ps):
            d = abs(u - s)
            if j not in used and d <= tol and d < bd: best, bd = j, d
        if best is not None: used.add(best); m += 1
    return 2.0 * m / (len(pu) + len(ps))

con = sqlite3.connect(DB)
rows = con.execute("""SELECT m.MeasurementID, m.SpecimenID, mat.MaterialName, m.SpectrumData
  FROM Measurement m JOIN Specimen s USING(SpecimenID) JOIN Material mat USING(MaterialID)
  JOIN InstrumentConfiguration c USING(InstrumentConfigurationID)
  WHERE c.AcquisitionMode='ER-IR' ORDER BY m.MeasurementID""").fetchall()
raw = []
for mid, sid, mat, js in rows:
    d = np.array(json.loads(js)); d = d[np.argsort(d[:, 0])]
    raw.append((mid, sid, mat, d))
assert all(r[3][0, 0] <= 600 for r in raw), "a scan starts above 600"
spec = np.array([r[1] for r in raw]); mat_raw = np.array([r[2] for r in raw])
# Tests A and B pool synthetic malachite with Malachite (second specimen); the tav test keeps the matcher's own material names
mat = np.array(["Malachite" if m == "Synthetic malachite" else m for m in mat_raw])
nspec = {m: len(set(spec[mat == m])) for m in set(mat)}

def build(grid, d_list):
    X = {"pearson": [], "deriv": []}; PK = []
    for d in d_list:
        y = np.interp(grid, d[:, 0], d[:, 1])
        X["pearson"].append(snv(y)); X["deriv"].append(snv(savgol_filter(y, 11, 2, deriv=1)))
        PK.append(peaks_of(snv(y), grid))
    return {k: np.array(v) for k, v in X.items()}, PK

def scores(grid, d_list_u, d_list_s):
    """score matrix [unknown, standard] for each method"""
    Xu, Pu = build(grid, d_list_u); Xs, Ps = build(grid, d_list_s)
    S = {k: (Xu[k] @ Xs[k].T) / Xu[k].shape[1] for k in ("pearson", "deriv")}   # SNV: corrcoef = mean(a*b)
    S["peaks"] = np.array([[pscore(a, b) for b in Ps] for a in Pu])
    return S

D = [r[3] for r in raw]
SC = {"650": scores(G650, D, D), "600": scores(G600, D, D)}

def top_rank(row, exclude, truth):
    best = {}
    for j, sc in enumerate(row):
        if exclude[j]: continue
        m = mat[j]
        if m not in best or sc > best[m]: best[m] = sc
    if truth not in best: return None
    order = sorted(best, key=lambda m: -best[m])
    return order.index(truth) + 1

def mcnemar(b, c):
    n = b + c
    if n == 0: return 1.0
    k = min(b, c)
    p = 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, p)

def run(name, idx_unknown, excl_fn):
    print("\n=== %s: %d scans, %d materials ===" % (name, len(idx_unknown), len(set(mat[idx_unknown]))))
    print("%-9s %9s %9s %6s %6s %8s %12s" % ("method", "top1@650", "top1@600", "only650", "only600", "p(McN)", "rank changed"))
    for meth in ("pearson", "deriv", "peaks"):
        r = {}
        for g in ("650", "600"):
            r[g] = [top_rank(SC[g][meth][i], excl_fn(i), mat[i]) for i in idx_unknown]
        keep = [k for k in range(len(idx_unknown)) if r["650"][k] is not None]
        a = np.array([r["650"][k] == 1 for k in keep]); b = np.array([r["600"][k] == 1 for k in keep])
        o650 = int((a & ~b).sum()); o600 = int((~a & b).sum())
        chg = sum(r["650"][k] != r["600"][k] for k in keep)
        print("%-9s %5d/%-3d %5d/%-3d %6d %6d %8.3f %12d" % (meth, a.sum(), len(keep), b.sum(), len(keep), o650, o600,
              mcnemar(o650, o600), chg))

# Test A: leave-one-specimen-out, scans of materials that have more than one specimen
A = [i for i in range(len(raw)) if nspec[mat[i]] > 1]
run("Test A (leave-one-specimen-out)", A, lambda i: spec == spec[i])
# Test B: leave-one-scan-out, scans of single-specimen materials
B = [i for i in range(len(raw)) if nspec[mat[i]] == 1]
run("Test B (leave-one-scan-out)", B, lambda i: np.arange(len(raw)) == i)

# Tav: 15 scans against all standards
files = sorted(f for f in glob.glob(TAVGLOB) if re.search(r"tav_[258]_", f))
TD = []
for f in files:
    d = np.loadtxt(f); TD.append(d[np.argsort(d[:, 0])])
names = [re.sub(r"^[0-9a-f]+-", "", os.path.basename(f)).replace(".0.dpt", "") for f in files]
print("\n=== Tav: %d scans ===" % len(files))
T = {"650": scores(G650, TD, D), "600": scores(G600, TD, D)}
def ranked(row):
    best = {}
    for j, sc in enumerate(row):
        if mat_raw[j] not in best or sc > best[mat_raw[j]]: best[mat_raw[j]] = sc
    return sorted(best, key=lambda m: -best[m])
for meth in ("pearson", "deriv", "peaks"):
    ch1 = ch3set = ch3order = 0; moved = []
    for k, n in enumerate(names):
        a, b = ranked(T["650"][meth][k]), ranked(T["600"][meth][k])
        if a[0] != b[0]: ch1 += 1; moved.append("%s: %s -> %s" % (n, a[0], b[0]))
        if set(a[:3]) != set(b[:3]): ch3set += 1
        if a[:3] != b[:3]: ch3order += 1
    print("%-8s top-1 material changed in %d/15; top-3 materials changed in %d/15 (top-3 order changed in %d/15)" %
          (meth, ch1, ch3set, ch3order))
    for m in moved: print("    ", m)
