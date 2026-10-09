"""
carbonate_statistics.py

Statistical evaluation and multivariate analysis of one mineral's ER-IR
scans (Section 4.1.3 framework), run on the HARMONIZED database.

  1. Descriptive statistics (mean, median, SD, CV, min, max, fold range)
     of the nu3 window maximum, window minimum, and peak position,
     per specimen.
  2. Two-sample tests on band positions between specimens: Student's t,
     Welch's t (unequal variances), and Mann-Whitney U (no normality
     assumption), plus Levene's test for equal variances.
  3. PCA on full spectra (4000-600 cm-1), on raw log10(1/R) and after
     SNV normalization (removes overall intensity, keeps shape).
  4. Hierarchical clustering: Ward/Euclidean and average/cosine, on raw
     and SNV data. Agreement with specimen labels = adjusted Rand index.

Scans tagged "Excluded:" or "Needs review:" are skipped. Use --exclude to
drop further scans for a sensitivity check.

USAGE:
  python3 carbonate_statistics.py er_ir_harmonized.db Calcite 1300 1800
  python3 carbonate_statistics.py er_ir_harmonized.db Calcite 1300 1800 --exclude Calcite_2_1 Calcite_2_5
Writes <Mineral>_PCA_raw.png, <Mineral>_PCA_SNV.png and
<Mineral>_dendrogram_Ward.png in the current folder.
"""
import sqlite3, sys, argparse
import numpy as np
from scipy import stats
from scipy.cluster.hierarchy import linkage, fcluster, dendrogram
from sklearn.decomposition import PCA
from sklearn.metrics import adjusted_rand_score, silhouette_score
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Band windows for position tests: (label, low, high, 'max' or 'min')
BANDS = {
    "Calcite": [("nu3 maximum (~1630)", 1580, 1700, "max"),
                ("nu3 minimum (~1510)", 1470, 1560, "min"),
                ("nu1+nu4 (~1800)", 1780, 1820, "max"),
                ("nu4 (~715)", 700, 730, "max")],
}


def load(db, mineral, exclude):
    cur = sqlite3.connect(db).cursor()
    rows = cur.execute("""
        SELECT sp.SpectrumID, sp.SourceFilename FROM Spectrum sp
        JOIN AcquisitionModeType amt ON amt.AcquisitionModeID = sp.AcquisitionModeID
        JOIN Measurement m ON m.MeasurementID = sp.MeasurementID
        JOIN Sample s ON s.SampleID = m.SampleID
        JOIN Material mat ON mat.MaterialID = s.MaterialID
        WHERE mat.MaterialName = ? AND amt.ModeName = 'ER-IR'
          AND sp.SpectrumID NOT IN (
            SELECT te.EntityID FROM TaggedEntity te JOIN Tag t ON t.TagID = te.TagID
            WHERE te.EntityType = 'Spectrum'
              AND (t.TagLabel LIKE 'Excluded:%' OR t.TagLabel LIKE 'Needs review:%'))""",
        (mineral,)).fetchall()
    names, spec, Y, wn = [], [], [], None
    for sid, fn in sorted(rows, key=lambda r: [int(x) for x in r[1].replace('.dpt', '').split('_')[1:]]):
        name = fn.replace(".dpt", "")
        if name in exclude:
            continue
        d = np.array(cur.execute("SELECT Wavenumber, Intensity FROM SpectralDataPoint "
                                 "WHERE SpectrumID = ? ORDER BY Wavenumber DESC", (sid,)).fetchall())
        if wn is None:
            wn = d[:, 0]
        elif len(d) != len(wn) or not np.allclose(d[:, 0], wn):
            sys.exit(f"{name} is on a different wavenumber grid; interpolate before multivariate analysis.")
        names.append(name); spec.append(int(name.split("_")[1])); Y.append(d[:, 1])
    return names, np.array(spec), wn, np.array(Y)


def extremum(wn, y, lo, hi, kind):
    """Position of the max/min in [lo, hi], refined by a 3-point parabola
    (sub-grid precision; the grid spacing is ~2 cm-1)."""
    idx = np.where((wn >= lo) & (wn <= hi))[0]
    k = idx[np.argmax(y[idx]) if kind == "max" else np.argmin(y[idx])]
    if k in (idx[0], idx[-1]):
        return wn[k], True  # at window edge: flag
    y0, y1, y2 = y[k - 1], y[k], y[k + 1]
    denom = y0 - 2 * y1 + y2
    shift = 0.5 * (y0 - y2) / denom if denom != 0 else 0.0
    return wn[k] + shift * (wn[k + 1] - wn[k]), False


def describe(v):
    v = np.asarray(v)
    return dict(n=len(v), mean=v.mean(), median=np.median(v), sd=v.std(ddof=1),
                cv=100 * v.std(ddof=1) / abs(v.mean()), min=v.min(), max=v.max())


