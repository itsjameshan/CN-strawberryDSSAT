# UFBA1401 Research Result Merge Audit

This document records the selective merge scope for the research result from branch
`24代码组A翟翔宇`. The goal is to keep only the model/data changes needed to reproduce the
UFBA1401 DSSAT-vs-Python comparison figure, and to exclude unrelated website, slide, zip,
video, and presentation assets.

## Merge Decision

- Source research branch: `origin/24代码组A翟翔宇`
- Safe integration branch: `codex/reproduce-ufba1401-comparison`
- Base branch: `origin/main`
- Base commit inspected: `2655a57e6160eee88d95d948204d7d3f26667a98`
- First integration commit: `f63585f2d53417fdca3ed36a5c845c774d5fe94a`
- Original branch was not directly merged because it has unrelated Git history and creates add/add conflicts with `main`.

## Files Included

| File | Status vs `origin/main` | Why Included |
| --- | --- | --- |
| `cropgro-strawberry-implementation.py` | Modified | Main research model implementation and calibrated UFBA1401 logic. |
| `load_dssat_weather.py` | Added | Parses DSSAT `.WTH` weather files and supports cross-year UFBA1401 weather loading. |
| `weather/UFBA1401.WTH` | Added | 2014 UFBA1401 weather input used by the Python model. |
| `weather/UFBA1501.WTH` | Added | 2015 continuation weather input used by the Python model. |
| `dssat_results/UFBA1401/PlantGro.OUT` | Added | DSSAT/Fortran reference output for the exact UFBA1401 comparison window. |
| `generate_ufba1401_comparison.py` | Added | Reproducible script that regenerates the comparison CSVs and figure. |
| `comparison_results/dssat_python_detailed_comparison.csv` | Modified | Regenerated row-level DSSAT-vs-Python comparison data. |
| `comparison_results/dssat_python_summary_comparison.csv` | Modified | Regenerated summary statistics and correlations matching the target figure. |
| `comparison_results/ufba1401_dssat_python_comparison.png` | Added | Generated 3x3 comparison figure for visual review. |
| `docs/UFBA1401_research_merge_audit.md` | Added | Records the selective merge scope, file-level rationale, and verification evidence. |

## Files Excluded

The integration branch intentionally excludes unrelated content from the source branch:

- HTML pages such as `index.html`, `主页.html`, `发布A.html`, `研发A.html`, `研发B.html`
- PPTX files
- zip archives
- MP4/video files
- training/demo image folders
- unrelated markdown guides and presentation notes
- whole-repository snapshot artifacts from the unrelated branch history

The safe branch diff contains only the ten included files listed above.

## Key Code Changes

Line references below are from `codex/reproduce-ufba1401-comparison`.

### `cropgro-strawberry-implementation.py`

This file changed from the previous simplified model into the DSSAT-aligned research model.
The main changed areas are:

| Lines | Area | Purpose |
| --- | --- | --- |
| 20-25 | Optional `numba` fallback | Keeps the model importable even when `numba/llvmlite` is unavailable; falls back to plain Python functions. |
| 29-124 | `PlantState` initial state | Sets DSSAT-aligned transplant initial biomass, LAI, root depth, reproductive state, seed/shell biomass, and diagnostic variables. |
| 147-203 | Thermal time and DSSAT table helpers | Adds DSSAT-style thermal-time and interpolation helper functions. |
| 233-334 | Photosynthesis helper | Implements DSSAT PHOTO-style canopy photosynthesis and radiation interception. |
| 606-730 | `CropgroStrawberry.__init__` | Adds UFBA1401/Radiance configuration, plant density, row spacing, stage thresholds, fruit cohort state, harvest state, and diagnostics. |
| 643-647 | KCAN handling | Uses `KCAN=0.67` directly to match observed DSSAT strawberry behavior instead of applying row-spacing correction. |
| 751-788 | Thermal time / phenology | Uses stage-aware DSSAT-like thermal time and phenological progression. |
| 902-1589 | Biomass partitioning | Adds DSSAT-style carbon allocation, `XFRUIT`, `FRLF/FRSTM/FRRT`, VSSINK limitation, seed/shell growth demand, and source-sink balancing. |
| 964-1038 | Stem and leaf allocation calibration | Includes calibrated `FRSTMF=0.28` and post-R1 allocation interpolation. |
| 1155-1264 | Seed and fruit set parameters | Uses calibrated `WTPSD`, `SDPDV`, `SFDUR`, `THRSH`, `PODUR`, and PMAX-style fruit set constraints. |
| 1481-1490 | Seed/shell biomass accounting | Recalculates `seed_biomass` and `shell_biomass` from fruit cohorts as the source of truth. |
| 1770-1966 | Flower-to-pod and fruit cohort updates | Adds fruit cohort aging, shell/seed growth, detachment/harvest behavior, and G#AD conversion. |
| 1964-1966 | `G#AD` conversion | Uses conversion factor `795.5 = SDPDV(185) * PLTPOP(4.3)` to align fruit-number scale with DSSAT. |
| 1970-2147 | Daily simulation output | Emits the columns required for comparison, including `vwad`, `seed_biomass`, `shell_biomass`, and diagnostic fields. |
| 2230-2266 | Growth loop and plotting | Runs daily simulation and keeps plotting helpers. |
| 2341-2390 | UFBA1401 example run | Loads `weather/UFBA1401.WTH` and `weather/UFBA1501.WTH`, uses UFBA1401 planting date `14282`, and configures Radiance parameters. |

