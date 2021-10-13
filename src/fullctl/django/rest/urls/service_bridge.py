import importlib

from django.conf import settings
from django.urls import include, path

import fullctl.django.rest.route.service_bridge

try:
    importlib.import_module(f"django_{settings.SERVICE_TAG}.rest.views.service_bridge")
except ImportError:
    print(f"No service bridge api views found for {settings.SERVICE_TAG}")


urlpatterns = [
    path("", include(fullctl.django.rest.route.service_bridge.router.urls)),
]
