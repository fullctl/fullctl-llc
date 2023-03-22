try:
    from django.conf import settings

    DEFAULT_SERVICE_KEY = settings.SERVICE_KEY
except ImportError:
    DEFAULT_SERVICE_KEY = ""

from fullctl.service_bridge.client import Bridge, DataObject, url_join

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
        self.url = url_join(self.url, "service-bridge/")


class Device(Devicectl):
    class Meta(Devicectl.Meta):
        ref_tag = "device"

    def request_dummy_device(self, org_slug, name, purpose):
        device = self.first(name=name, org_slug=org_slug)

        if device:
            return device

        device = self.create(
            {
                "name": name,
                "description": f"{purpose}",
                "org": org_slug,
                "type": "dummy",
            }
        )

        return device[0]


class Facility(Devicectl):
    class Meta(Devicectl.Meta):
        ref_tag = "facility"


class Port(Devicectl):
    class Meta(Devicectl.Meta):
        ref_tag = "port"

    def request_dummy_ports(
        self, org_slug, ports, name_prefix, device_type, member_id_arg="id"
    ):
        return self.post(
            "data/port/request_dummy_ports",
            json={
                "org": org_slug,
                "name_prefix": name_prefix,
                "device_type": device_type,
                "ports": ports,
            },
        )


class PortInfo(Devicectl):
    class Meta(Devicectl.Meta):
        ref_tag = "port_info"


class VirtualPort(Devicectl):
    class Meta(Devicectl.Meta):
        ref_tag = "virtual_port"


class IPAddress(Devicectl):
    class Meta(Devicectl.Meta):
        ref_tag = "ip"
