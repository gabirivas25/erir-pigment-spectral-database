# Import report

Loaded **256 measurements** from 256 readable, recognised files; 220 of them carry a link to an ATR standard.

Foreign-key check: no problems

## Per material

| Material | ER-IR loaded | ER-IR in old database | ATR loaded | Specimens |
|---|---|---|---|---|
| Aragonite | 18 | - | 1 | 3 |
| Azurite | 22 | - | 1 | 3 |
| Calcite | 21 | - | 1 | 3 |
| Cerussite | 20 | - | 1 | 3 |
| Cinnabar | 11 | - | 1 | 3 |
| Dolomite | 19 | - | 1 | 3 |
| Goethite | 19 | - | 1 | 3 |
| Hematite | 15 | - | 1 | 3 |
| Lazurite | 13 | - | 1 | 3 |
| Magnetite | 22 | - | 0 | 2 |
| Malachite | 10 | - | 1 | 2 |
| Orpiment | 20 | - | 1 | 3 |
| Synthetic malachite | 12 | - | 1 | 1 |
| Synthetic ultramarine | 10 | - | 1 | 1 |
| Verdigris | 10 | - | 1 | 1 |

## Skipped: empty or unreadable (0)

(none)

## Removed as exact duplicates (0)

(none)

## Not used on purpose (0)

(none)

## Files whose name matched no rule, not loaded (0)

(none)

## Filename typos corrected (6)

- `DolemitePowder.0.dpt` read as `dolomitepowder.0`
- `LasuriteFrag1_p1.0.dpt` read as `lazuritefrag1_p1.0`
- `cinnabr1.3.dpt` read as `cinnabar1.3`
- `dolomiter_ER_9.0.dpt` read as `dolomite_er_9.0`
- `hematitie1.3.dpt` read as `hematite1.3`
- `verdigirs_ER_2.0.dpt` read as `verdigris_er_2.0`

## Decisions the script made that you may want to check

- Minerals with ER-IR scans but no ATR standard (tagged `needs-atr-recollection`): Magnetite
- Stored under another name: `PowderATR/OrpimentPowder.1.dpt` as `PowderATR/Orpiment_ATR.dpt`
- The `powder_dolomite` scans (10) are stored under Dolomite specimen 2.
- Lazurite: scan names give the point (`p1`, `p2` ...), stored as the specimen spot description.
- Spectra are loaded exactly as in the files and never converted.
- DateTime is empty for every measurement.
