from django.conf import settings

from fullctl.service_bridge.client import Bridge, DataObject

CACHE = {}


class PeeringDBEntity(DataObject):
    description = "PeeringDB Object"


class Pdbctl(Bridge):

    """
    Service bridge to pdbctl for peeringdb data
    retrieval
    """

    def __init__(self, key=None, org=None, **kwargs):
        if not key:
            key = settings.SERVICE_KEY

        kwargs.setdefault("cache_duration", 5)
        kwargs.setdefault("cache", CACHE)

        super().__init__(settings.PDBCTL_HOST, key, org, **kwargs)


class InternetExchange(Pdbctl):
    ref_tag = "ix"


class Network(Pdbctl):
    ref_tag = "net"


class NetworkIXLan(Pdbctl):
    ref_tag = "netixlan"


class NetworkContact(Pdbctl):
    ref_tag = "poc"
