#!/usr/bin/env python3
"""Tie sensitivity of the Table 3.2 variants. Same as table32_rerun.py, but each variant is scored three ways: ties resolved by standard order (as before), ties in favour of the correct material, ties against it.
Re-run of the Table 3.2 variants on the current database.
Leave-one-specimen-out. Unknowns: ER-IR scans of materials with at least two specimens, where synthetic
malachite counts as the second specimen of Malachite (as in the thesis text). Standards: all ER-IR scans of other specimens.
A material's score is its best scan's score. Ties are resolved by the order of the standards (stable sort)."""
import json, sqlite3, sys
import numpy as np
from scipy.signal import savgol_filter, find_peaks
from scipy.stats import rankdata

DB = sys.argv[1]
GRID = np.linspace(650.0, 3990.0, 800); STEP = GRID[1] - GRID[0]
con = sqlite3.connect(DB)
rows = con.execute("""SELECT m.MeasurementID, m.SpecimenID, mat.MaterialName, m.SpectrumData
  FROM Measurement m JOIN Specimen s USING(SpecimenID) JOIN Material mat USING(MaterialID)
  JOIN InstrumentConfiguration c USING(InstrumentConfigurationID)
  WHERE c.AcquisitionMode='ER-IR' ORDER BY m.MeasurementID""").fetchall()
spec, mat, raw = [], [], []
for mid, sid, mn, js in rows:
    d = np.array(json.loads(js)); d = d[np.argsort(d[:, 0])]
    spec.append(sid); mat.append("Malachite" if mn == "Synthetic malachite" else mn); raw.append(np.interp(GRID, d[:, 0], d[:, 1]))
spec = np.array(spec); mat = np.array(mat); raw = np.array(raw)
nspec = {m: len(set(spec[mat == m])) for m in set(mat)}
U = [i for i in range(len(raw)) if nspec[mat[i]] > 1]
print("testable scans:", len(U), "materials:", len(set(mat[U])))

def snv(a): return (a - a.mean()) / a.std()
def sg(y, w, o=2, d=0): return savgol_filter(y, w, o, deriv=d)

def poly_baseline(y, order=3, it=100):
    x = np.linspace(-1, 1, len(y)); z = y.copy()
    for _ in range(it):
        fit = np.polyval(np.polyfit(x, z, order), x)
        z = np.minimum(z, fit)
    return np.polyval(np.polyfit(x, z, order), x)

def region(lo, hi, excl=None):
    m = (GRID >= lo) & (GRID <= hi)
    if excl: m &= ~((GRID >= excl[0]) & (GRID <= excl[1]))
    return m

def vec_pearson(y, m): return snv(y[m])
def vec_deriv(w, d=1):
    return lambda y, m: snv(sg(y, w, 2, d)[m])
def vec_pipeline(y, m):
    return snv(sg(y - poly_baseline(y), 11, 2)[m])

def peaks_of(a, g):
    p, _ = find_peaks(a, prominence=0.5, distance=max(1, int(round(20 / STEP))))
    return g[p]
def pscore(pu, ps, tol=8.0):
    if len(pu) + len(ps) == 0: return 0.0
    used, k = set(), 0
    for u in pu:
        best, bd = None, tol + 1
        for j, s in enumerate(ps):
            dd = abs(u - s)
            if j not in used and dd <= tol and dd < bd: best, bd = j, dd
        if best is not None: used.add(best); k += 1
    return 2.0 * k / (len(pu) + len(ps))

def score_matrix_corr(vecfn, m):
    X = np.array([vecfn(y, m) for y in raw]); return (X @ X.T) / X.shape[1]
def score_matrix_peaks(m, smooth=None):
    g = GRID[m]
    PK = [peaks_of(snv((sg(y, smooth) if smooth else y)[m]), g) for y in raw]
    n = len(raw); S = np.zeros((n, n))
    for i in U:
        for j in range(n): S[i, j] = pscore(PK[i], PK[j])
    return S

def material_scores(S, i):
    best = {}
    for j in range(len(raw)):
        if spec[j] == spec[i]: continue
        if mat[j] not in best or S[i, j] > best[mat[j]]: best[mat[j]] = S[i, j]
    return best
def ranks3(sc, truth):
    """rank of the true material: (as in table32_rerun, optimistic, pessimistic)"""
    order = sorted(sc, key=lambda m: -sc[m]); stable = order.index(truth) + 1
    t = sc[truth]
    opt = 1 + sum(1 for m in sc if m != truth and sc[m] > t)
    pes = 1 + sum(1 for m in sc if m != truth and sc[m] >= t)
    return stable, opt, pes
def summarize(rr):
    out = []
    for k in range(3):
        out.append((sum(r[k] == 1 for r in rr), sum(r[k] <= 3 for r in rr)))
    return out
def evaluate(S):
    return summarize([ranks3(material_scores(S, i), mat[i]) for i in U])
def combo(Ss):
    rr = []
    for i in U:
        per = [material_scores(S, i) for S in Ss]
        mats = list(per[0])
        ranks = [dict(zip(sorted(p, key=lambda m: -p[m]), range(1, len(p) + 1))) for p in per]
        tot = {m: -sum(rk[m] for rk in ranks) for m in mats}   # negate: higher is better
        rr.append(ranks3(tot, mat[i]))
    return summarize(rr)

FULL = region(650, 3990)
res = []
def show(name, r):
    res.append((name, r)); print("%-50s first: stable %3d  ties-favor %3d  ties-against %3d | top3: stable %3d  favor %3d  against %3d" % (name, r[0][0], r[1][0], r[2][0], r[0][1], r[1][1], r[2][1]), flush=True)
def add(name, S): show(name, evaluate(S))
def addc(name, Ss): show(name, combo(Ss))

S_d = score_matrix_corr(vec_deriv(11), FULL)
S_p = score_matrix_corr(vec_pearson, FULL)
S_k = score_matrix_peaks(FULL)
add("First derivative, window 11 (current)", S_d)
add("Pearson (current)", S_p)
add("Peak position (current)", S_k)
for lo, hi in ((650, 1800), (650, 1500), (650, 2000)):
    add("Pearson, %d to %d cm-1" % (lo, hi), score_matrix_corr(vec_pearson, region(lo, hi)))
add("First derivative, 650 to 1800 cm-1", score_matrix_corr(vec_deriv(11), region(650, 1800)))
add("First derivative, CO2 region (2250-2450) removed", score_matrix_corr(vec_deriv(11), region(650, 3990, (2250, 2450))))
add("Peak position, 650 to 1800 cm-1", score_matrix_peaks(region(650, 1800)))
add("Second derivative, window 11", score_matrix_corr(vec_deriv(11, 2), FULL))
add("Second derivative, window 21", score_matrix_corr(vec_deriv(21, 2), FULL))
add("First derivative, window 15", score_matrix_corr(vec_deriv(15), FULL))
add("First derivative, window 21", score_matrix_corr(vec_deriv(21), FULL))
add("Peak position after smoothing, window 11", score_matrix_peaks(FULL, 11))
add("Peak position after smoothing, window 21", score_matrix_peaks(FULL, 21))
add("General pipeline with Pearson", score_matrix_corr(vec_pipeline, FULL))
addc("Rank combination of the three methods", [S_d, S_p, S_k])
addc("Rank combination of derivative and peaks", [S_d, S_k])
json.dump({"n": len(U), "rows": res}, open("tie_sensitivity.json", "w"), indent=1)
