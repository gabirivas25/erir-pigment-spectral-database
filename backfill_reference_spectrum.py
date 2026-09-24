"""
Backfill script: links every ER-IR Spectrum to its mineral's ATR standard,
via the Spectrum.ReferenceSpectrumID self-referencing foreign key.

WHEN TO RUN THIS:
Run it any time a new ATR standard is added to the database (e.g. once
Magnetite's ATR standard is re-scanned and added), so that mineral's
existing ER-IR scans get linked to it automatically. Safe to re-run at
any time -- it only ever updates rows that are missing a link, and will
not overwrite a ReferenceSpectrumID that is already set.

USAGE:
    python3 backfill_reference_spectrum.py path/to/your_database.db

If no path is given, it defaults to er_ir_pigment_spectral_standards_sqlite.db
in the current directory.
"""

import sqlite3
import sys


def backfill(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Step 1: find each material's ATR spectrum.
    # If a material has more than one ATR spectrum, this flags it rather
    # than silently picking one -- that situation needs a human decision,
    # not an automatic guess.
    cur.execute("""
        SELECT mat.MaterialID, mat.MaterialName, sp.SpectrumID
        FROM Spectrum sp
        JOIN AcquisitionModeType amt ON amt.AcquisitionModeID = sp.AcquisitionModeID
        JOIN Measurement m ON m.MeasurementID = sp.MeasurementID
        JOIN Sample s ON s.SampleID = m.SampleID
        JOIN Material mat ON mat.MaterialID = s.MaterialID
        WHERE amt.ModeName = 'ATR'
    """)
    atr_rows = cur.fetchall()

    atr_by_material = {}
    seen_multiple = set()
    for material_id, material_name, spectrum_id in atr_rows:
        if material_id in atr_by_material:
            seen_multiple.add(material_name)
        else:
            atr_by_material[material_id] = spectrum_id

    if seen_multiple:
        print(f"WARNING: these materials have more than one ATR spectrum, "
              f"skipped automatic linking for them -- resolve manually: {seen_multiple}")
        for name in seen_multiple:
            for material_id, mname, _ in atr_rows:
                if mname == name:
                    atr_by_material.pop(material_id, None)

    print(f"ATR spectrum found for {len(atr_by_material)} material(s): "
          f"{sorted(atr_by_material.keys())}")

    # Step 2: find ER-IR spectra that don't yet have a ReferenceSpectrumID set.
    cur.execute("""
        SELECT sp.SpectrumID, mat.MaterialID, mat.MaterialName
        FROM Spectrum sp
        JOIN AcquisitionModeType amt ON amt.AcquisitionModeID = sp.AcquisitionModeID
        JOIN Measurement m ON m.MeasurementID = sp.MeasurementID
        JOIN Sample s ON s.SampleID = m.SampleID
        JOIN Material mat ON mat.MaterialID = s.MaterialID
        WHERE amt.ModeName = 'ER-IR' AND sp.ReferenceSpectrumID IS NULL
    """)
    unlinked = cur.fetchall()
    print(f"Found {len(unlinked)} ER-IR spectra currently missing a reference link.")

    updated = 0
    still_missing = []
    for spectrum_id, material_id, material_name in unlinked:
        if material_id in atr_by_material:
            cur.execute(
                "UPDATE Spectrum SET ReferenceSpectrumID = ? WHERE SpectrumID = ?",
                (atr_by_material[material_id], spectrum_id),
            )
            updated += 1
        else:
            still_missing.append(material_name)

    conn.commit()

    print(f"Updated: {updated} ER-IR spectra newly linked to their ATR standard.")
    if still_missing:
        unique_missing = sorted(set(still_missing))
        print(f"Still missing an ATR standard, left unlinked: {unique_missing}")
    else:
        print("Every mineral now has an ATR standard and every ER-IR spectrum is linked.")

    conn.close()


if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "er_ir_pigment_spectral_standards_sqlite.db"
  