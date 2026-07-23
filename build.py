"""Build and package the Mesh2Sheet Blender add-on into a distributable ZIP file."""

from __future__ import annotations

import shutil
import sys
import zipfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
DIST_DIR = PROJECT_ROOT / "dist"
OUTPUT_ZIP = DIST_DIR / "Mesh2Sheet.zip"
PACKAGE_NAME = "mesh2sheet"
EXCLUDED_DIR_NAMES = {
    ".git",
    ".github",
    ".vscode",
    ".idea",
    "__pycache__",
    ".pytest_cache",
    "dist",
    "tests",
    "docs",
}
EXCLUDED_FILE_SUFFIXES = {
    ".pyc",
    ".blend1",
    ".blend2",
    ".db",
}
EXCLUDED_FILES = {"Thumbs.db", ".DS_Store"}


def clean_previous_build() -> None:
    """Remove an older output archive before creating a new build."""
    print("Cleaning previous build...")
    if OUTPUT_ZIP.exists():
        OUTPUT_ZIP.unlink()


def create_dist_folder() -> None:
    """Create the dist directory if it does not already exist."""
    print("Creating dist folder...")
    DIST_DIR.mkdir(exist_ok=True)


def should_include(path: Path) -> bool:
    """Return True when a path should be included in the package archive."""
    if path.name in EXCLUDED_FILES:
        return False

    if path.is_dir():
        return path.name not in EXCLUDED_DIR_NAMES

    if path.suffix.lower() in EXCLUDED_FILE_SUFFIXES:
        return False

    return True


def collect_files() -> list[Path]:
    """Collect add-on source files to include in the build archive."""
    included_files: list[Path] = []
    for path in sorted(PROJECT_ROOT.glob("*.py")):
        if path.name == "build.py":
            continue
        if should_include(path):
            included_files.append(path)
    return included_files


def package_addon() -> None:
    """Create the Blender-installable ZIP archive for the add-on."""
    print("Packaging add-on...")
    try:
        with zipfile.ZipFile(OUTPUT_ZIP, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for file_path in collect_files():
                archive.write(file_path, arcname=f"{PACKAGE_NAME}/{file_path.name}")
    except Exception as exc:
        if OUTPUT_ZIP.exists():
            OUTPUT_ZIP.unlink()
        raise RuntimeError(f"Packaging failed: {exc}") from exc


def print_summary() -> None:
    """Print the resulting build summary and archive size."""
    if not OUTPUT_ZIP.exists():
        raise FileNotFoundError("Build output was not created")

    size_bytes = OUTPUT_ZIP.stat().st_size
    print("Build completed successfully.")
    print(f"Output: {OUTPUT_ZIP}")
    print(f"ZIP size: {size_bytes} bytes")


def main() -> int:
    """Run the build process and return a process exit code."""
    try:
        clean_previous_build()
        create_dist_folder()
        package_addon()
        print_summary()
    except Exception as exc:
        print(f"Error: {exc}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
