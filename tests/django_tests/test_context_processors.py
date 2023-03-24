from datetime import datetime

from django.http import HttpRequest

from fullctl.django import context_processors
from fullctl.django.auth import RemotePermissionsError


# Settings fixture allows for safe manipulations of settings inside test
def test_account_service(db, dj_account_objects, settings):
    request = HttpRequest()
    request.org = dj_account_objects.org

    expected = {
        "urls": {
            "create_org": "localhost/account/",
            "manage_org": "localhost/account/?org=test",
            "billing_setup": "localhost/billing/setup?org=test",
        }
    }

    context = context_processors.account_service(request)

    assert context["account_service"] == expected


def test_account_service_no_org(db, dj_account_objects, settings):
    request = HttpRequest()

    expected = {
        "urls": {
            "create_org": "localhost/account/",
            "manage_org": "localhost/account/?org=",
            "billing_setup": "localhost/billing/setup?org=",
        }
    }

    context = context_processors.account_service(request)

    assert context["account_service"] == expected


def test_permissions_crud(db, dj_account_objects, settings):
    request = HttpRequest()
    request.org = dj_account_objects.orgs[0]
    request.user = dj_account_objects.user
    request.perms = dj_account_objects.perms

    full_perms = {
        "billing": False,
        "create_instance": True,
        "read_instance": True,
        "update_instance": True,
        "delete_instance": True,
    }

    context = context_processors.permissions(request)
    assert context["permissions"] == full_perms


def test_permissions_crud_no_org(db, dj_account_objects, settings):
    request = HttpRequest()
    request.user = dj_account_objects.user
    request.perms = dj_account_objects.perms

    context = context_processors.permissions(request)
    assert context["permissions"] == {}


def test_permissions_crud_RemotePermissionsError():
    request = HttpRequest()
    request.error_response = RemotePermissionsError()

    context = context_processors.permissions(request)
    assert context["permissions"] == {}


def test_permissions_readonly(db, dj_account_objects, settings):
    request = HttpRequest()
    request.org = dj_account_objects.orgs[1]
    request.user = dj_account_objects.user
    request.perms = dj_account_objects.perms

    readonly_perms = {
        "billing": False,
        "create_instance": False,
        "read_instance": True,
        "update_instance": False,
        "delete_instance": False,
    }

    context = context_processors.permissions(request)
    assert context["permissions"] == readonly_perms


def test_conf(db, dj_account_objects, settings):
    request = HttpRequest()

    conf_support_email = {
        "google_analytics_id": None,
        "cloudflare_analytics_id": "asdf",
        "support_email": "support@localhost",
        "no_reply_email": "noreply@localhost",
        "contact_us_email": "hello@localhost",
        "post_feature_request_url": "test://new-feature",
        "docs_url": "test://docs",
        "legal_url": "test://legal",
        "current_year": datetime.now().year,
    }

    conf = context_processors.conf(request)
    assert conf == conf_support_email
