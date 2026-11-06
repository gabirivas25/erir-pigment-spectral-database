# Analysis scripts: tests of the matching methods

**These are not the matching program.** The program that matches an unknown spectrum is `match_unknown.py` in the main folder of the repository. The scripts here only test how well the matching methods work, for the thesis. To match a spectrum, use `match_unknown.py`; nothing in this folder is needed for that.

These scripts repeat the tests reported in Chapters 3 and 4 and Appendix D of the thesis. They use the database in this repository (schema v5: 288 ER-IR scans, 19 ATR scans, 20 materials) and the matching settings of `match_unknown.py`. They only read the database.

**Requirements:** Python 3, `numpy`, `scipy`. Run each script from the repository folder with `python3 -I analysis_scripts/SCRIPT DATABASE`. Scripts that use the 15 layered mock-up scans (tav_2, tav_5, tav_8) take a second argument, the path to those `.dpt` files in quotes, for example `'tav_scans/*.dpt'`. The mock-up scans are not stored in this repository.

**Settings kept fixed** (the defaults of `match_unknown.py`; the peak settings can be changed there with `--prominence`, `--spacing` and `--tolerance`, and the scripts that test them set their own values): 800-point grid from 650 to 3990 cm-1; standard normal variate; Savitzky-Golay first derivative, window 11, order 2; Pearson correlation; peaks found with prominence 0.5 and spacing 20 cm-1, matched within 8 cm-1. A material's score is the best score among its scans. Materials with equal scores are ordered by the position of their standards in the database. Synthetic malachite is counted as malachite.

| Script | What it tests | Extra argument |
|---|---|---|
| `table32_rerun.py` | 18 variants of the matching (regions, derivative windows, smoothing, baseline, combinations), leave-one-specimen-out on 221 scans | none |
| `tie_sensitivity.py` | The same variants, scored three ways for tied scores (by order, in favour of, against the correct material) | none |
| `permaterial_testA.py` | First place and top three for each material, with what was ranked first when the correct material was not | none |
| `test_b_leave_one_scan_out.py` | Leave-one-scan-out on 67 scans of the 7 manufactured pigments | none |
| `start600_test.py` | Grid starting at 600 cm-1 compared with 650 cm-1 (221 and 67 scans, and the 15 mock-up scans) | tav scans |
| `peak_settings_grid.py` | Grid search of prominence, spacing and tolerance, 64 combinations, on the standards | none |
| `tav_peak_settings.py` | How much the peak settings change the top material and top three of the 15 mock-up scans | tav scans |
| `tav_selected_settings.py` | The settings that scored highest on the standards, run on the 15 mock-up scans | tav scans |
| `count_peaks.py` | Number of peaks per measurement with the matcher's settings | none |
| `time_matcher.py` | Run time of one match against libraries of 288 to 10,000 spectra (copies of the real spectra). Imports `match_unknown.py`, so run it from the repository folder; edit the `sys.path.insert` line at the top if the repository is elsewhere | none |

**Output files:** some scripts write a `.json` file (for example `peak_settings_grid.json`) in the folder where they are run. These are not committed.

**Notes**
- The mock-up tests assume no correct answer: they count how many scans change their top material or top three.
- `test_b_leave_one_scan_out.py` has a long header comment made of several earlier descriptions joined together; the code is what counts.
- The run-time test uses copies of the 288 spectra, so it shows how time grows with library size, not whether accuracy holds.

## earlier_work/

Scripts from the early part of the project, before the matching tests. They were written for the earlier file layout and some contain paths that must be edited before they run (for example `/mnt/user-data/outputs`).

| Script | What it does |
|---|---|
| `ERIR_vs_ATR_plotting_and_pdf_report.py` | Plots each ER-IR scan of a mineral against its ATR standard and builds a PDF report |
| `ERIR_KramersKronig_transform_plotting.py` | Kramers-Kronig transform of ER-IR scans (aragonite) plotted against the ATR standard |
| `analyze_carbonate_band.py` | Analysis of the carbonate band position in the carbonate scans |
| `generate_anomalous_dispersion_figure.py` | Draws the figure of the refractive index n and absorption index k near an absorption band |
| `mineral_classifier_demo.py` | Proof-of-concept classifier of mineral identity from ER-IR scans |

The earlier analysis scripts that used the old schema are in [`../Archived/`](../Archived/).
