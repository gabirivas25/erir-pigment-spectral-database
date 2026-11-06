#!/usr/bin/env python3
"""Run chosen peak settings on the 15 tav scans and compare with the original settings.
Settings tested: original (prominence 0.5, spacing 20, tolerance 8) and the combinations that scored highest on the standards.
Usage: python3 -I tav_selected_settings.py DATABASE 'TAV_GLOB'"""
import glob, json, os, re, sqlite3, sys
import numpy as np
from scipy.signal import find_peaks
con = sqlite3.connect(sys.argv[1])
GRID = np.linspace(650.0, 3990.0, 800); STEP = GRID[1] - GRID[0]
def snv_on_grid(d):
    d = d[np.argsort(d[:, 0])]; y = np.interp(GRID, d[:, 0], d[:, 1]); return (y - y.mean()) / y.std()
rows = con.execute("""SELECT m.MeasurementID, mat.MaterialName, m.SpectrumData FROM Measurement m
  JOIN Specimen s USING(SpecimenID) JOIN Material mat USING(MaterialID)
  JOIN InstrumentConfiguration c USING(InstrumentConfigurationID) WHERE c.AcquisitionMode='ER-IR' ORDER BY m.MeasurementID""").fetchall()
std_mat = [r[1] for r in rows]; std = [snv_on_grid(np.array(json.loads(r[2]))) for r in rows]
files = sorted(f for f in glob.glob(sys.argv[2]) if re.search(r"tav_[258]_", f))
names = [re.sub(r"^[0-9a-f]+-", "", os.path.basename(f)).replace(".0.dpt", "") for f in files]
tav = [snv_on_grid(np.loadtxt(f)) for f in files]
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
def pk(a, prom, dist): return GRID[find_peaks(a, prominence=prom, distance=max(1, int(round(dist / STEP))))[0]]
def top3(prom, dist, tol):
    PS = [pk(a, prom, dist) for a in std]; out = []
    for t in tav:
        pt = pk(t, prom, dist); best = {}
        for m, ps in zip(std_mat, PS):
            s = pscore(pt, ps, tol)
            if m not in best or s > best[m]: best[m] = s
        out.append([(m, round(best[m], 2)) for m in sorted(best, key=lambda m: -best[m])[:3]])
    return out
CFG = [("original 0.5/20/8", (0.5, 20, 8)), ("0.5/10/12", (0.5, 10, 12)), ("0.25/10/12", (0.25, 10, 12)), ("0.25/10/8", (0.25, 10, 8))]
R = {n: top3(*c) for n, c in CFG}
for i, nm in enumerate(names):
    print(nm)
    for n, _ in CFG: print("   %-18s %s" % (n, "; ".join("%s %.2f" % t for t in R[n][i])))
base = R[CFG[0][0]]
print("\nScans (of 15) that differ from the original settings:")
for n, _ in CFG[1:]:
    r = R[n]
    print("  %-12s top material changed %2d, top-three set changed %2d, top-three order changed %2d" % (
        n, sum(a[0][0] != b[0][0] for a, b in zip(base, r)), sum({x[0] for x in a} != {x[0] for x in b} for a, b in zip(base, r)),
        sum([x[0] for x in a] != [x[0] for x in b] for a, b in zip(base, r))))
