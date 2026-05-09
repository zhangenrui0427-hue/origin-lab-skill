# Origin Lab Workflows

## Automation Route

- Use external Python with the official `originpro` package as the primary route.
- `originpro` uses Origin Automation Server COM through OriginExt and can launch Origin visible or hidden.
- Local requirement: Windows plus Origin 2021 or later. This machine has Origin2025 SR1 installed at `S:\OriginLab\Origin2025\`.
- COM ProgIDs observed locally: `Origin.Application` and `Origin.ApplicationSI`.

## Dependency Baseline

Use:

```powershell
& 'C:\Users\Administrator\AppData\Local\Programs\Python\Python313\python.exe' scripts\check_origin_env.py --install
```

Required imports:

- `originpro`
- `pandas`
- `openpyxl`
- `win32com`

The pip package for `win32com` is `pywin32`.

## Plot Type Mapping

| User intent | `origin_plot.py --plot-type` | Notes |
|---|---|---|
| Line curve, charge/discharge curve, cycling trend | `line` | Best default for continuous data. |
| Scatter points | `scatter` | Use when markers matter more than connecting lines. |
| Line with symbols | `line-symbol` | Good for electrochemical trends with visible points. |
| Bar or column comparison | `column` | Use for discrete categories or sample comparisons. |
| XRD stack or offset patterns | `xrd-stack` | Offset is display-only and must be reported. |
| Raman/FTIR/XPS stacked spectra | `spectrum-stack` | Offset is display-only and must be reported. |

## Export Policy

- Default: save both image exports and OPJU.
- Use `GPage.save_fig()` first.
- If `save_fig()` cannot apply a requested option, fall back to LabTalk export commands only when needed.
- Prefer SVG/PDF for manuscript vectors, TIFF for journal raster requirements, and PNG for quick preview.

## Scientific Figure Boundaries

- Raw data must remain untouched.
- Offset/normalization/baseline/smoothing/fitting must be explicit in the command and reported.
- Do not infer axis units or sample names when the data file lacks them; use column names or ask Enry.
- Keep a manifest JSON next to outputs so later edits can be traced.
