import warnings

from django.conf import settings

# from six.moves.urllib_parse import unquote, urlencode
from social_core.backends.oauth import BaseOAuth2
from social_core.exceptions import AuthFailed

warnings.warn(
    "These are deprecated in favor of fullctl.social.backends",
    DeprecationWarning,
)


# this should be able to be replaced with but needs testing
# from fullctl.social.backends import TwentycOAuth2


class TwentycOAuth2(BaseOAuth2):
    name = "twentyc"
    AUTHORIZATION_URL = settings.OAUTH_TWENTYC_AUTHORIZE_URL
    ACCESS_TOKEN_URL = settings.OAUTH_TWENTYC_ACCESS_TOKEN_URL
    PROFILE_URL = settings.OAUTH_TWENTYC_PROFILE_URL

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
        data = self.get_json(self.PROFILE_URL, headers=headers)
        return data

    def request(self, url, method="GET", *args, **kwargs):
        if "/profile/" in url:
            kwargs.update(params={"referer": "fullctl"})
        return super().request(url, method=method, *args, **kwargs)
