try:
    from django.conf import settings

    DEFAULT_SERVICE_KEY = settings.SERVICE_KEY
except ImportError:
    DEFAULT_SERVICE_KEY = ""

from fullctl.service_bridge.client import Bridge, DataObject, url_join

CACHE = {}


class PrefixctlEntity(DataObject):
    source = "prefixctl"
    description = "Prefixctl Object"


class Prefixctl(Bridge):

    """
    Service bridge for prefixctl data retrieval
    """

    class Meta:
        service = "prefixctl"
        ref_tag = "base"
        data_object_cls = PrefixctlEntity

    def __init__(self, key=None, org=None, **kwargs):
        if not key:
            key = DEFAULT_SERVICE_KEY

        kwargs.setdefault("cache_duration", 10)
        kwargs.setdefault("cache", CACHE)

        super().__init__(settings.PREFIXCTL_URL, key, org, **kwargs)
        self.url = url_join(self.url, "service-bridge/")


class PrefixSetObject(PrefixctlEntity):
    description = "PrefixCtl PrefixSet"


class PrefixSet(Prefixctl):
    class Meta(Prefixctl.Meta):
        ref_tag = "prefix_set"
        data_object_cls = PrefixSetObject
