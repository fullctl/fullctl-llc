from django.conf import settings
from django.contrib.auth import views as auth_views
from django.urls import include, path
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
        "login/",
        auth_views.LoginView.as_view(template_name="common/auth/login.html"),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(next_page="/login"), name="logout"),
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
