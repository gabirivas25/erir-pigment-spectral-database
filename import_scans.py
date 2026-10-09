#!/usr/bin/env python3
"""
import_scans.py: build the pigment spectral standards database from a folder of .dpt scans.

USAGE
    python3 import_scans.py SCANS_FOLDER SCHEMA.sql OUTPUT.db [--old-db OLD.db] [--report REPORT.md]

    SCANS_FOLDER  the unzipped scan folder (subfolders are searched)
    SCHEMA.sql    pigment_spectral_standards_sqlite_schema.sql
    OUTPUT.db     the database to create (must not already exist)
    --old-db      optional: the archived original database, used only to compare scan counts
    --report      where to write the report (default: import_report.md next to OUTPUT.db)

WHAT IT DOES
    1. Finds every .dpt file. Files that are empty or not readable text are skipped and listed.
    2. Works out material, specimen and mode (ER-IR or ATR) from the filename (rules below).
    3. Removes exact duplicates (identical intensity values for the same material and mode),
       keeping the lowest scan number, and lists every file it removed.
    4. Creates the database from the schema file, fills in the fixed records (operator,
       instrument, configurations, sources, materials, specimens) and loads every measurement,
       its spectrum, its file record (path, size, checksum) and its link to its ATR standard.
    5. Writes a report of everything it skipped, corrected, removed or guessed.

It never modifies the scans. Nothing is converted: spectra are loaded as they are in the file.

FILENAME RULES
    ATR     the name contains "ATR", or the file is in a folder called PowderATR
    ER-IR   everything else
    Names are lower-cased, spaces removed, and the typos in TYPOS below are corrected
    (every correction is listed in the report).
"""
import argparse
import collections
import hashlib
import json
import os
import re
import sqlite3
import sys

# ---------------------------------------------------------------------------
# EDIT HERE: the facts the script uses. Everything else is mechanical.
# ---------------------------------------------------------------------------

TYPOS = {            # misspelling -> correct spelling (applied to lower-cased filenames)
    "lasurite": "lazurite",
    "cinnabr": "cinnabar",
    "hematitie": "hematite",
    "verdigirs": "verdigris",
    "dolomiter": "dolomite",
    "dolemite": "dolomite",
}

NATURAL = ["aragonite", "azurite", "calcite", "cerussite", "cinnabar", "dolomite",
           "goethite", "hematite", "lazurite", "magnetite", "malachite", "orpiment"]

# key used in filenames -> (database name, is_synthetic, formula, description)
# Formulas and descriptions are as given by Gabriela (plain text: subscripts written inline).
MATERIALS = {
    "azurite": ("Azurite", 0, "Cu3(CO3)2(OH)2", "Basic copper carbonate"),
    "aragonite": ("Aragonite", 0, "CaCO3", "Calcium carbonate polymorph"),
    "calcite": ("Calcite", 0, "CaCO3", "Calcium carbonate polymorph"),
    "dolomite": ("Dolomite", 0, "CaMg(CO3)2", "Calcium magnesium carbonate"),
    "cerussite": ("Cerussite", 0, "PbCO3", "Lead carbonate"),
    "malachite": ("Malachite", 0, "Cu2CO3(OH)2", "Basic copper carbonate"),
    "synth_malachite": ("Synthetic malachite", 1, "Cu2CO3(OH)2", "Chemically identical to natural malachite"),
    "hematite": ("Hematite", 0, "Fe2O3", "Iron(III) oxide"),
    "goethite": ("Goethite", 0, "FeO(OH)", "Iron(III) oxide-hydroxide"),
    "magnetite": ("Magnetite", 0, "Fe3O4", "Iron(II,III) oxide"),
    "cinnabar": ("Cinnabar", 0, "HgS", "Mercury(II) sulfide"),
    "orpiment": ("Orpiment", 0, "As2S3", "Arsenic trisulfide"),
    "lazurite": ("Lazurite", 0, "(Na,Ca)8(AlSiO4)6(SO4,S,Cl)2",
                 "A complex sodalite-group tectosilicate; the main component of lapis lazuli"),
    "synth_ultramarine": ("Synthetic ultramarine", 1, "Na6-10Al6Si6O24S2-4",
                 "An idealized or simplified manufactured formula is often written as Na8Al6Si6O24S3"),
    "verdigris": ("Verdigris", 1, "Cu(CH3COO)2.H2O or [Cu(CH3COO)2]2.Cu(OH)2.5H2O",
                 "Neutral copper(II) acetate monohydrate, or the basic copper acetate formulation"),
}