def snv(Y):
    return (Y - Y.mean(1, keepdims=True)) / Y.std(1, keepdims=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("db"); ap.add_argument("mineral")
    ap.add_argument("lo", type=float); ap.add_argument("hi", type=float)
    ap.add_argument("--exclude", nargs="*", default=[])
    a = ap.parse_args()
    names, spec, wn, Y = load(a.db, a.mineral, set(a.exclude))
    groups = sorted(set(spec))
    print(f"{a.mineral}: {len(names)} scans " + ", ".join(f"Specimen {g} n={sum(spec == g)}" for g in groups))
    if a.exclude:
        print("Additionally excluded:", ", ".join(a.exclude))

    # 1. Descriptive statistics
    w = (wn >= a.lo) & (wn <= a.hi)
    metrics = {"nu3 window maximum": Y[:, w].max(1),
               "nu3 window minimum": Y[:, w].min(1)}
    print("\n1. DESCRIPTIVE STATISTICS (log10(1/R), window %g-%g cm-1)" % (a.lo, a.hi))
    print(f"{'Metric':<22}{'Group':<12}{'n':>3}{'Mean':>8}{'Median':>8}{'SD':>8}{'CV%':>7}{'Min':>8}{'Max':>8}{'Fold':>7}")
    for m, v in metrics.items():
        for g in ["All"] + groups:
            sel = v if g == "All" else v[spec == g]
            d = describe(sel)
            fold = f"{d['max'] / d['min']:.2f}" if d["min"] > 0 else "n/a"
            print(f"{m:<22}{str(g if g == 'All' else 'Specimen ' + str(g)):<12}{d['n']:>3}{d['mean']:>8.3f}"
                  f"{d['median']:>8.3f}{d['sd']:>8.3f}{d['cv']:>7.1f}{d['min']:>8.3f}{d['max']:>8.3f}{fold:>7}")

    # 2. Band-position tests
    print("\n2. BAND POSITIONS: SPECIMEN 1 vs SPECIMEN 2 (cm-1, mean ± SD)")
    print(f"{'Band':<22}{'Specimen 1':>18}{'Specimen 2':>18}{'Diff':>7}{'Student p':>11}{'Welch p':>10}{'MWU p':>9}{'Levene p':>10}")
    for label, lo, hi, kind in BANDS.get(a.mineral, []):
        pos, edge = zip(*[extremum(wn, y, lo, hi, kind) for y in Y])
        pos = np.array(pos)
        x1, x2 = pos[spec == groups[0]], pos[spec == groups[1]]
        st = stats.ttest_ind(x1, x2); we = stats.ttest_ind(x1, x2, equal_var=False)
        mw = stats.mannwhitneyu(x1, x2); lv = stats.levene(x1, x2)
        print(f"{label:<22}{x1.mean():>10.1f} ± {x1.std(ddof=1):<5.1f}{x2.mean():>10.1f} ± {x2.std(ddof=1):<5.1f}"
              f"{x1.mean() - x2.mean():>7.1f}{st.pvalue:>11.2g}{we.pvalue:>10.2g}{mw.pvalue:>9.2g}{lv.pvalue:>10.2g}"
              + ("  WARNING: edge hit" if any(edge) else ""))

    # 3-4. PCA and clustering
    print("\n3. PCA (full spectrum)   4. HIERARCHICAL CLUSTERING (k=2 vs specimen labels)")
    results = {}
    for label, M in [("raw log10(1/R)", Y), ("SNV-normalized", snv(Y))]:
        p = PCA(5).fit(M); S = p.transform(M); ev = p.explained_variance_ratio_ * 100
        sil = silhouette_score(S[:, :2], spec)
        print(f"-- {label}: PC1 {ev[0]:.1f}%, PC2 {ev[1]:.1f}%, PC3 {ev[2]:.1f}%; silhouette (PC1-PC2, by specimen) {sil:.2f}")
        for meth, metric in [("ward", "euclidean"), ("average", "cosine")]:
            Z = linkage(M, meth, metric=metric); c = fcluster(Z, 2, "maxclust")
            ari = adjusted_rand_score(spec, c)
            # scans whose cluster disagrees with the majority of their specimen
            wrong = []
            for g in groups:
                maj = np.bincount(c[spec == g]).argmax()
                wrong += [n for n, s, ci in zip(names, spec, c) if s == g and ci != maj]
            print(f"   {meth}/{metric}: ARI {ari:.2f}" + (f"; misplaced: {', '.join(wrong)}" if wrong else "; matches specimens exactly"))
        results[label] = (S, ev)

    # Figures: one PNG per panel
    colors = {groups[0]: "#1f77b4", groups[1]: "#d62728"}
    written = []
    for label, fname in [("raw log10(1/R)", "PCA_raw"), ("SNV-normalized", "PCA_SNV")]:
        S, ev = results[label]
        fig, ax = plt.subplots(figsize=(6, 5))
        for g in groups:
            ax.scatter(S[spec == g, 0], S[spec == g, 1], c=colors[g], label=f"Specimen {g}", s=40)
        for n, x, y in zip(names, S[:, 0], S[:, 1]):
            ax.annotate(n.split("_", 1)[1], (x, y), fontsize=7, xytext=(3, 3), textcoords="offset points")
        ax.set_xlabel(f"PC1 ({ev[0]:.1f}%)"); ax.set_ylabel(f"PC2 ({ev[1]:.1f}%)")
        ax.set_title(f"{a.mineral}: PCA, {label}", fontsize=11)
        ax.legend(fontsize=8)
        plt.tight_layout()
        out = f"{a.mineral}_{fname}.png"; plt.savefig(out, dpi=300); plt.close(fig); written.append(out)
    fig, ax = plt.subplots(figsize=(7, 5))
    Z = linkage(Y, "ward", metric="euclidean")
    dendrogram(Z, labels=[n.split("_", 1)[1] for n in names], ax=ax, leaf_rotation=90,
               color_threshold=0, above_threshold_color="grey")
    for t in ax.get_xticklabels():
        t.set_color(colors[int(t.get_text().split("_")[0])])
    ax.set_title(f"{a.mineral}: hierarchical clustering (Ward, Euclidean)", fontsize=11)
    ax.set_ylabel("Linkage distance"); ax.set_xlabel("Scan (blue: Specimen 1, red: Specimen 2)")
    plt.tight_layout()
    out = f"{a.mineral}_dendrogram_Ward.png"; plt.savefig(out, dpi=300); plt.close(fig); written.append(out)
    print("\nFigures written: " + ", ".join(written))


if __name__ == "__main__":
    main()
