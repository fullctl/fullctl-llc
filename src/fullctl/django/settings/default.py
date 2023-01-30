# Django config

ALLOWED_HOSTS = ["*"]
SITE_ID = 1

TIME_ZONE = "UTC"
USE_TZ = True

LANGUAGE_CODE = "en-us"
USE_I18N = True
USE_L10N = True

ADMINS = [
    ("Support", SERVER_EMAIL),
]
MANAGERS = ADMINS

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

settings_manager.set_option("HOST_URL", "https://localhost:8000")

settings_manager.set_option(
    "MEDIA_ROOT", os.path.abspath(os.path.join(BASE_DIR, "media"))
)
settings_manager.set_option("MEDIA_URL", f"/m/{PACKAGE_VERSION}/")

settings_manager.set_option(
    "STATIC_ROOT", os.path.abspath(os.path.join(BASE_DIR, "static"))
)
settings_manager.set_option("STATIC_URL", f"/s/{PACKAGE_VERSION}/")

settings_manager.set_option("SESSION_COOKIE_NAME", f"{SERVICE_TAG}sid")
settings_manager.set_bool("SESSION_COOKIE_SECURE", True)

if RELEASE_ENV == "dev":
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# settings_manager.set_from_env("SESSION_COOKIE_DOMAIN")

settings_manager.set_option("DEFAULT_FROM_EMAIL", SERVER_EMAIL)
settings_manager.set_option("NO_REPLY_EMAIL", SERVER_EMAIL)

settings_manager.set_option("DEFAULT_THEME", "v2")

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "django_cache",
        "OPTIONS": {
            # maximum number of entries in the cache
            "MAX_ENTRIES": 5000,
            # once max entries are reach delete 500 of the oldest entries
            "CULL_FREQUENCY": 10,
        },
    }
}

DATABASES = {
    "default": {
        "ENGINE": f"django.db.backends.{DATABASE_ENGINE}",
        "HOST": DATABASE_HOST,
        "PORT": DATABASE_PORT,
        "NAME": DATABASE_NAME,
        "USER": DATABASE_USER,
        "PASSWORD": DATABASE_PASSWORD,
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

CSRF_FROM_SESSIONS = True

FULLCTL_ADDON_URLS = []
