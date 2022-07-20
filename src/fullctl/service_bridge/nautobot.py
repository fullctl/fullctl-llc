try:
    from django.conf import settings

    DEFAULT_NAUTOBOT_TOKEN = settings.NAUTOBOT_TOKEN
except ImportError:
    DEFAULT_NAUTOBOT_TOKEN = ""

from fullctl.service_bridge.client import Bridge, DataObject

CACHE = {}


class NautobotObject(DataObject):
    source = "nautobot"
    description = "Nautobot Object"


class Nautobot(Bridge):

    """
    Service bridge for prefixctl data retrieval
    """

    url_prefix = ""
    results_key = "results"

    class Meta:
        service = "prefixctl"
        ref_tag = "base"
        data_object_cls = NautobotObject

    def __init__(self, key=None, org=None, **kwargs):

        if not key:
            key = DEFAULT_NAUTOBOT_TOKEN

        kwargs.setdefault("cache_duration", 10)
        kwargs.setdefault("cache", CACHE)

        super().__init__(settings.NAUTOBOT_URL, key, org, **kwargs)

    @property
    def auth_headers(self):
        return {"Authorization": f"Token {self.key}"}


class DeviceObject(NautobotObject):
    description = "Nautobot Device"


class Device(Nautobot):
    class Meta(Nautobot.Meta):
        ref_tag = "dcim/devices"
        data_object_cls = DeviceObject
