from django.urls import include, path

import fullctl.django.rest.route.usage
import fullctl.django.rest.views.usage

urlpatterns = [
    path("", include(fullctl.django.rest.route.usage.router.urls)),
]
