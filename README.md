# Pigment Spectral Standards Database

Relational SQLite/MySQL database of paired ER-IR and ATR infrared spectra of mineral pigment standards, for cultural heritage research.

Prepared by Maria Gabriela Rivas Carmona, University of Padova
Thesis advisors: Professor Alfonso Zoleo (Chemistry) and Professor Nicola Orio (Computer Science)

## What this is

A reference database of external reflectance infrared (ER-IR) scans, each paired with the attenuated total reflectance (ATR) standard of the same material. The ER-IR scans are the kind of spectrum that can be taken non-invasively on a real object; the ATR standards are the reference they are compared with. Spectra were measured on a Bruker LUMOS II FT-IR microscope.

**Status:** schema version 4 (17 tables), loaded from the re-exported absorbance scans. The database holds 256 measurements (242 ER-IR and 14 ATR) of 15 materials on 37 specimens. 220 of the ER-IR scans are linked to the ATR standard of the same material. Magnetite has no ATR standard yet and is tagged `needs-atr-recollection`. Files from the earlier version of the project are in [`Archived/`](Archived/).

## Files

| File | What it is |
|---|---|
| `pigment_spectral_standards.db` | The database, SQLite, ready to open |
| `scans/` | The 256 `.dpt` scan files the database was built from, named `mineral_ER_IR_specimen_scan.dpt` and `mineral_ATR.dpt` (see `NAMING.md`) |
| `import_scans.py` | Adds new scans from `scans/` to the database and writes `import_report.md` |
| `export_for_ui.py` | Writes the JSON data files for a web interface. The interface is designed (see the thesis) but not built yet; this script is for that future work and is not part of adding scans |
| `match_unknown.py` | Matches an unknown spectrum against the ER-IR standards (Pearson, first-derivative Pearson, peak position) and prints the top materials. Run `python3 match_unknown.py FILE`, or `python3 match_unknown.py FOLDER` to match every spectrum file in a folder in one table; needs `pip install numpy scipy` (plus `brukeropus` for Bruker `.dpt` binary files). A high score means a similar shape, not a confirmed identification; it never changes the database |
| `database_summary.py` | Prints the materials, the scan counts per acquisition mode and the total number of scans. Read-only; works on Mac and Windows, where there is no `sqlite3` command |
| `materials.csv` | The materials, their formulas, sources and specimen types, read by the script |
| `scan_batches.csv` | The date and operator of each group of scans, by folder, and the unit if a group was not exported as absorbance, read by the script |
| `operators.csv` | The people who make scans: name, email, institution, read by the script |
| `HANDOVER.md` | What to do when the person running the database leaves: ownership, operators, file list |
| `scan_rename_map.csv` | Old and new filename of every scan, from the renaming to the current naming convention (also records the lazurite point numbers) |
| `WORKFLOW.md` | Step-by-step instructions for adding scans and new materials |
| `NAMING.md` | How to name scans, folders and materials |
| `import_report.md` | What the import loaded, corrected and skipped |
| `pigment_spectral_standards_sqlite_schema.sql` | Creates an empty database in SQLite |
| `pigment_spectral_standards_mysql_schema.sql` | The same design for MySQL 8 (schema only) |
| `ER_Diagram.png` | Entity-relationship diagram of the 17 tables |
| `Archived/` | The earlier schema, its data and the analysis scripts that used it |

## How to open it, for non-technical readers

