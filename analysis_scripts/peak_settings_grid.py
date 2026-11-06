#!/usr/bin/env python3
"""Grid search of the peak-matching settings (prominence, minimum spacing, tolerance).
Tune on Test A (leave-one-specimen-out, 221 scans, synthetic malachite = 2nd malachite specimen).
Check on Test B (leave-one-scan-out, 67 scans of the 7 single-specimen materials, different materials).
Same grid, SNV and scoring as match_unknown.py. A material's score is its best scan's score.
Ties: stable (order of the standards), against the correct material, in favour of it.
Usage: python3 -I peak_settings_grid.py DATABASE"""
import itertools, json, sqlite3, sys
import numpy as np
from scipy.signal import find_peaks

con = sqlite3.connect(sys.argv[1])
GRID = np.linspace(650.0, 3990.0, 800); STEP = GRID[1] - GRID[0]
rows = con.execute("""SELECT m.MeasurementID, m.SpecimenID, mat.MaterialName, m.SpectrumData
  FROM Measurement m JOIN Specimen s USING(SpecimenID) JOIN Material mat USING(MaterialID)
  JOIN InstrumentConfiguration c USING(InstrumentConfigurationID)
  WHERE c.AcquisitionMode='ER-IR' ORDER BY m.MeasurementID""").fetchall()
spec, mat, snv_spec = [], [], []
for mid, sid, mn, js in rows:
    d = np.array(json.loads(js)); d = d[np.argsort(d[:, 0])]
    y = np.interp(GRID, d[:, 0], d[:, 1])
    spec.append(sid); mat.append("Malachite" if mn == "Synthetic malachite" else mn); snv_spec.append((y - y.mean()) / y.std())
spec = np.array(spec); mat = np.array(mat); n = len(spec)
nspec = {m: len(set(spec[mat == m])) for m in set(mat)}
A = [i for i in range(n) if nspec[mat[i]] > 1]
B = [i for i in range(n) if nspec[mat[i]] == 1]
print("Test A scans:", len(A), "Test B scans:", len(B), flush=True)

def pscore(pu, ps, tol):
    if len(pu) + len(ps) == 0: return 0.0
    used, k = set(), 0
    for u in pu:
        best, bd = None, tol + 1
        for j, s in enumerate(ps):
            dd = abs(u - s)
            if j not in used and dd <= tol and dd < bd: best, bd = j, dd
        if best is not None: used.add(best); k += 1
    return 2.0 * k / (len(pu) + len(ps))

def ranks(S, idx, excl):
    out = {"stable": [], "against": [], "favor": []}
    for i in idx:
        best = {}
        for j in range(n):
            if excl(i, j): continue
            if mat[j] not in best or S[i][j] > best[mat[j]]: best[mat[j]] = S[i][j]
        t = best[mat[i]]
        order = sorted(best, key=lambda m: -best[m])
        out["stable"].append(order.index(mat[i]) + 1)
        out["against"].append(1 + sum(1 for m, v in best.items() if m != mat[i] and v >= t))
        out["favor"].append(1 + sum(1 for m, v in best.items() if m != mat[i] and v > t))
    return {k: (sum(r == 1 for r in v), sum(r <= 3 for r in v)) for k, v in out.items()}

PROM = [0.25, 0.5, 1.0, 1.5]; DIST = [10, 20, 30, 40]; TOL = [4, 8, 12, 16]
res = []
for prom, dist in itertools.product(PROM, DIST):
    PK = [GRID[find_peaks(a, prominence=prom, distance=max(1, int(round(dist / STEP))))[0]] for a in snv_spec]
    npk = np.mean([len(p) for p in PK])
    for tol in TOL:
        S = {i: [pscore(PK[i], PK[j], tol) for j in range(n)] for i in set(A) | set(B)}
        ra = ranks(S, A, lambda i, j: spec[j] == spec[i])
        rb = ranks(S, B, lambda i, j: j == i)
        res.append(dict(prom=prom, dist=dist, tol=tol, mean_peaks=round(float(npk), 1), A=ra, B=rb))
        print("prom %.2f dist %2d tol %2d peaks/scan %5.1f | A first %3d (%3d..%3d) top3 %3d | B first %2d (%2d..%2d) top3 %2d" % (
            prom, dist, tol, npk, ra["stable"][0], ra["against"][0], ra["favor"][0], ra["stable"][1],
            rb["stable"][0], rb["against"][0], rb["favor"][0], rb["stable"][1]), flush=True)
json.dump({"nA": len(A), "nB": len(B), "rows": res}, open("peak_settings_grid.json", "w"), indent=1)
