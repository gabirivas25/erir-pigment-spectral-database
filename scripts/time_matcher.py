#!/usr/bin/env python3
"""How does the matcher's run time grow with the number of standards?
Builds scratch databases with N ER-IR spectra (copies of the real 288, with new file names), then times one match
the way match_unknown.py does it for a single file: SQL query, JSON parse + resample, then ranking for each method.
Copies are not new materials, so this shows how time grows with size, not whether accuracy holds.
Usage: python3 -I time_matcher.py DATABASE"""
import json, os, sqlite3, sys, tempfile, time
import numpy as np
sys.path.insert(0, "/home/claude/erir-pigment-spectral-database")
import match_unknown as mu
src = sqlite3.connect(sys.argv[1])
rows = src.execute("""SELECT m.FilePath, m.SpectrumData FROM Measurement m JOIN InstrumentConfiguration c
  ON c.InstrumentConfigurationID = m.InstrumentConfigurationID WHERE c.AcquisitionMode='ER-IR' ORDER BY m.FilePath""").fetchall()
print("source ER-IR spectra:", len(rows), flush=True)
unk = None
for sz in (288, 1000, 3000, 10000):
    path = os.path.join(tempfile.mkdtemp(), "t.db")
    c = sqlite3.connect(path)
    c.execute("CREATE TABLE InstrumentConfiguration (InstrumentConfigurationID INTEGER PRIMARY KEY, AcquisitionMode TEXT)")
    c.execute("INSERT INTO InstrumentConfiguration VALUES (1,'ER-IR')")
    c.execute("CREATE TABLE Measurement (MeasurementID INTEGER PRIMARY KEY, InstrumentConfigurationID INT, FilePath TEXT, SpectrumData TEXT)")
    out = []
    for k in range(sz):
        p, d = rows[k % len(rows)]
        base, ext = os.path.splitext(p)
        out.append((1, "%s_%d%s" % (base, k // len(rows), ext) if k >= len(rows) else p, d))
    c.executemany("INSERT INTO Measurement (InstrumentConfigurationID, FilePath, SpectrumData) VALUES (?,?,?)", out)
    c.commit(); c.close()
    con = sqlite3.connect(path)
    t0 = time.perf_counter(); r = con.execute("""SELECT m.FilePath, m.SpectrumData FROM Measurement m
        JOIN InstrumentConfiguration c ON c.InstrumentConfigurationID = m.InstrumentConfigurationID
        WHERE c.AcquisitionMode = 'ER-IR' ORDER BY m.FilePath""").fetchall(); t_sql = time.perf_counter() - t0
    t0 = time.perf_counter(); std = mu.load_standards(path); t_load = time.perf_counter() - t0   # sql + parse + resample
    if unk is None: unk = std[0]["raw"].copy()
    res = {}
    for m in ("pearson", "deriv", "peaks"):
        t0 = time.perf_counter(); mu.rank(unk, std, m); res[m] = time.perf_counter() - t0
    print("N %5d | SQL fetch %6.2fs | load_standards (SQL + JSON parse + resample) %6.2fs | rank pearson %6.2fs deriv %6.2fs peaks %6.2fs | one match total %6.2fs"
          % (len(std), t_sql, t_load, res["pearson"], res["deriv"], res["peaks"], t_load + sum(res.values())), flush=True)
