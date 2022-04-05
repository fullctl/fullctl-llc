import importlib  # noqa

from django.conf import settings
from django.contrib.staticfiles import views as static_file_views
from django.urls import include, path, re_path
from django.views.generic import TemplateView

import fullctl.django.views

urlpatterns = []

if getattr(settings, "PDBCTL_HOST", None):

    import fullctl.django.autocomplete.pdb

    urlpatterns += [
        path(
            "autocomplete/pdb/ix",
            fullctl.django.autocomplete.pdb.peeringdb_ix.as_view(),
            name="pdb ix autocomplete",
        ),
        path(
            "autocomplete/pdb/asn",
            fullctl.django.autocomplete.pdb.peeringdb_asn.as_view(),
            name="pdb asn autocomplete",
        ),
        path(
            "autocomplete/pdb/org",
            fullctl.django.autocomplete.pdb.peeringdb_org.as_view(),
            name="pdb org autocomplete",
        ),
    ]

if settings.DEBUG:
    # support version ignorant serving of static files
    urlpatterns += [
        re_path(r"^s/[^\/]+/(?P<path>.*)$", static_file_views.serve),
    ]


for import_path, namespace in getattr(settings, "FULLCTL_ADDON_URLS", []):
    urlpatterns += [path("", include((import_path, namespace), namespace=namespace))]

urlpatterns += [
    path("_diag", fullctl.django.views.diag),
    path(
        "api/account/",
        include(
            ("fullctl.django.rest.urls.account", "fullctl_account_api"),
            namespace="fullctl_account_api",
        ),
    ),
    path(
        "api/",
        include(
            ("fullctl.django.rest.urls.usage", "fullctl_usage_api"),
            namespace="fullctl_usage_api",
        ),
    ),
    path(
        "api/",
        include(
            ("fullctl.django.rest.urls.aaactl_sync", "fullctl_aaactl_sync_api"),
            namespace="fullctl_aaactl_sync_api",
        ),
    ),
    path(
        "api/",
        include(
            ("fullctl.django.rest.urls.service_bridge", "service_bridge_api"),
            namespace="service_bridge_api",
        ),
    ),
    path("logout/", fullctl.django.views.logout, name="logout"),
    path("login/", fullctl.django.views.login, name="login"),
    path(
        "apidocs/swagger",
        TemplateView.as_view(
            template_name="common/apidocs/swagger.html",
        ),
        name="swagger",
    ),
    path(
        "apidocs/redoc",
        TemplateView.as_view(
            template_name="common/apidocs/redoc.html",
        ),
        name="redoc",
    ),
]
