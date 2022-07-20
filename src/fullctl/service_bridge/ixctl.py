try:
    from django.conf import settings

    DEFAULT_SERVICE_KEY = settings.SERVICE_KEY
except ImportError:
    DEFAULT_SERVICE_KEY = ""

import fullctl.service_bridge.pdbctl as pdbctl
from fullctl.service_bridge.client import Bridge, DataObject

CACHE = {}


class IxctlEntity(DataObject):
    source = "ixctl"
    description = "Ixctl Object"


class Ixctl(Bridge):

    """
    Service bridge for ixctl data retrieval
    """

    class Meta:
        service = "ixctl"
        ref_tag = "base"
        data_object_cls = IxctlEntity

    def __init__(self, key=None, org=None, **kwargs):

        if not key:
            key = DEFAULT_SERVICE_KEY

        kwargs.setdefault("cache_duration", 10)
        kwargs.setdefault("cache", CACHE)

        super().__init__(settings.IXCTL_URL, key, org, **kwargs)
        self.url = f"{self.url}/service-bridge"


class InternetExchangeObject(IxctlEntity):
    description = "Ixctl Exchange"


class InternetExchange(Ixctl):
    class Meta(Ixctl.Meta):
        ref_tag = "ix"
        data_object_cls = InternetExchangeObject


class InternetExchangeMemberObject(IxctlEntity):
    description = "Ixctl Exchange Member"
    relationships = {
        "net": {"bridge": pdbctl.Network, "filter": ("asn", "asn")},
        "ix": {"bridge": InternetExchange, "filter": ("ix", "ix_id")},
    }


class InternetExchangeMember(Ixctl):
    class Meta(Ixctl.Meta):
        ref_tag = "member"
        data_object_cls = InternetExchangeMemberObject

    def set_mac_address(self, member_id, mac_address, source):
        data = {"mac_address": mac_address, "source": source}
        self.put(f"data/member/{member_id}/sync/mac-address", data=data)

    def set_as_macro(self, asn, as_macro, source):
        data = {"as_macro": as_macro, "asn": asn, "source": source}
        self.put("data/member/sync/as-macro", data=data)
