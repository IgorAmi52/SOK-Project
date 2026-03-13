"""
WSGI config for config project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os
import sys
from pathlib import Path

from django.core.wsgi import get_wsgi_application


PROJECT_ROOT = Path(__file__).resolve().parents[2]
for package_dir in (
    PROJECT_ROOT,
    PROJECT_ROOT / "platform",
    PROJECT_ROOT / "api",
):
    if str(package_dir) not in sys.path:
        sys.path.insert(0, str(package_dir))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_wsgi_application()
