#!/usr/bin/env python
import os
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


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
