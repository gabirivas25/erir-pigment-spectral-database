# Workflow: adding scans to the database

This guide is written for someone who has never used a terminal. Every step says exactly what to click or type. If you only want the short version, jump to **Quick reference** at the end of the setup.

## What happens when you add scans

You put new scan files (`.dpt`) in the `scans/` folder and run **one command**. A small program, `import_scans.py`, reads the files and **adds** them to the database. It never rebuilds the database and never changes what is already in it.

The program needs four things, all in this repository:

| File | What it holds |
|---|---|
| `scans/` | The scan files themselves |
| `materials.csv` | One line per material: name, formula, source, specimen type |
| `scan_batches.csv` | The date and the operator (the person who scanned) of each group of scans |
| `operators.csv` | The people who do scans: name, email, institution |

## What the program fills in, and what it does not

| Information | Where it comes from |
|---|---|
| The spectrum, file path, size, checksum | The `.dpt` file |
| ER-IR or ATR | The filename (see **Naming your files**) |
| Material and specimen number | The filename |
| Link from an ER-IR scan to its ATR standard | Found automatically: same material |
| Material name, formula, synthetic or not, description | `materials.csv` |
| Source, specimen type, specimen notes | `materials.csv` |
| Scan date (`ScanDate`) | `scan_batches.csv`, by the folder the scan is in |
| Operator | `scan_batches.csv`, by the folder the scan is in. The person must be in `operators.csv` |
| Instrument (Bruker LUMOS II), scan settings (ER-IR: 4 cm-1, 64 scans, ZnSe, 30 um aperture; ATR: 4 cm-1, 32 scans, ZnSe), site (Laboratory), intensity mode (Absorbance) | Fixed in the program: the standard setup, the same for every operator |
| Notes, coordinates, images | Not filled in. Type them into the database by hand if you want them |

---

# Part 1: One-time setup

The program runs on **your computer**, not in the web browser. The browser versions of GitHub and VS Code can show and edit the files, but they cannot run the program, so you need the steps below once.

You do this once on each computer. It takes about 15 minutes.

## Step 1: Install Python

Python is the free program that runs `import_scans.py`.

1. Open the Terminal.
   - **Mac:** press the Command key and the space bar, type `Terminal`, press Enter.
   - **Windows:** press the Windows key, type `cmd`, press Enter. A black window opens.
2. Check whether Python is already installed. Type this and press Enter:
   - **Mac:** `python3 --version`
   - **Windows:** `python --version`
3. If you see a line like `Python 3.11.4` (any number 3.8 or higher), Python is installed. Go to Step 2.
4. If you see an error or a lower number, go to <https://www.python.org/downloads/>, click the big yellow **Download Python** button, open the file that downloads, and follow the installer.
   - **Windows only:** on the first installer screen, tick the box **Add python.exe to PATH** before clicking Install.
5. Close the Terminal, open it again and repeat step 2 to check.

> **Windows users:** wherever this guide says `python3`, type `python` instead. If Windows answers that `python` is not recognized, type `py` instead (and tick **Add python.exe to PATH** when you reinstall Python).

## Step 2: Get the repository onto your computer

The repository is the folder with everything in it. The easiest way is GitHub Desktop.

1. Go to <https://desktop.github.com/>, download GitHub Desktop and install it.
2. Open it and sign in with your GitHub account.
3. Click **File**, then **Clone repository**.
4. Choose the tab **GitHub.com**, click `gabirivas25/erir-pigment-spectral-database`, choose where to save it (for example your Documents folder) and click **Clone**.
5. Wait until it finishes. You now have a folder called `erir-pigment-spectral-database`.

## Step 3: Open a Terminal inside that folder

You need the Terminal to be "in" the repository folder.

- **Mac:**
  1. Open the Terminal.
  2. Type `cd ` (the letters c, d and then **one space**). Do not press Enter yet.
  3. Open Finder, find the folder `erir-pigment-spectral-database` and **drag the folder into the Terminal window**. Its path appears after `cd `.
  4. Press Enter.
- **Windows:**
  1. Open the folder `erir-pigment-spectral-database` in File Explorer.
  2. Click the address bar at the top (where the folder path is shown), type `cmd` and press Enter. A black window opens, already inside the folder.

To check you are in the right place, type `ls` (Mac) or `dir` (Windows) and press Enter. You should see `import_scans.py`, `materials.csv`, `scans` and `WORKFLOW.md` in the list.

## Step 4: Test that everything works

