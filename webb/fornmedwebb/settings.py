"""
Inställningar för webbplatsen fornmed.se (Django och Wagtail).

Allt som skiljer mellan utveckling och drift läses ur miljön eller ur .env i
den här katalogen:

    WEBB_DATABASE_URL      webbplatsens egen databas (Wagtails sidor)
    FORNMED_DATABASE_URL   Fornmeds databas, bara läsning: källförteckningen
                           och uppdateringarna hämtas därifrån
    WEBB_SECRET_KEY        Djangos hemliga nyckel
    WEBB_ALLOWED_HOSTS     kommaseparerade värdnamn (standard: localhost)
    WEBB_DEBUG             på i utveckling (standard: av)
    WEBB_STATIC_ROOT       katalogen som collectstatic skriver till
    WEBB_MEDIA_ROOT        katalogen för uppladdade filer
    WEBB_STATISTIK_URL     Umamis adress, t.ex. https://stat.fornmed.se
    WEBB_STATISTIK_ID      webbplatsens id i Umami
    WEBB_ADMIN_URL         webbplatsens adress för länkar i Wagtails e-post
    WEBB_API_URL           API:ets publika adress, för länkar
    WEBB_API_INTERN_URL    söktjänsten direkt, för källtexterna (standard: 127.0.0.1:8424)
"""

import os
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
PROJEKT = BASE_DIR.parent
load_dotenv(BASE_DIR / ".env")

PA = ("på", "pa", "ja", "1", "true", "on")

DEBUG = os.environ.get("WEBB_DEBUG", "").strip().lower() in PA
SECRET_KEY = os.environ.get("WEBB_SECRET_KEY") or ("utveckling-ej-hemlig" if DEBUG else "")
if not SECRET_KEY:
    raise RuntimeError("WEBB_SECRET_KEY saknas.")
ALLOWED_HOSTS = [h.strip() for h in os.environ.get("WEBB_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
                 if h.strip()]
CSRF_TRUSTED_ORIGINS = [f"https://{h}" for h in ALLOWED_HOSTS if "." in h and not h[0].isdigit()]

INSTALLED_APPS = [
    "sidor",
    "wagtail.contrib.routable_page",
    "wagtail.contrib.redirects",
    "wagtail.sites",
    "wagtail.users",
    "wagtail.snippets",
    "wagtail.documents",
    "wagtail.images",
    "wagtail.search",
    "wagtail.admin",
    "wagtail",
    "modelcluster",
    "taggit",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
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
    "wagtail.contrib.redirects.middleware.RedirectMiddleware",
]

ROOT_URLCONF = "fornmedwebb.urls"
WSGI_APPLICATION = "fornmedwebb.wsgi.application"

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
                "sidor.kontext.webbplats",
            ],
        },
    },
]

DATABASES = {
    "default": dj_database_url.config(env="WEBB_DATABASE_URL", conn_max_age=600),
    # Fornmeds databas läses med söktjänstens skrivskyddade roll; routern
    # nedan ser till att inga modeller hamnar där. Vid ett databasbyte på
    # servern avbryts de öppna anslutningarna, och hälsokontrollen gör att
    # nästa begäran öppnar en ny i stället för att misslyckas på den gamla.
    "fornmed": dj_database_url.config(env="FORNMED_DATABASE_URL", conn_max_age=600,
                                      conn_health_checks=True),
}
DATABASE_ROUTERS = ["sidor.kallor.FornmedRouter"]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "sv"
TIME_ZONE = "Europe/Stockholm"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = os.environ.get("WEBB_STATIC_ROOT", str(BASE_DIR / "staticfiles"))
STATICFILES_DIRS = [("grafisk_profil", PROJEKT / "grafisk_profil")]
MEDIA_URL = "/media/"
MEDIA_ROOT = os.environ.get("WEBB_MEDIA_ROOT", str(BASE_DIR / "media"))
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
                    if not DEBUG else "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Bakom nginx: https och klientens adress kommer i huvudena
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

WAGTAIL_SITE_NAME = "Fornmed"
WAGTAILADMIN_BASE_URL = os.environ.get("WEBB_ADMIN_URL", "http://localhost:8425")
WAGTAILSEARCH_BACKENDS = {"default": {"BACKEND": "wagtail.search.backends.database"}}
WAGTAIL_I18N_ENABLED = False

WEBB_STATISTIK_URL = os.environ.get("WEBB_STATISTIK_URL", "")
WEBB_STATISTIK_ID = os.environ.get("WEBB_STATISTIK_ID", "")
API_URL = os.environ.get("WEBB_API_URL", "https://api.fornmed.se")
# Söktjänstens API direkt, utan nginx, för källtexterna på webbplatsen
API_INTERN_URL = os.environ.get("WEBB_API_INTERN_URL", "http://127.0.0.1:8424")
MCP_URL = os.environ.get("WEBB_MCP_URL", "https://mcp.fornmed.se")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "WARNING"},
}
