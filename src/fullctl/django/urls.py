import importlib  # noqa

from django.conf import settings
from django.contrib.staticfiles import views as static_file_views
from django.urls import include, path, re_path
from django.views.generic import TemplateView

import fullctl.django.rest.urls.service_bridge_proxy as proxy
import fullctl.django.views
from fullctl.django.views.api_schema import api_schema

urlpatterns = []

if settings.SERVICE_TAG != "aaactl":
    proxy.setup(
        "aaactl",
        proxy.proxy_api(
            "aaactl",
            settings.AAACTL_URL,
            [
                (
                    "billing/org/{org_tag}/start_trial/",
                    "billing/<str:org_tag>/start_trial/",
                    "start-trial",
                )
            ],
        ),
    )

    urlpatterns = proxy.urlpatterns(["aaactl"])


if getattr(settings, "PDBCTL_URL", None):
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
            "autocomplete/pdb/net",
            fullctl.django.autocomplete.pdb.peeringdb_net.as_view(),
            name="pdb asn autocomplete",
        ),
        path(
            "autocomplete/pdb/org",
            fullctl.django.autocomplete.pdb.peeringdb_org.as_view(),
            name="pdb org autocomplete",
        ),
    ]

if getattr(settings, "DEVICECTL_URL", None):
    import fullctl.django.autocomplete.devicectl

    urlpatterns += [
        path(
            "autocomplete/device/port",
            fullctl.django.autocomplete.devicectl.devicectl_port.as_view(),
            name="devicectl port autocomplete",
        ),
    ]


if getattr(settings, "PREFIXCTL_URL", None):
    import fullctl.django.autocomplete.prefixctl

    urlpatterns += [
        path(
            "autocomplete/prefix/prefix_set",
            fullctl.django.autocomplete.prefixctl.prefixctl_prefix_set.as_view(),
            name="prefix set autocomplete",
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
    path("health/tasks/", fullctl.django.views.tasks_queue_status, name="tasks-queue"),
    path("health/", fullctl.django.views.healthcheck),
    path("authcheck/", fullctl.django.views.authcheck),
    path("apidocs/schema.json", api_schema, name="api_schema"),
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
    path(
        "<str:org_tag>/file/<str:file_name>/",
        fullctl.django.views.organization_file_download,
        name="organization-file-download",
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
