"""Settings por variables de entorno (12-factor): mismo código en local, staging y AWS."""
import os
from pathlib import Path
from dotenv import load_dotenv
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-insegura-cambiar")
DEBUG = os.environ.get("DJANGO_DEBUG", "True") == "True"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# HIPAA R-07: ruta del panel admin configurable. En producción usar un valor
# no adivinable, ej: DJANGO_ADMIN_PATH="gestion-interna-9f3k/".
ADMIN_PATH = os.environ.get("DJANGO_ADMIN_PATH", "admin/").strip("/") + "/"

# HIPAA R-05: en producción está prohibido arrancar con la clave placeholder.
if not DEBUG and SECRET_KEY in ("dev-insegura-cambiar", "cambiar-en-produccion",
                                "cambiar-esta-clave-en-produccion"):
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY debe definirse con un valor único y secreto en producción.")

# CSRF: cada clínica se accede por subdominio (clinica-demo.localhost:8000) y el
# navegador envía ese Origin en el POST del login. Django lo rechaza si no está
# en la lista de orígenes confiables (403 "CSRF token from POST incorrect").
CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in os.environ.get(
        "DJANGO_CSRF_TRUSTED_ORIGINS",
        "http://localhost:8000,http://*.localhost:8000,http://127.0.0.1:8000",
    ).split(",") if o.strip()
]

# --- Multi-tenancy: un schema de PostgreSQL por clínica ---
SHARED_APPS = [
    "django_tenants",
    "core",  # aquí viven Clinic y Domain
    "django.contrib.contenttypes",
]
TENANT_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.admin",
    "simple_history",
    "accounts",
    "patients",
    "clinical",
    "billing",
    "documents",
    "scheduling",
    "portal",
]
INSTALLED_APPS = list(SHARED_APPS) + [a for a in TENANT_APPS if a not in SHARED_APPS]

TENANT_MODEL = "core.Clinic"
TENANT_DOMAIN_MODEL = "core.Domain"
DATABASE_ROUTERS = ("django_tenants.routers.TenantSyncRouter",)

MIDDLEWARE = [
    "django_tenants.middleware.main.TenantMainMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "accounts.middleware.MFAEnforcementMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
]

ROOT_URLCONF = "config.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "accounts.roles.user_role_ctx",
            ],
        },
    },
]

# --- Base de datos por URL (local: pgserver / Docker, prod: RDS) ---
# Soporta tanto TCP (postgresql://user:pass@host:5432/db)
# como socket Unix (postgresql://user@/db?host=/ruta/socket)
from urllib.parse import parse_qs

db_url = urlparse(os.environ.get("DATABASE_URL", ""))
db_qs = parse_qs(db_url.query)
DATABASES = {
    "default": {
        "ENGINE": "django_tenants.postgresql_backend",
        "NAME": db_url.path.lstrip("/"),
        "USER": db_url.username or "",
        "PASSWORD": db_url.password or "",
        "HOST": db_qs.get("host", [db_url.hostname or ""])[0],
        "PORT": db_qs.get("port", [str(db_url.port or "")])[0],
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# HIPAA 164.312(a)(2)(iii): logoff automático por inactividad (30 min).
SESSION_COOKIE_AGE = 1800
LOGIN_REDIRECT_URL = "/inicio/"
LOGIN_URL = "/accounts/login/"
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
# Las cookies de sesión solo viajan por HTTPS cuando hay TLS configurado.
SESSION_COOKIE_HTTPONLY = True

LANGUAGE_CODE = "es"
TIME_ZONE = "America/New_York"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# En producción (DEBUG=False) exigir HTTPS y cookies seguras
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
