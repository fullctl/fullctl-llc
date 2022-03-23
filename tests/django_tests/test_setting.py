import os
import sys

import fullctl.django.settings as settings


def test_print_debug():
    settings.print_debug("Test", "test123")


def test_get_locale_name():
    code = settings.get_locale_name("en")
    assert code == "English"

    code = settings.get_locale_name("cs-CZ.UTF-8")
    assert code == "Czech"

    code = settings.get_locale_name("not-a-code")
    assert code == "not-a-code"


def test_read_file():
    text = settings.read_file("./tests/django_tests/test-file.md")
    assert text == "Hello world!"


def test_SettingsManager_get():
    g = {"TEST_SETTING": "world"}
    settings_manager = settings.SettingsManager(g)
    setting = settings_manager.get("TEST_SETTING")

    assert setting == "world"


def test_SettingsManager_set():
    g = {}
    settings_manager = settings.SettingsManager(g)
    setting = settings_manager.set_option("TEST_SETTING", "world")

    assert setting == "world"


def test_SettingsManager_try_include():
    global settings_manager
    settings_manager = settings.SettingsManager(globals())
    settings_manager.try_include("./tests/django_tests/testdevnonexistent.py")

    settings_manager.try_include("./tests/django_tests/testdev.py")

    assert TEST_EXTERNAL_SETTING == "a whole new world"


def test_SettingsManager_try_include_env():
    global settings_manager
    settings_manager = settings.SettingsManager(globals())
    settings_manager.set_option("RELEASE_ENV", "testdev")
    settings_manager.try_include_env()  # TODO add assertion


def test_SettingsManager_set_relase_env():
    g = {}
    settings_manager = settings.SettingsManager(g)
    settings_manager.set_release_env()

    assert g["DEBUG"] is True
    assert g["EXPOSE_ADMIN"] is True

    g = {"RELEASE_ENV": "prod"}
    settings_manager = settings.SettingsManager(g)
    settings_manager.set_release_env()

    assert g["DEBUG"] is False
    assert g["EXPOSE_ADMIN"] is False


def test_SettingsManager_set_default_v1():
    global settings_manager
    settings_manager = settings.SettingsManager(globals())
    settings_manager.set_option("SERVICE_TAG", "testctl")
    os.environ["SERVER_EMAIL"] = "mail@testctl.com"
    settings_manager.set_option("BASE_DIR", "testctl")
    settings_manager.set_option("PACKAGE_VERSION", "1")
    settings_manager.set_default_v1()

    installed_apps = [
        "django.contrib.admin",
        "django.contrib.auth",
        "django.contrib.contenttypes",
        "django.contrib.sessions",
        "django.contrib.messages",
        "django.contrib.staticfiles",
    ]
    middleware = [
        "django.middleware.security.SecurityMiddleware",
        "whitenoise.middleware.WhiteNoiseMiddleware",
        "django.contrib.sessions.middleware.SessionMiddleware",
        "django.middleware.common.CommonMiddleware",
        "django.middleware.csrf.CsrfViewMiddleware",
        "django.contrib.auth.middleware.AuthenticationMiddleware",
        "django.contrib.messages.middleware.MessageMiddleware",
        "django.middleware.clickjacking.XFrameOptionsMiddleware",
        "fullctl.django.middleware.CurrentRequestContext",
    ]

    assert SECURE_SSL_REDIRECT is True
    assert CSRF_COOKIE_SECURE is True
    assert DATABASE_ENGINE == "postgresql_psycopg2"
    assert EMAIL_BACKEND == "django.core.mail.backends.console.EmailBackend"
    assert INSTALLED_APPS == installed_apps
    assert MIDDLEWARE == middleware
    assert WSGI_APPLICATION == "testctl.wsgi.application"


