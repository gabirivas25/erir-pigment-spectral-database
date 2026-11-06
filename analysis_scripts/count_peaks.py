import json, sqlite3, sys
import numpy as np
from scipy.signal import find_peaks
con = sqlite3.connect(sys.argv[1])
G = np.linspace(650, 3990, 800); STEP = G[1]-G[0]
rows = con.execute("""SELECT m.MeasurementID, c.AcquisitionMode, m.SpectrumData FROM Measurement m
 JOIN InstrumentConfiguration c USING(InstrumentConfigurationID)""").fetchall()
cnt = {"ER-IR": [], "ATR": []}
for mid, mode, js in rows:
    d = np.array(json.loads(js)); d = d[np.argsort(d[:,0])]
    y = np.interp(G, d[:,0], d[:,1]); y = (y-y.mean())/y.std()
    p,_ = find_peaks(y, prominence=0.5, distance=max(1,int(round(20/STEP))))
    cnt[mode].append(len(p))
tot = 0
for k,v in cnt.items():
    v = np.array(v); tot += v.sum()
    print(k, "measurements", len(v), "peaks", int(v.sum()), "mean %.1f min %d max %d" % (v.mean(), v.min(), v.max()))
print("total rows", int(tot))
