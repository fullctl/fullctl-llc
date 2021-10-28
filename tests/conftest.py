import os
from django.conf import settings

# FIXME: move this out
import tests.django_tests.project.settings
from tests.django_tests.fixtures import *  # noqa: F401, F403
import fullctl.service_bridge.client as client

client.TEST_DATA_PATH = os.path.join(
    os.path.dirname(__file__),
    "data"
)

_settings = {
    k: v
    for k, v in tests.django_tests.project.settings.__dict__.items()
    if (not k.startswith("_") and k.isupper())
}

settings.configure(**_settings)
