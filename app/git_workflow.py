from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path


PACKAGE_FILES = (
    Path("models/compatibility_view.sql"),
    Path("tests/change_regression.sql"),
    Path("MIGRATION.md"),
    Path("impact.json"),
)


def _git(repository: Path, *arguments: str) -> str:
    process = subprocess.run(
        ["git", *arguments], cwd=repository, check=False, capture_output=True, text=True, timeout=30
    )
    if process.returncode:
        detail = process.stderr.strip() or process.stdout.strip()
        raise RuntimeError(detail or f"git {' '.join(arguments)} failed")
    return process.stdout.strip()


def commit_change_package(package_dir: Path, repository: Path) -> dict:
    package_dir = package_dir.resolve()
    repository = repository.resolve()
    if not (repository / ".git").exists():
        raise ValueError(f"Target is not a Git repository: {repository}")
    missing = [str(path) for path in PACKAGE_FILES if not (package_dir / path).is_file()]
    if missing:
        raise ValueError(f"Incomplete ChangeSafe package; missing: {', '.join(missing)}")
    if _git(repository, "status", "--porcelain"):
        raise ValueError("Target repository must be clean before applying a ChangeSafe package")

    package_id = re.sub(r"[^a-z0-9-]+", "-", package_dir.name.lower()).strip("-")
    branch = f"changesafe/{package_id}"
    destinations = {
        Path("models/compatibility_view.sql"): Path("models/changesafe") / f"{package_id}.sql",
        Path("tests/change_regression.sql"): Path("tests/changesafe") / f"{package_id}.sql",
        Path("MIGRATION.md"): Path(".changesafe") / package_id / "MIGRATION.md",
        Path("impact.json"): Path(".changesafe") / package_id / "impact.json",
    }
    collisions = [str(path) for path in destinations.values() if (repository / path).exists()]
    if collisions:
        raise ValueError(f"Refusing to overwrite existing files: {', '.join(collisions)}")

    _git(repository, "switch", "-c", branch)
    for source, destination in destinations.items():
        target = repository / destination
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(package_dir / source, target)
    relative_paths = [str(path).replace("\\", "/") for path in destinations.values()]
    _git(repository, "add", "--", *relative_paths)
    _git(repository, "commit", "-m", f"Apply ChangeSafe migration {package_id}")
    return {
        "branch": branch,
        "commit": _git(repository, "rev-parse", "HEAD"),
        "files": relative_paths,
        "next_step": f"git push -u origin {branch}",
    }
