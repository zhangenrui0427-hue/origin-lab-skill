#!/usr/bin/env python
"""Check and optionally install dependencies for Origin automation."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

try:
    import winreg
except ImportError:  # pragma: no cover - Windows-only skill
    winreg = None


REQUIRED_IMPORTS = {
    "originpro": "originpro",
    "pandas": "pandas",
    "openpyxl": "openpyxl",
    "win32com": "pywin32",
}

PROGIDS = ["Origin.Application", "Origin.ApplicationSI"]
UNINSTALL_KEYS = [
    r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
    r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
]


def has_import(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def registry_value(root, path: str, value_name: str = ""):
    if winreg is None:
        return None
    try:
        with winreg.OpenKey(root, path) as key:
            return winreg.QueryValueEx(key, value_name)[0]
    except OSError:
        return None


def progid_exists(progid: str) -> bool:
    if winreg is None:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, progid):
            return True
    except OSError:
        return False


def find_origin_installations() -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    if winreg is None:
        return found
    for base in UNINSTALL_KEYS:
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base) as parent:
                for index in range(winreg.QueryInfoKey(parent)[0]):
                    sub_name = winreg.EnumKey(parent, index)
                    with winreg.OpenKey(parent, sub_name) as sub:
                        values = {}
                        for field in ["DisplayName", "DisplayVersion", "Publisher", "InstallLocation"]:
                            try:
                                values[field] = winreg.QueryValueEx(sub, field)[0]
                            except OSError:
                                values[field] = ""
                        haystack = f"{values.get('DisplayName', '')} {values.get('Publisher', '')}".lower()
                        if "origin" in haystack or "originlab" in haystack:
                            found.append(values)
        except OSError:
            continue
    return found


def check_output_dir(path: Path) -> dict[str, object]:
    path.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.NamedTemporaryFile(prefix="origin-lab-", suffix=".tmp", dir=path, delete=False) as handle:
            temp_path = Path(handle.name)
            handle.write(b"ok")
        temp_path.unlink(missing_ok=True)
        return {"path": str(path), "writable": True}
    except OSError as exc:
        return {"path": str(path), "writable": False, "error": str(exc)}


def install_missing(missing_imports: list[str]) -> int:
    packages = [REQUIRED_IMPORTS[name] for name in missing_imports]
    cmd = [sys.executable, "-m", "pip", "install", *packages]
    print("Installing missing packages:", " ".join(packages), file=sys.stderr)
    return subprocess.call(cmd)


def build_report(output_dir: Path) -> dict[str, object]:
    packages = {
        import_name: {
            "import": import_name,
            "pip": pip_name,
            "installed": has_import(import_name),
        }
        for import_name, pip_name in REQUIRED_IMPORTS.items()
    }
    progids = {progid: progid_exists(progid) for progid in PROGIDS}
    output = check_output_dir(output_dir)
    ok = all(item["installed"] for item in packages.values()) and any(progids.values()) and bool(output["writable"])
    return {
        "ok": ok,
        "python": sys.executable,
        "packages": packages,
        "origin_progids": progids,
        "origin_installations": find_origin_installations(),
        "output_dir": output,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Origin automation environment.")
    parser.add_argument("--install", action="store_true", help="Install missing Python packages with pip, then recheck.")
    parser.add_argument("--output-dir", default="origin_outputs", help="Directory to test for writable outputs.")
    parser.add_argument("--json", action="store_true", help="Print compact JSON only.")
    args = parser.parse_args()

    output_dir = Path(args.output_dir).expanduser().resolve()
    report = build_report(output_dir)
    missing = [name for name, item in report["packages"].items() if not item["installed"]]

    if missing and args.install:
        code = install_missing(missing)
        if code != 0:
            report["install_error"] = f"pip exited with {code}"
        report = build_report(output_dir)

    text = json.dumps(report, indent=None if args.json else 2, ensure_ascii=False)
    print(text)
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
