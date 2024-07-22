"""
Social Auth backends for aaaCtl OAuth2.

Replaces the deprecated `fullctl.django.social.backends` module.
"""
import os

from social_core.backends.oauth import BaseOAuth2
from social_core.exceptions import AuthFailed
from social_core.utils import append_slash

from fullctl.service_bridge.client import url_join


class AaactlMixin:
    """
    Mixin for AAACTL OAuth2 backends.

    This mixin provides the API URL and OAuth2 URLs for the AAACTL service.

    It replaces the static URLs below.

    AUTHORIZATION_URL = f"{AAACTL_URL}/account/auth/o/authorize/"
    ACCESS_TOKEN_URL = f"{AAACTL_URL}/account/auth/o/token/"
    PROFILE_URL = f"{AAACTL_URL}/account/auth/o/profile/"
    """

    def api_url(self):
        """Returns the API URL, checks {name}_API_URL first, and falls back to AAACTL_URL."""

        configured_url = self.setting("API_URL")
        return append_slash(configured_url or os.getenv("AAACTL_URL"))

    def authorization_url(self):
        return self._url("authorize/")

    def access_token_url(self):
        return self._url("token/")

    def profile_url(self):
        return self._url("profile/")

    def _url(self, path):
        return url_join(self.api_url(), "account/auth/o/", path)


class AaactlOAuth2(AaactlMixin, BaseOAuth2):
    name = "aaactl"

    ACCESS_TOKEN_METHOD = "POST"

    DEFAULT_SCOPE = ["email", "profile", "api_keys", "provider:peeringdb"]
    EXTRA_DATA = ["peeringdb", "api_keys", "organizations"]

    def get_user_details(self, response):
        """Return user details."""
        if response.get("verified_user") is not True:
            raise AuthFailed(self, "User is not verified")

        limit_org = self.setting("LIMIT_ORGANIZATION")

        if limit_org:
            response_orgs = response.get("organizations")
            if not response_orgs:
                raise AuthFailed(self, "User does not meet aaactl requirements.")

            if limit_org not in [org["slug"] for org in response_orgs]:
                raise AuthFailed(self, "User does not meet aaactl requirements.")

        return {
            "username": response.get("user_name"),
            "email": response.get("email") or "",
            "first_name": response.get("given_name"),
            "last_name": response.get("family_name"),
            "is_superuser": response.get("is_superuser"),
            "is_staff": response.get("is_staff"),
        }

    def user_data(self, access_token, *args, **kwargs):
        """Load user data from service."""
        headers = {"Authorization": "Bearer %s" % access_token}
        data = self.get_json(self.profile_url(), headers=headers)
        return data

    def request(self, url, method="GET", *args, **kwargs):
        if "/profile/" in url:
            kwargs.update(params={"referer": "fullctl"})
        return super().request(url, method=method, *args, **kwargs)


class FullCtlOAuth2(AaactlOAuth2):
    """FullCtl OAuth2 backend.
    name update for env variables, etc
    """

    name = "fullctl"


class TwentycOAuth2(AaactlOAuth2):
    """FullCtl OAuth2 backend.
    name update for env variables, etc
    """

    name = "twentyc"
