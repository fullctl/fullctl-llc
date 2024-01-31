
import os
from social_core.backends.oauth import BaseOAuth2
from social_core.utils import append_slash
from social_core.exceptions import AuthFailed
from fullctl.service_bridge.client import url_join
from urllib.parse import urljoin

print("3 XXXXXXXXXXXXXXXXXXXXXXXXXXXX\nfullctl.social.backends.twentyc.py")


class AaactlMixin:
#    def api_url(self):
#        """Returns the API URL, checks first for AAACTL_URL in env."""
#        return append_slash(os.getenv("AAACTL_URL", self.setting("API_URL")))

    def authorization_url(self):
        return self._url("authorize/")

    def access_token_url(self):
        return self._url("token/")

    def profile_url(self):
        return self._url("profile/")

    def _url(self, path):
        base_url = append_slash(os.getenv("AAACTL_URL", "https://account.fullctl.io"))
        return url_join(base_url, "account/auth/o/", path)


class TwentycOAuth2(AaactlMixin, BaseOAuth2):
    name = "twentyc"
#    AUTHORIZATION_URL = f"{AAACTL_URL}/account/auth/o/authorize/"
#    ACCESS_TOKEN_URL = f"{AAACTL_URL}/account/auth/o/token/"
#    PROFILE_URL = f"{AAACTL_URL}/account/auth/o/profile/"
    #    AUTHORIZATION_URL = "" # settings.OAUTH_TWENTYC_AUTHORIZE_URL
    #    ACCESS_TOKEN_URL = "" # settings.OAUTH_TWENTYC_ACCESS_TOKEN_URL
    #    PROFILE_URL = "" # settings.OAUTH_TWENTYC_PROFILE_URL

    ACCESS_TOKEN_METHOD = "POST"

    DEFAULT_SCOPE = ["email", "profile", "api_keys", "provider:peeringdb"]
    EXTRA_DATA = ["peeringdb", "api_keys", "organizations"]

    def get_user_details(self, response):
        """Return user details."""
        if response.get("verified_user") is not True:
            raise AuthFailed(self, "User is not verified")

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
