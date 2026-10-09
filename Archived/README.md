# Archived: earlier version of the database

Everything in this folder uses the **original schema**, with the tables `Sample`, `Spectrum`, `SpectralDataPoint`, `Preprocessing`, `OpticalArtifacts`, `MeasurementLocation` and `MineralClass`, and one row per wavenumber-intensity pair. It is kept so that the thesis results derived from it can be reproduced. The current schema is in the top-level folder.

| File | What it is |
|---|---|
| `er_ir_pigment_spectral_standards_sqlite.db` | The original database |
| `er_ir_harmonized.db` | Cleaned copy: duplicates removed, reflectance files converted to log10(1/R) |
| `er_ir_harmonized_harmonization_report.csv` | Report of every change the cleaning step made |
| `sq_lite_Revised_Schema_final.sql`, `er_ir_pigment_spectral_standards_mysql_schema_final.sql` | The original schema files |
| `ER_Diagram.png` | The original diagram |
| `harmonize_er_ir_database.py` | Cleaning step, run before any analysis. Never modifies the original database |
| `analyze_carbonate_mineral_spectra.py` | Band-position and distortion analysis of one carbonate mineral's ER-IR scans |
| `carbonate_statistics.py` | Statistics, PCA and clustering of one mineral's ER-IR scans |
| `Calcite_PCA_raw.png`, `Calcite_PCA_SNV.png`, `Calcite_dendrogram_Ward.png` | Figures produced by `carbonate_statistics.py` |

## Running the scripts

Python 3 with `numpy`, `scipy`, `scikit-learn` and `matplotlib`:

    python3 -m pip install numpy scipy scikit-learn matplotlib

Run from inside this folder:

    python3 harmonize_er_ir_database.py er_ir_pigment_spectral_standards_sqlite.db er_ir_harmonized.db
    python3 analyze_carbonate_mineral_spectra.py er_ir_harmonized.db Calcite
    python3 carbonate_statistics.py er_ir_harmonized.db Calcite 1300 1800

These scripts read the original tables and do not work on the current schema.
