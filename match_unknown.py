#!/usr/bin/env python3
"""Match an unknown spectrum against the ER-IR standards in pigment_spectral_standards.db

Usage:
    python match_unknown.py FILE [--db pigment_spectral_standards.db] [--from-transmittance] [--top 5]

FILE can be:
    .txt / .csv / .dpt (plain text)  two columns: wavenumber, intensity
    .dpt (Bruker OPUS binary)        needs:  pip install brukeropus
    .asc (Perkin-Elmer ASCII)        two columns after a "#DATA" line

The database holds ABSORBANCE. If your file is %T, add --from-transmittance
(absorbance = 2 - log10(%T)). That conversion is for trying things out only.
To load a batch that was exported as %T, mark it in scan_batches.csv instead (see WORKFLOW.md).

Methods (the same as the Match screen design):
  pearson  SNV, then Pearson correlation on a common grid (650-3990 cm-1, 800 points)
  deriv    Savitzky-Golay first derivative (window 11, order 2), SNV, Pearson
  peaks    SNV, peak picking (prominence >= 0.5, >= 20 cm-1 apart), peaks matched within 8 cm-1,
           score = 2 * matched / (peaks in unknown + peaks in standard)
A material's score is the best score among its ER-IR scans.
A high score means a similar spectral shape, not a confirmed identification.
"""
import argparse, json, os, re, sqlite3, sys
import numpy as np
from scipy.signal import savgol_filter, find_peaks

GRID = np.linspace(650.0, 3990.0, 800)
STEP = GRID[1] - GRID[0]
NAME_RE = re.compile(r"^(?P<key>.+?)_ER_IR_(?P<rest>[\d_]+)$", re.I)


def read_spectrum(path, from_transmittance=False):
    ext = os.path.splitext(path)[1].lower()
    with open(path, "rb") as fh:
        head = fh.read(4)
    x = y = None
    if ext in (".dpt", ".0") and not _looks_like_text(path):
        try:
            import brukeropus
        except ImportError:
            sys.exit("This looks like a Bruker OPUS binary file. Install the reader first:  pip install brukeropus")
        o = brukeropus.read_opus(path)
        key = o.data_keys[0]
        d = getattr(o, key)
        x, y = np.array(d.x, float), np.array(d.y, float)
    else:
        text = open(path, encoding="utf-8-sig", errors="replace").read()
        if "#DATA" in text:                       # Perkin-Elmer ASCII
            text = text.split("#DATA", 1)[1]
        xs, ys = [], []
        for line in text.splitlines():
            parts = re.split(r"[,;\t ]+", line.strip())
            if len(parts) < 2:
                continue
            try:
                xs.append(float(parts[0])); ys.append(float(parts[1]))
            except ValueError:
                continue
        x, y = np.array(xs), np.array(ys)
    if len(x) < 100:
        sys.exit("Fewer than 100 numeric rows: not a two-column spectrum.")
    o = np.argsort(x)
    x, y = x[o], y[o]
    if from_transmittance:
        y = 2.0 - np.log10(np.clip(y, 0.01, None))
    return x, y


def _looks_like_text(path):
    with open(path, "rb") as fh:
        chunk = fh.read(2000)
    try:
        s = chunk.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return sum(c.isdigit() or c in ".,;\t \r\n-+eE" for c in s) / max(1, len(s)) > 0.8


def resample(x, y):
    if x.min() > 700 or x.max() < 3900:
        sys.exit("Range %.0f to %.0f cm-1 does not cover 700 to 3900 cm-1." % (x.min(), x.max()))
    return np.interp(GRID, x, y)


def snv(a):
    s = a.std()
    if s == 0:
        sys.exit("The spectrum is constant after resampling; nothing to match.")
    return (a - a.mean()) / s


def prep(a, method):
    if method == "deriv":
        a = savgol_filter(a, 11, 2, deriv=1)
    return snv(a)


def peaks_of(a):
    p, _ = find_peaks(a, prominence=0.5, distance=max(1, int(round(20 / STEP))))
    return GRID[p]


def peak_score(pu, ps, tol=8.0):
    if len(pu) + len(ps) == 0:
        return 0.0
    used, m = set(), 0
    for u in pu:
        best, bd = None, tol + 1
        for j, s in enumerate(ps):
            d = abs(u - s)
            if j not in used and d <= tol and d < bd:
                best, bd = j, d
        if best is not None:
            used.add(best); m += 1
    return 2.0 * m / (len(pu) + len(ps))


def load_standards(db):
    con = sqlite3.connect(db)
    rows = con.execute("""SELECT f.FilePath, m.SpectrumData FROM Measurement m
        JOIN SpectralFile f ON f.MeasurementID = m.MeasurementID
        JOIN AcquisitionModeType a ON a.AcquisitionModeID = m.AcquisitionModeID
        WHERE a.ModeName = 'ER-IR' ORDER BY f.FilePath""").fetchall()
    std = []
    for path, data in rows:
        sid = path.split("/")[-1].rsplit(".", 1)[0]
        mm = NAME_RE.match(sid)
        if not mm:
            continue
        d = np.array(json.loads(data))
        d = d[np.argsort(d[:, 0])]
        std.append({"id": sid, "material": mm.group("key").lower(), "raw": np.interp(GRID, d[:, 0], d[:, 1])})
    return std


def rank(unknown, std, method):
    u = prep(unknown, method)
    pu = peaks_of(u) if method == "peaks" else None
    best = {}
    for s in std:
        v = prep(s["raw"], method)
        if method == "peaks":
            sc = peak_score(pu, peaks_of(v))
        else:
            sc = float(np.corrcoef(u, v)[0, 1])
        if s["material"] not in best or sc > best[s["material"]][0]:
            best[s["material"]] = (sc, s["id"])
    return sorted(((m, sc, i) for m, (sc, i) in best.items()), key=lambda t: -t[1])


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description="Match an unknown spectrum against the ER-IR standards.")
    ap.add_argument("file")
    ap.add_argument("--db", default=os.path.join(here, "pigment_spectral_standards.db"))
    ap.add_argument("--from-transmittance", action="store_true", help="file is in %%T; convert to absorbance")
    ap.add_argument("--top", type=int, default=5)
    a = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    std = load_standards(a.db)
    x, y = read_spectrum(a.file, a.from_transmittance)
    print("File: %s  (%d points, %.0f to %.0f cm-1)" % (os.path.basename(a.file), len(x), x.min(), x.max()))
    print("Standards compared: %d ER-IR scans" % len(std))
    g = resample(x, y)
    for method in ("pearson", "deriv", "peaks"):
        print("\n== %s ==" % method)
        for r, (m, sc, i) in enumerate(rank(g, std, method)[:a.top], 1):
            print("%d. %-22s %.3f   (best scan %s)" % (r, m, sc, i))
    print("\nA high score means a similar spectral shape, not a confirmed identification.")


if __name__ == "__main__":
    main()
