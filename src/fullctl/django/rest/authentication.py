from rest_framework import authentication


class APIKey:
    def __init__(self, key):
        self.key = key

    @property
    def is_authenticated(self):
        if self.key:
            return True
        return False

    @property
    def id(self):
        return self.key[:8]

    @property
    def pk(self):
        return self.id


def key_from_request(request):
    """
    Retrieves api key value from request by checking
    both the `key` url parameter, as well as the `Authorization`
    header for `Bearer` or `Token` authentication

    Returns the key if it could be found, returns None if not
    """
    key = request.GET.get("key")

    if not key:
        auth = request.headers.get("Authorization")
        if auth:
            auth = auth.split(" ")
            if auth[0].lower() in ["token", "bearer"]:
                key = auth[1]
    return key


class APIKeyAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        key = key_from_request(request)
        if key:
            request.api_key = key
            return (APIKey(key), None)
        else:
            return None
