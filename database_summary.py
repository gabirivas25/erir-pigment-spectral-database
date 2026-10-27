#!/usr/bin/env python3
"""Show what is in the database (works the same on Mac and Windows; read-only).

Usage:  python3 database_summary.py      (on Windows:  py database_summary.py)
"""
import os, sqlite3, sys

here = os.path.dirname(os.path.abspath(__file__))
db = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, "pigment_spectral_standards.db")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
con = sqlite3.connect(db)

print("Materials")
for name, formula, synth in con.execute(
        "SELECT MaterialName, ChemicalFormula, IsSynthetic FROM Material ORDER BY MaterialName"):
    print("  %-24s %-34s %s" % (name, formula or "", "synthetic" if synth == "Y" else "natural"))

print("\nScans by acquisition mode")
for mode, n in con.execute(
        """SELECT c.AcquisitionMode, COUNT(*) FROM Measurement m
           JOIN InstrumentConfiguration c ON c.InstrumentConfigurationID = m.InstrumentConfigurationID
           GROUP BY c.AcquisitionMode"""):
    print("  %-8s %d" % (mode, n))
print("\nTotal scans:", con.execute("SELECT COUNT(*) FROM Measurement").fetchone()[0])
