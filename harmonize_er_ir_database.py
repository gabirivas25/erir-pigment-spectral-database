"""
harmonize_er_ir_database.py

One-time cleaning step, run BEFORE any analysis. It never modifies the
original database: it copies it and applies all changes to the copy.

WHAT IT DOES:
1. DUPLICATE CHECK. Two ER-IR files with identical data points are the
   same export saved twice. The first file (lowest scan number) is kept;
   the others are tagged "Excluded: duplicate export" and a note names
   the file they duplicate.

2. UNIT CHECK. Most files are exported as pseudo-absorbance, log10(1/R)
   (baseline typically ~1-3). Some were exported as reflectance, R
   (baseline typically < 0.2). A file is treated as R when:
       median < 0.2  AND  min > -0.01  AND  max < 1.5
   It is converted with log10(1/R) = -log10(R) and then VERIFIED: the
   converted median must fall within 0.5x-2x of the median of the
   same mineral's native log10(1/R) files. If it passes, the converted
   values replace the originals, the file is tagged
   "Converted: R to log10(1/R)", and the step is logged in the
   Preprocessing table. If it fails, nothing is changed and the file is
   tagged "Needs review: units unclear".
   Reflectance values at or below zero (detector noise on very dark
   samples) cannot be log-transformed; they are set to a floor of 1e-4
   before conversion, and the number of such points is recorded.

3. SANITY CHECK. Any file that is neither plausible R nor plausible
   log10(1/R) (median < 0, or values beyond -1 to 6) is tagged
   "Needs review: units unclear" and left unchanged. If half or more of
   a mineral's files fail this check, ALL of that mineral's files are
   flagged, because the whole set was probably exported differently.

Files tagged "Excluded: ..." or "Needs review: ..." are skipped by
analyze_carbonate_mineral_spectra.py.

USAGE:
    python3 harmonize_er_ir_database.py input.db output.db
Writes a CSV report next to the output database.
"""
import sqlite3, shutil, sys, re, hashlib, json, csv, os
from datetime import datetime
from collections import defaultdict
import numpy as np

R_MEDIAN_MAX, R_MIN, R_MAX = 0.2, -0.01, 1.5
VERIFY_LOW, VERIFY_HIGH = 0.5, 2.0
R_FLOOR = 1e-4

TAG_DUP = "Excluded: duplicate export"
TAG_CONV = "Converted: R to log10(1/R)"
TAG_REVIEW = "Needs review: units unclear"


def scan_key(fn):
    """Sort 'Calcite_1_10.dpt' after 'Calcite_1_9.dpt' (numeric, not alphabetical)."""
    nums = re.findall(r"\d+", fn)
    return [int(n) for n in nums]


def tag(cur, spectrum_id, label):
    cur.execute("INSERT OR IGNORE INTO Tag (TagLabel) VALUES (?)", (label,))
    tag_id = cur.execute("SELECT TagID FROM Tag WHERE TagLabel = ?", (label,)).fetchone()[0]
    cur.execute("INSERT OR IGNORE INTO TaggedEntity (TagID, EntityType, EntityID) VALUES (?, 'Spectrum', ?)",
                (tag_id, spectrum_id))


def add_note(cur, spectrum_id, text):
    cur.execute("UPDATE Spectrum SET Notes = COALESCE(Notes || ' | ', '') || ? WHERE SpectrumID = ?",
                (text, spectrum_id))


