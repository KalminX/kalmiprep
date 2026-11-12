import os
import sys
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "django-insecure-kalmiprep-premium-edtech-platform-by-kalmitech-2026-xyz",
)

DEBUG = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")
PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY", "").strip()
PAYSTACK_TEST_MODE = os.getenv("PAYSTACK_TEST_MODE", "True" if DEBUG else "False").lower() in ("true", "1", "yes")
PAID_TEST_PIN_SECRET = os.getenv("PAID_TEST_PIN_SECRET", SECRET_KEY).strip() or SECRET_KEY
SITE_URL = os.getenv("SITE_URL", "").strip().rstrip("/")

ALLOWED_HOSTS = ["*"]

CSRF_TRUSTED_ORIGINS = [
    "https://*.kalmitech.app",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://0.0.0.0:8000",
    "http://localhost",
    "http://127.0.0.1",
    "http://0.0.0.0",
    "http://*.localhost:8000",
    "http://*.localhost",
    "https://*.ngrok-free.app",
    "https://*.ngrok.io",
    "https://*.loca.lt",
]

# Add any custom origins provided in environment variables
_extra_csrf = os.getenv("CSRF_TRUSTED_ORIGINS", "").strip()
if _extra_csrf:
    for _origin in _extra_csrf.split(","):
        _origin = _origin.strip()
        if _origin and _origin not in CSRF_TRUSTED_ORIGINS:
            CSRF_TRUSTED_ORIGINS.append(_origin)

# Application definition
INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "django_filters",
    "channels",
    # Local KalmiPrep apps
    "core.apps.CoreConfig",
    "curriculum.apps.CurriculumConfig",
    "questions.apps.QuestionsConfig",
    "practice.apps.PracticeConfig",
    "progress.apps.ProgressConfig",
    "accounts.apps.AccountsConfig",
    "monetization.apps.MonetizationConfig",
    "classrooms.apps.ClassroomsConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.kalmiprep_global_context",
            ],
            "builtins": [
                "core.templatetags.kalmi_tags",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Database
# Default to SQLite for local development, support PostgreSQL via env
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres"):
    import urllib.parse as urlparse
    url = urlparse.urlparse(DATABASE_URL)
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": url.path[1:],
            "USER": url.username,
            "PASSWORD": url.password,
            "HOST": url.hostname,
            "PORT": url.port or 5432,
            "CONN_MAX_AGE": 600,  # 10 minutes persistent connection pooling
            "CONN_HEALTH_CHECKS": True,  # Health check persistent sockets
            "OPTIONS": {
                "connect_timeout": 5,
                "application_name": "kalmiprep_app",
            },
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

if "test" in sys.argv or os.getenv("TESTING", "").lower() in ("true", "1"):
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Lagos"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = "static/"
STATICFILES_DIRS = [
    BASE_DIR / "static",
]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ==============================================================================
# Cloudflare R2 Object Storage (Production & CDN)
# ==============================================================================
USE_S3_STORAGE = os.getenv("USE_S3_STORAGE", "True").lower() in ("true", "1", "yes")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME", "edusphere").strip()
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID", "").strip()
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY", "").strip()
R2_ENDPOINT_URL = os.getenv("R2_ENDPOINT_URL", "").strip()
R2_CUSTOM_DOMAIN = os.getenv("R2_CUSTOM_DOMAIN", "").strip()

if USE_S3_STORAGE and R2_BUCKET_NAME and R2_ACCESS_KEY_ID and R2_SECRET_ACCESS_KEY:
    if "storages" not in INSTALLED_APPS:
        INSTALLED_APPS.append("storages")

    AWS_STORAGE_BUCKET_NAME = R2_BUCKET_NAME
    AWS_ACCESS_KEY_ID = R2_ACCESS_KEY_ID
    AWS_SECRET_ACCESS_KEY = R2_SECRET_ACCESS_KEY
    AWS_S3_ENDPOINT_URL = R2_ENDPOINT_URL
    AWS_S3_REGION_NAME = "auto"
    AWS_S3_SIGNATURE_VERSION = "s3v4"
    AWS_S3_FILE_OVERWRITE = False
    AWS_DEFAULT_ACL = None
    AWS_LOCATION = "kalmiprep"

    AWS_QUERYSTRING_AUTH = True
    AWS_QUERYSTRING_EXPIRE = 86400  # 24 hours valid signed URLs

    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3.S3Storage",
            "OPTIONS": {
                "access_key": AWS_ACCESS_KEY_ID,
                "secret_key": AWS_SECRET_ACCESS_KEY,
                "bucket_name": AWS_STORAGE_BUCKET_NAME,
                "endpoint_url": AWS_S3_ENDPOINT_URL,
                "region_name": AWS_S3_REGION_NAME,
                "signature_version": AWS_S3_SIGNATURE_VERSION,
                "file_overwrite": AWS_S3_FILE_OVERWRITE,
                "location": AWS_LOCATION,
                "querystring_auth": AWS_QUERYSTRING_AUTH,
                "querystring_expire": AWS_QUERYSTRING_EXPIRE,
                "custom_domain": R2_CUSTOM_DOMAIN if R2_CUSTOM_DOMAIN else None,
            },
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
        },
    }


DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Email is printed to the console in development and sent through deployment
# configured SMTP in production. Credentials only come from environment values.
EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend" if DEBUG else "django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = os.getenv("EMAIL_HOST", "")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True").lower() in ("true", "1", "yes")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "KalmiPrep <noreply@kalmiprep.com>")
TEACHER_TUTORIAL_URL = os.getenv("TEACHER_TUTORIAL_URL", "").strip()

# WhiteNoise storage for efficient static file serving
STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"

# Caching Engine (Redis with LocMem fallback)
REDIS_URL = os.getenv("REDIS_URL")
if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
            "KEY_PREFIX": "kalmiprep:v1",
            "TIMEOUT": 1800,  # 30 minutes default
        }
    }

    # Fast cached database sessions: Redis for read speed, Postgres for persistent write-through
    SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "kalmiprep-locmem",
            "TIMEOUT": 1800,
        }
    }

if REDIS_URL:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {"hosts": [REDIS_URL], "prefix": "kalmiprep:channels"},
        }
    }
else:
    CHANNEL_LAYERS = {
        "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}
    }

# Celery & RabbitMQ Distributed Ingestion Engine
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "amqp://kalmin:iamasaint@global-rabbitmq:5672//")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://kalmiprep-redis:6379/2")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_DEFAULT_QUEUE = "default"

# ==============================================================================
# Structured Logging & Error Diagnostics
# ==============================================================================
LOGS_DIR = BASE_DIR / "logs"
os.makedirs(LOGS_DIR, exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "simple": {
            "format": "%(levelname)s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "app_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOGS_DIR / "kalmiprep_app.log",
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "verbose",
            "encoding": "utf-8",
        },
        "payment_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOGS_DIR / "payment_errors.log",
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "verbose",
            "encoding": "utf-8",
        },
        "exam_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOGS_DIR / "exam_errors.log",
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "verbose",
            "encoding": "utf-8",
        },
    },
    "loggers": {
        "django.request": {
            "handlers": ["console", "app_file"],
            "level": "ERROR",
            "propagate": False,
        },
        "monetization": {
            "handlers": ["console", "payment_file"],
            "level": "INFO",
            "propagate": False,
        },
        "practice": {
            "handlers": ["console", "exam_file"],
            "level": "INFO",
            "propagate": False,
        },
        "core.telemetry": {
            "handlers": ["console", "app_file"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
