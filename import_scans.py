#!/usr/bin/env python3
"""
import_scans.py: load .dpt scans into the pigment spectral standards database.

USAGE
    python3 import_scans.py SCANS_FOLDER DATABASE.db [--schema SCHEMA.sql]
                            [--materials materials.csv] [--dates scan_dates.csv]
                            [--report REPORT.md] [--dry-run]

    SCANS_FOLDER  the folder holding the .dpt scans (subfolders are searched)
    DATABASE.db   the database. If it does not exist it is created from the schema file.
                  If it exists, the new scans are ADDED to it and nothing already in it is changed.
    --schema      the SQLite schema file (only needed when creating a new database)
    --materials   the materials sheet (default: materials.csv next to this script)
    --dates       the scan-date sheet (default: scan_dates.csv next to this script)
    --report      where to write the report (default: import_report.md next to the database)
    --dry-run     do everything and print the report, but save nothing

WHAT IT DOES
    1. Finds every .dpt file. Empty or unreadable files are skipped and listed.
    2. Works out material, specimen and mode (ER-IR or ATR) from the filename (rules below).
    3. Skips files already in the database, and removes exact duplicates (identical intensity
       values for the same material and mode), keeping the lowest scan number. Both are listed.
    4. Adds, for each new scan: the measurement, its spectrum, its file record (path, size,
       checksum) and its link to the ATR standard of the same material.
    5. Creates materials, sources and specimens as they are needed, from materials.csv.
       Each new scan gets its ScanDate from scan_dates.csv (longest matching folder prefix).
    6. Keeps the `needs-atr-recollection` tag up to date and writes a report.

It never modifies the scans. Nothing is converted: spectra are loaded as they are in the file.
The whole run is one transaction: if anything fails, nothing is saved.

FILENAME RULES  (the key is the file_key column of materials.csv)
    ER-IR, natural     <key><specimen>.<scan>.dpt                 e.g. hematite2.16.dpt
    ATR standard       <Key>Powder.<n>.dpt, <Key>_ATR.dpt or <key>_powder_ATR.dpt
                                                                   e.g. AzuritePowder.0.dpt
    synthetic ER-IR    <key>_ER_<n>.<m>.dpt                        e.g. verdigris_ER_3.0.dpt
    synthetic ATR      <key>_ATR.dpt                               e.g. verdigris_ATR.0.dpt
    Names are lower-cased, spaces removed, and the misspellings in TYPOS are corrected
    (every correction is listed in the report).
    A few legacy lazurite and dolomite names from the first scan session are also understood.
"""
import argparse
import collections
import csv
import hashlib
import json
import os
import re
import sqlite3
import sys

# ---------------------------------------------------------------------------
# Fixed facts. Materials, formulas, sources and specimen types live in materials.csv.
# ---------------------------------------------------------------------------

TYPOS = {            # misspelling -> correct spelling (applied to lower-cased filenames)
    "lasurite": "lazurite",
    "cinnabr": "cinnabar",
    "hematitie": "hematite",
    "verdigirs": "verdigris",
    "dolomiter": "dolomite",
    "dolemite": "dolomite",
}

# A scan that exists under another name in the database
RENAME = {"PowderATR/OrpimentPowder.1.dpt": "PowderATR/Orpiment_ATR.dpt"}
# Scans that are never loaded, with the reason
NOT_USED = {"PowderATR/OrpimentPowder.0.dpt": "Orpiment: OrpimentPowder.1.dpt is the standard"}

OPERATOR = ("Maria Gabriela Rivas Carmona", "gabrielarivas25@gmail.com", "University of Padova")
INSTRUMENT = ("FTIR microscope", "LUMOS II", "Bruker")
# (Resolution, AngleOfIncidence, NumberOfScans, BeamSplitterType, ApertureSize, Notes)
CONFIG = {
    "ER-IR": ("4 cm-1", None, 64, "ZnSe", "30 um", None),
    "ATR": ("4 cm-1", None, 32, "ZnSe", None, "Positioning speed: medium. Pressure: low."),
}
ATR_SPECIMEN_NOTE = "Reference standard for comparison"
TAG_MISSING_ATR = "needs-atr-recollection"

