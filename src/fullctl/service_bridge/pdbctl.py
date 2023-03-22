try:
    from django.conf import settings

    DEFAULT_SERVICE_KEY = settings.SERVICE_KEY
except ImportError:
    DEFAULT_SERVICE_KEY = ""

from fullctl.service_bridge.client import Bridge, DataObject, url_join

CACHE = {}


class PeeringDBEntity(DataObject):
    description = "PeeringDB Object"
    source = "pdbctl"


class Pdbctl(Bridge):

    """
    Service bridge to pdbctl for peeringdb data
    retrieval
    """

    class Meta:
        service = "pdbctl"
        ref_tag = "base"
        data_object_cls = PeeringDBEntity

    def __init__(self, key=None, org=None, **kwargs):
        if not key:
            key = DEFAULT_SERVICE_KEY

        kwargs.setdefault("cache_duration", 10)
        kwargs.setdefault("cache", CACHE)

        super().__init__(settings.PDBCTL_URL, key, org, **kwargs)
        self.url = url_join(self.url, "service-bridge/")


class InternetExchange(Pdbctl):
    class Meta(Pdbctl.Meta):
        ref_tag = "ix"


class Facility(Pdbctl):
    class Meta(Pdbctl.Meta):
        ref_tag = "fac"


class NetworkObject(PeeringDBEntity):
    description = "PeeringDB net"


class Network(Pdbctl):
    class Meta(Pdbctl.Meta):
        ref_tag = "net"
        data_object_cls = NetworkObject


class NetworkIXLanObject(PeeringDBEntity):
    description = "PeeringDB netixlan"
    relationships = {
        "net": {"bridge": Network, "filter": ("asn", "asn")},
        "ix": {"bridge": InternetExchange, "filter": ("ix", "ix_id")},
    }


class NetworkIXLan(Pdbctl):
    class Meta(Pdbctl.Meta):
        ref_tag = "netixlan"
        data_object_cls = NetworkIXLanObject


class NetworkContact(Pdbctl):
    ref_tag = "poc"


class IXLanPrefix(Pdbctl):
    ref_tag = "ixpfx"
