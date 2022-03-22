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
    setting = settings_manager.set_option("RELEASE_ENV", "testdev")
    settings_manager.try_include_env() # TODO add assertion