1. Download [DB Browser for SQLite](https://sqlitebrowser.org/). It is free and needs no account.
2. Open it, choose **File, then Open Database**, and select the `.db` file.
3. The **Browse Data** tab shows any table. The **Execute SQL** tab runs the example queries below.

## How to open it, for technical readers

```
sqlite3 pigment_spectral_standards.db
```

To add new scans to it, see [`WORKFLOW.md`](WORKFLOW.md). The same script creates a new database from the schema when the database file does not exist:

```
python3 import_scans.py scans new_database.db --schema pigment_spectral_standards_sqlite_schema.sql
```

To create an empty database from the schema:

```
sqlite3 new_database.db < pigment_spectral_standards_sqlite_schema.sql
```

SQLite enforces foreign keys only when `PRAGMA foreign_keys = ON` is set for the connection. DB Browser for SQLite turns it on by default.

```python
import sqlite3
conn = sqlite3.connect("your_database.db")
print(conn.execute("SELECT * FROM Material").fetchall())
```

## How spectra are stored

Each measurement holds its whole spectrum in one column, `Measurement.SpectrumData`, as a JSON array of `[wavenumber, intensity]` pairs, for example `[[598.1, 0.52], [600.2, 0.53], ...]`. An ER-IR scan has 1,660 pairs and an ATR scan has 1,934. The pairs stay together, and SQLite refuses text in this column that is not valid JSON.

The database holds absorbance data only. Spectra are exported as absorbance from OPUS, and `IntensityMode` is filled in as `Absorbance`. If a batch was exported as transmittance or reflectance by mistake, mark its line in `scan_batches.csv` (`intensity` column) and `import_scans.py` converts it to absorbance while loading; the measurement's Notes record the conversion. The original `.dpt` file for each measurement is recorded in `SpectralFile`, with its size and a checksum.

## Schema overview (17 tables)

**Core data**

| Table | Purpose |
|---|---|
| `Material` | A pigment or mineral: name, chemical formula, whether it is synthetic |
| `Source` | Who supplied a specimen, for example a collection or a commercial supplier |
| `Specimen` | The physical item that was measured: a powder, a ground mineral or a fragment |
| `Measurement` | One scan, with its spectrum, mode (ER-IR or ATR) and, for an ER-IR scan, the link to its ATR standard |
| `SpectralFile` | The `.dpt` file for each measurement, with type, size and checksum |
| `Identification` | Links a scan to a material it may match. A possible match, not a confirmed one. Written by the matching software |

**Provenance and instruments**

| Table | Purpose |
|---|---|
| `Object`, `Collection`, `Institution` | For real heritage objects: where they came from, where they are now, and who holds them |
| `Operator` | Who made the measurement |
| `Instrument`, `InstrumentConfiguration` | The instrument (with optional serial number and lab ID) and its settings. Each configuration belongs to one instrument |

**Data-quality tags**

| Table | Purpose |
|---|---|
| `Tag`, `TaggedEntity` | Labels, such as `needs-atr-recollection`, attached to a specimen or a measurement |

**Pick lists**

| Table | Values |
|---|---|
| `AcquisitionModeType` | ER-IR, ATR |
| `MeasurementSiteType` | Laboratory, In Situ - Interior, In Situ - Exterior |
| `SpecimenType` | powder pigment, ground mineral, mineral fragment |

Most fields are optional. The required ones are marked `NOT NULL` in the schema file.

## Example queries

How many ER-IR scans exist for each material:

```sql
SELECT mat.MaterialName, COUNT(*) AS n_scans
FROM Measurement m
JOIN AcquisitionModeType amt ON amt.AcquisitionModeID = m.AcquisitionModeID
JOIN Specimen s ON s.SpecimenID = m.SpecimenID
JOIN Material mat ON mat.MaterialID = s.MaterialID
WHERE amt.ModeName = 'ER-IR'
GROUP BY mat.MaterialName;
```

Unpack the full spectrum of one scan into wavenumber and intensity rows:

```sql
SELECT json_extract(p.value, '$[0]') AS Wavenumber,
       json_extract(p.value, '$[1]') AS Intensity
FROM Measurement m
JOIN SpectralFile f ON f.MeasurementID = m.MeasurementID,
     json_each(m.SpectrumData) p
WHERE f.FilePath LIKE '%aragonite_ER_IR_1_0.dpt'
ORDER BY Wavenumber DESC;
```

List each ER-IR scan next to its ATR standard:

```sql
SELECT fe.FilePath AS ER_IR_scan, fa.FilePath AS ATR_standard
FROM Measurement er
JOIN SpectralFile fe ON fe.MeasurementID = er.MeasurementID
JOIN SpectralFile fa ON fa.MeasurementID = er.ReferenceMeasurementID;
```

Show the data-quality tags on specimens:

```sql
SELECT t.TagLabel, mat.MaterialName, s.SpecimenID
FROM TaggedEntity te
JOIN Tag t ON t.TagID = te.TagID
JOIN Specimen s ON s.SpecimenID = te.EntityID
LEFT JOIN Material mat ON mat.MaterialID = s.MaterialID
WHERE te.EntityType = 'Specimen';
```

## How `match_unknown.py` works

**Setup and running.** Install the packages once: `python3 -m pip install numpy scipy brukeropus` (on Windows: `py -m pip install numpy scipy brukeropus`; on a Mac use `python3 -m pip`, because the plain `pip` command may not exist). `brukeropus` is only needed for Bruker OPUS binary `.dpt` files. Then, from the folder that contains the script and the database, run `python3 match_unknown.py PATH_TO_FILE` (Windows: `py match_unknown.py PATH_TO_FILE`). To match a whole folder, give the folder instead of a file (for example `python3 match_unknown.py scans/unknown`); it prints the top 3 materials per method for each file and counts the first places. A file it cannot read is listed at the end. The file can be anywhere on the computer; put its path in quotes if it contains spaces. To see what is in the database, run `python3 database_summary.py` (Windows: `py database_summary.py`).

The script compares one unknown spectrum with the 242 ER-IR standards in the database and ranks the materials. It only reads the database; it never changes it. Nothing inside the script has to be edited to test a new spectrum: the file name and options go on the command line (`--from-transmittance`, `--top N`, `--db PATH`).

1. **Read the unknown file** (`read_spectrum`). Text files, Perkin-Elmer `.ASC` files (data after a `#DATA` line) and Bruker OPUS binary `.dpt` files (needs `brukeropus`) are accepted. The points are sorted by wavenumber. With `--from-transmittance`, %T is converted to absorbance (2 - log10 %T). This conversion is for trying things out only; the database never converts spectra.
2. **Put it on a common grid** (`resample`). The unknown must cover 700 to 3900 cm-1. It is interpolated onto 800 evenly spaced points from 650 to 3990 cm-1 (about 4.2 cm-1 apart), the same grid used for the standards.
3. **Load the standards** (`load_standards`). One SQL query reads every ER-IR scan and its spectrum from `Measurement`, and each is put on the same grid.
4. **Normalize** (`snv`). Each spectrum has its own mean subtracted and is divided by its own standard deviation (SNV), so overall height and offset do not count and only shape is compared.
5. **Score with three methods** (`rank`):
   - `pearson`: Pearson correlation of the SNV spectra.
   - `deriv`: Savitzky-Golay first derivative (smoothing window of 11 points, about 42 cm-1, fitted with a quadratic), then SNV, then Pearson. This removes baseline slope and tilt and emphasizes band positions.
   - `peaks`: SNV, find peaks (at least 0.5 SNV units high, at least 20 cm-1 apart), match peaks within 8 cm-1 (each used once). Score = 2 x matched / (peaks in unknown + peaks in standard).
6. **Rank materials.** A material's score is the best score among its ER-IR scans. The top results are printed for each method.

The settings in steps 2 and 5 (range check, window, prominence, spacing, tolerance) are design choices for this prototype; they were not tuned or validated against the literature. A high score means a similar spectral shape, not a confirmed identification. Spectra from other instruments or measurement types (ATR, transmission), and materials with few bands between 650 and 3990 cm-1 (such as cinnabar and orpiment), match poorly.
