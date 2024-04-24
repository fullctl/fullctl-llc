from django.conf import settings
from django.contrib.auth import get_user_model, logout
from django.http import Http404

import fullctl.service_bridge.aaactl as aaactl
from fullctl.django.auth import RemotePermissions, permissions
from fullctl.django.context import current_request
from fullctl.django.models import Organization
from fullctl.django.rest.authentication import APIKey, key_from_request


class CurrentRequestContext:

    """
    Middleware that sets the current request context

    This allows us to access the current request from anywhere we need to
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        with current_request(request):
            return self.get_response(request)


class RequestAugmentation:

    """
    Augments the request by selecting org from `org_tag`
    passed in the URL

    When fullctl is not managed by oauth it also makes sure
    that the request users personal org exists.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        kwargs = request.resolver_match.kwargs

        request.perms = permissions(request.user)
        request.perms.load()

        if "impersonating" in request.session:
            # impersonation is enabled, set the impersonated user
            # as the current user on the request

            impersonate_user = get_user_model().objects.get(
                id=request.session["impersonating"]
            )

            request.impersonating = {
                "superuser": request.user,
                "user": impersonate_user,
            }
            request.user = impersonate_user

            # fetch permissions for the impersonated user

            request.perms = permissions(request.user)
            request.perms.load()

        if (
            not hasattr(request.user, "org_set") or not request.user.org_set.exists()
        ) and "org_tag" not in kwargs:
            if not request.user.is_authenticated:
                # user is not authenticated, return
                # Guest org

                request.org = Organization(name="Guest")
                return

        try:
            if "org_tag" in kwargs:
                request.org = Organization.objects.get(slug=kwargs["org_tag"])

            elif request.user.org_set.exists():
                default_org = request.user.org_set.filter(is_default=True).first()

                if default_org:
                    request.org = default_org.org
                else:
                    request.org = (
                        request.user.org_set.filter(user=request.user).first().org
                    )

            if hasattr(request.user, "org_set"):
                request.orgs = request.user.org_set.all()
            else:
                request.orgs = []
        except Organization.DoesNotExist:
            raise Http404

        if not getattr(request, "org", None):
            request.org = Organization(name="Guest")

            return


class TokenValidationMiddleware:

    """
    Uses the aaactl service bridge to check if the oAuth access
    token used to authenticate the requesting user is still
    valid.

    If it is no longer valid, the user is logged out forcing
    them to re-authenticate with aaactl.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        if user.is_authenticated:
            social_auth = user.social_auth.filter(provider="twentyc").first()

            if not social_auth:
                # user does not have a social auth record,
                # this is an edge case where the user was created
                # manually through create_superuser or via django-admin
                return self.get_response(request)

            access_token = social_auth.extra_data["access_token"]
            aaactl_token = aaactl.OauthAccessToken().first(token=access_token)

            if not aaactl_token or aaactl_token.expired:
                # token no longer valid on aaactl side, invalidate session
                # TODO: possibly extend token expiry on certain actions
                logout(request)

        response = self.get_response(request)
        return response


class AutocompleteRequestPermsMiddleware:

    """
    Middleware that attached perms to the request object
    if the request is for an autocomplete path
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        # only do this for the autocomplete path
        # other paths should use the drf to do the needful
        path = request.path
        if not path.startswith("/autocomplete/"):
            return

        if getattr(settings, "USE_LOCAL_PERMISSIONS", False):
            return

        permissions_cls = RemotePermissions

        key = key_from_request(request)

        if key:
            request.api_key = key
            request.perms = permissions_cls(APIKey(key))
