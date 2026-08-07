from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path

from .writeback import render_markdown


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9-]+", "-", value.lower()).strip("-")


def write_change_package(analysis: dict, root: Path) -> dict:
    change = analysis["change"]
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    package_id = _slug(f"{change['asset_id']}-{change['kind']}-{change['column']}-{stamp}")
    package_dir = root.resolve() / package_id
    package_dir.mkdir(parents=True, exist_ok=False)
    files = {
        "models/compatibility_view.sql": analysis["generated"]["compatibility_sql"] + "\n",
        "tests/change_regression.sql": analysis["generated"]["regression_tests"] + "\n",
        "MIGRATION.md": render_markdown(analysis) + "\n",
        "impact.json": json.dumps(analysis, indent=2) + "\n",
    }
    for relative, content in files.items():
        destination = package_dir / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")
    return {
        "package_id": package_id,
        "directory": str(package_dir),
        "files": sorted(files),
        "review_status": "human_review_required",
    }
