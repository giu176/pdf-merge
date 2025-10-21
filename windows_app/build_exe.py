"""Build the Windows executable using PyInstaller."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def build() -> None:
    """Invoke PyInstaller with the options required for a single-file build."""

    project_dir = Path(__file__).resolve().parent
    dist_dir = project_dir / "dist"
    build_dir = project_dir / "build"

    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    if build_dir.exists():
        shutil.rmtree(build_dir)

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        "--name",
        "pdf-merge",
        "--collect-all",
        "fitz",
        str(project_dir / "windows_main.py"),
    ]

    subprocess.run(cmd, check=True)

    exe_path = dist_dir / "pdf-merge.exe"
    print(f"Executable created at: {exe_path}")


if __name__ == "__main__":
    build()
