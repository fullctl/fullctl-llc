from functools import wraps

import reversion
from django.conf import settings
from django.contrib.auth import get_user_model
from django_grainy.decorators import grainy_rest_viewset_response
from rest_framework import exceptions
from rest_framework.response import Response

from fullctl.django.auth import Permissions, RemotePermissions
from fullctl.django.models import Instance, Organization
from fullctl.django.rest.authentication import APIKey
from fullctl.django.rest.core import HANDLEREF_FIELDS
from fullctl.service_bridge.client import AaaCtl


class base:
    def load_org_instance(self, request, data):
        data.update(org=request.org)

        if isinstance(data.get("instance"), self.instance_class):
            return

        instance, _ = self.instance_class.objects.get_or_create(org=request.org)
        data.update(instance=instance, org=request.org)


class load_object(base):

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

    def __init__(self, argname, model, instance_class=Instance, **filters):
        self.argname = argname
        self.model = model
        self.filters = filters
        self.instance_class = instance_class

    def __call__(self, fn):
        decorator = self

        def wrapped(self, request, *args, **kwargs):
            filters = {}

            decorator.load_org_instance(request, kwargs)

            for field, key in decorator.filters.items():
                filters[field] = kwargs.get(key)

            try:
                kwargs[decorator.argname] = decorator.model.objects.get(**filters)
            except decorator.model.DoesNotExist:
                return Response(status=404)

            return fn(self, request, *args, **kwargs)

        wrapped.__name__ = fn.__name__
        return wrapped


class grainy_endpoint_response(grainy_rest_viewset_response):

    """
    Override of grainy_rest_viewset_response so we can
    toggle permission application to responses on or off
    through our grainy_endpoint decorator
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.enable_apply_perms = kwargs.pop("enable_apply_perms", True)

    def apply_perms(self, request, response, view_function, view):
        if self.enable_apply_perms:
            return super().apply_perms(request, response, view_function, view)
        return response


class grainy_endpoint(base):
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
        self.enable_apply_perms = kwargs.pop("enable_apply_perms", True)
        self.kwargs = kwargs

    def __call__(self, fn):
        decorator = self

        if getattr(settings, "USE_LOCAL_PERMISSIONS", False):
            permissions_cls = Permissions
        else:
            permissions_cls = RemotePermissions

        @grainy_endpoint_response(
            namespace=decorator.namespace,
            namespace_instance=decorator.namespace,
            explicit=decorator.explicit,
            ignore_grant_all=True,
            permissions_cls=permissions_cls,
            enable_apply_perms=decorator.enable_apply_perms,
            **decorator.kwargs,
        )
        def inner(self, request, *args, **kwargs):
            """
            inner wrapper, called after grainy permissioning logic ran

            handles auth requirement, loading of organization instance
            and opening of reversion context
            """

            if decorator.require_auth and not request.user.is_authenticated:
                return Response(status=401)

            if decorator.instance_class:
                decorator.load_org_instance(request, kwargs)

            # if an api key is set, that should become the permission
            # holder

            if hasattr(request, "api_key"):
                request.perms = permissions_cls(APIKey(request.api_key))

            # check if the request is permissioned to access
            # the fullctl service

            if not request.perms.check(
                f"service.{settings.SERVICE_TAG}.{request.org.permission_id}",
                "r",
                ignore_grant_all=True,
            ):
                return Response(status=403)

            with reversion.create_revision():
                if isinstance(request.user, get_user_model()):
                    reversion.set_user(request.user)
                else:
                    reversion.set_comment(f"{request.user}")

                return fn(self, request, *args, **kwargs)

        inner.__name__ = fn.__name__

        @wraps(fn)
        def outer(self, request, *args, **kwargs):
            """
            outer wrapper, called before grainy permissioning logic runs

            handles superuser imitation for sufficiently provisioned api keys
            """

            as_user = request.headers.get("X-User")
            if as_user and hasattr(request, "api_key"):
                if permissions_cls(APIKey(request.api_key)).check(
                    f"superuser.{as_user}", "c"
                ):
                    request.user = get_user_model().objects.get(
                        social_auth__uid=as_user
                    )

            return inner(self, request, *args, **kwargs)

        outer.__name__ = fn.__name__

        return outer


class _aaactl:
    @property
    def connected(self):
        return getattr(settings, "AAACTL_URL", None) is not None

    def bridge(self, org_slug):
        return AaaCtl(settings.AAACTL_URL, settings.SERVICE_KEY, org_slug)


class billable(_aaactl):

    """
    Will use the aaactl service bridge to determine
    if the specified product/service has accumulated
    costs during the current subscription subscription_cycle and
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
                            f"Billing setup required to continue using {product}. Please set up billing for your organization at {settings.AAACTL_URL}/billing/setup?org={request.org.slug}"
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

        ref_tag = cls.ref_tag.replace(".", "__")
        setattr(Serializers, ref_tag, cls)
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
