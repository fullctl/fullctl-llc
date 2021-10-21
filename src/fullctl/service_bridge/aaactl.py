try:
    from django.conf import settings

    DEFAULT_SERVICE_KEY = settings.SERVICE_KEY
except ImportError:
    DEFAULT_SERVICE_KEY = ""

from fullctl.service_bridge.client import Bridge, DataObject

CACHE = {}


class AaactlEntity(DataObject):
    source = "aaactl"
    description = "Aaactl Object"


class Aaactl(Bridge):

    """
    Service bridge for aaactl data retrieval
    """

    class Meta:
        service = "aaactl"
        ref_tag = "base"
        data_object_cls = AaactlEntity

    def __init__(self, key=None, org=None, **kwargs):

        if not key:
            key = DEFAULT_SERVICE_KEY

        kwargs.setdefault("cache_duration", 10)
        kwargs.setdefault("cache", CACHE)

        super().__init__(settings.AAACTL_HOST, key, org, **kwargs)
        self.url = f"{self.url}/service-bridge"


class ServiceApplicationObject(AaactlEntity):
    description = "Aaactl ServiceApplication"

    def for_org(self, org):
        if org:
            self.org_redirect = self.invite_redirect.format(org=org)
        else:
            self.org_redirect = self.api_host
        return self


class ServiceApplication(Aaactl):
    class Meta(Aaactl.Meta):
        ref_tag = "svcapp"
        data_object_cls = ServiceApplicationObject
