#!/usr/bin/env python3
"""Re-run of the Table 3.2 variants on the current database.
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
def rank_of_truth(sc, truth):
    order = sorted(sc, key=lambda m: -sc[m]); return order.index(truth) + 1
def evaluate(S):
    r = [rank_of_truth(material_scores(S, i), mat[i]) for i in U]
    return sum(x == 1 for x in r), sum(x <= 3 for x in r)
def combo(Ss):
    r = []
    for i in U:
        per = [material_scores(S, i) for S in Ss]
        mats = list(per[0])
        ranks = [dict(zip(sorted(p, key=lambda m: -p[m]), range(1, len(p) + 1))) for p in per]
        tot = {m: sum(rk[m] for rk in ranks) for m in mats}
        order = sorted(mats, key=lambda m: tot[m]); r.append(order.index(mat[i]) + 1)
    return sum(x == 1 for x in r), sum(x <= 3 for x in r)


# ---- per-material results for Test A (221 scans), full range, three methods ----
from collections import Counter, defaultdict
FULL = region(650, 3990)
S = {"Pearson": score_matrix_corr(vec_pearson, FULL), "First derivative": score_matrix_corr(vec_deriv(11), FULL), "Peak position": score_matrix_peaks(FULL)}
mats = sorted(set(mat[U]))
print("\nPer material, Test A (leave-one-specimen-out), full range. Cells: first / top three, of N scans.")
print("%-22s %4s  %-14s %-14s %-14s" % ("Material", "N", "Pearson", "Derivative", "Peaks"))
conf = {k: defaultdict(Counter) for k in S}
for m in mats:
    idx = [i for i in U if mat[i] == m]
    cells = []
    for k, SM in S.items():
        f = t = 0
        for i in idx:
            sc = material_scores(SM, i)
            order = sorted(sc, key=lambda x: -sc[x])
            r = order.index(m) + 1
            f += r == 1; t += r <= 3
            if r != 1: conf[k][m][order[0]] += 1
        cells.append("%d / %d" % (f, t))
    print("%-22s %4d  %-14s %-14s %-14s" % (m, len(idx), *cells))
print("\nWhat the first derivative put first when the correct material was not first:")
for m in mats:
    if conf["First derivative"][m]:
        print("  %-20s -> %s" % (m, ", ".join("%s %d" % kv for kv in conf["First derivative"][m].most_common())))
print("\nPeak position, same:")
for m in mats:
    if conf["Peak position"][m]:
        print("  %-20s -> %s" % (m, ", ".join("%s %d" % kv for kv in conf["Peak position"][m].most_common())))

print("\nCinnabar scans (leave-one-specimen-out): rank of Vermilion and of Cinnabar, first derivative / Pearson / peaks")
for k, SM in S.items():
    rv, rc = [], []
    for i in [i for i in U if mat[i] == "Cinnabar"]:
        sc = material_scores(SM, i); order = sorted(sc, key=lambda x: -sc[x])
        rv.append(order.index("Vermilion") + 1); rc.append(order.index("Cinnabar") + 1)
    print("%-17s Vermilion ranks: %s | Cinnabar ranks: %s | Vermilion first in %d, Vermilion in top 3 in %d of %d" %
          (k, sorted(rv), sorted(rc), sum(r == 1 for r in rv), sum(r <= 3 for r in rv), len(rv)))
