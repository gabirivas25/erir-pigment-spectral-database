# Naming guide: scans and folders

The import program finds out everything about a scan **from its filename**: which material it is, which specimen, and whether it is an ER-IR scan or an ATR scan. It finds the **date and the operator** from the folder the scan is in. So names matter, and this guide is the single place where the rules are written down.

**A file with a name that does not follow these rules is not loaded.** The report lists it under "Files whose name matched no rule". Nothing is lost and nothing is guessed. Rename the file and run the program again.

There are three things to name:

1. [Your scans](#1-how-to-name-your-scans)
2. [Your folders](#2-how-to-name-your-folders)
3. [Your materials in `materials.csv`](#3-how-to-name-a-material-in-materialscsv)

---

## 1. How to name your scans

### The four patterns

| Kind of scan | Pattern | Example |
|---|---|---|
| ER-IR scan of a **mineral** | `mineralname_ER_IR_specimen_scannumber.dpt` | `hematite_ER_IR_2_16.dpt` |
| ATR standard of a **mineral** | `mineralname_ATR.dpt` | `hematite_ATR.dpt` |
| ER-IR scan of a **powdered pigment** | `synth_pigmentname_ER_IR_scannumber.dpt` | `synth_verdigris_ER_IR_3.dpt` |
| ATR scan of a **powdered pigment** | `synth_pigmentname_ATR.dpt` | `synth_verdigris_ATR.dpt` |

How to read them:
- `hematite_ER_IR_2_16.dpt` is an **ER-IR** scan of **hematite**, **specimen 2**, **scan 16**.
- `hematite_ATR.dpt` is the **ATR** standard of **hematite**.
- `synth_verdigris_ER_IR_3.dpt` is an **ER-IR** scan of the powdered pigment **verdigris**, **scan 3**.

### The rules

1. **Every ATR file has `ATR` in its name.** Every ER-IR file has `ER_IR` in its name. This way the two can never be confused.
2. **Use underscores** between the parts, never spaces, dashes or dots (the only dot is the one before `dpt`).
3. **`mineralname` and `pigmentname` are the `file_key` of the material** in `materials.csv` (see section 3). `hematite` and `synth_verdigris` are file keys. A powdered pigment's key always starts with `synth_`.
4. **Write `ER_IR` and `ATR` in capitals, the material in lower case.** The program ignores capitals, but one style keeps the folder easy to read.
5. **Minerals have a specimen number, powdered pigments do not.** A mineral can have several pieces (specimens). A powdered pigment is one jar, so it only has a scan number.
6. **A mineral has one ATR standard**, so its ATR file has no numbers.
7. **The file type is `.dpt`**, exported from OPUS as **absorbance**.

### What "specimen" and "scan number" mean

- A **specimen** is one physical piece or sample of a mineral. Calcite specimen 1 and calcite specimen 2 are two different pieces. A new piece gets the next specimen number.
- A **scan number** counts the scans on that specimen (or that jar of powder).
- **Never reuse a number.** Before naming new scans, look in the `scans` folder (search for `calcite_ER_IR_1_`) and continue from the highest scan number you find. If the last one is `calcite_ER_IR_1_14.dpt`, the next is `calcite_ER_IR_1_15.dpt`.
- A third specimen of calcite starts a new series: `calcite_ER_IR_3_0.dpt` (or `_1`, either start is fine).

### Right and wrong

| Name | Right? | Why |
|---|---|---|
| `hematite_ER_IR_2_16.dpt` | Yes | |
| `Hematite_ER_IR_2_16.dpt` | Works | Capitals are ignored. Prefer lower case |
| `hematite_ATR.dpt` | Yes | |
| `synth_verdigris_ER_IR_3.dpt` | Yes | |
| `hematite2.16.dpt` | **No** | Old naming. No `ER_IR` |
| `hematite_ER_2_16.dpt` | **No** | It must be `ER_IR`, with both parts |
| `hematite_ER_IR_16.dpt` | **No** | A mineral needs the specimen number too |
| `hematite_ER_IR_2_16 copy.dpt` | **No** | No spaces, no "copy" |
| `hematite_powder.dpt` | **No** | An ATR file must have `ATR` in its name |
| `verdigris_ER_IR_3.dpt` | **No** | A powdered pigment key must start with `synth_` |
| `synth_verdigris_ER_IR_1_3.dpt` | **No** | Powdered pigments have no specimen number |

### If you made a mistake

Rename the file in Finder or File Explorer (right-click the file, then **Rename**), and run the program again. A file that was not loaded can simply be renamed and loaded. For a file that **was** already loaded under a wrong name, ask Claude: the old name is stored in the database.

---

## 2. How to name your folders

The scan files live in the `scans` folder. The folder a scan is in tells the program **the date of the scan and who made it**. The folder name does not decide the material: that comes from the filename.

### The rules

1. **Folder names are lower case**, with underscores instead of spaces, and no capitals.
2. **A new batch of scans goes in its own new folder, named with the date of the scan**: year-month-day, with dashes.
   ```
   scans/2026-11-05/
   ```
3. **One folder per scan date.** If you scan on two different days, make two folders. If you did two separate sessions on the same day, use `2026-11-05` for the first and `2026-11-05_b` for the second, each with its own line in `scan_batches.csv`.
4. **Never put new scans in the older folders** (`carbonates`, `oxides`, and so on). They already carry their own older date, so a new scan would get the wrong date.
5. **Every new folder needs one line in `scan_batches.csv`**: the folder name **followed by a slash**, a comma, the date, a comma and the operator's name.
   ```
   2026-11-05/,2026-11-05,Maria Gabriela Rivas Carmona
   ```
   The operator must already be in `operators.csv`, spelled the same way (see `WORKFLOW.md`, Workflow 5). If you forget the line, the scan is still loaded, its date and operator stay empty and the report lists it under "Scans added without a date" and "Scans added without an operator".

### The folders that exist now

```
scans/
├── carbonates/                 aragonite, azurite, calcite, cerussite, dolomite, malachite
│   └── powder_dolomite/        the leftover dolomite scans (specimen 2)
├── oxides/                     goethite, hematite, magnetite
├── powder_atr/                 one ATR standard per mineral
├── silicates/                  lazurite
├── sulfides/                   cinnabar, orpiment
└── synthetics/
    ├── malachite/              synthetic malachite
    ├── ultramarine/            synthetic ultramarine
    └── verdigris/              verdigris
```

These are the folders from the first scan session. Their dates and operator are in `scan_batches.csv`: 2026-04-23 for the mineral folders, 2026-10-10 for `synthetics`, and 2026-10-09 for `carbonates/powder_dolomite`.

Subfolders inside a dated folder are allowed (for example `scans/2026-11-05/realgar/`). The date still comes from the first part of the path.

---

## 3. How to name a material in `materials.csv`

Each material has one line in `materials.csv`. Its first column, `file_key`, is the word the scan filenames start with.

| For | `file_key` | Example |
|---|---|---|
| A mineral | The mineral name, lower case, no spaces | `calcite`, `lazurite` |
| A powdered pigment | `synth_` followed by the pigment name | `synth_verdigris`, `synth_ultramarine` |

Rules:
- Lower case, underscores instead of spaces, no other punctuation.
- The `file_key` must be **exactly** the start of the scan filenames: key `calcite` goes with `calcite_ER_IR_1_0.dpt` and `calcite_ATR.dpt`.
- A key is used once. Do not change a key that already has scans loaded.
- For a powdered pigment, `is_synthetic` is `1`. The material name shown in the database does not need the `synth_` prefix (the key `synth_verdigris` has the material name `Verdigris`).

The full step-by-step for adding a new material is in [`WORKFLOW.md`](WORKFLOW.md), Workflow 2.

---

## Checklist before you run the program

- [ ] Every ER-IR file has `ER_IR` in its name, and every ATR file has `ATR`.
- [ ] Mineral ER-IR files have a specimen number and a scan number. Powdered pigment files only a scan number.
- [ ] No spaces, no old-style names such as `hematite2.16.dpt`.
- [ ] I did not reuse a scan number.
- [ ] The new scans are in a **new folder named with the date** (`scans/2026-11-05/`).
- [ ] That folder has a line in `scan_batches.csv` with the date and the operator, and the operator is in `operators.csv`.
- [ ] A new material has a line in `materials.csv`, and its `file_key` matches the start of the filenames.
