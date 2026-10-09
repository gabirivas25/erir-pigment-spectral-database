# Pigment Spectral Standards Database

Relational SQLite/MySQL database of paired ER-IR and ATR infrared spectra of mineral pigment standards, for cultural heritage research.

Prepared by Maria Gabriela Rivas Carmona, University of Padova
Thesis advisors: Professor Alfonso Zoleo (Chemistry) and Professor Nicola Orio (Computer Science)

## What this is

A reference database of external reflectance infrared (ER-IR) scans, each paired with the attenuated total reflectance (ATR) standard of the same material. The ER-IR scans are the kind of spectrum that can be taken non-invasively on a real object; the ATR standards are the reference they are compared with. Spectra were measured on a Bruker LUMOS II FT-IR microscope.

**Status:** schema version 4 (18 tables), loaded from the re-exported absorbance scans. The database holds 256 measurements (242 ER-IR and 14 ATR) of 15 materials on 37 specimens. 220 of the ER-IR scans are linked to the ATR standard of the same material. Magnetite has no ATR standard yet and is tagged `needs-atr-recollection`. Files from the earlier version of the project are in [`Archived/`](Archived/).

## Files

| File | What it is |
|---|---|
| `pigment_spectral_standards.db` | The database, SQLite, ready to open |
| `scans/` | The 256 original `.dpt` scan files the database was built from |
| `import_scans.py` | Builds the database from `scans/` and writes `import_report.md` |
| `import_report.md` | What the import loaded, corrected and skipped |
| `pigment_spectral_standards_sqlite_schema.sql` | Creates an empty database in SQLite |
| `pigment_spectral_standards_mysql_schema.sql` | The same design for MySQL 8 (schema only) |
| `ER_Diagram.png` | Entity-relationship diagram of the 18 tables |
| `Archived/` | The earlier schema, its data and the analysis scripts that used it |

## How to open it, for non-technical readers

1. Download [DB Browser for SQLite](https://sqlitebrowser.org/). It is free and needs no account.
2. Open it, choose **File, then Open Database**, and select the `.db` file.
3. The **Browse Data** tab shows any table. The **Execute SQL** tab runs the example queries below.

## How to open it, for technical readers

```
sqlite3 pigment_spectral_standards.db
```

To rebuild it from the scans:

```
python3 import_scans.py scans pigment_spectral_standards_sqlite_schema.sql new_database.db
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

The database holds absorbance data only. Spectra are converted to absorbance in OPUS before upload, and `IntensityMode` is filled in as `Absorbance`. The original `.dpt` file for each measurement is recorded in `SpectralFile`, with its size and a checksum.

## Schema overview (18 tables)

**Core data**

| Table | Purpose |
|---|---|
| `Material` | A pigment or mineral: name, chemical formula, whether it is synthetic |
| `Source` | Who supplied a specimen, for example a collection or a commercial supplier |
| `Specimen` | The physical item that was measured: a powder, a ground mineral or a fragment |
| `Measurement` | One scan, with its spectrum, mode (ER-IR or ATR) and, for an ER-IR scan, the link to its ATR standard |
| `SpectralFile` | The `.dpt` file for each measurement, with type, size and checksum |
| `Identification` | Links a specimen to a material it matched. Written by the matching software |

**Provenance and instruments**

| Table | Purpose |
|---|---|
| `Object`, `Collection`, `Institution` | For real heritage objects: where they came from, where they are now, and who holds them |
| `Operator` | Who made the measurement |
| `Instrument`, `InstrumentConfiguration` | The instrument and its settings |
| `EnvironmentConditions` | Optional temperature, humidity, pressure and illumination |

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
WHERE f.FilePath LIKE '%Aragonite1.0.dpt'
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
