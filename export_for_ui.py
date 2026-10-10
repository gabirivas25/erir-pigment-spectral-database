#!/usr/bin/env python3
"""
export_for_ui.py: write the data files the web UI loads, from the database.

Usage:
    python3 export_for_ui.py [DATABASE.db] [OUTPUT_FOLDER]
    (defaults: pigment_spectral_standards.db  ui_data)

Run it after every import (see WORKFLOW.md), then republish the UI.
It only reads the database. It never changes it.

Files written to OUTPUT_FOLDER:
    materials.json      one entry per material (name, formula, source, colour, scan counts)
    scans.json          one entry per scan (metadata only, no spectrum)
    match_index.json    every ER-IR spectrum resampled to one common wavenumber grid, for matching
    spectra_er_ir.json  the full spectra of all ER-IR scans (see format below)
    spectra_atr.json    the full spectra of all ATR scans (same format)

Format of spectra_*.json: {"axes": [[wavenumbers...], ...],
    "spectra": {"<scan id>": {"axis": <index into axes>, "intensity": [...]}}}
Scans measured on the same wavenumber axis share one entry in "axes".
"""
import bisect
import json
import os
import re
import sqlite3
import sys

GRID_START, GRID_END, GRID_POINTS = 650.0, 3990.0, 800

# Display colour for each material (file key). Pigment-inspired, chosen for the UI.
COLORS = {
    "aragonite": "#b7894f", "azurite": "#1f5fa8", "calcite": "#6EC1E8",
    "cerussite": "#F4DD7A", "cinnabar": "#9C453B", "dolomite": "#F0937A",
    "goethite": "#E8821E", "hematite": "#756F6A", "lazurite": "#3a2d9a",
    "magnetite": "#3a3a3a", "malachite": "#17704A", "orpiment": "#e0a800",
    "synth_malachite": "#9FE0C0", "synth_ultramarine": "#5b4bd6",
    "synth_verdigris": "#2aa198",
}
FALLBACK_COLOR = "#8a8f94"

NAME_RE = re.compile(r"^(?P<key>.+?)_(?P<mode>ER_IR|ATR)(?:_(?P<rest>[\d_]+))?$", re.I)


def resample(points):
    """Linear interpolation of [[wavenumber, intensity], ...] onto the common grid."""
    pts = sorted(points)
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    step = (GRID_END - GRID_START) / (GRID_POINTS - 1)
    out = []
    for i in range(GRID_POINTS):
        x = GRID_START + i * step
        j = bisect.bisect_left(xs, x)
        if j == 0:
            y = ys[0]
        elif j >= len(xs):
            y = ys[-1]
        else:
            x0, x1, y0, y1 = xs[j - 1], xs[j], ys[j - 1], ys[j]
            y = y0 if x1 == x0 else y0 + (y1 - y0) * (x - x0) / (x1 - x0)
        out.append(round(y, 5))
    return out


