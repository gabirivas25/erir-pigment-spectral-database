"""
Quantitative analysis of a mineral's spectral behavior, using its main
carbonate absorption band as the diagnostic feature, across all of that
mineral's ER-IR scans, compared against its ATR standard.

Script Name: analyze_carbonate_mineral_spectra.py

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
    python3 analyze_carbonate_mineral_spectra.py   [window_low] [window_high]

The window bounds are optional; if omitted, they default to 1300-1800 cm-1
(validated for Calcite). ALWAYS validate the window for each new mineral
before trusting its results -- different carbonates have their main band
at different positions (e.g., Calcite's ATR peak is at 1395.7 cm-1;
Aragonite's is at 1452.0 cm-1). Check a few real ER-IR scans first to
confirm the chosen window does not clip the peak or minimum at either edge.

Examples:
    python3 analyze_carbonate_mineral_spectra.py er_ir_pigment_spectral_standards_sqlite.db Calcite
    python3 analyze_carbonate_mineral_spectra.py er_ir_pigment_spectral_standards_sqlite.db Aragonite 1200 1900
"""

import sqlite3
import sys
import numpy as np
from scipy.signal import find_peaks

# Default wavenumber window, validated for Calcite specifically.
# Override via command-line arguments for other minerals -- see USAGE above.
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


def analyze_one_scan(wn, intensity, lo=WINDOW_LOW, hi=WINDOW_HIGH, prominence_fraction=0.15):
    """Find the peak and the minimum within [lo, hi] cm-1, and classify
    the scan's distortion character using two tiers, matching Section
    4.1.1's documented two-stage method:

    TIER 1 -- Severe / baseline-crossing inversion (Imin < 0):
    The primary, simplest test. A trough value falling below the
    absolute zero baseline is unambiguous evidence of a severe,
    baseline-crossing inverted band.

    TIER 2 -- Derivative-shaped, local-slope check (prominence-based):
    Tier 1 alone misses a real case: a scan can show a genuine local
    trough-then-peak shape, the hallmark of reststrahlen distortion,
    while the whole curve sits on an elevated baseline that keeps the
    trough above zero. This tier tests for a genuine LOCAL peak and a
    genuine LOCAL trough within the window, using prominence (how much
    a feature stands out from its immediate surroundings) rather than
    an absolute zero line. Prominence is scaled to each scan's own
    intensity range within the window (prominence_fraction), since peak
    heights vary by two orders of magnitude across this dataset; a
    fixed absolute prominence threshold would be too strict for
    low-intensity scans and too lenient for high-intensity ones.

    Every Tier 1 case is automatically also a Tier 2 case (a trough
    below zero is, by definition, a real local trough). Tier 2 is the
    more complete classification; Tier 1 is reported separately because
    it identifies the more severe subset specifically.

    Returns (peak_wn, peak_value, min_wn, min_value,
             is_severe_inversion, is_derivative_shaped).
    """
    mask = (wn >= lo) & (wn <= hi)
    region_wn = wn[mask]
    region_intensity = intensity[mask]

    peak_idx = np.argmax(region_intensity)
    min_idx = np.argmin(region_intensity)
    peak_wn = region_wn[peak_idx]
    peak_value = region_intensity[peak_idx]
    min_wn = region_wn[min_idx]
    min_value = region_intensity[min_idx]

    # Tier 1: severe, baseline-crossing inversion
    is_severe_inversion = min_value < 0

    # Tier 2: local-slope check via prominence, scaled to this scan's own range
    scan_range = region_intensity.max() - region_intensity.min()
    min_prominence = scan_range * prominence_fraction
    local_peaks, _ = find_peaks(region_intensity, prominence=min_prominence)
    local_troughs, _ = find_peaks(-region_intensity, prominence=min_prominence)
    is_derivative_shaped = len(local_peaks) > 0 and len(local_troughs) > 0

    return peak_wn, peak_value, min_wn, min_value, is_severe_inversion, is_derivative_shaped


def specimen_number(filename):
    """Extract the physical specimen number from a filename like
    'Calcite_1_0.dpt' -> '1'. Assumes the MaterialName_Specimen_Scan
    naming convention used throughout this database."""
    parts = filename.replace(".dpt", "").split("_")
    return parts[1] if len(parts) >= 2 else "unknown"


def main(db_path, material_name, window_low=WINDOW_LOW, window_high=WINDOW_HIGH):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    print(f"Using diagnostic window: {window_low}-{window_high} cm-1\n")

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

    print(f"{'Scan':<20}{'PeakWN':<10}{'PeakVal':<10}{'MinWN':<10}{'MinVal':<10}{'Severe':<8}{'DerivShape'}")
    results = []
    for spectrum_id, filename in scans:
        wn, intensity = get_spectrum(cur, spectrum_id)
        peak_wn, peak_val, min_wn, min_val, is_severe, is_deriv = analyze_one_scan(
            wn, intensity, lo=window_low, hi=window_high)
        specimen = specimen_number(filename)
        results.append(dict(
            filename=filename, specimen=specimen,
            peak_wn=peak_wn, peak_val=peak_val,
            min_wn=min_wn, min_val=min_val,
            is_severe=is_severe, is_deriv=is_deriv,
        ))
        print(f"{filename:<20}{peak_wn:<10.1f}{peak_val:<10.3f}{min_wn:<10.1f}{min_val:<10.3f}{str(is_severe):<8}{is_deriv}")

    # --- Warn if any result sits exactly on the window edge (clipping check) ---
    edge_hits = [r for r in results if r["peak_wn"] in (window_low, window_high)
                 or r["min_wn"] in (window_low, window_high)]
    if edge_hits:
        print(f"\nWARNING: {len(edge_hits)} scan(s) have a peak or minimum exactly at the "
              f"window edge ({window_low} or {window_high} cm-1). The window may be clipping "
              f"the true feature -- consider widening the window and re-running.")

    # --- Summary statistics ---
    peak_vals = [r["peak_val"] for r in results]
    severe_count = sum(1 for r in results if r["is_severe"])
    deriv_count = sum(1 for r in results if r["is_deriv"])

    print(f"\nPeak intensity range: {min(peak_vals):.3f} to {max(peak_vals):.3f} "
          f"({max(peak_vals) / min(peak_vals):.1f}x variation)")
    print(f"Tier 1 -- Severe, baseline-crossing inversion (Imin < 0): {severe_count} of {len(results)}")
    print(f"Tier 2 -- Derivative-shaped, local-slope check (includes all Tier 1 cases): {deriv_count} of {len(results)}")

    specimens = sorted(set(r["specimen"] for r in results))
    for spec in specimens:
        spec_results = [r for r in results if r["specimen"] == spec]
        spec_severe = sum(1 for r in spec_results if r["is_severe"])
        spec_deriv = sum(1 for r in spec_results if r["is_deriv"])
        spec_mean_peak_wn = np.mean([r["peak_wn"] for r in spec_results])
        print(f"  Specimen {spec} (n={len(spec_results)}): {spec_severe} severe / {spec_deriv} derivative-shaped, "
              f"mean peak position {spec_mean_peak_wn:.1f} cm-1")

    conn.close()


if __name__ == "__main__":
    if len(sys.argv) not in (3, 5):
        print("Usage: python3 analyze_carbonate_mineral_spectra.py   [window_low] [window_high]")
        sys.exit(1)
    if len(sys.argv) == 5:
        main(sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4]))
    else:
        main(sys.argv[1], sys.argv[2])