Type this and press Enter (Windows: use `python`):

```
python3 import_scans.py scans pigment_spectral_standards.db --dry-run
```

`--dry-run` means "show me what you would do, but save nothing". After a few seconds a report appears. The third line should say something like:

> DRY RUN, nothing saved. **0 scans added**, 256 skipped because they were already in the database.

If you see that, setup is finished. If you see an error, copy the whole message and send it to Claude.

## Notes for Windows users

- Type `python` instead of `python3`. If Windows says `python` is not recognized, type `py`.
- To open a Terminal in the folder, use the File Explorer address bar trick in Step 3 (type `cmd` and press Enter).
- Open the `.csv` files in **Notepad**, not Excel.
- Folder and file names work the same as on a Mac. Use the same names and the same `/` in `scan_batches.csv` (for example `2026-11-05/`), not `\`.
- The program has not yet been run on a Windows computer. If it shows an error, copy the whole message and send it to Claude.

## Quick reference

You will use only these two commands from now on (Windows: `python` instead of `python3`):

| What you want | Command |
|---|---|
| See what would happen, save nothing | `python3 import_scans.py scans pigment_spectral_standards.db --dry-run` |
| Add the new scans for real | `python3 import_scans.py scans pigment_spectral_standards.db` |

---

# Part 2: Naming your files and folders

The program reads each scan's **filename** to find the material, the specimen and ER-IR or ATR, and the scan's **folder** to find the date. The full rules, with examples and a checklist, are in **[`NAMING.md`](NAMING.md)**. Read it before you add scans. The short version:

| Kind of scan | Filename |
|---|---|
| ER-IR scan of a mineral | `mineralname_ER_IR_specimen_scannumber.dpt` (for example `hematite_ER_IR_2_16.dpt`) |
| ATR standard of a mineral | `mineralname_ATR.dpt` (for example `hematite_ATR.dpt`) |
| ER-IR scan of a powdered pigment | `synth_pigmentname_ER_IR_scannumber.dpt` (for example `synth_verdigris_ER_IR_3.dpt`) |
| ATR scan of a powdered pigment | `synth_pigmentname_ATR.dpt` (for example `synth_verdigris_ATR.dpt`) |

New scans go in a **new folder named with the date**, for example `scans/2026-11-05/`, with one line for it in `scan_batches.csv` (date and operator).

---

# Part 3: Step-by-step workflows

> **Always open the `.csv` files (`materials.csv`, `scan_batches.csv`, `operators.csv`) in a plain-text editor, not in Excel.**
> - **Windows:** right-click the file, **Open with**, **Notepad**.
> - **Mac:** right-click the file, **Open With**, **TextEdit**, then **Format, Make Plain Text**.
>
> Excel changes dates such as `2026-11-05` into `11/5/2026`, which breaks the program. If you do use Excel, save as **CSV UTF-8**, and format the date column as Text first. Details: **How to edit the sheets** in Part 4.

Before each workflow, do these three things:

1. **Close DB Browser for SQLite** if it is open. The program cannot write to a database that is open with unsaved changes.
2. In GitHub Desktop, click **Fetch origin**, and if the button changes to **Pull origin**, click it. This makes sure you have the latest version.
3. Open the Terminal inside the repository folder (Part 1, Step 3).

## Workflow 1: New scans of a material that is already in the database

Example: three new calcite scans, measured on 5 November 2026.

1. **Export the scans from OPUS as absorbance `.dpt` files.**
2. **Name them** with the pattern in Part 2, for example `calcite_ER_IR_1_12.dpt`, `calcite_ER_IR_1_13.dpt`, `calcite_ER_IR_1_14.dpt` (the next scans of calcite specimen 1).
3. **Make a new folder** inside the `scans` folder, named with the date of the scan: `scans/2026-11-05`. Put the new files inside it. Do **not** put new scans in the older folders (carbonates, oxides, silicates, sulfides, powder_atr, synthetics): those folders already carry an older date.
4. **Tell the program the date and who scanned.** Open `scan_batches.csv` (see **How to edit the sheets** below) and add one line at the bottom:
   ```
   2026-11-05/,2026-11-05,Maria Gabriela Rivas Carmona
   ```
   The first part is the folder name, followed by a slash. The second part is the date, written year-month-day. The third part is the operator, spelled **exactly** as in `operators.csv`.
5. **Check first.** In the Terminal, type the dry-run command and press Enter:
   ```
   python3 import_scans.py scans pigment_spectral_standards.db --dry-run
   ```
   Read the report (see **Reading the report**). You want to see your three scans under "Added in this run", and nothing under "Files whose name matched no rule" or "Scans added without a date" or "Scans added without an operator".
6. **Run it for real**, the same command without `--dry-run`:
   ```
   python3 import_scans.py scans pigment_spectral_standards.db
   ```
   The third line of the report now says `Saved` and `3 scans added`.
7. **Check in DB Browser** (optional but recommended): open `pigment_spectral_standards.db`, click the **Browse Data** tab, choose the table **Measurement** and look at the last rows. The new scans are at the bottom.
8. **Save your work to GitHub.** Open GitHub Desktop. It lists the changed files (the new scans, `scan_batches.csv`, the database and `import_report.md`). Type a short description in the **Summary** box, for example `Add calcite scans from 5 November`, click **Commit to main**, then click **Push origin**.

Each new ER-IR scan is linked to the ATR standard of the same material automatically. A new specimen is created from that material's line in `materials.csv`.

## Workflow 2: A material that is not in the database yet

Example: a new mineral, realgar, with two ER-IR scans (specimen 1) and one ATR standard, measured on 5 November 2026.

**Before you start** (every time): close DB Browser, click **Fetch origin** (or **Pull origin**) in GitHub Desktop, and keep the Terminal ready (Part 1, Step 3).

### Step 1: Add the material to `materials.csv`

1. Open the repository folder in Finder (Mac) or File Explorer (Windows).
2. Right-click `materials.csv`, choose **Open With**, then **TextEdit** (Mac) or **Notepad** (Windows). On a Mac, click **Format**, then **Make Plain Text**.
3. Scroll to the bottom. Click at the very end of the last line, press **Enter** to start a new line, and type one new line for your material. The columns, in this order, are:

   | Column | What to type | Example |
   |---|---|---|
   | `file_key` | The mineral name used at the start of the scan filenames. Lower case, no spaces. For a powdered pigment it must start with `synth_` | `realgar` |
   | `material_name` | The name shown in the database | `Realgar` |
   | `chemical_formula` | Plain text, numbers written inline, no subscripts | `As4S4` |
   | `is_synthetic` | `1` if synthetic, `0` if natural | `0` |
   | `description` | A short description, or leave empty | `Arsenic sulfide` |
   | `source` | Who supplied it: `UniPD mineral collection`, `Kremer`, `Maimeri`, or a new name. Empty = not recorded | `UniPD mineral collection` |
   | `specimen_type` | Exactly one of: `powder pigment`, `ground mineral`, `mineral fragment` | `ground mineral` |
   | `preparation_notes` | For example `Ground/prepared for FTIR analysis`, or empty | `Ground/prepared for FTIR analysis` |
   | `source_notes` | Product number or label text, or empty | |

   The whole line for realgar (commas between the columns, and an empty last column after the final comma):
   ```
   realgar,Realgar,As4S4,0,Arsenic sulfide,UniPD mineral collection,ground mineral,Ground/prepared for FTIR analysis,
   ```
   A value that contains a comma must be inside double quotes, for example `"(Na,Ca)8(AlSiO4)6(SO4,S,Cl)2"`.
4. Save the file (**File, then Save**). If a window asks about the format, keep **plain text / CSV**.

### Step 2: Export and name the scans

1. Export the scans from OPUS as absorbance `.dpt` files.
2. Name them with the pattern in Part 2 (full rules in [`NAMING.md`](NAMING.md)), using the `file_key` from step 1:
   - `realgar_ER_IR_1_0.dpt` and `realgar_ER_IR_1_1.dpt` for the ER-IR scans (specimen 1, scans 0 and 1)
   - `realgar_ATR.dpt` for the ATR standard

### Step 3: Put the scans in a new dated folder

1. Open the `scans` folder in the repository.
2. Create a new folder named with the scan date: `2026-11-05`.
3. Copy the three files into it.

### Step 4: Tell the program the date and the operator

1. Open `scan_batches.csv` the same way as in step 1 (plain-text editor).
2. At the end of the last line press **Enter** and type:
   ```
   2026-11-05/,2026-11-05,Maria Gabriela Rivas Carmona
   ```
   The first part is the folder name followed by a slash, the second part is the date (year-month-day), the third is the operator's name exactly as in `operators.csv`. Save the file.

### Step 5: Do a trial run

1. Open the Terminal inside the repository folder (Part 1, Step 3). It should show the folder name `erir-pigment-spectral-database`.
2. Type this command and press **Enter** (Windows: `python` instead of `python3`):
   ```
   python3 import_scans.py scans pigment_spectral_standards.db --dry-run
   ```
   `--dry-run` means "show me, but do not save anything".
3. Read the report that appears in the Terminal. Under **Added in this run** you should see:
   ```
   - Realgar, ATR: 1
   - Realgar, ER-IR: 2
   ```
   Under **Files whose name matched no rule** and **Scans added without a date** and **Scans added without an operator** you should see `(none)`.
4. If your scans are listed under "matched no rule", the filename does not start with the `file_key` you typed in `materials.csv`, or it does not follow the pattern in Part 2. Fix the name or the key, and do the trial run again.

### Step 6: Run it for real

1. In the same Terminal window, type the same command **without** `--dry-run` and press **Enter**:
   ```
   python3 import_scans.py scans pigment_spectral_standards.db
   ```
2. The third line of the report now says `Saved` and `3 scans added`.

### Step 7: Check the result

1. Open `pigment_spectral_standards.db` in DB Browser for SQLite.
2. Click the **Browse Data** tab and choose the table **Material**. The last row should be Realgar, with its formula.
3. Choose the table **Measurement**. The last three rows are the new scans. The two ER-IR scans have a number in the column `ReferenceMeasurementID`: that is the link to the realgar ATR standard.
4. Close DB Browser without changing anything.

### Step 8: Save your work to GitHub

1. Open GitHub Desktop. It lists the changed files: `materials.csv`, `scan_batches.csv`, the database, `import_report.md` and the three new scans.
2. Type a short description in the **Summary** box, for example `Add realgar`.
3. Click **Commit to main**, then click **Push origin**.

**For a powdered pigment** (synthetic), use `is_synthetic` = `1`, a `file_key` that starts with `synth_` (for example `synth_cinnabar`), and the filenames `synth_cinnabar_ER_IR_1.dpt` and `synth_cinnabar_ATR.dpt`. The ER-IR and ATR scans then share one specimen (one jar of powder).

**If you forget Step 1:** the scans are not loaded, and the report lists them under "Files whose name matched no rule". Nothing is guessed. Do Step 1, then run the command again.

## Workflow 3: An ATR standard collected later

Example: Magnetite has no ATR standard, so its ER-IR scans are unlinked and tagged `needs-atr-recollection`.

1. Collect the ATR spectrum and export it from OPUS as absorbance.
2. Name it `magnetite_ATR.dpt`.
3. Follow Workflow 1 from step 3 (new dated folder, line in `scan_batches.csv`, dry run, run, commit).

The program loads the standard, links **every earlier Magnetite ER-IR scan** to it, and removes the tag. The report says how many scans were linked.

If a material already has an ATR standard, a second one is loaded but the existing links are kept.

## Workflow 4: A scan was wrong and has been re-exported

The program skips any file whose path is already in the database, so a corrected file with the same name is not picked up. First remove the old rows by hand.

1. Open `pigment_spectral_standards.db` in DB Browser for SQLite.
2. Click the **Execute SQL** tab.
3. Delete everything in the box and paste the two lines below, changing only the file path in the first line to the scan you are replacing:
   ```sql
   DELETE FROM SpectralFile WHERE FilePath = 'oxides/hematite_ER_IR_2_3.dpt';
   DELETE FROM Measurement WHERE MeasurementID NOT IN (SELECT MeasurementID FROM SpectralFile);
   ```
4. Click the **play button** (the triangle) above the box. You should see `Execution finished without errors`.
5. Click **Write Changes** (top bar) or press Ctrl+S (Command+S on Mac). **This step is easy to forget, and without it nothing is saved.**
6. **Close DB Browser.**
7. Replace the file in the `scans` folder with the corrected one, keeping the same name.
8. Run the program (dry run first, then for real), then commit and push in GitHub Desktop.

Do not delete an ATR standard this way while ER-IR scans point to it.

## Workflow 5: A new person is doing the scans

Example: Jane Smith (Università di Padova) takes over the scanning from 12 January 2027. The scans are made with the same instrument and the same settings as before, so only the person changes.

1. **Add the person to `operators.csv`.** Open it in a plain-text editor and add one line at the bottom: name, email, institution.
   ```
   Jane Smith,jane.smith@unipd.it,University of Padova
   ```
2. **Name the scans and put them in a new dated folder** as in Workflow 1 (`scans/2027-01-12/`).
3. **Add the folder to `scan_batches.csv`** with her name, spelled exactly as in `operators.csv`:
   ```
   2027-01-12/,2027-01-12,Jane Smith
   ```
4. Dry run, run, commit and push as in Workflow 1.

The program creates the operator in the database the first time it is used. Earlier scans keep their original operator. If the name in `scan_batches.csv` is not in `operators.csv`, the program stops with a message and saves nothing. If the operator column is left empty the scans are loaded without an operator and listed in the report.

The instrument and the scan settings are not asked for: they are the standard setup. If the setup ever changes, the program has to be changed (ask Claude), because the old and new scans must not be recorded as identical.

When the person who runs the database changes, see [`HANDOVER.md`](HANDOVER.md).

## Workflow 6: Scans that are not standards (real objects, unknown specimens)

**Not covered yet.** The program handles standards, where the material is always known. A scan from a real object needs a specimen with no material, an Object, a Collection and spot descriptions, and its identification is written later by the matching software. When you have such scans, the program needs a new mode. Ask Claude.

---

# Part 4: Reference

## How to edit the sheets (`materials.csv`, `scan_batches.csv` and `operators.csv`)

These are plain text tables. Each line is one row, and commas separate the columns. **Do not change the first line (the column names).**

**The safest way is a plain text editor**: Notepad on Windows, or TextEdit on Mac (choose **Format, then Make Plain Text** first). Open the file, add your line at the bottom, press Enter at the end so the file ends with a new line, and save.

If you prefer Excel, Numbers or Google Sheets, be careful:
- **Dates:** they change dates such as `2026-11-05` into `11/5/2026`, which breaks the program. Format the date columns as **Text** before typing, or use a text editor.
- **Saving:** save as **CSV (UTF-8)**, never as `.xlsx`.

Rules for all sheets:
- No empty lines in the middle.
- A value that contains a comma must be inside double quotes, for example `"(Na,Ca)8(AlSiO4)6(SO4,S,Cl)2"`.
- Dates are always year-month-day with dashes: `2026-11-05`.
- In `scan_batches.csv`, the columns are `path_prefix,date,operator`. The first column is a folder name **ending with a slash**. The longest matching folder wins, so a line for `carbonates/powder_dolomite/` overrides the line for `carbonates/`.
- The operator name in `scan_batches.csv` must be spelled exactly as in `operators.csv`.
- In `operators.csv`, the columns are `name,email,institution`.

## Reading the report

The report is printed in the Terminal and saved as `import_report.md` in the repository folder. You can open that file in any text editor or in GitHub.

| Section | What it means | What to do |
|---|---|---|
| Added in this run | What was loaded, by material and mode | Check that it matches what you expected |
| Scans added without a date | Scans whose folder has no line in `scan_batches.csv` | Add a line to `scan_batches.csv`, or type the date into the database |
| Scans added without an operator | Scans whose folder has no line, or an empty operator, in `scan_batches.csv` | Add the operator to the line, or type it into the database |
| Skipped: empty or unreadable | Files that are empty or not plain text | Re-export them from OPUS |
| Removed as duplicates | A file with exactly the same intensity values as another file in the same material and mode. The lowest scan number is kept | Nothing. The files stay in `scans/` until you delete them |
| Files whose name matched no rule | Not loaded | Fix the filename, or add the material to `materials.csv` |
| Filename typos corrected | Known misspellings read as the right name | Nothing |
| Things to check | Materials still missing an ATR standard | Nothing, or collect the standard (Workflow 3) |

## If something goes wrong: undoing a run

The database is saved in GitHub, so any run can be undone.

**Before you have committed** (the run just finished and you do not like the result):
1. Open GitHub Desktop. The **Changes** list shows every file the run changed.
2. Right-click `pigment_spectral_standards.db` and choose **Discard changes**. Do the same for `import_report.md`.
3. The database is back to how it was. The scan files you added stay in `scans/`.

**After you have committed and pushed:**
1. In GitHub Desktop, click the **History** tab.
2. Right-click your commit and choose **Revert changes in commit**, then click **Push origin**.

A run is also all or nothing: if the program stops with an error, nothing is saved.

## What the program never does

- It never changes or deletes a scan file.
- It never converts a spectrum. It loads the numbers in the file, so the file must already be absorbance.
- It never changes a measurement that is already in the database.
- It never records who the operator is by guessing: it only uses `scan_batches.csv`.
