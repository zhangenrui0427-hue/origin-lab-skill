---
name: origin-lab
description: Automate local Origin/OriginPro plotting and graph editing for research figures. Use when Codex needs to create Origin graphs from CSV, TXT, XLSX, or tabular data; edit existing OPJ/OPJU graph projects; apply Origin templates or figure styling; export PNG, TIFF, SVG, PDF, or editable OPJU outputs; or help Enry batch-adjust scientific figures in local Origin 2025.
---

# Origin Lab

## Overview

Use local Origin 2025 through external Python and the official `originpro` package. Prefer visible Origin windows while the workflow is still being tuned so Enry can inspect graphs and catch blocked automation.

Always preserve the raw input data and save an editable Origin project (`.opju`) alongside exported image files unless Enry asks for images only.

## Quick Workflow

1. Run `scripts/check_origin_env.py` before the first Origin task in a session.
2. If required packages are missing, run the same script with `--install` using `C:\Users\Administrator\AppData\Local\Programs\Python\Python313\python.exe`.
3. For new graphs from data, use `scripts/origin_plot.py`.
4. For existing Origin projects, use `scripts/origin_edit.py`.
5. Save outputs in an explicit output folder; if none is provided, use `origin_outputs/` next to the current task.
6. Report exported files, saved OPJU path, any display-only transformations, and any settings that failed to apply.

## Create Graphs From Data

Use `scripts/origin_plot.py` for CSV, TXT, TSV, or XLSX files. It supports line, scatter, line-symbol, column, xrd-stack, and spectrum-stack plots.

Typical command:

```powershell
& 'C:\Users\Administrator\AppData\Local\Programs\Python\Python313\python.exe' scripts\origin_plot.py --input data.csv --x "Voltage" --y "Capacity,Efficiency" --plot-type line-symbol --formats png,svg,pdf --output-dir origin_outputs
```

Defaults:

- First column is X when `--x` is omitted.
- Numeric columns other than X are Y columns when `--y` is omitted.
- PNG export is produced when `--formats` is omitted.
- The Origin window is visible unless `--hidden` is supplied.

For XRD, Raman, FTIR, XPS survey, or other stacked spectra, use `--plot-type xrd-stack` or `--plot-type spectrum-stack`. Treat offsets as display transformations, not raw data changes, and report the offset value.

## Edit Existing Origin Projects

Use `scripts/origin_edit.py` for OPJ/OPJU files. It opens the project, targets a graph by name or the first graph, applies simple styling and axis edits, exports images, and saves a new OPJU.

Typical command:

```powershell
& 'C:\Users\Administrator\AppData\Local\Programs\Python\Python313\python.exe' scripts\origin_edit.py --project figure.opju --graph Graph1 --font-size 22 --line-width 2 --formats png,tif,svg --output-dir origin_outputs
```

Never overwrite the source project by default. Save to `*_edited.opju` unless Enry gives an explicit output path.

## Reliability Rules

- Do not fabricate data, peaks, fits, baselines, uncertainty values, labels, or conclusions.
- Do not smooth, normalize, offset, baseline-correct, fit, delete points, or crop data unless Enry explicitly asks.
- When any display or data transformation is requested, preserve the original input and report the transformation in the final answer.
- Prefer vector exports (`svg` or `pdf`) for manuscripts and high-DPI raster exports (`png` or `tif`) for slides or previews.
- If Origin automation fails, state whether the failure is dependency-related, COM/Origin startup-related, graph API-related, or export-related.

## References

Read `references/origin_workflows.md` when choosing a plot type, export method, or troubleshooting Origin automation.
