from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
for package_dir in (
    PROJECT_ROOT,
    PROJECT_ROOT / "platform",
    PROJECT_ROOT / "api",
):
    if str(package_dir) not in sys.path:
        sys.path.insert(0, str(package_dir))

from graph_platform.flask_app import app


__all__ = ["app"]