Important mapping decision:

- DSSAT `GWAD` is grain/seed weight, so the comparison script maps Python `seed_biomass * 43` to `GWAD`.
- Python `fruit_biomass` includes seed plus shell/fleshy part and must not be used for `GWAD`, otherwise the target figure is not reproduced.

### `load_dssat_weather.py`

| Lines | Area | Purpose |
| --- | --- | --- |
| 24-36 | `dssat_date_to_calendar` | Converts DSSAT `YYDDD` dates such as `14282` to calendar dates. |
| 40-93 | `_parse_wth_file` | Parses DSSAT `.WTH` rows, extracts SRAD/TMAX/TMIN/RAIN/WIND/RHUM, converts wind from km/day to m/s. |
| 97-146 | `load_dssat_weather` | Accepts one or more `.WTH` files, merges cross-year weather, deduplicates by DSSAT date, and slices from the planting date. |
| 149-150 | Manual test paths | Documents the exact UFBA1401/UFBA1501 weather files used by the research result. |

### `generate_ufba1401_comparison.py`

| Lines | Area | Purpose |
| --- | --- | --- |
| 13-14 | Unit constants | Defines `43.0` kg/ha per g/plant and `795.5` fruit-number conversion. |
| 16-25 | Variable map | Defines the exact figure variables: `LAID`, `LWAD`, `SWAD`, `GWAD`, `RWAD`, `VWAD`, `G#AD`, `RDPD`. |
| 20 | `GWAD` mapping | Maps `GWAD` to Python `seed_biomass`, not total `fruit_biomass`. |
| 38-78 | `parse_plantgro` | Reads the UFBA1401 DSSAT `PlantGro.OUT` block. |
| 80-109 | `run_python_model` | Runs the Python model with UFBA1401 weather and Radiance parameters. |
| 112-128 | `convert_python_output` | Converts Python units to DSSAT comparison units. |
| 118 | `GWAD` conversion | Uses `seed_biomass * 43.0`. |
| 125 | `G#AD` conversion | Uses `fruit_number * 795.5`. |
| 131-166 | `build_comparison` | Checks row count and DAP alignment, then produces detailed and summary comparison DataFrames. |
| 170-221 | `plot_comparison` | Generates the 3x3 figure with 8 time-series panels plus mean-value comparison. |
| 211-214 | Figure title | Matches the target figure title and experiment metadata. |
| 224-248 | CLI entrypoint | Default input is `dssat_results/UFBA1401/PlantGro.OUT`; outputs CSVs and PNG to `comparison_results/`. |

## Data Files

| File | Size | Purpose |
| --- | ---: | --- |
| `weather/UFBA1401.WTH` | 22,106 bytes | 2014 UFBA1401 weather data. |
| `weather/UFBA1501.WTH` | 22,106 bytes | 2015 weather continuation. |
| `dssat_results/UFBA1401/PlantGro.OUT` | 29,949 bytes | DSSAT reference output, 85 daily rows, DAP 0-84. |
| `comparison_results/dssat_python_detailed_comparison.csv` | 25,618 bytes | Row-level comparison data. |
| `comparison_results/dssat_python_summary_comparison.csv` | 887 bytes | Summary statistics and correlations. |
| `comparison_results/ufba1401_dssat_python_comparison.png` | 409,190 bytes | Generated comparison figure. |
| `docs/UFBA1401_research_merge_audit.md` | 9,803 bytes | Selective merge audit and verification record. |

## Verification

Run this from the repository root after checking out the safe integration branch:

```bash
MPLBACKEND=Agg python generate_ufba1401_comparison.py --output-dir comparison_results
```

Expected rounded correlations:

| Variable | Correlation |
| --- | ---: |
| LAID | 0.996 |
| LWAD | 0.992 |
| SWAD | 0.997 |
| GWAD | 0.923 |
| RWAD | 0.996 |
| VWAD | 0.994 |
| G#AD | 0.958 |
| RDPD | 0.999 |

The generated summary from the verified branch was:

```text
Variable  DSSAT_Mean  Python_Mean  Correlation
    LAID       0.594        0.575        0.996
    LWAD     377.318      378.694        0.992
    SWAD     441.353      442.526        0.997
    GWAD       3.282        3.262        0.923
    RWAD     451.412      409.762        0.996
    VWAD     818.765      821.220        0.994
    G#AD     276.165      300.651        0.958
    RDPD       1.063        1.162        0.999
```

Additional verification commands run:

```bash
python -m py_compile cropgro-strawberry-implementation.py load_dssat_weather.py generate_ufba1401_comparison.py
```

```bash
python - <<'PY'
import pandas as pd
summary = pd.read_csv("comparison_results/dssat_python_summary_comparison.csv")
expected = {
    "LAID": 0.996,
    "LWAD": 0.992,
    "SWAD": 0.997,
    "GWAD": 0.923,
    "RWAD": 0.996,
    "VWAD": 0.994,
    "G#AD": 0.958,
    "RDPD": 0.999,
}
for variable, rounded in expected.items():
    actual = float(summary.loc[summary["Variable"] == variable, "Correlation"].iloc[0])
    assert round(actual, 3) == rounded, (variable, actual)
print("correlations match")
PY
```

## Recommendation

Merge `codex/reproduce-ufba1401-comparison`, not `24代码组A翟翔宇`.

This keeps the research result and its reproducibility chain while avoiding unrelated files from the source branch.