UNIPD = "UniPD mineral collection"
SOURCE_OF = {m: UNIPD for m in NATURAL}
SOURCE_OF.update({"synth_ultramarine": "Maimeri", "synth_malachite": "Kremer", "verdigris": "Unknown"})

# ATR files that are NOT used (none in the repo copy: OrpimentPowder.0.dpt was removed)
ATR_NOT_USED = {"PowderATR/OrpimentPowder.0.dpt": "Orpiment: OrpimentPowder.1.dpt is the standard"}
# Files stored under a different name in the database (the repo already holds the renamed file)
RENAME = {"PowderATR/OrpimentPowder.1.dpt": "PowderATR/Orpiment_ATR.dpt"}

OPERATOR = ("Maria Gabriela Rivas Carmona", "gabrielarivas25@gmail.com", "University of Padova")
INSTRUMENT = ("FTIR microscope", "LUMOS II", "Bruker")
# (Resolution, AngleOfIncidence, NumberOfScans, BeamSplitterType, ApertureSize, Notes)
CONFIG = {
    "ER-IR": ("4 cm-1", None, 64, "ZnSe", "30 um", None),
    "ATR": ("4 cm-1", None, 32, "ZnSe", None, "Positioning speed: medium. Pressure: low."),
}
TAG_MISSING_ATR = "needs-atr-recollection"

# ---------------------------------------------------------------------------


def read_dpt(path):
    """Return a list of (wavenumber, intensity) sorted by wavenumber, or None if unreadable."""
    try:
        pts = []
        with open(path, "r", encoding="utf-8", errors="strict") as fh:
            for line in fh:
                s = line.strip()
                if not s or not re.match(r"^[-+]?[0-9.]", s):
                    continue
                parts = re.split(r"[,\s;]+", s)
                if len(parts) >= 2:
                    pts.append((float(parts[0]), float(parts[1])))
        if len(pts) < 100:
            return None
        return sorted(pts)
    except (UnicodeDecodeError, ValueError, OSError):
        return None


