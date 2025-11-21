"""Build the Windows executable using PyInstaller."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def build() -> None:
    """Invoke PyInstaller with the options required for a single-file build."""

    project_dir = Path(__file__).resolve().parent
    repo_root = project_dir.parent
    dist_dir = repo_root / "dist"
    build_dir = repo_root / "build"

    for path in (dist_dir, build_dir):
        if path.exists():
            try:
                shutil.rmtree(path)
            except PermissionError as exc:  # pragma: no cover - Windows specific
                raise RuntimeError(
                    f"Unable to remove {path}. Close any running instances of pdf-merge.exe and retry."
                ) from exc

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
        "--distpath",
        str(dist_dir),
        "--workpath",
        str(build_dir),
        "--specpath",
        str(repo_root),
        "--collect-all",
        "fitz",
        str(project_dir / "windows_main.py"),
    ]

    subprocess.run(cmd, check=True)

    exe_path = dist_dir / "pdf-merge.exe"
    print(f"Executable created at: {exe_path}")


if __name__ == "__main__":
    build()
