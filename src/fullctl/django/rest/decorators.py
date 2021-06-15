import reversion
from django.conf import settings
from django.contrib.auth import get_user_model
from django_grainy.decorators import grainy_rest_viewset_response
from rest_framework import exceptions
from rest_framework.response import Response

from fullctl.django.auth import Permissions, RemotePermissions
from fullctl.django.models import Organization
from fullctl.django.rest.core import HANDLEREF_FIELDS
from fullctl.service_bridge.client import AaaCtl


class load_object:

    """
    Will load an object and pass it to the view handler
    for `model` Model as argument `argname`

    **Arguments**

    - argname (`str`): will be passed as this keyword argument
    - model (`Model`): django model class

    **Keyword Arguments**

    Any keyword argument will be passed as a filter to the
    `get` query
    """

    def __init__(self, argname, model, **filters):
        self.argname = argname
        self.model = model
        self.filters = filters

    def __call__(self, fn):

        decorator = self

        def wrapped(self, request, *args, **kwargs):
            filters = {}
            for field, key in decorator.filters.items():
                filters[field] = kwargs.get(key)

            try:
                kwargs[decorator.argname] = decorator.model.objects.get(**filters)
            except decorator.model.DoesNotExist:
                return Response(status=404)
            return fn(self, request, *args, **kwargs)

        wrapped.__name__ = fn.__name__
        return wrapped


class grainy_endpoint:
    def __init__(
        self,
        namespace=None,
        require_auth=True,
        explicit=False,
        instance_class=None,
        **kwargs,
    ):
        self.namespace = namespace or ["org", "{request.org.permission_id}"]
        self.require_auth = require_auth
        self.explicit = explicit
        self.instance_class = instance_class
        self.kwargs = kwargs

    def __call__(self, fn):
        decorator = self

        if getattr(settings, "USE_LOCAL_PERMISSIONS", False):
            permissions_cls = Permissions
        else:
            permissions_cls = RemotePermissions

        @grainy_rest_viewset_response(
            namespace=decorator.namespace,
            namespace_instance=decorator.namespace,
            explicit=decorator.explicit,
            ignore_grant_all=True,
            permissions_cls=permissions_cls,
            **decorator.kwargs,
        )
        def wrapped(self, request, *args, **kwargs):

            if decorator.require_auth and not request.user.is_authenticated:
                return Response(status=401)

            if decorator.instance_class:
                instance, _ = decorator.instance_class.objects.get_or_create(
                    org=request.org
                )
                kwargs.update(instance=instance)

            with reversion.create_revision():
                if isinstance(request.user, get_user_model()):
                    reversion.set_user(request.user)
                else:
                    reversion.set_comment(f"{request.user}")

                return fn(self, request, org=request.org, *args, **kwargs)

        wrapped.__name__ = fn.__name__

        return wrapped


class _aaactl:
    @property
    def connected(self):
        return getattr(settings, "AAACTL_HOST", None) is not None

    def bridge(self, org_slug):
        return AaaCtl(settings.AAACTL_HOST, settings.SERVICE_KEY, org_slug)


class billable(_aaactl):

    """
    Will use the aaactl service bridge to determine
    if the specified product/service has accumulated
    costs during the current subscription cycle and
    return an error response if the there are costs
    but the organization has not yet set up billing
    """

    def __init__(self, product):
        self.product = product

    def __call__(self, fn):

        product = self.product

        # if billing integration is disabled we just
        # return the undecorated function

        if not settings.BILLING_INTEGRATION:
            return fn

        def wrapped(viewset, request, *args, **kwargs):

            if not self.connected:
                return fn(viewset, request, *args, **kwargs)

            aaactl = self.bridge(request.org.slug)

            if aaactl.requires_billing(product):
                return Response(
                    {
                        "non_field_errors": [
                            f"Billing setup required to continue using {product}. Please set up billing for your organization at {settings.AAACTL_HOST}/billing/setup?org={request.org.slug}"
                        ]
                    },
                    status=403,
                )
            return fn(viewset, request, *args, **kwargs)

        return wrapped


def serializer_registry():
    class Serializers:
        pass

    def register(cls):
        if not hasattr(cls, "ref_tag"):
            cls.ref_tag = cls.Meta.model.HandleRef.tag
            cls.Meta.fields += ["grainy"] + HANDLEREF_FIELDS
        setattr(Serializers, cls.ref_tag, cls)
        return cls

    return (Serializers, register)


def set_org(fn):
    def wrapped(self, request, pk, *args, **kwargs):
        if pk == "personal":
            org = request.user.personal_org
        else:
            org = Organization.objects.get(slug=pk)
        kwargs["org"] = org
        return fn(self, request, pk, *args, **kwargs)

    wrapped.__name__ = fn.__name__
    return wrapped


def disable_api_key(fn):
    def wrapped(self, request, *args, **kwargs):
        if hasattr(request, "api_key"):
            raise exceptions.AuthenticationFailed(
                "API key authentication not allowed for this operation"
            )
        return fn(self, request, *args, **kwargs)

    wrapped.__name__ = fn.__name__
    return wrapped
