import os

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
