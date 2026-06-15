"""Production settings for container and managed-platform deployments."""

from decouple import Csv, config
from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403,F401

DEBUG = False

SECRET_KEY = config("SECRET_KEY", default="")
if len(SECRET_KEY) < 50:
    raise ImproperlyConfigured(
        "SECRET_KEY must be set to a unique value of at least 50 characters."
    )

ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="", cast=Csv())
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured("ALLOWED_HOSTS must be set in production.")

DATABASE_URL = config("DATABASE_URL", default="")
if not DATABASE_URL:
    raise ImproperlyConfigured("DATABASE_URL is required for production settings.")

try:
    import dj_database_url
except ImportError as exc:
    raise ImproperlyConfigured(
        "Install dj-database-url to use production settings with DATABASE_URL."
    ) from exc

DATABASES = {
    "default": dj_database_url.parse(
        DATABASE_URL,
        conn_max_age=config("DB_CONN_MAX_AGE", default=600, cast=int),
        conn_health_checks=True,
        ssl_require=config("DB_SSL_REQUIRE", default=True, cast=bool),
    )
}

CSRF_TRUSTED_ORIGINS = config("CSRF_TRUSTED_ORIGINS", default="", cast=Csv())
SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=True, cast=bool)
SESSION_COOKIE_SECURE = config("SESSION_COOKIE_SECURE", default=True, cast=bool)
CSRF_COOKIE_SECURE = config("CSRF_COOKIE_SECURE", default=True, cast=bool)
SESSION_COOKIE_HTTPONLY = True
# Existing AJAX forms read the CSRF token from this cookie.
CSRF_COOKIE_HTTPONLY = False
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "DENY"
SECURE_HSTS_SECONDS = config("SECURE_HSTS_SECONDS", default=31536000, cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = config(
    "SECURE_HSTS_INCLUDE_SUBDOMAINS", default=True, cast=bool
)
SECURE_HSTS_PRELOAD = config("SECURE_HSTS_PRELOAD", default=True, cast=bool)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True

# WhiteNoise serves versioned static assets directly from the web process.
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
WHITENOISE_MAX_AGE = 31536000

# User-uploaded media should use object storage in multi-instance deployments.
AWS_STORAGE_BUCKET_NAME = config("AWS_STORAGE_BUCKET_NAME", default="")
if AWS_STORAGE_BUCKET_NAME:
    INSTALLED_APPS += ["storages"]  # noqa: F405
    AWS_ACCESS_KEY_ID = config("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = config("AWS_SECRET_ACCESS_KEY")
    AWS_S3_REGION_NAME = config("AWS_S3_REGION_NAME", default="")
    AWS_S3_ENDPOINT_URL = config("AWS_S3_ENDPOINT_URL", default=None)
    AWS_S3_CUSTOM_DOMAIN = config("AWS_S3_CUSTOM_DOMAIN", default=None)
    AWS_QUERYSTRING_AUTH = config("AWS_QUERYSTRING_AUTH", default=False, cast=bool)
    AWS_DEFAULT_ACL = None
    AWS_S3_FILE_OVERWRITE = False
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3.S3Storage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }
    if AWS_S3_CUSTOM_DOMAIN:
        MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/"

# Suitable only for a single instance with a persistent MEDIA_ROOT volume.
SERVE_MEDIA_FILES = config("SERVE_MEDIA_FILES", default=False, cast=bool)
