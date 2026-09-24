# erir-pigment-spectral-database
Relational SQLite/MySQL spectral database and automated ingestion pipeline for cultural heritage mineral pigments (FTIR ER-IR and ATR standards).
# Pigment Spectral Standards Database

Prepared by Maria Gabriela Rivas Carmona — University of Padova
Thesis advisors: Professor Alfonso Zoleo (Chemistry) & Professor Nicola Orio (Computer Science)

## What this is

A working, populated relational database containing every ER-IR scan and ATR reference standard
collected so far across all 12 mineral pigments studied in this thesis.

**Format:** SQLite (`er_ir_pigment_spectral_standards_sqlite.db`) — a real, queryable database in a single
file, requiring no server setup. A verified MySQL-compatible version
(`er_ir_pigment_spectral_standards_mysql_schema_final.sql`) is included separately, so the same design can
be deployed to a real MySQL server later (e.g. a university-hosted server), requiring only a data
migration step.

*Note: unlike an earlier draft of this schema, the MySQL version has been tested directly against
a live 9.3.0 MySQL Community Server - GPL — all 21 tables and every foreign-key relationship were confirmed to build
and function correctly, not just written by inspection.*

## How to open it — for non-technical readers

1. Download **[DB Browser for SQLite](https://sqlitebrowser.org/)** — free, no account needed,
   available for Windows, Mac, and Linux.
2. Open the app, then **File → Open Database**, and select `er_ir_pigment_spectral_standards_sqlite.db`.
3. Click the **Browse Data** tab to scroll through any table visually (e.g. `Material`, `Spectrum`).
4. Click the **Execute SQL** tab to run any of the example queries below and see the results
   directly in a table. No installation of anything beyond this one free app is required.

## How to open it — for technical readers

**Command line:**
```
sqlite3 er_ir_pigment_spectral_standards_sqlite.db
```

**Python** (using the standard library, no extra installation needed):
```python
import sqlite3
conn = sqlite3.connect("er_ir_pigment_spectral_standards_sqlite.db")
cursor = conn.cursor()
cursor.execute("SELECT * FROM Material")
print(cursor.fetchall())
```

## Schema overview (21 tables)

| Table | Purpose |
|---|---|
| `MineralClass` | Lookup: mineral category (Carbonate, Oxide, Silicate, Sulfide) |
| `LocationType` | Lookup: measurement setting (Laboratory, In Situ – Interior, In Situ – Exterior) |
| `AcquisitionModeType` | Lookup: spectral acquisition mode (ER-IR, ATR) |
| `Institution` | University of Padova |
| `Operator` | The measurement operator |
| `Collection` / `Object` | For future use, if real heritage objects (not just standards) are added; `Collection` links to `Institution`, `Object` carries its own permanent `SiteLocationID` |
| `Material` | The 12 minerals, linked to `MineralClass`, with chemical formula |
| `Sample` | Each physical specimen, or (in future use) a non-invasive measurement point on a real object |
| `Instrument` / `InstrumentConfiguration` | The Bruker LUMOS II FT-IR microscope and its settings |
| `EnvironmentConditions` | For future use, if temperature/humidity logging is added |
| `MeasurementLocation` | Where a specific measurement session physically took place |
| `Measurement` | One row per scan event (links sample, instrument, operator, date) |
| `Spectrum` | One row per resulting spectrum, linked to `AcquisitionModeType`, with source filename |
| `SpectralDataPoint` | Every individual (wavenumber, intensity) pair — the actual spectral data |
| `OpticalArtifacts` | Structured record of observed optical effects (e.g. the reststrahlen effect) |
| `Preprocessing` | Record of data-transformation steps applied to a spectrum |
| `SpectralFile` | Reference to the underlying raw/processed source files |
| `Tag` / `TaggedEntity` | Flexible labeling system, used to flag known data-quality issues |

## What's populated right now

- **220 ER-IR spectra** and **11 ATR reference standards**, across all 12 minerals
- **386,474 individual spectral data points**
- **200 of the 220 ER-IR spectra** are directly linked to their own mineral's ATR standard via
  `ReferenceSpectrumID` (the remaining 20, all Magnetite, await that mineral's ATR standard)
- **18 known-empty scan files skipped** (7 from Dolomite, 11 from Malachite) — not fabricated,
  not silently dropped, genuinely absent from the source data
- `Collection`, `Object`, `EnvironmentConditions`, `OpticalArtifacts`, `Preprocessing`,
  `SpectralFile`, and `LocationType`'s linkage are ready for future use but not yet populated
  with real records beyond `LocationType`'s own three standard category rows

## Known data-quality issues — already tagged in the database itself

```sql
SELECT t.TagLabel, s.SampleType
FROM TaggedEntity te
JOIN Tag t ON t.TagID = te.TagID
JOIN Sample s ON s.SampleID = te.EntityID AND te.EntityType = 'Sample';
```

- `needs-atr-recollection` — Magnetite (ATR standard lost during sample grinding)
- `partial-scan-data` — Dolomite and Malachite (some scan files are 0 bytes)

## Example queries

Get every mineral and how many ER-IR scans exist for it:
```sql
SELECT mat.MaterialName, COUNT(*) AS n_scans
FROM Spectrum sp
JOIN AcquisitionModeType amt ON amt.AcquisitionModeID = sp.AcquisitionModeID
JOIN Measurement m ON m.MeasurementID = sp.MeasurementID
JOIN Sample s ON s.SampleID = m.SampleID
JOIN Material mat ON mat.MaterialID = s.MaterialID
WHERE amt.ModeName = 'ER-IR'
GROUP BY mat.MaterialName;
```

Pull the full spectrum for one specific scan:
```sql
SELECT dp.Wavenumber, dp.Intensity
FROM SpectralDataPoint dp
JOIN Spectrum sp ON sp.SpectrumID = dp.SpectrumID
WHERE sp.SourceFilename = 'Aragonite_1_0.dpt'
ORDER BY dp.Wavenumber DESC;
```

Find a mineral's ER-IR scan alongside its own ATR reference standard, using `ReferenceSpectrumID`:
```sql
SELECT er.SourceFilename AS ER_IR_scan, atr.SourceFilename AS ATR_standard
FROM Spectrum er
JOIN Spectrum atr ON atr.SpectrumID = er.ReferenceSpectrumID;
```
*`ReferenceSpectrumID` has been backfilled for all 200 ER-IR spectra with a corresponding ATR
standard (11 of 12 minerals). Magnetite's 20 ER-IR spectra have no linked reference yet, since no
ATR standard has been collected for it (see `needs-atr-recollection` below); once Magnetite's ATR
scan is added, re-running the backfill will link these automatically.*

## Next steps for this database

- Populate `Preprocessing` with a record of the SNV normalization or OPUS absorbance conversion
  applied, so the transformation history is traceable alongside the raw data
- Add the Magnetite ATR standard once re-scanned, and the missing Dolomite/Malachite scan batches
  once recollected, then remove the corresponding `Tag` entries
- Consider populating `EnvironmentConditions` if temperature/humidity were logged during acquisition
- If real heritage objects are analyzed later, `Collection` and `Object` are ready to use without
  any schema changes, and `Object.SiteLocationID` / `Sample.MeasurementPointDescription` are ready
  to record a real object's permanent site and a specific non-invasive measurement point on it
