# Handover: who runs and owns this database

This page is for whoever takes over the database when the person running it leaves (the thesis author, Maria Gabriela Rivas Carmona, will not be running it after graduation). It says what exists, who owns what, and what has to be decided and done.

## 1. Decisions that are still open

These are for the author and the advisors (Prof. Alfonso Zoleo, Prof. Nicola Orio). Fill them in.

| Question | Decision | Decided by / date |
|---|---|---|
| Who owns the GitHub repository `gabirivas25/erir-pigment-spectral-database` after graduation? (a) transfer to a university or laboratory account, (b) transfer to the next person, (c) stay on the author's account with the next person added as administrator | | |
| Who is the next person running the scans and the import? | | |
| Who is the contact for questions about the data? | | |
| Who may add scans? (everyone in the group, or only the person above) | | |

Why this matters: the repository is on a **personal** GitHub account. If that account is closed or abandoned, the database, the scans and the history go with it. Ownership should move to someone who stays.

## 2. How to change ownership (GitHub)

- **Transfer the repository:** on GitHub open the repository, then **Settings**, scroll to **Danger Zone**, **Transfer ownership**, and type the new owner's account or organisation name. Issues, history and links are kept, and GitHub redirects the old address.
- **Or add an administrator:** **Settings**, **Collaborators**, **Add people**, and give the role **Admin**. The author can then leave without losing access for the group.
- Do one of these **before** the author's university account or email is closed.
- After a transfer, each person who has a local copy should check the address in GitHub Desktop (**Repository, Repository settings**) and pull again.
- The repository has a `LICENSE` file. Whoever owns it should confirm it is the licence the university and advisors want.

## 3. Who else has access

- The Claude GitHub app (used by the author to help with the import) has push access to this repository. The new owner should check **Settings, Integrations** and keep or remove it as they prefer. The repository works without it.
- Anyone who can push can change the database, so give write access only to people who run the import.

## 4. The operator changes

Each measurement records the operator, taken from `scan_batches.csv`. When a new person starts scanning:

1. Add them to `operators.csv`.
2. Put their scans in a new dated folder and add a line to `scan_batches.csv` with their name.

Step by step: `WORKFLOW.md`, Workflow 5. Earlier scans keep the operator they already have.

## 5. The instrument and the settings do not change

The program records one standard setup for every scan, whoever the operator is:

| | ER-IR | ATR |
|---|---|---|
| Instrument | Bruker LUMOS II FTIR microscope | same |
| Resolution | 4 cm-1 | 4 cm-1 |
| Number of scans | 64 | 32 |
| Detector window / crystal | ZnSe | ZnSe |
| Aperture | 30 um | n/a |
| Notes | | Positioning speed: medium. Pressure: low. |
| Site | Laboratory | Laboratory |
| Intensity mode | Absorbance | Absorbance |

A new operator should use the same setup. If the instrument or the settings ever change, the program (`import_scans.py`) has to be changed too, otherwise the new scans would be recorded with the wrong settings.

## 6. Every file that matters

| File | What it is | Who edits it |
|---|---|---|
| `pigment_spectral_standards.db` | The database (SQLite) | The import program; by hand only for corrections (`WORKFLOW.md`, Workflow 4) |
| `scans/` | The `.dpt` scan files, the original data | Add new files in a new dated folder. Never edit or delete old ones |
| `import_scans.py` | The program that adds scans to the database | Only when the setup or the rules change |
| `materials.csv` | One line per material: name, formula, source, specimen type | Add a line for each new material |
| `scan_batches.csv` | Date and operator of each folder of scans | Add a line for each new folder |
| `operators.csv` | The people who make scans | Add a line for each new person |
| `scan_rename_map.csv` | Old and new filename of every scan from the renaming in 2026, with lazurite point numbers | Not edited. It is a record |
| `import_report.md` | What the last import loaded, skipped and found wrong | Written by the program |
| `README.md` | What the database is, the tables, example queries | When the design changes |
| `WORKFLOW.md` | Step-by-step instructions for adding scans, materials and operators | When the process changes |
| `NAMING.md` | How to name scans, folders and materials. Files with other names are not loaded | When the rules change |
| `HANDOVER.md` | This page | When ownership or people change |
| `pigment_spectral_standards_sqlite_schema.sql` | Creates an empty SQLite database | When the design changes |
| `pigment_spectral_standards_mysql_schema.sql` | The same design for MySQL 8. Only checked for syntax, **not yet run on a real server** | When the design changes |
| `ER_Diagram.png` | Diagram of the 17 tables | When the design changes |
| `Archived/` | The earlier schema, its data and analysis scripts | Not edited |

## 7. Checklist before the author leaves

- [ ] Section 1 is filled in.
- [ ] Repository ownership is transferred, or the next person is an administrator (section 2).
- [ ] The next person has Python and GitHub Desktop working and has run the test in `WORKFLOW.md`, Part 1, Step 4 (it should say 0 scans added).
- [ ] The next person has added themselves to `operators.csv`.
- [ ] The next person has done one real import with a dry run first (`WORKFLOW.md`, Workflow 1).
- [ ] The advisors know where the repository is and who owns it.
- [ ] Open data items (below) are either done or written down as open.

## 8. Open data items at the time of writing

- Verdigris: the supplier is recorded as `Unknown`. It needs a photo of the label, then `materials.csv` and the database are updated.
- Magnetite has no ATR standard. Its ER-IR scans carry the tag `needs-atr-recollection` until one is collected (`WORKFLOW.md`, Workflow 3).
- The MySQL schema has not been run on a real server.
- Scans of real objects are not supported by the program yet (`WORKFLOW.md`, Workflow 6).
