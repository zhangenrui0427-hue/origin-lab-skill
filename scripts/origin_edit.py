#!/usr/bin/env python
"""Edit and export an existing Origin OPJ/OPJU project."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re


def parse_list(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip().lstrip(".").lower() for item in value.split(",") if item.strip()]


def slug(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    return cleaned.strip("._") or "origin_graph"


def set_origin_visible(op, visible: bool) -> None:
    for name in ["set_show", "set_visible"]:
        func = getattr(op, name, None)
        if callable(func):
            try:
                func(visible)
                return
            except Exception:
                pass


def find_graph(op, graph_name: str | None):
    if graph_name:
        try:
            return op.find_graph(graph_name)
        except Exception:
            pass
    for candidate in [0, "Graph1"]:
        try:
            graph = op.find_graph(candidate)
            if graph:
                return graph
        except Exception:
            continue
    raise RuntimeError("No graph page found. Supply --graph with an existing graph name.")


def safe_axis(layer, axis: str, title: str | None, begin: float | None, end: float | None, step: float | None) -> list[str]:
    notes: list[str] = []
    if title:
        try:
            layer.axis(axis).title = title
        except Exception as exc:
            notes.append(f"Failed to set {axis} title: {exc}")
    if begin is not None or end is not None or step is not None:
        try:
            if axis == "x":
                layer.set_xlim(begin=begin, end=end, step=step)
            else:
                layer.set_ylim(begin=begin, end=end, step=step)
        except Exception as exc:
            notes.append(f"Failed to set {axis} limits: {exc}")
    return notes


def apply_style(graph, args) -> list[str]:
    notes: list[str] = []
    try:
        graph.set_int("aa", 1)
    except Exception:
        pass
    for layer_index, layer in enumerate(graph):
        notes.extend(safe_axis(layer, "x", args.x_title, args.x_from, args.x_to, args.x_step))
        notes.extend(safe_axis(layer, "y", args.y_title, args.y_from, args.y_to, args.y_step))
        if args.font_size:
            for label_name in ["Legend", "legend"]:
                try:
                    layer.label(label_name).set_int("fsize", args.font_size)
                except Exception:
                    pass
            try:
                layer.lt_exec(f"layer -ga; tick -l {args.font_size};")
            except Exception as exc:
                notes.append(f"Layer {layer_index + 1}: font-size LabTalk command failed: {exc}")
        if args.line_width:
            try:
                layer.lt_exec(f"set %C -w {args.line_width};")
            except Exception as exc:
                notes.append(f"Layer {layer_index + 1}: line-width LabTalk command failed: {exc}")
        if args.legend_off:
            for label_name in ["Legend", "legend"]:
                try:
                    layer.label(label_name).remove()
                except Exception:
                    pass
        try:
            layer.rescale()
        except Exception:
            pass
    return notes


def export_graph(graph, output_dir: Path, stem: str, formats: list[str], width: int | None) -> list[str]:
    paths: list[str] = []
    for fmt in formats:
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
    parser = argparse.ArgumentParser(description="Edit and export an existing Origin project.")
    parser.add_argument("--project", required=True, help="Input OPJ/OPJU path.")
    parser.add_argument("--graph", help="Graph page name. Defaults to first graph.")
    parser.add_argument("--output-dir", default="origin_outputs")
    parser.add_argument("--project-out", help="Output OPJU path. Defaults to *_edited.opju in output-dir.")
    parser.add_argument("--formats", default="png")
    parser.add_argument("--width", type=int, default=1600)
    parser.add_argument("--font-size", type=int)
    parser.add_argument("--line-width", type=float)
    parser.add_argument("--x-title")
    parser.add_argument("--y-title")
    parser.add_argument("--x-from", type=float)
    parser.add_argument("--x-to", type=float)
    parser.add_argument("--x-step", type=float)
    parser.add_argument("--y-from", type=float)
    parser.add_argument("--y-to", type=float)
    parser.add_argument("--y-step", type=float)
    parser.add_argument("--legend-off", action="store_true")
    parser.add_argument("--hidden", action="store_true")
    parser.add_argument("--keep-open", action="store_true")
    args = parser.parse_args()

    project = Path(args.project).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = slug(args.graph or f"{project.stem}_edited")
    project_out = Path(args.project_out).expanduser().resolve() if args.project_out else output_dir / f"{project.stem}_edited.opju"
    formats = parse_list(args.formats) or ["png"]

    try:
        import originpro as op
    except ImportError as exc:
        raise SystemExit("Missing dependency: install originpro first with check_origin_env.py --install") from exc

    if project_out.resolve() == project.resolve():
        raise SystemExit("Refusing to overwrite the source Origin project. Use a different --project-out.")

    exported: list[str] = []
    notes: list[str] = []
    set_origin_visible(op, not args.hidden)
    try:
        try:
            op.open(str(project))
        except AttributeError:
            op.lt_exec(f'doc -o "{project}";')
        graph = find_graph(op, args.graph)
        notes.extend(apply_style(graph, args))
        exported = export_graph(graph, output_dir, stem, formats, args.width)
        op.save(str(project_out))
    finally:
        if not args.keep_open:
            try:
                op.exit()
            except Exception:
                pass

    manifest = {
        "source_project": str(project),
        "project": str(project_out),
        "graph": args.graph,
        "exports": exported,
        "notes": notes,
    }
    manifest_path = output_dir / f"{stem}.origin-lab-edit.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