# ---------------------------------------------------------------------------


def load_materials(path):
    if not os.path.exists(path):
        sys.exit("Materials sheet not found: " + path)
    rows = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            key = r["file_key"].strip().lower()
            if not key:
                continue
            if key in rows:
                sys.exit("materials.csv: file_key '%s' appears twice" % key)
            if not r["material_name"].strip():
                sys.exit("materials.csv: row '%s' has no material_name" % key)
            if r["is_synthetic"].strip() not in ("0", "1"):
                sys.exit("materials.csv: row '%s': is_synthetic must be 0 or 1" % key)
            rows[key] = {k: (v.strip() if v and v.strip() else None) for k, v in r.items()}
            rows[key]["is_synthetic"] = int(r["is_synthetic"])
    return rows


def load_dates(path):
    """Return a list of (prefix, date), longest prefix first. A missing sheet means no dates."""
    if not os.path.exists(path):
        return []
    rows = []
    with open(path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            prefix, date = (r["path_prefix"] or "").strip(), (r["date"] or "").strip()
            if not prefix:
                continue
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
                sys.exit("scan_dates.csv: '%s' is not a date in the form YYYY-MM-DD (row '%s')" % (date, prefix))
            rows.append((prefix, date))
    return sorted(rows, key=lambda x: -len(x[0]))


def date_for(path, dates):
    for prefix, date in dates:
        if path.startswith(prefix):
            return date
    return None


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


def spectrum_hash(ys):
    return hashlib.md5(repr([round(y, 8) for y in ys]).encode()).hexdigest()


def classify(rel, mats, corrections=None):
    """Describe a file from its name, or return None if no rule matches."""
    corrections = corrections if corrections is not None else []
    folder, fname = os.path.split(rel)
    base = fname[:-4] if fname.lower().endswith(".dpt") else fname
    key = base.lower().replace(" ", "")
    fixed = key
    for bad, good in TYPOS.items():
        if bad in fixed:
            fixed = fixed.replace(bad, good)
    if fixed != key:
        corrections.append((fname, fixed))
    natural = [k for k, v in mats.items() if not v["is_synthetic"]]
    synth = [k for k, v in mats.items() if v["is_synthetic"]]

    if synth:   # synthetic powders: <key>_ER_<n>.<m>  or  <key>_ATR[.<n>]
        m = re.match(r"^(%s)_(atr|er)(?:_(\d+))?(?:\.(\d+))?$" % "|".join(map(re.escape, synth)), fixed)
        if m:
            return dict(material=m.group(1), specimen=1, mode="ATR" if m.group(2) == "atr" else "ER-IR",
                        order=(int(m.group(3) or 0), int(m.group(4) or 0)), spot=None)
    if natural:
        alt = "|".join(map(re.escape, natural))
        m = re.match(r"^(%s)powder\.(\d+)$" % alt, fixed)            # AzuritePowder.0
        if m:
            return dict(material=m.group(1), specimen=0, mode="ATR", order=(int(m.group(2)), 0), spot=None)
        m = re.match(r"^(%s)_powder_atr$" % alt, fixed)                # dolomite_powder_ATR
        if m:
            return dict(material=m.group(1), specimen=0, mode="ATR", order=(0, 0), spot=None)
        m = re.match(r"^(%s)_atr$" % alt, fixed)                      # Orpiment_ATR
        if m:
            return dict(material=m.group(1), specimen=0, mode="ATR", order=(0, 0), spot=None)
    # legacy names from the first scan session
    if "dolomite" in mats:
        m = re.match(r"^dolomite_er_(\d+)\.0$", fixed)
        if m and "powder_dolomite" in folder.lower():
            return dict(material="dolomite", specimen=2, mode="ER-IR", order=(int(m.group(1)), 0), spot=None)
    if "lazurite" in mats:
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
    if natural:
        m = re.match(r"^(%s)(\d+)\.(\d+)$" % "|".join(map(re.escape, natural)), fixed)   # hematite2.16
        if m:
            return dict(material=m.group(1), specimen=int(m.group(2)), mode="ER-IR",
                        order=(int(m.group(3)), 0), spot=None)
    return None


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description="Add .dpt scans to the pigment spectral standards database.")
    ap.add_argument("scans")
    ap.add_argument("database")
    ap.add_argument("--schema", default=os.path.join(here, "pigment_spectral_standards_sqlite_schema.sql"))
    ap.add_argument("--materials", default=os.path.join(here, "materials.csv"))
    ap.add_argument("--dates", default=os.path.join(here, "scan_dates.csv"))
    ap.add_argument("--report")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    mats = load_materials(a.materials)
    dates = load_dates(a.dates)
    exists = os.path.exists(a.database)
    if not exists and not os.path.exists(a.schema):
        sys.exit("The database does not exist and the schema file was not found: " + a.schema)

    # ---- read and classify the scans ----
    corrections, unmatched, unreadable, not_used = [], [], [], []
    records = []
    for root, _, files in os.walk(a.scans):
        for f in sorted(files):
            if not f.lower().endswith(".dpt"):
                continue
            full = os.path.join(root, f)
            rel = os.path.relpath(full, a.scans).replace(os.sep, "/")
            tail = "/".join(rel.split("/")[-2:])
            if tail in NOT_USED or rel in NOT_USED:
                not_used.append((rel, NOT_USED.get(tail) or NOT_USED.get(rel)))
                continue
            info = classify(rel, mats, corrections)
            if info is None:
                unmatched.append(rel)
                continue
            pts = read_dpt(full)
            if pts is None:
                unreadable.append((rel, os.path.getsize(full)))
                continue
            info.update(rel=rel, full=full, pts=pts, path=RENAME.get(tail, RENAME.get(rel, rel)))
            records.append(info)

    # ---- open or create the database ----
    con = sqlite3.connect(":memory:" if (a.dry_run and not exists) else a.database)
    if not exists:
        con.executescript(open(a.schema, encoding="utf-8").read())
    con.execute("PRAGMA foreign_keys = ON")
    cur = con.cursor()
    cur.execute("BEGIN")

    def one(sql, args=()):
        r = cur.execute(sql, args).fetchone()
        return r[0] if r else None

    def pick(table, col, val, idcol):
        v = one("SELECT %s FROM %s WHERE %s=?" % (idcol, table, col), (val,))
        if v is None:
            sys.exit("'%s' is not in the %s pick list. Check materials.csv." % (val, table))
        return v

    for k, m in mats.items():
        if m["specimen_type"]:
            pick("SpecimenType", "TypeName", m["specimen_type"], "SpecimenTypeID")

    # fixed records (only when creating)
    if one("SELECT COUNT(*) FROM Operator") == 0:
        cur.execute("INSERT INTO Institution(InstitutionName) VALUES (?)", (OPERATOR[2],))
        cur.execute("INSERT INTO Operator(Name,Email,InstitutionID) VALUES (?,?,?)", OPERATOR[:2] + (cur.lastrowid,))
    if one("SELECT COUNT(*) FROM Instrument") == 0:
        cur.execute("INSERT INTO Instrument(InstrumentName,Model,Manufacturer) VALUES (?,?,?)", INSTRUMENT)
    cfg_id = {}
    for mode, vals in CONFIG.items():
        found = one("SELECT InstrumentConfigurationID FROM InstrumentConfiguration WHERE Resolution IS ? "
                    "AND NumberOfScans IS ? AND BeamSplitterType IS ? AND ApertureSize IS ? AND Notes IS ?",
                    (vals[0], vals[2], vals[3], vals[4], vals[5]))
        if found is None:
            cur.execute("INSERT INTO InstrumentConfiguration(Resolution,AngleOfIncidence,NumberOfScans,"
                        "BeamSplitterType,ApertureSize,Notes) VALUES (?,?,?,?,?,?)", vals)
            found = cur.lastrowid
        cfg_id[mode] = found
    operator_id = one("SELECT MIN(OperatorID) FROM Operator")
    instrument_id = one("SELECT MIN(InstrumentID) FROM Instrument")
    site = pick("MeasurementSiteType", "TypeName", "Laboratory", "MeasurementSiteTypeID")
    mode_id = {m: pick("AcquisitionModeType", "ModeName", m, "AcquisitionModeID") for m in ("ER-IR", "ATR")}

    # ---- what is already in the database ----
    key_of_name = {v["material_name"]: k for k, v in mats.items()}
    mat_id, spec_id, atr_meas = {}, {}, {}
    have_paths, have_hashes = set(), set()
    for name, mid in cur.execute("SELECT MaterialName, MaterialID FROM Material"):
        if name in key_of_name:
            mat_id[key_of_name[name]] = mid
    for mid, mode, sid, path, js in cur.execute(
            "SELECT m.MeasurementID, am.ModeName, m.SpecimenID, f.FilePath, m.SpectrumData FROM Measurement m "
            "JOIN SpectralFile f USING(MeasurementID) JOIN AcquisitionModeType am USING(AcquisitionModeID) "
            "ORDER BY m.MeasurementID").fetchall():
        have_paths.add(path)
        info = classify(path, mats)
        if info is None:
            continue
        have_hashes.add((info["material"], mode, spectrum_hash([p[1] for p in sorted(json.loads(js))])))
        spec_id.setdefault((info["material"], 1 if mats[info["material"]]["is_synthetic"] else info["specimen"]), sid)
        if mode == "ATR":
            atr_meas.setdefault(info["material"], mid)

    # ---- skip what is already loaded; remove duplicates ----
    already = [r for r in records if r["path"] in have_paths]
    records = [r for r in records if r["path"] not in have_paths]
    groups = collections.defaultdict(list)
    for r in records:
        groups[(r["material"], r["mode"], spectrum_hash([y for _, y in r["pts"]]))].append(r)
    duplicates, kept = [], []
    for g in groups.values():
        g.sort(key=lambda r: (r["specimen"], r["order"], r["rel"]))
        if (g[0]["material"], g[0]["mode"], spectrum_hash([y for _, y in g[0]["pts"]])) in have_hashes:
            duplicates += [(d["rel"], "a scan already in the database") for d in g]
            continue
        kept.append(g[0])
        duplicates += [(d["rel"], g[0]["rel"]) for d in g[1:]]
    records = sorted(kept, key=lambda r: (r["material"], r["mode"], r["specimen"], r["order"], r["rel"]))

    # ---- create what is missing, then load ----
    sources = set()
    def material(key):
        if key not in mat_id:
            m = mats[key]
            cur.execute("INSERT INTO Material(MaterialName,ChemicalFormula,IsSynthetic,Description) VALUES (?,?,?,?)",
                        (m["material_name"], m["formula"], m["is_synthetic"], m["description"]))
            mat_id[key] = cur.lastrowid
        return mat_id[key]

    def source(name):
        if name is None:
            return None
        cur.execute("INSERT OR IGNORE INTO Source(SourceName) VALUES (?)", (name,))
        return one("SELECT SourceID FROM Source WHERE SourceName=?", (name,))

    def specimen(key, n):
        m = mats[key]
        k = (key, 1 if m["is_synthetic"] else n)
        if k in spec_id:
            return spec_id[k]
        stype = pick("SpecimenType", "TypeName", m["specimen_type"], "SpecimenTypeID") if m["specimen_type"] else None
        if n == 0 and not m["is_synthetic"]:
            row = (None, ATR_SPECIMEN_NOTE, None)
        else:
            row = (stype, m["preparation_notes"], m["source_notes"])
        cur.execute("INSERT INTO Specimen(SpecimenTypeID,PreparationNotes,SourceNotes,MaterialID,SourceID) "
                    "VALUES (?,?,?,?,?)", (row[0], row[1], row[2], material(key), source(m["source"])))
        spec_id[k] = cur.lastrowid
        return spec_id[k]

    added = collections.Counter()
    undated = []
    for r in [x for x in records if x["mode"] == "ATR"] + [x for x in records if x["mode"] == "ER-IR"]:
        mode, key = r["mode"], r["material"]
        sid = specimen(key, r["specimen"])
        ref = atr_meas.get(key) if mode == "ER-IR" else None
        spectrum = json.dumps([[x, y] for x, y in r["pts"]], separators=(",", ":"))
        cur.execute(
            "INSERT INTO Measurement(SpecimenID,InstrumentID,InstrumentConfigurationID,AcquisitionModeID,"
            "SpectrumData,OperatorID,MeasurementSiteTypeID,ReferenceMeasurementID,SpecimenSpotDescription,ScanDate) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (sid, instrument_id, cfg_id[mode], mode_id[mode], spectrum, operator_id, site, ref, r["spot"],
             date_for(r["path"], dates)))
        if date_for(r["path"], dates) is None:
            undated.append(r["path"])
        mid = cur.lastrowid
        if mode == "ATR":
            atr_meas.setdefault(key, mid)
        data = open(r["full"], "rb").read()
        cur.execute("INSERT INTO SpectralFile(MeasurementID,FilePath,FileType,FileSize,Checksum) VALUES (?,?,?,?,?)",
                    (mid, r["path"], "dpt", len(data), hashlib.sha256(data).hexdigest()))
        added[(mats[key]["material_name"], mode)] += 1

    # ER-IR scans loaded earlier without a standard are linked now if one exists
    relinked = 0
    for key, am in atr_meas.items():
        if key in mat_id:
            cur.execute("UPDATE Measurement SET ReferenceMeasurementID=? WHERE ReferenceMeasurementID IS NULL AND "
                        "AcquisitionModeID=? AND SpecimenID IN (SELECT SpecimenID FROM Specimen WHERE MaterialID=?)",
                        (am, mode_id["ER-IR"], mat_id[key]))
            relinked += cur.rowcount

    # tag: materials with ER-IR scans but no ATR standard
    cur.execute("INSERT OR IGNORE INTO Tag(TagLabel) VALUES (?)", (TAG_MISSING_ATR,))
    tag_id = one("SELECT TagID FROM Tag WHERE TagLabel=?", (TAG_MISSING_ATR,))
    cur.execute("DELETE FROM TaggedEntity WHERE TagID=? AND EntityType='Specimen'", (tag_id,))
    cur.execute("""INSERT INTO TaggedEntity
        SELECT ?, 'Specimen', s.SpecimenID FROM Specimen s WHERE s.MaterialID IN (
          SELECT s2.MaterialID FROM Specimen s2 JOIN Measurement m USING(SpecimenID)
          WHERE m.AcquisitionModeID=? AND s2.MaterialID IS NOT NULL
            AND s2.MaterialID NOT IN (SELECT s3.MaterialID FROM Specimen s3 JOIN Measurement m3 USING(SpecimenID)
                                      WHERE m3.AcquisitionModeID=? AND s3.MaterialID IS NOT NULL))""",
                (tag_id, mode_id["ER-IR"], mode_id["ATR"]))

    # ---- checks ----
    fk = cur.execute("PRAGMA foreign_key_check").fetchall()
    if fk:
        con.rollback()
        sys.exit("Foreign-key problems, nothing saved: %r" % fk)
    n_meas = one("SELECT COUNT(*) FROM Measurement")
    n_linked = one("SELECT COUNT(*) FROM Measurement WHERE ReferenceMeasurementID IS NOT NULL")
    per_mat = cur.execute("""
        SELECT mat.MaterialName, SUM(am.ModeName='ER-IR'), SUM(am.ModeName='ATR'), COUNT(DISTINCT s.SpecimenID)
        FROM Measurement m JOIN Specimen s USING(SpecimenID) JOIN Material mat USING(MaterialID)
        JOIN AcquisitionModeType am USING(AcquisitionModeID) GROUP BY mat.MaterialName ORDER BY 1""").fetchall()
    no_atr = [r[0] for r in cur.execute(
        "SELECT DISTINCT mat.MaterialName FROM TaggedEntity te JOIN Specimen s ON s.SpecimenID=te.EntityID "
        "JOIN Material mat USING(MaterialID) WHERE te.TagID=?", (tag_id,))]

    # ---- report ----
    L = ["# Import report\n"]
    L.append("%s. **%d scans added**, %d skipped because they were already in the database. "
             "The database now holds **%d measurements**, %d of them linked to an ATR standard.\n"
             % ("DRY RUN, nothing saved" if a.dry_run else "Saved", len(records), len(already), n_meas, n_linked))
    L.append("Foreign-key check: no problems\n")
    L.append("## Added in this run\n")
    L += ["- %s, %s: %d" % (m, mode, n) for (m, mode), n in sorted(added.items())] or ["(nothing new)"]
    if relinked:
        L.append("- %d earlier ER-IR scans were linked to an ATR standard that is now available." % relinked)
    L.append("\n## Scans added without a date (%d)\n" % len(undated))
    L += ["- `%s`" % x for x in sorted(undated)] or ["(none)"]
    if undated:
        L.append("\nAdd a line for them to scan_dates.csv, or type the date into the database (ScanDate).")
    L.append("\n## Database totals per material\n")
    L.append("| Material | ER-IR | ATR | Specimens |\n|---|---|---|---|")
    L += ["| %s | %d | %d | %d |" % r for r in per_mat]
    L.append("\n## Skipped: empty or unreadable (%d)\n" % len(unreadable))
    L += ["- `%s` (%d bytes)" % x for x in unreadable] or ["(none)"]
    L.append("\n## Removed as duplicates (%d)\n" % len(duplicates))
    L += ["- `%s` is identical to `%s`" % x for x in sorted(duplicates)] or ["(none)"]
    L.append("\n## Not used on purpose (%d)\n" % len(not_used))
    L += ["- `%s`: %s" % x for x in not_used] or ["(none)"]
    L.append("\n## Files whose name matched no rule, not loaded (%d)\n" % len(unmatched))
    L += ["- `%s`" % x for x in sorted(unmatched)] or ["(none)"]
    if unmatched:
        L.append("\nIf these are a new material, add a row for it to materials.csv. "
                 "Otherwise rename the files to the pattern in WORKFLOW.md.")
    L.append("\n## Filename typos corrected (%d)\n" % len(corrections))
    L += ["- `%s` read as `%s`" % x for x in sorted(set(corrections))] or ["(none)"]
    L.append("\n## Things to check\n")
    L.append("- Materials with ER-IR scans but no ATR standard (tagged `%s`): %s"
             % (TAG_MISSING_ATR, ", ".join(no_atr) or "none"))
    L.append("- Spectra are loaded exactly as in the files and never converted.")
    rep = a.report or os.path.join(os.path.dirname(os.path.abspath(a.database)), "import_report.md")
    if a.dry_run:
        con.rollback()
    else:
        con.commit()
        open(rep, "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L))
    con.close()


if __name__ == "__main__":
    main()
