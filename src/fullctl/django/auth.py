import json

import django_grainy.remote
import django_grainy.util
from django.conf import settings
from django.contrib.auth import get_user_model


class RemotePermissionsError(IOError):
    def __init__(self):

        if not getattr(settings, "SERVICE_KEY", None):
            msg = "No SERVICE_KEY specified"
        else:
            msg = (
                "Could not parse response from aaactl for remote permissions."
                "Please check aaactl logs for diagnostic details"
            )
        super().__init__(msg)


class Permissions(django_grainy.util.Permissions):
    pass


class RemotePermissions(django_grainy.remote.Permissions):

    """
    Permissions are provided from the oauth instance.

    We use grainy remote permissions to facilitate this
    """

    def __init__(self, obj):
        super().__init__(obj, **settings.GRAINY_REMOTE)

    def fetch(self, *args, **kwargs):
        try:
            return super().fetch(*args, **kwargs)
        except json.decoder.JSONDecodeError:
            raise RemotePermissionsError()

    def prepare_request(self, params, headers):
        try:
            if isinstance(self.obj, get_user_model()):
                key = settings.SERVICE_KEY
                headers.update(Grainy=self.obj.social_auth.first().uid)
            else:
                key = self.obj.key

            headers.update(Authorization=f"Bearer {key}")
        except AttributeError:
            pass


def permissions(permission_holder, refresh=False):
    if hasattr(permission_holder, "_fullctl_permissions") and not refresh:
        return permission_holder._fullctl_permissions

    if getattr(settings, "USE_LOCAL_PERMISSIONS", False):
        perms = Permissions(permission_holder)
    else:
        perms = RemotePermissions(permission_holder)
    permission_holder._fullctl_permissions = perms
    return perms