def main():
    db = sys.argv[1] if len(sys.argv) > 1 else "pigment_spectral_standards.db"
    out = sys.argv[2] if len(sys.argv) > 2 else "ui_data"
    if not os.path.exists(db):
        sys.exit("Database not found: " + db)
    os.makedirs(out, exist_ok=True)
    bundles = {"ER-IR": {"axes": [], "spectra": {}}, "ATR": {"axes": [], "spectra": {}}}
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row

    rows = con.execute("""
        SELECT m.MeasurementID, m.SpectrumData, m.ScanDate, m.ReferenceMeasurementID,
               m.IntensityMode, amt.ModeName AS Mode, f.FilePath,
               op.Name AS Operator, mat.MaterialName, mat.ChemicalFormula, mat.IsSynthetic,
               mat.Description, src.SourceName,
               ic.Resolution, ic.NumberOfScans, ic.BeamSplitterType, ic.ApertureSize, ic.Notes AS ConfigNotes,
               ins.InstrumentName, ins.Model, ins.Manufacturer, st.TypeName AS SiteName
        FROM Measurement m
        JOIN SpectralFile f ON f.MeasurementID = m.MeasurementID
        JOIN AcquisitionModeType amt ON amt.AcquisitionModeID = m.AcquisitionModeID
        JOIN Specimen s ON s.SpecimenID = m.SpecimenID
        LEFT JOIN Material mat ON mat.MaterialID = s.MaterialID
        LEFT JOIN Source src ON src.SourceID = s.SourceID
        LEFT JOIN Operator op ON op.OperatorID = m.OperatorID
        LEFT JOIN InstrumentConfiguration ic ON ic.InstrumentConfigurationID = m.InstrumentConfigurationID
        LEFT JOIN Instrument ins ON ins.InstrumentID = m.InstrumentID
        LEFT JOIN MeasurementSiteType st ON st.MeasurementSiteTypeID = m.MeasurementSiteTypeID
        ORDER BY f.FilePath
    """).fetchall()

    id_by_measurement = {}
    for r in rows:
        id_by_measurement[r["MeasurementID"]] = os.path.splitext(os.path.basename(r["FilePath"]))[0]

    tags = {}
    for t in con.execute("""SELECT te.EntityID, t.TagLabel FROM TaggedEntity te
                            JOIN Tag t ON t.TagID = te.TagID WHERE te.EntityType = 'Measurement'"""):
        tags.setdefault(t["EntityID"], []).append(t["TagLabel"])

    scans, materials, match_index = [], {}, []
    for r in rows:
        sid = id_by_measurement[r["MeasurementID"]]
        mm = NAME_RE.match(sid)
        if not mm:
            print("skipped (name not recognised):", sid)
            continue
        key = mm.group("key").lower()
        mode = "ER-IR" if mm.group("mode").upper() == "ER_IR" else "ATR"
        nums = [n for n in (mm.group("rest") or "").split("_") if n != ""]
        if mode == "ER-IR" and not key.startswith("synth_") and len(nums) == 2:
            specimen, scan_no = int(nums[0]), int(nums[1])
        elif mode == "ER-IR" and nums:
            specimen, scan_no = 1, int(nums[0])
        else:
            specimen, scan_no = None, None

        data = json.loads(r["SpectrumData"])
        data.sort()
        b = bundles[mode]
        axis = [round(p[0], 3) for p in data]
        if axis not in b["axes"]:
            b["axes"].append(axis)
        b["spectra"][sid] = {"axis": b["axes"].index(axis),
                             "intensity": [round(p[1], 5) for p in data]}

        if mode == "ER-IR":
            match_index.append({"id": sid, "material": key, "intensity": resample(data)})

        scans.append({
            "id": sid, "file": r["FilePath"], "material": key, "mode": mode,
            "specimen": specimen, "scanNumber": scan_no,
            "scanDate": r["ScanDate"], "operator": r["Operator"],
            "intensityMode": r["IntensityMode"],
            "atrStandardId": id_by_measurement.get(r["ReferenceMeasurementID"]),
            "tags": tags.get(r["MeasurementID"], []),
            "instrument": " ".join(x for x in (r["Manufacturer"], r["InstrumentName"], r["Model"]) if x),
            "resolution": r["Resolution"], "numberOfScans": r["NumberOfScans"],
            "window": r["BeamSplitterType"], "aperture": r["ApertureSize"],
            "configNotes": r["ConfigNotes"], "site": r["SiteName"],
            "points": len(data),
        })

        m = materials.setdefault(key, {
            "id": key, "name": r["MaterialName"], "formula": r["ChemicalFormula"],
            "isSynthetic": bool(r["IsSynthetic"]), "description": r["Description"],
            "source": r["SourceName"], "color": COLORS.get(key, FALLBACK_COLOR),
            "erIrCount": 0, "atrCount": 0,
        })
        m["erIrCount" if mode == "ER-IR" else "atrCount"] += 1

    json.dump(sorted(materials.values(), key=lambda m: m["name"]),
              open(os.path.join(out, "materials.json"), "w"), indent=1)
    json.dump(scans, open(os.path.join(out, "scans.json"), "w"), indent=1)
    for mode, fname in (("ER-IR", "spectra_er_ir.json"), ("ATR", "spectra_atr.json")):
        json.dump(bundles[mode], open(os.path.join(out, fname), "w"), separators=(",", ":"))
    json.dump({"grid": {"start": GRID_START, "end": GRID_END, "points": GRID_POINTS,
                        "unit": "cm-1", "intensityMode": "Absorbance"},
               "spectra": match_index},
              open(os.path.join(out, "match_index.json"), "w"), separators=(",", ":"))
    print("Wrote %s: %d materials, %d scans (%d ER-IR in the match index)" %
          (out, len(materials), len(scans), len(match_index)))


if __name__ == "__main__":
    main()