def main(src, dst):
    if os.path.abspath(src) == os.path.abspath(dst):
        sys.exit("Output must be a different file from the input.")
    shutil.copyfile(src, dst)
    conn = sqlite3.connect(dst)
    cur = conn.cursor()
    now = datetime.now().isoformat(timespec="seconds")

    rows = cur.execute("""
        SELECT sp.SpectrumID, sp.SourceFilename, mat.MaterialName
        FROM Spectrum sp
        JOIN AcquisitionModeType amt ON amt.AcquisitionModeID = sp.AcquisitionModeID
        JOIN Measurement m ON m.MeasurementID = sp.MeasurementID
        JOIN Sample s ON s.SampleID = m.SampleID
        JOIN Material mat ON mat.MaterialID = s.MaterialID
        WHERE amt.ModeName = 'ER-IR'
    """).fetchall()
    rows.sort(key=lambda r: (r[2], scan_key(r[1])))

    spectra = {}
    for sid, fn, mat in rows:
        d = np.array(cur.execute(
            "SELECT DataPointID, Wavenumber, Intensity FROM SpectralDataPoint "
            "WHERE SpectrumID = ? ORDER BY Wavenumber DESC", (sid,)).fetchall())
        spectra[sid] = dict(fn=fn, mat=mat, ids=d[:, 0].astype(int), wn=d[:, 1], y=d[:, 2])

    report = {sid: dict(file=s["fn"], mineral=s["mat"], status="native log10(1/R)", detail="")
              for sid, s in spectra.items()}

    # 1. Duplicates
    groups = defaultdict(list)
    for sid, _, _ in rows:
        s = spectra[sid]
        h = hashlib.sha256(np.round(np.column_stack([s["wn"], s["y"]]), 6).tobytes()).hexdigest()
        groups[h].append(sid)
    duplicates = set()
    for sids in groups.values():
        keep = sids[0]
        for sid in sids[1:]:
            duplicates.add(sid)
            tag(cur, sid, TAG_DUP)
            add_note(cur, sid, f"Duplicate of {spectra[keep]['fn']}")
            report[sid].update(status="excluded: duplicate", detail=f"duplicate of {spectra[keep]['fn']}")

    # 2-3. Classify units
    cls = {}
    for sid, s in spectra.items():
        y = s["y"]; med = np.median(y)
        if med < R_MEDIAN_MAX and y.min() > R_MIN and y.max() < R_MAX:
            cls[sid] = "R"
        elif med < 0 or y.min() < -1 or y.max() > 6:
            cls[sid] = "review"
        else:
            cls[sid] = "log"

    native_medians = defaultdict(list)
    # If half or more of a mineral's files are implausible, the whole set is
    # suspect (e.g., exported with a different processing step): flag all of it.
    by_mat = defaultdict(list)
    for sid, s in spectra.items():
        by_mat[s["mat"]].append(sid)
    whole_set_review = set()
    for mat, sids in by_mat.items():
        if sum(cls[sid] == "review" for sid in sids) >= len(sids) / 2:
            whole_set_review.add(mat)
            for sid in sids:
                cls[sid] = "review"

    for sid, s in spectra.items():
        if cls[sid] == "log" and sid not in duplicates:
            native_medians[s["mat"]].append(np.median(s["y"]))

    for sid, s in spectra.items():
        if cls[sid] == "review":
            tag(cur, sid, TAG_REVIEW)
            report[sid].update(status=report[sid]["status"] + " | needs review" if sid in duplicates else "needs review",
                               detail=(report[sid]["detail"] + "; " if report[sid]["detail"] else "")
                               + f"values {s['y'].min():.3g} to {s['y'].max():.3g}, median {np.median(s['y']):.3g}")
            continue
        if cls[sid] != "R":
            continue
        n_floor = int((s["y"] <= R_FLOOR).sum())
        conv = -np.log10(np.clip(s["y"], R_FLOOR, None))
        ref = np.median(native_medians[s["mat"]]) if native_medians[s["mat"]] else None
        conv_med = np.median(conv)
        if ref is None or not (VERIFY_LOW * ref <= conv_med <= VERIFY_HIGH * ref):
            tag(cur, sid, TAG_REVIEW)
            why = "no native files to verify against" if ref is None else \
                  f"converted median {conv_med:.2f} vs native median {ref:.2f}"
            report[sid].update(status="needs review", detail=f"looks like R but failed verification ({why})")
            continue
        cur.executemany("UPDATE SpectralDataPoint SET Intensity = ? WHERE DataPointID = ?",
                        [(float(v), int(i)) for v, i in zip(conv, s["ids"])])
        tag(cur, sid, TAG_CONV)
        params = dict(formula="log10(1/R) = -log10(R)", reflectance_floor=R_FLOOR,
                      points_floored=n_floor, original_median=round(float(np.median(s["y"])), 5),
                      converted_median=round(float(conv_med), 4),
                      mineral_native_median=round(float(ref), 4))
        cur.execute("INSERT INTO Preprocessing (SpectrumID, StepType, Parameters, DateTime) VALUES (?, ?, ?, ?)",
                    (sid, "Unit conversion: R to log10(1/R)", json.dumps(params), now))
        add_note(cur, sid, "Exported as reflectance; converted to log10(1/R)")
        detail = f"converted median {conv_med:.2f} vs native {ref:.2f}"
        if n_floor:
            detail += f"; {n_floor} points at or below zero set to floor"
        if sid in duplicates:
            report[sid]["status"] += " | converted"
            report[sid]["detail"] += "; " + detail
        else:
            report[sid].update(status="converted from R", detail=detail)

    conn.commit()
    conn.close()

    out = os.path.splitext(dst)[0] + "_harmonization_report.csv"
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["mineral", "file", "status", "detail"])
        w.writeheader()
        for sid, _, _ in rows:
            w.writerow(report[sid])

    counts = defaultdict(lambda: defaultdict(int))
    for r in report.values():
        for k in ("excluded: duplicate", "converted", "needs review"):
            if k in r["status"]:
                counts[r["mineral"]][k] += 1
    print(f"Harmonized copy written to {dst}\nReport written to {out}\n")
    print(f"{'Mineral':<12}{'Files':>6}{'Dupes':>7}{'Converted':>11}{'Review':>8}")
    for mat in sorted({s['mat'] for s in spectra.values()}):
        n = sum(1 for s in spectra.values() if s["mat"] == mat)
        c = counts[mat]
        print(f"{mat:<12}{n:>6}{c['excluded: duplicate']:>7}{c['converted']:>11}{c['needs review']:>8}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("Usage: python3 harmonize_er_ir_database.py input.db output.db")
    main(sys.argv[1], sys.argv[2])
