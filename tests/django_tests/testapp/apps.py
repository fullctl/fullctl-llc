from django.apps import AppConfig


class TestAppConfig(AppConfig):
    name = "tests.django_tests.testapp"
    #name = "testapp"
    label = "fullctl_testapp"
    default_auto_field = "django.db.models.AutoField"
