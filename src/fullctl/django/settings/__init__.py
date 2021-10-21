"""
This file handles the default django settings for fullctl services.

Versioning has been dropped in favor of using separate function names.
"""
import os
import sys

import confu.util


def print_debug(*args, **kwargs):
    # XXX
    print(*args, **kwargs)


def get_locale_name(code):
    """Gets the readble name for a locale code."""
    language_map = dict(django.conf.global_settings.LANGUAGES)

    # check for exact match
    if code in language_map:
        return language_map[code]

    # try for the language, fall back to just using the code
    language = code.split("-")[0]
    return language_map.get(language, code)


def read_file(name):
    with open(name) as fh:
        return fh.read()


# TODO : add dict access and logging
class SettingsManager(confu.util.SettingsManager):

    # settings manager extensions

    def get(self, name):
        """Get name, raise if not set.
        Should use _DEFAULT_ARG
        """
        #        if key in self.scope:
        return self.scope[name]

    def set_option(self, name, value, envvar_type=None):
        """Return the resulting value after setting."""
        super().set_option(name, value, envvar_type)
        return self.get(name)

    def print_debug(self, *args, **kwargs):
        if DEBUG:
            print(*args, **kwargs)

    def try_include(self, filename):
        """Tries to include another file into current scope."""
        print_debug(f"including {filename}")
        try:
            with open(filename) as f:
                exec(compile(f.read(), filename, "exec"), self.scope)

            print_debug(f"loaded additional settings file '{filename}'")

        except FileNotFoundError:
            print_debug(
                f"additional settings file '{filename}' was not found, skipping"
            )

    def try_include_env(self, suffix=""):
        # look for mainsite/settings/${RELEASE_ENV}.py and load if it exists
        # needs __file__ from caller
        env_file = os.path.join(
            os.path.dirname(__file__), f"{self.get('RELEASE_ENV')}.py"
        )
        settings.try_include(env_file)


def set_release_env_v1(settings_manager):
    """
    Sets release env for django service settings version 1.

    Version is an arbitrary number to define the defaults to allow for ease of service migration.
    """
    # set RELEASE_ENV, usually one of dev, beta, prod, run_tests
    settings_manager.set_option("RELEASE_ENV", "dev")
    release_env = settings_manager.scope["RELEASE_ENV"]

    # set DEBUG first, print_debug() depends on it
    if release_env == "dev":
        settings_manager.set_bool("DEBUG", True)
    else:
        settings_manager.set_bool("DEBUG", False)

    if release_env == "prod":
        # we only expose admin on non-production environments
        settings_manager.set_bool("EXPOSE_ADMIN", False)
    else:
        settings_manager.set_bool("EXPOSE_ADMIN", True)


def set_default_v1(settings_manager):
    """
    Sets default django service settings version 1.

    Version is an arbitrary number to define the defaults to allow for ease of service migration.
    """
    service_tag = settings_manager.scope["SERVICE_TAG"]

    # Contact email, from address, support email
    settings_manager.set_from_env("SERVER_EMAIL")

    # django secret key
    settings_manager.set_from_env("SECRET_KEY")

    # database

    settings_manager.set_option("DATABASE_ENGINE", "postgresql_psycopg2")
    settings_manager.set_option("DATABASE_HOST", "127.0.0.1")
    settings_manager.set_option("DATABASE_PORT", "")
    settings_manager.set_option("DATABASE_NAME", service_tag)
    settings_manager.set_option("DATABASE_USER", service_tag)
    settings_manager.set_option("DATABASE_PASSWORD", "")

    # email

    # default email goes to console
    settings_manager.set_option(
        "EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
    )
    # TODO EMAIL_SUBJECT_PREFIX = "[{}] ".format(RELEASE_ENV)

    settings_manager.set_from_env("EMAIL_HOST")
    settings_manager.set_from_env("EMAIL_PORT")
    settings_manager.set_from_env("EMAIL_HOST_USER")
    settings_manager.set_from_env("EMAIL_HOST_PASSWORD")
    settings_manager.set_bool("EMAIL_USE_TLS", True)

    # Application definition

    INSTALLED_APPS = [
        "django.contrib.admin",
        "django.contrib.auth",
        "django.contrib.contenttypes",
        "django.contrib.sessions",
        "django.contrib.messages",
        "django.contrib.staticfiles",
    ]
    settings_manager.set_default("INSTALLED_APPS", INSTALLED_APPS)

    MIDDLEWARE = [
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
    settings_manager.set_default("MIDDLEWARE", MIDDLEWARE)

    settings_manager.set_default("ROOT_URLCONF", f"{service_tag}.urls")
    settings_manager.set_default("WSGI_APPLICATION", f"{service_tag}.wsgi.application")

    # eval from default.py file
    filename = os.path.join(os.path.dirname(__file__), f"default.py")
    settings_manager.try_include(filename)


def set_default_append(settings_manager):
    DEBUG = settings_manager.get("DEBUG")
    settings_manager.set_option("DEBUG_EMAIL", DEBUG)
    for template in settings_manager.get("TEMPLATES"):
        template["OPTIONS"]["debug"] = DEBUG
    # TEMPLATES[0]["OPTIONS"]["debug"] = DEBUG

    # use structlog for logging
    import structlog

    MIDDLEWARE = settings_manager.get("MIDDLEWARE")

    MIDDLEWARE += [
        "django_structlog.middlewares.RequestMiddleware",
    ]

    # set these explicitly, not with DEBUG
    DJANGO_LOG_LEVEL = settings_manager.set_option("DJANGO_LOG_LEVEL", "INFO")
    FULLCTL_LOG_LEVEL = settings_manager.set_option("FULLCTL_LOG_LEVEL", "DEBUG")

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=structlog.threadlocal.wrap_dict(dict),
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # logging define extra formatters and handlers for convenience
    LOGGING = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processor": structlog.processors.JSONRenderer(),
            },
            "color_console": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processor": structlog.dev.ConsoleRenderer(),
            },
            "key_value": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processor": structlog.processors.KeyValueRenderer(
                    key_order=["timestamp", "level", "event", "logger"]
                ),
            },
        },
        "handlers": {
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
        },
        "loggers": {
            "django": {
                "handlers": ["console_json"],
                "level": DJANGO_LOG_LEVEL,
            },
            "django_structlog": {
                "handlers": ["console_json"],
                "level": FULLCTL_LOG_LEVEL,
            },
        },
    }


def set_languages_docs(settings_manager):
    settings_manager.set_option("ENABLE_ALL_LANGUAGES", False)

    if ENABLE_ALL_LANGUAGES:
        language_dict = dict(LANGUAGES)
        for locale_path in LOCALE_PATHS:
            for name in os.listdir(locale_path):
                path = os.path.join(locale_path, name)
                if not os.path.isdir(os.path.join(path, "LC_MESSAGES")):
                    continue
                code = name.replace("_", "-").lower()
                if code not in language_dict:
                    name = _(get_locale_name(code))
                    language_dict[code] = name

        LANGUAGES = sorted(language_dict.items())

    API_DOC_INCLUDES = {}
    API_DOC_PATH = os.path.join(BASE_DIR, "docs", "api")
    for i, j, files in os.walk(API_DOC_PATH):
        for file in files:
            base, ext = os.path.splitext(file)
            if ext == ".md":
                API_DOC_INCLUDES[base] = os.path.join(API_DOC_PATH, file)
