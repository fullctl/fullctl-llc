from functools import wraps

import django.http
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse

import fullctl.django.context as context
from fullctl.django.models import Instance, Organization


class require_auth:

    """
    decorate a view to require auth
    """

    def __call__(self, fn):
        def wrapped(request, *args, **kwargs):
            local_auth = getattr(settings, "USE_LOCAL_PERMISSIONS", False)

            if not request.user.is_authenticated:
                if not local_auth:
                    return redirect(
                        reverse("social:begin", args=("twentyc",))
                        + f"?next={request.get_full_path()}"
                    )
                else:
                    # redirect to django-admin login
                    return redirect(
                        reverse("admin:login") + f"?next={request.get_full_path()}"
                    )

            return fn(request, *args, **kwargs)

        wrapped.__name__ = fn.__name__
        return wrapped


class load_instance:

    """
    decorator that loads the instance for the selected
    org.

    org is selected in middleware.py and set on the request
    at request.org

    This will create the org's instance if it does not exist yet

    Keyword Argument(s):

    - public (`bool`): if public, no permission checks will be done,
    otherwise read permission to the org is required
    """

    def __init__(self, public=False):
        self.model = Instance
        self.public = public

    def __call__(self, fn):
        model = self.model
        public = self.public

        def wrapped(request, *args, **kwargs):
            org = request.org
            if not public and org not in Organization.accessible(request.user):
                if request.user.is_authenticated and not getattr(
                    request, "impersonating", None
                ):
                    raise django.http.Http404()
                else:
                    return redirect(
                        reverse("login") + f"?next={request.get_full_path()}"
                    )

            try:
                instance, _ = model.objects.get_or_create(org=org)
            except model.DoesNotExist:
                raise django.http.Http404()

            request.app_id = instance.app_id

            return fn(request, instance, *args, **kwargs)

        wrapped.__name__ = fn.__name__
        wrapped.public = public

        return wrapped


class service_bridge_sync:
    def __init__(self, **kwargs):
        self.ctx_args = kwargs

    def __call__(self, fn):
        ctx_args = self.ctx_args

        def wrapped(*args, **kwargs):
            with context.service_bridge_sync(**ctx_args):
                return fn(*args, **kwargs)

        wrapped.__name__ = fn.__name__
        return wrapped


def origin_allowed(origins):
    """
    Origin white listing for CORS enabled views.
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            origin = request.META.get("HTTP_ORIGIN")
            if origin not in origins:
                response_data = {"status": "error", "message": "Origin not allowed"}
                return JsonResponse(response_data, status=403)

            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator
