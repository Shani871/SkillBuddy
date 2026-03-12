"""
Settings package.

Backward-compatible default import so older scripts using
DJANGO_SETTINGS_MODULE="config.settings" still work.
"""

from .local import *  # noqa: F401,F403
