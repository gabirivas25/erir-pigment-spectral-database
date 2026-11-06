#!/usr/bin/env python3
"""How much do the tav (unknown) results change with different peak settings?
Peak-position method only. Baseline = prominence 0.5, spacing 20 cm-1, tolerance 8 cm-1 (match_unknown.py).
Each tav_2, tav_5, tav_8 scan (15) is matched against all ER-IR standards. No correct answer is assumed;
the script counts how many scans change their top material and their top-three materials against the baseline.
Ties: materials with equal scores are ordered by the standards' order (stable).
Usage: python3 -I tav_peak_settings.py DATABASE 'TAV_GLOB'"""
import glob, itertools, json, os, re, sqlite3, sys
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
print("tav scans:", len(tav), "standards:", len(std))
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
        out.append(sorted(best, key=lambda m: -best[m])[:3])
    return out
BASE = (0.5, 20, 8); base = top3(*BASE)
print("\nBaseline (prom 0.5, spacing 20, tol 8) top three per scan:")
for n, b in zip(names, base): print("  %-22s %s" % (n, ", ".join(b)))
def compare(cfg):
    r = top3(*cfg)
    return (sum(a[0] != b[0] for a, b in zip(base, r)), sum(set(a) != set(b) for a, b in zip(base, r)), sum(a != b for a, b in zip(base, r)))
print("\nOne setting changed at a time (scans out of 15 that differ from the baseline):")
print("%-34s %9s %12s %13s" % ("setting", "top-1", "top-3 set", "top-3 order"))
for p in (0.25, 0.5, 1.0, 1.5):
    for d in (10, 20, 30, 40):
        for t in (4, 8, 12, 16):
            if (p != 0.5) + (d != 20) + (t != 8) > 1: continue
            if (p, d, t) == BASE: continue
            c = compare((p, d, t)); print("prom %.2f spacing %2d tol %2d        %9d %12d %13d" % (p, d, t, *c), flush=True)
allc = [compare(c) for c in itertools.product((0.25, 0.5, 1.0, 1.5), (10, 20, 30, 40), (4, 8, 12, 16)) if c != BASE]
a = np.array(allc)
print("\nAll 63 other combinations of prominence {0.25,0.5,1.0,1.5} x spacing {10,20,30,40} x tolerance {4,8,12,16}:")
for k, nm in enumerate(("top-1 changed", "top-3 set changed", "top-3 order changed")):
    print("  %-20s median %.0f  min %d  max %d scans of 15" % (nm, np.median(a[:, k]), a[:, k].min(), a[:, k].max()))