def classify(rel, corrections):
    """Return a dict describing the file, or None if the name matches no rule."""
    folder, fname = os.path.split(rel)
    base = fname[:-4] if fname.lower().endswith(".dpt") else fname
    key = base.lower().replace(" ", "")
    fixed = key
    for bad, good in TYPOS.items():
        if bad in fixed:
            fixed = fixed.replace(bad, good)
    if fixed != key:
        corrections.append((fname, fixed))
    in_powderatr = "powderatr" in folder.lower()
    spot = None

    # 1. synthetics: synth_malachite_ER_3, verdigris_ATR.0, synth_ultramarine_ER_10.0 ...
    m = re.match(r"^(synth_malachite|synth_ultramarine|verdigris)_(atr|er)(?:_(\d+))?(?:\.(\d+))?$", fixed)
    if m:
        mat, mode = m.group(1), "ATR" if m.group(2) == "atr" else "ER-IR"
        return dict(material=mat, specimen=1, mode=mode,
                    order=(int(m.group(3) or 0), int(m.group(4) or 0)), spot=None)

    # 2. leftover dolomite mineral sample (powder_dolomite folder): dolomite specimen 2
    m = re.match(r"^dolomite_er_(\d+)\.0$", fixed)
    if m and "powder_dolomite" in folder.lower():
        return dict(material="dolomite", specimen=2, mode="ER-IR", order=(int(m.group(1)), 0), spot=None)

    # 3. ATR standards named <Mineral>Powder.<n>
    m = re.match(r"^([a-z]+)powder\.(\d+)$", fixed)
    if m and m.group(1) in NATURAL:
        return dict(material=m.group(1), specimen=0, mode="ATR", order=(int(m.group(2)), 0), spot=None)

    # 3b. ATR standards already renamed to <Mineral>_ATR (e.g. Orpiment_ATR.dpt)
    m = re.match(r"^([a-z]+)_atr$", fixed)
    if m and m.group(1) in NATURAL:
        return dict(material=m.group(1), specimen=0, mode="ATR", order=(0, 0), spot=None)

    # 4. lazurite: names carry the point, not a scan number
    m = re.match(r"^lazurite(?:frag1|sample|samp1)?_p(\d+)(?:\.(\d+))?$", fixed)
    if m:
        return dict(material="lazurite", specimen=1, mode="ER-IR",
                    order=(int(m.group(1)), int(m.group(2) or 0)), spot="point %s" % m.group(1))
    m = re.match(r"^lazurite_samp2_p(\d+)(?:\.(\d+))?$", fixed)
    if m:
        return dict(material="lazurite", specimen=2, mode="ER-IR",
                    order=(int(m.group(1)), int(m.group(2) or 0)), spot="point %s" % m.group(1))
    if fixed == "lazurite1.1":
        return dict(material="lazurite", specimen=1, mode="ER-IR", order=(1, 1), spot="point 1")

    # 5. general ER-IR name: <Mineral><specimen>.<scan>
    m = re.match(r"^([a-z]+)(\d+)\.(\d+)$", fixed)
    if m and m.group(1) in NATURAL:
        return dict(material=m.group(1), specimen=int(m.group(2)), mode="ER-IR",
                    order=(int(m.group(3)), 0), spot=None)

    # any other file with ATR in its name or in PowderATR
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scans")
    ap.add_argument("schema")
    ap.add_argument("output")
    ap.add_argument("--old-db")
    ap.add_argument("--report")
    a = ap.parse_args()
    if os.path.exists(a.output):
        sys.exit("Refusing to overwrite existing file: " + a.output)

    corrections, unmatched, unreadable, not_used = [], [], [], []
    records = []
    for root, _, files in os.walk(a.scans):
        for f in sorted(files):
            if not f.lower().endswith(".dpt"):
                continue
            full = os.path.join(root, f)
            rel = os.path.relpath(full, a.scans).replace(os.sep, "/")
            rel_short = "/".join(rel.split("/")[-2:]) if rel.count("/") > 1 else rel
            info = classify(rel, corrections)
            if info is None:
                unmatched.append(rel)
                continue
            if rel_short in ATR_NOT_USED or rel in ATR_NOT_USED:
                not_used.append((rel, ATR_NOT_USED.get(rel_short) or ATR_NOT_USED.get(rel)))
                continue
            pts = read_dpt(full)
            if pts is None:
                unreadable.append((rel, os.path.getsize(full)))
                continue
            info.update(rel=rel, rel_short=rel_short, full=full, pts=pts)
            records.append(info)

    # ---- duplicates: same material and mode, identical intensities; keep lowest scan ----
    groups = collections.defaultdict(list)
    for r in records:
        h = hashlib.md5(repr([round(y, 8) for _, y in r["pts"]]).encode()).hexdigest()
        groups[(r["material"], r["mode"], h)].append(r)
    duplicates, kept = [], []
    for g in groups.values():
        g.sort(key=lambda r: (r["specimen"], r["order"], r["rel"]))
        kept.append(g[0])
        for d in g[1:]:
            duplicates.append((d["rel"], g[0]["rel"]))
    records = sorted(kept, key=lambda r: (r["material"], r["mode"], r["specimen"], r["order"], r["rel"]))

    # ---- build the database ----
    con = sqlite3.connect(a.output)
    con.executescript(open(a.schema, encoding="utf-8").read())
    con.execute("PRAGMA foreign_keys = ON")
    cur = con.cursor()

    def pick(table, col, val, idcol):
        return cur.execute("SELECT %s FROM %s WHERE %s=?" % (idcol, table, col), (val,)).fetchone()[0]

    cur.execute("INSERT INTO Institution(InstitutionName) VALUES (?)", (OPERATOR[2],))
    cur.execute("INSERT INTO Operator(Name,Email,InstitutionID) VALUES (?,?,1)", OPERATOR[:2])
    cur.execute("INSERT INTO Instrument(InstrumentName,Model,Manufacturer) VALUES (?,?,?)", INSTRUMENT)
    cfg_id = {}
    for mode, vals in CONFIG.items():
        cur.execute("INSERT INTO InstrumentConfiguration(Resolution,AngleOfIncidence,NumberOfScans,"
                    "BeamSplitterType,ApertureSize,Notes) VALUES (?,?,?,?,?,?)", vals)
        cfg_id[mode] = cur.lastrowid
    for name in sorted(set(SOURCE_OF.values())):
        cur.execute("INSERT INTO Source(SourceName) VALUES (?)", (name,))

    used = sorted({r["material"] for r in records})
    mat_id = {}
    for key in used:
        name, syn, formula, desc = MATERIALS[key]
        cur.execute("INSERT INTO Material(MaterialName,ChemicalFormula,IsSynthetic,Description) VALUES (?,?,?,?)",
                    (name, formula, syn, desc))
        mat_id[key] = cur.lastrowid

    site = pick("MeasurementSiteType", "TypeName", "Laboratory", "MeasurementSiteTypeID")
    t_ground = pick("SpecimenType", "TypeName", "ground mineral", "SpecimenTypeID")
    t_frag = pick("SpecimenType", "TypeName", "mineral fragment", "SpecimenTypeID")
    t_powder = pick("SpecimenType", "TypeName", "powder pigment", "SpecimenTypeID")

    spec_id = {}
    def specimen(mat, n, mode):
        # synthetic powders: one specimen measured in both modes
        synthetic = MATERIALS[mat][1] == 1
        k = (mat, 1 if synthetic else n)
        if k in spec_id:
            return spec_id[k]
        src = pick("Source", "SourceName", SOURCE_OF[mat], "SourceID")
        if synthetic:
            notes = {"synth_malachite": "Kremer Pigmente art. 44400, C.I. 77422, CAS 12069-69-1; label: Malachit, synthetisch",
                     "synth_ultramarine": "Maimeri art. 3517392, no. 392, PB29; label: Ultramarine Deep (Blu oltremare scuro)",
                     "verdigris": None}[mat]
            row = (t_powder, None, notes)
        elif n == 0:       # ATR standard of a mineral
            row = (None, "Reference standard for comparison", None)
        else:
            row = (t_ground, "Ground/prepared for FTIR analysis", None)
        cur.execute("INSERT INTO Specimen(SpecimenTypeID,PreparationNotes,SourceNotes,MaterialID,SourceID) "
                    "VALUES (?,?,?,?,?)", (row[0], row[1], row[2], mat_id[mat], src))
        spec_id[k] = cur.lastrowid
        return spec_id[k]

    atr_meas = {}
    meas_of = {}
    # ATR first, so ER-IR scans can point to them
    for r in [x for x in records if x["mode"] == "ATR"] + [x for x in records if x["mode"] == "ER-IR"]:
        mode = r["mode"]
        sid = specimen(r["material"], r["specimen"], mode)
        ref = atr_meas.get(r["material"]) if mode == "ER-IR" else None
        spectrum = json.dumps([[x, y] for x, y in r["pts"]], separators=(",", ":"))
        cur.execute(
            "INSERT INTO Measurement(SpecimenID,InstrumentID,InstrumentConfigurationID,AcquisitionModeID,"
            "SpectrumData,OperatorID,MeasurementSiteTypeID,ReferenceMeasurementID,SpecimenSpotDescription) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (sid, 1, cfg_id[mode], pick("AcquisitionModeType", "ModeName", mode, "AcquisitionModeID"),
             spectrum, 1, site, ref, r["spot"]))
        mid = cur.lastrowid
        if mode == "ATR":
            atr_meas[r["material"]] = mid
        data = open(r["full"], "rb").read()
        path = RENAME.get(r["rel_short"], RENAME.get(r["rel"], r["rel"]))
        cur.execute("INSERT INTO SpectralFile(MeasurementID,FilePath,FileType,FileSize,Checksum) VALUES (?,?,?,?,?)",
                    (mid, path, "dpt", len(data), hashlib.sha256(data).hexdigest()))
        meas_of[r["rel"]] = mid

    # tag: minerals that have ER-IR scans but no ATR standard
    cur.execute("INSERT INTO Tag(TagLabel) VALUES (?)", (TAG_MISSING_ATR,))
    tag_id = cur.lastrowid
    no_atr = [m for m in used if m not in atr_meas]
    for m in no_atr:
        for (mat, n), sid in spec_id.items():
            if mat == m:
                cur.execute("INSERT INTO TaggedEntity VALUES (?,?,?)", (tag_id, "Specimen", sid))
    con.commit()

    # ---- checks ----
    fk = con.execute("PRAGMA foreign_key_check").fetchall()
    n_meas = con.execute("SELECT COUNT(*) FROM Measurement").fetchone()[0]
    n_linked = con.execute("SELECT COUNT(*) FROM Measurement WHERE ReferenceMeasurementID IS NOT NULL").fetchone()[0]
    per_mat = con.execute("""
        SELECT mat.MaterialName,
               SUM(am.ModeName='ER-IR'), SUM(am.ModeName='ATR'),
               COUNT(DISTINCT s.SpecimenID)
        FROM Measurement m JOIN Specimen s USING(SpecimenID) JOIN Material mat USING(MaterialID)
        JOIN AcquisitionModeType am USING(AcquisitionModeID) GROUP BY mat.MaterialName ORDER BY 1""").fetchall()
    old = {}
    if a.old_db:
        oc = sqlite3.connect("file:%s?mode=ro" % a.old_db, uri=True)
        for name, n in oc.execute("""SELECT m.MaterialName, COUNT(*) FROM Spectrum sp
            JOIN AcquisitionModeType a USING(AcquisitionModeID) JOIN Measurement me USING(MeasurementID)
            JOIN Sample s ON s.SampleID=me.SampleID JOIN Material m ON m.MaterialID=s.MaterialID
            WHERE a.ModeName='ER-IR' GROUP BY m.MaterialName"""):
            old[name.replace("Dolemite", "Dolomite")] = n

    # ---- report ----
    L = []
    L.append("# Import report\n")
    L.append("Loaded **%d measurements** from %d readable, recognised files; %d of them carry a link to an ATR standard.\n"
             % (n_meas, len(records) + len(duplicates), n_linked))
    L.append("Foreign-key check: %s\n" % ("no problems" if not fk else "PROBLEMS: %r" % fk))
    L.append("## Per material\n")
    L.append("| Material | ER-IR loaded | ER-IR in old database | ATR loaded | Specimens |\n|---|---|---|---|---|")
    for name, er, atr, sp in per_mat:
        L.append("| %s | %d | %s | %d | %d |" % (name, er, old.get(name, "-") if old else "-", atr, sp))
    L.append("\n## Skipped: empty or unreadable (%d)\n" % len(unreadable))
    L += ["- `%s` (%d bytes)" % x for x in unreadable] or ["(none)"]
    L.append("\n## Removed as exact duplicates (%d)\n" % len(duplicates))
    L += ["- `%s` is identical to `%s` (kept)" % x for x in sorted(duplicates)] or ["(none)"]
    L.append("\n## Not used on purpose (%d)\n" % len(not_used))
    L += ["- `%s`: %s" % x for x in not_used] or ["(none)"]
    L.append("\n## Files whose name matched no rule, not loaded (%d)\n" % len(unmatched))
    L += ["- `%s`" % x for x in sorted(unmatched)] or ["(none)"]
    L.append("\n## Filename typos corrected (%d)\n" % len(corrections))
    L += ["- `%s` read as `%s`" % x for x in sorted(corrections)] or ["(none)"]
    L.append("\n## Decisions the script made that you may want to check\n")
    L.append("- Minerals with ER-IR scans but no ATR standard (tagged `%s`): %s"
             % (TAG_MISSING_ATR, ", ".join(MATERIALS[m][0] for m in no_atr) or "none"))
    L.append("- Stored under another name: " + ", ".join("`%s` as `%s`" % kv for kv in RENAME.items()))
    L.append("- The `powder_dolomite` scans (10) are stored under Dolomite specimen 2.")
    L.append("- Lazurite: scan names give the point (`p1`, `p2` ...), stored as the specimen spot description.")
    L.append("- Spectra are loaded exactly as in the files and never converted.")
    L.append("- DateTime is empty for every measurement.")
    rep = a.report or os.path.join(os.path.dirname(os.path.abspath(a.output)), "import_report.md")
    open(rep, "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L))
    con.close()


if __name__ == "__main__":
    main()
