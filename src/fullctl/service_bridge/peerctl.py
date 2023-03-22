try:
    from django.conf import settings

    DEFAULT_SERVICE_KEY = settings.SERVICE_KEY
except ImportError:
    DEFAULT_SERVICE_KEY = ""

from fullctl.service_bridge.client import Bridge, DataObject, url_join

CACHE = {}


class PeerctlEntity(DataObject):
    source = "peerctl"
    description = "Peerctl Object"


class Peerctl(Bridge):

    """
    Service bridge for peerctl data retrieval
    """

    class Meta:
        service = "peerctl"
        ref_tag = "base"
        data_object_cls = PeerctlEntity

    def __init__(self, key=None, org=None, **kwargs):
        if not key:
            key = DEFAULT_SERVICE_KEY

        kwargs.setdefault("cache_duration", 10)
        kwargs.setdefault("cache", CACHE)

        super().__init__(settings.PEERCTL_URL, key, org, **kwargs)
        self.url = url_join(self.url, "service-bridge/")


class NetworkObject(PeerctlEntity):
    description = "Peerctl Network"


class Network(Peerctl):
    class Meta(Peerctl.Meta):
        ref_tag = "net"
        data_object_cls = NetworkObject