def test_SettingsManager_set_default_append():
    g = {}
    settings_manager = settings.SettingsManager(g)
    settings_manager.set_option("DEBUG", True)
    settings_manager.set_option("TEMPLATES", "")
    settings_manager.set_option("MIDDLEWARE", [""])
    settings_manager.set_default_append()

    # logging define extra formatters and handlers for convenience
    version = 1
    disable_existing_loggers = False
    handlers = {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "color_console",
            "stream": sys.stdout,
        },
        "console_json": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "stream": sys.stdout,
        },
        "mail_admins": {
            "class": "django.utils.log.AdminEmailHandler",
            "level": "ERROR",
            # plain text by default - HTML is nicer
            "include_html": True,
        },
    }
    loggers = {
        "django": {
            "handlers": ["console_json"],
            "level": "INFO",
        },
        "django_structlog": {
            "handlers": ["console_json"],
            "level": "DEBUG",
        },
    }

    assert version == g["LOGGING"]["version"]
    assert disable_existing_loggers == g["LOGGING"]["disable_existing_loggers"]
    assert handlers == g["LOGGING"]["handlers"]
    assert loggers == g["LOGGING"]["loggers"]


def test_SettingsManager_set_service_bridges():
    g = {}
    settings_manager = settings.SettingsManager(g)
    settings_manager.set_service_bridges()

    assert g["AAACTL_HOST"] == ""
    assert g["PDBCTL_HOST"] == ""
    assert g["PEERCTL_HOST"] == ""
    assert g["IXCTL_HOST"] == ""


def test_SettingsManager_set_twentyc_oauth():
    g = {}
    settings_manager = settings.SettingsManager(g)
    settings_manager.set_option("AAACTL_HOST", "aaactlhost.com")
    settings_manager.set_twentyc_oauth()
    aaactlhost = "aaactlhost.com"
    settings_manager.set_twentyc_oauth(aaactlhost)

    assert g["OAUTH_TWENTYC_HOST"] == aaactlhost
    assert g["OAUTH_TWENTYC_ACCESS_TOKEN_URL"] == "aaactlhost.com/account/auth/o/token/"
    assert (
        g["OAUTH_TWENTYC_AUTHORIZE_URL"] == "aaactlhost.com/account/auth/o/authorize/"
    )
    assert g["OAUTH_TWENTYC_PROFILE_URL"] == "aaactlhost.com/account/auth/o/profile/"
    assert g["OAUTH_TWENTYC_KEY"] == ""
    assert g["OAUTH_TWENTYC_SECRET"] == ""
    assert g["SOCIAL_AUTH_REDIRECT_IS_HTTPS"] is True

    authentication_backends = [
        "fullctl.django.social.backends.twentyc.TwentycOAuth2",
        "django.contrib.auth.backends.ModelBackend",
    ]
    assert g["AUTHENTICATION_BACKENDS"] == authentication_backends
    assert g["GRAINY_REMOTE"] == {"url_load": "grainy/load/"}

    social_auth_pipeline = (
        "social_core.pipeline.social_auth.social_details",
        "social_core.pipeline.social_auth.social_uid",
        "social_core.pipeline.social_auth.social_user",
        "social_core.pipeline.user.get_username",
        "social_core.pipeline.user.create_user",
        "social_core.pipeline.social_auth.associate_user",
        "social_core.pipeline.social_auth.load_extra_data",
        "fullctl.django.social.pipelines.sync_organizations",
        "social_core.pipeline.user.user_details",
    )
    assert g["SOCIAL_AUTH_PIPELINE"] == social_auth_pipeline
    assert g["LOGIN_REDIRECT_URL"] == "/"
    assert g["LOGOUT_REDIRECT_URL"] == "/login"
    assert g["LOGIN_URL"] == "/login"


def test_SettingsManager_set_twentyc_service():
    g = {}
    settings_manager = settings.SettingsManager(g)
    settings_manager.set_option("SERVER_EMAIL", "mail@testctl.com")
    settings_manager.set_twentyc_service()

    assert g["SUPPORT_EMAIL"] == "mail@testctl.com"
    assert g["SOCIAL_AUTH_NO_DEFAULT_PROTECTED_USER_FIELDS"] is True
    assert g["SOCIAL_AUTH_PROTECTED_USER_FIELDS"] == ("id", "pk")
    assert g["BILLING_INTEGRATION"] is True
    assert g["SESSION_EXPIRE_AT_BROWSER_CLOSE"] is True
