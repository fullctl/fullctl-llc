from rest_framework.throttling import SimpleRateThrottle

__all__ = [
    "ContactMessage",
]


class ContactMessage(SimpleRateThrottle):

    """
    Rate limiting for contact messages to support.
    """

    scope = "contact_message"

    def get_cache_key(self, request, view):
        ident = self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}
