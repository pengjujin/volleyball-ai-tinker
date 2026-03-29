from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent.parent
CHECK_SUFFIXES = {
    ".css",
    ".html",
    ".json",
    ".md",
    ".py",
    ".ts",
    ".tsx",
}
SKIP_DIRS = {
    ".git",
    "__pycache__",
    "node_modules",
    "dist",
    ".vite",
    "reports",
}


def iter_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix in CHECK_SUFFIXES:
            files.append(path)
    return sorted(files)


def main() -> int:
    errors: list[str] = []

    for path in iter_files():
        for index, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if raw_line.rstrip() != raw_line:
                errors.append(f"{path.relative_to(ROOT)}:{index}: trailing whitespace")
            if "\t" in raw_line:
                errors.append(f"{path.relative_to(ROOT)}:{index}: tab character")

    if errors:
        for error in errors:
            print(error)
        return 1

    print("style checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
