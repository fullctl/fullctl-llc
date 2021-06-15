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


class APIKeyAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        key = request.GET.get("key")

        if not key:
            auth = request.headers.get("Authorization")
            if auth:
                auth = auth.split(" ")
                if auth[0].lower() in ["token", "bearer"]:
                    key = auth[1]

        if key:
            request.api_key = key
            return (APIKey(key), None)
        else:
            return None
