# Workflow: adding scans to the database

Everything here uses one script, `import_scans.py`, and one sheet, `materials.csv`. The script **adds** new scans to the existing database. It never rebuilds it and never changes what is already loaded.

## The one command

Run it from the repository folder:

```
python3 import_scans.py scans pigment_spectral_standards.db
```

It prints a report and saves it as `import_report.md`. To see what it would do without saving anything, add `--dry-run`:

```
python3 import_scans.py scans pigment_spectral_standards.db --dry-run
```

Two safety nets: a run is all or nothing (if anything fails, nothing is saved), and the database is in git, so a bad run can be undone by restoring the file.

## What the script fills in, and where it comes from

| Information | Where it comes from |
|---|---|
| The spectrum, file path, size, checksum | The `.dpt` file |
| ER-IR or ATR | The filename (see the naming table) |
| Material and specimen number | The filename |
| Link from an ER-IR scan to its ATR standard | Same material, found automatically |
| Material name, formula, synthetic or not, description | `materials.csv` |
| Source, specimen type, specimen notes | `materials.csv` |
| Instrument (Bruker LUMOS II), operator, scan settings, site (Laboratory), intensity mode (Absorbance) | Fixed in the script |
| Scan date (`ScanDate`, as YYYY-MM-DD), environment, notes, coordinates, images | Not filled in. Enter by hand if wanted |

## Naming rules

The script reads the filename. The key is the `file_key` column of `materials.csv`. Upper or lower case does not matter.

| Kind of scan | Filename | Example |
|---|---|---|
| ER-IR, natural mineral | `<key><specimen>.<scan>.dpt` | `hematite2.16.dpt` is hematite, specimen 2, scan 16 |
| ATR standard, natural mineral | `<Key>Powder.<n>.dpt`, `<Key>_ATR.dpt` or `<key>_powder_ATR.dpt` | `AzuritePowder.0.dpt`, `dolomite_powder_ATR.dpt` |
| ER-IR, synthetic pigment | `<key>_ER_<n>.<m>.dpt` | `verdigris_ER_3.0.dpt` |
| ATR, synthetic pigment | `<key>_ATR.dpt` | `verdigris_ATR.0.dpt` |

Scans can be in any subfolder of `scans/`. Folder names do not matter, except that the folder is stored as part of the file path.

## Case 1: new scans of a material already in the database

1. Export the scans from OPUS as absorbance `.dpt` files.
2. Name them with the pattern above, for example `calcite1.12.dpt` for the next scan of calcite specimen 1. A new specimen is just the next number: `calcite3.0.dpt`.
3. Copy them into `scans/` (any subfolder).
4. Run the command. Read the report.
5. Commit `scans/`, the database and `import_report.md` to git.

Each new ER-IR scan is linked to the ATR standard of the same material automatically. A new specimen is created from the material's row in `materials.csv`.

## Case 2: a new material

Example: a new pigment, realgar.

1. Open `materials.csv` and add one row. Columns:

   | Column | What to type |
   |---|---|
   | `file_key` | The word used at the start of filenames, lower case, no spaces: `realgar` |
   | `material_name` | The name shown in the database: `Realgar` |
   | `formula` | Plain text, numbers inline: `As4S4` |
   | `is_synthetic` | `1` if synthetic, `0` if natural |
   | `description` | A short description, or leave empty |
   | `source` | Who supplied it: `UniPD mineral collection`, `Kremer`, `Maimeri` or a new name. Empty means no source is recorded |
   | `specimen_type` | One of `powder pigment`, `ground mineral`, `mineral fragment` |
   | `preparation_notes` | For example `Ground/prepared for FTIR analysis`, or empty |
   | `source_notes` | Product number, label text, or empty |

2. Name the scans with the new key: `realgar1.0.dpt`, `RealgarPowder.0.dpt`.
3. Run the command.

If a scan's material has no row in `materials.csv`, the file is listed in the report under "name matched no rule" and is **not** loaded. Nothing is guessed. Adding the row and running again loads it.

For a synthetic pigment, the ER-IR and ATR scans share one specimen (one jar of powder), so use the synthetic naming pattern.

## Case 3: an ATR standard added later

Example: Magnetite has no ATR standard, so its ER-IR scans are unlinked and tagged `needs-atr-recollection`.

1. Collect the ATR spectrum, export it as absorbance, and name it `MagnetitePowder.0.dpt`.
2. Put it in `scans/PowderATR/` and run the command.

The script loads the standard, links every earlier Magnetite ER-IR scan to it, and removes the tag. The report says how many scans were linked.

If a material already has an ATR standard, a second one is loaded but the existing links are kept.

## Case 4: a scan was wrong and has been re-exported

The script skips any file whose path is already in the database, so a corrected file with the same name is not picked up. First remove the old rows by hand in DB Browser for SQLite (Execute SQL), using the file path:

```sql
DELETE FROM SpectralFile WHERE FilePath = 'Oxides/hematite2.3.dpt';
DELETE FROM Measurement
WHERE MeasurementID NOT IN (SELECT MeasurementID FROM SpectralFile);
```

Then put the corrected file in `scans/` and run the command. Do not delete an ATR standard this way while ER-IR scans point to it.

## Case 5: scans that are not standards (real objects, unknown specimens)

Not covered yet. The script handles standards, where the material is always known. A scan from a real object needs a specimen with no material, an Object, a Collection and spot descriptions, and its identification is written later by the matching software. When you have such scans, this part of the script needs to be extended.

## Reading the report

| Section | Meaning |
|---|---|
| Added in this run | What was loaded, by material and mode |
| Skipped: empty or unreadable | Files that are empty or not plain text. Re-export them |
| Removed as duplicates | A file with exactly the same intensity values as another one, in the same material and mode. The lowest scan number is kept. Duplicates are not loaded, but the files stay in `scans/` until you delete them |
| Files whose name matched no rule | Not loaded. Fix the name, or add the material to `materials.csv` |
| Filename typos corrected | Known misspellings that were read as the right name |
| Things to check | Materials still missing an ATR standard |

## What the script never does

- It never changes or deletes a scan file.
- It never converts a spectrum. It loads the numbers in the file, so the file must already be absorbance.
- It never changes a measurement that is already in the database.
