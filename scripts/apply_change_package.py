from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.git_workflow import commit_change_package


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply a reviewed ChangeSafe package to a clean Git repository.")
    parser.add_argument("package", type=Path, help="Generated ChangeSafe package directory")
    parser.add_argument("repository", type=Path, help="Target Git repository")
    args = parser.parse_args()
    print(json.dumps(commit_change_package(args.package, args.repository), indent=2))


if __name__ == "__main__":
    main()
