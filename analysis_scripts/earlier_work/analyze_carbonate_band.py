"""
Quantitative analysis of a mineral's spectral behavior, using its main
carbonate absorption band as the diagnostic feature, across all of that
mineral's ER-IR scans, compared against its ATR standard.

This script is written for carbonate minerals specifically (Calcite,
Aragonite, Dolomite, Cerussite, etc.), since they share a common
diagnostic feature, the carbonate ion's asymmetric stretch. The mineral
being analyzed is the subject of the analysis; the carbonate band is
simply the specific feature used to characterize it.

WHAT THIS DOES, IN PLAIN TERMS:
For each ER-IR scan of the chosen mineral, this script looks at a fixed
wavenumber window expected to contain that mineral's main carbonate band,
and finds:
  1. The peak position and height within that window (the tallest point)
  2. The lowest point within that window (to detect a dip below the
     absorbance zero-line, which indicates an inverted/derivative-shaped
     band -- a hallmark of reststrahlen distortion)
It then reports the range of variation across all scans, and separately
for each physical specimen (parsed from the filename, e.g. "Calcite_1_0"
is specimen 1, scan 0).

HOW TO ADAPT THIS FOR MATLAB:
The core logic is three operations MATLAB handles identically:
  - Read (wavenumber, intensity) pairs for a given SpectrumID
    -> in MATLAB: use a SQLite connector (e.g. the Database Toolbox's
       sqlite() function) and run the same SQL query below.
  - Restrict to a wavenumber window and find max/min
    -> in MATLAB: logical indexing (wn >= lo & wn <= hi), then max()/min()
  - Group results by specimen number parsed from the filename
    -> in MATLAB: regexp() or split on underscores, same as here.

WHY THE WINDOW IS 1300-1800 cm-1, NOT A NARROWER RANGE:
An earlier version of this analysis used a 1350-1600 cm-1 window. Several
scans' peaks landed exactly on the window's upper edge (1599.8 cm-1),
which is a red flag: it means the true peak may lie outside the window,
and the window was clipping it rather than genuinely capturing it. The
window was widened to 1300-1800 cm-1 specifically to remove this
boundary-clipping artifact. Always check for this: if any result's peak
or minimum sits exactly at your window's edge, the window is too narrow.

USAGE:
    python3 analyze_carbonate_band.py <path_to_database.db> <MaterialName>

Example:
    python3 analyze_carbonate_band.py er_ir_pigment_spectral_standards_sqlite.db Calcite
"""

import sqlite3
import sys
import numpy as np

# The wavenumber window searched for the main band, in cm-1.
# Adjust this per mineral -- the right window is wherever that mineral's
# own main diagnostic band actually falls; check a plot first.
WINDOW_LOW = 1300
WINDOW_HIGH = 1800


def get_spectrum(cur, spectrum_id):
    """Return (wavenumber array, intensity array) for one SpectrumID,
    sorted from high to low wavenumber (standard IR convention)."""
    cur.execute(
        "SELECT Wavenumber, Intensity FROM SpectralDataPoint "
        "WHERE SpectrumID = ? ORDER BY Wavenumber DESC",
        (spectrum_id,),
    )
    rows = cur.fetchall()
    wn = np.array([r[0] for r in rows])
    intensity = np.array([r[1] for r in rows])
    return wn, intensity


def analyze_one_scan(wn, intensity, lo=WINDOW_LOW, hi=WINDOW_HIGH):
    """Find the peak and the minimum within [lo, hi] cm-1.
    Returns (peak_wn, peak_value, min_wn, min_value, dips_below_zero)."""
    mask = (wn >= lo) & (wn <= hi)
    region_wn = wn[mask]
    region_intensity = intensity[mask]

    peak_idx = np.argmax(region_intensity)
    min_idx = np.argmin(region_intensity)

    peak_wn = region_wn[peak_idx]
    peak_value = region_intensity[peak_idx]
    min_wn = region_wn[min_idx]
    min_value = region_intensity[min_idx]
    dips_below_zero = min_value < 0

    return peak_wn, peak_value, min_wn, min_value, dips_below_zero


def specimen_number(filename):
    """Extract the physical specimen number from a filename like
    'Calcite_1_0.dpt' -> '1'. Assumes the MaterialName_Specimen_Scan
    naming convention used throughout this database."""
    parts = filename.replace(".dpt", "").split("_")
    return parts[1] if len(parts) >= 2 else "unknown"


def main(db_path, material_name):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Get every ER-IR scan for this material
    cur.execute(
        """
        SELECT sp.SpectrumID, sp.SourceFilename
        FROM Spectrum sp
        JOIN AcquisitionModeType amt ON amt.AcquisitionModeID = sp.AcquisitionModeID
        JOIN Measurement m ON m.MeasurementID = sp.MeasurementID
        JOIN Sample s ON s.SampleID = m.SampleID
        JOIN Material mat ON mat.MaterialID = s.MaterialID
        WHERE mat.MaterialName = ? AND amt.ModeName = 'ER-IR'
        ORDER BY sp.SourceFilename
        """,
        (material_name,),
    )
    scans = cur.fetchall()

    if not scans:
        print(f"No ER-IR scans found for material '{material_name}'.")
        return

    print(f"{'Scan':<20}{'PeakWN':<10}{'PeakVal':<10}{'MinWN':<10}{'MinVal':<10}{'DipBelow0'}")
    results = []
    for spectrum_id, filename in scans:
        wn, intensity = get_spectrum(cur, spectrum_id)
        peak_wn, peak_val, min_wn, min_val, dips = analyze_one_scan(wn, intensity)
        specimen = specimen_number(filename)
        results.append(dict(
            filename=filename, specimen=specimen,
            peak_wn=peak_wn, peak_val=peak_val,
            min_wn=min_wn, min_val=min_val, dips=dips,
        ))
        print(f"{filename:<20}{peak_wn:<10.1f}{peak_val:<10.3f}{min_wn:<10.1f}{min_val:<10.3f}{dips}")

    # --- Warn if any result sits exactly on the window edge (clipping check) ---
    edge_hits = [r for r in results if r["peak_wn"] in (WINDOW_LOW, WINDOW_HIGH)
                 or r["min_wn"] in (WINDOW_LOW, WINDOW_HIGH)]
    if edge_hits:
        print(f"\nWARNING: {len(edge_hits)} scan(s) have a peak or minimum exactly at the "
              f"window edge ({WINDOW_LOW} or {WINDOW_HIGH} cm-1). The window may be clipping "
              f"the true feature -- consider widening WINDOW_LOW/WINDOW_HIGH and re-running.")

    # --- Summary statistics ---
    peak_vals = [r["peak_val"] for r in results]
    dip_count = sum(1 for r in results if r["dips"])

    print(f"\nPeak intensity range: {min(peak_vals):.3f} to {max(peak_vals):.3f} "
          f"({max(peak_vals) / min(peak_vals):.1f}x variation)")
    print(f"Scans with a dip below zero (inverted/derivative character): {dip_count} of {len(results)}")

    specimens = sorted(set(r["specimen"] for r in results))
    for spec in specimens:
        spec_results = [r for r in results if r["specimen"] == spec]
        spec_dips = sum(1 for r in spec_results if r["dips"])
        spec_mean_peak_wn = np.mean([r["peak_wn"] for r in spec_results])
        print(f"  Specimen {spec} (n={len(spec_results)}): {spec_dips} show dip below zero, "
              f"mean peak position {spec_mean_peak_wn:.1f} cm-1")

    conn.close()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 analyze_carbonate_band.py <path_to_database.db> <MaterialName>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
