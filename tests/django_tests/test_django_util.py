from django_grainy.util import Permissions

import fullctl.django.util as util


def test_verified_asns(db, dj_account_objects):
    user = dj_account_objects.user
    user.grainy_permissions.add_permission_set({"verified.asn.123": "crud"})
    perms = Permissions(user)

    assert util.verified_asns(perms)[0]["asn"] == "123"
