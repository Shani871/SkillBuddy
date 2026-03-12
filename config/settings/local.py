"""Local development settings."""

from decouple import Csv, config

from .base import *  # noqa: F403,F401

DEBUG = config("DEBUG", default=True, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="127.0.0.1,localhost", cast=Csv())
EMAIL_BACKEND = config(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)

# Use local static storage to avoid manifest requirements in development.
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"

# Optional debug toolbar support for local development.
if config("ENABLE_DEBUG_TOOLBAR", default=False, cast=bool):
    try:
        import debug_toolbar  # noqa: F401

        INSTALLED_APPS += ["debug_toolbar"]  # noqa: F405
        MIDDLEWARE.insert(1, "debug_toolbar.middleware.DebugToolbarMiddleware")  # noqa: F405
        INTERNAL_IPS = config("INTERNAL_IPS", default="127.0.0.1", cast=Csv())
    except ImportError:
        pass
