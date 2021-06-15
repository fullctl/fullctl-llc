from django.http import HttpRequest

from fullctl.django import context_processors


# Settings fixture allows for safe manipulations of settings inside test
def test_account_service(db, dj_account_objects, settings):

    request = HttpRequest()
    request.org = dj_account_objects.org

    expected = {
        "urls": {
            "create_org": "localhost/account/org/create/",
            "manage_org": "localhost/account/?org=test",
            "billing_setup": "localhost/billing/setup?org=test",
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
        "create_instance": True,
        "read_instance": True,
        "update_instance": True,
        "delete_instance": True,
    }

    context = context_processors.permissions(request)
    assert context["permissions"] == full_perms


def test_permissions_readonly(db, dj_account_objects, settings):
    request = HttpRequest()
    request.org = dj_account_objects.orgs[1]
    request.user = dj_account_objects.user
    request.perms = dj_account_objects.perms

    readonly_perms = {
        "create_instance": False,
        "read_instance": True,
        "update_instance": False,
        "delete_instance": False,
    }

    context = context_processors.permissions(request)
    assert context["permissions"] == readonly_perms
