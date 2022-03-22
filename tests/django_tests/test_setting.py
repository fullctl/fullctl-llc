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
