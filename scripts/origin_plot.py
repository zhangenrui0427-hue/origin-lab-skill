#!/usr/bin/env python
"""Create Origin graphs from local tabular data."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Iterable

import pandas as pd


PLOT_TYPES = {
    "line": {"template": "line", "origin_type": "line"},
    "scatter": {"template": "scatter", "origin_type": "s"},
    "line-symbol": {"template": "line", "origin_type": "line"},
    "column": {"template": "column", "origin_type": "column"},
    "xrd-stack": {"template": "line", "origin_type": "line"},
    "spectrum-stack": {"template": "line", "origin_type": "line"},
}


def parse_list(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def slug(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    return cleaned.strip("._") or "origin_graph"


def read_table(path: Path, sheet: str | int | None = None) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix in [".xlsx", ".xlsm", ".xls"]:
        return pd.read_excel(path, sheet_name=sheet or 0)
    if suffix == ".tsv":
        return pd.read_csv(path, sep="\t")
    return pd.read_csv(path, sep=None, engine="python")


def column_index(df: pd.DataFrame, selector: str | None, default: int = 0) -> int:
    if selector is None:
        return default
    if selector in df.columns:
        return int(df.columns.get_loc(selector))
    try:
        idx = int(selector)
    except ValueError as exc:
        raise ValueError(f"Column not found: {selector}") from exc
    if idx < 0 or idx >= len(df.columns):
        raise ValueError(f"Column index out of range: {selector}")
    return idx


def y_indices(df: pd.DataFrame, selectors: Iterable[str], x_idx: int) -> list[int]:
    selected = list(selectors)
    if selected:
        return [column_index(df, item) for item in selected]
    numeric = []
    for idx, col in enumerate(df.columns):
        if idx == x_idx:
            continue
        if pd.api.types.is_numeric_dtype(df[col]):
            numeric.append(idx)
    if not numeric:
        raise ValueError("No numeric Y columns found. Supply --y with column names or indices.")
    return numeric


def apply_display_offset(df: pd.DataFrame, y_cols: list[int], offset: float) -> tuple[pd.DataFrame, list[int], list[str]]:
    out = df.copy()
    new_indices: list[int] = []
    notes: list[str] = []
    for order, idx in enumerate(y_cols):
        source = df.columns[idx]
        new_name = f"{source}__display_offset_{order}"
        out[new_name] = pd.to_numeric(df.iloc[:, idx], errors="coerce") + order * offset
        new_indices.append(int(out.columns.get_loc(new_name)))
        notes.append(f"{new_name} = {source} + {order} * {offset}")
    return out, new_indices, notes


def set_origin_visible(op, visible: bool) -> None:
    for name in ["set_show", "set_visible"]:
        func = getattr(op, name, None)
        if callable(func):
            try:
                func(visible)
                return
            except Exception:
                pass


def fill_worksheet(wks, df: pd.DataFrame) -> None:
    for idx, col in enumerate(df.columns):
        values = df.iloc[:, idx].tolist()
        try:
            wks.from_list(idx, values, lname=str(col))
        except TypeError:
            wks.from_list(idx, values)
            try:
                wks.set_label(idx, str(col))
            except Exception:
                pass


def safe_set_axis_title(layer, axis: str, title: str | None) -> None:
    if not title:
        return
    try:
        layer.axis(axis).title = title
    except Exception:
        try:
            layer.lt_exec(f"{axis}t.text$={title}")
        except Exception:
            pass


def export_graph(graph, output_dir: Path, stem: str, formats: list[str], width: int | None) -> list[str]:
    paths: list[str] = []
    for fmt in formats:
        fmt = fmt.lower().lstrip(".")
        out = output_dir / f"{stem}.{fmt}"
        kwargs = {}
        if width:
            kwargs["width"] = width
        try:
            graph.save_fig(str(out), **kwargs)
        except TypeError:
            graph.save_fig(str(out))
        paths.append(str(out))
    return paths


def main() -> int:
    parser = argparse.ArgumentParser(description="Create an Origin graph from tabular data.")
    parser.add_argument("--input", required=True, help="CSV, TSV, TXT, XLS, or XLSX data file.")
    parser.add_argument("--sheet", help="Excel sheet name or index.")
    parser.add_argument("--x", help="X column name or zero-based index. Defaults to first column.")
    parser.add_argument("--y", help="Comma-separated Y column names or zero-based indices.")
    parser.add_argument("--plot-type", choices=sorted(PLOT_TYPES), default="line")
    parser.add_argument("--template", help="Origin graph template name. Overrides plot-type default.")
    parser.add_argument("--graph-name", default="origin_graph", help="Output stem and graph long name.")
    parser.add_argument("--x-title")
    parser.add_argument("--y-title")
    parser.add_argument("--formats", default="png", help="Comma-separated export formats, e.g. png,svg,pdf,tif.")
    parser.add_argument("--output-dir", default="origin_outputs")
    parser.add_argument("--project-out", help="Output OPJU path. Defaults to output-dir/graph-name.opju.")
    parser.add_argument("--width", type=int, default=1600, help="Export width in pixels where supported.")
    parser.add_argument("--offset", type=float, default=0.0, help="Display offset for stacked spectra.")
    parser.add_argument("--hidden", action="store_true", help="Try to run Origin hidden.")
    parser.add_argument("--keep-open", action="store_true", help="Leave Origin open after completion.")
    args = parser.parse_args()

    input_path = Path(args.input).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = slug(args.graph_name or input_path.stem)
    project_out = Path(args.project_out).expanduser().resolve() if args.project_out else output_dir / f"{stem}.opju"
    formats = parse_list(args.formats) or ["png"]

    try:
        import originpro as op
    except ImportError as exc:
        raise SystemExit("Missing dependency: install originpro first with check_origin_env.py --install") from exc

    df = read_table(input_path, args.sheet)
    if df.empty:
        raise SystemExit(f"No data found in {input_path}")

    x_idx = column_index(df, args.x, 0)
    y_cols = y_indices(df, parse_list(args.y), x_idx)
    transform_notes: list[str] = []
    plot_df = df
    plot_y_cols = y_cols
    if args.plot_type in {"xrd-stack", "spectrum-stack"} and args.offset:
        plot_df, plot_y_cols, transform_notes = apply_display_offset(df, y_cols, args.offset)

    set_origin_visible(op, not args.hidden)
    graph = None
    exported: list[str] = []
    try:
        try:
            wks = op.new_sheet(type="w", lname="Data")
        except TypeError:
            wks = op.new_sheet("w")
        fill_worksheet(wks, plot_df)

        meta = PLOT_TYPES[args.plot_type]
        template = args.template or meta["template"]
        graph = op.new_graph(template=template)
        layer = graph[0]
        for idx in plot_y_cols:
            try:
                layer.add_plot(wks, coly=idx, colx=x_idx, type=meta["origin_type"])
            except Exception:
                layer.add_plot(wks, coly=idx, colx=x_idx)
        try:
            if len(plot_y_cols) > 1:
                layer.group()
        except Exception:
            pass
        safe_set_axis_title(layer, "x", args.x_title or str(plot_df.columns[x_idx]))
        safe_set_axis_title(layer, "y", args.y_title)
        try:
            layer.rescale()
        except Exception:
            pass

        exported = export_graph(graph, output_dir, stem, formats, args.width)
        try:
            op.save(str(project_out))
        except Exception as exc:
            raise RuntimeError(f"Failed to save Origin project to {project_out}: {exc}") from exc
    finally:
        if not args.keep_open:
            try:
                op.exit()
            except Exception:
                pass

    manifest = {
        "input": str(input_path),
        "project": str(project_out),
        "exports": exported,
        "plot_type": args.plot_type,
        "x_column": str(plot_df.columns[x_idx]),
        "y_columns": [str(plot_df.columns[idx]) for idx in plot_y_cols],
        "source_y_columns": [str(df.columns[idx]) for idx in y_cols],
        "transform_notes": transform_notes,
    }
    manifest_path = output_dir / f"{stem}.origin-lab.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
