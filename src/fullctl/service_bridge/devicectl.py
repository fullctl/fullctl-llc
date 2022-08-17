try:
    from django.conf import settings

    DEFAULT_SERVICE_KEY = settings.SERVICE_KEY
except ImportError:
    DEFAULT_SERVICE_KEY = ""

from fullctl.service_bridge.client import Bridge, DataObject

CACHE = {}


class DeviceCtlEntity(DataObject):
    description = "DeviceCtl Object"
    source = "devicectl"


class Devicectl(Bridge):

    """
    Service bridge to devicectl for data
    retrieval
    """

    class Meta:
        service = "devicectl"
        ref_tag = "base"
        data_object_cls = DeviceCtlEntity

    def __init__(self, key=None, org=None, **kwargs):
        if not key:
            key = DEFAULT_SERVICE_KEY

        kwargs.setdefault("cache_duration", 10)
        kwargs.setdefault("cache", CACHE)

        super().__init__(settings.DEVICECTL_URL, key, org, **kwargs)
        self.url = f"{self.url}/service-bridge"


class Device(Devicectl):
    class Meta(Devicectl.Meta):
        ref_tag = "device"


class Facility(Devicectl):
    class Meta(Devicectl.Meta):
        ref_tag = "facility"
