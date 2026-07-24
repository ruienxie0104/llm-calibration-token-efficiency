#!/usr/bin/env python3
"""Check whether the local runtime has the dependencies needed by this project."""

from __future__ import annotations

from importlib import metadata, util
import os
import shutil
import sys


REQUIRED_MODULES = {
    "datasets": ("datasets", "datasets"),
    "matplotlib": ("matplotlib", "matplotlib"),
    "numpy": ("numpy", "numpy"),
    "pandas": ("pandas", "pandas"),
    "pm4py": ("pm4py", "pm4py"),
    "python-pptx": ("pptx", "python-pptx"),
    "scipy": ("scipy", "scipy"),
    "seaborn": ("seaborn", "seaborn"),
}


def main() -> int:
    problems: list[str] = []

    if not (3, 12) <= sys.version_info[:2] < (3, 14):
        problems.append(
            f"Python {sys.version_info.major}.{sys.version_info.minor} is unsupported; "
            "use Python 3.12 or 3.13."
        )

    print(f"Python: {sys.version.split()[0]}")
    for package, (module_name, distribution_name) in REQUIRED_MODULES.items():
        if util.find_spec(module_name) is None:
            problems.append(f"Missing Python package: {package}")
            continue
        try:
            version = metadata.version(distribution_name)
        except metadata.PackageNotFoundError:
            version = "installed"
        print(f"{package}: {version}")

    if shutil.which("dot") is None:
        problems.append("Missing Graphviz executable: dot")
    else:
        print(f"Graphviz: {shutil.which('dot')}")

    if os.getenv("OLLAMA_API_KEY"):
        print("OLLAMA_API_KEY: configured")
    else:
        print("OLLAMA_API_KEY: not configured (required only for API experiments)")

    if problems:
        print("\nEnvironment is not ready:")
        for problem in problems:
            print(f"- {problem}")
        return 1

    print("\nEnvironment is ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
