# Interface mock-up

A design for the web interface described in Chapter 5 of the thesis. It is a mock-up: three static pages with example data, no server and no matching. The interface itself has not been built.

**To look at it:** open `materials.html` in a web browser. The three pages link to each other. Fonts load from Google Fonts; without a connection the browser uses its default font.

| Page | File | Figure in the thesis |
|---|---|---|
| Materials | `materials.html` | Fig. 5.1 |
| Match an unknown spectrum | `match.html` | Fig. 5.2 |
| Scan (spectrum viewer) | `scan.html` | Fig. 5.3 |

In `match.html` the unknown spectrum and the selected standard are drawn one above the other on the same wavenumber axis. In `scan.html` the ER-IR scan and its ATR standard are drawn the same way.

**Files:** `data.js` holds the calcite ER-IR scan `calcite_ER_IR_1_3` and the calcite ATR standard (reduced to about 100 points each, read from the database). `plot.js` draws the plots; `match.js` and `scan.js` build the plots of their pages. `unipd-logo.svg` is the University of Padova logo. `screenshots/` holds the images used in the thesis.

**Example data.** The unknown spectrum on the Match page is the calcite scan with a small change, and the scores are made up. The counts on the Materials page (15 materials, 242 ER-IR scans, 14 ATR standards) are from an earlier state of the database; the database now holds 20 materials, 288 ER-IR scans and 19 ATR standards.

**Not in the mock-up:** a place to add results of other techniques (XRF, Raman), the display of the chosen method, region and peak settings next to each result, and the exported report. Chapter 5 says the interface should have them.
